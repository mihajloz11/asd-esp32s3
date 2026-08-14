/* Vidi asd_operator.h. */
#include "asd_operator.h"

#include "asd_events.h"

/* 30 ms je iznad odskoka svakog taktilnog tastera koji se koristi na pločici, a
 * ispod praga na kojem se pritisak osjeti kao spor. 1500 ms za dug pritisak je
 * dovoljno da se ne desi slučajno, a da se ne čeka predugo. */
#define DEFAULT_DEBOUNCE_MS    30u
#define DEFAULT_LONG_PRESS_MS  1500u

/* Obrasci lampice. Biraju se tako da se razlikuju golim okom bez brojanja:
 * rijedak kratak bljesak, brzo treperenje, stalno svjetlo, mrak i dupli bljesak. */
#define IDLE_PERIOD_MS      2000u
#define IDLE_ON_MS            80u
#define LEARNING_PERIOD_MS   200u
#define LEARNING_ON_MS       100u
#define FAULT_PERIOD_MS     1600u
#define FAULT_PULSE_MS       120u
#define FAULT_GAP_MS         240u

asd_button_policy_t asd_button_default_policy(void) {
    asd_button_policy_t policy = {
        .debounce_ms = DEFAULT_DEBOUNCE_MS,
        .long_press_ms = DEFAULT_LONG_PRESS_MS,
    };
    return policy;
}

void asd_button_init(asd_button_t *btn, const asd_button_policy_t *policy,
                     int initial_pressed, uint32_t now_ms) {
    if (!btn) return;
    btn->policy = policy ? *policy : asd_button_default_policy();
    btn->stable_level = initial_pressed ? 1 : 0;
    btn->raw_level = btn->stable_level;
    btn->raw_since_ms = now_ms;
    btn->pressed_since_ms = now_ms;
    /* Ako je taster već držan pri startu, to držanje se NE broji kao pritisak.
     * Zaglavljen ili slučajno pritisnut taster pri uključenju ne smije da
     * pokrene učenje sam od sebe. */
    btn->long_fired = btn->stable_level ? 1 : 0;
    btn->initialised = 1;
}

asd_button_event_t asd_button_update(asd_button_t *btn, int pressed,
                                     uint32_t now_ms) {
    if (!btn || !btn->initialised) return ASD_BTN_NONE;
    int level = pressed ? 1 : 0;

    if (level != btn->raw_level) {
        btn->raw_level = level;
        btn->raw_since_ms = now_ms;
        return ASD_BTN_NONE;
    }

    if (level == btn->stable_level) {
        if (level && !btn->long_fired) {
            uint32_t down = now_ms - btn->pressed_since_ms;
            if (down >= btn->policy.long_press_ms) {
                btn->long_fired = 1;
                return ASD_BTN_LONG;
            }
        }
        return ASD_BTN_NONE;
    }
    /* Nenegativno oduzimanje: uint32 se prelijeva poslije ~49 dana rada, a
     * razlika dva uint32 ostaje tačna i preko prelijevanja. */
    if (now_ms - btn->raw_since_ms < btn->policy.debounce_ms) {
        return ASD_BTN_NONE;
    }

    /* Nivo se stabilizovao na novoj vrijednosti. */
    btn->stable_level = level;
    if (level) {
        btn->pressed_since_ms = btn->raw_since_ms;
        btn->long_fired = 0;
        return ASD_BTN_NONE;
    }
    /* Puštanje. Kratak pritisak se javlja tek na puštanju; dug je već javljen
     * dok je taster bio držan, pa se na puštanju ne javlja drugi put. */
    if (btn->long_fired) {
        return ASD_BTN_NONE;
    }
    return ASD_BTN_SHORT;
}

asd_ui_mode_t asd_ui_mode(asd_flow_stage_t stage, asd_state_t state) {
    switch (stage) {
        case ASD_STAGE_LEARNING:
            /* I dok uči, terminalni ishod je jači od faze: fail-closed stop se
             * mora vidjeti odmah, a ne tek kad se sesija formalno zatvori. */
            return asd_state_is_terminal(state) ? ASD_UI_FAULT : ASD_UI_LEARNING;
        case ASD_STAGE_MONITORING:
            if (asd_state_is_terminal(state)) return ASD_UI_FAULT;
            if (state == ASD_STATE_ANOMALY) return ASD_UI_ALARM;
            /* Mašine više nema: nadzor nema šta da nadzire, pa lampica ne smije
             * pokazivati „spreman". Vraća se na obrazac čekanja. */
            if (state == ASD_STATE_NO_MACHINE) return ASD_UI_IDLE;
            return ASD_UI_READY;
        case ASD_STAGE_IDLE:
        default:
            return asd_state_is_terminal(state) ? ASD_UI_FAULT : ASD_UI_IDLE;
    }
}

