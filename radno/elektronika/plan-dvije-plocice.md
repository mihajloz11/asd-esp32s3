# Plan: dvije odvojene pločice — uređaj i mjerna

**Datum:** 19.08.2026. · *dopunjeno: dimenzije, nabavka, varijanta sa laboratorijskim napajanjem, ispravka VBS*
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
| Ploča | **100 × 50 mm** (18 × 38 rupa) — KUPITI | **40 × 60 mm**, A1938 (15 × 23 rupe) — imaš |
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

Provjera dimenzija je urađena i za jednu i za drugu ploču — sekcija 2.5.

---

## 2. Šta ide na koju ploču

### 2.1 PLOČA U — na samu ploču se lemi

| Komponenta | Kom | Pakovanje / oznaka | Pozicija na ploči |
|---|---|---|---|
| ESP32-S3-DevKitC-1 N32R16V | 1 | 63,0 × 25,5 mm, 2 × 22 pina | ženski headeri, kolone **3** (J1) i **12** (J3), redovi 4–25 |
| Ženski header 1×22 | 2 | reže se iz letvice 40x1 F — **KUPITI** | isto |
| Muška letvica 40 pin (A1632) | 2 | 2,54 mm | ~44 pina lemi se **na samu S3 ploču** |
| Test ploča 100×50 tačke | 1 | Mikro Princ ident **057516** — **KUPITI 144 din** | — |
| LED 5 mm zelena (A3506) | 1 | prozirna | red 33, kolona 6 |
| LED 5 mm crvena (A2177) | 1 | — | red 33, kolona 12 |
| Otpornik 330 Ω 1/4 W | 2 | Mikro Princ **RM1/4 330**, ident 32004 — **KUPITI** | red 30, kolone 4–6 i 10–12 |
| Ženski header 1×6 — **K-MIK** | 1 | iz letvice | kolona 16, redovi 3–8 |
| Ženski header 1×2 — **K-TAS** | 1 | iz letvice | kolona 16, redovi 12–13 |
| Ženski header 1×4 — **K-M** | 1 | iz letvice | kolona 16, redovi 17–20 |
| Ženski header 1×3 — **K-UART** | 1 | iz letvice | kolona 16, redovi 24–26 |
| Gola kalajisana žica | ≈15 cm | — | **GND šina** red 37, **3V3 šina** red 38 |

### 2.2 PLOČA U — dio uređaja, ali NIJE na ploči

| Komponenta | Kom | Gdje je | Zašto ne na ploči |
|---|---|---|---|
| INMP441 (A1477) | 1 | na žicama **< 10 cm** iz K-MIK, usmjeren ka ventilatoru | mora biti kod izvora zvuka |
| Keramika 100 nF | 1 | **zalemljena na padove mikrofona** (< 5 mm) — Mikro Princ **CKM 0.1uF/63V RM2.5** | HF dekapling gubi smisao na 10 cm žice |
| Elektrolit 10 µF (iz A642K) | 1 | **zalemljen na padove mikrofona** | isto |
| Arkadni taster 30 mm (A4059) | 1 | 2 faston jezička, žice iz K-TAS | 30 mm, ide na kutiju |
| Powerbank + USB-C kabl | 1 | u USB-C konektor ploče S3 | — |

### 2.3 PLOČA M — na samu ploču se lemi

| Komponenta | Kom | Pakovanje / oznaka | Pozicija na ploči |
|---|---|---|---|
| Prototipna ploča 4×6 cm (A1938) | 1 | **imaš** | ovo je ploča M |
| AMS1117-3.3 modul 800 mA (A1652) | 1 | ≈20 × 10 mm, 4 muška pina **već zalemljena** | red 6 — OUT+ kol. 4, OUT− kol. 5, IN+ kol. 10, IN− kol. 11 |
| INA226 modul (A3627) | 1 | 20,5 × 19,4 mm, jedan shunt **R100 = 0,1 Ω**, adresa **0x44** | red 18, kolone 4–11 · **VBS se spaja**, vidi 4.1 |
| Elektrolit 470 µF (iz A642K) | 1 | **polarizovan**, na **vadivim** kontaktima | kolone 13/14, red 20 |
| Ženski header 1×8 (INA226) | 1 | iz letvice | red 18 |
| Ženski header 1×2, 2 kom (AMS1117) | 2 | iz letvice | red 6 |
| Ženski header 1×2 (470 µF) | 1 | iz letvice | red 20 |
| Ženski header 1×2 — **5 V ULAZ** | 1 | iz letvice | kolona 14, redovi 3–4 |
| Ženski header 1×4 — **K-U** | 1 | iz letvice | kolona 2, redovi 17–20 |
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

