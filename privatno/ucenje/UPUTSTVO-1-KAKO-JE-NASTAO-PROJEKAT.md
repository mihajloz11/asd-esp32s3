# Uputstvo 1 — kako je nastao projekat, šta je gdje, i kojim redom se čita

> Razvojni materijal. Za ispravljeno tumačenje završnih proba i filter prozora
> važi [revizija rezultata od 06.09.2026.](../../docs/probe/rezultat-finalna-validacija-2026-08-27.md). Starije brojke i planovi ovdje nisu novi dokazi.

**Napisano:** 01.09.2026. · **Za koga:** za tebe za šest mjeseci, za mentora, za
komisiju, i za bilo koga ko prvi put otvara repo.

Ovaj dokument ne uvodi nijednu novu brojku. Sve brojke ispod već postoje u
datiranim dokumentima na koje se pokazuje; ovdje su samo poređane u priču.
Ako se ovaj dokument ikad raziđe sa datiranim izvorom, **datirani izvor
pobjeđuje** (pravilo iz [`README.md`](../../docs/README.md)).

Prateća uputstva:

- [`UPUTSTVO-2-TEORIJA-OD-NULE.md`](UPUTSTVO-2-TEORIJA-OD-NULE.md) — šta je
  Furijeova transformacija, PSD, ML, TFLite, I2S drajver, metrike.
- [`UPUTSTVO-3-LITERATURA.md`](UPUTSTVO-3-LITERATURA.md) — naučni radovi,
  gdje se koji koristi i šta u njemu treba pročitati.

---

## 0. Rečenica koja objašnjava cio projekat

> Mala pločica (ESP32-S3) sluša ventilator preko jednog mikrofona, prvih ~2
> minuta uči kako taj konkretan ventilator zvuči kad je ispravan, i poslije toga
> **sama, bez računara**, javlja kad se zvuk trajno promijeni.

Ono što je naučeno **na računaru unaprijed** je samo *oblik varijacije* zvuka
ventilatora uopšte (kovarijansna matrica iz 990 snimaka ispravnih ventilatora).
Ono što se uči **na licu mjesta** je *centar* — kako baš ovaj primjerak zvuči —
i *prag* iznad kojeg se javlja alarm.

Ta podjela posla je srž rada i nije bila očigledna na početku; do nje se došlo
mjerenjem (vidi etapu 5).

---

## 1. Mapa repoa — šta je zaista ključno

Repo ima puno fajlova jer je metodologija tražila da se zapiše i svaki neuspjeh.
Ovo je kratka lista onoga bez čega projekat ne postoji.

### 1.1 Ulazne tačke (pročitati prvo, ovim redom)

| Fajl | Zašto |
|---|---|
| [`../../KONTEKST.md`](../KONTEKST.md) | pravila rada, zlatna pravila dokaza, gdje je istina |
| [`../../docs/pregled-projekta.md`](../../docs/pregled-projekta.md) | gdje je projekat sada, u jednoj strani |
| [`README.md`](../../docs/README.md) | mapa cijele dokumentacije: aktuelno vs istorijsko |
| [`cilj-modela.md`](../../docs/model/cilj-modela.md) | nepromjenjivi cilj i kriterij uspjeha (AUC ≥ 0,80) |
| [`../../plan-master-rada.md`](../istorija/planovi/plan-master-rada-jul.md) | originalni plan i metodologija (jul 2026) |

### 1.2 PC strana — Python (učenje, mjerenje, alati)

