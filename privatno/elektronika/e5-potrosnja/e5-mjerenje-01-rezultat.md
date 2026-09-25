# E5 — prvo mjerenje potrošnje, rezultat

**Datum:** 11.08.2026
**Firmware:** `on-device-verified-37-gc5a8678`, ESP-IDF v5.5.5, build `ASD_INA_TEST=1`
**Sirovi log:** [`results/e5_mjerenje_01_uart.log`](../../../results/e5_mjerenje_01_uart.log)
**Postavka:** [`e5-povezivanje-i-mjerenje.md`](e5-povezivanje-i-mjerenje.md)

---

## Ishod u jednoj rečenici

Strujni mjerni lanac radi i nezavisno je potvrđen; naponski kanal INA226 odstupa
za oko 200 mV i nije upotrebljiv dok se ne otkloni uzrok.

| Dio sistema | Status |
|---|---|
| I2C komunikacija sa INA226 | ✔ senzor odgovara, identitet potvrđen |
| Konfiguracija i kalibracija | ✔ ostaje upisana, čita se nazad ispravno |
| Mjerenje struje (šant) | ✔ potvrđeno nezavisnim instrumentom |
| Stabilnost očitanja | ✔ 12 µV raspona na 10 uzoraka |
| Rad na eksternom napajanju bez USB-a | ✔ |
| Jednokratni NVS izvještaj (armiranje → mjerenje → čitanje) | ✔ puni ciklus dokazan |
| **Mjerenje napona magistrale (VBUS)** | ✘ **čita 3,425 V umjesto ~3,22 V** |
| **Otpor napojne grane** | ✘ **~2 Ω, gubi 66 mV na kontaktima** |

---

## Kakvo je mjerenje rađeno

Cilj je bio dokazati da strujni put kroz šant radi prije nego se piše puni E5
firmware, a ne izmjeriti konačne brojeve potrošnje.

Ograničenje koje je oblikovalo cijelu proceduru: **USB ploče mora biti iskopčan**,
jer bi napajao ESP32 mimo šanta i zaobišao mjerenje. Zato firmware ne može
jednostavno ispisivati rezultat na konzolu i čekati da ga neko pročita.

### Riješeno na dva načina istovremeno

**1. Jednokratni armirani režim u firmveru** ([`ina226_test.c`](../../../firmware/esp32s3_asd/main/ina226_test.c))

Test prolazi kroz tri stanja koja se čuvaju u NVS-u:

| Stanje | Kada | Šta radi |
|---|---|---|
| `ARMED` | prvi boot poslije flešovanja | samo se armira, ne mjeri |
| `RUNNING` → `READY` | prvo potpuno uključenje (`ESP_RST_POWERON`) | mjeri i čuva rezultat |
| `READY` | svaki naredni boot | ispisuje sačuvano, **ne prepisuje ga** |

Uzorci se drže u RAM-u tokom mjerenja, a u flash se upisuju tek poslije
posljednjeg — da upis u flash ne uđe u mjerenu potrošnju.

**2. Odvojen USB-UART odvod za praćenje uživo**

CH340 adapter na `COM7`, spojen samo `adapter RX ← ESP32 TX (GPIO43)` i
zajednički GND. `VCC` adaptera namjerno nespojen, da ne zaobiđe šant.

Konzola ide na UART0 (`CONFIG_ESP_CONSOLE_UART_DEFAULT=y`, `UART_NUM=0`,
115200 8N1), pa se cijeli tok vidi u realnom vremenu bez USB-a ploče. Hvatanje
je pasivno — `DTR`/`RTS` se drže spušteni da ništa ne resetuje ploču.

### Oprema i podešavanja

- laboratorijsko napajanje: `3,30 V`, strujni limit `0,30 A`
- INA226 sa šantom `R100 = 0,1 Ω`, `CAL = 1024`, `Current_LSB = 50 µA`
- konfiguracija senzora `0x4527`: AVG=16, VBUSCT=1,1 ms, VSHCT=1,1 ms,
  kontinuirani režim — oko 35 ms po konverziji
