#include "audio_i2s.h"
#include "pins.h"

#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/ringbuf.h"
#include "driver/i2s_std.h"
#include "esp_heap_caps.h"
#include "esp_log.h"

static const char *TAG = "audio";

#define DMA_FRAME_NUM  1024   /* uzoraka po DMA deskriptoru */
#define DMA_DESC_NUM   4
#define READ_CHUNK     1024   /* uzoraka po i2s_channel_read pozivu */

/* INMP441 i I2S se sliježu poslije uključenja. Izmjereno na pločici 11.08.2026,
 * prva tri bloka od 256 ms daju rms -4,1 / -18,0 / -35,4 dBFS uz dc
 * -6410 / -7378 / -1011 i peak 29968 / 17047 / 2325, dok je ustaljeno stanje
 * rms ~-46 dBFS uz dc ~-0,4 (mjereno 06.08.2026). Amplituda tranzijenta se
 * mijenja od reseta do reseta, pa se ne može tolerisati pragom.
 *
 * Tranzijent nije zvuk i odbacuje se jednokratno NA IZVORU, prije nego uđe u
 * ring buffer, u `raw_peak` ili u ocjenu kvaliteta. Dva razloga:
 *   1. fail-closed gate iz Faze 1 ocjenjuje i prvi WAIT blok, pa je prolaz
 *      padao na `CLIPPING` u tri od četiri reseta;
 *   2. `raw_peak` je dokaz kojim je zatvoren rizik C1 (rezerva do klipovanja) —
 *      tranzijent od 29968 bi tu rezervu prikazao lažno malom.
 *
 * Ovo nije `warn and continue` i ne popušta ni jedan gate: mjerni prozor počinje
 * kad se senzor ustali, a svaki blok koji uđe u lanac se i dalje ocjenjuje. */
#define SETTLE_SAMPLES (AUDIO_SR)   /* 1,0 s */

static i2s_chan_handle_t rx_chan;
static RingbufHandle_t ring;
static uint32_t dropped;
static int32_t raw_peak;
static size_t settle_remaining = SETTLE_SAMPLES;

/* Capture task: I2S (32-bit slot) -> 16-bit PCM -> ring buffer u PSRAM-u.
 * Visok prioritet, pinovan na core 0 (inference ide na core 1) — rizik C4. */
static void capture_task(void *arg) {
    static int32_t raw[READ_CHUNK];
    static int16_t pcm[READ_CHUNK];
    size_t nbytes;
    while (1) {
        if (i2s_channel_read(rx_chan, raw, sizeof(raw), &nbytes, portMAX_DELAY) != ESP_OK)
            continue;
        size_t n = nbytes / sizeof(int32_t);

        /* Preskoči period slijeganja; poslednji preskočeni blok je obično
         * djelimičan, pa se ostatak istog bloka normalno obrađuje. */
        size_t off = 0;
        if (settle_remaining) {
            off = n < settle_remaining ? n : settle_remaining;
            settle_remaining -= off;
            if (off == n) continue;
        }

        /* INMP441: 24-bit MSB u 32-bit slotu -> >>14 daje pun 16-bit opseg
         * (provjeri amplitudu na WAV testu, rizik C1) */
        for (size_t i = off; i < n; i++) {
            int32_t a = raw[i] < 0 ? -raw[i] : raw[i];
            if (a > raw_peak) raw_peak = a;
            pcm[i - off] = (int16_t)(raw[i] >> 14);
        }
        size_t out = n - off;
        if (xRingbufferSend(ring, pcm, out * sizeof(int16_t), 0) != pdTRUE)
            dropped += out;
    }
}

esp_err_t audio_i2s_init(void) {
    /* Ring buffer: PSRAM ako postoji, inače interni SRAM (2 s @ 16 kHz 16-bit
     * = 64 KB — staje i na klasični ESP32). DMA baferi drajvera ostaju u
     * internom SRAM-u u oba slučaja (S3 DMA ne vidi PSRAM). */
    static StaticRingbuffer_t rb_struct;
    const size_t ring_bytes = AUDIO_RING_LEN * sizeof(int16_t);
    uint8_t *rb_storage = heap_caps_malloc(ring_bytes, MALLOC_CAP_SPIRAM);
    if (!rb_storage) {
        rb_storage = heap_caps_malloc(ring_bytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
        ESP_LOGI(TAG, "ring buffer u internom SRAM-u (%u B)", (unsigned)ring_bytes);
    }
    if (!rb_storage) return ESP_ERR_NO_MEM;
    ring = xRingbufferCreateStatic(ring_bytes, RINGBUF_TYPE_BYTEBUF, rb_storage, &rb_struct);
    if (!ring) return ESP_ERR_NO_MEM;

    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
    chan_cfg.dma_desc_num = DMA_DESC_NUM;
    chan_cfg.dma_frame_num = DMA_FRAME_NUM;
    ESP_ERROR_CHECK(i2s_new_channel(&chan_cfg, NULL, &rx_chan));

    i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(AUDIO_SR),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT,
                                                        I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = PIN_I2S_BCLK,
            .ws = PIN_I2S_WS,
            .dout = I2S_GPIO_UNUSED,
            .din = PIN_I2S_DIN,
        },
    };
    /* INMP441 L/R na GND -> podaci u lijevom slotu */
    std_cfg.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT;
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(rx_chan, &std_cfg));
    return ESP_OK;
}

esp_err_t audio_i2s_start(void) {
    ESP_ERROR_CHECK(i2s_channel_enable(rx_chan));
    BaseType_t ok = xTaskCreatePinnedToCore(capture_task, "audio_cap", 4096, NULL,
                                            configMAX_PRIORITIES - 2, NULL, 0);
    return ok == pdPASS ? ESP_OK : ESP_FAIL;
}

size_t audio_read(int16_t *dst, size_t n_samples) {
    size_t got = 0;
    while (got < n_samples) {
        size_t item_size;
        int16_t *p = xRingbufferReceiveUpTo(ring, &item_size, portMAX_DELAY,
                                            (n_samples - got) * sizeof(int16_t));
        if (!p) break;
        memcpy(dst + got, p, item_size);
        vRingbufferReturnItem(ring, p);
        got += item_size / sizeof(int16_t);
    }
    return got;
}

uint32_t audio_dropped_samples(void) { return dropped; }

int32_t audio_raw_peak(void) { return raw_peak; }
void    audio_raw_peak_reset(void) { raw_peak = 0; }
