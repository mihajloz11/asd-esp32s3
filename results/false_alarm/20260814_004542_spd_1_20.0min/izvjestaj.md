# Duga proba laznih alarma

- Vrijeme: `2026-08-14T01:05:42`
- Zvuk: TARGET normalan ventilator, brzina `spd_1`, preko zvucnika
- Kalibracija: 14 klipova (140 s)
- Detekciona petlja: 7 klipova (70 s), kalibracija ih NIJE cula
- Trajanje zahtijevano: 20.0 min
- Prag (zamrznut poslije kalibracije): 1087.9694
- LOO kalibracije: mean=394.80 sd=231.06

## Rezultat

| | |
|---|---|
| Prozora u detekciji | 107 (17.6 min) |
| Prozora iznad praga | 6 (5.6 %) |
| Prozora u alarmu (3 uzastopna) | **0** |
| Alarmnih epizoda | **0** |
| **Laznih alarma na sat** | **0.00** |
| Score | mean=426.00 sd=323.13 min=131.75 max=2672.96 |
| Rezerva do praga | max score je 245.7 % praga |

## Drift kroz prolaz (isti zvuk u petlji)

| Interval | Prozora | Score mean | sd | max | Alarma |
|---|---|---|---|---|---|
| 0-10 min | 61 | 502.66 | 398.73 | 2672.96 | 0 |
| 10-20 min | 46 | 324.35 | 117.96 | 707.71 | 0 |

## Prvi prolaz vs ponavljanja

Detekciona petlja je 70 s (~7 prozora). Prvi prolaz je jedini nad zvukom koji uredjaj nikad nije cuo.

| | Prozora | Score mean | max | Alarma |
|---|---|---|---|---|
| prvi prolaz (nov zvuk) | 7 | 515.79 | 1200.16 | 0 |
| ponavljanja | 100 | 419.71 | 2672.96 | 0 |

## Zdravlje lanca

- Protokol: `asd-quality-v1.3.0` · gate prisustva: -57.07 dBFS
- QUALITY zapisa: 177, ne-OK: **0**
- `dropped` ukupno: **0** · `clipped` ukupno: **0**
- nivo u detekciji: -46.5 do -46.0 dBFS (gate je -60 dBFS)

## Ogranicenja ovog prolaza

- Zvuk je snimak preko zvucnika, **nije fizicki ventilator**; u radu se ne smije navesti kao fizicki test.
- Detekcioni snimak od 70 s se ponavlja, pa ovo mjeri stabilnost praga naspram drifta kanala i uredjaja, a ne otpornost na nepoznat normalan zvuk.
- Jedna brzina ventilatora; prelazi izmedju brzina nisu testirani.
