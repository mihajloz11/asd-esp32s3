/* Faza 2: prisustvo masine, rezim i semantika dogadjaja.
 *
 * Bez ESP-IDF zavisnosti; firmware i host testovi zovu isti API.
 *
 * Tri stvari su namjerno razdvojene:
 *   stanje (asd_state_t)   sta uredjaj JESTE, cinjenica o sopstvenom toku;
 *   dogadjaj (asd_event_t) najuza tvrdnja koju dokazi podnose;
 *   uzrok                  ovdje se ne pravi (trazi f0, near/far, tranzijente).
 * Trajno odstupanje zato daje ANOMALY + UNKNOWN_CHANGE, nikad
 * MECHANICAL_ANOMALY; asd_event_capability() to cuva u kodu.
 *
 * Hijerarhija odluke, strogo ovim redom; nivo koji okine gasi sve ispod:
 *   1. zdravlje senzora
 *   2. prisustvo masine
 *   3. radni rezim (ceka Fazu 3)
 *   4. odstupanje od centra
 */
#ifndef ASD_EVENTS_H
#define ASD_EVENTS_H

#include "audio_quality_state.h"
#include "asd_interference.h"
#include "asd_temporal.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ASD_EVENTS_PROTOCOL "asd-events-v1.1.0-development"

typedef enum {
    ASD_EVENT_NONE = 0,
    ASD_EVENT_FAN_STOPPED,
    ASD_EVENT_SPEED_CHANGED,
    ASD_EVENT_MECHANICAL_ANOMALY,
    ASD_EVENT_AMBIENT_NOISE,
    ASD_EVENT_SENSOR_FAULT,
    ASD_EVENT_UNKNOWN_CHANGE
} asd_event_t;

/* Sta mora postojati da bi dogadjaj smio biti emitovan. Rezervisani
 * dogadjaji su u zakljucanoj taksonomiji, ali bi njihovo emitovanje sada
 * bila dijagnoza bez dokaza. */
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

/* Gate prisustva, izveden samo iz normalnih podataka
 * (derive_presence_policy.py -> asd_presence_policy_v1.json). */
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
    float threshold_enter;
    float threshold_exit;
} asd_calibration_t;

typedef struct {
    asd_quality_reason_t quality;
    asd_quality_phase_t phase;
    float rms_dbfs;
    float score;
    float tonalness_delta;
    float subsegment_instability;
} asd_observation_t;

/* Brojaci toka zive ovdje, da pozivalac nema svoje stanje. Odstupanje
 * broji asd_temporal.c (Faza 4). */
/* 12 alarmnih prozora x 10 s = dva minuta. Pogonska odluka kada odstupanje
 * postaje stanje koje trazi covjeka, a ne prag izveden iz podataka. */
#define ASD_SUSTAINED_ANOMALY_WINDOWS 12u

typedef struct {
    asd_state_t state;
    int absent_run;
    uint32_t anomaly_windows;
    int sustained_reported;
    asd_temporal_t temporal;
    asd_interference_t interference;
    asd_presence_policy_t policy;
} asd_decision_ctx_t;

typedef struct {
    asd_state_t state;
    asd_event_t event;
    asd_decision_level_t level;
    int flow_stop;         /* 1 = fail-closed: caller must stop the flow */
    int state_changed;     /* 1 = state differs from the previous observation */
    int observation_hold;  /* unreliable single-mic observation; no diagnosis */
    int hold_warning;      /* hold exceeded the DEVELOPMENT inspection limit */
    /* 1 u prozoru u kojem alarm napuni dva minuta MJERENOG vremena; HOLD
     * prozori se ne broje. Tvrdnja je o trajanju, ne o uzroku (UNKNOWN_CHANGE). */
    int sustained_anomaly;
} asd_decision_t;

void asd_decision_init(asd_decision_ctx_t *ctx,
                       const asd_presence_policy_t *policy);
void asd_decision_set_interference_policy(
    asd_decision_ctx_t *ctx, const asd_interference_policy_t *policy);

/* One window in, one decision out.  Deterministic: identical ctx + inputs
 * always produce an identical result. */
asd_decision_t asd_decide(asd_decision_ctx_t *ctx,
                          const asd_calibration_t *cal,
                          const asd_observation_t *obs);

asd_capability_t asd_event_capability(asd_event_t event);
int asd_event_is_emittable(asd_event_t event);

/* Semantika Faze 2 za fail-closed odbijanja u WAIT/CAL, koja ne prolaze
 * kroz asd_decide(). Prenizak nivo daje ASD_EVENT_NONE, ne FAN_STOPPED:
 * bez kalibracije uredjaj masinu nije ni cuo. */
asd_event_t asd_event_for_quality_reject(asd_quality_reason_t reason);
asd_decision_level_t asd_level_for_quality_reject(asd_quality_reason_t reason);

/* Deterministicka tabela prelaza, 1 = dozvoljen. Zabranjen je ulaz u
 * CALIBRATED_NORMAL ili ANOMALY bez kalibracije i izlaz iz terminalnog
 * stanja. */
int asd_transition_allowed(asd_state_t from, asd_state_t to);
int asd_state_is_terminal(asd_state_t state);

const char *asd_event_name(asd_event_t event);
const char *asd_capability_name(asd_capability_t capability);
const char *asd_decision_level_name(asd_decision_level_t level);

#ifdef __cplusplus
}
#endif

#endif
