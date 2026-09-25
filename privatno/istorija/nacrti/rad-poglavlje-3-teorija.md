# Poglavlje 3 — Teorijske osnove (draft)

> Draft za master rad. Prošireno iz [teorija-ucenje.html](../../ucenje/stari-pregledi/teorija-ucenje.html).
>
> **ISTORIJSKI AE/TFLM/GAMMA NACRT — zamijenjen finalnim putem.** Poglavlje
> čuva teoriju i raniju neuralnu fazu, ali ne opisuje trenutni detektor kao
> cjelinu. Finalna implementacija koristi visokorezolucioni `psd_shape`,
> Ledoit–Wolf preciziju, lokalni centar i Mahalanobis score bez TFLM-a, uz
> normal-only LOO prag i temporalnu politiku `n=3`. Za aktuelno stanje vidi
> [odluka-finalni-model.md](../../../docs/model/odluka-finalni-model.md).

## 3.1 Front-end: log-mel spektrogram

Sirovi audio signal (16 kHz, 10 s ≈ 160 000 uzoraka) previše je
visokodimenzionalan za direktnu obradu neuronskom mrežom. Standardni front-end
transformiše ga u kompaktan spektralni opis:

1. **STFT** — signal se dijeli na frejmove (1024 uzorka = 64 ms) sa preklapanjem
   50 % (hop 512), na svaki se primjenjuje Hann prozor i računa FFT. Rezultat je
   spektrogram vrijeme × frekvencija.
2. **Mel filterbanka** — 513 FFT binova grupiše se u 128 perceptualno
   ravnomjernih mel kanala (Slaney formula), po uzoru na nelinearnu frekvencijsku
   rezoluciju ljudskog sluha.
3. **Logaritam** — `log(mel + ε)` sabija dinamički opseg, u skladu sa
   logaritamskim doživljajem glasnoće.
4. **Kontekst** — P = 5 uzastopnih log-mel frejmova konkatenira se u vektor
   dimenzije 640, čime se hvata kratkoročna vremenska dinamika.

Kritičan zahtjev za deployment: front-end na PC-u (trening) i na uređaju
(inferenca) mora biti numerički identičan, inače model na uređaju "gleda"
drugačije ulaze. U ovom radu to je osigurano zajedničkim C kodom pozivanim i iz
Pythona (ctypes), sa izmjerenom razlikom < 4·10⁻⁵ dB na realnom klipu.

## 3.2 Autoencoder za detekciju anomalija

Autoenkoder (AE) je neuronska mreža obučena da rekonstruiše svoj ulaz kroz usko
grlo (*bottleneck*). Arhitektura baseline modela: 640 → 128×4 → 8 → 128×4 → 640,
sa Dense slojevima, ReLU aktivacijom i batch normalizacijom. Prisiljena da 640
vrijednosti sabije u 8, mreža uči suštinske obrasce normalnog zvuka.

**Anomaly score.** Mreža obučena samo na normalnom zvuku dobro rekonstruiše
normalne ulaze, a loše anomalne. Greška rekonstrukcije je stoga mjera
neobičnosti:
- **MSE mod:** score = srednji kvadrat razlike ulaza i rekonstrukcije.
- **MAHALA mod:** Mahalanobisova distanca rekonstrukcione greške u odnosu na
  kovarijansu grešaka fitovanu na treningu. Za razliku od MSE, MAHALA "zna" koje
  su greške tipične i na normalnom zvuku, pa bolje razdvaja *drugačiji ali
  ispravan* zvuk (domain shift) od stvarnog kvara.

## 3.3 Evaluacione metrike

- **ROC/AUC** — mjera razdvajanja nezavisna od izbora praga; AUC je vjerovatnoća
  da nasumičan anoman klip dobije viši score od nasumičnog normalnog.
- **pAUC** — AUC ograničen na zonu niskog broja lažnih alarma (FPR ≤ 0.1),
  operativno relevantnu za industrijsku primjenu.
- **Harmonijska sredina** AUC(source), AUC(target), pAUC — zvanični DCASE skor.
- **Gamma prag** — prag alarma kao 90. percentil gamma raspodjele fitovane na
  normalne score-ove; fituje se momentnom metodom (zatvorena forma iz srednje
  vrijednosti i varijanse) ili MLE, bez ikakvog korišćenja test skupa.

## 3.4 Kvantizacija (afina, int8)

Kvantizacija preslikava float32 parametre i aktivacije u int8 preko afine
transformacije: `realno ≈ scale × (int8 − zero_point)`. Parametri `scale` i
`zero_point` određuju se po tenzoru (ili kanalu) tako da pokriju stvarni opseg
vrijednosti, koji se procjenjuje provlačenjem reprezentativnog skupa kroz model.
Post-training kvantizacija (PTQ) primjenjuje se na već obučen model i jeftina je;
quantization-aware training (QAT) je skuplja rezerva. Prednosti int8: 4× manja
memorija i znatno brža aritmetika, posebno uz SIMD instrukcije.

## 3.5 Arhitektura ESP32-S3 i embedded izvršavanje

**Xtensa LX7 jezgro** sa PIE (*Processor Instruction Extensions*) SIMD
instrukcijama koje ubrzavaju int8 operacije. **Memorijska hijerarhija:** 512 KB
internog SRAM-a (jedini koji DMA vidi), do 16 MB eksternog PSRAM-a (velik ali
sporiji, DMA ga ne pristupa), flash za kod i konstante. Ova podjela diktira
arhitekturu firmvera: DMA baferi u SRAM, veliki baferi u PSRAM, model i tabele
u flash.

**TensorFlow Lite Micro (TFLM)** izvršava kvantizovani model bez dinamičke
alokacije, iz statički rezervisane *tensor arene*. Optimizovani int8 kerneli
(esp-nn) koriste PIE. U istorijskom AE putu procjena ispod 25 kB odnosila se
samo na dio streaming log-mel feature obrade, ne na cijeli firmware niti na
finalni PSD put. Finalni PSD firmware takođe koristi streaming da ne baferuje
oko 640 kB velik puni float ulazni prozor; njegov build report navodi oko
293 kB zauzetog i 342 kB slobodnog DIRAM-a.

## 3.6 On-device kalibracija praga

Uređaj može sam izračunati prag na novoj mašini: akumulira score-ove normalnog
rada (Welfordov algoritam za srednju vrijednost i varijansu), momentnom metodom
procijeni parametre gamma raspodjele, i preko Wilson–Hilferty aproksimacije
inverzne gamma CDF izračuna 90. percentil — sve u čistoj aritmetici, bez
prenosa podataka u cloud. U ovom radu potvrđeno na hardveru: prag izračunat na
čipu poklapa se sa referentnim PC pragom unutar 0.03 %.
