# Cjeline za lemljenje i mjerenje potrošnje

**Datum:** 01.09.2026. · Praktična, bench verzija plana iz
[plan-dvije-plocice.md](plan-dvije-plocice.md) i [e5-povezivanje-i-mjerenje.md](e5-povezivanje-i-mjerenje.md).

Sklop se dijeli na **dvije nezavisne cjeline** koje se spajaju sa 4 žice:

```
   ┌──── CJELINA 1: MJERNA (energetska) ────┐             ┌──── CJELINA 2: UREĐAJ ────┐
   │  ploča 4×6 cm, sve zalemljeno          │   4 žice    │  ESP32-S3 + INMP441       │
   │  AMS1117 → INA226 (šant 0,1 Ω) → 470µF │ ══════════  │  + 2 LED + otpornici      │
   └────────────────────────────────────────┘  3V3 GND    │  + taster                 │
        ↑                                      SDA SCL    └───────────────────────────┘
   5 V punjač  ILI  lab. 3,3 V direktno na IN+                 ↑ 4 žice (12/13/14+GND)
                                                              logički analizator
```

---

## CJELINA 1 — mjerna ploča (ovo kačiš za mjerenje)

Nosač: prototipna ploča **4×6 cm (A1938)**, koju već imaš.

### Šta se lemi

| # | Šta | Spojeva | Napomena |
|---|---|---|---|
| 1 | Ženski header 1×8 — za INA226 | 8 | INA226 već ima svoju mušku letvicu zalemljenu |
| 2 | Ženski header 2× 1×2 — za AMS1117 | 4 | AMS1117 ima 4 muška pina, ne lemi se |
| 3 | Ženski header 1×2 — za 470 µF | 2 | kondenzator ostaje **vadiv** |
| 4 | Ženski header 1×2 — **5 V ULAZ** | 2 | za varijantu sa punjačem |
| 5 | Ženski header 1×4 — **K-U** (ka uređaju) | 4 | 3V3 · GND · SDA · SCL |
| 6 | Gola kalajisana žica — **GND šina** | — | jedan red preko ploče, sve mase u nju |
| 7 | Izolovane žice za veze ispod | — | kratko, bez petlji |

Ukupno ≈ 20 spojeva + veze. AMS1117, INA226 i 470 µF se **ne leme** — ubadaju se.

### Kako se povezuje

```
  [punjač 5 V]
    +5V ──> 5V ULAZ pin1 ──> AMS1117 IN+
    GND ──> 5V ULAZ pin2 ──> AMS1117 IN− ──> GND ŠINA


                          ČVOR "3V3 IZVOR"              ČVOR "3V3 POTROŠAČ"
  AMS1117 OUT+ ────────────────┬──> INA226 IN+          INA226 IN− ──┬──> INA226 VBS
        (mora biti 3,3 V)      └──> INA226 VCC              ↑        ├──> 470 µF (+)  [vadiv]
                                                       šant 0,1 Ω    └──> K-U pin1  (3V3)
  AMS1117 OUT− ──> GND ŠINA
  INA226 GND   ──> GND ŠINA ──> K-U pin2  (GND)
  470 µF (−)   ──> GND ŠINA

  INA226 SDA ──────────────────> K-U pin3  (ide na GPIO 8)
  INA226 SCL ──────────────────> K-U pin4  (ide na GPIO 9)
  INA226 ALE ──────────────────> ne spaja se
```

Silk redoslijed INA226: `IN+ · IN− · VBS · ALE · SDA · SCL · GND · VCC`
(sa druge strane čitaš obrnuto — provjeri natpise prije lemljenja).

### Tri pravila koja se ne krše

1. **`3V3 IZVOR` i `3V3 POTROŠAČ` se nikad ne spajaju.** Ako se spoje, struja
   zaobiđe šant, INA226 mjeri nulu, a uređaj i dalje radi — greška se ne vidi.
   Prije prvog napajanja: ommetrom između ta dva čvora mora biti **≈ 0,1 Ω**
   (ne 0 Ω, ne prekid).
2. **`VBS` mora biti spojen** na `3V3 POTROŠAČ`. Ako visi, `bus_mv` i `pwr_uw`
   su smeće, a struja i dalje izgleda tačno.
