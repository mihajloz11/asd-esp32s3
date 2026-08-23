/* Vidi asd_events.h. */
#include "asd_events.h"

/* Alarm koji traje se broji ovdje, a ne u pozivaocu, da bi bio pokriven istim
 * host testovima kao i ostatak odluke. */

#include <math.h>
#include <string.h>

/* Izvedeno iz normalnih podataka: pc/tools/derive_presence_policy.py, zaključano
 * u pc/config/asd_presence_policy_v1.json (`target_anomalies_used=false`).
 *
 * 11 dB nije sigma račun. Nivo po klipu u DCASE-u je normalizovan (sd 0,02 dB
 * preko 60 target klipova), pa je artefakt skupa i ne ulazi u marginu. Ulazi
 * samo varijacija unutar klipa, i to po TROJKAMA prozora, jer se odluka donosi
 * po tri uzastopna prozora. Najgori normalan pad po trojki je −7,90 dB
 * (source kontrola, 7400 trojki), plus 3 dB rezerve → 11 dB. Čisti 6σ bi dao
 * 3,87 dB i lažno bi palio, jer raspodjela ima težak rep u oba smjera.
 *
 * OGRANIČENJE: izvedeno iz snimaka, ne iz fizičkog ventilatora. Ponoviti kad
 * ventilator bude dostupan. */
#define DEFAULT_ABSENT_MARGIN_DB  11.0f
#define DEFAULT_MIN_CONSECUTIVE   3

asd_presence_policy_t asd_presence_default_policy(void) {
    asd_presence_policy_t policy = {
        .absent_margin_db = DEFAULT_ABSENT_MARGIN_DB,
        .min_consecutive = DEFAULT_MIN_CONSECUTIVE,
    };
    return policy;
}

void asd_decision_init(asd_decision_ctx_t *ctx,
                       const asd_presence_policy_t *policy) {
    if (!ctx) return;
    memset(ctx, 0, sizeof(*ctx));
    ctx->state = ASD_STATE_NO_MACHINE;
    ctx->policy = policy ? *policy : asd_presence_default_policy();
    asd_temporal_init(&ctx->temporal, NULL);
    asd_interference_init(&ctx->interference, NULL);
}

void asd_decision_set_interference_policy(
    asd_decision_ctx_t *ctx, const asd_interference_policy_t *policy) {
    if (!ctx) return;
    asd_interference_init(&ctx->interference, policy);
}

asd_capability_t asd_event_capability(asd_event_t event) {
    switch (event) {
        /* Nivo signala naspram kalibrisane sredine je dovoljan dokaz da
         * kalibrisane mašine više nema. Ne tvrdi ZAŠTO je nema. */
        case ASD_EVENT_FAN_STOPPED:        return ASD_CAP_AVAILABLE;
        /* Faza 1 već razlikuje klase kvara senzora. */
        case ASD_EVENT_SENSOR_FAULT:       return ASD_CAP_AVAILABLE;
        /* Namjerno neinformativan, i zato uvijek dozvoljen. */
        case ASD_EVENT_UNKNOWN_CHANGE:     return ASD_CAP_AVAILABLE;
        case ASD_EVENT_NONE:               return ASD_CAP_AVAILABLE;
        /* Razlikovanje promjene režima od kvara traži f0 sa confidenceom;
         * `spd_1/2/3` iz imena fajla nije dostupan na uređaju. */
        case ASD_EVENT_SPEED_CHANGED:      return ASD_CAP_NEEDS_F0;
        /* Pripisati energiju okolini, a ne mašini, traži drugi kanal. */
        case ASD_EVENT_AMBIENT_NOISE:      return ASD_CAP_NEEDS_DUAL_CHANNEL;
        /* Mehanički kvar se smije tvrditi tek kad se promjena režima i buka
         * okoline mogu ISKLJUČITI, dakle poslije Faza 3, 5 i 6. */
        case ASD_EVENT_MECHANICAL_ANOMALY: return ASD_CAP_NEEDS_TRANSIENT;
        default:                           return ASD_CAP_NEEDS_TRANSIENT;
    }
}

