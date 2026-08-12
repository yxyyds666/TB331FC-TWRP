# TWRP device tree for Lenovo TB331FC

TWRP recovery for the Lenovo Xiaoxin Pad 2024 (TB331FC), Qualcomm SM6225-AD (bengal/khaje).

## Device specifications

| Property       | Value                                |
| -------------- | ------------------------------------ |
| SoC            | Qualcomm SM6225-AD (Snapdragon 685)  |
| Board          | bengal                               |
| CPU            | Octa-core (4x2.8 GHz Cortex-A73 & 4x1.9 GHz Cortex-A53) |
| GPU            | Adreno 610                           |
| Android        | 13 (TKQ1.230227.001), ZUI 1.1.10     |
| Touch          | Novatek NVT36523 (SPI)               |
| Boot header    | v4 (GKI, no dtb in boot)             |

## Porting strategy

Fused from two proven sources:

1. **Stock recovery_a.img** (from the device): authoritative partition layout
   (`system/etc/recovery.fstab`), init scripts, boot control / fastboot / health
   HAL binaries.
2. **spes-515-devs twrp-12.1** device tree: Redmi Note 11 is the same platform
   (SM6225 bengal + Adreno 610 + GKI 5.15), providing a verified twrp-12.1
   build framework. twrp-12.1 manifest is self-consistent (vold 12.1 still has
   the fscrypt/cryptfs APIs that Android 14 removed), so **no source patches
   are needed**.

The device is a GKI device: stock `recovery_a.img` contains **no kernel**
(empty Image). The bootloader loads the kernel from the boot partition.
`TARGET_PREBUILT_KERNEL := /dev/null` reproduces this exactly.

## Build

```shell
lunch twrp_TB331FC-eng
mka recoveryimage
```

CI: `.github/workflows/build.yml` uses the twrp-12.1 minimal manifest and
downloads the GKI kernel from `yxyyds666/TB331FC-Kernel`.

## Flash

The device has a dedicated recovery partition (A/B):

```shell
fastboot flash recovery_a recovery.img
fastboot flash recovery_b recovery.img
```

## Resources

- Stock images: `dtbo_a.img`, `init_boot_a.img`, `recovery_a.img` (device dump)
- Kernel: `yxyyds666/TB331FC-Kernel` (GKI 5.15, stock KMI compatible)
- Reference: `spes-515-devs/device_xiaomi_spes-twrp-5.15` (same platform)
- Reference: `polygraphene/android_device_lenovo_TB321FU` (Lenovo tablet TWRP)