| Fajl | Šta radi |
|---|---|
| [`../../pc/asd/features.py`](../../pc/asd/features.py) | log-mel front-end (STFT 1024, 128 mel traka, vektor 640) — **istorijski put**, ostaje jer su na njemu mjereni AE rezultati |
| [`../../pc/asd/data.py`](../../pc/asd/data.py) | pronalaženje DCASE fajlova i keširanje obilježja |
| [`../../pc/asd/model.py`](../../pc/asd/model.py) | autoenkoder: baseline 640→128→8→128→640 + „tiny" familija |
| [`../../pc/asd/train.py`](../../pc/asd/train.py) | trening jedne varijante (E1/E2) |
| [`../../pc/asd/eval.py`](../../pc/asd/eval.py) | scoring i metrike: MSE/Mahalanobis, AUC, pAUC, gamma prag |
| [`../../pc/asd/quantize.py`](../../pc/asd/quantize.py) | int8 kvantizacija u `.tflite` (E3) |
| [`../../pc/tools/bench_periodicity.py`](../../pc/tools/bench_periodicity.py) | **ovdje je nastao finalni model** — Welch PSD 8192, 96 log traka |
| [`../pc/tools/bench_research*.py`](../../pc/tools/) | šest serija eksperimenata nad scoring backendom |
| [`../../pc/tools/evaluate_canonical.py`](../../pc/tools/evaluate_canonical.py) | kanonska evaluacija bez curenja podataka (referentna brojka) |
| [`../../pc/tools/gen_psd_model_header.py`](../../pc/tools/gen_psd_model_header.py) | pretvara naučeni model u C header za firmware |
| [`../../pc/tools/physical_fan_experiment.py`](../../pc/tools/physical_fan_experiment.py) | host koji vodi fizički run i piše artefakte |
| [`../../pc/tools/guided25_launcher.ps1`](../../pc/tools/guided25_launcher.ps1) | pokretanje vođenog testa jednom komandom |
| [`../pc/config/*.json`](../../pc/config/) | **zaključane politike** — prag, vremensko pravilo, kapija smetnji; CI provjerava da se poklapaju sa firmverom |
| [`../../pc/tests/`](../../pc/tests/) | 478 testova, uključujući PC↔C parity preko `ctypes` |

### 1.3 Firmware — C (ESP-IDF v5.5)

Finalni put (`ASD_PSD_LIVE`):

| Fajl | Šta radi |
|---|---|
| [`../../firmware/esp32s3_asd/main/audio_i2s.c`](../../firmware/esp32s3_asd/main/audio_i2s.c) | **drajver mikrofona**: I2S, DMA, 32→16 bita, ring buffer, odbacivanje tranzijenta |
| [`../../firmware/esp32s3_asd/main/psd_features_c.c`](../../firmware/esp32s3_asd/main/psd_features_c.c) | FFT 8192, Hann, Welch, 96 logaritamskih traka; batch i streaming varijanta |
| [`../../firmware/esp32s3_asd/main/psd_model_data.h`](../../firmware/esp32s3_asd/main/psd_model_data.h) | naučena matrica 96×96 + normalizacija, generisana sa PC-a |
| [`../../firmware/esp32s3_asd/main/psd_live.c`](../../firmware/esp32s3_asd/main/psd_live.c) | glavna živa petlja: stanja, skor, alarm, telemetrija (1461 linija) |
| [`../../firmware/esp32s3_asd/main/asd_commissioning.c`](../../firmware/esp32s3_asd/main/asd_commissioning.c) | tok `SETTLE → CENTER_LEARNING → DERIVE → VERIFY → MONITORING` |
| [`../../firmware/esp32s3_asd/main/asd_temporal.c`](../../firmware/esp32s3_asd/main/asd_temporal.c) | vremensko pravilo alarma: histereza 1,0/0,7 + 3 uzastopna prozora |
| [`../../firmware/esp32s3_asd/main/asd_events.c`](../../firmware/esp32s3_asd/main/asd_events.c) | semantika događaja i kapije koje zabranjuju netačne tvrdnje |
| [`../../firmware/esp32s3_asd/main/asd_interference.c`](../../firmware/esp32s3_asd/main/asd_interference.c) | kapija pouzdanosti prozora (`OBSERVATION_HOLD`) |
| [`../../firmware/esp32s3_asd/main/asd_profile_store.c`](../../firmware/esp32s3_asd/main/asd_profile_store.c) | trajni profil u NVS: schema, generacija, CRC32 |
| [`../../firmware/esp32s3_asd/main/asd_operator.c`](../../firmware/esp32s3_asd/main/asd_operator.c) | taster i obrasci treptanja LED-a |
| [`../../firmware/esp32s3_asd/main/pins.h`](../../firmware/esp32s3_asd/main/pins.h) | pin-plan za oba targeta i zabranjeni pinovi |

