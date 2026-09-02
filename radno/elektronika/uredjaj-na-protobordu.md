# Uređaj na protobordu — odluka, šta se kupuje, kako se veže

**Datum:** 02.09.2026.
**Odluka:** uređaj ostaje na protobordu **MB-102**, ne lemi se na ploču.
LED, otpornici i taster idu na **3D štampani držač**, na žicama.
Mjerni dio (AMS1117 + INA226 + 470 µF) je i dalje odvojena cjelina —
[lemljenje-cjeline-i-mjerenje.md](lemljenje-cjeline-i-mjerenje.md).

---

## 1. Da li protobord ima smisla — da

Ne zato što je lakše, nego zato što je **već dokazano**:

| Dokaz | Gdje |
|---|---|
| Mikrofon proradio na protobordu 06.08. (BCLK 4, WS 5, SD 6, L/R→GND) | [dnevnik-projekta.md](../../docs/dnevnik-projekta.md) |
| FAN01 fizički test 16.08. — ista postavka | [rezultat-fan01-2026-08-16.md](../../docs/rezultat-fan01-2026-08-16.md) |
| Dva validna fizička runa 27.08. — ista postavka | [rezultat-finalna-validacija-2026-08-27.md](../../docs/rezultat-finalna-validacija-2026-08-27.md) |

I2S ovdje radi na ~1 MHz (16 kHz × 32 bita × 2 kanala), što je za protobord
sitnica. Sve tvrdnje rada koje već stoje u dokumentaciji izmjerene su na
protobordu — lemljenje uređaja ne bi dodalo nijedan novi rezultat.

**Protobord koji imaš:** MB-102, 830 tačaka
([hardver-lista.md](hardver-lista.md)). To je onaj sa dvije napojne šine sa svake
strane i srednjim kanalom — ESP32-S3-DevKitC-1 je 25,5 mm širok i **staje preko
srednjeg kanala**, sa po jednim slobodnim redom kontakata sa svake strane.

### Jedini uslov — vrijedi samo tokom E5 mjerenja

Prošlo mjerenje je palo na **~2 Ω serijskog otpora u napojnoj grani** i 205 mV
greške napona, i uzrok je bio razvod preko protoborda
([e5-mjerenje-01-rezultat.md](e5-mjerenje-01-rezultat.md)).

Zato, kad kačiš mjernu ploču:

```
   3V3 i GND sa mjerne ploče idu PRAVO na 3V3 i GND pinove ESP32-S3,
   kratkom debljom žicom — NE na napojne šine protoborda.

   Šine protoborda se onda napajaju IZ ESP32-S3 pinova i nose samo
   mikrofon (nekoliko mA), gdje pad napona ne znači ništa.
```

U normalnom radu (powerbank preko USB-C) ovo nije bitno — vezuj kako ti je zgodno.

---

## 2. Podjela na tri fizičke stvari

| # | Gdje | Šta |
|---|---|---|
| 1 | **MB-102 protobord** | ESP32-S3-DevKitC-1, napojne šine 3V3 i GND |
| 2 | **na žicama < 10 cm** | INMP441 + 470 nF + 10 µF **zalemljeni na padove mikrofona** |
| 3 | **3D štampani držač** | 2 LED + 2 otpornika + arkadni taster, na žicama proizvoljne dužine |

Zašto mikrofon nije na protobordu: mora da gleda ka ventilatoru, a duge I2S žice
su rizik C1. Zato ide na kratke žice, sa kondenzatorima na sebi.

Zašto LED i taster smiju na duge žice: to su statički signali, ne takt.
Držač može biti i pola metra daleko, ništa se ne kvari.

---

## 3. Šta kupuješ — samo otpornici

**Kondenzatore NE kupuješ. Sve tri vrijednosti već imaš na stolu.**

| Kondenzator | Imaš ga kao | Gdje ide |
|---|---|---|
| **470 nF keramika** | A2400, 3 kom | VDD–GND mikrofona, bez polariteta. Datasheet traži 100 nF; 470 nF radi isto za digitalni MEMS. |
| **10 µF elektrolit** | iz seta A642K (120 kom) | paralelno uz njega, **+ na VDD**, − na GND |
| **470 µF elektrolit** | iz istog seta | mjerna ploča, na 3V3 POTROŠAČ, **vadiv** |

Nema redne ni paralelne veze nigdje. Svaka vrijednost postoji kao jedan komad.

### Otpornici — 2 vrijednosti, ne jedna

Napajanje je 3,3 V, a dvije LED imaju bitno različit `Vf`, pa jedna vrijednost
ne pokriva obje:

