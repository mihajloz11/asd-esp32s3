# Master rad — ASD na ESP32-S3

Nenadgledana detekcija anomalija zvuka mašina (DCASE 2026 Task 2) na ESP32-S3-WROOM-1
N32R16V. Plan i metodologija: [plan-master-rada.md](plan-master-rada.md).

## Gdje je projekat sada (26.08.2026)

Prvi fizički test ventilatora postoji i dokumentovan je u
[rezultat-fan01-2026-08-16.md](docs/rezultat-fan01-2026-08-16.md). `psd_shape`
je veoma dobro rangirao bezbjedno izazvanu promjenu protoka papirićem, ali tadašnji
prag iz kratke kalibracije nije radio: 54/60 normalnih prozora bilo je iznad
praga. Papirić nije potvrđen stvarni kvar, a broj `324/h` iz starog izvještaja
znači alarmne **prozore** po satu, ne alarmne epizode po satu.

Poslije FAN01 softver je preuređen u fail-closed tok
`SETTLE → CENTER_LEARNING → COMMISSION_DERIVE → COMMISSION_VERIFY → MONITORING`.
Centar, izvođenje praga i kasnija provjera sada su odvojeni; enter/exit su
apsolutni pragovi. K1 i multi-session host su centralizovani, research build
čuva `96 + 5×96` obilježja, audio čitanje je bounded, a NVS storage modul ima
schema/fingerprint/generation/CRC. DEVELOPMENT policy je fail-closed RAM-only:
ne učitava, ne čuva i ne emituje `PROFILESTORE` dok politika ne bude fizički
potvrđena i zamrznuta. `OBSERVATION_HOLD` v3 je uključen kao DEVELOPMENT
reliability gate: apsolutni prag se više ne prenosi između položaja mikrofona,
nego se u svakoj sesiji izvodi kao `max(10 CAL normal-only) × 1,25`. Papirić,
govor i vrata ne ulaze u fit. Kod, host i ploča su pripremljeni, ali isti
GUIDED25 fizički retest tek treba potvrditi rezultat; commissioning i HOLD
brojevi zato još nisu proizvodno završeni.

| | |
|---|---|
| Serijski protokol | live `asd-quality-v1.6.0` · host `physical-fan-v1.9.0` + `physical-fan-artifacts-v1.9.0`; offline read ostaje zaključan i za v1.6↔q1.3, v1.7↔q1.4 i v1.8↔q1.5 |
| Model | `psd_shape`, 96 traka log-PSD, Mahalanobis; finalni `k=10`: AUC 0,856 (razvojno, 20 podjela); referentni PC `k=20`: AUC 0,867 (kanonski, 100 podjela) |
| PC testovi | **472 passed** (26.08.2026), uključujući PC↔C, multi-session, research, commissioning/HOLD, oba fizička setapa kao zamrznutu regresiju, strogi q1.6 live tok, audio i NVS ugovore |
| Posljednji build | ESP-IDF 5.5.5 `ASD_PSD_LIVE` + research: **PASS**, 353 168 B, SHA-256 `A1778C59…5718D17`; flash na COM3 i IDLE FLAGS preflight **PASS** |
| Fizički dokaz | FAN01 ostaje istorijski; GUIDED25 run 26.08. je potvrdio P20, ali je prekinut hard deadlineom i otkrio setup-osjetljiv v2 HOLD prag; v3 fizički retest je otvoren |
| **Ostalo** | **završiti elektroniku · zamrznuti normal-only politiku · kratak fizički run · power-loss/I2S runtime** → [docs/PREOSTALO.md](docs/PREOSTALO.md) |
| Lemljenje | dvije ploče (uređaj + mjerna) → [docs/plan-dvije-plocice.md](docs/plan-dvije-plocice.md) · crteži [docs/sema-sklopa.pdf](docs/sema-sklopa.pdf) |

Šta je urađeno i izmjereno, hronološki:
[docs/DNEVNIK-NEXT-LEVEL.md](docs/DNEVNIK-NEXT-LEVEL.md).
Putanja modela sa svim pokušajima i negativnim rezultatima:
[docs/put-do-modela.md](docs/put-do-modela.md).
Problemi i zamke (P1–P19): [docs/problemi-i-rjesenja.md](docs/problemi-i-rjesenja.md).
Mapa cijele dokumentacije, sa oznakom šta je aktuelno a šta istorijsko:
[docs/INDEKS.md](docs/INDEKS.md). Kontekst i pravila rada na projektu:
[KONTEKST.md](KONTEKST.md).

> **Granica tvrdnje.** FAN01 i GUIDED25 su stvarni ventilator, ali papirić je
> kontrolisana promjena protoka, ne potvrđen kvar. V3 je host/build/flash/IDLE
> preflight potvrđen, ali još nije prošao kompletan fizički GUIDED25 niti
> power-loss test. Benchmark, regresija i build nisu fizička tačnost.

