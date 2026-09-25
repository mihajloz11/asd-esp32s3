/* One-microphone observation reliability gate.  It never diagnoses ambient noise. */
#ifndef ASD_INTERFERENCE_H
#define ASD_INTERFERENCE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ASD_INTERFERENCE_POLICY "asd-interference-policy-v3.0.0-development"
#define ASD_INTERFERENCE_POLICY_ID 0x49505633u

typedef enum {
    ASD_INTERFERENCE_PASS = 0,
    ASD_INTERFERENCE_HOLD,
    ASD_INTERFERENCE_HOLD_WARNING,
    ASD_INTERFERENCE_INVALID
} asd_interference_result_t;

typedef struct {
    int enabled;
    int developmental;
    /* Tonalnost je iskljucena iz odluke: pomjera je i stvarna promjena na
     * masini, pa bi bila jos jedan detektor promjene. Kapija gleda slaganje
     * podsegmenata unutar prozora. Granica se ipak cuva i biljezi. */
    int use_tonalness_delta;
    float max_abs_tonalness_delta;
    /* V3 ne prenosi apsolutnu granicu iz drugog polozaja mikrofona. Svaka
     * sesija je izvodi iz svojih prihvacenih CAL normal-only prozora. */
    float normal_max_multiplier;
    uint32_t calibration_min_windows;
    float max_subsegment_instability;
    uint32_t long_hold_windows;
} asd_interference_policy_t;

typedef struct {
    float tonalness_delta;
    float subsegment_instability;
    int score_high;
    int alarm_active;
} asd_interference_observation_t;

typedef struct {
    asd_interference_policy_t policy;
    uint32_t hold_windows;
    int hold_active;
    int warning_emitted;
} asd_interference_t;

asd_interference_policy_t asd_interference_default_policy(void);
int asd_interference_calibrate_normal(
    asd_interference_policy_t *policy,
    float normal_max_subsegment_instability,
    uint32_t normal_windows);
void asd_interference_init(asd_interference_t *gate,
                           const asd_interference_policy_t *policy);
void asd_interference_reset(asd_interference_t *gate);
asd_interference_result_t asd_interference_update(
    asd_interference_t *gate,
    const asd_interference_observation_t *observation);
const char *asd_interference_result_name(asd_interference_result_t result);

#ifdef __cplusplus
}
#endif

#endif