Istorijski put (čuva se zbog mjerenja u radu, **ne koristi se u finalnom toku**):
`features_c.c` (log-mel u C), `tflm_infer.cc` (TensorFlow Lite Micro),
`model_data.h`, `eval_mode.c`, `live_capture.c`, `live_adapt.c`.

### 1.4 Rezultati i radovi

| Putanja | Sadržaj |
|---|---|
| [`../../results/results.csv`](../../results/) | svaki trening/evaluacija kao red |
| `../../results/physical_fan/` | fizički runovi sa ventilatorom (netaknuti artefakti) |
| `../../results/canonical_evaluation/` | referentna evaluacija bez curenja |
| [`../../radovi/master-rad/`](../../radovi/master-rad/) | master rad, 48 strana, generiše se iz `rad_tekst.py` |
| [`../../radovi/telfor2026/`](../../radovi/telfor2026/) | TELFOR 2026 rad, 4 strane |

---

## 2. Hronologija — šta smo radili, kojim redom, i zašto se mijenjalo

Svaka etapa ima isti oblik: **šta je urađeno → šta je izmjereno → šta je ta
brojka natjerala da se promijeni**. To je i format cijelog projekta.

### Etapa 1 (17.07.) — postavka i PC pipeline

Napravljen Python paket `pc/asd` (obilježja → podaci → model → trening →
evaluacija → kvantizacija), skinut DCASE 2026 dev skup (7 zipova, 4,6 GB), i
odmah napisan **jedan jedini C kod za obilježja** koji se testira i sa PC-a
preko `ctypes`.

**Zašto tako.** Najčešći uzrok pada tačnosti pri prenosu modela na mikrokontroler
je da PC i uređaj računaju obilježja *malo* drugačije. Umjesto dvije
implementacije koje se porede, napisana je jedna koja se koristi na oba mjesta.

**Izmjereno:** PC↔C razlika na realnom klipu **3,8·10⁻⁵ dB**. Rizik zatvoren po
konstrukciji, ne po nadi.

**Namjerna odstupanja od librose** (i dalje važe, opisana u README-u): `center=False`
u STFT-u (uređaj nema padding), `LOG_EPS = 1e-12`, per-dimenziona
standardizacija.

Dnevnik: [`dnevnik-projekta.md`](../dnevnici/dnevnik-projekta.md), unos 17.07.

### Etapa 2 (17–20.07.) — autoenkoderi, kvantizacija, sve 7 mašina

Odrađeni eksperimenti E1 (reprodukcija baseline-a), E2 (Pareto sweep: 7 mašina ×
5 veličina modela) i E3 (int8 kvantizacija).

**Izmjereno:**
- int8 kvantizacija je **besplatna** za ovakav autoenkoder: ΔhMean ∈ [−0,005; +0,011]
  preko svih 35 kombinacija;
- Pareto kriva je plitka — 12× manji model gubi 2–3 procentna poena;
- Mahalanobis scoring pomaže na 5 od 7 mašina (na `fan` +6 do +10 p.p.).

To zadnje je prvi nagovještaj finalnog pravca: **backend statistike je bolji od
greške rekonstrukcije.**

### Etapa 3 (19.07.) — prvi izlazak na hardver

Firmware flešovan na ESP32-S3, klipovi stavljeni na FAT particiju, pa poređeni
skorovi uređaja i PC-a.

**Izmjereno:** TFLM arena **7 960 B** (plan je procjenjivao 50–150 KB),
featuring 665 ms + inferenca 870 ms po klipu od 10 s (15 % realnog vremena),
razlika uređaj↔PC **1,5·10⁻⁴** na 16/16 klipova, kasnije **2,2·10⁻⁴** na punih
60 klipova.

Isti firmware pušten i na klasičnom ESP32 (DevKit V1) kao kontrola: skorovi
bit-identični, S3 je **2,76× brži** ukupno; `esp-nn` (PIE vektorske instrukcije)
sam po sebi daje **1,33×**.

Uređaj je i sam fitovao gamma prag iz 30 normalnih skorova: **0,77090** naspram
PC-ovih **0,77064** — relativna razlika 0,03 %. To je dokaz da kalibracija može
da se radi *na čipu*, bez oblaka.

