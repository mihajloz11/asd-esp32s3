# Master rad — Detekcija anomalija zvuka mašina na ESP32-S3
## Kompletan plan: literatura, dataset, metode, implementacija, hardver, eksperimenti, timeline

**Radni naslov:** *Nenadgledana detekcija anomalija zvuka mašina na resursno ograničenim uređajima: kvantizacija, optimizacija i evaluacija na platformi ESP32-S3*

**Engleski (za prijavu/publikaciju):** *Unsupervised Anomalous Sound Detection for Machine Condition Monitoring on Resource-Constrained Devices: Quantization, Optimization and Evaluation on ESP32-S3*

---

## 1. Cilj, doprinos, benefit

### 1.1 Problem
Mašine (ventilatori, pumpe, ležajevi, reduktori, ventili) mijenjaju akustični potpis prije otkaza. Detekcija anomalija zvuka (ASD — Anomalous Sound Detection) je etablirana istraživačka oblast (DCASE Challenge Task 2, 2020–2026), ali se praktično sva istraživanja izvode na GPU/server klasi hardvera, često sa velikim ansamblima modela. Realna industrijska primjena traži suprotno: jeftin, autonoman senzorski čvor koji radi bez mreže i clouda.

### 1.2 Ključno istraživačko pitanje
> Koliko detekcione performanse (AUC/pAUC) DCASE-klase ASD sistema preživi migraciju na mikrokontroler sa 512 KB SRAM — i kakav je kvantitativni kompromis između tačnosti, memorije, latencije i energije?

### 1.3 Doprinosi rada (šta komisija dobija "za uhvatiti se")
1. **Sistematska evaluacija** DCASE ASD pristupa na MCU klasi hardvera — Pareto analiza tačnost ↔ memorija ↔ latencija ↔ energija (ne postoji u literaturi za DCASE domain-shift setup).
2. **Kvantizaciona studija**: fp32 → int8 (post-training quantization), gdje i koliko AUC degradira, po tipu mašine.
3. **Izmjeren efekat PIE SIMD instrukcija** ESP32-S3 naspram običnog ESP32 na identičnom kodu (esp-nn optimizovani kerneli on/off) — čist hardverski ablation.
4. **On-device kalibracija** (stretch): uređaj lokalno fituje statistiku anomaly score-a i prag odlučivanja na novoj mašini — adaptacija bez clouda.
5. **Open-source artefakt**: reproducibilan repo (PC trening pipeline + ESP-IDF firmware) — upotrebljiv i poslije odbrane.

### 1.4 Benefit / primjena
- Prediktivno održavanje: "akustični stetoskop" od ~15 € po mašini (HVAC, pumpne stanice, kompresori, proizvodne linije).
- Privacy + offline: zvuk ne napušta uređaj.
- Metodološki: uputstvo drugim istraživačima koliko "staje" ASD u dati memorijski/energetski budžet.

---

## 2. Pregled literature (šta postoji, šta je rupa)

### 2.1 DCASE Challenge Task 2 — temeljna linija radova (obavezno pročitati, hronološki)
| Godina | Fokus | Ključno za tebe |
|---|---|---|
| 2020 | Unsupervised ASD — samo normalni zvuci u treningu | Definicija problema, AE baseline, log-mel front-end |
| 2021 | Domain shift + domain adaptation | AE i MobileNetV2 (outlier-exposure) baseline |
| 2022 | Domain generalization | Isti prag za source i target domen; MIMII DG + ToyADMOS2 datasetovi |
| 2023 | First-shot: potpuno novi tipovi mašina | Realan deployment scenario |
| 2024 | First-shot, sakriveni atributi | AE baseline sa 2 moda: MSE i selektivni Mahalanobis |
| 2025 | First-shot, nastavak | Zadnja "klasična" godina |
| 2026 | Noise-aware: dvokanalni audio (blizu/daleko od mašine) | Aktuelni dataset; baseline MSE vs MAHALA mod |

Ključne činjenice iz baseline sistema (direktno preuzimaš metodologiju):
- **Front-end:** log-mel spektrogram, F = 128 mel filtera, STFT frame 64 ms, hop 50 %; P = 5 uzastopnih frejmova konkateniranih u ulazni vektor dimenzije D = 640.
- **AE baseline:** treniran minimizacijom MSE rekonstrukcije na normalnim zvukovima; anomaly score = greška rekonstrukcije (MSE mod) ili Mahalanobisova distanca (MAHALA mod).
- **Prag:** score-ovi normalnih klipova fituju se gamma raspodjelom; prag = 90. percentil. (→ ovo je tvoja on-device kalibracija u C-u, poglavlje 6.)
- **MobileNetV2 OE baseline:** klasifikator sekcija mašine, anomaly score = negativni logit tačne sekcije. (Za tebe: opciona druga arhitektura, ali AE je primaran.)
- **Metrike:** AUC (source/target domen posebno), pAUC (parcijalni AUC pri niskom FPR), zvanični skor = harmonijska sredina. Bitno: prag se NE tunira na test skupu.

### 2.2 Jače metode (za poglavlje "pregled stanja", ne moraš implementirati)
- Self-supervised klasifikacija + embedding backend (kNN / Mahalanobis / GMM preko embeddinga) — dominira challenge od 2022.
- STgram-MFN (ArcFace), kontrastivno predtreniranje (CLP-SCF), IDNN, Glow-based.
- Zaključak iz literature koji citiraš: nijedna arhitektura ne dominira na svim tipovima mašina — AE bolji na nekim (ToyCar, Slider), MobileNetV2 na drugim. To opravdava tvoj izbor jednostavnog, deployabilnog AE.

