# Master rad — stanje i šta još fali

**Ažurirano:** 27.08.2026. · **Prva kompletna verzija je generisana i
renderovana:** 48 strana, 11 367 riječi, 6 slika, 20 tabela.

| fajl | šta radi |
|---|---|
| [`rad_tekst.py`](rad_tekst.py) | **tekst rada** — ovdje se piše, na latinici |
| [`build_rad.py`](build_rad.py) | sklapa `.docx`, preslovljava u ćirilicu, primjenjuje FTN stilove |
| [`make_slike.py`](make_slike.py) | pravi sve slike iz stvarnih podataka |
| [`render_check.py`](render_check.py) | osvježi sadržaj u Wordu, prijavi broj strana, snimi PDF |
| [`preview_strane.py`](preview_strane.py) | snimi izabrane strane kao PNG radi provjere preloma |

```bash
cd radovi/master-rad && ../../.venv/Scripts/python.exe make_slike.py && ../../.venv/Scripts/python.exe build_rad.py && ../../.venv/Scripts/python.exe render_check.py
```

> **Redoslijed je bitan:** `make_slike.py` prije `build_rad.py`. I ne uređivati
> `.docx` ručno dok se izmjene rade kroz skriptu — svaki `build_rad.py`
> prepisuje fajl. Kad krene finalno sređivanje u Wordu, prestati pokretati
> skripte.

---

## 1. Odakle je izveden format

Format nije pretpostavljen nego pročitan iz dva izvora, oba u
[`sablon/`](sablon/):

| Fajl | Šta daje |
|---|---|
| `uputstvo-za-pisanje-radova-v8.pdf` | uputstvo nastavnika usmjerenja (Mezei, 24.08.2026): obavezna struktura, **ćirilica**, kurziv za strane termine, tabele numerisane iznad a slike ispod, jednačine desno, 30–50 strana, najviše 2 decimale |
| `ftn-diplomski-sablon.doc` / `.docx` | zvanični FTN šablon: Heading 1 Arial 16 bold desno, Heading 2 Arial 14 bold lijevo, Heading 3 Arial 12 bold lijevo, Body Text Times 11 obostrano sa uvlakom 1 cm, kod Courier New 10 |
| `ftn-msc-rad.dot` / `.docx` | MSc šablon sa tačnim poljima ključne dokumentacijske informacije i njihovog engleskog parnjaka |

## 2. Pismo — jedna stvar za provjeru sa mentorom

Uputstvo v8 kaže izričito: *„Završni radovi se obavezno pišu ćirilicom.“*
Zvanični MSc šablon u polju `Jezik publikacije, JP` ima upisano
*„Srpski / latinica“*. Ta dva se razilaze.

Zbog toga se iz istog izvora generišu **oba pisma**:

- `master_rad_asd_esp32s3_cir.docx` — ćirilica, prati uputstvo (podrazumijevano);
- `master_rad_asd_esp32s3_lat.docx` — latinica, ako mentor kaže drugačije.

Prebacivanje ne traži nikakvu izmjenu teksta. Skraćenice, oznake jedinica,
identifikatori iz koda, engleski blokovi i literatura ostaju latinični u obje
verzije, kako uputstvo i traži.

## 3. Slike — sve iz stvarnih podataka

| Slika | Izvor | Stanje |
|---|---|---|
| 3.1 podjela posla računar/uređaj | crtano | gotovo |
| 4.1 spektar u dvije rezolucije | `data/dcase2026_dev/fan/train/*.wav` | gotovo |
| 4.2 napredak AUC po fazama | `docs/put-do-modela.md` | gotovo |
| 5.1 šema povezivanja | crtano | gotovo |
| 7.1 trasa mjerenja sa papirićem | `run_20260827T213148_*/detections.csv` | gotovo |
| 7.2 trasa mjerenja sa tonom | `run_20260827T220338_*/detections.csv` | gotovo |

Nijedna brojka na slikama nije upisana rukom — pragovi se čitaju iz `PROFILE`
zapisa u serijskom logu, a trase iz `detections.csv`.

## 4. Preostale `[TODO]` oznake

| # | Gdje | Šta treba |
|---|---|---|
| 1 | naslovna, KDI | **broj indeksa** — u radu stoji `E1 80/2024`, izveden iz putanje fakultetskog gita; potvrditi tačan |
| 2 | KDI i KWD | fizički opis rada (poglavlja / strana / citata / tabela / slika / priloga) — popunjava se na kraju, kad je prelom konačan |
| 3 | KDI i KWD | članovi komisije |
| 4 | literatura | referenca na sistematsko poređenje ocjenjivača (`arXiv:2606.19269`) — provjeriti autore i stranice ili je izbaciti |
| 5 | Prilog A | adresa javnog spremišta |

## 5. Šta rad namjerno **ne** tvrdi

Isto kao u ostatku repoa, i ne mijenjati bez novog mjerenja:

- Izbor obilježja je **pobjeda za ventilator**, ne opšte poboljšanje; po
  harmonijskoj sredini preko sedam mašina lošiji je od mel osnove.
- Papirić i pušteni ton su **kontrolisane promjene, ne potvrđeni kvarovi**.
- Odsustvo alarma tokom nekoliko desetina minuta **nije** procjena dugoročne
  stope lažnih uzbuna.
- Vrijeme oporavka poslije jakog izvora promjene **nije izmjereno**.
- Lemljenje, `I2S` liveness, power-loss i samostalan demo bez računara
  **nisu** fizički potvrđeni.
- Sekcija o mjerenju potrošnje sa `INA226` **namjerno je izostavljena** dok se
  cijeli lanac ne izmjeri; dodaje se poslije, u poglavlje 5.

## 6. Prije predaje

- [ ] Riješene `[TODO]` oznake iz sekcije 4
- [ ] `render_check.py` — sadržaj osvježen, broj strana u opsegu 30–50
- [ ] Provjera pravopisa u Wordu nad finalnom verzijom
- [ ] Rad pročitao neko ko nije pisao (uputstvo to izričito traži)
- [ ] Rad za Zbornik FTN na 4 strane — **ili** objavljen konferencijski rad sa
      istim rezultatima; [rad za TELFOR](../telfor2026/) pokriva tu obavezu
- [ ] Prva verzija mentoru na vrijeme za korekture
- [ ] PDF članovima komisije najmanje 3 dana prije odbrane
