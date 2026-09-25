# Porudžbina — elektromodul.rs (✅ ISPORUČENO 04.08.2026)

> **STATUS: naručeno i stiglo kompletno — 3.118 RSD.** Sve stavke 1–10 su na stolu.
> Jedina razlika: taster je isporučen u **plavoj** varijanti (SKU A4059) umjesto crvene —
> isti mikroprekidač, bez uticaja na šemu. Inventar: [inventar.md](inventar.md).
> **Šta se lemi i kojim redom: [lemljenje.md](../sklop/lemljenje.md).**
>
> Ostatak dokumenta je originalna analiza prije kupovine (cijene provjerene 22.07.2026);
> ostavljena je zbog obrazloženja izbora komponenti i analize rizika.
> Detaljno obrazloženje svake stavke: [inventar.md](inventar.md).

## ✅ ŠTA IMAŠ (ne poručuj)

| Komponenta | Status |
|---|---|
| ESP32-S3-WROOM 32MB/16MB (1.890 din) | imaš — to je N32R16V, glavni target |
| USB-to-UART adapter | imaš → CP2102 izbačen iz spiska |
| Protoboard **MB-102** (830 rupa) | imaš — vidi objašnjenje na dnu |

## 🔧 IZ FIRME (donesi, ne kupuj)

| Komponenta | Kom | Za šta |
|---|---|---|
| Otpornik ~330 Ω (1/4 W) | 2 | Serijski uz svaku LED (obavezno — LED se ne veže direktno na GPIO) |
| *(opciono)* Keramika **100 nF X7R** | 2–3 | Ako je imaš na poslu — to je **datasheet-tačna** vrijednost za mikrofon; onda ni 470NF dole ne moraš kupiti |

## 🛒 ŠTA DA PORUČIŠ (elektromodul.rs)

### Obavezno (1–6) — bez ovoga nema eksperimenata

