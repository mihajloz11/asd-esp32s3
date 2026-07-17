#include "calib_gamma.h"
#include <math.h>

void gamma_calib_reset(gamma_calib_t *c) {
    c->n = 0;
    c->mean = 0.0;
    c->m2 = 0.0;
}

void gamma_calib_add(gamma_calib_t *c, float score) {
    c->n++;
    double d = (double)score - c->mean;
    c->mean += d / c->n;
    c->m2 += d * ((double)score - c->mean);
}

/* Inverzna CDF standardne normalne (Acklam aproksimacija, |err|<1.15e-9). */
static double norm_ppf(double p) {
    static const double a[] = {-3.969683028665376e+01, 2.209460984245205e+02,
                               -2.759285104469687e+02, 1.383577518672690e+02,
                               -3.066479806614716e+01, 2.506628277459239e+00};
    static const double b[] = {-5.447609879822406e+01, 1.615858368580409e+02,
                               -1.556989798598866e+02, 6.680131188771972e+01,
                               -1.328068155288572e+01};
    static const double c_[] = {-7.784894002430293e-03, -3.223964580411365e-01,
                                -2.400758277161838e+00, -2.549732539343734e+00,
                                4.374664141464968e+00, 2.938163982698783e+00};
    static const double d[] = {7.784695709041462e-03, 3.224671290700398e-01,
                               2.445134137142996e+00, 3.754408661907416e+00};
    double q, r;
    if (p < 0.02425) {
        q = sqrt(-2.0 * log(p));
        return (((((c_[0] * q + c_[1]) * q + c_[2]) * q + c_[3]) * q + c_[4]) * q + c_[5]) /
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0);
    }
    if (p > 1.0 - 0.02425) {
        q = sqrt(-2.0 * log(1.0 - p));
        return -(((((c_[0] * q + c_[1]) * q + c_[2]) * q + c_[3]) * q + c_[4]) * q + c_[5]) /
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0);
    }
    q = p - 0.5;
    r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q /
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0);
}

float gamma_calib_threshold(const gamma_calib_t *c, float p) {
    if (c->n < 2) return -1.0f;
    double var = c->m2 / (c->n - 1);
    if (var <= 0.0 || c->mean <= 0.0) return -1.0f;
    double k = c->mean * c->mean / var;     /* shape (momentna metoda) */
    double theta = var / c->mean;           /* scale */
    /* Wilson–Hilferty: gamma_ppf(p;k,θ) ≈ k·θ·(1 - 1/(9k) + z·sqrt(1/(9k)))^3 */
    double z = norm_ppf((double)p);
    double t = 1.0 - 1.0 / (9.0 * k) + z * sqrt(1.0 / (9.0 * k));
    if (t < 0.0) t = 0.0;
    return (float)(k * theta * t * t * t);
}