### 2.5 Provjera dimenzija — staje li sve

**PLOČA M na A1938 (40 × 60 mm) — staje, sa 64 % praznog prostora.**

Korisna mreža 15 × 23 rupe = **35,6 × 55,9 mm = 1 987 mm²**.

| Komponenta | Gabarit | Površina |
|---|---|---|
| INA226 modul | 20,5 × 19,4 mm | 398 mm² |
| AMS1117-3.3 modul | 20,0 × 10,0 mm | 200 mm² |
| Elektrolit 470 µF (Ø 8 mm) | ≈ 9 × 9 mm | 81 mm² |
| 5 V ULAZ 1×2 | 5,1 × 2,5 mm | 13 mm² |
| K-U 1×4 | 10,2 × 2,5 mm | 26 mm² |
| **Ukupno** | | **717 mm² = 36 % mreže** |

Kritična je visina, ne površina — dva modula jedan ispod drugog:

| Od gornje ivice | Šta |
|---|---|
| 2,1 – 12,1 mm | AMS1117 tijelo (10 mm) |
| 12,1 – 22,6 mm | slobodno, tu prolazi šina *3V3 IZVOR* (red 8) |
| 22,6 – 42,0 mm | INA226 tijelo (19,4 mm) |
| 42,0 – 49,6 mm | INA226 pinovi (red 18), K-U, 470 µF |
| 49,6 – 54,6 mm | GND šina (red 22) |
| **rezerva** | **5,4 mm do ivice** |

Zaključak: **kupljena A1938 je dovoljna za cijeli mjerni dio.** Ne treba ništa veće.

**PLOČA U — 100 × 50 mm.** ESP32-S3 leži uz dužu stranu:

- S3 zauzima 63 × 25,5 mm; pinovi 22 × 2,54 = 53,34 mm, redovi headera 22,86 mm (9 rastera).
- Uz 100 mm dužine ostaje **≈ 33 mm** iza S3, uz 50 mm širine ostaje **≈ 21 mm** sa strane.
- U taj slobodan dio staju sva tri konektora (K-MIK, K-TAS, K-M), obje LED sa
  otpornicima, i obje šine preko cijele širine ploče.

Zašto ne manje: **100 × 50 mm je najmanja „tačke" ploča koju Mikro Princ ima.**
Ponuda je 100×50 (144 din), 100×75 (210), 100×100 (270), 100×160 (420) — nema
7×9 ni 6×8 cm. Sa S3 od 63 mm, 100 × 50 je i logički minimum.

---

### 2.6 Varijanta A — laboratorijsko napajanje, mjerni dio na MB-102

**Ovo je preporučena varijanta ako se mjerenje radi na poslu.**

Cijeli mjerni dio postoji zato što nije bilo regulisanog izvora 3,3 V. Sa
laboratorijskim napajanjem (podesiv napon i strujna granica) polovina njega
otpada:

| Šta | Varijanta osnovna (zidni punjač) | **Varijanta A (lab. napajanje)** |
|---|---|---|
| Izvor | punjač 5 V | lab. napajanje na **3,3 V** |
| 5 V ULAZ 1×2 | treba | **ne treba** |
| AMS1117-3.3 | treba (5 V → 3,3 V) | **ne treba** — lab. napajanje je već regulisano |
| INA226 | treba | treba |
| 470 µF | vadiv | vadiv |
| Nosač | ploča M, zalemljena | **MB-102, ništa se ne lemi** |

Ostaje samo: **INA226 + 470 µF + četiri žice** ka ploči U. To se ubode u MB-102
za dvije minute i rasklopi kad se završi.

```
lab. napajanje 3,3 V  ──→  INA226 IN+   (čvor 3V3 IZVOR, tu ide i VCC)
                                │ shunt 0,1 Ω
                           INA226 IN−   (čvor 3V3 POTROŠAČ, tu ide i VBS)
                                ├──→  470 µF (+)   [vadiv]
                                └──→  K-M pin 1 na ploči U
lab. napajanje  −     ──→  GND šina  ──→  K-M pin 2
                           INA226 SDA ──→  K-M pin 3   (GPIO 8)
                           INA226 SCL ──→  K-M pin 4   (GPIO 9)
```

