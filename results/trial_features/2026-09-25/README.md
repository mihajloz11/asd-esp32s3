# Obilježja završnih fizičkih proba — naknadna analiza

25.09.2026. Alat: [analyze_trial_features.py](../../../pc/tools/analyze_trial_features.py).
Firmware, model i pragovi nisu mijenjani. Ulaz su FEATURE96 zapisi koje je
uređaj poslao tokom proba 27.08, model iz `psd_model_data.h` i centar iz
prihvaćenih CAL prozora (za papirić bez izbačenih prozora 2 i 9).

```powershell
python pc/tools/analyze_trial_features.py --output results/trial_features/2026-09-25
```

## 1. Ponovljena ocjena

Ocjena izračunata na PC-u iz sačuvanih obilježja odstupa od ocjene sa
uređaja najviše 9,0e−7 (papirić) i 4,2e−7 (ton), relativno. Model, centar i
izbor CAL prozora su dakle isti kao na uređaju, pa su tačke 2 i 3 pouzdane.

## 2. Nivo nasuprot obliku spektra

Osam traka ispod 28 Hz nema nijedan FFT bin i nosi fiksnu vrijednost −20.
Poslije oduzimanja srednje vrijednosti one prenose širokopojasni nivo u
svih 96 komponenti. Druga ocjena vraća nivo popunjenih traka na kalibracioni,
a oblik spektra ostavlja isti.

| Uslov | Ocjena | Na nivou kalibracije | Promjena | Nivo traka |
|---|---:|---:|---:|---:|
| papirić 1 | 30 255 | 30 409 | +0,5 % | +1,5 dB |
| papirić 2 | 62 344 | 62 607 | +0,4 % | +1,2 dB |
| papirić 3 | 19 844 | 19 933 | +0,5 % | +0,2 dB |
| razgovor | 38 307 | 28 450 | −25,7 % | +6,0 dB |
| vrata | 49 549 | 32 935 | −33,5 % | +9,0 dB |
| ton 1 kHz | 23 574 | 22 667 | −3,8 % | −0,1 dB |

Papirić i ton detektovani su po obliku spektra. Kod razgovora i vrata nivo
nosi četvrtinu do trećine ocjene; ostatak je i dalje 3,5–4 puta iznad
ulaznog praga. Nivo traka (srednji log snage preko 88 traka) nije isto što
i RMS nivo prozora iz `detections.csv`.

## 3. Gdje pobuda mijenja spektar

Medijana odstupanja `z − c` po traci, prozori iz metrike:

| Uslov | Najveća odstupanja |
|---|---|
| papirić | 1,3–3,9 kHz i oko 436 Hz |
| razgovor | 76–210 Hz; prazne trake oko −12 (curenje nivoa) |
| ton | 982 Hz i 3021 Hz (treći harmonik) |

U probi sa tonom traka od 1 kHz ostaje oko +42 još 36 prozora poslije
oznake `recovery_after_tone`, do 1844,6 s, pa naglo pada na nulu. Ton je
dakle svirao oko šest minuta poslije oznake kraja. Poslije gašenja ocjene
stoje između 12 266 i 19 561, iznad izlaznog praga 10 905, do kraja snimka
(14 prozora). Traka od 3 kHz raste zajedno sa 1 kHz oko 1315 s, što se
poklapa sa pojačanjem koje je operater zabilježio bez vremena.

Puni zapis, uključujući 96 vrijednosti po uslovu i vremenski tok obje trake:
[summary.json](summary.json). Sl. 2 i 3 TELFOR rada crtaju se iz istih podataka.

## Granice

Dvije sesije jednog ventilatora. Analiza ne mijenja ishod proba (GUIDED25
FAIL za papirić) i ne zamjenjuje fizičku probu mape bez praznih traka iz
[psd_nonempty](../../psd_nonempty/2026-09-07/README.md).
