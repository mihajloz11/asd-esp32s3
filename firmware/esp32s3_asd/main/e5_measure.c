/* E5 instrumentation only. Model/feature/quality implementations are unchanged.
 * Triggered conversions keep all four data registers stable until the next
 * trigger. No per-sample UART or flash writes occur during E5RUN.
 */
#include "e5_measure.h"
#ifdef ASD_E5_MEASURE
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include "esp_partition.h"
#include "esp_crc.h"
#include "esp_system.h"
#include "esp_app_desc.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "driver/gpio.h"
#include "ina226.h"
#include "audio_i2s.h"
#include "psd_features_c.h"

#define MAX_SAMPLES 20000
#define RUN_US 60000000LL
#define TRIGGER_CONFIG 0x4123 /* AVG=1; bus/shunt 1.1 ms; triggered both */
enum { OTHER, CAPTURE_WAIT, DSP, SCORE, MIXED };
static const char *phase_names[] = {"OTHER", "CAPTURE_WAIT", "DSP", "SCORE", "MIXED"};
typedef struct {
    int64_t trigger_us, ready_us;
    int32_t bus_uv, shunt_nv, current_ua, power_uw;
    uint32_t sequence;
    uint16_t mask;
    uint8_t phase;
} sample_t;
static sample_t *samples;
static unsigned count;
static _Atomic int pending, busy, stop_requested, recording;
static int available;
static portMUX_TYPE phase_lock = portMUX_INITIALIZER_UNLOCKED;
static unsigned phase_now, phase_sequence;
static int64_t phase_since, phase_time[4];
static int64_t run_start, run_end;
static unsigned errors;
static esp_timer_handle_t conversion_timer;
static TaskHandle_t measurement_task;
static const esp_partition_t *store_partition;
static int store_writable;
static unsigned boot_delay_s;
static _Atomic unsigned requested_delay_s;
static uint8_t run_firmware_sha[32];
/* Unallocated last 2 MiB of this 32 MiB board; registered at runtime with
 * overlap checks. Existing partition table, FAT clips and NVS are preserved. */
#define STORE_MAGIC 0x45355231u
typedef struct {
    uint32_t magic, version, sample_size, count, errors, data_crc, header_crc;
    uint8_t firmware_sha[32];
    int64_t start, end, phase_time[4];
} stored_header_t;

static int load_saved(void) {
    stored_header_t h;
    if (!store_partition || esp_partition_read(store_partition, 0, &h, sizeof(h)) != ESP_OK)
        return 0;
    uint32_t header_crc = h.header_crc;
    h.header_crc = 0;
    if (h.magic != STORE_MAGIC || h.version != 1 || h.sample_size != sizeof(sample_t) ||
        h.count > MAX_SAMPLES || header_crc != esp_crc32_le(0, (uint8_t *)&h, sizeof(h))) return 0;
    size_t bytes = h.count * sizeof(sample_t);
    uint32_t crc = 0;
    uint8_t block[256];
    for (size_t off = 0; off < bytes; off += sizeof(block)) {
        size_t n = bytes - off < sizeof(block) ? bytes - off : sizeof(block);
        if (esp_partition_read(store_partition, 4096 + off, block, n) != ESP_OK) return 0;
        crc = esp_crc32_le(crc, block, n);
    }
    if (h.data_crc != crc || esp_partition_read(store_partition, 4096, samples, bytes) != ESP_OK) return 0;
    count = h.count; errors = h.errors; run_start = h.start; run_end = h.end;
    memcpy(phase_time, h.phase_time, sizeof(phase_time));
    memcpy(run_firmware_sha, h.firmware_sha, sizeof(run_firmware_sha));
    return 1;
}

