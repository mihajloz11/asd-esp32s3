# Dorada sistema poslije FAN01 — završna konsolidacija

**Datum:** 20.08.2026.

**Plan:** [PLAN-DORADA-POSLIJE-FAN01.md](../privatno/planovi/PLAN-DORADA-POSLIJE-FAN01.md)

**Live ugovor na dan pisanja (20.08.2026):** `physical-fan-v1.8.0` /
`physical-fan-artifacts-v1.8.0` ↔ `asd-quality-v1.5.0`

> **Zamijenjeno 24.08.2026.** Aktuelan par je `physical-fan-v1.9.0` /
> `physical-fan-artifacts-v1.9.0` ↔ `asd-quality-v1.6.0` — vidi
> [protokol-fizicki-ventilator.md](protokol-fizicki-ventilator.md) i
> [DNEVNIK-NEXT-LEVEL.md](../privatno/dnevnici/DNEVNIK-NEXT-LEVEL.md). Ostatak ovog dokumenta je
> zapis stanja od 20.08. i ne prepisuje se.

**Zaključak:** softverska arhitektura, testovi i ESP-IDF build su završeni;
numerička commissioning/HOLD politika, flash/runtime i novi fizički rezultat su
još `PENDING`.

## 1. Polazni rezultat koji je pokrenuo doradu

[FAN01](rezultat-fan01-2026-08-16.md) je prvi valjan run u kojem INMP441 sluša
stvarni ventilator. Pokazao je dvije odvojene činjenice:

1. `psd_shape` + Mahalanobis dobro rangira bezbjedno izazvanu promjenu protoka:
   papirić naspram normale AUC je bio 0,999 bez prelaznih prozora, uz vrlo mali
   uzorak i samo jednu postavku;
2. tadašnji `mean + 3σ` prag iz kratke kalibracije nije radio: 54/60 normalnih
   prozora bilo je iznad praga.

Raniji zapis `324/h` znači `54/60 × 360 = 324` alarmna prozora po satu. To nije
broj alarmnih epizoda/h: susjedni alarmni prozori pripadaju jednoj epizodi dok
se alarm ne ugasi. Papirić je kontrolisana promjena protoka, ne potvrđen kvar.
Razgovor je takođe dizao score; uzorak nije dovoljan da bi sistem bio proglašen
otpornim na govor.

Istorijski `cold-start-04` imao je reporting bug: SUMMARY ga je nazvao fizički
validnim iako `loo_cv=0,6275 > 0,6`. Centralni read-only recompute sada daje
`calibration_rejected:loo_cv_above_max`, `protocol_valid=True` i
`metrics_eligible=False`. Originalni run i SUMMARY nisu izmijenjeni.

## 2. Šta je urađeno po fazama

| Faza | Završena softverska promjena | Granica dokaza |
|---|---|---|
| 1 — K1 | Jedinstvena host/C commissioning politika; K1 prije ADAPTTHR/DET; terminalni reject je auditabilan, nije protocol error. | Host-C, literal replay i build; novi runtime nije fizički potvrđen. |
| 2 — multi-session | Novi `SESSION STARTED` resetuje samo session stanje; brojači, condition i temporalno stanje ne cure u sljedeću sesiju. CSV/summary razlikuju local window, run index i firmware session. | Puni sintetički drugi WAIT/CAL/DET tok; dvije žive sesije nisu ponovljene. |
| 3 — research telemetrija | Opcioni `asd-research-v1.0.0`: finalni `feature96`, pet `subseg96`, checksum, manifest i eksterni WAV link bez lažne tvrdnje da PCM postoji. | Bit-identičnost i parser testirani; research build/run sa fanom nije snimljen. |
| 4 — commissioning lab | Hronološki CENTER/DERIVE/VERIFY bez overlap-a/randomizacije; percentile, median+kMAD, block-max i conformal kandidati; episode/time/chatter/stability izbor. | Alati su DEVELOPMENT; target anomalije se čitaju samo nakon frozen policy. |
| 5 — runtime profil | Čisti state API `SETTLE→CENTER→DERIVE→VERIFY→MONITORING`; timeout/reject/abort fail-closed. SETTLE nema score prije centra. Profil čuva center96, reference, oba praga, counts i policy. | Runtime integracija host-testirana; numerički counts/pragovi nisu proizvodno zamrznuti. |
| 6 — smetnja/HOLD | `OBSERVATION_HOLD` suspenduje buildup, ne proglašava normalu, ne briše aktivan alarm ili profil; stable high poslije HOLD-a ponovo gradi alarm; long-hold warning. | Čista semantika testirana; interference policy je `enabled=false`, numeric DEVELOPMENT. |
| 7 — audio liveness | `audio_read_exact` koristi jedan ukupni deadline; `AUDIO_TIMEOUT` i `AUDIO_READ_ERROR` su fail-closed `SENSOR_ERROR`. | Host fixture i ESP-IDF build; fizički prekid I2S-a nije testiran. |
| 8 — storage profil | `asd-profile-v1.0.0`: magic/schema/size, fingerprint, generation, center96, reference, enter/exit, counts, policy ID-i i CRC32; briše samo ASD ključ. | Storage je kompajliran/testiran, ali DEVELOPMENT je RAM-only (`compile=0`, `developmental=1`): nema NVS load/save/PROFILESTORE do frozen production policy. |

