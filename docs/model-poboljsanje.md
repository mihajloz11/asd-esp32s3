# Poboljšanje modela — šta je probano i šta je ispalo

Konačni sistemski cilj, pravilo poštenog mjerenja i cilj AUC >= 0,80 definisani
su u [cilj-modela.md](cilj-modela.md). Taj cilj ima prednost nad pojedinačnim
eksperimentom ili trenutno najboljim rezultatom.

> Polazno stanje: autoenkoder daje AUC 0,45–0,60 na ventilatoru, što je blizu
> pogađanja i neupotrebljivo. Ovaj dokument bilježi **svaki** pokušaj da se to
> popravi, uključujući one koji nisu uspjeli, sa izmjerenim brojevima.
>
> Sve brojke su AUC na **novom ventilatoru** (target domen) — primjerku koji
> model nije čuo. To je scenario primjene: ploča se postavi pored nepoznate
> mašine, kalibriše na njenom normalnom radu, i pazi na tu mašinu.

## Protokol mjerenja

Da poređenje bude pošteno, kod svih pokušaja isto:

- **Kalibracija:** k normalnih klipova ciljne mašine (podrazumijevano 20 = 200 s)
- **Ocjena:** preostali normalni klipovi + sve anomalije te mašine
- Klip koji je ušao u kalibraciju **nikad se ne ocjenjuje**
- 20 ponavljanja sa različitim slučajnim izborom, prijavljuje se sredina ± std

Skript: [`pc/tools/bench_adapt.py`](../pc/tools/bench_adapt.py) i srodni.

Ovo je protokol istorijskog PC poređenja. Finalna implementacija koristi
`k=10` (~115 s zajedno sa `WAIT` fazom), dok `k=20` ostaje referentna analiza
osjetljivosti.

---

## Rezultati, poređani po uspjehu

| # | Pristup | AUC | Odluka |
|---|---|---|---|
| 1 | **Visokorezolucioni PSD oblik + naučena kovarijansa** | **0,864** | ✔ novi pobjednik, cilj 0,80 pređen |
| 2 | Sažetak log-mela + naučena kovarijansa | 0,674 | stari pobjednik |
| 3 | Sažetak + dijagonalna kovarijansa | 0,595 | veze između traka nose signal |
| 4 | Klasifikator brzina ventilatora | 0,530 | premalo klasa, uči napamet |
| 5 | Naučena ugradnja preko svih 7 mašina | 0,495 | uči da ignoriše ono što treba |
| 6 | Autoenkoder (polazno stanje) | 0,451 | referenca |

**Napredak: 0,451 → 0,864, više od četrdeset AUC poena.** Detalji i ograničenja
novog mjerenja su u [istrazivanje-psd-model.md](istrazivanje-psd-model.md).

---

## Novi pobjednik: visokorezolucioni PSD otisak

Ventilator je periodična mašina, pa se kvar bolje pokazao u uskim harmonijskim
linijama nego u širokim mel trakama. Novi otisak koristi FFT 8192, 96 traka od
10 do 4000 Hz, Ledoit–Wolf kovarijansu naučenu samo iz normalnih source klipova
i lokalno izmjeren centar novog ventilatora.

Sa k=20 i 50 ponavljanja: **target AUC 0,864 ± 0,025**. Stari 1280-dimenzioni
pristup pod istim seedovima daje 0,669 ± 0,031. Float32 ne mijenja AUC, a cijela
matrica zauzima 36 864 B. Prijenos u firmware i stvarno mjerenje na pločici još
nisu završeni.

---

## Prethodni pobjednik i zašto je bio bolji od autoenkodera

Od svakog klipa se računa **otisak**: sredina i standardna devijacija po svakoj
od 128 mel traka, ukupno 256 brojeva po klipu (odnosno 1280 nad postojećim
640-dimenzionim vektorima).

Sa 990 snimaka ispravnih ventilatora nauči se **kovarijansa** — koje trake se
mijenjaju zajedno kad ventilator ubrza, šta je normalno kolebanje, šta ide u
paru. To nije mreža nego tabela odnosa.

Na ploči se mjeri **samo centar** novog primjerka. Score je Mahalanobisova
udaljenost od tog centra, mjerena u naučenom obliku.

Ključna podjela: **oblik varijacije se uči unaprijed** (traži stotine klipova),
**centar se mjeri na licu mjesta** (dovoljno je deset).

### Zašto je bolje od autoenkodera

Autoenkoder uči da prekopira zvuk. Mreža koja dobro kopira ne mora razumjeti
mašinu — dovoljno joj je da zapamti prosječan oblik spektra. Izmjereno na istom
snimku: ispravan ventilator 2,53, neispravan 2,57, razlika 1,6 %.