### 2.3 TinyML deployment prior art (tvoja direktna konkurencija — i zašto ne pokriva tvoju rupu)
| Rad | Šta je urađeno | Šta NIJE (tvoja rupa) |
|---|---|---|
| AE TinyML na Cortex-M4 (7.5 KB model, 256 KB SRAM) | Real-time AE anomaly detection na industrijskom zvuku | Bez DCASE protokola, bez domain-shift evaluacije, bez energetske Pareto analize |
| OutlierNets (686 param., 2.7 KB) | Ekstremno kompaktni conv-AE za MIMII | Deploy na Core i5 / Cortex-A72 — NIJE MCU klasa! |
| LSTM-AE urban noise na ESP32 (4 ms inferenca, ~0.27–0.33 W) | ESP32 deployment, kvantizacija | Urbani šum, ne mašine; bez DCASE metrika; bez S3/PIE analize |
| ArrythML (ESP32-S3, TFLM, ESP-IDF) | Metodološki šablon za S3 deployment | EKG domen — ali workflow (xxd → flash → TFLM) kopiraš |
| TinyML surveyi (2025/2026) | Mapiraju polje | Eksplicitno navode on-device adaptaciju i energetsko profilisanje kao otvorene probleme |

**Formulacija rupe (za uvod rada):** postoje (a) DCASE ASD metode evaluirane na GPU i (b) ad-hoc TinyML audio deploymenti bez DCASE rigora. Ne postoji sistematska studija koja DCASE protokol (domain shift, AUC/pAUC, first-shot uslovi) spušta na MCU sa izmjerenim resursnim budžetom. Ovaj rad zatvara tu rupu.

### 2.4 Redoslijed čitanja (prvih 15, ~2 sedmice)
1. DCASE 2020 Task 2 description (arXiv 2006.05822) — definicija problema
2. DCASE 2022 Task 2 (arXiv 2206.05876) — domain generalization + baseline tabele
3. DCASE 2024 Task 2 (arXiv 2406.07250) — AE baseline sa MSE/Mahalanobis modovima (tvoja polazna implementacija)
4. DCASE 2026 Task 2 (arXiv 2606.01578) — aktuelni setup
5. MIMII DG paper — dataset koji koristiš
6. ToyADMOS2 paper — drugi dataset
7. Koizumi et al., Neyman-Pearson AE ASD (TASLP 2019) — teorijska osnova
8. Suefusa et al., IDNN (ICASSP 2020) — interpolaciona varijanta AE
9. OutlierNets (kompaktni AE) — model-size referenca
10. AE TinyML na Cortex-M4 — MCU referenca
11. TFLM paper (David et al., MLSys 2021) — framework
12. MCUNet (NeurIPS 2020) — memory-aware NN dizajn
13. TinyML→TinyDL survey (arXiv 2506.18927) — pregled polja + on-device learning poglavlje
14. Banbury et al., MLPerf Tiny benchmark — metodologija mjerenja
15. ESP32-S3 TRM (poglavlja: PIE, I2S, SRAM/cache) — nije "rad" ali je obavezno

---

## 3. Datasetovi

### 3.1 Primarni: DCASE 2026 Task 2 Development Dataset (Zenodo)
- 7 tipova mašina: ToyCar, ToyCarEmu, Fan, Gearbox, Bearing, Slide rail, Valve (emu varijante).
- Jednokanalni 10–12 s klipovi, 16 kHz, normalan rad + anomalije (anomalije samo u test dijelu), realan šum okoline; 2026 specifičnost: parovi blizu/daleko mikrofona za noise-aware pristupe.
- Trening: SAMO normalni zvuci (unsupervised setup).

### 3.2 Sekundarni (za širinu i poređenje sa literaturom)
- **MIMII DG** — industrijske mašine sa domain-shift sekcijama (osnova DCASE 2022+).
- **ToyADMOS2** — toy mašine, kontrolisane anomalije.
- **DCASE 2022/2024 dev setovi** — da se tvoji rezultati mogu direktno porediti sa objavljenim baseline tabelama (jaka tačka u odbrani: "moj int8 model na ESP32 vs zvanični fp32 GPU baseline").

### 3.3 Mini demo-set (snimaš sam, 1 dan posla, NIJE naučna evaluacija)
- Kućni ventilator / bušilica / akvarijumska pumpa preko INMP441: normalan rad + izazvane anomalije (začepljen usis, odvrnut šraf, struganje).
- Svrha: live demo na odbrani + sanity-check cijelog audio lanca. U radu ide kao "kvalitativna validacija".

---

## 4. ML metodologija (PC strana, Python)

### 4.1 Pipeline
```
WAV 16 kHz → STFT (frame 64 ms = 1024 uzoraka, hop 32 ms)
          → mel filterbank (F = 128) → log
          → konkatenacija P = 5 frejmova → vektor 640
          → Autoencoder → anomaly score → AUC/pAUC
```

### 4.2 Modeli
1. **AE-baseline (referentni):** dense 640→128→128→8→128→128→640, ReLU + BatchNorm — identičan DCASE baselineu. ~270 k parametara → fp32 ~1.1 MB, int8 ~280 KB (staje u flash bez problema; SRAM footprint određuje arena, ne težine ako idu iz flasha/PSRAM-a).
2. **AE-tiny familija (tvoj doprinos):** sweep širine (64/32/16) i bottlenecka (8/4) + varijanta sa smanjenim F (64 mel) i P (3) → serija tačaka za Pareto krivu. Cilj: naći koljeno krive.
3. **(Opciono) depthwise-conv AE** na log-mel "slici" — ako vrijeme dozvoli; OutlierNets pokazuju da conv-AE može biti <10 KB.

### 4.3 Anomaly score i prag
- MSE mod: score = MSE rekonstrukcije.
- MAHALA mod: Mahalanobis preko rekonstrukcionih grešaka (kovarijansa fitovana na treningu) — DCASE 2024/2026 baseline pokazuje da MAHALA često diže target-domain AUC.
- Prag: gamma fit na score-ovima normalnih klipova, 90. percentil.

