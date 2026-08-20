# Review Faze 1 i Faze 2 dorade (necommit-ovan rad) — 18.08.2026.

**Status:** analiza završena, popravke NISU primijenjene.
**Razlog:** čeka se da se završi ostatak plana
(`docs/PLAN-DORADA-POSLIJE-FAN01.md`, faze 3–9) prije nego što se radi jedan fix-pass,
umjesto popravljanja komad po komad dok se plan još izvodi.
**Opseg pregleda:** `git diff HEAD` u trenutku pisanja — necommit-ovana implementacija
Faze 1 (K1 fail-closed gate, `docs/DORADA-FAZA1-K1-2026-08-16.md`) i Faze 2
(multi-session host, `docs/DORADA-FAZA2-MULTI-SESSION-2026-08-16.md`).

## Metodologija

`/code-review high` — 8 nezavisnih agenata (3 correctness ugla + reuse + simplification +
efficiency + altitude + conventions), pa 1-vote verifikacija svakog kandidata preko
zasebnog agenta. Od 10 verifikovanih kandidata: 9 potvrđeno (CONFIRMED), 1 oboreno
(REFUTED).

## Opšti zaključak

Plan i arhitektura K1 gate-a i multi-session tracking-a su solidni — `pytest pc/tests`
prolazi (331 passed), `asd_calibration_quality.c/.h` je pažljivo napisan (npr.
zaokruživanje `loo_cv` na 6 decimala da se izbjegne float32/double ULP neslaganje
firmware↔host na granici praga). ESP-IDF build nije lokalno provjeren (nema `idf.py` na
ovoj Windows mašini). Nijedan stari `results/physical_fan/` artefakt nije dirnut.

Nađenih 9 potvrđenih problema — nijedan nije rušilački, ali #1–#3 direktno tiču integritet
podataka/audit trail bitan za odbranu teze.

## Potvrđeni nalazi (rangirano po ozbiljnosti)

### 1. Duplikat `run_det_index` kad DET red padne semantičku validaciju
**Fajl:** `pc/tools/physical_fan_experiment.py:2739-2755` (upis reda), inkrement u
DET grani `transition_firmware_protocol` (~1891-1896).

`run_det_records` (izvor za `run_det_index`) inkrementira se tek NAKON
`_det_semantic_error()` early-return provjere (npr. threshold ≠ ADAPTTHR, negativan
score). CSV red se ipak gradi i piše bezuslovno (`detections.append(row)` /
`det_writer.writerow(row)`), pa nevalidan DET red dobije isti `run_det_index` kao
prethodni validan red. Krši dokumentovanu jedinstvenost ključa
`detection_keys=["firmware_session_index","window","run_det_index"]` iz
`provenance.json`. Efektivno je to jednokratni duplikat na kraju runa (loop odmah
poslije prekida čitanje), ne kontinuirani problem.

**Popravka:** ili ne pisati red u `detections.csv` kad `semantic_error` postoji, ili
dodijeliti `run_det_index` PRIJE poziva `transition_firmware_protocol`/nezavisno od
uspjeha validacije.

### 2. Provenance hash nikad ne pokriva stvarni `asd_temporal_policy_v1.json`
**Fajl:** `pc/tools/physical_fan_experiment.py:86-90` (`RELEVANT_FILES`).

Lista sadrži `pc/config/asd_temporal_policy_v2.json` (ne postoji na disku — typo u
verziji) umjesto stvarnog, aktivno učitanog i korišćenog `asd_temporal_policy_v1.json`
(učitava se i koristi za validaciju oko linije ~101-104). `sha256_file()` tiho vraća
`None` za fajl koji ne postoji (bez upozorenja), pa `provenance.json` ima
`source_sha256["...v2.json"]=null`, a fajl koji STVARNO upravlja temporalnim
odlukama nikad ne uđe u hash manifest. Test
`test_phase2_provenance_hash_scope_is_explicit_even_for_future_files` provjerava samo
članstvo u `RELEVANT_FILES`, ne i da li putanje postoje — ne hvata ovo.

**Popravka:** ispraviti `v2` → `v1` u `RELEVANT_FILES` (ili dodati v1 pored v2 ako je v2
zaista namijenjen za budući fajl per Faza 2 dokument).

