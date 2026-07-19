# Hardver — lista (imamo / treba kupiti)

> Sažeta lista za projekat. Detalji kompatibilnosti i pinova: [hardware.md](hardware.md)
> i [sema-povezivanja.md](sema-povezivanja.md).

## ✅ Imamo (potvrđeno na stolu, 19.07.2026)

| Uređaj | Specifikacija | Port | Uloga | Status |
|---|---|---|---|---|
| **ESP32-S3-WROOM-1 N32R16V** | 32 MB flash, 16 MB oktalni PSRAM (1.8 V), 240 MHz LX7, PIE SIMD | COM4 (CH343) | **Glavni target** — TFLM inferenca, svi eksperimenti | ✔ flešovan, verifikovan |
| **ESP32 DevKit V1** | ESP32-D0WD-V3, 4 MB flash, 520 KB SRAM, **bez PSRAM**, LX6 | COM5 (CP2102) | **E4 kontrola** — poređenje bez PIE | ✔ flešovan, E4 izmjeren |
| Protoboard MB-102 (830) | — | — | Montaža senzora (žice < 10 cm) | ✔ |
| Jumper žice + USB kablovi | — | — | Spajanje, flash, UART | ✔ |
| mmWave 24 GHz FMCW | micro-motion senzor | — | Van scope-a rada (opciona future-work ideja) | nekorišćen |
| DHT11 | temp/vlažnost | — | Van scope-a rada | nekorišćen |

## 🛒 Treba kupiti (jedino što fali za E5 + živi zvuk)

| Stavka | Kom | Najjeftinije (KP, 17.07) | Cijena | Za šta |
|---|---|---|---|---|
| INMP441 I2S MEMS mikrofon | 2 | KP Inđija (jedini na KP) | 600 din/kom | Živi audio ulaz + demo |
| INA226 (bolji od INA219) | 1 | KP Kikinda (521 ocjena) | 270 din | E5 mjerenje struje/energije |
| Kondenzatori: 100 nF + 10 µF (uz mikrofon), ≥470 µF (poslije INA) | par | lokalno | ~300 din | Decoupling + protiv brownout-a (rizik C7) |
| **UKUPNO** | | | **~1770 din (~15 €)** | u budžetu plana (≤18 €) |

**Preporuka:** INA226 iz Kikinde + 2× INMP441 iz Inđije (KP dostava), kondenzatori lokalno.

## Kompatibilnost (provjereno)

- INMP441 (3.3 V I2S) i INA226 (3.3 V I2C) rade na **obje** ploče — isti IDF v5 drajver.
- Pinovi se biraju automatski po targetu (`main/pins.h`): S3 BCLK/WS/DIN = 4/5/6,
  I2C = 8/9; ESP32 = 26/25/33, I2C = 21/22.
- Zabranjeni pinovi: S3 GPIO 35/36/37 (PSRAM); ESP32 GPIO 6–11 (flash).
