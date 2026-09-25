/* Visokorezolucioni PSD otisak: Welch 8192, 96 log traka 10 Hz - 4 kHz,
 * oduzeta srednja vrijednost. PC referenca:
 * pc/tools/bench_periodicity.py::periodic_features. */
#ifndef ASD_PSD_FEATURES_C_H
#define ASD_PSD_FEATURES_C_H

#define ASD_PSD_N_FFT 8192
#define ASD_PSD_HOP 4096
#define ASD_PSD_BANDS 96
#define ASD_PSD_SIDECAR_GROUPS 5

/* Razvojni sidecar za jedan standardni 10 s prozor. Grupe nisu nezavisni
 * klipovi: sadrze uzastopne, preklapajuce Welch segmente 8/8/8/7/7. */
typedef struct {
    int segments;
    int group_segments[ASD_PSD_SIDECAR_GROUPS];
    float group_feature[ASD_PSD_SIDECAR_GROUPS][ASD_PSD_BANDS];
} asd_psd_sidecar_t;

#ifdef __cplusplus
extern "C" {
#endif

void asd_psd_init(void);

/* Mono float signal [-1,1] -> 96-dim psd_shape. Vraća broj Welch segmenata,
 * odnosno 0 ako je signal kraći od jednog FFT prozora. */
int asd_psd_extract(const float *signal, int n_samples, float *out_feature);

/* Streaming varijanta istog racuna: FFT se izvrsi cim se skupi segment, pa
 * nije potreban bafer od 10 s. Rezultat je identican asd_psd_extract, jer je
 * Welch segment tacno dva hopa (8192 = 2 x 4096)
 * (test_psd_features_c.py::test_psd_stream_matches_batch). */
void asd_psd_stream_reset(void);
int  asd_psd_stream_push_hop(const float *hop);   /* 1 = segment obrađen */
int  asd_psd_stream_finish(float *out_feature);   /* -> broj segmenata */

/* Opcioni razvojni put. Stari reset/finish ostaju jedini produkcijski API i
 * njihov finalni 96-dim izlaz mora ostati bit-identican. Sidecar se akumulira
 * samo nakon ovog reset poziva i zapisuje u caller-owned izlaz (ne na stack). */
void asd_psd_stream_reset_sidecar(void);
int  asd_psd_stream_finish_sidecar(float *out_feature,
                                   asd_psd_sidecar_t *out_sidecar);

/* Mahalanobis score nad već izdvojenim feature-om. Sve matrice su row-major. */
float asd_psd_score(const float *feature, const float *norm_mean,
                    const float *norm_std, const float *precision,
                    const float *local_center, int dim);

#ifdef __cplusplus
}
#endif
#endif