static void init_store(void) {
    esp_err_t err = esp_partition_register_external(NULL, 0x1e00000, 0x200000,
        "e5_store", ESP_PARTITION_TYPE_DATA, 0x40, &store_partition);
    if (err != ESP_OK) { printf("E5ERROR op=STORE_INIT error=%s\n", esp_err_to_name(err)); return; }
    if (load_saved()) { store_writable = 1; printf("E5SAVED_AVAILABLE samples=%u\n", count); return; }
    uint8_t block[256];
    for (size_t off = 0; off < store_partition->size; off += sizeof(block)) {
        if (esp_partition_read(store_partition, off, block, sizeof(block)) != ESP_OK) return;
        for (unsigned i = 0; i < sizeof(block); i++) {
            if (block[i] != 0xff) { printf("E5ERROR op=STORE_INIT error=REGION_NOT_EMPTY_OR_INVALID\n"); return; }
        }
    }
    store_writable = 1;
}

static esp_err_t save_samples(void) {
    if (!store_writable || !store_partition) return ESP_ERR_INVALID_STATE;
    stored_header_t h = {0};
    h.magic = STORE_MAGIC; h.version = 1; h.sample_size = sizeof(sample_t);
    h.count = count; h.errors = errors; h.start = run_start; h.end = run_end;
    memcpy(h.phase_time, phase_time, sizeof(phase_time));
    memcpy(h.firmware_sha, run_firmware_sha, sizeof(run_firmware_sha));
    size_t bytes = count * sizeof(sample_t);
    h.data_crc = esp_crc32_le(0, (uint8_t *)samples, bytes);
    h.header_crc = esp_crc32_le(0, (uint8_t *)&h, sizeof(h));
    esp_err_t err = esp_partition_erase_range(store_partition, 0, store_partition->size);
    if (err != ESP_OK) return err;
    for (size_t off = 0; off < bytes; off += 4096) {
        size_t n = bytes - off < 4096 ? bytes - off : 4096;
        err = esp_partition_write(store_partition, 4096 + off, (uint8_t *)samples + off, n);
        if (err != ESP_OK) return err;
        vTaskDelay(1);
    }
    /* Commit header last. A torn write never becomes a valid saved result. */
    return esp_partition_write(store_partition, 0, &h, sizeof(h));
}

static esp_err_t arm_next_boot(unsigned seconds) {
    nvs_handle_t h;
    esp_err_t err = nvs_open("e5_measure", NVS_READWRITE, &h);
    if (err != ESP_OK) return err;
    err = nvs_set_u32(h, "delay_s", seconds);
    if (err == ESP_OK) err = nvs_commit(h);
    nvs_close(h);
    return err;
}

static void conversion_ready(void *arg) {
    (void)arg;
    xTaskNotifyGive(measurement_task);
}

static unsigned phase_set(unsigned next) {
    if (!atomic_load(&recording)) return OTHER;
    portENTER_CRITICAL(&phase_lock);
    if (!atomic_load(&recording)) { portEXIT_CRITICAL(&phase_lock); return OTHER; }
    unsigned previous = phase_now;
    int64_t now = esp_timer_get_time();
    phase_time[previous] += now - phase_since;
    phase_since = now;
    phase_now = next;
    phase_sequence++;
    gpio_set_level(GPIO_NUM_12, next == CAPTURE_WAIT);
    gpio_set_level(GPIO_NUM_13, next == DSP);
    gpio_set_level(GPIO_NUM_14, next == SCORE);
    portEXIT_CRITICAL(&phase_lock);
    return previous;
}

static void phase_snapshot(unsigned *phase, unsigned *sequence) {
    portENTER_CRITICAL(&phase_lock);
    *phase = phase_now;
    *sequence = phase_sequence;
    portEXIT_CRITICAL(&phase_lock);
}

