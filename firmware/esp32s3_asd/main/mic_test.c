/* Bring-up mod za INMP441 — vidi mic_test.h.
 *
 * Dvije faze:
 *   1) mjerač nivoa (~8 s): RMS/peak svakih 250 ms + bar na UART-u; ovdje se
 *      golim okom vidi da li mikrofon reaguje (kucni po njemu, zvizni).
 *   2) snimak 5 s u PSRAM -> statistika -> base64 PCM na UART.
 *
 * Statistika sadrži i peak SIROVOG 32-bitnog I2S slota (prije >>14 iz
 * audio_i2s.c) — to je jedini način da se provjeri je li shift dobro odabran
 * (rizik C1): ako je sirovi peak daleko ispod punog opsega, shift je prejak i
 * baca bite; ako 16-bit izlaz klipuje a sirovi ne, shift je preslab.
 */
#include "mic_test.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_heap_caps.h"
#include "esp_log.h"

#include "audio_i2s.h"
#include "pins.h"

static const char *TAG = "mic";

#define MIC_TEST_SEC     5
#define MIC_METER_SEC    8
#define MIC_WARMUP_MS    500                        /* INMP441 startup + DC settling */
#define MIC_CHUNK        (AUDIO_SR / 4)             /* 250 ms */
#define MIC_N_SAMPLES    (AUDIO_SR * MIC_TEST_SEC)
#define MIC_CLIP_LEVEL   32000

typedef struct {
    double  dc;         /* srednja vrijednost (DC offset) */
    double  rms;        /* RMS oko DC-a */
    int32_t peak;       /* max |x| */
    int     clipped;    /* broj uzoraka >= MIC_CLIP_LEVEL */
    int     zeros;      /* broj uzoraka tačno 0 */
} mic_stats_t;

static void mic_stats(const int16_t *pcm, size_t n, mic_stats_t *st) {
    double sum = 0.0, sumsq = 0.0;
    int32_t peak = 0;
    int clipped = 0, zeros = 0;

    for (size_t i = 0; i < n; i++) {
        int32_t s = pcm[i];
        sum += s;
        sumsq += (double)s * (double)s;
        int32_t a = s < 0 ? -s : s;
        if (a > peak) peak = a;
        if (a >= MIC_CLIP_LEVEL) clipped++;
        if (s == 0) zeros++;
    }
    st->dc = sum / (double)n;
    double var = sumsq / (double)n - st->dc * st->dc;
    st->rms = var > 0.0 ? sqrt(var) : 0.0;
    st->peak = peak;
    st->clipped = clipped;
    st->zeros = zeros;
}

static float mic_dbfs(double amp) {
    if (amp < 1e-9) return -999.0f;
    return (float)(20.0 * log10(amp / 32768.0));
}

/* base64 PCM (little-endian int16) u linijama po 76 znakova.
 * Dump traje ~19 s na 115200 bauda; bez ustupanja procesora IDLE0 skapa i
 * task watchdog upise svoj tekst PRAVO U SREDINU base64 toka (dekodovanje se
 * onda pomjeri i WAV je smece). Zato vTaskDelay svakih par linija. */
