# Stvarni fizicki fan eksperiment

- Status: `aborted_by_operator`
- Status fizičkog rezultata: `run_status:aborted_by_operator`
- Validan fizički rezultat: **NE**
- Protokol izvještaja: `physical-fan-v1.8.0`
- Izvorni protokol artefakta: `physical-fan-v1.8.0`
- Firmware protokol validan i kompletan: **DA**
- Kalibracija prihvaćena (K1): **NE** (`loo_cv_above_max`; politika `asd-commissioning-policy-v1.0.0`)
- Prozori podobni za metrike: **NE**
- Fan ID: `fan02`
- Sesija: `guided25-20260822-162922`
- Port: `COM3` @ 115200 baud
- Udaljenost: 20.0 cm
- Prostorija: soba
- Prag: nije dobijen
- DET prozora: 0
- Validnih DET prozora za metrike: 0
- Condition+protocol validnih DET kandidata: 0
- Protocol-valid DET prozora: 0
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 0
- Alarmnih validnih DET prozora: 0
- Firmware sesija: 1
- Run DET total (tracker/CSV): 0/0
- Alarmnih prozora / ulazaka / epizoda: 0 / 0 / 0
- Vrijeme u alarmu: 0.00%
- Medijana oporavka: nije izmjerena s
- Isključenih prelaznih prozora: 0
- Najveci prijavljeni `dropped`: 0

## Rezultati po firmware sesiji

| Sesija | Protokol | K1 | DET raw/metric | Alarm prozori/epizode | Alarm % | Oporavak s | Prelazni isključeni |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | calibration_rejected (valid) | loo_cv_above_max | 0/0 | 0/0 | 0.00 | - | 0 |

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| (nema DET podataka) | 0 | 0 | - | - |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora i prihvaćene K1 kalibracije ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.047 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.500 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `61.156 s` **virtual_button / guided25**: panel
- `61.156 s` **virtual_button / press**: panel
- `116.438 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `217.078 s` **protocol / terminal_drain_complete**: terminal STATE/FLOW_STOPPED/SESSION ENDED sacuvani
- `217.094 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `217.094 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `217.094 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `222.047 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `227.047 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `232.063 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `237.078 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `242.078 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `247.094 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `252.110 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `257.110 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `262.125 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `267.141 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `272.141 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `277.156 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `282.172 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `287.172 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `292.188 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `297.188 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `302.203 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `307.219 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `312.219 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `317.235 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `322.250 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `327.250 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `332.266 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `337.281 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `342.281 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `347.297 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `352.297 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `357.313 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `362.328 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `367.328 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `372.344 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `377.360 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `382.360 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `387.375 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `390.406 s` **session / abort**: operator_panel_abort