### 4.4 Kvantizacija
- Post-training quantization (PTQ) u int8, TensorFlow Lite converter, reprezentativni dataset = podskup trening klipova.
- Mjeriš: ΔAUC (fp32 vs int8) po mašini i po domenu (source/target) — hipoteza za rad: degradacija nije uniformna po tipu mašine.
- Ako PTQ previše degradira: fallback QAT (quantization-aware training) — ali PTQ prvo, jeftiniji je.

### 4.5 Eksperimenti (PC)
- **E1:** Reprodukcija zvaničnog baseline-a (fp32) na DCASE 2026 dev — sanity check protiv objavljenih brojeva.
- **E2:** AE-tiny sweep → AUC vs broj parametara (tabela + kriva).
- **E3:** PTQ int8 svih varijanti → ΔAUC.

### 4.6 Alati
Python 3.11, TensorFlow/Keras (poravnanje sa TFLM), librosa ili torchaudio za featuring (pazi: mel implementacija na PC-u i u C-u mora biti bit-approx ista — testiraj razliku!), scikit-learn (AUC/gamma fit), zvanični DCASE baseline repo kao referenca.

---

## 5. Embedded implementacija (ESP-IDF, C)

### 5.1 Platforme i toolchain
- **ESP32-S3-DevKitC-1 / tvoja S3 ploča** (target) + **obični ESP32** (kontrolna platforma za PIE ablation).
- ESP-IDF v5.x (najnoviji stable), CMake, `idf.py`; komponenta `esp-tflite-micro` (TFLM port sa `esp-nn` optimizovanim kernelima), `esp-dsp` (FFT).
- Napomena: esp-nn ima Xtensa-optimizovane int8 kernele koji koriste PIE na S3 — tvoj "PIE on/off" eksperiment = build sa esp-nn optimizacijama vs referentni C kernel (Kconfig opcija), plus S3 vs ESP32 poređenje.

### 5.2 Arhitektura firmvera (FreeRTOS)
```
[I2S RX + DMA] → ring buffer (PSRAM/SRAM)
      │ (capture task, prio visok)
      ▼
[Feature task] STFT (esp-dsp radix-2 FFT, Hann prozor iz LUT)
               → mel filterbank (unaprijed izračunate sparse težine u flashu)
               → log → normalizacija (mean/std iz treninga, u flashu)
      ▼
[Inference task] TFLM interpreter, int8 model iz flasha,
                 tensor arena u SRAM (statički alocirana)
      ▼
[Decision] klizni prosjek score-a preko klipa → poređenje s pragom
      ▼
[Izlaz] LED / UART log / (opciono) BLE notifikacija
```

### 5.3 Drajverski sloj — šta konkretno pišeš u C-u
1. **I2S ulaz (INMP441):** IDF v5 `i2s_std` drajver; 16 kHz, 32-bit slot (INMP441 daje 24-bit MSB), mono (L/R pin na GND), DMA deskriptori (npr. 4×1024 uzoraka); konverzija 32→16 bit sa shiftom. Ovo je tvoje "pisanje drajverske konfiguracije" — nisko-nivovski, ali dokumentovan API; rizik mali.
2. **DSP front-end:** ručno: framing + Hann + `dsps_fft2r_fc32` (ili fixed-point varijanta) + power spectrum + mel množenje. Mel matricu generišeš Python skriptom → C header (sparse format: za svaki mel filter offset + niz težina). Log preko `logf` ili LUT aproksimacije (uporedi tačnost/brzinu — mini-rezultat za rad).
3. **TFLM integracija:** model → `xxd -i` → `model_data.cc` u flash; `MicroMutableOpResolver` samo sa potrebnim opovima (FullyConnected, Relu, Quantize/Dequantize) — smanjuje binar; tensor arena dimenzionisana eksperimentalno (kreni 100 KB, mjeri `arena_used_bytes`).
4. **Mjerni hooks:** `esp_timer_get_time()` oko svake faze; ciklusi preko `xthal_get_ccount()`; heap watermark (`esp_get_free_heap_size`, `uxTaskGetStackHighWaterMark`).

### 5.4 Memorijski budžet (planiraj unaprijed, izmjeri stvarno)
| Stavka | Procjena |
|---|---|
| Ring buffer audio (2 s @ 16 kHz, 16-bit, double) | 128 KB → ako škripi u SRAM, ide u PSRAM (ako je ploča ima) ili skrati na 1 s |
| FFT radni baferi | ~16 KB |
| Mel + log izlaz (frame) | <2 KB |
| TFLM arena (AE-baseline int8) | 50–150 KB (izmjeriti; AE-tiny znatno manje) |
| Model (flash) | 30–300 KB zavisno od varijante |
| Stack taskova + IDF | ~40 KB |

Ako AE-baseline (640-dim ulaz) ne stane komotno u interni SRAM — to je REZULTAT, ne problem: pokazuješ tačno gdje puca i koliko AE-tiny mora biti da stane, a PSRAM (16 MB na tvom N32R16V) služi kao komotna varijanta za poređenje. Mjeri OBJE konfiguracije: "sve u SRAM" (AE-tiny) vs "arena u PSRAM" (AE-baseline) — razlika u latenciji i potrošnji je rezultat za rad.

### 5.5 On-device kalibracija (stretch, poglavlje sa fallbackom)
- Mod "kalibracija": uređaj snima N (npr. 60) klipova normalnog rada nove mašine → računa score-ove → fituje gamma raspodjelu momentnom metodom (mean/var → k, θ — zatvorena forma, čista aritmetika, bez backpropa) → prag = 90. percentil (inverzna gamma CDF: ili Wilson–Hilferty aproksimacija ili mala LUT).
- Opciono +: on-device Mahalanobis — running mean i dijagonalna kovarijansa grešaka (Welfordov algoritam, O(D) memorije).
- Eksperiment **E6:** prag fitovan on-device vs na PC-u — poklapanje + trošak (vrijeme/energija kalibracije).
- Fallback: ako zapne, prag se računa offline i upisuje u NVS — rad i dalje kompletan.

