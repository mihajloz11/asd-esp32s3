# Stvarni fizicki fan eksperiment

- Status: `invalid_firmware_telemetry`
- Status fizičkog rezultata: `run_status:invalid_firmware_telemetry`
- Validan fizički rezultat: **NE**
- Protokol izvještaja: `physical-fan-v1.8.0`
- Izvorni protokol artefakta: `physical-fan-v1.8.0`
- Firmware protokol validan i kompletan: **NE**
- Kalibracija prihvaćena (K1): **NE** (`missing_cal_summary`; politika `asd-commissioning-policy-v1.0.0`)
- Prozori podobni za metrike: **NE**
- Fan ID: `fan02`
- Sesija: `guided25-202608212101`
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
| 1 | invalid_firmware_telemetry (invalid) | missing_cal_summary | 0/0 | 0/0 | 0.00 | - | 0 |

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| (nema DET podataka) | 0 | 0 | - | - |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora i prihvaćene K1 kalibracije ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.016 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.469 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `92.156 s` **virtual_button / guided25**: panel
- `92.172 s` **virtual_button / press**: panel
- `92.172 s` **virtual_button / guided25**: panel
- `92.187 s` **virtual_button / press**: panel
- `94.281 s` **protocol / invalid_firmware_telemetry**: terminal_STATE_reason_unknown
