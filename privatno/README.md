# `privatno/` — lični materijal, ne ide uz predaju

Sve ovdje služi meni za rad, učenje i odbranu. Kopija za predaju pravi se bez
ovog foldera i bez `radovi/`:

```powershell
python pc/tools/napravi_predaju.py            # dist/predaja/asd-esp32s3/
python pc/tools/napravi_predaju.py --zip      # i .zip pored foldera
```

Skripta uzima samo commitovano stanje (`git archive`), izbacuje sve označeno
sa `export-ignore` u `.gitattributes`, briše `<!-- privatno:start/end -->`
blokove, linkove ka izbačenim fajlovima pretvara u običan tekst i na kraju
provjerava da ništa privatno nije procurilo.

**Ovaj GitHub repo mora ostati privatan.** Istorija commitova sadrži sve,
uključujući ovaj folder. Za javnu objavu napraviti **novi** repo iz izvezene
kopije (nova istorija, jedan početni commit).

## Raspored

```
privatno/
  KONTEKST.md      ulazna tačka, pravila rada, gdje je istina
  PREOSTALO.md     jedina aktuelna lista preostalog rada
  ideje.md         ideje koje ne idu u kod
  elektronika/     sklop, lemljenje, E5 potrošnja, nabavka, šeme
  ucenje/          uputstva i vodiči za razumijevanje i odbranu
  dnevnici/        hronologija rada (tracking)
  revizije/        revizije iz avgusta (tracking)
  istorija/        stari planovi, handoff, nacrti poglavlja
  fotografije/     fotografije postavke (HEIC)
```

## Aktuelno

| Fajl | Sadržaj |
|---|---|
| [KONTEKST.md](KONTEKST.md) | ulazna tačka i pravila rada na projektu (i za AI asistente) |
| [PREOSTALO.md](PREOSTALO.md) | **jedina aktuelna lista preostalog rada** |
| [ideje.md](ideje.md) | ideje za budući rad; ništa od toga nije u finalnom kodu |
| [elektronika/README.md](elektronika/README.md) | šta važi za sklop i potrošnju sada, i mapa fajlova |

## Tracking

| Fajl | Sadržaj |
|---|---|
| [dnevnici/dnevnik-projekta.md](dnevnici/dnevnik-projekta.md) | hronologija: datum → šta → rezultat → odluka |
| [dnevnici/DNEVNIK-NEXT-LEVEL.md](dnevnici/DNEVNIK-NEXT-LEVEL.md) | izvršenje plana NEXT LEVEL, append-style |
| [revizije/REVIEW-KRITICNO-2026-08-20.md](revizije/REVIEW-KRITICNO-2026-08-20.md) | status kritičnih nalaza revizije |
| [revizije/REVIEW-DORADA-FAZA1-FAZA2-2026-08-18.md](revizije/REVIEW-DORADA-FAZA1-FAZA2-2026-08-18.md) | review faza 1–2 |

## `istorija/`

Istraživački trag, ne današnja lista zadataka. Ne ažurira se.

| Fajl | Sadržaj |
|---|---|
| [planovi/plan-master-rada-jul.md](istorija/planovi/plan-master-rada-jul.md) | prvobitni plan iz jula (AE/TFLM smjer); raniji nacrt istog plana (`novi plan.txt`) je izbačen jer je ovaj njegova proširena verzija |
| [planovi/PLAN.md](istorija/planovi/PLAN.md) | plan od 09.08. |
| [planovi/analiza-stanja-i-sljedeci-koraci-2026-08-09.md](istorija/planovi/analiza-stanja-i-sljedeci-koraci-2026-08-09.md) | analiza stanja 09.08. |
| [planovi/PLAN-NEXT-LEVEL.md](istorija/planovi/PLAN-NEXT-LEVEL.md) | plan NEXT LEVEL (dnevnik izvršenja je u `dnevnici/`) |
| [planovi/PLAN-DORADA-POSLIJE-FAN01.md](istorija/planovi/PLAN-DORADA-POSLIJE-FAN01.md) | plan dorade poslije prvog fizičkog testa |
| [planovi/handoff-2026-08-22.md](istorija/planovi/handoff-2026-08-22.md) | predaja stanja u novu sesiju, 22.08. |
| [planovi/PLAN-ZAVRSNICA.md](istorija/planovi/PLAN-ZAVRSNICA.md) | plan završnice |
| [planovi/sazetak-za-mentora.md](istorija/planovi/sazetak-za-mentora.md) | prijedlog teme za mentora |
| `nacrti/rad-poglavlje-2-pregled.md`, `rad-poglavlje-3-teorija.md` | stari nacrti poglavlja; tekst rada je u `radovi/master-rad/` |

## `ucenje/`

Ne uvode nove brojke; sabiraju postojeće iz datiranih dokumenata. Ako se
razilaze sa `docs/` ili `results/`, izvor pobjeđuje.

| Fajl | Sadržaj |
|---|---|
| [UPUTSTVO-1-KAKO-JE-NASTAO-PROJEKAT.md](ucenje/UPUTSTVO-1-KAKO-JE-NASTAO-PROJEKAT.md) | mapa ključnih fajlova i hronologija u 11 etapa |
| [UPUTSTVO-2-TEORIJA-OD-NULE.md](ucenje/UPUTSTVO-2-TEORIJA-OD-NULE.md) | zvuk, Furije, Welch/PSD, ML, Mahalanobis, metrike, TFLM, I2S |
| [UPUTSTVO-3-LITERATURA.md](ucenje/UPUTSTVO-3-LITERATURA.md) | radovi: gdje se koji koristi i šta čitati |
| [UPUTSTVO-4-PREZENTACIJA-MENTORU.md](ucenje/UPUTSTVO-4-PREZENTACIJA-MENTORU.md) | projekat u sedam koraka, za izlaganje |
| [VODIC-KROZ-PROJEKAT.md](ucenje/VODIC-KROZ-PROJEKAT.md), [.html](ucenje/VODIC-KROZ-PROJEKAT.html) | interaktivni vodič sa objašnjenjima i kodom |
| [VODIC-ZA-RAZGOVOR-SA-PROFESOROM.md](ucenje/VODIC-ZA-RAZGOVOR-SA-PROFESOROM.md) | priprema za razgovor sa mentorom |
| `napravi-vodic.py`, `vizuelni-dodaci.py`, `studio-izgled.py`, `fft-lekcija.py` | prave `VODIC-KROZ-PROJEKAT.html` i `*.svg` pored sebe |
| `nacrtaj-skice.py` | pravi `slike/*.svg` i `slike/*.png` |
| `stari-pregledi/` | HTML pregledi iz jula, prije PSD smjera |

## Ostalo

- `../radovi/`: master i TELFOR rukopisi, šabloni fakulteta i liste za predaju.
  Ne izvoze se dok radovi nisu objavljeni i odbranjeni
  (`napravi_predaju.py --sa-radovima` ih uključuje, bez šablona i lista).
- Javna dokumentacija je u [`../docs/README.md`](../docs/README.md).

## Rad van `master`-a

| Grana | Sadržaj | Stanje |
|---|---|---|
| `claude/psd-nonempty-bands` | neprazne PSD trake iza `ASD_PSD_NONEMPTY_BANDS`, zasićenje audio uzoraka | ESP-IDF build prolazi; nije flešovano |
| `measurement/e5-ina226` | E5 firmware, `pc/tools/e5_capture.py`, kit `results/mjerenje_2026-09-21/` | build prolazi (381 488 B); nije flešovano |
