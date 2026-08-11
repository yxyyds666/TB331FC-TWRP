#
# Copyright (C) 2024 The Android Open Source Project
#
# SPDX-License-Identifier: Apache-2.0
#

# Inherit from these configurations
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/base.mk)

# Inherit from device configuration
$(call inherit-product, device/lenovo/TB331FC/device.mk)

# Inherit from TWRP common configuration
$(call inherit-product, vendor/twrp/config/common.mk)

## Device identifier
PRODUCT_DEVICE := TB331FC
PRODUCT_NAME := twrp_TB331FC
PRODUCT_BRAND := Lenovo
PRODUCT_MODEL := Lenovo TB331FC
PRODUCT_MANUFACTURER := Lenovo

PRODUCT_GMS_CLIENTID_BASE := android-lenovo

PRODUCT_BUILD_PROP_OVERRIDES += \
    PRIVATE_BUILD_DESC="TB331FC_PRC-user 13 TKQ1.230227.001 ZUI_15.1.045_230928_PRC release-keys"

BUILD_FINGERPRINT := Lenovo/TB331FC_PRC/TB331FC:13/TKQ1.230227.001/ZUI_15.1.045_230928_PRC:user/release-keys
