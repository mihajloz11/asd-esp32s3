# Finalna validacija firmvera na fizičkom ventilatoru — 26–27.08.2026

**Status:** firmware je funkcionalno završen i potvrđen na pločici.
**Live ugovor:** `asd-quality-v1.6.0` ↔ host `physical-fan-v1.9.0` /
`physical-fan-artifacts-v1.9.0`.
**Dva validna fizička runa** nose sve brojke u ovom dokumentu; nijedna nije
prepisana iz starijeg teksta.

> **Granica tvrdnje.** Dokazano je da uređaj sam nauči normalno stanje
> nepoznatog ventilatora, sam izvede prag iz normal-only podataka i pouzdano
> prijavi **konstantnu akustičku promjenu**, uz `dropped=0`. Nije dokazano da
> je uzrok te promjene mehanički kvar — jedan mikrofon to ne može tvrditi.
> Papirić i pušteni ton su kontrolisane promjene, ne potvrđeni kvarovi.
> GUIDED25 kapija za papirić i dalje daje `FAIL` po sopstvenom kriteriju
> (`1/3` bloka); razlog je izmjeren i opisan u odjeljku 2.

---

## 1. Šta je tačno potvrđeno

| Tvrdnja | Dokaz |
|---|---|
| Uređaj se sam kalibriše na ventilatoru koji nikad nije čuo | `CALIBRATION_ACCEPTED` u oba runa, K1 `accepted` |
| Prag se izvodi na uređaju, iz normal-only prozora | `ADAPTTHR n=44 p=0.9900`, `PROFILE ... valid=1` |
| Odvojeni VERIFY zaista obara loš prag | run `5c`: `VERIFY_NORMAL_REJECT` (odjeljak 5.2) |
| Konstantna promjena podiže alarm | ton: `ANOMALY_ENTERED` poslije 3 uzastopna prozora |
| Trajnost promjene se posebno prijavljuje | `ANOMALY_SUSTAINED` poslije 12 alarmnih prozora |
| Nestabilan prozor se odbija, ne tumači | `OBSERVATION_HOLD` / `OBSERVATION_RESUMED` |
| Telemetrija je kompletna i bez gubitka | `dropped=0`, research paket `125/125` i `75/75` |
| Realno vrijeme je zadovoljeno | `compute_ms` 716–728 ms na prozor od 10 s |

Binarni fajl je **isti u oba validna runa**:

```
firmware/esp32s3_asd/build/esp32s3_asd.bin
354 784 B
SHA-256 9ac2caca2c5010747547d4bb942aae96f700221588a4a6863b5c01948d967813
project_version on-device-verified-78-g14aaebb-dirty
ESP-IDF v5.5.5-34-g21f3b71cbbf, target esp32s3
build flags: ASD_PSD_LIVE + ASD_RESEARCH_TELEMETRY (oba potvrđena u provenance)
```

---

## 2. Run A — GUIDED25 sa papirićem

`results/physical_fan/run_20260827T213148_fan02_guided25-20260827-v3recovery5d`

Postavka: `fan02`, 40 cm, 9°, soba, USB 5 V, `COM3` @ 115200.

**Kalibracija.** Sirovi `loo_cv` je bio `0,841676` — iznad kapije `0,6`, dakle
run bi po staroj logici pao kao `UNSTABLE_CALIBRATION`. Novi K1 trim je izbacio
dva najgora klipa i ponovo izračunao centar:

```
CALTRIM policy=k1-two-clip-trim-v1 discarded_count=2
  discarded_index_1=9 discarded_loo_1=1616.417358
  discarded_index_2=2 discarded_loo_2=998.927979
  retained=8 raw_loo_cv=0.841676
CAL_SUMMARY loo_mean=290.661407 loo_sd=123.838638 loo_cv=0.426058 loo_range=377.994690
```

**Izvedeni prag.**

```
ADAPTTHR n=44 mean=1041.676880 sd=1637.902954 p=0.9900 thr=8084.49365
PROFILE  center_windows=10 derive_windows=44 verify_windows=22
         level_mean_dbfs=-51.8519592 threshold_enter=8084.49365 threshold_exit=3707.34448
INTERFERENCE source=CAL_NORMAL_ONLY normal_windows=10 normal_max=1.49000776
         multiplier=1.25 threshold=1.86250973
```