3. **Zvjezdasta masa.** Sve mase (AMS1117 OUT−, INA226 GND, 470 µF −, K-U pin2)
   dolaze u **jednu tačku** na GND šini. Prošli put je upravo razvučena masa
   preko breadboarda dala grešku napona od 205 mV i ~2 Ω u napojnoj grani
   ([e5-mjerenje-01-rezultat.md](e5-mjerenje-01-rezultat.md)). Lemljenje ove
   ploče je ispravka tog nalaza — nema smisla ako masa opet bude razvučena.

---

## CJELINA 2 — uređaj (S3 + mikrofon + LED + taster)

Ovo je odvojena cjelina, radi sama na powerbanku i ne dira se pri mjerenju.

> **Odluka 02.09.2026:** uređaj se **ne lemi na ploču** — ostaje na protobordu
> MB-102, a LED, otpornici i taster idu na 3D štampani držač.
> Obrazloženje, računica otpornika i tabela veza:
> [uredjaj-na-protobordu.md](uredjaj-na-protobordu.md).

### Šta se lemi (headeri S3, mikrofona i INA226 su već zalemljeni)

| # | Šta | Spojeva |
|---|---|---|
| 1 | Otpornik 100 Ω (zelena) i 330 Ω (crvena), u seriji sa LED | 4 |
| 2 | Zelena LED (status) + crvena LED (alarm) | 4 |
| 3 | Žice na faston jezičke arkadnog tastera | 2 (nabijaju se, ne leme) |
| 4 | 470 nF + 10 µF **na padove mikrofona** (100 nF ako ga nabaviš) | 4 |
| 5 | *(opciono)* header K-LA 1×4 za logički analizator | 4 |

### Kako se povezuje

```
  INMP441                    ESP32-S3
  ───────                    ────────
  VDD  ──────────────────── 3V3          ┐ 470 nF (keramika) između VDD i GND
  GND  ──────────────────── GND          ┘ 10 µF (elektrolit, + na VDD) — oba
  SCK  ──────────────────── GPIO 4         zalemljena NA pločicu mikrofona
  WS   ──────────────────── GPIO 5
  SD   ──────────────────── GPIO 6
  L/R  ──────────────────── GND     ← obavezno, inače firmware čita tišinu


  GPIO 2  ──[ 100 Ω ]──▶|── GND       zelena LED (status)
  GPIO 11 ──[ 330 Ω ]──▶|── GND       crvena LED (alarm)
            ▲ duža nožica (anoda) ide ka otporniku

  GPIO 10 ────── taster ────── GND    interni pull-up, bez otpornika
```

**Zamka:** ako je taster pritisnut u trenutku uključenja, firmware ulazi u
EVAL mod. Ne držati ga pri bootu.

Žice mikrofona ostaju **< 10 cm**. LED i taster idu na žice po volji.

---

## Kako se spaja za mjerenje (E5)

### Korak 1 — eksterno napajanje

Dvije varijante, biraš jednu:

| | Varijanta L — lab. napajanje (posao) | Varijanta P — zidni punjač (kuća) |
|---|---|---|
| Izvor | lab. napajanje **3,30 V**, limit **300–500 mA** | punjač 5 V, presječen USB kabl |
| Gdje se kači | **direktno na INA226 IN+** i GND šinu | na **5 V ULAZ** ploče |
| AMS1117 | preskače se | koristi se |
| Preciznost | bolja (podesiv napon, strujna zaštita) | dovoljna |

```
  VARIJANTA L:   lab +3,30 V ──> INA226 IN+
                 lab   −     ──> GND ŠINA ploče 1

  VARIJANTA P:   punjač +5 V ──> 5V ULAZ ──> AMS1117 ──> INA226 IN+
                 punjač GND  ──> 5V ULAZ ──> GND ŠINA
```

**Nikad preko 3,6 V** na 3V3 pin — to je apsolutni maksimum ESP32-S3, jer se
zaobilazi onboard LDO ploče.

### Korak 2 — 4 žice između cjelina

