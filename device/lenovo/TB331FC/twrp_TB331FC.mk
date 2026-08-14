#
# Copyright (C) 2024 The Android Open Source Project
# SPDX-License-Identifier: Apache-2.0
#

# Inherit from these configurations (aligned with working TB321FU: no
# core_64_bit_only/base.mk which reset PLATFORM_VERSION to 12)
# Inherit from device configuration
$(call inherit-product, device/lenovo/TB331FC/device.mk)

# Same arch flags as core_64_bit_only.mk, set explicitly so PLATFORM_VERSION
# is not reset by inheriting that product
TARGET_SUPPORTS_32_BIT_APPS := false
TARGET_SUPPORTS_64_BIT_APPS := true

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