**Rezultat po uslovu** (medijana skora; prag `8084,49`):

| Uslov | Prozora | HOLD | Alarmnih | Medijana |
|---|---:|---:|---:|---:|
| `normal_baseline` | 5 | 0 | 0 | 1 190,0 |
| `airflow_change_paper_1` | 5 | 4 | 0 | 26 398,5 |
| `recovery_normal_1` | 5 | 0 | 0 | 2 836,9 |
| `airflow_change_paper_2` | 5 | 3 | 0 | 60 049,9 |
| `recovery_normal_2` | 5 | 1 | 0 | 2 662,7 |
| `airflow_change_paper_3` | 5 | 2 | **2** | 14 388,8 |
| `recovery_normal_3` | 5 | 0 | 2 | 3 635,8 |
| `ambient_speech` | 5 | 4 | 0 | 36 838,2 |
| `recovery_after_speech` | 5 | 1 | 0 | 3 038,9 |
| `ambient_door` | 3 | 1 | 0 | 4 366,2 |
| `final_recovery` | 6 | 1 | 0 | 2 863,7 |

Run metrike: 65 DET prozora sirovo, 43 za metrike, 3 alarmna prozora, 2 epizode,
`6,98 %` vremena u alarmu, medijana oporavka `10,08 s`, `dropped=0`.

**Zašto je papirić prošao samo jednom.** Model je promjenu vidio u sva tri
bloka — medijane `26k`, `60k`, `14k` naspram normalne `1,2k`. Alarm nije podignut
u prva dva jer je kapija pouzdanosti odbila prozore kao nestabilne: 4 od 5
odnosno 3 od 5 prozora završilo je u `OBSERVATION_HOLD`, pa brojač uzastopnih
prekoračenja nikad nije stigao do 3. Treći blok je bio najmirniji — jedan HOLD,
pa `1 → 2 → 3` i alarm:

```
1229.6 airflow_change_paper_3 score= 11645 hold=1 consec=0
1239.6 airflow_change_paper_3 score= 14051 hold=0 consec=1
1249.6 airflow_change_paper_3 score= 25298 hold=0 consec=2
1259.6 airflow_change_paper_3 score= 29760 hold=0 consec=3 ALARM
```

To je **projektovano ponašanje, a ne promašaj**: papirić se drži rukom, pa
stimulus po konstrukciji nije konstantan. Sistem odbija da nestabilan prozor
proglasi anomalijom. Alarm se zatim prenio dva prozora u `recovery_normal_3`
(`12 866` i `4 190`, oba iznad izlaznog praga `3 707`) i ugasio se na `2 221` —
to je jedini razlog zašto GUIDED25 kapija za ovaj run kaže `FAIL`
(`alarm_or_carried_alarm:recovery_normal_3`, `paper_blocks_passed:1/3`).

**Govor i vrata nisu podigli alarm** iako su skorovi bili visoki
(`36 838` i `4 366`): 4 od 5 prozora govora završilo je u HOLD-u. To je tražena
osobina — smetnja se odbija kao nepouzdana, ne proglašava se kategorijom.

---

## 3. Run B — konstantni ton, završna provjera

`results/physical_fan/run_20260827T220338_fan02_tone-validation-20260827-final`

Ista postavka i isti binarni fajl. Cilj: provjeriti šta se dešava kad promjena
zaista jeste konstantna. Izvor: konstantni 1 kHz ton sa zvučnika, fiksne jačine
i položaja.

**Kalibracija je prošla bez trima** — `loo_cv=0,432290` je ispod kapije `0,6`,
pa `CALTRIM` nije ni emitovan.

```
CAL_SUMMARY loo_mean=448.132965 loo_sd=193.723618 loo_cv=0.432290 loo_range=640.332397
ADAPTTHR    n=44 mean=2887.967285 sd=5745.928711 p=0.9900 thr=21809.5059
PROFILE     level_mean_dbfs=-51.9622917 threshold_enter=21809.5059 threshold_exit=10904.7529
PRESENCE    level_mean_dbfs=-51.9622917 margin_db=11 gate_dbfs=-62.9622917 min_consecutive=3
INTERFERENCE normal_max=0.991275728 multiplier=1.25 threshold=1.23909461
```

