# TB331FC TWRP 构建调试记录

联想小新 Pad 2024 (TB331FC, SM6225-AD/khaje) TWRP 移植 · GitHub Actions 云编译
仓库:`yxyyds666/TB331FC-TWRP` · 产物:`recovery.img`(独立 recovery 分区)

---

## 一、核心架构要素

### Manifest 与分支
| 项 | 值 |
|---|---|
| manifest | `minimal-manifest-twrp/platform_manifest_twrp_aosp` |
| 分支 | **twrp-14.1**(必须,非 twrp-14) |
| bootable/recovery | 已由 twrp-default.xml 内置覆盖为 TeamWin `android_bootable_recovery` android-14.1 |
| build/make | TeamWin `android_build` android-14.1(三段式 lunch、release config 机制) |
| 内核 | `yxyyds666/TB331FC-Kernel` release 的 `boot-main.img`(header v4),unpack_bootimg 提取 Image |
| 内核提取工具 | `LineageOS/android_system_tools_mkbootimg` lineage-22.1 的 unpack_bootimg.py(osm0sis 是纯 C,无 py;PyPI 无 mkbootimg) |

### 设备树关键配置
| 项 | 值 |
|---|---|
| 平台 | khaje, arm64 |
| 内核 | prebuilt GKI 5.15.167 Image,`BOARD_BOOT_HEADER_VERSION := 4` |
| recovery 分区 | 独立存在(用户确认),产物 recovery.img 刷 recovery_a/recovery_b |
| `TARGET_COPY_OUT_VENDOR := vendor` | 必须,否则 board_config.mk:682 报错 |
| `BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4` | TWRP 拷贝 vendor 文件进 ramdisk 的机制(保留) |
| crypto | TW_INCLUDE_CRYPTO/FBE、TW_INCLUDE_FBE_METADATA_DECRYPT、BOARD_USES_QCOM_FBE_DECRYPTION |
| 模块加载 | TW_LOAD_VENDOR_MODULES(nvt36523_spi.ko nopmi-chg.ko panel_event_notifier.ko spi-msm-geni.ko)+ modules.load.twrp + init rc 触发 |
| 动态分区 | lenovo_dynamic_partitions, SUPER=9126805504 |
| 已删除 | PRODUCT_STATIC_BOOT_CONTROL_HAL(obsolete)、BOARD_USES_RECOVERY_AS_BOOT |

### CI 关键要素(.github/workflows/build.yml)
- **OOM 防护**:禁用 systemd-oomd + 12G swap + 构建目录放 /mnt + `-j2`(16GB runner 必配)
- **ccache**:actions/cache 缓存 ~/.ccache,显著加速重复构建
- **lunch**:三段格式 `<product>-<release>-<variant>`,尝试 ap2a→ap3a→trunk_staging→trunk
- **AIDL stub**:Build 前为 4 个缺失 ndk_platform 库建空 .so/.so.toc(**obj 和 obj_arm 都要**)
- **补丁脚本**:`device/lenovo/TB331FC/patch-vold-fscrypt.py`(恢复 vold fscrypt union API)
- **产物定位**:shell 变量(FOUND)而非 $GITHUB_ENV(同步骤不可读)
- **pipefail**:`set -o pipefail`,防止 tee 吞掉 ninja 失败

---

## 二、完整报错清单与修复(16 轮)

