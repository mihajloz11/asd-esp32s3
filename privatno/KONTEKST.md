# KONTEKST.md — kontekst projekta

Ovaj fajl je **ulazna tačka** u projekat. Cilj mu je da se rad nikad ne nastavi
od pogrešnog ili zastarjelog stanja.

**Revizija 06.09.2026.** Aktuelan pregled je u
[README-u](../README.md), [nalazima revizije](../results/repository_audit/2026-09-06/README.md)
i [preostalim stavkama](planovi/PREOSTALO.md). Stariji sažeci ispod ostaju kontekst
razvoja; kod i sirovi artefakti imaju prednost. Papirić ima GUIDED25 FAIL,
validna telemetrija nije prolaz probe, a oporavak nakon tona nije izmjeren.
Posljednji firmware se čuva bez izmjena i novih fizičkih proba.

---

## 1. Šta je projekat

Master rad: **nenadgledana detekcija anomalija zvuka mašina (ASD)** na
ESP32-S3-WROOM-1 N32R16V, uz DCASE 2026 Task 2 dev skup.

Finalni model je `psd_shape`: dugoročni spektar (FFT 8192) sažet u **96
logaritamskih traka 10–4000 Hz**, normalizovan po nivou, pa **Mahalanobis**
udaljenost od lokalnog centra u kovarijansi naučenoj na PC-u
(Ledoit–Wolf, 990 ispravnih source snimaka). Nema neuronske mreže, nema TFLM-a
u finalnom putu. Uređaj se sam kalibriše na ventilatoru koji nikad nije čuo i
sam javlja odstupanje, bez računara.

Metodologija i plan rada: [`plan-master-rada.md`](planovi/plan-master-rada.md).
Nepromjenjivi cilj modela: [`docs/cilj-modela.md`](../docs/cilj-modela.md).

---

## 2. Zlatna pravila — ovo se ne pregovara

Ovaj projekat je vođen strogom disciplinom dokaza. Ona je važnija od brzine.

1. **Softverski PASS nije fizički dokaz.** Zeleni testovi, uspješan build i
   veličina bina ne dokazuju ni flash, ni runtime, ni rad na ventilatoru.
   Nikad ne pisati „radi" za nešto što je samo host-testirano.
2. **Ne izmišljati i ne prepisivati brojke.** Svaka brojka u dokumentaciji mora
   imati izvor: log, artefakt u `results/`, test, ili upravo pokrenuta komanda.
   Ako brojka nije izmjerena, ne piše se.
3. **Prag se nikad ne podešava post-hoc.** Enter/exit pragovi se izvode iz
   normal-only DERIVE bloka i zamrznu prije VERIFY-a. Papirić i razgovor su
   readout, nikad ulaz u fit. Ako VERIFY padne, run je `reject` — prag se ne
   mijenja da bi run prošao.
4. **Target anomalije ne ulaze u fit.** Sve politike u `pc/config/*.json` moraju
   nositi `target_anomalies_used: false` ili `target_anomalies_used_for_fit:
   false`; CI to obara ako se promijeni.
5. **Fail-closed.** Nedostatak dokaza je `FAIL`, ne „vjerovatno prolazi".
   Nema „upozori pa svejedno nastavi kalibraciju" u finalnom putu — CI to grepuje.
6. **Granica tvrdnje se piše uz tvrdnju.** Model radi **za ventilator**;
   izmjereno je da ne generalizuje na svih 7 DCASE mašina. Papirić je
   kontrolisana promjena protoka, **ne potvrđen kvar**.
7. **Istorijski artefakti se ne prepravljaju.** Stari runovi u
   `results/physical_fan/` ostaju netaknuti; ispravke idu kao read-only recompute.
8. **Ne praviti novi „plan" ili „status" dokument** ako postojeći pokriva temu.
   Repo je već imao problem sa preklapajućim MD fajlovima. Ažurirati postojeći i
   datirati izmjenu.

---

## 3. Gdje je istina — hijerarhija dokumenata

Kad se dokumenti razilaze, **noviji datirani snapshot pobjeđuje**, a redoslijed
autoriteta je ovaj:

| Pitanje | Autoritativni izvor |
|---|---|
| Šta još treba uraditi | [`privatno/planovi/PREOSTALO.md`](planovi/PREOSTALO.md) |
| **Finalna validacija firmvera na pločici** | [`docs/rezultat-finalna-validacija-2026-08-27.md`](../docs/rezultat-finalna-validacija-2026-08-27.md) |
| Gdje je projekat sada, ukratko | [`README.md`](../README.md) |
| Konsolidacija svih faza poslije FAN01 | [`docs/DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md`](../docs/DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md) |
| Status kritičnih nalaza revizije | [`privatno/revizije/REVIEW-KRITICNO-2026-08-20.md`](revizije/REVIEW-KRITICNO-2026-08-20.md) |
| Zaključani protokol fizičkog runa | [`docs/protokol-fizicki-ventilator.md`](../docs/protokol-fizicki-ventilator.md) |
| Vođeni 25-minutni test | [`docs/GUIDED25-TEST-VENTILATORA.md`](../docs/GUIDED25-TEST-VENTILATORA.md) |
| Rezultat prvog fizičkog testa | [`docs/rezultat-fan01-2026-08-16.md`](../docs/rezultat-fan01-2026-08-16.md) |
| Sve zamke koje su već koštale vremena (P1–P28) | [`docs/problemi-i-rjesenja.md`](../docs/problemi-i-rjesenja.md) |
| Hronologija svega urađenog | [`privatno/dnevnici/DNEVNIK-NEXT-LEVEL.md`](dnevnici/DNEVNIK-NEXT-LEVEL.md), [`privatno/dnevnici/dnevnik-projekta.md`](dnevnici/dnevnik-projekta.md) |
| Elektronika i lemljenje | [`privatno/elektronika/plan-dvije-plocice.md`](elektronika/plan-dvije-plocice.md) + `privatno/elektronika/sema-sklopa.pdf` |

**Puni indeks sa oznakom aktuelno/istorijsko:** [`docs/INDEKS.md`](../docs/INDEKS.md).

Dokumenti sa banerom „ISTORIJSKI" na vrhu (`PLAN.md`, `PLAN-NEXT-LEVEL.md`,
`PLAN-ZAVRSNICA.md`, `sazetak-za-mentora.md`, `edge-adaptacija.md`,
`rad-poglavlje-3-teorija.md`, `analiza-stanja-i-sljedeci-koraci-2026-08-09.md`)
su **istraživački trag, ne današnja TODO lista**. Iz njih se ne izvlači trenutni status.

---

## 4. Provjereno stanje (27.08.2026)

Ovo je izmjereno, ne prepisano:

| Stavka | Vrijednost | Kako je provjereno |
|---|---|---|
| PC test suite | **478 passed** | `python -m pytest pc/tests -q` (mašina sa `data/`) |
| Schema/politike saglasne | PASS, `asd-quality-v1.6.0` | `python pc/tools/check_schema_consistency.py` |
| Build | 354 784 B, SHA-256 `9ac2caca…8d967813` | `provenance.json` oba validna runa |
| Fizički dokaz | **dva `valid_physical_result` runa 27.08.** | `results/physical_fan/run_20260827T213148_*`, `run_20260827T220338_*` |

**Firmware je funkcionalno završen i potvrđen na pločici.** Uređaj se sam
kalibriše, sam izvodi prag iz normal-only prozora, odbija nepouzdan prozor
(`OBSERVATION_HOLD`) i prijavljuje konstantnu promjenu (`ANOMALY`,
`ANOMALY_SUSTAINED`). Detalji i sve granice:
[`docs/rezultat-finalna-validacija-2026-08-27.md`](../docs/rezultat-finalna-validacija-2026-08-27.md).

Ono što je i dalje **nedokazano** (i mora ostati tako napisano):

- taster, dvije LED i otpornici **nisu zalemljeni**;
- commissioning pragovi su i dalje `DEVELOPMENT` — pravilo je potvrđeno na dva
  runa, ali zamrzavanje za proizvodnju traži bump verzije i novi
  preregistrovani retest;
- GUIDED25 papirić kapija daje `1/3` i FAIL; ručna nestabilnost je moguće
  objašnjenje, bez izolovanog dokaza uzroka; **prag se zbog toga ne pomjera**;
