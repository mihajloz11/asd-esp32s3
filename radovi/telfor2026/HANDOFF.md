# TELFOR 2026 — handoff za pisanje rada

**Stanje 27.08.2026:** rad je ažuriran rezultatima dva validna fizička
mjerenja na ventilatoru i ponovo renderovan — **4 strane**. Ostala je jedna
`[TODO]` oznaka, IEEE copyright broj, koji se dobija tek u registracionom
sistemu. Šta još fali: [`PREOSTALO-RAD.md`](PREOSTALO-RAD.md).

**Šta se promijenilo u odnosu na verziju od 14.08.:** bin 316 400 → 354 784 B,
račun 704 → 716 ms po prozoru, pravilo praga `max(p90, mean+3σ)` → normal-only
p99 ulaz / p95 izlaz sa odvojenim VERIFY-em, dodata kapija pouzdanosti
(`OBSERVATION_HOLD`), popunjena Tabela III, dodata Sl. 2 sa fizičkog mjerenja,
izbačena sekcija o potrošnji i fotografija ploče. Sekcija VI više ne prijavljuje
nestabilnost praga kao otvoren problem nego kao izmjeren problem sa izmjerenim
rješenjem, uz četvrti negativan rezultat koji je uređaj sam odbio na VERIFY-u.
Puna analiza: [`docs/rezultat-finalna-validacija-2026-08-27.md`](../../docs/rezultat-finalna-validacija-2026-08-27.md).

Ovaj fajl ostaje kao zapis o formatu i izvorima brojeva.

---

## 1. Pravila TELFOR-a (provjereno na telfor.rs, 14.08.2026)

| Stavka | Vrijednost |
|---|---|
| Dužina | **najviše 4 A4 strane** (redovni i studentski rad); pozvani 8 |
| Format | **IEEE dvokolonski konferencijski šablon, A4** |
| Alat | MS Word ili LaTeX; predaja u **PDF** |
| Jezik | engleski **ili** srpski |
| Validacija | IEEE PDF eXpress prije predaje |
| Predaja | https://registration.telfor.rs/ |
| Konferencija | **34. TELFOR, Beograd, 24–26. novembar 2026.** (potvrđeno na telfor.rs) |
| **Rok za rad** | **4. septembar 2026.** |
| Obavještenje | 27. oktobar 2026. |
| Program | 16. novembar 2026. |
| Ograničenje | najviše 3 rada po autoru; obavezna prezentacija; bez survey/tutorial radova osim po pozivu |
| Copyright | ide na dno prve strane; **tačan broj se dobija u registracionom sistemu** — treba ga uzeti odande |

**Rok je tri sedmice od danas.** To je glavno vremensko ograničenje.

## 2. Šta je skinuto

```
radovi/telfor2026/
  sablon/
    IEEE_conference_template_a4.docx   zvanični IEEE A4 šablon (32 KB)
    Call_for_papers_TELFOR_2025.pdf
  primjeri/
    TELFOR2009_10_14.pdf               PRAVI konferencijski rad, 4 strane, srpski
    TelforJournal_Vol17No1_A1.pdf      Telfor Journal (prošireni format, 6 str.)
    TelforJournal_Vol16No2_A1.pdf      Telfor Journal
```

### Izmjereno iz zvaničnog šablona (ne prepisano napamet)

- stranica A4 210 × 297 mm
- margine: gore **9,53 mm**, dolje **25,4 mm**, lijevo/desno **15,75 mm**
- stilovi u šablonu: `paper title` (24 pt), `Author` (9 pt), `Abstract` (9 pt),
  `Keywords`, `Heading 1..4`, `Body Text`, `references`, `sponsors` (8 pt)
- šablon ima **6 sekcija** (naslovni blok 1 kolona, autorski blok 3 kolone,
  tijelo 2 kolone). Za 1–2 autora se autorski 3-kolonski blok ne koristi —
  dovoljne su dvije sekcije: naslov/autori 1 kolona, tijelo 2 kolone.

### Struktura pravog TELFOR konferencijskog rada (iz TELFOR2009)

```
17. Telekomunikacioni forum TELFOR 2009    Srbija, Beograd, novembar 24.-26., 2009.
<Naslov>
<Autori, u jednom redu>
Sadržaj — ...            (Abstract — ako je engleski)
Ključne reči — ...       (Keywords — ...)
I. UVOD                  (rimski brojevi, velika slova)
II. ...
```

## 3. Odluke — potvrđene 14.08.2026

