/* Kvalitet zvuka i fail-closed odluke, bez ESP-IDF, I2S i PSD zavisnosti.
 * Firmware dovodi PCM blokove i brojac gubitaka, host testovi iste ulaze
 * kao fixture.
 */
#ifndef ASD_AUDIO_QUALITY_STATE_H
#define ASD_AUDIO_QUALITY_STATE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* v1.5.0: bounded audio consumer razlikuje timeout od I2S/ring greške. */
/* v1.6.0: DET red nosi `hold=`, a `OBSERVATION_HOLD` se pojavljuje kao
 * stanje na zici. Do v1.5.0 je kapija pouzdanosti bila iskljucena, pa taj put
 * nijedan host nikad nije vidio. */
#define ASD_QUALITY_PROTOCOL "asd-quality-v1.6.0"
#define ASD_QUALITY_POLICY_ID 0x51555632u

typedef enum {
    ASD_QUALITY_OK = 0,
    ASD_QUALITY_SHORT_READ,
    ASD_QUALITY_NONFINITE,
    ASD_QUALITY_STUCK_SIGNAL,
    ASD_QUALITY_LOW_LEVEL_OBSERVATION,
    ASD_QUALITY_INSUFFICIENT_LEVEL,
    ASD_QUALITY_CLIPPING,
    ASD_QUALITY_DROPPED_SAMPLES,
    ASD_QUALITY_INVALID_ARGUMENT,
    ASD_QUALITY_AUDIO_TIMEOUT,
    ASD_QUALITY_AUDIO_READ_ERROR
} asd_quality_reason_t;

typedef enum {
    ASD_STATE_NO_MACHINE = 0,
    ASD_STATE_CALIBRATION_REJECTED,
    ASD_STATE_CALIBRATED_NORMAL,
    ASD_STATE_ANOMALY,
    ASD_STATE_SENSOR_ERROR,
    ASD_STATE_RECALIBRATION_REQUIRED,
    ASD_STATE_OBSERVATION_HOLD
} asd_state_t;

typedef enum {
    ASD_PHASE_WAIT = 0,
    ASD_PHASE_CAL,
    ASD_PHASE_DET
} asd_quality_phase_t;

typedef enum {
    ASD_FLOW_CONTINUE = 0,
    ASD_FLOW_STOP
} asd_flow_action_t;

typedef struct {
    float level_floor_dbfs;
    int32_t clip_level;
    float max_clip_fraction;
    float max_zero_fraction;
    float max_stuck_fraction;
} asd_quality_policy_t;

typedef struct {
    uint32_t expected_samples;
    uint32_t sample_count;
    double sum;
    double sumsq;
    int32_t peak;
    uint32_t clipped_count;
    uint32_t zero_count;
    uint32_t stuck_count;
    int16_t previous;
    uint8_t has_previous;
    uint32_t dropped_before;
    int32_t clip_level;
} asd_quality_accumulator_t;

typedef struct {
    uint32_t expected_samples;
    uint32_t sample_count;
    float dc;
    float rms;
    float rms_dbfs;
    int32_t peak;
    uint32_t clipped_count;
    uint32_t zero_count;
    uint32_t stuck_count;
    uint32_t dropped_delta;
} asd_quality_metrics_t;

asd_quality_policy_t asd_quality_default_policy(void);
void asd_quality_reset(asd_quality_accumulator_t *acc,
                       uint32_t expected_samples,
                       uint32_t dropped_before,
                       const asd_quality_policy_t *policy);
void asd_quality_add_pcm(asd_quality_accumulator_t *acc,
                         const int16_t *pcm,
                         size_t count);
void asd_quality_finish(const asd_quality_accumulator_t *acc,
                        uint32_t dropped_after,
                        asd_quality_metrics_t *out);
asd_quality_reason_t asd_quality_evaluate(const asd_quality_metrics_t *metrics,
                                          const asd_quality_policy_t *policy);
int asd_quality_floats_finite(const float *values, size_t count);

/* OK continues every phase. LOW_LEVEL_OBSERVATION may continue only the WAIT
 * observation period and is never a reject; every actual reject is fail-closed.
 * CAL/DET continue only when this function returns ASD_FLOW_CONTINUE. */
asd_flow_action_t asd_quality_flow_action(asd_quality_reason_t reason,
                                          asd_quality_phase_t phase);
asd_state_t asd_quality_reject_state(asd_quality_reason_t reason,
                                     asd_quality_phase_t phase);

const char *asd_quality_reason_name(asd_quality_reason_t reason);
const char *asd_state_name(asd_state_t state);

#ifdef __cplusplus
}
#endif

#endif