**Šta se i dalje mora zalemiti:** letvica od 8 pinova na sam INA226 modul —
stigao je nezalemljen i bez toga ne ulazi u MB-102. To je 8 spojeva, ne cijela
ploča.

**Podešavanje lab. napajanja prije nego išta spojiš:**

- napon **3,30 V**, provjeren multimetrom na krajevima kablova, ne po displeju;
- strujna granica **300–500 mA** — to je jedina zaštita koju imaš, jer 3V3 pin
  zaobilazi onboard LDO ploče S3;
- **nikad preko 3,6 V** — to je apsolutni maksimum ESP32-S3. Pogrešno okrenuta
  dugmad = mrtva ploča, bez upozorenja.

**Rizik varijante A:** kontakti na MB-102 su opružni i mogu zaigrati. Padne li
kontakt usred runa, S3 se resetuje (brownout) i run je nevažeći. To se odmah
vidi jer uređaj krene ispočetka, pa nije tiha greška. Mjere: kratke krute žice,
pritisnuti do kraja, ne pomjerati ploču tokom mjerenja. Ako se ponovi — tek tada
se isplati lemiti ploču M.

**Kada ipak lemiti ploču M na A1938:** ako mjerenje ne prolazi iz prve i mora se
ponavljati, ili ako se E5 radi više puta u različitim uslovima. Staje sa viškom
(sekcija 2.5), pa je to uvijek otvorena opcija — ne gubiš ništa time što prvo
probaš na MB-102.

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

Redoslijed za E5: otkači USB → ubodi 4-žilni kabl → uključi napajanje.
Poslije mjerenja obrnutim redom.

### 3.1 K-UART 1×3 — čitanje dok je USB otkačen

USB mora biti otkačen tokom E5, a s njim odlazi i serijska konzola preko
onboard CH343 mosta. Dvije opcije:

| Opcija | Šta treba | Napomena |
|---|---|---|
| **UART adapter** | USB-TTL adapter (3,3 V) na K-UART | logovi uživo tokom mjerenja |
| **Log u flash** | ništa | čitaš poslije, preko USB-a |

| K-UART pin | S3 | Na adapteru |
|---|---|---|
| 1 **TX** | J3-2, GPIO43 | ide na **RX** adaptera |
| 2 **RX** | J3-3, GPIO44 | ide na **TX** adaptera |
| 3 **GND** | GND šina | zajednička masa |

Header je 3 rupe i praktično ništa ne košta sada, a poslije se ne može dodati
uredno. Zalemi ga bez obzira na to koju opciju biraš.

> CH343 ostaje spojen na te iste linije i kad je USB izvučen. U praksi radi, ali
> ako adapter ne uhvati ništa, to je prvo mjesto gdje treba gledati.

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

### 4.1 VBS mora biti spojen — ispravka

Ranija verzija ove šeme je govorila da `VBS` ostaje prazan. **To je bilo pogrešno.**

Firmware u [`ina226_test.c`](../../firmware/esp32s3_asd/main/ina226_test.c) u svakom
očitavanju čita četiri veličine:

```c
ina226_shunt_uv(&shunt_uv);
ina226_bus_mv(&bus_mv);
ina226_current_ua(&cur_ua);
ina226_power_uw(&pwr_uw);
```

`bus_mv` dolazi iz registra napona magistrale, a `pwr_uw` INA226 računa interno
kao *napon magistrale × struja*. Oba mjere napon na pinu **VBS** u odnosu na GND.
Ako VBS visi u vazduhu, ta dva registra su **nula ili smeće**, i cijelo E5
mjerenje energije je bezvrijedno — a struja i shunt napon i dalje izgledaju
tačno, pa se greška ne primijeti dok se ne pogleda snaga.

**VBS ide na čvor *3V3 POTROŠAČ*** — isti čvor kao `IN−`, 470 µF (+) i K-U pin 1.
To je napon koji ESP32-S3 stvarno dobija, pa je i snaga onda stvarna snaga
potrošača. `ALE` ostaje jedini nepovezan pin.

