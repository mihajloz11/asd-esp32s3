# Dnevnik projekta — ASD na ESP32-S3

> Živi dokument. Ovdje se bilježi SVE: šta je urađeno, rezultati, očekivano vs
> dobijeno, zaključci, alternative koje smo odbacili (i zašto), bugovi i pouke.
> Ažurira se uz svaki radni blok. Referenca za povratak u bilo koju tačku.
> Format zapisa: datum → šta → rezultat → zaključak/odluka.

---

## STANJE (zadnje ažuriranje: 06.08.2026)

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
| **Hardver (INMP441, INA226, AMS1117, pasive, demo)** | ✔ **stigao 04.08.2026** — vidi docs/hardver-lista.md |
| E5 energija | hardver na stolu; **blokira INA226 I2C drajver** (ne postoji u firmware-u) |
| **Živi zvuk (INMP441 na S3)** | ✔ **06.08 — mikrofon radi**, rms 158.7 / peak 1020 / clipped 0 / dropped 0; WAV verifikovan sumom |
| Rizik C1 (`>>14` shift) | ✔ zatvoren mjerenjem sirovog 32-bit peaka — 15.6 dB rezerve do klipovanja |
| **PC↔uređaj na živom mikrofonu** | ✔ **06.08 — rel. razlika 7.99e-05** (ranije samo nad klipovima s flasha) |
| Prilagođavanje praga okruženju | ✔ radi na čipu (0.779 → 62.46, bez lažnih uzbuna); ograničenje: drift okruženja naduvava prag |
| E5 energija | **blokirano hardverski** — INA226 ne odgovara na I2C, vidi ina226-provjera.md |
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

### 19.07 — PC-strana bez hardvera (5-seed, MAHALA-int8, pisanje)

**MAHALA-int8** (tools/score_mahala_int8.py): GOTOVO za svih 35 modela.
**Zaključak: MAHALA uplift potpuno preživljava int8** — razlika MAHALA int8 vs
fp32 po mašinama (baseline) u opsegu [−0.003, +0.003], tj. u šumu:

| mašina | MSE fp32 | MAHALA fp32 | MAHALA int8 | int8−fp32 |
|---|---|---|---|---|
| fan | 0.5405 | 0.5553 | 0.5577 | +0.0024 |
| bearingEmu | 0.5836 | 0.5888 | 0.5878 | −0.0010 |
| gearboxEmu | 0.5162 | 0.5440 | 0.5439 | −0.0001 |
| sliderEmu | 0.5292 | 0.5092 | 0.5101 | +0.0009 |
| ToyCar | 0.3698 | 0.4077 | 0.4107 | +0.0030 |
| ToyCarEmu | 0.5497 | 0.5042 | 0.5012 | −0.0030 |
| valveEmu | 0.6158 | 0.6367 | 0.6360 | −0.0007 |

Znači: i "pametni" backend (Mahalanobis, sa kovarijansom fitovanom na fp32
greškama) radi na int8 modelu bez gubitka → int8 je kompletno bezbjedan za
deployment, ne samo za MSE nego i za MAHALA. Dashboard regenerisan.

**5-seed finalne tabele:** seed_queue.ps1 pokrenut (čeka MAHALA-int8 da izbjegne
konflikt upisa u results.csv) — fan seeds 1-4 prvo (kompletan 5-seed za fan),
zatim ostale mašine preko noći. Agregacija: tools/results_stats.py (mean±std + LaTeX).

**Pisanje:** draft poglavlja 2 (pregled literature) i 3 (teorija) — docs/
rad-poglavlje-2-pregled.md, rad-poglavlje-3-teorija.md. HTML pregled cijelog
projekta (plan vs urađeno, hronologija, hardver planovi): docs/pregled-projekta.html.

### 20.07 — fan 5-seed komplet GOTOV (mean ± std)

Prva mašina sa punih 5 seedova (int8, MSE). Niska varijansa = pouzdani brojevi:

| Varijanta | hmean (mean ± std, n=5) | min–max |
|---|---|---|
| baseline | **0.543 ± 0.006** | 0.537–0.550 |
| tiny64 | 0.526 ± 0.003 | 0.523–0.530 |
| tiny32 | 0.517 ± 0.002 | 0.513–0.519 |
| tiny16 | 0.513 ± 0.003 | 0.510–0.517 |
| tiny32b4 | 0.511 ± 0.006 | 0.503–0.520 |

