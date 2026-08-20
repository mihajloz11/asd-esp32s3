#include "asd_commissioning.h"

#include <math.h>
#include <string.h>

#define DEV_MIN_SETTLE_WINDOWS 4u
#define DEV_STABLE_SETTLE_WINDOWS 3u
#define DEV_MAX_SETTLE_WINDOWS 60u
#define DEV_CENTER_WINDOWS 10u
#define DEV_DERIVE_WINDOWS 120u
#define DEV_VERIFY_WINDOWS 60u

asd_commission_policy_t asd_commission_default_policy(void) {
    asd_commission_policy_t policy = {
        .min_settle_windows = DEV_MIN_SETTLE_WINDOWS,
        .stable_settle_windows = DEV_STABLE_SETTLE_WINDOWS,
        .max_settle_windows = DEV_MAX_SETTLE_WINDOWS,
        .center_windows = DEV_CENTER_WINDOWS,
        .derive_windows = DEV_DERIVE_WINDOWS,
        .verify_windows = DEV_VERIFY_WINDOWS,
        .settle_timeout_ms = 120000u,
        .center_timeout_ms = 300000u,
        .derive_timeout_ms = 1500000u,
        .verify_timeout_ms = 900000u,
        .max_level_step_db = 3.0f,
        .max_tonalness_step = 1.0f,
        .max_feature_drift = 5.0f,
        .max_verify_episodes = 0u,
        .max_verify_alarm_windows = 0u,
        .max_verify_chatter = 0u,
        .verify_min_consecutive = 3u,
        .developmental = 1,
    };
    return policy;
}

asd_commission_policy_t asd_commission_guided25_policy(void) {
    asd_commission_policy_t policy = asd_commission_default_policy();
    policy.max_settle_windows = 8u;
    policy.derive_windows = 44u;
    policy.verify_windows = 22u;
    policy.settle_timeout_ms = 90000u;
    policy.derive_timeout_ms = 560000u;
    policy.verify_timeout_ms = 290000u;
    return policy;
}

static int policy_valid(const asd_commission_policy_t *policy) {
    return policy && policy->min_settle_windows > 0u &&
           policy->stable_settle_windows > 0u &&
           policy->max_settle_windows >= policy->min_settle_windows &&
           policy->center_windows > 0u && policy->derive_windows > 0u &&
           policy->verify_windows > 0u && policy->settle_timeout_ms > 0u &&
           policy->center_timeout_ms > 0u && policy->derive_timeout_ms > 0u &&
           policy->verify_timeout_ms > 0u &&
           isfinite(policy->max_level_step_db) && policy->max_level_step_db >= 0.0f &&
           isfinite(policy->max_tonalness_step) && policy->max_tonalness_step >= 0.0f &&
           isfinite(policy->max_feature_drift) && policy->max_feature_drift >= 0.0f &&
           policy->verify_min_consecutive > 0u;
}

int asd_commission_profile_persistence_allowed(
    const asd_commission_policy_t *policy) {
    return ASD_PROFILE_PERSISTENCE_ALLOWED == 1 && policy_valid(policy) &&
           policy->developmental == 0;
}

void asd_commission_init(asd_commissioning_t *flow,
                         const asd_commission_policy_t *policy) {
    if (!flow) return;
    memset(flow, 0, sizeof(*flow));
    flow->policy = policy ? *policy : asd_commission_default_policy();
    if (!policy_valid(&flow->policy)) {
        flow->phase = ASD_COMMISSION_REJECTED;
        flow->reject_reason = ASD_COMMISSION_REJECT_INVALID_PROFILE;
    }
}

static void begin_phase(asd_commissioning_t *flow,
                        asd_commission_phase_t phase, uint32_t now_ms) {
    flow->phase = phase;
    flow->phase_started_ms = now_ms;
    flow->phase_windows = 0u;
}

static int reject(asd_commissioning_t *flow, asd_commission_reject_t reason) {
    if (!flow) return 0;
    flow->phase = ASD_COMMISSION_REJECTED;
    flow->reject_reason = reason;
    return 0;
}

int asd_commission_start(asd_commissioning_t *flow, uint32_t now_ms) {
    if (!flow || flow->phase != ASD_COMMISSION_IDLE ||
        !policy_valid(&flow->policy))
        return reject(flow, ASD_COMMISSION_REJECT_INVALID_TRANSITION);
    begin_phase(flow, ASD_COMMISSION_SETTLE, now_ms);
    return 1;
}

static uint32_t current_timeout(const asd_commissioning_t *flow) {
    switch (flow->phase) {
        case ASD_COMMISSION_SETTLE: return flow->policy.settle_timeout_ms;
        case ASD_COMMISSION_CENTER_LEARNING: return flow->policy.center_timeout_ms;
        case ASD_COMMISSION_DERIVE: return flow->policy.derive_timeout_ms;
        case ASD_COMMISSION_VERIFY: return flow->policy.verify_timeout_ms;
        default: return 0u;
    }
}

