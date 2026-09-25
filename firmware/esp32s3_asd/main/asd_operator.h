/* Operaterski tok: taster pokrece ucenje, lampice javljaju dokle se stiglo.
 *
 * Bez ESP-IDF/GPIO zavisnosti; firmware dovodi stanje pina i vrijeme, host
 * testovi iste ulaze kao fixture.
 *
 * Dva pravila zive u kodu:
 *   1. Kratak pritisak NIKAD ne odbacuje nauceni centar; za to treba dug
 *      pritisak, da slucajan dodir ne pokvari kalibraciju.
 *   2. Nema automatskog ponovnog ucenja. Svaki novi centar dolazi od
 *      eksplicitne radnje operatera (P10).
 */
#ifndef ASD_OPERATOR_H
#define ASD_OPERATOR_H

#include <stdint.h>

#include "audio_quality_state.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ASD_OPERATOR_PROTOCOL "asd-operator-v1.0.0"

/* Faza toka, onako kako je vidi operater — ne isto što i `asd_state_t`, koji
 * je činjenica o kalibraciji. */
typedef enum {
    ASD_STAGE_IDLE = 0,
    ASD_STAGE_CENTER_LEARNING,
    ASD_STAGE_MONITORING,
    ASD_STAGE_SETTLE,
    ASD_STAGE_COMMISSION_DERIVE,
    ASD_STAGE_COMMISSION_VERIFY
} asd_flow_stage_t;

/* Source compatibility while psd_live migrates its legacy local name. */
#define ASD_STAGE_LEARNING ASD_STAGE_CENTER_LEARNING

/* Šta lampica pokazuje. Pet obrazaca, razlučivih golim okom. */
typedef enum {
    ASD_UI_IDLE = 0,   /* kratak bljesak na 2 s: živ sam, čekam taster */
    ASD_UI_LEARNING,   /* brzo treperi 5 Hz: učim, ne diraj ventilator */
    ASD_UI_READY,      /* stalno svijetli: UČENJE GOTOVO, nadzirem, normalno */
    ASD_UI_ALARM,      /* ugašena: trajno odstupanje */
    ASD_UI_FAULT,      /* dvostruki bljesak: fail-closed stop, treba restart */
    ASD_UI_HOLD        /* sporo treperi: moguca smetnja / cekam */
} asd_ui_mode_t;

typedef enum {
    ASD_BTN_NONE = 0,
    ASD_BTN_SHORT,     /* pritisnut i pušten prije praga dugog pritiska */
    ASD_BTN_LONG       /* zadržan preko praga; javlja se JEDNOM, dok je još držan */
} asd_button_event_t;

typedef enum {
    ASD_UI_CMD_NONE = 0,
    ASD_UI_CMD_START_LEARNING, /* pokreni novu sesiju učenja */
    ASD_UI_CMD_ABORT           /* prekini sesiju u toku, vrati se u IDLE */
} asd_ui_command_t;

typedef struct {
    uint32_t debounce_ms;    /* koliko dugo nivo mora biti stabilan */
    uint32_t long_press_ms;  /* prag dugog pritiska */
} asd_button_policy_t;

typedef struct {
    int stable_level;         /* odbounceovan nivo: 1 = pritisnut */
    int raw_level;            /* poslednji sirovi nivo */
    uint32_t raw_since_ms;    /* otkad sirovi nivo drži istu vrijednost */
    uint32_t pressed_since_ms;/* otkad je stabilno pritisnut */
    int long_fired;           /* dug pritisak je već prijavljen u ovom držanju */
    int initialised;
    asd_button_policy_t policy;
} asd_button_t;

asd_button_policy_t asd_button_default_policy(void);

void asd_button_init(asd_button_t *btn, const asd_button_policy_t *policy,
                     int initial_pressed, uint32_t now_ms);

/* Jedan uzorak pina ulazi, najvise jedan dogadjaj izlazi; isti niz
 * (pressed, now_ms) uvijek daje isti niz dogadjaja. `pressed` je logicki
 * nivo (1 = pritisnut); active-low pretvara pozivalac. */
asd_button_event_t asd_button_update(asd_button_t *btn, int pressed,
                                     uint32_t now_ms);

/* Faza toka + stanje kalibracije -> šta lampica pokazuje. */
asd_ui_mode_t asd_ui_mode(asd_flow_stage_t stage, asd_state_t state);

/* Nivo statusne (zelene) lampice. Čista funkcija vremena: nema internog
 * brojača, pa je obrazac isti bez obzira kada se pozove. */
int asd_indicator_level(asd_ui_mode_t mode, uint32_t now_ms);

/* Crvena lampica: svijetli dok traje odstupanje, treperi u fail-closed
 * stanju. Razlikuje "ugasena zelena" od "uredjaj mrtav". */
int asd_alarm_level(asd_ui_mode_t mode, uint32_t now_ms);

/* Šta pritisak znači u datom režimu. Ovdje živi pravilo da kratak pritisak
 * nikad ne odbacuje naučeni centar. */
asd_ui_command_t asd_ui_command(asd_ui_mode_t mode, asd_button_event_t event);

/* 1 ako bi ova komanda odbacila već naučeni centar. Pozivalac to mora
 * zapisati kao operaterovu odluku, ne kao automatsku rekalibraciju. */
int asd_ui_command_discards_calibration(asd_ui_mode_t mode,
                                        asd_ui_command_t command);

const char *asd_ui_mode_name(asd_ui_mode_t mode);
const char *asd_button_event_name(asd_button_event_t event);
const char *asd_ui_command_name(asd_ui_command_t command);
const char *asd_flow_stage_name(asd_flow_stage_t stage);

#ifdef __cplusplus
}
#endif

#endif
