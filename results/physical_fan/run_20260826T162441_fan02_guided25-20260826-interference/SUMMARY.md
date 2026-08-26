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
- Sesija: `guided25-20260826-interference`
- Port: `COM3` @ 115200 baud
- Udaljenost: 40.0 cm
- Prostorija: soba
- Prag: 2832.83325
- DET prozora: 68
- Validnih DET prozora za metrike: 0
- Condition+protocol validnih DET kandidata: 37
- Protocol-valid DET prozora: 68
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 68
- Alarmnih validnih DET prozora: 0
- Firmware sesija: 1
- Run DET total (tracker/CSV): 68/68
- Alarmnih prozora / ulazaka / epizoda: 0 / 0 / 0
- Vrijeme u alarmu: 0.00%
- Medijana oporavka: nije izmjerena s
- Isključenih prelaznih prozora: 10
- Najveci prijavljeni `dropped`: 0

## Rezultati po firmware sesiji

| Sesija | Protokol | K1 | DET raw/metric | Alarm prozori/epizode | Alarm % | Oporavak s | Prelazni isključeni |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | accepted (valid) | accepted | 68/0 | 0/0 | 0.00 | - | 10 |

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| (nema DET podataka) | 0 | 0 | - | - |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora i prihvaćene K1 kalibracije ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.000 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.453 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `33.031 s` **virtual_button / guided25**: panel
- `33.047 s` **virtual_button / press**: panel
- `88.328 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `847.234 s` **phase / detection**: firmware DET faza; operator condition i dalje nije potvrđen
- `1063.875 s` **condition / normal_baseline**: Normalna osnova: Miruj i ne pricaj.
- `1113.703 s` **condition / airflow_change_paper_1**: Papiric 1: Drzi papiric uz usis, bez dodira ventilatora.
- `1163.843 s` **condition / recovery_normal_1**: Oporavak 1: Skloni papiric i ruku; tisina.
- `1213.640 s` **condition / airflow_change_paper_2**: Papiric 2: Ponovi isti polozaj papirica.
- `1263.578 s` **condition / recovery_normal_2**: Oporavak 2: Skloni papiric i ruku; tisina.
- `1313.468 s` **condition / airflow_change_paper_3**: Papiric 3: Treci put ponovi isti polozaj.
- `1363.500 s` **condition / recovery_normal_3**: Oporavak 3: Skloni papiric i ruku; tisina.
- `1414.281 s` **condition / ambient_speech**: Razgovor: Pricaj normalno sa oznacenog mjesta.
- `1464.328 s` **condition / recovery_after_speech**: Oporavak poslije govora: Prestani da pricas; tisina.
- `1514.203 s` **condition / ambient_door**: Vrata: Jednom normalno otvori i zatvori vrata; ne lupaj.
- `1534.109 s` **session / abort**: guided25_hard_deadline