int asd_event_is_emittable(asd_event_t event) {
    return asd_event_capability(event) == ASD_CAP_AVAILABLE;
}

int asd_state_is_terminal(asd_state_t state) {
    /* Iz ovih stanja se tok ne nastavlja: operater mora ponovo pokrenuti
     * kalibraciju. Tiho nastavljanje bi bilo `warn and continue`, a automatska
     * rekalibracija bi mogla naučiti kvar kao normalu (P10). */
    return state == ASD_STATE_CALIBRATION_REJECTED ||
           state == ASD_STATE_SENSOR_ERROR ||
           state == ASD_STATE_RECALIBRATION_REQUIRED;
}

int asd_transition_allowed(asd_state_t from, asd_state_t to) {
    if (from == to) {
        /* Ostajanje u istom stanju je uvijek dozvoljeno; prvi BOOT_FAIL_CLOSED
         * u NO_MACHINE se time pokriva, a ponavljanje ne mijenja ništa. */
        return 1;
    }
    if (asd_state_is_terminal(from)) {
        /* Nema izlaza iz terminalnog stanja. */
        return 0;
    }
    switch (from) {
        case ASD_STATE_NO_MACHINE:
            /* U CALIBRATED_NORMAL se ulazi samo kroz prihvaćenu kalibraciju.
             * ANOMALY je zabranjen: bez validne kalibracije nema od čega da
             * odstupa. */
            return to == ASD_STATE_CALIBRATED_NORMAL ||
                   to == ASD_STATE_CALIBRATION_REJECTED ||
                   to == ASD_STATE_SENSOR_ERROR ||
                   to == ASD_STATE_RECALIBRATION_REQUIRED;
        case ASD_STATE_CALIBRATED_NORMAL:
            return to == ASD_STATE_ANOMALY ||
                   to == ASD_STATE_OBSERVATION_HOLD ||
                   to == ASD_STATE_NO_MACHINE ||
                   to == ASD_STATE_SENSOR_ERROR ||
                   to == ASD_STATE_RECALIBRATION_REQUIRED;
        case ASD_STATE_ANOMALY:
            return to == ASD_STATE_CALIBRATED_NORMAL ||
                   to == ASD_STATE_NO_MACHINE ||
                   to == ASD_STATE_SENSOR_ERROR ||
                   to == ASD_STATE_RECALIBRATION_REQUIRED;
        case ASD_STATE_OBSERVATION_HOLD:
            return to == ASD_STATE_CALIBRATED_NORMAL ||
                   to == ASD_STATE_ANOMALY ||
                   to == ASD_STATE_NO_MACHINE ||
                   to == ASD_STATE_SENSOR_ERROR ||
                   to == ASD_STATE_RECALIBRATION_REQUIRED;
        default:
            return 0;
    }
}

/* Kvar senzora naspram odsustva mašine: prenizak nivo NIJE kvar senzora, nego
 * podatak o mašini, i rješava se na sljedećem nivou hijerarhije. */
static int reason_is_sensor_fault(asd_quality_reason_t reason) {
    switch (reason) {
        case ASD_QUALITY_SHORT_READ:
        case ASD_QUALITY_NONFINITE:
        case ASD_QUALITY_STUCK_SIGNAL:
        case ASD_QUALITY_CLIPPING:
        case ASD_QUALITY_DROPPED_SAMPLES:
        case ASD_QUALITY_INVALID_ARGUMENT:
        case ASD_QUALITY_AUDIO_TIMEOUT:
        case ASD_QUALITY_AUDIO_READ_ERROR:
            return 1;
        default:
            return 0;
    }
}

asd_event_t asd_event_for_quality_reject(asd_quality_reason_t reason) {
    if (reason == ASD_QUALITY_OK) return ASD_EVENT_NONE;
    if (reason_is_sensor_fault(reason)) return ASD_EVENT_SENSOR_FAULT;
    /* Ostaje samo LOW_LEVEL_OBSERVATION / INSUFFICIENT_LEVEL. Bez kalibracije
     * uređaj mašinu nikad nije ni čuo, pa `FAN_STOPPED` ovdje ne bi bila
     * konzervativna tvrdnja nego izmišljena. */
    return ASD_EVENT_NONE;
}

