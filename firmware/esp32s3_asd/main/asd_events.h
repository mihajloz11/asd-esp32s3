/* Faza 2 — prisustvo mašine, režim i semantika događaja.
 *
 * Host-testable, no ESP-IDF / I2S / PSD dependencies, same pattern as
 * audio_quality_state.c.  The live firmware feeds it one observation per
 * window; host tests feed the same API deterministic fixtures.
 *
 * THREE THINGS ARE KEPT SEPARATE, and conflating them is the mistake this
 * module exists to prevent:
 *
 *   status (asd_state_t)  — what the device IS: a fact about its own flow.
 *   event  (asd_event_t)  — what HAPPENED: the most specific claim that the
 *                           currently available evidence supports.
 *   cause                 — WHY it happened. Not produced here. Requires f0
 *                           (Faza 3), near/far (Faza 5) and the transient path
 *                           (Faza 6).
 *
 * Consequence: a sustained deviation from the calibrated centre yields
 * status ASD_STATE_ANOMALY (a fact) with event ASD_EVENT_UNKNOWN_CHANGE (a
 * conservative claim) — never ASD_EVENT_MECHANICAL_ANOMALY, which would be a
 * diagnosis this pipeline cannot yet justify.  asd_event_capability() encodes
 * that refusal in code so it cannot be forgotten.
 *
 * DECISION HIERARCHY, evaluated strictly in this order.  A level that fires
 * suppresses every level below it, because a lower level's input is
 * meaningless once a higher one is violated:
 *
 *   1. sensor health     — is the signal trustworthy at all?
 *   2. machine presence  — is the calibrated machine still there?
 *   3. operating regime  — which normal mode is it in?   (needs Faza 3)
 *   4. deviation         — does it depart from the calibrated centre?
 */
#ifndef ASD_EVENTS_H
#define ASD_EVENTS_H

#include "audio_quality_state.h"
#include "asd_temporal.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ASD_EVENTS_PROTOCOL "asd-events-v1.0.0"

typedef enum {
    ASD_EVENT_NONE = 0,
    ASD_EVENT_FAN_STOPPED,
    ASD_EVENT_SPEED_CHANGED,
    ASD_EVENT_MECHANICAL_ANOMALY,
    ASD_EVENT_AMBIENT_NOISE,
    ASD_EVENT_SENSOR_FAULT,
    ASD_EVENT_UNKNOWN_CHANGE
} asd_event_t;

/* What must exist before an event may legally be emitted.  Reserved events are
 * part of the locked taxonomy so the serial contract does not change later, but
 * emitting one now would be an unsupported diagnosis. */
typedef enum {
    ASD_CAP_AVAILABLE = 0,       /* emittable with what exists today */
    ASD_CAP_NEEDS_F0,            /* Faza 3: fundamental frequency + confidence */
    ASD_CAP_NEEDS_DUAL_CHANNEL,  /* Faza 5: near/far attribution */
    ASD_CAP_NEEDS_TRANSIENT      /* Faza 6: fast transient path */
} asd_capability_t;

typedef enum {
    ASD_LEVEL_SENSOR_HEALTH = 0,
    ASD_LEVEL_MACHINE_PRESENCE,
    ASD_LEVEL_OPERATING_REGIME,
    ASD_LEVEL_DEVIATION
} asd_decision_level_t;

/* Machine-presence gate.  Derived from normal-only data by
 * pc/tools/derive_presence_policy.py and locked in
 * pc/config/asd_presence_policy_v1.json.  Never tuned on target anomalies. */
typedef struct {
    float absent_margin_db;   /* how far below the calibrated level counts as gone */
    int min_consecutive;      /* sustained windows before any event is emitted */
} asd_presence_policy_t;

asd_presence_policy_t asd_presence_default_policy(void);

/* Frozen result of an accepted calibration.  `valid` is the gate that makes
 * presence and deviation judgeable at all. */
typedef struct {
    int valid;
    float level_mean_dbfs;
    float score_threshold;
} asd_calibration_t;

typedef struct {
    asd_quality_reason_t quality;
    asd_quality_phase_t phase;
    float rms_dbfs;
    float score;
} asd_observation_t;

/* Carries the run counters so callers keep no ad-hoc state of their own.
 *
 * Odstupanje više ne broji ovaj modul nego `asd_temporal.c` (Faza 4): tamo
 * živi i histereza, i tamo je izmjereno zašto EWMA i CUSUM nisu uzeti. */
typedef struct {
    asd_state_t state;
    int absent_run;
    asd_temporal_t temporal;
    asd_presence_policy_t policy;
} asd_decision_ctx_t;

typedef struct {
    asd_state_t state;
    asd_event_t event;
    asd_decision_level_t level;
    int flow_stop;         /* 1 = fail-closed: caller must stop the flow */
    int state_changed;     /* 1 = state differs from the previous observation */
} asd_decision_t;

void asd_decision_init(asd_decision_ctx_t *ctx,
                       const asd_presence_policy_t *policy);

/* One window in, one decision out.  Deterministic: identical ctx + inputs
 * always produce an identical result. */
asd_decision_t asd_decide(asd_decision_ctx_t *ctx,
                          const asd_calibration_t *cal,
                          const asd_observation_t *obs);

asd_capability_t asd_event_capability(asd_event_t event);
int asd_event_is_emittable(asd_event_t event);

/* Semantika Faze 2 za fail-closed odbijanja iz Faze 1 (WAIT/CAL gate-ovi).
 *
 * Ove faze ne prolaze kroz `asd_decide()`, jer tamo još nema kalibracije od
 * koje bi se odstupalo, ali njihov ishod ipak mora dobiti isti rječnik
 * događaja i nivoa. Preslikavanje živi ovdje, u testiranom modulu, a ne u
 * neprovjerenoj I2S petlji.
 *
 * Prenizak nivo daje `ASD_EVENT_NONE`, ne `FAN_STOPPED`: kad kalibracije nema,
 * uređaj nije ni čuo mašinu, pa ne smije tvrditi da je stala. */
asd_event_t asd_event_for_quality_reject(asd_quality_reason_t reason);
asd_decision_level_t asd_level_for_quality_reject(asd_quality_reason_t reason);

/* Deterministic transition table.  Returns 1 for an allowed transition.
 * Notably forbidden: any path into CALIBRATED_NORMAL or ANOMALY without a
 * valid calibration, and any escape from a terminal state. */
int asd_transition_allowed(asd_state_t from, asd_state_t to);
int asd_state_is_terminal(asd_state_t state);

const char *asd_event_name(asd_event_t event);
const char *asd_capability_name(asd_capability_t capability);
const char *asd_decision_level_name(asd_decision_level_t level);

#ifdef __cplusplus
}
#endif

#endif
