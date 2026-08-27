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
- Sesija: `guided25-20260827-v3recovery5d`
- Port: `COM3` @ 115200 baud
- Udaljenost: 40.0 cm
- Prostorija: soba
- Prag: 8084.49365
- DET prozora: 65
- Validnih DET prozora za metrike: 43
- Condition+protocol validnih DET kandidata: 43
- Protocol-valid DET prozora: 65
- Tracker/CSV DET count saglasan: **DA**
- Isključenih DET prozora: 22
- Alarmnih validnih DET prozora: 3
- Firmware sesija: 1
- Run DET total (tracker/CSV): 65/65
- Alarmnih prozora / ulazaka / epizoda: 3 / 2 / 2
- Vrijeme u alarmu: 6.98%
- Medijana oporavka: 10.077999999999975 s
- Isključenih prelaznih prozora: 11
- Najveci prijavljeni `dropped`: 0

## Rezultati po firmware sesiji

| Sesija | Protokol | K1 | DET raw/metric | Alarm prozori/epizode | Alarm % | Oporavak s | Prelazni isključeni |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | accepted (valid) | accepted | 65/43 | 3/2 | 6.98 | 10.077999999999975 | 11 |

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| normal_baseline | 4 | 0 | 1146.352 | 1079.915..2134.034 |
| airflow_change_paper_1 | 4 | 0 | 30255.497 | 16007.936..56166.879 |
| recovery_normal_1 | 4 | 0 | 2756.886 | 2562.906..3096.692 |
| airflow_change_paper_2 | 4 | 0 | 62343.756 | 54025.855..66837.820 |
| recovery_normal_2 | 4 | 0 | 2554.802 | 2119.846..3233.730 |
| airflow_change_paper_3 | 4 | 2 | 19843.514 | 14050.712..29759.594 |
| recovery_normal_3 | 4 | 1 | 3085.976 | 2220.808..4189.742 |
| ambient_speech | 4 | 0 | 38307.469 | 31073.873..41066.277 |
| recovery_after_speech | 4 | 0 | 2819.233 | 2527.874..3049.974 |
| ambient_door | 2 | 0 | 49548.869 | 4366.168..94731.570 |
| final_recovery | 5 | 0 | 2824.620 | 2593.522..3456.374 |

## Ogranicenje

Samo DET prozori nakon eksplicitne operatorove condition komande i nakon validnog firmware handshake/CAL ugovora i prihvaćene K1 kalibracije ulaze u metrike. Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

- `0.016 s` **session / start**: sigurnosna postavka potvrđena; operator condition=unconfirmed
- `0.469 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `46.078 s` **virtual_button / guided25**: panel
- `46.094 s` **virtual_button / press**: panel
- `101.391 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `860.375 s` **phase / detection**: firmware DET faza; operator condition i dalje nije potvrđen
- `979.063 s` **condition / normal_baseline**: Normalna osnova: Miruj i ne pricaj.
- `1029.125 s` **condition / airflow_change_paper_1**: Papiric 1: Drzi papiric uz usis, bez dodira ventilatora.
- `1079.047 s` **condition / recovery_normal_1**: Oporavak 1: Skloni papiric i ruku; tisina.
- `1128.922 s` **condition / airflow_change_paper_2**: Papiric 2: Ponovi isti polozaj papirica.
- `1178.875 s` **condition / recovery_normal_2**: Oporavak 2: Skloni papiric i ruku; tisina.
- `1229.578 s` **condition / airflow_change_paper_3**: Papiric 3: Treci put ponovi isti polozaj.
- `1279.516 s` **condition / recovery_normal_3**: Oporavak 3: Skloni papiric i ruku; tisina.
- `1329.453 s` **condition / ambient_speech**: Razgovor: Pricaj normalno sa oznacenog mjesta.
- `1379.391 s` **condition / recovery_after_speech**: Oporavak poslije govora: Prestani da pricas; tisina.
- `1429.250 s` **condition / ambient_door**: Vrata: Jednom normalno otvori i zatvori vrata; ne lupaj.
- `1459.234 s` **condition / final_recovery**: Zavrsni oporavak: Miruj i ostavi ventilator da radi normalno.
- `1509.172 s` **session / stop**: kraj plana
- `1509.891 s` **session / final_buffer_drain_complete**: buffered UART je procitan prije finalizacije; trajanje=0.719 s; paket_jos_otvoren=0
