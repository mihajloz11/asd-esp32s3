/* Deterministic SETTLE -> CENTER -> DERIVE -> VERIFY -> MONITORING flow. */
#ifndef ASD_COMMISSIONING_H
#define ASD_COMMISSIONING_H

#include <stdint.h>

#include "asd_profile_runtime.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ASD_COMMISSIONING_POLICY "asd-commissioning-policy-v1.0.0-development"
#define ASD_COMMISSIONING_POLICY_VERSION 1u
#define ASD_COMMISSIONING_POLICY_ID 0x434d5631u

/* DEVELOPMENT policy is RAM-only.  A future production build must opt in at
 * compile time AND use a frozen non-developmental runtime policy. */
#ifndef ASD_PROFILE_PERSISTENCE_ALLOWED
#define ASD_PROFILE_PERSISTENCE_ALLOWED 0
#endif

typedef enum {
    ASD_COMMISSION_IDLE = 0,
    ASD_COMMISSION_SETTLE,
    ASD_COMMISSION_CENTER_LEARNING,
    ASD_COMMISSION_DERIVE,
    ASD_COMMISSION_VERIFY,
    ASD_COMMISSION_MONITORING,
    ASD_COMMISSION_REJECTED,
    ASD_COMMISSION_ABORTED
} asd_commission_phase_t;

typedef enum {
    ASD_COMMISSION_REJECT_NONE = 0,
    ASD_COMMISSION_REJECT_TIMEOUT,
    ASD_COMMISSION_REJECT_QUALITY,
    ASD_COMMISSION_REJECT_UNSTABLE_SETTLE,
    ASD_COMMISSION_REJECT_K1,
    ASD_COMMISSION_REJECT_INVALID_PROFILE,
    ASD_COMMISSION_REJECT_VERIFY_NORMAL,
    ASD_COMMISSION_REJECT_INVALID_TRANSITION,
    ASD_COMMISSION_REJECT_OPERATOR_ABORT
} asd_commission_reject_t;

typedef struct {
    uint32_t min_settle_windows;
    uint32_t stable_settle_windows;
    uint32_t max_settle_windows;
    uint32_t center_windows;
    uint32_t derive_windows;
    uint32_t verify_windows;
    uint32_t settle_timeout_ms;
    uint32_t center_timeout_ms;
    uint32_t derive_timeout_ms;
    uint32_t verify_timeout_ms;
    float max_level_step_db;
    float max_tonalness_step;
    float max_feature_drift;
    uint32_t max_verify_episodes;
    uint32_t max_verify_alarm_windows;
    uint32_t max_verify_chatter;
    uint32_t verify_min_consecutive;
    int developmental;
} asd_commission_policy_t;

typedef struct {
    int quality_ok;
    float level_dbfs;
    float tonalness;
    float feature_drift;
    uint32_t dropped_delta;
} asd_settle_observation_t;

typedef struct {
    asd_commission_phase_t phase;
    asd_commission_reject_t reject_reason;
    asd_commission_policy_t policy;
    uint32_t phase_started_ms;
    uint32_t phase_windows;
    uint32_t settle_windows;
    uint32_t stable_run;
    float previous_level_dbfs;
    float previous_tonalness;
    int previous_settle_valid;
    int center_ready;
    int derive_ready;
    uint32_t verify_high_run;
    uint32_t verify_alarm_windows;
    uint32_t verify_episodes;
    uint32_t verify_chatter;
    int verify_active;
    int verify_had_exit;
} asd_commissioning_t;

asd_commission_policy_t asd_commission_default_policy(void);
/* Short, explicitly selected DEVELOPMENT validation policy. Default remains
 * the 120/60 normal-only commissioning policy. */
asd_commission_policy_t asd_commission_guided25_policy(void);
int asd_commission_profile_persistence_allowed(
    const asd_commission_policy_t *policy);
void asd_commission_init(asd_commissioning_t *flow,
                         const asd_commission_policy_t *policy);
int asd_commission_start(asd_commissioning_t *flow, uint32_t now_ms);
int asd_commission_poll(asd_commissioning_t *flow, uint32_t now_ms);
void asd_commission_abort(asd_commissioning_t *flow);

/* SETTLE intentionally has no score argument: Mahalanobis is impossible here. */
int asd_commission_observe_settle(asd_commissioning_t *flow, uint32_t now_ms,
                                  const asd_settle_observation_t *observation);
int asd_commission_record_center(asd_commissioning_t *flow, uint32_t now_ms,
                                 int quality_ok);
int asd_commission_commit_center(asd_commissioning_t *flow, uint32_t now_ms,
                                 asd_profile_runtime_t *profile,
                                 const float *center, float level_mean_dbfs,
                                 float tonalness_reference, int k1_accepted);
int asd_commission_record_derive(asd_commissioning_t *flow, uint32_t now_ms,
                                 float score, int quality_ok);
int asd_commission_freeze_thresholds(asd_commissioning_t *flow,
                                     uint32_t now_ms,
                                     asd_profile_runtime_t *profile,
                                     float threshold_enter,
                                     float threshold_exit);
int asd_commission_record_verify(asd_commissioning_t *flow, uint32_t now_ms,
                                 asd_profile_runtime_t *profile,
                                 float score, int quality_ok);

const char *asd_commission_phase_name(asd_commission_phase_t phase);
const char *asd_commission_reject_name(asd_commission_reject_t reason);

#ifdef __cplusplus
}
#endif

#endif
