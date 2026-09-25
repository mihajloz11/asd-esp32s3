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

## Kontekst i planovi

| Fajl | Sadržaj |
|---|---|
| [KONTEKST.md](KONTEKST.md) | ulazna tačka i pravila rada na projektu (i za AI asistente) |
| [planovi/PREOSTALO.md](planovi/PREOSTALO.md) | **jedina aktuelna lista preostalog rada** |
| [planovi/plan-master-rada.md](planovi/plan-master-rada.md) | metodologija i plan master rada |
| [planovi/future-work.md](planovi/future-work.md) | ideje koje ne idu u kod |
| [planovi/handoff.md](planovi/handoff.md) | predaja stanja u novu sesiju |
| [planovi/PLAN-DORADA-POSLIJE-FAN01.md](planovi/PLAN-DORADA-POSLIJE-FAN01.md) | plan dorade poslije prvog fizičkog testa |
| `planovi/PLAN.md`, `PLAN-NEXT-LEVEL.md`, `PLAN-ZAVRSNICA.md`, `analiza-stanja-…`, `sazetak-za-mentora.md`, `novi plan.txt` | ISTORIJSKI planovi i prijedlog teme |

## Dnevnici, revizije, nacrti

| Fajl | Sadržaj |
|---|---|
| [dnevnici/dnevnik-projekta.md](dnevnici/dnevnik-projekta.md) | hronologija: datum → šta → rezultat → odluka |
| [dnevnici/DNEVNIK-NEXT-LEVEL.md](dnevnici/DNEVNIK-NEXT-LEVEL.md) | izvršenje plana NEXT LEVEL, append-style |
| [revizije/REVIEW-KRITICNO-2026-08-20.md](revizije/REVIEW-KRITICNO-2026-08-20.md) | status kritičnih nalaza revizije |
| [revizije/REVIEW-DORADA-FAZA1-FAZA2-2026-08-18.md](revizije/REVIEW-DORADA-FAZA1-FAZA2-2026-08-18.md) | review faza 1–2 |
| `nacrti/rad-poglavlje-2-pregled.md`, `rad-poglavlje-3-teorija.md` | stari nacrti poglavlja; tekst rada je u `radovi/master-rad/` |

## `ucenje/` — uputstva za razumijevanje projekta

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
| `fft-lekcija.py`, `napravi-vodic.py`, `vizuelni-dodaci.py`, `studio-izgled.py`, `*.svg` | generatori i ilustracije vodiča |
| `stari-pregledi/` | HTML pregledi iz jula, prije PSD smjera |

## `elektronika/` — sklapanje, lemljenje, potrošnja

| Fajl | Sadržaj |
|---|---|
| [plan-dvije-plocice.md](elektronika/plan-dvije-plocice.md) | podjela: ploča U (uređaj) i ploča M (mjerna) |
| [uredjaj-na-protobordu.md](elektronika/uredjaj-na-protobordu.md) | odluka 02.09.: MB-102, LED i taster na 3D držaču, otpornici |
| [lemljenje-cjeline-i-mjerenje.md](elektronika/lemljenje-cjeline-i-mjerenje.md) | šta se lemi po cjelini, spajanje za E5 |
| `lemljenje.md`, `lemljenje-kratko.md`, `lemljenje-kratko.html` | procedura lemljenja |
| `sema-cjeline.svg`, `sema-povezivanja.md/.svg`, `sema-sklopa.pdf`, `sema-lemljenje.svg` | šeme; `make_sema_sklopa.py` pravi PDF i `img/sema-sklopa-s*.png` |
| [kondenzatori.md](elektronika/kondenzatori.md) | koji kondenzator gdje ide i da li treba |
| `e5-povezivanje-i-mjerenje.md`, `e5-mjerenje-01-rezultat.md`, `ina226-provjera.md` | E5 potrošnja; šema u prvom je zastarjela |
| `hardver-lista.md`, `hardware.md`, `porudzbina-elektromodul.md`, `donijeti-sa-posla.md` | inventar i nabavka |
| `img/` | fotografije modula, crteži, renderi |

Pinovi za javnu verziju su u `firmware/esp32s3_asd/main/pins.h`.

## Ostalo

- `fotografije/`: fotografije postavke (HEIC).
- `../radovi/`: master i TELFOR rukopisi, šabloni fakulteta i liste za predaju.
  Ne izvoze se dok radovi nisu objavljeni i odbranjeni
  (`napravi_predaju.py --sa-radovima` ih uključuje, bez šablona i lista).

## Rad van `master`-a

| Grana | Sadržaj | Stanje |
|---|---|---|
| `claude/psd-nonempty-bands` | neprazne PSD trake iza `ASD_PSD_NONEMPTY_BANDS`, zasićenje audio uzoraka | ESP-IDF build prolazi; nije flešovano |
| `measurement/e5-ina226` | E5 firmware, `pc/tools/e5_capture.py`, kit `results/mjerenje_2026-09-21/` | build prolazi (381 488 B); nije flešovano |
