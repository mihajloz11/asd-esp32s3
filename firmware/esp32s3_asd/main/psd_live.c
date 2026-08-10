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
#include "audio_quality_state.h"
#include "psd_features_c.h"
#include "psd_model_data.h"

static const char *TAG = "psdlive";

#define DIM            ASD_PSD_MODEL_DIM        /* 96 */
#define HOP            ASD_PSD_HOP              /* 4096 uzoraka = 256 ms */
#define HOPS_PER_CLIP  39                       /* 39 x 4096 = 159 744 ~ 10 s */
#define N_CAL          10                       /* 10 x 10 s = 100 s; PC AUC 0,853 */
#define WARM_HOPS      60                       /* ~15 s da se pusti ventilator */

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
#define SCORE_NEGATIVE_TOL 1.0e-3f

static float cal_feat[N_CAL][DIM];
static float center[DIM];
static float feature[DIM];
static asd_quality_policy_t quality_policy;

static void emit_state(asd_state_t from, asd_state_t to, const char *reason) {
    printf("STATE protocol=%s from=%s to=%s reason=%s\n",
           ASD_QUALITY_PROTOCOL, asd_state_name(from), asd_state_name(to), reason);
}

static void emit_event(const char *type, asd_state_t state,
                       const char *phase, const char *reason) {
    printf("EVENT protocol=%s type=%s state=%s phase=%s reason=%s\n",
           ASD_QUALITY_PROTOCOL, type, asd_state_name(state), phase, reason);
}

static void emit_quality(const char *phase, int index, int total,
                         const asd_quality_metrics_t *m,
                         asd_quality_reason_t reason, int feature_valid,
                         float tonalness_proxy) {
    /* UART schema requires finite numerics even on a rejected fixture.  The
     * result token carries the fault; unavailable diagnostics use explicit,
     * finite sentinels and a not_computed gate. */
    float serial_rms = isfinite(m->rms_dbfs) ? m->rms_dbfs : -999.0f;
    float serial_dc = isfinite(m->dc) ? m->dc : 0.0f;
    int metrics_valid = isfinite(m->rms_dbfs) && isfinite(m->rms) && isfinite(m->dc);
    int tonal_computed = isfinite(tonalness_proxy);
    float serial_tonalness = tonal_computed ? tonalness_proxy : 0.0f;
    printf("QUALITY protocol=%s phase=%s index=%d total=%d result=%s "
           "metrics_valid=%d samples=%lu expected=%lu rms_dbfs=%.3f dc=%.3f peak=%ld "
           "clipped=%lu zeros=%lu stuck=%lu dropped_delta=%lu "
           "feature_valid=%d tonalness_valid=%d tonalness_proxy=%.6f tonal_gate=%s\n",
           ASD_QUALITY_PROTOCOL, phase, index, total,
           asd_quality_reason_name(reason),
           metrics_valid,
           (unsigned long)m->sample_count, (unsigned long)m->expected_samples,
           (double)serial_rms, (double)serial_dc, (long)m->peak,
           (unsigned long)m->clipped_count, (unsigned long)m->zero_count,
           (unsigned long)m->stuck_count, (unsigned long)m->dropped_delta,
           feature_valid,
           tonal_computed,
           (double)serial_tonalness,
           tonal_computed ? "pending_normal_only" : "not_computed");
}

static void stop_flow(const char *phase_name, asd_quality_phase_t phase,
                      asd_state_t from,
                      asd_quality_reason_t reason) {
    asd_state_t to = asd_quality_reject_state(reason, phase);
    gpio_set_level(PIN_LED, 0);
    emit_state(from, to, asd_quality_reason_name(reason));
    emit_event("FLOW_STOPPED", to, phase_name, asd_quality_reason_name(reason));
    ESP_LOGE(TAG, "fail-closed stop u %s: %s -> %s", phase_name,
             asd_quality_reason_name(reason), asd_state_name(to));
}

static float feature_tonalness_proxy(const float *feat) {
    /* Peak prominence in the mean-centred log-PSD shape.  It is logged only;
     * no threshold exists until a normal-only preregistration run. */
    float maximum = feat[0];
    for (int i = 1; i < DIM; i++)
        if (feat[i] > maximum) maximum = feat[i];
    return maximum;
}

/* Mahalanobis score and the centred tonalness proxy are theoretically
 * non-negative.  Binary32 accumulation may produce a tiny negative residue;
 * clamp only that explicit numerical tolerance and reject anything larger. */