| # | 报错 | 根因 | 修复 |
|---|------|------|------|
| 1 | YAML ScannerError line 61 / "workflow file issue" | heredoc 写 XML 行首无缩进,YAML 断裂 | 改 printf |
| 2 | `E: Unable to locate package lib32gcc-1` | 包名不存在 | 改 lib32gcc-s1 |
| 3 | `No matching distribution found for mkbootimg` | PyPI 无此包 | 弃 pip,用仓库脚本 |
| 4 | `unpack_bootimg: 404: command not found` | osm0sis 仓库无 py 文件 | 换 LineageOS 镜像 |
| 5 | `remove-project element specifies non-existent project` | twrp-14 已内置 TeamWin 覆盖,重复 remove | 删 local manifest;顺带发现 twrp-14 缺 build/release → 切 twrp-14.1 |
| 6 | `Invalid lunch combo: twrp_TB331FC-eng` | TeamWin android-14.1 要求三段 `<p>-<release>-<variant>` | 循环试 ap2a 等 |
| 7 | `No release config found for TARGET_RELEASE: ap2a. Available releases are: .` | twrp-14 分支无 build/release 项目 | 切 twrp-14.1(自带 ap2a) |
| 8 | `PRODUCT_STATIC_BOOT_CONTROL_HAL is obsolete` | 14.1 弃用该变量 | 从 device.mk 删除 |
| 9 | `TARGET_COPY_OUT_VENDOR must be set to 'vendor' to use a vendor image` | vendor image 路径缺该变量 | BoardConfig 补 `TARGET_COPY_OUT_VENDOR := vendor` |
| 10 | `The hosted runner lost communication with the server` | Soong 全树分析 OOM,被 systemd-oomd 杀 | 禁 oomd + 12G swap + /mnt + -j2 |
| 11 | `no recovery/boot img found`(构建实际成功) | `${{ env.FOUND }}` 同步骤内读不到刚写入的 GITHUB_ENV | 改 shell 变量 |
| 12 | `kernel.mk:594: commands commence before first target` | TeamWin vendor/twrp 上游 tab 缩进 bug(rule 外 tab 行) | CI sed 删除该行(depmod 已由 prebuilt/Android.mk 完成) |
| 13 | `ninja: 'android.security.apc-ndk_platform.so.toc' ... missing and no known rule` | Android 14 只生成 `-ndk`,libtar 链接 `-ndk_platform` | 建空 stub(obj + obj_arm 两架构) |
| 14 | `append.c:154: undeclared function 'get_policy_size'` + v1/v2 指针不匹配 | vold android-14.1 在 2022 年退化 fscrypt API(删 union/get_policy_*),libtar 14.1 仍用 | 补丁脚本恢复 12.1 的 union API |
| 15 | `Decrypt.cpp:126: undeclared identifier 'policy'` | 补丁脚本只换签名行,14.1 旧函数体残留 | 整函数替换 + 括号偏移修正 |
| 16 | `fscryptpolicyget.cpp:33: no matching function for call to 'fscrypt_policy_get_struct'` | 14.1 工具仍用旧 v1/v2 API | 替换为 12.1 版 fscryptpolicyget.cpp |

---

## 三、vold fscrypt API 补丁(patch-vold-fscrypt.py)

**上游 bug**:`system/vold` android-14.1 分支 2022 年 commit "fscrypt: move functionality to libvold" 删除了:
- `typedef union fscrypt_policy`(v1/v2 合并)
- `get_policy_size` / `get_policy_descriptor` / `get_policy` / `fscrypt_policy_size`
- 而 `bootable/recovery` android-14.1 的 libtar(append.c/extract.c)仍在调用 → 编译失败

**12.1 分支反而有完整新 API**(2023-01 "vold: dynamically choose fscrypt policy [2/2]")。

**补丁内容**:
1. `fscrypt_policy.h` → 12.1 版(union typedef + 全部新 API 声明)
2. `fscrypt_policy.cpp` → 12.1 版(实现),其中 `isFsKeyringSupported` 分支删除(14.1 已移除该 API,改为恒走 EX ioctl)
3. `fscryptpolicyget.cpp` → 12.1 版(union API)
4. `Decrypt.cpp`:lookup_ref_key_internal 整体替换为 12.1 风格(签名加 size/hex_size,保留 14.1 的 UserPolicies 类型 `it->second.internal.key_raw_ref`);lookup_ref_key / lookup_ref_tar 改为 union 签名(调用方 libtar 传 `fscrypt_policy*`)

---

## 四、待办 / 当前状态

- [x] 设备树 + CI 全链路修复(16 轮)
- [ ] 构建产出 recovery.img 并发布 Release
- [ ] 刷机实测:fastboot flash recovery_a/b recovery.img
- [ ] 验证触摸/解密/ADB 等功能
- [ ] 未决点:recovery.img 是否含内核(polygraphene 联想平板方案用 `BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := true`,待实机验证)

## 五、参考仓库

- `polygraphene/android_device_lenovo_TB321FU` — 联想平板 TWRP(同思路:BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE, vendor.prop 等)
- `DUptain1993/kansas-device-tree` — fox_14.1 完整 CI(OOM/磁盘/内存全套踩坑记录)
- `Night114514/twrp-builder-rothko` PR#9/10 — AIDL ndk_platform stub 方案(与 #13 相同)
- `MissMyTime/twrp_device_sm8850` — TWRP 14/16 设备树补丁集
