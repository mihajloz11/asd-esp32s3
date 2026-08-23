/* Vidi psd_live.h. */
#include "psd_live.h"

#include <math.h>
#include <stdint.h>
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
#include "asd_calibration_quality.h"
#include "asd_commissioning.h"
#include "asd_events.h"
#include "asd_interference.h"
#include "asd_cmd.h"
#include "asd_operator.h"
#include "asd_profile_runtime.h"
#include "asd_profile_nvs.h"
#include "asd_profile_store.h"
#include "asd_temporal.h"
#include "psd_features_c.h"
#include "psd_model_data.h"

static const char *TAG = "psdlive";

/* Jedan protokolarni red mora stici na UART neprekinut.
 *
 * ESP-IDF ostavlja `stdout` bez baferovanja, pa svaka konverzija odlazi na UART
 * zasebnim upisom. `emit_research_vector` jedan FEATURE96/SUBSEG96 red ispisuje
 * kroz 98 poziva, a UI task u međuvremenu emituje FLAGS iz svog konteksta.
 * Izmjereno u runu 22.08.2026: FLAGS se zalijepio usred niza brojeva, host
 * parser je u istom redu vidio dva `protocol=` i odbio ga kao
 * `duplicate_key:protocol` — 64 takva reda, pa je cijeli run pao na
 * `invalid_research_telemetry` iako je i kalibracija i detekcija radila.
 *
 * `flockfile` uzima isti FILE lock koji koristi i `printf` iz drugih taskova i
 * `ESP_LOGx` (koji ide preko `vprintf` na isti `stdout`), pa se pod njim ne
 * moze umetnuti ni jedan ni drugi. Zakljucava se cijeli red, ne pojedinacni
 * poziv. */
#define EMIT_BEGIN() flockfile(stdout)
#define EMIT_END()   funlockfile(stdout)

#define DIM            ASD_PSD_MODEL_DIM        /* 96 */
#define HOP            ASD_PSD_HOP              /* 4096 uzoraka = 256 ms */
#define HOPS_PER_CLIP  39                       /* 39 x 4096 = 159 744 ~ 10 s */
#define N_CAL          10                       /* 10 x 10 s = 100 s; PC AUC 0,853 */
#define WARM_HOPS      60                       /* ~15 s da se pusti ventilator */

/* Pragovi se izvode tek iz kasnijeg normal-only DERIVE bloka, ne iz deset
 * uzastopnih CENTER/LOO klipova. Enter je unaprijed registrovani empirijski
 * p99 kandidat, a exit je odvojeni p75. Sa `percentile_higher` i strogim
 * `score > enter`, p99 ostavlja najvise jedan DERIVE score iznad enter praga
 * za podrzane blokove od 52 ili 120 prozora. Zato DERIVE po konstrukciji ne
 * moze proizvesti n=3 alarmnu epizodu; vremenski kasniji VERIFY i dalje mora
 * nezavisno proci nulti episode/alarm-window/chatter gate. */
#define COMMISSION_ENTER_QUANTILE 0.99f
/* Izlaz iz alarma je 23.08.2026 podignut sa p75 na p95 DERIVE raspodjele, i to
 * iskljucivo iz normal-only podataka -- nijedan papiric, govor ni vrata nisu
 * gledani. Razlog je izmjeren: run tog dana je imao enter 6341 i exit 341, a
 * najtisi normalan DET prozor je bio 463, pa se alarm iz prvog papirica NIKAD
 * nije ugasio i sljedeca dva bloka nisu imala u sta da udju.
 *
 * p75 znaci da cetvrtina ispravnih prozora stoji IZNAD izlaza, pa i najmanji
 * pomak okruzenja izmedju kalibracije i mjerenja zakljuca alarm zauvijek. p95
 * znaci da se 95 % ispravnih prozora vraca u normalu prvim prozorom.
 *
 * Simetrija je namjerno asimetricna: ulaz trazi TRI uzastopna prozora iznad
 * enter praga, a izlaz jedan ispod exit praga. Zato visi izlaz ne pravi
 * treperenje -- povratak u alarm i dalje kosta tri prozora. */
#define COMMISSION_EXIT_QUANTILE  0.95f
/* Histereza ne smije da se skupi: izlaz nikad iznad ove frakcije ulaza. */
#define COMMISSION_EXIT_MAX_FRACTION 0.5f
/* Ni da propadne ispod medijane normale, jer bi povratak bio nemoguc. */
#define COMMISSION_EXIT_FLOOR_QUANTILE 0.50f
#define SCORE_NEGATIVE_TOL 1.0e-3f
#define MAX_COMMISSION_WINDOWS 128

/* Ucenje uvijek pokrece operater. Time uredjaj ne moze sam zapoceti
 * kalibraciju prije nego sto su ventilator i mikrofon spremni. */
#define UI_TICK_MS            20

static float cal_feat[N_CAL][DIM];
static float center[DIM];
static float feature[DIM];
static asd_quality_policy_t quality_policy;

/* Pet podsegmenata istog prozora. Od v2 se racunaju UVIJEK, ne samo u
 * razvojnom buildu: iz njih zivi `subsegment_instability`, jedina velicina
 * kojom kapija pouzdanosti razlikuje trajnu promjenu na masini od tudjeg zvuka.
 * Ne kostaju nove FFT-ove -- grupe su particija istih Welch segmenata. */
static asd_psd_sidecar_t window_sidecar;

#ifdef ASD_RESEARCH_TELEMETRY
#define ASD_RESEARCH_PROTOCOL "asd-research-v1.0.0"
static uint64_t research_window_start_ms;
static uint64_t research_window_end_ms;

/* Isti FNV-1a obrazac kao `mic_test.c::asd_dump_pcm_block`, ali samo preko
 * 96 binary32 vrijednosti. Dev host ponovo pakuje parsirane round-trip decimale
 * kao little-endian float32 i odbija ostecen zapis. */
static uint32_t research_feature_fnv1a(const float *values) {
    const uint8_t *bytes = (const uint8_t *)values;
    uint32_t hash = 2166136261u;
    for (size_t i = 0; i < ASD_PSD_BANDS * sizeof(float); i++) {
        hash ^= bytes[i];
        hash *= 16777619u;
    }
    return hash;
}

