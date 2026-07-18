/* Pin-plan — per-target (plan 5.6 + docs/hardware.md). FIKSIRANO PRIJE LEMLJENJA.
 *
 * ESP32-S3 N32R16V: ZABRANJENI GPIO 35/36/37 (oktalni PSRAM);
 *                   strapping 0, 3, 45, 46 — izbjegavati.
 * ESP32 DevKit V1:  ZABRANJENI GPIO 6-11 (SPI flash);
 *                   strapping 0, 2, 12, 15 — LED na 2 je OK (onboard).
 *
 * | Signal        | S3   | ESP32 | Napomena                         |
 * |---------------|------|-------|----------------------------------|
 * | INMP441 BCLK  |  4   |  26   | I2S bit clock                    |
 * | INMP441 WS    |  5   |  25   | I2S word select                  |
 * | INMP441 SD    |  6   |  33   | data in (L/R pin mikrofona->GND) |
 * | INA226 SDA    |  8   |  21   | I2C                              |
 * | INA226 SCL    |  9   |  22   | I2C                              |
 * | LED status    |  2   |   2   | svijetli=normal, gasi=anomalija  |
 * | Taster (demo) | 10   |  27   | izbor izvora: mic/flash klipovi  |
 */
#ifndef ASD_PINS_H
#define ASD_PINS_H

#include "sdkconfig.h"

#if CONFIG_IDF_TARGET_ESP32S3
#define PIN_I2S_BCLK  4
#define PIN_I2S_WS    5
#define PIN_I2S_DIN   6
#define PIN_I2C_SDA   8
#define PIN_I2C_SCL   9
#define PIN_LED       2
#define PIN_BUTTON    10
#elif CONFIG_IDF_TARGET_ESP32
#define PIN_I2S_BCLK  26
#define PIN_I2S_WS    25
#define PIN_I2S_DIN   33
#define PIN_I2C_SDA   21
#define PIN_I2C_SCL   22
#define PIN_LED       2
#define PIN_BUTTON    27
#else
#error "nepodrzan target — dodaj pin-mapu"
#endif

#endif
