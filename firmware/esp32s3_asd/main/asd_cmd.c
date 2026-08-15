/* Vidi asd_cmd.h. */
#include "asd_cmd.h"

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
#define CMD_MAX_LEN   16   /* najduža komanda je "PRESS" */

static _Atomic int pending_event = ASD_BTN_NONE;
static char line_buf[CMD_MAX_LEN];
static int line_len;
static int line_overflow;

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
    if (strcmp(cmd, "PRESS") == 0) {
        atomic_store(&pending_event, ASD_BTN_SHORT);
        emit_vbutton("SHORT", "accepted");
    } else if (strcmp(cmd, "HOLD") == 0) {
        atomic_store(&pending_event, ASD_BTN_LONG);
        emit_vbutton("LONG", "accepted");
    } else {
        emit_vbutton("NONE", "unknown_command");
    }
}

static void feed(uint8_t byte) {
    if (byte == '\r' || byte == '\n') {
        if (line_overflow) {
            emit_vbutton("NONE", "unknown_command");
        } else if (line_len > 0) {
            line_buf[line_len] = '\0';
            dispatch(line_buf);
        }
        line_len = 0;
        line_overflow = 0;
        return;
    }
    /* Predugačak red se odbacuje cijeli, da se njegov rep ne protumači kao
     * zasebna komanda. */
    if (line_len >= CMD_MAX_LEN - 1) {
        line_overflow = 1;
        return;
    }
    if (byte >= 'a' && byte <= 'z') byte = (uint8_t)(byte - 'a' + 'A');
    line_buf[line_len++] = (char)byte;
}

/* Oba periferijala se samo prazne iz svog RX FIFO-a. Ništa se ne instalira i
 * ništa se ne preusmjerava, pa TX put ostaje netaknut. */
static void poll_sources(void) {
    uint8_t buf[32];

#if SOC_USB_SERIAL_JTAG_SUPPORTED
    while (usb_serial_jtag_ll_rxfifo_data_available()) {
        int n = usb_serial_jtag_ll_read_rxfifo(buf, sizeof(buf));
        if (n <= 0) break;
        for (int i = 0; i < n; i++) feed(buf[i]);
    }
#endif

    uart_dev_t *uart0 = UART_LL_GET_HW(0);
    for (;;) {
        uint32_t avail = uart_ll_get_rxfifo_len(uart0);
        if (avail == 0) break;
        if (avail > sizeof(buf)) avail = sizeof(buf);
        uart_ll_read_rxfifo(uart0, buf, avail);
        for (uint32_t i = 0; i < avail; i++) feed(buf[i]);
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
    line_len = 0;
    atomic_store(&pending_event, ASD_BTN_NONE);
    /* 3 KB: task zove `printf` sa tri `%s` argumenta, isto kao UI task. */
    xTaskCreatePinnedToCore(cmd_task, "asd_cmd", 3072, NULL, 4, NULL, 0);
}

asd_button_event_t asd_cmd_take_event(void) {
    return (asd_button_event_t)atomic_exchange(&pending_event, ASD_BTN_NONE);
}
