# Istraživačka runda: probijanje 0,674 na novom ventilatoru

> Sesija 09.08.2026. Šest rundi eksperimenata (`pc/tools/bench_research*.py`),
> svi sa identičnim protokolom i seedovima (3000+rep, k=20, 20 ponavljanja,
> kalibracioni klip se nikad ne ocjenjuje, učenje isključivo na source korpusu).
> Rezultati u `results/research*.json`. Paralelna sesija je istovremeno radila
> `bench_periodicity.py` — nalazi su spojeni u rundi 6.

## Prvo otkriće: 0,674 i 0,643 nisu isti eksperiment

Dokumentovani „pobjednik 0,674" je iz `bench_blend.py` (seedovi 4000+,
regularizacija 1e-4, korpus 800). Na seedovima 3000+ (kao `bench_adapt.py`)
ista metoda daje **0,643 ± 0,024**. Razlika od 3 poena je šum izbora
kalibracionih klipova, ne stvarna razlika metoda.

**Pravilo od sada:** poređenja metoda važe samo na uparenim seedovima, uz
uparenu statistiku (dobitak po seedu, broj pobjeda, t-test).

## Šta je probano, po rundama (sve target domen, k=20, upareni seedovi)

| Runda | Pristup | AUC | Zaključak |
|---|---|---|---|
| — | referenca: sažetak 1280 + shrink 0,1 + sredina | 0,643 ± 0,024 | polazna tačka |
| 1 | mel256 (128 traka, bez 5× redundanse) + Ledoit-Wolf | 0,673 ± 0,025 | **+3 poena, 19/20 pobjeda, p<1e-4** — problem je bio USLOVLJENOST kovarijanse |
| 1 | PPCA nisko-rang (q=32) | 0,672 ± 0,035 | isto poboljšanje, jeftinije na ploči |
| 1 | kNN na kalibracione egzemplare | 0,565–0,585 | min-udaljenost šteti (kao ranije adapt_mode) |
| 1 | pod-segmenti 2 s + percentil | 0,504–0,544 | razvodnjavanje ne pomaže |
| 1 | delta/modulacija sažetak | 0,561 | ne |
| 1 | dual (blizina source korpusa) | 0,539–0,583 | ne |
| 2 | GWRP pooling r=0,99 + LW (TWFR ideja) | 0,686 ± 0,024 | +1 nad mel256+LW |
| 2 | sprega traka unutar klipa (coup) | 0,460 | ispod 0,5 — ne |
| 2 | temporalna autokorelacija traka | 0,434 | ne |
| 2 | modulacioni spektar mel energija | 0,550 | ne |
| 3 | **medijana kalibracionog centra** umjesto sredine | **0,716 ± 0,037** | +3 nad sredinom; validirano i na source (ne šteti) |
| 4 | medijana na 7 mašina vs referenca | dobitak +0,004 do +0,075 | generalizuje: 5/7 mašina p<0,01, nigdje značajno gore |
| 5 | medijana UDALJENOSTI do svakog kal. klipa; MCD kovarijansa | 0,607–0,701 | robusno ocjenjivanje ne dodaje ništa |
| 6 | **psd_shape** (paralelna sesija) + moje kombinacije | **0,856 ± 0,026** | vidi dolje |

## Proboj: psd_shape (iz `bench_periodicity.py`, paralelna sesija)

Visokorezolucioni dugoročni spektar: Welch nperseg=8192 (rezolucija 1,95 Hz),
96 logaritamskih traka 10–4000 Hz, minus skalarna sredina (gain-invarijantno).
Ledoit-Wolf precizija na source korpusu, centar sa kalibracije. Izbor varijante
napravljen **na source domenu** (bez gledanja target anomalija), pa zamrznut:

| k | psd_shape sredina | psd_shape medijana | ansambl psd+mel |
|---|---|---|---|
| 10 | 0,845 ± 0,041 | 0,837 ± 0,054 | 0,761 |
| 20 | **0,856 ± 0,026** | 0,855 ± 0,034 | 0,784 |
| 40 | 0,868 ± 0,049 | 0,872 ± 0,046 | 0,794 |

- **Cilj AUC ≥ 0,80 je dostignut na benchmarku**, sa poštenim protokolom.
- Zašto radi: kvar rotacione mašine pomjera USKE harmonike osnovne frekvencije
  vrtnje; log-mel (FFT 1024, ~15,6 Hz po binu, mel razmazivanje) ih ne razdvaja,
  a 1,95 Hz rezolucija da. Envelope spektar (env) je pao (0,51) — signal je u
  finim spektralnim linijama, ne u amplitudskoj modulaciji.
- Medijana centra na psd_shape ne dodaje ništa (prostor je već čist);
  ansambl sa mel-om VUČE NADOLE — mel je slabiji signal, ne miješati.

## Pouke za tezu

1. **Uslovljenost je bila polovina problema.** 1280-dim kovarijansa iz 990
   klipova je matematički neodrživa; Ledoit-Wolf skupljanje ili 256-dim prostor
   odmah daju +3 poena. (Isti razlog zašto je „bogatiji sažetak" ranije PAO —
   nije bila loša ideja nego loša procjena kovarijanse.)
2. **Robusnost kalibracije vrijedi.** Medijana centra: mala izmjena, mjerljiv
   dobitak, generalizuje preko mašina — i trivijalna na ploči.
3. **Feature nosi više od backenda.** Deset varijanti scoring-a na mel sažetku
   staje na ~0,71; promjena front-enda (visokorezolucioni PSD) skače na 0,86.
   Poklapa se sa nalazima iz literature 2026 (arXiv 2606.19269).
4. **Ansambl nije besplatan.** Slabiji feature u rang-ansamblu POGORŠAVA jači.

## Šta ovo znači za ploču (ESP32-S3)

Novi front-end je izvodljiv i JEDNOSTAVNIJI od TFLM autoenkodera:

- Welch preko 10 s prozora: FFT 8192 (esp-dsp, PSRAM), usrednjavanje segmenata,
  96 log-traka, log10, minus sredina → 96 brojeva.
- Score: z-skala (iz firmvera), (x−centar)ᵀ P (x−centar), P = 96×96 matrica u
  flešu (~37 KB float32). Jedno matrično množenje po klipu — zanemarljivo
  naspram 1055 ms inferencije autoenkodera.
- Kalibracija na licu mjesta: samo centar (96 brojeva) + prag, kao do sada.
- Pažnja: PC↔uređaj verifikacija front-enda mora se ponoviti za novi PSD tok
  (postojeća verifikacija 7,99e-05 važi za log-mel, ne za ovo).

## Status naknadno

Analiza pragova, finalne razvojne tabele i C implementacija sa PC↔uređaj
provjerom su završene. Finalni firmware koristi `k=10` zbog praktične
kalibracije (~115 s sa `WAIT` fazom); `k=20` ostaje jači referentni PC
benchmark. Otvoren je test sa stvarnim ventilatorom, bezbjedno izazvanim
promjenama i kompletno spojenim hardverom.
