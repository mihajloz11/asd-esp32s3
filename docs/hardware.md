# Hardver — inventar, kompatibilnost, nabavka

## Postojeće (potvrđeno, jul 2026)

| Uređaj | Spec | Uloga u radu |
|---|---|---|
| **ESP32-S3-WROOM-1 N32R16V** | 32 MB flash, 16 MB oktalni PSRAM (1.8 V), Wi-Fi 2.4 GHz | **Glavna target platforma** — TFLM int8 inferenca, svi E-eksperimenti |
| **ESP32 DevKit V1** (WROOM-32, 30-pin) | 4 MB flash, 520 KB SRAM, **bez PSRAM-a**, bez PIE | **Kontrolna platforma za E4** (PIE/esp-nn ablation) — vidi plan ispod |
| mmWave 24 GHz FMCW (micro-motion) | UART/GPIO | Nije u scope-u rada. Opciona ideja u future-work: prisustvo osobe kao gate za duty-cycling |
| DHT11 temp/vlažnost | 1-wire | Nije u scope-u rada |
| Protoboard MB-102 (830) | — | Montaža INMP441 + INA (žice < 10 cm!) |
| Jumper žice + USB kablovi | — | Spajanje, flash, UART |

## Za kupovinu (jedino što fali)

| Stavka | Kom | Najjeftinije nađeno (17.07) | Cijena |
|---|---|---|---|
| INMP441 I2S MEMS mikrofon | 2 | [KP — Inđija](https://www.kupujemprodajem.com/elektronika-i-komponente/moduli-za-samoizgradnju/mikrofon-za-arduino-inmp441-i2s-microphone/oglas/142894803) (jedini na KP) | 600 din/kom |
| INA226 (bolji od INA219 — 16-bit, brži sampling za E5) | 1 | [KP — Kikinda, 521 ocjena](https://www.kupujemprodajem.com/elektronika-i-komponente/moduli-za-samoizgradnju/ina226-i2c-dvosmerni-digitalni-merac-struje-i-napona/oglas/124510988) | 270 din |
| INA219 (fallback ako 226 ode) | (1) | [KP — Zvezdara, lično preuzimanje](https://www.kupujemprodajem.com/elektronika-i-komponente/moduli-za-samoizgradnju/zero-drift-ina219-i2c-modul-current-power-sensor-ina-219/oglas/151504648) | 240 din |
| Keramika 100 nF + elektrolit 10 µF (decoupling uz mikrofon) + ≥470 µF (poslije INA, rizik C7) | par | bilo koja lokalna prodavnica komponenti | ~300 din |

Ukupno ≈ **1800 din (~15 €)** — u budžetu iz plana (≤18 €).
Preporuka: **INA226 iz Kikinde + 2× INMP441 iz Inđije** (KP dostava), kondenzatori lokalno.

## Kompatibilnost sa našim pločama (provjereno)

**INMP441** — 3.3 V I2S digitalni mikrofon: radi na **obje** ploče (i S3 i klasični
ESP32 imaju I2S kontroler; `i2s_std` drajver identičan, IDF v5). GPIO matrix
dozvoljava skoro bilo koje pinove na obje.

**INA219/226** — I2C @ 3.3 V: radi na obje ploče (bilo koja 2 pina preko GPIO matrixa).

**Pinovi se RAZLIKUJU po ploči** (riješeno u `firmware/.../main/pins.h` per-target):

| Signal | ESP32-S3 (N32R16V) | ESP32 DevKit V1 |
|---|---|---|
| I2S BCLK | GPIO 4 | GPIO 26 |
| I2S WS | GPIO 5 | GPIO 25 |
| I2S DIN | GPIO 6 | GPIO 33 |
| I2C SDA/SCL | GPIO 8 / 9 | GPIO 21 / 22 |
| LED | GPIO 2 | GPIO 2 (onboard) |

Pažnja: na klasičnom ESP32 GPIO 6–11 su SPI flash (zabranjeni); na S3 GPIO 35/36/37
su oktalni PSRAM (zabranjeni). Strapping pinovi (0, 3, 45, 46 na S3; 0, 2*, 12, 15
na ESP32) — LED na GPIO2 je OK (strapping samo pri bootu, LED ga ne vuče).

## Plan za drugi ESP32 (DevKit V1) — E4 ablation

1. **Uloga:** izmjeriti koliko PIE SIMD (S3) + esp-nn donose vs identičan kod na
   klasičnom Xtensa LX6 jezgru — matrica {ESP32, S3} × {esp-nn on/off} iz plana 6.1.
2. **Memorijska realnost:** bez PSRAM-a, ~300 KB upotrebljivog heapa. Streaming
   pipeline (vidi docs/edge-adaptacija.md) troši < 15 KB RAM za featuring, pa
   DevKit nosi AE-tiny int8 (67 KB flash, arena ~20–40 KB) bez problema;
   AE-baseline int8 ide tijesno, fp32 ne ide — to JE rezultat za rad (5.4).
3. **Flash 4 MB:** particija `partitions_esp32.csv` (FAT ~1.4 MB ≈ 4 test klipa —
   dovoljno za latencijska mjerenja; puna evaluacija ostaje na S3 sa 20 MB FAT).
4. **Build:** isti firmware, `idf.py set-target esp32` — per-target sdkconfig
   (`sdkconfig.defaults.esp32` bez SPIRAM-a) i pins.h rade automatski.
5. Oba na 240 MHz, Wi-Fi/BT off tokom mjerenja (fer poređenje, rizik D4).
