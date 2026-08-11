/* Bring-up test za INA226 — vidi ina226_test.h.
 *
 * Radi sa samo 4 spojene žice (VCC/GND/SDA/SCL): skenira bus, provjeri
 * identitet čipa, konfiguriše ga i ispiše sirove registre + očitanja.
 *
 * VAŽNO za tumačenje: dok IN+/IN− i VBS nisu spojeni, ti pinovi vise u vazduhu.
 * Šant napon, struja i snaga tada NISU mjerenje ničega — očekuje se šum oko
 * nule. Ono što se ovdje stvarno provjerava je I2C komunikacija: da senzor
 * odgovara, da su ID registri tačni, i da konfiguracija ostaje upisana.
 */
#include "ina226_test.h"
#include "ina226.h"

#include <stdio.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "esp_system.h"
#include "nvs.h"
#include "nvs_flash.h"

#include "pins.h"

static const char *TAG = "inatest";

#define N_READINGS  10
#define PERIOD_MS   300
#define REPORT_MAGIC 0x4535494EU
#define REPORT_VERSION 2
#define REPORT_NAMESPACE "ina_e5"
#define REPORT_KEY "report"

typedef enum {
    REPORT_ARMED = 1,
    REPORT_RUNNING,
    REPORT_READY,
} report_state_t;

typedef enum {
    TEST_NOT_RUN = 0,
    TEST_OK,
    TEST_BUS_UNUSABLE,
    TEST_NO_DEVICE,
    TEST_INIT_FAILED,
    TEST_READ_FAILED,
} test_status_t;

typedef struct {
    uint32_t magic;
    uint16_t version;
    uint8_t state;
    uint8_t status;
    int32_t error;
    uint8_t address;
    uint8_t reading_count;
    uint16_t config;
    uint16_t calibration;
    int32_t shunt_uv[N_READINGS];
    int32_t bus_mv[N_READINGS];
    int32_t current_ua[N_READINGS];
    int32_t power_uw[N_READINGS];
} ina226_report_t;

static const char *test_status_name(uint8_t status) {
    switch (status) {
        case TEST_OK: return "USPJESNO";
        case TEST_BUS_UNUSABLE: return "I2C BUS NIJE UPOTREBLJIV";
        case TEST_NO_DEVICE: return "INA226 NIJE PRONADJEN";
        case TEST_INIT_FAILED: return "INA226 INIT NIJE USPIO";
        case TEST_READ_FAILED: return "GRESKA PRI CITANJU";
        default: return "TEST NIJE ZAVRSEN";
    }
}

static esp_err_t report_write(const ina226_report_t *report) {
    nvs_handle_t handle;
    esp_err_t err = nvs_open(REPORT_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) return err;

    err = nvs_set_blob(handle, REPORT_KEY, report, sizeof(*report));
    if (err == ESP_OK) err = nvs_commit(handle);
    nvs_close(handle);
    return err;
}

static bool report_read(ina226_report_t *report) {
    nvs_handle_t handle;
    esp_err_t err = nvs_open(REPORT_NAMESPACE, NVS_READONLY, &handle);
    if (err != ESP_OK) return false;

    size_t size = sizeof(*report);
    err = nvs_get_blob(handle, REPORT_KEY, report, &size);
    nvs_close(handle);
    return err == ESP_OK && size == sizeof(*report) &&
           report->magic == REPORT_MAGIC && report->version == REPORT_VERSION;
}

static void report_print(const ina226_report_t *report) {
    ESP_LOGI(TAG, "=== SACUVANI INA226 E5 IZVJESTAJ ===");
    ESP_LOGI(TAG, "status=%s  greska=%ld  adresa=0x%02X  config=0x%04X  cal=%u",
             test_status_name(report->status), (long)report->error, report->address,
             report->config, report->calibration);
    for (uint8_t i = 0; i < report->reading_count; i++) {
        printf("  [%2u] sant=%8ld uV   bus=%6ld mV   struja=%8ld uA   snaga=%8ld uW\n",
               (unsigned)(i + 1), (long)report->shunt_uv[i], (long)report->bus_mv[i],
               (long)report->current_ua[i], (long)report->power_uw[i]);
    }
    ESP_LOGI(TAG, "=== KRAJ SACUVANOG IZVJESTAJA ===");
}

