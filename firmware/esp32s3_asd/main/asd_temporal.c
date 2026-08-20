/* Vidi asd_temporal.h. */
#include "asd_temporal.h"

#include <math.h>
#include <string.h>

/* Izabrano pravilo: `hysteresis_1.0_0.7_n3`.
 *
 * Izvedeno samo iz normalnih podataka, 40 splitova, 2000 prozora
 * (pc/config/asd_temporal_policy_v1.json, `target_anomalies_used=false`).
 * EWMA i CUSUM su ostavljeni u strukturi politike jer su mjereni i odbačeni —
 * da se ne „otkriju" ponovo kao nova ideja — ali su isključeni nulom. */
#define DEFAULT_MIN_CONSECUTIVE 3
#define DEFAULT_EWMA_ALPHA      0.0f
#define DEFAULT_ENTER_SCALE     1.0f
#define DEFAULT_EXIT_SCALE      0.7f
#define DEFAULT_CUSUM_K         0.0f
#define DEFAULT_CUSUM_H         0.0f
#define DEFAULT_FAST_SCALE      0.0f

asd_temporal_policy_t asd_temporal_default_policy(void) {
    asd_temporal_policy_t policy = {
        .min_consecutive = DEFAULT_MIN_CONSECUTIVE,
        .ewma_alpha = DEFAULT_EWMA_ALPHA,
        .enter_scale = DEFAULT_ENTER_SCALE,
        .exit_scale = DEFAULT_EXIT_SCALE,
        .cusum_k = DEFAULT_CUSUM_K,
        .cusum_h = DEFAULT_CUSUM_H,
        .fast_scale = DEFAULT_FAST_SCALE,
    };
    return policy;
}

void asd_temporal_init(asd_temporal_t *det, const asd_temporal_policy_t *policy) {
    if (!det) return;
    memset(det, 0, sizeof(*det));
    det->policy = policy ? *policy : asd_temporal_default_policy();
    if (det->policy.min_consecutive < 1) det->policy.min_consecutive = 1;
}

void asd_temporal_reset(asd_temporal_t *det) {
    if (!det) return;
    det->ewma = 0.0f;
    det->ewma_valid = 0;
    det->run = 0;
    det->cusum = 0.0f;
    det->active = 0;
}

void asd_temporal_suspend(asd_temporal_t *det) {
    if (!det) return;
    det->run = 0;
    det->cusum = 0.0f;
    /* `active` i EWMA ostaju: alarm koji traje nije poništen time što viši
     * nivo hijerarhije preuzima odluku. */
}

int asd_temporal_update(asd_temporal_t *det, float score,
                        float threshold_enter, float threshold_exit) {
    if (!det) return 0;
    /* Fail-closed: bez konačnog score-a i pozitivnog praga odluka se ne donosi,
     * a tekuće stanje se ne zadržava — pozivalac (asd_events.c) je već odbio
     * nekonačne vrijednosti na nivou zdravlja senzora. */
    if (!isfinite(score) || !isfinite(threshold_enter) ||
        !isfinite(threshold_exit) ||
        !(threshold_exit > 0.0f && threshold_exit < threshold_enter)) {
        asd_temporal_reset(det);
        return 0;
    }

    float statistic = score;
    if (det->policy.ewma_alpha > 0.0f) {
        det->ewma = det->ewma_valid
            ? det->policy.ewma_alpha * score +
              (1.0f - det->policy.ewma_alpha) * det->ewma
            : score;
        det->ewma_valid = 1;
        statistic = det->ewma;
    }
    if (det->policy.cusum_h > 0.0f) {
        float step = (score / threshold_enter - 1.0f) - det->policy.cusum_k;
        det->cusum = det->cusum + step;
        if (det->cusum < 0.0f) det->cusum = 0.0f;
    }

    if (det->active) {
        /* Histereza: iz alarma se izlazi tek ispod NIŽEG praga. Bez toga
         * score koji visi oko praga pali i gasi alarm iz prozora u prozor. */
        if (statistic <= threshold_exit) {
            det->active = 0;
            det->run = 0;
            det->cusum = 0.0f;
        }
    } else {
        /* Strogo veće, isto kao ranije u psd_live.c: score tačno na pragu je
         * normalan. */
        det->run = statistic > threshold_enter ? det->run + 1 : 0;
        int fired = det->run >= det->policy.min_consecutive;
        if (det->policy.cusum_h > 0.0f && det->cusum > det->policy.cusum_h)
            fired = 1;
        if (det->policy.fast_scale > 0.0f &&
            score > threshold_enter * det->policy.fast_scale)
            fired = 1;
        if (fired) det->active = 1;
    }
    return det->active;
}
