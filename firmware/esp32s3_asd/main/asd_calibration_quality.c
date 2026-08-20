#include "asd_calibration_quality.h"

#include <math.h>

asd_calibration_quality_policy_t asd_calibration_quality_default_policy(void) {
    asd_calibration_quality_policy_t policy = {
        .max_loo_cv = ASD_CALIBRATION_MAX_LOO_CV,
    };
    return policy;
}

asd_calibration_quality_reason_t asd_calibration_quality_evaluate(
    const asd_calibration_quality_metrics_t *metrics,
    const asd_calibration_quality_policy_t *policy) {
    if (!metrics || !policy || !isfinite(policy->max_loo_cv) ||
        policy->max_loo_cv < 0.0f)
        return ASD_CALIBRATION_QUALITY_INVALID_ARGUMENT;

    if (!isfinite(metrics->loo_mean) || !isfinite(metrics->loo_sd) ||
        !isfinite(metrics->loo_cv) || !isfinite(metrics->loo_range))
        return ASD_CALIBRATION_QUALITY_NONFINITE;

    if (metrics->loo_mean < 0.0f || metrics->loo_sd < 0.0f ||
        metrics->loo_cv < 0.0f || metrics->loo_range < 0.0f)
        return ASD_CALIBRATION_QUALITY_NEGATIVE_METRIC;

    /* CAL_SUMMARY serializes loo_cv with six decimals. Decide on that same
     * audit value so a binary32 value one ULP above 0.6 cannot be rejected by
     * firmware while the host receives `0.600000` and accepts it. */
    double wire_loo_cv = round((double)metrics->loo_cv *
                               ASD_CALIBRATION_LOO_CV_SCALE) /
                         ASD_CALIBRATION_LOO_CV_SCALE;
    if (wire_loo_cv > (double)policy->max_loo_cv)
        return ASD_CALIBRATION_QUALITY_UNSTABLE;
    return ASD_CALIBRATION_QUALITY_ACCEPTED;
}

const char *asd_calibration_quality_reason_name(
    asd_calibration_quality_reason_t reason) {
    switch (reason) {
        case ASD_CALIBRATION_QUALITY_ACCEPTED: return "ACCEPTED";
        case ASD_CALIBRATION_QUALITY_INVALID_ARGUMENT: return "INVALID_ARGUMENT";
        case ASD_CALIBRATION_QUALITY_NONFINITE: return "NONFINITE";
        case ASD_CALIBRATION_QUALITY_NEGATIVE_METRIC: return "INVALID_ARGUMENT";
        case ASD_CALIBRATION_QUALITY_UNSTABLE: return "UNSTABLE_CALIBRATION";
        default: return "INVALID_ARGUMENT";
    }
}

const char *asd_calibration_quality_policy_protocol(void) {
    return ASD_COMMISSIONING_POLICY_PROTOCOL;
}