static void emit_research_vector(const char *kind, unsigned session,
                                 const char *phase, int window, int group,
                                 int segments, const float *values,
                                 float score, float level_dbfs,
                                 float tonalness) {
    uint32_t hash = research_feature_fnv1a(values);
    EMIT_BEGIN();
    if (group == 0) {
        printf("%s protocol=%s session=%u phase=%s window=%d "
               "window_start_ms=%llu window_end_ms=%llu score=%.9g "
               "level_dbfs=%.9g quality=OK tonalness_proxy=%.9g "
               "dims=%d fnv1a=%08lx values=",
               kind, ASD_RESEARCH_PROTOCOL, session, phase, window,
               (unsigned long long)research_window_start_ms,
               (unsigned long long)research_window_end_ms,
               score, level_dbfs, tonalness, ASD_PSD_BANDS,
               (unsigned long)hash);
    } else {
        printf("%s protocol=%s session=%u phase=%s window=%d group=%d "
               "segments=%d dims=%d fnv1a=%08lx values=",
               kind, ASD_RESEARCH_PROTOCOL, session, phase, window, group,
               segments, ASD_PSD_BANDS, (unsigned long)hash);
    }
    for (int i = 0; i < ASD_PSD_BANDS; i++)
        printf(i == 0 ? "%.9g" : ",%.9g", values[i]);
    printf("\n");
    EMIT_END();
}

static void emit_research_window(unsigned session, const char *phase,
                                 int window, const float *final_feature,
                                 float score, float level_dbfs,
                                 float tonalness) {
    emit_research_vector("FEATURE96", session, phase, window, 0,
                         window_sidecar.segments, final_feature,
                         score, level_dbfs, tonalness);
    for (int group = 0; group < ASD_PSD_SIDECAR_GROUPS; group++)
        emit_research_vector("SUBSEG96", session, phase, window, group + 1,
                             window_sidecar.group_segments[group],
                             window_sidecar.group_feature[group],
                             score, level_dbfs, tonalness);
}
#endif

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
 * Ime zapisa je namjerno izvan zaključanog rječnika `asd-quality-v1.4.0` —
 * host parser ga ne prepoznaje i preskače, pa red ne može ući u lanac
 * telemetrije koji odlučuje o valjanosti prolaza. Sva mjerodavna stanja i
 * dalje idu kroz `STATE`/`EVENT`. */
static const char *green_pattern(asd_ui_mode_t mode) {
    switch (mode) {
        case ASD_UI_IDLE:     return "flash_2s";
        case ASD_UI_LEARNING: return "blink_5hz";
        case ASD_UI_READY:    return "on";
        case ASD_UI_ALARM:    return "off";
        case ASD_UI_HOLD:     return "pulse_1s";
        default:              return "double_blink";
    }
}

