# Istraživanje modela: visokorezolucioni PSD otisak ventilatora

**Datum eksperimenta:** 09.08.2026
**Status ažuriran 14.08.2026:** PC eksperiment, model header, C modul, živi
firmware i mjerenje na pločici su potvrđeni. Finalni firmware koristi `k=10`;
`k=20` u tabelama ispod ostaje jači referentni PC benchmark.

## Rezultat

Novi pristup je prvi prešao zadani cilj AUC 0,80 na DCASE 2026 target-domain
ventilatoru.

| Kalibracionih klipova | Trajanje | Target AUC, 50 ponavljanja |
|---:|---:|---:|
| 5 | 50 s | 0,834 ± 0,047 |
| 10 | 100 s | 0,853 ± 0,033 |
| **20** | **200 s** | **0,864 ± 0,025** |
| 30 | 300 s | 0,866 ± 0,026 |
| 40 | 400 s | 0,875 ± 0,042 |

Direktno poređenje pod istih 50 seedova i sa k=20:

| Metoda | Target AUC |
|---|---:|
| Stari 1280-dim. log-mel sažetak + kovarijansa | 0,669 ± 0,031 |
| **Novi 96-dim. PSD oblik + kovarijansa** | **0,864 ± 0,025** |

Napredak je približno **+0,195 AUC**. I sirovi PSD bez oduzimanja ukupnog nivoa
daje 0,841 ± 0,027, pa prelazak preko 0,80 ne zavisi samo od jedne
normalizacione sitnice.

## Šta sada koristimo umjesto neuronske mreže

Ovo nije autoenkoder i nema neurone, slojeve, TFLite ni backpropagaciju.

1. Od 10 s zvuka računamo precizan prosječni spektar pomoću FFT-a 8192.
2. Opseg 10–4000 Hz sabijemo u 96 logaritamskih frekvencijskih traka.
3. Od svakog klipa dobijemo mali **otisak normalnog zvuka ventilatora**.
4. Na računaru iz 990 ispravnih source snimaka naučimo koje se komponente tog
   otiska normalno mijenjaju zajedno. Ledoit–Wolf regularizacija sprečava da
   matrica povjeruje slučajnom šumu.
5. Na pločici iz 5–40 dobrih snimaka novog ventilatora izmjerimo samo njegov
   centar.
6. Za svaki novi klip računamo Mahalanobisovu udaljenost od centra. Udaljenost
   je simetrična: hvata i porast i pad pojedinačnih spektralnih komponenti.

Jednostavna slika: veliki normalni korpus unaprijed nauči **oblik dozvoljenog
kretanja**, a kratka lokalna kalibracija kaže **gdje se baš ovaj ventilator
nalazi** unutar tog oblika.

## Zašto je bolji od log-mela i autoenkodera

Ventilator je periodična rotaciona mašina. Kvar često dodaje ili pomjera uske
harmonike i bočne linije. Dosadašnji 1024 FFT ima razmak oko 15,6 Hz i mel trake
dodatno spajaju susjedne frekvencije. Novi 8192 FFT ima razmak oko 1,95 Hz, pa
takve promjene ostaju vidljive.

Autoenkoder je pokušavao rekonstruisati 640 brojeva po prozoru i davao gotovo
isti MSE normalnom i neispravnom ventilatoru. Novi postupak direktno mjeri ono
što fizički očekujemo od rotacione mašine: stabilnost njenog uskog spektralnog
potpisa.

## Poštenost protokola

- Kovarijansa, normalizacija i budući firmware model uče se samo iz 990
  **normalnih source** snimaka.
- Varijanta `psd_shape` izabrana je na odvojenom source skupu: 800 normalnih za
  model, preostali normalni za kalibraciju/ocjenu i source anomalije samo za
  izbor feature-a. Na tom skupu AUC je 0,969 ± 0,004.
- Target anomalije nisu korištene za učenje matrice, centra ili izbor feature-a.
- U svakom ponavljanju klip izabran za lokalnu kalibraciju uklanja se iz skupa
  za ocjenu.
- Target AUC je ponovljen kroz 50 kalibracionih podjela; dodatna kontrola sa
  200 drugih seedova za k=20 dala je 0,867 ± 0,026.

Skript: [`pc/tools/bench_periodicity.py`](../../../pc/tools/bench_periodicity.py).  
Rezultati: `results/periodicity_fan_k{5,10,20,30,40}.json`.

Paralelna runda je nezavisno spojila ovaj PSD otisak sa još šest serija
scoring eksperimenata i potvrdila da je PSD sam jači od ansambla sa slabijim
mel score-om: [istrazivanje-preko-0674.md](istrazivanje-preko-0674.md).

