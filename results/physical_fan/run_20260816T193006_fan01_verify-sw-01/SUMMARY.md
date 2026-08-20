# Stvarni fizicki fan eksperiment

- Status: `invalid_firmware_telemetry`
- Validan fizički rezultat: **NE**
- Protokol: `physical-fan-v1.6.0`
- Fan ID: `fan01`
- Sesija: `verify-sw-01`
- Port: `COM3` @ 115200 baud
- Udaljenost: 20.0 cm
- Prostorija: soba
- Prag: 40545.5742
- DET prozora: 3
- Validnih DET prozora za metrike: 0
- Protocol-valid DET prozora: 3
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 3
- Alarmnih validnih DET prozora: 0
- Najveci prijavljeni `dropped`: 107520

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| (nema DET podataka) | 0 | 0 | - | - |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.000 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.453 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `10.985 s` **virtual_button / press**: panel
- `26.360 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `126.344 s` **phase / detection**: firmware DET faza; operator condition i dalje nije potvrđen
- `147.328 s` **virtual_button / hold**: panel
- `156.235 s` **protocol / invalid_firmware_telemetry**: STATE_chain_mismatch:expected_from=CALIBRATED_NORMAL:got=NO_MACHINE
