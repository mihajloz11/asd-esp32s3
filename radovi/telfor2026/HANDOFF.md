# TELFOR 2026 — format, odluke i izvori brojki

Stanje: 25.09.2026. Šta još fali: [PREOSTALO-RAD.md](PREOSTALO-RAD.md).

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
VI   Discussion   VII Conclusion   Acknowledgment   References [1]-[9]
```

Ugao rada: kompletan detektor na mikrokontroleru koji sam uči centar i
pragove iz normalnog zvuka, i pošteno izmjeren ishod na ventilatoru,
uključujući proba koja nije prošla i uzrok koji se vidi u podacima.

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
| Robustni kandidat 791, VERIFY 2083–7766 | run `…T205240…v3recovery5c`, `serial.log` |
| Pragovi, CV, HOLD, medijane, 43/65 i 99/115 | `radovi/rezultati.py` nad `results/physical_fan/run_20260827T*` |
| Jedna epizoda po probi, 130 s do trajnog odstupanja | `firmware_events.csv` obje probe |
| Ulazni prag = maksimum 44 DERIVE prozora | `serial.log`, `COMMISSION … phase=COMMISSION_DERIVE` |
| Nivo nasuprot obliku, 1 kHz traka, 36 prozora, 12 266–19 561 | `results/trial_features/2026-09-25/summary.json` |
| 716–728 ms, 354 784 B, PC↔C 9,5e−7, PC↔uređaj 1,7e−6 | `docs/probe/rezultat-finalna-validacija-2026-08-27.md`, `docs/uredjaj/hardver-verifikacija.md` |

Minute u tekstu (20,5, 23,3, 29,4) računate su od početka CAL faze, isto
kao osa Sl. 2.

## 4. Reference

Provjerene prema primarnim izvorima 14.08. ([2]–[7]) i 25.09.2026.
([1] DCASE2020 Task 2, pp. 81–85; [8] Randall, Wiley 2011; [9] MLPerf Tiny,
NeurIPS Datasets and Benchmarks 2021).