### 5.6 Specifičnosti N32R16V modula (32 MB flash + 16 MB oktalni PSRAM)

**sdkconfig (postavi odmah, prije prvog builda):**
```
CONFIG_SPIRAM=y
CONFIG_SPIRAM_MODE_OCT=y
CONFIG_SPIRAM_SPEED_80M=y
CONFIG_SPIRAM_MALLOC_ALWAYSINTERNAL=4096   # mali alloci u SRAM, veliki u PSRAM
CONFIG_ESPTOOLPY_FLASHSIZE_32MB=y
```
Verifikacija u boot logu: `Octal PSRAM initialized` + `Found 16MB PSRAM`; runtime: `heap_caps_get_total_size(MALLOC_CAP_SPIRAM)` ≈ 16 MB.

**Kritična pravila:**
1. **GPIO 35, 36, 37 su ZAUZETI oktalnim PSRAM-om** — ne smiju se koristiti ni za šta. Pin-plan za INMP441 (npr.): BCLK=GPIO4, WS=GPIO5, DIN=GPIO6; INA219 I2C: SDA=GPIO8, SCL=GPIO9. Napravi tabelu pinova u repo-u PRIJE lemljenja.
2. **I2S DMA baferi moraju biti u internom SRAM-u** — DMA periferije na S3 ne pristupaju PSRAM-u. Tok: I2S DMA (interni SRAM, mali deskriptori) → capture task kopira u veliki ring buffer u PSRAM-u. Alokacija: `heap_caps_malloc(size, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL)` za DMA, `MALLOC_CAP_SPIRAM` za ring buffer.
3. **"V" (1.8 V) varijanta**: VDD_SPI je na 1.8 V preko eFuse-a — NE diraj eFuse, NE forsiraj drugačiji SPI napon u esptool-u; pogrešan SPIRAM mode u sdkconfig-u (quad umjesto octal) daje boot-loop — prepoznaješ ga i vraćaš config, ništa nije trajno oštećeno.
4. **PSRAM nije energetski besplatan**: oktalni PSRAM na 80 MHz vuče primjetnu struju i u idle-u. U E5 mjeri i "SRAM-only" varijantu (AE-tiny, PSRAM neiskorišćen) — "cijena komoditeta PSRAM-a u mW" je zaseban rezultat.
5. **Flash particija za evaluaciju**: custom `partitions.csv` sa FAT particijom ~20 MB; upload klipova preko `esptool.py write_flash` ili fatfsgen; uređaj čita WAV-ove i računa score-ove → identičan ulaz kao PC → bit-po-bit poređenje.

---

## 6. Mjerenja na hardveru

### 6.1 Latencija i propusnost (E4)
- Po fazi: I2S→bafer, FFT+mel (po frejmu), inferenca (po 640-vektoru), ukupno po 10 s klipu.
- Matrica: {ESP32, ESP32-S3} × {esp-nn optimizovano, referentni kerneli} × {AE-baseline, AE-tiny} → PIE speedup tabela.
- Real-time kriterijum: obrada 10 s klipa < 10 s (očekivano: daleko ispod; dense mreže ove veličine su par ms po vektoru).

### 6.2 Energija (E5)
- INA219/INA226 breakout u seriju sa 3.3 V napajanjem modula (isključi USB-UART most iz mjerenja: napajaj modul direktno, ili mjeri na 5 V pa diskutuj overhead).
- Mjeri: idle, capture, DSP, inferenca; energija po klipu (mJ); projekcija baterijskog rada uz duty-cycling (npr. 10 s slušanja svakih 5 min + light sleep).
- Ako INA219 sample rate bude grub za kratke faze: produži faze u petlji (100× inferenca) i usrednjuj — standardan trik, navedi ga u metodologiji.

### 6.3 Validnost
- Svako mjerenje ≥5 ponavljanja, mean ± std (DCASE praksa).
- Fiksiraj CPU frekvenciju (240 MHz), isključi Wi-Fi/BT tokom mjerenja, logging na minimum.

---

## 7. Hardver

### 7.1 Postojeći (potvrđeno)
| Uređaj | Specifikacija | Uloga |
|---|---|---|
| **ESP32-S3-WROOM-1 N32R16V** | 32 MB flash, **16 MB oktalni PSRAM (1.8 V)**, Wi-Fi 2.4 GHz, MAC 90:e5:b1:d8:1c:c4 | Glavna target platforma — najbolja moguća varijanta WROOM-1 za ovaj projekat |
| ESP32 (klasični) | — | Kontrolna platforma za PIE ablation (E4) |

Implikacije N32R16V na plan (detalji u 5.6):
- Memorijski rizici iz 5.4 praktično nestaju — arena i baferi bilo koje veličine.
- **fp32 vs int8 na istom uređaju**: fp32 model može iz PSRAM-a → precision ablation na identičnom hardveru (jača kvantizacionu studiju E3/E4).
- **32 MB flasha**: FAT/SPIFFS particija ~20 MB → ~60 DCASE test klipova (16 kHz mono WAV, 10 s ≈ 320 KB) na samom uređaju → E4 evaluacija bez SD kartice i streaminga, bit-po-bit uporediva sa PC-om.

### 7.2 Za kupovinu (naruči sedmicu 1)
| Stavka | Svrha | Cijena (~) |
|---|---|---|
| INMP441 I2S MEMS mikrofon (2 kom) | Audio ulaz, demo | 8 € |
| INA219 (ili INA226 ako je dostupan — bolji sample rate) | Mjerenje struje/energije | 5 € |
| Sitnice: protoboard, kablovi, 100 nF + 10 µF keramika za decoupling | Setup | 5 € |
| **Ukupno** | | **≤ 18 €** ✔ duboko u budžetu |

---

