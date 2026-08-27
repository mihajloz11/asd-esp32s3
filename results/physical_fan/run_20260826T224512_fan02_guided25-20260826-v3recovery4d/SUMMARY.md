# Stvarni fizicki fan eksperiment

- Status: `aborted_by_operator`
- Status fizičkog rezultata: `run_status:aborted_by_operator`
- Validan fizički rezultat: **NE**
- Protokol izvještaja: `physical-fan-v1.9.0`
- Izvorni protokol artefakta: `physical-fan-v1.9.0`
- Firmware protokol validan i kompletan: **DA**
- Kalibracija prihvaćena (K1): **DA** (`accepted`; politika `asd-commissioning-policy-v1.0.0`)
- Prozori podobni za metrike: **NE**
- Fan ID: `fan02`
- Sesija: `guided25-20260826-v3recovery4d`
- Port: `COM3` @ 115200 baud
- Udaljenost: 40.0 cm
- Prostorija: soba
- Prag: 3599.81665
- DET prozora: 13
- Validnih DET prozora za metrike: 0
- Condition+protocol validnih DET kandidata: 9
- Protocol-valid DET prozora: 13
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 13
- Alarmnih validnih DET prozora: 0
- Firmware sesija: 1
- Run DET total (tracker/CSV): 13/13
- Alarmnih prozora / ulazaka / epizoda: 0 / 0 / 0
- Vrijeme u alarmu: 0.00%
- Medijana oporavka: nije izmjerena s
- Isključenih prelaznih prozora: 3
- Najveci prijavljeni `dropped`: 0

## Rezultati po firmware sesiji

| Sesija | Protokol | K1 | DET raw/metric | Alarm prozori/epizode | Alarm % | Oporavak s | Prelazni isključeni |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | accepted (valid) | accepted | 13/0 | 0/0 | 0.00 | - | 3 |

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| (nema DET podataka) | 0 | 0 | - | - |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora i prihvaćene K1 kalibracije ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.047 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.500 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `17.032 s` **virtual_button / guided25**: panel
- `17.047 s` **virtual_button / press**: panel
- `72.391 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `831.313 s` **phase / detection**: firmware DET faza; operator condition i dalje nije potvrđen
- `847.313 s` **condition / normal_baseline**: Normalna osnova: Miruj i ne pricaj.
- `897.391 s` **condition / airflow_change_paper_1**: Papiric 1: Drzi papiric uz usis, bez dodira ventilatora.
- `948.063 s` **condition / recovery_normal_1**: Oporavak 1: Skloni papiric i ruku; tisina.
- `969.110 s` **session / abort**: operator_panel_abort