**Izmjena u odnosu na [sema-povezivanja.md](sema-povezivanja.md):** INA226 `VCC`
sada ide na čvor **3V3 IZVOR** (prije shunta), a ne na 3V3 šinu ploče S3.
Time vlastita potrošnja senzora (~350 µA) ne ulazi u E5 rezultat. Ranija verzija
ju je uračunavala.

---

## 5. Redoslijed rada

### Faza A — ploča U (blokira demo i snimak odbrane)

1. Naručiti sa Mikro Princa (sekcija 7) — ploča, 3 letvice ženskih pinova,
   10 × otpornik 330 Ω, 1 × keramika 100 nF.
2. Zalemiti muške letvice na ESP32-S3 ploču (~44 spoja) — ona je stigla bez pinova.
3. Ženski headeri za S3 na ploču U (kolone 3 i 12, redovi 4–25).
4. GND šina (red 37) i 3V3 šina (red 38) — gola kalajisana žica.
5. Otpornici + LED → **test: obrasci lampica** prije nego se ide dalje.
6. Konektori K-MIK, K-TAS, K-M.
7. INMP441 na žice + dekapling **na padove mikrofona** → **test: 5 s WAV**.
8. Taster na faston jezičke.
9. Ploča U radi na powerbanku. Demo sa ventilatorom je time zatvoren.

### Faza B — mjerni dio (blokira samo E5 mjerenje)

> Prvo pročitaj **2.6**. Sa laboratorijskim napajanjem na poslu preskačeš
> korake 10, 12 i AMS1117 — ubodeš INA226 i 470 µF u MB-102 i to je to.

10. Isjeći ženske headere za M iz letvice (1×8, 2 × 1×2, 1×2, 1×2, 1×4).
11. Zalemiti letvicu 8 pinova na INA226 modul (stigla nezalemljena).
12. Headeri + GND šina na ploču M. AMS1117 se **ne lemi** — ima svoje pinove.
13. **Prije spajanja na ploču U:**
    - izmjeri AMS1117 OUT+ sa punjačem — mora biti ≈ 3,3 V;
    - izmjeri otpornost IZVOR ↔ POTROŠAČ — mora biti ≈ 0,1 Ω;
    - provjeri da GND ploče M i GND ploče U dolaze na isti čvor.
14. Otkači USB sa S3 → ubodi K-M (i K-UART ako čitaš uživo) → uključi napajanje.
15. Mjeri **prvo BEZ 470 µF**. Dodaj ga samo ako se javi brownout reset, i
    dokumentuj oba slučaja (rizik C7).

---

## 6. Šta ovaj plan ne mijenja

- **Pin-mapa ostaje ista** — [`pins.h`](../../firmware/esp32s3_asd/main/pins.h):
  SCK/WS/SD = 4/5/6, I2C = 8/9, taster = 10, LED = 2 i 11. Firmware se ne dira.
- **Jedan mikrofon, ne dva** — zatvoreno mjerenjem 14.08.
  ([PREOSTALO.md](../../docs/PREOSTALO.md)) Drugi INMP441 ostaje rezerva.
- **470 µF ostaje vadiv**, ne fiksno zalemljen — mjerni kompromis iz
  [sema-povezivanja.md](sema-povezivanja.md), sekcija 2.
- Sve mjere opreza pri lemljenju INMP441 iz [lemljenje.md](lemljenje.md) važe
  nepromijenjeno: 300–350 °C, max 2–3 s po pinu, kapton preko sound porta,
  ne prati ploču poslije lemljenja.

---

## 7. Nabavka — Mikro Princ, provjereno 19.08.2026

