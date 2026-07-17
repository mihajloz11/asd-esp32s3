# Master rad — ASD na ESP32-S3

Nenadgledana detekcija anomalija zvuka mašina (DCASE 2026 Task 2) na ESP32-S3-WROOM-1
N32R16V. Plan i metodologija: [plan-master-rada.md](plan-master-rada.md).

## Struktura

```
pc/                 Python pipeline (trening, evaluacija, kvantizacija)
  asd/              paket: features, data, model, train, eval, quantize
  tools/            generatori C headera + test vektora za uređaj
  tests/            PC↔C unit testovi (featuri, gamma kalibracija)
  run_sweep.ps1     E1+E2+E3 za jednu mašinu (svi modeli + int8)
firmware/esp32s3_asd/   ESP-IDF v5.x projekat (I2S, DSP front-end, TFLM, kalibracija)
data/               DCASE 2026 dev dataset (gitignored)
models/             .keras / .tflite / meta.json (gitignored osim meta)
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
```

Svi rezultati se dopisuju u `results/results.csv` (kolona `precision`: fp32 /
fp32_tflite / int8 — ΔAUC analiza je pivot po toj koloni).

## Firmware (na mašini sa ESP-IDF v5.x)

```bash
cd firmware/esp32s3_asd
idf.py set-target esp32s3
idf.py build flash monitor
```

Pin-plan i zabranjeni pinovi (GPIO 35/36/37 = oktalni PSRAM): `main/pins.h`.
PSRAM/flash config za N32R16V: `sdkconfig.defaults` (OCT mod — quad daje boot-loop).

## Ključne odluke (odstupanja od librosa/baseline — za pogl. 5 rada)

1. **center=False** u STFT (bez reflect paddinga) — na uređaju nema paddinga; PC
   pipeline identičan po konstrukciji. Gubi se ~2 rubna frejma po klipu.
2. **LOG_EPS = 1e-12** (float32-representable) umjesto `sys.float_info.epsilon`.
3. **Per-dimenziona standardizacija** (mean/std sa treninga, 640+640 float u flash)
   — pomaže i int8 kvantizaciji (uži dinamički opseg).
4. **Isti C kod featura na PC-u i uređaju** (ctypes test): razlika na realnim
   klipovima < 4e-5 dB — rizik B1 iz plana zatvoren po konstrukciji.
5. Gamma prag: momentna metoda + Wilson–Hilferty u C — poklapanje sa scipy < 2 %.