**Bug koji je vrijedan rada:** DCASE 2026 klipovi su stereo (par blizu/daleko);
PC je tiho uzimao kanal 0, a na particiju su otišli originalni stereo fajlovi.
Parser ih je odbio sa tačnim razlogom. Pouka: testiraj sloj po sloj.

### Etapa 4 (04.–08.08.) — živi mikrofon i prve neugodne istine

Hardver stigao 04.08. Zalemljeni headeri, INMP441 spojen, napisan bring-up mod
[`mic_test.c`](../../firmware/esp32s3_asd/main/mic_test.c).

**Izmjereno:** RMS −46,3 dBFS, peak −30,1 dBFS, `clipped=0`, `dropped=0`;
rezerva do klipovanja **15,6 dB** (time je zatvoren rizik oko pomjeranja `>>14`).
PC↔uređaj **na živom zvuku**: 7,99·10⁻⁵ — sad je pokriven i put kroz I2S i ring
buffer, ne samo račun.

**Tri nalaza koja su promijenila postavku:**

1. **Skor može da PADNE kad se pojavi anomalija**, ne samo da poraste. Model
   mjeri *udaljenost od naučenog*, ne jačinu zvuka. Uveden **dvostrani** prag
   ([P11](../../docs/problemi-i-rjesenja.md#p11)).
2. **Kalibracija je tri puta naučila ventilator laptopa kao „normalno stanje"**,
   jer kreće odmah po bootu — a boot je tačno kad se ploča fleširala. Uvedeno
   obavezno čekanje da se okruženje umiri ([P10](../../docs/problemi-i-rjesenja.md#p10)).
3. **Okruženje nije stacionarno.** Prag zavisi od toga *kada* se kalibriše, ne
   samo kako. Ista soba, isti kod, red veličine bolja kalibracija kad je mirno.

### Etapa 5 (09.08.) — proboj: promijenjen front-end, ne model

Do ovog trenutka sve je dijelilo isti log-mel front-end i sve je stajalo oko
AUC 0,67–0,72. Dvanaest varijanti scoring backenda dalo je +7 poena i stalo.

Onda je promijenjen **front-end**: umjesto STFT 1024 + 128 mel traka →
**Welch PSD sa FFT 8192**, 96 **logaritamskih** traka 10–4000 Hz, oduzimanje
skalarnog nivoa klipa.

**Izmjereno: AUC 0,864 ± 0,025** (sa 0,674). Jedna promjena front-enda dala je
dvostruko više od dvanaest promjena backenda.

**Zašto radi** (i ovo je fizika, ne ML): ventilator je rotaciona mašina, njegov
potpis su **uske harmonijske linije** obrtne frekvencije. Stari front-end ima
razmak binova 15,6 Hz i mel trake koje dodatno spajaju susjedne frekvencije — te
linije se razmažu prije nego što model bilo šta vidi. FFT 8192 daje razmak
**1,95 Hz** i razdvaja ih.

**Odmah zatim izmjereno i ograničenje** (isti dan, `faza 4b`): psd_shape pobjeđuje
na **2 od 7** mašina. Po harmonijskoj sredini (zvanična DCASE mjera) je *lošiji*
od mel osnove. Zato se tvrdnja u radu piše precizno: *„AUC 0,864 **za
ventilator**"*, nikad „PSD je bolji za ASD uopšte".

Puna priča sa svim brojkama: [`put-do-modela.md`](../../docs/model/put-do-modela.md),
odluka: [`odluka-finalni-model.md`](../../docs/model/odluka-finalni-model.md).

### Etapa 6 (09.–14.08.) — model na pločici i mjerenje šta benchmark ne vidi

PSD front-end prepisan u C ([`psd_features_c.c`](../../firmware/esp32s3_asd/main/psd_features_c.c)),
napravljen `ASD_PSD_LIVE` mod, izmjereno na uređaju.

**Izmjereno:** račun **704 ms** na 10 s zvuka (rezerva 14,2×), `dropped=0`,
PC↔uređaj na živom mikrofonu **1,70·10⁻⁶**.

Ali AUC preko **zvučnika i mikrofona** je 0,716, ne 0,864. Uzrok je izmjeren:
DCASE anomalija pomjeri skor za oko 48 %, a akustički kanal (zvučnik → vazduh →
mikrofon) pravi rasipanje reda veličine većeg. Kontrolisanim sintetičkim kvarom
izmjeren je i prag osjetljivosti: DCASE anomalija odgovara kvaru od ≈ −30 dB, a
preko zvučnika treba ≈ −15 dB. Razlika od 15 dB objašnjava svaki propušteni
prolaz — i **razdvaja „model ne valja" od „ovaj kvar je pretih za ovaj put zvuka"**.

Zatim je odrađena faza u kojoj je **šest unaprijed navedenih alternativa**
izmjereno odjednom, pod istim podjelama (`evaluate_advanced.py`): order-warp,
režimi, tri dual-channel varijante, tranzijentni put. **Nijedna ne pobjeđuje.**
Jedini pozitivan pomak (+0,0012) je dvadeset puta manji od sopstvenog rasipanja.

Zaključak koji je preusmjerio cio projekat: **usko grlo više nije obilježje nego
prag.**

I još jedan rezultat suprotan očekivanju: EWMA i CUSUM, udžbenički alati za
detekciju pomjeraja, **pogoršali** su sistem (0 → 5,4 lažnih alarma/h), jer su
napravljeni da hvataju *mali trajni* pomjeraj, a ovdje treba odbaciti *veliku
kratku* pobudu. Usvojena je histereza 1,0/0,7 + 3 uzastopna prozora.

### Etapa 7 (16.08.) — FAN01: prvi stvarni ventilator

Prvi run u kojem INMP441 sluša pravi ventilator, a cijela telemetrija prolazi
kroz zaključani host: [`rezultat-fan01-2026-08-16.md`](../../docs/probe/rezultat-fan01-2026-08-16.md).

**Dvije odvojene tvrdnje, i moraju ostati odvojene:**

1. Model je **odlično rangirao** promjenu protoka papirićem (medijana skora
   876 → 29 899).
2. **Prag nije radio**: 54 od 60 normalnih prozora bilo je iznad praga.

Drugim riječima: rangiranje je bilo skoro savršeno, a upotrebljivost nula. To je
najvažnija pouka cijelog projekta — AUC nije uređaj.

Iz tog nalaza je nastao plan dorade
([`PLAN-DORADA-POSLIJE-FAN01.md`](../istorija/planovi/PLAN-DORADA-POSLIJE-FAN01.md)).

### Etapa 8 (16.–20.08.) — osam faza dorade: od modela ka uređaju

Ovdje se skoro ništa nije mijenjalo u modelu, a skoro sve u tome *kako se od
skora pravi odluka*:

| Faza | Šta je uvedeno | Fajl |
|---|---|---|
| 1 | K1 fail-closed kapija kvaliteta kalibracije | [`asd_calibration_quality.c`](../../firmware/esp32s3_asd/main/asd_calibration_quality.c) |
| 2 | više firmware sesija u jednom host runu, metrike po epizodama | [`runtime_protocol.py`](../../pc/asd/runtime_protocol.py) |
| 3 | research telemetrija: 96 + 5×96 obilježja preko UART-a | [`psd_features_c.h`](../../firmware/esp32s3_asd/main/psd_features_c.h) |
| 4 | normal-only laboratorija na PC-u (CENTER/DERIVE/VERIFY hronološki) | [`derive_commissioning_policy.py`](../../pc/tools/derive_commissioning_policy.py) |
| 5–6 | odvojeni apsolutni enter/exit pragovi i `OBSERVATION_HOLD` | [`asd_commissioning.c`](../../firmware/esp32s3_asd/main/asd_commissioning.c), [`asd_interference.c`](../../firmware/esp32s3_asd/main/asd_interference.c) |
| 7 | audio čitanje sa ograničenim vremenom (bounded read) | [`audio_i2s.c`](../../firmware/esp32s3_asd/main/audio_i2s.c) |
| 8 | trajni profil u NVS sa schema/generation/CRC32 | [`asd_profile_store.c`](../../firmware/esp32s3_asd/main/asd_profile_store.c) |

Ključna promjena filozofije: **prag se izvodi iz normal-only prozora i zamrzava
prije nego što se pusti bilo kakav stimulus.** Papirić, govor i vrata su
*readout*, nikad ulaz u fit. To je zapisano kao pravilo u
[`KONTEKST.md`](../KONTEKST.md) i CI ga provjerava.

### Etapa 9 (20.–22.08.) — bugovi koji su obarali runove

Nekoliko problema koji su svaki koštali po run:

- **I2S timeout u tickovima umjesto u milisekundama** — drajver je čitao 25 ms
  umjesto 250 ms, kraće od jednog DMA deskriptora, pa ring buffer nikad nije
  napunjen. Komentar sa mjerenjem stoji u
  [`audio_i2s.c:60`](../../firmware/esp32s3_asd/main/audio_i2s.c#L60).
- **UART redovi sastavljani iz više `printf` poziva** su se miješali između
  taskova → zaključavanje reda.
- **Drenaža bafera zatvarala run usred research paketa** → svaki run je gubio
  posljednji prozor.
- **Hard deadline 1 500 s** obarao run prije kraja plana → deadline uklonjen,
  uveden limit pokušaja.

Svi su zapisani sa simptomom, uzrokom, rješenjem i dokazom u
[`problemi-i-rjesenja.md`](../../docs/problemi-i-rjesenja.md) (P1–P28). Ta baza je jedan od
najkorisnijih dijelova repoa.

### Etapa 10 (26.–27.08.) — finalna validacija: devet runova, dva validna

Puna analiza: [`rezultat-finalna-validacija-2026-08-27.md`](../../docs/probe/rezultat-finalna-validacija-2026-08-27.md).

**Run A (papirić):** uređaj se sam kalibrisao, sam izveo prag `8 084,49`, i
podigao alarm u trećem bloku. U prva dva bloka **nije** podigao alarm iako je
vidio promjenu (medijane 26k i 60k naspram normalnih 1,2k) — jer je kapija
pouzdanosti odbila 4/5 odnosno 3/5 prozora kao nestabilne. To je projektovano
ponašanje: papirić se drži rukom, stimulus nije konstantan.

**Run B (konstantni ton):** prag `21 809,51`, `ANOMALY` poslije 3 prozora
(~30 s), `ANOMALY_SUSTAINED` poslije 12 (~2 min).

**Govor i vrata nisu podigli alarm** iako su im skorovi bili visoki — odbijeni
kao nestabilni. To je tražena osobina.

Oba runa je pustio **isti binarni fajl** (354 784 B, SHA-256 `9ac2caca…8d967813`),
oba sa `dropped=0`.

### Etapa 11 (27.–31.08.) — pisanje

Master rad (48 strana, ćirilica i latinica iz istog izvora) i TELFOR 2026 rad
(4 strane) generišu se iz koda, ne kucaju se ručno:
[`radovi/master-rad/build_rad.py`](../../radovi/master-rad/build_rad.py) +
[`rad_tekst.py`](../../radovi/master-rad/rad_tekst.py).

---

## 3. Šta je testirano i gdje

| Sloj | Kako se provjerava | Gdje |
|---|---|---|
| Obilježja PC vs C | `ctypes` učitava isti C kod na PC-u i poredi brojeve | [`test_psd_features_c.py`](../../pc/tests/test_psd_features_c.py) |
| Streaming vs batch | isti ulaz kroz oba puta mora dati identičan izlaz | isti fajl |
| Logika stanja uređaja | C moduli se kompajliraju u `.dll`/`.so` i testiraju iz Pythona | `test_asd_commissioning_c.py`, `test_asd_temporal_c.py`, `test_asd_events_c.py` … |
| Protokol UART-a | strogi parser odbija nevalidan redoslijed | [`test_runtime_protocol.py`](../../pc/tests/test_runtime_protocol.py) |
| Fizički runovi | zamrznuti kao regresija — ako se parser pokvari, testovi padnu | [`test_physical_fan_experiment.py`](../../pc/tests/test_physical_fan_experiment.py) |
| Saglasnost politika | verzije u `pc/config` moraju odgovarati firmveru | [`check_schema_consistency.py`](../../pc/tools/check_schema_consistency.py) |
| Antipatterni | grep kapije: nema „warn and continue", nema target anomalija u fitu | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) |

Stanje 27.08.2026: **478 testova prolazi.**

> **Ali:** zeleni testovi nisu fizički dokaz. To je zlatno pravilo 1 iz
> [`KONTEKST.md`](../KONTEKST.md) i ponavlja se namjerno.

---

## 4. Komande — minimum koji treba znati

Postavka:

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r pc/requirements.txt
```

Testovi (traže `gcc` u PATH-u zbog C parity dijela):

```bash
.venv/Scripts/python.exe -m pytest pc/tests -q
```

Provjera da se politike i firmware slažu:

```bash
.venv/Scripts/python.exe pc/tools/check_schema_consistency.py
```

Trening i kvantizacija jednog modela (istorijski AE put):

```bash
cd pc && ../.venv/Scripts/python.exe -m asd.train --data ../data/dcase2026_dev/fan --variant baseline
```

Firmware (na mašini sa ESP-IDF v5.5):

```bash
cd firmware/esp32s3_asd && idf.py set-target esp32s3 && idf.py reconfigure build flash monitor
```

> ⚠ Pri **svakoj** promjeni build moda obavezan `idf.py reconfigure` — inače
> build tiho ostane u starom modu. To je P2 i već je koštalo vremena.

Vođeni fizički test sa ventilatorom: pokrenuti `scripts\POKRENI-GUIDED25.cmd`, uputstvo
za operatera u [`guided25.md`](../../docs/probe/guided25.md).

---

## 5. Šta je namjerno ostavljeno nedokazano

Ovo se piše da niko (uključujući tebe za pola godine) ne bi pomislio da je
gotovo:

- taster, dvije LED i otpornici **nisu zalemljeni**;
- commissioning pragovi su i dalje `DEVELOPMENT` — pravilo je potvrđeno na dva
  runa, ali zamrzavanje za proizvodnju traži bump verzije i novi preregistrovani
  retest;
- I2S liveness, gubitak napajanja i NVS persistence nisu fizički testirani;
- E5 / INA226 strujni put nije završen (naponski kanal odstupa, ~2 Ω u napojnoj
  grani);
- samostalan demo bez PC-a nije odrađen;
- **nije dokazano da je detektovana promjena mehanički kvar** — papirić i ton su
  kontrolisane promjene. Jedan mikrofon to ne može tvrditi.

Aktuelna lista: [`PREOSTALO.md`](../PREOSTALO.md).

---

## 6. Devet pouka koje vrijede i van ovog rada

1. **Obilježje nosi više od backenda.** Dvanaest varijanti scoring-a: +7 poena.
   Jedna promjena front-enda: +15.
2. **Negativan rezultat na bliskim parametrima ne zatvara pravac.** „FFT 4096 +
   linearne trake → 0,50–0,64" je zaustavilo istraživanje na duže vrijeme.
   Pobjednik je bio dva parametra dalje: 8192 i logaritamske trake.
3. **„Verifikovano" ne znači „optimalno".** Log-mel front-end je bio verifikovan
   na 8·10⁻⁵ i zato tretiran kao nedodirljiv. Verifikacija dokazuje da je
   implementacija tačna, ne da je izbor dobar.
4. **Loše uslovljena kovarijansa liči na lošu ideju.** Prije nego odbaciš
   obilježje sa mnogo dimenzija, provjeri regularizaciju.
5. **Fizika mašine je bolji vodič od arhitekture modela.**
6. **Ansambl nije besplatan** — slabiji član je u svakom mjerenju pokvario jačeg.
7. **Standardna tehnika nije isto što i prikladna tehnika** (EWMA/CUSUM).
8. **Kad rezultat iznenadi, prvo provjeri mjerenje** — tri puta je artefakt
   mjerenja bio kriv, jednom nije, i samo provjera razlikuje ta dva slučaja.
9. **AUC nije uređaj.** FAN01 je imao skoro savršeno rangiranje i 90 % lažnih
   alarma istovremeno.
