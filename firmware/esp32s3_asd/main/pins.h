/* Pin-plan za ESP32-S3-WROOM-1 N32R16V — FIKSIRANO PRIJE LEMLJENJA (plan 5.6).
 *
 * ZABRANJENI pinovi (oktalni PSRAM): GPIO 35, 36, 37 — ne koristiti NIKAD.
 * Izbjegavati strapping: GPIO 0, 3, 45, 46.
 *
 * | Signal          | GPIO | Napomena                          |
 * |-----------------|------|-----------------------------------|
 * | INMP441 BCLK    |  4   | I2S bit clock                     |
 * | INMP441 WS      |  5   | I2S word select (LRCLK)           |
 * | INMP441 SD/DIN  |  6   | I2S data in                       |
 * | INMP441 L/R     | GND  | lijevi kanal (hardverski na GND)  |
 * | INA219 SDA      |  8   | I2C data                          |
 * | INA219 SCL      |  9   | I2C clock                         |
 * | LED status      |  2   | zelena=normal, trep=anomalija     |
 * | Taster (demo)   | 10   | izbor izvora: mic / flash klipovi |
 */
#ifndef ASD_PINS_H
#define ASD_PINS_H

#define PIN_I2S_BCLK  4
#define PIN_I2S_WS    5
#define PIN_I2S_DIN   6
#define PIN_I2C_SDA   8
#define PIN_I2C_SCL   9
#define PIN_LED       2
#define PIN_BUTTON    10

#endif