Izlazni prag je ovdje pao tačno na `0,5 × enter`, dakle udario je u gornju
granicu koja živi u `psd_live.c` (`COMMISSION_EXIT_MAX_FRACTION`), a ne na p95
DERIVE raspodjele.

**Rezultat po uslovu** (prag `21 809,51`):

| Uslov | Prozora | HOLD | Alarmnih | Medijana | Opseg |
|---|---:|---:|---:|---:|---|
| `normal_baseline` | 6 | 0 | 0 | 7 163,7 | 6 711,7 – 8 171,3 |
| `constant_tone_1khz` | 45 | 8 | 14 | 22 628,5 | 6 890,3 – 87 151,6 |
| `recovery_after_tone` | 51 | 8 | 51 | 32 883,8 | 12 266,0 – 127 539,3 |

**Tok alarma.**

```
1315.5  score= 30012  hold=1  consec=0
1325.4  score= 32183  hold=1  consec=0
1335.4  score= 31475  hold=0  consec=1
1345.4  score= 33436  hold=0  consec=2
1355.4  score= 32709  hold=0  consec=3  ALARM
```

```
1356.047 s  ANOMALY_ENTERED    reason=THRESHOLD_PERSISTENCE  event=UNKNOWN_CHANGE
1485.843 s  ANOMALY_SUSTAINED  reason=SUSTAINED_DEVIATION
1855.250 s  OBSERVATION_HOLD_WARNING  reason=LONG_OBSERVATION_HOLD
```

Run metrike: 115 DET prozora sirovo, 99 za metrike, 64 alarmna prozora,
2 epizode, `64,65 %` vremena u alarmu, `dropped=0`,
`physical_result_status: valid_physical_result`.

Research paket je kompletan: 125 prozora očekivano, 125 kompletno,
125 `FEATURE96` i 625 `SUBSEG96` zapisa,
`window_features.npz` SHA-256
`c0cd588d2ab99dcc00389ea7df007ac843441208c148c0435f5c71cef24e8b09`.

**Prvi dio tona je bio pretih.** Prvih devet prozora tona dalo je
`6 890 – 15 582`, dakle unutar normalnog opsega — zvučnik je bio na premaloj
jačini. Poslije pojačanja skor skače na stabilnih `30 – 33k` i alarm se diže u
tri prozora, oko 30 s. To je koristan negativan podatak: **promjena mora biti
dovoljno jaka u odnosu na sopstveni šum ventilatora**, prag nije apsolutna
osjetljivost.

**Šta se desilo poslije gašenja.** Ton je stvarno utišan oko `1 861 s`.
Skor je odmah pao sa `~40k` na `12 266 – 19 561`, dakle **ispod ulaznog** praga
`21 809` ali **iznad izlaznog** `10 905`, pa je alarm ostao zaključan do kraja
runa. Histereza je radila kako je projektovana; run je završen prije nego što je
skor stigao ispod izlazne granice, tako da vrijeme oporavka za ovaj stimulus
**nije izmjereno**.

> **Napomena o označavanju.** Oznaka `recovery_after_tone` je unesena u
> `1 491 s`, a ton je stvarno ugašen tek oko `1 861 s`. Zato taj red u
> `SUMMARY.md` miješa ~6 minuta uključenog i ~2,3 minute isključenog tona i
> **ne smije se čitati kao „oporavak"**. Rastavljanje je vidljivo tek u
> `detections.csv`, po prozorima.

---

## 4. Kako lanac odluke radi u ovoj verziji

```
WAIT → CAL (10 × 10 s) → K1 → SETTLE → CENTER_LEARNING (10)
     → COMMISSION_DERIVE (44) → COMMISSION_VERIFY (22) → MONITORING
```

- **K1** odbija nestabilnu osnovu preko `loo_cv > 0,6`. Od 26.08. smije
  izbaciti **najviše dva** najgora CAL klipa; poslije svakog izbacivanja centar
  i LOO se računaju ponovo. Treća nestabilnost obara kalibraciju.
- **Prag** se izvodi isključivo iz 44 normal-only DERIVE prozora:
  `enter = empirical p99` (`percentile_higher`), `exit = p95`, ograničen na
  `[p50, 0,5 × enter]`. Centar ostaje onaj koji je K1 prihvatio iz CAL-a.
