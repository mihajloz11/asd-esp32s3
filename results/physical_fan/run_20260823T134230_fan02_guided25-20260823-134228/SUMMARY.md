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
- Sesija: `guided25-20260823-134228`
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

- `0.000 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.453 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `32.016 s` **virtual_button / guided25**: panel
- `32.016 s` **virtual_button / press**: panel
- `87.375 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `187.953 s` **protocol / terminal_drain_complete**: terminal STATE/FLOW_STOPPED/SESSION ENDED sacuvani
- `187.953 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `187.985 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `187.985 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `192.907 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `197.922 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `202.922 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `207.938 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `212.953 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `217.969 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `222.969 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `227.985 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `232.985 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `238.000 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `243.016 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `248.016 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `253.032 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `258.032 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `263.047 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `268.063 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `273.078 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `278.078 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `283.094 s` **calibration / rejected**: session=1; UNSTABLE_CALIBRATION; K1 loo_cv_above_max; host ostaje aktivan za novu sesiju
- `286.110 s` **session / abort**: operator_panel_abort
