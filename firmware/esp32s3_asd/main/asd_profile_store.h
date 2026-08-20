/* Pure, deterministic persisted-profile blob.  No ESP-IDF/NVS dependency. */
#ifndef ASD_PROFILE_STORE_H
#define ASD_PROFILE_STORE_H

#include <stddef.h>
#include <stdint.h>

#include "asd_profile_runtime.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ASD_PROFILE_STORE_SCHEMA "asd-profile-v1.0.0"
#define ASD_PROFILE_STORE_MAGIC 0x41534450u /* ASCII "ASDP" */
#define ASD_PROFILE_STORE_SCHEMA_VERSION 1u
#define ASD_PROFILE_MODEL_FINGERPRINT_SIZE 32u

typedef struct {
    uint32_t generation;
    float derive_mean;
    float derive_sd;
    float verify_alarm_time_percent;
    uint32_t verify_alarm_windows;
    uint32_t verify_episodes;
    uint32_t verify_chatter;
    uint32_t quality_policy_id;
    uint32_t commissioning_policy_id;
    uint32_t temporal_policy_id;
    uint32_t interference_policy_id;
} asd_profile_store_metadata_t;

typedef struct {
    uint32_t magic;
    uint16_t schema_version;
    uint16_t flags;
    uint32_t struct_size;
    uint8_t model_fingerprint[ASD_PROFILE_MODEL_FINGERPRINT_SIZE];
    uint32_t generation;
    float center[ASD_PROFILE_DIM];
    float level_mean_dbfs;
    float tonalness_reference;
    float threshold_enter;
    float threshold_exit;
    uint32_t center_windows;
    uint32_t derive_windows;
    uint32_t verify_windows;
    uint32_t profile_policy_version;
    uint32_t profile_policy_id;
    float derive_mean;
    float derive_sd;
    float verify_alarm_time_percent;
    uint32_t verify_alarm_windows;
    uint32_t verify_episodes;
    uint32_t verify_chatter;
    uint32_t quality_policy_id;
    uint32_t commissioning_policy_id;
    uint32_t temporal_policy_id;
    uint32_t interference_policy_id;
    uint32_t crc32;
} asd_profile_blob_v1_t;

uint32_t asd_profile_store_crc32(const void *data, size_t size);

int asd_profile_store_encode(
    asd_profile_blob_v1_t *blob,
    const asd_profile_runtime_t *profile,
    const asd_profile_store_metadata_t *metadata,
    const uint8_t model_fingerprint[ASD_PROFILE_MODEL_FINGERPRINT_SIZE]);

int asd_profile_store_decode(
    const void *blob_data, size_t blob_size,
    const uint8_t expected_fingerprint[ASD_PROFILE_MODEL_FINGERPRINT_SIZE],
    asd_profile_runtime_t *profile,
    asd_profile_store_metadata_t *metadata);

#ifdef __cplusplus
}
#endif

#endif
