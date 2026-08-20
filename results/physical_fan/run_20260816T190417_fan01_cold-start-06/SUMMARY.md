# Stvarni fizicki fan eksperiment

- Status: `invalid_firmware_telemetry`
- Validan fizički rezultat: **NE**
- Protokol: `physical-fan-v1.6.0`
- Fan ID: `fan01`
- Sesija: `cold-start-06`
- Port: `COM3` @ 115200 baud
- Udaljenost: 20.0 cm
- Prostorija: soba
- Prag: 743.83667
- DET prozora: 15
- Validnih DET prozora za metrike: 0
- Protocol-valid DET prozora: 15
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 15
- Alarmnih validnih DET prozora: 0
- Najveci prijavljeni `dropped`: 474112

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| (nema DET podataka) | 0 | 0 | - | - |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.047 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.500 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `33.922 s` **virtual_button / press**: panel
- `49.297 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `149.344 s` **phase / detection**: firmware DET faza; operator condition i dalje nije potvrđen
- `179.860 s` **virtual_button / hold**: panel
- `222.547 s` **virtual_button / hold**: panel
- `292.000 s` **note / operator**: virtuelni taster hold -> COM4
- `299.000 s` **protocol / invalid_firmware_telemetry**: SESSION_ENDED_without_START
