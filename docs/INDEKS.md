# Indeks dokumentacije

**Ažurirano:** 27.08.2026.

Repo ima mnogo dokumenata jer je metodologija tražila da se svaki pokušaj i
svaki negativan rezultat zapišu. Zato je lako naletjeti na stariji fajl i
zaključiti pogrešno stanje. Ova tabela kaže **šta je aktuelno, a šta je
istraživački trag**.

Pravilo: kad se dva dokumenta razilaze, **noviji datirani snapshot pobjeđuje**.
Dokumenti označeni kao istorijski imaju baner na vrhu i **ne opisuju trenutno
stanje** — čuvaju se jer objašnjavaju *zašto* je nešto odbačeno.

---

## Počni odavde

| Dokument | Za šta je autoritet |
|---|---|
| [`../KONTEKST.md`](../KONTEKST.md) | kontekst i pravila rada na projektu |
| [`../README.md`](../README.md) | gdje je projekat sada, ukratko |
| [`PREOSTALO.md`](PREOSTALO.md) | **jedina aktuelna lista preostalog rada** |
| [`../plan-master-rada.md`](../plan-master-rada.md) | metodologija i plan master rada |
| [`cilj-modela.md`](cilj-modela.md) | nepromjenjivi cilj i kriterij uspjeha |

## Uputstva za razumijevanje projekta (01.09.2026)

Ne uvode nove brojke — sabiraju postojeće na jedno mjesto, za učenje i za odbranu.
Stoje u [`../radno/ucenje/`](../radno/) — vidi [`../radno/README.md`](../radno/README.md).

| Dokument | Sadržaj |
|---|---|
| [`UPUTSTVO-1-KAKO-JE-NASTAO-PROJEKAT.md`](../radno/ucenje/UPUTSTVO-1-KAKO-JE-NASTAO-PROJEKAT.md) | mapa ključnih fajlova + hronologija u 11 etapa: šta je urađeno, izmjereno i zašto je promijenjeno |
| [`UPUTSTVO-2-TEORIJA-OD-NULE.md`](../radno/ucenje/UPUTSTVO-2-TEORIJA-OD-NULE.md) | zvuk, Furijeova transformacija, Welch/PSD, ML, Mahalanobis, metrike, TFLite/TFLM, I2S drajver, rječnik |
| [`UPUTSTVO-3-LITERATURA.md`](../radno/ucenje/UPUTSTVO-3-LITERATURA.md) | naučni radovi: gdje se koji koristi u projektu i šta u njemu treba pročitati |

## Aktuelno stanje i protokoli

| Dokument | Sadržaj | Stanje |
|---|---|---|
| [`DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md`](DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md) | konsolidacija faza 1–8, go/no-go protokol | aktuelno |
| [`REVIEW-KRITICNO-2026-08-20.md`](REVIEW-KRITICNO-2026-08-20.md) | status kritičnih nalaza revizije | aktuelno |
| [`protokol-fizicki-ventilator.md`](protokol-fizicki-ventilator.md) | zaključani protokol fizičkog runa (živi par `physical-fan-v1.9.0` ↔ `asd-quality-v1.6.0`) | aktuelno |
| [`GUIDED25-TEST-VENTILATORA.md`](GUIDED25-TEST-VENTILATORA.md) | vođeni test do 25 min, pass/fail kriteriji | aktuelno |
| [`KAKO-SAMOSTALNO-POKRENUTI-GUIDED25.md`](KAKO-SAMOSTALNO-POKRENUTI-GUIDED25.md) | operatersko uputstvo za launcher | aktuelno |
| [`kanonska-evaluacija.md`](kanonska-evaluacija.md) | usvojeni razvojni benchmark bez curenja | aktuelno |
| [`odluka-finalni-model.md`](odluka-finalni-model.md) | finalni model, rezerva, kriteriji prihvatanja | aktuelno |
| [`problemi-i-rjesenja.md`](problemi-i-rjesenja.md) | baza znanja P1–P19 | živi dokument |
| [`handoff.md`](handoff.md) | predaja stanja u novu sesiju | živi dokument |

## Faze dorade poslije FAN01 (implementacioni zapisi)

Svaki je zapis jedne faze, ne opšti status. Zbirni status je u
`DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md`.