static bool report_prepare(ina226_report_t *report) {
    esp_err_t err = nvs_flash_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "NVS init nije uspio: %s", esp_err_to_name(err));
        return false;
    }

    if (!report_read(report)) {
        *report = (ina226_report_t){
            .magic = REPORT_MAGIC,
            .version = REPORT_VERSION,
            .state = REPORT_ARMED,
            .status = TEST_NOT_RUN,
        };
        err = report_write(report);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "ne mogu armirati test: %s", esp_err_to_name(err));
            return false;
        }
        ESP_LOGI(TAG, "TEST JE ARMIRAN. Sada iskopcaj USB, spoji semu i ukljuci 3,30 V.");
        return false;
    }

    if (report->state != REPORT_ARMED) {
        if (report->state == REPORT_READY) {
            report_print(report);
        } else {
            ESP_LOGE(TAG, "prethodni test je prekinut prije cuvanja rezultata");
        }
        ESP_LOGI(TAG, "Rezultat se nece prepisati novim mjerenjem.");
        return false;
    }

    if (esp_reset_reason() != ESP_RST_POWERON) {
        ESP_LOGI(TAG, "test je armiran i ceka potpuno gasenje pa eksterno napajanje");
        return false;
    }

    *report = (ina226_report_t){
        .magic = REPORT_MAGIC,
        .version = REPORT_VERSION,
        .state = REPORT_RUNNING,
        .status = TEST_NOT_RUN,
    };
    err = report_write(report);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "ne mogu oznaciti pocetak testa: %s", esp_err_to_name(err));
        return false;
    }
    return true;
}

static void report_finish(ina226_report_t *report, test_status_t status, esp_err_t error) {
    report->state = REPORT_READY;
    report->status = status;
    report->error = error;
    esp_err_t err = report_write(report);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "rezultat NIJE sacuvan: %s", esp_err_to_name(err));
        return;
    }
    ESP_LOGI(TAG, "rezultat je sacuvan u flash; iskljuci izvor pa ponovo prikljuci USB");
}

/* Stanje linija PRIJE nego I2C drajver preuzme pinove. Razdvaja tri slučaja:
 *   bez pull-upa 1 / 1  -> spolja postoje pull-upovi = modul je spojen i napojen
 *   bez pull-upa 0 / 0  -> linija visi na masi ili nema pull-upa nigdje
 *   sa pull-upom  0     -> ta linija je kratko spojena na GND
 * Bez ove provjere se gubi vrijeme na prekopavanje žica naslijepo. */
static void probe_lines(void) {
    const gpio_num_t pins[2] = {PIN_I2C_SDA, PIN_I2C_SCL};
    const char *names[2] = {"SDA", "SCL"};

    for (int pass = 0; pass < 2; pass++) {
        for (int i = 0; i < 2; i++) {
            gpio_config_t cfg = {
                .pin_bit_mask = 1ULL << pins[i],
                .mode = GPIO_MODE_INPUT,
                .pull_up_en = pass ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE,
                .pull_down_en = GPIO_PULLDOWN_DISABLE,
            };
            gpio_config(&cfg);
        }
        vTaskDelay(pdMS_TO_TICKS(20));
        ESP_LOGI(TAG, "linije %s internog pull-upa: %s(GPIO%d)=%d  %s(GPIO%d)=%d",
                 pass ? "SA" : "BEZ",
                 names[0], (int)pins[0], gpio_get_level(pins[0]),
                 names[1], (int)pins[1], gpio_get_level(pins[1]));
    }
    /* Klasifikacija svake linije posebno, iz sirovih mjerenja (pouka P9:
     * prvo brojevi, pa tek onda zakljucak). Redoslijed je bitan — obaranje se
     * provjerava PRIJE svega ostalog, jer ako linija ne moze da se obori,
     * sva ostala mjerenja su bezvrijedna.
     *
     *   obaranje != 0            -> linija je tvrdo na 3V3
     *   pusteno(5us) == 1        -> spoljni pull-up (modul napojen i spojen)
     *   pusteno(5ms) == 0        -> pluta: nema pull-upa nigdje na liniji
     */
    for (int i = 0; i < 2; i++) {
        gpio_num_t pin = pins[i];
        gpio_config_t od = {
            .pin_bit_mask = 1ULL << pin,
            .mode = GPIO_MODE_INPUT_OUTPUT_OD,       /* nikad push-pull, vidi napomenu */
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
        };
        gpio_config(&od);

        gpio_set_level(pin, 1);
        esp_rom_delay_us(200);
        int idle = gpio_get_level(pin);

        gpio_set_level(pin, 0);
        esp_rom_delay_us(200);
        int driven = gpio_get_level(pin);

        gpio_set_level(pin, 1);
        esp_rom_delay_us(5);
        int rel_fast = gpio_get_level(pin);
        esp_rom_delay_us(5000);
        int rel_slow = gpio_get_level(pin);

        const char *verdict;
        if (driven != 0)      verdict = "TVRDO NA 3V3 — linija je na napajanju, ne na senzoru";
        else if (rel_fast)    verdict = "spoljni pull-up (modul napojen i linija stize do njega)";
        else if (rel_slow)    verdict = "slab/spor pull-up";
        else                  verdict = "PLUTA — nema pull-upa (nije spojeno ili modul nije napojen)";

        ESP_LOGI(TAG, "%s(GPIO%d): mirno=%d obaranje=%d pusteno@5us=%d pusteno@5ms=%d",
                 names[i], (int)pin, idle, driven, rel_fast, rel_slow);
        ESP_LOGI(TAG, "   -> %s", verdict);

        gpio_reset_pin(pin);
    }

    /* NAPOMENA (06.08): raniji test je obarao liniju u push-pull rezimu. Ako je
     * linija tvrdo vezana na 3V3, to je kratak spoj 3V3->GND kroz GPIO. Zato
     * se od sada linije obaraju ISKLJUCIVO open-drain (vidi bitbang_scan) —
     * open-drain izlaz protiv kratkog spoja na 3V3 samo ne uspije, bez struje.
     * Zakljucak o pull-upu se izvodi iz bit-bang self-checka, ne odavde. */

    /* vrati pinove u neutralno stanje da ih I2C drajver moze preuzeti */
    for (int i = 0; i < 2; i++) gpio_reset_pin(pins[i]);
}

