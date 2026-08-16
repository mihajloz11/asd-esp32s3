/* Vidi psd_live.h. */
#include "psd_live.h"

#include <math.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_log.h"

#include "pins.h"
#include "audio_i2s.h"
#include "audio_quality_state.h"
#include "asd_events.h"
#include "asd_cmd.h"
#include "asd_operator.h"
#include "asd_temporal.h"
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
 * i alarm i dalje trazi vise uzastopnih prozora (kvar je trajan, spoljna buka
 * nije). Broj uzastopnih prozora dolazi iz politike prisustva Faze 2, da postoji
 * samo jedno mjesto gdje se to pravilo mijenja. Vidi docs/hardver-verifikacija.md. */
#define CAL_P_HI       0.90f
#define CAL_K_SIGMA    3.0f
#define SCORE_NEGATIVE_TOL 1.0e-3f

/* Ucenje uvijek pokrece operater. Time uredjaj ne moze sam zapoceti
 * kalibraciju prije nego sto su ventilator i mikrofon spremni. */
#define UI_TICK_MS            20

static float cal_feat[N_CAL][DIM];
static float center[DIM];
static float feature[DIM];
static asd_quality_policy_t quality_policy;

/* Dijeljeno sa UI taskom. Task samo čita fazu/stanje i upisuje komandu; glavni
 * tok samo čita i briše komandu. */
static asd_button_t button;
static volatile asd_flow_stage_t ui_stage = ASD_STAGE_IDLE;
static volatile asd_state_t ui_state = ASD_STATE_NO_MACHINE;
static _Atomic int ui_command = ASD_UI_CMD_NONE;

static uint32_t now_ms(void) {
    return (uint32_t)(esp_timer_get_time() / 1000);
}

static void emit_state(asd_state_t from, asd_state_t to, const char *reason) {
    printf("STATE protocol=%s from=%s to=%s reason=%s\n",
           ASD_QUALITY_PROTOCOL, asd_state_name(from), asd_state_name(to), reason);
}

/* Od protokola v1.3.0 događaj nosi i semantiku Faze 2: `event` je najslabija
 * tvrdnja koju dokazi podnose, `capability` kaže šta bi tvrdnja tražila, a
 * `level` na kojem je nivou hijerarhije odluka donesena. */
static void emit_event(const char *type, asd_state_t state,
                       const char *phase, const char *reason,
                       asd_event_t event, asd_decision_level_t level) {
    printf("EVENT protocol=%s type=%s state=%s phase=%s reason=%s "
           "event=%s capability=%s level=%s\n",
           ASD_QUALITY_PROTOCOL, type, asd_state_name(state), phase, reason,
           asd_event_name(event),
           asd_capability_name(asd_event_capability(event)),
           asd_decision_level_name(level));
}

static void emit_session(const char *action, const char *source,
                         const char *reason, int discards_calibration) {
    printf("SESSION protocol=%s action=%s source=%s reason=%s "
           "discards_calibration=%d\n",
           ASD_QUALITY_PROTOCOL, action, source, reason, discards_calibration);
}

static void emit_button(asd_ui_mode_t mode, asd_button_event_t event,
                        asd_ui_command_t command) {
    printf("BUTTON protocol=%s event=%s mode=%s command=%s discards=%d\n",
           ASD_QUALITY_PROTOCOL, asd_button_event_name(event),
           asd_ui_mode_name(mode), asd_ui_command_name(command),
           asd_ui_command_discards_calibration(mode, command));
}

/* Softverski pandan lampicama. Obrazac zelene i crvene je čista funkcija
 * režima (`asd_indicator_level`/`asd_alarm_level`), pa se ovdje objavljuje sam
 * režim i imenovani obrazac — host onda crta istu lampicu koju bi vidio na
 * ploči, i kad nijedna dioda nije zalemljena.
 *
 * Emituje se SAMO na promjenu režima, ne na svaki treptaj: pet promjena po
 * sesiji umjesto deset redova u sekundi.
 *
 * Ime zapisa je namjerno izvan zaključanog rječnika `asd-quality-v1.3.0` —
 * host parser ga ne prepoznaje i preskače, pa red ne može ući u lanac
 * telemetrije koji odlučuje o valjanosti prolaza. Sva mjerodavna stanja i
 * dalje idu kroz `STATE`/`EVENT`. */
