# Dnevnik projekta — ASD na ESP32-S3

> Živi dokument. Ovdje se bilježi SVE: šta je urađeno, rezultati, očekivano vs
> dobijeno, zaključci, alternative koje smo odbacili (i zašto), bugovi i pouke.
> Ažurira se uz svaki radni blok. Referenca za povratak u bilo koju tačku.
> Format zapisa: datum → šta → rezultat → zaključak/odluka.

---

## STANJE (zadnje ažuriranje: 19.07.2026)

| Oblast | Status |
|---|---|
| PC pipeline (featuring, trening, eval, PTQ int8) | ✔ kompletan, testiran |
| E1 (reprodukcija baseline-a) | ✔ fan hmean 0.540 — u rangu DCASE brojeva |
| E2 (Pareto sweep, 7 mašina × 5 varijanti) | ✔ kompletan (1 seed) |
| E3 (int8 ΔAUC) | ✔ kompletan — degradacija ≈ 0 svuda |
| MAHALA scoring (7 mašina × 5 varijanti) | ✔ — pomaže na 5/7 mašina |
| Firmware (streaming, oba targeta) | ✔ builduje se bez grešaka |
| **On-device verifikacija (uređaj == PC)** | ✔ **max rel razlika 1.5e-04** |
| E4 latencija | ✔ KOMPLETNO: S3 vs ESP32 2.76× (platforma); esp-nn on/off na S3 1.33× (čist PIE) — results/e4_latency.md |
| Puna on-device AUC | ✔ 60 klipova na S3: AUC 0.596, score-ovi vs PC max 2.2e-04 |
| E6 on-device gamma prag | ✔ device 0.77090 vs PC 0.77064 = rel 0.03% — kalibracija radi na čipu |
| E5 energija | čeka INA226 (naručuje se) |
| Živi zvuk | čeka INMP441 (naručuje se) |
| E6 on-device gamma kalibracija | C kod ✔ + PC test ✔; on-device test čeka |
| 5-seed finalne tabele | alati ✔; treninzi nisu pušteni |
| Pisanje rada | sažetak za mentora ✔ (čeka slanje); poglavlja nisu počela |

**Git tagovi:** `setup-v1` → `e1-e3-fan` → `mahala-fan` → `e1-e3-all-machines` →
`mahala-all` → `on-device-verified`

---

## HRONOLOGIJA

### 17.07 — Postavka i PC pipeline (plan sekcije 4–5)

**Urađeno:** git repo; Python 3.11 venv (TF 2.20, librosa, scipy...); DCASE 2026
dev dataset (7 zipova, 4.6 GB, Zenodo 19336329) skinut i raspakovan; kompletan
`pc/asd` paket (features → data → model → train → eval → quantize); generatori
C headera (mel sparse 3.9 KB, model, norm); ESP-IDF firmware skeleton (I2S
INMP441, portabilni log-mel u C, TFLM, gamma kalibracija, pin-plan); PC↔C unit
testovi preko ctypes (WinLibs GCC preko winget-a).

**Ključne odluke (sa alternativama):**
- **Featuring = JEDAN C kod, testiran na PC-u preko ctypes.** Alternativa je
  bila dvije nezavisne implementacije + poređenje — odbačeno jer je to izvor
  rizika B1 (najčešći uzrok pada AUC na uređaju). "Nuklearna opcija" iz plana
  usvojena od starta.
- **center=False u STFT** (librosa default je reflect padding) — uređaj nema
  padding; PC namjerno isti. Gubi se ~2 rubna frejma po klipu. Dokumentovano
  odstupanje od zvaničnog baseline-a.
- **LOG_EPS = 1e-12** umjesto sys.float_info.epsilon (float32-representable).
- **Per-dimenziona standardizacija** (nije u zvaničnom baseline-u) — pomaže
  int8 kvantizaciji; rizik po E1 poređenje prihvaćen i dokumentovan.
- **Slaney mel iz librosa.filters.mel** eksportovan u C header — ista matrica
  na obje strane po konstrukciji (alternativa HTK formule odbačena — baseline
  koristi librosa/Slaney).

**Rezultati testova:** PC↔C featuri na realnom klipu **3.8e-05 dB** max razlike
(kriterijum 1e-3); čisti sinusi 1e-3–4e-3 — razlika živi u FFT error flooru
ispod −100 dB, nebitno za realan zvuk (dokumentovano u testu). C gamma
kalibracija vs scipy < 2 %. Streaming == batch **bit-identično** (0.0).

**Bugovi/pouke:** cp1252 encoding pri pisanju headera (fix: utf-8 eksplicitno);
`%.9g` daje `0f` — nevalidan C literal (fix: dodaj `.0`); prazan string kao
gcc argument na Windowsu; PS 5.1 čita ps1 kao cp1252 → em-dash lomi parser
(pouka: **ps1 fajlovi samo ASCII**).

### 17–18.07 (noć) — E1–E3 fan + streaming arhitektura

