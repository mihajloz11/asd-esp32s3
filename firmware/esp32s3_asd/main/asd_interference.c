#include "asd_interference.h"

#include <math.h>
#include <string.h>

asd_interference_policy_t asd_interference_default_policy(void) {
    /* V2 je prenosila apsolutnu granicu iz jednog polozaja mikrofona, pa je u
     * drugom mjerila postavku umjesto pouzdanosti. V3 zadrzava pravilo
     * max(CAL normal) * 1,25, ali granicu izvodi u svakoj sesiji. */
    asd_interference_policy_t policy = {
        .enabled = 1,
        .developmental = 1,
        .use_tonalness_delta = 0,
        .max_abs_tonalness_delta = 0.547454f,
        .normal_max_multiplier = 1.250000f,
        .calibration_min_windows = 10u,
        .max_subsegment_instability = 0.0f,
        .long_hold_windows = 6u,
    };
    return policy;
}

int asd_interference_calibrate_normal(
    asd_interference_policy_t *policy,
    float normal_max_subsegment_instability,
    uint32_t normal_windows) {
    if (!policy || !policy->enabled ||
        normal_windows < policy->calibration_min_windows ||
        !isfinite(normal_max_subsegment_instability) ||
        !(normal_max_subsegment_instability > 0.0f) ||
        !isfinite(policy->normal_max_multiplier) ||
        !(policy->normal_max_multiplier > 1.0f))
        return 0;
    float threshold = normal_max_subsegment_instability *
        policy->normal_max_multiplier;
    if (!isfinite(threshold) || !(threshold > normal_max_subsegment_instability))
        return 0;
    policy->max_subsegment_instability = threshold;
    return 1;
}

static int policy_valid(const asd_interference_policy_t *policy) {
    if (!policy || policy->long_hold_windows == 0u) return 0;
    if (!policy->enabled) return 1;
    if (
        policy->calibration_min_windows == 0u ||
        !isfinite(policy->normal_max_multiplier) ||
        !(policy->normal_max_multiplier > 1.0f)) return 0;
    /* Ukljucena politika mora imati bar jedan kriterijum, inace bi tiho
     * propustala sve i izgledala kao da radi. */
    if (!policy->use_tonalness_delta &&
        !(policy->max_subsegment_instability > 0.0f)) return 0;
    return isfinite(policy->max_abs_tonalness_delta) &&
           policy->max_abs_tonalness_delta >= 0.0f &&
           isfinite(policy->max_subsegment_instability) &&
           policy->max_subsegment_instability >= 0.0f;
}

void asd_interference_init(asd_interference_t *gate,
                           const asd_interference_policy_t *policy) {
    if (!gate) return;
    memset(gate, 0, sizeof(*gate));
    gate->policy = policy ? *policy : asd_interference_default_policy();
}

void asd_interference_reset(asd_interference_t *gate) {
    if (!gate) return;
    gate->hold_windows = 0u;
    gate->hold_active = 0;
    gate->warning_emitted = 0;
}

asd_interference_result_t asd_interference_update(
    asd_interference_t *gate,
    const asd_interference_observation_t *obs) {
    if (!gate || !obs || !policy_valid(&gate->policy) ||
        !isfinite(obs->tonalness_delta) ||
        !isfinite(obs->subsegment_instability) ||
        obs->subsegment_instability < 0.0f)
        return ASD_INTERFERENCE_INVALID;
    if (!gate->policy.enabled || !obs->score_high) {
        asd_interference_reset(gate);
        return ASD_INTERFERENCE_PASS;
    }
    int unreliable =
        (gate->policy.use_tonalness_delta &&
         fabsf(obs->tonalness_delta) > gate->policy.max_abs_tonalness_delta) ||
        obs->subsegment_instability > gate->policy.max_subsegment_instability;
    if (!unreliable) {
        /* The next stable high window starts a fresh temporal run. */
        asd_interference_reset(gate);
        return ASD_INTERFERENCE_PASS;
    }
    gate->hold_active = 1;
    gate->hold_windows++;
    if (gate->hold_windows >= gate->policy.long_hold_windows) {
        gate->warning_emitted = 1;
        return ASD_INTERFERENCE_HOLD_WARNING;
    }
    return ASD_INTERFERENCE_HOLD;
}

const char *asd_interference_result_name(asd_interference_result_t result) {
    switch (result) {
        case ASD_INTERFERENCE_PASS: return "PASS";
        case ASD_INTERFERENCE_HOLD: return "OBSERVATION_HOLD";
        case ASD_INTERFERENCE_HOLD_WARNING: return "OBSERVATION_HOLD_WARNING";
        case ASD_INTERFERENCE_INVALID: return "INVALID_OBSERVATION";
        default: return "UNKNOWN_INTERFERENCE_RESULT";
    }
}
