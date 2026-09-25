/* Ulazna tacka firmvera. Mod se bira env varijablom pri `idf.py reconfigure`
 * (main/CMakeLists.txt): ASD_PSD_LIVE je finalni samostalni detektor, a
 * ASD_PSD_VERIFY, ASD_MIC_TEST i ASD_INA_TEST su pojedinacne provjere.
 *
 * Bez zastavice radi istorijski AE/TFLM tok, cuvan zbog E4 mjerenja:
 * [I2S capture, core 0] -> ring -> [core 1] log-mel -> AE int8 -> ocjena klipa.
 */
#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
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
#include "ina226_test.h"
#include "live_capture.h"
#include "live_adapt.h"
#include "psd_live.h"
#include "psd_verify.h"

static const char *TAG = "asd";

#define CLIP_SEC   10
#define HOPS_PER_CLIP (AUDIO_SR * CLIP_SEC / ASD_HOP)   /* 312 */
#define INA226_I2C_ADDRESS_MIN 0x40
#define INA226_I2C_ADDRESS_MAX 0x4F
#define I2C_PROBE_TIMEOUT_MS 100

static asd_stream_t stream;

static void probe_ina226(void) {
    i2c_master_bus_config_t bus_config = {
        .i2c_port = -1,
        .sda_io_num = PIN_I2C_SDA,
        .scl_io_num = PIN_I2C_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    i2c_master_bus_handle_t bus_handle;
    esp_err_t err = i2c_new_master_bus(&bus_config, &bus_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "INA226 I2C init nije uspio: %s", esp_err_to_name(err));
        return;
    }

    ESP_LOGI(TAG, "I2C idle: SDA=%d SCL=%d",
             gpio_get_level(PIN_I2C_SDA), gpio_get_level(PIN_I2C_SCL));
    int found_address = -1;
    for (uint16_t address = INA226_I2C_ADDRESS_MIN;
         address <= INA226_I2C_ADDRESS_MAX; address++) {
        err = i2c_master_probe(bus_handle, address, I2C_PROBE_TIMEOUT_MS);
        if (err == ESP_OK) {
            found_address = address;
            break;
        }
    }
    ESP_LOGI(TAG, "I2C poslije probe: SDA=%d SCL=%d",
             gpio_get_level(PIN_I2C_SDA), gpio_get_level(PIN_I2C_SCL));
    if (found_address >= 0) {
        ESP_LOGI(TAG, "INA226 OK na 0x%02X (SDA GPIO %d, SCL GPIO %d)",
                 found_address, PIN_I2C_SDA, PIN_I2C_SCL);
    } else {
        ESP_LOGE(TAG, "INA226 nije pronadjen na adresama 0x%02X-0x%02X",
                 INA226_I2C_ADDRESS_MIN, INA226_I2C_ADDRESS_MAX);
    }
    ESP_ERROR_CHECK(i2c_del_master_bus(bus_handle));
}

static void process_clip(void) {
    static int16_t pcm[ASD_HOP];
    static float hop_f32[ASD_HOP];
    static float vec[ASD_INPUT_DIM];

    int64_t t_feat = 0, t_inf = 0;
    uint64_t abs_sum = 0;
    int32_t audio_peak = 0;
    uint32_t zero_samples = 0;
    float score_sum = 0.0f;
    int n_vec = 0;

    int64_t t0 = esp_timer_get_time();
    asd_stream_reset(&stream);

    for (int h = 0; h < HOPS_PER_CLIP; h++) {
        audio_read(pcm, ASD_HOP);
        for (int i = 0; i < ASD_HOP; i++) {
            int32_t sample = pcm[i];
            int32_t magnitude = sample < 0 ? -sample : sample;
            abs_sum += (uint32_t)magnitude;
            if (magnitude > audio_peak) audio_peak = magnitude;
            if (sample == 0) zero_samples++;
            hop_f32[i] = (float)pcm[i] / 32768.0f;
        }

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

    const uint32_t sample_count = HOPS_PER_CLIP * ASD_HOP;
    float mean_abs = (float)abs_sum / (float)sample_count;
    float zero_pct = 100.0f * (float)zero_samples / (float)sample_count;
    ESP_LOGI(TAG, "score=%.5f thr=%.5f %s | feat=%lld ms inf=%lld ms total=%lld ms "
             "(%d vec) dropped=%lu | audio peak=%ld mean_abs=%.1f zero=%.1f%%",
             score, (float)ASD_SCORE_THRESHOLD, anomaly ? "ANOMALIJA" : "normal",
             t_feat / 1000, t_inf / 1000, t_total / 1000,
             n_vec, (unsigned long)audio_dropped_samples(),
             (long)audio_peak, mean_abs, zero_pct);
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

    /* INA226 bring-up (E5): samo I2C, bez audia i modela — set ASD_INA_TEST=1 */
#ifdef ASD_INA_TEST
    ina226_test_run();
    while (1) vTaskDelay(portMAX_DELAY);
#endif

    probe_ina226();

    /* Mic bring-up (rizik C1): samo I2S, bez modela — set ASD_MIC_TEST=1 */
#ifdef ASD_MIC_TEST
    ESP_ERROR_CHECK(audio_i2s_init());
    ESP_ERROR_CHECK(audio_i2s_start());
    mic_test_run();
    while (1) vTaskDelay(portMAX_DELAY);
#endif

    /* Samostalni PSD detektor (finalni model) — set ASD_PSD_LIVE=1.
     * Stoji PRIJE tflm_init jer ovaj tok ne koristi neuronsku mrezu: nema
     * TFLM arene ni modela u RAM-u, samo matrica 96x96 iz fleša. */
#if defined(ASD_PSD_LIVE) || defined(ASD_PSD_VERIFY)
    ESP_ERROR_CHECK(audio_i2s_init());
    ESP_ERROR_CHECK(audio_i2s_start());
#ifdef ASD_PSD_VERIFY
    psd_verify_run();
#else
    psd_live_run();
#endif
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

    /* Jedan živi klip + score + snimak na PC — set ASD_LIVE_CAPTURE=1 */
#ifdef ASD_LIVE_CAPTURE
    live_capture_run();
    while (1) vTaskDelay(portMAX_DELAY);
#endif

    /* Prilagođavanje praga stvarnom okruženju — set ASD_LIVE_ADAPT=1 */
#ifdef ASD_LIVE_ADAPT
    live_adapt_run();
    while (1) vTaskDelay(portMAX_DELAY);
#endif

    ESP_LOGI(TAG, "start — klip %d s (%d hopova), prag %.5f",
             CLIP_SEC, HOPS_PER_CLIP, (float)ASD_SCORE_THRESHOLD);

    while (1) {
        process_clip();
        vTaskDelay(1); /* watchdog (rizik C6) */
    }
}
