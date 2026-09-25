# DNEVNIK NEXT LEVEL IZVRŠENJA

Ovaj dnevnik je append-style evidencija plana iz
[`PLAN-NEXT-LEVEL.md`](../istorija/planovi/PLAN-NEXT-LEVEL.md). Brojke se unose onakve kakve jesu;
`PASS`, `FAIL`, `BLOCKED_HARDWARE` i `NOT_RUN` nisu međusobno zamjenjivi.

## 09.08.2026. — početno stanje

- Korisnik je odobrio redom izvršenje osam softverskih pravaca.
- Pločica nije povezana; flash i uređajna mjerenja nisu pokrenuti.
- Kanonski v1.1.0 ostaje zamrznut na `mel1280`, `mel256`, `psd_shape`.
- Fan `psd_shape`: AUC `0,8666`, standardized pAUC@FPR≤0,1 `0,6669`;
  developmental rezultat sa istorijskim model-selection biasom.
- PC testovi prije novih izmjena: `32 passed`.
- Radni tree je već dirty zbog canonical, audit i physical-capture rada; nove
  faze moraju dirati samo eksplicitno navedene fajlove.

## Phase 0 — dokumentaciono mapiranje

**Status:** `PASS`

### Potvrđeno

- `psd_live.c` upozorava na tišinu, ali nastavlja kalibraciju.
- PSD live nema clipping, stuck/zero, short-read ni per-phase dropped gate.
- Nema eksplicitne state machine, EWMA, CUSUM, histereze ni rolling odluka.
- Nema f0/RPM/order-normalized PSD implementacije.
- Trenutni kanonski evaluator koristi near kanal.
- Raniji clip-level envelope/scalar/ensemble pravci već su ispitani i bili
  slabiji; neće se ponavljati.

### Otvoreno

- tonalness, LOO-spread, f0-confidence i rolling pragovi moraju se preregistrovati
  samo na normalnim/source fixtureima;
- flash/runtime i fizički događaji čekaju pločicu i fan;
- teacher feasibility zahtijeva poseban inventar prije preuzimanja modela.

## Faza 1 — fail-closed kalibracija i osnovna stanja

**Status:** `PASS_PC_BUILD` / `BLOCKED_HARDWARE`

### Planirani izlazi

- čisti C quality/state modul;
- host unit testovi;
- PSD live integracija;
- parser/schema/protocol bump;
- normal-only threshold provenance;
- ESP-IDF build bez flasha.

### Rezultati

- Dodani su čisti host-testabilni
  `firmware/esp32s3_asd/main/audio_quality_state.c/.h`: PCM accumulator,
  quality policy i stabilni reason/state nazivi. `OK` nastavlja svaku fazu;
  `LOW_LEVEL_OBSERVATION` smije nastaviti samo WAIT observation, dok svaki
  stvarni reject zaustavlja tok.
- Metrike su preuzete iz postojećeg `mic_test.c` obrasca: exact sample count,
  DC, RMS/dBFS, peak, clipping, zero i stuck count. `dropped_delta` prati obrazac
  `psd_verify.c`/`live_capture.c`.
- `psd_live.c` sada fail-closed zaustavlja WAIT/CAL/DET na vraćenom short readu,
  nonfinite vrijednosti, stuck/zero signalu, clippingu i bilo kom dropu. Prenizak
  nivo ne može proći iz WAIT u CAL; tokom CAL/DET završava u `NO_MACHINE`. LED se na
  stop putu gasi. Centar se i dalje nikad automatski ne pomjera.
- Uvedeni su ASCII `QUALITY`, `STATE`, `EVENT` zapisi protokola
  `asd-quality-v1.2.0` i svih šest zaključanih stanja.
- `physical_fan_experiment.py` je bumpovan na `physical-fan-v1.5.0`; operatorov
  `condition` ostaje u `events.csv`/`detections.csv`, dok firmware zapisi idu
  odvojeno u `firmware_quality.csv`, `firmware_states.csv` i
  `firmware_events.csv`; parse greške idu u `firmware_parse_errors.csv`.
- Operator condition sada počinje kao `unconfirmed`; firmware DET poruka ga ne
  mijenja. Metrike prihvataju samo eksplicitno potvrđene condition prozore nakon
  handshakea, očekivanih quality countova i oba `CALIBRATION_ACCEPTED` zapisa.
- Poznati QUALITY/STATE/EVENT sa pogrešnim/missing protokolom, malformed brojem
  ili missing poljem auditira se kao `PARSE_ERROR` i invalidira run. Terminalni
  firmware state/event odmah završava host run kao nevalidan.
- Review P2 je zaključao tačan telemetry redoslijed: WAIT `1..60/60`, CAL
  `1..10/10`, exactly-one CAL_SUMMARY i jednokratni DET QUALITY token uparen sa
  istim sljedećim DET windowom. Duplikat, replay, preskok ili interposed zapis
  invalidira run i ulazi u semantic audit.
- Host provjerava finite floatove, fazni sample count, count opsege, nulti drop
  za prihvaćeni observation, binarne LED/alarm vrijednosti i konzistentan
  `window/total_anom/uzastopnih/verdict`. Firmware DET ispis je proširen na 9
  značajnih cifara radi round-trip provjere binary32 poređenja.
- Firmware više ne emituje `nan`/`inf`: `metrics_valid` i `tonalness_valid`
  razdvajaju konačne sentinele od stvarno izračunatih metrika. Host iz metrika
  ponovo računa quality odluku i provjerava da je `result` saglasan sa
  verzionisanom politikom; literalni WAIT i reject ispisi iz `emit_quality`
  pokriveni su replay testovima.
- Najmanje 30/60 WAIT zapisa mora biti stvarni `OK`. CAL summary mora imati
  nenegativan i koherentan mean/sd/CV/range; tačno jedan `ADAPTTHR` mora doći
  poslije summaryja, prije acceptancea, i njegov prag mora ostati isti u svakom
  DET zapisu i u provenance/summary artefaktima.
- Dozvoljena STATE/EVENT gramatika i chain su zatvoreni: samo prvi
  `BOOT_FAIL_CLOSED` smije ostati u `NO_MACHINE`; kasniji NO_MACHINE i svi
  terminalni ishodi invalidiraju rezultat. Terminal drain završava tek kada su
  sačuvani i odgovarajući STATE i `FLOW_STOPPED`.
