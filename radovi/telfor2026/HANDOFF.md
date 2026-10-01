# TELFOR 2026 — format, odluke i izvori brojki

Stanje: 01.10.2026. Šta još fali: [PREOSTALO-RAD.md](PREOSTALO-RAD.md).

## 1. Pravila TELFOR-a

| Stavka | Vrijednost |
|---|---|
| Dužina | najviše 4 A4 strane (redovni rad) |
| Format | IEEE dvokolonski konferencijski šablon, A4 (`sablon/`) |
| Jezik | engleski (radi IEEE Xplore) |
| Predaja | PDF, poslije IEEE PDF eXpress provjere, na registration.telfor.rs |
| Konferencija | 34. TELFOR, Beograd, 24–26. novembar 2026. |
| Rok | 4. oktobar 2026. |
| Copyright | broj iz registracionog sistema, dno prve strane |

Margine izmjerene iz šablona: gore 9,53 mm, dolje 25,4 mm, lijevo/desno
15,75 mm. Autori: Mihajlo Živković, Ivan Mezei; zajednička afilijacija FTN
Novi Sad. Kategorija: redovan rad (studentska sekcija ne ide u Xplore).

## 2. Struktura

```
I    Introduction
II   Detector: hardware, spectral feature, model, offline comparison (Tab. I)
III  Commissioning on the device: zašto 10 prozora nije dosta, CAL/DERIVE/VERIFY
IV   Runtime decision chain: quality, presence, reliability (HOLD), temporal
V    Trials on a physical fan (Tab. II, Sl. 2, Sl. 3): papirić, ton,
     šta pobuda mijenja, zavisnost od nivoa
VI   Discussion   VII Conclusion   References [1]-[9]
```

Ugao rada: kompletan detektor na mikrokontroleru koji sam uči centar i
pragove iz normalnog zvuka, i pošteno izmjeren ishod na ventilatoru,
uz potvrđenu dosljednost implementacije i ograničenja detekcije pri
promjenljivoj pobudi.

## 3. Izvori brojki

| Brojka u radu | Izvor |
|---|---|
| AUC PSD 0,867 (k=20), log-mel 0,627, poređenje 7 mašina | `results/canonical_evaluation/.../aggregate_summary.csv` |
| AUC PSD 0,863 (k=10), neprazne trake 0,878, pad na 0,505 pri ×2, medijana ×28 | `results/psd_nonempty/2026-09-07/summary.json` |
| AE baseline 0,470 ± 0,010, AE 45k int8 0,453 ± 0,005 | `results/results_stats.csv` (fan, target, 5 seedova) |
| AE na uređaju 1,54 s (665 + 870 ms) | `results/e4_latency.md` |
| Sedam dodatnih kandidata, najviše +0,0012 | `results/advanced/advanced_results.json` |
| Pravilo histereze: 0 lažnih, 5,40/h naspram 11,16/h | `pc/config/asd_temporal_policy_v1.json` |
| Pragovi 5687 / 347 / 1088, ×16, ×4,7, 92 % | `results/false_alarm/*/detections.csv` |
| Robustni kandidat 791, VERIFY 263–7766; 8/22 iznad praga, posljednjih 6 uzastopno | run `…T205240…v3recovery5c`, svih 22 WINDOW zapisa, uključujući završni REJECTED u `serial.log` |
| Pragovi, CV, HOLD, medijane, 43/65 i 99/115 | `radovi/rezultati.py` nad `results/physical_fan/run_20260827T*` |
| Ocjene papirić bloka 1 od 16 008 do 56 167 | `radovi/rezultati.py` (`low`/`high`), isto u `docs/probe/rezultat-finalna-validacija-2026-08-27.md` |
| Jedna epizoda po probi, 130 s do trajnog odstupanja | `firmware_events.csv` obje probe |
| Ponovljene HOLD i alarm odluke: 65/65 i 115/115, bez neslaganja | `verify_decisions.py`, `verification/decision_replay.json` |
| Ulazni prag = maksimum 44 DERIVE prozora | `serial.log`, `COMMISSION … phase=COMMISSION_DERIVE` |
| Nivo nasuprot obliku, 1 kHz traka, 36 prozora, 12 266–19 561 | `results/trial_features/2026-09-25/summary.json` |
| 716–728 ms, 354 784 B, PC↔C 9,5e−7, PC↔uređaj 1,7e−6 | `docs/probe/rezultat-finalna-validacija-2026-08-27.md`, `docs/uredjaj/hardver-verifikacija.md` |

Minute u tekstu (20,5, 23,3, 29,4) računate su od početka CAL faze, isto
kao osa Sl. 2.

Revizija od 30.09. jasno objašnjava histerezu: ton je detektovan, a alarm
je očekivano ostao aktivan jer ocjena nije dostigla niži izlazni prag.
Gašenje je potvrđeno u probi papirićem. Kriterijumi protokola papirića
nisu ispunjeni, iako su odluke firmware-a dosljedne pravilima u svih 180
prozora obje probe. Replay je naknadna provjera sačuvanih podataka, a ne
novo fizičko mjerenje. Razdvojene su provjera originalnih ocjena i analiza
sa izmijenjenim nivoom. Broj vremenskih konfiguracija je 11; poređenje
autoenkodera ograničeno je na ispitane osnove i razvojnu evaluaciju.

Dopuna od 30.09. uveče: V.A navodi da je papirić držan rukom i da ga je
bilo teško držati mirno cijeli blok, pa se zvuk mijenjao, vjerovatno i po
frekvenciji, i prozori nisu bili isti. „Perturbations“ je svuda zamijenjeno
sa „unsteady changes“, doprinosi 3) i 4) su preformulisani, a „hardware far
larger than a sensor node“ glasi „PCs or GPUs rather than a microcontroller“.

## 4. Reference

Revizija od 01.10: [detaljna provjera i odluke o formulacijama](PROVJERA-2026-10-01.md).
Razjašnjeni su VERIFY bez HOLD-a, GUIDED25 44/22 naspram podrazumijevanih
120/60, minimum od oko 800 s sa smirivanjem i jednostrana kapija prisustva.
Opis tona prati snimljena obilježja bez tvrdnje o tačnom broju promjena
glasnoće. Struktura rada i izmjereni pozitivni rezultati ostali su isti.

Provjerene prema primarnim izvorima 14.08. ([2]–[7]) i 25.09.2026.
([1] DCASE2020 Task 2, pp. 81–85; [8] Randall, Wiley 2011; [9] MLPerf Tiny,
NeurIPS Datasets and Benchmarks 2021).