Fazni izvještaji:

- [DORADA-FAZA1-K1-2026-08-16.md](DORADA-FAZA1-K1-2026-08-16.md)
- [DORADA-FAZA2-MULTI-SESSION-2026-08-16.md](DORADA-FAZA2-MULTI-SESSION-2026-08-16.md)
- [DORADA-FAZA3-RESEARCH-TELEMETRIJA-2026-08-20.md](DORADA-FAZA3-RESEARCH-TELEMETRIJA-2026-08-20.md)
- [DORADA-FAZA4-COMMISSIONING-LAB-2026-08-20.md](DORADA-FAZA4-COMMISSIONING-LAB-2026-08-20.md)
- [DORADA-FAZA5-6-RUNTIME-HOLD-2026-08-20.md](DORADA-FAZA5-6-RUNTIME-HOLD-2026-08-20.md)
- [DORADA-FAZA7-8-LIVENESS-NVS-2026-08-20.md](DORADA-FAZA7-8-LIVENESS-NVS-2026-08-20.md)

## 3. Novi sistemski tok

### 3.1 Svježe učenje

1. `SETTLE` prati samo kvalitet, level, tonalness, feature drift i dropped
   samples. Mahalanobis score prije centra nije dozvoljen API-jem.
2. `CENTER_LEARNING` uči lokalni centar iz čistih normalnih klipova. K1 odlučuje
   je li centar dovoljno stabilan da tok smije dalje.
3. `COMMISSION_DERIVE` koristi kasnije normal-only prozore i zamrzava odvojene,
   apsolutne `threshold_enter` i `threshold_exit`, uz `0 < exit < enter`.
4. `COMMISSION_VERIFY` koristi još kasniji normal-only blok. Ne mijenja centar
   ili prag; neuspjeh odbija profil.
5. `MONITORING` koristi samo finalizovan profil u RAM-u. Trajno NVS čuvanje je
   zabranjeno za DEVELOPMENT policy; smije se otvoriti tek nakon fizičke
   normal-only validacije i zasebnog frozen production policy bumpa.

K1 više nije praktični prag detekcije. Ne postoji implicitni `0,7×T_enter`.
Normalni prozori biraju prag preko alarmnih epizoda, vremena u alarmu, chattera,
najdužeg high niza i stabilnosti kroz blokove — ne preko procenta pojedinačnih
prozora i nikad preko papirića.

### 3.2 Odluka tokom nadzora

Redoslijed je fail-closed:

1. audio read/quality;
2. prisustvo ventilatora;
3. pouzdanost opažanja;
4. temporalna anomalija sa apsolutnim enter/exit pragovima.

Ako je opažanje nepouzdano, stanje je `OBSERVATION_HOLD`, ne
`AMBIENT_NOISE`: jedan mikrofon ne može dokazati da je uzrok baš govor. HOLD
zaustavlja novi buildup, ali aktivan alarm ostaje aktivan. Ako je score i nakon
prestanka smetnje stabilno visok, gradi se novi alarmni niz.

Ova arhitektura još nije isto što i fizički dokaz separacije. Numeric HOLD
granice su isključene dok novi normal-only/research run ne pruži podatke za
zamrzavanje policy verzije.

## 4. Verifikacioni dokazi

