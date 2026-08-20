# Dorada poslije FAN01 — Faza 2: multi-session host

**Datum:** 16.08.2026.  
**Implementacioni status:** završeno u kodu i PC replay testovima.  
**Hardverski status:** nije ponovo flashovano niti provjereno na ventilatoru;
to je namjerno ostavljeno za naredni, kraći fizički prolaz.

## 1. Zašto je dorada bila potrebna

Host je ranije praktično tretirao cijeli proces kao jednu firmware sesiju.
Poslije urednog K1 pada (`loo_cv > 0,6`) završio bi capture ili bi naredni
`WAIT` poredio sa brojačem prethodne sesije. Time nova kalibracija u istom host
runu nije bila pouzdano auditabilna. Isto tako, firmware-local `DET window=1`
nije bilo moguće jednoznačno razlikovati od `window=1` naredne sesije.

Faza 2 uvodi eksplicitan ugovor: PC proces je **run**, a svaki par `SESSION
STARTED ... SESSION ENDED` je zasebna **firmware sesija**.

## 2. Razdvojeno stanje

`pc/tools/physical_fan_experiment.py` sada ima dva opsega u istom strogo
provjeravanom trackeru:

| Run-scope, nikad se ne resetuje na `SESSION STARTED` | Session-scope, resetuje se |
|---|---|
| boot handshake | WAIT/CAL/CAL_SUMMARY/DET brojači |
| `run_quality_counts` i `run_det_records` | `wait_ok_count`, `cal_summary` |
| broj otvorenih/zatvorenih sesija | ADAPTTHR/PRESENCE/TEMPORAL i pragovi |
| `session_history` | K1 acceptance/rejection parovi |
| COM i provenance u artefaktu | DET window, alarm total i temporalno stanje |
| prethodno zatvoreni audit zapisi | terminal drain i lokalni state-chain anchor |

Na početku svake sesije state-chain se ponovo otvara iz `NO_MACHINE` i traži se
tačno jedan novi `BOOT_FAIL_CLOSED` neposredno poslije `SESSION STARTED`.
Firmware ga emituje unutar svakog `run_session()`. Host čuva zbirni run-scope
dokaz i broj BOOT zapisa, ali resetuje session-local `session_boot_seen`.
Operatorov condition se nezavisno vraća na `unconfirmed`; ne može se naslijediti
iz prethodne sesije.

K1-odbijena sesija poslije odgovarajućih `STATE`, `FLOW_STOPPED` i `SESSION
ENDED` ostaje u `session_history` kao validan `calibration_rejected` audit bez
DET metrika. Host zatim nastavlja da čita UART i može prihvatiti novu sesiju.
Bounded terminal drain iz Faze 1 ostaje aktivan: nedostajući `SESSION ENDED`
i dalje završava fail-closed timeoutom.

## 3. Novi artifact contract i CSV identitet

Novi v1.7 artefakt eksplicitno nosi:

```text
protocol_version=physical-fan-v1.7.0
quality_protocol_version=asd-quality-v1.4.0
artifact_contract_version=physical-fan-artifacts-v1.7.0
```

Offline reader radi fail-closed:

- istorijski v1.6 prihvata samo par `physical-fan-v1.6.0` ↔
  `asd-quality-v1.3.0` i dobija kompatibilne podrazumijevane indekse jedine
  sesije;
- v1.7 prihvata samo par v1.7 ↔ v1.4 uz tačan artifact contract token;
- missing, nepoznat ili nepodudaran par/token odbija čitanje.

Session-vezani CSV redovi nose `firmware_session_index`. `detections.csv`
dodatno čuva oba identiteta prozora:

- `window`: firmware-local broj, ponovo kreće od 1 u novoj sesiji;
- `run_det_index`: monotono raste kroz cijeli host run.

`events.csv` takođe veže host condition/note/fazu za trenutni session index;
run događaji prije prve sesije imaju indeks 0.

## 4. Metrike bez miješanja sesija

`provenance.json` i `SUMMARY.md` sada imaju tabelu po firmware sesiji i zbir za
cijeli run:

- protocol status i K1 acceptance;
- raw DET, protocol-valid DET i DET prozori podobni za metrike;
- alarmni prozori, alarm entries i alarmne epizode;
- procenat podobnih prozora proveden u alarmu;
- medijanu latencije od posljednjeg alarmnog prozora do prvog normalnog;
- broj izuzetih transition prozora;
- session i run DET totals i provjeru saglasnosti sa CSV redovima.

