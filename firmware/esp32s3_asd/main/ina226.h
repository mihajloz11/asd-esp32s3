/* INA226 — mjerenje struje/napona za E5 (energija po inferenci).
 *
 * Modul sa elektromodul.rs ima šant R100 = 0,1 Ω. Kalibracija je odabrana za
 * Current_LSB = 50 µA (CAL = 1024), što daje:
 *   - opseg struje  ±819 mA  (ograničen šantom: ±81,92 mV / 0,1 Ω)
 *   - rezoluciju    50 µA
 *   - Power_LSB     1,25 mW
 * ESP32-S3 bez WiFi-ja vuče 30–250 mA, pa je opseg dovoljan sa rezervom.
 *
 * Konverzija: 16 usrednjavanja × (1,1 ms bus + 1,1 ms šant) = 35,2 ms po
 * očitanju — dovoljno sporo da se filtrira šum, dovoljno brzo za profil
 * potrošnje po fazi (featuring vs inferencija traju stotine ms).
 */
#ifndef ASD_INA226_H
#define ASD_INA226_H

#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define INA226_ADDR_DEFAULT   0x40    /* A0=A1=GND */
#define INA226_MANUF_ID       0x5449  /* "TI" */
#define INA226_DIE_ID         0x2260

/* Podiže I2C master bus (PIN_I2C_SDA/SCL) i konfiguriše senzor na adresi addr.
 * Provjerava Manufacturer/Die ID — vraća ESP_ERR_NOT_FOUND ako se ne poklapaju. */
esp_err_t ina226_init(uint8_t addr);

/* Sirovo čitanje 16-bitnog registra (dijagnostika). */
esp_err_t ina226_read_reg(uint8_t reg, uint16_t *out);

#ifdef ASD_E5_MEASURE
/* Measurement-only single-shot configuration; no changes to legacy modes. */
esp_err_t ina226_e5_trigger(uint16_t config);
#endif

/* Napon na šantu [µV] — predznakom označava smjer struje. */
esp_err_t ina226_shunt_uv(int32_t *out);

/* Napon na VBS pinu [mV]. Ako VBS nije spojen, očitanje nije upotrebljivo. */
esp_err_t ina226_bus_mv(int32_t *out);

/* Struja [µA] i snaga [µW] — validni samo ako je teret vezan preko IN+/IN−. */
esp_err_t ina226_current_ua(int32_t *out);
esp_err_t ina226_power_uw(int32_t *out);

/* Skenira I2C bus i ispisuje nađene adrese. Ako first_address nije NULL,
 * upisuje prvu adresu ili 0 kada nema uređaja. Vraća broj nađenih uređaja. */
int ina226_bus_scan(uint8_t *first_address);

/* Dijagnostika: skenira na proizvoljnom paru pinova (odvojen I2C port), pa
 * briše bus. Služi da se zamijenjene SDA/SCL utvrde bez prekopavanja žica. */
int ina226_scan_on(int sda, int scl);

#ifdef __cplusplus
}
#endif
#endif
