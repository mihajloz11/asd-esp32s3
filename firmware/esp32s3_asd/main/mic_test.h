/* Bring-up mod za INMP441 (rizik C1): snimi nekoliko sekundi živog zvuka,
 * ispiši statistiku (RMS/peak/DC/clipping + peak sirovog 32-bitnog I2S slota)
 * i izbaci PCM kao base64 preko UART-a.
 *
 * PC strana: pc/tools/mic_capture.py -> WAV (16 kHz mono) za Audacity.
 *
 * Ulazak u mod: build sa -DASD_MIC_TEST (set ASD_MIC_TEST=1, pa
 * idf.py reconfigure build flash). Ne dira ni model ni featuring lanac.
 */
#ifndef ASD_MIC_TEST_H
#define ASD_MIC_TEST_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Očekuje da su audio_i2s_init()/audio_i2s_start() već pozvani. Ne vraća se
 * prije nego što odradi snimak i dump. */
void mic_test_run(void);

/* Uokviren base64 ispis PCM bloka: MICWAV_BEGIN zaglavlje sa dužinom i
 * FNV-1a sumom, base64 linije, MICWAV_END. Isti protokol koriste mic_test i
 * live_capture, pa je PC parser (mic_capture.py / live_compare.py) jedan. */
void asd_dump_pcm_block(const int16_t *pcm, size_t n_samples, int sr);

#ifdef __cplusplus
}
#endif
#endif
