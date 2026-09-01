# Uputstvo 3 — literatura: koji radovi, gdje se koriste, šta u njima čitati

**Napisano:** 01.09.2026.

> **Prvo, pošteno:** PDF-ovi ovih radova **nisu preuzeti u repo**. U projektu
> postoje samo citati i linkovi — u
> [`../../plan-master-rada.md`](../../plan-master-rada.md) (sekcije 2 i 12),
> [`istrazivanje-psd-model.md`](../../docs/istrazivanje-psd-model.md) (dno) i u spisku
> literature master rada
> ([`../../radovi/master-rad/rad_tekst.py`](../../radovi/master-rad/rad_tekst.py),
> funkcija `_literatura`). Ovaj dokument ih sabira na jedno mjesto i za svaki
> kaže **zašto postoji u ovom radu** i **šta u njemu treba pročitati**.
> Preuzimanje PDF-ova: vidi [odjeljak 5](#5-kako-preuzeti-pdf-ove).

Oznake važnosti:

- ★★★ — bez ovoga ne možeš odbraniti rad
- ★★ — čitati zbog konteksta i poređenja
- ★ — referenca, dovoljno znati da postoji

---

## 1. DCASE Task 2 — definicija zadatka i baseline

Ovo je grupa radova koja definiše **šta se tačno mjeri** i sa čim se porediš.
Svi imaju istu strukturu: uvod → opis zadatka → baseline sistem → rezultati →
zaključak. Za odbranu ti trebaju **opis zadatka** i **tabele rezultata**.

| # | Rad | Link | Važnost |
|---|---|---|---|
| 1 | Nishida et al., *Description and discussion on DCASE 2026 Challenge Task 2: Noise-aware unsupervised ASD for machine condition monitoring* | [arXiv:2606.01578](https://arxiv.org/abs/2606.01578) | ★★★ |
| 2 | Harada et al., *First-shot anomaly sound detection for machine condition monitoring: A domain generalization baseline*, EUSIPCO 2023, **str. 191–195** | [doi:10.23919/EUSIPCO58844.2023.10289721](https://doi.org/10.23919/EUSIPCO58844.2023.10289721) | ★★★ |
| 3 | DCASE 2024 Task 2 description | [arXiv:2406.07250](https://arxiv.org/abs/2406.07250) | ★★ |
| 4 | DCASE 2022 Task 2 description (domain generalization) | [arXiv:2206.05876](https://arxiv.org/abs/2206.05876) | ★★ |
| 5 | DCASE 2020 Task 2 description (originalna definicija zadatka) | [arXiv:2006.05822](https://arxiv.org/abs/2006.05822) | ★★ |
| 6 | DCASE 2021 / 2023 Task 2 | [arXiv:2106.04492](https://arxiv.org/abs/2106.04492) · [arXiv:2305.07828](https://arxiv.org/abs/2305.07828) | ★ |

**Gdje se koriste u projektu:**

- Referenca [1] u radu i cijela postavka mjerenja — 7 mašina, `source`/`target`
  domen, first-shot uslovi.
- Baseline autoenkoder iz [2]/[3] je tačno ono što je implementirano u
  [`../../pc/asd/model.py`](../../pc/asd/model.py) (640→128→8→128→640) i što je dalo
  AUC 0,451 na `fan` target domenu.
- Metrika (AUC + pAUC pri FPR ≤ 0,1, harmonijska sredina) implementirana u
  [`../../pc/asd/eval.py`](../../pc/asd/eval.py).

**Šta konkretno čitati:**

| Rad | Odjeljci koje treba pročitati | Šta iz njih uzimaš |
|---|---|---|
| [1] Nishida 2026 | odjeljak sa **opisom zadatka** i **postavkom podataka**; tabela sa baseline rezultatima | definicija first-shot i noise-aware postavke; brojevi sa kojima porediš svoje |
| [2] Harada 2023 (5 strana, čitaj cio) | posebno **opis baseline sistema** i **evaluacione metrike** | tačna arhitektura AE-a, MSE vs Mahalanobis scoring, formula harmonijske sredine |
| [3]–[5] | **samo tabele rezultata i odjeljak o domenskom pomaku** | istorijski trend i kontekst; nemoj čitati cijele |

> Praktičan savjet: [2] je najkorisniji jedan rad u cijelom spisku — kratak je,
> a sadrži i arhitekturu i metriku koje si direktno implementirao.

---

## 2. Datasetovi

| # | Rad | Link | Važnost |
|---|---|---|---|
| 7 | DCASE 2026 Task 2 **development dataset** (7 zipova, 4,6 GB) | [Zenodo 19336329](https://zenodo.org/records/19336329) | ★★★ |
| 8 | Dohi et al., *MIMII DG: Sound dataset for malfunctioning industrial machine investigation and inspection for domain generalization task*, DCASE Workshop 2022, str. 1–5 | [dcase.community](https://dcase.community) | ★★ |
| 9 | Harada et al., *ToyADMOS2*, DCASE Workshop 2021, str. 1–5 | [doi:10.5281/zenodo.5770113](https://doi.org/10.5281/zenodo.5770113) | ★★ |

**Gdje se koriste:** [7] su podaci na kojima je sve mjereno
([`../../pc/asd/data.py`](../../pc/asd/data.py) očekuje raspakovanu strukturu
`data/dcase2026_dev/<masina>/{train,test}`). [8] i [9] su izvorni skupovi od
kojih je DCASE 2026 sastavljen — citiraju se, ne koriste direktno.

**Šta čitati:** kod oba rada dovoljni su **opis snimanja** (mikrofoni,
udaljenost, uslovi) i **spisak tipova kvarova**. To je jedini dio koji ti treba
da bi u radu mogao napisati *šta „anomalija" u ovom skupu zapravo jeste* — a to
je važno, jer je izmjereno da DCASE anomalija odgovara kvaru od oko −30 dB, što
je vrlo suptilno ([`put-do-modela.md`](../../docs/put-do-modela.md), faza 5).

---

## 3. Metode — teorijska osnova finalnog modela

Ova tri rada su **temelj onoga što je stvarno na pločici**.

| # | Rad | Link | Važnost |
|---|---|---|---|
| 10 | P. D. Welch, *The use of the fast Fourier transform for the estimation of power spectra*, IEEE Trans. Audio Electroacoust., **vol. 15, br. 2, str. 70–73**, 1967 | [doi:10.1109/TAU.1967.1161901](https://doi.org/10.1109/TAU.1967.1161901) | ★★★ |
| 11 | O. Ledoit i M. Wolf, *A well-conditioned estimator for large-dimensional covariance matrices*, J. Multivariate Anal., **vol. 88, br. 2, str. 365–411**, 2004 | [doi:10.1016/S0047-259X(03)00096-4](https://doi.org/10.1016/S0047-259X(03)00096-4) | ★★★ |
| 12 | P. C. Mahalanobis, *On the generalised distance in statistics*, Proc. Natl. Inst. Sci. India, **vol. 2, br. 1, str. 49–55**, 1936 | (istorijski, dostupan slobodno) | ★★ |

**Gdje se koriste:**

- **Welch [10]** → [`psd_features_c.c`](../../firmware/esp32s3_asd/main/psd_features_c.c)
  i `bench_periodicity.py`: `nperseg = 8192`, preklapanje 50 %, Hann prozor. To je
  doslovno metod iz ovog rada.
- **Ledoit–Wolf [11]** → procjena kovarijanse iz 990 snimaka, čiji inverz je
  matrica 96×96 u [`psd_model_data.h`](../../firmware/esp32s3_asd/main/psd_model_data.h).
  Bez skupljanja inverz nije numerički siguran.
- **Mahalanobis [12]** → funkcija `asd_psd_score` u istom C fajlu.

**Šta čitati:**

| Rad | Koliko | Šta tražiti |
|---|---|---|
| [10] Welch | **cijela 4 strane** — kratak je i vrijedi ga pročitati u cjelini | zašto se periodogrami usrednjavaju, uticaj preklapanja i prozora na varijansu procjene |
| [11] Ledoit–Wolf | **uvod + dio u kojem se definiše estimator i optimalni koeficijent skupljanja** (prvih desetak strana). Ostatak je asimptotska teorija i dokazi — **preskoči ih** | formula oblika `(1−α)·S + α·(tr(S)/p)·I` i argument zašto se `α` može odrediti iz samih podataka |
| [12] Mahalanobis | **7 strana, čitaj cio** ako te zanima istorija; za rad je dovoljna definicija | originalna definicija udaljenosti |

---

## 4. TinyML i deployment na mikrokontroler

Ova grupa je kontekst za poglavlje o edge implementaciji. **Nijedan od njih nije
direktno implementiran** — koriste se za poređenje i za formulaciju „rupe" koju
rad popunjava.

| # | Rad / izvor | Link | Važnost |
|---|---|---|---|
| 13 | TinyML → TinyDL survey (2025) | [arXiv:2506.18927](https://arxiv.org/abs/2506.18927) | ★★ |
| 14 | ESP32-S3 TFLM deployment šablon (ArrythML) | [arXiv:2606.02256](https://arxiv.org/abs/2606.02256) | ★★ |
| 15 | AE TinyML na Cortex-M4 (7,5 KB model) | [ResearchGate 364182863](https://www.researchgate.net/publication/364182863) | ★★ |
| 16 | LSTM-AE za urbani šum na ESP32 | [ScienceDirect S2542660523001713](https://www.sciencedirect.com/science/article/pii/S2542660523001713) | ★ |
| 17 | TinyML research trends (2025) | [ScienceDirect S2590005625003017](https://www.sciencedirect.com/science/article/pii/S2590005625003017) | ★ |
| 18 | Warden & Situnayake, *TinyML* (knjiga, O'Reilly) | — | ★★ |

**Šta čitati i zašto:**

- [13] i [17] — **samo poglavlja o on-device učenju i energetskom profilisanju**.
  Odatle dolazi argument iz uvoda rada: ta dva pitanja su u literaturi
  eksplicitno navedena kao otvorena, a ovaj rad ih dodiruje (kalibracija na
  uređaju + INA226 mjerenje).
- [14] — **workflow deploymenta** (konverzija → `xxd` → fleš → TFLM). To je tačno
  put koji je odrađen za istorijski TFLM mod; domen (EKG) nije bitan.
- [15] i [16] — za tabelu poređenja: šta jesu i **šta nisu** uradili (nema DCASE
  protokola, nema domain-shift evaluacije, nije MCU klasa…). Ta tabela je u
  [`../../plan-master-rada.md`](../../plan-master-rada.md), sekcija 2.3.
- [18] — **poglavlja o kvantizaciji i o TFLM areni**, ako želiš temeljno
  razumijevanje umjesto samo upotrebe.

---

## 5. Radovi na koje se projekat oslanjao u istraživanju modela

Ovi se pominju u [`istrazivanje-psd-model.md`](../../docs/istrazivanje-psd-model.md) i
[`put-do-modela.md`](../../docs/put-do-modela.md) kao potvrda ili kontrast nalazima.

| # | Rad | Link | Zašto |
|---|---|---|---|
| 19 | Zhou i Wang, sistematsko poređenje ASD scoring backenda pod domenskim pomakom | [arXiv:2606.19269](https://arxiv.org/abs/2606.19269) | potvrđuje našu pouku: **front-end nosi više od backenda** |
| 20 | Saengthong i Shinozaki, BEAM/AdaBEAM podopsežno poređenje | [arXiv:2603.13749](https://arxiv.org/abs/2603.13749) | podopsežni pristupi, kontekst za izbor 96 traka |
| 21 | Liu et al., spektralno-vremenska fuzija za ASD rotacionih mašina | [arXiv:2201.05510](https://arxiv.org/abs/2201.05510) | zašto rotacione mašine traže drugačiji front-end |
| 22 | Zvanični DCASE AE + Selective Mahalanobis baseline (kod) | [github.com/nttcslab/dcase2023_task2_baseline_ae](https://github.com/nttcslab/dcase2023_task2_baseline_ae) | referentna implementacija koju smo reprodukovali |
| 23 | CLP-SCF kontrastivno učenje | [arXiv:2304.03588](https://arxiv.org/abs/2304.03588) | alternativni pravac koji nije uzet |
| 24 | AEGM — pregled AE varijanti | [arXiv:2311.08829](https://arxiv.org/abs/2311.08829) | zašto AE varijante nisu dalje gurane |

> ⚠ **Referenca [19] je u master radu označena kao `[TODO]`** — u
> `rad_tekst.py` piše da treba provjeriti tačne autore i stranice prije predaje.
> To je jedina nezatvorena stavka u spisku literature.

**Šta čitati:** kod [19] je dovoljan **odjeljak sa poređenjem backenda i
zaključak** — to je rad koji ti u odbrani daje spoljnu potvrdu da tvoj najveći
dobitak (promjena front-enda) nije slučajnost. Kod [21] pročitaj **uvod i
motivaciju**: tu je fizičko obrazloženje harmonijskih linija rotacionih mašina.

---

## 6. Tehnička dokumentacija (nije „literatura", ali je obavezna)

| Izvor | Šta gledati | Link |
|---|---|---|
| ESP32-S3 Series Datasheet | memorijska mapa, PSRAM, ograničenja GPIO | [espressif.com](https://www.espressif.com/) |
| ESP32-S3 Technical Reference Manual | **poglavlja o I2S, PIE i SRAM/kešu** | Espressif |
| ESP-IDF Programming Guide v5.5 | `i2s_std` drajver, FreeRTOS, NVS | [docs.espressif.com](https://docs.espressif.com/projects/esp-idf/) |
| InvenSense INMP441 datasheet (DS-INMP441) | format podataka, 24 bita u 32-bitnom slotu, `L/R` pin | InvenSense |
| esp-tflite-micro / esp-nn / esp-dsp | TFLM port, PIE kerneli, DSP funkcije | [esp-tflite-micro](https://github.com/espressif/esp-tflite-micro) · [esp-nn](https://github.com/espressif/esp-nn) · [esp-dsp](https://github.com/espressif/esp-dsp) |
| Pedregosa et al., *Scikit-learn*, JMLR 12, str. 2825–2830, 2011 | alat (Ledoit–Wolf, ROC/AUC) | — |
| Virtanen et al., *SciPy 1.0*, Nature Methods 17, str. 261–272, 2020 | alat (FFT, statistika) | [doi:10.1038/s41592-019-0686-2](https://doi.org/10.1038/s41592-019-0686-2) |

**INMP441 datasheet je jedini dokument iz ove tabele koji vrijedi pročitati u
cjelini** — kratak je, a objašnjava tačno ono što je u
[`audio_i2s.c`](../../firmware/esp32s3_asd/main/audio_i2s.c) implementirano.

---

## 7. Redoslijed čitanja — ako imaš samo jedan dan

1. **Harada 2023 (EUSIPCO, 5 str.)** — zadatak, baseline, metrika. ★★★
2. **Welch 1967 (4 str.)** — srce front-enda. ★★★
3. **Nishida 2026, odjeljak sa opisom zadatka** — aktuelna postavka. ★★★
4. **Ledoit–Wolf, uvod + definicija estimatora** — zašto je kovarijansa sigurna. ★★★
5. **Zhou i Wang [19], zaključak** — spoljna potvrda glavne pouke. ★★
6. **INMP441 datasheet** — hardverska strana. ★★

Poslije toga možeš objasniti svaki brojku u radu i svaku liniju u
`psd_features_c.c`.

---

## 8. Kako preuzeti PDF-ove

PDF-ovi nisu u repou i `data/`-stil velikih binarnih fajlova se namjerno ne
komituje. Ako ih želiš lokalno, arXiv radovi se skidaju direktno (svaki
`arxiv.org/abs/XXXX` ima `arxiv.org/pdf/XXXX`):

```bash
mkdir -p radovi/literatura && cd radovi/literatura && for id in 2606.01578 2406.07250 2206.05876 2006.05822 2506.18927 2606.02256 2606.19269 2603.13749 2201.05510; do curl -L -o "arxiv_$id.pdf" "https://arxiv.org/pdf/$id"; done
```

Radovi iza IEEE/Elsevier paywalla (Welch, Ledoit–Wolf, MIMII DG, ToyADMOS2) se
skidaju preko fakultetskog pristupa ili sa DCASE stranice
([dcase.community](https://dcase.community), Task 2 po godinama — workshop radovi
su tamo besplatni).

> Ako dodaješ `radovi/literatura/`, dodaj je i u `.gitignore` ili je komituj
> svjesno — desetak PDF-ova je 20–50 MB.