- 10 uzoraka na 300 ms

---

## Rezultati

### I2C lanac

| Provjera | Očekivano | Dobijeno |
|---|---|---|
| Mapa pinova | pull-up samo na I2C linijama | GPIO8, GPIO9 (i GPIO0 — strapping ploče) |
| Stanje SDA/SCL | spoljni pull-up na obje | `obaranje=0`, `pusteno@5us=1` na obje |
| Bit-bang self-check | master može oboriti i pustiti obje | `SDA low=1 high=1 \| SCL low=1 high=1` |
| Bit-bang scan | 1 uređaj | ACK sa **0x44** |
| Hardverski scan | ista adresa | 0x44 |
| Identitet | `manuf=0x5449`, `die=0x2260` | poklapa se — pravi TI INA226 |
| Config pročitan nazad | `0x4527` | `0x4527` |
| Kalibracija | `1024` | `1024` |

**Adresa je `0x44`, ne `0x40`.** Modul ima `A0`/`A1` strapovane tako da daju
`0x44`. Dinamičko traženje adrese (commit `c5a8678`) je zato bilo neophodno.

### Očitanja

| # | Šant [µV] | Bus [mV] | Struja [µA] | Snaga [µW] |
|---|---|---|---|---|
| 1 | 3482 | 3423 | 34850 | 118750 |
| 2 | 3470 | 3425 | 34700 | 118750 |
| 3 | 3472 | 3425 | 34750 | 118750 |
| 4 | 3470 | 3425 | 34700 | 118750 |
| 5 | 3470 | 3425 | 34700 | 118750 |
| 6 | 3470 | 3425 | 34700 | 118750 |
| 7 | 3470 | 3425 | 34700 | 118750 |
| 8 | 3470 | 3425 | 34700 | 118750 |
| 9 | 3472 | 3425 | 34750 | 118750 |
| 10 | 3472 | 3425 | 34750 | 118750 |

Srednje: šant **3471,8 µV**, struja **34,73 mA**. Raspon šanta 3470–3482 µV,
širina **12 µV** — oko 5 LSB na rezoluciji od 2,5 µV.

Stanje uređaja tokom mjerenja: ESP32-S3 na 240 MHz, PSRAM aktivan, WiFi i BT
isključeni, bez audia i modela — samo I2C test. To je najniže aktivno stanje
koje će E5 mjeriti.

### Puni ciklus bez USB-a — dokazan

Log bilježi tri događaja koji zajedno potvrđuju cijeli mehanizam:

| Vrijeme u logu | Događaj |
|---|---|
| `t = 205,9 s` | `rst:0x1 (POWERON)` — uključen izvor, test se izvršava i čuva rezultat |
| `t = 394,4 s` | `E BOD: Brownout detector was triggered` — isključen izvor |
| `t = 749,7 s` | `rst:0x1 (POWERON)` — ponovo uključen; ispisuje **sačuvani** izvještaj |

Nakon ponovnog uključenja firmware ispisuje `status=USPJESNO adresa=0x44
config=0x4527 cal=1024` i svih deset uzoraka **identičnih** onima izmjerenim
uživo, pa poruku `Rezultat se nece prepisati novim mjerenjem.`

Time je potvrđeno da E5 može mjeriti potpuno odvojeno od računara i da se
rezultat pouzdano vraća poslije prekida napajanja.

> Poruke `E BOD: Brownout detector was triggered` u logu nisu kvar — to je
> normalna reakcija na gašenje izvora, dok napon pada.

---

## Unakrsna provjera sa nezavisnim instrumentima

| Veličina | Displej izvora | Multimetar | INA226 |
|---|---|---|---|
| Struja | 0,034 A | — | 34,73 mA |
| Napon | 3,29 V (na stezaljkama) | ~3,22 V (na `3V3_LOAD`) | 3,425 V |

### Nalaz 1 — strujni kanal je ispravan

Izvor i INA226 se slažu unutar rezolucije displeja izvora. Uz to su
međusobno konzistentne i sve četiri veličine senzora:

