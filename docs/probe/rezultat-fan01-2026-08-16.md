# Rezultat — prvi valjan fizički test ventilatora

**Datum:** 16.08.2026. · **Run:** `results/physical_fan/run_20260816T193342_fan01_verify-sw-02`
**Status:** `completed_by_operator`, 131 DET prozor, **nijedna greška protokola**
**Kod:** `c72f1e1` · **Protokol:** `physical-fan-v1.6.0`, firmware `ASD_PSD_LIVE`

Ovo je prvi run u kojem INMP441 sluša stvarni ventilator, a cijela telemetrija
prolazi kroz zaključani host bez ijedne odbačene linije. Sve prethodno u repou
je zvučnik ili DCASE snimak.

> **Korekcija tumačenja, 20.08.2026.** Ovaj istorijski v1.6/q1.3 run i njegov
> `SUMMARY.md` ostaju netaknuti. Trenutni softver je v1.8/q1.5, ali još nije
> fizički ponovljen. Broj `324/h` ispod je broj alarmnih prozora po satu
> (`54/60 × 360`), ne broj alarmnih epizoda po satu. Papirić je bezbjedna,
> kontrolisana promjena protoka i nije potvrđen stvarni kvar.

> **Ime sesije je `verify-sw-02`, a ne `cold-start-07`.** Sesija je počela kao
> provjera softvera poslije popravki, kalibracija je ispala najbolja tog dana
> (`loo_cv` 0,307), pa je odlučeno da se mjerenje odradi na njoj umjesto da se
> ta kalibracija baci. Ime je jedina posljedica; svi ostali uslovi su iz
> [preregistracije](preregistracija-fan01.md).

---

## 1. Postavka

| | |
|---|---|
| Ventilator | prenosivi USB, **na punjaču** (ne na bateriji) |
| Mikrofon | INMP441, **20 cm** od osovine, **90°** na osu duvanja |
| Zašto bočno | u struji vazduha turbulencija na membrani nadjača zvuk mašine |
| Montaža | ventilator i mikrofon na stolici, zalijepljeni, nepomjerani |
| Laptop | 85 cm vodoravno, 30 cm više, neopterećen |
| Prostorija | soba, prozor zatvoren |
| Nivo kroz run | −46,4 … −40,3 dBFS, medijana **−41,0** |

Izazvana promjena: papirić uz **usisnu** stranu, sa spoljne strane rešetke, bez
kontakta sa lopaticama. Tri ponavljanja.

## 2. Kalibracija

| | |
|---|---|
| `loo_mean` | 208,16 |
| `loo_sd` | 63,82 |
| **`loo_cv`** | **0,3066** — prošlo pravilo K1 (prag 0,6) |
| `loo_range` | 190,77 |
| **prag** | **399,61** (`mean + 3σ`) |
| trajanje | 60 WAIT blokova + 10 × 10 s |

Za poređenje, `loo_cv` kroz dan: 1,03 (operater lupao) · 0,67 · 0,63 (baterija)
· 0,52 · **0,31**. Kvalitet kalibracije je lutrija i to je samo po sebi nalaz.

## 3. Mjerenje, blok po blok

| # | Blok | Prozora | Medijana | Min | Max |
|---|---|---:|---:|---:|---:|
| 1 | prije oznake | 7 | 245 | 159 | 554 |
| 2 | **normalna osnova** | 60 | **876** | 180 | 16 152 |
| 3 | **papirić 1** | 6 | **29 899** | 2 197 | 40 812 |
| 4 | oporavak 1 | 9 | 2 883 | 553 | 27 200 |
| 5 | **papirić 2** | 6 | **30 050** | 953 | 40 217 |
| 6 | oporavak 2 | 9 | 624 | 409 | 28 173 |
| 7 | **papirić 3** | 6 | **47 299** | 1 111 | 48 827 |
| 8 | oporavak 3 | 10 | 718 | 643 | 48 204 |
| 9 | **razgovor 2 m** | 6 | **11 946** | 10 751 | 18 202 |
| 10 | oporavak | 9 | 1 155 | 785 | 1 581 |
| 11 | gašenje ventilatora | 3 | 15 778 | 1 324 | 15 936 |

Odziv na papirić prema medijani osnove: **34× / 34× / 54×**. Ponovljivost je
bolja nego što se očekivalo — prva dva ponavljanja se razlikuju za 0,5 %.

Oporavci se vraćaju uz osnovu (624 · 718 · 1 155 prema 876), dakle sistem se ne
zaglavljuje. Blok 10 je najuvjerljiviji: raspon 785–1 581, bez ijednog izleta.

## 4. Razdvajanje (AUC po prozoru)

| Poređenje | svi prozori | bez prelaznih |
|---|---:|---:|
| **papirić vs normalno** | 0,954 | **0,999** |
| razgovor vs normalno | 0,986 | 0,987 |
| **papirić vs razgovor** | 0,824 | **0,979** |

„Prelazni" = prvi i posljednji prozor svakog bloka. Oznaka uslova se upisuje na
granici, pa taj prozor od 10 s sadrži oba stanja; protokol traži da se tako i
tretira. Svaki blok papirića ima tačno jedan nizak prozor (2 197 / 953 / 1 111)
i to su upravo te granice.

**Istraživački cilj rada je bio AUC ≥ 0,80. Na fizičkom ventilatoru dobijeno je
0,999 (0,954 sa prelaznima).** Do sada je taj cilj bio pređen samo na PC
benchmarku (0,864) i pao na zvučniku (0,716).

## 5. Prag — odvojen i neriješen problem

```
54 / 60 prozora normalnog rada iznad praga  =  90 %
324 alarmna prozora na sat (nije broj epizoda/h)
```