| LED | `Vf` (tipično) | 330 Ω | 220 Ω | 100 Ω | Uzmi |
|---|---|---|---|---|---|
| **crvena** (A2177) | ≈ 1,9 V | **4,2 mA** ✔ | 6,4 mA | 14 mA | **330 Ω** |
| **zelena prozirna** (A3506) | 2,1 V ili 3,0 V* | 0,9 mA ✘ | 1,4 mA — granično | **3–12 mA** ✔ | **100 Ω** |

\* Prozirno sočivo obično znači InGaN visoke svjetline sa `Vf ≈ 3,0–3,2 V`.
Sa 3,3 V napajanja tu ostaje 0,1–0,3 V na otporniku, pa 330 Ω daje ispod 1 mA i
LED izgleda kao da je firmware pokvaren. **100 Ω je bezbjedno u oba slučaja**
(kod `Vf = 2,1 V` daje 12 mA, što je i dalje uredu i za LED i za GPIO).

**Provjeri prije nego kupiš:** multimetar u diodnom režimu na zelenu LED. Displej
pokaže `Vf`. Ako pokaže preko 3,1 V, nijedan otpornik neće pomoći — tada uzmi
običnu difuznu zelenu LED (`Vf ≈ 2,1 V`) i vozi je sa 330 Ω.

### Porudžbina

| Šta | Kom | Gdje | Cijena |
|---|---|---|---|
| Otpornik **330 Ω** 1/4 W | 10 (min. pakovanje) | Mikro Princ, `RM1/4 330`, ident **32004** | 2,28 din/kom |
| Otpornik **100 Ω** 1/4 W | 10 (min. pakovanje) | Mikro Princ, traži `RM1/4 100` | ≈ 2,3 din/kom |

**Ukupno ≈ 46 din.** Treba ti po jedan komad od svake; ostatak je rezerva.
Ako ih ima s posla, ne kupuj ništa — vrijednosti su standardne i nose se u
svakoj kutiji otpornika.

Ostalo sa ranijeg spiska (ženske letvice, ploča 100×50, 100 nF keramika)
**otpada** — to je bilo za lemljenje uređaja, a uređaj se ne lemi.

---

## 4. Kako se veže

### Na protobordu

```
   ESP32-S3 preko srednjeg kanala MB-102.
   Sa ploče na šine:  3V3 pin → crvena šina,  GND pin → plava šina.

   INMP441 (na žicama < 10 cm)        ESP32-S3
   ───────────────────────────        ────────
   VDD  ─────────────────────────── 3V3 šina    ┐ 470 nF (bez polariteta)
   GND  ─────────────────────────── GND šina    ┘ 10 µF (+ na VDD)
   SCK  ─────────────────────────── GPIO 4        oba na padove mikrofona
   WS   ─────────────────────────── GPIO 5
   SD   ─────────────────────────── GPIO 6
   L/R  ─────────────────────────── GND šina    ← obavezno, inače čita tišinu
```

### Na 3D držaču

```
   GPIO 2  ──[ 100 Ω ]──▶|── GND šina     ZELENA LED — status
   GPIO 11 ──[ 330 Ω ]──▶|── GND šina     CRVENA LED — alarm
             ▲ duža nožica (anoda) ka otporniku

   GPIO 10 ────── taster ────── GND šina   interni pull-up, bez otpornika
```

Otpornik prati **LED, ne pin**: 100 Ω uvijek uz zelenu, 330 Ω uvijek uz crvenu.
Raspored pinova je iz [`pins.h`](../../firmware/esp32s3_asd/main/pins.h) —
GPIO 2 je status (zelena), GPIO 11 je alarm (crvena).

**Držač:** 5 žica ka protobordu (2 LED + 2 otpornika idu u seriju na samom
držaču, pa iz njega izlaze 2 signalne žice + 1 zajednički GND, plus 2 žice
tastera). Taster ima faston jezičke 2,8 mm — žica se nabija, ne lemi.

**Zamka:** taster **ne smije biti pritisnut pri uključenju** — firmware to čita
kao ulazak u EVAL mod.

---

## 5. Šta ova odluka ne mijenja

- **Mjerna ploča se i dalje lemi** na 4×6 cm. Ona je jedina koja ima razlog za
  lemljenje: prošlo E5 mjerenje je palo baš zbog protoborda.
- **Pin-mapa ostaje ista** — firmware se ne dira.
- **Kondenzatori mikrofona ostaju zalemljeni na mikrofon**, ne na protobord.
  Na 10 cm žice dekapling na drugom kraju ne radi ništa.
- Ranije crtani fizički raspored ploče U
  ([`sema-sklopa.pdf`](sema-sklopa.pdf), strana 3) ostaje u dokumentaciji kao
  varijanta ako se ikad predomisliš. Tabela veza sa strane 6 važi nepromijenjeno
  i za protobord.
