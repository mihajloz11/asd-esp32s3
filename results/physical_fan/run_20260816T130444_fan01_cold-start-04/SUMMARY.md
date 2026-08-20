# Stvarni fizicki fan eksperiment

- Status: `completed_by_operator`
- Validan fizički rezultat: **DA**
- Protokol: `physical-fan-v1.6.0`
- Fan ID: `fan01`
- Sesija: `cold-start-04`
- Port: `COM3` @ 115200 baud
- Udaljenost: 20.0 cm
- Prostorija: soba
- Prag: 6335.04297
- DET prozora: 52
- Validnih DET prozora za metrike: 51
- Protocol-valid DET prozora: 52
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 1
- Alarmnih validnih DET prozora: 38
- Najveci prijavljeni `dropped`: 1515520

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| normal_baseline | 51 | 38 | 12523.176 | 838.599..13715.827 |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.000 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.453 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `98.968 s` **virtual_button / press**: panel
- `114.343 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `214.375 s` **phase / detection**: firmware DET faza; operator condition i dalje nije potvrđen
- `227.390 s` **condition / normal_baseline**: Normalna osnova: Sjedi mirno. Ne pricaj, ne kucaj, ne prilazi ventilatoru.
- `738.937 s` **session / stop**: kalibracija odbacena po pravilu K1 (loo_cv 0.6275 > 0.6)
- `739.047 s` **session / final_buffer_drain_complete**: buffered UART je procitan prije finalizacije
