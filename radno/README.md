# `radno/` — sadržaj koji se odvaja prije javnog repoa

Ovaj folder je namjerno **odvojiv u jednom potezu**. Sve u njemu je korisno za
rad na projektu, ali ne pripada javnoj verziji repoa — ili zato što je lično
(bilješke za učenje), ili zato što je vezano za konkretnu nabavku, radni sto i
komponente koje niko drugi neće ponavljati.

**Odvajanje kad dođe vrijeme:**

```bash
git rm -r --cached radno && echo "radno/" >> .gitignore
```

Fajlovi ostaju na disku, izlaze iz istorije narednih komitova, i ništa u
`pc/`, `firmware/`, `docs/`, `results/` ni `radovi/` ne prestaje da radi — jedini
trag su linkovi iz `docs/INDEKS.md`, `README.md` i `KONTEKST.md` ka
`radno/elektronika/`, koje tada treba ukloniti.

---

## `elektronika/` — sklapanje, lemljenje i energetski dio

Sve što opisuje **fizičku izradu uređaja i mjerenje potrošnje**:

| Fajl | Sadržaj |
|---|---|
| `plan-dvije-plocice.md` | aktuelna podjela: ploča U (uređaj) + ploča M (mjerna) |
| `lemljenje-cjeline-i-mjerenje.md` | bench verzija: šta se lemi po cjelini, spajanje za E5, logički analizator |
| `uredjaj-na-protobordu.md` | odluka 02.09.: uređaj na MB-102, LED/taster na 3D držaču, izbor otpornika i kondenzatora |
| `lemljenje.md`, `lemljenje-kratko.md`, `lemljenje-kratko.html` | procedura lemljenja |
| `sema-cjeline.svg` | šema u tri panela: mjerna ploča · uređaj · spajanje za mjerenje |
| `sema-povezivanja.md`, `sema-povezivanja.svg` | pinout INMP441 + INA226 |
| `sema-sklopa.pdf`, `sema-lemljenje.svg` | crteži sklopa |
| `make_sema_sklopa.py` | generiše `sema-sklopa.pdf` i `img/sema-sklopa-s{1..7}.png` |
| `e5-povezivanje-i-mjerenje.md` | postavka E5 mjerenja potrošnje |
| `e5-mjerenje-01-rezultat.md` | prvo mjerenje: 34,73 mA, naponski kanal odstupa |
| `ina226-provjera.md` | dijagnostika INA226 |
| `hardver-lista.md`, `hardware.md` | inventar i kompatibilnost |
| `porudzbina-elektromodul.md`, `donijeti-sa-posla.md` | nabavka |
| `img/` | fotografije modula, crteži sklopa, renderi |

`make_sema_sklopa.py` putanje računa u odnosu na sam skript
(`DOCS = Path(__file__).parent`, `IMG = DOCS / "img"`), pa radi i poslije ovog
premještanja bez izmjene.

**Ostalo je u `docs/`:** [`hardver-verifikacija.md`](../docs/hardver-verifikacija.md)
— to su mjerenja koja nose tvrdnje rada (PC↔uređaj, latencija, `dropped=0`), pa
pripada naučnom tragu, ne radnom stolu.

## `ucenje/` — uputstva za razumijevanje projekta

Napisana 01.09.2026. Ne uvode nijednu novu brojku — sabiraju postojeće iz
datiranih dokumenata na jedno mjesto.

| Fajl | Sadržaj |
|---|---|
| `UPUTSTVO-1-KAKO-JE-NASTAO-PROJEKAT.md` | mapa ključnih fajlova + hronologija u 11 etapa |
| `UPUTSTVO-2-TEORIJA-OD-NULE.md` | zvuk, Furije, Welch/PSD, ML, Mahalanobis, metrike, TFLite/TFLM, I2S drajver, rječnik |
| `UPUTSTVO-3-LITERATURA.md` | naučni radovi: gdje se koji koristi i šta u njemu čitati |

Ako se dokument iz ovog foldera raziđe sa datiranim izvorom u `docs/`,
**datirani izvor pobjeđuje** — pravilo iz [`docs/INDEKS.md`](../docs/INDEKS.md).