int asd_commission_poll(asd_commissioning_t *flow, uint32_t now_ms) {
    if (!flow) return 0;
    uint32_t timeout = current_timeout(flow);
    if (timeout && (uint32_t)(now_ms - flow->phase_started_ms) > timeout)
        return reject(flow, ASD_COMMISSION_REJECT_TIMEOUT);
    return flow->phase != ASD_COMMISSION_REJECTED &&
           flow->phase != ASD_COMMISSION_ABORTED;
}

void asd_commission_abort(asd_commissioning_t *flow) {
    if (!flow || flow->phase == ASD_COMMISSION_REJECTED ||
        flow->phase == ASD_COMMISSION_ABORTED)
        return;
    flow->phase = ASD_COMMISSION_ABORTED;
    flow->reject_reason = ASD_COMMISSION_REJECT_OPERATOR_ABORT;
}

int asd_commission_observe_settle(asd_commissioning_t *flow, uint32_t now_ms,
                                  const asd_settle_observation_t *obs) {
    if (!flow || !obs || flow->phase != ASD_COMMISSION_SETTLE)
        return reject(flow, ASD_COMMISSION_REJECT_INVALID_TRANSITION);
    if (!asd_commission_poll(flow, now_ms)) return 0;
    if (!obs->quality_ok || obs->dropped_delta != 0u ||
        !isfinite(obs->level_dbfs) || !isfinite(obs->tonalness) ||
        !isfinite(obs->feature_drift) || obs->feature_drift < 0.0f)
        return reject(flow, ASD_COMMISSION_REJECT_QUALITY);
    flow->phase_windows++;
    flow->settle_windows++;
    int stable = obs->feature_drift <= flow->policy.max_feature_drift;
    if (flow->previous_settle_valid) {
        stable = stable &&
            fabsf(obs->level_dbfs - flow->previous_level_dbfs) <=
                flow->policy.max_level_step_db &&
            fabsf(obs->tonalness - flow->previous_tonalness) <=
                flow->policy.max_tonalness_step;
    } else {
        stable = 0;
    }
    flow->previous_level_dbfs = obs->level_dbfs;
    flow->previous_tonalness = obs->tonalness;
    flow->previous_settle_valid = 1;
    flow->stable_run = stable ? flow->stable_run + 1u : 0u;
    if (flow->settle_windows >= flow->policy.min_settle_windows &&
        flow->stable_run >= flow->policy.stable_settle_windows) {
        begin_phase(flow, ASD_COMMISSION_CENTER_LEARNING, now_ms);
        return 1;
    }
    if (flow->settle_windows >= flow->policy.max_settle_windows)
        return reject(flow, ASD_COMMISSION_REJECT_UNSTABLE_SETTLE);
    return 1;
}

int asd_commission_record_center(asd_commissioning_t *flow, uint32_t now_ms,
                                 int quality_ok) {
    if (!flow || flow->phase != ASD_COMMISSION_CENTER_LEARNING ||
        flow->center_ready)
        return reject(flow, ASD_COMMISSION_REJECT_INVALID_TRANSITION);
    if (!asd_commission_poll(flow, now_ms)) return 0;
    if (!quality_ok) return reject(flow, ASD_COMMISSION_REJECT_QUALITY);
    flow->phase_windows++;
    if (flow->phase_windows >= flow->policy.center_windows)
        flow->center_ready = 1;
    return 1;
}

int asd_commission_commit_center(asd_commissioning_t *flow, uint32_t now_ms,
                                 asd_profile_runtime_t *profile,
                                 const float *center, float level_mean_dbfs,
                                 float tonalness_reference, int k1_accepted) {
    if (!flow || flow->phase != ASD_COMMISSION_CENTER_LEARNING ||
        !flow->center_ready)
        return reject(flow, ASD_COMMISSION_REJECT_INVALID_TRANSITION);
    if (!k1_accepted) return reject(flow, ASD_COMMISSION_REJECT_K1);
    if (!asd_profile_runtime_set_center(
            profile, center, ASD_PROFILE_DIM, level_mean_dbfs,
            tonalness_reference, flow->policy.center_windows,
            ASD_COMMISSIONING_POLICY_VERSION, ASD_COMMISSIONING_POLICY_ID,
            flow->policy.developmental))
        return reject(flow, ASD_COMMISSION_REJECT_INVALID_PROFILE);
    begin_phase(flow, ASD_COMMISSION_DERIVE, now_ms);
    return 1;
}

int asd_commission_record_derive(asd_commissioning_t *flow, uint32_t now_ms,
                                 float score, int quality_ok) {
    if (!flow || flow->phase != ASD_COMMISSION_DERIVE || flow->derive_ready)
        return reject(flow, ASD_COMMISSION_REJECT_INVALID_TRANSITION);
    if (!asd_commission_poll(flow, now_ms)) return 0;
    if (!quality_ok || !isfinite(score) || score < 0.0f)
        return reject(flow, ASD_COMMISSION_REJECT_QUALITY);
    flow->phase_windows++;
    if (flow->phase_windows >= flow->policy.derive_windows)
        flow->derive_ready = 1;
    return 1;
}