- oporavak poslije jakog stimulusa nije izmjeren — run B je završen dok je skor
  bio između izlaznog i ulaznog praga;
- I2S liveness, power-loss i NVS persistence nisu fizički testirani;
- E5/INA226 strujni put nije završen; mjerni firmware je napisan 21–22.09.2026.
  na grani `measurement/e5-ina226`, ali nije flešovan ni mjeren na ploči;
- samostalan demo bez PC-a nije odrađen.

---

## 5. Komande

Razvoj je **Windows-native** (ESP-IDF, PowerShell, `.venv`), i CI je namjerno
`windows-latest`. Host testovi rade i na Linuxu (C parity gradi `.so` umjesto `.dll`).

```powershell
# Windows, iz korijena repoa
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt   # puni (TensorFlow)
# ili samo ono što testovi traže:
.\.venv\Scripts\python.exe -m pip install -r pc\requirements-ci.txt

.\.venv\Scripts\python.exe -m pytest pc/tests -q                # host + C parity
.\.venv\Scripts\python.exe pc\tools\check_schema_consistency.py # verzije politika
```

C parity testovi traže **gcc u PATH-u** (`winget install -e --id
BrechtSanders.WinLibs.POSIX.UCRT`, ili MinGW-w64 kao u CI-ju).

DCASE 2026 dev skup: 7 zipova sa <https://zenodo.org/records/19336329>, raspakovati u
`data/dcase2026_dev/<masina>/{train,test}`. `data/` je gitignorovan.

Trening/evaluacija/artefakti za firmware: vidi „Workflow" u [`README.md`](../README.md).

Fizički vođeni test: `POKRENI-GUIDED25.cmd` → `pc/tools/guided25_launcher.ps1`;
uputstvo za operatera u
[`docs/KAKO-SAMOSTALNO-POKRENUTI-GUIDED25.md`](../docs/KAKO-SAMOSTALNO-POKRENUTI-GUIDED25.md).

---

## 6. Struktura

```
pc/asd/         paket: features, data, model, train, eval, quantize,
                runtime_protocol, guided_test, commissioning_policy
pc/tools/       generatori C headera, benchmarci, host eksperiment
                (physical_fan_experiment.py, asd_panel.py, evaluate_canonical.py)
pc/config/      zaključane politike (*.json) — CI provjerava saglasnost sa firmverom
pc/tests/       host testovi + PC↔C parity preko ctypes
firmware/esp32s3_asd/main/   ESP-IDF v5.x izvori
docs/           dokumentacija (vidi docs/INDEKS.md)
models/         PSD .npz/meta + istorijski .keras/.tflite artefakti
results/        results.csv, logovi, fizički runovi, kanonska evaluacija
data/           DCASE 2026 dev skup (gitignored)
privatno/       lično, ne ide uz predaju: KONTEKST, planovi, dnevnici, revizije,
                učenje, elektronika, fotografije; vidi privatno/README.md
radovi/         rukopisi (master, TELFOR); ne ide uz predaju dok nisu objavljeni
```

Finalni put u firmveru je `psd_live.c` + `psd_features_c.c` +
`asd_commissioning.c` + `asd_events.c` + `asd_operator.c` + `asd_temporal.c` +
`audio_i2s.c` + `audio_quality_state.c` + `asd_profile_*`.
`live_adapt.c`, `live_capture.c`, `eval_mode.c`, `tflm_infer.cc` su **stariji
demo/TFLM modovi** — čuvaju se zbog ranijih mjerenja, ne uvoze se u finalni tok
i **nisu uzor za novi kod**.

---

## 7. Firmware build modovi

Bira se env varijablom, iz `firmware/esp32s3_asd/main/CMakeLists.txt`:

| Env var | Šta radi |
|---|---|
| `ASD_PSD_LIVE` | **finalni** samostalni PSD detektor |
| `ASD_RESEARCH_TELEMETRY` | `96 + 5×96` sidecar preko UART-a; samo uz `ASD_PSD_LIVE` |
| `ASD_PSD_VERIFY` | PC↔uređaj parity PSD front-enda |
| `ASD_MIC_TEST` | bring-up mikrofona |
| `ASD_INA_TEST` | INA226 / potrošnja |
| `ASD_EVAL_MODE` | klipovi sa flash particije (istorijski) |
| `ASD_LIVE_CAPTURE`, `ASD_LIVE_ADAPT` | stariji demo modovi (istorijski) |

