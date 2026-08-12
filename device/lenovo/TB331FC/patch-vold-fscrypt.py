#!/usr/bin/env python3
"""
Patch TeamWin system/vold android-14.1 to restore the fscrypt_policy union API
that libtar (bootable/recovery android-14.1) requires.

Upstream bug: vold's fscrypt_policy.h was regressed in 2022 ("fscrypt: move
functionality to libvold") and no longer declares the union fscrypt_policy
type nor get_policy_size/get_policy_descriptor/get_policy helpers, while
libtar still calls them. android-12.1 still has the full API.

Strategy:
  1. Replace fscrypt_policy.h and fscrypt_policy.cpp with the android-12.1
     versions (they contain the union typedef + helpers + implementations).
  2. Rewrite lookup_ref_key / lookup_ref_tar in Decrypt.cpp to the union
     signatures used by libtar, keeping vold 14.1's UserPolicies internals.
"""

import os
import subprocess
import sys

VOLD = "system/vold"
VOLD_BRANCH = "android-14.1"
TW_ORG = "https://raw.githubusercontent.com/TeamWin/android_system_vold"


def sh(cmd):
    print(">>> " + cmd, flush=True)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit(r.returncode)
    return r.stdout


def fetch(url, dest):
    sh(f"curl -sL '{url}' -o {dest}")