/* ---- Bit-bang I2C: isključuje sumnju u hardverski drajver ----------------
 * Hardverski drajver javlja timeout na SVAKOJ adresi, što ne razlikuje "nema
 * uređaja" od "bus ne radi". Ručno klokovanje pokazuje tačno šta se dešava:
 * da li master uopšte može da obori linije, i da li ih iko drži.
 */
#define BB_DELAY_US 5                                  /* ~100 kHz */

static gpio_num_t bb_sda, bb_scl;

static void bb_pin_mode(gpio_num_t pin) {
    gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << pin,
        .mode = GPIO_MODE_INPUT_OUTPUT_OD,             /* open-drain: 1 = pušteno */
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
    };
    gpio_config(&cfg);
    gpio_set_level(pin, 1);
}

static inline void bb_set(gpio_num_t pin, int v) {
    gpio_set_level(pin, v);
    esp_rom_delay_us(BB_DELAY_US);
}

static void bb_start(void) {
    bb_set(bb_sda, 1); bb_set(bb_scl, 1);
    bb_set(bb_sda, 0); bb_set(bb_scl, 0);
}

static void bb_stop(void) {
    bb_set(bb_sda, 0); bb_set(bb_scl, 1); bb_set(bb_sda, 1);
}

/* Šalje bajt, vraća stanje SDA za vrijeme ACK kloka (0 = uređaj je potvrdio). */
static int bb_write_byte(uint8_t b) {
    for (int i = 7; i >= 0; i--) {
        bb_set(bb_sda, (b >> i) & 1);
        bb_set(bb_scl, 1);
        bb_set(bb_scl, 0);
    }
    bb_set(bb_sda, 1);                                 /* pusti SDA slave-u */
    bb_set(bb_scl, 1);
    int ack = gpio_get_level(bb_sda);
    esp_rom_delay_us(BB_DELAY_US);
    bb_set(bb_scl, 0);
    return ack;
}

