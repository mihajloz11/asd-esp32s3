/* Vidi psd_live.h. */
#include "psd_live.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_log.h"

#include "pins.h"
#include "audio_i2s.h"
#include "psd_features_c.h"
#include "psd_model_data.h"

static const char *TAG = "psdlive";

#define DIM            ASD_PSD_MODEL_DIM        /* 96 */
#define HOP            ASD_PSD_HOP              /* 4096 uzoraka = 256 ms */
#define HOPS_PER_CLIP  39                       /* 39 x 4096 = 159 744 ~ 10 s */
#define N_CAL          10                       /* 10 x 10 s = 100 s; PC AUC 0,853 */
#define WARM_HOPS      60                       /* ~15 s da se pusti ventilator */
#define LEVEL_FLOOR    -60.0f                   /* dBFS ispod ovoga = tisina */

/* PRAG. Polazno pravilo je bio 90. percentil leave-one-out score-ova
 * kalibracije (izmjereno na PC-u: odziv 64 %, lazni alarmi 12,7 % po prozoru).
 * Zivo mjerenje 09.08. je pokazalo da je taj prag SISTEMATSKI PRENIZAK:
 * kalibracioni klipovi su snimljeni jedan za drugim, u istim uslovima, pa LOO
 * potcjenjuje koliko normalan rad varira KASNIJE. Izmjereno u prolazu 2:
 * LOO sredina 1328 sd 894 -> prag 1667, a normalni prozori u detekciji su
 * dosezali 2414 i vise.
 *
 * Zato se uzima veca od dvije granice:
 *   p90 LOO            — empirijsko pravilo sa PC-a
 *   sredina + K*sd     — margina za varijaciju koju LOO ne vidi
 * i alarm i dalje trazi N_CONSEC uzastopnih prozora (kvar je trajan, spoljna
 * buka nije). Vidi docs/hardver-verifikacija.md. */
#define CAL_P_HI       0.90f
#define CAL_K_SIGMA    3.0f
#define N_CONSEC       3

static float cal_feat[N_CAL][DIM];
static float center[DIM];
static float feature[DIM];

/* Jedan klip od 10 s: snimanje i FFT se preklapaju (streaming), pa nema
 * bafera od 640 KB niti prekida u snimanju. Vraca dBFS nivo klipa. */
static float capture_clip(float *out_feature, int64_t *t_compute_us) {
    static int16_t pcm[HOP];
    static float hop[HOP];

    asd_psd_stream_reset();
    double energy = 0.0;
    int64_t t_comp = 0;

    for (int h = 0; h < HOPS_PER_CLIP; h++) {
        audio_read(pcm, HOP);
        for (int i = 0; i < HOP; i++) {
            hop[i] = (float)pcm[i] / 32768.0f;
            energy += (double)hop[i] * (double)hop[i];
        }
        int64_t a = esp_timer_get_time();
        asd_psd_stream_push_hop(hop);
        t_comp += esp_timer_get_time() - a;
    }

    int64_t a = esp_timer_get_time();
    int segments = asd_psd_stream_finish(out_feature);
    t_comp += esp_timer_get_time() - a;

    if (t_compute_us) *t_compute_us = t_comp;
    if (segments != 38)
        ESP_LOGW(TAG, "ocekivano 38 Welch segmenata, dobijeno %d", segments);

    double rms = sqrt(energy / (double)(HOPS_PER_CLIP * HOP));
    return 20.0f * log10f((float)rms + 1e-12f);
}

static float score_with_center(const float *feat, const float *c) {
    return asd_psd_score(feat, asd_psd_norm_mean, asd_psd_norm_std,
                         asd_psd_precision, c, DIM);
}

static int cmp_float(const void *a, const void *b) {
    float x = *(const float *)a, y = *(const float *)b;
    return (x > y) - (x < y);
}