std ≤ 0.006 svuda → jednoseed brojevi su bili reprezentativni; Pareto poredak
stabilan (baseline > tiny64 > tiny32 > tiny16 ≈ tiny32b4). Za rad: ove ± vrijednosti
idu u finalnu tabelu. Ostale 6 mašina 5-seed = opciono (dugo, preko noći uz
wakelock). Agregacija: results/results_stats.csv (tools/results_stats.py).
Napomena: seed run pao prvi put (laptop sleep) — riješeno keep_awake.ps1 wakelockom.

### 04.08 — HARDVER STIGAO (kompletna porudžbina elektromodul.rs)

**Isporučeno sve sa spiska, 3.118 RSD** (2.578 roba + 540 dostava, ~27 €) — u budžetu
plana (≤18 € je bila stara procjena bez E5/demo dijela; sa AMS1117 i demo komponentama
ispalo 27 €). Detaljan inventar: docs/hardver-lista.md.

2× INMP441, 1× INA226, set od 120 elektrolita, 3× keramika 470 nF, AMS1117 3.3 V LDO,
2× muška pin letvica 40 pin, prototipna ploča 4×6, LED crvena + zelena, arkadni taster
30 mm. **Jedino odstupanje:** taster je isporučen plavi (SKU A4059) umjesto crvenog —
isti mikroprekidač, bez uticaja na šemu ni kod.

**Napisan docs/lemljenje.md** — procedura u dvije faze: faza 1 samo headeri (~19 spojeva:
2×6 na mikrofone, 4 na INA226, 3 na AMS1117) da moduli uđu u MB-102; faza 2 finalni
zalemljeni sklop na ploči 4×6 tek pošto cijeli lanac proradi na breadboardu. Kondenzatori,
LED i otpornici se do tada samo ubadaju.

**Tri stvari koje su ispale iz nabavke (blokiraju dijelove demoa):**
1. **Otpornici 220–330 Ω za LED nisu kupljeni** — bili su na spisku "iz firme". Do tada
   LED se ne smije vezati na GPIO. *(Usput: sema-povezivanja.md piše 220 Ω, a
   porudzbina-elektromodul.md 330 Ω — oba rade, nesklad nije ispravljan.)*
2. **Ženski headeri nisu naručeni** — na ploči 4×6 moduli bi išli fiksno zalemljeni.
   Ako INMP441 treba da ostane vadiv, dokupiti (~30 din) prije faze 2.
3. **Firmware pali samo jednu LED (GPIO 2)** — kupljene su dvije (crvena + zelena), ali
   za obje treba 2. pin (GPIO 11) + izmjena u app_main.c. Za sad ide jedna.

**Zaključak / redoslijed:** kritični put više nije nabavka nego (a) lemljenje 6 pinova na
prvi INMP441 → test 5 s WAV u Audacity (rizik C1), i (b) **INA226 I2C drajver — i dalje ne
postoji u firmware-u**, pa E5 ne može ni da počne iako je senzor na stolu. Pinovi za I2C
su definisani (8/9 na S3), ali nema koda za čitanje struje. To je sad jedini softverski
blokator E5, procjena ~pola dana.

### 06.08 — ŽIVI MIKROFON RADI (rizik C1 zatvoren)

**Urađeno:** headeri zalemljeni (S3, oba INMP441, INA226); INMP441 #1 spojen na
breadboard (BCLK 4, WS 5, SD 6, VDD 3V3, L/R→GND); firmware rebuildovan u živi
mod i flešovan; napisan **mic bring-up mod** (`main/mic_test.c`, ulaz preko
`ASD_MIC_TEST=1`) + PC alat `pc/tools/mic_capture.py`.

**Mic test radi u dvije faze:** 8 s mjerač nivoa sa bar-grafom (RMS/peak/DC svakih
250 ms — odmah se vidi reaguje li mikrofon na kucanje), pa 5 s snimak u PSRAM →
statistika → base64 PCM preko UART-a → WAV na PC.

**Rezultat (snimak u sobi, 5 s):**

| veličina | vrijednost |
|---|---|
| rms | 158.7 (−46.3 dBFS) |
| peak | 1020 (−30.1 dBFS) |
| dc offset | −0.4 |
| clipped / dropped | 0 / 0 |
| zeros | 220 / 80 000 (prolasci kroz nulu, ne mrtva linija) |