## Struktura

```
pc/                 Python pipeline (trening, evaluacija, kvantizacija)
  asd/              paket: features, data, model, train, eval, quantize
  tools/            generatori C headera + test vektora za uređaj
  tests/            PC↔C unit testovi (featuri, gamma kalibracija)
  run_sweep.ps1     E1+E2+E3 za jednu mašinu (svi modeli + int8)
firmware/esp32s3_asd/   ESP-IDF v5.x projekat (finalni PSD/Mahalanobis; istorijski TFLM modovi)
data/               DCASE 2026 dev dataset (gitignored)
models/             PSD .npz/meta + istorijski .keras/.tflite artefakti
results/            results.csv + logovi + keš featura
```

## Setup (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# GCC za PC↔C testove: winget install -e --id BrechtSanders.WinLibs.POSIX.UCRT
```

Dataset: 7 zipova sa https://zenodo.org/records/19336329 raspakovati u
`data/dcase2026_dev/<masina>/{train,test}`.

## Workflow

```powershell
cd pc
# jedan model:
..\.venv\Scripts\python.exe -m asd.train --data ..\data\dcase2026_dev\fan --variant baseline
..\.venv\Scripts\python.exe -m asd.quantize --data ..\data\dcase2026_dev\fan --tag fan_baseline_s0
# cijeli sweep za mašinu (E1+E2+E3):
.\run_sweep.ps1 -Machine fan
# artefakti za firmware:
..\.venv\Scripts\python.exe tools\gen_mel_header.py
..\.venv\Scripts\python.exe tools\gen_model_header.py --tag fan_baseline_s0
..\.venv\Scripts\python.exe tools\export_test_vectors.py --wav <klip.wav> --tag fan_baseline_s0
# PC↔C testovi (traže gcc u PATH):
..\.venv\Scripts\python.exe -m pytest tests\ -v
# dashboard svih eksperimenata (results\dashboard.html):
..\.venv\Scripts\python.exe tools\gen_dashboard.py
# E4: klipovi za flash particiju + PC referenca + poredjenje sa uredjajem:
..\.venv\Scripts\python.exe tools\prepare_eval_clips.py --data ..\data\dcase2026_dev\fan --tag fan_baseline_s0
..\.venv\Scripts\python.exe tools\compare_eval.py --machine fan
```

Svi rezultati se dopisuju u `results/results.csv` (kolona `precision`: fp32 /
fp32_tflite / int8 — ΔAUC analiza je pivot po toj koloni).

## Firmware (na mašini sa ESP-IDF v5.x) — dva targeta

```bash
cd firmware/esp32s3_asd
idf.py set-target esp32s3   # glavna platforma (N32R16V)
# ili: idf.py set-target esp32   # DevKit V1 — E4 kontrola (bez PIE/PSRAM)
idf.py build flash monitor
```

Modovi builda se biraju env varijablom prije `idf.py reconfigure build`:
`ASD_PSD_LIVE` (samostalni detektor — ovo je finalni mod), `ASD_MIC_TEST`
(bring-up mikrofona), `ASD_INA_TEST` (potrošnja), `ASD_PSD_VERIFY` (PC↔uređaj
parity front-enda).

Per-target pinovi i sdkconfig se biraju automatski (`main/pins.h`,
`sdkconfig.defaults.<target>`). Zabranjeni pinovi: S3 GPIO 35/36/37 (oktalni
PSRAM), ESP32 GPIO 6–11 (flash). Firmware koristi **streaming** obradu hop-po-hop
i time izbjegava baferovanje približno 640 KB velikog punog float ulaznog
prozora. Finalni ESP32-S3 build report pokazuje oko 293 kB zauzetog i 342 kB
slobodnog DIRAM-a; ne tvrdi se da cijeli finalni PSD feature put koristi manje
od 25 kB. Detalji: [docs/edge-adaptacija.md](docs/edge-adaptacija.md), inventar
i nabavka: [docs/hardware.md](docs/hardware.md).

## Ključne odluke (odstupanja od librosa/baseline — za pogl. 5 rada)

1. **center=False** u STFT (bez reflect paddinga) — na uređaju nema paddinga; PC
   pipeline identičan po konstrukciji. Gubi se ~2 rubna frejma po klipu.
2. **LOG_EPS = 1e-12** (float32-representable) umjesto `sys.float_info.epsilon`.
3. **Per-dimenziona standardizacija** (mean/std sa treninga, 640+640 float u flash)
   — pomaže i int8 kvantizaciji (uži dinamički opseg).
4. **Isti C kod featura na PC-u i uređaju** (ctypes test): razlika na realnim
   klipovima < 4e-5 dB — rizik B1 iz plana zatvoren po konstrukciji.
5. Gamma prag: momentna metoda + Wilson–Hilferty u C — poklapanje sa scipy < 2 %.