asd_decision_level_t asd_level_for_quality_reject(asd_quality_reason_t reason) {
    return reason_is_sensor_fault(reason) ? ASD_LEVEL_SENSOR_HEALTH
                                          : ASD_LEVEL_MACHINE_PRESENCE;
}

static asd_decision_t finish(asd_decision_ctx_t *ctx, asd_state_t previous,
                             asd_state_t next, asd_event_t event,
                             asd_decision_level_t level, int flow_stop) {
    asd_decision_t out;
    /* Tabela tranzicija je jedini autoritet. Ako bi odluka napravila nedozvoljen
     * prelaz, to je greška u ovom modulu, a fail-closed odgovor je SENSOR_ERROR
     * umjesto tihog prihvatanja. */
    if (!asd_transition_allowed(previous, next)) {
        next = ASD_STATE_SENSOR_ERROR;
        event = ASD_EVENT_SENSOR_FAULT;
        level = ASD_LEVEL_SENSOR_HEALTH;
        flow_stop = 1;
    }
    /* Rezervisan događaj se nikad ne emituje; degradira se u UNKNOWN_CHANGE. */
    if (!asd_event_is_emittable(event)) {
        event = ASD_EVENT_UNKNOWN_CHANGE;
    }
    ctx->state = next;
    out.state = next;
    out.event = event;
    out.level = level;
    out.flow_stop = flow_stop;
    out.state_changed = (next != previous);
    out.observation_hold = 0;
    out.hold_warning = 0;

    /* Trajanje alarma se mjeri centralno, da nijedna grana ne moze zaboraviti
     * da resetuje brojac kad se uredjaj vrati u normalu. */
    out.sustained_anomaly = 0;
    if (next == ASD_STATE_ANOMALY) {
        if (ctx->anomaly_windows < UINT32_MAX) ctx->anomaly_windows++;
        if (ctx->anomaly_windows >= ASD_SUSTAINED_ANOMALY_WINDOWS &&
            !ctx->sustained_reported) {
            ctx->sustained_reported = 1;
            out.sustained_anomaly = 1;
        }
    } else {
        ctx->anomaly_windows = 0u;
        ctx->sustained_reported = 0;
    }
    return out;
}