int asd_indicator_level(asd_ui_mode_t mode, uint32_t now_ms) {
    switch (mode) {
        case ASD_UI_READY:
            return 1;
        case ASD_UI_ALARM:
            return 0;
        case ASD_UI_LEARNING:
            return (now_ms % LEARNING_PERIOD_MS) < LEARNING_ON_MS;
        case ASD_UI_FAULT: {
            uint32_t phase = now_ms % FAULT_PERIOD_MS;
            return phase < FAULT_PULSE_MS ||
                   (phase >= FAULT_GAP_MS && phase < FAULT_GAP_MS + FAULT_PULSE_MS);
        }
        case ASD_UI_IDLE:
        default:
            return (now_ms % IDLE_PERIOD_MS) < IDLE_ON_MS;
    }
}

int asd_alarm_level(asd_ui_mode_t mode, uint32_t now_ms) {
    switch (mode) {
        case ASD_UI_ALARM:
            return 1;
        case ASD_UI_FAULT:
            /* Isti dvostruki bljesak kao zelena, ali u protivfazi: obje
             * lampice tada rade i kvar se ne moze zamijeniti sa alarmom. */
            return !asd_indicator_level(ASD_UI_FAULT, now_ms);
        default:
            return 0;
    }
}

asd_ui_command_t asd_ui_command(asd_ui_mode_t mode, asd_button_event_t event) {
    if (event == ASD_BTN_NONE) return ASD_UI_CMD_NONE;
    switch (mode) {
        case ASD_UI_IDLE:
            /* Ništa se ne gubi, pa je i kratak pritisak dovoljan. */
            return ASD_UI_CMD_START_LEARNING;
        case ASD_UI_FAULT:
            /* Poslije fail-closed stopa nema šta da se sačuva; operater
             * ponovo pokreće tok. */
            return ASD_UI_CMD_START_LEARNING;
        case ASD_UI_LEARNING:
            /* Kratak pritisak se namjerno ignoriše: slučajan dodir tokom
             * kalibracije ne smije da je prekine. */
            return event == ASD_BTN_LONG ? ASD_UI_CMD_ABORT : ASD_UI_CMD_NONE;
        case ASD_UI_READY:
        case ASD_UI_ALARM:
            /* Naučeni centar postoji. Odbacuje ga samo dug pritisak, i to je
             * jedini put do novog centra — automatskog nema. */
            return event == ASD_BTN_LONG ? ASD_UI_CMD_START_LEARNING
                                         : ASD_UI_CMD_NONE;
        default:
            return ASD_UI_CMD_NONE;
    }
}

int asd_ui_command_discards_calibration(asd_ui_mode_t mode,
                                        asd_ui_command_t command) {
    if (command != ASD_UI_CMD_START_LEARNING) return 0;
    /* Centar postoji samo poslije prihvaćene kalibracije. IDLE i FAULT ga
     * nemaju, pa tu nema šta da se odbaci. */
    return mode == ASD_UI_READY || mode == ASD_UI_ALARM;
}

const char *asd_ui_mode_name(asd_ui_mode_t mode) {
    switch (mode) {
        case ASD_UI_IDLE: return "IDLE";
        case ASD_UI_LEARNING: return "LEARNING";
        case ASD_UI_READY: return "READY";
        case ASD_UI_ALARM: return "ALARM";
        case ASD_UI_FAULT: return "FAULT";
        default: return "UNKNOWN_MODE";
    }
}

const char *asd_button_event_name(asd_button_event_t event) {
    switch (event) {
        case ASD_BTN_NONE: return "NONE";
        case ASD_BTN_SHORT: return "SHORT";
        case ASD_BTN_LONG: return "LONG";
        default: return "UNKNOWN_EVENT";
    }
}

const char *asd_ui_command_name(asd_ui_command_t command) {
    switch (command) {
        case ASD_UI_CMD_NONE: return "NONE";
        case ASD_UI_CMD_START_LEARNING: return "START_LEARNING";
        case ASD_UI_CMD_ABORT: return "ABORT";
        default: return "UNKNOWN_COMMAND";
    }
}

const char *asd_flow_stage_name(asd_flow_stage_t stage) {
    switch (stage) {
        case ASD_STAGE_IDLE: return "IDLE";
        case ASD_STAGE_LEARNING: return "LEARNING";
        case ASD_STAGE_MONITORING: return "MONITORING";
        default: return "UNKNOWN_STAGE";
    }
}