static const char *green_pattern(asd_ui_mode_t mode) {
    switch (mode) {
        case ASD_UI_IDLE:     return "flash_2s";
        case ASD_UI_LEARNING: return "blink_5hz";
        case ASD_UI_READY:    return "on";
        case ASD_UI_ALARM:    return "off";
        default:              return "double_blink";
    }
}

static void emit_flags(asd_ui_mode_t mode, asd_state_t state) {
    printf("FLAGS protocol=%s mode=%s state=%s waiting=%d learning=%d "
           "learned=%d anomaly=%d fault=%d green=%s red=%s\n",
           ASD_QUALITY_PROTOCOL, asd_ui_mode_name(mode), asd_state_name(state),
           mode == ASD_UI_IDLE, mode == ASD_UI_LEARNING,
           mode == ASD_UI_READY || mode == ASD_UI_ALARM,
           mode == ASD_UI_ALARM, mode == ASD_UI_FAULT,
           green_pattern(mode),
           mode == ASD_UI_ALARM ? "on"
                                : (mode == ASD_UI_FAULT ? "double_blink" : "off"));
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

/* Fail-closed stop iz Faze 1. Semantika događaja se ne izmišlja ovdje nego se
 * uzima iz `asd_events.c`, da WAIT/CAL i DET govore istim rječnikom. */
static asd_state_t stop_flow(const char *phase_name, asd_quality_phase_t phase,
                             asd_state_t from, asd_quality_reason_t reason) {
    asd_state_t to = asd_quality_reject_state(reason, phase);
    const char *name = asd_quality_reason_name(reason);
    ui_state = to;
    emit_state(from, to, name);
    emit_event("FLOW_STOPPED", to, phase_name, name,
               asd_event_for_quality_reject(reason),
               asd_level_for_quality_reject(reason));
    ESP_LOGE(TAG, "fail-closed stop u %s: %s -> %s", phase_name, name,
             asd_state_name(to));
    return to;
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

/* --- operaterski tok ------------------------------------------------------ */

/* Lampica i taster idu u zasebnom tasku, na 20 ms. Bez toga bi se obrazac
 * lampice osvježavao tek svakih 256 ms (koliko traje jedan audio blok), pa se
 * treperenje od 5 Hz ne bi ni vidjelo, a odskok tastera se ne bi mogao
 * odbounceovati. */
static void ui_task(void *arg) {
    (void)arg;
    int last_flags_mode = -1;
    uint32_t last_flags_at = 0;
    for (;;) {
        uint32_t t = now_ms();
        asd_state_t state = ui_state;
        asd_ui_mode_t mode = asd_ui_mode(ui_stage, state);
        gpio_set_level(PIN_LED, asd_indicator_level(mode, t));
        gpio_set_level(PIN_LED_ALARM, asd_alarm_level(mode, t));
        /* Na promjenu režima odmah, inače na 5 s. Ponavljanje postoji zbog
         * hosta koji se zakači usred sesije: bez njega bi panel čekao prvu
         * sljedeću promjenu da uopšte sazna šta lampica pokazuje. */
        if ((int)mode != last_flags_mode || (uint32_t)(t - last_flags_at) >= 5000u) {
            emit_flags(mode, state);
            last_flags_mode = (int)mode;
            last_flags_at = t;
        }
        /* Taster je na masu, sa unutrašnjim pull-upom: nizak nivo = pritisnut. */
        asd_button_event_t event =
            asd_button_update(&button, gpio_get_level(PIN_BUTTON) == 0, t);
        /* Virtuelni pritisak sa konzole ulazi ovdje, na istom mjestu gdje i pin,
         * i odatle dijeli cijeli put: `asd_ui_command`, `BUTTON` zapis i
         * `ui_command`. Fizički taster ima prednost — ako je stigao pravi
         * pritisak u istom ciklusu, virtuelni ostaje da čeka sljedeći. */
        if (event == ASD_BTN_NONE)
            event = asd_cmd_take_event();
        if (event != ASD_BTN_NONE) {
            asd_ui_command_t command = asd_ui_command(mode, event);
            emit_button(mode, event, command);
            if (command != ASD_UI_CMD_NONE)
                atomic_store(&ui_command, (int)command);
        }
        vTaskDelay(pdMS_TO_TICKS(UI_TICK_MS));
    }
}

static asd_ui_command_t take_command(void) {
    return (asd_ui_command_t)atomic_exchange(&ui_command, ASD_UI_CMD_NONE);
}

/* Ceka eksplicitnu operaterovu komandu; nema vremenskog autostarta. */
static void wait_for_start(asd_state_t state) {
    ui_stage = ASD_STAGE_IDLE;
    ui_state = state;
    take_command();                       /* odbaci komandu zaostalu iz ranije */
    ESP_LOGI(TAG, "pritisni taster (GPIO%d) ili posalji PRESS da pocne ucenje",
             PIN_BUTTON);
    for (;;) {
        if (take_command() == ASD_UI_CMD_START_LEARNING) return;
        vTaskDelay(pdMS_TO_TICKS(UI_TICK_MS));
    }
}

/* Postavlja se kad operater tokom nadzora dugim pritiskom traži novo učenje;
 * tada se sesija zatvara i odmah otvara nova, bez povratka u čekanje. */
static int relearn_requested;

/* 1 ako operater traži da se sesija u toku prekine. Dvije komande vode ovamo:
 * ABORT iz faze učenja i START_LEARNING iz nadzora. Obje se moraju POTROŠITI
 * ovdje — da se komanda ne izgubi, i da dug pritisak tokom nadzora zaista
 * pokrene novo učenje umjesto da bude progutan. */
static int session_interrupted(void) {
    asd_ui_command_t command = take_command();
    if (command == ASD_UI_CMD_START_LEARNING) {
        relearn_requested = 1;
        return 1;
    }
    return command == ASD_UI_CMD_ABORT;
}

/* --- snimanje ------------------------------------------------------------- */

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

/* --- jedna sesija: WAIT -> CAL -> DET -------------------------------------- */

/* Vraća stanje u kojem je sesija završila. Nikad se ne vraća sa validnom
 * kalibracijom „u vazduhu": svaki izlaz prolazi kroz stop_flow ili prekid. */
static asd_state_t run_session(void) {
    asd_state_t state = ASD_STATE_NO_MACHINE;
    asd_decision_ctx_t decision;
    asd_presence_policy_t presence = asd_presence_default_policy();
    asd_decision_init(&decision, &presence);
    asd_calibration_t calibration = {0, NAN, NAN};

    ui_stage = ASD_STAGE_LEARNING;
    ui_state = state;
    emit_state(state, state, "BOOT_FAIL_CLOSED");

    /* Baci sve sto se nakupilo dok je uredjaj cekao pritisak. Bez ovoga prvi
     * WAIT blok naslijedi `dropped` iz cijelog perioda cekanja i fail-closed
     * obori sesiju u SENSOR_ERROR. Vidi audio_flush() u audio_i2s.c. */
    size_t stale = audio_flush();
    if (stale)
        ESP_LOGI(TAG, "odbacen ustajali zvuk iz cekanja: %u uzoraka",
                 (unsigned)stale);

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
        if (asd_quality_flow_action(reason, ASD_PHASE_WAIT) == ASD_FLOW_STOP)
            return stop_flow("WAIT", ASD_PHASE_WAIT, state, reason);
        if (session_interrupted()) {
            emit_session("ABORTED", "BUTTON", "OPERATOR_LONG_PRESS", 0);
            ESP_LOGW(TAG, "operater prekinuo ucenje u fazi WAIT");
            return state;
        }
    }
    if (loud < WARM_HOPS / 2) {
        ESP_LOGE(TAG, "WAIT odbijen: samo %d/%d validnih blokova iznad %.0f dBFS",
                 loud, WARM_HOPS, (double)quality_policy.level_floor_dbfs);
        return stop_flow("WAIT", ASD_PHASE_WAIT, state,
                         ASD_QUALITY_INSUFFICIENT_LEVEL);
    }

    /* --- 2) kalibracija: centar novog primjerka. Matrica se NE dira. --- */
    ESP_LOGI(TAG, "--- KALIBRACIJA: %d klipova po 10 s ---", N_CAL);
    int64_t t_comp = 0, t_comp_sum = 0;
    /* Referentni nivo kalibrisane masine. Faza 2 iz njega izvodi test prisustva:
     * masina je prisutna dok je nivo iznad ove sredine minus margina. */
    float cal_level_sum = 0.0f;
    for (int i = 0; i < N_CAL; i++) {
        asd_quality_metrics_t metrics;
        int feature_valid = 0;
        asd_quality_reason_t reason = capture_clip(
            cal_feat[i], &t_comp, &metrics, &feature_valid);
        t_comp_sum += t_comp;
        cal_level_sum += metrics.rms_dbfs;
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
        if (asd_quality_flow_action(reason, ASD_PHASE_CAL) == ASD_FLOW_STOP)
            return stop_flow("CAL", ASD_PHASE_CAL, state, reason);
        if (session_interrupted()) {
            emit_session("ABORTED", "BUTTON", "OPERATOR_LONG_PRESS", 0);
            ESP_LOGW(TAG, "operater prekinuo ucenje u fazi CAL");
            return state;
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
        if (!clamp_nonnegative_score(&loo[i]))
            return stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_NONFINITE);
    }
    if (!asd_quality_floats_finite(loo, N_CAL))
        return stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_NONFINITE);

    float sorted[N_CAL];
    memcpy(sorted, loo, sizeof(sorted));
    qsort(sorted, N_CAL, sizeof(float), cmp_float);

    float sum = 0.0f;
    for (int i = 0; i < N_CAL; i++) sum += loo[i];
    float mean = sum / N_CAL;
    float var = 0.0f;
    for (int i = 0; i < N_CAL; i++) var += (loo[i] - mean) * (loo[i] - mean);
    float sd = sqrtf(var / (N_CAL - 1));
    if (!isfinite(mean) || !isfinite(sd))
        return stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_NONFINITE);
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
    if (!isfinite(thr_p) || !isfinite(thr_s) || !isfinite(thr))
        return stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_NONFINITE);

    float cal_level_mean = cal_level_sum / (float)N_CAL;
    if (!isfinite(cal_level_mean))
        return stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_NONFINITE);

    ESP_LOGI(TAG, "--- kalibracija gotova (centar zamrznut) ---");
    ESP_LOGI(TAG, "LOO score: mean=%.2f sd=%.2f min=%.2f max=%.2f",
             mean, sd, sorted[0], sorted[N_CAL - 1]);
    ESP_LOGI(TAG, "referentni nivo masine: %.2f dBFS (gate prisustva %.2f dBFS)",
             cal_level_mean, cal_level_mean - presence.absent_margin_db);
    printf("LOOALL");
    for (int i = 0; i < N_CAL; i++) printf(" %.3f", loo[i]);
    printf("\n");
    ESP_LOGI(TAG, "PRAG = %.2f (p%.0f dao %.2f, sredina+%.0fsd dao %.2f), "
             "alarm poslije %d uzastopna prozora, gasi se ispod %.2f",
             thr, CAL_P_HI * 100.0f, thr_p, CAL_K_SIGMA, thr_s,
             decision.temporal.policy.min_consecutive,
             thr * decision.temporal.policy.exit_scale);
    printf("ADAPTTHR n=%d mean=%.6f sd=%.6f k=0 theta=0 p=%.4f thr=%.9g lo=0.000000 "
           "factory=0.000000\n", N_CAL, mean, sd, CAL_P_HI, thr);
    ESP_LOGI(TAG, "racun po klipu: %lld ms (rezerva %.1fx), dropped=%lu",
             t_comp_sum / N_CAL / 1000,
             10000.0 / ((double)(t_comp_sum / N_CAL) / 1000.0),
             (unsigned long)audio_dropped_samples());
    /* Gate prisustva mora biti u serijskom toku, a ne samo u logu: bez njega
     * host ne moze NEZAVISNO ponoviti odluku Faze 2, nego bi morao vjerovati
     * firmveru. Isti razlog zbog kojeg se prag emituje kao ADAPTTHR. */
    printf("PRESENCE protocol=%s level_mean_dbfs=%.9g margin_db=%.9g "
           "gate_dbfs=%.9g min_consecutive=%d\n",
           ASD_QUALITY_PROTOCOL, cal_level_mean, presence.absent_margin_db,
           cal_level_mean - presence.absent_margin_db, presence.min_consecutive);
    /* Isti razlog kao za PRESENCE: bez objavljene vremenske politike host ne
     * moze ponoviti odluku o odstupanju, nego bi morao vjerovati firmveru. */
    asd_temporal_policy_t temporal = decision.temporal.policy;
    printf("TEMPORAL protocol=%s policy=%s min_consecutive=%d ewma_alpha=%.9g "
           "enter_scale=%.9g exit_scale=%.9g fast_scale=%.9g\n",
           ASD_QUALITY_PROTOCOL, ASD_TEMPORAL_POLICY, temporal.min_consecutive,
           temporal.ewma_alpha, temporal.enter_scale, temporal.exit_scale,
           temporal.fast_scale);

    /* Kalibracija je prihvaćena: od sada Faza 2 ima referentni nivo i prag, pa
     * `asd_decide()` može ocjenjivati i prisustvo i odstupanje. */
    calibration.valid = 1;
    calibration.level_mean_dbfs = cal_level_mean;
    calibration.score_threshold = thr;
    decision.state = ASD_STATE_CALIBRATED_NORMAL;

    emit_state(state, ASD_STATE_CALIBRATED_NORMAL, "CALIBRATION_ACCEPTED");
    state = ASD_STATE_CALIBRATED_NORMAL;
    ui_stage = ASD_STAGE_MONITORING;
    ui_state = state;
    emit_event("CALIBRATION_ACCEPTED", state, "CAL", "QUALITY_OK",
               ASD_EVENT_NONE, ASD_LEVEL_DEVIATION);
    ESP_LOGI(TAG, "LAMPICA STALNO SVIJETLI = ucenje gotovo, nadzirem");

    /* --- 3) detekcija: uredjaj je od sada samostalan. Centar se NE pomjera
     * automatski (P10: tiha rekalibracija bi naucila kvar kao normalu). --- */
    ESP_LOGI(TAG, "--- DETEKCIJA RADI. Sada izazovi kvar. ---");
    ESP_LOGI(TAG, "zelena LED (GPIO%d) svijetli = normalno; crvena (GPIO%d) = ALARM",
             PIN_LED, PIN_LED_ALARM);

    int i = 0, n_alarm = 0;
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
        if (asd_quality_flow_action(reason, ASD_PHASE_DET) == ASD_FLOW_STOP)
            return stop_flow("DET", ASD_PHASE_DET, state, reason);

        float s = score_with_center(feature, center);
        if (!clamp_nonnegative_score(&s))
            return stop_flow("DET", ASD_PHASE_DET, state, ASD_QUALITY_NONFINITE);

        /* Jedini izvor odluke od Faze 2. Hijerarhija (zdravlje senzora ->
         * prisustvo masine -> rezim -> odstupanje) i oba brojaca zive u
         * `asd_events.c` i pokriveni su host testovima; ovdje se rezultat samo
         * ispisuje i sprovodi. */
        asd_observation_t obs = {reason, ASD_PHASE_DET, metrics.rms_dbfs, s};
        asd_decision_t decided = asd_decide(&decision, &calibration, &obs);
        int alarm = decided.state == ASD_STATE_ANOMALY;
        n_alarm += alarm;
        i++;
        ui_state = decided.state;

        /* 9 significant digits round-trip a binary32 value, so the host can
         * independently verify score > threshold without decimal ambiguity. */
        printf("DET %d score=%.9g lo=0 hi=%.9g led=%d anom=%d total_anom=%d "
               "%s (uzastopnih=%d nivo=%.1f dBFS racun=%lld ms)\n",
               i, s, thr, !alarm, alarm, n_alarm,
               /* Ulazni prag, ne sirovi: ako `enter_scale` ikad prestane biti
                * 1,0, verdict i host provjera moraju ostati saglasni. */
               alarm ? "ALARM"
                     : (s > thr * decision.temporal.policy.enter_scale
                        ? "iznad praga" : "normal"),
               decision.temporal.run, metrics.rms_dbfs, t_comp / 1000);

        /* DET consumes the immediately preceding QUALITY token.  State/event
         * transitions are emitted only after that pair is complete. */
        if (decided.state_changed) {
            const char *why = decided.state == ASD_STATE_ANOMALY
                ? "THRESHOLD_PERSISTENCE"
                : (decided.state == ASD_STATE_CALIBRATED_NORMAL ? "ALARM_CLEARED"
                                                                : "PRESENCE_LOST");
            const char *type = decided.state == ASD_STATE_ANOMALY
                ? "ANOMALY_ENTERED"
                : (decided.state == ASD_STATE_CALIBRATED_NORMAL ? "ANOMALY_CLEARED"
                                                                : "PRESENCE_LOST");
            emit_state(state, decided.state, why);
            emit_event(type, decided.state, "DET", why,
                       decided.event, decided.level);
            state = decided.state;
        }
        if (decided.flow_stop) {
            /* `reason` je ime događaja iz zaključane taksonomije Faze 2 —
             * stabilan ASCII token, isti rječnik kao polje `event`. */
            emit_event("FLOW_STOPPED", decided.state, "DET",
                       asd_event_name(decided.event), decided.event,
                       decided.level);
            ESP_LOGW(TAG, "tok zaustavljen u DET: %s (%s)",
                     asd_event_name(decided.event), asd_state_name(decided.state));
            return decided.state;
        }
        if (session_interrupted()) {
            emit_session("ABORTED", "BUTTON",
                         relearn_requested ? "OPERATOR_RELEARN"
                                           : "OPERATOR_LONG_PRESS", 1);
            ESP_LOGW(TAG, "operater prekinuo nadzor%s",
                     relearn_requested ? " i trazi novo ucenje" : "");
            return state;
        }
        vTaskDelay(1); /* watchdog (rizik C6) */
    }
}

