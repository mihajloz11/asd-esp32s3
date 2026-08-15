# Šta još fali u radu za TELFOR 2026

**Stanje:** 14.08.2026. · Izvor rada je ažuriran; postojeći DOCX je prethodno
imao **4 strane**, ali ga treba ponovo generisati i renderovati nakon izmjena.
Sve slike osim fotografije napravljene su iz stvarnih podataka.
**Rok: 4. septembar 2026.**

| fajl | šta radi |
|---|---|
| [`telfor2026_asd_esp32s3.docx`](telfor2026_asd_esp32s3.docx) | rad |
| [`make_figures.py`](make_figures.py) | pravi Sl. 1, 2 i 4 u `slike/` |
| [`build_paper.py`](build_paper.py) | sklapa `.docx` iz IEEE šablona |
| [`render_check.py`](render_check.py) | PDF + slike strana, ispiše broj strana |
| [`check_todo.py`](check_todo.py) | broji preostale `[TODO]` |

```bash
cd radovi/telfor2026 && ../../.venv/Scripts/python.exe make_figures.py && ../../.venv/Scripts/python.exe build_paper.py && ../../.venv/Scripts/python.exe render_check.py
```

> **Redoslijed je bitan:** `make_figures.py` prije `build_paper.py`.
> I ne uređivati `.docx` ručno dok se ne završe izmjene kroz skriptu — svaki
> `build_paper.py` prepisuje fajl. Kad krene finalno sređivanje u Wordu,
> prestati pokretati skripte.

---

## 1. Slike — šta je napravljeno

| # | Slika | Izvor | Stanje |
|---|---|---|---|
| 1 | Signal path + hijerarhija odlučivanja | crtano | **gotovo** |
| 2 | Trasa score-a, čist prolaz na uređaju | `results/false_alarm/20260814_004542.../detections.csv` | **gotovo** |
| 3 | Fotografija postavke | — | **čeka lemljenje** |
| 4 | Nestabilnost praga, tri kalibracije | sva tri `detections.csv` | **gotovo** |

Nijedna brojka na slikama nije upisana rukom — sve se računa iz CSV-a pri
svakom pokretanju. Provjereno usput: u čistom prolazu **najduži niz iznad praga
je 2 prozora**, a pravilo traži 3. To je sad izračunato, ne prepisano.

**Tabela IV je izbačena** — Sl. 4 pokazuje isto, ali ubjedljivije.

### Ako fotografija ne bude gotova na vrijeme

Rad staje na 4 strane i **bez** Sl. 3. Brisanjem tog jednog `("figure", ...)`
reda u `build_paper.py` dobija se pola kolone slobodno. Nije katastrofa ako
fotografije nema — ali rad je jači sa njom, jer je jedini vizuelni dokaz da
uređaj fizički postoji.

## 2. Treba li profesionalna šema hardvera — **ne za ovaj rad**

Kratko: **ne.** Razlozi:

- Doprinos rada nisu veze na pločici nego politike odlučivanja. Šema povezivanja
  ne nosi nijednu tvrdnju rada.
- Pojela bi oko četvrtine strane, a limit od 4 strane je već tijesan.
- Sl. 1 već nosi ono što je čitaocu potrebno: koji senzor, kojim interfejsom,
  šta radi procesor, i kako se donosi odluka.

Šema **ide u master rad**, gdje nema ograničenja strana — već postoji kao
[`docs/sema-povezivanja.md`](../../docs/sema-povezivanja.md) i
[`sema-povezivanja.svg`](../../docs/sema-povezivanja.svg). Tamo ima smisla i
puna tabela pinova.

## 3. Preostale `[TODO]` oznake — 5 stavki, 10 pojava u izvoru

```bash
cd radovi/telfor2026 && ../../.venv/Scripts/python.exe check_todo.py
```

| # | Gdje | Šta treba | Blokira |
|---|---|---|---|
| 1 | podnožje 1. strane | IEEE copyright broj | registracija rada |
| 2 | II.A | potrošnja cijelog lanca (sad stoji samo 119 mW praznog hoda) | **E5**: 5 V izvor + re-arm `ASD_INA_TEST` |
| 3 | Tabela III (6 ćelija) | mjerenja sa fizičkim ventilatorom | **ventilator** |
| 4 | Tabela III, napomena | briše se kad se tabela popuni | isto |
| 5 | Sl. 3 | fotografija zalemljene ploče | **lemljenje** |

