#!/usr/bin/env python3
"""
Patch TeamWin bootable/recovery android-14.1 libtar/Android.mk so libtar.so
links against the AIDL NDK libs that actually exist in the twrp-14.1 minimal
manifest, and against the transitive deps of libvold.

Root cause:
  - libtar/Android.mk (android-14.1) references the pre-Android-14 AIDL library
    names `android.security.apc-ndk_platform`, `android.system.keystore2-V1-ndk_platform`,
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
import sys

LIBTAR = "bootable/recovery/libtar/Android.mk"

# (old, new) pairs in the LOCAL_SHARED_LIBRARIES block
RENAMES = [
    ("android.security.apc-ndk_platform", "android.security.apc-ndk"),
    ("android.system.keystore2-V1-ndk_platform", "android.system.keystore2-V4-ndk"),
    ("android.security.authorization-ndk_platform", "android.security.authorization-ndk"),
    ("android.security.maintenance-ndk_platform", "android.security.maintenance-ndk"),
]

# Libraries libvold depends on but libtar does not link
ADD_SHARED = [
    "libsysutils",
    "libasync_safe",
    "libboot_control_client",
]


def main():
    if not os.path.isfile(LIBTAR):
        print(f"error: {LIBTAR} not found (run from workspace root)")
        sys.exit(1)

    with open(LIBTAR) as f:
        src = f.read()

    for old, new in RENAMES:
        if old in src:
            src = src.replace(old, new)
            print(f"renamed: {old} -> {new}")
        else:
            print(f"warning: {old} not found")

    # Add missing shared libs at the end of the LOCAL_SHARED_LIBRARIES list.
    # The FBE block ends with "libgatekeeper_aidl" (no trailing backslash).
    anchor = "        libgatekeeper_aidl"
    if anchor not in src:
        print("error: libgatekeeper_aidl anchor not found")
        sys.exit(1)

    added = []
    for lib in ADD_SHARED:
        if re_line_present(src, lib):
            print(f"already present: {lib}")
            continue
        src = src.replace(anchor, f"{anchor} \\\n        {lib}", 1)
        added.append(lib)
        print(f"added: {lib}")

    with open(LIBTAR, "w") as f:
        f.write(src)

    if added:
        print(f"patched: libtar link libs updated (+{len(added)})")
    else:
        print("patched: libtar link libs OK")
    print("done")


def re_line_present(src, name):
    # match a line that is exactly the module name with optional trailing '\'
    import re
    return re.search(rf"^\s+{re.escape(name)}\s*\\?$", src, re.MULTILINE) is not None


if __name__ == "__main__":
    main()