static int bitbang_scan(gpio_num_t sda, gpio_num_t scl) {
    bb_sda = sda; bb_scl = scl;
    bb_pin_mode(bb_sda);
    bb_pin_mode(bb_scl);
    esp_rom_delay_us(100);

    /* Self-check: da li master uopste moze da obori svaku liniju? */
    gpio_set_level(bb_sda, 0); esp_rom_delay_us(50);
    int sda_low_ok = (gpio_get_level(bb_sda) == 0);
    gpio_set_level(bb_sda, 1); esp_rom_delay_us(50);
    int sda_high_ok = (gpio_get_level(bb_sda) == 1);

    gpio_set_level(bb_scl, 0); esp_rom_delay_us(50);
    int scl_low_ok = (gpio_get_level(bb_scl) == 0);
    gpio_set_level(bb_scl, 1); esp_rom_delay_us(50);
    int scl_high_ok = (gpio_get_level(bb_scl) == 1);

    ESP_LOGI(TAG, "bit-bang self-check: SDA low=%d high=%d | SCL low=%d high=%d",
             sda_low_ok, sda_high_ok, scl_low_ok, scl_high_ok);
    if (!sda_low_ok || !scl_low_ok) {
        ESP_LOGE(TAG, ">>> %s%s ostaje na 1 i kad je master obara.",
                 sda_low_ok ? "" : "SDA ", scl_low_ok ? "" : "SCL ");
        ESP_LOGE(TAG, ">>> Open-drain izlaz ne moze nadjacati TVRDU vezu na 3V3.");
        ESP_LOGE(TAG, ">>> Ta linija nije na SDA/SCL senzora nego na napajanju —");
        ESP_LOGE(TAG, ">>> provjeri da zica nije u + sini breadboarda ili u pogresnom redu.");
        return -1;
    }
    if (!sda_high_ok || !scl_high_ok) {
        ESP_LOGE(TAG, "linija ostaje na 0 kad je pustimo — neko je drzi (kratak spoj na GND)");
        return -1;
    }

    int found = 0;
    for (uint8_t a = 0x08; a < 0x78; a++) {
        bb_start();
        int ack = bb_write_byte((uint8_t)(a << 1));    /* write bit */
        bb_stop();
        if (ack == 0) {
            ESP_LOGI(TAG, "  bit-bang ACK sa adrese 0x%02X", a);
            found++;
        }
    }
    ESP_LOGI(TAG, "bit-bang scan [SDA=%d SCL=%d]: %d uredjaja", (int)sda, (int)scl, found);

    gpio_reset_pin(bb_sda);
    gpio_reset_pin(bb_scl);
    return found;
}

/* Mapa svih slobodnih pinova: gdje su zice STVARNO zavrsile.
 * Za svaki pin tri stanja:
 *   slobodan       — interni pull-down ga obori, nista spolja ne vuce
 *   pull-up 10k    — spolja visok, ALI ga open-drain izlaz obori => prava I2C linija
 *   tvrdo na 3V3   — spolja visok i ne moze se oboriti => pin je na napajanju
 * Preskacu se pinovi flesa/PSRAM-a (26-37), USB (19,20), konzole (43,44)
 * i strapping (0,45,46). */
static void map_all_pins(void) {
    /* Strapping pinovi (0,45,46) su UKLJUCENI: boot je odavno gotov, a bili su
     * ranije izostavljeni — zbog cega je skeniranje moglo promasiti zicu koja
     * je zavrsila bas na njima. */
    static const int cand[] = {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,
                               21,38,39,40,41,42,45,46,47,48};
    ESP_LOGI(TAG, "--- mapa pinova (sta je gdje stvarno spojeno) ---");

    for (size_t i = 0; i < sizeof(cand)/sizeof(cand[0]); i++) {
        gpio_num_t pin = (gpio_num_t)cand[i];

        gpio_config_t pd = {
            .pin_bit_mask = 1ULL << pin,
            .mode = GPIO_MODE_INPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_ENABLE,   /* ~45k na masu */
        };
        gpio_config(&pd);
        esp_rom_delay_us(300);
        int pulled_high = gpio_get_level(pin);      /* 1 => spolja vuce gore */

        if (!pulled_high) { gpio_reset_pin(pin); continue; }

        /* Nesto ga drzi gore — koliko jako? Open-drain izlaz obara. */
        gpio_config_t od = {
            .pin_bit_mask = 1ULL << pin,
            .mode = GPIO_MODE_INPUT_OUTPUT_OD,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
        };
        gpio_config(&od);
        gpio_set_level(pin, 0);
        esp_rom_delay_us(300);
        int can_pull_low = (gpio_get_level(pin) == 0);
        gpio_set_level(pin, 1);

        ESP_LOGI(TAG, "  GPIO%-2d: spolja visok, %s", (int)pin,
                 can_pull_low ? "obara se => PULL-UP (prava I2C linija)"
                              : "NE obara se => TVRDO NA 3V3");
        gpio_reset_pin(pin);
    }
    ESP_LOGI(TAG, "--- pinovi koji se ne pojavljuju su slobodni ---");
}