def main():
    if not os.path.isdir(VOLD):
        print(f"error: {VOLD} not found (run from workspace root)")
        sys.exit(1)

    # 1. Replace fscrypt_policy.h / fscrypt_policy.cpp with android-12.1 versions
    fetch(f"{TW_ORG}/android-12.1/fscrypt_policy.h", f"{VOLD}/fscrypt_policy.h")
    fetch(f"{TW_ORG}/android-12.1/fscrypt_policy.cpp", f"{VOLD}/fscrypt_policy.cpp")

    # 1a. fscryptpolicyget.cpp (14.1) uses the old v1/v2 API; replace with
    #     the android-12.1 version that uses the union API.
    fetch(f"{TW_ORG}/android-12.1/fscryptpolicyget.cpp", f"{VOLD}/fscryptpolicyget.cpp")

    # 1b. android-14.1 removed android::vold::isFsKeyringSupported(); the 12.1
    #     fscrypt_policy_get_struct uses it. Drop the keyring branch and always
    #     use the EX ioctl like 14.1 does.
    fp = f"{VOLD}/fscrypt_policy.cpp"
    with open(fp) as f:
        fpsrc = f.read()
    old_keyring = """    if (android::vold::isFsKeyringSupported()) {
        ex_policy.policy_size = sizeof(ex_policy.policy);
        if (ioctl(fd, FS_IOC_GET_ENCRYPTION_POLICY_EX, &ex_policy) != 0) {
            PLOG(ERROR) << "Failed to get encryption policy for " << directory;
            close(fd);
            return false;
        }
    } else {
        if (ioctl(fd, FS_IOC_GET_ENCRYPTION_POLICY, &ex_policy.policy.v1) != 0) {
            PLOG(ERROR) << "Failed to get encryption policy for " << directory;
            close(fd);
            return false;
        }
    }"""
    new_keyring = """    ex_policy.policy_size = sizeof(ex_policy.policy);
    if (ioctl(fd, FS_IOC_GET_ENCRYPTION_POLICY_EX, &ex_policy) != 0) {
        PLOG(ERROR) << "Failed to get encryption policy for " << directory;
        close(fd);
        return false;
    }"""
    if old_keyring in fpsrc:
        fpsrc = fpsrc.replace(old_keyring, new_keyring)
        with open(fp, "w") as f:
            f.write(fpsrc)
        print("patched: fscrypt_policy_get_struct keyring branch removed")
    else:
        print("warning: keyring branch pattern not found in fscrypt_policy.cpp")

    # 2. Rewrite lookup_ref_key / lookup_ref_tar / lookup_ref_key_internal in
    #    Decrypt.cpp to union signatures (libtar passes fscrypt_policy*).
    dec = f"{VOLD}/Decrypt.cpp"
    with open(dec) as f:
        src = f.read()

    internal_14 = """static bool lookup_ref_key_internal(std::map<userid_t, UserPolicies> key_map, const uint8_t* policy, userid_t* user_id) {"""

    # The 12.1 internal takes (size, hex_size) too; keep 14.1's UserPolicies
    # type but extend the signature like 12.1 so union callers can pass sizes.
    internal_12 = """static bool lookup_ref_key_internal(std::map<userid_t, UserPolicies> key_map, const uint8_t* policy, uint8_t size, uint8_t hex_size, userid_t* user_id) {
	char policy_string_hex[hex_size];
	char key_map_hex[hex_size];
	bytes_to_hex(policy, size, policy_string_hex);

    for (std::map<userid_t, UserPolicies>::iterator it=key_map.begin(); it!=key_map.end(); ++it) {
		bytes_to_hex(reinterpret_cast<const uint8_t*>(&it->second.internal.key_raw_ref[0]), size, key_map_hex);
		std::string key_map_hex_string = std::string(key_map_hex);
		if (key_map_hex_string == policy_string_hex) {
            *user_id = it->first;
            return true;
        }
    }
    return false;
}"""

    if internal_14 not in src:
        print("error: 14.1 lookup_ref_key_internal signature not found")
        sys.exit(1)
    # Replace the ENTIRE 14.1 internal function (signature line through its
    # closing brace at column 0) with the 12.1-style implementation.
    fstart = src.find(internal_14)
    # find the closing "}\n" of the function: the line after the last
    # "    return false;\n}\n" belonging to this function
    fend = src.find("\n}\n", fstart)
    if fend == -1:
        print("error: lookup_ref_key_internal body end not found")
        sys.exit(1)
    src = src[:fstart] + internal_12 + src[fend + 3:]

    # Replace the whole conditional-compiled lookup_ref_key (v1/v2 split)
    # with a single union-signature implementation.
    start = src.find("""#ifdef USE_FSCRYPT_POLICY_V1
extern "C" bool lookup_ref_key(fscrypt_policy_v1* fep, uint8_t* policy_type) {""")
    if start == -1:
        print("error: lookup_ref_key (v1/v2) not found")
        sys.exit(1)
    # find the end of lookup_ref_key (the closing of the #else branch)
    end_marker = """	memcpy(policy_type, policy_type_string.data(), policy_type_string.size());
	printf("storing policy type: %s\\n", policy_type);
    return true;
}

extern "C" bool lookup_ref_tar"""
    end = src.find(end_marker, start)
    if end == -1:
        print("error: lookup_ref_key end marker not found")
        sys.exit(1)
    end += len("""	memcpy(policy_type, policy_type_string.data(), policy_type_string.size());
	printf("storing policy type: %s\\n", policy_type);
    return true;
}

""")

    new_lookup_ref_key = """extern "C" bool lookup_ref_key(fscrypt_policy* fep, uint8_t* policy_type) {
	userid_t user_id = 0;
	std::string policy_type_string;

	uint8_t *descriptor = get_policy_descriptor(fep);
	uint8_t hex_size = get_policy_size(fep, true);
	uint8_t size = get_policy_size(fep, false);
	char policy_hex[hex_size];
	bytes_to_hex(descriptor, size, policy_hex);
	if (std::strncmp((const char*)descriptor, de_key_raw_ref.c_str(), size) == 0) {
		policy_type_string = std::to_string(fep->version) + SYSTEM_DE_FSCRYPT_POLICY;
		memcpy(policy_type, policy_type_string.data(), policy_type_string.size());
		return true;
	}
	if (!lookup_ref_key_internal(s_de_policies, descriptor, size, hex_size, &user_id)) {
		if (!lookup_ref_key_internal(s_ce_policies, descriptor, size, hex_size, &user_id)) return false;
		else policy_type_string = std::to_string(fep->version) + USER_CE_FSCRYPT_POLICY + std::to_string(user_id);

	} else policy_type_string = std::to_string(fep->version) + USER_DE_FSCRYPT_POLICY + std::to_string(user_id);

	memcpy(policy_type, policy_type_string.data(), policy_type_string.size());
	printf("storing policy type: %s\\n", policy_type);
	return true;
}

"""
    src = src[:start] + new_lookup_ref_key + src[end:]

    # Replace lookup_ref_tar: 14.1 takes (const uint8_t*, uint8_t*),
    # libtar calls lookup_ref_tar(fscrypt_policy*, uint8_t*).
    start = src.find('extern "C" bool lookup_ref_tar(')
    if start == -1:
        print("error: lookup_ref_tar not found")
        sys.exit(1)
    # find the closing brace of the function (last '}' before the next extern/static)
    # simpler: locate "extern "C" bool fscrypt_policy_get_struct" or next function
    nxt = src.find("\n}\n", start)
    # find function boundary by scanning for a line starting with '}' at col 0 followed by blank
    idx = start
    brace = src.find("\n}\n", idx)
    if brace == -1:
        print("error: lookup_ref_tar closing brace not found")
        sys.exit(1)
    end = brace + 3

    new_lookup_ref_tar = """extern "C" bool lookup_ref_tar(fscrypt_policy *fep, uint8_t* policy) {
	if (fep->version < FSCRYPT_POLICY_V1 || fep->version > FSCRYPT_POLICY_V2) {
		printf("Unexpected version: %d\\n", (int)fep->version);
 		return false;
 	}
	uint8_t hex_size, size, *descriptor;
	hex_size = get_policy_size(fep, true);
	size = get_policy_size(fep, false);
	descriptor = get_policy_descriptor(fep);
	std::string policy_type_string = std::string((char *) descriptor);
	char policy_hex[hex_size];
	bytes_to_hex(descriptor, size, policy_hex);
	if (policy_type_string.substr(1, 2) == SYSTEM_DE_KEY) {
		memcpy(policy, de_key_raw_ref.data(), de_key_raw_ref.size());
		return true;
	}

	std::string raw_ref;

	if (policy_type_string.substr(1, 1) == USER_DE_KEY) {
		userid_t user_id = std::stoi(policy_type_string.substr(3, 4).c_str());
		if (!lookup_key_ref(s_de_policies, user_id, &raw_ref)) return false;
		memcpy(policy, raw_ref.data(), raw_ref.size());
		return true;
	} else if (policy_type_string.substr(1, 1) == USER_CE_KEY) {
		userid_t user_id = std::stoi(policy_type_string.substr(3, 4).c_str());
		if (!lookup_key_ref(s_ce_policies, user_id, &raw_ref)) return false;
		memcpy(policy, raw_ref.data(), raw_ref.size());
		return true;
	} else {
		printf("Unexpected policy type: %s\\n", policy_type_string.c_str());
		return false;
	}
}

"""
    src = src[:start] + new_lookup_ref_tar + src[end:]

    with open(dec, "w") as f:
        f.write(src)

    print("vold fscrypt patch applied OK")


if __name__ == "__main__":
    main()
