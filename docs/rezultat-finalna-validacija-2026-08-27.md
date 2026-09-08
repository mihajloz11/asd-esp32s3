# Finalna validacija firmvera na fizičkom ventilatoru — 26–27.08.2026

**Revizija tumačenja:** 06.09.2026. Firmware je izvršen na pločici; prolaz telemetrijskih provjera nije isto što i prolaz eksperimenta.
**Live ugovor:** `asd-quality-v1.6.0` ↔ host `physical-fan-v1.9.0` /
`physical-fan-artifacts-v1.9.0`.
**Dva validna fizička runa** nose sve brojke u ovom dokumentu; nijedna nije
prepisana iz starijeg teksta.

> **Granica tvrdnje.** Obje sesije imaju prihvaćenu kalibraciju i validnu
> telemetriju. Ton daje alarm i trajno odstupanje. GUIDED25 proba papirićem
> ima FAIL: 1/3 detektovanih blokova i prenesen alarm u oporavak. Nestabilnost
> ručne pobude je moguće objašnjenje, ne dokaz jedinog uzroka. Pobude nisu
> potvrđeni kvarovi, a dugoročna pouzdanost nije izmjerena.

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
| Izmjeren trošak računanja | `compute_ms` 716–728 ms za obilježje i ocjenu; ne obuhvata cijeli tok |

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

| Uslov | Prozora | HOLD | Alarmnih | Medijana | Opseg |
|---|---:|---:|---:|---:|---|
| `normal_baseline` | 4 | 0 | 0 | 1 146 | 1 080 – 2 134 |
| `airflow_change_paper_1` | 4 | 3 | 0 | 30 255 | 16 008 – 56 167 |
| `recovery_normal_1` | 4 | 0 | 0 | 2 757 | 2 563 – 3 097 |
| `airflow_change_paper_2` | 4 | 3 | 0 | 62 344 | 54 026 – 66 838 |
| `recovery_normal_2` | 4 | 0 | 0 | 2 555 | 2 120 – 3 234 |
| `airflow_change_paper_3` | 4 | 1 | 2 | 19 844 | 14 051 – 29 760 |
| `recovery_normal_3` | 4 | 0 | 1 | 3 086 | 2 221 – 4 190 |
| `ambient_speech` | 4 | 4 | 0 | 38 307 | 31 074 – 41 066 |
| `recovery_after_speech` | 4 | 0 | 0 | 2 819 | 2 528 – 3 050 |
| `ambient_door` | 2 | 1 | 0 | 49 549 | 4 366 – 94 732 |
| `final_recovery` | 5 | 0 | 0 | 2 825 | 2 594 – 3 456 |

Filter: validan protokol, potvrđen uslov, bez prelaznog prozora; HOLD ostaje uključen.

Run metrike: 65 DET prozora sirovo, 43 za metrike, 3 alarmna prozora, 2 epizode,
`6,98 %` vremena u alarmu, medijana oporavka `10,08 s`, `dropped=0`.

**Ishod papirića.** Medijane ocjene su 30 255, 62 344 i 19 844,
naspram osnove 1146. U prva dva bloka tri od četiri prozora imaju HOLD,
pa se ne ostvari uslov od tri uzastopna pouzdana prekoračenja. Alarm se javlja
u trećem bloku. To jeste promašaj zadatih kriterija detekcije, iako tok
firmvera odgovara implementiranom pravilu. GUIDED25 prijavljuje i prenesen
alarm u `recovery_normal_3`. Ručno držanje papirića nije izolovano kao jedini
uzrok nestabilnosti. U četiri prozora govora i dva prozora vrata nema alarma;
taj mali uzorak ne potvrđuje opštu otpornost na buku.

---

## 3. Run B — konstantni ton, završna provjera

`results/physical_fan/run_20260827T220338_fan02_tone-validation-20260827-final`

Ista postavka i isti binarni fajl. Cilj: provjeriti šta se dešava kad promjena
ima tonski karakter. Izvor je ton od 1 kHz sa zvučnika. Bilješke navode naknadno pojačanje; tačno vrijeme promjene jačine nije zabilježeno.

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
| `normal_baseline` | 5 | 0 | 0 | 7 085 | 6 712 – 8 171 |
| `constant_tone_1khz` | 44 | 8 | 14 | 23 574 | 7 327 – 87 152 |
| `recovery_after_tone` | 50 | 8 | 50 | 33 170 | 12 266 – 127 539 |

Filter: validan protokol, potvrđen uslov, bez prelaznog prozora; HOLD ostaje uključen.

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

**Oznake i vrijeme pobude.** Rani prozori označeni kao ton ostaju ispod
praga. Bilješke navode kasnije pojačanje, bez precizne vremenske oznake.
Zato tri uzastopna pouzdana prekoračenja opisuju pravilo ulaska u alarm,
a ne izmjereno kašnjenje od 30 s od početka tona.

Oznaka `recovery_after_tone` ne potvrđuje da je zvučnik tada utišan.
Veliki dio tog bloka ostaje na visokim ocjenama. Kasniji pad ispod ulaznog,
ali iznad izlaznog praga vidljiv je u CSV-u; sam pad ne određuje tačan
trenutak gašenja izvora. Završni oporavak i njegovo kašnjenje nisu izmjereni.

---

## 4. Kako lanac odluke radi u ovoj verziji

```
WAIT → SETTLE → CENTER_LEARNING (10 prozora, zatim K1)
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
- **Kapija pouzdanosti** se primjenjuje na ocjene iznad ulaznog praga; njena granica se izvodi po sesiji kao
  `max(10 CAL normal-only subsegment_instability) × 1,25`. HOLD suspenduje
  gradnju alarma, **ne briše** aktivan alarm i **ne mijenja** profil. Šest
  uzastopnih HOLD prozora daju `OBSERVATION_HOLD_WARNING`.
- **Alarm** traži 3 uzastopna pouzdana prozora iznad `enter` praga
  (`asd-events-v1.1.0-development`, `min_consecutive=3`), a gasi se na ili ispod
  `exit` praga.
- **Trajnost**: na dvanaestom mjerenom alarmnom prozoru, uključujući ulaz (HOLD pauzira brojanje), emituje se
  `ANOMALY_SUSTAINED`. Stanje ostaje `ANOMALY`.

**„Kvar" nije akustička kategorija.** Terminalno stanje koje panel prikazuje kao
problem rezervisano je za grešku senzora ili toka (`AUDIO_TIMEOUT`,
`NONFINITE`, `PRESENCE_LOST`, `VERIFY_NORMAL_REJECT`). Dugotrajna akustička
promjena se prijavljuje kao `ANOMALY` + `ANOMALY_SUSTAINED`, sa oznakom događaja
`UNKNOWN_CHANGE`. To je namjerno: jedan mikrofon može potvrditi da se promjena
održava, ali ne može dokazati mehanički uzrok.

---

Kompletan vođeni postupak traje oko 13,57 min od virtuelnog tastera do nadzora u obje sesije. Deset CAL, 44 DERIVE i 22 VERIFY prozora daju najmanje 760 s zvuka prije čekanja i ostalog troška.

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

Radna verzija ostaje sačuvana. GUIDED25 FAIL, neizmjeren završni oporavak,
ponovljivost kalibracije i kratki uzorci ostaju ograničenja. Ručna pobuda nije
izolovana kao jedini uzrok promašaja. Potpuno samostalan interfejs, prekid I2S,
power-loss i potrošnja cijelog lanca nisu potvrđeni. Dodatna mjerenja se ne
podrazumijevaju kao uslov za završetak dokumentovanja postojećih rezultata.

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
