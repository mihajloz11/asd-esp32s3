# Lemljenje — šta, kojim redom, na šta paziti

> Komponente stigle 04.08.2026 (vidi [hardver-lista.md](hardver-lista.md)).
> Pinovi su fiksirani u [pins.h](../firmware/esp32s3_asd/main/pins.h), šema u
> [sema-povezivanja.md](sema-povezivanja.md). **Ništa ne lemi dok ne provjeriš pin-mapu.**

Princip: **faza 1 = samo headeri** (da moduli uđu u MB-102, sve ostalo se ubada bez
lemilice) → sve proraditi na breadboardu → **faza 2 = finalni zalemljeni sklop** na
prototipnoj ploči 4×6 za demo na odbrani.

---

## FAZA 1 — headeri (obavezno, bez ovoga ne možeš ništa spojiti)

| # | Komponenta | Šta se lemi | Spojeva | Kritično? |
|---|---|---|---|---|
| 1 | **INMP441 #1** | muški header 6 pinova (VDD, GND, SCK, WS, SD, L/R) | 6 | **DA** — bez ovoga nema živog zvuka |
| 2 | **INMP441 #2** (rezerva) | isto, 6 pinova | 6 | tek kad #1 proradi |
| 3 | **INA226** | header 4 pina (VCC, GND, SDA, SCL) — *ako nije već zalemljen*; IN+/IN− su obično već na screw-terminalu | 0–4 | samo za E5 |
| 4 | **AMS1117 3.3V modul** | 3 kontakta (IN, GND, OUT) — header ili žice direktno | 3 | samo za E5 |
| 5 | **ESP32-S3 ploča** | 2 reda headera — **samo ako ploča nije već sa zalemljenim pinovima** | 0 ili ~2×22 | provjeri prvo! |

**Ukupno u najgorem slučaju:** ~60 spojeva. Realno (S3 već ima headere, INA226 stiže
zalemljena): **~19 spojeva.**

### Kako zalemiti header pravo (trik za MB-102)

1. Ubodi mušku letvicu u breadboard (kratke nožice gore).
2. Nasloni modul odozgo na pinove — breadboard ga drži savršeno pod 90°.
3. Zalemi **prvo jedan ugaoni pin**, provjeri da modul stoji ravno, pa ostale.

Letvica se lomi/siječe na dužinu — 40 pinova ima dovoljno za sve (6+6+4+3 = 19 od 80).

### ⚠️ INMP441 — ovo je jedina komponenta koju možeš uništiti

- **MEMS je ESD-osjetljiv** i gine od pregrijavanja. Zato ti i stoje **2 komada**.
- Lemilica **300–350 °C**, **max 2–3 s po pinu**, pauza između pinova.
- **Ne diraj rupicu (sound port) na mikrofonu** — ni prstom, ni fluksom, ni komprimovanim
  zrakom, ni izopropanolom. Ako uđe fluks u membranu — mikrofon je gotov.
- **Ne peri ploču** poslije lemljenja. Ostavi fluks.
- Uzemlji se (dodirni radijator/kućište) prije nego uzmeš modul iz kese.
- Lemi **jedan po jedan mikrofon** — prvi zalemi, testiraj, tek onda drugi.

---

## FAZA 2 — finalni sklop na prototipnoj ploči 4×6 (tek poslije breadboarda)

Ovo lemiš **tek kad cijeli lanac radi na MB-102**. Na breadboardu se sve ubada — nema
potrebe da bilo šta od dole lemiš ranije.

| # | Šta | Gdje | Napomena |
|---|---|---|---|
| 6 | **470 nF keramika** | VDD ↔ GND mikrofona | **što bliže mikrofonu** (< 5 mm). Nije polarizovan. |
| 7 | **10 µF elektrolit** | VDD ↔ GND mikrofona, paralelno sa 470 nF | **polarizovan** — traka/kraća nožica = **minus → GND** |
| 8 | **LED + otpornik** | anoda → 220–330 Ω → **GPIO 2**, katoda → GND | duža nožica = anoda (+). Otpornik može i sa strane katode, svejedno. |
| 9 | **Žice do mikrofona** | SCK/WS/SD/VDD/GND/L-R | **< 10 cm**, GND uz signale (rizik C1). L/R **obavezno na GND**! |
| 10 | **470 µF elektrolit** | INA226 IN− ↔ GND | **polarizovan**. Samo E5, i **samo ako se javi brownout** — vidi napomenu dole |