## 8. Struktura rada (poglavlja)

1. **Uvod** — motivacija (prediktivno održavanje, edge AI), problem, ciljevi, doprinosi, struktura.
2. **Pregled stanja u oblasti** — DCASE Task 2 istorijat i metode; TinyML deployment radovi; formulacija rupe (tabela 2.3 odavde).
3. **Teorijske osnove** — log-mel featuring, autoencoder za ASD, metrike (AUC/pAUC), kvantizacija (afina int8), arhitektura ESP32-S3 (Xtensa LX7, PIE, memorijska hijerarhija).
4. **Metodologija** — dataset, modeli, eksperimenti E1–E6, mjerni protokol.
5. **Implementacija** — PC pipeline; firmware arhitektura (dijagram iz 5.2), drajveri, DSP, TFLM integracija, on-device kalibracija.
6. **Rezultati i diskusija** — E1–E6 tabele/grafovi; Pareto kriva; PIE speedup; energetski profil; poređenje sa literaturom; ograničenja.
7. **Zaključak i budući rad** — on-device fine-tuning, conv-AE, dvokanalni noise-aware pristup (2026 setup), federated flota.
- Prilozi: šeme povezivanja, repo struktura, uputstvo za reprodukciju.

---

## 9. Plan po sedmicama (start: 20.07, odbrana-ready: 30.09)

| Sedmica | Datumi | Zadaci | Izlaz/milestone |
|---|---|---|---|
| 1 | 20.07–26.07 | Radovi 1–6; skini DCASE 2026 dev + baseline repo; postavi Python env; naruči hardver ODMAH | Baseline repo se vrti; hardver naručen |
| 2 | 27.07–02.08 | Radovi 7–15; E1: reprodukuj baseline AUC brojeve; skica poglavlja 2 | E1 ✔; 3–4 str. pregleda literature |
| 3 | 03.08–09.08 | E2: AE-tiny sweep (pusti treninge preko noći); počni pisati pogl. 3 | Pareto tačke fp32 |
| 4 | 10.08–16.08 | E3: PTQ int8 svih varijanti, ΔAUC analiza; mel→C header generator skripta | int8 modeli + tabela ΔAUC |
| 5 | 17.08–23.08 | Firmware skeleton: I2S drajver + FFT/mel u C; unit test: PC vs C featuri (max apsolutna razlika) | Audio lanac radi na S3 |
| 6 | 24.08–30.08 | TFLM integracija; prvi on-device score; end-to-end na snimljenom klipu sa SD/flasha | Inferenca na uređaju ✔ |
| 7 | 31.08–06.09 | E4: latencija/RAM matrica (ESP32 vs S3, esp-nn on/off); E5: energija sa INA | Glavne hardverske tabele |
| 8 | 07.09–13.09 | E6 (stretch): on-device gamma kalibracija; mini demo-set snimanje; **cut-off za nove feature: 13.09** | Kalibracija ili svjestan cut |
| 9 | 14.09–20.09 | Pisanje: poglavlja 5–6 kompletna; svi grafovi finalni | Draft v1 kompletan |
| 10 | 21.09–30.09 | Revizija, mentor feedback, priprema odbrane + live demo skripta; buffer | Predaja ✔ |

Pravila: piši usput (min. 2 h sedmično na tekst od sedmice 2); svaki eksperiment odmah u tabelu/graf, ne "sredicu kasnije"; git od prvog dana, tagovi po eksperimentu.

---

## 10. Rizici i fallback

| Rizik | Vjerovatnoća | Fallback |
|---|---|---|
| PC↔C mel featuri se ne poklapaju (AUC pada na uređaju) | Srednja | Izvuci featuring u zajednički C kod (isti kod na PC-u preko ctypes/CFFI) — eliminišeš razliku po definiciji |
| TFLM arena ne staje za AE-baseline | Niska–srednja | PSRAM; ili samo AE-tiny na uređaju, AE-baseline ostaje PC referenca (i dalje validna Pareto priča) |
| INA219 pregrub za kratke faze | Srednja | Petlja ×100 + usrednjavanje; ili mjeri samo agregat po klipu |
| E6 kalibracija škripi | Srednja | Offline prag u NVS; E6 postaje "budući rad" — rad kompletan bez njega |
| Vrijeme (posao + rok) | Visoka | Scope je već sječen: bez QAT, bez conv-AE, bez 2-kanalnog noise-aware — sve to ide u "budući rad" |

**Minimalni odbranjiv rad** (ako sve krene po zlu, spreman do ~10.09): E1 + E3 + jedan model deployovan na S3 sa izmjerenom latencijom/RAM-om. Sve preko toga diže ocjenu i publikabilnost.

---

## 11. Publikacija (opciono, poslije odbrane)
- ETRAN/IcETRAN ili IEEE regionalna (TELFOR, MECO) — E2–E5 su dovoljni za solidan konferencijski rad "DCASE-grade ASD on MCU-class hardware: an empirical study".
- Repo + kratak tehnički izvještaj na arXiv podiže vidljivost za posao.

---

## 12. Reference (polazna lista — URL-ovi)

**DCASE Task 2:**
- 2020: https://arxiv.org/abs/2006.05822
- 2021: https://arxiv.org/abs/2106.04492
- 2022: https://arxiv.org/abs/2206.05876
- 2023: https://arxiv.org/abs/2305.07828
- 2024: https://arxiv.org/abs/2406.07250
- 2026: https://arxiv.org/abs/2606.01578
- 2026 dev dataset: https://zenodo.org/records/19336329
- Challenge stranice + baseline kod: https://dcase.community (Task 2 po godinama; baseline repoi linkovani odatle)

**Metode/teorija:**
- Koizumi et al., Neyman-Pearson AE ASD, IEEE/ACM TASLP 2019
- Suefusa et al., IDNN, ICASSP 2020: https://arxiv.org/abs/2006.05822 (ref. u task paperima)
- CLP-SCF kontrastivno: https://arxiv.org/abs/2304.03588
- AEGM (AE varijante pregled): https://arxiv.org/abs/2311.08829

