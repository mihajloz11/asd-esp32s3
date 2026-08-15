# Preregistracija — prvi fizički test ventilatora (`fan01`)

**Pisano:** 15.08.2026, uveče · **Run planiran:** 16.08.2026
**Protokol:** [protokol-fizicki-ventilator.md](protokol-fizicki-ventilator.md),
`physical-fan-v1.6.0` · **Firmware:** `ASD_PSD_LIVE`, flešovan 15.08.2026

> Ovaj dokument je napisan **prije** nego što je ijedan mjerodavni prozor
> snimljen. Postoji zato da se pravila prihvatanja ne mogu izabrati poslije
> rezultata. Ono što se ovdje ne može popuniti unaprijed označeno je sa
> `POPUNITI NA LICU MJESTA` i upisuje se prije prvog `condition`, ne poslije.

---

## 1. Šta se već zna

Sve što slijedi je izmjereno 15.08.2026, ali **nijedno nije valjan rezultat** —
išlo je kroz panel, van alata za eksperiment, bez zapisa i bez oznaka uslova.
Vrijednosti stoje ovdje samo kao očekivanje reda veličine, ne kao referenca.

| | |
|---|---|
| Prag iz te kalibracije | 529 |
| Normalni prozori | 418 i **592** — jedan iznad praga bez promjene |
| Papirić uz rešetku | 24 873 → 52 046, alarm na trećem uzastopnom prozoru |
| Papirić izvađen | 2 668 — i dalje 7× iznad izlaznog praga (370) |
| Oporavak (`ANOMALY_CLEARED`) | **nikad viđen** — ventilator je ugašen prerano |
| Račun po klipu | 705 ms na 10 s zvuka |

Otuda i dva prioriteta sutrašnjeg runa: **izmjeriti oporavak** i **vidjeti
koliko je margina između normale i praga stvarno tijesna**.

---

## 2. Postavka (zaključati prije prvog `condition`)

| Stavka | Vrijednost |
|---|---|
| `fan_id` | `fan01` |
| `session_id` | `POPUNITI NA LICU MJESTA` (npr. `cold-start-03`) |
| Tip ventilatora | prenosivi USB ventilator |
| Napajanje / brzina | `POPUNITI NA LICU MJESTA` (USB 5 V; upisati stepen ako ih ima) |
| Rastojanje mikrofona | `POPUNITI NA LICU MJESTA` cm |
| Ugao | `POPUNITI NA LICU MJESTA` ° |
| Prostorija | soba, **prozor zatvoren** |
| Pozadinska buka | ulica prigušena zatvorenim prozorom; upisati šta se još čuje |
| Fiksiranje | mikrofon i žice zalijepljeni, ne pomjeraju se do kraja sesije |
| Hladni / topli start | `POPUNITI NA LICU MJESTA` |
| Operater | odmaknut od laptopa ([P19](problemi-i-rjesenja.md#p19)) |

Ventilator, mikrofon, rastojanje, ugao i napajanje se **ne pomjeraju** između
kalibracije i ocjene iste sesije.

---

## 3. Pravila prihvatanja — fiksirana, ne biraju se poslije

**K1 — kalibracija.** Poslije `CAL_SUMMARY` gleda se `loo_cv`. Ako je
**> 0,6**, kalibracija se odbacuje i ponavlja dugim pritiskom. Odluka se donosi
prije nego što se pogleda ijedan `DET` prozor.

> Broj 0,6 je procjena između dva prolaza iz [P17](problemi-i-rjesenja.md#p17)
> (loš prolaz `CV = 1,77`, dobar `CV = 0,36`). **Nije izveden mjerenjem** i tako
> se piše u radu. Upisan unaprijed je pošten; izabran poslije rezultata ne bi
> bio.

**K2 — skraćena osnova.** Normalna osnova traje **10 minuta**, ne 30–60 kako
protokol traži. Posljedica se piše eksplicitno: broj lažnih alarma na sat
izveden iz ~60 prozora ima širok interval i **ne poredi se** sa brojkama iz
punih sesija.

**K3 — ventilator se ne gasi dok run traje.** `controlled_stop` je posljednji
događaj sesije, jer gašenje ruši nivo ispod praga prisustva i završava run kroz
`NO_MACHINE` → `FLOW_STOPPED`.

**K4 — trajanje događaja.** Svaki uslov se drži najmanje **5 punih prozora**
(60 s). Alarm traži tri uzastopna, pa kraće od toga ne dokazuje ništa.

**K5 — oporavak.** Poslije svakog `airflow_change` ide `recovery_normal` u
trajanju od **najmanje 90 s**, i čeka se `ANOMALY_CLEARED`. Ako ne padne, to je
rezultat koji se zapisuje — ne razlog da se prag dira.

**K6 — bez naknadnog podešavanja.** Ni prag, ni model, ni politika se ne mijenjaju
na osnovu ishoda ovog runa. Ako ishod bude loš, to je nalaz, ne kvar.

---

## 4. Redoslijed sesije

| # | Faza | Trajanje | Komanda |
|---|---|---|---|
| 1 | kalibracija | ~115 s | klik **Kratak pritisak** u panelu |
| 2 | provjera K1 | — | pogledati `loo_cv` u `CAL_SUMMARY` |
| 3 | normalna osnova | 10 min | `condition normal_baseline` |
| 4 | papirić uz rešetku | 60 s | `condition airflow_change` |
| 5 | oporavak | 90 s | `condition recovery_normal` |
| 6 | ponoviti 4–5 još dva puta | ~5 min | |
| 7 | razgovor na 2 m | 60 s | `condition ambient_noise` |
| 8 | oporavak | 90 s | `condition recovery_normal` |
| 9 | gašenje ventilatora | — | `condition controlled_stop` |
| 10 | kraj | — | `stop` |

Ukupno oko **22 minuta** od pritiska tastera do `stop`.

**Bezbjednost:** papirić se drži sa **spoljne strane zaštitne rešetke**, bez
kontakta sa lopaticama i bez guranja kroz rešetku. Ventilator se ne oštećuje.

---

## 5. Kako se pokreće

Panel ide u `--command-file` režim jer port smije držati samo alat:

```bash
.venv\Scripts\python.exe pc\tools\physical_fan_experiment.py run --port COM3 --fan-id fan01 --session-id cold-start-03 --distance-cm NN --angle-deg NN --room soba --fan-speed-or-voltage usb-5v --command-file results\physical_fan\cmd_fan01.txt
```

```bash
.venv\Scripts\python.exe pc\tools\asd_panel.py --command-file results\physical_fan\cmd_fan01.txt --follow results\physical_fan\run_XXXX\serial.log
```

Klik u panelu i otkucana komanda u alatu rade isto.

---

## 6. Šta ovaj run može, a šta ne može da tvrdi

**Može:** da prototip u ovoj postavci detektuje bezbjedno izazvanu promjenu
protoka, sa izmjerenim kašnjenjem, oporavkom i brojem lažnih alarma na skraćenoj
osnovi.

**Ne može:** da je to „stvarni kvar" — promjena je izazvana i vraćena, bez
nezavisne stručne potvrde. Ne može ni generalizaciju na druge ventilatore:
jedan primjerak, jedna soba, jedna sesija.
