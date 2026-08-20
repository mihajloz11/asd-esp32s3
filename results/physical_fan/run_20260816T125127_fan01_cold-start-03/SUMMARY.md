# Stvarni fizicki fan eksperiment

- Status: `invalid_firmware_terminal`
- Validan fizički rezultat: **NE**
- Protokol: `physical-fan-v1.6.0`
- Fan ID: `fan01`
- Sesija: `cold-start-03`
- Port: `COM3` @ 115200 baud
- Udaljenost: 20.0 cm
- Prostorija: soba
- Prag: nije dobijen
- DET prozora: 0
- Validnih DET prozora za metrike: 0
- Protocol-valid DET prozora: 0
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 0
- Alarmnih validnih DET prozora: 0
- Najveci prijavljeni `dropped`: nije ispisan

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| (nema DET podataka) | 0 | 0 | - | - |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.016 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.469 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `126.969 s` **virtual_button / press**: panel
- `162.969 s` **virtual_button / press**: panel
- `256.547 s` **protocol / invalid_firmware_terminal**: quality_reject:WAIT:DROPPED_SAMPLES
- `256.594 s` **protocol / terminal_drain_complete**: terminal STATE/FLOW_STOPPED sacuvani
