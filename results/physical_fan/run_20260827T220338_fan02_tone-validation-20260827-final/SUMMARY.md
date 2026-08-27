# Stvarni fizicki fan eksperiment

- Status: `completed_by_operator`
- Status fizičkog rezultata: `valid_physical_result`
- Validan fizički rezultat: **DA**
- Protokol izvještaja: `physical-fan-v1.9.0`
- Izvorni protokol artefakta: `physical-fan-v1.9.0`
- Firmware protokol validan i kompletan: **DA**
- Kalibracija prihvaćena (K1): **DA** (`accepted`; politika `asd-commissioning-policy-v1.0.0`)
- Prozori podobni za metrike: **DA**
- Fan ID: `fan02`
- Sesija: `tone-validation-20260827-final`
- Port: `COM3` @ 115200 baud
- Udaljenost: 40.0 cm
- Prostorija: soba
- Prag: 21809.5059
- DET prozora: 115
- Validnih DET prozora za metrike: 99
- Condition+protocol validnih DET kandidata: 99
- Protocol-valid DET prozora: 115
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 16
- Alarmnih validnih DET prozora: 64
- Firmware sesija: 1
- Run DET total (tracker/CSV): 115/115
- Alarmnih prozora / ulazaka / epizoda: 64 / 2 / 2
- Vrijeme u alarmu: 64.65%
- Medijana oporavka: nije izmjerena s
- Isključenih prelaznih prozora: 3
- Najveci prijavljeni `dropped`: 0

## Rezultati po firmware sesiji

| Sesija | Protokol | K1 | DET raw/metric | Alarm prozori/epizode | Alarm % | Oporavak s | Prelazni isključeni |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | accepted (valid) | accepted | 115/99 | 64/2 | 64.65 | - | 3 |

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| normal_baseline | 5 | 0 | 7085.269 | 6711.745..8171.274 |
| constant_tone_1khz | 44 | 14 | 23573.911 | 7326.984..87151.586 |
| recovery_after_tone | 50 | 50 | 33169.562 | 12266.021..127539.258 |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora i prihvaćene K1 kalibracije ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.031 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.468 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `32.047 s` **virtual_button / guided25**: panel
- `32.047 s` **virtual_button / press**: panel
- `87.390 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `846.312 s` **phase / detection**: firmware DET faza; operator condition i dalje nije potvrđen
- `982.156 s` **condition / normal_baseline**: Zavrsna provjera tona: cista normalna osnova prije pustanja.
- `1040.578 s` **condition / constant_tone_1khz**: Konstantni YouTube 1 kHz ton; fiksna jacina i polozaj.
- `1491.578 s` **condition / recovery_after_tone**: Konstantni ton ugasen; provjera povratka u normalu.
- `2000.250 s` **session / stop**: kraj zavrsne provjere konstantnog tona
- `2000.375 s` **session / final_buffer_drain_complete**: buffered UART je procitan prije finalizacije; trajanje=0.125 s; paket_jos_otvoren=0
