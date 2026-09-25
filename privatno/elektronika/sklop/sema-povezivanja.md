# Šema povezivanja — INMP441 + INA226 na ESP32-S3 (N32R16V)

> **Mjerodavno je samo poglavlje 1 (mikrofon), 3, 4 i 5.** Za INA226 i mjerenje
> potrošnje (poglavlje 2) važi [plan-dvije-plocice.md](plan-dvije-plocice.md),
> sekcija 4.1: **`VCC` ide PRIJE šanta** (čvor `3V3 IZVOR`, zajedno sa `IN+`), a
> **`VBS` na `IN−`** (čvor `3V3 POTROŠAČ`). Raniji raspored iz ovog fajla —
> `VCC` iza šanta i `VBS` nepovezan — daje `bus_mv` i `pwr_uw` jednake nuli i
> ne smije se koristiti. Isto upozorenje nosi i zapis stvarnog ožičenja na
> grani `measurement/e5-ina226`.
>
> Vizuelna šema [sema-povezivanja.svg](../seme/sema-povezivanja.svg) još crta stari
> raspored `VCC` i nema `VBS`; nije preslikana, koristi crteže iz
> [sema-sklopa.pdf](../seme/sema-sklopa.pdf).

Šema zalemljenog sklopa (dvije ploče, 7 strana A4): [sema-sklopa.pdf](../seme/sema-sklopa.pdf) ·
podjela i spisak komponenti: [plan-dvije-plocice.md](plan-dvije-plocice.md)
Sve ide na protoboard MB-102, žice do mikrofona **< 10 cm**.

## 1. INMP441 mikrofon (I2S) — ovo je stalna veza, treba ti odmah

INMP441 breakout ima 6 pinova. Povezuješ ovako:

| INMP441 pin | Ide na | Napomena |
|---|---|---|
| **VDD** | 3V3 | + **470 nF keramika i 10 µF** između VDD i GND, ŠTO BLIŽE mikrofonu — zalemljeni na padove mikrofona ([uredjaj-na-protobordu.md](uredjaj-na-protobordu.md)) |
| **GND** | GND | |
| **SCK** (nekad piše BCLK) | **GPIO 4** | I2S bit clock |
| **WS** (nekad LRCL) | **GPIO 5** | I2S word select |
| **SD** (nekad DOUT) | **GPIO 6** | I2S data → u S3 |
| **L/R** | **GND** | = lijevi kanal. Firmware čita lijevi slot — ako ovo visi u vazduhu, dobijaš tišinu (rizik C1) |

```
INMP441                            ESP32-S3
┌──────────┐                      ┌──────────────┐
│ VDD ●────┼──────┬──── 3V3 ──────┤ 3V3          │
│          │  470nF + 10µF        │              │
│ GND ●────┼──────┴──── GND ──────┤ GND          │
│ SCK ●────┼─────────────────────►│ GPIO 4       │
│ WS  ●────┼─────────────────────►│ GPIO 5       │
│ SD  ●────┼─────────────────────►│ GPIO 6       │
│ L/R ●────┼──── na GND!          │              │
└──────────┘                      └──────────────┘
```

Test poslije lemljenja: snimi 5 s WAV na flash, otvori u Audacity (prije ikakvog ML-a).

## 2. INA226 senzor struje — SAMO za E5 mjerenja energije, ne treba za razvoj

INA226 mjeri struju kroz svoj **shunt** (IN+ → IN−), tj. mora biti **u seriji sa
napajanjem** ploče. Dvije veze: mjerna (shunt) + I2C (očitavanje).

| INA226 pin | Ide na | Napomena |
|---|---|---|
| **IN+** | + izvora 3,3 V | čvor `3V3 IZVOR`; izvor: lab. napajanje ili AMS1117 iz punjača 5 V |
| **VCC** | **isti čvor kao IN+** | napajanje logike senzora — **prije šanta**, da ne ulazi u mjerenu struju tereta |
| **IN−** | **3V3 pin ploče S3** | čvor `3V3 POTROŠAČ`; + **≥470 µF elektrolit** između IN− i GND (rizik C7 — brownout) |
| **VBS** | **isti čvor kao IN−** | ulaz za napon magistrale. Ako visi, `bus_mv` i `pwr_uw` su nula i cijelo E5 mjerenje je neupotrebljivo |
| **ALE** | nepovezan | alarmni izlaz, ne koristi se |
| **GND** | GND (zajednička masa sa izvorom i S3!) | zvjezdasta masa, ne preko šina protoborda |
| **SDA** | **GPIO 8** | I2C (moduli imaju pull-up otpornike na sebi) |
| **SCL** | **GPIO 9** | I2C, ovaj modul je potvrđen na adresi `0x44` |