| # | Naziv na sajtu (link) | Kom | Cijena | Ukupno | Uloga |
|---|---|---|---|---|---|
| 1 | [INMP441 I2S Mikrofon za Arduino](https://elektromodul.rs/inmp441-i2s-mikrofon-arduino-cena-srbija/) | 2 | 600 | 1.200 | audio ulaz (+rezerva) |
| 2 | [INA226 I2C senzor struje i snage](https://elektromodul.rs/ina226-i2c-senzor-struje-i-snage-cena-srbija/) | 1 | 300 | 300 | E5 mjerenje potrošnje |
| 3 | [Set 120 Elektrolitskih Kondenzatora 1µF-470µF](https://elektromodul.rs/120-komada-kondenzator-radijalni-12-vrsta/) | 1 | 500 | 500 | daje **10 µF (B)** + **470 µF (C)** |
| 4 | [Keramički kondenzator 470NF – MLCC 50V](https://elektromodul.rs/50v-monolithic-ceramic-capacitor-470nf/) | 3 | 16 | 48 | **VF čišćenje uz mikrofon (A)** |
| 5 | [AMS1117 3.3V LDO Regulator Modul 800mA](https://elektromodul.rs/ams1117-3-3v-ldo-regulator-modul-800ma/) | 1 | 120 | 120 | čist 3,3 V za E5 (bez USB-a) |
| 6 | [Muska Pin Letvica 40 Pinova 2.54mm](https://elektromodul.rs/muska-pin-letvica-40pin-arduino-cena-srbija/) | 2 | 28 | 56 | headeri za 2 mikrofona **+ rezerva za S3 ploču ako je bez headera** |

**Obavezno = 2.224 din**

### Opciono — demo na odbrani + finalni sklop

| # | Naziv na sajtu (link) | Kom | Cijena | Ukupno | Uloga |
|---|---|---|---|---|---|
| 7 | [Dvoslojna prototipna ploča 4×6 cm](https://elektromodul.rs/dvoslojna-prototipna-ploca-4x6-cm-cena-srbija/) | 1 | 120 | 120 | finalni **zalemljen** sklop (MB-102 je za razvoj) |
| 8 | [LED 5mm crvena dioda F5mm](https://elektromodul.rs/led-5mm-crvena-dioda-f5mm/) | 1 | 14 | 14 | demo — anomalija |
| 9 | [LED 5mm Prozirna Dioda Zeleno Svetlo F5mm](https://elektromodul.rs/led-5mm-prozirna-dioda-zeleno-svetlo-f5mm/) | 1 | 80 | 80 | demo — normalan rad |
| 10 | [Crveni taster arkadni 30 mm](https://elektromodul.rs/crveni-kontakt-taster-30mm-za-arkadne-igrice-i-diy-cena-srbija/) | 1 | 140 | 140 | demo taster (GPIO10, interni pull-up) |

**Opciono = 354 din**

## Zbir

| Stavka | Din |
|---|---|
| Obavezno (1–6) | 2.224 |
| + Opciono (7–10) | +354 |
| **Roba ukupno** | **2.578** |
| + Dostava (fiksno) | +540 |
| **UKUPNO ZA PLAĆANJE** | **~3.118 din (~27 €)** |

Samo obavezno + dostava = **2.764 din**.

## Napomene prije plaćanja
1. **Provjeri da S3 ploča ima izvučen 3V3 pin i USB** (pošto flešuješ — skoro sigurno ima).
2. **INA226 šant** po dolasku: oznaka `R100`=0,1 Ω / `R010`=0,01 Ω; kalibriši multimetrom.
3. **AMS1117 izlaz** izmjeri multimetrom (~3,3 V) prije spajanja S3. Nikad USB + eksterno 3V3 istovremeno.
4. **470NF vs 100 nF:** datasheet mikrofona traži 0,1 µF (100 nF); sajt nema pojedinačni 100 nF,
   470NF radi funkcionalno isto za digitalni MEMS. Ako doneseš 100 nF s posla — preskoči stavku 4.

## Analiza rizika (hardver ↔ softver) — provjereno u firmware-u

Prošao sam kroz `main/` da vidim gdje spisak i kod mogu da se ne poklope. Ukratko: **spisak je dobar, ništa ne fali od kupovine za osnovni rad**, ali ima 6 stvari koje mogu da te iznenade pri spajanju.

### ✅ Što je potvrđeno da radi (kod postoji, poklapa se s hardverom)
- **I2S mikrofon:** pinovi 4/5/6, 32-bit slot, **lijevi slot** (L/R→GND), mono, `>>14` shift — INMP441 potpuno podržan ([audio_i2s.c](../../../firmware/esp32s3_asd/main/audio_i2s.c)).
- **PSRAM OCT + 32 MB flash** u sdkconfig-u — tačno za N32R16V, nema boot-loop rizika ako koristiš default.
- **Particija:** 4 MB app + 20 MB FAT za klipove; eval čita PCM16 mono 16 kHz s flasha.
- **Model je ugrađen** (`fan_tiny32_s0` int8, 69 KB) — on-device inferenca ima šta da vrti.
- **LED (GPIO2)** i **taster (GPIO10, interni pull-up, držan pri bootu → eval mod)**.

### ⚠️ Rizici — i može li ih hardver riješiti

| # | Rizik | Rješenje | Hardver? |
|---|---|---|---|
| 1 | **INA226 nema drajver u firmware-u** — pinovi definisani, ali nema I2C koda ni čitanja struje. E5 mjerenje **neće raditi dok ne napišeš I2C drajver** (~pola dana). | Napiši INA226 I2C drajver; ESP32 **sam sebe** mjeri preko I2C. | **Ne** treba dodatni hardver |
| 2 | **Powerbank se sam gasi** pri maloj struji (ESP32 s Wi-Fi off vuče ~30–50 mA, ispod praga nekih powerbanka) → prekid mjerenja usred E5. | Za E5 koristi **5 V punjač telefona** (zidni), ne powerbank — konstantan napon, ne gasi se. | Imaš (punjač) |
| 3 | **S3 ploča možda nema zalemljene headere** → ne možeš je ubosti u breadboard. | Zato 2× pin letvica na spisku. Provjeri ploču; ako je bez headera, zalemi prije svega. | Pokriveno (2× letvica) |
| 4 | **Jumper žice** — treba ti ~20 muško-muško (breadboard) + par žensko-žensko. | Potvrdi da imaš; ako ne, dodaj set (~200 din). | Provjeri zalihe |
| 5 | **MEMS je ESD-osjetljiv i gine pri pregrijavanju** pri lemljenju headera. | Zato 2. INMP441 kao rezerva; lemi brzo, ne diraj membranu. | Pokriveno (2. mik) |
| 6 | **Multimetar** — treba za bring-up (potvrdi 3,3 V, šant, kontinuitet). | Ti si embedded — vrv imaš. Ako ne, bilo koji jeftini. | Imaš |

### Šta bih promijenio / dodao / izbacio
- **DODATO (već u spisku):** 2. pin letvica (28 din) — jeftino osiguranje da uopšte možeš spojiti ploče.
- **NAJVEĆI dobitak na pouzdanost = 0 din:** koristi zidni 5 V punjač umjesto powerbanka za E5 (rizik #2). To ti sam po sebi diže šansu da E5 prođe iz prve.
- **Ništa ne treba izbaciti** — sve je ili obavezno ili jeftin demo/rezerva.
- **Moglo bi biti bolje?** Ne za tvoj slučaj: AMS1117 (linearni) je **namjerno** bolji od buck-a za mjerenje (nema switching šum); INA226 je već bolji izbor od INA219. Ne mijenjaj.

### Redoslijed bring-upa (da uhvatiš grešku sloj po sloj)
1. Samo mikrofon → snimi 5 s WAV na flash → otvori u Audacity (prije ML-a).
2. Eval mod (taster pri bootu) → klipovi s flasha → provjeri da score-ovi imaju smisla.
3. Živi rad (mikrofon) → LED reaguje.
4. **Tek na kraju** INA226 + E5 (poslije pisanja drajvera) + napajanje preko AMS1117/punjača.

---

## Šta je MB-102?

**MB-102** je oznaka standardne **breadboard / protobord ploče sa 830 rupa** — bijela plastična
ploča u koju **utiskuješ nožice komponenti bez lemljenja**. To je ono na čemu praviš privremeni
sklop dok razvijaš: ubodeš INMP441, INA226, žice i sve spojiš bez lemilice, pa lako mijenjaš
ako nešto ne radi.

- **Uloga u radu:** razvoj i prvo testiranje (snimi 5 s WAV, provjeri I2S, itd.).
- **Zašto onda prototipna ploča 4×6 (stavka 7)?** Za **finalnu, zalemljanu** verziju — na breadboardu
  žice znaju ispasti i I2S linije sa dugim jumperима hvataju šum. Za demo na odbrani hoćeš čvrst,
  zalemljen sklop sa kratkim vezama (pravilo <10 cm). MB-102 = razvoj, 4×6 lemljena = finalno.
- MB-102 često dolazi i sa malim žutim **MB-102 power supply** modulom (3,3/5 V na šine breadboarda) —
  njega **ne koristiš** za E5 mjerenje (za to ide AMS1117 preko INA226), ali je zgodan za obično napajanje.
