# Hardver: inventar, kompatibilnost i nabavka

Spojeno 25.09.2026 iz `hardver-lista.md` (stanje na stolu, 05.08.) i
`hardware.md` (prvobitni inventar i plan nabavke, 22.07.). Prvi dio je
aktuelan; drugi dio je istorijski i ostaje zbog obrazloženja izbora
komponenti i plana za E4 na drugom ESP32.

> Pinovi: [sema-povezivanja.md](../sklop/sema-povezivanja.md). Šta se lemi i kojim redom:
> [lemljenje.md](../sklop/lemljenje.md). Podjela na dvije ploče (uređaj + mjerna) i
> spisak komponenti po pločama: [plan-dvije-plocice.md](../sklop/plan-dvije-plocice.md).

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
| Otpornik **330 Ω** (1/4 W) | 2 + rezerva | Nije bio u porudžbini; sada je u nabavci sa Mikro Princa | LED se **ne smije** vezati na GPIO |
| Otpornik **100 Ω** (1/4 W) | 2 | Rezerva ako zelena LED ima visok `Vf` | Zelena može ostati tamna a da je firmware ispravan |
| Keramika **100 nF**, raster 2,54 mm | 2 | Datasheet-tačna vrijednost za INMP441; kupljenih 470 nF radi funkcionalno | Kozmetika, ne blokada |
| *(opciono)* Ženski header 2.54 mm | ~1 | Nije naručen | Na ploči 4×6 moduli idu fiksno zalemljeni |

Nabavka i identi: [plan-dvije-plocice.md §7](../sklop/plan-dvije-plocice.md). Šta se od
toga uzima s posla umjesto kupovine, uz račun struje kroz otpornik i zamku sa
zelenom LED: [donijeti-sa-posla.md](donijeti-sa-posla.md).

### Redoslijed lemljenja i mjere opreza

Puna procedura: **[lemljenje.md](../sklop/lemljenje.md)**. Ukratko: faza 1 = samo headeri
(~19 spojeva) → sve proraditi na MB-102 → faza 2 = finalni sklop na ploči 4×6.
INMP441 je ESD-osjetljiv i gine od pregrijavanja — 300–350 °C, max 2–3 s po pinu,
**ne dirati sound port**; zato i stoje 2 komada.

## Kompatibilnost (provjereno)

- INMP441 (3.3 V I2S) i INA226 (3.3 V I2C) rade na **obje** ploče — isti IDF v5 drajver.
- Pinovi se biraju automatski po targetu (`main/pins.h`): S3 BCLK/WS/DIN = 4/5/6,
  I2C = 8/9; ESP32 = 26/25/33, I2C = 21/22.
- Zabranjeni pinovi: S3 GPIO 35/36/37 (PSRAM); ESP32 GPIO 6–11 (flash).

---

## Prvobitni inventar i plan nabavke (22.07.2026, istorijski)

### Postojeće (potvrđeno, jul 2026)

| Uređaj | Spec | Uloga u radu |
|---|---|---|
| **ESP32-S3-WROOM-1 N32R16V** | 32 MB flash, 16 MB oktalni PSRAM (1.8 V), Wi-Fi 2.4 GHz | **Glavna target platforma** — TFLM int8 inferenca, svi E-eksperimenti |
| **ESP32 DevKit V1** (WROOM-32, 30-pin) | 4 MB flash, 520 KB SRAM, **bez PSRAM-a**, bez PIE | **Kontrolna platforma za E4** (PIE/esp-nn ablation) — vidi plan ispod |
| mmWave 24 GHz FMCW (micro-motion) | UART/GPIO | Nije u scope-u rada. Opciona ideja u future-work: prisustvo osobe kao gate za duty-cycling |
| DHT11 temp/vlažnost | 1-wire | Nije u scope-u rada |
| Protoboard MB-102 (830) | — | Montaža INMP441 + INA (žice < 10 cm!) |
| Jumper žice + USB kablovi | — | Spajanje, flash, UART |

### Za kupovinu (jedino što fali)

Izvor: **elektromodul.rs** (lager u Srbiji, sve u jednoj pošiljci, isti dan do 13h).
Nazivi su tačno kako stoje na sajtu — kucaš ih u pretragu. Cijene provjerene 22.07.2026.

#### Obavezno (bez ovoga nema E5/E6/demo)

