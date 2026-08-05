# Hardver — lista (imamo / treba kupiti)

> Sažeta lista za projekat. Detalji kompatibilnosti i pinova: [hardware.md](hardware.md)
> i [sema-povezivanja.md](sema-povezivanja.md). Šta se lemi i kojim redom:
> [lemljenje.md](lemljenje.md).

## ✅ Imamo (potvrđeno na stolu, 19.07.2026)

| Uređaj | Specifikacija | Port | Uloga | Status |
|---|---|---|---|---|
| **ESP32-S3-WROOM-1 N32R16V** | 32 MB flash, 16 MB oktalni PSRAM (1.8 V), 240 MHz LX7, PIE SIMD | COM4 (CH343) | **Glavni target** — TFLM inferenca, svi eksperimenti | ✔ flešovan, verifikovan |
| **ESP32 DevKit V1** | ESP32-D0WD-V3, 4 MB flash, 520 KB SRAM, **bez PSRAM**, LX6 | COM5 (CP2102) | **E4 kontrola** — poređenje bez PIE | ✔ flešovan, E4 izmjeren |
| Protoboard MB-102 (830) | — | — | Montaža senzora (žice < 10 cm) | ✔ |
| Jumper žice + USB kablovi | — | — | Spajanje, flash, UART | ✔ |
| mmWave 24 GHz FMCW | micro-motion senzor | — | Van scope-a rada (opciona future-work ideja) | nekorišćen |
| DHT11 | temp/vlažnost | — | Van scope-a rada | nekorišćen |

## 📦 Stiglo 04.08.2026 — porudžbina elektromodul.rs (SVE na stolu)

Naručeno po [porudzbina-elektromodul.md](porudzbina-elektromodul.md), isporučeno kompletno.
**Ukupno plaćeno: 3.118 RSD** (2.578 roba + 540 dostava, ~27 €) — u budžetu plana.

| Stavka (SKU) | Kom | Cijena | Uloga | Lemiti? |
|---|---|---|---|---|
| INMP441 I2S mikrofon (A1477) | 2 | 1.200 | Živi audio ulaz + rezerva (MEMS krhak, rizik C1) | **DA** — 6 pinova po modulu (stigle 2 letvice po 3) |
| INA226 I2C senzor struje i snage (A3627) | 1 | 300 | E5 mjerenje energije | **DA** — letvica 8 pinova, stigla nezalemljena |
| Set 120 elektrolita 1µF–470µF, 12 vrijednosti (A642K) | 1 | 500 | Daje **10 µF** (uz mikrofon) i **470 µF** (poslije INA, rizik C7) | tek u fazi 2 (ploča 4×6) |
| Keramika 470 nF MLCC 50 V (A2400) | 3 | 48 | HF decoupling uz VDD mikrofona (1 po miku + rezerva) | tek u fazi 2 |
| AMS1117 3.3V LDO modul 800 mA (A1652) | 1 | 120 | Čist 3,3 V za E5 bez USB-a (rizik D2) | **NE** — stigao sa 4 muška pina zalemljena |
| Muška pin letvica 40 pin 2.54 mm (A1632) | 2 | 56 | Headeri za **ESP32-S3** (~44 od 80 pinova) | to su same nožice |
| Dvoslojna prototipna ploča 4×6 cm (A1938) | 1 | 120 | Finalni zalemljeni sklop za demo | **DA** — cijela faza 2 |
| LED 5 mm crvena (A2177) | 1 | 14 | Demo — anomalija | faza 2 |
| LED 5 mm zelena, prozirna (A3506) | 1 | 80 | Demo — normalan rad | faza 2 |
| Taster arkadni 30 mm, **plavi** (A4059) | 1 | 140 | Demo taster (GPIO 10, interni pull-up) | **NE** — faston jezičci |

Odstupanje od spiska: taster je **plavi** umjesto crvenog — funkcionalno identičan
mikroprekidač, bez uticaja na šemu ili kod.

### Provjereno na stvarnim komadima (05.08.2026)

- **ESP32-S3 ploča je bez pinova** → obje 40-pinske letvice idu na nju (~44 spoja).
- **AMS1117 ima 4 muška pina već zalemljena** → ne lemi se, ženski jumper ide direktno.
- **INA226 ima 8 pinova** (VCC, GND, VBS, ALE, SDA, SCL, IN−, IN+) i stigla je nezalemljena
  letvica od 8 — **nema screw-terminala**, IN+/IN− su na headeru.
- **INMP441** je stigao sa 2 letvice po 3 pina po modulu → spajaju se u isti red.

### ⚠️ I dalje fali (nije bilo u porudžbini)

| Šta | Kom | Zašto fali | Bez toga |
|---|---|---|---|
| Otpornik **220–330 Ω** (1/4 W) | 2 | Bio na spisku "iz firme" — donijeti s posla | LED se **ne smije** vezati na GPIO |
| *(opciono)* Ženski header 2.54 mm | ~1 | Nije naručen | Na ploči 4×6 moduli idu fiksno zalemljeni |

### Redoslijed lemljenja i mjere opreza

Puna procedura: **[lemljenje.md](lemljenje.md)**. Ukratko: faza 1 = samo headeri
(~19 spojeva) → sve proraditi na MB-102 → faza 2 = finalni sklop na ploči 4×6.
INMP441 je ESD-osjetljiv i gine od pregrijavanja — 300–350 °C, max 2–3 s po pinu,
**ne dirati sound port**; zato i stoje 2 komada.

## Kompatibilnost (provjereno)

- INMP441 (3.3 V I2S) i INA226 (3.3 V I2C) rade na **obje** ploče — isti IDF v5 drajver.
- Pinovi se biraju automatski po targetu (`main/pins.h`): S3 BCLK/WS/DIN = 4/5/6,
  I2C = 8/9; ESP32 = 26/25/33, I2C = 21/22.
- Zabranjeni pinovi: S3 GPIO 35/36/37 (PSRAM); ESP32 GPIO 6–11 (flash).
