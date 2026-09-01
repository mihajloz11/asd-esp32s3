# Master rad — ASD na ESP32-S3

Nenadgledana detekcija anomalija zvuka mašina (DCASE 2026 Task 2) na ESP32-S3-WROOM-1
N32R16V. Plan i metodologija: [plan-master-rada.md](plan-master-rada.md).

## Gdje je projekat sada (27.08.2026)

**Firmware je funkcionalno završen i potvrđen na pločici.** Dva validna fizička
runa 27.08.2026 pokazuju cio lanac kako je zamišljen: uređaj sam nauči normalno
stanje nepoznatog ventilatora, sam izvede prag iz normal-only prozora, odbije
nepouzdan prozor umjesto da ga tumači, i pouzdano prijavi konstantnu akustičku
promjenu — bez računara, uz `dropped=0`. Puna analiza sa svim brojkama, svim
odbačenim pokušajima i granicama tvrdnje:
[rezultat-finalna-validacija-2026-08-27.md](docs/rezultat-finalna-validacija-2026-08-27.md).

Kratko: konstantni ton je podigao `ANOMALY` u tri prozora (~30 s) i
`ANOMALY_SUSTAINED` poslije dvanaest (~2 min), dok govor i vrata nisu podigli
alarm iako su im skorovi bili visoki — kapija pouzdanosti ih je odbila kao
nestabilne. Papirić je i dalje `1/3` po GUIDED25 kriteriju, i to iz izmjerenog
razloga: drži se rukom, pa stimulus nije konstantan.

Prvi fizički test ventilatora ostaje u
[rezultat-fan01-2026-08-16.md](docs/rezultat-fan01-2026-08-16.md). `psd_shape`
je i tada veoma dobro rangirao promjenu protoka papirićem, ali prag iz kratke
kalibracije nije radio: 54/60 normalnih prozora bilo je iznad praga. Broj
`324/h` iz tog izvještaja znači alarmne **prozore** po satu, ne epizode.

Poslije FAN01 softver je preuređen u fail-closed tok
`SETTLE → CENTER_LEARNING → COMMISSION_DERIVE → COMMISSION_VERIFY → MONITORING`.
Centar, izvođenje praga i kasnija provjera su odvojeni; enter/exit su apsolutni
pragovi. K1 i multi-session host su centralizovani, research build čuva
`96 + 5×96` obilježja, audio čitanje je bounded, a NVS storage modul ima
schema/fingerprint/generation/CRC. DEVELOPMENT policy je fail-closed RAM-only:
ne učitava, ne čuva i ne emituje `PROFILESTORE` dok politika ne bude zamrznuta.
`OBSERVATION_HOLD` v3 je uključen: prag se ne prenosi između položaja
mikrofona, nego se po sesiji izvodi kao `max(10 CAL normal-only) × 1,25`.
Papirić, govor, vrata i ton **ne ulaze** ni u jedan fit.

| | |
|---|---|
| Serijski protokol | live `asd-quality-v1.6.0` · host `physical-fan-v1.9.0` + `physical-fan-artifacts-v1.9.0`; offline read ostaje zaključan i za v1.6↔q1.3, v1.7↔q1.4 i v1.8↔q1.5 |
| Model | `psd_shape`, 96 traka log-PSD, Mahalanobis; finalni `k=10`: AUC 0,856 (razvojno, 20 podjela); referentni PC `k=20`: AUC 0,867 (kanonski, 100 podjela) |
| PC testovi | **478 passed** (27.08.2026), uključujući PC↔C, multi-session, research, commissioning/HOLD, oba fizička setapa kao zamrznutu regresiju, strogi q1.6 live tok, audio i NVS ugovore |
| Posljednji build | ESP-IDF 5.5.5 `ASD_PSD_LIVE` + research: **PASS**, 354 784 B, SHA-256 `9ac2caca…8d967813`; **isti bin je pustio oba validna fizička runa** |
| Fizički dokaz | **27.08.2026: dva `valid_physical_result` runa** — papirić (`8 084,49` prag, alarm u 3. bloku, oporavak `10,08 s`) i konstantni ton (`21 809,51` prag, `ANOMALY` + `ANOMALY_SUSTAINED`), oba `dropped=0` |
| **Ostalo** | **završiti elektroniku · zamrznuti normal-only politiku · kratak fizički run · power-loss/I2S runtime** → [docs/PREOSTALO.md](docs/PREOSTALO.md) |
| Radovi | master rad (48 strana, ćirilica i latinica iz istog izvora) → [radovi/master-rad/](radovi/master-rad/) · TELFOR 2026 (4 strane) → [radovi/telfor2026/](radovi/telfor2026/) |
| Lemljenje | dvije ploče (uređaj + mjerna) → [radno/elektronika/plan-dvije-plocice.md](radno/elektronika/plan-dvije-plocice.md) · crteži [radno/elektronika/sema-sklopa.pdf](radno/elektronika/sema-sklopa.pdf) |

Šta je urađeno i izmjereno, hronološki:
[docs/DNEVNIK-NEXT-LEVEL.md](docs/DNEVNIK-NEXT-LEVEL.md).
Putanja modela sa svim pokušajima i negativnim rezultatima:
[docs/put-do-modela.md](docs/put-do-modela.md).
Problemi i zamke (P1–P27): [docs/problemi-i-rjesenja.md](docs/problemi-i-rjesenja.md).
Mapa cijele dokumentacije, sa oznakom šta je aktuelno a šta istorijsko:
[docs/INDEKS.md](docs/INDEKS.md). Kontekst i pravila rada na projektu:
[KONTEKST.md](KONTEKST.md).

> **Granica tvrdnje.** FAN01, GUIDED25 i završna provjera tonom su stvarni
> ventilator, ali papirić i pušteni ton su kontrolisane promjene, ne potvrđeni
> kvarovi. Dokazano je da uređaj pouzdano prijavljuje **konstantnu akustičku
> promjenu** i da je razlikuje od govora i vrata; nije dokazano da je uzrok
> mehanički kvar — jedan mikrofon to ne može tvrditi. Lemljenje, I2S liveness,
> power-loss/NVS i samostalan demo bez PC-a i dalje nisu fizički potvrđeni.
> Benchmark, regresija i build nisu fizička tačnost.

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
radno/              odvojivo prije javnog repoa (radno/README.md)
  elektronika/      sklapanje, lemljenje, šeme, E5/INA226 energetski dio
  ucenje/           uputstva za razumijevanje projekta
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
i nabavka: [radno/elektronika/hardware.md](radno/elektronika/hardware.md).

## Ključne odluke (odstupanja od librosa/baseline — za pogl. 5 rada)

1. **center=False** u STFT (bez reflect paddinga) — na uređaju nema paddinga; PC
   pipeline identičan po konstrukciji. Gubi se ~2 rubna frejma po klipu.
2. **LOG_EPS = 1e-12** (float32-representable) umjesto `sys.float_info.epsilon`.
3. **Per-dimenziona standardizacija** (mean/std sa treninga, 640+640 float u flash)
   — pomaže i int8 kvantizaciji (uži dinamički opseg).
4. **Isti C kod featura na PC-u i uređaju** (ctypes test): razlika na realnim
   klipovima < 4e-5 dB — rizik B1 iz plana zatvoren po konstrukciji.
5. Gamma prag: momentna metoda + Wilson–Hilferty u C — poklapanje sa scipy < 2 %.