/* Link wrappers call the exact existing implementation with the same arguments. */
esp_err_t __real_audio_read_exact(int16_t *, size_t, uint32_t, size_t *);
esp_err_t __wrap_audio_read_exact(int16_t *p, size_t n, uint32_t timeout, size_t *got) {
    unsigned old = phase_set(CAPTURE_WAIT);
    esp_err_t result = __real_audio_read_exact(p, n, timeout, got);
    phase_set(old);
    return result;
}
int __real_asd_psd_stream_push_hop(const float *);
int __wrap_asd_psd_stream_push_hop(const float *p) {
    unsigned old = phase_set(DSP);
    int result = __real_asd_psd_stream_push_hop(p);
    phase_set(old);
    return result;
}
int __real_asd_psd_stream_finish_sidecar(float *, asd_psd_sidecar_t *);
int __wrap_asd_psd_stream_finish_sidecar(float *p, asd_psd_sidecar_t *sidecar) {
    unsigned old = phase_set(DSP);
    int result = __real_asd_psd_stream_finish_sidecar(p, sidecar);
    phase_set(old);
    return result;
}
float __real_asd_psd_score(const float *, const float *, const float *, const float *, const float *, int);
float __wrap_asd_psd_score(const float *f, const float *m, const float *s,
                          const float *p, const float *c, int dim) {
    unsigned old = phase_set(SCORE);
    float result = __real_asd_psd_score(f, m, s, p, c, dim);
    phase_set(old);
    return result;
}

static esp_err_t read_sample(sample_t *s) {
    unsigned before, after, phase_before, phase_after;
    uint16_t raw_shunt, raw_bus, raw_current, raw_power, mask = 0;
    phase_snapshot(&phase_before, &before);
    s->trigger_us = esp_timer_get_time();
    esp_err_t err = ina226_e5_trigger(TRIGGER_CONFIG);
    if (err != ESP_OK) return err;
    /* A timer notification avoids changing the application's RTOS tick rate.
     * The device-ready flag remains authoritative, not the nominal delay. */
    int64_t deadline = s->trigger_us + 100000;
    do {
        err = esp_timer_start_once(conversion_timer, 2500);
        if (err != ESP_OK) return err;
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        err = ina226_read_reg(0x06, &mask);
        if (err != ESP_OK) return err;
        if (esp_timer_get_time() > deadline) return ESP_ERR_TIMEOUT;
    } while (!(mask & 0x0008));
    s->ready_us = esp_timer_get_time();
    phase_snapshot(&phase_after, &after);
    s->phase = before == after && phase_before == phase_after ? phase_before : MIXED;
    s->sequence = after;
    s->mask = mask;
    if (mask & 0x0004) return ESP_ERR_INVALID_STATE; /* math overflow */
    if ((err = ina226_read_reg(0x01, &raw_shunt)) != ESP_OK ||
        (err = ina226_read_reg(0x02, &raw_bus)) != ESP_OK ||
        (err = ina226_read_reg(0x04, &raw_current)) != ESP_OK ||
        (err = ina226_read_reg(0x03, &raw_power)) != ESP_OK) return err;
    s->shunt_nv = (int16_t)raw_shunt * 2500;
    s->bus_uv = raw_bus * 1250;
    s->current_ua = (int16_t)raw_current * 50;
    s->power_uw = raw_power * 1250;
    if (raw_shunt == 0x7fff || raw_shunt == 0x8000) return ESP_ERR_INVALID_STATE;
    return ESP_OK;
}

static void emit_sample(const char *kind, unsigned index, const sample_t *s) {
    printf("%s index=%u trigger_us=%lld ready_us=%lld bus_uv=%ld shunt_nv=%ld "
           "current_ua=%ld power_uw=%ld phase=%s sequence=%lu mask=0x%04x\n",
           kind, index, (long long)s->trigger_us, (long long)s->ready_us,
           (long)s->bus_uv, (long)s->shunt_nv, (long)s->current_ua,
           (long)s->power_uw, phase_names[s->phase], (unsigned long)s->sequence, s->mask);
}