| Dokument | Faza |
|---|---|
| [`PLAN-DORADA-POSLIJE-FAN01.md`](PLAN-DORADA-POSLIJE-FAN01.md) | plan cijelog ciklusa (16.08.) |
| [`DORADA-FAZA1-K1-2026-08-16.md`](DORADA-FAZA1-K1-2026-08-16.md) | K1 fail-closed ugovor |
| [`DORADA-FAZA2-MULTI-SESSION-2026-08-16.md`](DORADA-FAZA2-MULTI-SESSION-2026-08-16.md) | multi-session host |
| [`DORADA-FAZA3-RESEARCH-TELEMETRIJA-2026-08-20.md`](DORADA-FAZA3-RESEARCH-TELEMETRIJA-2026-08-20.md) | research telemetrija 96 + 5×96 |
| [`DORADA-FAZA4-COMMISSIONING-LAB-2026-08-20.md`](DORADA-FAZA4-COMMISSIONING-LAB-2026-08-20.md) | normal-only commissioning, PC laboratorija |
| [`DORADA-FAZA5-6-RUNTIME-HOLD-2026-08-20.md`](DORADA-FAZA5-6-RUNTIME-HOLD-2026-08-20.md) | commissioning runtime, `OBSERVATION_HOLD` |
| [`DORADA-FAZA7-8-LIVENESS-NVS-2026-08-20.md`](DORADA-FAZA7-8-LIVENESS-NVS-2026-08-20.md) | audio liveness, verzionisani NVS profil |
| [`REVIEW-DORADA-FAZA1-FAZA2-2026-08-18.md`](REVIEW-DORADA-FAZA1-FAZA2-2026-08-18.md) | review faza 1–2 (nalazi kasnije zatvoreni) |

## Rezultati i mjerenja

| Dokument | Sadržaj |
|---|---|
| [`rezultat-finalna-validacija-2026-08-27.md`](rezultat-finalna-validacija-2026-08-27.md) | **finalna validacija firmvera na pločici — dva validna runa, svi odbačeni pokušaji, granice tvrdnje** |
| [`rezultat-fan01-2026-08-16.md`](rezultat-fan01-2026-08-16.md) | prvi valjan fizički test ventilatora |
| [`preregistracija-fan01.md`](preregistracija-fan01.md) | preregistracija tog runa (pisana prije runa) |
| [`hardver-verifikacija.md`](hardver-verifikacija.md) | šta je izmjereno na pločici (09.08.) |
| [`e5-mjerenje-01-rezultat.md`](../radno/elektronika/e5-mjerenje-01-rezultat.md) | prvo mjerenje potrošnje |
| [`e5-povezivanje-i-mjerenje.md`](../radno/elektronika/e5-povezivanje-i-mjerenje.md) | postavka E5 mjerenja |
| [`panel-i-virtuelni-taster.md`](panel-i-virtuelni-taster.md) | panel i virtuelni taster |
| [`faza2-semantika-dogadjaja.md`](faza2-semantika-dogadjaja.md) | prisustvo mašine, režim, semantika događaja |

## Put do modela (istraživanje)

| Dokument | Sadržaj |
|---|---|
| [`put-do-modela.md`](put-do-modela.md) | **svi** pokušaji sa brojkama, uključujući neuspjele |
| [`istrazivanje-psd-model.md`](istrazivanje-psd-model.md) | pobjednički PSD otisak |
| [`istrazivanje-preko-0674.md`](istrazivanje-preko-0674.md) | šest rundi probijanja 0,674 |
| [`model-poboljsanje.md`](model-poboljsanje.md) | šta je probano i kako je ispalo |
| [`plan-otpornost-na-buku.md`](plan-otpornost-na-buku.md) | plan otpornosti na buku okoline |

## Hardver i elektronika

Cio ovaj skup živi u [`../radno/elektronika/`](../radno/), zajedno sa
fotografijama i crtežima (`img/`) i generatorom `make_sema_sklopa.py`.
Zašto je odvojen: [`../radno/README.md`](../radno/README.md).

