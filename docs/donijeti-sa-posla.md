# Šta donijeti s posla

> Stanje 14.08.2026. Spisak je kratak namjerno — **kondenzatori se ne kupuju i
> ne donose, svi su već na stolu** (set od 120 elektrolita 1 µF–470 µF i 3×
> keramika 470 nF, stiglo 04.08. — [hardver-lista.md](hardver-lista.md)).
> I2C pull-upovi se takođe ne donose: INA226 modul ih ima na sebi, izmjereno je
> `obaranje=0`, `pušteno@5us=1` na obje linije.

---

## Spisak

| # | Šta | Kom | Zašto | Šta odblokira | Prioritet |
|---|---|---|---|---|---|
| 1 | **5 V izvor sa golim žicama** — USB-A breakout, 5 V adapter sa terminalima, ili žrtveni USB kabl koji se smije rezati | 1 | Ulaz za AMS1117 koji već imaš | **E5 mjerenja kod kuće, bez laboratorijskog napajanja** | **visok** |
| 2 | **Multimetar** (ili 15 min pristupa njemu) | 1 | Sonde direktno na nožice INA226 modula | Eksperiment A — lokalizacija greške naponskog kanala | **visok** |
| 3 | Otpornik **220–330 Ω**, 1/4 W | 4 | 2 potrebna + 2 rezerve | LED demo — **zelena GPIO2 (status), crvena GPIO11 (alarm)**; firmware je gotov i testiran, ovo je jedino što fali | **visok** |
| 4 | *(opciono)* Laboratorijsko napajanje, ako se smije iznijeti | 1 | Podesiv napon + **strujni limit** | Bolje od AMS1117: limit štiti od kratkog spoja, napon se može podesiti na tačnih 3,30 V | srednji |
| 5 | *(opciono)* Ženski header 2.54 mm | ~1 | Da INMP441 ostane vadiv | Faza 2 (ploča 4×6) — bez toga se moduli leme fiksno | nizak |

**Zašto je stavka 1 najvažnija:** AMS1117 3.3 V modul (800 mA, 4 muška pina već
zalemljena) je već tu, ali nema šta da ga napoji. Sa golim 5 V žicama iz punjača
E5 se može mjeriti kod kuće — bez toga svako dalje mjerenje potrošnje čeka da
pločica ode na posao.