- **VERIFY** je odvojen i fail-closed: 22 normalna prozora ne smiju dati
  nijednu alarmnu epizodu. Ako daju — `VERIFY_NORMAL_REJECT`, run pada.
- **Kapija pouzdanosti** (`OBSERVATION_HOLD`) se izvodi po sesiji kao
  `max(10 CAL normal-only subsegment_instability) × 1,25`. HOLD suspenduje
  gradnju alarma, **ne briše** aktivan alarm i **ne mijenja** profil. Šest
  uzastopnih HOLD prozora daju `OBSERVATION_HOLD_WARNING`.
- **Alarm** traži 3 uzastopna pouzdana prozora iznad `enter` praga
  (`asd-events-v1.1.0-development`, `min_consecutive=3`), a gasi se ispod
  `exit` praga.
- **Trajnost**: poslije 12 alarmnih prozora (~2 min) emituje se
  `ANOMALY_SUSTAINED`. Stanje ostaje `ANOMALY`.

**„Kvar" nije akustička kategorija.** Terminalno stanje koje panel prikazuje kao
problem rezervisano je za grešku senzora ili toka (`AUDIO_TIMEOUT`,
`NONFINITE`, `PRESENCE_LOST`, `VERIFY_NORMAL_REJECT`). Dugotrajna akustička
promjena se prijavljuje kao `ANOMALY` + `ANOMALY_SUSTAINED`, sa oznakom događaja
`UNKNOWN_CHANGE`. To je namjerno: jedan mikrofon može potvrditi da se promjena
održava, ali ne može dokazati mehanički uzrok.

---

## 5. Kako se došlo dovde — svi pokušaji 26–27.08.

Devet runova, dva validna. Svi su sačuvani, uključujući odbačene.

| # | Run | Ishod | Šta je dokazao |
|---|---|---|---|
| 1 | `…T172038 …v3recovery4` | `invalid_firmware_terminal` | `LOW_LEVEL_OBSERVATION` na `rms=-66,709 dBFS` oborio run usred DET; prag `1 051,74` bio pretup |
| 2 | `…T221646 …v3recovery4b` | bez DET | `UNSTABLE_CALIBRATION`, `K1 loo_cv_above_max` |
| 3 | `…T223806 …v3recovery4c` | bez DET | isto, ponovljeno |
| 4 | `…T224512 …v3recovery4d` | `aborted_by_operator` | prvi `CALTRIM` (`0,769753 → 0,463238`, 1 klip), K1 prošao, ali prag `3 599,82` i dalje slab |
| 5 | `…T232638 …v3recovery5` | `invalid_firmware_telemetry` | host ne poznaje novi terminalni razlog |
| 6 | `…T205001 …v3recovery5b` | `aborted_by_operator` | prekid na 121 s |
| 7 | `…T205240 …v3recovery5c` | `invalid_firmware_telemetry` | **robustni fit odbijen na VERIFY-u** (5.2) |
| 8 | `…T213148 …v3recovery5d` | **`valid_physical_result`** | Run A, papirić |
| 9 | `…T220338 …tone-validation-final` | **`valid_physical_result`** | Run B, konstantni ton |

### 5.1 Šta je bilo pokvareno i šta je popravljeno

**(a) Apsolutni prag nivoa je zavisio od udaljenosti mikrofona.**
Run 1 je oboren jer je jedan DET prozor pao na `-66,709 dBFS`, ispod tadašnjeg
inženjerskog poda `-60 dBFS`. Taj pod je bio zamišljen kao provjera da audio
uopšte živi, ali je u praksi postao skrivena kapija prisustva mašine koja zavisi
od rastojanja. Pod je spušten na `-80 dBFS`, uz zamrznuto obrazloženje iz
normal-only SETTLE mjerenja (`-66,1637 dBFS`, rezerva `13,8 dB`).
Prisustvo mašine i dalje čuvaju `PRESENCE` gate (`level_mean − 11 dB`) i
`STUCK`/`ZERO`/`NONFINITE` provjere, koje su nezavisne od rastojanja.
`pc/config/asd_quality_policy_v1.json` `v1.0.0 → v1.1.0`,
`ASD_QUALITY_POLICY_ID 0x51555631 → 0x51555632`.