Sve na jednom mjestu, [mikroprinc.com](https://www.mikroprinc.com/sr), Kralja
Milutina 31, Beograd. Sve četiri stavke su na stanju („Dostupan").

| # | Stavka | Ident | Kom | Cijena/kom | Ukupno | Ploča |
|---|---|---|---|---|---|---|
| 1 | [Test ploča 100x50 tačke](https://www.mikroprinc.com/sr/proizvod/test-ploca-100x50-tacke) — raster 2,54 mm | 057516 | 1 | 144,00 | **144,00** | U |
| 2 | [PIN letvica 40x1 prava F](https://www.mikroprinc.com/sr/proizvod/pin-letvica-40x1-prava-f) — ženska, 2,54 mm | 407 | 3 | 42,24 | **126,72** | U + M |
| 3 | [RM1/4 330, otpornik](https://www.mikroprinc.com/sr/proizvod/rm14-330-otpornik) — metal film 0,25 W ±1 %, sa nožicama | 32004 | 10 | 2,28 | **22,80** | U |
| 4 | [CKM 0.1uF/63V RM2.5](https://www.mikroprinc.com/sr/proizvodi/keramicki-multilejer-kondenzatori) — keramika 100 nF, raster 2,54 mm | — | 2 | 12,00 | **24,00** | mikrofon |
| | | | | **UKUPNO** | **≈ 318 din** | |

Ispod 4 000 din poštarina je 600 din — isplati se pokupiti lično ili dodati u
neku veću porudžbinu.

### Zašto baš to

**Ploča (1).** Mikro Princ ima samo četiri „tačke" ploče: 100×50, 100×75,
100×100, 100×160. Nema 7×9 ni 6×8 cm. 100×50 je najmanja i taman je — vidi 2.5.
Uzeti verziju **„tačke"** (svaka rupa zaseban pad), ne „linije" — raspored u
PDF-u je crtan za odvojene padove.

**Letvice (2).** Treba **76 ženskih kontakata**: 2×22 za S3, 6+2+4 za konektore
ploče U, 8+2+2+2+4 za ploču M. Pri rezanju letvice gine po jedan kontakt na svaki
rez (~10 komada). Tri letvice po 40 = 120 kontakata pokriva to sa rezervom.
Jedna letvica ne stiže ni za dva reda S3.

**Otpornici (3).** Minimalna količina je 10, a trebaju samo 2 (za LED). Ostalih 8
je rezerva. **Ne treba nijedan drugi otpornik u cijelom sklopu:** taster koristi
interni pull-up ESP32-S3, a I2C pull-up otpornici su već na INA226 modulu.
±1 % je preciznije nego što treba za LED, ali to je ono što imaju sa nožicama.

**Kondenzator (4).** Onaj sa posla je SMD — bez nožica ne može na perfboard.
Bira se **CKM 0.1uF/63V RM2.5** zbog dvije stvari koje piše u deklaraciji:
raster **2,54 mm** (poklapa se sa rasterom ploče, ostale CKM verzije su 5,08 mm)
i tolerancija **±10 %** (ostale su ±20 %, serija Y5V). Serija je navedena kao
C315/C320. INMP441 datasheet traži 0,1 µF, pa je 100 nF ujedno i ispravnija
vrijednost od 470 nF iz starije verzije dokumentacije. Uzeti 2 komada
(jedan je rezerva — mikrofon je krhak i lemi se dva puta).

> Ako hoćeš tačno 470 nF kako je stajalo ranije: **CKM 0.47uF/63V**, 11,52 din.
> Radi, ali je Y5V (±20 %, raster 5,08 mm) — slabija keramika i ne poklapa se sa
> rasterom ploče. Dielektrik nije izričito naveden ni za jedan od ta dva artikla,
> tako da je ±10 % jedini objavljen pokazatelj kvaliteta.

### Šta se NE kupuje

| Šta | Zašto |
|---|---|
| Ploča za mjerni dio | A1938 (4×6 cm) koju već imaš je dovoljna — sekcija 2.5 |
| Muške letvice | imaš 2 × 40 pinova (A1632), troši se ~44 na samu S3 ploču |
| Elektrolit 10 µF i 470 µF | iz seta od 120 komada (A642K) |
| INA226, AMS1117, INMP441, LED, taster | sve stiglo 04.08.2026 |
| Napajanje 5 V | mjeri se na poslu, laboratorijskim napajanjem — sekcija 2.6 |
| Bilo koji dodatni otpornik | nema ga u šemi — vidi gore |

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
- [ ] **VBS spojen na 3V3 POTROŠAČ.** Ako visi, `bus_mv` i `pwr_uw` su nula, a
      struja i dalje izgleda tačno — vidi 4.1.
- [ ] Lab. napajanje: **3,30 V** izmjereno multimetrom, strujna granica **300–500 mA**,
      nikad preko **3,6 V** (apsolutni maksimum ESP32-S3).
- [ ] **Prebroj rupe na kupljenoj ploči 100 × 50.** Raspored u PDF-u je crtan
      za mrežu 18 × 38; ako tvoj komad ima 19 × 39, pomjeri sve za jednu rupu —
      milimetri i međusobni odnosi ostaju isti.
