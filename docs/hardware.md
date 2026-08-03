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

Izvor: **elektromodul.rs** (lager u Srbiji, sve u jednoj pošiljci, isti dan do 13h).
Nazivi su tačno kako stoje na sajtu — kucaš ih u pretragu. Cijene provjerene 22.07.2026.

### Obavezno (bez ovoga nema E5/E6/demo)

| Naziv na sajtu | Kom | Cijena | Svrha |
|---|---|---|---|
| INMP441 I2S Mikrofon za Arduino | 2 | 600 | Audio ulaz. 1 obavezan, 2. je rezerva (MEMS krhak, rizik C1) + po jedan na S3 i DevKit V1 |
| INA226 I2C senzor struje i snage | 1 | 300 | Cijeli E5. Provjeri šant po dolasku: R100=0,1 Ω / R010=0,01 Ω; kalibriši multimetrom |
| Set 120 Elektrolitskih Kondenzatora 1µF-470µF — 12 Vrednosti | 1 | 500 | Daje **10 µF** (bulk uz mikrofon) i **470 µF** (poslije INA, rizik C7) |
| Keramički kondenzator 470NF (Monolithic Ceramic) – MLCC 50V | 3 | 16 | HF decoupling uz VDD mikrofona. Datasheet traži 100 nF X7R; sajt nema pojedinačni 100 nF — 470 nF je funkcionalno identičan za digitalni MEMS. Po jedan na svaki mik + rezerva |

### Za E5 mjerenje potrošnje (rizik D2 — napajanje bez USB-a)

| Naziv na sajtu | Kom | Cijena | Svrha |
|---|---|---|---|
| AMS1117 3.3V LDO Regulator Modul 800mA | 1 | 120 | Powerbank 5V → čist 3,3 V → INA → ploča. Linearni (nema switching ripple u mjerenju). Izmjeri izlaz multimetrom prije spajanja S3 |
| CP2102 USB to TTL UART modul 6Pin 3.3V/5V | 1 | 450 | Čitanje logova kad je USB otkačen. Veži **samo TX(S3)→RXD i GND→GND, NE VCC** |

### Montaža

| Naziv na sajtu | Kom | Cijena | Svrha |
|---|---|---|---|
| Muska Pin Letvica 40 Pinova 2.54mm za Arduino | 1 | 28 | INMP441 breakout često stigne bez zalemljenih headera |
| Dvoslojna prototipna ploča 4×6 cm | 1 | 120 | Kratke I2S veze (<10 cm) — integritet digitalnog signala, rizik C1 |

### Demo na odbrani (opciono)

| Naziv na sajtu | Kom | Cijena | Svrha |
|---|---|---|---|
| LED 5mm crvena dioda F5mm | 1 | 14 | Anomalija |
| LED 5mm Prozirna Dioda Zeleno Svetlo F5mm | 1 | 80 | Normalan rad |
| Crveni taster za arkadne igrice i DIY 30 mm | 1 | 140 | Momentary, 2 žice na GPIO10+GND (interni pull-up). Firmware čita GPIO10/27 — **NE** BOOT (GPIO0 je strapping) |

**NE naručuj** (imaš / donosi s posla):
- 2× otpornik ~330 Ω za LED (set 600 kom je bacanje para za 2 komada)
- 10 µF i 470 µF posebno — već u setu elektrolita

Ukupno: obavezno = **2.048 din**, +E5 = **2.618**, +montaža = **2.766**, sve sa demo = **~3.000 din (~26 €)**.

### Ispravke u odnosu na prvu verziju (22.07)
1. **1 µF MLCC → 470 nF** (bliže datasheet 100 nF; 1 µF je bila greška).
2. **BOOT dugme NIJE user-taster** — firmware čita GPIO10/27, treba fizički taster.
3. **LED treba serijski otpornik** (~330 Ω); firmware sad pali **jednu** LED (GPIO2) —
   za zeleno/crveno demo treba 2. LED (GPIO11) + izmjena u app_main.c.
4. **470 µF ublažava strujni špic koji mjeriš u E5** — mjeri prvo BEZ njega, dodaj samo
   ako se javi brownout, dokumentuj oba slučaja (dopuna rizika C7/D2).
5. **Potvrdi da je S3 devkit sa USB+3V3 pinom** (ne goli WROOM-1 modul) prije naručivanja.

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