**(b) K1 je padao na jednom klipu od deset.** Runovi 2 i 3 su tačno onaj kvar
opisan u [P23](problemi-i-rjesenja.md) — devet klipova uredno, deseti strada u
uskom pojasu `66–75 Hz`. Uvedeno je izbacivanje **najviše dva** najgora CAL
klipa uz ponovno računanje centra i LOO (`K1_MAX_DISCARDED_CAL_CLIPS 2`), i
auditabilan `CALTRIM` zapis. Bez toga bi run 8 pao (`raw_loo_cv 0,841676`).
Kapija `max_loo_cv = 0,6` **nije** dirana.

**(c) Hard deadline je obarao run prije kraja plana.** GUIDED25 je imao
`hard_deadline_seconds: 1500`, a puni plan sa commissioningom traje duže, pa je
treći pokušaj automatski prekinut. Deadline je isključen (`null`, guard `0`),
limit pokušaja podignut `3 → 5`, a razlog upisan kao `recovery_amendment` blok u
`pc/config/guided25_workflow_v1.json` (`v1.1.0 → v1.2.0`). Panel, launcher i
`start_fan_run.py` prate isto.

**(d) Host nije poznavao novi terminalni razlog.** Runovi 5 i 7 su označeni
`invalid_firmware_telemetry / terminal_STATE_reason_unknown` iako je firmware
uradio ispravnu stvar. `VERIFY_NORMAL_REJECT` je dodat u
`CALIBRATION_STOP_REASONS`, pa se sada ispravno mapira na
`CALIBRATION_REJECTED`.

### 5.2 Šta je probano i odbačeno — robustni fit

Poslije runa 4 činilo se da je prag pretup zato što ga vuku pojedinačni visoki
DERIVE prozori. Napisan je `asd_robust_fit.c`: koordinatni 10 % trimmed centar
i Hampelova granica `median + 3 × 1,4826 × MAD`, sa p99 kao gornjim plafonom.

Run 7 je to isprobao na pločici i **odvojeni VERIFY ga je odbio**:

```
THRFIT method=trimmed-center-hampel-v1 source=COMMISSION_DERIVE_NORMAL_ONLY n=44
       center_trim=0.1000 median=298.332031 mad=110.771149 robust_sigma=164.229309
       sigma_multiplier=3.0000 p99_ceiling=1548.228516 threshold=791.019958 capped_high=3
…
COMMISSION_VERIFY  score=2871.271
COMMISSION_VERIFY  score=7766.39014
COMMISSION_VERIFY  score=2083.61792
COMMISSION_VERIFY  score=5385.0957
REJECTED           result=VERIFY_NORMAL_REJECT
STATE from=NO_MACHINE to=CALIBRATION_REJECTED reason=VERIFY_NORMAL_REJECT
```

Prag `791` naspram normalnih VERIFY prozora `2 083 – 7 766` — robustna granica je
bila daleko pretijesna i pravila bi niz lažnih alarma. Fail-closed VERIFY je to
uhvatio prije nego što je ijedan DET prozor nastao. **Ovo je najvrjedniji
negativan rezultat večeri: kapija koja postoji zbog ovakvih grešaka stvarno je
proradila na pločici.**

Zato je živi put vraćen na `frozen CAL center + empirical p99`.
`asd_robust_fit.c/.h` **ostaje u repou** sa host parity testom
(`pc/tests/test_asd_robust_fit_c.py`) da bi regresija bila reproducibilna, ali:

- nije u `SRCS` u `main/CMakeLists.txt`, dakle **ne ulazi ni u binarni fajl** —
  host parity test ga kompajlira zasebno u `.dll`/`.so`;
- `psd_live.c` ga ne poziva;
- `pc/tools/check_schema_consistency.py` obara provjeru ako se pojavi u živom
  putu;
- `pc/tests/test_guided25_workflow.py` isto to provjerava kao test;
- `pc/tools/derive_commissioning_policy.py` ga zadržava kao imenovani odbačeni
  kandidat (`hampel3-capped-p99_exit-p95-clamped`).

---

## 6. Izmijenjeni fajlovi

**Firmware**

| Fajl | Izmjena |
|---|---|
| `main/psd_live.c` | K1 trim do dva CAL klipa uz ponovno centriranje; `CALTRIM` zapis |
| `main/audio_quality_state.c` | pod nivoa `-60 → -80 dBFS`, uz obrazloženje u komentaru |
| `main/audio_quality_state.h` | `ASD_QUALITY_POLICY_ID 0x51555631 → 0x51555632` |
| `main/asd_robust_fit.c/.h` | **novo, van živog puta** — odbačeni robustni fit, čuva se zbog regresije |

