/* Vidi live_capture.h. */
#include "live_capture.h"
#include "mic_test.h"          /* asd_dump_pcm_block */

#include <stdio.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "esp_log.h"

#include "audio_i2s.h"
#include "features_c.h"
#include "tflm_infer.h"
#include "model_data.h"

static const char *TAG = "livecap";

#define LIVE_SEC        10
#define LIVE_N_SAMPLES  (AUDIO_SR * LIVE_SEC)
#define LIVE_WARMUP     (AUDIO_SR / 2)

/* Bodovanje iz bafera — namjerno ISTI redoslijed operacija kao process_clip()
 * u app_main.c (hop po hop kroz streaming API), da poređenje sa živim radom
 * ne zavisi od načina na koji su uzorci stigli. */
static float score_buffer(const int16_t *pcm, size_t n,
                          int64_t *t_feat, int64_t *t_inf, int *n_vec_out) {
    static asd_stream_t st;
    static float hop_f32[ASD_HOP];
    static float vec[ASD_INPUT_DIM];

    asd_stream_reset(&st);
    float sum = 0.0f;
    int n_vec = 0;
    *t_feat = 0;
    *t_inf = 0;

    for (size_t off = 0; off + ASD_HOP <= n; off += ASD_HOP) {
        for (int i = 0; i < ASD_HOP; i++)
            hop_f32[i] = (float)pcm[off + i] / 32768.0f;

        int64_t a = esp_timer_get_time();
        int new_frame = asd_stream_push_hop(&st, hop_f32);
        *t_feat += esp_timer_get_time() - a;

        if (new_frame && asd_stream_vector(&st, asd_norm_mean, asd_norm_std, vec)) {
            int64_t c = esp_timer_get_time();
            sum += tflm_score_vector(vec);
            *t_inf += esp_timer_get_time() - c;
            n_vec++;
        }
    }
    *n_vec_out = n_vec;
    return n_vec ? sum / (float)n_vec : 0.0f;
}

void live_capture_run(void) {
    static int16_t chunk[AUDIO_SR / 4];

    ESP_LOGI(TAG, "=== ZIVI KLIP + SCORE + SNIMAK ===");

    int16_t *buf = heap_caps_malloc(LIVE_N_SAMPLES * sizeof(int16_t), MALLOC_CAP_SPIRAM);
    if (!buf) {
        ESP_LOGE(TAG, "nema PSRAM-a za %d uzoraka", LIVE_N_SAMPLES);
        return;
    }

    for (int i = 0; i < LIVE_WARMUP / (AUDIO_SR / 4); i++)
        audio_read(chunk, AUDIO_SR / 4);

    ESP_LOGI(TAG, "snimam %d s...", LIVE_SEC);
    uint32_t dropped_before = audio_dropped_samples();
    for (int off = 0; off < LIVE_N_SAMPLES; off += AUDIO_SR / 4)
        audio_read(buf + off, AUDIO_SR / 4);
    uint32_t dropped = audio_dropped_samples() - dropped_before;

    int64_t t_feat = 0, t_inf = 0;
    int n_vec = 0;
    float score = score_buffer(buf, LIVE_N_SAMPLES, &t_feat, &t_inf, &n_vec);

    ESP_LOGI(TAG, "gotovo — score=%.6f prag=%.6f (%s)",
             score, (float)ASD_SCORE_THRESHOLD,
             score > ASD_SCORE_THRESHOLD ? "ANOMALIJA" : "normal");

    /* Mašinski čitljiva linija za pc/tools/live_compare.py */
    printf("LIVESCORE score=%.8f thr=%.8f n_vec=%d feat_ms=%lld inf_ms=%lld dropped=%lu\n",
           score, (float)ASD_SCORE_THRESHOLD, n_vec,
           t_feat / 1000, t_inf / 1000, (unsigned long)dropped);

    asd_dump_pcm_block(buf, LIVE_N_SAMPLES, AUDIO_SR);

    ESP_LOGI(TAG, "snimak poslat — PC: python tools/live_compare.py");
    free(buf);
}
