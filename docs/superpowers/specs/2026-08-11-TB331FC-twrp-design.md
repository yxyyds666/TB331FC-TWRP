# TB331FC (Lenovo Xiaoxin Pad 2024) TWRP 移植设计

日期:2026-08-11
状态:设计定稿,待实施

## 1. 背景与目标

为联想小新 Pad 2024 (TB331FC) 移植 Team Win Recovery Project (TWRP),通过 GitHub Actions 云编译产出可直接刷入的 recovery 镜像。

### 设备信息

- 型号:Lenovo Xiaoxin Pad 2024,代号 `bengal_515`,仓库设备名 `TB331FC`
- SoC:Qualcomm Snapdragon 685 (SM6225-AD),平台代号 `khaje` / `bengal`
- 系统:Android 13 (TKQ1.230227.001) / ZUI 15.1.045,内核 GKI 5.15.167
- 显示:11 寸 1920x1200 IPS,Synaptics TCM I2C 触摸屏
- 分区:A/B + 动态分区(super logical),独立 recovery 分区 100MB

### 目标产物

1. `recovery.img` — TWRP recovery 镜像(fastboot 刷入)
2. `TB331FC-TWRP-AnyKernel3.zip` — 设备端可刷的安装包
3. GitHub Actions 工作流:push 自动编译 + 发布 Release

## 2. 已确认的关键事实(实机镜像分析)

来源:用户提供的 `dtbo_a/b.img`、`vendor_boot_a/b.img`、`vbmeta*.img` + 内核仓库的 `boot_a.img`。

- **boot_a.img**:boot header v4,内核 Image ~47MB,无 ramdisk(GKI 原版)
- **vendor_boot_a.img**:含 dtb(6 个 FDT,`qcom,khaje` 平台)+ vendor ramdisk(LZ4 cpio)
  - vendor ramdisk 内含 first_stage_ramdisk + 240 个 `.ko` + `modules.load.recovery` + fstab
  - 显示栈完整:`msm_drm.ko`、`dispcc-khaje.ko`、`pinctrl-khaje.ko` 等
  - **触摸驱动不在其中**(Synaptics TCM 驱动 `synaptics_tcm_*.ko` 与固件 `Ksynaptics_firmware_k.img` 在 `vendor_dlkm` 分区)
- **dtbo_a.img**:标准 dtbo 格式,45 个 FDT overlay entry
- **fstab**(从 vendor ramdisk 提取):全 logical 分区 + userdata f2fs 加密(aes-256-xts wrappedkey v0)+ metadata

## 3. 编译架构

### 3.1 构建管线

```
TWRP twrp-14 manifest (minimal-manifest-twrp_aosp)
  + repo sync (Android 14 base)
  + device/lenovo/TB331FC (本仓库设备树)
  + prebuilt GKI 5.15 kernel Image (从 TB331FC-Kernel release 下载)
  + dtb.img (从 vendor_boot_a.img 提取的 6 个 FDT,经 mkdtimg 打包)
  → 编译 recoveryimage
  → recovery.img + repack AnyKernel3 zip
  → 发布 GitHub Release
```

### 3.2 参照基准

- 主要参照:`chickendrop89/device_xiaomi_sm6225ad-recovery`(twrp-12.1 分支,同 khaje/SM6225-AD 平台,已验证可编译)
  - 分区尺寸、GKI 处理、init rc、USB functionfs、AVB 配置均对齐
- 结构来源:`twrpdtgen/android_device_lenovo_bengal_515`(本机固件生成,提供机型专属信息)
  - 设备代号、分区表、fstab、kernel 尺寸、触摸节点(synaptics_tcm@20)

## 4. 设备树结构

```
device/lenovo/TB331FC/
├── Android.mk / AndroidProducts.mk
├── BoardConfig.mk          # 平台/分区/内核/AVB 配置
├── twrp_TB331FC.mk         # PRODUCT_NAME := twrp_TB331FC
├── device.mk               # 继承产品配置
├── board-info.txt          # require board=TB331FC
├── system.prop
├── recovery/
│   └── root/
│       ├── init.recovery.qcom.rc
│       ├── init.recovery.usb.rc
│       └── system/etc/recovery.fstab
└── prebuilt/               # vendor blobs 占位 + dtb.img 生成脚本
```

### 4.1 BoardConfig.mk 关键项

```makefile
TARGET_BOARD_PLATFORM      := khaje
TARGET_BOARD_PLATFORM_GPU  := qcom-adreno610
TARGET_PREBUILT_KERNEL     := /dev/null   # GKI,recovery 不含内核
BOARD_USES_GENERIC_KERNEL_IMAGE := true
BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := true
BOARD_USES_RECOVERY_AS_BOOT :=            # 独立 recovery 分区
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 104857600
BOARD_DTBOIMG_PARTITION_SIZE := 25165824
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := 100663296
BOARD_RAMDISK_USE_LZ4 := true
BOARD_AVB_ENABLE := true
BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --flags 3
```

