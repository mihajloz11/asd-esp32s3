/* Virtuelni taster — softverska alternativa fizičkom tasteru na GPIO.
 *
 * ZAŠTO POSTOJI. `asd_operator.c` traži eksplicitnu operaterovu radnju za
 * svako učenje (P10: tiha rekalibracija bi naučila kvar kao normalu). Dok
 * taster nije zalemljen, ta radnja nema kako da stigne do uređaja i ploča
 * stoji u IDLE zauvijek. Ovaj modul otvara drugi ulaz za istu radnju: red
 * teksta sa konzole.
 *
 * ŠTA OVAJ MODUL NE RADI. Ne odlučuje ništa. Ne zna šta pritisak znači, ne
 * dira kalibraciju i ne pravi novu semantiku. Pretvara red teksta u
 * `asd_button_event_t` i tu staje; sve dalje radi isti `asd_ui_command()`
 * koji obrađuje i fizički taster. Zato virtuelni i fizički pritisak ne mogu
 * da se raziđu u ponašanju — dijele cijeli put poslije ove tačke.
 *
 * KOMANDE (jedan red, CR ili LF na kraju, velika ili mala slova):
 *
 *   PRESS   kratak pritisak  -> u IDLE pokreće učenje
 *   HOLD    dug pritisak     -> odbacuje naučeni centar i pokreće novo učenje
 *
 * ČITA SA OBA PORTA. ESP32-S3 devkit se javlja i kao native USB (VID 303A,
 * kod nas COM3) i kao CH343 most na UART0 (COM4). Koji je od ta dva u
 * upotrebi zavisi od kabla, pa se oba prozivaju — komanda radi bez obzira
 * na to gdje je alat zakačen.
 *
 * NE DIRA IZLAZ. Čita se direktno iz RX FIFO-a oba periferijala, bez
 * instaliranja drajvera i bez VFS preusmjeravanja. Serijski ispis
 * (`printf`, `ESP_LOG`) ostaje na tačno istom putu kao prije, jer zaključani
 * protokol `asd-quality-v1.3.0` zavisi od njega.
 */
#ifndef ASD_CMD_H
#define ASD_CMD_H

#include "asd_operator.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Pokreće task koji osluškuje konzolu. Zove se jednom, prije UI taska. */
void asd_cmd_start(void);

/* Uzima i briše zaostali virtuelni pritisak; `ASD_BTN_NONE` ako ga nema.
 * Poziva ga UI task na istom mjestu gdje čita i fizički pin. */
asd_button_event_t asd_cmd_take_event(void);

#ifdef __cplusplus
}
#endif

#endif