| Provjera | Tačan rezultat |
|---|---|
| Faza 2 puni regresioni prolaz | `328 passed in 9.62s` |
| Faza 1–2 follow-up review suite | `331 passed` |
| Faza 3 research ciljano | `105 passed` |
| Faza 4 commissioning lab | `5 passed` |
| Faze 5–6 runtime/HOLD ciljano | `203 passed in 4.83s` |
| Faze 7–8 audio/NVS/integracija ciljano | `272 passed` |
| Strogi q1.5 + 120/60 + persistence target | **`151 passed in 5.16s`** |
| Završni PC suite poslije kritičnog reviewa, 20.08.2026. | **`444 passed in 16.99s`** |
| ESP-IDF 5.5.5 `ASD_PSD_LIVE` reconfigure build | **PASS** |
| Firmware bin | `0x55d80` = **351 616 B**, oko 92% app particije slobodno |

Ovi dokazi potvrđuju kodni ugovor i build. Ne potvrđuju da je v1.8/q1.5
flashovan, da periferija timeoutuje u stvarnosti, da DEVELOPMENT runtime zaista
ne pravi ASD NVS zapis ili da je fizička razlika fan/papirić/razgovor poboljšana.

## 5. Integritet istorijskih dokaza

Faza 9 je prije i poslije dokumentacionih izmjena provjerila SHA-256. Nije
prepisan nijedan physical-run SUMMARY, preregistracija K1–K6 niti kanonski
benchmark. Ključne zaključane vrijednosti su:

| Artefakt | SHA-256 |
|---|---|
| `docs/preregistracija-fan01.md` | `caa27a107ceb0fdf2730fd773fb9bb6c189ed06f1deb1247ad0f46f90208c655` |
| `cold-start-04/SUMMARY.md` | `af9b3e3e22267fe29cd1f391d688ebc814fa0f6dae1b4ffd88c163a819f8ec24` |
| valjani `verify-sw-02/SUMMARY.md` | `f7853a3ee263f762e089e8cf4858e9fec9cb3e7bca738dd0cb25b01e4e1b0cbb` |
| canonical evaluation `SUMMARY.md` | `b54d9cb77d8ab1cfa0353bcabeede07c2a6429b04e3aa43d2125e000e514b0a8` |
| `results/results.csv` | `755ff5649464c8204985bfbeddafaba54f9b82db83b1f547807e9fea9cf75e13` |

Korekcije istorijskih zaključaka žive samo u novim dokumentima ili read-only
recompute izlazu, ne u izvornom runu.

## 6. Šta je završeno, a šta nije

### Software done

- verzioni i backward-read ugovori v1.6/q1.3, v1.7/q1.4 i v1.8/q1.5;
- K1, terminal drain i multi-session host;
- research telemetry/artifact contract;
- developmental candidate evaluation bez anomaly fita;
- commissioning/profile/absolute temporal API;
- HOLD state semantics;
- bounded audio i testiran NVS storage format sa DEVELOPMENT persistence gate-om;
- ciljani i puni PC testovi te finalni production-mode build.

### Policy pending

- stvarni SETTLE stability brojevi;
- izbor enter/exit kandidata na novom 20-min normal-only DERIVE bloku;
- nezavisni 10-min VERIFY;
- relative tonalness/subsegment granice koje bi uključile HOLD;
- dugoročna false-episode stopa. Deset minuta nije dovoljno za proizvodnu
  tvrdnju.

### Hardware/runtime pending

- flash i boot v1.8/q1.5;
- FEATURE/SUBSEG UART burst i `dropped_delta=0` sa stvarnim fanom;
- fizički I2S timeout/read-error;
- potvrda da DEVELOPMENT restart traži novo učenje; tek poslije frozen policy
  NVS valid/invalid restore, manual relearn i kontrolisani power-loss;
- zalemljeni taster/LED/otpornici i autonoman rad bez računara;
- INA226/E5 mjerenje i provjera da njegov namespace ostaje netaknut;
- novi fizički fan/papirić/razgovor rezultat.

## 7. Skraćeni naredni fizički protokol

Cilj je dobiti maksimalno informativan run uz malo ručnog snimanja, bez
post-hoc praga. Ovo je funkcionalni go/no-go za jednu postavku, ne dokaz
generalizacije.

### 7.1 Prije mjerenja

1. Flashovati tačno identifikovan v1.8/q1.5 research build i sačuvati Git/build
   provenance. Novi run ne prepisuje nijedan stari direktorij.
