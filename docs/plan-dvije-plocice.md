# Plan: dvije odvojene pločice — uređaj i mjerna

**Datum:** 19.08.2026.
**Status:** plan lemljenja, ništa još nije zalemljeno
**Grafika:** [sema-sklopa.pdf](sema-sklopa.pdf) — 7 strana A4, generiše se sa
[`make_sema_sklopa.py`](make_sema_sklopa.py)
**Zamjenjuje:** raspored „sve na jednoj ploči" iz ranije verzije šeme

---

## 1. Odluka

Sklop se dijeli na **dvije fizički odvojene pločice**:

| | **PLOČA U — uređaj** | **PLOČA M — mjerna** |
|---|---|---|
| Šta radi | detekcija anomalije ventilatora | mjeri potrošnju ploče U (E5) |
| Ploča | prototipna **7 × 9 cm** (24 × 34 rupe) | prototipna **4 × 6 cm**, A1938 (15 × 23 rupe) |
| Napajanje | **powerbank → USB-C** | **zidni punjač 5 V** |
| Kad se koristi | uvijek | jednom, za E5 mjerenje, pa se skida |
| Ostaje zalemljena | da, trajno | da, ali se rasklapa od uređaja |
| Veza između njih | **4 žice** ≈ 20 cm: 3V3 · GND · SDA · SCL | |

Razlog podjele: INA226 grana se koristi **jednom**, traži **otkačen USB** i mijenja
se između mjerenja (sa i bez 470 µF). Nema smisla lemiti je fiksno na ploču koja
inače cijelo vrijeme radi na USB-u. Odvojena, može se donijeti, prikačiti,
izmjeriti i skloniti, a demo-uređaj ostaje netaknut.

Drugi razlog: **ESP32-S3-DevKitC-1 je 63 mm dugačak, a ploča A1938 je 60 mm** —
ne staje. Ploča U mora biti veća, a A1938 se time oslobađa i postaje ploča M.

---

## 2. Šta ide na koju ploču

### 2.1 PLOČA U — na samu ploču se lemi

| Komponenta | Kom | Pakovanje / oznaka | Pozicija na ploči |
|---|---|---|---|
| ESP32-S3-DevKitC-1 N32R16V | 1 | 63,0 × 25,5 mm, 2 × 22 pina | ženski headeri, kolone **4** (J1) i **13** (J3), redovi 4–25 |
| Ženski header 1×22 | 2 | 2,54 mm — **KUPITI ≈ 60 din** | isto |
| Muška letvica 40 pin (A1632) | 2 | 2,54 mm | ~44 pina lemi se **na samu S3 ploču** |
| Prototipna ploča 7×9 cm | 1 | **KUPITI ≈ 100 din** | — |
| LED 5 mm zelena (A3506) | 1 | prozirna | red 31, kolona 7 |
| LED 5 mm crvena (A2177) | 1 | — | red 31, kolona 12 |
| Otpornik 330 Ω 1/4 W | 2 | narandž./narandž./smeđa — **donijeti s posla** | red 29, kolone 5–7 i 10–12 |
| Ženski header 1×6 — **K-MIK** | 1 | **KUPITI** | kolona 20, redovi 5–10 |
| Ženski header 1×2 — **K-TAS** | 1 | **KUPITI** | kolona 20, redovi 14–15 |
| Ženski header 1×4 — **K-M** | 1 | **KUPITI** | kolona 20, redovi 19–22 |
| Gola kalajisana žica | ≈15 cm | — | **GND šina** red 33, **3V3 šina** red 34 |

### 2.2 PLOČA U — dio uređaja, ali NIJE na ploči

| Komponenta | Kom | Gdje je | Zašto ne na ploči |
|---|---|---|---|
| INMP441 (A1477) | 1 | na žicama **< 10 cm** iz K-MIK, usmjeren ka ventilatoru | mora biti kod izvora zvuka |
| Keramika 470 nF (A2400) | 1 | **zalemljena na padove mikrofona** (< 5 mm) | HF dekapling gubi smisao na 10 cm žice |
| Elektrolit 10 µF (iz A642K) | 1 | **zalemljen na padove mikrofona** | isto |
| Arkadni taster 30 mm (A4059) | 1 | 2 faston jezička, žice iz K-TAS | 30 mm, ide na kutiju |
| Powerbank + USB-C kabl | 1 | u USB-C konektor ploče S3 | — |

### 2.3 PLOČA M — na samu ploču se lemi

