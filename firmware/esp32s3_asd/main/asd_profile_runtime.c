#include "asd_profile_runtime.h"

#include <math.h>
#include <string.h>

void asd_profile_runtime_clear(asd_profile_runtime_t *profile) {
    if (!profile) return;
    memset(profile, 0, sizeof(*profile));
}

static int finite_vector(const float *values, size_t count) {
    if (!values || count != ASD_PROFILE_DIM) return 0;
    for (size_t i = 0; i < count; i++)
        if (!isfinite(values[i])) return 0;
    return 1;
}

int asd_profile_runtime_set_center(asd_profile_runtime_t *profile,
                                   const float *center, size_t dimensions,
                                   float level_mean_dbfs,
                                   float tonalness_reference,
                                   uint32_t center_windows,
                                   uint32_t policy_version,
                                   uint32_t policy_id,
                                   int developmental) {
    if (!profile || profile->valid || profile->center_windows != 0u ||
        !finite_vector(center, dimensions) || !isfinite(level_mean_dbfs) ||
        !isfinite(tonalness_reference) || center_windows == 0u ||
        policy_version == 0u || policy_id == 0u)
        return 0;
    memcpy(profile->center, center, sizeof(profile->center));
    profile->level_mean_dbfs = level_mean_dbfs;
    profile->tonalness_reference = tonalness_reference;
    profile->center_windows = center_windows;
    profile->policy_version = policy_version;
    profile->policy_id = policy_id;
    profile->developmental = developmental ? 1 : 0;
    return 1;
}

int asd_profile_runtime_freeze_thresholds(asd_profile_runtime_t *profile,
                                          float threshold_enter,
                                          float threshold_exit,
                                          uint32_t derive_windows) {
    if (!profile || profile->valid || profile->center_windows == 0u ||
        profile->derive_windows != 0u || derive_windows == 0u ||
        !isfinite(threshold_enter) || !isfinite(threshold_exit) ||
        !(threshold_exit > 0.0f && threshold_exit < threshold_enter))
        return 0;
    profile->threshold_enter = threshold_enter;
    profile->threshold_exit = threshold_exit;
    profile->derive_windows = derive_windows;
    return 1;
}

int asd_profile_runtime_validate(const asd_profile_runtime_t *profile,
                                 int require_finalized) {
    if (!profile || profile->center_windows == 0u ||
        profile->derive_windows == 0u || profile->policy_version == 0u ||
        profile->policy_id == 0u || !isfinite(profile->level_mean_dbfs) ||
        !isfinite(profile->tonalness_reference) ||
        !finite_vector(profile->center, ASD_PROFILE_DIM) ||
        !isfinite(profile->threshold_enter) ||
        !isfinite(profile->threshold_exit) ||
        !(profile->threshold_exit > 0.0f &&
          profile->threshold_exit < profile->threshold_enter))
        return 0;
    if (require_finalized && (!profile->valid || profile->verify_windows == 0u))
        return 0;
    return 1;
}

int asd_profile_runtime_finalize(asd_profile_runtime_t *profile,
                                 uint32_t verify_windows) {
    if (!profile || profile->valid || verify_windows == 0u ||
        !asd_profile_runtime_validate(profile, 0))
        return 0;
    profile->verify_windows = verify_windows;
    profile->valid = 1;
    return 1;
}
