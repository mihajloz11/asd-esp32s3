#include "ina226.h"
#include "pins.h"

#include "driver/i2c_master.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "ina226";

/* Registri */
#define REG_CONFIG      0x00
#define REG_SHUNT_V     0x01
#define REG_BUS_V       0x02
#define REG_POWER       0x03
#define REG_CURRENT     0x04
#define REG_CALIB       0x05
#define REG_MANUF_ID    0xFE
#define REG_DIE_ID      0xFF

/* Kalibracija za R100 (0,1 Ω) i Current_LSB = 50 µA:
 *   CAL = 0.00512 / (Current_LSB * R_shunt) = 0.00512 / (50e-6 * 0.1) = 1024 */
#define CAL_VALUE       1024
#define CURRENT_LSB_UA  50
#define POWER_LSB_UW    (25 * CURRENT_LSB_UA)   /* datasheet: 25 × Current_LSB */
#define SHUNT_LSB_NV    2500                    /* 2,5 µV po bitu */
#define BUS_LSB_UV      1250                    /* 1,25 mV po bitu */

/* AVG=16 (0b010) · VBUSCT=1,1 ms (0b100) · VSHCT=1,1 ms (0b100) · MODE=cont oba (0b111)
 * Bit 14 je rezervisan i u fabričkom 0x4127 je postavljen — zadržavamo ga. */
#define CONFIG_VALUE    (0x4000 | (0x2 << 9) | (0x4 << 6) | (0x4 << 3) | 0x7)

/* 100 kHz: interni pull-upovi su slabi (~45 kΩ), a linije idu preko breadboarda.
 * Senzor podržava do 2,94 MHz — brzina ovdje nije usko grlo (35 ms po konverziji). */
#define I2C_SPEED_HZ    100000

static i2c_master_bus_handle_t bus;
static i2c_master_dev_handle_t dev;

static esp_err_t bus_up(void) {
    if (bus) return ESP_OK;
    i2c_master_bus_config_t cfg = {
        .i2c_port = I2C_NUM_0,
        .sda_io_num = PIN_I2C_SDA,
        .scl_io_num = PIN_I2C_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    return i2c_new_master_bus(&cfg, &bus);
}

esp_err_t ina226_read_reg(uint8_t reg, uint16_t *out) {
    uint8_t rx[2];
    esp_err_t err = i2c_master_transmit_receive(dev, &reg, 1, rx, 2, 200);
    if (err != ESP_OK) return err;
    *out = ((uint16_t)rx[0] << 8) | rx[1];       /* INA226 je big-endian */
    return ESP_OK;
}

static esp_err_t write_reg(uint8_t reg, uint16_t val) {
    uint8_t tx[3] = {reg, (uint8_t)(val >> 8), (uint8_t)(val & 0xFF)};
    return i2c_master_transmit(dev, tx, sizeof(tx), 200);
}

int ina226_bus_scan(void) {
    if (bus_up() != ESP_OK) {
        ESP_LOGE(TAG, "ne mogu da podignem I2C bus");
        return -1;
    }
    int found = 0;
    ESP_LOGI(TAG, "skeniram I2C bus (SDA=%d SCL=%d)...", PIN_I2C_SDA, PIN_I2C_SCL);
    /* Drajver loguje gresku za svaku neuspjelu adresu — 112 linija smeca po
     * skenu. Zanima nas samo zbirni rezultat. */
    esp_log_level_set("i2c.master", ESP_LOG_NONE);
    for (uint8_t a = 0x08; a < 0x78; a++) {
        if (i2c_master_probe(bus, a, 50) == ESP_OK) {
            ESP_LOGI(TAG, "  nadjen uredjaj na 0x%02X", a);
            found++;
        }
    }
    if (!found)
        ESP_LOGE(TAG, "  nijedan uredjaj — provjeri VCC, GND, SDA/SCL i da nisu zamijenjeni");
    return found;
}

int ina226_scan_on(int sda, int scl) {
    i2c_master_bus_handle_t b;
    i2c_master_bus_config_t cfg = {
        .i2c_port = I2C_NUM_1,                   /* odvojen port od glavnog */
        .sda_io_num = sda,
        .scl_io_num = scl,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    if (i2c_new_master_bus(&cfg, &b) != ESP_OK) return -1;

    int found = 0;
    for (uint8_t a = 0x08; a < 0x78; a++) {
        if (i2c_master_probe(b, a, 50) == ESP_OK) {
            ESP_LOGI(TAG, "  [SDA=%d SCL=%d] nadjen uredjaj na 0x%02X", sda, scl, a);
            found++;
        }
    }
    i2c_del_master_bus(b);
    return found;
}

esp_err_t ina226_init(uint8_t addr) {
    esp_err_t err = bus_up();
    if (err != ESP_OK) return err;

    if (!dev) {
        i2c_device_config_t dcfg = {
            .dev_addr_length = I2C_ADDR_BIT_LEN_7,
            .device_address = addr,
            .scl_speed_hz = I2C_SPEED_HZ,
        };
        err = i2c_master_bus_add_device(bus, &dcfg, &dev);
        if (err != ESP_OK) return err;
    }

    uint16_t manuf = 0, die = 0;
    if ((err = ina226_read_reg(REG_MANUF_ID, &manuf)) != ESP_OK) return err;
    if ((err = ina226_read_reg(REG_DIE_ID, &die)) != ESP_OK) return err;
    ESP_LOGI(TAG, "manuf=0x%04X die=0x%04X", manuf, die);

    if (manuf != INA226_MANUF_ID || die != INA226_DIE_ID) {
        ESP_LOGE(TAG, "identitet ne odgovara INA226 (ocekivano 0x%04X/0x%04X)",
                 INA226_MANUF_ID, INA226_DIE_ID);
        return ESP_ERR_NOT_FOUND;
    }

    if ((err = write_reg(REG_CONFIG, CONFIG_VALUE)) != ESP_OK) return err;
    if ((err = write_reg(REG_CALIB, CAL_VALUE)) != ESP_OK) return err;
    vTaskDelay(pdMS_TO_TICKS(50));               /* prva konverzija: 35,2 ms */

    ESP_LOGI(TAG, "konfigurisan: config=0x%04X cal=%d (LSB struje %d uA, sant 0,1 ohm)",
             CONFIG_VALUE, CAL_VALUE, CURRENT_LSB_UA);
    return ESP_OK;
}

esp_err_t ina226_shunt_uv(int32_t *out) {
    uint16_t raw;
    esp_err_t err = ina226_read_reg(REG_SHUNT_V, &raw);
    if (err != ESP_OK) return err;
    *out = (int32_t)((int16_t)raw) * SHUNT_LSB_NV / 1000;
    return ESP_OK;
}

esp_err_t ina226_bus_mv(int32_t *out) {
    uint16_t raw;
    esp_err_t err = ina226_read_reg(REG_BUS_V, &raw);
    if (err != ESP_OK) return err;
    *out = (int32_t)raw * BUS_LSB_UV / 1000;
    return ESP_OK;
}

esp_err_t ina226_current_ua(int32_t *out) {
    uint16_t raw;
    esp_err_t err = ina226_read_reg(REG_CURRENT, &raw);
    if (err != ESP_OK) return err;
    *out = (int32_t)((int16_t)raw) * CURRENT_LSB_UA;
    return ESP_OK;
}

esp_err_t ina226_power_uw(int32_t *out) {
    uint16_t raw;
    esp_err_t err = ina226_read_reg(REG_POWER, &raw);
    if (err != ESP_OK) return err;
    *out = (int32_t)raw * POWER_LSB_UW;
    return ESP_OK;
}