**TinyML / deployment:**
- TFLM (David et al., MLSys 2021)
- MCUNet (Lin et al., NeurIPS 2020)
- OutlierNets (kompaktni AE za MIMII)
- AE TinyML na Cortex-M4: https://www.researchgate.net/publication/364182863
- ESP32 urban noise LSTM-AE: https://www.sciencedirect.com/science/article/pii/S2542660523001713
- ESP32-S3 TFLM deployment šablon (ArrythML): https://arxiv.org/abs/2606.02256
- TinyML→TinyDL survey: https://arxiv.org/abs/2506.18927
- TinyML research trends: https://www.sciencedirect.com/science/article/pii/S2590005625003017

**Espressif dokumentacija:**
- ESP32-S3 TRM (PIE, I2S, memorija)
- esp-tflite-micro: https://github.com/espressif/esp-tflite-micro
- esp-nn: https://github.com/espressif/esp-nn
- esp-dsp: https://github.com/espressif/esp-dsp
- ESP-IDF I2S std drajver docs

---

## 13. Kompletan registar rizika — sve što može poći po zlu i kako pristupiti

Format: **Problem → Kako ga rano prepoznati → Kako pristupiti.** Grupisano po fazi. Zvjezdica (★) = najvjerovatniji problemi po iskustvu iz sličnih projekata.

### A) Dataset i ML (PC faza)

**A1. ★ Reprodukcija baseline-a se ne poklapa sa objavljenim brojevima.**
- Prepoznaješ: E1 AUC odstupa >2–3 p.p. od tabela u task paperu.
- Pristup: objavljeni rezultati su mean ± std iz 5 nezavisnih treninga i GPU trening je nedeterministički — poklapanje unutar ±std JE uspješna reprodukcija. Pinuj verzije (requirements.txt iz zvaničnog repoa), fiksiraj seedove, pusti 5 treninga. Ako i dalje bježi: provjeri sample rate učitavanja (16 kHz!), normalizaciju i broj epoha — 90 % grešaka je u data loaderu, ne u modelu.

**A2. AUC blizu 50 % (slučajnost) na pojedinim mašinama, tipično Valve.**
- Prepoznaješ: E1/E2 tabela po mašinama.
- Pristup: ovo je POZNATO svojstvo — neimpulsivni AE loše hvata kratke, nestacionarne zvukove ventila; i zvanični baseline ima pAUC ~52 % na valve. Ne gubiš vrijeme "popravljajući" — citiraš literaturu, diskutuješ zašto, i to je legitimna analiza. Rad ne pada zbog jedne teške mašine.

**A3. ★ int8 kvantizacija ozbiljno obara AUC (>5 p.p.) na nekim modelima.**
- Prepoznaješ: E3 ΔAUC tabela.
- Pristup: redom — (1) per-channel umjesto per-tensor kvantizacija težina; (2) veći/reprezentativniji kalibracioni skup za PTQ; (3) ostavi ulaz/izlaz u fp32 (samo unutrašnjost int8); (4) tek onda QAT kao teška artiljerija. I ne zaboravi: asimetrična degradacija po mašinama je ZANIMLJIV rezultat, ne neuspjeh — analiziraj korelaciju sa dinamičkim opsegom featura.

**A4. Trening prespor na IdeaPad-u (nema jak GPU).**
- Prepoznaješ: sedmica 3, sweep se vuče.
- Pristup: ovi dense AE modeli su sitni — CPU trening je minute-do-sati po modelu; pusti sweep preko noći skriptom. Ako zapne: Google Colab (besplatan GPU) za trening, lokalno samo evaluacija. Ne kupuj ništa.

**A5. Zenodo spor / dataset velik / nestane prostora na disku.**
- Prepoznaješ: sedmica 1.
- Pristup: skidaj odmah (sedmica 1, ne kad zatreba), preko noći; drži samo 16 kHz mono verzije; obriši raspakovane duplikate. Provjeri slobodan disk prije (dataset + featuri + modeli ≈ 15–30 GB).

**A6. Prekasno "otkriće" da protokol nije fiksiran (tuniranje na test skupu).**
- Prepoznaješ: recenzent/mentor pita "na čemu si birao hiperparametre?"
- Pristup: fiksiraj protokol u sedmici 2 pismeno: svi izbori na trening skupu + validacionom podskupu normalnih; test klipovi se diraju SAMO za finalne tabele. DCASE pravila eksplicitno zabranjuju tuniranje praga na testu — drži se toga i citiraj pravilo.

### B) Featuring i port PC → C (najčešći izvor "misterioznih" gubitaka tačnosti)

**B1. ★★ PC i C log-mel featuri se ne poklapaju → AUC na uređaju niži nego na PC-u.**
- Prepoznaješ: unit test iz sedmice 5 (isti WAV kroz oba pipeline-a, max |razlika|) — NE čekaj da vidiš pad AUC-a, testiraj feature nivo direktno.
- Pristup po koracima: (1) identičan prozor (Hann, ista formula — librosa `sym=False`!); (2) ista FFT dužina i hop u UZORCIMA, ne u ms; (3) ista mel formula (HTK vs Slaney — librosa default je Slaney, mnogi C portovi HTK!); (4) isti epsilon u log(x+ε); (5) ista normalizacija (mean/std iz treninga, upisana u C header, ne računata na uređaju). Nuklearna opcija koja rješava sve: featuring napisan JEDNOM u C-u, na PC-u pozivan preko CFFI/ctypes — razlika nestaje po definiciji. Planiraj ovu opciju od starta ako u sedmici 5 razlika > 1e-3.

