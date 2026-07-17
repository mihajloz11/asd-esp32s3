/* ASD na ESP32-S3 — glavna petlja (plan 5.2):
 * [I2S capture task, core 0] -> ring buffer (PSRAM)
 * [main/inference, core 1]  -> log-mel -> AE int8 (TFLM) -> score -> prag -> LED
 *
 * Mjerni hooks: esp_timer_get_time() po fazi, ispis svakih N klipova (E4).
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

static const char *TAG = "asd";

#define CLIP_SEC       10
#define CLIP_SAMPLES   (AUDIO_SR * CLIP_SEC)
#define MAX_LM_FRAMES  (1 + (CLIP_SAMPLES - ASD_N_FFT) / ASD_HOP)  /* 312 */

/* Veliki baferi u PSRAM-u (16 MB na N32R16V) */
static float *clip_f32;   /* CLIP_SAMPLES */
static float *logmel_buf; /* MAX_LM_FRAMES x 128 */

static void process_clip(void) {
    static int16_t pcm[ASD_HOP];  /* čitamo u komadima */
    int64_t t0 = esp_timer_get_time();

    /* 1) capture: 10 s klipa iz ring buffera, konverzija u float [-1,1] */
    for (int off = 0; off < CLIP_SAMPLES; off += ASD_HOP) {
        size_t n = audio_read(pcm, ASD_HOP);
        for (size_t i = 0; i < n; i++)
            clip_f32[off + i] = (float)pcm[i] / 32768.0f;
    }
    int64_t t_cap = esp_timer_get_time();

    /* 2) featuring */
    int n_frames = asd_logmel(clip_f32, CLIP_SAMPLES, logmel_buf, MAX_LM_FRAMES);
    int64_t t_feat = esp_timer_get_time();

    /* 3) inferenca: score = mean MSE preko svih vektora klipa */
    static float vec[ASD_INPUT_DIM];
    float score_sum = 0.0f;
    int n_vec = n_frames - ASD_N_FRAMES + 1;
    for (int t = 0; t < n_vec; t++) {
        asd_make_vector(logmel_buf, t, asd_norm_mean, asd_norm_std, vec);
        score_sum += tflm_score_vector(vec);
    }
    float score = score_sum / (float)n_vec;
    int64_t t_inf = esp_timer_get_time();

    int anomaly = score > ASD_SCORE_THRESHOLD;
    gpio_set_level(PIN_LED, !anomaly);

    ESP_LOGI(TAG, "score=%.5f thr=%.5f %s | cap=%lld ms feat=%lld ms inf=%lld ms "
             "(%d vec) dropped=%lu",
             score, (float)ASD_SCORE_THRESHOLD, anomaly ? "ANOMALIJA" : "normal",
             (t_cap - t0) / 1000, (t_feat - t_cap) / 1000, (t_inf - t_feat) / 1000,
             n_vec, (unsigned long)audio_dropped_samples());
}

void app_main(void) {
    ESP_LOGI(TAG, "PSRAM: %u B", (unsigned)heap_caps_get_total_size(MALLOC_CAP_SPIRAM));

    gpio_config_t io = {.pin_bit_mask = 1ULL << PIN_LED, .mode = GPIO_MODE_OUTPUT};
    gpio_config(&io);

    clip_f32 = heap_caps_malloc(CLIP_SAMPLES * sizeof(float), MALLOC_CAP_SPIRAM);
    logmel_buf = heap_caps_malloc((size_t)MAX_LM_FRAMES * ASD_N_MELS * sizeof(float),
                                  MALLOC_CAP_SPIRAM);
    if (!clip_f32 || !logmel_buf) {
        ESP_LOGE(TAG, "PSRAM alloc failed — provjeri sdkconfig (SPIRAM_MODE_OCT)");
        return;
    }

    asd_features_init();
    if (tflm_init() != 0) {
        ESP_LOGE(TAG, "TFLM init failed");
        return;
    }
    ESP_LOGI(TAG, "TFLM arena used: %u B", (unsigned)tflm_arena_used());

    ESP_ERROR_CHECK(audio_i2s_init());
    ESP_ERROR_CHECK(audio_i2s_start());
    ESP_LOGI(TAG, "start — klip %d s, prag %.5f", CLIP_SEC, (float)ASD_SCORE_THRESHOLD);

    while (1) {
        process_clip();
        vTaskDelay(1); /* watchdog (rizik C6) */
    }
}
