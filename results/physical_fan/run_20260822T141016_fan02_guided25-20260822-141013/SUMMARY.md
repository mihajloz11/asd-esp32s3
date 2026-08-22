# Stvarni fizicki fan eksperiment

- Status: `invalid_research_telemetry`
- Status fizičkog rezultata: `run_status:invalid_research_telemetry`
- Validan fizički rezultat: **NE**
- Protokol izvještaja: `physical-fan-v1.8.0`
- Izvorni protokol artefakta: `physical-fan-v1.8.0`
- Firmware protokol validan i kompletan: **DA**
- Kalibracija prihvaćena (K1): **DA** (`accepted`; politika `asd-commissioning-policy-v1.0.0`)
- Prozori podobni za metrike: **NE**
- Fan ID: `fan02`
- Sesija: `guided25-20260822-141013`
- Port: `COM3` @ 115200 baud
- Udaljenost: 20.0 cm
- Prostorija: soba
- Prag: 4374.05859
- DET prozora: 65
- Validnih DET prozora za metrike: 0
- Condition+protocol validnih DET kandidata: 42
- Protocol-valid DET prozora: 65
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 65
- Alarmnih validnih DET prozora: 0
- Firmware sesija: 1
- Run DET total (tracker/CSV): 65/65
- Alarmnih prozora / ulazaka / epizoda: 0 / 0 / 0
- Vrijeme u alarmu: 0.00%
- Medijana oporavka: nije izmjerena s
- Isključenih prelaznih prozora: 11
- Najveci prijavljeni `dropped`: 0

## Rezultati po firmware sesiji

| Sesija | Protokol | K1 | DET raw/metric | Alarm prozori/epizode | Alarm % | Oporavak s | Prelazni isključeni |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | accepted (valid) | accepted | 65/0 | 0/0 | 0.00 | - | 11 |

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| (nema DET podataka) | 0 | 0 | - | - |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora i prihvaćene K1 kalibracije ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.032 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.485 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `168.344 s` **virtual_button / guided25**: panel
- `168.344 s` **virtual_button / press**: panel
- `223.657 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `982.563 s` **phase / detection**: firmware DET faza; operator condition i dalje nije potvrđen
- `1108.719 s` **condition / normal_baseline**: Normalna osnova: Miruj i ne pricaj.
- `1158.782 s` **condition / airflow_change_paper_1**: Papiric 1: Drzi papiric uz usis, bez dodira ventilatora.
- `1208.172 s` **condition / recovery_normal_1**: Oporavak 1: Skloni papiric i ruku; tisina.
- `1258.188 s` **condition / airflow_change_paper_2**: Papiric 2: Ponovi isti polozaj papirica.
- `1308.266 s` **condition / recovery_normal_2**: Oporavak 2: Skloni papiric i ruku; tisina.
- `1358.313 s` **condition / airflow_change_paper_3**: Papiric 3: Treci put ponovi isti polozaj.
- `1408.344 s` **condition / recovery_normal_3**: Oporavak 3: Skloni papiric i ruku; tisina.
- `1458.782 s` **condition / ambient_speech**: Razgovor: Pricaj normalno sa oznacenog mjesta.
- `1508.672 s` **condition / recovery_after_speech**: Oporavak poslije govora: Prestani da pricas; tisina.
- `1558.657 s` **condition / ambient_door**: Vrata: Jednom normalno otvori i zatvori vrata; ne lupaj.
- `1588.688 s` **condition / final_recovery**: Zavrsni oporavak: Miruj i ostavi ventilator da radi normalno.
- `1638.735 s` **session / stop**: kraj plana
- `1638.860 s` **session / final_buffer_drain_complete**: buffered UART je procitan prije finalizacije