**B2. Fiksni format / preciznost FFT-a unosi šum.**
- Prepoznaješ: featuri se poklapaju na tihim, razilaze na glasnim signalima.
- Pristup: koristi float32 FFT iz esp-dsp (`dsps_fft2r_fc32`) — S3 ima FPU, nema potrebe za fixed-point; fixed-point ostavi kao opcionu optimizaciju SA mjerenjem greške.

**B3. Model očekuje drugačiji raspored (frame-major vs mel-major) ili kvantizacione parametre ulaza.**
- Prepoznaješ: score-ovi na uređaju besmisleni (svi isti / eksplozivni) iako featuri OK.
- Pristup: ispiši input scale/zero-point iz .tflite fajla i uporedi sa onim što firmware primjenjuje; provjeri redoslijed konkatenacije P frejmova. Debug tehnika: ubaci poznati vektor (iz PC-a, hardkodovan) direktno u interpreter na uređaju i uporedi izlaz sa PC izlazom — izoluje model od featuringa.

### C) Embedded / hardver

**C1. ★ INMP441 daje tišinu, šum ili "pomjeren" signal.**
- Prepoznaješ: snimi 5 s u WAV na flash particiju, prebaci na PC, otvori u Audacity — OBAVEZAN prvi test, prije ikakvog ML-a.
- Pristup: klasične greške redom — L/R pin mora na GND (lijevi kanal) i drajver konfigurisan na isti slot; INMP441 šalje 24-bit MSB u 32-bit slotu → čitaj 32-bit pa `>> 8` (ili >>14 za 16-bit put — provjeri amplitudu); WS/BCLK zamijenjeni; napajanje mikrofona sa šumnog pina (dodaj 100 nF + 10 µF uz sam mikrofon); predugi kablovi (drži <10 cm na protoboardu).

**C2. GPIO konflikt (35/36/37 na oktalnom PSRAM-u) ili strapping pinovi.**
- Prepoznaješ: reset/boot-loop čim se periferija inicijalizuje, ili PSRAM "nestane".
- Pristup: pin-tabela u repo-u prije lemljenja (pravilo iz 5.6); izbjegavaj i GPIO0/3/45/46 (strapping). Ako se desi: samo premjesti pinove — I2S matrix na S3 dozvoljava skoro bilo koje.

**C3. ★ Boot-loop poslije uključenja PSRAM-a u sdkconfig.**
- Prepoznaješ: ploča se restartuje u krug sa PSRAM error porukom.
- Pristup: pogrešan mod (quad umjesto OCT) ili pogrešna brzina — vrati na vrijednosti iz 5.6. Ništa nije trajno oštećeno; eFuse ne diraš nikad.

**C4. I2S DMA overrun / gubljenje uzoraka pod opterećenjem.**
- Prepoznaješ: periodični "klik" artefakti u snimku; brojač dropovanih deskriptora.
- Pristup: capture task na višem prioritetu i pinovan na drugo jezgro od inference taska (`xTaskCreatePinnedToCore`); povećaj broj/veličinu DMA deskriptora; ring buffer u PSRAM-u dovoljno velik da amortizuje inference špic. Loguj watermark ring buffera — ako raste, dizajn ne stiže.

**C5. TFLM: nepodržan op ili pad pri alokaciji arene.**
- Prepoznaješ: `AllocateTensors()` vraća grešku ili interpreter odbija op.
- Pristup: dense AE koristi samo FullyConnected/Relu/(De)Quantize — svi podržani; ako converter ubaci nešto egzotično (npr. kroz BatchNorm fuziju), pogledaj graf u Netron-u i pojednostavi model (BN fuzuj u Dense prije konverzije). Arena: kreni 512 KB u PSRAM-u, očitaj `arena_used_bytes()`, pa smanji.

**C6. Stack overflow / watchdog reset tokom dugih mjernih petlji.**
- Prepoznaješ: `Guru Meditation` / task WDT poruke baš tokom E4/E5.
- Pristup: `uxTaskGetStackHighWaterMark` za svaki task (drži >512 B rezerve); u mjernim petljama periodično `vTaskDelay(1)` ili reconfig task WDT-a; ne zovi `printf` u hot path (UART blokira i kvari mjerenje).

**C7. Brownout / nestabilnost kad se doda INA u seriju.**
- Prepoznaješ: resetovi pri Wi-Fi burstu ili špicu potrošnje; brownout poruka.
- Pristup: shunt INA219 (0.1 Ω) + otpor kablova obara napon pri špicevima — dodaj ≥470 µF elektrolit POSLIJE INA (na strani ploče); za mjerenja isključi Wi-Fi/BT (ionako pravilo iz 6.3); po potrebi INA226 sa manjim shuntom.

**C8. Flash particija: slika ne staje / fatfsgen problemi.**
- Prepoznaješ: `write_flash` grešaka ili FS se ne mountuje.
- Pristup: provjeri da offseti u partitions.csv ne preklapaju app particiju; koristi wear-levelling FAT samo za čitanje (read-only mount) — jednostavnije i brže; alternativa ako zapne: prebaci klipove preko UART-a u PSRAM pri startu (sporije, ali radi).

### D) Mjerenja (validnost rezultata — ovo komisija napada)

**D1. ★ INA219 prespor za kratke faze (inferenca od par ms).**
- Prepoznaješ: očitavanja "preskaču" fazu.
- Pristup: petlja ×100–1000 iste faze + prosjek (standard u MLPerf Tiny metodologiji — citiraj); ili mjeri agregat po cijelom klipu (to je ionako operativno relevantna metrika); INA226 (veći sample rate) ako si ga uzeo.

**D2. USB-UART most i LED-ovi zagađuju mjerenje potrošnje.**
- Prepoznaješ: idle struja sumnjivo visoka (>40–50 mA).
- Pristup: napajaj modul direktno na 3.3 V pin (preko INA), USB otkačen tokom mjerenja (logove čitaj poslije iz flasha/RAM-a ili preko posebnog UART-a na 1.8/3.3 V adapteru); ako ploča ima power LED — navedi njen doprinos ili ga fizički ukloni; u radu jasno dokumentuj mjernu tačku.