int asd_commission_freeze_thresholds(asd_commissioning_t *flow,
                                     uint32_t now_ms,
                                     asd_profile_runtime_t *profile,
                                     float threshold_enter,
                                     float threshold_exit) {
    if (!flow || flow->phase != ASD_COMMISSION_DERIVE || !flow->derive_ready)
        return reject(flow, ASD_COMMISSION_REJECT_INVALID_TRANSITION);
    if (!asd_profile_runtime_freeze_thresholds(
            profile, threshold_enter, threshold_exit,
            flow->policy.derive_windows))
        return reject(flow, ASD_COMMISSION_REJECT_INVALID_PROFILE);
    begin_phase(flow, ASD_COMMISSION_VERIFY, now_ms);
    return 1;
}

int asd_commission_record_verify(asd_commissioning_t *flow, uint32_t now_ms,
                                 asd_profile_runtime_t *profile,
                                 float score, int quality_ok) {
    if (!flow || flow->phase != ASD_COMMISSION_VERIFY)
        return reject(flow, ASD_COMMISSION_REJECT_INVALID_TRANSITION);
    if (!asd_commission_poll(flow, now_ms)) return 0;
    if (!quality_ok || !isfinite(score) || score < 0.0f ||
        !asd_profile_runtime_validate(profile, 0))
        return reject(flow, ASD_COMMISSION_REJECT_QUALITY);

    flow->phase_windows++;
    if (!flow->verify_active) {
        flow->verify_high_run = score > profile->threshold_enter
            ? flow->verify_high_run + 1u : 0u;
        if (flow->verify_high_run >= flow->policy.verify_min_consecutive) {
            flow->verify_active = 1;
            flow->verify_episodes++;
            if (flow->verify_had_exit) flow->verify_chatter++;
        }
    } else if (score <= profile->threshold_exit) {
        flow->verify_active = 0;
        flow->verify_high_run = 0u;
        flow->verify_had_exit = 1;
    }
    if (flow->verify_active) flow->verify_alarm_windows++;

    if (flow->phase_windows < flow->policy.verify_windows) return 1;
    if (flow->verify_episodes > flow->policy.max_verify_episodes ||
        flow->verify_alarm_windows > flow->policy.max_verify_alarm_windows ||
        flow->verify_chatter > flow->policy.max_verify_chatter)
        return reject(flow, ASD_COMMISSION_REJECT_VERIFY_NORMAL);
    if (!asd_profile_runtime_finalize(profile, flow->policy.verify_windows))
        return reject(flow, ASD_COMMISSION_REJECT_INVALID_PROFILE);
    begin_phase(flow, ASD_COMMISSION_MONITORING, now_ms);
    return 1;
}

const char *asd_commission_phase_name(asd_commission_phase_t phase) {
    switch (phase) {
        case ASD_COMMISSION_IDLE: return "IDLE";
        case ASD_COMMISSION_SETTLE: return "SETTLE";
        case ASD_COMMISSION_CENTER_LEARNING: return "CENTER_LEARNING";
        case ASD_COMMISSION_DERIVE: return "COMMISSION_DERIVE";
        case ASD_COMMISSION_VERIFY: return "COMMISSION_VERIFY";
        case ASD_COMMISSION_MONITORING: return "MONITORING";
        case ASD_COMMISSION_REJECTED: return "REJECTED";
        case ASD_COMMISSION_ABORTED: return "ABORTED";
        default: return "UNKNOWN_PHASE";
    }
}

const char *asd_commission_reject_name(asd_commission_reject_t reason) {
    switch (reason) {
        case ASD_COMMISSION_REJECT_NONE: return "NONE";
        case ASD_COMMISSION_REJECT_TIMEOUT: return "PHASE_TIMEOUT";
        case ASD_COMMISSION_REJECT_QUALITY: return "QUALITY_REJECT";
        case ASD_COMMISSION_REJECT_UNSTABLE_SETTLE: return "SETTLE_UNSTABLE";
        case ASD_COMMISSION_REJECT_K1: return "K1_REJECT";
        case ASD_COMMISSION_REJECT_INVALID_PROFILE: return "INVALID_PROFILE";
        case ASD_COMMISSION_REJECT_VERIFY_NORMAL: return "VERIFY_NORMAL_REJECT";
        case ASD_COMMISSION_REJECT_INVALID_TRANSITION: return "INVALID_TRANSITION";
        case ASD_COMMISSION_REJECT_OPERATOR_ABORT: return "OPERATOR_ABORT";
        default: return "UNKNOWN_REJECT";
    }
}