| Naziv na sajtu | Kom | Cijena | Svrha |
|---|---|---|---|
| INMP441 I2S Mikrofon za Arduino | 2 | 600 | Audio ulaz. 1 obavezan, 2. je rezerva (MEMS krhak, rizik C1) + po jedan na S3 i DevKit V1 |
| INA226 I2C senzor struje i snage | 1 | 300 | Cijeli E5. Provjeri šant po dolasku: R100=0,1 Ω / R010=0,01 Ω; kalibriši multimetrom |
| Set 120 Elektrolitskih Kondenzatora 1µF-470µF — 12 Vrednosti | 1 | 500 | Daje **10 µF** (bulk uz mikrofon) i **470 µF** (poslije INA, rizik C7) |
| Keramički kondenzator 470NF (Monolithic Ceramic) – MLCC 50V | 3 | 16 | HF decoupling uz VDD mikrofona. Datasheet traži 100 nF X7R; sajt nema pojedinačni 100 nF — 470 nF je funkcionalno identičan za digitalni MEMS. Po jedan na svaki mik + rezerva |

#### Za E5 mjerenje potrošnje (rizik D2 — napajanje bez USB-a)

| Naziv na sajtu | Kom | Cijena | Svrha |
|---|---|---|---|
| AMS1117 3.3V LDO Regulator Modul 800mA | 1 | 120 | Powerbank 5V → čist 3,3 V → INA → ploča. Linearni (nema switching ripple u mjerenju). Izmjeri izlaz multimetrom prije spajanja S3 |
| CP2102 USB to TTL UART modul 6Pin 3.3V/5V | 1 | 450 | Čitanje logova kad je USB otkačen. Veži **samo TX(S3)→RXD i GND→GND, NE VCC** |

#### Montaža

| Naziv na sajtu | Kom | Cijena | Svrha |
|---|---|---|---|
| Muska Pin Letvica 40 Pinova 2.54mm za Arduino | 1 | 28 | INMP441 breakout često stigne bez zalemljenih headera |
| Dvoslojna prototipna ploča 4×6 cm | 1 | 120 | Kratke I2S veze (<10 cm) — integritet digitalnog signala, rizik C1 |

#### Demo na odbrani (opciono)

| Naziv na sajtu | Kom | Cijena | Svrha |
|---|---|---|---|
| LED 5mm crvena dioda F5mm | 1 | 14 | Anomalija |
| LED 5mm Prozirna Dioda Zeleno Svetlo F5mm | 1 | 80 | Normalan rad |
| Crveni taster za arkadne igrice i DIY 30 mm | 1 | 140 | Momentary, 2 žice na GPIO10+GND (interni pull-up). Firmware čita GPIO10/27 — **NE** BOOT (GPIO0 je strapping) |

**NE naručuj** (imaš / donosi s posla):
- 2× otpornik ~330 Ω za LED (set 600 kom je bacanje para za 2 komada)
- 10 µF i 470 µF posebno — već u setu elektrolita

Ukupno: obavezno = **2.048 din**, +E5 = **2.618**, +montaža = **2.766**, sve sa demo = **~3.000 din (~26 €)**.

#### Ispravke u odnosu na prvu verziju (22.07)
1. **1 µF MLCC → 470 nF** (bliže datasheet 100 nF; 1 µF je bila greška).
2. **BOOT dugme NIJE user-taster** — firmware čita GPIO10/27, treba fizički taster.
3. **LED treba serijski otpornik** (~330 Ω); firmware sad pali **jednu** LED (GPIO2) —
   za zeleno/crveno demo treba 2. LED (GPIO11) + izmjena u app_main.c.
4. **470 µF ublažava strujni špic koji mjeriš u E5** — mjeri prvo BEZ njega, dodaj samo
   ako se javi brownout, dokumentuj oba slučaja (dopuna rizika C7/D2).
5. **Potvrdi da je S3 devkit sa USB+3V3 pinom** (ne goli WROOM-1 modul) prije naručivanja.

### Kompatibilnost sa našim pločama (provjereno)

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

### Plan za drugi ESP32 (DevKit V1) — E4 ablation

1. **Uloga:** izmjeriti koliko PIE SIMD (S3) + esp-nn donose vs identičan kod na
   klasičnom Xtensa LX6 jezgru — matrica {ESP32, S3} × {esp-nn on/off} iz plana 6.1.
2. **Memorijska realnost:** bez PSRAM-a, ~300 KB upotrebljivog heapa. Streaming
   pipeline (vidi docs/model/istrazivanja/edge-adaptacija.md) troši < 15 KB RAM za featuring, pa
   DevKit nosi AE-tiny int8 (67 KB flash, arena ~20–40 KB) bez problema;
   AE-baseline int8 ide tijesno, fp32 ne ide — to JE rezultat za rad (5.4).
3. **Flash 4 MB:** particija `partitions_esp32.csv` (FAT ~1.4 MB ≈ 4 test klipa —
   dovoljno za latencijska mjerenja; puna evaluacija ostaje na S3 sa 20 MB FAT).
4. **Build:** isti firmware, `idf.py set-target esp32` — per-target sdkconfig
   (`sdkconfig.defaults.esp32` bez SPIRAM-a) i pins.h rade automatski.
5. Oba na 240 MHz, Wi-Fi/BT off tokom mjerenja (fer poređenje, rizik D4).