### 4.2 recovery.fstab

基于原厂 fstab 改写为 TWRP 格式:
- 全 logical 分区(system/system_ext/product/vendor/odm/vendor_dlkm/system_dlkm):slotselect + logical
- userdata:f2fs + 加密参数
- metadata:f2fs + wrappedkey
- persist / misc / modem
- microSD(sdhci)+ USB OTG

## 5. 触摸屏处理(已确认方案)

### 5.1 硬件事实(镜像级证据)

- **量产触摸芯片:Novatek NVT36523(SPI)** — `vendor_dlkm` 分区只有 `nvt36523_spi.ko`,
  compatible=`novatek,NVT-ts-spi`(对应 dtbo overlay `qupv3_se0_spi` 下的 `touch@0` 节点)
- dtbo overlay 同时含 synaptics/novatek/himax 三套节点,但 vendor_dlkm 只编译了 Novatek SPI 版
  → 判定 TB331FC 实际触摸 = **Novatek NVT36523 SPI**
- 驱动依赖:`depends=nopmi-chg,panel_event_notifier`(此两模块在 vendor_boot ramdisk 中)
- 总线驱动:`spi-msm-geni.ko`(SPI 控制器,vendor_boot 有)
- GPIO:irq=tlmm 0x50,int,reset=tlmm 0x56,SPI 总线 `qupv3_se0_spi`
- 固件:Novatek 量产参数存于 dtbo `novatek-mp-criteria-6072@0`,驱动经 `novatek,mp-support-dt` 从 DT 读取(无需单独固件文件)

### 5.2 加载机制(参照 tapas/OrangeFox 已验证做法)

```
init.recovery.qcom.rc
  └─ 触发模块加载
      └─ system/bin/runatboot.sh
          └─ load_touch_drivers()  →  modprobe nvt36523_spi
```

- 模块放入 `prebuilt/vendor/lib/modules/1.1/`(含依赖 `nopmi-chg.ko`、`panel_event_notifier.ko`、`spi-msm-geni.ko`)
- `runatboot.sh` 中把 `nvt36523_spi` 加入 `modules` 列表,`modprobe -d` 加载

### 5.3 资源来源(已完成提取)

用户已提供 `vendor_dlkm_a.img`(58MB ext2),从中提取:
- `nvt36523_spi.ko` — 触摸主驱动 ✅
- 依赖模块从 vendor_boot ramdisk 取 ✅
- 固件参数在 dtbo,recovery 用原厂 dtb/dtbo 即可 ✅

### 5.4 实施顺序

1. **阶段 1**:无触摸可启动镜像(音量键 + 电源键导航),验证显示/分区/刷机管线
2. **阶段 2**:把 `nvt36523_spi.ko` + 依赖 + `spi-msm-geni.ko` 打进 recovery ramdisk,
   `runatboot.sh` 加载,验证触摸

## 6. GitHub Actions 工作流

### 6.1 触发

- push 到 main 分支自动构建(版本 patch)
- workflow_dispatch 手动触发(可 bump minor/major,复用内核仓库版本规范)

### 6.2 环境

- `ubuntu-22.04`(或 24.04),Python 3.11+
- 需足够磁盘(~40GB,repo sync + 编译)

### 6.3 步骤

1. checkout
2. 安装依赖(java、repo、git、lz4、mkbootimg 工具)
3. `repo init -u minimal-manifest-twrp_aosp -b twrp-14` + repo sync
4. 放入设备树(本仓库 `device/lenovo/TB331FC`)
5. 下载 GKI 内核 Image(从 TB331FC-Kernel release 获取)
6. 提取 vendor_boot dtb → 打包 dtb.img
7. `source build/envsetup.sh && lunch twrp_TB331FC-eng && mka recoveryimage adbd`
8. 产物:recovery.img + AnyKernel3 zip
9. 发布 Release

## 7. 刷机方式

- `fastboot flash recovery recovery.img`(独立 recovery 分区)
- 或设备端刷 AnyKernel3 zip
- 注意:A/B 设备需确认当前槽位,刷对应 recovery_<slot>

## 8. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 触摸不可用 | 使用不便 | 音量键导航;后续补 vendor_dlkm 模块 |
| GKI 内核与 recovery 兼容 | 可能无法启动 | 复用已验证的 GKI 5.15.167 内核,配置对齐 tapas 成功案例 |
| dtb 打包错误 | 显示不工作 | 严格按 vendor_boot 提取的原始 FDT,mkdtimg 验证 |
| CI 磁盘/内存不足 | 编译失败 | 使用 24.04 + 大 runner,清理 ccache |

## 9. 范围

- 本阶段:可启动的 TWRP 镜像(显示+分区+ADB+刷机),触摸为后续迭代
- 不包括:data 解密、OTA 保留(update_engine sideload 可后续加)、触摸增强
