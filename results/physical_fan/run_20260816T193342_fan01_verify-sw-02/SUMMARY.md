# Stvarni fizicki fan eksperiment

- Status: `completed_by_operator`
- Validan fizički rezultat: **DA**
- Protokol: `physical-fan-v1.6.0`
- Fan ID: `fan01`
- Sesija: `verify-sw-02`
- Port: `COM3` @ 115200 baud
- Udaljenost: 20.0 cm
- Prostorija: soba
- Prag: 399.611877
- DET prozora: 131
- Validnih DET prozora za metrike: 124
- Protocol-valid DET prozora: 131
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 7
- Alarmnih validnih DET prozora: 118
- Najveci prijavljeni `dropped`: 107520

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| normal_baseline | 60 | 54 | 876.484 | 180.484..16151.690 |
| airflow_change | 18 | 18 | 30857.239 | 952.863..48827.094 |
| recovery_normal | 37 | 37 | 1045.995 | 408.917..48204.457 |
| ambient_noise | 6 | 6 | 11945.647 | 10750.943..18201.873 |
| controlled_stop | 3 | 3 | 15777.658 | 1324.259..15935.842 |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.031 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.484 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `11.000 s` **virtual_button / press**: panel
- `26.391 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `126.359 s` **phase / detection**: firmware DET faza; operator condition i dalje nije potvrđen
- `204.375 s` **condition / normal_baseline**: Normalna osnova: Sjedi mirno. Ne pricaj, ne kucaj, ne prilazi ventilatoru.
- `805.094 s` **condition / airflow_change**: Papiric 1: Drzi papiric uz USIS (zadnja strana), spolja, bez kontakta.
- `865.078 s` **condition / recovery_normal**: Oporavak 1: Skloni papiric I ruku. Odmakni se korak. Tisina.
- `954.906 s` **condition / airflow_change**: Papiric 2: Papiric uz usis, isto mjesto i isti zahvat kao prvi put.
- `1014.812 s` **condition / recovery_normal**: Oporavak 2: Skloni papiric I ruku. Tisina.
- `1104.656 s` **condition / airflow_change**: Papiric 3: Papiric uz usis, treci put.
- `1164.562 s` **condition / recovery_normal**: Oporavak 3: Skloni papiric I ruku. Tisina.
- `1255.469 s` **condition / ambient_noise**: Razgovor: Pricaj normalnim glasom sa oznacenog mjesta, 2 m od mikrofona.
- `1315.391 s` **condition / recovery_normal**: Oporavak: Prestani da pricas. Tisina.
- `1405.219 s` **condition / controlled_stop**: Gasenje: SAD ugasi ventilator. Ne pomjeraj ga.
- `1435.141 s` **session / stop**: kraj plana
- `1435.266 s` **session / final_buffer_drain_complete**: buffered UART je procitan prije finalizacije
