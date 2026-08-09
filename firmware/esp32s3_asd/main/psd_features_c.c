#include "psd_features_c.h"

#include <math.h>
#include <stdint.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define PSD_SR 16000.0
#define PSD_MIN_HZ 10.0
#define PSD_MAX_HZ 4000.0

static float tw_re[ASD_PSD_N_FFT / 2];
static float tw_im[ASD_PSD_N_FFT / 2];
static uint16_t bitrev[ASD_PSD_N_FFT];
static float hann[ASD_PSD_N_FFT];
static float fft_re[ASD_PSD_N_FFT];
static float fft_im[ASD_PSD_N_FFT];
static float power_sum[ASD_PSD_N_FFT / 2 + 1];
static uint16_t band_start[ASD_PSD_BANDS];
static uint16_t band_len[ASD_PSD_BANDS];

static void psd_fft(void) {
    for (int i = 0; i < ASD_PSD_N_FFT; i++) {
        int j = bitrev[i];
        if (j > i) {
            float t = fft_re[i]; fft_re[i] = fft_re[j]; fft_re[j] = t;
            t = fft_im[i]; fft_im[i] = fft_im[j]; fft_im[j] = t;
        }
    }
    for (int len = 2; len <= ASD_PSD_N_FFT; len <<= 1) {
        int half = len >> 1;
        int step = ASD_PSD_N_FFT / len;
        for (int i = 0; i < ASD_PSD_N_FFT; i += len) {
            for (int k = 0; k < half; k++) {
                float wr = tw_re[k * step], wi = tw_im[k * step];
                int a = i + k, b = a + half;
                float xr = fft_re[b] * wr - fft_im[b] * wi;
                float xi = fft_re[b] * wi + fft_im[b] * wr;
                fft_re[b] = fft_re[a] - xr;
                fft_im[b] = fft_im[a] - xi;
                fft_re[a] += xr;
                fft_im[a] += xi;
            }
        }
    }
}

void asd_psd_init(void) {
    int log2n = 0;
    while ((1 << log2n) < ASD_PSD_N_FFT) log2n++;
    for (int i = 0; i < ASD_PSD_N_FFT; i++) {
        double a = -2.0 * M_PI * (double)i / (double)ASD_PSD_N_FFT;
        if (i < ASD_PSD_N_FFT / 2) {
            tw_re[i] = (float)cos(a);
            tw_im[i] = (float)sin(a);
        }
        hann[i] = (float)(0.5 - 0.5 * cos(2.0 * M_PI * (double)i /
                                        (double)ASD_PSD_N_FFT));
        unsigned r = 0;
        for (int b = 0; b < log2n; b++)
            if ((unsigned)i & (1u << b)) r |= 1u << (log2n - 1 - b);
        bitrev[i] = (uint16_t)r;
    }

    const double ratio = PSD_MAX_HZ / PSD_MIN_HZ;
    for (int band = 0; band < ASD_PSD_BANDS; band++) {
        double lo = PSD_MIN_HZ * pow(ratio, (double)band / ASD_PSD_BANDS);
        double hi = PSD_MIN_HZ * pow(ratio, (double)(band + 1) / ASD_PSD_BANDS);
        int first = -1, count = 0;
        for (int bin = 0; bin <= ASD_PSD_N_FFT / 2; bin++) {
            double hz = (double)bin * PSD_SR / ASD_PSD_N_FFT;
            if (hz >= lo && hz < hi) {
                if (first < 0) first = bin;
                count++;
            }
        }
        band_start[band] = (uint16_t)(first < 0 ? 0 : first);
        band_len[band] = (uint16_t)count;
    }
}

/* Jedan Welch segment: prozor je vec u fft_re (bez prozorske funkcije). */
static void psd_accumulate_segment(void) {
    for (int i = 0; i < ASD_PSD_N_FFT; i++) {
        fft_re[i] *= hann[i];
        fft_im[i] = 0.0f;
    }
    psd_fft();
    for (int bin = 0; bin <= ASD_PSD_N_FFT / 2; bin++)
        power_sum[bin] += fft_re[bin] * fft_re[bin] + fft_im[bin] * fft_im[bin];
}