```
3470 µV / 0,1 Ω          = 34,70 mA   (poklapa se sa strujnim registrom)
3,425 V × 34,70 mA       = 118,85 mW  (unutar jednog LSB prijavljene snage)
```

Ta konzistentnost potvrđuje da su `CAL`, `Current_LSB` i vrijednost šanta tačni.

### Nalaz 2 — naponski kanal odstupa za ~200 mV

INA226 je **iza** šanta, pa fizički ne može čitati veći napon od izvora.
Odstupanje je `3,425 − 3,22 = 205 mV`, odnosno **+6,4 %**.

Senzor tu ne bi smio toliko griješiti: katalog daje grešku pojačanja ±0,1 % i
ofset najviše ±2,5 mV, dakle oko ±5 mV na 3,3 V. Izmjereno odstupanje je
četrdesetak puta veće.

**Radna hipoteza:** INA226 mjeri `VBUS` u odnosu na **svoj** `GND` pin. Ako
INA-in i ESP-ov GND ne diraju masenu šinu na istom mjestu, a između tih tačaka
postoji otpor, povratna struja ESP-a podiže ESP-ovu masu iznad INA-ine i senzor
vidi prividno veći napon. Smjer greške se poklapa, a red veličine traži
`205 mV / 34,73 mA ≈ 6 Ω` između dvije tačke koje bi trebale biti isti čvor.

Hipotezu dodatno podupire presedan: [`ina226-provjera.md`](ina226-provjera.md)
bilježi da je 10.08.2026. već jednom nađen **pogrešno spojen GND na strani
ESP32-S3**, zbog čega SDA i SCL nisu mogli da se obore. Masa je u ovoj postavci
dokazano slaba tačka.

Hipoteza još **nije potvrđena mjerenjem** — vidi eksperiment A niže.

### Nalaz 3 — ~2 Ω serijskog otpora u napojnoj grani

Izvor daje 3,29 V, do potrošača stiže 3,22 V. Šant objašnjava samo 3,5 mV od
tih 70 mV; ostatak pada na kontaktima i žicama:

```
66 mV / 34,73 mA ≈ 1,9 Ω
```

Ovo je ozbiljnije nego što izgleda jer **skalira sa strujom**. Na 60–80 mA
(snimanje i inferenca) pad bi bio 120–160 mV, pa bi svako E5 stanje bilo
izmjereno na drugom naponu — što bi samo po sebi pokvarilo poređenje stanja.

Uzrok je gotovo sigurno breadboard razvod, što je
[postavka već predviđala kao rizik](e5-povezivanje-i-mjerenje.md).

---

## Šta je dokazano, a šta nije

**Dokazano:**

- I2C drajver, adresiranje, identitet i trajnost konfiguracije
- Kalibracija šanta i tačnost strujnog mjerenja, potvrđena drugim instrumentom
- Šum mjerenja od 12 µV — dovoljno precizno za razlikovanje E5 stanja
- Mjerenje bez računara, sa pouzdanim vraćanjem rezultata poslije gašenja
- Praćenje uživo preko odvojenog UART-a, bez zaobilaženja šanta

**Nije dokazano:**

- Tačnost naponskog kanala INA226
- Da je napon na potrošaču stabilan pri promjeni opterećenja
- Bilo koji broj potrošnje po fazama rada (idle / snimanje / DSP / inferenca)

**Najbolja trenutna procjena potrošnje u mirovanju**, računata iz pouzdane
struje i multimetrom potvrđenog napona:

```
P = 3,22 V × 34,73 mA ≈ 112 mW
```

Broj je privremen dok se ne otkloni otpor napojne grane i napon ne podigne na
tačnih 3,30 V na potrošaču.

### Sistematski pomak koji treba imati na umu

`INA226 VCC` je spojen na `IN−`, dakle senzor se napaja **iza** šanta i mjeri
i vlastitu potrošnju (katalog: tipično 330 µA, najviše 420 µA). Isto važi za
struju kroz pull-up otpornike I2C linija.

