# Odluka: finalni model i rezervna alternativa

**Datum odluke:** 09.08.2026 · **Usklađeno:** 14.08.2026. · **Status:**
odlučeno; svi dosadašnji kriteriji prihvatanja na pločici **prošli** (vidi
tabelu niže). Ostaje test sa fizičkim ventilatorom i kompletnim hardverom.

Dvije sesije su 09.08.2026 paralelno istraživale kako preći AUC 0,80
([cilj-modela.md](cilj-modela.md)). Nalazi su se ukrstili i POTVRĐUJU jedni
druge; ovdje je poređenje, odluka i uslovi pod kojima se odluka mijenja.

## Šta je koja linija rada dala

| | Linija A (PSD, `bench_periodicity.py`) | Linija B (scoring, `bench_research1-6.py`) |
|---|---|---|
| Glavni nalaz | **psd_shape**: FFT 8192, 96 log traka 10–4000 Hz, gain-normalizovan → **0,864 ± 0,025** (k=20, 50 rep.) | metodologija + granice mel prostora: LW kovarijansa (+3), medijana centra (+3, 7 mašina), upareni seedovi kao pravilo |
| Negativni rezultati | envelope spektar (0,51) | kNN/min-udaljenost, pod-segmenti, delta, modulacija mel energija, sprega traka, MCD, ansambli — sve izmjereno, ništa ne prelazi 0,72 na mel sažetku |
| Ukrštena provjera | — | psd_shape nezavisno reprodukovan (0,856 ± 0,026, 20 rep.); medijana na psd NE dodaje; ansambl psd+mel POGORŠAVA (0,78) |
| Inženjering | C modul + header + meta json, PC↔C 9,54e-07, testovi 11/11, prag analiza | cross-machine framework (`bench_research_final.py`), uparena statistika |

Ključno: Linija B je pokušala „poboljšati" psd_shape (medijana, ansambl) i
izmjerila da NE treba — što znači da je jednostavan recept Linije A ujedno i
optimalan od svega probanog.

## Opseg važenja odluke (dopuna 09.08.2026)

Poslije mjerenja na svih 7 mašina: **psd_shape je pobjeda za ventilator, ne
uopšte.** Dobija +0,277 AUC na `fan`, ali gubi na 5 od 6 ostalih mašina, i po
harmonijskoj sredini (0,537) je lošiji od mel osnove (0,573). Fizički razlog:
uske harmonijske linije postoje kod rotacionih mašina, ne kod ventila i klizača.
Tabela i objašnjenje: [put-do-modela.md](put-do-modela.md), faza 4b.

Uređaj iz ovog rada je namijenjen **ventilatorima**, pa odluka ispod ostaje na
snazi. Ali tvrdnja se piše precizno: *„za ventilator"*, ne *„za ASD uopšte"*.
Ako se sistem ikad širi na drugi tip mašine, front-end se bira po tipu, i to je
izvodljivo **bez target oznaka** (izbor na source domenu, harmonijska sredina
0,577 — bolje od bilo kojeg fiksnog izbora).

## ODLUKA — šta ide na pločicu

**Finalna implementacija: psd_shape + Ledoit-Wolf precizija + lokalni centar
(sredina), `k=10`.** `k=20` ostaje jači referentni PC benchmark, a nije
konfiguracija trenutnog firmwarea.

- Front-end: Welch FFT 8192 (hop 4096), 96 log traka 10–4000 Hz, log10,
  minus skalarna sredina.
- Model u flešu: precizija 96×96 (36 864 B) + normalizacija (768 B) —
  `psd_model_data.h`, porijeklo u `models/fan_psd_shape_meta.json`.
- Kalibracija na licu mjesta: centar (384 B) iz `k=10` validnih klipova
  (100 s mjerenja, uz oko 15 s `WAIT`, ukupno oko 115 s). Razvojna evaluacija
  za ovu konfiguraciju daje AUC 0,856 ± 0,024 na 20 podjela.
- `k=20` (200 s, AUC 0,864 ± 0,025 u ranijem poređenju; oko 0,867 u
  kanonskoj evaluaciji sa 100 podjela) ostaje referentni PC rezultat i
  analiza osjetljivosti, ne skrivena druga firmware konfiguracija.
- Score: Mahalanobis, **dvostran po konstrukciji** (udaljenost hvata i porast
  i pad) — uklapa se u postojeću dvostranu logiku demoa.
- Alarm: tek poslije tačno 3 uzastopna anomalna prozora (prag sam po sebi daje
  ~64 % odziva uz 12,7 % lažnih — nedovoljno bez vremenske potvrde).
- Bez tihe rekalibracije: centar se ne pomjera automatski (P10 pouka —
  uređaj ne smije naučiti kvar kao normalu).

**Rezerva (ostaje dokumentovana i NE briše se): mel256 + Ledoit-Wolf +
medijana centra, AUC 0,716 ± 0,037** ([istrazivanje-preko-0674.md](istrazivanje-preko-0674.md)).
Koristi POSTOJEĆI, već verifikovani log-mel front-end (7,99e-05 PC↔uređaj) i
zahtijeva samo zamjenu scoring koda. Aktivira se SAMO ako PSD padne na
hardverskoj provjeri ispod:

| Kriterij prihvatanja PSD-a na S3 | Granica | Izmjereno 09.08. | |
|---|---|---|---|
| vrijeme računanja po 10 s klipu | < 10 s (očekivano < 2 s) | **704 ms**, rezerva 14,2× | ✔ |
| RAM (PSRAM + interni) | staje, `dropped=0` | DIRAM 86 %, `dropped=0` | ✔ |
| PC↔uređaj razlika feature-a na živom mikrofonu | red 1e-4 | **1,70e-06** | ✔ |
| demo normalan → neispravan → zaustavljen | prelazi tačno | prelazi u oba smjera | ✔ |

**Svi kriteriji prošli — PSD ostaje primarni izbor, rezerva se ne aktivira.**
Detalji mjerenja: [hardver-verifikacija.md](hardver-verifikacija.md).

## Zašto ova odluka prati krajnji cilj

Cilj ([cilj-modela.md](cilj-modela.md)): uči na gomili ispravnih → spusti na
pločicu → kalibriši na NEPOZNATOM ventilatoru → pločica SAMA fleguje.
PSD recept je tačno to, i jednostavniji je od svega dosadašnjeg: nema mreže,
nema TFLM arene, nema treninga na pločici — flash tabela + jedno množenje.
U trenutku odluke FFT 8192 bio je nova implementacijska nepoznanica. Taj
istorijski rizik je naknadno zatvoren PC↔C provjerom, uspješnim buildom i
on-device speaker/microphone mjerenjem vremena, RAM-a i `dropped=0`. Time nije
zatvoren rizik stvarnog ventilatora ni potpuno sastavljenog hardvera; oni
ostaju sljedeća fizička provjera.

## Trenutni status i sljedeći koraci

PSD live mod, PC↔C provjera, mjerenje vremena/RAM-a, lokalni centar i prag,
temporalno pravilo `n=3` i operatorov interfejs su implementirani. Finalni
softverski izbor je `k=10`; `k=20` se koristi samo kao referentni PC benchmark.

Otvoreni su fizički koraci: zalemiti kompletan sklop, pokrenuti unaprijed
zaključani protokol na stvarnom ventilatoru, izmjeriti duži normalni rad i
bezbjedno izazvane promjene te završiti E5 mjerenje potrošnje. Ti rezultati se
ne smiju unaprijed izvoditi iz speaker testa.