void ina226_test_run(void) {
    ESP_LOGI(TAG, "=== INA226 TEST ===");

    ina226_report_t report;
    if (!report_prepare(&report)) return;

    map_all_pins();
    probe_lines();

    /* Bit-bang ide PRVI: ako master ne moze ni da obori liniju, hardverski
     * skener bi samo 11 s trosio na timeoutove bez nove informacije. */
    if (bitbang_scan(PIN_I2C_SDA, PIN_I2C_SCL) < 0) {
        ESP_LOGE(TAG, "prekidam — bus nije upotrebljiv, nema smisla skenirati");
        report_finish(&report, TEST_BUS_UNUSABLE, ESP_FAIL);
        return;
    }

    uint8_t found_address = 0;
    int found = ina226_bus_scan(&found_address);
    if (found <= 0) {
        /* Isti obrazac (linije visoke, nema ACK-a) daju i zamijenjene SDA/SCL —
         * provjerava se softverski, prije nego se dira ijedna zica. */
        ESP_LOGW(TAG, "probam obrnut raspored pinova (SDA<->SCL)...");
        int swapped = ina226_scan_on(PIN_I2C_SCL, PIN_I2C_SDA);
        if (swapped > 0) {
            ESP_LOGE(TAG, ">>> ZICE SU ZAMIJENJENE: SDA i SCL treba zamijeniti mjesta.");
            ESP_LOGE(TAG, ">>> SDA modula ide na GPIO%d, SCL na GPIO%d.",
                     PIN_I2C_SDA, PIN_I2C_SCL);
        } else {
            ESP_LOGE(TAG, "ni obrnuto nema odgovora — nije stvar redoslijeda SDA/SCL");
        }
        ESP_LOGE(TAG, "prekidam — nema uredjaja na busu");
        report_finish(&report, TEST_NO_DEVICE, ESP_ERR_NOT_FOUND);
        return;
    }

    report.address = found_address;

    esp_err_t err = ina226_init(found_address);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "init na 0x%02X nije uspio: %s",
                 found_address, esp_err_to_name(err));
        report_finish(&report, TEST_INIT_FAILED, err);
        return;
    }

    /* Provjera da konfiguracija stvarno stoji u čipu (a ne da je upis "prošao"
     * a senzor se resetovao zbog lošeg napajanja). */
    uint16_t cfg = 0, cal = 0;
    ina226_read_reg(0x00, &cfg);
    ina226_read_reg(0x05, &cal);
    report.config = cfg;
    report.calibration = cal;
    ESP_LOGI(TAG, "procitano nazad: config=0x%04X cal=%u", cfg, cal);

    ESP_LOGI(TAG, "--- ocitanja strujnog puta ---");
    int32_t shunt_min = INT32_MAX, shunt_max = INT32_MIN;

    for (int i = 0; i < N_READINGS; i++) {
        int32_t shunt_uv = 0, bus_mv = 0, cur_ua = 0, pwr_uw = 0;
        esp_err_t e1 = ina226_shunt_uv(&shunt_uv);
        esp_err_t e2 = ina226_bus_mv(&bus_mv);
        esp_err_t e3 = ina226_current_ua(&cur_ua);
        esp_err_t e4 = ina226_power_uw(&pwr_uw);

        if (e1 || e2 || e3 || e4) {
            ESP_LOGE(TAG, "greska pri citanju (%d/%d/%d/%d)", e1, e2, e3, e4);
            report_finish(&report, TEST_READ_FAILED, e1 ? e1 : e2 ? e2 : e3 ? e3 : e4);
            return;
        }
        report.shunt_uv[i] = shunt_uv;
        report.bus_mv[i] = bus_mv;
        report.current_ua[i] = cur_ua;
        report.power_uw[i] = pwr_uw;
        report.reading_count++;
        if (shunt_uv < shunt_min) shunt_min = shunt_uv;
        if (shunt_uv > shunt_max) shunt_max = shunt_uv;

        printf("  [%2d] sant=%8ld uV   bus=%6ld mV   struja=%8ld uA   snaga=%8ld uW\n",
               i + 1, (long)shunt_uv, (long)bus_mv, (long)cur_ua, (long)pwr_uw);
        vTaskDelay(pdMS_TO_TICKS(PERIOD_MS));
    }

    ESP_LOGI(TAG, "sant raspon: %ld..%ld uV (sirina %ld uV)",
             (long)shunt_min, (long)shunt_max, (long)(shunt_max - shunt_min));
    ESP_LOGI(TAG, "I2C lanac ispravan — senzor odgovara i drzi konfiguraciju.");
    report_finish(&report, TEST_OK, ESP_OK);
}
