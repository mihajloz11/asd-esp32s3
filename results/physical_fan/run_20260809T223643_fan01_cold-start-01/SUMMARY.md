# Stvarni fizicki fan eksperiment

- Status: `invalid_no_physical_fan`
- Validan fizički rezultat: **NE**
- Naknadna korekcija: fizički ventilator nije bio dostupan; ovo je samo
  preflight pločice/mikrofona i ne smije se koristiti kao fan eksperiment.
- Protokol: `physical-fan-v1.0.0`
- Fan ID: nije primjenjivo (`fan01` je bio pogrešan placeholder)
- Sesija: `cold-start-01`
- Port: `COM3` @ 115200 baud
- Udaljenost od fana: nije primjenjivo
- Prostorija: radna-soba
- Prag: nije dobijen
- DET prozora: 0
- Alarmnih DET prozora: 0
- Najveci prijavljeni `dropped`: nije ispisan

## Rezultati po rucno oznacenom uslovu

| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |
|---|---:|---:|---:|---:|
| (nema DET podataka) | 0 | 0 | - | - |

## Ogranicenje

Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.

## Dogadjaji

> Posthoc korekcija 09.08.2026: početne tvrdnje ispod da je fan bio normalan
> nisu bile tačne; fizički fan nije postojao u postavci. Originalni događaji
> ostaju prikazani radi audit traga.

- `0.000 s` **session / start**: serijski port otvoren; fan potvrđen normalan
- `0.453 s` **device / reset**: RTS reset; pocinje WAIT/CAL/DET
- `16.656 s` **phase / calibration**: fan mora ostati u potvrđeno normalnom stanju
- `65.656 s` **session / stop**: restartovan prije DET radi punih 30 minuta baselinea
