#include "asd_profile_nvs.h"

#include "nvs.h"
#include "nvs_flash.h"

#include "asd_commissioning.h"
#include "asd_interference.h"
#include "asd_temporal.h"
#include "audio_quality_state.h"

esp_err_t asd_profile_nvs_init(void) {
    /* Fail closed.  This module never erases an NVS partition and never opens
     * a namespace other than the ASD-owned namespace below. */
    return nvs_flash_init();
}

static void discard_invalid_profile(void) {
    nvs_handle_t handle;
    if (nvs_open(ASD_PROFILE_NVS_NAMESPACE, NVS_READWRITE, &handle) != ESP_OK)
        return;
    if (nvs_erase_key(handle, ASD_PROFILE_NVS_KEY) == ESP_OK)
        (void)nvs_commit(handle);
    nvs_close(handle);
}

esp_err_t asd_profile_nvs_load(
    const uint8_t expected_fingerprint[ASD_PROFILE_MODEL_FINGERPRINT_SIZE],
    asd_profile_runtime_t *profile,
    asd_profile_store_metadata_t *metadata,
    uint32_t *blob_crc32,
    int *loaded) {
    if (!expected_fingerprint || !profile || !metadata || !blob_crc32 || !loaded)
        return ESP_ERR_INVALID_ARG;
    *loaded = 0;
    *blob_crc32 = 0u;
    nvs_handle_t handle;
    esp_err_t error = nvs_open(
        ASD_PROFILE_NVS_NAMESPACE, NVS_READONLY, &handle);
    if (error == ESP_ERR_NVS_NOT_FOUND) return ESP_OK;
    if (error != ESP_OK) return error;
    size_t size = 0;
    error = nvs_get_blob(handle, ASD_PROFILE_NVS_KEY, NULL, &size);
    if (error == ESP_ERR_NVS_NOT_FOUND) {
        nvs_close(handle);
        return ESP_OK;
    }
    if (error != ESP_OK) {
        nvs_close(handle);
        return error;
    }
    if (size != sizeof(asd_profile_blob_v1_t)) {
        nvs_close(handle);
        discard_invalid_profile();
        return ESP_OK;
    }
    asd_profile_blob_v1_t blob;
    error = nvs_get_blob(handle, ASD_PROFILE_NVS_KEY, &blob, &size);
    nvs_close(handle);
    if (error != ESP_OK) return error;
    if (!asd_profile_store_decode(&blob, size, expected_fingerprint,
                                  profile, metadata)) {
        discard_invalid_profile();
        return ESP_OK;
    }
    if (metadata->quality_policy_id != ASD_QUALITY_POLICY_ID ||
        metadata->commissioning_policy_id != ASD_COMMISSIONING_POLICY_ID ||
        metadata->temporal_policy_id != ASD_TEMPORAL_POLICY_ID ||
        metadata->interference_policy_id != ASD_INTERFERENCE_POLICY_ID) {
        discard_invalid_profile();
        return ESP_OK;
    }
    *blob_crc32 = blob.crc32;
    *loaded = 1;
    return ESP_OK;
}

esp_err_t asd_profile_nvs_save(
    const asd_profile_runtime_t *profile,
    const asd_profile_store_metadata_t *metadata,
    const uint8_t model_fingerprint[ASD_PROFILE_MODEL_FINGERPRINT_SIZE],
    uint32_t *blob_crc32) {
    if (blob_crc32) *blob_crc32 = 0u;
    asd_profile_blob_v1_t blob;
    if (!asd_profile_store_encode(&blob, profile, metadata, model_fingerprint))
        return ESP_ERR_INVALID_ARG;
    nvs_handle_t handle;
    esp_err_t error = nvs_open(
        ASD_PROFILE_NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (error != ESP_OK) return error;
    error = nvs_set_blob(handle, ASD_PROFILE_NVS_KEY, &blob, sizeof(blob));
    if (error == ESP_OK) error = nvs_commit(handle);
    nvs_close(handle);
    if (error == ESP_OK && blob_crc32) *blob_crc32 = blob.crc32;
    return error;
}
