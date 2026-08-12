#!/usr/bin/env python3
"""
Patch TeamWin bootable/recovery android-14.1 build files so recovery/libtar
link against the AIDL NDK libs that actually exist in the twrp-14.1 minimal
manifest, and against the transitive deps of libvold.

Files patched:
  - bootable/recovery/Android.mk        (recovery executable)
  - bootable/recovery/libtar/Android.mk (libtar.so, FBE decrypt)

Root cause:
  - Both files reference the pre-Android-14 AIDL library names
    `android.security.apc-ndk_platform`, `android.system.keystore2-V1-ndk_platform`,
    `android.security.authorization-ndk_platform`, `android.security.maintenance-ndk_platform`.
    In Android 14 these interfaces are declared with only the plain `-ndk`
    variant (and keystore2 is versioned V4), so the `-ndk_platform` modules do
    not exist and ninja reports "no known rule to make it".
  - libvold (static lib pulled in by libtar) additionally requires
    libsysutils, libasync_safe and libboot_control_client, which are missing
    from libtar's LOCAL_SHARED_LIBRARIES -> undefined symbols at link time
    (NetlinkEvent::*, async_safe_format_log, BootControlClient::WaitForService).
"""

import os
import re
import sys

FILES = [
    "bootable/recovery/Android.mk",
    "bootable/recovery/libtar/Android.mk",
]

# (old, new) pairs applied to every patched file
RENAMES = [
    ("android.security.apc-ndk_platform", "android.security.apc-ndk"),
    ("android.system.keystore2-V1-ndk_platform", "android.system.keystore2-V4-ndk"),
    ("android.security.authorization-ndk_platform", "android.security.authorization-ndk"),
    ("android.security.maintenance-ndk_platform", "android.security.maintenance-ndk"),
]

# Libraries libvold depends on but libtar does not link.
# NOTE: vold_default_libs lists libasync_safe in static_libs (it is a static
# lib, no libasync_safe.so exists); libsysutils and libboot_control_client are
# in shared_libs.
ADD_SHARED = [
    "libsysutils",
    "libboot_control_client",
]

ADD_STATIC = [
    "libasync_safe",
]


def main():
    for f in FILES:
        if not os.path.isfile(f):
            print(f"error: {f} not found (run from workspace root)")
            sys.exit(1)

    for f in FILES:
        print(f"=== {f} ===")
        with open(f) as fh:
            src = fh.read()

        for old, new in RENAMES:
            if old in src:
                src = src.replace(old, new)
                print(f"renamed: {old} -> {new}")
            else:
                print(f"ok (absent): {old}")

        # recovery executable uses the same libgatekeeper_aidl anchor as libtar
        anchor = "        libgatekeeper_aidl"
        if anchor not in src:
            print("warning: libgatekeeper_aidl anchor not found, skipping shared/static adds")
        else:
            added = []
            for lib in ADD_SHARED:
                if re_line_present(src, lib):
                    print(f"already present: {lib}")
                    continue
                src = src.replace(anchor, f"{anchor} \\\n        {lib}", 1)
                added.append(lib)
                print(f"added: {lib}")

            # Add static libs to LOCAL_STATIC_LIBRARIES (libtar FBE block).
            # Recovery executable's crypto block uses "LOCAL_STATIC_LIBRARIES += libkeymint_support".
            if "libvold libscrypt_static" in src:
                anchor_static = "    LOCAL_STATIC_LIBRARIES += libvold libscrypt_static"
                for lib in ADD_STATIC:
                    if re_line_present(src, lib):
                        print(f"already present: {lib}")
                        continue
                    src = src.replace(anchor_static,
                                      f"{anchor_static} {lib}", 1)
                    added.append(lib)
                    print(f"added (static): {lib}")

        with open(f, "w") as fh:
            fh.write(src)
        print(f"patched: {f}")


def re_line_present(src, name):
    # match a line that is exactly the module name with optional trailing '\'
    return re.search(rf"^\s+{re.escape(name)}\s*\\?$", src, re.MULTILINE) is not None


if __name__ == "__main__":
    main()