asd_decision_t asd_decide(asd_decision_ctx_t *ctx,
                          const asd_calibration_t *cal,
                          const asd_observation_t *obs) {
    asd_decision_t bad = {ASD_STATE_SENSOR_ERROR, ASD_EVENT_SENSOR_FAULT,
                          ASD_LEVEL_SENSOR_HEALTH, 1, 0};
    if (!ctx || !cal || !obs) return bad;

    asd_state_t previous = ctx->state;
    if (asd_state_is_terminal(previous)) {
        /* Terminalno ostaje terminalno; brojači se ne diraju. */
        return finish(ctx, previous, previous, ASD_EVENT_NONE,
                      ASD_LEVEL_SENSOR_HEALTH, 1);
    }

    /* --- 1) zdravlje senzora ------------------------------------------- */
    if (reason_is_sensor_fault(obs->quality)) {
        ctx->absent_run = 0;
        asd_temporal_reset(&ctx->temporal);
        asd_interference_reset(&ctx->interference);
        return finish(ctx, previous,
                      asd_quality_reject_state(obs->quality, obs->phase),
                      ASD_EVENT_SENSOR_FAULT, ASD_LEVEL_SENSOR_HEALTH, 1);
    }
    if (!isfinite(obs->rms_dbfs) || !isfinite(obs->score) ||
        !isfinite(obs->tonalness_delta) ||
        !isfinite(obs->subsegment_instability) ||
        obs->subsegment_instability < 0.0f) {
        ctx->absent_run = 0;
        asd_temporal_reset(&ctx->temporal);
        asd_interference_reset(&ctx->interference);
        return finish(ctx, previous, ASD_STATE_SENSOR_ERROR,
                      ASD_EVENT_SENSOR_FAULT, ASD_LEVEL_SENSOR_HEALTH, 1);
    }

    /* --- 2) prisustvo mašine ------------------------------------------- */
    /* Bez validne kalibracije nema referentnog nivoa, pa se prisustvo ne može
     * ocijeniti; WAIT i CAL faze žive ovdje i Faza 1 ih već pokriva. */
    if (!cal->valid || !isfinite(cal->level_mean_dbfs) ||
        !isfinite(cal->threshold_enter) || !isfinite(cal->threshold_exit) ||
        !(cal->threshold_exit > 0.0f &&
          cal->threshold_exit < cal->threshold_enter)) {
        ctx->absent_run = 0;
        asd_temporal_reset(&ctx->temporal);
        asd_interference_reset(&ctx->interference);
        return finish(ctx, previous, previous, ASD_EVENT_NONE,
                      ASD_LEVEL_MACHINE_PRESENCE, 0);
    }

    float gate = cal->level_mean_dbfs - ctx->policy.absent_margin_db;
    if (obs->rms_dbfs < gate) {
        ctx->absent_run++;
        /* Odstupanje se NE ocjenjuje dok je nivo ispod gate-a. Kad mašina
         * utihne, score i tako skoči (izmjereno 08.08: 10 → 59), pa bi se bez
         * ovoga prvo emitovala nepostojeća anomalija, a tek onda zaustavljanje.
         * Hijerarhija znači da viši nivo guši niži.
         *
         * SUSPEND, ne RESET: uspon ka alarmu se prekida, ali alarm koji već
         * traje se ne briše. Mašina koja na trenutak utihne ne poništava
         * odstupanje koje je uređaj stvarno izmjerio, a tiho gašenje bi
         * značilo da uređaj zaboravi alarm zbog jednog tihog prozora. */
        asd_temporal_suspend(&ctx->temporal);
        if (ctx->absent_run >= ctx->policy.min_consecutive) {
            return finish(ctx, previous, ASD_STATE_NO_MACHINE,
                          ASD_EVENT_FAN_STOPPED, ASD_LEVEL_MACHINE_PRESENCE, 1);
        }
        /* Još nije trajno: stanje se ne mijenja i ništa se ne emituje. */
        return finish(ctx, previous, previous, ASD_EVENT_NONE,
                      ASD_LEVEL_MACHINE_PRESENCE, 0);
    }
    ctx->absent_run = 0;

    /* Mašina je prisutna, a prethodno je bila odsutna: centar se NIKAD ne
     * pomjera automatski (P10), pa se tok ne nastavlja nego traži ponovnu
     * kalibraciju. */
    if (previous == ASD_STATE_NO_MACHINE) {
        return finish(ctx, previous, ASD_STATE_RECALIBRATION_REQUIRED,
                      ASD_EVENT_UNKNOWN_CHANGE, ASD_LEVEL_MACHINE_PRESENCE, 1);
    }

    /* --- 3) radni režim ------------------------------------------------ */
    /* Prazan nivo do Faze 3. Bez f0 se promjena režima ne može razlikovati od
     * kvara, i to je jedini razlog zbog kojeg odstupanje ispod dobija
     * UNKNOWN_CHANGE umjesto SPEED_CHANGED ili MECHANICAL_ANOMALY. */

    /* --- 4) odstupanje ------------------------------------------------- */
    /* Vremenska odluka je cijela u `asd_temporal.c` (Faza 4): koliko uzastopnih
     * prozora, histereza pri izlasku, i zašto EWMA/CUSUM nisu uzeti. Ovdje
     * ostaje samo prevod alarma u stanje i događaj. */
    asd_interference_observation_t interference_observation = {
        .tonalness_delta = obs->tonalness_delta,
        .subsegment_instability = obs->subsegment_instability,
        .score_high = obs->score > cal->threshold_enter,
        .alarm_active = ctx->temporal.active,
    };
    asd_interference_result_t interference = asd_interference_update(
        &ctx->interference, &interference_observation);
    if (interference == ASD_INTERFERENCE_INVALID) {
        asd_temporal_reset(&ctx->temporal);
        asd_decision_t out = finish(
            ctx, previous, ASD_STATE_SENSOR_ERROR, ASD_EVENT_SENSOR_FAULT,
            ASD_LEVEL_SENSOR_HEALTH, 1);
        return out;
    }
    if (interference == ASD_INTERFERENCE_HOLD ||
        interference == ASD_INTERFERENCE_HOLD_WARNING) {
        asd_temporal_suspend(&ctx->temporal);
        asd_state_t held_state = (ctx->temporal.active ||
                                  previous == ASD_STATE_ANOMALY)
            ? ASD_STATE_ANOMALY : ASD_STATE_OBSERVATION_HOLD;
        asd_decision_t out = finish(ctx, previous, held_state, ASD_EVENT_NONE,
                                    ASD_LEVEL_DEVIATION, 0);
        out.observation_hold = 1;
        out.hold_warning = interference == ASD_INTERFERENCE_HOLD_WARNING;
        return out;
    }
    if (asd_temporal_update(&ctx->temporal, obs->score,
                            cal->threshold_enter, cal->threshold_exit)) {
        /* Status je činjenica, događaj je najslabija tvrdnja koju dokazi
         * podnose. Uzrok se ne tvrdi. */
        return finish(ctx, previous, ASD_STATE_ANOMALY,
                      ASD_EVENT_UNKNOWN_CHANGE, ASD_LEVEL_DEVIATION, 0);
    }
    /* Dok traje uspon ka alarmu stanje se ne mijenja; tek kad detektor nije u
     * alarmu i nije u usponu, prozor je normalan. */
    if (ctx->temporal.run > 0)
        return finish(ctx, previous, previous, ASD_EVENT_NONE,
                      ASD_LEVEL_DEVIATION, 0);
    return finish(ctx, previous, ASD_STATE_CALIBRATED_NORMAL, ASD_EVENT_NONE,
                  ASD_LEVEL_DEVIATION, 0);
}