- `stop`/`--max-seconds` rade kratki final-buffer drain prije validne
  finalizacije. Serial-open i ne-prazan command-file failure i nevalidna
  operator condition više ne mogu preskočiti provenance/summary finalizaciju;
  otvoren port se uvijek zatvara.
- Treća review korekcija dodaje `feature_valid`: PCM quality i PSD
  segment/feature validnost više se ne miješaju. PCM-validan feature failure je
  zakoniti `NONFINITE` reject sa terminalnim drainom; literalni UART test to
  reprodukuje.
- DET alarm sada iz prethodnog statea izvodi tačno očekivani STATE/EVENT par.
  Missing, spurious, pogrešan, state-only i stop-race putevi invalidiraju run;
  full literalni v1.2 trace sa `%.9g` pragom i `ANOMALY_ENTERED` parom prolazi.
- Firmware i host dijele eksplicitnu `1e-3` toleranciju za teorijski
  nenegativne LOO/DET/tonalness vrijednosti. Tiny negative se clampuje na nulu,
  materijalno negativan score se odbija. Host dodatno provjerava anchorovan DET,
  `lo=0`, RMS/DC/peak fiziku i nenegativne summary/tonalness vrijednosti.
- Summary više nema drugi threshold argument: prag se čita samo iz trackerovog
  verifikovanog `ADAPTTHR`. Import, artifact-open, artifact-close i serial-close
  failure putevi best-effort zamjenjuju `in_progress` status i završavaju
  provenance/summary prije ponovnog podizanja greške.
- Poslije quality rejecta host ne prihvata dalji eksperiment, nego najviše 2,5 s
  samo drenira UART do terminalnog STATE + `FLOW_STOPPED`; pure drain odluka i
  terminal/timeout putevi imaju adversarial testove.
- Politika je verzionisana u `pc/config/asd_quality_policy_v1.json` sa
  `target_anomalies_used=false`. Tonalness proxy i LOO mean/sd/CV/range se
  instrumentiraju, ali njihovi gateovi ostaju `pending_normal_only`; nije
  izmišljen prag iz target anomalija.
- Ciljani testovi poslije svih review korekcija: `61 passed in 1.52s`.
- Svi PC testovi poslije svih review korekcija: `88 passed in 6.85s`.
- ESP-IDF 5.5.5: `ASD_PSD_LIVE=1`, `idf.py reconfigure build` — `PASS`.
  `audio_quality_state.c` i `psd_live.c` su kompajlirani; finalni v1.1 schema
  bin ima `295312 B`, SHA-256
  `2eeeb700dc0dc304dccf038053a07de3ba8c3f15101373e7f79925ccdbf24d25`,
  a najmanja app particija ima 93% slobodno.
- `git diff --check` — `PASS`; anti-pattern grep nije našao stari
  „kalibrišem svejedno”, automatsko pomjeranje centra niti target-anomaly prag.

### Otvoreno poslije Faze 1

- Pločica nije povezana: flash, UART schema provjera i runtime valid/invalid
  kalibracije su `BLOCKED_HARDWARE`, ne `PASS`.
- Host short-read fixture prolazi, ali `audio_read(..., portMAX_DELAY)` može na
  stvarnom prekidu I2S toka ostati blokiran umjesto da vrati short read; timeout
  i liveness ostaju P2 hardverski gap.
- Fizički ventilator nije dostupan: nema realne potvrde `NO_MACHINE` naspram
  validnog fana niti false-reject mjerenja.
- Tonalness i LOO-spread **rejection** gate ostaju namjerno neaktivni dok se
  pragovi ne preregistruju samo iz normalnih podataka. Postojeći LOO-derived
  anomaly threshold ostaje aktivan i to nije isti gate.

## 11.08.2026. — Faza 1 na pločici: prvi hardverski dokaz

Pločica je povezana (COM4, CH343). `ASD_PSD_LIVE=1`, `idf.py reconfigure build`
pa `flash` — build `on-device-verified-39-gc8833ad`, bin `0x4bca0` = 310 432 B,
najmanja app particija 93 % slobodna. Mikrofon INMP441 spojen (BCLK 4, WS 5,
SD 6, VDD 3V3, L/R→GND), bez kondenzatora. INA226 nije spojen; `app_main`
uredno prijavljuje `INA226 nije pronadjen` i nastavlja.

### Iz `BLOCKED_HARDWARE` u `PASS`

**Flash i boot:** `PASS`. PSRAM 16 MB, čist boot, `dropped_delta=0` u svakom
posmatranom bloku.

**UART schema na stvarnom uređaju:** `PASS`. Protokol `asd-quality-v1.2.0` se
emituje kako je specificiran — `STATE`, `EVENT` i `QUALITY` sa svim poljima,
`WAIT` indeksi uredno `1..60/60`, `metrics_valid=1`, nigdje `nan`/`inf`,
`tonal_gate=not_computed` odnosno `pending_normal_only` kako je i projektovano.
Do sada je ovo bilo provjereno samo replay testovima na hostu.

**Runtime nevalidna kalibracija:** `PASS` na **dvije različite klase odbijanja**,
obje sa tačnim lancem stanja i terminalnim događajem:

| Klasa | Lanac na uređaju |
|---|---|
| `CLIPPING` | `NO_MACHINE → CALIBRATION_REJECTED` + `FLOW_STOPPED` u fazi WAIT |
| `INSUFFICIENT_LEVEL` | `NO_MACHINE → NO_MACHINE` + `FLOW_STOPPED`, poslije `0/60 validnih blokova iznad -60 dBFS` |

Agregatni gate radi kako je specificiran: `LOW_LEVEL_OBSERVATION` je 60 puta
nastavio WAIT observation, ali **nijedan** se nije prebrojao kao `OK`, pa je
uslov „najmanje 30/60 stvarnih `OK`" ispravno odbio prolaz. To je tačno
ponašanje koje je Faza 1 obećala, prvi put potvrđeno na senzoru.

### `FAIL` koji je Faza 1 otkrila i koji je odmah popravljen

Fail-closed gate je pao u **prvom** WAIT bloku u tri od četiri reseta:
`CLIPPING`, `dc=-13286`, `peak=32763`. Uzrok nije gate nego `audio_i2s.c`, koji
nije odbacivao period slijeganja INMP441 poslije `i2s_channel_enable`.