static void dump(void) {
    char sha[65];
    for (unsigned i = 0; i < 32; i++) snprintf(sha + 2*i, 3, "%02x", run_firmware_sha[i]);
    printf("E5BEGIN protocol=e5-v1 samples=%u errors=%u start_us=%lld end_us=%lld "
           "source=UNVERIFIED config=0x4123 cal=1024 shunt_mohm=100 tick_ms=%u firmware_sha=%s\n",
           count, errors, (long long)run_start, (long long)run_end, (unsigned)portTICK_PERIOD_MS, sha);
    for (unsigned i = 0; i < count; i++) {
        emit_sample("E5DATA", i, &samples[i]);
        if (i % 32 == 0) vTaskDelay(1);
    }
    for (unsigned i = 0; i < 4; i++)
        printf("E5TIME phase=%s duration_us=%lld\n", phase_names[i], (long long)phase_time[i]);
    printf("E5END samples=%u errors=%u\n", count, errors);
}

static void measure_task(void *arg) {
    (void)arg;
    measurement_task = xTaskGetCurrentTaskHandle();
    if (boot_delay_s) {
        atomic_store(&busy, 1);
        printf("E5AUTOSTART delay_s=%u source=POWERON_UNVERIFIED\n", boot_delay_s);
        for (unsigned i = 0; i < boot_delay_s && !atomic_load(&stop_requested); i++)
            vTaskDelay(pdMS_TO_TICKS(1000));
        if (!atomic_load(&stop_requested)) atomic_store(&pending, 2);
        else { atomic_store(&busy, 0); printf("E5AUTOSTART cancelled=1\n"); }
    }
    for (;;) {
        int command = atomic_exchange(&pending, 0);
        if (!command) { vTaskDelay(pdMS_TO_TICKS(20)); continue; }
        if (command == 3) { dump(); atomic_store(&busy, 0); continue; }
        if (command == 4 || command == 6) {
            unsigned delay_s = command == 6 ? 0 : atomic_load(&requested_delay_s);
            esp_err_t err = store_writable ? arm_next_boot(delay_s) : ESP_ERR_INVALID_STATE;
            printf("E5ARM result=%s delay_s=%u next=POWERON\n", esp_err_to_name(err), delay_s);
            atomic_store(&busy, 0); continue;
        }
        if (command == 5) {
            if (load_saved()) dump();
            else printf("E5ERROR op=LOAD error=NO_VALID_SAVED_RUN\n");
            atomic_store(&busy, 0); continue;
        }
        atomic_store(&stop_requested, 0);
        if (command == 1) {
            for (unsigned i = 0; i < 10 && !atomic_load(&stop_requested); i++) {
                sample_t s = {0};
                esp_err_t err = read_sample(&s);
                if (err == ESP_OK) emit_sample("E5CHECK", i, &s);
                else printf("E5ERROR op=CHECK error=%s\n", esp_err_to_name(err));
                vTaskDelay(pdMS_TO_TICKS(100));
            }
            printf("E5CHECK_END\n");
        } else {
            count = errors = 0;
            memset(phase_time, 0, sizeof(phase_time));
            memcpy(run_firmware_sha, esp_app_get_description()->app_elf_sha256, sizeof(run_firmware_sha));
            phase_now = phase_sequence = 0;
            run_start = phase_since = esp_timer_get_time();
            atomic_store(&recording, 1);
            printf("E5START duration_s=60 source=UNVERIFIED\n");
            while (esp_timer_get_time() - run_start < RUN_US && !atomic_load(&stop_requested)) {
                if (count == MAX_SAMPLES) { errors++; break; }
                esp_err_t err = read_sample(&samples[count]);
                if (err != ESP_OK) { errors++; break; }
                count++;
            }
            portENTER_CRITICAL(&phase_lock);
            run_end = esp_timer_get_time();
            phase_time[phase_now] += run_end - phase_since;
            atomic_store(&recording, 0);
            portEXIT_CRITICAL(&phase_lock);
            gpio_set_level(GPIO_NUM_12, 0); gpio_set_level(GPIO_NUM_13, 0); gpio_set_level(GPIO_NUM_14, 0);
            esp_err_t saved = save_samples();
            printf("E5SAVE result=%s samples=%u\n", esp_err_to_name(saved), count);
            dump();
        }
        atomic_store(&busy, 0);
    }
}