/* Zajednicki zavrsni korak za batch i streaming — po konstrukciji isti rezultat.
 * scipy.signal.welch(..., scaling="spectrum", return_onesided=True):
 * prosjek segmenata, 1/sum(window)^2, i x2 za unutrasnje one-sided binove.
 * Za periodicni Hann sum(window)=N/2. */
static int psd_finalize(int segments, float *out_feature) {
    if (segments <= 0) return 0;
    const float win_sum = (float)ASD_PSD_N_FFT * 0.5f;
    const float scale = 2.0f / ((float)segments * win_sum * win_sum);
    float feature_mean = 0.0f;
    for (int band = 0; band < ASD_PSD_BANDS; band++) {
        int count = band_len[band];
        if (count == 0) {
            out_feature[band] = -20.0f;
        } else {
            float sum = 0.0f;
            int first = band_start[band];
            for (int i = 0; i < count; i++) sum += power_sum[first + i];
            float mean_power = scale * sum / (float)count;
            out_feature[band] = log10f(mean_power + 1e-20f);
        }
        feature_mean += out_feature[band];
    }
    feature_mean /= (float)ASD_PSD_BANDS;
    for (int band = 0; band < ASD_PSD_BANDS; band++) out_feature[band] -= feature_mean;
    return segments;
}

int asd_psd_extract(const float *signal, int n_samples, float *out_feature) {
    if (n_samples < ASD_PSD_N_FFT) return 0;
    memset(power_sum, 0, sizeof(power_sum));
    int segments = 0;
    for (int start = 0; start + ASD_PSD_N_FFT <= n_samples; start += ASD_PSD_HOP) {
        for (int i = 0; i < ASD_PSD_N_FFT; i++) fft_re[i] = signal[start + i];
        psd_accumulate_segment();
        segments++;
    }
    return psd_finalize(segments, out_feature);
}

/* --- streaming --- */

/* Prozor mora biti tacno dva hopa, inace donja logika "hop k zatvara segment
 * k-1" ne vazi i streaming bi se razisao od batch racuna. */
#if ASD_PSD_N_FFT != 2 * ASD_PSD_HOP
#error "streaming PSD trazi N_FFT == 2*HOP"
#endif

static float stream_prev[ASD_PSD_HOP];
static int stream_have_prev;
static int stream_segments;

void asd_psd_stream_reset(void) {
    memset(power_sum, 0, sizeof(power_sum));
    stream_have_prev = 0;
    stream_segments = 0;
}

int asd_psd_stream_push_hop(const float *hop) {
    int done = 0;
    if (stream_have_prev) {
        /* prozor = [prethodni hop | tekuci hop] */
        for (int i = 0; i < ASD_PSD_HOP; i++) fft_re[i] = stream_prev[i];
        for (int i = 0; i < ASD_PSD_HOP; i++) fft_re[ASD_PSD_HOP + i] = hop[i];
        psd_accumulate_segment();
        stream_segments++;
        done = 1;
    }
    memcpy(stream_prev, hop, sizeof(stream_prev));
    stream_have_prev = 1;
    return done;
}

int asd_psd_stream_finish(float *out_feature) {
    return psd_finalize(stream_segments, out_feature);
}

float asd_psd_score(const float *feature, const float *norm_mean,
                    const float *norm_std, const float *precision,
                    const float *local_center, int dim) {
    static float delta[ASD_PSD_BANDS];
    static float projected[ASD_PSD_BANDS];
    if (dim > ASD_PSD_BANDS) return NAN;
    for (int i = 0; i < dim; i++)
        delta[i] = (feature[i] - norm_mean[i]) / norm_std[i] - local_center[i];
    for (int i = 0; i < dim; i++) {
        float sum = 0.0f;
        for (int j = 0; j < dim; j++) sum += precision[i * dim + j] * delta[j];
        projected[i] = sum;
    }
    float score = 0.0f;
    for (int i = 0; i < dim; i++) score += delta[i] * projected[i];
    return score;
}