Za E5 to je oko 1 % i **jednako je u svim mjerenim stanjima**, pa se pri
poređenju stanja skoro potpuno poništi. Prebacivanje `VCC` na `IN+` postaje
neophodno tek ako se bude mjerio deep sleep, gdje ESP troši ~10 µA i 330 µA
senzora bi potpuno progutalo signal.

---

## Sljedeći eksperimenti

### A. Lokalizacija greške naponskog kanala

Multimetar, bez lemljenja, sonde **direktno na nožice modula** — u tome je
poenta, jer breadboard šina je upravo ono što je pod sumnjom.

| # | Mjeri između | Očekivano | Tumačenje ako odstupa |
|---|---|---|---|
| A1 | `INA226 GND` ↔ `ESP32 GND` | 0–2 mV | preko ~20 mV potvrđuje hipotezu o masi |
| A2 | `INA226 VBS` ↔ `INA226 GND` | ono što čip mjeri | 3,42 → masa kriva; 3,22 → čip griješi |
| A3 | izvor `+` ↔ `INA226 IN+` | 0–5 mV | više = loš kontakt u plus grani |

A1 je najvrednije: dvije tačke koje bi po šemi trebale biti isti čvor.

### B. Čvrst razvod pa ponoviti prolaz

Kratke zalemljene žice umjesto breadboard razvoda, sve mase u jednu tačku
(zvjezdasta masa), pa novi armirani prolaz.

Kriterij uspjeha:

- pad izvor → potrošač ispod 5 mV
- `VBUS` se poklapa sa multimetrom unutar ±10 mV
- napon na potrošaču podešen na tačnih 3,30 V

### C. Linearnost naponskog kanala — samo ako B ne riješi

Izmjeriti `VBUS` naspram multimetra na tri napona: 3,0 / 3,3 / 3,6 V.

- **konstantno odstupanje** → problem ofseta ili reference
- **odstupanje proporcionalno naponu** → greška pojačanja, moguć klon čipa
  umjesto originalnog TI dijela

### D. Puni E5 — energija po fazama

Ono zbog čega je sve ostalo rađeno. Traži izmjene firmvera:

- ubrzati uzorkovanje: `AVG=1` uz `VBUSCT/VSHCT = 1,1 ms` daje ~2,2 ms po
  uzorku (~450 Hz) umjesto sadašnjih 35 ms; šum raste oko 4× (na ~50 µV,
  odnosno 0,5 mA) što je i dalje sitno naspram 35 mA
- markeri granica faza: idle, I2S snimanje, DSP/featuring, inferenca
- integracija `∫P dt` po fazi u RAM-u, upis u flash tek na kraju

**Zamka koju treba izmjeriti, ne pretpostaviti:** I2C anketiranje na 450 Hz i
samo troši struju i CPU, dakle mjerenje mijenja ono što mjeri. Kvantifikovati
tako što se idle izmjeri sa anketiranjem i bez njega.

### E. Poređenje PSD i neuronskog modela po energiji

Završna tačka za rad. PSD model je već pobijedio po tačnosti
(target AUC 0,864 naspram 0,669 — [`istrazivanje-psd-model.md`](../../../docs/model/istrazivanja/istrazivanje-psd-model.md)).
Ako pobijedi i po energiji po inferenci, to je jak zaključak koji spaja E4, E5 i
izbor finalnog modela.

Mjeriti `J/inferenca` za oba toka pod istim uslovima.

### F. Doprinos samog INA226 — opciono

Potrebno samo ako se bude tražio apsolutni broj sa greškom ispod 1 %, ili ako
se pređe na mjerenje deep sleepa. ESP32 se napoji sa USB-a, `3V3_LOAD` se
odvoji od ESP-a, a INA226 ostane na laboratorijskom izvoru kroz šant uz
zajedničku masu. Senzor tada mjeri isključivo sebe i svoje pull-upove, pa se
dobijena vrijednost oduzima od svih ostalih mjerenja.
