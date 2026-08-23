/* One-microphone observation reliability gate.  It never diagnoses ambient noise. */
#ifndef ASD_INTERFERENCE_H
#define ASD_INTERFERENCE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ASD_INTERFERENCE_POLICY "asd-interference-policy-v2.0.0-development"
#define ASD_INTERFERENCE_POLICY_ID 0x49505632u

typedef enum {
    ASD_INTERFERENCE_PASS = 0,
    ASD_INTERFERENCE_HOLD,
    ASD_INTERFERENCE_HOLD_WARNING,
    ASD_INTERFERENCE_INVALID
} asd_interference_result_t;

typedef struct {
    int enabled;
    int developmental;
    /* Tonalnost je iskljucena iz odluke i to nije stelovanje brojke nego
     * posljedica onoga sto mjeri: koliko se tonalni potpis prozora razlikuje od
     * kalibracionog. Stvarna promjena na masini ga pomjeri isto kao i tudji
     * zvuk, pa je to detektor PROMJENE -- a promjenu skor vec mjeri. Kapija
     * pouzdanosti mora gledati nesto ortogonalno, a to je slaganje podsegmenata
     * unutar istog prozora. Granica se svejedno cuva i biljezi. */
    int use_tonalness_delta;
    float max_abs_tonalness_delta;
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
