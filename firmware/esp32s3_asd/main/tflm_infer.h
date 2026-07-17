/* TFLM int8 inferenca AE modela (plan 5.3): model iz model_data.h (flash),
 * tensor arena statički — SRAM ili PSRAM (Kconfig/definom, E4/E5 poređenje).
 */
#ifndef ASD_TFLM_INFER_H
#define ASD_TFLM_INFER_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

int tflm_init(void);                 /* 0 = OK */
size_t tflm_arena_used(void);        /* stvarno iskorišćena arena (bajta) */

/* Standardizovan ulazni vektor (640 float) -> MSE rekonstrukcije (anomaly score
 * po vektoru). Kvantizacija/dekvantizacija ulaza/izlaza interno. */
float tflm_score_vector(const float *vec);

#ifdef __cplusplus
}
#endif
#endif
