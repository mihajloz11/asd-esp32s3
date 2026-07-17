/* Log-mel front-end u C — IDENTIČAN kod se kompajlira na ESP32-S3 i na PC-u
 * (preko ctypes, pc/tests/test_features_c.py). Time PC↔C razlika featura
 * nestaje po definiciji (plan, rizik B1).
 *
 * Parametri i mel/Hann tabele dolaze iz generisanog mel_data.h
 * (pc/tools/gen_mel_header.py) — iste vrijednosti kao u Python pipeline-u.
 */
#ifndef ASD_FEATURES_C_H
#define ASD_FEATURES_C_H

#include <stdint.h>

#define ASD_N_FFT     1024
#define ASD_HOP       512
#define ASD_N_MELS    128
#define ASD_N_FRAMES  5
#define ASD_INPUT_DIM (ASD_N_MELS * ASD_N_FRAMES)

#ifdef __cplusplus
extern "C" {
#endif

/* Inicijalizacija (twiddle faktori FFT-a). Pozvati jednom. */
void asd_features_init(void);

/* Jedan STFT frejm (1024 float uzoraka, [-1,1]) -> 128 log-mel vrijednosti. */
void asd_logmel_frame(const float *frame, float *out_mel);

/* Cijeli signal -> log-mel matrica (row-major, n_frames x 128, center=false).
 * Vraća broj frejmova (<= max_frames). */
int asd_logmel(const float *y, int n_samples, float *out, int max_frames);

/* P=5 uzastopnih log-mel frejmova (od indeksa t) -> ulazni vektor 640,
 * standardizovan sa (x-mean)/std iz model headera. */
void asd_make_vector(const float *logmel, int t, const float *mean,
                     const float *std, float *out_vec);

#ifdef __cplusplus
}
#endif
#endif