static void mic_dump_b64(const uint8_t *data, size_t nbytes) {
    static const char tbl[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    char line[80];
    int col = 0;
    int lines = 0;

    for (size_t i = 0; i < nbytes; i += 3) {
        uint32_t v = (uint32_t)data[i] << 16;
        if (i + 1 < nbytes) v |= (uint32_t)data[i + 1] << 8;
        if (i + 2 < nbytes) v |= (uint32_t)data[i + 2];

        line[col++] = tbl[(v >> 18) & 63];
        line[col++] = tbl[(v >> 12) & 63];
        line[col++] = (i + 1 < nbytes) ? tbl[(v >> 6) & 63] : '=';
        line[col++] = (i + 2 < nbytes) ? tbl[v & 63] : '=';

        if (col >= 76) {
            line[col] = '\0';
            printf("%s\n", line);
            col = 0;
            if (++lines % 16 == 0) vTaskDelay(1);
        }
    }
    if (col) { line[col] = '\0'; printf("%s\n", line); }
}

void asd_dump_pcm_block(const int16_t *pcm, size_t n_samples, int sr) {
    const uint8_t *bytes = (const uint8_t *)pcm;
    const size_t nbytes = n_samples * sizeof(int16_t);

    /* Kontrolna suma preko bajtova — PC strana provjerava da prenos nije
     * pomjeren (base64 tok je osjetljiv na svaki visak/manjak znaka; vidi
     * docs/problemi-i-rjesenja.md P4). */
    uint32_t crc = 2166136261u;                       /* FNV-1a 32 */
    for (size_t i = 0; i < nbytes; i++) {
        crc ^= bytes[i];
        crc *= 16777619u;
    }

    printf("MICWAV_BEGIN sr=%d n=%u bytes=%u fnv1a=%08lx\n",
           sr, (unsigned)n_samples, (unsigned)nbytes, (unsigned long)crc);
    mic_dump_b64(bytes, nbytes);
    printf("MICWAV_END\n");
}

void mic_test_run(void) {
    static int16_t chunk[MIC_CHUNK];
    mic_stats_t st;

    ESP_LOGI(TAG, "=== MIC TEST === pinovi: BCLK=%d WS=%d SD=%d (L/R mikrofona -> GND)",
             PIN_I2S_BCLK, PIN_I2S_WS, PIN_I2S_DIN);

    /* 1) zagrijavanje — prvi uzorci poslije enable-a su smeće */
    for (int i = 0; i < MIC_WARMUP_MS / 250; i++)
        audio_read(chunk, MIC_CHUNK);
    audio_raw_peak_reset();

    /* 2) mjerač nivoa */
    ESP_LOGI(TAG, "mjerac nivoa %d s — kucni po mikrofonu ili zvizni:", MIC_METER_SEC);
    for (int i = 0; i < MIC_METER_SEC * 4; i++) {
        audio_read(chunk, MIC_CHUNK);
        mic_stats(chunk, MIC_CHUNK, &st);

        int bars = (int)((mic_dbfs(st.rms) + 70.0f) / 70.0f * 32.0f);
        if (bars < 0) bars = 0;
        if (bars > 32) bars = 32;
        char bar[33];
        for (int b = 0; b < 32; b++) bar[b] = b < bars ? '#' : '.';
        bar[32] = '\0';

        printf("  [%s] rms=%7.1f (%6.1f dBFS) peak=%6ld dc=%8.1f%s\n",
               bar, st.rms, mic_dbfs(st.rms), (long)st.peak, st.dc,
               st.zeros == MIC_CHUNK ? "   <-- SAMO NULE" : "");
    }

    /* 3) snimak */
    int16_t *rec = heap_caps_malloc(MIC_N_SAMPLES * sizeof(int16_t), MALLOC_CAP_SPIRAM);
    if (!rec) rec = heap_caps_malloc(MIC_N_SAMPLES * sizeof(int16_t), MALLOC_CAP_8BIT);
    if (!rec) {
        ESP_LOGE(TAG, "nema memorije za %d uzoraka", MIC_N_SAMPLES);
        return;
    }

    ESP_LOGI(TAG, "snimam %d s...", MIC_TEST_SEC);
    audio_raw_peak_reset();
    uint32_t dropped_before = audio_dropped_samples();
    for (int off = 0; off < MIC_N_SAMPLES; off += MIC_CHUNK)
        audio_read(rec + off, MIC_CHUNK);

    mic_stats(rec, MIC_N_SAMPLES, &st);
    int32_t raw_peak = audio_raw_peak();

    ESP_LOGI(TAG, "--- rezultat ---");
    ESP_LOGI(TAG, "rms=%.1f (%.1f dBFS)  peak=%ld (%.1f dBFS)  dc=%.1f",
             st.rms, mic_dbfs(st.rms), (long)st.peak, mic_dbfs(st.peak), st.dc);
    ESP_LOGI(TAG, "clipped=%d  zeros=%d/%d  dropped=%lu",
             st.clipped, st.zeros, MIC_N_SAMPLES,
             (unsigned long)(audio_dropped_samples() - dropped_before));
    ESP_LOGI(TAG, "sirovi 32-bit peak=%ld -> zauzima %d od 31 bita (shift u audio_i2s.c je >>14)",
             (long)raw_peak, raw_peak > 0 ? (int)(log(fabs((double)raw_peak)) / log(2.0)) + 1 : 0);

    if (st.zeros == MIC_N_SAMPLES)
        ESP_LOGE(TAG, "SVE NULE — nema podataka sa SD linije (provjeri SD/GPIO6, L/R->GND, VDD)");
    else if (st.rms < 2.0)
        ESP_LOGW(TAG, "signal je jedva iznad nule — provjeri VDD i da li je L/R na GND");
    else if (st.clipped > 0)
        ESP_LOGW(TAG, "ima klipovanja (%d uzoraka) — signal preglasan ili je shift preslab",
                 st.clipped);

    asd_dump_pcm_block(rec, MIC_N_SAMPLES, AUDIO_SR);

    ESP_LOGI(TAG, "gotovo — na PC-u: python pc/tools/mic_capture.py");
    free(rec);
}
