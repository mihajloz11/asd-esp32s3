/* Operaterski tok — taster koji pokreće učenje i lampica koja javlja dokle se
 * stiglo.
 *
 * Host-testabilno, bez ESP-IDF/GPIO zavisnosti, isti obrazac kao
 * `audio_quality_state.c` i `asd_events.c`. Živi firmware dovodi sirovo stanje
 * pina i vrijeme; host testovi dovode iste ulaze kao determinističke fixture.
 *
 * ZAŠTO POSTOJI. Do sada je uređaj kretao u kalibraciju čim se upali, pa je
 * operater morao da pogodi trenutak uključenja ventilatora. Taster to obrće:
 * uređaj čeka, operater pusti ventilator, provjeri da radi normalno, pa
 * pritisne. Lampica zatim javlja kad je učenje gotovo, jer bez nje operater ne
 * zna kada smije da izazove kvar.
 *
 * DVA PRAVILA KOJA OVAJ MODUL NOSI U KODU:
 *
 *   1. Kratak pritisak NIKAD ne odbacuje naučeni centar. Odbacivanje traži
 *      dug pritisak. Slučajan dodir tokom kalibracije ne smije da je pokvari.
 *   2. Nema automatskog ponovnog učenja. Svaki novi centar dolazi od
 *      eksplicitne radnje operatera i zapisuje se kao takav
 *      (docs/problemi-i-rjesenja.md P10 — tiha rekalibracija bi naučila kvar
 *      kao normalu).
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
    ASD_STAGE_IDLE = 0,      /* nema sesije: uređaj čeka taster */
    ASD_STAGE_LEARNING,      /* WAIT + CAL: sluša i uči normalan rad */
    ASD_STAGE_MONITORING     /* DET: centar je zamrznut, nadzire */
} asd_flow_stage_t;

/* Šta lampica pokazuje. Pet obrazaca, razlučivih golim okom. */
typedef enum {
    ASD_UI_IDLE = 0,   /* kratak bljesak na 2 s: živ sam, čekam taster */
    ASD_UI_LEARNING,   /* brzo treperi 5 Hz: učim, ne diraj ventilator */
    ASD_UI_READY,      /* stalno svijetli: UČENJE GOTOVO, nadzirem, normalno */
    ASD_UI_ALARM,      /* ugašena: trajno odstupanje */
    ASD_UI_FAULT       /* dvostruki bljesak: fail-closed stop, treba restart */
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

/* Jedan uzorak pina ulazi, najviše jedan događaj izlazi. Deterministički:
 * isti niz (pressed, now_ms) uvijek daje isti niz događaja.
 *
 * `pressed` je LOGIČKI nivo (1 = pritisnut). Pretvaranje iz active-low pina
 * radi pozivalac, da modul ne zna ništa o hardveru. */
asd_button_event_t asd_button_update(asd_button_t *btn, int pressed,
                                     uint32_t now_ms);

/* Faza toka + stanje kalibracije -> šta lampica pokazuje. */
asd_ui_mode_t asd_ui_mode(asd_flow_stage_t stage, asd_state_t state);

/* Nivo statusne (zelene) lampice. Čista funkcija vremena: nema internog
 * brojača, pa je obrazac isti bez obzira kada se pozove. */
int asd_indicator_level(asd_ui_mode_t mode, uint32_t now_ms);

/* Nivo alarmne (crvene) lampice. Svijetli samo dok traje odstupanje, i
 * treperi u fail-closed stanju. Redundantna je sa zelenom po informaciji,
 * ali razlikuje „ugašena zelena" od „uređaj mrtav" — što se na snimku
 * demoa inače ne vidi. */
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