**D3. Latencija varira između pokretanja (cache, flash XIP).**
- Prepoznaješ: std latencije velika, prvi prolaz uvijek sporiji.
- Pristup: hot funkcije u IRAM (`IRAM_ATTR`), warm-up prolaz prije mjerenja, fiksiraj CPU na 240 MHz, ≥5 ponavljanja × mean ± std (već u 6.3), i JEDNO objašnjenje u radu zašto je prvi prolaz odbačen.

**D4. Poređenje ESP32 vs S3 nije "fer" (različit clock, različit IDF config).**
- Prepoznaješ: recenzentsko pitanje.
- Pristup: identičan IDF, identičan config gdje hardver dozvoljava, oba na 240 MHz; razlike koje ostaju (cache veličina, PSRAM prisustvo) eksplicitno tabelarno navedi. PIE efekat izoluj i unutar samog S3 (esp-nn on/off) — to je čist ablation nezavisan od platformskih razlika.

### E) Proces, rok, mentor

**E1. ★★ Klizanje rokova (posao + 2 h/dan realnost).**
- Prepoznaješ: dva uzastopna sedmična milestone-a probijena.
- Pristup: plan već ima cut-off 13.09 i definisan minimalni odbranjiv rad (sekcija 10) — aktiviraj ga BEZ griže savjesti: siječeš E6, pa conv-AE, pa demo-set, tim redom. Nikad ne siječeš pisanje. Sedmični 15-min pregled nedjeljom uveče: šta je milestone, jesam li na njemu, šta sijećem.

**E2. Mentor traži izmjene teme / ne prihvata "sistemski" rad.**
- Prepoznaješ: prvi sastanak.
- Pristup: idi mentoru SEDMICE 1 sa jednostranim sažetkom (cilj, doprinosi, E1–E6, timeline) — ne poslije mjesec dana rada. Ako traži više "klasičnog ML-a": E2 sweep + E3 kvantizaciona analiza SU klasična ML evaluacija, samo ih naglasi. Ako traži vezu sa prethodnim CSI radom: uvod može framirati oba kao "edge inference pod resursnim ograničenjima".

**E3. Gubitak podataka/koda.**
- Pristup: git od prvog dana (privatni GitHub repo), push svaki radni dan; featuri i modeli (veliki fajlovi) na eksterni disk + cloud; tag po eksperimentu (`e1-baseline`, `e3-int8-v2`) da svaki broj u radu ima commit iz kog je nastao — ovo je i reproducibilnost koju možeš navesti u radu.

**E4. Scope creep (tvoja poznata sklonost: "dodao bih još...").**
- Prepoznaješ: ideja koja nije u E1–E6.
- Pristup: fajl `future-work.md` u repo-u — svaka nova ideja ide TAMO, ne u kod. Prazan trošak: 30 sekundi. Poslije odbrane taj fajl je zlato (publikacija, projekti).

**E5. Pisanje ostavljeno za kraj → panika u sedmici 9.**
- Pristup: pravilo iz sekcije 9 (2 h sedmično na tekst od sedmice 2) + trik: svaki eksperiment se "zatvara" tek kad su tabela+graf+3 rečenice diskusije u draftu. Eksperiment bez teksta = nezavršen eksperiment.

### F) Odbrana i demo

**F1. Live demo zakaže na odbrani (Murphy).**
- Pristup: snimi VIDEO uspješnog demoa unaprijed (telefon, 60 s: normalan ventilator → zelena LED; začepljen usis → crvena) — pustiš ga ako hardver štrajkuje; demo hardver nosi SVOJ napajački bank, ne zavisi od sale; imaj i "kanski" mod: unaprijed snimljeni klipovi sa flash particije umjesto živog mikrofona (jedan taster bira izvor).

**F2. Pitanje "zašto nisi koristio [SOTA metodu X / veći model / drugi MCU]?"**
- Pristup: odgovor je već u radu ako si napisao sekciju ograničenja: cilj rada je resursno ograničen deployment i sistematska analiza kompromisa, ne SOTA AUC; jače metode su u pregledu literature i u future work. Pripremi 3 slajda "anticipirana pitanja" (SOTA, generalizacija, energija metodologija).

**F3. Pitanje "kolika je praktična vrijednost ako je AUC ~70 %?"**
- Pristup: iskren odgovor iz literature — i GPU baseline je na sličnim brojevima za teške mašine u domain-shift uslovima; praktični sistemi rade sa dužim vremenskim prozorima glasanja (majority vote preko N klipova diže efektivnu tačnost) — ako imaš vremena, mini-eksperiment glasanja preko 5 klipova je jeftin dodatak koji ovo pitanje ubija unaprijed.

### Zlatna pravila (sažetak pristupa problemima)
1. **Testiraj sloj po sloj, ne end-to-end**: audio → WAV na PC (C1) → featuri PC vs C (B1) → model sa hardkodovanim ulazom (B3) → tek onda cijeli lanac. Svaki sloj ima svoj test i svoj "poznat dobar" ulaz.
2. **Svaki čudan rezultat prvo provjeri u data pipeline-u**, tek onda u modelu — 90 % "ML misterija" su bug u učitavanju/featuringu.
3. **Loš rezultat ≠ propao rad**: asimetrična degradacija, teške mašine, cijena PSRAM-a — sve su to REZULTATI ako su izmjereni čisto i pošteno diskutovani.
4. **Sve što se mjeri: ≥5 ponavljanja, mean ± std, dokumentovana mjerna tačka.** To je razlika između "studentskog projekta" i rada koji se može citirati.
5. **Kad zapneš >2 večeri na istom problemu**: fallback iz ovog registra, i dalje. Rok je tvrd; nijedan pojedinačni problem nije vrijedan sedmice.
