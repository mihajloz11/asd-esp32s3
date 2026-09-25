# Indeks dokumentacije

**Ažurirano:** 25.09.2026.

Metodologija je tražila da se zapiše svaki pokušaj, uključujući neuspjele,
pa dokumenata ima mnogo. Ova tabela kaže gdje je šta. Kad se dokumenti
razilaze, mjerodavni su sirovi zapisi u `results/` i konkretna verzija koda.
Dokumenti sa banerom „ISTORIJSKI" objašnjavaju odbačene smjerove i ne
opisuju trenutno stanje.

## Počni odavde

| Dokument | Sadržaj |
|---|---|
| [`../README.md`](../README.md) | projekat ukratko, rezultati, build i provjere |
| [`rezultat-finalna-validacija-2026-08-27.md`](rezultat-finalna-validacija-2026-08-27.md) | **završna validacija na ventilatoru**: dva validna runa, svi odbačeni pokušaji, granice tvrdnje |
| [`cilj-modela.md`](cilj-modela.md) | cilj i kriterij uspjeha |
| [`odluka-finalni-model.md`](odluka-finalni-model.md) | finalni model, rezerva, kriteriji prihvatanja |
| [`../results/README.md`](../results/README.md) | mapa rezultata i dokaza |

## Model i evaluacija

| Dokument | Sadržaj |
|---|---|
| [`put-do-modela.md`](put-do-modela.md) | svi pokušaji sa brojkama, od autoenkodera do PSD detektora |
| [`istrazivanje-psd-model.md`](istrazivanje-psd-model.md) | visokorezolucioni PSD otisak |
| [`istrazivanje-preko-0674.md`](istrazivanje-preko-0674.md) | šest rundi nad log-mel obilježjima |
| [`model-poboljsanje.md`](model-poboljsanje.md) | šta je probano i kako je ispalo |
| [`kanonska-evaluacija.md`](kanonska-evaluacija.md) | razvojni benchmark sa zaštitom od curenja |
| [`plan-otpornost-na-buku.md`](plan-otpornost-na-buku.md) | otpornost na buku okoline, dvokanalni pristup |
| [`edge-adaptacija.md`](edge-adaptacija.md) | ISTORIJSKI: autoenkoder i TFLM na uređaju |

## Sistem na uređaju

| Dokument | Sadržaj |
|---|---|
| [`hardver-verifikacija.md`](hardver-verifikacija.md) | PC ↔ uređaj, vrijeme računanja, RAM, `dropped=0` |
| [`faza2-semantika-dogadjaja.md`](faza2-semantika-dogadjaja.md) | prisustvo mašine, režim, semantika događaja |
| [`DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md`](DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md) | konsolidacija faza 1–8 poslije prvog fizičkog testa |
| [`DORADA-FAZA1-K1-2026-08-16.md`](DORADA-FAZA1-K1-2026-08-16.md) | K1 fail-closed ugovor |
| [`DORADA-FAZA2-MULTI-SESSION-2026-08-16.md`](DORADA-FAZA2-MULTI-SESSION-2026-08-16.md) | više sesija u jednom runu |
| [`DORADA-FAZA3-RESEARCH-TELEMETRIJA-2026-08-20.md`](DORADA-FAZA3-RESEARCH-TELEMETRIJA-2026-08-20.md) | research telemetrija 96 + 5×96 |
| [`DORADA-FAZA4-COMMISSIONING-LAB-2026-08-20.md`](DORADA-FAZA4-COMMISSIONING-LAB-2026-08-20.md) | commissioning iz normalnog rada, PC laboratorija |
| [`DORADA-FAZA5-6-RUNTIME-HOLD-2026-08-20.md`](DORADA-FAZA5-6-RUNTIME-HOLD-2026-08-20.md) | commissioning na uređaju, `OBSERVATION_HOLD` |
| [`DORADA-FAZA7-8-LIVENESS-NVS-2026-08-20.md`](DORADA-FAZA7-8-LIVENESS-NVS-2026-08-20.md) | audio liveness, verzionisani NVS profil |
| [`panel-i-virtuelni-taster.md`](panel-i-virtuelni-taster.md) | panel i virtuelni taster |

## Fizičke probe

| Dokument | Sadržaj |
|---|---|
| [`protokol-fizicki-ventilator.md`](protokol-fizicki-ventilator.md) | zaključani protokol runa (`physical-fan-v1.9.0` ↔ `asd-quality-v1.6.0`) |
| [`GUIDED25-TEST-VENTILATORA.md`](GUIDED25-TEST-VENTILATORA.md) | vođeni test, kriteriji prolaza |
| [`KAKO-SAMOSTALNO-POKRENUTI-GUIDED25.md`](KAKO-SAMOSTALNO-POKRENUTI-GUIDED25.md) | pokretanje testa i prikupljanje zapisa |
| [`preregistracija-fan01.md`](preregistracija-fan01.md) | preregistracija prvog testa, pisana prije runa |
| [`rezultat-fan01-2026-08-16.md`](rezultat-fan01-2026-08-16.md) | prvi valjan fizički test |
| [`rezultat-finalna-validacija-2026-08-27.md`](rezultat-finalna-validacija-2026-08-27.md) | završne probe, papirić i ton |

## Problemi

[`problemi-i-rjesenja.md`](problemi-i-rjesenja.md): baza znanja P1–P28, svaka
zamka sa uzrokom, dokazom i rješenjem. Komentari u kodu upućuju na P-oznake.

## Pravila

- Svaka brojka ima izvor: log, artefakt, test ili komandu.
- Zeleni testovi i uspješan build su softverski dokaz, ne fizički.
- Istorijski zapisi u `results/` se ne prepravljaju; ispravke idu kao datirane napomene.
