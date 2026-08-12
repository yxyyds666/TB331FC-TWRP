# TB331FC-TWRP

TWRP Recovery for **Lenovo Xiaoxin Pad 2024 (TB331FC)** — Qualcomm SM6225-AD (bengal/khaje), Snapdragon 685, Adreno 610.

[![Build](https://github.com/yxyyds666/TB331FC-TWRP/actions/workflows/build.yml/badge.svg)](https://github.com/yxyyds666/TB331FC-TWRP/actions/workflows/build.yml)

## About

A TWRP device tree fused from two proven sources:

- **Stock recovery** (dumped from the device): authoritative partition layout, init scripts, QTI boot/health HAL binaries
- **[spes-515-devs twrp-12.1](https://github.com/spes-515-devs/device_xiaomi_spes-twrp-5.15)**: Redmi Note 11 is the same platform (SM6225 bengal + Adreno 610 + GKI 5.15), providing a verified `twrp-12.1` build framework

The `twrp-12.1` minimal manifest is self-consistent — vold 12.1 still ships the fscrypt/cryptfs APIs that Android 14 removed, so **no source patches are required**.

The device is GKI: stock `recovery_a.img` contains no kernel (empty Image). The bootloader loads the kernel from the boot partition; `TARGET_PREBUILT_KERNEL := /dev/null` reproduces this.

## Features

- Full FBE decryption (metadata wrapped key, QCOM FBE)
- Dynamic partitions (ext4, lenovo group)
- A/B slots, dedicated recovery partition
- FastbootD, MTP, NTFS-3G, repack tools
- Touch (Novatek NVT36523 SPI), display, charger kernel modules loaded in recovery

## Build

CI (`.github/workflows/build.yml`) builds automatically on push to `main`:

```shell
lunch twrp_TB331FC-eng
mka recoveryimage
```

## Flash

```shell
fastboot flash recovery_a recovery.img
fastboot flash recovery_b recovery.img
```

## Resources

- Kernel: [yxyyds666/TB331FC-Kernel](https://github.com/yxyyds666/TB331FC-Kernel) (GKI 5.15, stock KMI compatible)
- Stock images: `dtbo_a.img`, `init_boot_a.img`, `recovery_a.img` (device dump)
- More details: [`device/lenovo/TB331FC/README.md`](device/lenovo/TB331FC/README.md)
