# Duga proba laznih alarma

- Vrijeme: `2026-08-13T23:42:58`
- Zvuk: TARGET normalan ventilator, brzina `spd_1`, preko zvucnika
- Kalibracija: 13 klipova (130 s)
- Detekciona petlja: 8 klipova (80 s), kalibracija ih NIJE cula
- Trajanje zahtijevano: 8.0 min
- Prag (zamrznut poslije kalibracije): 5687.1147
- LOO kalibracije: mean=899.86 sd=1595.75

## Rezultat

| | |
|---|---|
| Prozora u detekciji | 36 (5.8 min) |
| Prozora iznad praga | 0 (0.0 %) |
| Prozora u alarmu (3 uzastopna) | **0** |
| Alarmnih epizoda | **0** |
| **Laznih alarma na sat** | **0.00** |
| Score | mean=829.75 sd=727.88 min=215.49 max=3337.43 |
| Rezerva do praga | max score je 58.7 % praga |

## Drift kroz prolaz (isti zvuk u petlji)

| Interval | Prozora | Score mean | sd | max | Alarma |
|---|---|---|---|---|---|
| 0-10 min | 36 | 829.75 | 727.88 | 3337.43 | 0 |

## Prvi prolaz vs ponavljanja

Detekciona petlja je 80 s (~8 prozora). Prvi prolaz je jedini nad zvukom koji uredjaj nikad nije cuo.

| | Prozora | Score mean | max | Alarma |
|---|---|---|---|---|
| prvi prolaz (nov zvuk) | 8 | 483.12 | 640.75 | 0 |
| ponavljanja | 28 | 928.79 | 3337.43 | 0 |

## Zdravlje lanca

- QUALITY zapisa: 106, ne-OK: **0**
- `dropped` ukupno: **0** · `clipped` ukupno: **0**
- nivo u detekciji: -46.1 do -45.6 dBFS (gate je -60 dBFS)

## Ogranicenja ovog prolaza

- Zvuk je snimak preko zvucnika, **nije fizicki ventilator**; u radu se ne smije navesti kao fizicki test.
- Detekcioni snimak od 80 s se ponavlja, pa ovo mjeri stabilnost praga naspram drifta kanala i uredjaja, a ne otpornost na nepoznat normalan zvuk.
- Jedna brzina ventilatora; prelazi izmedju brzina nisu testirani.