Rangiranje je skoro savršeno, a **politika praga je slomljena**. To su dvije
različite stvari i ovaj run ih prvi put razdvaja mjerenjem.

Tadašnji izvještaj nije imao sadašnji episode-aware obračun. Zato se 54 prozora
ne smiju nazvati 54 epizode niti skalirati u `324 epizode/h`; uzastopni alarmni
prozori pripadaju istoj alarmnoj epizodi dok se alarm ne ugasi.

Šta bi prag trebalo da bude, izvedeno iz iste osnove:

| Prag | Izvor | Lažni alarmi | Uhvaćeno papirića |
|---:|---|---:|---:|
| 400 | **stvarni**, `mean+3σ` iz 100 s | **90,0 %** | 100 % |
| 1 777 | p90 osnove | 10,0 % | 88,9 % |
| 2 016 | p95 osnove | 5,0 % | 88,9 % |
| 6 449 | p98 osnove | 3,3 % | 83,3 % |
| 10 886 | p99 osnove | 1,7 % | 83,3 % |
| 16 152 | maksimum osnove | 0,0 % | 77,8 % |

> ⚠️ Ovo je **in-sample**: prag izveden iz iste osnove na kojoj se i mjeri, pa
> su brojke gornja granica, ne poštena procjena. Služe da pokažu red veličine i
> oblik kompromisa, ne kao rezultat. Pošten izvod traži zaseban normal-only
> period, kako je i zapisano u [P17](../problemi-i-rjesenja.md#p17).

Uzrok je fizički: kalibracija gleda 100 sekundi, a ventilator izluta izvan tog
opsega kroz 10 minuta. Nivo pritom stoji na −41 dBFS — **ne mijenja se jačina
nego položaj harmonijskih linija**, što uho ne primjećuje a Mahalanobis preko 96
traka vidi kao veliku udaljenost.

## 6. Tri nalaza

1. **Obilježje radi na stvarnom ventilatoru.** PSD otisak + naučena kovarijansa
   daje AUC 0,999 na bezbjedno izazvanoj promjeni protoka, ponovljivo tri puta.
2. **Politika praga ne radi.** 90 % lažnih alarma. `mean + 3σ` iz 100 s je
   preusko za mašinu koja luta; treba mu duži normal-only period.
3. **Buka je stvarna prijetnja, ali razdvojiva.** Razgovor na 2 m diže score na
   13,6× osnove i pali alarm — ali se od papirića i dalje razdvaja sa AUC 0,979.
   Uzorak je premali da bi ta brojka bila dokaz.

## 7. Ograničenja — pišu se u rad bez uljepšavanja

- **Jedan ventilator, jedna sesija, jedna prostorija.** Ništa o generalizaciji.
- „Anomalija" je **bezbjedno izazvana promjena protoka**, ne stvarni kvar, i ne
  smije se tako zvati bez nezavisne stručne potvrde.
- Bez prelaznih prozora ostaje **12 prozora papirića i 4 razgovora**. AUC 0,979
  iz 48 parova ima ogroman interval povjerenja — indikacija, ne dokaz.
- Sweep praga je in-sample (vidi upozorenje gore).
- Osnova od 10 minuta daje 60 prozora; lažni alarmi na sat izvedeni iz toga
  imaju širok interval.
- **Oporavak nije mogao da ugasi alarm**, jer je i normalno stanje bilo iznad
  praga. Tri faze oporavka zato nisu izmjerile ono zbog čega su planirane;
  izmjerile su da se score vraća uz osnovu, što je slabija tvrdnja.

## 8. Šta slijedi, izvedeno iz ovih brojki

| # | Posao | Zašto baš to |
|---|---|---|
| 1 | **Novo pravilo praga iz dužeg normal-only perioda** | Arhitektura CENTER/DERIVE/VERIFY je implementirana; brojevi ostaju DEVELOPMENT do novog runa. |
| 2 | Kratki, unaprijed ograničen readout papirića i razgovora | Najviše 3 + 2 bloka poslije freeze-a; mali uzorak je funkcionalna provjera, ne dokaz stope. |
| 3 | Označavati prelazne prozore | Host sada čuva `transition_window` i izbacuje ga iz metrika; novi fizički run to tek treba potvrditi. |
| 4 | Host podrška za **više sesija po runu** | Softverski završeno i replay-testirano; nije fizički ponovljeno. |
| 5 | Drugi ventilator | I dalje jedini put do bilo kakve tvrdnje o generalizaciji. |

Stavka 1 ostaje najvažnija numerička provjera, ali nije jedina granica
upotrebljivog uređaja: HOLD policy, novi flash/runtime, power-loss i kompletan
hardver takođe ostaju otvoreni.

---

## Prilog — sirovi artefakti

Sve u `results/physical_fan/run_20260816T193342_fan01_verify-sw-02/`:
`serial.raw` (bajt-tačan prijem) · `detections.csv` (131 prozor sa oznakama
uslova) · `firmware_quality.csv` · `events.csv` (operaterske oznake) ·
`provenance.json` · `SUMMARY.md`.

Prethodni runovi istog dana (`cold-start-03` do `-06`, `verify-sw-01`) su
nevalidni i čuvaju se samo kao dokaz šest grešaka opisanih u
[preregistraciji](preregistracija-fan01.md), sekcija 4b.

Posebno, `cold-start-04` je u istorijskom `SUMMARY.md` pogrešno bio prikazan kao
fizički validan jer tadašnja funkcija nije provjeravala K1. Centralni read-only
recompute sada daje `calibration_rejected:loo_cv_above_max`,
`protocol_valid=True`, `metrics_eligible=False`. Originalni run, SUMMARY i
preregistrovana pravila K1–K6 nisu prepisani.
