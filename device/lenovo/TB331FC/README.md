# TWRP device tree for Lenovo TB331FC

TWRP recovery for the Lenovo Xiaoxin Pad 2024 (TB331FC), Qualcomm SM6225-AD (khaje).

## Device specifications

| Property       | Value                                |
| -------------- | ------------------------------------ |
| SoC            | Qualcomm SM6225-AD (Snapdragon 685)  |
| Board          | khaje                                |
| CPU            | Octa-core (4x2.8 GHz Cortex-A73 & 4x1.9 GHz Cortex-A53) |
| GPU            | Adreno 610                           |
| Android        | 13 (TKQ1.230227.001), ZUI 15.1.045   |
| Touch          | Novatek NVT36523 (SPI)               |
| Boot header    | v4 (GKI, no dtb in boot)             |

## Build

Uses twrp-14 minimal manifest with `TeamWin/android_bootable_recovery` (android-14)
replacing AOSP `bootable/recovery`.

```shell
lunch twrp_TB331FC-eng
mka recoveryimage
```

## Flash

The device has a dedicated recovery partition:

```shell
fastboot flash recovery_a recovery.img
fastboot flash recovery_b recovery.img
```