| Komponenta | Kom | Pakovanje / oznaka | Pozicija na ploči |
|---|---|---|---|
| Prototipna ploča 4×6 cm (A1938) | 1 | **imaš** | ovo je ploča M |
| AMS1117-3.3 modul 800 mA (A1652) | 1 | ≈20 × 10 mm, 4 muška pina **već zalemljena** | red 6 — OUT+ kol. 4, OUT− kol. 5, IN+ kol. 10, IN− kol. 11 |
| INA226 modul (A3627) | 1 | 20,5 × 19,4 mm, jedan shunt **R100 = 0,1 Ω**, adresa **0x44** | red 18, kolone 4–11 |
| Elektrolit 470 µF (iz A642K) | 1 | **polarizovan**, na **vadivim** kontaktima | kolone 13/14, red 20 |
| Ženski header 1×8 (INA226) | 1 | **KUPITI** | red 18 |
| Ženski header 1×2, 2 kom (AMS1117) | 2 | **KUPITI** | red 6 |
| Ženski header 1×2 (470 µF) | 1 | **KUPITI** | red 20 |
| Ženski header 1×2 — **5 V ULAZ** | 1 | **KUPITI** | kolona 14, redovi 3–4 |
| Ženski header 1×4 — **K-U** | 1 | **KUPITI** | kolona 2, redovi 17–20 |
| Gola kalajisana žica | ≈10 cm | — | **GND šina** red 22 |

### 2.4 PLOČA M — van ploče

| Komponenta | Gdje |
|---|---|
| Zidni punjač 5 V + presječen USB kabl | crvena = +5 V, crna = GND → u 5 V ULAZ. **Provjeri multimetrom prije lemljenja.** |
| Kabl 4 žile ≈ 20 cm | K-U (ploča M) ↔ K-M (ploča U). Mogu jumperi. |

> **Powerbank se za E5 NE koristi.** Gasi se pri maloj struji (S3 bez Wi-Fi vuče
> ~30–50 mA, ispod praga nekih powerbanka) i prekinuo bi mjerenje usred runa —
> rizik #2 iz [porudzbina-elektromodul.md](porudzbina-elektromodul.md).
> Za E5 ide zidni punjač na ploču M.

---

## 3. Interfejs K-M ↔ K-U (4 žice)

| Pin | Signal | Ploča M | Ploča U |
|---|---|---|---|
| 1 | **3V3** | čvor *3V3 POTROŠAČ* (poslije shunta) | 3V3 šina — napaja cijelu ploču U |
| 2 | **GND** | GND šina ploče M | GND šina ploče U |
| 3 | **SDA** | INA226 SDA | GPIO 8 (J1-12) |
| 4 | **SCL** | INA226 SCL | GPIO 9 (J1-15) |

**Pravilo koje se ne krši:** *ILI* powerbank preko USB-C *ILI* ploča M preko
K-M/3V3. Nikad oboje — dva izvora na istom 3,3 V čvoru znače da onboard LDO
ploče S3 gura protiv AMS1117.

Redoslijed za E5: otkači USB → ubodi 4-žilni kabl → uključi punjač u struju.
Poslije mjerenja obrnutim redom.

---

## 4. Dvije 3,3 V mreže na ploči M — najveća zamka

Na ploči M postoje **dva odvojena 3,3 V čvora**, i ne smiju se spojiti:

| Čvor | Šta ga čini | Boja na šemi |
|---|---|---|
| **3V3 IZVOR** | AMS1117 OUT+ → INA226 **IN+** i INA226 **VCC** | narandžasto |
| **3V3 POTROŠAČ** | INA226 **IN−** → 470 µF (+) → K-U pin 1 → ploča U | ljubičasto |

Između njih je shunt od **0,1 Ω** i sva mjerena struja ide kroz njega.

> Ako se ta dva čvora spoje, struja zaobiđe shunt: **INA226 mjeri nulu, a ploča U
> i dalje uredno radi.** Greška se ne vidi bez mjerenja. Zato prije prvog
> napajanja izmjeri otpornost IZVOR ↔ POTROŠAČ — mora biti **≈ 0,1 Ω, ne 0 Ω**.

**Izmjena u odnosu na [sema-povezivanja.md](sema-povezivanja.md):** INA226 `VCC`
sada ide na čvor **3V3 IZVOR** (prije shunta), a ne na 3V3 šinu ploče S3.
Time vlastita potrošnja senzora (~350 µA) ne ulazi u E5 rezultat. Ranija verzija
ju je uračunavala.

---

## 5. Redoslijed rada

### Faza A — ploča U (blokira demo i snimak odbrane)

1. Kupiti: ploča 7×9 cm, 2 × ženski header 1×22, ženski headeri 1×6 / 1×2 / 1×4.
   Donijeti s posla: 2 × otpornik 330 Ω.
