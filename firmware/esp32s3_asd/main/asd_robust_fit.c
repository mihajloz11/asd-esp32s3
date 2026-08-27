#include "asd_robust_fit.h"

#include <math.h>
#include <stdlib.h>

static int cmp_float(const void *left, const void *right) {
    float a = *(const float *)left;
    float b = *(const float *)right;
    return (a > b) - (a < b);
}

static float sorted_median(const float *values, size_t count) {
    if ((count & 1u) != 0u) return values[count / 2u];
    return 0.5f * (values[count / 2u - 1u] + values[count / 2u]);
}

static float percentile_higher_sorted(const float *values, size_t count,
                                      float quantile) {
    size_t index = (size_t)ceilf(quantile * (float)count) - 1u;
    if (index >= count) index = count - 1u;
    return values[index];
}

int asd_robust_fit_center(const float *features, size_t count, size_t dims,
                          const float *norm_mean, const float *norm_std,
                          float trim_fraction, float *center, float *scratch) {
    if (!features || !norm_mean || !norm_std || !center || !scratch ||
        count < 3u || dims == 0u || !isfinite(trim_fraction) ||
        trim_fraction < 0.0f || trim_fraction >= 0.5f)
        return 0;

    size_t trim = (size_t)floorf(trim_fraction * (float)count);
    if (2u * trim >= count) return 0;
    size_t retained = count - 2u * trim;

    for (size_t dim = 0; dim < dims; dim++) {
        if (!isfinite(norm_mean[dim]) || !isfinite(norm_std[dim]) ||
            !(norm_std[dim] > 0.0f))
            return 0;
        for (size_t row = 0; row < count; row++) {
            float value = features[row * dims + dim];
            if (!isfinite(value)) return 0;
            scratch[row] = value;
        }
        qsort(scratch, count, sizeof(float), cmp_float);
        double sum = 0.0;
        for (size_t row = trim; row < count - trim; row++) sum += scratch[row];
        float trimmed_mean = (float)(sum / (double)retained);
        center[dim] = (trimmed_mean - norm_mean[dim]) / norm_std[dim];
        if (!isfinite(center[dim])) return 0;
    }
    return 1;
}

int asd_robust_fit_threshold(const float *scores, size_t count,
                             float ceiling_quantile, float sigma_multiplier,
                             asd_robust_threshold_fit_t *fit, float *scratch) {
    if (!scores || !fit || !scratch || count < 3u ||
        !isfinite(ceiling_quantile) || ceiling_quantile <= 0.0f ||
        ceiling_quantile >= 1.0f || !isfinite(sigma_multiplier) ||
        !(sigma_multiplier > 0.0f))
        return 0;

    for (size_t i = 0; i < count; i++) {
        if (!isfinite(scores[i]) || scores[i] < 0.0f) return 0;
        scratch[i] = scores[i];
    }
    qsort(scratch, count, sizeof(float), cmp_float);
    float median = sorted_median(scratch, count);
    float ceiling = percentile_higher_sorted(scratch, count, ceiling_quantile);

    for (size_t i = 0; i < count; i++) scratch[i] = fabsf(scores[i] - median);
    qsort(scratch, count, sizeof(float), cmp_float);
    float mad = sorted_median(scratch, count);
    float robust_sigma = ASD_ROBUST_NORMAL_SIGMA * mad;
    float robust_limit = median + sigma_multiplier * robust_sigma;
    float threshold = robust_limit < ceiling ? robust_limit : ceiling;
    if (!isfinite(median) || !isfinite(mad) || !isfinite(robust_sigma) ||
        !isfinite(ceiling) || !isfinite(threshold) || !(threshold > 0.0f))
        return 0;

    uint32_t capped = 0u;
    for (size_t i = 0; i < count; i++)
        if (scores[i] > threshold) capped++;
    *fit = (asd_robust_threshold_fit_t){
        .median = median,
        .mad = mad,
        .robust_sigma = robust_sigma,
        .percentile_ceiling = ceiling,
        .threshold = threshold,
        .capped_high_windows = capped,
    };
    return 1;
}