Silk redoslijed pinova na modulu: `IN+ · IN− · VBS · ALE · SDA · SCL · GND · VCC`.

```
  3,3 V izvor                INA226                     ESP32-S3
┌────────────┐          ┌──────────────┐            ┌──────────────┐
│         + ●┼─────┬───►│ IN+     IN− ●┼─────┬─────►│ 3V3 (napaja  │
│            │     │    │   (shunt)    │     │      │  cijelu ploču)│
│            │     └───►│ VCC     VBS ●┼─────┤      │              │
│         − ●┼────┬─────┤ GND          │  ≥470µF    │              │
└────────────┘    │     │ SDA ●────────┼───────────►│ GPIO 8       │
                  │     │ SCL ●────────┼───────────►│ GPIO 9       │
                  │     │ ALE ● nepov. │            │              │
                  └─────┴──────────────┴────────────┤ GND          │
                   GND (zvjezdasta masa za sve!)    └──────────────┘

  IN+ i VCC = čvor 3V3 IZVOR       IN− i VBS = čvor 3V3 POTROŠAČ
```

**Pravila za E5 mjerenje (iz plana, sekcija 6.2/D2):**
1. **USB OTKAČEN** sa S3 tokom mjerenja — USB-UART most i njegov LED zagađuju
   potrošnju. Logove čitaš poslije (iz flasha) ili preko posebnog UART adaptera.
2. Napajanje ide na **3V3 pin direktno** (zaobilazi onboard LDO — to i hoćeš,
   mjeriš samo modul). **Nikad USB i externo 3V3 istovremeno.**
3. Wi-Fi/BT isključeni, CPU fiksno 240 MHz (već u sdkconfig).
4. Za razvoj (van mjerenja): normalno preko USB-a, INA226 ti tada ne treba —
   možeš je ostaviti povezanu samo na I2C, a 3V3 pin vratiti na USB napajanje.
5. **470 µF je mjerni kompromis**: ublažava strujni špic koji baš pokušavaš izmjeriti
   (INA226 ga vidi kao odgođeno punjenje → energija se pripiše pogrešnoj fazi).
   Zato: mjeri **prvo BEZ 470 µF**; dodaj ga samo ako se javi brownout reset; dokumentuj
   oba slučaja ("bez" i "sa 470 µF"). 470 µF je za stabilnost (C7), ne stalni dio mjerenja.

## 3. Opciono: LED + taster (demo na odbrani)

Uređaj ima **dvije** LED — `PIN_LED` i `PIN_LED_ALARM` u `pins.h`. Otpornik
prati LED, ne pin (izbor i računica: [uredjaj-na-protobordu.md](uredjaj-na-protobordu.md)):

| Šta | Ide na | Napomena |
|---|---|---|
| **Zelena** LED — status (+ **100 Ω** anoda→otpornik, katoda→GND) | **GPIO 2** | pet obrazaca: IDLE kratko bljeska, učenje brzo treperi, nadzor stalno, `OBSERVATION_HOLD` sporo pulsira, fault dvostruki puls |
| **Crvena** LED — alarm (+ **330 Ω**) | **GPIO 11** | svijetli dok traje odstupanje; treperi u fail-closed stanju |
| Taster | **GPIO 10** ↔ GND | interni pull-up. **Ne smije biti pritisnut pri uključenju** — firmware to čita kao ulazak u EVAL mod |

## 4. Šta NIKAKO

- **GPIO 35, 36, 37 ne koristiti ni za šta** — zauzeti oktalnim PSRAM-om (N32R16V).
- Strapping pinove 0, 3, 45, 46 izbjegavati.
- Ne dirati eFuse / VDD_SPI (1.8 V "V" varijanta) — pogrešan SPIRAM mod u
  sdkconfig-u daje samo boot-loop (vrati config), ali eFuse je TRAJNO.

## 5. Isti spoj na ESP32 DevKit V1 (E4 kontrola)

Identična logika, samo drugi pinovi: SCK→26, WS→25, SD→33, SDA→21, SCL→22
(GPIO 6–11 su tamo flash — zabranjeni). Vidi pins.h — bira se automatski pri buildu.