Autorski blok, mentorov kontakt, odluka da nema zahvalnice/finansiranja i
referenca [6] riješeni su u `build_paper.py`. Postojeći DOCX još sadrži stari
tekst dok se ponovo ne generiše.

## 4. Reference — završene prema primarnim izvorima

Rad sada ima šest relevantnih referenci bez `[TODO]`: first-shot baseline,
ToyADMOS2, MIMII DG, Welch, Ledoit-Wolf i zvanični opis DCASE 2026 Task 2
(`arXiv:2606.01578`). DOI i stranice koje postoje potvrđeni su na IEEE/EUSIPCO,
DCASE, Zenodo i izdavačkim stranicama. Neprovjerena TinyML referenca nije
ubačena samo da bi se povećao broj citata.

## 5. Redovan ili studentski rad — riješeno dokazom

Iz poziva za radove: u studentskoj sekciji **autori mogu biti samo studenti**
(mentor ide u fusnotu), i ti radovi izlaze **samo u CD zborniku, ne u IEEE
Xplore**. Pošto je engleski izabran baš zbog Xplorea, a Mezei je koautor —
**rad je redovan.** Ako se ipak ide na studentsku sekciju, Mezei izlazi iz
autorskog bloka.

Sekcija pri prijavi: **SP (Signal Processing)** prvi izbor, **AEL (Applied
Electronics)** drugi.

## 6. Šta bih još doradio ako ostane vremena

Poređano po odnosu korist/trud:

| # | Šta | Zašto | Trud |
|---|---|---|---|
| 1 | **Ponovo renderovati i zadržati 4 strane** | autorski blok, jednačine i preciznije formulacije mijenjaju prelom | 20 min |
| 2 | **Rečenica o tome zašto Mahalanobis, a ne autoenkoder** | dodati samo ako postoji prostor i ako se tvrdnja može vezati za izmjerene rezultate | 15 min |
| 3 | Provjera engleskog od nekoga ko nije pisao rad | tipične greške se ne vide sopstvenom oku | — |
| 4 | Sl. 2 i Sl. 4 u boji | CD zbornik je u boji; sad su sivo, radi štampe | 20 min |

Jednačine za kvadrirani Mahalanobis score i normal-only prag sada su sažeto
ugrađene u tekst izvora, bez dodatnih blokova koji bi nepotrebno trošili prostor.

Namjerno **nisam** dodao: spektar normalno/anomalno (razlika je premala da bi
slika išta pokazala, a niske trake prave artefakte), ROC krive (Tabela I nosi
isto), i šemu povezivanja (vidi sekciju 2).

## 7. Prije predaje

- [ ] Sva `[TODO]` riješena — `check_todo.py` mora ispisati `0`
- [ ] **Tačno 4 strane** poslije ubacivanja fotografije — `render_check.py`
- [ ] Copyright u podnožju prve strane (sad je Word footer prve strane; ako
      IEEE PDF eXpress traži lijevu kolonu, prebaciti u fusnotu)
- [ ] **IEEE PDF eXpress** validacija
- [ ] Predaja PDF-a na https://registration.telfor.rs/
- [ ] Najviše 3 rada po autoru — ovo je prvi

## 8. Šta rad **ne** tvrdi

Namjerno, i ne mijenjati bez novog mjerenja:

- Nijedan rezultat nije mjeren na fizički pokrenutom ventilatoru (rekao u V.D).
- Benchmark brojevi su razvojni, sa istorijskom pristrasnošću izbora modela
  (rekao na početku V).
- **Front-end nije opšti ASD rezultat.** Nova sekcija V.C kaže otvoreno: na
  ventilatoru 0,867 protiv 0,627 za log-mel; log-mel pobjeđuje na pet od ostalih
  šest mašina. `sliderEmu` je izuzetak: PSD 0,5851 protiv najboljeg log-mel
  rezultata 0,5593. Primjeri obrnutog odnosa su ToyCar 0,448 protiv 0,539,
  ležaj 0,506 protiv 0,576 i reduktor 0,544 protiv 0,611.
- Kumulativni `dropped` (122 880) se **ne** navodi kao gubitak mjernih uzoraka;
  navodi se samo `dropped_delta = 0` po prozoru.
- Na uređaju su opažene **nula alarmnih epizoda tokom 17,6 min**. To nije
  pouzdano procijenjena dugoročna stopa lažnih alarma.