**470 µF nije stalni dio sklopa.** Iz [sema-povezivanja.md](sema-povezivanja.md): on ublažava
baš onaj strujni špic koji u E5 mjeriš. Mjeri **prvo bez njega**, dodaj samo ako ti ploča
resetuje (brownout), i dokumentuj oba slučaja. Zato ga **ne lemi fiksno** — ostavi ga na
odvojivim kontaktima ili ga drži na breadboardu.

---

## Ne treba lemiti

| Komponenta | Zašto |
|---|---|
| **Arkadni taster 30 mm** | Mikroprekidač ima 2 faston jezička (2,8 mm) — žica se **nabija** na njih. Lemljenje je opciono (ako nemaš faston papučice, prikalajiši žicu na jezičak — 2 spoja, lako). |
| **Sve na MB-102 tokom razvoja** | Kondenzatori, LED, otpornici, žice — sve se ubada. |
| **Set od 120 elektrolita** | Iz njega vadiš samo 10 µF i 470 µF, ostalo ostaje u setu. |

---

## Redoslijed rada (da grešku uhvatiš sloj po sloj)

```
1. Zalemi header na INMP441 #1                    → 6 spojeva, 10 min
2. Ubodi u MB-102, spoji na S3 (4/5/6, L/R→GND)   → bez lemljenja
3. TEST: snimi 5 s WAV na flash → Audacity        ← ovdje se vidi je li mikrofon živ
4. Tek ako radi: header na INMP441 #2 (rezerva)
5. Eval mod (taster pri bootu) → klipovi s flasha
6. Živi rad → LED reaguje
7. Zalemi INA226 + AMS1117 header → E5 (tek poslije INA226 drajvera)
8. NA KRAJU: prebaci sve na 4×6 ploču, zalemi (faza 2)
```

---

## ⚠️ Provjeriti prije lemljenja

1. **Otpornici 220–330 Ω za LED — NISU u porudžbini** (bili su na spisku "iz firme").
   Bez njih **ne vezuj LED na GPIO** — spržićeš pin. Donesi 2 komada s posla.
   *(Napomena: `sema-povezivanja.md` piše 220 Ω, `porudzbina-elektromodul.md` piše 330 Ω —
   oba rade, 330 Ω je sigurniji i tamniji.)*
2. **Ženski headeri nisu naručeni** — na ploči 4×6 moduli idu ili direktno zalemljeni
   (nepovratno) ili preko žica. Ako hoćeš da INMP441 ostane vadiv, uzmi ženski header
   (~30 din) prije faze 2.
3. **Firmware pali SAMO JEDNU LED (GPIO 2).** Imaš crvenu i zelenu, ali za obje treba
   2. pin (GPIO 11) + izmjena u [app_main.c](../firmware/esp32s3_asd/main/app_main.c)
   (`gpio_set_level(PIN_LED, !anomaly)` je trenutno jedan poziv). Za sad zalemi jednu
   (zelenu = normal, gasi se pri anomaliji) ili prvo dopuni kod.
4. **INA226 šant** — po dolasku pročitaj oznaku: `R100` = 0,1 Ω, `R010` = 0,01 Ω.
   Kalibriši multimetrom prije E5.
5. **AMS1117 izlaz izmjeri multimetrom (~3,3 V)** prije nego ga spojiš na S3.
   **Nikad USB i eksterno 3V3 istovremeno.**
6. **Zabranjeni pinovi:** S3 GPIO 35/36/37 (oktalni PSRAM), strapping 0/3/45/46.

## Alat i potrošni

- Lemilica sa podesivom temperaturom, **300–350 °C**, tanki vrh
- Kalajna žica **0,5–0,8 mm** (60/40 sa fluksom je najlakša za ovo)
- Sitna kliješta za sječenje nožica, pinceta
- Multimetar (kontinuitet + napon) — **obavezan** za bring-up
- Opciono: fluks olovka, pumpica/žica za odlemljivanje
