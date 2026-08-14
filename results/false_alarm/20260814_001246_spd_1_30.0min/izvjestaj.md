# Duga proba laznih alarma

- Vrijeme: `2026-08-14T00:42:46`
- Zvuk: TARGET normalan ventilator, brzina `spd_1`, preko zvucnika
- Kalibracija: 14 klipova (140 s)
- Detekciona petlja: 7 klipova (70 s), kalibracija ih NIJE cula
- Trajanje zahtijevano: 30.0 min
- Prag (zamrznut poslije kalibracije): 346.8928
- LOO kalibracije: mean=167.15 sd=59.92

## Rezultat

| | |
|---|---|
| Prozora u detekciji | 167 (27.6 min) |
| Prozora iznad praga | 152 (91.0 %) |
| Prozora u alarmu (3 uzastopna) | **139** |
| Alarmnih epizoda | **4** |
| **Laznih alarma na sat** | **8.69** |
| Score | mean=3130.93 sd=8557.25 min=135.77 max=100149.53 |
| Rezerva do praga | max score je 28870.5 % praga |

## Drift kroz prolaz (isti zvuk u petlji)

| Interval | Prozora | Score mean | sd | max | Alarma |
|---|---|---|---|---|---|
| 0-10 min | 61 | 4596.07 | 13902.64 | 100149.53 | 33 |
| 10-20 min | 60 | 2604.17 | 1757.92 | 9688.20 | 60 |
| 20-30 min | 46 | 1875.10 | 846.68 | 7093.02 | 46 |

## Prvi prolaz vs ponavljanja

Detekciona petlja je 70 s (~7 prozora). Prvi prolaz je jedini nad zvukom koji uredjaj nikad nije cuo.

| | Prozora | Score mean | max | Alarma |
|---|---|---|---|---|
| prvi prolaz (nov zvuk) | 7 | 262.67 | 583.03 | 0 |
| ponavljanja | 160 | 3256.41 | 100149.53 | 139 |

## Zdravlje lanca

- Protokol: `asd-quality-v1.3.0` · gate prisustva: -56.64 dBFS
- QUALITY zapisa: 237, ne-OK: **0**
- `dropped` ukupno: **0** · `clipped` ukupno: **0**
- nivo u detekciji: -46.5 do -40.4 dBFS (gate je -60 dBFS)

## Ogranicenja ovog prolaza

- Zvuk je snimak preko zvucnika, **nije fizicki ventilator**; u radu se ne smije navesti kao fizicki test.
- Detekcioni snimak od 70 s se ponavlja, pa ovo mjeri stabilnost praga naspram drifta kanala i uredjaja, a ne otpornost na nepoznat normalan zvuk.
- Jedna brzina ventilatora; prelazi izmedju brzina nisu testirani.