### 3. Prag K1 `0,6` hardkodovan na dva mjesta — krši sopstveno pravilo iz plana
**Fajlovi:** `firmware/esp32s3_asd/main/asd_calibration_quality.h:15`
(`#define ASD_CALIBRATION_MAX_LOO_CV 0.6f`) i
`pc/config/asd_commissioning_policy_v1.json:4` (`"max_loo_cv": 0.6`).

`docs/PLAN-DORADA-POSLIJE-FAN01.md:305` eksplicitno zabranjuje baš ovo: *"Ne kopirati
`0,6` na više mjesta bez jednog verzionisanog izvora politike."* Jedina sinhronizacija
je `pc/tests/test_asd_calibration_quality_c.py::test_c_policy_matches_versioned_pc_policy`,
koji se **preskače** (`pytest.skip`) ako nema `gcc`/`clang` na mašini. Postojeći
`pc/tools/check_schema_consistency.py` (već ožičen u CI) provjerava slične parove
firmware `#define` ↔ JSON, ali NIJE proširen za ovaj novi par.

**Popravka:** dodati ovaj par u `check_schema_consistency.py`, ili generisati C header iz
JSON-a u build koraku.

### 4. Fabrikovana recovery-latency statistika (10,0 s fallback)
**Fajl:** `pc/tools/physical_fan_experiment.py:899-904` (`detection_metrics`).

Kad `elapsed_s` ne može da se parsira kao float u trenutku zatvaranja alarmne epizode,
kod ubacuje fiksnih `10.0` sekundi umjesto da izuzme uzorak. Realno dostižno kroz
`--recompute-summary` na oštećenom/ručno mijenjanom `detections.csv`
(`events.csv` put pored njega FORSIRA cast i pukao bi na lošem podatku — asimetrija).
Rezultat: tiho pogrešna "Medijana oporavka" u `SUMMARY.md` bez ikakvog signala da je
ulaz nepotpun.

**Popravka:** izuzeti uzorak iz `recovery_latencies` (ili ga eksplicitno označiti kao
`None`/nedostupan) umjesto fallback vrijednosti.

### 5. Status cijelog runa zavisi samo od poslednje sesije
**Fajl:** `pc/tools/physical_fan_experiment.py:738` (`firmware_protocol_complete`,
session-scope funkcija) korišćena kao jedini run-level gate na liniji `~2866`.

Ako sesija 1 potpuno i validno završi (K1 prihvaćen, DET podaci), a operater onda
pokrene sesiju 2 i prekine je prije kraja WAIT/CAL, `firmware_protocol_complete`
procjenjuje SAMO sesiju 2 (nedovršenu) → run status se forsira na
`"invalid_missing_telemetry"`, iako `session_history`/`evaluate_run_validity`-eva
`session_summaries` tabela i dalje sadrži validne podatke sesije 1.
`evaluate_run_validity` ima nezavisnu provjeru (`all(item["protocol_complete"] ...)`)
koja dolazi do istog "invalid" zaključka — podaci nisu izgubljeni, samo je vrhovni
status zbunjujuć za nekoga ko ne otvori per-session tabelu.

**Popravka (opciono, nije nužno bag nego dizajn-odluka za preispitati):** ili
eksplicitno dokumentovati da "run" znači "sve sesije unutar njega moraju biti
kompletne", ili dodati poseban status (npr. `partial_valid_sessions`) kad postoji bar
jedna validna sesija unutar inače nevalidnog runa.

### 6. `stop` komanda pogrešno etiketira ne-K1 prekide kao "aborted_before_detection"
**Fajl:** `pc/tools/physical_fan_experiment.py:2565-2578`.

Samo `protocol_status=="calibration_rejected"` (K1) dobija poseban label
`"completed_calibration_rejected"`. Svaki drugi dokumentovan terminalni prekid
(`SENSOR_ERROR`, `RECALIBRATION_REQUIRED`, ...) pada u generičku granu
`"aborted_before_detection"`, kao da je operater bez razloga prekinuo, iako je
`protocol_status="invalid_firmware_terminal"` — dokumentovan i auditabilan uzrok.