| K-U (ploča 1) | ↔ | Uređaj (S3) |
|---|---|---|
| pin1 **3V3** (čvor POTROŠAČ) | — | pin **3V3** |
| pin2 **GND** | — | pin **GND** |
| pin3 **SDA** | — | **GPIO 8** |
| pin4 **SCL** | — | **GPIO 9** |

Žice ≤ 20 cm; za 3V3 i GND uzeti deblje/kraće nego za SDA/SCL.

### Korak 3 — USB mora biti iskopčan

**ILI powerbank/USB ILI mjerna ploča. Nikad oboje.** USB napaja S3 mimo šanta
i mjerenje pokazuje besmislicu, a dva izvora guraju jedan protiv drugog.

Za logove dok je USB vani: USB-TTL adapter na **GPIO 43 (TX) → RX adaptera**,
**GND → GND**, a **VCC adaptera se NE spaja** (zaobišao bi šant).

### Korak 4 — logički analizator

**Logički analizator ne mjeri struju.** On daje **vremensku osu**: koliko tačno
traje koja faza. Struju i napon daje INA226. Energija po fazi je onda:

```
  E_faza = U × I_faza × t_faza
           └──INA226──┘   └─LA─┘
```

Bez toga se ne može razdvojiti idle / snimanje / DSP / inferenca, što je
tačno ono što traži eksperiment D u [e5-mjerenje-01-rezultat.md](e5-mjerenje-01-rezultat.md).

```
  LOGIČKI ANALIZATOR            ESP32-S3
  ──────────────────            ────────
  CH0 ───────────────────────── GPIO 12    marker: I2S snimanje
  CH1 ───────────────────────── GPIO 13    marker: DSP / feature
  CH2 ───────────────────────── GPIO 14    marker: inferenca
  GND ───────────────────────── GND        ← samo GND, ništa drugo

  sve tri niske = idle
```

GPIO 12/13/14 su slobodni i susjedni na lijevoj letvici DevKitC-1. GND se
spaja **prvi**, prije signala.

**Bez izmjene firmvera** (fallback, daje manje): kači se
CH0 → GPIO 5 (I2S WS — pulsira dok se snima), CH1 → GPIO 2, CH2 → GPIO 11
(LED obrasci), i po potrebi CH3/CH4 → GPIO 8/9 (I2C, dekodira se saobraćaj ka
INA226). Granice DSP-a i inference se tako ne vide — za njih trebaju markeri.

### Korak 5 — redoslijed

1. Izlaz napajanja **OFF**, USB iskopčan.
2. Spoji 4 žice ploča 1 ↔ uređaj, pa GND i sonde analizatora, pa UART adapter.
3. Multimetrom provjeri: `IZVOR ↔ POTROŠAČ ≈ 0,1 Ω`, `3V3 ↔ GND` nije kratak
   spoj, mase obje cjeline su isti čvor.
4. Uključi izlaz, sačekaj 10 s. Ako izvor uđe u CC ili se S3 resetuje —
   odmah OFF i traži grešku.
5. Mjeri **prvo bez 470 µF**. Dodaj ga samo ako se javi brownout i dokumentuj
   oba slučaja.
6. Poslije mjerenja: izvor OFF → skini žice → tek onda USB.

---

## Šta fali za ovo

| Šta | Kom | Gdje |
|---|---|---|
| Ženska pin letvica 40×1 (ident 407) — samo za mjernu ploču | 2 | Mikro Princ, 42 din/kom |
| Otpornik **330 Ω** 1/4 W (ident 32004) — crvena LED | 10 (min. pakovanje) | Mikro Princ, 2,28 din/kom |
| Otpornik **100 Ω** 1/4 W — zelena LED | 10 (min. pakovanje) | Mikro Princ, ≈ 2,3 din/kom |

≈ 130 din. **Kondenzatori se ne kupuju** — 470 nF keramika, 10 µF i 470 µF
elektroliti su već na stolu. Zašto dvije različite vrijednosti otpornika i zašto
uređaj ostaje na protobordu: [uredjaj-na-protobordu.md](uredjaj-na-protobordu.md).

**Firmware:** markeri faza na GPIO 12/13/14 još nisu implementirani — to je
`gpio_set_level` na ulazu i izlazu iz tri postojeće faze u `psd_live.c`.