static void emit_flags(asd_ui_mode_t mode, asd_state_t state) {
#ifdef ASD_RESEARCH_TELEMETRY
    const int research_telemetry = 1;
#else
    const int research_telemetry = 0;
#endif
    printf("FLAGS protocol=%s mode=%s state=%s waiting=%d learning=%d "
           "learned=%d anomaly=%d hold=%d fault=%d green=%s red=%s "
           "guided25_available=1 workflow_pending=%s research_telemetry=%d "
           "profile_persistence_allowed=0 dropped=%lu\n",
           ASD_QUALITY_PROTOCOL, asd_ui_mode_name(mode), asd_state_name(state),
           mode == ASD_UI_IDLE, mode == ASD_UI_LEARNING,
           mode == ASD_UI_READY || mode == ASD_UI_ALARM || mode == ASD_UI_HOLD,
           mode == ASD_UI_ALARM, mode == ASD_UI_HOLD, mode == ASD_UI_FAULT,
           green_pattern(mode),
           mode == ASD_UI_ALARM ? "on"
                                : (mode == ASD_UI_FAULT ? "double_blink" : "off"),
           asd_cmd_workflow_name(asd_cmd_pending_workflow()), research_telemetry,
           (unsigned long)audio_dropped_samples());
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

static void emit_commissioning(const asd_commissioning_t *flow,
                               const char *action, int index, int total,
                               int score_valid, float score,
                               float level_dbfs, float tonalness,
                               float feature_drift) {
    printf("COMMISSION protocol=%s policy=%s developmental=%d action=%s "
           "phase=%s index=%d total=%d result=%s score_valid=%d score=%.9g "
           "level_dbfs=%.9g tonalness_proxy=%.9g feature_drift=%.9g\n",
           ASD_QUALITY_PROTOCOL, ASD_COMMISSIONING_POLICY,
           flow ? flow->policy.developmental : 1, action,
           flow ? asd_commission_phase_name(flow->phase) : "REJECTED",
           index, total,
           flow ? asd_commission_reject_name(flow->reject_reason)
                : "INVALID_PROFILE",
           score_valid, score_valid ? score : 0.0f,
           isfinite(level_dbfs) ? level_dbfs : -999.0f,
           isfinite(tonalness) ? tonalness : 0.0f,
           isfinite(feature_drift) ? feature_drift : 0.0f);
}

static void emit_runtime_profile(const asd_profile_runtime_t *profile) {
    printf("PROFILE protocol=%s schema=%s policy=%s developmental=%d valid=%d "
           "policy_version=%lu policy_id=%08lx center_windows=%lu "
           "derive_windows=%lu verify_windows=%lu level_mean_dbfs=%.9g "
           "tonalness_reference=%.9g threshold_enter=%.9g threshold_exit=%.9g\n",
           ASD_QUALITY_PROTOCOL, ASD_PROFILE_SCHEMA, ASD_COMMISSIONING_POLICY,
           profile->developmental, profile->valid,
           (unsigned long)profile->policy_version,
           (unsigned long)profile->policy_id,
           (unsigned long)profile->center_windows,
           (unsigned long)profile->derive_windows,
           (unsigned long)profile->verify_windows,
           profile->level_mean_dbfs, profile->tonalness_reference,
           profile->threshold_enter, profile->threshold_exit);
}

/* K1 je valjan, auditabilan kraj CAL toka, ne kvar UART-a ni senzora. Zato
 * koristi postojeci terminalni STATE/FLOW_STOPPED par, ali sa zasebnim javnim
 * reason tokenom iz cistog commissioning modula. */
static asd_state_t stop_unstable_calibration(
    asd_state_t from, asd_calibration_quality_reason_t reason) {
    const char *name = asd_calibration_quality_reason_name(reason);
    asd_state_t to = ASD_STATE_CALIBRATION_REJECTED;
    ui_state = to;
    emit_state(from, to, name);
    emit_event("FLOW_STOPPED", to, "CAL", name,
               ASD_EVENT_NONE, ASD_LEVEL_DEVIATION);
    ESP_LOGE(TAG, "K1 odbio kalibraciju: %s -> %s", name,
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
        /* Prazni ring i dok se ceka. Capture task radi neprekidno, pa bi bez
         * ovoga ring (2 s) bio pun poslije dvije sekunde i `dropped` bi rastao
         * 16000 uzoraka/s cijelo vrijeme cekanja. Prelivanje dok niko ne mjeri
         * nije kvar senzora, ali panel prije armiranja trazi `dropped=0`
         * (asd_panel.py, arm_ready) pa se GUIDED25 ne bi mogao ni pokrenuti. */
        (void)audio_flush();
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

#ifdef ASD_RESEARCH_TELEMETRY
    research_window_start_ms = (uint64_t)(esp_timer_get_time() / 1000);
#endif
    asd_psd_stream_reset_sidecar();
    int64_t t_comp = 0;
    uint32_t dropped_before = audio_dropped_samples();
    asd_quality_accumulator_t acc;
    asd_quality_reset(&acc, HOPS_PER_CLIP * HOP, dropped_before, &quality_policy);

    for (int h = 0; h < HOPS_PER_CLIP; h++) {
        size_t got = 0;
        esp_err_t audio_error = audio_read_exact(
            pcm, HOP, AUDIO_READ_DEFAULT_TIMEOUT_MS, &got);
        asd_quality_add_pcm(&acc, pcm, got);
        if (audio_error != ESP_OK || got != HOP) {
            asd_quality_finish(&acc, audio_dropped_samples(), quality);
            if (t_compute_us) *t_compute_us = t_comp;
            if (audio_error == ESP_ERR_TIMEOUT)
                return ASD_QUALITY_AUDIO_TIMEOUT;
            if (audio_error != ESP_OK)
                return ASD_QUALITY_AUDIO_READ_ERROR;
            return ASD_QUALITY_SHORT_READ;
        }
        for (int i = 0; i < HOP; i++) {
            hop[i] = (float)pcm[i] / 32768.0f;
        }
        int64_t a = esp_timer_get_time();
        asd_psd_stream_push_hop(hop);
        t_comp += esp_timer_get_time() - a;
    }

    /* Kraj prozora je kraj posljednjeg audio hopa, ne kraj UART ispisa. */
#ifdef ASD_RESEARCH_TELEMETRY
    research_window_end_ms = (uint64_t)(esp_timer_get_time() / 1000);
#endif
    int64_t a = esp_timer_get_time();
    int segments = asd_psd_stream_finish_sidecar(out_feature, &window_sidecar);
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

/* Koliko se pet podsegmenata istog prozora medjusobno ne slazu, u
 * normalizovanim jedinicama modela:
 *
 *   z_g[d] = (grupa_g[d] - norm_mean[d]) / norm_std[d]
 *   instability = mean_d( std_g( z_g[d] ) )
 *
 * Trajna promjena na masini izgleda isto kroz cijeli prozor pa su podsegmenti
 * slozni; govor, vrata i koraci nisu. Isti izraz racuna i
 * `pc/tools/derive_interference_policy.py`, pa su granica i mjera u istim
 * jedinicama. Populaciona sd (dijeli se sa G), da se poklopi sa numpy.std. */
static float subsegment_instability(const asd_psd_sidecar_t *sidecar) {
    if (!sidecar) return NAN;
    float total = 0.0f;
    for (int d = 0; d < DIM; d++) {
        float z[ASD_PSD_SIDECAR_GROUPS];
        float mean = 0.0f;
        for (int g = 0; g < ASD_PSD_SIDECAR_GROUPS; g++) {
            z[g] = (sidecar->group_feature[g][d] - asd_psd_norm_mean[d]) /
                   asd_psd_norm_std[d];
            mean += z[g];
        }
        mean /= (float)ASD_PSD_SIDECAR_GROUPS;
        float variance = 0.0f;
        for (int g = 0; g < ASD_PSD_SIDECAR_GROUPS; g++)
            variance += (z[g] - mean) * (z[g] - mean);
        total += sqrtf(variance / (float)ASD_PSD_SIDECAR_GROUPS);
    }
    return total / (float)DIM;
}

static float score_with_center(const float *feat, const float *c) {
    return asd_psd_score(feat, asd_psd_norm_mean, asd_psd_norm_std,
                         asd_psd_precision, c, DIM);
}

static int cmp_float(const void *a, const void *b) {
    float x = *(const float *)a, y = *(const float *)b;
    return (x > y) - (x < y);
}

static float feature_drift_mean_abs(const float *current,
                                    const float *previous) {
    if (!current || !previous) return 0.0f;
    float sum = 0.0f;
    for (int i = 0; i < DIM; i++) sum += fabsf(current[i] - previous[i]);
    return sum / (float)DIM;
}

static float percentile_higher(float *values, int count, float quantile) {
    if (!values || count <= 0 || !(quantile > 0.0f && quantile < 1.0f))
        return NAN;
    qsort(values, count, sizeof(float), cmp_float);
    int index = (int)ceilf(quantile * (float)count) - 1;
    if (index < 0) index = 0;
    if (index >= count) index = count - 1;
    return values[index];
}

static asd_state_t stop_commissioning(asd_state_t from,
                                      const asd_commissioning_t *flow) {
    const char *reason = flow
        ? asd_commission_reject_name(flow->reject_reason)
        : "INVALID_PROFILE";
    ui_state = ASD_STATE_CALIBRATION_REJECTED;
    emit_state(from, ASD_STATE_CALIBRATION_REJECTED, reason);
    emit_event("FLOW_STOPPED", ASD_STATE_CALIBRATION_REJECTED,
               flow ? asd_commission_phase_name(flow->phase) : "REJECTED",
               reason, ASD_EVENT_NONE, ASD_LEVEL_DEVIATION);
    return ASD_STATE_CALIBRATION_REJECTED;
}

/* --- jedna sesija: WAIT -> CAL -> DET -------------------------------------- */

/* Vraća stanje u kojem je sesija završila. Nikad se ne vraća sa validnom
 * kalibracijom „u vazduhu": svaki izlaz prolazi kroz stop_flow ili prekid. */
static asd_state_t run_session(unsigned session_index,
                               asd_profile_runtime_t *persisted_profile,
                               asd_profile_store_metadata_t *persisted_metadata,
                               uint32_t *persisted_blob_crc32,
                               int *profile_loaded,
                               int use_persisted_profile,
                               asd_workflow_t workflow) {
#ifndef ASD_RESEARCH_TELEMETRY
    (void)session_index;
#endif
    asd_state_t state = ASD_STATE_NO_MACHINE;
    asd_decision_ctx_t decision;
    asd_presence_policy_t presence = asd_presence_default_policy();
    asd_decision_init(&decision, &presence);
    asd_calibration_t calibration = {0, NAN, NAN, NAN};
    asd_profile_runtime_t runtime_profile;
    asd_profile_runtime_clear(&runtime_profile);
    asd_commissioning_t commissioning;
    asd_commission_policy_t commissioning_policy = workflow == ASD_WORKFLOW_GUIDED25
        ? asd_commission_guided25_policy() : asd_commission_default_policy();
    const int profile_persistence_allowed =
        asd_commission_profile_persistence_allowed(&commissioning_policy);
    asd_commission_init(&commissioning, &commissioning_policy);
    int restored = profile_persistence_allowed && use_persisted_profile &&
        profile_loaded && *profile_loaded && persisted_profile &&
        persisted_metadata && asd_profile_runtime_validate(persisted_profile, 1);
    int64_t t_comp = 0, t_comp_sum = 0;
    float cal_level_mean = NAN;
    float threshold_enter = NAN;
    float threshold_exit = NAN;
    float derive_mean = NAN;
    float derive_sd = NAN;
    if (!restored && !asd_commission_start(&commissioning, now_ms()))
        return stop_commissioning(state, &commissioning);

    ui_stage = ASD_STAGE_SETTLE;
    ui_state = state;
    emit_state(state, state, "BOOT_FAIL_CLOSED");
    if (restored) {
        runtime_profile = *persisted_profile;
        memcpy(center, runtime_profile.center, sizeof(center));
        cal_level_mean = runtime_profile.level_mean_dbfs;
        threshold_enter = runtime_profile.threshold_enter;
        threshold_exit = runtime_profile.threshold_exit;
        derive_mean = persisted_metadata->derive_mean;
        derive_sd = persisted_metadata->derive_sd;
        printf("PROFILESTORE protocol=%s schema=%s result=LOADED generation=%lu "
               "fingerprint=%s crc32=%08lx threshold_enter=%.9g "
               "threshold_exit=%.9g center_windows=%lu derive_windows=%lu "
               "verify_windows=%lu profile_policy_version=%lu "
               "profile_policy_id=%lu quality_policy_id=%lu "
               "commissioning_policy_id=%lu temporal_policy_id=%lu "
               "interference_policy_id=%lu derive_mean=%.9g derive_sd=%.9g "
               "verify_alarm_time_percent=%.9g verify_alarm_windows=%lu "
               "verify_episodes=%lu verify_chatter=%lu\n",
               ASD_QUALITY_PROTOCOL, ASD_PROFILE_STORE_SCHEMA,
               (unsigned long)persisted_metadata->generation,
               ASD_PSD_MODEL_FINGERPRINT_HEX,
               (unsigned long)(persisted_blob_crc32 ? *persisted_blob_crc32 : 0u),
               runtime_profile.threshold_enter, runtime_profile.threshold_exit,
               (unsigned long)runtime_profile.center_windows,
               (unsigned long)runtime_profile.derive_windows,
               (unsigned long)runtime_profile.verify_windows,
               (unsigned long)runtime_profile.policy_version,
               (unsigned long)runtime_profile.policy_id,
               (unsigned long)persisted_metadata->quality_policy_id,
               (unsigned long)persisted_metadata->commissioning_policy_id,
               (unsigned long)persisted_metadata->temporal_policy_id,
               (unsigned long)persisted_metadata->interference_policy_id,
               derive_mean, derive_sd,
               persisted_metadata->verify_alarm_time_percent,
               (unsigned long)persisted_metadata->verify_alarm_windows,
               (unsigned long)persisted_metadata->verify_episodes,
               (unsigned long)persisted_metadata->verify_chatter);
        goto profile_ready;
    }
    emit_commissioning(&commissioning, "STARTED", 0,
                       commissioning.policy.max_settle_windows,
                       0, 0.0f, NAN, NAN, NAN);

    /* SETTLE uses only level, tonalness, feature drift and quality.  Its API
     * has no score argument, so a pre-center Mahalanobis call cannot be added
     * accidentally.  Numeric limits are DEVELOPMENT until physical normal-only
     * validation; no profile from this build is persisted. */
    float previous_settle_feature[DIM];
    int previous_settle_feature_valid = 0;
    int settle_index = 0;
    while (commissioning.phase == ASD_COMMISSION_SETTLE) {
        asd_quality_metrics_t metrics;
        int feature_valid = 0;
        int64_t settle_compute_us = 0;
        asd_quality_reason_t reason = capture_clip(
            feature, &settle_compute_us, &metrics, &feature_valid);
        float tonalness = reason == ASD_QUALITY_OK
            ? feature_tonalness_proxy(feature) : NAN;
        float drift = (reason == ASD_QUALITY_OK && previous_settle_feature_valid)
            ? feature_drift_mean_abs(feature, previous_settle_feature) : 0.0f;
        asd_settle_observation_t settle_observation = {
            .quality_ok = reason == ASD_QUALITY_OK && feature_valid,
            .level_dbfs = metrics.rms_dbfs,
            .tonalness = tonalness,
            .feature_drift = drift,
            .dropped_delta = metrics.dropped_delta,
        };
        settle_index++;
        int continued = asd_commission_observe_settle(
            &commissioning, now_ms(), &settle_observation);
        emit_commissioning(&commissioning, "WINDOW", settle_index,
                           commissioning.policy.max_settle_windows,
                           0, 0.0f, metrics.rms_dbfs, tonalness, drift);
        if (!continued) return stop_commissioning(state, &commissioning);
        if (reason == ASD_QUALITY_OK && feature_valid) {
            memcpy(previous_settle_feature, feature,
                   sizeof(previous_settle_feature));
            previous_settle_feature_valid = 1;
        }
        if (session_interrupted()) {
            asd_commission_abort(&commissioning);
            emit_session("ABORTED", "BUTTON", "OPERATOR_LONG_PRESS", 0);
            return state;
        }
    }
    ui_stage = ASD_STAGE_CENTER_LEARNING;
    emit_commissioning(&commissioning, "PHASE_ENTERED", 0,
                       commissioning.policy.center_windows,
                       0, 0.0f, NAN, NAN, NAN);

    /* Legacy WAIT quality precheck remains wire-compatible for existing host
     * captures.  Stabilization authority is the variable-length SETTLE above.
     * WAIT never contributes a center or threshold. */
    /* --- 1) cekanje: operater pusta ventilator, provjerava se da mikrofon
     * stvarno nesto cuje (P3: konstantan score ne dokazuje da mikrofon radi) --- */
    static int16_t pcm[HOP];
    int loud = 0;
    for (int h = 0; h < WARM_HOPS; h++) {
        asd_quality_accumulator_t acc;
        asd_quality_metrics_t metrics;
        asd_quality_reset(&acc, HOP, audio_dropped_samples(), &quality_policy);
        size_t got = 0;
        esp_err_t audio_error = audio_read_exact(
            pcm, HOP, AUDIO_READ_DEFAULT_TIMEOUT_MS, &got);
        asd_quality_add_pcm(&acc, pcm, got);
        asd_quality_finish(&acc, audio_dropped_samples(), &metrics);
        asd_quality_reason_t reason = audio_error == ESP_ERR_TIMEOUT
            ? ASD_QUALITY_AUDIO_TIMEOUT
            : (audio_error != ESP_OK
                ? ASD_QUALITY_AUDIO_READ_ERROR
                : asd_quality_evaluate(&metrics, &quality_policy));
        emit_quality("WAIT", h + 1, WARM_HOPS, &metrics, reason, 0, NAN);
        if (reason == ASD_QUALITY_OK) loud++;
        printf("WAIT %d/%d level_dbfs=%.2f spread=0.000 nivo=%.1f dBFS %s\n",
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
    /* Referentni nivo kalibrisane masine. Faza 2 iz njega izvodi test prisustva:
     * masina je prisutna dok je nivo iznad ove sredine minus margina. */
    float cal_level_sum = 0.0f;
    float cal_tonalness_sum = 0.0f;
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
        if (reason == ASD_QUALITY_OK) cal_tonalness_sum += tonalness;
        emit_quality("CAL", i + 1, N_CAL, &metrics, reason,
                     feature_valid, tonalness);
        printf("CAL %2d/%d score=0.00000 nivo=%.1f dBFS racun=%lld ms\n",
               i + 1, N_CAL, metrics.rms_dbfs, t_comp / 1000);
#ifdef ASD_RESEARCH_TELEMETRY
        if (reason == ASD_QUALITY_OK && feature_valid)
            emit_research_window(session_index, "CAL", i + 1, cal_feat[i],
                                 0.0f, metrics.rms_dbfs, tonalness);
#endif
        if (asd_quality_flow_action(reason, ASD_PHASE_CAL) == ASD_FLOW_STOP)
            return stop_flow("CAL", ASD_PHASE_CAL, state, reason);
        if (!asd_commission_record_center(
                &commissioning, now_ms(), reason == ASD_QUALITY_OK))
            return stop_commissioning(state, &commissioning);
        if (session_interrupted()) {
            asd_commission_abort(&commissioning);
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
    float loo_range = sorted[N_CAL - 1] - sorted[0];
    /* CAL_SUMMARY wire schema ne dozvoljava NaN/Inf. Cisti modul ih svakako
     * odbija u host testu, ali UART ne smije prvo objaviti neparsabilan zapis. */
    if (!isfinite(loo_cv) || !isfinite(loo_range))
        return stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_NONFINITE);
    printf("QUALITY protocol=%s phase=CAL_SUMMARY result=OBSERVED "
           "loo_mean=%.6f loo_sd=%.6f loo_cv=%.6f loo_range=%.6f "
           "loo_gate=pending_normal_only\n",
           ASD_QUALITY_PROTOCOL, mean, sd, loo_cv,
           loo_range);

    /* K1 se izvrsava odmah nakon auditabilnog CAL_SUMMARY zapisa. Nijedan prag,
     * CALIBRATION_ACCEPTED zapis ni DET prozor ne smije nastati poslije pada. */
    asd_calibration_quality_policy_t calibration_policy =
        asd_calibration_quality_default_policy();
    asd_calibration_quality_metrics_t calibration_metrics = {
        .loo_mean = mean,
        .loo_sd = sd,
        .loo_cv = loo_cv,
        .loo_range = loo_range,
    };
    asd_calibration_quality_reason_t calibration_reason =
        asd_calibration_quality_evaluate(&calibration_metrics,
                                         &calibration_policy);
    if (calibration_reason == ASD_CALIBRATION_QUALITY_UNSTABLE)
        return stop_unstable_calibration(state, calibration_reason);
    if (calibration_reason == ASD_CALIBRATION_QUALITY_NONFINITE)
        return stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_NONFINITE);
    if (calibration_reason != ASD_CALIBRATION_QUALITY_ACCEPTED)
        return stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_INVALID_ARGUMENT);

    cal_level_mean = cal_level_sum / (float)N_CAL;
    float cal_tonalness_reference = cal_tonalness_sum / (float)N_CAL;
    if (!isfinite(cal_level_mean) || !isfinite(cal_tonalness_reference))
        return stop_flow("CAL", ASD_PHASE_CAL, state, ASD_QUALITY_NONFINITE);

    if (!asd_commission_commit_center(
            &commissioning, now_ms(), &runtime_profile, center,
            cal_level_mean, cal_tonalness_reference, 1))
        return stop_commissioning(state, &commissioning);

    ESP_LOGI(TAG, "--- kalibracija gotova (centar zamrznut) ---");
    ESP_LOGI(TAG, "LOO score: mean=%.2f sd=%.2f min=%.2f max=%.2f",
             mean, sd, sorted[0], sorted[N_CAL - 1]);
    ESP_LOGI(TAG, "referentni nivo masine: %.2f dBFS (gate prisustva %.2f dBFS)",
             cal_level_mean, cal_level_mean - presence.absent_margin_db);
    /* Drugi red koji se sastavlja iz vise poziva; vidi EMIT_BEGIN. */
    EMIT_BEGIN();
    printf("LOOALL");
    for (int i = 0; i < N_CAL; i++) printf(" %.3f", loo[i]);
    printf("\n");
    EMIT_END();
    if (commissioning.policy.derive_windows > MAX_COMMISSION_WINDOWS ||
        commissioning.policy.verify_windows > MAX_COMMISSION_WINDOWS)
        return stop_commissioning(state, NULL);

    ui_stage = ASD_STAGE_COMMISSION_DERIVE;
    float derive_scores[MAX_COMMISSION_WINDOWS];
    float derive_sum = 0.0f;
    for (uint32_t index = 0; index < commissioning.policy.derive_windows; index++) {
        asd_quality_metrics_t metrics;
        int feature_valid = 0;
        asd_quality_reason_t reason = capture_clip(
            feature, &t_comp, &metrics, &feature_valid);
        float tonalness = reason == ASD_QUALITY_OK
            ? feature_tonalness_proxy(feature) : NAN;
        float score = reason == ASD_QUALITY_OK
            ? score_with_center(feature, center) : NAN;
        if (reason == ASD_QUALITY_OK &&
            (!clamp_nonnegative_score(&tonalness) ||
             !clamp_nonnegative_score(&score)))
            reason = ASD_QUALITY_NONFINITE;
        int continued = asd_commission_record_derive(
            &commissioning, now_ms(), score, reason == ASD_QUALITY_OK);
        emit_commissioning(&commissioning, "WINDOW", (int)index + 1,
                           (int)commissioning.policy.derive_windows,
                           reason == ASD_QUALITY_OK, score, metrics.rms_dbfs,
                           tonalness, 0.0f);
        if (!continued) return stop_commissioning(state, &commissioning);
        derive_scores[index] = score;
        derive_sum += score;
        if (session_interrupted()) {
            asd_commission_abort(&commissioning);
            return stop_commissioning(state, &commissioning);
        }
    }
    float derive_sorted[MAX_COMMISSION_WINDOWS];
    memcpy(derive_sorted, derive_scores,
           commissioning.policy.derive_windows * sizeof(float));
    threshold_enter = percentile_higher(
        derive_sorted, (int)commissioning.policy.derive_windows,
        COMMISSION_ENTER_QUANTILE);
    memcpy(derive_sorted, derive_scores,
           commissioning.policy.derive_windows * sizeof(float));
    threshold_exit = percentile_higher(
        derive_sorted, (int)commissioning.policy.derive_windows,
        COMMISSION_EXIT_QUANTILE);
    memcpy(derive_sorted, derive_scores,
           commissioning.policy.derive_windows * sizeof(float));
    float exit_floor = percentile_higher(
        derive_sorted, (int)commissioning.policy.derive_windows,
        COMMISSION_EXIT_FLOOR_QUANTILE);
    float exit_ceiling = COMMISSION_EXIT_MAX_FRACTION * threshold_enter;
    /* Redoslijed je bitan: prvo plafon, pa pod. Obrnuto je pod mrtav kod, jer
     * je p95 >= p50 za svaku raspodjelu, a plafon je onda mogao da gurne izlaz
     * ispod medijane normale -- tacno kvar zbog kojeg je ovo i mijenjano. */
    if (isfinite(exit_ceiling) && threshold_exit > exit_ceiling)
        threshold_exit = exit_ceiling;
    if (isfinite(exit_floor) && threshold_exit < exit_floor)
        threshold_exit = exit_floor;
    /* Ako pod prelazi plafon, raspodjela je toliko tijesna da histereza nema
     * gdje da stane. To se ne rjesava tihim biranjem jedne granice nego
     * odbijanjem kalibracije. */
    if (isfinite(exit_floor) && isfinite(exit_ceiling) &&
        exit_floor > exit_ceiling)
        return stop_commissioning(state, &commissioning);
    if (!asd_commission_freeze_thresholds(
            &commissioning, now_ms(), &runtime_profile,
            threshold_enter, threshold_exit))
        return stop_commissioning(state, &commissioning);

    ui_stage = ASD_STAGE_COMMISSION_VERIFY;
    for (uint32_t index = 0; index < commissioning.policy.verify_windows; index++) {
        asd_quality_metrics_t metrics;
        int feature_valid = 0;
        asd_quality_reason_t reason = capture_clip(
            feature, &t_comp, &metrics, &feature_valid);
        float tonalness = reason == ASD_QUALITY_OK
            ? feature_tonalness_proxy(feature) : NAN;
        float score = reason == ASD_QUALITY_OK
            ? score_with_center(feature, center) : NAN;
        if (reason == ASD_QUALITY_OK &&
            (!clamp_nonnegative_score(&tonalness) ||
             !clamp_nonnegative_score(&score)))
            reason = ASD_QUALITY_NONFINITE;
        int continued = asd_commission_record_verify(
            &commissioning, now_ms(), &runtime_profile, score,
            reason == ASD_QUALITY_OK);
        emit_commissioning(&commissioning, "WINDOW", (int)index + 1,
                           (int)commissioning.policy.verify_windows,
                           reason == ASD_QUALITY_OK, score, metrics.rms_dbfs,
                           tonalness, 0.0f);
        if (!continued) return stop_commissioning(state, &commissioning);
        if (session_interrupted()) {
            asd_commission_abort(&commissioning);
            return stop_commissioning(state, &commissioning);
        }
    }
    if (commissioning.phase != ASD_COMMISSION_MONITORING ||
        !asd_profile_runtime_validate(&runtime_profile, 1))
        return stop_commissioning(state, &commissioning);

    derive_mean = derive_sum / (float)commissioning.policy.derive_windows;
    float derive_var = 0.0f;
    for (uint32_t index = 0; index < commissioning.policy.derive_windows; index++)
        derive_var += (derive_scores[index] - derive_mean) *
                      (derive_scores[index] - derive_mean);
    derive_sd = commissioning.policy.derive_windows > 1u
        ? sqrtf(derive_var / (float)(commissioning.policy.derive_windows - 1u))
        : 0.0f;
    asd_profile_store_metadata_t stored_metadata = {
        .generation = persisted_metadata
            ? persisted_metadata->generation + 1u : 1u,
        .derive_mean = derive_mean,
        .derive_sd = derive_sd,
        .verify_alarm_time_percent = runtime_profile.verify_windows > 0u
            ? 100.0f * (float)commissioning.verify_alarm_windows /
                (float)runtime_profile.verify_windows
            : 0.0f,
        .verify_alarm_windows = commissioning.verify_alarm_windows,
        .verify_episodes = commissioning.verify_episodes,
        .verify_chatter = commissioning.verify_chatter,
        .quality_policy_id = ASD_QUALITY_POLICY_ID,
        .commissioning_policy_id = ASD_COMMISSIONING_POLICY_ID,
        .temporal_policy_id = ASD_TEMPORAL_POLICY_ID,
        .interference_policy_id = ASD_INTERFERENCE_POLICY_ID,
    };
    if (profile_persistence_allowed) {
        uint32_t stored_crc32 = 0u;
        esp_err_t store_error = asd_profile_nvs_save(
            &runtime_profile, &stored_metadata, asd_psd_model_fingerprint,
            &stored_crc32);
        if (store_error == ESP_OK) {
            if (persisted_profile) *persisted_profile = runtime_profile;
            if (persisted_metadata) *persisted_metadata = stored_metadata;
            if (persisted_blob_crc32) *persisted_blob_crc32 = stored_crc32;
            if (profile_loaded) *profile_loaded = 1;
            ESP_LOGI(TAG, "profil sacuvan u NVS-u, generacija %lu",
                     (unsigned long)stored_metadata.generation);
        } else {
            ESP_LOGE(TAG, "profil validan u RAM-u, ali NVS save nije uspio: %s",
                     esp_err_to_name(store_error));
        }
    } else {
        if (profile_loaded) *profile_loaded = 0;
        ESP_LOGW(TAG, "DEVELOPMENT profil ostaje samo u RAM-u; NVS save je zabranjen");
    }

profile_ready:
    emit_runtime_profile(&runtime_profile);
    if (!restored)
        printf("ADAPTTHR n=%lu mean=%.6f sd=%.6f k=0 theta=0 p=%.4f "
               "thr=%.9g lo=0.000000 factory=0.000000\n",
               (unsigned long)runtime_profile.derive_windows,
               derive_mean, derive_sd,
               (double)COMMISSION_ENTER_QUANTILE, threshold_enter);
    if (!restored)
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
           "enter_scale=%.9g exit_scale=%.9g fast_scale=%.9g "
           "threshold_mode=absolute_profile threshold_enter=%.9g "
           "threshold_exit=%.9g\n",
           ASD_QUALITY_PROTOCOL, ASD_TEMPORAL_POLICY, temporal.min_consecutive,
           temporal.ewma_alpha, temporal.enter_scale, temporal.exit_scale,
           temporal.fast_scale, runtime_profile.threshold_enter,
           runtime_profile.threshold_exit);

    /* Kalibracija je prihvaćena: od sada Faza 2 ima referentni nivo i prag, pa
     * `asd_decide()` može ocjenjivati i prisustvo i odstupanje. */
    calibration.valid = 1;
    calibration.level_mean_dbfs = cal_level_mean;
    calibration.threshold_enter = runtime_profile.threshold_enter;
    calibration.threshold_exit = runtime_profile.threshold_exit;
    decision.state = ASD_STATE_CALIBRATED_NORMAL;

    emit_state(state, ASD_STATE_CALIBRATED_NORMAL,
               restored ? "PROFILE_RESTORED" : "CALIBRATION_ACCEPTED");
    state = ASD_STATE_CALIBRATED_NORMAL;
    ui_stage = ASD_STAGE_MONITORING;
    ui_state = state;
    emit_event(restored ? "PROFILE_RESTORED" : "CALIBRATION_ACCEPTED", state,
               restored ? "PROFILE" : "CAL",
               restored ? "PROFILE_VALID" : "QUALITY_OK",
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
        /* Do v2 je ovdje stajala tvrda nula, pa je kapija pouzdanosti bila
         * povezana ali slijepa. Sada dobija stvarnu mjeru iz istog prozora. */
        /* NE sanira se u nulu: nula znaci "podsegmenti su savrseno slozni", pa
         * bi pokvaren sidecar tiho PROSAO kapiju. `asd_decide` vec ima
         * fail-closed granu za nekonacnu nestabilnost i ona mora da je vidi. */
        float instability = subsegment_instability(&window_sidecar);
        asd_observation_t obs = {
            reason, ASD_PHASE_DET, metrics.rms_dbfs, s,
            tonalness - runtime_profile.tonalness_reference,
            instability,
        };
        asd_decision_t decided = asd_decide(&decision, &calibration, &obs);
        int alarm = decided.state == ASD_STATE_ANOMALY;
        n_alarm += alarm;
        i++;
        ui_state = decided.state;

        /* 9 significant digits round-trip a binary32 value, so the host can
         * independently verify score > threshold without decimal ambiguity. */
        /* `hold=` postoji od q1.6.0. Bez njega host ne moze da reprodukuje
         * `uzastopnih=0` u prozoru koji je kapija proglasila nepouzdanim, pa bi
         * svaki HOLD prozor izgledao kao neslaganje sa firmverom. */
        printf("DET %d score=%.9g lo=0 hi=%.9g led=%d anom=%d total_anom=%d "
               "hold=%d %s (uzastopnih=%d nivo=%.1f dBFS racun=%lld ms)\n",
               i, s, threshold_enter, !alarm, alarm, n_alarm,
               decided.observation_hold,
               alarm ? "ALARM"
                     : (s > threshold_enter
                        ? "iznad praga" : "normal"),
               decision.temporal.run, metrics.rms_dbfs, t_comp / 1000);

        /* Core ugovor ostaje neposredan QUALITY DET -> DET. Research sidecar
         * dolazi tek poslije kompletnog para i zato ga ne moze presjeci. */
#ifdef ASD_RESEARCH_TELEMETRY
        emit_research_window(session_index, "DET", i, feature, s,
                             metrics.rms_dbfs, tonalness);
#endif

        /* DET consumes the immediately preceding QUALITY token.  State/event
         * transitions are emitted only after that pair is complete. */
        if (decided.state_changed) {
            const char *why = decided.state == ASD_STATE_ANOMALY
                ? "THRESHOLD_PERSISTENCE"
                : (decided.state == ASD_STATE_OBSERVATION_HOLD
                    ? "OBSERVATION_UNCERTAIN"
                : (decided.state == ASD_STATE_CALIBRATED_NORMAL
                    ? (state == ASD_STATE_OBSERVATION_HOLD
                       ? "OBSERVATION_RESUMED" : "ALARM_CLEARED")
                    : "PRESENCE_LOST"));
            const char *type = decided.state == ASD_STATE_ANOMALY
                ? "ANOMALY_ENTERED"
                : (decided.state == ASD_STATE_OBSERVATION_HOLD
                    ? "OBSERVATION_HOLD"
                : (decided.state == ASD_STATE_CALIBRATED_NORMAL
                    ? (state == ASD_STATE_OBSERVATION_HOLD
                       ? "OBSERVATION_RESUMED" : "ANOMALY_CLEARED")
                    : "PRESENCE_LOST"));
            emit_state(state, decided.state, why);
            emit_event(type, decided.state, "DET", why,
                       decided.event, decided.level);
            state = decided.state;
        }
        if (decided.hold_warning)
            emit_event("OBSERVATION_HOLD_WARNING", decided.state, "DET",
                       "LONG_OBSERVATION_HOLD", ASD_EVENT_NONE,
                       ASD_LEVEL_DEVIATION);
        /* Odstupanje koje traje dva minuta vise nije epizoda. Tvrdnja je i
         * dalje o trajanju, ne o uzroku -- dogadjaj ostaje UNKNOWN_CHANGE, jer
         * jedan mikrofon bez f0 ne moze reci da je kvar mehanicki. */
        if (decided.sustained_anomaly)
            emit_event("ANOMALY_SUSTAINED", decided.state, "DET",
                       "SUSTAINED_DEVIATION", decided.event,
                       ASD_LEVEL_DEVIATION);
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
    asd_profile_runtime_t persisted_profile;
    asd_profile_runtime_clear(&persisted_profile);
    asd_profile_store_metadata_t persisted_metadata = {0};
    uint32_t persisted_blob_crc32 = 0u;
    int profile_loaded = 0;
    asd_commission_policy_t startup_commissioning_policy =
        asd_commission_default_policy();
    const int profile_persistence_allowed =
        asd_commission_profile_persistence_allowed(&startup_commissioning_policy);
    if (profile_persistence_allowed) {
        esp_err_t nvs_error = asd_profile_nvs_init();
        if (nvs_error == ESP_OK) {
            nvs_error = asd_profile_nvs_load(
                asd_psd_model_fingerprint, &persisted_profile,
                &persisted_metadata, &persisted_blob_crc32, &profile_loaded);
        }
        if (nvs_error != ESP_OK) {
            profile_loaded = 0;
            ESP_LOGE(TAG, "NVS profil nije dostupan: %s; potrebno je novo ucenje",
                     esp_err_to_name(nvs_error));
        }
    } else {
        ESP_LOGW(TAG, "DEVELOPMENT policy: NVS profile load/save je zabranjen");
    }

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
    unsigned session_index = 0;
    int restore_pending = profile_loaded;
    for (;;) {
        int use_persisted_profile = restore_pending;
        restore_pending = 0;
        if (use_persisted_profile) {
            /* Validan blob nastavlja nadzor poslije nestanka napajanja bez
             * ucenja; dug pritisak i dalje eksplicitno odbacuje taj izbor. */
        } else if (relearn_requested) {
            /* Operater je dugim pritiskom tokom nadzora već tražio novo učenje;
             * ne vraća se u čekanje, jer bi tražio drugi pritisak za istu
             * namjeru. */
            relearn_requested = 0;
        } else {
            wait_for_start(state);
        }
        asd_workflow_t workflow = use_persisted_profile
            ? ASD_WORKFLOW_DEFAULT : asd_cmd_take_workflow();
        asd_cmd_set_session_active(1);
        /* Baci sve sto se nakupilo dok je uredjaj cekao pritisak, i nuliraj
         * `dropped`. Mora PRIJE `emit_session("STARTED")`: host na tom zapisu
         * resetuje svoj `max_dropped`, pa svaki sljedeci FLAGS -- ukljucujuci
         * onaj koji UI task posalje cim mode postane LEARNING -- vec mora
         * nositi brojac ove sesije. Vidi audio_flush() u audio_i2s.c. */
        size_t stale = audio_flush();
        if (stale)
            ESP_LOGI(TAG, "odbacen ustajali zvuk iz cekanja: %u uzoraka",
                     (unsigned)stale);
        emit_session("STARTED", use_persisted_profile ? "FIRMWARE" : "BUTTON",
                     use_persisted_profile ? "PROFILE_RESTORED" : "OPERATOR_REQUEST",
                     state == ASD_STATE_CALIBRATED_NORMAL ||
                     state == ASD_STATE_ANOMALY);
        session_index++;
        state = run_session(session_index, &persisted_profile,
                            &persisted_metadata, &persisted_blob_crc32,
                            &profile_loaded,
                            use_persisted_profile, workflow);
        asd_cmd_set_session_active(0);
        emit_session("ENDED", "FIRMWARE", asd_state_name(state), 0);
        ESP_LOGI(TAG, "sesija zavrsena u stanju %s; taster pokrece novo ucenje",
                 asd_state_name(state));
    }
}