Popravka: odbacivanje prve **1,0 s** u `capture_task`, na izvoru, prije ring
buffera, `raw_peak` i ocjene kvaliteta. Nije popuštanje gate-a i nije
`warn and continue`. Poslije popravke tri reseta daju ponovljiv rezultat
(blok 1 rms −67 dBFS, blokovi 3–4 −79 dBFS, `dc` → 0, razlika između reseta
< 1 dB). Puna analiza: [problemi-i-rjesenja.md → P15](../../docs/problemi-i-rjesenja.md#p15).

Sporedni, ali bitan nalaz iste popravke: `raw_peak` je dokaz kojim je zatvoren
rizik C1, a tranzijent od 29968 ga je mogao kontaminirati. Mjerenje C1 treba
ponoviti poslije popravke.

### Ostaje `BLOCKED_HARDWARE`

- **Validna kalibracija na uređaju** i cijela DET faza. Blokira
  [P16](../../docs/problemi-i-rjesenja.md#p16): mikrofon ne registruje zvuk iz zvučnika iako
  je mjerenjem potvrđeno da audio stiže na Realtek izlaz (Stereo Mix −16,03 dBFS)
  i da I2S podatkovni put radi. Nije razlučeno je li uzrok zvučnik ili mikrofon;
  za to treba fizička provjera (kucanje po mikrofonu, provjera `VDD`/`GND`/`L/R`,
  eventualno drugi INMP441).
- **False alarms/hour i latency** iz sekcije 11 — alat i zvuk su spremni
  ([`pc/tools/false_alarm_test.py`](../../pc/tools/false_alarm_test.py), kalibracioni
  snimak 130 s + detekciona petlja 80 s od `spd_1` target normalnih klipova,
  nivoi izjednačeni na −13,5 / −13,4 dBFS), ali prolaz ne može početi dok P16
  nije zatvoren.
- **Bezbjedno označeni događaji** — nema fizičkog ventilatora.
- `audio_read(..., portMAX_DELAY)` liveness gap iz Faze 1 ostaje neriješen i nije
  testiran na stvarnom prekidu I2S toka.

### Status Faze 1 poslije ovog bloka

`PASS` za flash, UART schemu i runtime odbijanje nevalidne kalibracije.
`BLOCKED_HARDWARE` za validnu kalibraciju, DET i sve što slijedi.
Jedan `FAIL` nađen i zatvoren (P15).

### Mikrofon #1 je akustički mrtav — dodatni blokator

Tap test, 116 blokova kroz 31 s neprekidnog kucanja: rms opseg **1,2 dB**, peak
nikad iznad **20**, naspram referentnih **1020** u mirnoj sobi i **6675** na
kucanje (06.08). Podatkovni put radi, akustički ne postoji. Mikrofon je istog
dana ponovo lemljen i pri čišćenju **naprskan alkoholom u sound port**, što je
kod MEMS mikrofona zabranjeno i objašnjava tačno ovaj potpis. Puna analiza:
[problemi-i-rjesenja.md → P16](../../docs/problemi-i-rjesenja.md#p16).

Sve što traži zvuk je time `BLOCKED_HARDWARE` do zamjene modulom #2.

## 11.08.2026. — Faza 2: semantika događaja, PC dio

**Status:** `PASS_PC_BUILD` / `NOT_RUN` na uređaju

Puna specifikacija: [faza2-semantika-dogadjaja.md](../../docs/uredjaj/semantika-dogadjaja.md).

### Rezultati

- Dodan čist host-testabilan modul
  [`asd_events.c/.h`](../../firmware/esp32s3_asd/main/asd_events.c), protokol
  `asd-events-v1.0.0`, bez ESP-IDF/I2S/PSD zavisnosti, isti obrazac kao
  `audio_quality_state.c`.
- **Razdvojeni status, događaj i uzrok.** Trajno odstupanje daje status
  `ANOMALY` uz događaj `UNKNOWN_CHANGE`; uzrok se ne tvrdi. `MECHANICAL_ANOMALY`
  se ne može emitovati.
- **Kapabilitetni gate u kodu**, ne u disciplini: `asd_event_capability()`
  označava `SPEED_CHANGED` kao `NEEDS_F0` (Faza 3), `AMBIENT_NOISE` kao
  `NEEDS_DUAL_CHANNEL` (Faza 5), `MECHANICAL_ANOMALY` kao `NEEDS_TRANSIENT`
  (Faza 6), a `finish()` svaki nedozvoljen događaj degradira u `UNKNOWN_CHANGE`.
  Cijela taksonomija je zaključana da se serijski ugovor ne mijenja kasnije.
- **Hijerarhija `sensor health → machine present → operating regime →
  deviation`**, gdje viši nivo guši niži. Konkretna posljedica: kad nivo padne,
  odstupanje se ne ocjenjuje i brojač odstupanja se resetuje, pa se ne emituje
  nepostojeća anomalija prije `FAN_STOPPED`. Bez toga bi skok score-a pri
  zaustavljanju (izmjereno 08.08: 10 → 59) proizveo lažnu anomaliju.
- Nivo `OPERATING_REGIME` je namjerno prazan do Faze 3 i to je jedini razlog
  zbog kojeg odstupanje dobija `UNKNOWN_CHANGE`.
- **Gate prisustva izveden samo iz normalnih podataka**
  ([`derive_presence_policy.py`](../../pc/tools/derive_presence_policy.py) →
  [`asd_presence_policy_v1.json`](../../pc/config/asd_presence_policy_v1.json),
  `target_anomalies_used=false`): `rms_dbfs ≥ kalibrisana_sredina − 11,0 dB`
  kroz 3 uzastopna prozora.

  Metodološki nalaz iz samog izvođenja: **nivo po klipu u DCASE-u je
  normalizovan** — sd je `0,02 dB` preko 60 target klipova. To je artefakt
  skupa podataka, ne fizika, i **isključen je** iz margine. Ulazi samo
  varijacija unutar klipa, i to po trojkama prozora, jer se odluka donosi po tri
  uzastopna prozora. Najgori normalan pad po trojki je `−7,90 dB` (source
  kontrola, 7400 trojki), plus 3 dB rezerve → 11 dB. Čisti 6σ račun bi dao
  `3,87 dB` i normalan rad bi sam sebe prijavljivao kao odsutnu mašinu, jer
  raspodjela ima težak rep u oba smjera (pojedinačni prozori −8,3 do +13,0 dB).
- **Tabela tranzicija** je deterministička i jedini autoritet. `NO_MACHINE →
  ANOMALY` zabranjeno; terminalna stanja bez izlaza; vraćanje mašine poslije
  zaustavljanja ide u `RECALIBRATION_REQUIRED`, nikad u `CALIBRATED_NORMAL`.
- **89 host testova** ([`test_asd_events_c.py`](../../pc/tests/test_asd_events_c.py)):
  svih 36 parova stanja naspram tabele prepisane nezavisno u testu, kapabiliteti,
  hijerarhija, oba brojača, determinizam kroz tri ponavljanja, `NULL` fail-closed.
  Ukupno u repou: **`177 passed`**.
- ESP-IDF `ASD_PSD_LIVE=1` build: `PASS`, `asd_events.c.obj` se kompajlira bez
  upozorenja, bin `0x4bcd0` = 310 480 B, app particija 93 % slobodna.

### Otvoreno poslije Faze 2

- Modul **nije uvezan u `psd_live.c`**. Namjerno: uvezivanje traži bump
  serijskog protokola i time izmjenu parsera `physical-fan-v1.5.0` i njegovih
  testova. Živi demo trenutno radi i ovom izmjenom se ne kvari.
- Gate prisustva od 11 dB je izveden iz snimaka. Na stvarnoj mašini nivo varira
  sa udaljenošću i opterećenjem, što DCASE normalizacija skriva, pa se margina
  **mora ponovo izvesti** kad ventilator bude dostupan.
- Nijedna tranzicija nije potvrđena na uređaju — `NOT_RUN`, ne `PASS`.

---

## 13–14.08.2026. — mikrofon #2, i zatvaranje softverskih faza

Plan izvršenja ovog bloka: [PLAN-ZAVRSNICA.md](../istorija/planovi/PLAN-ZAVRSNICA.md). Redoslijed je
promijenjen u odnosu na `PLAN-NEXT-LEVEL.md` jer je zamjena mikrofona odblokirala
hardverski put koji je bio glavno usko grlo; razlog je zapisan u samom planu.

### Mikrofon #2 radi — P16 zatvoren

Kontrolisani A/B test, 1 kHz sinus preko zvučnika, ista postavka na kojoj je
mikrofon #1 pao:

| | tišina | ton |
|---|---|---|
| rms medijana | −68,58 dBFS | **−32,71 dBFS** |
| rms raspon kroz fazu | 1,62 dB | — |
| peak | 46 | **1117** (2641 na ataku) |

Razlika **+35,87 dB**, peak **48×**. Ton se pojavio u bloku u kojem je krenula
reprodukcija i nestao u bloku u kojem je WAV završio. Mikrofon #1 je na istu
pobudu davao raspon 1,2 dB i peak ≤ 20.

`PASS`. Sve što je čekalo zvuk je odblokirano.

## Blok A — puni živi lanac na uređaju

**Status:** `PASS`

Prvi put je kalibracija **prihvaćena na uređaju**, i prvi put je DET faza
odradila puni prolaz. Zvuk je snimak TARGET normalnog ventilatora preko
zvučnika — nije fizički ventilator i tako se i vodi.

| | prolaz 1 (8 min) | prolaz 2 (30 min) |
|---|---|---|
| QUALITY zapisa / ne-`OK` | 106 / **0** | 237 / **0** |
| `dropped` / `clipped` | **0** / **0** | **0** / **0** |
| DET prozora | 36 (5,8 min) | 167 (27,6 min) |
| prozora iznad praga | 0 (0 %) | 152 (**91 %**) |
| lažnih alarmnih epizoda na sat | 0,00 | **8,69** |

**Lanac je u oba prolaza besprijekoran** — nula ne-`OK` zapisa, nula `dropped`,
nula `clipped` kroz 237 prozora. Time iz `BLOCKED_HARDWARE` u `PASS` prelaze
**validna kalibracija na uređaju** i **cijela DET faza**, dvije stavke koje su
od 11.08. bile glavni otvoreni dug.

**Ali brojka lažnih alarma nije svojstvo sistema.** Prvi prolaz je dao 0,00 na
sat, drugi 8,69 na sat, na istoj pločici, istom mikrofonu, istom zvuku i u istoj
sobi. Bilo bi pogrešno izvijestiti prvi broj kao rezultat.

### Nalaz koji je ovaj blok otkrio: prag je dominantni izvor rasipanja

Razlika između dva prolaza **ne dolazi od score-a nego od praga**:

| | prolaz 1 | prolaz 2 |
|---|---|---|
| LOO sredina / sd | 899,86 / 1595,75 | 167,15 / 59,92 |
| LOO CV | **1,77** | 0,36 |
| **prag** | **5687,11** | **346,89** |
| medijana score-a u DET | 567,7 | 1604,6 |
| medijana / prag | **0,10×** | **4,63×** |

Prag se razlikuje **16×**, dok se medijana score-a razlikuje 2,8×. Ukrštena
provjera to potvrđuje jednoznačno:

- prozori **prolaza 1**, ocijenjeni pragom prolaza 2: **92 %** iznad praga;
- prozori **prolaza 2**, ocijenjeni pragom prolaza 1: **8 %** iznad praga.

Dakle isti sistem, isti zvuk, a ishod se okreće naopako u zavisnosti od toga
kojih je deset kalibracionih klipova slučajno čuo.

**Mehanizam.** Formula je `max(p90 LOO, sredina + 3 sd LOO)`. U prolazu 1 je
jedan od deset kalibracionih klipova odskočio (LOO max 5430 uz medijanu reda
200), `sd` je odnio prag na 5687 i uređaj je postao praktično slijep. U prolazu
2 je kalibracija bila „čista" (sd 60), prag je pao na 347, a stvarna varijacija
normalnog rada kasnije je imala sd **8557** — dakle LOO je potcijenio buduće
rasipanje za **dva reda veličine**. Komentar u `psd_live.c` je to i predviđao
(„kalibracioni klipovi su snimljeni jedan za drugim, pa LOO potcjenjuje koliko
normalan rad varira KASNIJE"); sada je i izmjereno koliko.

Ovo je najvažnija otvorena stavka projekta i vodi se kao
[P17](../../docs/problemi-i-rjesenja.md#p17).

### Prolaz 3 — čisto mjerenje, na neopterećenoj mašini

Prolaz 2 je bio kontaminiran ([P19](../../docs/problemi-i-rjesenja.md#p19)), pa je ponovljen
na neopterećenom laptopu, sa firmverom koji već ima histerezu iz Faze 4:

| | prolaz 3 (20 min) |
|---|---|
| prag | 1087,97 (LOO sredina 394,80 sd 231,06, CV 0,59) |
| QUALITY zapisa / ne-`OK` | 177 / **0** |
| DET prozora | 107 (17,6 min) |
| prozora **iznad praga** | 6 (5,6 %) |
| prozora u alarmu | **0** |
| **lažnih alarma na sat** | **0,00** |

**Ovo je mjerodavna brojka.** I ona pokazuje zašto vremensko pravilo postoji:
šest prozora je prešlo prag, a **nijedan** put nije bilo tri uzastopna. Bez
pravila iz Faze 4 to bi bilo šest alarma na 17,6 min; sa njim je nula.

Sva tri prolaza zajedno:

| prolaz | prag | LOO CV | iznad praga | lažnih/h | napomena |
|---|---|---|---|---|---|
| 1 (8 min) | 5687 | 1,77 | 0 % | 0,00 | prag previsok |
| 2 (30 min) | 347 | 0,36 | 91 % | 8,69 | kontaminiran ([P19](../../docs/problemi-i-rjesenja.md#p19)) |
| **3 (20 min)** | **1088** | **0,59** | **5,6 %** | **0,00** | **čisto mjerenje** |

Prag varira 16× kroz tri kalibracije i to ostaje
[P17](../../docs/problemi-i-rjesenja.md#p17). Ali kad prag padne u sredinu tog opsega,
sistem radi tačno kako je projektovan.

### Ograničenje prolaza 2

Tokom prolaza 2 je na istom laptopu radilo teško računanje (Faze 3/5/6 nad 1100
klipova), a zvuk je puštan preko zvučnika tog istog laptopa. Nivo u detekciji je
porastao sa −46,5 na −40,4 dBFS u najglasnijem prozoru, a score-ovi opadaju kroz
prolaz (4596 → 2604 → 1875 po desetominutnim intervalima) kako se opterećenje
smanjivalo. Dio razlike između dva prolaza je zato **stvarna promjena u sobi**,
koju je uređaj ispravno vidio, a ne lažni alarm. Zaključak o pragu se time ne
mijenja, jer je izveden iz ukrštene provjere pragova nad **istim** prozorima,
ali sam broj lažnih alarma iz prolaza 2 nije čisto mjerenje. Vidi
[P19](../../docs/problemi-i-rjesenja.md#p19).

## Blok B — Faza 2 uvezana u živi tok, protokol `asd-quality-v1.3.0`

**Status:** `PASS_PC` / `PASS` na uređaju

- `asd_decide()` je od sada **jedini izvor odluke u DET fazi**; ad-hoc brojači
  iz `psd_live.c` su uklonjeni. Faza 1 i dalje drži WAIT/CAL gate-ove i to je
  namjerna granica: tamo još nema kalibracije od koje bi se odstupalo.
- `EVENT` nosi `event`, `capability` i `level`. Preslikavanje fail-closed
  odbijanja iz Faze 1 u rječnik Faze 2 živi u `asd_events.c`
  (`asd_event_for_quality_reject`), ne u neprovjerenoj I2S petlji. Prenizak
  nivo daje `event=NONE`, **ne** `FAN_STOPPED`: bez kalibracije uređaj mašinu
  nikad nije ni čuo, pa ne smije tvrditi da je stala.
- Novi zapisi: `PRESENCE` (gate prisustva), `TEMPORAL` (vremenska politika),
  `SESSION` i `BUTTON`. Prva dva postoje zato da host **nezavisno ponovi**
  odluku, umjesto da vjeruje firmveru — isti razlog zbog kojeg se prag emituje
  kao `ADAPTTHR`.
- Parser `physical-fan-v1.6.0` sada sam izvodi i prisustvo i histerezu iz
  objavljenih politika. Nenajavljen `PRESENCE_LOST` se odbija kao
  `spurious_PRESENCE_LOST`, a rezervisan događaj na žici (`MECHANICAL_ANOMALY`,
  `SPEED_CHANGED`, `AMBIENT_NOISE`) je greška protokola, ne nepoznato polje.
- `BUTTON` je van lanca telemetrije, jer ga piše zaseban UI task; pritisak u
  pogrešnoj milisekundi ne smije poništiti inače ispravan prolaz.

Potvrđeno na uređaju u tadašnjem, istorijskom autostart buildu:
`SESSION action=STARTED source=AUTOSTART`, `PRESENCE gate_dbfs=-56.64`,
`EVENT ... event=NONE capability=AVAILABLE level=DEVIATION`.

## Blok C — taster pokreće učenje, lampica javlja dokle se stiglo

**Status:** `PASS_PC` / `BLOCKED_HARDWARE` za sam taster i LED

Novi modul [`asd_operator.c`](../../firmware/esp32s3_asd/main/asd_operator.c),
43 host testa. Dva pravila su u kodu, ne u disciplini:

1. **Kratak pritisak nikad ne odbacuje naučeni centar.** Odbacivanje traži dug
   pritisak (1,5 s). Slučajan dodir tokom kalibracije je ne može pokvariti.
2. **Nema automatskog učenja u finalnoj konfiguraciji.** Istorijski speaker
   bring-up build dopuštao je da prva sesija krene sama poslije 10 s kako PC
   alati ne bi zavisili od tastera. Poslije završne revizije autostart je
   uklonjen: svaka kalibracija traži eksplicitan pritisak operatera, a ponovno
   učenje zapisuje `discards_calibration=1`.

Lampica, pet obrazaca razlučivih golim okom:

| režim | lampica | značenje |
|---|---|---|
| `IDLE` | kratak bljesak na 2 s | živ sam, čekam taster |
| `LEARNING` | treperi 5 Hz | učim, ne diraj ventilator |
| `READY` | **stalno svijetli** | **učenje gotovo**, nadzirem, normalno |
| `ALARM` | ugašena | trajno odstupanje |
| `FAULT` | dvostruki bljesak | fail-closed stop, treba restart |

Lampica i taster idu u zasebnom FreeRTOS tasku na 20 ms; bez toga bi se obrazac
osvježavao tek svakih 256 ms i treperenje od 5 Hz se ne bi ni vidjelo.

Ostaje `BLOCKED_HARDWARE`: taster i LED **nisu zalemljeni**. Otpornici 220–330 Ω
su na spisku [donijeti-sa-posla.md](../elektronika/nabavka/donijeti-sa-posla.md). Logika je pokrivena
testovima, sam pritisak nije provjeren na pločici.

## Blok D — Faza 4: vremenska odluka

**Status:** `PASS`

Alat: [`derive_temporal_policy.py`](../../pc/tools/derive_temporal_policy.py) →
[`asd_temporal_policy_v1.json`](../../pc/config/asd_temporal_policy_v1.json),
`target_anomalies_used=false`. 40 splitova, 2000 normalnih prozora.

**Rezultat je djelimično suprotan očekivanju.** EWMA i CUSUM su „očigledna"
nadogradnja i oba su **gora**:

| pravilo | lažnih/h | tuđa mašina/h | pobuda 1 prozor | pobuda 2 prozora | kašnjenje |
|---|---|---|---|---|---|
| 3 uzastopna (dosadašnje) | 0,00 | 11,16 | 0,004 | 0,062 | 3 |
| 4 uzastopna | 0,00 | 10,98 | 0,000 | 0,008 | 4 |
| **histereza 1,0/0,7 + n=3** | **0,00** | **5,40** | **0,000** | 0,087 | **3** |
| EWMA(0,4) + n=3 | 5,40 | 6,48 | 0,592 | 0,571 | 3 |
| CUSUM k=0,5 h=2 | 5,40 | 11,16 | 0,721 | 0,675 | 1 |

**Zašto EWMA i CUSUM gube:** oba **prenose** kratku pobudu kroz više prozora.
Jedan glasan udarac drži statistiku iznad praga dovoljno dugo da dopuni niz od
tri, pa upravo ono što je trebalo da filtrira kratku buku — nju i propušta.
Reakcija na pobudu od jednog prozora skače sa 0,004 na 0,59 odnosno 0,72.

**Usvojeno: histereza 1,0/0,7 uz nepromijenjenih 3 uzastopna prozora.** Uz iste
lažne alarme (0) i isto kašnjenje (3 prozora, dakle 30 s), izlazni prag na 0,7
ulaznog **prepolovljuje** alarmne epizode kad se akustika pomjeri: 11,16 → 5,40
na sat na klipovima drugog fizičkog ventilatora. To je tačno rizik pri dugom
radu — soba se mijenja, ventilator stari.

Implementacija: [`asd_temporal.c`](../../firmware/esp32s3_asd/main/asd_temporal.c),
22 testa, uključujući **PC↔C parity na svih 8 pravila** preko slučajnih tokova.
EWMA i CUSUM su ostavljeni u strukturi politike, isključeni nulom — da se ne
„otkriju" ponovo kao nova ideja.

### Metodološka ispravka unutar same faze

Prvi prolaz alata je javio **14,31 lažnih alarma na sat** za dosadašnje pravilo.
To je bila greška postavke, ne nalaz: u normalan tok su bili ubačeni i `source`
klipovi, a to je **drugi fizički ventilator**, dok se uređaj kalibriše na mašini
koju i nadzire. Mjerio se domenski pomak, ne vremensko pravilo. Poslije
ispravke tok sadrži samo klipove iste mašine, a tuđa mašina se izvještava
odvojeno i ne ulazi u izbor pravila.

Drugi ispravljeni korak: prvi kriterij izbora tražio je apsolutnu nulu na sve
tri ose i **nijedno pravilo ga nije prošlo**. Razlog nije bio u pravilima nego u
kriteriju — kratka pobuda uz prozor koji je ionako iznad praga može dopuniti niz
od tri, i to nijedno pravilo koje broji uzastopne prozore ne može isključiti.
Oba kriterija su zapisana u izlaznom JSON-u.

## Blokovi E, F, G — Faze 3, 5 i 6

**Status:** `PASS` kao izvršene faze, **negativan rezultat** kao ishod

Alat: [`evaluate_advanced.py`](../../pc/tools/evaluate_advanced.py), protokol
`advanced-evaluation-v1.0.0`, odvojen namespace. Kanonski v1.1.0 nije diran.
Kandidati su navedeni u kodu **prije** pokretanja; anomalije se otvaraju tek kad
su svi modeli fitovani i splitovi zamrznuti. 20 splitova.

| kandidat | faza | AUC | pAUC@0,1 | vs baseline |
|---|---|---|---|---|
| `psd_shape` (baseline) | — | **0,8556 ± 0,0240** | 0,6393 | — |
| `psd_order` | 3 | 0,6388 ± 0,0467 | 0,5171 | **−0,2168** |
| `psd_regime` | 3 | 0,8556 ± 0,0240 | 0,6393 | 0,0000 |
| `psd_logratio` | 5 | 0,7185 ± 0,0347 | 0,5848 | −0,1371 |
| `psd_coherence` | 5 | 0,7506 ± 0,0398 | 0,5774 | −0,1050 |
| `psd_masked` | 5 | 0,4500 ± 0,0645 | 0,4884 | **−0,4056** |
| `transient` | 6 | 0,5647 ± 0,0267 | 0,5062 | −0,2909 |
| `psd_plus_transient` | 6 | 0,8568 ± 0,0258 | 0,6433 | +0,0012 |

### Faza 3 — režimi se ne mogu izvesti iz f0, i to je svojstvo skupa

Estimator f0 daje medijanu **34,0 Hz za sve tri brzine**. Prvi refleks je bio da
je estimator pokvaren, jer harmonijska suma po prirodi vuče ka niskim f0.
Kontrola, nezavisna od estimatora, gleda gdje su tonalni vrhovi iznad spektralne
pozadine:

| brzina | vrhovi iznad pozadine |
|---|---|
| `spd_1` | 68,4 · 76,2 · 78,1 · 93,8 · 99,6 · 101,6 Hz |
| `spd_2` | 68,4 · 76,2 · 78,1 · 93,8 · 99,6 · 101,6 Hz |
| `spd_3` | 68,4 · 76,2 · 78,1 · 95,7 · 99,6 · 101,6 Hz |

Vrhovi se poklapaju unutar jednog FFT bina (1,95 Hz). `spd_1/2/3` se u ovom
skupu **ne razlikuju po obrtnoj frekvenciji** nego po širokopojasnom nivou
(~0,5 dekada oko 240 Hz). Estimator radi ispravno; 68,4 Hz je drugi harmonik
od 34,2 Hz.

Posljedica: order-warp gubi rezoluciju traka bez ičega zauzvrat (−0,217), a
režimski centri se degenerišu u jedan (razlika 0,0000). **Faza 3 pada svoj
sopstveni kriterij prolaza** („mjerljivo razlikovanje `spd_1/2/3` iz normalnih
klipova"), pa `SPEED_CHANGED` ostaje `NEEDS_F0` i neemitljiv.

### Faza 5 — drugi mikrofon se ne isplati

Sve tri dual-channel varijante su **slabije** od near kanala samog.
`psd_masked` je ispod slučajnog pogađanja (0,45): maska izvedena iz far kanala
potiskuje upravo trake u kojima je ventilator glasan u oba kanala — dakle sam
ventilator.

**Posljedica za hardver: finalna šema ostaje sa jednim INMP441.** Ovo je bio
jedini otvoreni pravac koji je mogao promijeniti šemu, i zato je i mjeren prije
nje. `AMBIENT_NOISE` ostaje `NEEDS_DUAL_CHANNEL` i neemitljiv.

### Faza 6 — tranzijentni put ne dodaje ništa mjerljivo

Sam po sebi slab (0,565). Spojen sa PSD-om daje +0,0012 AUC, uz sd po splitu
0,024 — dakle **dvadeset puta manje od sopstvenog rasipanja**. To nije
poboljšanje. Anomalije ovog ventilatora su tonalne i širokopojasne, ne udarne.
`MECHANICAL_ANOMALY` ostaje `NEEDS_TRANSIENT` i neemitljiv.

### Šta ova tri negativna rezultata zajedno znače

Kapabilitetni gate iz Faze 2 je odbijao da tvrdi `SPEED_CHANGED`,
`AMBIENT_NOISE` i `MECHANICAL_ANOMALY` jer dokaza nije bilo. Faze 3, 5 i 6 su
te dokaze potražile i **nisu ih našle**. Gate je time potvrđen mjerenjem, a ne
samo oprezom, i `UNKNOWN_CHANGE` ostaje najjača tvrdnja koju sistem smije
izreći.

## Blok H — Faza 7: zaustavljeno na feasibility gate-u

**Status:** `NOT_RUN`, sa razlogom

Inventar ([`faza7_inventory.json`](../../results/advanced/faza7_inventory.json)):
`torch`, `torchaudio`, `transformers` i HF cache **ne postoje**; TensorFlow
2.19.1 i librosa 0.11.0 postoje; disk ima 194 GB slobodno.

Pokretanje zamrznutog BEATs/EAT embeddinga traži instalaciju PyTorcha (~200 MB
CPU wheel) i preuzimanje checkpointa (~350 MB), pa ~6 min računa na CPU-u za
1100 klipova. Tehnički izvodljivo.

Zaustavljeno ipak, iz dva razloga:

1. **Teacher je PC upper bound, eksplicitno ne ESP32 kandidat.** Distilacija je
   po planu opravdana samo ako je dobitak velik i ponovljiv.
2. **Izmjereno usko grlo nije feature nego prag.** Šest unaprijed navedenih
   alternativa nije nadmašilo `psd_shape`, dok se prag između dva prolaza mijenja
   16×. Bolji embedding ne rješava prag koji je nestabilan.

Ovo je ishod koji plan izričito dozvoljava kao kraj faze. Ako se PyTorch
instalira, faza se pokreće bez ijedne dalje odluke.

## Blok I — Faza 8: metrike, CI i provjera schema

**Status:** `PASS`

- [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml): host testovi i C
  parity, provjera schema, grep na zabranjene obrasce. Namjerno **ne** vrti
  ništa što traži pločicu ili DCASE audio — CI ne smije stvoriti utisak da je
  fizički lanac provjeren.
- [`check_schema_consistency.py`](../../pc/tools/check_schema_consistency.py) hvata
  klasu greške koja ne obori nijedan test odmah, nego tek fizički prolaz kad se
  ventilator već vrti: verzija protokola ili prag promijenjen na jednom mjestu,
  a ne na drugom. Trenutno: protokol `asd-quality-v1.3.0`, prisustvo 11,0 dB / 3
  prozora, vremenska odluka `hysteresis_1.0_0.7_n3`, sve politike
  `target_anomalies_used=false`.

## Stanje testova i builda

| | |
|---|---|
| PC testovi | **271 passed** (bilo 177 na početku bloka) |
| novi test fajlovi | `test_asd_operator_c.py` (43), `test_asd_temporal_c.py` (22) |
| ESP-IDF build | `PASS`, bin `0x4D3F0` = 316 400 B, slobodno 3 877 904 B od 4 MiB (**92,46 %**) |
| Flash + provjera na uređaju | `PASS` — `SESSION`/`PRESENCE`/`TEMPORAL` na žici |
| schema provjera | `PASS` |

## Šta ostaje otvoreno

1. **Fizički ventilator.** Nijedna tvrdnja o stvarnom kvaru ne postoji i ne
   može postojati dok se ne kupi. Sve dosadašnje je zvučnik.
2. **Šema i lemljenje** — kondenzatori, dioda, regulator, otpornici, taster i
   LED. Faza 5 je zatvorila jedino pitanje koje je moglo promijeniti šemu:
   **jedan mikrofon**.
3. **Prag** ([P17](../../docs/problemi-i-rjesenja.md#p17)) — **glavna otvorena stavka.**
   Razlikuje se 16× između dvije kalibracije i odlučuje hoće li uređaj biti
   slijep ili će vikati. Sve ostalo u lancu radi; ovo ne.
4. **`audio_read(..., portMAX_DELAY)` liveness** — i dalje neriješen i
   netestiran na stvarnom prekidu I2S toka.
5. **Taster i LED na pločici** — logika testirana, hardver nije spojen.

## 20.08.2026. — konsolidacija dorada poslije FAN01 (Faze 1–8)

Ovaj datirani blok dopunjava, ali ne prepisuje, raniju hronologiju. Tvrdnja
iz prethodnog bloka da fizički ventilator ne postoji prestala je važiti
16.08.2026: FAN01 je prvi valjan fizički run. `psd_shape` je razdvojio
kontrolisanu promjenu protoka papirićem od normale, ali je tadašnji prag stavio
54/60 normalnih prozora iznad praga. `324/h` je broj alarmnih prozora skaliran
na sat, ne alarmnih epizoda/h. Papirić nije potvrđen stvarni kvar.

Poslije tog nalaza izvršen je plan
[PLAN-DORADA-POSLIJE-FAN01.md](../istorija/planovi/PLAN-DORADA-POSLIJE-FAN01.md):

- **Faza 1:** centralni K1 host/C gate, literalni terminalni UART redoslijed i
  read-only korekcija `cold-start-04`; originalni artefakt nije mijenjan.
- **Faza 2:** više firmware sesija u jednom host runu, session-scoped reset,
  `firmware_session_index`, transition-window i episode-aware metrike.
- **Faza 3:** opcioni `asd-research-v1.0.0` sidecar sa finalnih 96 obilježja,
  pet podsegmenata 8/8/8/7/7, checksumom i NPZ manifestom.
- **Faza 4:** razvojni normal-only laboratorij za hronološki
  CENTER/DERIVE/VERIFY, threshold i feature kandidate; target anomalija ne
  ulazi u fit.
- **Faze 5–6:** čisti commissioning/profile/interference moduli, odvojeni
  apsolutni enter/exit i `OBSERVATION_HOLD`. HOLD suspenduje buildup, ne briše
  alarm/profil, ali numeric policy ostaje `DEVELOPMENT`, `enabled=false`.
- **Faze 7–8:** bounded audio read sa ukupnim timeoutom i NVS storage format
  `asd-profile-v1.0.0` sa fingerprintom, generation, policy ID-ima i CRC32.
  DEVELOPMENT runtime je RAM-only: compile i runtime gate zabranjuju load/save.

Aktuelni live par je `physical-fan-v1.8.0` /
`physical-fan-artifacts-v1.8.0` ↔ `asd-quality-v1.5.0`. Offline reader čuva
istorijske v1.6/q1.3 i v1.7/q1.4 parove; stari SUMMARY, UART, CSV,
preregistracija K1–K6 i kanonski benchmark nisu prepisani.

Dokazi na 20.08.2026:

| Dokaz | Rezultat |
|---|---|
| puni trenutni PC suite | `423 passed in 14.46s` |
| research ciljano | `105 passed` |
| commissioning lab ciljano | `5 passed` |
| commissioning/HOLD ciljano | `203 passed in 4.83s` |
| audio/NVS/integracija ciljano | `272 passed` |
| ESP-IDF 5.5.5 `ASD_PSD_LIVE` | `PASS`, 349 728 B |

Build i host testovi nisu flash/runtime dokaz. V1.8/q1.5 nije potvrđen novim
bootom ili fizičkim runom; prekid I2S-a, DEVELOPMENT restart/relearn i potpuno
autonoman LED/taster rad ostaju `PENDING_HARDWARE_RUNTIME`. NVS restore i
power-loss dolaze tek poslije frozen production policy bumpa.
Numerički commissioning i interference policy ostaju
`DEVELOPMENT/PENDING_PHYSICAL_VALIDATION`.

Sljedeći fizički prolaz je namjerno kratak: 30 min normal-only podijeljenih
hronološki na 20 min DERIVE i kasnijih 10 min VERIFY, zatim najviše tri
papirić i dva conversation bloka. Centar, oba praga i policy manifest moraju
biti zamrznuti prije target readouta; nema post-hoc podešavanja. VERIFY traži
nula alarmnih prozora, epizoda i chatter prelaza. Nula epizoda u 10 min ipak
daje tek približno 18 epizoda/h kao jednostrani 95% Poisson gornji limit, pa je
to funkcionalni go/no-go, ne dokaz dugoročne pouzdanosti.


## 26–27.08.2026. — finalna validacija firmvera na pločici

Devet runova, dva validna. Puna analiza sa svim brojkama:
[`rezultat-finalna-validacija-2026-08-27.md`](../../docs/probe/rezultat-finalna-validacija-2026-08-27.md).

Aktuelni live par je `physical-fan-v1.9.0` / `physical-fan-artifacts-v1.9.0` ↔
`asd-quality-v1.6.0`. Offline reader i dalje čuva v1.6/q1.3, v1.7/q1.4 i
v1.8/q1.5; istorijski runovi nisu dirani.

**Šta je oboreno i popravljeno:**

| Problem | Fix | Zapis |
|---|---|---|
| Pod `-60 dBFS` postao skrivena kapija prisustva mašine | pod `-80 dBFS`, obrazložen iz normal-only SETTLE `-66,1637 dBFS` | [P24](../../docs/problemi-i-rjesenja.md) |
| K1 pada na jednom klipu od deset | trim najviše dva CAL klipa uz ponovno centriranje, kapija `0,6` netaknuta | [P25](../../docs/problemi-i-rjesenja.md) |
| Robustni Hampel prag `791` naspram normalnih VERIFY prozora `2 083–7 766` | robustni fit odbačen, živi put vraćen na frozen CAL centar + empirical p99 | [P26](../../docs/problemi-i-rjesenja.md) |
| Hard deadline 1 500 s obara run prije kraja plana | deadline `null`, limit pokušaja `5`, `recovery_amendment` u workflow politici | [P27](../../docs/problemi-i-rjesenja.md) |

**Dokazi na 27.08.2026:**

| Dokaz | Rezultat |
|---|---|
| puni PC suite | `478 passed in 29.17s` |
| `check_schema_consistency.py` | PASS, `asd-quality-v1.6.0`, sve politike `target_anomalies_used=false` |
| ESP-IDF 5.5.5 `ASD_PSD_LIVE` + research | `PASS`, 354 784 B, SHA-256 `9ac2caca…8d967813` |
| Run A — papirić (`v3recovery5d`) | `valid_physical_result`; prag `8 084,49`; alarm u 3. bloku; oporavak `10,08 s`; `dropped=0` |
| Run B — konstantni ton (`tone-validation-final`) | `valid_physical_result`; prag `21 809,51`; `ANOMALY` u 3 prozora, `ANOMALY_SUSTAINED` u 12; `dropped=0` |

Isti binarni fajl je pustio oba runa, pa je q1.6 par ovim boot/runtime potvrđen.
Govor i vrata nisu podigli alarm iako su im skorovi bili visoki — kapija
pouzdanosti ih je odbila kao nestabilne, što je tražena osobina.

**Šta i dalje nije dokazano:** lemljenje tastera i LED, I2S liveness na
hardveru, power-loss / NVS persistence, INA226 / E5 strujni put i samostalan
demo bez PC-a. GUIDED25 papirić kapija ostaje `1/3` — uzrok je izmjeren
(stimulus se drži rukom), i prag se zbog toga **ne** pomjera.