const char *asd_event_name(asd_event_t event) {
    switch (event) {
        case ASD_EVENT_NONE: return "NONE";
        case ASD_EVENT_FAN_STOPPED: return "FAN_STOPPED";
        case ASD_EVENT_SPEED_CHANGED: return "SPEED_CHANGED";
        case ASD_EVENT_MECHANICAL_ANOMALY: return "MECHANICAL_ANOMALY";
        case ASD_EVENT_AMBIENT_NOISE: return "AMBIENT_NOISE";
        case ASD_EVENT_SENSOR_FAULT: return "SENSOR_FAULT";
        case ASD_EVENT_UNKNOWN_CHANGE: return "UNKNOWN_CHANGE";
        default: return "UNKNOWN_EVENT";
    }
}

const char *asd_capability_name(asd_capability_t capability) {
    switch (capability) {
        case ASD_CAP_AVAILABLE: return "AVAILABLE";
        case ASD_CAP_NEEDS_F0: return "NEEDS_F0";
        case ASD_CAP_NEEDS_DUAL_CHANNEL: return "NEEDS_DUAL_CHANNEL";
        case ASD_CAP_NEEDS_TRANSIENT: return "NEEDS_TRANSIENT";
        default: return "UNKNOWN_CAPABILITY";
    }
}

const char *asd_decision_level_name(asd_decision_level_t level) {
    switch (level) {
        case ASD_LEVEL_SENSOR_HEALTH: return "SENSOR_HEALTH";
        case ASD_LEVEL_MACHINE_PRESENCE: return "MACHINE_PRESENCE";
        case ASD_LEVEL_OPERATING_REGIME: return "OPERATING_REGIME";
        case ASD_LEVEL_DEVIATION: return "DEVIATION";
        default: return "UNKNOWN_LEVEL";
    }
}
