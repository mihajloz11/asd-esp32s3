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
- Sesija: `guided25-20260823-202143`
- Port: `COM3` @ 115200 baud
- Udaljenost: 20.0 cm
- Prostorija: soba
- Prag: 6341.41992
- DET prozora: 55
- Validnih DET prozora za metrike: 0
- Condition+protocol validnih DET kandidata: 43
- Protocol-valid DET prozora: 55
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 55
- Alarmnih validnih DET prozora: 0
- Firmware sesija: 1
- Run DET total (tracker/CSV): 55/55
- Alarmnih prozora / ulazaka / epizoda: 0 / 0 / 0
- Vrijeme u alarmu: 0.00%
- Medijana oporavka: nije izmjerena s
- Isključenih prelaznih prozora: 11
- Najveci prijavljeni `dropped`: 0

## Rezultati po firmware sesiji

| Sesija | Protokol | K1 | DET raw/metric | Alarm prozori/epizode | Alarm % | Oporavak s | Prelazni isključeni |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | accepted (valid) | accepted | 55/0 | 0/0 | 0.00 | - | 11 |

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| (nema DET podataka) | 0 | 0 | - | - |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora i prihvaćene K1 kalibracije ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.016 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.454 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `27.016 s` **virtual_button / guided25**: panel
- `27.032 s` **virtual_button / press**: panel
- `82.329 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `841.235 s` **phase / detection**: firmware DET faza; operator condition i dalje nije potvrđen
- `860.250 s` **condition / normal_baseline**: Normalna osnova: Miruj i ne pricaj.
- `910.344 s` **condition / airflow_change_paper_1**: Papiric 1: Drzi papiric uz usis, bez dodira ventilatora.
- `910.969 s` **note / operator**: guided25_confirm phase=airflow_change_paper_1 edge=start host_utc=2026-08-23T18:36:56.842+00:00
- `960.032 s` **condition / recovery_normal_1**: Oporavak 1: Skloni papiric i ruku; tisina.
- `963.610 s` **note / operator**: guided25_confirm phase=recovery_normal_1 edge=start host_utc=2026-08-23T18:37:49.035+00:00
- `1010.110 s` **condition / airflow_change_paper_2**: Papiric 2: Ponovi isti polozaj papirica.
- `1012.547 s` **note / operator**: guided25_confirm phase=airflow_change_paper_2 edge=start host_utc=2026-08-23T18:38:37.510+00:00
- `1060.157 s` **condition / recovery_normal_2**: Oporavak 2: Skloni papiric i ruku; tisina.
- `1063.485 s` **note / operator**: guided25_confirm phase=recovery_normal_2 edge=start host_utc=2026-08-23T18:39:28.794+00:00
- `1110.235 s` **condition / airflow_change_paper_3**: Papiric 3: Treci put ponovi isti polozaj.
- `1112.360 s` **note / operator**: guided25_confirm phase=airflow_change_paper_3 edge=start host_utc=2026-08-23T18:40:17.947+00:00
- `1160.313 s` **condition / recovery_normal_3**: Oporavak 3: Skloni papiric i ruku; tisina.
- `1162.297 s` **note / operator**: guided25_confirm phase=recovery_normal_3 edge=start host_utc=2026-08-23T18:41:08.079+00:00
- `1210.360 s` **condition / ambient_speech**: Razgovor: Pricaj normalno sa oznacenog mjesta.
- `1213.329 s` **note / operator**: guided25_confirm phase=ambient_speech edge=start host_utc=2026-08-23T18:41:58.472+00:00
- `1260.375 s` **condition / recovery_after_speech**: Oporavak poslije govora: Prestani da pricas; tisina.
- `1262.360 s` **note / operator**: guided25_confirm phase=recovery_after_speech edge=start host_utc=2026-08-23T18:42:47.335+00:00
- `1310.329 s` **condition / ambient_door**: Vrata: Jednom normalno otvori i zatvori vrata; ne lupaj.
- `1310.469 s` **note / operator**: guided25_confirm phase=ambient_door edge=start host_utc=2026-08-23T18:43:36.383+00:00
- `1340.313 s` **condition / final_recovery**: Zavrsni oporavak: Miruj i ostavi ventilator da radi normalno.
- `1340.563 s` **note / operator**: guided25_confirm phase=final_recovery edge=start host_utc=2026-08-23T18:44:06.500+00:00
- `1390.250 s` **session / stop**: kraj plana
- `1390.766 s` **session / final_buffer_drain_complete**: buffered UART je procitan prije finalizacije
