/* Vidi asd_cmd.h. */
#include "asd_cmd.h"
#include "e5_measure.h"

#include <stdatomic.h>
#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "soc/soc_caps.h"
#include "hal/uart_ll.h"
#if SOC_USB_SERIAL_JTAG_SUPPORTED
#include "hal/usb_serial_jtag_ll.h"
#endif

#include "audio_quality_state.h"   /* ASD_QUALITY_PROTOCOL */

#define CMD_TICK_MS   20   /* isti period kao UI task; komande su rijetke */
#define CMD_MAX_LEN   16   /* najduža komanda je "GUIDED25" */

/* Dva porta su dva NEZAVISNA toka i moraju imati dva odvojena bafera reda.
 *
 * Sa jednim zajednickim baferom, ista komanda koja stigne na oba porta u istom
 * trenutku isprepletala je bajtove: "HOLD" + "HOLD" -> "HHOOLLDD", pa
 * `unknown_command`. To se desilo cim je host poceo da salje na oba porta
 * (izmjereno 16.08.2026, run `cold-start-06`) -- dotad je USB put bio mrtav pa
 * se sudar nije mogao vidjeti. */
typedef enum { SRC_USB = 0, SRC_UART, SRC_COUNT } cmd_source_t;

typedef struct {
    char buf[CMD_MAX_LEN];
    int len;
    int overflow;
} cmd_line_t;

static _Atomic int pending_event = ASD_BTN_NONE;
static _Atomic int pending_workflow = ASD_WORKFLOW_DEFAULT;
static _Atomic int session_active;
static cmd_line_t lines[SRC_COUNT];

/* Provenijencija. Zaključani host parser ne prepoznaje `VBUTTON` i uredno ga
 * preskače (u regexu nema granice riječi ispred `BUTTON`), pa red ne može
 * pokvariti prolaz — a ostaje u `serial.raw` i `serial.log` kao dokaz da je
 * pritisak stigao sa hosta, a ne sa pina. Sam pritisak se poslije prijavljuje
 * običnim `BUTTON` redom, isto kao fizički. */
static void emit_vbutton(const char *event, const char *result) {
    printf("VBUTTON protocol=%s source=console event=%s result=%s\n",
           ASD_QUALITY_PROTOCOL, event, result);
}

static void dispatch(const char *cmd) {
    if (e5_measure_command(cmd)) return;
    if (strcmp(cmd, "PRESS") == 0) {
        atomic_store(&pending_event, ASD_BTN_SHORT);
        emit_vbutton("SHORT", "accepted");
    } else if (strcmp(cmd, "HOLD") == 0) {
        atomic_store(&pending_event, ASD_BTN_LONG);
        emit_vbutton("LONG", "accepted");
    } else if (strcmp(cmd, "GUIDED25") == 0) {
        if (atomic_load(&session_active)) {
            printf("VWORKFLOW mode=GUIDED25 result=busy_session\n");
        } else {
            atomic_store(&pending_workflow, ASD_WORKFLOW_GUIDED25);
            printf("VWORKFLOW mode=GUIDED25 result=accepted\n");
        }
    } else {
        emit_vbutton("NONE", "unknown_command");
    }
}

static void feed(cmd_source_t src, uint8_t byte) {
    cmd_line_t *line = &lines[src];
    if (byte == '\r' || byte == '\n') {
        if (line->overflow) {
            emit_vbutton("NONE", "unknown_command");
        } else if (line->len > 0) {
            line->buf[line->len] = '\0';
            dispatch(line->buf);
        }
        line->len = 0;
        line->overflow = 0;
        return;
    }
    /* Predugačak red se odbacuje cijeli, da se njegov rep ne protumači kao
     * zasebna komanda. */
    if (line->len >= CMD_MAX_LEN - 1) {
        line->overflow = 1;
        return;
    }
    if (byte >= 'a' && byte <= 'z') byte = (uint8_t)(byte - 'a' + 'A');
    line->buf[line->len++] = (char)byte;
}

/* Oba periferijala se samo prazne iz svog RX FIFO-a. Ništa se ne instalira i
 * ništa se ne preusmjerava, pa TX put ostaje netaknut. */
static void poll_sources(void) {
    uint8_t buf[32];

#if SOC_USB_SERIAL_JTAG_SUPPORTED
    /* Periferija drzi primljeni OUT paket dok se status prijema ne obrise, i
     * do tada NE prima sljedeci. Bez ovog brisanja radi samo prva komanda
     * poslije boota, a svaka sljedeca nikad ne stigne (izmjereno 16.08.2026:
     * dva `PRESS` preko COM3 bez ijednog `VBUTTON`). */
    int total = 0;
    while (usb_serial_jtag_ll_rxfifo_data_available()) {
        int n = usb_serial_jtag_ll_read_rxfifo(buf, sizeof(buf));
        if (n <= 0) break;
        for (int i = 0; i < n; i++) feed(SRC_USB, buf[i]);
        total += n;
    }
    if (total > 0)
        usb_serial_jtag_ll_clr_intsts_mask(USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT);
#endif

    uart_dev_t *uart0 = UART_LL_GET_HW(0);
    for (;;) {
        uint32_t avail = uart_ll_get_rxfifo_len(uart0);
        if (avail == 0) break;
        if (avail > sizeof(buf)) avail = sizeof(buf);
        uart_ll_read_rxfifo(uart0, buf, avail);
        for (uint32_t i = 0; i < avail; i++) feed(SRC_UART, buf[i]);
    }
}

static void cmd_task(void *arg) {
    (void)arg;
    for (;;) {
        poll_sources();
        vTaskDelay(pdMS_TO_TICKS(CMD_TICK_MS));
    }
}

void asd_cmd_start(void) {
    memset(lines, 0, sizeof(lines));
    atomic_store(&pending_event, ASD_BTN_NONE);
    atomic_store(&pending_workflow, ASD_WORKFLOW_DEFAULT);
    atomic_store(&session_active, 0);
    /* 3 KB: task zove `printf` sa tri `%s` argumenta, isto kao UI task. */
    xTaskCreatePinnedToCore(cmd_task, "asd_cmd", 3072, NULL, 4, NULL, 0);
}

void asd_cmd_set_session_active(int active) {
    atomic_store(&session_active, active ? 1 : 0);
}

asd_workflow_t asd_cmd_take_workflow(void) {
    return (asd_workflow_t)atomic_exchange(&pending_workflow, ASD_WORKFLOW_DEFAULT);
}

asd_workflow_t asd_cmd_pending_workflow(void) {
    return (asd_workflow_t)atomic_load(&pending_workflow);
}

const char *asd_cmd_workflow_name(asd_workflow_t workflow) {
    return workflow == ASD_WORKFLOW_GUIDED25 ? "GUIDED25" : "DEFAULT";
}

asd_button_event_t asd_cmd_take_event(void) {
    return (asd_button_event_t)atomic_exchange(&pending_event, ASD_BTN_NONE);
}
