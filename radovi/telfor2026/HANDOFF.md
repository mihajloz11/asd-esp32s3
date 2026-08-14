# TELFOR 2026 — handoff za pisanje rada

**Stanje:** istraživanje formata završeno, materijali skinuti, rad **još nije kucan**.
**Nastavlja se u novom četu.** Ovaj fajl je sve što je potrebno da se nastavi.

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
| 2 | **Autori** | **Mihajlo Živković, Ivan Mezei** | tim redoslijedom; afilijacija za oba: University of Novi Sad, Faculty of Technical Sciences |
| 3 | Kategorija | studentski rad | provjeriti da li se prijavljuje kao studentski (može nositi nagradu) — **jedino još otvoreno** |

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
| Binarni fajl | 316 464 B; **92 %** app particije slobodno |
| Račun po klipu | **705 ms** na 10 s prozora → **14,2×** rezerve u realnom vremenu |

### Feature i model
| | |
|---|---|
| Feature | Welch PSD (`nperseg` 8192, 50 % preklapanje) → **96** log-raspoređenih traka 10–4000 Hz → oduzeta sredina |
| Model | globalna standardizacija + Ledoit-Wolf precision na `source/train/normal` (**990** klipova); lokalni centar iz **10** kalibracionih klipova; Mahalanobis |
| Prag | `max(p90 LOO, sredina + 3σ LOO)` |
| Gate prisustva | nivo ≥ kalibrisana sredina − **11 dB**, 3 uzastopna prozora |
| Vremenska odluka | 3 uzastopna prozora, izlaz iz alarma ispod **0,7×** praga |

### Tabela I — kandidati (DCASE 2026 dev, fan, 20 splitova)
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
| prolaz | prag | LOO CV | iznad praga | lažnih/h |
|---|---|---|---|---|
| 1 (8 min) | 5687 | 1,77 | 0 % | 0,00 |
| 2 (30 min) | 347 | 0,36 | 91 % | 8,69 (kontaminiran) |
| 3 (20 min, čist) | 1088 | 0,59 | 5,6 % | **0,00** |

Ukrštena provjera nad **istim** prozorima: prozori prolaza 1 ocijenjeni pragom
prolaza 2 → 92 % iznad praga; obrnuto → 8 %. Medijana score-a se razlikuje samo
2,8×, prag 16×.

### Mjerenje na uređaju (prolaz 3, čist)
| | |
|---|---|
| DET prozora | 107 (17,6 min) |
| prozora iznad praga | 6 (5,6 %) |
| alarmnih epizoda | **0** |
| **lažnih alarma na sat** | **0,00** |
| QUALITY zapisa / ne-`OK` | 178 / **0** |
| `dropped_delta` | **0 u svih 178 mjerenih prozora** |

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
5. **E-mail adresa i tačan naziv katedre za Ivana Mezeija** u autorskom bloku —
   ime je potvrđeno, kontakt podaci nisu.

## 7. Reference — provjerene, ne izmišljene

- P. Welch, „The use of the fast Fourier transform for the estimation of power
  spectra", *IEEE Trans. Audio Electroacoust.*, vol. 15, no. 2, pp. 70–73, 1967.
- O. Ledoit, M. Wolf, „A well-conditioned estimator for large-dimensional
  covariance matrices", *J. Multivariate Anal.*, vol. 88, no. 2, pp. 365–411, 2004.
- Y. Koizumi et al., „ToyADMOS: A dataset of miniature-machine operating sounds
  for anomalous sound detection", *WASPAA*, 2019.
- H. Purohit et al., „MIMII Dataset: Sound dataset for malfunctioning industrial
  machine investigation and inspection", *DCASE Workshop*, 2019.
- N. Harada et al., „ToyADMOS2: Another dataset of miniature-machine operating
  sounds for anomalous sound detection under domain shift conditions",
  *DCASE Workshop*, Barcelona, Nov. 2021.
- K. Dohi et al., „MIMII DG: Sound dataset for malfunctioning industrial machine
  investigation and inspection for domain generalization task",
  arXiv:2205.13879, 2022.
- N. Harada et al., „First-shot anomaly detection for machine condition
  monitoring: A domain generalization baseline", *EUSIPCO*, 2023, pp. 191–195.

Godine i mjesta su provjereni pretragom 14.08.2026. Prije predaje ih ipak
uporediti sa originalima — DOI/stranice nisu potvrđeni za sve.

## 8. Prvi korak u novom četu

1. ~~Potvrditi jezik i ime mentora.~~ Riješeno — vidi sekciju 3.
2. Napraviti `radovi/telfor2026/telfor2026_asd_esp32s3.docx` iz zvaničnog
   šablona (`python-docx`, otvoriti šablon → obrisati tijelo → puniti stilovima
   šablona, da se formatiranje ne rekonstruiše ručno).
3. Provjeriti izgled renderovanjem u PDF i gledanjem strana:
   `soffice --headless --convert-to pdf` pa `pdftoppm -jpeg -r 100`.
4. Držati se 4 strane — to je tvrdo ograničenje, ne preporuka.