2. Zalemiti muške letvice na ESP32-S3 ploču (~44 spoja) — ona je stigla bez pinova.
3. Ženski headeri za S3 na ploču U (kolone 4 i 13, redovi 4–25).
4. GND šina (red 33) i 3V3 šina (red 34) — gola kalajisana žica.
5. Otpornici + LED → **test: obrasci lampica** prije nego se ide dalje.
6. Konektori K-MIK, K-TAS, K-M.
7. INMP441 na žice + dekapling **na padove mikrofona** → **test: 5 s WAV**.
8. Taster na faston jezičke.
9. Ploča U radi na powerbanku. Demo sa ventilatorom je time zatvoren.

### Faza B — ploča M (blokira samo E5 mjerenje)

10. Kupiti ženske headere za M (1×8, 2 × 1×2, 1×2, 1×2, 1×4).
11. Zalemiti letvicu 8 pinova na INA226 modul (stigla nezalemljena).
12. Headeri + GND šina na ploču M. AMS1117 se **ne lemi** — ima svoje pinove.
13. **Prije spajanja na ploču U:**
    - izmjeri AMS1117 OUT+ sa punjačem — mora biti ≈ 3,3 V;
    - izmjeri otpornost IZVOR ↔ POTROŠAČ — mora biti ≈ 0,1 Ω;
    - provjeri da GND ploče M i GND ploče U dolaze na isti čvor.
14. Otkači USB sa S3 → ubodi K-M → uključi punjač.
15. Mjeri **prvo BEZ 470 µF**. Dodaj ga samo ako se javi brownout reset, i
    dokumentuj oba slučaja (rizik C7).

---

## 6. Šta ovaj plan ne mijenja

- **Pin-mapa ostaje ista** — [`pins.h`](../firmware/esp32s3_asd/main/pins.h):
  SCK/WS/SD = 4/5/6, I2C = 8/9, taster = 10, LED = 2 i 11. Firmware se ne dira.
- **Jedan mikrofon, ne dva** — zatvoreno mjerenjem 14.08.
  ([PREOSTALO.md](PREOSTALO.md)) Drugi INMP441 ostaje rezerva.
- **470 µF ostaje vadiv**, ne fiksno zalemljen — mjerni kompromis iz
  [sema-povezivanja.md](sema-povezivanja.md), sekcija 2.
- Sve mjere opreza pri lemljenju INMP441 iz [lemljenje.md](lemljenje.md) važe
  nepromijenjeno: 300–350 °C, max 2–3 s po pinu, kapton preko sound porta,
  ne prati ploču poslije lemljenja.

---

## 7. Šta treba kupiti

| Stavka | Kom | Procjena | Za koju ploču |
|---|---|---|---|
| Prototipna ploča 7×9 cm | 1 | ≈ 100 din | U |
| Ženski header 1×22 | 2 | ≈ 60 din | U |
| Ženski header 1×6 / 1×2 / 1×4 | po 1 | ≈ 40 din | U |
| Ženski header 1×8 / 1×2 ×3 / 1×4 | — | ≈ 60 din | M |
| **Ukupno** | | **≈ 260 din** | |

Otpornici 330 Ω (2 kom) se donose s posla — nisu bili u porudžbini.
Sve ostalo je već na stolu.

> Ako se ne kupuju ženski headeri, moduli se leme fiksno i ploče prestaju biti
> rasklopive. Za ploču M to je promašaj cijele ideje — ona se **mora** rasklapati.
> Za S3 na ploči U to znači da se ploča ne može skinuti radi flešovanja preko
> USB-a bez petljanja, pa se ni tu ne isplati štedjeti 60 dinara.

---

## 8. Provjere prije nego se bilo šta napaja

- [ ] Pin se traži po **oznaci na silkscreenu**, ne po broju rupe. J1/J3
      numeracija je iz zvanične Espressif dokumentacije — na klonu provjeri
      multimetrom.
- [ ] Razmak pinova INA226 i AMS1117 **izmjeri lenjirom na svojim komadima**.
      Obrisi u PDF-u su crtani po fotografijama modula, ne po datasheetu klona.
      Strana 5 PDF-a je u razmjeri 1:1 baš za to — štampaj na 100 % i naslaži
      komponente na papir.
- [ ] 3V3 šina ploče U dodiruje **samo** pinove 3V3 i K-M pin 1. Nijedan GPIO
      ne smije na šinu.
- [ ] INMP441 `L/R` **obavezno na GND** — inače firmware čita tišinu (rizik C1).
- [ ] Redoslijed pinova INA226 provjeri po silkscreenu prije lemljenja letvice.
- [ ] Otpornost IZVOR ↔ POTROŠAČ na ploči M ≈ 0,1 Ω (ne 0 Ω, ne prekid).
