# Lemljenje — kratka verzija (šta ponijeti, šta na šta)

> Puna procedura i mjere opreza: [lemljenje.md](lemljenje.md) · Koji pin gdje ide: [sema-povezivanja.svg](sema-povezivanja.svg)

![Šta se lemi](sema-lemljenje.svg)

## 1. Ponesi na posao (za lemljenje)

| Komponenta | Lemi se | Spojeva |
|---|---|---|
| **INMP441 #1** | muška letvica 6 pinova | 6 |
| **INMP441 #2** (rezerva) | isto — tek kad #1 progovori | 6 |
| **AMS1117 3.3V** | 3 kontakta (IN, GND, OUT) | 3 |
| **INA226** | 4 pina — **samo ako header nije već zalemljen** | 0–4 |
| **ESP32-S3 ploča** | 2 reda headera — **samo ako nema pinove**, provjeri prije pakovanja | 0 ili ~2×22 |
| **Muška letvica 40 pin** (obje) | materijal — siječe se na dužinu | — |

**Realno: ~15 spojeva.** Najgori slučaj ~60, ako i S3 i INA226 idu bez headera.

Prototipnu ploču 4×6, kondenzatore, LED i taster **ostavi kod kuće** — to je faza 2.

## 2. Šta se za šta lemi (pin po pin)

**INMP441** — muška letvica, pa se modul ubada u MB-102:

| Pin mikrofona | Ide na S3 |
|---|---|
| VDD | 3V3 |
| GND | GND |
| SCK | GPIO 4 |
| WS | GPIO 5 |
| SD | GPIO 6 |
| L/R | **GND** (obavezno — bez toga nema zvuka na lijevom slotu) |

**AMS1117** — 3 kontakta: IN ← 5 V zidni punjač · GND zajednički · OUT → 3V3 ploče.
Samo za E5, i **nikad istovremeno sa USB napajanjem**.

**INA226** — 4 pina: VCC → 3V3 · GND → GND · SDA → GPIO 8 · SCL → GPIO 9.
IN+/IN− idu na screw-terminal, tu se ništa ne lemi.

**ESP32-S3** — ako ide header, lemi se cijeli red; pinovi su već fiksirani u
[pins.h](../firmware/esp32s3_asd/main/pins.h), ne mijenjaj ih.

## 3. Nađi na poslu

| Šta | Kom | Zašto |
|---|---|---|
| **Otpornik 220–330 Ω** (1/4 W) | 2 | **Obavezno** — bez njega LED ne ide na GPIO, spržiš pin |
| Keramika **100 nF X7R** | 2–3 | Opciono, ali datasheet-tačna vrijednost za mikrofon (bolja od 470 nF koju imaš) |
| Ženski header 2.54 mm | 1 | Opciono — da INMP441 ostane vadiv u fazi 2 |
| Lemilica sa podesivom temperaturom, tanki vrh | — | 300–350 °C |
| Kalaj 0,5–0,8 mm, pinceta, sitna kliješta, multimetar | — | Multimetar je obavezan za bring-up |

## 4. Spajaš sad bez lemljenja (MB-102)

- Sve žice S3 ↔ INMP441 (4/5/6 + VDD/GND, L/R na GND)
- Kondenzatori 470 nF, 10 µF, 470 µF — ubadaju se
- LED + otpornik — ubada se
- **Arkadni taster** — faston jezičci 2,8 mm, žica se nabija, **ne lemi se uopšte**
- INA226 i AMS1117 ako već imaju kontakte — samo žice

## 5. Redoslijed (grešku hvataš sloj po sloj)

```
1. Header na INMP441 #1                       → 6 spojeva, ~10 min
2. Ubodi u MB-102, spoji na S3 (4/5/6, L/R→GND)
3. TEST: snimi 5 s WAV na flash → Audacity    ← ovdje se vidi je li mikrofon živ
4. Tek ako radi: header na INMP441 #2
5. Eval mod (taster pri bootu) → klipovi s flasha
6. Živi rad → LED reaguje
7. INA226 + AMS1117 → E5 (tek poslije I2C drajvera)
8. NA KRAJU: sve na ploču 4×6 (faza 2)
```

## ⚠️ Tri stvari koje te mogu koštati

1. **INMP441 je jedina komponenta koju možeš uništiti.** 300–350 °C, **max 2–3 s po pinu**,
   pauza između. **Ne diraj sound port** (ni prstom, ni fluksom, ni izopropanolom),
   **ne peri ploču** poslije. Uzemlji se prije vađenja iz kese. Zato lemiš jedan po jedan.
2. **Otpornici fale** — bez 220–330 Ω ne vezuj LED na GPIO.
3. **Firmware pali samo jednu LED (GPIO 2).** Imaš crvenu i zelenu; za obje treba GPIO 11
   + izmjena u [app_main.c](../firmware/esp32s3_asd/main/app_main.c). Za sad zalemi zelenu
   (svijetli = normal, gasi se pri anomaliji).
