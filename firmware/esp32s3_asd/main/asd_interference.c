#include "asd_interference.h"

#include <math.h>
#include <string.h>

asd_interference_policy_t asd_interference_default_policy(void) {
    /* Granice su izvedene 23.08.2026 iz 18 normal-only prozora jednog runa
     * (10 CAL + 8 DET pod uslovima `normal_baseline`/`final_recovery`), pravilom
     * `max(normal) * 1,25`. Nijedan papiric, govor ni vrata nisu otvoreni u
     * izvodjenju -- vidi `pc/tools/derive_interference_policy.py` i
     * `pc/config/asd_interference_policy_v2.json`.
     *
     * Nezavisan readout POSLIJE zamrzavanja, medijana nestabilnosti po uslovu:
     * normalno 0,85 - papiric 0,94/1,06/1,09 - govor 1,89 - vrata 1,89.
     * Granica 1,40 je pala izmedju papirica i smetnje, a nije birana da padne. */
    asd_interference_policy_t policy = {
        .enabled = 1,
        .developmental = 1,
        .use_tonalness_delta = 0,
        .max_abs_tonalness_delta = 0.547454f,
        .max_subsegment_instability = 1.400175f,
        .long_hold_windows = 6u,
    };
    return policy;
}

static int policy_valid(const asd_interference_policy_t *policy) {
    if (!policy || policy->long_hold_windows == 0u) return 0;
    if (!policy->enabled) return 1;
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