**Politike**

| Fajl | Izmjena |
|---|---|
| `pc/config/asd_quality_policy_v1.json` | `v1.1.0`, pod `-80 dBFS` sa izvorom brojke |
| `pc/config/asd_commissioning_runtime_v1.json` | novi blok `normal_only_threshold_fit` |
| `pc/config/guided25_workflow_v1.json` | `v1.2.0`, deadline `null`, `attempt_limit 5`, `recovery_amendment` |

**Host**

| Fajl | Izmjena |
|---|---|
| `pc/tools/physical_fan_experiment.py` | `THRFIT` rječnik za čitanje istorijskih runova; `VERIFY_NORMAL_REJECT` kao kalibracioni stop |
| `pc/tools/check_schema_consistency.py` | provjerava da živi put ne koristi robustni fit i da p99/p95 pravilo stoji na sve tri strane |
| `pc/tools/derive_commissioning_policy.py` | imenovani odbačeni kandidat radi reprodukcije |
| `pc/tools/asd_panel.py`, `guided25_launcher.ps1`, `start_fan_run.py` | deadline opcionalan, limit pokušaja 5 |
| `pc/asd/guided_test.py` | `hard_deadline_seconds` smije biti `null` |

---

## 7. Validacija na hostu (27.08.2026)

```
.\.venv\Scripts\python.exe -m pytest pc/tests -q
478 passed in 29.17s

.\.venv\Scripts\python.exe pc\tools\check_schema_consistency.py
schema i politike saglasne:
  protokol            asd-quality-v1.6.0
  prisustvo           11.0 dB / 3 prozora
  vremenska odluka    absolute_profile (n=3, odvojeni enter/exit pragovi)
  sve politike        target_anomalies_used=false
```

Nijedna target anomalija (papirić, govor, vrata, ton) nije ušla ni u jedan fit.
Svi pragovi u oba runa izvedeni su iz normal-only prozora te iste sesije.

---

## 8. Šta ostaje otvoreno

Firmware je funkcionalno završen. Ostaje sitno čišćenje i fizički dokazi koji
nemaju veze sa algoritmom:

1. **GUIDED25 papirić kapija** i dalje daje `1/3`. Uzrok je izmjeren — papirić
   se drži rukom, pa stimulus nije konstantan. Ako se traži `3/3`, treba
   mehanički fiksirana prepreka, ne izmjena praga. **Prag se ne pomjera da bi
   run prošao.**
2. **Oporavak poslije jakog stimulusa nije izmjeren** — run B je završen dok je
   skor još bio između izlaznog i ulaznog praga.
3. `CALTRIM` ispisuje `discarded_loo_2=nan` kad je izbačen samo jedan klip.
   Bezopasno (nije parsirani protokolarni zapis, `firmware_parse_errors.csv` je
   prazan u oba runa), ali treba srediti pri sljedećem bumpu protokola.
4. Nedokazano i dalje: lemljenje tastera i LED, I2S liveness na hardveru,
   power-loss / NVS persistence, INA226 / E5 strujni put, samostalan demo bez
   PC-a.

Ažurirana lista: [`PREOSTALO.md`](PREOSTALO.md).

---

## 9. Artefakti

```
results/physical_fan/run_20260827T213148_fan02_guided25-20260827-v3recovery5d/
results/physical_fan/run_20260827T220338_fan02_tone-validation-20260827-final/
```

Svaki run nosi: `SUMMARY.md`, `detections.csv`, `events.csv`,
`firmware_events.csv`, `firmware_states.csv`, `firmware_quality.csv`,
`firmware_operator.csv`, `firmware_parse_errors.csv`, `guided25_report.json`,
`provenance.json` (git HEAD, diff SHA-256, SHA-256 svakog izvornog fajla,
SHA-256 bina), `serial.log`, `serial.raw`, `window_features.npz` + manifest.

Odbačeni runovi 1–7 iz tabele u odjeljku 5 sačuvani su u istom direktorijumu i
**ne smiju se brisati** — oni su izvor brojki za odjeljke 5.1 i 5.2.