static int clamp_nonnegative_score(float *value) {
    if (!value || !isfinite(*value) || *value < -SCORE_NEGATIVE_TOL)
        return 0;
    if (*value < 0.0f) *value = 0.0f;
    return 1;
}

/* Jedan klip od 10 s: snimanje i FFT se preklapaju (streaming), pa nema
 * bafera od 640 KB niti prekida u snimanju. Quality se akumulira iz istih PCM
 * uzoraka; short read se nikad ne dopunjava nulama niti salje u PSD. */
static asd_quality_reason_t capture_clip(float *out_feature,
                                         int64_t *t_compute_us,
                                         asd_quality_metrics_t *quality,
                                         int *feature_valid) {
    static int16_t pcm[HOP];
    static float hop[HOP];

    if (feature_valid) *feature_valid = 0;

    asd_psd_stream_reset();
    int64_t t_comp = 0;
    uint32_t dropped_before = audio_dropped_samples();
    asd_quality_accumulator_t acc;
    asd_quality_reset(&acc, HOPS_PER_CLIP * HOP, dropped_before, &quality_policy);

    for (int h = 0; h < HOPS_PER_CLIP; h++) {
        size_t got = audio_read(pcm, HOP);
        asd_quality_add_pcm(&acc, pcm, got);
        if (got != HOP) {
            asd_quality_finish(&acc, audio_dropped_samples(), quality);
            if (t_compute_us) *t_compute_us = t_comp;
            return ASD_QUALITY_SHORT_READ;
        }
        for (int i = 0; i < HOP; i++) {
            hop[i] = (float)pcm[i] / 32768.0f;
        }
        int64_t a = esp_timer_get_time();
        asd_psd_stream_push_hop(hop);
        t_comp += esp_timer_get_time() - a;
    }

    int64_t a = esp_timer_get_time();
    int segments = asd_psd_stream_finish(out_feature);
    t_comp += esp_timer_get_time() - a;

    asd_quality_finish(&acc, audio_dropped_samples(), quality);
    if (t_compute_us) *t_compute_us = t_comp;
    asd_quality_reason_t reason = asd_quality_evaluate(quality, &quality_policy);
    if (reason != ASD_QUALITY_OK) return reason;
    if (segments != 38 || !asd_quality_floats_finite(out_feature, DIM))
        return ASD_QUALITY_NONFINITE;
    if (feature_valid) *feature_valid = 1;
    return ASD_QUALITY_OK;
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
    quality_policy = asd_quality_default_policy();
    asd_state_t state = ASD_STATE_NO_MACHINE;

    ESP_LOGI(TAG, "=== SAMOSTALNI PSD DETEKTOR ===");
    /* Statusni ispis je namjerno ASCII (pouka P12): serijski tok cita PC alat
     * cija konzolna kodna stranica ne mora podrzavati nasa slova. */
    ESP_LOGI(TAG, "model: %d traka, matrica %dx%d iz flesa, naucen na 990 "
             "ispravnih ventilatora", DIM, DIM, DIM);
    ESP_LOGI(TAG, "1) pusti ventilator koji radi NORMALNO");
    ESP_LOGI(TAG, "2) kalibracija %d x 10 s = %d s - ne mijenjaj nista",
             N_CAL, N_CAL * 10);
    ESP_LOGI(TAG, "3) poslije toga izazovi kvar - uredjaj radi sam");
    emit_state(state, state, "BOOT_FAIL_CLOSED");

    /* --- 1) cekanje: operater pusta ventilator, provjerava se da mikrofon
     * stvarno nesto cuje (P3: konstantan score ne dokazuje da mikrofon radi) --- */
    static int16_t pcm[HOP];
    int loud = 0;
    for (int h = 0; h < WARM_HOPS; h++) {
        asd_quality_accumulator_t acc;
        asd_quality_metrics_t metrics;
        asd_quality_reset(&acc, HOP, audio_dropped_samples(), &quality_policy);
        size_t got = audio_read(pcm, HOP);
        asd_quality_add_pcm(&acc, pcm, got);
        asd_quality_finish(&acc, audio_dropped_samples(), &metrics);
        asd_quality_reason_t reason = asd_quality_evaluate(&metrics, &quality_policy);
        emit_quality("WAIT", h + 1, WARM_HOPS, &metrics, reason, 0, NAN);
        if (reason == ASD_QUALITY_OK) loud++;
        printf("WAIT %d/%d score=%.2f spread=0.000 nivo=%.1f dBFS %s\n",
               h + 1, WARM_HOPS, metrics.rms_dbfs, metrics.rms_dbfs,
               reason == ASD_QUALITY_OK ? "cujem" : "nevalidno");
        /* LOW_LEVEL is allowed during the operator warm-up, but it never
         * counts as valid and the aggregate gate below must pass. */
        if (asd_quality_flow_action(reason, ASD_PHASE_WAIT) == ASD_FLOW_STOP) {
            stop_flow("WAIT", ASD_PHASE_WAIT, state, reason);
            return;
        }
    }
    if (loud < WARM_HOPS / 2) {
        ESP_LOGE(TAG, "WAIT odbijen: samo %d/%d validnih blokova iznad %.0f dBFS",
                 loud, WARM_HOPS, (double)quality_policy.level_floor_dbfs);
        stop_flow("WAIT", ASD_PHASE_WAIT, state, ASD_QUALITY_INSUFFICIENT_LEVEL);
        return;
    }

    /* --- 2) kalibracija: centar novog primjerka. Matrica se NE dira. --- */
    ESP_LOGI(TAG, "--- KALIBRACIJA: %d klipova po 10 s ---", N_CAL);
    int64_t t_comp = 0, t_comp_sum = 0;
    for (int i = 0; i < N_CAL; i++) {
        asd_quality_metrics_t metrics;
        int feature_valid = 0;
        asd_quality_reason_t reason = capture_clip(
            cal_feat[i], &t_comp, &metrics, &feature_valid);
        t_comp_sum += t_comp;
        float tonalness = reason == ASD_QUALITY_OK
            ? feature_tonalness_proxy(cal_feat[i]) : NAN;
        if (reason == ASD_QUALITY_OK && !clamp_nonnegative_score(&tonalness)) {
            reason = ASD_QUALITY_NONFINITE;
            feature_valid = 0;
            tonalness = NAN;
        }
        emit_quality("CAL", i + 1, N_CAL, &metrics, reason,
                     feature_valid, tonalness);
        printf("CAL %2d/%d score=0.00000 nivo=%.1f dBFS racun=%lld ms\n",
               i + 1, N_CAL, metrics.rms_dbfs, t_comp / 1000);
        if (asd_quality_flow_action(reason, ASD_PHASE_CAL) == ASD_FLOW_STOP) {
            stop_flow("CAL", ASD_PHASE_CAL, state, reason);
            return;
        }
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
        if (!clamp_nonnegative_score(&loo[i])) {
            stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_NONFINITE);
            return;
        }
    }
    if (!asd_quality_floats_finite(loo, N_CAL)) {
        stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_NONFINITE);
        return;
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
    if (!isfinite(mean) || !isfinite(sd)) {
        stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_NONFINITE);
        return;
    }
    float loo_cv = fabsf(mean) > 1e-12f ? sd / fabsf(mean) : 0.0f;
    printf("QUALITY protocol=%s phase=CAL_SUMMARY result=OBSERVED "
           "loo_mean=%.6f loo_sd=%.6f loo_cv=%.6f loo_range=%.6f "
           "loo_gate=pending_normal_only\n",
           ASD_QUALITY_PROTOCOL, mean, sd, loo_cv,
           sorted[N_CAL - 1] - sorted[0]);

    /* linearna interpolacija percentila (isto sto numpy.percentile radi) */
    float pos = CAL_P_HI * (N_CAL - 1);
    int lo_i = (int)pos;
    int hi_i = lo_i + 1 < N_CAL ? lo_i + 1 : N_CAL - 1;
    float thr_p = sorted[lo_i] + (pos - lo_i) * (sorted[hi_i] - sorted[lo_i]);
    float thr_s = mean + CAL_K_SIGMA * sd;
    float thr = thr_p > thr_s ? thr_p : thr_s;
    if (!isfinite(thr_p) || !isfinite(thr_s) || !isfinite(thr)) {
        stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_NONFINITE);
        return;
    }

    ESP_LOGI(TAG, "--- kalibracija gotova (centar zamrznut) ---");
    ESP_LOGI(TAG, "LOO score: mean=%.2f sd=%.2f min=%.2f max=%.2f",
             mean, sd, sorted[0], sorted[N_CAL - 1]);
    printf("LOOALL");
    for (int i = 0; i < N_CAL; i++) printf(" %.3f", loo[i]);
    printf("\n");
    ESP_LOGI(TAG, "PRAG = %.2f (p%.0f dao %.2f, sredina+%.0fsd dao %.2f), "
             "alarm poslije %d uzastopna prozora",
             thr, CAL_P_HI * 100.0f, thr_p, CAL_K_SIGMA, thr_s, N_CONSEC);
    printf("ADAPTTHR n=%d mean=%.6f sd=%.6f k=0 theta=0 p=%.4f thr=%.9g lo=0.000000 "
           "factory=0.000000\n", N_CAL, mean, sd, CAL_P_HI, thr);
    ESP_LOGI(TAG, "racun po klipu: %lld ms (rezerva %.1fx), dropped=%lu",
             t_comp_sum / N_CAL / 1000,
             10000.0 / ((double)(t_comp_sum / N_CAL) / 1000.0),
             (unsigned long)audio_dropped_samples());
    emit_state(state, ASD_STATE_CALIBRATED_NORMAL, "CALIBRATION_ACCEPTED");
    state = ASD_STATE_CALIBRATED_NORMAL;
    emit_event("CALIBRATION_ACCEPTED", state, "CAL", "QUALITY_OK");

    /* --- 3) detekcija: uredjaj je od sada samostalan. Centar se NE pomjera
     * automatski (P10: tiha rekalibracija bi naucila kvar kao normalu). --- */
    ESP_LOGI(TAG, "--- DETEKCIJA RADI. Sada izazovi kvar. ---");
    ESP_LOGI(TAG, "LED (GPIO%d) svijetli = normalno, gasi se = ALARM", PIN_LED);

    int i = 0, run = 0, n_alarm = 0;
    while (1) {
        asd_quality_metrics_t metrics;
        int feature_valid = 0;
        asd_quality_reason_t reason = capture_clip(
            feature, &t_comp, &metrics, &feature_valid);
        float tonalness = reason == ASD_QUALITY_OK
            ? feature_tonalness_proxy(feature) : NAN;
        if (reason == ASD_QUALITY_OK && !clamp_nonnegative_score(&tonalness)) {
            reason = ASD_QUALITY_NONFINITE;
            feature_valid = 0;
            tonalness = NAN;
        }
        emit_quality("DET", i + 1, 0, &metrics, reason,
                     feature_valid, tonalness);
        if (asd_quality_flow_action(reason, ASD_PHASE_DET) == ASD_FLOW_STOP) {
            stop_flow("DET", ASD_PHASE_DET, state, reason);
            return;
        }
        float s = score_with_center(feature, center);
        if (!clamp_nonnegative_score(&s)) {
            stop_flow("DET", ASD_PHASE_DET, state, ASD_QUALITY_NONFINITE);
            return;
        }
        int over = s > thr;
        run = over ? run + 1 : 0;
        int alarm = run >= N_CONSEC;
        n_alarm += alarm;
        i++;

        gpio_set_level(PIN_LED, !alarm);

        /* 9 significant digits round-trip a binary32 value, so the host can
         * independently verify score > threshold without decimal ambiguity. */
        printf("DET %d score=%.9g lo=0 hi=%.9g led=%d anom=%d total_anom=%d "
               "%s (uzastopnih=%d nivo=%.1f dBFS racun=%lld ms)\n",
               i, s, thr, !alarm, alarm, n_alarm,
               alarm ? "ALARM" : (over ? "iznad praga" : "normal"),
               run, metrics.rms_dbfs, t_comp / 1000);

        /* DET consumes the immediately preceding QUALITY token.  State/event
         * transitions are emitted only after that pair is complete. */
        asd_state_t next_state = alarm ? ASD_STATE_ANOMALY : ASD_STATE_CALIBRATED_NORMAL;
        if (next_state != state) {
            emit_state(state, next_state, alarm ? "THRESHOLD_PERSISTENCE" : "ALARM_CLEARED");
            emit_event(alarm ? "ANOMALY_ENTERED" : "ANOMALY_CLEARED",
                       next_state, "DET", alarm ? "THRESHOLD_PERSISTENCE" : "ALARM_CLEARED");
            state = next_state;
        }
        vTaskDelay(1); /* watchdog (rizik C6) */
    }
}