## Istorijska procjena za ESP32-S3 i naknadna potvrda

Na dan prvog PC eksperimenta procjena po memoriji i broju operacija pokazivala
je da model staje na ESP32-S3, ali vrijeme, RAM i kontinuitet audio-toka tada
još nisu bili izmjereni stvarnim C kodom na pločici.

| Stavka | Float32 trošak |
|---|---:|
| Matrica 96 × 96 | 36 864 B |
| Source mean + std | 768 B |
| Centar novog ventilatora | 384 B |
| Množenja po 10 s klipu | 9 216 |

Float32 i float64 su u PC provjeri dali identičan AUC 0,86438. Novi front-end
traži 38 preklapajućih FFT-ova dužine 8192 po klipu. Izolovani čisti C modul je
napravljen i na realnom DCASE WAV-u daje maksimalnu PC↔C razliku 9,54e-07;
Mahalanobis score se relativno razlikuje 4,37e-07.

Taj istorijski implementacijski rizik je kasnije zatvoren: `ASD_PSD_LIVE`
build, live tok preko mikrofona, vrijeme oko 704 ms po klipu, RAM i
`dropped=0` potvrđeni su na ESP32-S3 u speaker/microphone postavci. To nije
potvrda rada uz fizički ventilator; taj eksperiment ostaje otvoren.

## AUC nije isto što i gotov alarmni prag

AUC 0,864 znači dobro rangiranje, ne automatski 86,4 % tačnih odluka. U kontroli
sa 200 podjela, k=20 i pragom na 90. percentilu kalibracionih leave-one-out
score-ova dobijeno je približno:

- odziv na anomalije 64,1 %,
- lažni alarmi 12,7 %,
- F1 0,727.

Sam prag nije dovoljan za miran samostalni alarm. Implementirano je zaključano
pravilo: alarm tek nakon tačno 3 uzastopna prozora, uz izlaznu histerezu 0,7.
Stabilnost praga kroz fizičke sesije još treba provjeriti. Kontinuirano
automatsko pomjeranje centra nije dozvoljeno jer bi moglo naučiti kvar kao
normalu.

## Granice tvrdnje

- Broj 0,864 važi za DCASE 2026 `fan` target domen i ovaj simulirani protokol
  lokalne kalibracije. Ne dokazuje još ponašanje na svakom fizičkom ventilatoru.
- DCASE source korpus ima 990 dobrih snimaka, ali nije zamjena za vlastiti
  korpus više stvarnih ventilatora, mikrofona, udaljenosti i prostorija.
- Test sa stvarnim ventilatorom i fizičkim kvarovima ostaje obavezan prije
  konačne tvrdnje master rada.

## Sljedeći tehnički koraci

Prva četiri prvobitna koraka su završena: PSD live mod, mjerenje vremena/RAM-a,
lokalni centar i prag te temporalna potvrda sa LED/serijskim statusom postoje.
Preostaje snimiti više stvarnih normalnih ventilatora i bezbjedno izazvanih
promjena, uz kompletno spojen hardver.

Artefakti pripremljeni 09.08.2026:

- `models/fan_psd_shape_meta.json` — porijeklo, specifikacija i checksum,
- `firmware/esp32s3_asd/main/psd_model_data.h` — float32 model,
- `firmware/esp32s3_asd/main/psd_features_c.{h,c}` — izolovani C front-end/score,
- `pc/tests/test_psd_features_c.py` — PC↔C provjera; cijeli paket 11/11 prolazi.

## Primarni izvori koji su usmjerili eksperiment

- [DCASE 2026 Task 2 — službeni opis i rezultati](https://dcase.community/challenge2026/task-first-shot-unsupervised-anomalous-sound-detection-for-machine-condition-monitoring-results)
- [Nishida et al., opis DCASE 2026 noise-aware ASD zadatka](https://arxiv.org/abs/2606.01578)
- [Saengthong i Shinozaki, BEAM/AdaBEAM podopsežno poređenje](https://arxiv.org/abs/2603.13749)
- [Službeni DCASE autoenkoder i Selective Mahalanobis baseline](https://github.com/nttcslab/dcase2023_task2_baseline_ae)
- [Liu et al., spektralno-vremenska fuzija za ASD rotacionih mašina](https://arxiv.org/abs/2201.05510)
- [Zhou i Wang, sistematsko poređenje ASD scoring backenda pod domain shiftom](https://arxiv.org/abs/2606.19269)
