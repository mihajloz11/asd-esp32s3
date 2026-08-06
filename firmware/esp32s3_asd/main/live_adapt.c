/* Vidi live_adapt.h. */
#include "live_adapt.h"

#include <math.h>
#include <stdio.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_log.h"

#include "pins.h"
#include "audio_i2s.h"
#include "features_c.h"
#include "tflm_infer.h"
#include "calib_gamma.h"
#include "model_data.h"

static const char *TAG = "adapt";

/* Prozor od 2 s umjesto 10 s: kalibracija traži dovoljno uzoraka za procjenu
 * raspodjele, a 30 x 10 s = 5 minuta je predugo za demo. 2 s daje ~59 vektora
 * po prozoru — score je nešto šumniji, ali raspodjela se fituje 5x brže. */
#define WIN_SEC        2
#define HOPS_PER_WIN   (AUDIO_SR * WIN_SEC / ASD_HOP)
#define N_CALIB        30                  /* 30 x 2 s = 60 s kalibracije */
#define CALIB_P        0.99f               /* percentil normalnog rada */
#define N_DETECT       30                  /* 60 s detekcije poslije toga */

static asd_stream_t stream;

static float score_window(void) {
    static int16_t pcm[ASD_HOP];
    static float hop[ASD_HOP];
    static float vec[ASD_INPUT_DIM];

    asd_stream_reset(&stream);
    float sum = 0.0f;
    int n = 0;

    for (int h = 0; h < HOPS_PER_WIN; h++) {
        audio_read(pcm, ASD_HOP);
        for (int i = 0; i < ASD_HOP; i++)
            hop[i] = (float)pcm[i] / 32768.0f;

        if (asd_stream_push_hop(&stream, hop) &&
            asd_stream_vector(&stream, asd_norm_mean, asd_norm_std, vec)) {
            sum += tflm_score_vector(vec);
            n++;
        }
    }
    return n ? sum / (float)n : 0.0f;
}

void live_adapt_run(void) {
    gamma_calib_t cal;
    gamma_calib_reset(&cal);

    ESP_LOGI(TAG, "=== PRILAGODJAVANJE PRAGA ZIVOM OKRUZENJU ===");
    ESP_LOGI(TAG, "fabricki prag (iz DCASE trening podataka): %.5f",
             (float)ASD_SCORE_THRESHOLD);
    ESP_LOGI(TAG, "kalibracija: %d prozora po %d s = %d s. NE PRAVI BUKU.",
             N_CALIB, WIN_SEC, N_CALIB * WIN_SEC);

    float smin = 1e30f, smax = -1e30f;
    for (int i = 0; i < N_CALIB; i++) {
        float s = score_window();
        gamma_calib_add(&cal, s);
        if (s < smin) smin = s;
        if (s > smax) smax = s;
        printf("CAL %2d/%d  score=%.5f\n", i + 1, N_CALIB, s);
    }

    double var = cal.m2 / (cal.n - 1);
    double sd = sqrt(var);
    /* Momentna procjena gamma parametara (isto što calib_gamma radi interno) */
    double k = (cal.mean * cal.mean) / var;
    double theta = var / cal.mean;

    float thr = gamma_calib_threshold(&cal, CALIB_P);

    ESP_LOGI(TAG, "--- kalibracija gotova ---");
    ESP_LOGI(TAG, "n=%d  mean=%.5f  sd=%.5f  min=%.5f  max=%.5f",
             cal.n, cal.mean, sd, smin, smax);
    ESP_LOGI(TAG, "gamma fit: k=%.4f theta=%.5f", k, theta);
    ESP_LOGI(TAG, "NOVI PRAG (p=%.2f): %.5f   [fabricki je bio %.5f]",
             CALIB_P, thr, (float)ASD_SCORE_THRESHOLD);
    printf("ADAPTTHR n=%d mean=%.6f sd=%.6f k=%.6f theta=%.6f p=%.4f thr=%.6f factory=%.6f\n",
           cal.n, cal.mean, sd, k, theta, CALIB_P, thr, (float)ASD_SCORE_THRESHOLD);

    if (thr <= 0.0f) {
        ESP_LOGE(TAG, "kalibracija nije uspjela (premala varijansa?)");
        return;
    }

    ESP_LOGI(TAG, "--- detekcija sa novim pragom, %d s: sad pravi buku ---",
             N_DETECT * WIN_SEC);
    ESP_LOGI(TAG, "LED (GPIO%d) svijetli = normalno, gasi se = anomalija", PIN_LED);

    int n_anom = 0;
    for (int i = 0; i < N_DETECT; i++) {
        float s = score_window();
        int anom = s > thr;
        n_anom += anom;
        gpio_set_level(PIN_LED, !anom);
        printf("DET %2d/%d  score=%.5f thr=%.5f  %s\n",
               i + 1, N_DETECT, s, thr, anom ? "ANOMALIJA" : "normal");
    }

    ESP_LOGI(TAG, "gotovo: %d/%d prozora oznaceno kao anomalija (ocekivano ~%.0f%% "
                  "na mirnom okruzenju)", n_anom, N_DETECT, (1.0f - CALIB_P) * 100.0f);
}
