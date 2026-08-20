#ifndef ASD_PROFILE_NVS_H
#define ASD_PROFILE_NVS_H

#include "esp_err.h"

#include "asd_profile_store.h"

#define ASD_PROFILE_NVS_NAMESPACE "asd"
#define ASD_PROFILE_NVS_KEY "profile_v1"

esp_err_t asd_profile_nvs_init(void);
esp_err_t asd_profile_nvs_load(
    const uint8_t expected_fingerprint[ASD_PROFILE_MODEL_FINGERPRINT_SIZE],
    asd_profile_runtime_t *profile,
    asd_profile_store_metadata_t *metadata,
    uint32_t *blob_crc32,
    int *loaded);
esp_err_t asd_profile_nvs_save(
    const asd_profile_runtime_t *profile,
    const asd_profile_store_metadata_t *metadata,
    const uint8_t model_fingerprint[ASD_PROFILE_MODEL_FINGERPRINT_SIZE],
    uint32_t *blob_crc32);

#endif
