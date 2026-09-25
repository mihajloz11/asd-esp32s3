/* Virtuelni taster: red teksta sa konzole kao drugi ulaz za istu radnju
 * operatera, dok fizicki taster nije zalemljen.
 *
 * Modul nista ne odlucuje. Pretvara red u asd_button_event_t, a dalje ide
 * isti asd_ui_command() kao za fizicki taster, pa se ponasanje ne moze
 * razici.
 *
 * Komande (jedan red, CR ili LF, bez obzira na velika slova):
 *   PRESS   kratak pritisak -> u IDLE pokrece ucenje
 *   HOLD    dug pritisak    -> odbacuje centar i pokrece novo ucenje
 *
 * Cita oba porta (native USB i CH343 na UART0) direktno iz RX FIFO-a, bez
 * drajvera i VFS-a, pa serijski ispis ostaje netaknut.
 */
#ifndef ASD_CMD_H
#define ASD_CMD_H

#include "asd_operator.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Pokreće task koji osluškuje konzolu. Zove se jednom, prije UI taska. */
void asd_cmd_start(void);

typedef enum {
    ASD_WORKFLOW_DEFAULT = 0,
    ASD_WORKFLOW_GUIDED25
} asd_workflow_t;

/* GUIDED25 can only be armed while no session is active. It changes only the
 * commissioning counts; PRESS and the physical button still share one path. */
void asd_cmd_set_session_active(int active);
asd_workflow_t asd_cmd_take_workflow(void);
const char *asd_cmd_workflow_name(asd_workflow_t workflow);
asd_workflow_t asd_cmd_pending_workflow(void);

/* Uzima i briše zaostali virtuelni pritisak; `ASD_BTN_NONE` ako ga nema.
 * Poziva ga UI task na istom mjestu gdje čita i fizički pin. */
asd_button_event_t asd_cmd_take_event(void);

#ifdef __cplusplus
}
#endif

#endif