**Urađeno:** pun sweep fan (5 varijanti × 100 epoha + PTQ int8); MAHALA na svih
5 fan modela; streaming API u features_c (hop-po-hop, <25 KB RAM) + bit-test;
per-target pins.h i sdkconfig (S3 + klasični ESP32); docs (hardware,
edge-adaptacija, šema povezivanja md+svg); teorija-ucenje.html; dashboard
(statični + live server na :8765); eval mod firmvera (WAV parser + FAT);
prepare/compare_eval alati; sažetak za mentora; 5-seed alati.

**Odluke:**
- **Streaming umjesto batch obrade na uređaju** — batch traži 640 KB za klip
  (ne staje bez PSRAM-a); streaming omogućava identičan firmware na klasičnom
  ESP32 (E4 kontrola). Bit-jednakost dokazana testom.
- **Telefon kao Wi-Fi mikrofon: ODBAČENO za eksperimente** (AGC/NS boji signal,
  ruši offline priču, Wi-Fi kvari E5); prihvaćeno kao demo mod za odbranu
  (future-work, ~1 dan, septembar). Isto za on-device live dashboard (~2 dana,
  septembar, SoftAP + WebSocket — dizajn skiciran u future-work.md).
- INA226 umjesto INA219 (16-bit, brži sampling) — KP Kikinda 270 din.

### 18–19.07 (noć) — svih 7 mašina

**Urađeno:** sweep queue za preostale mašine; MAHALA za sve; dedup slider
duplikata (dva paralelna reda — vidi pouke); finalne tabele + Pareto grafovi.

**Pouke o procesu:** PowerShell `*>>` piše UTF-16 → bash `grep` i Python
`utf-8` čitanje tiho ne vide sadržaj (fix: BOM detekcija svuda); detached
watcher procesi znaju umrijeti tiho — pratiti kroz tracked background taskove
ili monitor; jedan izvor istine za red čekanja (duplikat slider sweep-a jer su
dva reda radila paralelno).

### 19.07 — Deployment na stvarni hardver

**Urađeno:** ESP-IDF v5.5 instaliran (`~\esp\esp-idf`, targeti esp32+esp32s3);
build iz prve (1505/1505, binarka 425 KB); flash na S3 (COM4, CH343); boot čist;
16 fan klipova na FAT particiju (fatfsgen + parttool); eval mod end-to-end;
poređenje sa PC referencom; teorija-ucenje.html dopunjen (sekcije 12–13).

**Rezultati (mjereno na pločici):**
- `Found 16MB PSRAM` — OCT config ispravan iz prve (rizik C3 nije se desio)
- **TFLM arena: 7 960 B** (plan procjenjivao 50–150 KB → stvarnost 7.9 KB!)
- Latencija po 10 s klipu: **featuring 665 ms + inferenca ~870 ms** (307
  vektora; ~5 ms po vektoru ukupno) → 15 % realnog vremena, 7× rezerva
- dropped=0 (ring buffer dizajn stiže)
- Bez mikrofona: score 690 vs prag 0.78 → ANOMALIJA — ispravno (I2S šum nije
  naučeni zvuk)
- **Poklapanje uređaj vs PC: max relativna razlika 1.5e-04 na 16/16 klipova**
  (prag 1e-3) — SVE PC tabele važe za hardver. Milestone sedmice 6 plana
  postignut prije zvaničnog starta.

**Bug nađen (vrijedan za rad):** DCASE 2026 klipovi su **stereo** (blizu/daleko
par iz noise-aware postavke) — PC pipeline tiho uzima kanal 0, a prvi FAT image
je nosio originalne stereo fajlove → eval parser (s provjerom formata) odbio
sve sa tačnim razlogom za sekundu. Fix: prepare_eval_clips konvertuje u mono
kanal 0. Pouka = zlatno pravilo 1 (testiraj sloj po sloj) radi u praksi.

---

### 19.07 — E4 klasični ESP32 (DevKit V1, ESP32-D0WD-V3, COM5/CP2102)

Flešovan isti eval firmware (`set-target esp32`, 4 klipa na 1.4 MB FAT). Score-ovi
**bit-identični** S3/PC-u → korektnost cross-platform. Latencija (po 10 s klipu):
S3 665+870 ms vs ESP32 1095+3140 ms → **S3 2.76× brži ukupno, 3.6× na inferenci**
(esp-nn PIE int8). Arena 7960 B na oba. Detalji: results/e4_latency.md.
Zaključak: čak i klasični ESP32 bez PSRAM-a nosi model komotno (42 % real-time).

### 19.07 — E4 dovršen + puna on-device AUC (#2) + E6 (#3)

**esp-nn on/off na S3 (čist PIE):** inferenca 870 ms (asm) vs 1157 ms (ANSI C) =
**1.33×**. Razdvaja PIE (1.33×) od pune platformske razlike prema klasičnom
ESP32 (3.6×). Featuring nepromijenjen (FFT je naš kod, ne esp-nn).

**#2 Puna on-device AUC:** 60 fan klipova (30 normal + 30 anomalija, source+target)
na S3 20 MB FAT particiji. Device AUC = **0.596**, score-ovi vs PC max razlika
**2.2e-04** → hardver reprodukuje PC na PUNOM setu, ne samo na 16 verifikacionih.

