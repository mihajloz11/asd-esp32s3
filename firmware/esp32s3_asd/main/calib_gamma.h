/* On-device kalibracija praga (E6, plan 5.5): Welford running mean/var nad
 * score-ovima normalnog rada -> momentna procjena gamma (k, θ) -> prag kao
 * p-ti percentil preko Wilson–Hilferty aproksimacije inverzne gamma CDF.
 * Čista aritmetika, bez backpropa. Portabilno C (testirano na PC-u protiv scipy).
 */
#ifndef ASD_CALIB_GAMMA_H
#define ASD_CALIB_GAMMA_H

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int n;
    double mean;
    double m2; /* suma kvadrata odstupanja (Welford) */
} gamma_calib_t;

void gamma_calib_reset(gamma_calib_t *c);
void gamma_calib_add(gamma_calib_t *c, float score);

/* Prag = p-ti percentil (npr. 0.90) fitovane gamma raspodjele.
 * Vraća < 0 ako je n < 2 ili varijansa ~0. */
float gamma_calib_threshold(const gamma_calib_t *c, float p);

#ifdef __cplusplus
}
#endif
#endif
