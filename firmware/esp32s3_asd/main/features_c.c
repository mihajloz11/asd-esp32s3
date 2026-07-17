/* Portabilna float32 implementacija: Hann -> radix-2 FFT -> power -> sparse mel -> log.
 * Bez zavisnosti od ESP-IDF-a — kompajlira se i na PC-u (ctypes unit test).
 * Kasnija optimizacija: zamjena FFT-a sa esp-dsp dsps_fft2r_fc32 iza #ifdef,
 * uz obavezan re-run PC↔C testa razlike.
 */
#include "features_c.h"
#include "mel_data.h" /* generisano: asd_hann[1024], mel sparse tabele */

#include <math.h>
#include <string.h>

#define LOG_EPS 1e-12f
/* 20/POWER * log10(x) za POWER=2 -> 10*log10(x) = (10/ln10)*ln(x) */
#define LOG10_SCALE 4.342944819032518f

static float tw_re[ASD_N_FFT / 2];
static float tw_im[ASD_N_FFT / 2];
static uint16_t bitrev[ASD_N_FFT];
static float fft_re[ASD_N_FFT];
static float fft_im[ASD_N_FFT];

void asd_features_init(void) {
    for (int i = 0; i < ASD_N_FFT / 2; i++) {
        double a = -2.0 * M_PI * (double)i / (double)ASD_N_FFT;
        tw_re[i] = (float)cos(a);
        tw_im[i] = (float)sin(a);
    }
    int log2n = 0;
    while ((1 << log2n) < ASD_N_FFT) log2n++;
    for (int i = 0; i < ASD_N_FFT; i++) {
        unsigned r = 0;
        for (int b = 0; b < log2n; b++)
            if (i & (1u << b)) r |= 1u << (log2n - 1 - b);
        bitrev[i] = (uint16_t)r;
    }
}

/* In-place iterativni radix-2 DIT FFT nad fft_re/fft_im. */
static void fft(void) {
    for (int i = 0; i < ASD_N_FFT; i++) {
        int j = bitrev[i];
        if (j > i) {
            float t = fft_re[i]; fft_re[i] = fft_re[j]; fft_re[j] = t;
            t = fft_im[i]; fft_im[i] = fft_im[j]; fft_im[j] = t;
        }
    }
    for (int len = 2; len <= ASD_N_FFT; len <<= 1) {
        int half = len >> 1;
        int step = ASD_N_FFT / len;
        for (int i = 0; i < ASD_N_FFT; i += len) {
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

void asd_logmel_frame(const float *frame, float *out_mel) {
    for (int i = 0; i < ASD_N_FFT; i++) {
        fft_re[i] = frame[i] * asd_hann[i];
        fft_im[i] = 0.0f;
    }
    fft();
    /* power spektar, binovi 0..N/2 */
    static float power[ASD_N_FFT / 2 + 1];
    for (int i = 0; i <= ASD_N_FFT / 2; i++)
        power[i] = fft_re[i] * fft_re[i] + fft_im[i] * fft_im[i];
    /* sparse mel: filter m pokriva binove [start, start+len) */
    for (int m = 0; m < ASD_N_MELS; m++) {
        const float *w = &asd_mel_weights[asd_mel_offset[m]];
        int start = asd_mel_start[m], len = asd_mel_len[m];
        float acc = 0.0f;
        for (int i = 0; i < len; i++) acc += power[start + i] * w[i];
        out_mel[m] = LOG10_SCALE * logf(acc + LOG_EPS);
    }
}

int asd_logmel(const float *y, int n_samples, float *out, int max_frames) {
    if (n_samples < ASD_N_FFT) return 0;
    int n_frames = 1 + (n_samples - ASD_N_FFT) / ASD_HOP;
    if (n_frames > max_frames) n_frames = max_frames;
    for (int t = 0; t < n_frames; t++)
        asd_logmel_frame(y + (long)t * ASD_HOP, out + (long)t * ASD_N_MELS);
    return n_frames;
}

void asd_make_vector(const float *logmel, int t, const float *mean,
                     const float *std, float *out_vec) {
    for (int p = 0; p < ASD_N_FRAMES; p++) {
        const float *src = logmel + (long)(t + p) * ASD_N_MELS;
        float *dst = out_vec + (long)p * ASD_N_MELS;
        const float *mu = mean + (long)p * ASD_N_MELS;
        const float *sd = std + (long)p * ASD_N_MELS;
        for (int i = 0; i < ASD_N_MELS; i++)
            dst[i] = (src[i] - mu[i]) / sd[i];
    }
}
