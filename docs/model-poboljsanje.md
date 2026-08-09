# Poboljšanje modela — šta je probano i šta je ispalo

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

---

## Rezultati, poređani po uspjehu

| # | Pristup | AUC | Odluka |
|---|---|---|---|
| 1 | **Sažetak log-mela + naučena kovarijansa** | **0,674** | ✔ najbolje |
| 2 | Sažetak + dijagonalna kovarijansa | 0,595 | veze između traka nose signal |
| 3 | Klasifikator brzina ventilatora | 0,530 | premalo klasa, uči napamet |
| 4 | Naučena ugradnja preko svih 7 mašina | 0,495 | uči da ignoriše ono što treba |
| 5 | Autoenkoder (polazno stanje) | 0,451 | referenca |

**Napredak: 0,451 → 0,674, dvadeset dva poena.**

---

## Šta je pobijedilo i zašto

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
| Finiji FFT (4096) i linearne trake | 0,501–0,643 | postojeći front-end je već bolji |
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

## Šta ovo znači za ploču

Pobjednički pristup je **jednostavniji od postojećeg**, ne složeniji:

| | Autoenkoder (sad) | Kovarijansa (predlog) |
|---|---|---|
| Model u flešu | 428 KB binarke, TFLM arena 7960 B | matrica + centar |
| Račun po prozoru | 1055 ms inferencije | jedno množenje vektora matricom |
| Zavisnosti | TFLite Micro, esp-nn | ništa, čist C |
| Kalibracija na licu mjesta | samo prag | centar (256 brojeva) + prag |

Front-end se **ne dira** — log-mel već postoji i verifikovan je na 7,99e-05
protiv PC-a.

---

## Iskrena granica

**0,8 nije dostignuto.** Deset različitih pristupa staje na 0,674, i to nije
stvar podešavanja nego granice onoga što se dâ izvući iz ovog front-enda na
ovom skupu.

Bitan kontekst: DCASE anomalije su **namjerno suptilne**, to je istraživački
izazov. Na živoj ploči, kad je mašina stala, score je skočio sa 10 na 59 i
detekcija je bila trenutna i nedvosmislena (7/7 prozora).

Za primjenu je zato mjerodavnije pitanje **gdje pada stvarni kvar** —
zaglavljena lopatica, disbalans, strano tijelo u rešetki. To je grublje od
DCASE anomalija i treba ga izmjeriti direktno, sa pravim ventilatorom.

## Šta dalje

1. Prenijeti pobjednički pristup na ploču (jednostavnije nego postojeće stanje)
2. Izmjeriti sa **stvarnim ventilatorom i stvarnim kvarom** — ta brojka je za
   primjenu mjerodavnija od benchmark broja
3. Ako je za rad potreban veći benchmark broj, preostaje ozbiljan istraživački
   posao: kontrastivno učenje sa augmentacijama, ArcFace margine, ansambli.
   Bez garancije, i van obima onoga što je dosad probano.
