#ifndef ASD_ROBUST_FIT_H
#define ASD_ROBUST_FIT_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ASD_ROBUST_NORMAL_SIGMA 1.4826f

typedef struct {
    float median;
    float mad;
    float robust_sigma;
    float percentile_ceiling;
    float threshold;
    uint32_t capped_high_windows;
} asd_robust_threshold_fit_t;

/* Doradjuje lokalni centar samo iz normal-only DERIVE prozora. Za svaku
 * spektralnu traku odbacuje isti procenat najnizih i najvisih vrijednosti,
 * pa kratki tranzijent ne moze povuci svih 96 koordinata centra. `scratch`
 * mora imati mjesta za `count` float vrijednosti. */
int asd_robust_fit_center(const float *features, size_t count, size_t dims,
                          const float *norm_mean, const float *norm_std,
                          float trim_fraction, float *center, float *scratch);

/* Gornja normalna granica je manja od preregistrovanog empirijskog percentila
 * i Hampelove granice median + k * 1.4826 * MAD. Izolovani visoki prozori zato
 * ne mogu sami podici prag; kasniji VERIFY i dalje mora proci fail-closed. */
int asd_robust_fit_threshold(const float *scores, size_t count,
                             float ceiling_quantile, float sigma_multiplier,
                             asd_robust_threshold_fit_t *fit, float *scratch);

#ifdef __cplusplus
}
#endif

#endif