**#3 E6 on-device kalibracija:** uređaj SAM fitovao gamma prag iz 30 normalnih
score-ova (momentna metoda + Wilson–Hilferty u C): **0.77090** vs PC gamma na
istim klipovima **0.77064** = **rel 0.03 %**. On-device adaptacija bez clouda
dokazana na hardveru — E6 iz "stretch" prešao u "urađeno". Kod: eval_mode.c
akumulira klipove s prefiksom 'n', ispisuje E6CALIB liniju.

## REZULTATI — GLAVNE TABELE (1 seed; finalno ide 5 seedova)

### hmean po mašini (baseline / najbolji tiny, MSE fp32)

| | fan | bearingEmu | gearboxEmu | sliderEmu | ToyCar | ToyCarEmu | valveEmu |
|---|---|---|---|---|---|---|---|
| baseline (270k) | 0.540 | 0.584 | 0.516 | 0.529 | 0.370 | 0.550 | 0.616 |
| najbolji tiny | 0.525 (t64) | 0.582 (t32) | 0.532 (t64) | 0.532 (t64) | 0.382 (t32) | 0.535 | 0.573 (t64) |

### Zaključci (redom po snazi)

1. **int8 PTQ je besplatan** za dense AE: ΔhMean ∈ [−0.005, +0.011] preko svih
   35 kombinacija. Očekivanje (plan): degradacija neuniformna po mašinama —
   dobijeno: uniformno ≈ 0. Jači rezultat od očekivanog.
2. **Pareto je plitka**: 12× manji model gubi 2–3 p.p. Bottleneck bitniji od
   širine (tiny32b4 < tiny32 uz isti broj parametara).
3. **MAHALA pomaže na 5/7 mašina** (fan target +6 do +10 p.p.!), škodi na
   sliderEmu (−2) i ToyCarEmu (−5) → backend birati po mašini. Na malom modelu
   MAHALA zna nadoknaditi gubitak od smanjivanja (fan tiny16+MAHALA ≈
   baseline+MSE). Izvodljivo on-device (cov 640×640 = 1.6 MB u PSRAM).
4. **ToyCar = studija slučaja domain shifta**: source 0.79, target 0.25 (ispod
   slučajnosti — target-normalno "anomalnije" od anomalija). Očekivano po
   literaturi da je teško; OVOLIKI raspad je nalaz za diskusiju.
5. **valveEmu neočekivano najbolja** (0.616) — plan (A2) je predviđao da je
   valve najteža za AE. Emu varijanta 2026 očito drugačija od klasičnog valve.
   → provjeriti protiv zvaničnih baseline tabela kad budu objavljene.

### Otvorena pitanja / za provjeru

- [ ] ToyCar 0.37 i valveEmu 0.616 — uporediti sa zvaničnim DCASE 2026 baseline
      brojevima (E1 formalna potvrda)
- [ ] MAHALA za int8 modele (sad je samo fp32) — da li uplift preživi kvantizaciju?
- [ ] Device AUC na punom test setu (~60 klipova staje na 20 MB particiju;
      16 je bilo samo za verifikaciju poklapanja)
- [ ] 5 seedova za finalne tabele (mean±std)

---

## SLJEDEĆI KORACI (prioritet)

1. **Mihajlo:** poslati sažetak mentoru (docs/sazetak-za-mentora.md) — kritični put
2. **Mihajlo:** naručiti 2× INMP441 + INA226 (docs/hardware.md, KP linkovi)
3. Klasični ESP32 build + flash (`set-target esp32`) → prva polovina E4 matrice
   (PIE ablation: S3 esp-nn vs ESP32 generic)
4. esp-nn on/off na samom S3 (Kconfig) → druga polovina E4
5. 5-seed treninzi preko noći (run_sweep -Seed 1..4)
6. Kad stigne INMP441: živi audio lanac (test: WAV snimak u Audacity — rizik C1)
7. Kad stigne INA226: E5 energija (šema u docs/sema-povezivanja.md)
8. Pisanje: poglavlje 2 (pregled literature) i 3 (teorija) — materijal spreman
   u teorija-ucenje.html

## ARTEFAKTI — GDJE JE ŠTA

- `pc/asd/` — pipeline; `pc/tools/` — generatori, dashboardi, eval, stats
- `pc/run_sweep.ps1` — E1–E3 za mašinu; `pc/tests/` — PC↔C testovi
- `firmware/esp32s3_asd/` — kompletan firmware (build: export.bat pa idf.py)
- `results/results.csv` — svi brojevi; `results/dashboard.html` — pregled;
  live: `python tools/live_dashboard.py` → :8765
- `docs/` — hardware, šema povezivanja, edge-adaptacija, teorija (HTML),
  sažetak za mentora, ovaj dnevnik
- ESP-IDF: `%USERPROFILE%\esp\esp-idf` (v5.5); eval build: `set ASD_EVAL_MODE=1`
- Eval poređenje: prepare_eval_clips.py → fatfsgen → parttool → serial capture
  → compare_eval.py
