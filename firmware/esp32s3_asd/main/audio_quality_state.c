#include "audio_quality_state.h"

#include <limits.h>
#include <math.h>
#include <string.h>

/* These are engineering/sensor-health gates, not anomaly-model parameters.
 * LEVEL_FLOOR and CLIP_LEVEL preserve the previously documented firmware
 * values.  Fraction limits are preregistered in pc/config/
 * asd_quality_policy_v1.json and must not be tuned on target anomalies. */
#define DEFAULT_LEVEL_FLOOR_DBFS  (-60.0f)
#define DEFAULT_CLIP_LEVEL        32000
#define DEFAULT_MAX_CLIP_FRAC     0.001f
#define DEFAULT_MAX_ZERO_FRAC     0.999f
#define DEFAULT_MAX_STUCK_FRAC    0.999f

asd_quality_policy_t asd_quality_default_policy(void) {
    asd_quality_policy_t policy = {
        .level_floor_dbfs = DEFAULT_LEVEL_FLOOR_DBFS,
        .clip_level = DEFAULT_CLIP_LEVEL,
        .max_clip_fraction = DEFAULT_MAX_CLIP_FRAC,
        .max_zero_fraction = DEFAULT_MAX_ZERO_FRAC,
        .max_stuck_fraction = DEFAULT_MAX_STUCK_FRAC,
    };
    return policy;
}

void asd_quality_reset(asd_quality_accumulator_t *acc,
                       uint32_t expected_samples,
                       uint32_t dropped_before,
                       const asd_quality_policy_t *policy) {
    if (!acc) return;
    memset(acc, 0, sizeof(*acc));
    acc->expected_samples = expected_samples;
    acc->dropped_before = dropped_before;
    acc->clip_level = policy ? policy->clip_level : 0;
}

void asd_quality_add_pcm(asd_quality_accumulator_t *acc,
                         const int16_t *pcm,
                         size_t count) {
    if (!acc || (!pcm && count != 0)) return;
    for (size_t i = 0; i < count; i++) {
        int32_t sample = pcm[i];
        int32_t magnitude = sample < 0 ? -sample : sample;
        acc->sum += (double)sample;
        acc->sumsq += (double)sample * (double)sample;
        if (magnitude > acc->peak) acc->peak = magnitude;
        if (acc->clip_level > 0 && magnitude >= acc->clip_level)
            acc->clipped_count++;
        if (sample == 0) acc->zero_count++;
        if (acc->has_previous && sample == acc->previous) acc->stuck_count++;
        acc->previous = (int16_t)sample;
        acc->has_previous = 1;
        if (acc->sample_count != UINT32_MAX) acc->sample_count++;
    }
}

void asd_quality_finish(const asd_quality_accumulator_t *acc,
                        uint32_t dropped_after,
                        asd_quality_metrics_t *out) {
    if (!out) return;
    memset(out, 0, sizeof(*out));
    if (!acc) {
        out->rms_dbfs = NAN;
        return;
    }
    out->expected_samples = acc->expected_samples;
    out->sample_count = acc->sample_count;
    out->peak = acc->peak;
    out->clipped_count = acc->clipped_count;
    out->zero_count = acc->zero_count;
    out->stuck_count = acc->stuck_count;
    out->dropped_delta = dropped_after - acc->dropped_before;
    if (acc->sample_count == 0) {
        out->rms_dbfs = -INFINITY;
        return;
    }
    double n = (double)acc->sample_count;
    double dc = acc->sum / n;
    double variance = acc->sumsq / n - dc * dc;
    if (variance < 0.0 && variance > -1e-9) variance = 0.0;
    out->dc = (float)dc;
    out->rms = variance >= 0.0 ? (float)sqrt(variance) : NAN;
    out->rms_dbfs = out->rms > 0.0f
        ? 20.0f * log10f(out->rms / 32768.0f)
        : -INFINITY;
}

