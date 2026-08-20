/* Host-testable K1 acceptance gate for normal-only calibration.
 *
 * This module owns the firmware copy of the versioned commissioning contract.
 * It has no ESP-IDF, audio or PSD dependencies, so host tests can exercise the
 * exact binary32 comparisons used on the device.
 */
#ifndef ASD_CALIBRATION_QUALITY_H
#define ASD_CALIBRATION_QUALITY_H

#ifdef __cplusplus
extern "C" {
#endif

#define ASD_COMMISSIONING_POLICY_PROTOCOL "asd-commissioning-policy-v1.0.0"
#define ASD_CALIBRATION_MAX_LOO_CV 0.6f
#define ASD_CALIBRATION_LOO_CV_SCALE 1000000.0

typedef struct {
    float max_loo_cv;
} asd_calibration_quality_policy_t;

typedef struct {
    float loo_mean;
    float loo_sd;
    float loo_cv;
    float loo_range;
} asd_calibration_quality_metrics_t;

typedef enum {
    ASD_CALIBRATION_QUALITY_ACCEPTED = 0,
    ASD_CALIBRATION_QUALITY_INVALID_ARGUMENT,
    ASD_CALIBRATION_QUALITY_NONFINITE,
    ASD_CALIBRATION_QUALITY_NEGATIVE_METRIC,
    ASD_CALIBRATION_QUALITY_UNSTABLE
} asd_calibration_quality_reason_t;

asd_calibration_quality_policy_t asd_calibration_quality_default_policy(void);

/* Equality is accepted. A finite loo_cv strictly above max_loo_cv returns
 * ASD_CALIBRATION_QUALITY_UNSTABLE and the public UART reason token
 * UNSTABLE_CALIBRATION. */
asd_calibration_quality_reason_t asd_calibration_quality_evaluate(
    const asd_calibration_quality_metrics_t *metrics,
    const asd_calibration_quality_policy_t *policy);

const char *asd_calibration_quality_reason_name(
    asd_calibration_quality_reason_t reason);
const char *asd_calibration_quality_policy_protocol(void);

#ifdef __cplusplus
}
#endif

#endif