2. Fiksirati ventilator i mikrofon, zapisati napajanje, udaljenost, ugao,
   prostoriju i cold/warm start. Ne mijenjati montažu do kraja.
3. Izvršiti explicit relearn; DEVELOPMENT build namjerno ne učitava NVS profil.
4. Unaprijed zapisati candidate manifest, temporalnu politiku `n=3`, pravilo
   izbora i ovaj acceptance gate.

### 7.2 GUIDED25 normal-only commissioning

Podrazumijevani operaterski put je DEVELOPMENT `GUIDED25`, ne puni 120/60
laboratorijski protokol. Njegov stvarni, zaključani profil je:

- najviše 8 SETTLE i tačno 10 CENTER prozora;
- 44 hronološka DERIVE prozora (nominalno 7 min 20 s);
- 22 kasnija VERIFY prozora (nominalno 3 min 40 s).

Firmware iz DERIVE score-ova zamrzava unaprijed registrovani `psd_shape`
`T_enter=p99` i `T_exit=p75`. Sa strogim `score > enter`, p99 nad 44 prozora je
maksimum, pa DERIVE po konstrukciji ne može naoružati `n=3` alarm. VERIFY ne
mijenja prag i mora imati 0 epizoda, 0 aktivnih alarmnih prozora i 0 chattera;
svaki pad odbija profil i run.

Nema `SETTHR` komande niti DEVELOPMENT NVS importa laboratorijskog rezultata.
PC candidate laboratorija je offline analiza research sidecara i može uticati
samo na novu, verzionisanu policy/build verziju i novi preregistrovani retest.
Time rezultat papirića ili govora ne može post-hoc promijeniti prag istog runa.

Ako u 22 VERIFY prozora od približno 9,984 s nema nijedne epizode, jednostrani
95% Poisson gornji limit je približno **49,1 epizoda/h**. Zato GUIDED25 smije
reći samo „prošao kratki functional gate”, ne dokazati nisku dugoročnu stopu.

### 7.3 GUIDED25 frozen readout

Poslije uspješnog VERIFY-a panel vodi 8:50 raspored: normalna osnova, tri
papirić bloka sa oporavcima, jedan razgovor, oporavak, vrata i završni oporavak.
Papirić blok traje 50 s. Prvi prozor poslije promjene condition oznake je
`transition_window` i ne ulazi u konačne metrike.

Preregistrovani funkcionalni kriteriji su:

- najmanje 2/3 papirić bloka dostignu `consecutive>=3` i stvarni ulazak u
  alarm; ne traže se tri dodatna prozora provedena u već aktivnom alarmu;
- normalna osnova, svi oporavci, govor, vrata i završni oporavak nemaju ulazak
  niti preneseni aktivni alarm i imaju propisani minimum izmjerenih prozora;
- `DROPPED=0`, sve faze su potvrđene i research parovi/manifest su kompletni.

Live interference politika ostaje `enabled=false`, pa HOLD nije uslov prolaza
ovog runa. Govor/vrata ovdje mogu dokazati samo opaženu toleranciju konkretne
postavke; ne dokazuju klasifikator govora niti opštu otpornost na smetnje.

### 7.4 Odvojeni puni 120/60 laboratorijski protokol

Puni default firmware tok sa 120 DERIVE + 60 VERIFY prozora ostaje zaseban,
duži normal-only eksperiment. On se ne izvršava kada je armiran `GUIDED25` i
ne smije se opisivati kao rezultat 25-minutnog runa. Tek njegovih 60 nezavisnih
VERIFY prozora (oko 10 min) daje ranije navedeni Poisson gornji limit od oko
18 epizoda/h. Ni taj kratki limit nije proizvodna tvrdnja.

## 8. Završna odluka

Sistem je sada arhitektonski spreman da problem FAN01 izmjeri pošteno: centar,
prag i provjera više nisu isti kratki blok; govor se ne pretvara automatski u
normalu; pragovi su apsolutni i auditabilni; audio/NVS kvarovi su fail-closed.

Sistem još nije „gotov uređaj” dok novi normal-only VERIFY, frozen target
readout, flash/runtime, power-loss i elektronika ne prođu. Najvažnije je da
sljedeći test više ne može sakriti neuspjeh naknadnim izborom praga.
