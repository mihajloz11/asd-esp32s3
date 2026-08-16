/* I2S capture za INMP441 (plan 5.3): i2s_std drajver, 16 kHz, 32-bit slot
 * (INMP441 daje 24-bit MSB), mono lijevi kanal. DMA baferi u INTERNOM SRAM-u
 * (S3 DMA ne pristupa PSRAM-u!); veliki ring buffer u PSRAM-u.
 */
#ifndef ASD_AUDIO_I2S_H
#define ASD_AUDIO_I2S_H

#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"

#define AUDIO_SR         16000
#define AUDIO_RING_SEC   2                       /* ring buffer kapacitet */
#define AUDIO_RING_LEN   (AUDIO_SR * AUDIO_RING_SEC)

esp_err_t audio_i2s_init(void);
esp_err_t audio_i2s_start(void);

/* Blokirajuće čitanje n uzoraka (16-bit PCM) iz ring buffera. */
size_t audio_read(int16_t *dst, size_t n_samples);

/* Prazni ring bafer i vraća koliko je uzoraka odbačeno. Zove se na početku
 * sesije, da nakupljeno čekanje ne padne na teret prvog mjernog bloka. */
size_t audio_flush(void);

/* Broj dropovanih uzoraka od starta (dijagnostika DMA overruna, rizik C4). */
uint32_t audio_dropped_samples(void);

/* Max |x| sirovog 32-bitnog I2S slota (prije shifta u 16 bita) od zadnjeg
 * reseta — provjera da li je shift dobro odabran (rizik C1, mic_test.c). */
int32_t audio_raw_peak(void);
void    audio_raw_peak_reset(void);

#endif