asd_quality_reason_t asd_quality_evaluate(const asd_quality_metrics_t *m,
                                          const asd_quality_policy_t *p) {
    if (!m || !p || m->expected_samples == 0 || p->clip_level <= 0 ||
        p->clip_level > 32768 ||
        !isfinite(p->level_floor_dbfs) || !isfinite(p->max_clip_fraction) ||
        !isfinite(p->max_zero_fraction) || !isfinite(p->max_stuck_fraction) ||
        p->max_clip_fraction < 0.0f || p->max_clip_fraction > 1.0f ||
        p->max_zero_fraction < 0.0f || p->max_zero_fraction > 1.0f ||
        p->max_stuck_fraction < 0.0f || p->max_stuck_fraction > 1.0f)
        return ASD_QUALITY_INVALID_ARGUMENT;
    if (m->sample_count != m->expected_samples)
        return ASD_QUALITY_SHORT_READ;
    if (m->dropped_delta > 0)
        return ASD_QUALITY_DROPPED_SAMPLES;

    float count = (float)m->sample_count;
    float zero_fraction = m->zero_count / count;
    float stuck_fraction = m->sample_count > 1
        ? m->stuck_count / (float)(m->sample_count - 1)
        : 1.0f;
    if (zero_fraction > p->max_zero_fraction ||
        stuck_fraction > p->max_stuck_fraction)
        return ASD_QUALITY_STUCK_SIGNAL;
    if (!isfinite(m->dc) || !isfinite(m->rms) || !isfinite(m->rms_dbfs))
        return ASD_QUALITY_NONFINITE;
    if (m->clipped_count / count > p->max_clip_fraction)
        return ASD_QUALITY_CLIPPING;
    if (m->rms_dbfs < p->level_floor_dbfs)
        return ASD_QUALITY_LOW_LEVEL_OBSERVATION;
    return ASD_QUALITY_OK;
}

int asd_quality_floats_finite(const float *values, size_t count) {
    if (!values && count != 0) return 0;
    for (size_t i = 0; i < count; i++)
        if (!isfinite(values[i])) return 0;
    return 1;
}

asd_flow_action_t asd_quality_flow_action(asd_quality_reason_t reason,
                                          asd_quality_phase_t phase) {
    if (reason == ASD_QUALITY_OK) return ASD_FLOW_CONTINUE;
    if (reason == ASD_QUALITY_LOW_LEVEL_OBSERVATION && phase == ASD_PHASE_WAIT)
        return ASD_FLOW_CONTINUE;
    return ASD_FLOW_STOP;
}

asd_state_t asd_quality_reject_state(asd_quality_reason_t reason,
                                     asd_quality_phase_t phase) {
    switch (reason) {
        case ASD_QUALITY_LOW_LEVEL_OBSERVATION:
        case ASD_QUALITY_INSUFFICIENT_LEVEL:
            return ASD_STATE_NO_MACHINE;
        case ASD_QUALITY_CLIPPING:
            return phase == ASD_PHASE_DET
                ? ASD_STATE_RECALIBRATION_REQUIRED
                : ASD_STATE_CALIBRATION_REJECTED;
        case ASD_QUALITY_SHORT_READ:
        case ASD_QUALITY_NONFINITE:
        case ASD_QUALITY_STUCK_SIGNAL:
        case ASD_QUALITY_DROPPED_SAMPLES:
        case ASD_QUALITY_INVALID_ARGUMENT:
        case ASD_QUALITY_AUDIO_TIMEOUT:
        case ASD_QUALITY_AUDIO_READ_ERROR:
        default:
            return ASD_STATE_SENSOR_ERROR;
    }
}

const char *asd_quality_reason_name(asd_quality_reason_t reason) {
    switch (reason) {
        case ASD_QUALITY_OK: return "OK";
        case ASD_QUALITY_SHORT_READ: return "SHORT_READ";
        case ASD_QUALITY_NONFINITE: return "NONFINITE";
        case ASD_QUALITY_STUCK_SIGNAL: return "STUCK_SIGNAL";
        case ASD_QUALITY_LOW_LEVEL_OBSERVATION: return "LOW_LEVEL_OBSERVATION";
        case ASD_QUALITY_INSUFFICIENT_LEVEL: return "INSUFFICIENT_LEVEL";
        case ASD_QUALITY_CLIPPING: return "CLIPPING";
        case ASD_QUALITY_DROPPED_SAMPLES: return "DROPPED_SAMPLES";
        case ASD_QUALITY_INVALID_ARGUMENT: return "INVALID_ARGUMENT";
        case ASD_QUALITY_AUDIO_TIMEOUT: return "AUDIO_TIMEOUT";
        case ASD_QUALITY_AUDIO_READ_ERROR: return "AUDIO_READ_ERROR";
        default: return "UNKNOWN_REASON";
    }
}

const char *asd_state_name(asd_state_t state) {
    switch (state) {
        case ASD_STATE_NO_MACHINE: return "NO_MACHINE";
        case ASD_STATE_CALIBRATION_REJECTED: return "CALIBRATION_REJECTED";
        case ASD_STATE_CALIBRATED_NORMAL: return "CALIBRATED_NORMAL";
        case ASD_STATE_ANOMALY: return "ANOMALY";
        case ASD_STATE_SENSOR_ERROR: return "SENSOR_ERROR";
        case ASD_STATE_RECALIBRATION_REQUIRED: return "RECALIBRATION_REQUIRED";
        case ASD_STATE_OBSERVATION_HOLD: return "OBSERVATION_HOLD";
        default: return "SENSOR_ERROR";
    }
}