void psd_live_run(void) {
    asd_psd_init();

    ESP_LOGI(TAG, "=== SAMOSTALNI PSD DETEKTOR ===");
    /* Statusni ispis je namjerno ASCII (pouka P12): serijski tok cita PC alat
     * cija konzolna kodna stranica ne mora podrzavati nasa slova. */
    ESP_LOGI(TAG, "model: %d traka, matrica %dx%d iz flesa, naucen na 990 "
             "ispravnih ventilatora", DIM, DIM, DIM);
    ESP_LOGI(TAG, "1) pusti ventilator koji radi NORMALNO");
    ESP_LOGI(TAG, "2) kalibracija %d x 10 s = %d s - ne mijenjaj nista",
             N_CAL, N_CAL * 10);
    ESP_LOGI(TAG, "3) poslije toga izazovi kvar - uredjaj radi sam");

    /* --- 1) cekanje: operater pusta ventilator, provjerava se da mikrofon
     * stvarno nesto cuje (P3: konstantan score ne dokazuje da mikrofon radi) --- */
    static int16_t pcm[HOP];
    int loud = 0;
    for (int h = 0; h < WARM_HOPS; h++) {
        audio_read(pcm, HOP);
        double e = 0.0;
        for (int i = 0; i < HOP; i++) {
            float x = (float)pcm[i] / 32768.0f;
            e += (double)x * (double)x;
        }
        float db = 20.0f * log10f((float)sqrt(e / HOP) + 1e-12f);
        if (db > LEVEL_FLOOR) loud++;
        printf("WAIT %d/%d score=%.2f spread=0.000 nivo=%.1f dBFS %s\n",
               h + 1, WARM_HOPS, db, db,
               db > LEVEL_FLOOR ? "cujem" : "tiho");
    }
    if (loud < WARM_HOPS / 2)
        ESP_LOGW(TAG, "mikrofon vecinu vremena nije cuo nista (%d/%d iznad %.0f dBFS) "
                 "— kalibrisem svejedno, ali provjeri da ventilator radi",
                 loud, WARM_HOPS, (double)LEVEL_FLOOR);

    /* --- 2) kalibracija: centar novog primjerka. Matrica se NE dira. --- */
    ESP_LOGI(TAG, "--- KALIBRACIJA: %d klipova po 10 s ---", N_CAL);
    int64_t t_comp = 0, t_comp_sum = 0;
    for (int i = 0; i < N_CAL; i++) {
        float db = capture_clip(cal_feat[i], &t_comp);
        t_comp_sum += t_comp;
        printf("CAL %2d/%d score=0.00000 nivo=%.1f dBFS racun=%lld ms\n",
               i + 1, N_CAL, db, t_comp / 1000);
    }

    for (int d = 0; d < DIM; d++) {
        float s = 0.0f;
        for (int i = 0; i < N_CAL; i++)
            s += (cal_feat[i][d] - asd_psd_norm_mean[d]) / asd_psd_norm_std[d];
        center[d] = s / (float)N_CAL;
    }

    /* Leave-one-out: klip se ocjenjuje centrom koji NE sadrzi njega samog.
     * Bez toga je prag optimisticki jer je klip ucestvovao u svom centru. */
    float loo[N_CAL];
    for (int i = 0; i < N_CAL; i++) {
        float c[DIM];
        for (int d = 0; d < DIM; d++) {
            float zi = (cal_feat[i][d] - asd_psd_norm_mean[d]) / asd_psd_norm_std[d];
            c[d] = (center[d] * (float)N_CAL - zi) / (float)(N_CAL - 1);
        }
        loo[i] = score_with_center(cal_feat[i], c);
    }

    float sorted[N_CAL];
    memcpy(sorted, loo, sizeof(sorted));
    qsort(sorted, N_CAL, sizeof(float), cmp_float);

    float sum = 0.0f;
    for (int i = 0; i < N_CAL; i++) sum += loo[i];
    float mean = sum / N_CAL;
    float var = 0.0f;
    for (int i = 0; i < N_CAL; i++) var += (loo[i] - mean) * (loo[i] - mean);
    float sd = sqrtf(var / (N_CAL - 1));

    /* linearna interpolacija percentila (isto sto numpy.percentile radi) */
    float pos = CAL_P_HI * (N_CAL - 1);
    int lo_i = (int)pos;
    int hi_i = lo_i + 1 < N_CAL ? lo_i + 1 : N_CAL - 1;
    float thr_p = sorted[lo_i] + (pos - lo_i) * (sorted[hi_i] - sorted[lo_i]);
    float thr_s = mean + CAL_K_SIGMA * sd;
    float thr = thr_p > thr_s ? thr_p : thr_s;

    ESP_LOGI(TAG, "--- kalibracija gotova (centar zamrznut) ---");
    ESP_LOGI(TAG, "LOO score: mean=%.2f sd=%.2f min=%.2f max=%.2f",
             mean, sd, sorted[0], sorted[N_CAL - 1]);
    printf("LOOALL");
    for (int i = 0; i < N_CAL; i++) printf(" %.3f", loo[i]);
    printf("\n");
    ESP_LOGI(TAG, "PRAG = %.2f (p%.0f dao %.2f, sredina+%.0fsd dao %.2f), "
             "alarm poslije %d uzastopna prozora",
             thr, CAL_P_HI * 100.0f, thr_p, CAL_K_SIGMA, thr_s, N_CONSEC);
    printf("ADAPTTHR n=%d mean=%.6f sd=%.6f k=0 theta=0 p=%.4f thr=%.6f lo=0.000000 "
           "factory=0.000000\n", N_CAL, mean, sd, CAL_P_HI, thr);
    ESP_LOGI(TAG, "racun po klipu: %lld ms (rezerva %.1fx), dropped=%lu",
             t_comp_sum / N_CAL / 1000,
             10000.0 / ((double)(t_comp_sum / N_CAL) / 1000.0),
             (unsigned long)audio_dropped_samples());

    /* --- 3) detekcija: uredjaj je od sada samostalan. Centar se NE pomjera
     * automatski (P10: tiha rekalibracija bi naucila kvar kao normalu). --- */
    ESP_LOGI(TAG, "--- DETEKCIJA RADI. Sada izazovi kvar. ---");
    ESP_LOGI(TAG, "LED (GPIO%d) svijetli = normalno, gasi se = ALARM", PIN_LED);

    int i = 0, run = 0, n_alarm = 0;
    while (1) {
        float db = capture_clip(feature, &t_comp);
        float s = score_with_center(feature, center);
        int over = s > thr;
        run = over ? run + 1 : 0;
        int alarm = run >= N_CONSEC;
        n_alarm += alarm;
        i++;

        gpio_set_level(PIN_LED, !alarm);

        printf("DET %d score=%.5f lo=0.00000 hi=%.5f led=%d anom=%d total_anom=%d "
               "%s (uzastopnih=%d nivo=%.1f dBFS racun=%lld ms)\n",
               i, s, thr, !alarm, alarm, n_alarm,
               alarm ? "ALARM" : (over ? "iznad praga" : "normal"),
               run, db, t_comp / 1000);
        vTaskDelay(1); /* watchdog (rizik C6) */
    }
}