Mahalanobis mjeri **kombinaciju**, ne pojedinačne vrijednosti. Nešto može biti
u normalnom rasponu po svakoj traci posebno, a ipak daleko jer je kombinacija
nemoguća — kao čovjek visok 150 cm i težak 120 kg.

---

## Šta nije uspjelo (i zašto se ne treba vraćati na to)

| Ideja | Rezultat | Zašto nije radilo |
|---|---|---|
| Dijagonalna kovarijansa | 0,595 | baca veze između traka, a tu je signal |
| Miješanje naučene i izmjerene kovarijanse | 0,674 (α=1) | najbolje je čisto naučena, mješavina ne pomaže |
| CMN (oduzimanje sredine klipa) | 0,544 | uklanja i korisnu informaciju o nivou |
| Bogatiji sažetak (percentili, dinamika) | 0,578 | više dimenzija, lošija procjena kovarijanse |
| Kalibracija po radnom režimu (k-means) | 0,582 | mali dobitak, ne mijenja sliku |
| Najjača odstupanja umjesto zbira | 0,645 | kvar nije lokalizovan u par traka |
| Finiji FFT (4096) i linearne trake | 0,501–0,643 | ta konkretna rezolucija/agregacija nije bila dovoljna; kasniji FFT 8192 PSD jeste |
| Naučena ugradnja preko svih mašina | 0,495 | vidi dolje |

### Zašto je naučena ugradnja pala

Mreža je učena da razlikuje tipove mašina i radne režime. Taj zadatak je
prelak — dovoljno joj je da nauči „ovo je ventilator, ovo je gearbox". Zato
namjerno **odbacuje varijaciju unutar jedne mašine**, a baš ta varijacija
razlikuje ispravan od neispravnog primjerka. Naučila je da ignoriše ono što
nam treba.

*(Napomena: prvi pokušaj je pao iz drugog razloga — podaci nisu bili
promiješani, pa je validacija ispala jedna jedina klasa i rano zaustavljanje
je vratilo težine iz prve epohe. To je bio bug, ispravljen; i poslije ispravke
pristup je dao 0,495.)*

---

## Šta novi PSD model znači za ploču

Finalni pobjednički pristup je **jednostavniji od istorijskog autoenkodera**;
zahtijevao je novi visokorezolucioni spektralni front-end koji je u međuvremenu
implementiran i provjeren:

| | Istorijski AE/TFLM put | Finalni PSD + Mahalanobis put |
|---|---|---|
| Model u flešu | 428 KB binarke, TFLM arena 7960 B | 96 × 96 matrica 36 864 B + centar |
| Račun po klipu | 1055 ms inferencije poslije log-mela | 38 FFT-ova 8192 + 9216 množenja za score |
| Zavisnosti | TFLite Micro, esp-nn | ništa, čist C |
| Kalibracija na licu mjesta | samo prag | centar (96 brojeva) + prag |

Front-end se **promijenio**. Za PSD tok su napravljeni posebni test-vektori i
PC↔C provjera; finalni `ASD_PSD_LIVE` koristi ovaj put bez TFLM-a.

---

## Iskrena trenutna granica

**Cilj 0,8 je dostignut na PC benchmarku: 0,864 ± 0,025 za referentni
`k=20`.** PSD front-end, Mahalanobis score, lokalni centar i vremenska potvrda
`n=3` preneseni su na pločicu. Finalna implementacija koristi `k=10` (100 s
mjerenja, oko 115 s sa `WAIT` fazom); njen razvojni rezultat je AUC 0,856 ±
0,024 na 20 podjela. Stabilnost praga i ponašanje na fizičkom ventilatoru
ostaju otvoreni i ne mogu se dokazati speaker testom.

Bitan kontekst: DCASE anomalije su **namjerno suptilne**, to je istraživački
izazov. Na živoj ploči, kad je mašina stala, score je skočio sa 10 na 59 i
detekcija je bila trenutna i nedvosmislena (7/7 prozora).

Za primjenu je zato mjerodavnije pitanje **gdje pada stvarni kvar** —
zaglavljena lopatica, disbalans, strano tijelo u rešetki. To je grublje od
DCASE anomalija i treba ga izmjeriti direktno, sa pravim ventilatorom.

## Šta dalje

1. Izmjeriti sa **stvarnim ventilatorom i bezbjedno izazvanim promjenama** —
   ta brojka je za primjenu mjerodavnija od benchmark broja.
2. Na fizičkim normalnim sesijama provjeriti stabilnost normal-only praga i
   po potrebi unaprijed zaključati robustniju formulu. Temporalna potvrda
   `n=3` već je implementirana.
3. Završiti kompletno povezivanje i E5 mjerenje potrošnje.
