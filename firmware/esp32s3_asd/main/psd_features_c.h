/* Visokorezolucioni PSD otisak ventilatora.
 * PC referenca: pc/tools/bench_periodicity.py::periodic_features.
 * Ovaj modul je za sada izolovan od zivog app_main toka dok PC<->C test i
 * on-device latencija ne budu zatvoreni. */
#ifndef ASD_PSD_FEATURES_C_H
#define ASD_PSD_FEATURES_C_H

#define ASD_PSD_N_FFT 8192
#define ASD_PSD_HOP 4096
#define ASD_PSD_BANDS 96

#ifdef __cplusplus
extern "C" {
#endif

void asd_psd_init(void);

/* Mono float signal [-1,1] -> 96-dim psd_shape. Vraća broj Welch segmenata,
 * odnosno 0 ako je signal kraći od jednog FFT prozora. */
int asd_psd_extract(const float *signal, int n_samples, float *out_feature);

/* Streaming varijanta istog računa, za živi rad: FFT se izvrši čim se skupi
 * prozor, pa se račun preklapa sa snimanjem i nije potreban bafer od 10 s.
 * Rezultat je identičan asd_psd_extract nad istim uzorcima — Welch prozor je
 * tačno dva hopa (8192 = 2 x 4096), pa hop k zatvara segment k-1.
 * Provjereno testom pc/tests/test_psd_features_c.py::test_psd_stream_matches_batch. */
void asd_psd_stream_reset(void);
int  asd_psd_stream_push_hop(const float *hop);   /* 1 = segment obrađen */
int  asd_psd_stream_finish(float *out_feature);   /* -> broj segmenata */

/* Mahalanobis score nad već izdvojenim feature-om. Sve matrice su row-major. */
float asd_psd_score(const float *feature, const float *norm_mean,
                    const float *norm_std, const float *precision,
                    const float *local_center, int dim);

#ifdef __cplusplus
}
#endif
#endif