**Zašto stavka 2 nije zamjenjiva softverom:** otvoreni nalaz je da INA226 čita
3,425 V umjesto ~3,22 V, a hipoteza je razlika potencijala između INA-ine i
ESP-ove mase. To je mjerenje na fizičkim nožicama modula i ne može se ustanoviti
iz firmvera. Detalji i tabela A1–A3:
[e5-mjerenje-01-rezultat.md](e5-mjerenje-01-rezultat.md#a-lokalizacija-greške-naponskog-kanala).

### Promjena 14.08.2026 — otpornici su podigli prioritet

Firmware za taster i lampice je napisan, testiran (43 host testa) i flešovan.
Zelena LED nosi cijeli tok demoa kroz pet obrazaca (čekam / učim / **naučio** /
alarm / kvar), a crvena razrješava „ugašena zelena" naspram „uređaj mrtav".
Bez otpornika LED se **ne smije** vezati na GPIO, pa su oni sada na kritičnom
putu za demo, ne više „srednji prioritet".

**Drugi mikrofon se NE lemi.** Faza 5 je izmjerila da su sve dual-channel
varijante slabije od jednog kanala; modul #2 ostaje rezerva. Detalji:
[DNEVNIK-NEXT-LEVEL.md](DNEVNIK-NEXT-LEVEL.md), blok G.

## Šta NE treba donositi

- **Kondenzatori** — svi su tu. 10 µF i 470 µF iz seta elektrolita, 470 nF
  keramika za mikrofon.
- **Pull-up otpornici za I2C** — na INA226 modulu su, potvrđeno mjerenjem.
- **Ništa za mikrofon.** INMP441 radi bez ijedne dodatne komponente; kondenzatori
  uz njega su poboljšanje, ne uslov. Živi lanac je radio bez njih 06.08.
  (rms 158,7 / peak 1020 / clipped 0 / dropped 0).

---

## Kako povezati INA226 sada, bez spoljnog napajanja

Dva slučaja. Za **dugu probu lažnih alarma senzor uopšte ne treba** — taj test
koristi samo mikrofon i USB.

### A) Samo I2C — senzor je živ, ali ne mjeri ništa korisno

Ovo je stanje u kojem je senzor bio potvrđen 10.08. Radi bez spoljnog napajanja.

```text
INA226 VCC ────────────── ESP32-S3 3V3
INA226 GND ────────────── ESP32-S3 GND
INA226 SDA ────────────── ESP32-S3 GPIO8
INA226 SCL ────────────── ESP32-S3 GPIO9
INA226 IN+ ────────────── NEPOVEZANO
INA226 IN− ────────────── NEPOVEZANO
INA226 VBS ────────────── NEPOVEZANO
INA226 ALE ────────────── NEPOVEZANO
```

Senzor odgovara na `0x44`, vraća `manuf=0x5449`/`die=0x2260`, prima config i
kalibraciju. Šant tada čita šum od −10 do −7 µV, jer kroz njega ne teče struja.

**Za ovo nema šta da se mjeri od potrošnje** — ploča se napaja s USB-a, mimo
šanta. Ako ti je muka da diraš žice, ostavi ovako; ništa ne kvari.

> ⚠️ `IN+` i `IN−` ne ostavljati spojene na žice koje vise u vazduh, posebno ne
> pored mikrofona — vise kao antena. Ili ih spoji po šemi, ili skini.

### B) Puni E5 bez laboratorijskog napajanja — traži stavku 1 sa spiska

Ovo je razlog zbog kojeg je AMS1117 i kupljen (rizik D2 iz plana).

```text
5 V punjač +  ──────────── AMS1117 IN
5 V punjač −  ──────────── AMS1117 GND ──┐
                                          │
AMS1117 OUT (3,3 V) ────── INA226 IN+     │
                                          │
INA226 IN− ──┬─────────── ESP32-S3 3V3    │
             ├─────────── INA226 VBS      │  ZVJEZDASTA MASA
             └─────────── INA226 VCC      │  (sve u JEDNU tačku)
                                          │
INA226 GND ───────────────────────────────┤
ESP32-S3 GND ─────────────────────────────┘

470 µF elektrolit:  + na čvor IN−/3V3   ·  − na zajednički GND
INA226 SDA → GPIO8  ·  SCL → GPIO9  ·  ALE nepovezan
```

**Tri stvari koje se ne smiju preskočiti:**

1. **USB pločice mora biti iskopčan.** Inače napaja ESP32 mimo šanta i mjerenje
   nema smisla. Zato test i čuva rezultat u NVS — vidi
   [e5-povezivanje-i-mjerenje.md](e5-povezivanje-i-mjerenje.md).
2. **Zvjezdasta masa, kratke zalemljene žice, ne breadboard razvod.** Ovo je
   direktno rješenje otvorenog nalaza: sadašnja postavka ima ~2 Ω u napojnoj
   grani (66 mV pada na kontaktima) i vjerovatno razliku potencijala između
   masa. Kriterij uspjeha: pad izvor → potrošač **ispod 5 mV**, `VBUS` se
   poklapa sa multimetrom unutar **±10 mV**.
3. **Prije bilo kakvog mjerenja treba re-arm u firmveru** — vidi ispod.

**Za praćenje uživo:** CH340 USB-UART adapter (bio na COM7), samo
`adapter RX ← ESP32 TX (GPIO43)` + zajednički GND. **`VCC` adaptera ostaje
nespojen**, inače zaobiđe šant.

**Razlika naspram laboratorijskog napajanja:** AMS1117 daje fiksnih ~3,3 V i
**nema strujni limit**. Za poređenje potrošnje po fazama rada je dovoljan, jer
INA226 mjeri i stvarni napon. Za prvi prolaz posle prelemljivanja je ipak
sigurnije laboratorijsko napajanje sa limitom 0,30 A (stavka 4).

---

## Softverski blokator koji ide prije svega ovoga

`ASD_INA_TEST` je trenutno u stanju `READY` i **odbija da ponovi mjerenje**.
Guard je `esp_reset_reason() != ESP_RST_POWERON`
([ina226_test.c:147](../firmware/esp32s3_asd/main/ina226_test.c:147)), a reset
preko EN pina se prijavljuje kao `rst:0x1 (POWERON)` — izmjereno 11.08.
Posljedice:

- dok je test `ARMED`, **svako ubadanje USB-a troši armirani prolaz** i sačuva
  mjerenje napravljeno na USB napajanju, mimo šanta;
- iz `READY` (ili iz `RUNNING`, ako brownout prekine prolaz — brownout se
  prijavljuje kao `RTC_SW_SYS_RST`, pa stanje ostane zaglavljeno) jedini izlaz je
  `erase-flash`, što briše i FAT particiju s klipovima.

**Znači: mjerenje #2 nije izvodljivo bez re-arm puta.** ~15 min koda, i mora ući
prije nego što se diraju žice.