| Dokument | Sadržaj |
|---|---|
| [`plan-dvije-plocice.md`](../radno/elektronika/plan-dvije-plocice.md) | **aktuelna** podjela: ploča U (uređaj) + ploča M (mjerna) |
| [`lemljenje-cjeline-i-mjerenje.md`](../radno/elektronika/lemljenje-cjeline-i-mjerenje.md) | **bench verzija**: šta se lemi po cjelini, spajanje za E5, logički analizator |
| [`sema-cjeline.svg`](../radno/elektronika/sema-cjeline.svg) | šema u tri panela: mjerna ploča · uređaj · spajanje za mjerenje |
| [`sema-sklopa.pdf`](../radno/elektronika/sema-sklopa.pdf) | crteži sklopa, 7 strana A4 (generiše `make_sema_sklopa.py`) |
| [`sema-povezivanja.md`](../radno/elektronika/sema-povezivanja.md) | pinout INMP441 + INA226 |
| [`lemljenje.md`](../radno/elektronika/lemljenje.md) | procedura lemljenja (ažurirana na dvije ploče) |
| [`lemljenje-kratko.md`](../radno/elektronika/lemljenje-kratko.md) | kratka lista za lemljenje |
| [`hardver-lista.md`](../radno/elektronika/hardver-lista.md) | inventar imamo/kupiti |
| [`hardware.md`](../radno/elektronika/hardware.md) | kompatibilnost i nabavka |
| [`donijeti-sa-posla.md`](../radno/elektronika/donijeti-sa-posla.md) | spisak za donijeti s posla |
| [`porudzbina-elektromodul.md`](../radno/elektronika/porudzbina-elektromodul.md) | porudžbina, isporučeno 04.08. |
| [`ina226-provjera.md`](../radno/elektronika/ina226-provjera.md) | dijagnostika INA226 (riješeno 10.08.) |

## Materijal za rad

| Dokument | Sadržaj |
|---|---|
| [`rad-poglavlje-2-pregled.md`](rad-poglavlje-2-pregled.md) | draft poglavlja 2 |
| [`../radovi/master-rad/`](../radovi/master-rad/) | **master rad: tekst, generator `.docx`, FTN šablon i uputstvo mentora** |
| [`../radovi/telfor2026/`](../radovi/telfor2026/) | TELFOR 2026: `HANDOFF.md`, `PREOSTALO-RAD.md`, generatori |
| [`../future-work.md`](../future-work.md) | ideje koje NE idu u kod |

## Dnevnici (hronologija)

| Dokument | Period |
|---|---|
| [`dnevnik-projekta.md`](dnevnik-projekta.md) | cijeli projekat, format datum → šta → rezultat → odluka |
| [`DNEVNIK-NEXT-LEVEL.md`](DNEVNIK-NEXT-LEVEL.md) | izvršenje `PLAN-NEXT-LEVEL.md`, append-style |

---

## ISTORIJSKO — ne koristiti kao trenutno stanje

Ovi fajlovi imaju baner na vrhu i namjerno se ne brišu: objašnjavaju odbačene
smjerove i čine istraživački trag za rad. **Ne izvlačiti iz njih status, plan
ni brojke o trenutnom sistemu.**

| Dokument | Zašto je zamijenjen |
|---|---|
| [`PLAN.md`](PLAN.md) | snimak stanja 09.08.; zamijenjen `PLAN-ZAVRSNICA.md` pa `PREOSTALO.md` |
| [`PLAN-NEXT-LEVEL.md`](PLAN-NEXT-LEVEL.md) | plan izvršen/zatvoren 14.08.; ishodi u `DNEVNIK-NEXT-LEVEL.md` |
| [`PLAN-ZAVRSNICA.md`](PLAN-ZAVRSNICA.md) | zatvoren 14.08. |
| [`analiza-stanja-i-sljedeci-koraci-2026-08-09.md`](analiza-stanja-i-sljedeci-koraci-2026-08-09.md) | datirani audit od 09.08. |
| [`sazetak-za-mentora.md`](sazetak-za-mentora.md) | prijedlog teme iz jula, AE/TFLM smjer |
| [`edge-adaptacija.md`](edge-adaptacija.md) | AE/TFLM deployment putanja, nije finalni detektor |
| [`rad-poglavlje-3-teorija.md`](rad-poglavlje-3-teorija.md) | AE/TFLM/gamma nacrt poglavlja 3 |
| `novi plan.txt` | prvobitni plan iz jula 2026. |
| `teorija-ucenje.html`, `pregled-projekta.html` | HTML pregledi iz jula, prije PSD smjera |

---

## Šta NE ide u dokumentaciju

- Brojka bez izvora (log, artefakt, test ili komanda koju si upravo pokrenuo).
- Tvrdnja da nešto „radi" na osnovu zelenih testova ili uspješnog builda —
  to je softverski dokaz, ne fizički.
- Novi „plan"/„status" fajl kad postojeći pokriva temu. Ažuriraj postojeći i
  datiraj izmjenu.
