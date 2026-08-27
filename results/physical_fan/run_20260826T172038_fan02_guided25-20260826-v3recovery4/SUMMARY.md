# Stvarni fizicki fan eksperiment

- Status: `invalid_firmware_terminal`
- Status fizičkog rezultata: `run_status:invalid_firmware_terminal`
- Validan fizički rezultat: **NE**
- Protokol izvještaja: `physical-fan-v1.9.0`
- Izvorni protokol artefakta: `physical-fan-v1.9.0`
- Firmware protokol validan i kompletan: **NE**
- Kalibracija prihvaćena (K1): **DA** (`accepted`; politika `asd-commissioning-policy-v1.0.0`)
- Prozori podobni za metrike: **NE**
- Fan ID: `fan02`
- Sesija: `guided25-20260826-v3recovery4`
- Port: `COM3` @ 115200 baud
- Udaljenost: 40.0 cm
- Prostorija: soba
- Prag: 1051.74402
- DET prozora: 18
- Validnih DET prozora za metrike: 0
- Condition+protocol validnih DET kandidata: 0
- Protocol-valid DET prozora: 18
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 18
- Alarmnih validnih DET prozora: 0
- Firmware sesija: 1
- Run DET total (tracker/CSV): 18/18
- Alarmnih prozora / ulazaka / epizoda: 0 / 0 / 0
- Vrijeme u alarmu: 0.00%
- Medijana oporavka: nije izmjerena s
- Isključenih prelaznih prozora: 0
- Najveci prijavljeni `dropped`: 0

## Rezultati po firmware sesiji

| Sesija | Protokol | K1 | DET raw/metric | Alarm prozori/epizode | Alarm % | Oporavak s | Prelazni isključeni |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | invalid_firmware_terminal (invalid) | accepted | 18/0 | 0/0 | 0.00 | - | 0 |

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| (nema DET podataka) | 0 | 0 | - | - |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora i prihvaćene K1 kalibracije ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.015 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.468 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `33.046 s` **virtual_button / guided25**: panel
- `33.046 s` **virtual_button / press**: panel
- `88.343 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `847.281 s` **phase / detection**: firmware DET faza; operator condition i dalje nije potvrđen
- `1036.812 s` **protocol / invalid_firmware_terminal**: quality_reject:DET:LOW_LEVEL_OBSERVATION
- `1036.859 s` **protocol / terminal_drain_complete**: terminal STATE/FLOW_STOPPED sacuvani