Spektar snimka: širokopojasan sa dominantnim niskim frekvencijama (95 dB u
20–100 Hz) i padom ka 8 kHz (68 dB) — realan sobni šum, ne zaglavljena linija.
Kucanje po mikrofonu u mjeraču nivoa daje skok rms 40 → 211 i peak 146 → 6675.

**Rizik C1 (`>>14` shift) — zatvoren mjerenjem.** Dodato praćenje peaka sirovog
32-bitnog slota prije shifta. Kroz tri snimka: sirovi peak 89.064.960 / 54.037.376
/ 16.724.480 (27/26/24 od 31 bita) → 16-bit peak 5436 / 3298 / 1020, aritmetika se
poklapa tačno, `clipped=0` svuda, **15.6 dB rezerve** do klipovanja na najglasnijem
događaju. `>>14` ostaje; obrazloženje kompromisa u [problemi-i-rjesenja.md](problemi-i-rjesenja.md#p6).

**Bugovi nađeni i riješeni ovog bloka** (detaljno u problemi-i-rjesenja.md):
- **P2** — `idf.py build` je tiho zadržao eval mod jer se `if(DEFINED ENV{...})`
  evaluira samo pri konfiguraciji. Obavezan `idf.py reconfigure` pri promjeni moda.
- **P4** — task watchdog je upisivao svoj tekst **usred base64 toka** (dump traje
  19 s bez ustupanja procesora) → WAV pomjeren i pokvaren. Riješeno `vTaskDelay`
  svakih 16 linija + FNV-1a kontrolna suma.
- **P5** — prva verzija PC skripta je snimila neispravan WAV uz blago upozorenje.
  Sada ne piše izlaz ako provjera dužine ili sume padne.
- **P3** — bez mikrofona živi rad daje konstantan `score=690.88586` koji izgleda
  potpuno ispravno. Zabilježeno kao dijagnostički potpis mrtvog ulaza.

**Uveden [problemi-i-rjesenja.md](problemi-i-rjesenja.md)** — baza svih problema
(simptom → uzrok → rješenje → dokaz) i odbačenih ideja. Popunjava se uz svaki blok,
i za probleme riješene u 5 minuta.

**Sljedeće:** INA226 I2C drajver (spojiti samo VCC/GND/SDA 8/SCL 9 — struja kroz
IN+/IN− tek poslije), pa živi ASD rad sa LED-om kad stignu otpornici.

### 06.08 (nastavak) — ŽIVI ASD LANAC: PC↔uređaj na mikrofonu + prilagođavanje praga

INA226 odložen (čeka multimetar, vidi [ina226-provjera.md](ina226-provjera.md)),
pa je urađeno sve što zavisi samo od mikrofona.

**1. Živi rad, 60 s.** Prvi put pun lanac nad stvarnim zvukom umjesto klipova
sa flash particije:

```
score=21.45 / 21.25 / 24.66 / 24.70 / 43.97 / 43.58
feat=663 ms  inf=1055 ms  total=10049 ms  (307 vec)  dropped=0
```

Score se mijenja iz klipa u klip (za razliku od konstante 690.88586 bez
mikrofona), lanac stiže u realnom vremenu sa **5.8× rezerve**, nema dropova.

**2. PC↔uređaj na ŽIVOM zvuku — novo (`ASD_LIVE_CAPTURE` + `tools/live_compare.py`).**
Uređaj snimi klip, boduje ga svojim lancem, i pošalje isti snimak na PC:

| | |
|---|---|
| PC score | 27.27804947 |
| uređaj score | 27.27587128 |
| **relativna razlika** | **7.99e-05** |
| broj vektora | 307 = 307 |

Razlika u odnosu na raniju verifikaciju (1.5e-04): tamo su klipovi stizali na
uređaj kao **identični bajtovi** preko flash particije. Ovdje ulaz nastaje na
uređaju — kroz I2S, konverziju 32→16 bita i ring buffer — pa je provjeren i
taj dio lanca, koji do sada nikad nije bio pokriven.

**3. Prilagođavanje praga okruženju (`ASD_LIVE_ADAPT`).** Fabrički prag
(0.77863) izračunat je nad DCASE trening podacima i u stvarnoj sobi je
besmislen — score je reda desetica, pa sve postaje "anomalija". Uređaj je
30 × 2 s bodovao živi zvuk kao normalno stanje, fitovao gamma momentnom
metodom i uzeo p=0.99 percentil:

```
n=30  mean=28.967  sd=11.566  min=16.182  max=48.288
gamma fit: k=6.273  theta=4.618
NOVI PRAG: 62.459   [fabricki 0.779]
detekcija: 0/30 prozora oznaceno kao anomalija (bez laznih uzbuna)
```

**NALAZ ZA DISKUSIJU — okruženje nije stacionarno.** Score raste kroz cijeli
eksperiment: kalibracioni prozori 1–18 daju 16–24, prozori 19–30 daju 30–48,
a detekcija 41–55. Gamma fit pretpostavlja stacionarnost, pa je `sd` naduvana
driftom i prag je ispao viši nego što bi trebalo. Posljedica: nema lažnih
uzbuna, ali je **osjetljivost smanjena** — prava blaga anomalija bi prošla.

Praktična pouka za rad: kalibracija mora trajati preko reprezentativnog perioda
normalnog rada, ili se prag mora osvježavati klizno. Ovo je ograničenje metode,
ne implementacije.

**Otvoreno pitanje.** Da li drift dolazi iz sobe (klima, frižider, ventilator
laptopa) ili iz uređaja (zagrijavanje, ustaljivanje DC offseta mikrofona)?
Provjera: ponoviti kalibraciju dva puta zaredom — ako se ista putanja rasta
ponovi identično, uzrok je u uređaju, ne u okruženju.

**Novi build modovi** (svaki traži `idf.py reconfigure` pri promjeni, vidi P2):
`ASD_MIC_TEST` · `ASD_INA_TEST` · `ASD_LIVE_CAPTURE` · `ASD_LIVE_ADAPT` ·
`ASD_EVAL_MODE`.

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
2. ~~naručiti 2× INMP441 + INA226~~ ✔ **stiglo 04.08** (docs/hardver-lista.md)
3. **Mihajlo:** donijeti 2× otpornik 220–330 Ω s posla (jedino što fali za LED demo)
4. Zalemiti header na INMP441 #1 → živi audio lanac → test WAV u Audacity (rizik C1);
   procedura: docs/lemljenje.md
5. **Napisati INA226 I2C drajver** (~pola dana) — bez njega E5 ne kreće iako je senzor tu
6. Klasični ESP32 build + flash (`set-target esp32`) → prva polovina E4 matrice
   (PIE ablation: S3 esp-nn vs ESP32 generic)
7. esp-nn on/off na samom S3 (Kconfig) → druga polovina E4
8. 5-seed treninzi preko noći (run_sweep -Seed 1..4)
9. E5 energija: AMS1117 → INA226 → 3V3, USB otkačen (šema u docs/sema-povezivanja.md)
10. Pisanje: poglavlje 2 (pregled literature) i 3 (teorija) — materijal spreman
    u teorija-ucenje.html

## ARTEFAKTI — GDJE JE ŠTA

- `pc/asd/` — pipeline; `pc/tools/` — generatori, dashboardi, eval, stats
- `pc/run_sweep.ps1` — E1–E3 za mašinu; `pc/tests/` — PC↔C testovi
- `firmware/esp32s3_asd/` — kompletan firmware (build: export.bat pa idf.py)
- `results/results.csv` — svi brojevi; `results/dashboard.html` — pregled;
  live: `python tools/live_dashboard.py` → :8765
- `docs/` — hardware, hardver-lista (inventar), lemljenje, šema povezivanja,
  edge-adaptacija, teorija (HTML), sažetak za mentora, ovaj dnevnik,
  **problemi-i-rjesenja.md** (baza bugova i slijepih ulica)
- Mic bring-up: `set ASD_MIC_TEST=1` → `idf.py reconfigure build flash`, pa
  `python tools/mic_capture.py --port COM4 --out ../results/mic_test.wav`
  (⚠️ pri svakoj promjeni moda obavezan `reconfigure` — vidi problemi P2)
- ESP-IDF: `%USERPROFILE%\esp\esp-idf` (v5.5); eval build: `set ASD_EVAL_MODE=1`
- Eval poređenje: prepare_eval_clips.py → fatfsgen → parttool → serial capture
  → compare_eval.py