bool e5_measure_command(const char *command) {
    int op = !strcmp(command, "E5CHECK") ? 1 : !strcmp(command, "E5RUN") ? 2 :
             !strcmp(command, "E5DUMP") ? 3 : !strcmp(command, "E5SAVED") ? 5 :
             !strcmp(command, "E5DISARM") ? 6 : 0;
    unsigned delay = 15;
    if (!strncmp(command, "E5ARM", 5)) {
        const char *p = command + 5;
        if (*p) {
            delay = 0;
            for (; *p; p++) {
                if (*p < '0' || *p > '9' || delay > 3600) return false;
                delay = delay * 10 + (unsigned)(*p - '0');
            }
        }
        if (delay < 5 || delay > 3600) { printf("E5ERROR op=ARM error=DELAY_RANGE\n"); return true; }
        op = 4;
    }
    if (!strcmp(command, "E5STOP")) { atomic_store(&stop_requested, 1); return true; }
    if (!op) return false;
    if (!available) { printf("E5ERROR op=COMMAND error=UNAVAILABLE\n"); return true; }
    int expected = 0;
    if (!atomic_compare_exchange_strong(&busy, &expected, 1)) {
        printf("E5ERROR op=COMMAND error=BUSY\n"); return true;
    }
    atomic_store(&requested_delay_s, delay);
    atomic_store(&pending, op);
    return true;
}

void e5_measure_start(int address) {
    if (address < 0 || ina226_init((uint8_t)address) != ESP_OK) {
        printf("E5ERROR op=INIT error=SENSOR_NOT_READY\n"); return;
    }
    uint16_t config = 0, cal = 0;
    if (ina226_read_reg(0, &config) != ESP_OK || ina226_read_reg(5, &cal) != ESP_OK ||
        config != 0x4527 || cal != 1024) {
        printf("E5ERROR op=INIT error=REGISTER_READBACK\n"); return;
    }
    samples = heap_caps_calloc(MAX_SAMPLES, sizeof(sample_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!samples) { printf("E5ERROR op=INIT error=NO_MEMORY\n"); return; }
    init_store();
    if (nvs_flash_init() == ESP_OK) {
        nvs_handle_t h;
        if (nvs_open("e5_measure", NVS_READONLY, &h) == ESP_OK) {
            uint32_t delay = 0;
            esp_err_t got = nvs_get_u32(h, "delay_s", &delay);
            nvs_close(h);
            if (got == ESP_OK && delay >= 5 && delay <= 3600 &&
                esp_reset_reason() == ESP_RST_POWERON && store_writable && arm_next_boot(0) == ESP_OK)
                boot_delay_s = delay;
        }
    }
    gpio_config_t cfg = {.pin_bit_mask=(1ULL<<12)|(1ULL<<13)|(1ULL<<14), .mode=GPIO_MODE_OUTPUT};
    if (gpio_config(&cfg) != ESP_OK) { printf("E5ERROR op=INIT error=GPIO\n"); return; }
    esp_timer_create_args_t timer_args = {.callback=conversion_ready, .name="e5_conversion"};
    if (esp_timer_create(&timer_args, &conversion_timer) != ESP_OK) {
        printf("E5ERROR op=INIT error=TIMER\n"); return;
    }
    if (xTaskCreatePinnedToCore(measure_task, "e5_measure", 4096, NULL, 2, NULL, 1) != pdPASS) {
        printf("E5ERROR op=INIT error=TASK\n"); return;
    }
    available = 1;
    printf("E5INFO protocol=e5-v1 address=0x%02x config=0x%04x cal=%u "
           "commands=E5CHECK,E5RUN,E5STOP,E5DUMP,E5ARM,E5SAVED,E5DISARM markers=12,13,14\n", address, config, cal);
}
#endif