void psd_live_run(void) {
    asd_psd_init();
    quality_policy = asd_quality_default_policy();

    gpio_config_t led_cfg = {
        .pin_bit_mask = (1ULL << PIN_LED) | (1ULL << PIN_LED_ALARM),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&led_cfg);
    gpio_config_t btn_cfg = {
        .pin_bit_mask = 1ULL << PIN_BUTTON,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    gpio_config(&btn_cfg);

    asd_button_policy_t btn_policy = asd_button_default_policy();
    asd_button_init(&button, &btn_policy, gpio_get_level(PIN_BUTTON) == 0,
                    now_ms());
    /* Drugi ulaz za istu operaterovu radnju: PRESS/HOLD sa konzole. Postoji da
     * bi eksperiment mogao da se izvede i dok taster nije zalemljen. */
    asd_cmd_start();
    /* 4 KB steka: task zove `printf` sa vise `%s` argumenata pri svakom
     * pritisku, a newlib formatiranje na Xtensi ume da potrosi preko 2 KB. */
    BaseType_t ui_task_result =
        xTaskCreatePinnedToCore(ui_task, "asd_ui", 4096, NULL, 4, NULL, 0);
    if (ui_task_result != pdPASS) {
        /* Bez UI taska taster se ne cita. Posto vise nema autostarta, nastavak
         * bi ostavio prividno ziv detektor koji nikad ne moze poceti ucenje.
         * Isti ESP_ERROR_CHECK put kao za I2S init/start u app_main.c zavrsava
         * tok fail-closed; zakljucana panic politika zatim restartuje uredjaj. */
        ESP_LOGE(TAG, "UI task nije pokrenut; taster nije dostupan, restartujem");
        ESP_ERROR_CHECK(ESP_ERR_NO_MEM);
    }

    ESP_LOGI(TAG, "=== SAMOSTALNI PSD DETEKTOR ===");
    /* Statusni ispis je namjerno ASCII (pouka P12): serijski tok cita PC alat
     * cija konzolna kodna stranica ne mora podrzavati nasa slova. */
    ESP_LOGI(TAG, "model: %d traka, matrica %dx%d iz flesa, naucen na 990 "
             "normalnih snimaka ventilatora", DIM, DIM, DIM);
    ESP_LOGI(TAG, "1) pusti ventilator koji radi NORMALNO");
    ESP_LOGI(TAG, "2) pritisni taster ILI posalji PRESS sa konzole -> ucenje "
             "%d x 10 s = %d s, lampica treperi", N_CAL, N_CAL * 10);
    ESP_LOGI(TAG, "3) lampica stalno svijetli = naucio; tek tada izazovi kvar");

    asd_state_t state = ASD_STATE_NO_MACHINE;
    for (;;) {
        if (relearn_requested) {
            /* Operater je dugim pritiskom tokom nadzora već tražio novo učenje;
             * ne vraća se u čekanje, jer bi tražio drugi pritisak za istu
             * namjeru. */
            relearn_requested = 0;
        } else {
            wait_for_start(state);
        }
        emit_session("STARTED", "BUTTON", "OPERATOR_REQUEST",
                     state == ASD_STATE_CALIBRATED_NORMAL ||
                     state == ASD_STATE_ANOMALY);
        state = run_session();
        emit_session("ENDED", "FIRMWARE", asd_state_name(state), 0);
        ESP_LOGI(TAG, "sesija zavrsena u stanju %s; taster pokrece novo ucenje",
                 asd_state_name(state));
    }
}
