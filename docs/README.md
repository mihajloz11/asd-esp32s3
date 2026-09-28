# Dokumentacija

**Ažurirano:** 25.09.2026.

Metodologija je tražila da se zapiše svaki pokušaj, uključujući neuspjele.
Dokumenti su zato podijeljeni u tri foldera: model, uređaj i fizičke probe.
Kad se dokument i izvor razilaze, mjerodavni su sirovi zapisi u `results/` i
konkretna verzija koda. Dokumenti sa oznakom „istorijski" objašnjavaju
odbačene smjerove i ne opisuju trenutno stanje.

## Počni odavde

| Dokument | Sadržaj |
|---|---|
| [`pregled-projekta.md`](pregled-projekta.md) | projekat ukratko, rezultati, build i provjere |
| [`probe/rezultat-finalna-validacija-2026-08-27.md`](probe/rezultat-finalna-validacija-2026-08-27.md) | **završne probe na ventilatoru**: dva validna runa, odbačeni pokušaji, granice tvrdnje |
| [`model/cilj-modela.md`](model/cilj-modela.md) | cilj i kriterij uspjeha |
| [`model/odluka-finalni-model.md`](model/odluka-finalni-model.md) | finalni model, rezerva, kriteriji prihvatanja |
| [`problemi-i-rjesenja.md`](problemi-i-rjesenja.md) | baza znanja P1–P28: zamka, uzrok, dokaz, rješenje; komentari u kodu upućuju na P-oznake |
| [`../results/README.md`](../results/README.md) | mapa rezultata i dokaza |

## `model/`: od autoenkodera do PSD detektora

| Dokument | Sadržaj |
|---|---|
| [`put-do-modela.md`](model/put-do-modela.md) | **glavni dokument**: svi pokušaji sa brojkama, faze 1–7, pouke |
| [`kanonska-evaluacija.md`](model/kanonska-evaluacija.md) | razvojni benchmark sa zaštitom od curenja |
| [`plan-otpornost-na-buku.md`](model/plan-otpornost-na-buku.md) | buka okoline, dvokanalni pristup |
| [`istrazivanja/istrazivanje-preko-0674.md`](model/istrazivanja/istrazivanje-preko-0674.md) | detalj faze 3: šest rundi nad log-mel obilježjima (09.08.) |
| [`istrazivanja/istrazivanje-psd-model.md`](model/istrazivanja/istrazivanje-psd-model.md) | detalj faze 4: visokorezolucioni PSD otisak |
| [`istrazivanja/edge-adaptacija.md`](model/istrazivanja/edge-adaptacija.md) | istorijski: autoenkoder i TFLM na uređaju |

## `uredjaj/`: firmware i host

| Dokument | Sadržaj |
|---|---|
| [`hardver-verifikacija.md`](uredjaj/hardver-verifikacija.md) | PC ↔ uređaj, vrijeme računanja, RAM, `dropped=0` |
| [`semantika-dogadjaja.md`](uredjaj/semantika-dogadjaja.md) | prisustvo mašine, režim, semantika događaja |
| [`panel-i-virtuelni-taster.md`](uredjaj/panel-i-virtuelni-taster.md) | panel i virtuelni taster |
| [`dorada-poslije-fan01.md`](uredjaj/dorada-poslije-fan01.md) | konsolidacija dorade poslije prvog fizičkog testa: faze, novi tok, odluka |
| [`dorada-poslije-fan01-faze.md`](uredjaj/dorada-poslije-fan01-faze.md) | izvorni zapisi faza 1–8 (16–20.08.), u jednom fajlu |

## `probe/`: fizički ventilator

| Dokument | Sadržaj |
|---|---|
| [`protokol-fizicki-ventilator.md`](probe/protokol-fizicki-ventilator.md) | zaključani protokol runa (`physical-fan-v1.9.0` ↔ `asd-quality-v1.6.0`) |
| [`guided25.md`](probe/guided25.md) | vođeni test: build, pokretanje, tok, kriterij prolaza, zapisi |
| [`preregistracija-fan01.md`](probe/preregistracija-fan01.md) | preregistracija prvog testa, pisana prije runa |
| [`rezultat-fan01-2026-08-16.md`](probe/rezultat-fan01-2026-08-16.md) | prvi valjan fizički test |
| [`rezultat-finalna-validacija-2026-08-27.md`](probe/rezultat-finalna-validacija-2026-08-27.md) | završne probe, papirić i ton, sa ispravkama od 25.09. |

## Pravila

- Svaka brojka ima izvor: log, artefakt, test ili komandu.
- Zeleni testovi i uspješan build su softverski dokaz, ne fizički.
- Istorijski zapisi u `results/` se ne prepravljaju; ispravke idu kao datirane
  napomene.

## Stare putanje

Zamrznuti artefakti u `results/` pominju putanje od prije 25.09.2026. Ovdje
je gdje su ti dokumenti sada.

| Stara putanja | Sada |
|---|---|
| `docs/INDEKS.md` | `docs/README.md` |
| `docs/cilj-modela.md`, `put-do-modela.md`, `odluka-finalni-model.md`, `kanonska-evaluacija.md`, `plan-otpornost-na-buku.md` | `docs/model/` |
| `docs/istrazivanje-preko-0674.md`, `istrazivanje-psd-model.md`, `edge-adaptacija.md` | `docs/model/istrazivanja/` |
| `docs/model-poboljsanje.md` | spojeno u `docs/model/put-do-modela.md` |
| `docs/hardver-verifikacija.md`, `panel-i-virtuelni-taster.md` | `docs/uredjaj/` |
| `docs/faza2-semantika-dogadjaja.md` | `docs/uredjaj/semantika-dogadjaja.md` |
| `docs/DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md` | `docs/uredjaj/dorada-poslije-fan01.md` |
| `docs/DORADA-FAZA1…FAZA7-8-*.md` (šest fajlova) | `docs/uredjaj/dorada-poslije-fan01-faze.md` |
| `docs/GUIDED25-TEST-VENTILATORA.md`, `KAKO-SAMOSTALNO-POKRENUTI-GUIDED25.md` | `docs/probe/guided25.md` |
| `docs/protokol-fizicki-ventilator.md`, `preregistracija-fan01.md`, `rezultat-*.md` | `docs/probe/` |
| `docs/PLAN*.md`, `PREOSTALO.md`, `handoff.md`, `dnevnik-*.md`, `REVIEW-*.md` i ostalo lično | van predaje (lični folder) |