Alarmni prozori se namjerno ne predstavljaju kao epizode. Npr. tri uzastopna
alarmna prozora su tri alarmna prozora, ali jedna alarmna epizoda. Prvi DET
poslije nove `condition` komande dobija `transition_window=1` i isključuje se iz
metrika, jer desetosekundni prozor može sadržati oba uslova.

K1-odbijena sesija ostaje u session tabeli, ali ne daje metric rows. Valjan run
može nastati tek iz kasnije prihvaćene, kompletne sesije sa ponovo potvrđenim
operator conditionom.

## 5. Provenance hash opseg

Pored ranijih izvora, hash manifest eksplicitno obuhvata:

```text
firmware/esp32s3_asd/main/asd_temporal.c/.h
firmware/esp32s3_asd/main/asd_cmd.c/.h
pc/config/asd_temporal_policy_v2.json
pc/config/asd_commissioning_policy_v1.json
firmware/esp32s3_asd/main/asd_calibration_quality.c/.h
pc/config/asd_interference_policy_v1.json
firmware/esp32s3_asd/main/asd_interference.c/.h
```

Budući policy/modul je naveden i prije nastanka; hash je `null` dok fajl ne
postoji. Tako odsustvo nije prećutano, a kasnije pojavljivanje automatski ulazi
u audit bez promjene semantike starog artefakta.

## 6. `start_fan_run.py` montažna potvrda

Ispravljena je netačna tvrdnja da `--montaza-potvrdio` ide u `events.csv`.
Wrapper je prosljeđuje kao `--notes`, pa stvarna putanja glasi:

```text
provenance.json -> metadata.operator_notes
```

Konzolni ispis ostaje. Dodan je čisti `build_tool_command()` i test koji
provjerava doslovan prenos potvrde i dokumentovanu putanju.

## 7. Verifikacioni replay

Najvažniji test koristi doslovne UART linije i izvodi cio tok:

1. po jedan `BOOT_FAIL_CLOSED` odmah poslije `SESSION STARTED` u svakoj sesiji;
2. sesija 1: puni `WAIT 1..60`, `CAL 1..10`, K1 pad, terminalni par i
   `SESSION ENDED`;
3. sesija 2: ponovo `WAIT 1..60` (ne 61), `CAL 1..10`, ADAPTTHR, PRESENCE,
   TEMPORAL, acceptance par i tri DET prozora;
4. condition iz prve sesije se ne nasljeđuje: prvi DET druge sesije je
   `unconfirmed`;
5. nova condition prije DET 2 čini DET 2 transition prozorom; DET 3 je prvi
   podoban metric row;
6. `SESSION ENDED`, operator stop i provjera svih CSV/provenance/summary
   brojača.

Targetirani rezultat prije punog suitea:

```text
90 passed in 2.61s
```

Puni regresioni prolaz:

```powershell
.\.venv\Scripts\python.exe -m pytest pc\tests -q
```

```text
328 passed in 9.62s
```

Firmware izvor u Fazi 2 nije mijenjan, pa ESP-IDF rebuild nije ponavljan samo
zbog host/CSV/docs promjene. Firmware build iz Faze 1 ostaje zaseban dokaz; nije
dokaz flasha ni fizičkog runtimea.

Stvarni istorijski `cold-start-04` pročitan je ponovo bez pisanja artefakta:

```text
result_status=calibration_rejected:loo_cv_above_max
protocol_valid=True
metrics_eligible=False
firmware_sessions=1
run_det_records=52
```

Originalni `SUMMARY.md` ostao je na SHA-256
`AF9B3E3E22267FE29CD1F391D688EBC814FA0F6DAE1B4FFD88C163A819F8EC24`;
privremeni verifikacioni sidecar je uklonjen i ne ostaje u run direktoriju.

## 8. Šta ovo još ne dokazuje

Ova faza dokazuje parser, state machine, bounded drain, artifact compatibility,
CSV identitet i izvještavanje na PC-u. Ne dokazuje:

- da je novi firmware flashovan na ESP32-S3;
- da dvije stvarne sesije rade bez USB/serijskog problema;
- da su prag ili razlika papirić/govor/normalan fan poboljšani;
- da su tonalnost i dvostepena odluka završeni.

To pripada narednim fazama i kratkom fizičkom testu nakon softverskih dorada.
