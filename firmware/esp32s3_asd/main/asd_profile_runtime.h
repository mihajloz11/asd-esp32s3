/* Runtime-only calibrated fan profile.  No ESP-IDF/NVS dependency. */
#ifndef ASD_PROFILE_RUNTIME_H
#define ASD_PROFILE_RUNTIME_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ASD_PROFILE_DIM 96
#define ASD_PROFILE_SCHEMA "asd-runtime-profile-v1.0.0-development"

typedef struct {
    int valid;
    int developmental;
    float center[ASD_PROFILE_DIM];
    float level_mean_dbfs;
    float tonalness_reference;
    float threshold_enter;
    float threshold_exit;
    uint32_t center_windows;
    uint32_t derive_windows;
    uint32_t verify_windows;
    uint32_t policy_version;
    uint32_t policy_id;
} asd_profile_runtime_t;

void asd_profile_runtime_clear(asd_profile_runtime_t *profile);

/* Center can be committed once.  Thresholds remain unset and valid remains 0. */
int asd_profile_runtime_set_center(asd_profile_runtime_t *profile,
                                   const float *center, size_t dimensions,
                                   float level_mean_dbfs,
                                   float tonalness_reference,
                                   uint32_t center_windows,
                                   uint32_t policy_version,
                                   uint32_t policy_id,
                                   int developmental);

/* Absolute instance thresholds; no ratio or hidden exit scale is accepted. */
int asd_profile_runtime_freeze_thresholds(asd_profile_runtime_t *profile,
                                          float threshold_enter,
                                          float threshold_exit,
                                          uint32_t derive_windows);

/* The profile becomes valid only after a non-empty, successful VERIFY block. */
int asd_profile_runtime_finalize(asd_profile_runtime_t *profile,
                                 uint32_t verify_windows);

int asd_profile_runtime_validate(const asd_profile_runtime_t *profile,
                                 int require_finalized);

#ifdef __cplusplus
}
#endif

#endif