⚠ **Pri svakoj promjeni moda obavezan `idf.py reconfigure`** — `if(DEFINED
ENV{...})` se evaluira samo pri konfiguraciji, inače build tiho ostane u starom
modu. To je P2 i već je koštalo vremena.

```bash
cd firmware/esp32s3_asd
idf.py set-target esp32s3      # glavna platforma (N32R16V)
# ili: idf.py set-target esp32  # DevKit V1 — E4 kontrola, bez PIE/PSRAM
idf.py reconfigure build flash monitor
```

Zabranjeni pinovi: S3 GPIO 35/36/37 (oktalni PSRAM), ESP32 GPIO 6–11 (flash).
Per-target pinovi u `main/pins.h`, konfiguracija u `sdkconfig.defaults.<target>`.

---

## 8. Verzije protokola

Aktuelni par: host `physical-fan-v1.9.0` / `physical-fan-artifacts-v1.9.0` ↔
live `asd-quality-v1.6.0` (policy ID `0x51555632`).

Offline čitanje **mora ostati unazad kompatibilno** za istorijske parove:
v1.6↔q1.3, v1.7↔q1.4, v1.8↔q1.5. Ne brisati stare grane parsiranja — istorijski
runovi u `results/physical_fan/` se čitaju njima. Isto važi i za `THRFIT`
rječnik: firmware ga više ne emituje, ali runovi 26–27.08. ga sadrže.

Svaka promjena politike ili praga traži **bump verzije i novi preregistrovani
retest**, ne tihu izmjenu brojke.

---

## 9. CI kapije (`.github/workflows/ci.yml`)

Tri joba na `windows-latest`:

1. **tests** — `pytest pc/tests -q` uz `pc/requirements-ci.txt` (namjerno bez
   TensorFlow-a) i gcc za C parity.
2. **schema** — `check_schema_consistency.py`, bez ijedne zavisnosti.
3. **antipatterns** — grep kapije nad **finalnim putem**: nema „warn and
   continue", nema pomjeranja centra tokom detekcije (P10), nema politike koja
   tvrdi da koristi target anomalije; plus trailing whitespace i markeri konflikta.

CI **ne dokazuje** ništa fizičko i to je eksplicitno zapisano u samom workflowu.

---

## 10. Jezik i stil

- Dokumentacija i komit poruke su na **srpskom, ijekavica, latinica**.
- Komit poruke opisuju **šta je postignuto i šta je izmjereno**, ne spisak fajlova.
- U MD fajlovima dva razmaka na kraju reda su namjeran prelom (CI ih ne dira).
- U kodu: bez trailing whitespace-a (CI obara), komentari objašnjavaju **zašto**,
  ne šta — postojeći kod ima gustu „zašto" kulturu komentara, prati je.

---

## 11. Zamke koje su već koštale vremena

Puna lista je P1–P28 u [`docs/problemi-i-rjesenja.md`](../docs/problemi-i-rjesenja.md).
Najskuplje:

- **P2** promjena build moda bez `reconfigure` → build tiho ostane u starom modu;
- **P4** task watchdog upisuje tekst usred base64 toka → pokvaren WAV;
- **P10** kalibracija nauči ventilator laptopa kao „normalno stanje";
- **P11** jednostrani prag propušta pola promjena — prag je dvostran;
- **P15** tranzijent pri uključenju mikrofona ruši prvi blok;
- **P17** prag se između dvije kalibracije razlikovao 16×;
- **P19** sopstveno računanje na laptopu kontaminiralo probu lažnih alarma;
- curenje u mjerenju: kovarijansa učena i ocjenjivana na istim klipovima → 0,96
  umjesto 0,758. Uvijek razdvojiti korpus za učenje od skupa za ocjenu;
- `git add -A` je jednom pokupio 1,2 GB keša featura — provjeri `git status`
  prije dodavanja.
