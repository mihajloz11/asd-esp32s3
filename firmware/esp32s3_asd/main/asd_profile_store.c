#include "asd_profile_store.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

uint32_t asd_profile_store_crc32(const void *data, size_t size) {
    if (!data && size != 0u) return 0u;
    const uint8_t *bytes = (const uint8_t *)data;
    uint32_t crc = 0xffffffffu;
    for (size_t index = 0; index < size; index++) {
        crc ^= bytes[index];
        for (unsigned bit = 0; bit < 8u; bit++)
            crc = (crc >> 1u) ^ (0xedb88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}

static int metadata_valid(const asd_profile_store_metadata_t *metadata) {
    return metadata && metadata->generation != 0u &&
        isfinite(metadata->derive_mean) && metadata->derive_mean >= 0.0f &&
        isfinite(metadata->derive_sd) && metadata->derive_sd >= 0.0f &&
        isfinite(metadata->verify_alarm_time_percent) &&
        metadata->verify_alarm_time_percent >= 0.0f &&
        metadata->verify_alarm_time_percent <= 100.0f &&
        metadata->quality_policy_id != 0u &&
        metadata->commissioning_policy_id != 0u &&
        metadata->temporal_policy_id != 0u &&
        metadata->interference_policy_id != 0u;
}

int asd_profile_store_encode(
    asd_profile_blob_v1_t *blob,
    const asd_profile_runtime_t *profile,
    const asd_profile_store_metadata_t *metadata,
    const uint8_t model_fingerprint[ASD_PROFILE_MODEL_FINGERPRINT_SIZE]) {
    if (!blob || !model_fingerprint ||
        !asd_profile_runtime_validate(profile, 1) || !metadata_valid(metadata))
        return 0;
    memset(blob, 0, sizeof(*blob));
    blob->magic = ASD_PROFILE_STORE_MAGIC;
    blob->schema_version = ASD_PROFILE_STORE_SCHEMA_VERSION;
    blob->flags = profile->developmental ? 1u : 0u;
    blob->struct_size = (uint32_t)sizeof(*blob);
    memcpy(blob->model_fingerprint, model_fingerprint,
           sizeof(blob->model_fingerprint));
    blob->generation = metadata->generation;
    memcpy(blob->center, profile->center, sizeof(blob->center));
    blob->level_mean_dbfs = profile->level_mean_dbfs;
    blob->tonalness_reference = profile->tonalness_reference;
    blob->threshold_enter = profile->threshold_enter;
    blob->threshold_exit = profile->threshold_exit;
    blob->center_windows = profile->center_windows;
    blob->derive_windows = profile->derive_windows;
    blob->verify_windows = profile->verify_windows;
    blob->profile_policy_version = profile->policy_version;
    blob->profile_policy_id = profile->policy_id;
    blob->derive_mean = metadata->derive_mean;
    blob->derive_sd = metadata->derive_sd;
    blob->verify_alarm_time_percent = metadata->verify_alarm_time_percent;
    blob->verify_alarm_windows = metadata->verify_alarm_windows;
    blob->verify_episodes = metadata->verify_episodes;
    blob->verify_chatter = metadata->verify_chatter;
    blob->quality_policy_id = metadata->quality_policy_id;
    blob->commissioning_policy_id = metadata->commissioning_policy_id;
    blob->temporal_policy_id = metadata->temporal_policy_id;
    blob->interference_policy_id = metadata->interference_policy_id;
    blob->crc32 = asd_profile_store_crc32(blob, offsetof(asd_profile_blob_v1_t, crc32));
    return 1;
}

int asd_profile_store_decode(
    const void *blob_data, size_t blob_size,
    const uint8_t expected_fingerprint[ASD_PROFILE_MODEL_FINGERPRINT_SIZE],
    asd_profile_runtime_t *profile,
    asd_profile_store_metadata_t *metadata) {
    if (!blob_data || !expected_fingerprint || !profile || !metadata ||
        blob_size != sizeof(asd_profile_blob_v1_t))
        return 0;
    /* NVS currently returns aligned storage, but the pure reader also accepts
     * byte buffers from tests/tools.  Copy before typed access to avoid an
     * unaligned struct dereference on stricter targets. */
    asd_profile_blob_v1_t aligned_blob;
    memcpy(&aligned_blob, blob_data, sizeof(aligned_blob));
    const asd_profile_blob_v1_t *blob = &aligned_blob;
    if (blob->magic != ASD_PROFILE_STORE_MAGIC ||
        blob->schema_version != ASD_PROFILE_STORE_SCHEMA_VERSION ||
        (blob->flags & ~1u) != 0u || blob->struct_size != sizeof(*blob) ||
        memcmp(blob->model_fingerprint, expected_fingerprint,
               ASD_PROFILE_MODEL_FINGERPRINT_SIZE) != 0 ||
        blob->crc32 != asd_profile_store_crc32(
            blob, offsetof(asd_profile_blob_v1_t, crc32)))
        return 0;

    asd_profile_runtime_t decoded;
    asd_profile_runtime_clear(&decoded);
    if (!asd_profile_runtime_set_center(
            &decoded, blob->center, ASD_PROFILE_DIM, blob->level_mean_dbfs,
            blob->tonalness_reference, blob->center_windows,
            blob->profile_policy_version, blob->profile_policy_id,
            (blob->flags & 1u) != 0u) ||
        !asd_profile_runtime_freeze_thresholds(
            &decoded, blob->threshold_enter, blob->threshold_exit,
            blob->derive_windows) ||
        !asd_profile_runtime_finalize(&decoded, blob->verify_windows))
        return 0;

    asd_profile_store_metadata_t decoded_metadata = {
        .generation = blob->generation,
        .derive_mean = blob->derive_mean,
        .derive_sd = blob->derive_sd,
        .verify_alarm_time_percent = blob->verify_alarm_time_percent,
        .verify_alarm_windows = blob->verify_alarm_windows,
        .verify_episodes = blob->verify_episodes,
        .verify_chatter = blob->verify_chatter,
        .quality_policy_id = blob->quality_policy_id,
        .commissioning_policy_id = blob->commissioning_policy_id,
        .temporal_policy_id = blob->temporal_policy_id,
        .interference_policy_id = blob->interference_policy_id,
    };
    if (!metadata_valid(&decoded_metadata)) return 0;
    *profile = decoded;
    *metadata = decoded_metadata;
    return 1;
}
