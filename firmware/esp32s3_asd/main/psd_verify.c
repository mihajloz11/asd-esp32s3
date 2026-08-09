/* Vidi psd_verify.h. */
#include "psd_verify.h"
#include "mic_test.h"          /* asd_dump_pcm_block */

#include <stdio.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "esp_log.h"

#include "audio_i2s.h"
#include "psd_features_c.h"

static const char *TAG = "psdver";

#define VER_SEC        10
#define VER_N_SAMPLES  (AUDIO_SR * VER_SEC)
#define VER_WARMUP     (AUDIO_SR / 2)

void psd_verify_run(void) {
    static int16_t chunk[AUDIO_SR / 4];
    static float hop[ASD_PSD_HOP];
    static float feature[ASD_PSD_BANDS];

    asd_psd_init();
    ESP_LOGI(TAG, "=== PSD PROVJERA NA ZIVOM MIKROFONU ===");

    int16_t *buf = heap_caps_malloc(VER_N_SAMPLES * sizeof(int16_t), MALLOC_CAP_SPIRAM);
    if (!buf) {
        ESP_LOGE(TAG, "nema PSRAM-a za %d uzoraka", VER_N_SAMPLES);
        return;
    }

    for (int i = 0; i < VER_WARMUP / (AUDIO_SR / 4); i++)
        audio_read(chunk, AUDIO_SR / 4);

    ESP_LOGI(TAG, "snimam %d s...", VER_SEC);
    uint32_t dropped_before = audio_dropped_samples();
    for (int off = 0; off < VER_N_SAMPLES; off += AUDIO_SR / 4)
        audio_read(buf + off, AUDIO_SR / 4);
    uint32_t dropped = audio_dropped_samples() - dropped_before;

    /* Isti redoslijed operacija kao zivi rad (streaming, hop po hop), da bi
     * poredjenje sa PC-om vrijedilo bas za tok koji radi u psd_live.c. */
    int64_t t0 = esp_timer_get_time();
    asd_psd_stream_reset();
    for (int off = 0; off + ASD_PSD_HOP <= VER_N_SAMPLES; off += ASD_PSD_HOP) {
        for (int i = 0; i < ASD_PSD_HOP; i++)
            hop[i] = (float)buf[off + i] / 32768.0f;
        asd_psd_stream_push_hop(hop);
    }
    int segments = asd_psd_stream_finish(feature);
    int64_t t_us = esp_timer_get_time() - t0;

    printf("PSDFEAT segments=%d compute_us=%lld dropped=%lu\n",
           segments, t_us, (unsigned long)dropped);
    printf("PSDVEC");
    for (int i = 0; i < ASD_PSD_BANDS; i++) printf(" %.8e", feature[i]);
    printf("\n");

    asd_dump_pcm_block(buf, VER_N_SAMPLES, AUDIO_SR);
    ESP_LOGI(TAG, "snimak poslat — PC: python tools/psd_verify_compare.py");
    free(buf);
}