| # | Pitanje | Odluka | Zašto |
|---|---|---|---|
| 1 | **Jezik** | **engleski** | TELFOR prima oba, ali u IEEE Xplore idu engleski radovi; korisno i za CV i inostrane prijave |
| 2 | **Autori** | **Mihajlo Živković, Ivan Mezei** | tim redoslijedom; u radu samo zajednička afilijacija: University of Novi Sad, Faculty of Technical Sciences, Novi Sad, Serbia. Interno: Mezei je na Chair of Electronics; `imezei@uns.ac.rs` potvrđen na [zvaničnoj FTN stranici](https://ftn.uns.ac.rs/944/ivan-mezei) |
| 3 | Kategorija | **redovan rad** | studentska sekcija po pozivu za radove prima **samo studente kao autore** (mentor ide u fusnotu) i objavljuje **samo u CD zborniku, ne u Xploreu** — a engleski je izabran baš zbog Xplorea. Detalji i tabela poređenja: [PREOSTALO-RAD.md](PREOSTALO-RAD.md) |
| 4 | Kalibracija | **k=10 u firmwareu i demonstraciji** | oko 115 s i 0,8556 ± 0,0240 AUC / 20 splitova; **k=20** ostaje samo kanonski PC referentni rezultat, 0,8666 AUC / 100 splitova |

Rad se piše na engleskom, dakle `Abstract —` / `Keywords —`, ne `Sadržaj —` /
`Ključne reči —`.

## 4. Predložena struktura rada (4 strane)

```
I.   INTRODUCTION
II.  SYSTEM OVERVIEW
     A. Hardware   B. Feature and model   C. On-device operating flow
III. FAIL-CLOSED CALIBRATION AND DECISION HIERARCHY
IV.  NORMAL-ONLY DESIGN PROTOCOL
V.   RESULTS
     A. Benchmark   B. Temporal decision   C. On-device   D. [ostavljeno za ventilator]
VI.  THRESHOLD INSTABILITY (otvoren problem)
VII. CONCLUSION AND FUTURE WORK
REFERENCES
```

**Ugao rada koji ga čini objavljivim:** nije „još jedan AUC na DCASE-u" nego
**šta se pokvari kad se isti pristup stvarno stavi na mikrokontroler** —
fail-closed kalibracija, hijerarhija odlučivanja, sve politike izvedene bez
ijedne anomalije, i tri izmjerena **negativna** rezultata.

## 5. Brojke za rad — sve provjerene, nijedna napamet

### Hardver i implementacija
| | |
|---|---|
| Platforma | ESP32-S3-WROOM-1 N32R16V, 240 MHz, 16 MB PSRAM |
| Mikrofon | INMP441 MEMS I2S, 16 kHz, 16-bit |
| ESP-IDF | v5.5.5 |
| Binarni fajl | 316 400 B; **92 %** app particije slobodno |
| Račun po klipu | **704 ms** na 10 s prozora → **14,2×** rezerve u realnom vremenu |

### Feature i model
| | |
|---|---|
| Feature | Welch PSD (`nperseg` 8192, 50 % preklapanje) → **96** log-raspoređenih traka 10–4000 Hz → oduzeta sredina |
| Model | globalna standardizacija + Ledoit-Wolf precision na `source/train/normal` (**990** klipova); lokalni centar iz **10** kalibracionih klipova; Mahalanobis |
| Score | `s(x) = (z − c)ᵀ P (z − c)`; kvadrirani Mahalanobis score |
| Prag | `max(p90 LOO, sredina + 3σ LOO)` |
| Gate prisustva | iznad kalibrisane sredine − **11 dB** odmah znači prisutna mašina; tek **3 uzastopna prozora ispod** znače da je stala |
| Vremenska odluka | 3 uzastopna prozora, izlaz iz alarma ispod **0,7×** praga |

### Tabela I — kandidati (DCASE 2026 dev, fan, k=10, 20 splitova)
| kandidat | AUC | pAUC@0,1 | Δ |
|---|---|---|---|
| `psd_shape` (baseline) | **0,8556 ± 0,0240** | 0,6393 | — |
| `psd_order` (f0/red) | 0,6388 ± 0,0467 | 0,5171 | −0,2168 |
| `psd_regime` | 0,8556 ± 0,0240 | 0,6393 | 0,0000 |
| `psd_logratio` (dual-ch) | 0,7185 ± 0,0347 | 0,5848 | −0,1371 |
| `psd_coherence` (dual-ch) | 0,7506 ± 0,0398 | 0,5774 | −0,1050 |
| `psd_masked` (dual-ch) | 0,4500 ± 0,0645 | 0,4884 | −0,4056 |
| `transient` | 0,5647 ± 0,0267 | 0,5062 | −0,2909 |
| `psd_plus_transient` | 0,8568 ± 0,0258 | 0,6433 | +0,0012 |

Izvor: `results/advanced/advanced_results.json`

Odvojeni kanonski PC referentni rezultat koristi **k=20 i 100 splitova**:
`psd_shape` AUC **0,8666**. Ne predstavljati ga kao konfiguraciju ugrađenu u
firmware; ugrađena/demonstrirana konfiguracija je k=10.

### Tabela II — vremenska pravila (40 splitova, 2000 normalnih prozora)
| pravilo | lažnih/h | tuđa mašina/h | pobuda 1 prozor | kašnjenje |
|---|---|---|---|---|
| 3 uzastopna | 0,00 | 11,16 | 0,004 | 3 |
| 4 uzastopna | 0,00 | 10,98 | 0,000 | 4 |
| **histereza 1,0/0,7 + n=3** | **0,00** | **5,40** | **0,000** | **3** |
| EWMA(0,4) + n=3 | 5,40 | 6,48 | 0,592 | 3 |
| CUSUM k=0,5 h=2 | 5,40 | 11,16 | 0,721 | 1 |

Izvor: `pc/config/asd_temporal_policy_v1.json`

### Tabela III — nestabilnost praga (glavni otvoren nalaz)
| prolaz | prag | LOO CV | iznad praga | opažene alarmne epizode/h |
|---|---|---|---|---|
| 1 (8 min) | 5687 | 1,77 | 0 % | 0,00 |
| 2 (30 min) | 347 | 0,36 | 91 % | 8,69 (kontaminiran speaker run; nije čista procjena lažnih alarma) |
| 3 (20 min, čist) | 1088 | 0,59 | 5,6 % | **0,00** |

Ukrštena provjera nad **istim** prozorima: prozori prolaza 1 ocijenjeni pragom
prolaza 2 → 92 % iznad praga; obrnuto → 8 %. Medijana score-a se kroz tri
prolaza razlikuje **4,689×** (oko 4,7×), a prag 16×.

### Mjerenje na uređaju (prolaz 3, čist)
| | |
|---|---|
| DET prozora | 107 (17,6 min) |
| prozora iznad praga | 6 (5,6 %) |
| alarmnih epizoda | **0 opaženih tokom 17,6 min** |
| kvalitet | **177 mjerenih audio-prozora**, svi `OK`, plus 1 `CAL_SUMMARY` zapis |
| `dropped_delta` | **0 u svih 177 mjerenih prozora** |

PC je tokom ovog bench prolaza služio samo kao izvor audio-stimulusa preko
zvučnika. Kalibracija, score, prag, temporalna odluka i alarm izvršavali su se
na ESP32-S3, bez hosta u putanji odlučivanja.

> ⚠️ **Preciznost koja se ne smije izgubiti:** kumulativni `dropped` brojač na
> kraju kalibracije pokazuje 122 880 uzoraka. To **nisu** izgubljeni mjerni
> uzorci — nastaju dok uređaj stoji u praznom hodu i čeka taster, kada ring
> buffer niko ne prazni. Mjerodavno je `dropped_delta = 0` po prozoru. U radu
> se smije tvrditi samo to drugo.

## 6. Gdje ostaviti prostor (eksplicitan zahtjev)

Rad mora imati jasno označena mjesta za ono što još nije urađeno
(vidi [`docs/PREOSTALO.md`](../../docs/PREOSTALO.md)):

1. **Sekcija V.D — fizički ventilator.** Tabela sa `TBD`: prolaz sa stvarnim
   ventilatorom, bezbjedno izazvana promjena, latencija alarma, oporavak.
2. **Potrošnja (E5, INA226).** Nije mjereno; čeka 5 V izvor i re-arm firmvera.
3. **Slika postavke.** Fotografija zalemljene ploče sa tasterom i LED —
   nema je dok se ne zalemi.
4. **Copyright broj** na dnu prve strane — uzima se iz registracionog sistema.

## 7. Reference — provjerene prema primarnim izvorima 14.08.2026.

- N. Harada et al., „First-shot anomaly **sound** detection for machine
  condition monitoring: A domain generalization baseline", *EUSIPCO 2023*,
  pp. 191–195, doi: `10.23919/EUSIPCO58844.2023.10289721`.
- N. Harada et al., „ToyADMOS2: Another dataset of miniature-machine operating
  sounds for anomalous sound detection under domain shift conditions",
  *DCASE Workshop 2021*, pp. 1–5, doi: `10.5281/zenodo.5770113`.
- K. Dohi et al., „MIMII DG: Sound dataset for malfunctioning industrial
  machine investigation and inspection for domain generalization task",
  *DCASE Workshop 2022*, pp. 1–5.
- P. D. Welch, „The use of the fast Fourier transform for the estimation of
  power spectra: A method based on time averaging over short, modified
  periodograms", *IEEE Trans. Audio Electroacoust.*, vol. 15, no. 2,
  pp. 70–73, doi: `10.1109/TAU.1967.1161901`.
- O. Ledoit and M. Wolf, „A well-conditioned estimator for large-dimensional
  covariance matrices", *J. Multivariate Anal.*, vol. 88, no. 2, pp. 365–411,
  doi: `10.1016/S0047-259X(03)00096-4`.
- T. Nishida et al., „Description and discussion on DCASE 2026 Challenge Task
  2: Noise-aware unsupervised anomalous sound detection for machine condition
  monitoring", arXiv:`2606.01578`, 2026.

## 8. Prvi korak u novom četu

1. Ponovo generisati `radovi/telfor2026/telfor2026_asd_esp32s3.docx` iz
   ažuriranog `build_paper.py`.
2. Provjeriti izgled renderovanjem u PDF i gledanjem svih strana:
   `soffice --headless --convert-to pdf` pa `pdftoppm -jpeg -r 100`.
3. Držati se 4 strane — to je tvrdo ograničenje, ne preporuka.
