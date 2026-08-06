/* ASD — glavna petlja, STREAMING arhitektura (radi na S3 i klasičnom ESP32):
 * [I2S capture task, core 0] -> ring buffer
 * [main loop, core 1] hop (512 uzoraka) -> log-mel frejm -> klizni vektor 640
 *                     -> AE int8 (TFLM) -> score -> agregacija po klipu -> LED
 *
 * RAM featuring puta: ~9 KB (asd_stream_t + vektor) — bez PSRAM zavisnosti;
 * PSRAM (ako postoji) koristi samo TFLM arena i audio ring buffer.
 * Mjerni hooks po fazi (E4): akumulirano vrijeme featuringa i inferencije po klipu.
 */
#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "esp_heap_caps.h"

#include "pins.h"
#include "audio_i2s.h"
#include "features_c.h"
#include "tflm_infer.h"
#include "calib_gamma.h"
#include "model_data.h"
#include "eval_mode.h"
#include "mic_test.h"

static const char *TAG = "asd";

#define CLIP_SEC   10
#define HOPS_PER_CLIP (AUDIO_SR * CLIP_SEC / ASD_HOP)   /* 312 */

static asd_stream_t stream;

static void process_clip(void) {
    static int16_t pcm[ASD_HOP];
    static float hop_f32[ASD_HOP];
    static float vec[ASD_INPUT_DIM];

    int64_t t_feat = 0, t_inf = 0;
    float score_sum = 0.0f;
    int n_vec = 0;

    int64_t t0 = esp_timer_get_time();
    asd_stream_reset(&stream);

    for (int h = 0; h < HOPS_PER_CLIP; h++) {
        audio_read(pcm, ASD_HOP);
        for (int i = 0; i < ASD_HOP; i++)
            hop_f32[i] = (float)pcm[i] / 32768.0f;

        int64_t a = esp_timer_get_time();
        int new_frame = asd_stream_push_hop(&stream, hop_f32);
        int64_t b = esp_timer_get_time();
        t_feat += b - a;

        if (new_frame && asd_stream_vector(&stream, asd_norm_mean, asd_norm_std, vec)) {
            int64_t c = esp_timer_get_time();
            score_sum += tflm_score_vector(vec);
            t_inf += esp_timer_get_time() - c;
            n_vec++;
        }
    }
    int64_t t_total = esp_timer_get_time() - t0;

    float score = score_sum / (float)n_vec;
    int anomaly = score > ASD_SCORE_THRESHOLD;
    gpio_set_level(PIN_LED, !anomaly);

    ESP_LOGI(TAG, "score=%.5f thr=%.5f %s | feat=%lld ms inf=%lld ms total=%lld ms "
             "(%d vec) dropped=%lu",
             score, (float)ASD_SCORE_THRESHOLD, anomaly ? "ANOMALIJA" : "normal",
             t_feat / 1000, t_inf / 1000, t_total / 1000,
             n_vec, (unsigned long)audio_dropped_samples());
}

void app_main(void) {
#if CONFIG_SPIRAM
    ESP_LOGI(TAG, "PSRAM: %u B", (unsigned)heap_caps_get_total_size(MALLOC_CAP_SPIRAM));
#else
    ESP_LOGI(TAG, "bez PSRAM-a (SRAM-only konfiguracija)");
#endif
    ESP_LOGI(TAG, "free heap: %u B", (unsigned)esp_get_free_heap_size());

    gpio_config_t io = {.pin_bit_mask = 1ULL << PIN_LED, .mode = GPIO_MODE_OUTPUT};
    gpio_config(&io);

    /* Mic bring-up (rizik C1): samo I2S, bez modela — set ASD_MIC_TEST=1 */
#ifdef ASD_MIC_TEST
    ESP_ERROR_CHECK(audio_i2s_init());
    ESP_ERROR_CHECK(audio_i2s_start());
    mic_test_run();
    while (1) vTaskDelay(portMAX_DELAY);
#endif

    asd_features_init();
    if (tflm_init() != 0) {
        ESP_LOGE(TAG, "TFLM init failed");
        return;
    }
    ESP_LOGI(TAG, "TFLM arena used: %u B", (unsigned)tflm_arena_used());

    /* Eval mod (E4): taster drzan pri bootu, ili build sa -DASD_EVAL_MODE */
    gpio_config_t btn = {.pin_bit_mask = 1ULL << PIN_BUTTON,
                         .mode = GPIO_MODE_INPUT, .pull_up_en = GPIO_PULLUP_ENABLE};
    gpio_config(&btn);
    vTaskDelay(pdMS_TO_TICKS(50));
#ifndef ASD_EVAL_MODE
    if (gpio_get_level(PIN_BUTTON) == 0)
#endif
    {
        ESP_LOGI(TAG, "ulazim u EVAL mod (klipovi sa flash particije)");
        eval_mode_run();
        ESP_LOGI(TAG, "eval zavrsen — restartuj bez tastera za zivi rad");
        while (1) vTaskDelay(portMAX_DELAY);
    }

    ESP_ERROR_CHECK(audio_i2s_init());
    ESP_ERROR_CHECK(audio_i2s_start());
    ESP_LOGI(TAG, "start — klip %d s (%d hopova), prag %.5f",
             CLIP_SEC, HOPS_PER_CLIP, (float)ASD_SCORE_THRESHOLD);

    while (1) {
        process_clip();
        vTaskDelay(1); /* watchdog (rizik C6) */
    }
}