**Popravka:** izvesti label generički iz `protocol_status`/`invalid_reason` umjesto
`if/elif` samo za K1 slučaj.

### 7. Run-level razlog odbijanja pokazuje samo poslednju sesiju
**Fajl:** `pc/tools/physical_fan_experiment.py:~998` (`evaluate_run_validity`).

Kad nijedna sesija u runu nije K1-prihvaćena, `calibration_acceptance_reason` na
run-nivou uzima se iz `session_summaries[-1]` — samo poslednje sesije. Ako sesija 1
padne sa `nonfinite_loo_cv` (potencijalni firmware/UART bug — akcionabilno), a sesija 2
sa običnim `loo_cv_above_max`, run-level izvještaj pokazuje samo ovaj drugi, benigniji
razlog.

**Popravka:** agregirati sve distinct razloge iz `session_summaries`, ne samo poslednji.

### 8. `calibration_acceptance()` ne odbacuje `bool` kao tip za `loo_cv`
**Fajl:** `pc/asd/commissioning_policy.py:42-47`.

`float(cal_summary["loo_cv"])` prolazi i za `bool` (Python `bool` je podklasa `int`-a),
pa bi `False` prošao kao `0.0` (validna kalibracija) umjesto da bude odbijen kao
pogrešan tip. **Trenutno nedostižno** — oba stvarna pozivaoca uvijek grade `loo_cv` iz
`float()`-castovanog regex-parsiranog UART stringa. Defense-in-depth propust, ne aktivan
bag.

**Popravka (niska prioritet):** dodati `isinstance(value, bool)` provjeru prije
`float()`.

### 9. Dva različita C razloga greške mapiraju na isti string
**Fajl:** `firmware/esp32s3_asd/main/asd_calibration_quality.c:44`.

`asd_calibration_quality_reason_name()` vraća `"INVALID_ARGUMENT"` i za
`ASD_CALIBRATION_QUALITY_NEGATIVE_METRIC` i za `ASD_CALIBRATION_QUALITY_INVALID_ARGUMENT`.
**Trenutno nedostižno** — jedini pozivalac (`stop_unstable_calibration` u `psd_live.c`)
poziva ga samo za `UNSTABLE`, a `NEGATIVE_METRIC` fizički ne može nastati jer su
`loo_mean/loo_sd/loo_cv/loo_range` unaprijed clamp-ovani na non-negative. Untested
(nijedan test ne zove `reason_name()` za `NEGATIVE_METRIC`).

**Popravka (niska prioritet):** `return "NEGATIVE_METRIC";` na liniji 44, plus test koji
to pinuje.

## Oboreno u verifikaciji (ne popravljati)

**"`drain_required` se nikad ne resetuje za ne-K1 terminalne prekide → duplirani
`terminal_drain_complete` eventi"** — inicijalni nalaz altitude-agenta. Verifikator je
pokazao da svaki ne-K1 terminalni put ide kroz `_invalidate(..., drain=True)`, koji
zatim vodi u `break` iz cijele `while True` serial-read petlje — dakle nema "sljedećih
linija" na kojima bi se ponovo okinulo. Test
`test_stop_drains_buffered_terminal_telemetry_and_bad_condition_does_not_crash` to
potvrđuje. **Nema akcije.**

## Šta nije ni počelo

Faze 3–9 iz `docs/PLAN-DORADA-POSLIJE-FAN01.md`: razvojna telemetrija (96-dim
sidecar), PC normal-only commissioning laboratorija, novi firmware state machine
(`SETTLE → CENTER_LEARNING → COMMISSION_DERIVE → COMMISSION_VERIFY → MONITORING`), HOLD
odluka bez lažne `AMBIENT_NOISE` dijagnoze, audio liveness/total-timeout, NVS profil,
finalna dokumentaciona korekcija. Ništa od toga nije dirano u ovom radnom stanju.

## Sljedeći korak

Kad se završi ostatak plana (ili eksplicitno stane i zatraži pregled), proći kroz
nalaze 1–9 iznad i primijeniti popravke prije commit-a. Prioritet: #1, #2, #3 (integritet
podataka i audit trail), zatim #4–#7, #8–#9 su nice-to-have.
