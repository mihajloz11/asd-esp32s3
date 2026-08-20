# Put do modela — svi pokušaji, sa brojkama

> Materijal za poglavlje master rada. Ovdje je **svaki** pristup koji je probran
> na putu od autoenkodera (AUC 0,451) do finalnog PSD detektora (AUC 0,864),
> uključujući neuspjele — jer neuspjeli objašnjavaju *zašto* pobjednik radi.
>
> Sve brojke su **AUC na target domenu ventilatora** (primjerak koji model nije
> čuo), osim gdje je izričito navedeno drugačije.

## Zadatak i protokol mjerenja

DCASE 2026 Task 2, mašina `fan`, first-shot postavka. Model uči **samo iz
normalnih** snimaka source domena (990 klipova). Ocjena se radi na target
domenu: drugi fizički primjerak iste vrste mašine.

Protokol lokalne kalibracije, isti kod svih pristupa:

1. k klipova ciljne mašine ide u kalibraciju (mjeri se samo centar),
2. ocjena na preostalim normalnim + svim anomalijama te mašine,
3. klip iz kalibracije se **nikad** ne ocjenjuje,
4. 20–50 ponavljanja sa različitim izborom, prijavljuje se sredina ± std.

**Pravilo poštenog poređenja (naučeno na svojoj koži):** poređenja važe samo na
**uparenim seedovima**. Isti metod pod seedovima 4000+ daje 0,674, a pod 3000+
daje 0,643 — razlika od tri poena je čist šum izbora kalibracionih klipova.
Prije nego što je to uočeno, ta razlika je bila zavedena kao razlika *metoda*.
Uz AUC se zato prijavljuje i broj pobjeda po seedu i uparени t-test.

---

## Faza 1 — neuronske mreže (polazno stanje)

| # | Pristup | AUC | Zašto nije radilo |
|---|---|---:|---|
| 1 | Autoenkoder (DCASE baseline) | 0,451 | vidi dolje |
| 2 | Naučena ugradnja preko svih 7 mašina | 0,495 | vidi dolje |
| 3 | Klasifikator brzina ventilatora (spd 1/2/3) | 0,530 | tri klase su premalo, mreža uči napamet |
| 4 | Samonadzirano učenje (`train_ssl.py`) | ~0,5 | isti razlog kao ugradnja |

**Zašto autoenkoder ne radi.** Uči da prekopira spektar. Mreža koja dobro kopira
ne mora razumjeti mašinu — dovoljno joj je da zapamti prosječan oblik. Izmjereno
na istom snimku: ispravan ventilator 2,53, neispravan 2,57 — **razlika 1,6 %**.
Greška rekonstrukcije nije mjera zdravlja mašine.

**Zašto naučena ugradnja pada.** Mreža je učena da razlikuje tipove mašina i
radne režime. Taj zadatak je prelak: dovoljno joj je „ovo je ventilator, ovo je
gearbox". Zato namjerno **odbacuje varijaciju unutar jedne mašine** — a baš ta
varijacija razlikuje ispravan od neispravnog primjerka. Naučila je da ignoriše
ono što nam treba.

*(Prvi pokušaj ugradnje je pao i iz banalnijeg razloga: podaci nisu bili
promiješani, validacija je ispala jedna jedina klasa, rano zaustavljanje vratilo
težine iz prve epohe. Bug je ispravljen; i poslije ispravke rezultat je 0,495.)*

---

## Faza 2 — statistika nad log-mel sažetkom

Napuštena je mreža. Otisak klipa = sredina + std po mel traci; kovarijansa se
uči unaprijed sa 990 source klipova, na ploči se mjeri samo centar.

| # | Pristup | AUC | Zaključak |
|---|---|---:|---|
| 5 | Sažetak 1280 + puna kovarijansa | 0,643–0,674 | prvi upotrebljiv rezultat |
| 6 | Sažetak + **dijagonalna** kovarijansa | 0,595 | signal je u **vezama** među trakama |
| 7 | Miješanje naučene i izmjerene kovarijanse | 0,674 (α=1) | čisto naučena je najbolja |
| 8 | CMN (oduzimanje sredine po traci) | 0,544 | briše i korisnu informaciju |
| 9 | Bogatiji sažetak (percentili, dinamika) | 0,578 | *pogrešno protumačeno, vidi #12* |
| 10 | Kalibracija po radnom režimu (k-means) | 0,582 | mali dobitak, ne mijenja sliku |
| 11 | Top-k odstupanja umjesto zbira | 0,645 | kvar nije lokalizovan u par traka |

Ključni nalaz faze: **puna kovarijansa 0,855 na source vs dijagonalna 0,543**
znači da informaciju nose korelacije među trakama, ne pojedinačna rasipanja.
Odatle podjela posla koja je ostala do kraja: *oblik varijacije se uči unaprijed*
(traži stotine klipova), *centar se mjeri na licu mjesta* (dovoljno deset).

---

## Faza 3 — sistematska runda nad scoring backendom

Šest serija eksperimenata (`pc/tools/bench_research{,2,3,4,5,6}.py`), sve na
uparenim seedovima, k=20, 20 ponavljanja.

| # | Pristup | AUC | Zaključak |
|---|---|---:|---|
| 12 | **Ledoit–Wolf skupljanje + prostor 256** | **0,673** | +3 poena, 19/20 pobjeda, p<10⁻⁴ |
| 13 | PPCA nisko-rang kovarijansa (q=32) | 0,672 | isti dobitak, jeftinije na ploči |
| 14 | GWRP pooling (TWFR ideja), r=0,99 | 0,686 | +1 nad #12 |
| 15 | **Medijana kalibracionog centra** | **0,716** | +3, potvrđeno na 7 mašina |
| 16 | Trimovana (winsorizovana) sredina centra | 0,671–0,684 | medijana je bolja |
| 17 | kNN na kalibracione egzemplare | 0,565–0,585 | min-udaljenost šteti |
| 18 | Pod-segmenti 2 s + percentil | 0,504–0,544 | razvodnjavanje ne pomaže |
| 19 | Delta/modulacija u sažetku | 0,561 | ne |
| 20 | Modulacioni spektar mel energija | 0,550 | ne |
| 21 | Sprega susjednih traka unutar klipa | 0,460 | ispod slučajnog |
| 22 | Temporalna autokorelacija traka | 0,434 | ispod slučajnog |
| 23 | Medijana *udaljenosti* umjesto centra | 0,684–0,701 | robusno ocjenjivanje ne dodaje |
| 24 | MinCovDet robusna kovarijansa | 0,607–0,682 | lošije od Ledoit–Wolf |
| 25 | Dual score (blizina source korpusa) | 0,539–0,583 | ne |
| 26 | Rang-ansambli mel varijanti | 0,578–0,684 | slabiji član vuče jačeg nadole |

**Otkriće #12 mijenja tumačenje #9.** „Bogatiji sažetak" ranije nije pao zato što
je ideja loša, nego zato što je kovarijansa **loše uslovljena**: matrica 1280×1280
procijenjena iz 990 klipova je matematički neodrživa. Kad se skupljanje uradi
kako treba (Ledoit–Wolf), više dimenzija prestaje da bude kazna.

**Nalaz #15** je jedina izmjena iz ove faze koja je preživjela do kraja kao opšte
pravilo: medijana je otpornija na atipičan kalibracioni klip, dobitak generalizuje
preko mašina (5/7 mašina p<0,01, nigdje značajno gore), a na ploči je trivijalna.

**Plato.** Dvanaest varijanti staje na 0,716. To je bio signal da problem nije u
scoring backendu.

---

## Faza 4 — promjena front-enda (proboj)

Do ovog trenutka svi pristupi su dijelili isti log-mel front-end: FFT 1024,
128 mel traka. Prešlo se na **visokorezolucioni PSD** (`bench_periodicity.py`):

- Welch, `nperseg=8192`, preklapanje 50 % → razmak binova **1,95 Hz**,
- 96 **logaritamskih** traka 10–4000 Hz,
- log10 srednje snage po traci, pa oduzimanje **skalarne** sredine klipa.

| # | Pristup | AUC | Zaključak |
|---|---|---:|---|
| 27 | **`psd_shape`** (gore opisan) | **0,864 ± 0,025** | ✔ **finalni model** |
| 28 | `psd_raw` (bez oduzimanja nivoa) | 0,841 | proboj ne zavisi samo od normalizacije |
| 29 | `periodic` (psd + envelope + skalari) | 0,827 | envelope kvari |
| 30 | Envelope spektar sam (0,5–200 Hz) | 0,513 | modulacija ne nosi signal |
| 31 | psd_shape + medijana centra | 0,855 | medijana ovdje **ne** pomaže |
| 32 | Ansambl psd_shape + mel256 | 0,784 | slabiji član kvari jačeg |

**Zašto radi.** Ventilator je rotaciona mašina: njen potpis su **uske harmonijske
linije** osnovne frekvencije vrtnje. Stari front-end ima razmak binova 15,6 Hz i
mel trake koje dodatno spajaju susjedne frekvencije — te linije se razmažu prije
nego što model uopšte išta vidi. Rezolucija od 1,95 Hz ih razdvaja.

**Zašto #31 i #32 ne pomažu.** Medijana je pomagala jer je mel prostor bio šumniji;
u čistijem PSD prostoru robusnost više nema šta da popravlja. A ansambl potvrđuje
pravilo iz #26: rang-ansambl slabijeg i jačeg featura pogoršava jačeg.

**Zavisnost od dužine kalibracije** (finalni model):

| Kalibracija | 50 s | 100 s | 200 s | 300 s | 400 s |
|---|---:|---:|---:|---:|---:|
| AUC | 0,834 | 0,853 | **0,864** | 0,866 | 0,875 |

Već 50 s prelazi cilj 0,80. Kriva je ravna poslije 200 s — dužina kalibracije
nije usko grlo, što se poklapa sa ranijim mjerenjem na mel modelu (50 s → 0,631,
400 s → 0,639).

---

---

## Faza 4b — generalizacija: PSD je pobjeda **za ventilator**, ne uopšte

Pobjednik je do 09.08.2026 bio mjeren samo na `fan`. Poslije izdvajanja
periodičnih featura za svih 7 mašina slika je bitno drugačija:

| Mašina | psd_shape | mel256 | razlika |
|---|---:|---:|---:|
| **fan** | **0,864** | 0,587 | **+0,277** |
| sliderEmu | 0,587 | 0,557 | +0,031 |
| gearboxEmu | 0,555 | 0,584 | −0,029 |
| valveEmu | 0,728 | 0,764 | −0,036 |
| bearingEmu | 0,495 | 0,560 | −0,065 |
| ToyCar | 0,446 | 0,539 | −0,092 |
| ToyCarEmu | 0,366 | 0,489 | −0,123 |
| **sredina** | 0,577 | 0,583 | −0,005 |
| **harmonijska sredina** (DCASE mjera) | **0,537** | **0,573** | **−0,036** |

**psd_shape pobjeđuje na 2 od 7 mašina.** Po harmonijskoj sredini — a to je
zvanična DCASE mjera — on je **lošiji** od mel osnove.

**Zašto je to fizički očekivano.** Ventilator je rotaciona mašina: potpis su
uske harmonijske linije osnovne frekvencije vrtnje, i rezolucija od 1,95 Hz ih
razdvaja. Ostale mašine u skupu nemaju tu strukturu — ventil je impulsivan,
klizač je trenje, ToyCar je igračka. Tamo visoka frekvencijska rezolucija ne
donosi ništa, a troši dimenzije i pogoršava procjenu kovarijanse.

### Posljedica za sistem: front-end se bira po tipu mašine

Protokol `bench_periodicity.py` bira varijantu **na source domenu, bez ijedne
target oznake**. Taj izbor daje:

| Strategija | Harmonijska sredina AUC |
|---|---:|
| uvijek psd_shape | 0,537 |
| uvijek mel256 | 0,573 |
| **izbor po mašini, samo iz source podataka** | **0,577** |

Izbor po mašini je najbolji i **ne koristi target oznake**, pa je legitiman u
first-shot postavci. Nije nepogrešiv: na `ToyCar` je izabrao `periodic` (0,429)
iako bi `mel256` dao 0,539.

**Za ovaj rad to znači:** uređaj je namijenjen ventilatorima, pa PSD ostaje
ispravan izbor i tvrdnja „AUC 0,864" **važi za ventilator**. Tvrdnja da je PSD
opšte poboljšanje ASD-a **ne stoji** i tako se mora i napisati.

*(Napomena o poređenju: brojke za `mel256` u ovoj tabeli dolaze iz
`bench_periodicity.py`, koji koristi svoju normalizaciju i sredinu kao centar.
Ranije izmjerenih 0,706 za `fan` je varijanta sa medijanom centra iz
`bench_research4.py`. Poređenja važe unutar istog alata.)*

---

## Faza 5 — provjera na pločici (šta benchmark ne pokaže)

Model je prenesen na ESP32-S3 i mjeren uživo ([hardver-verifikacija.md](hardver-verifikacija.md)).
Numerički je sve potvrđeno: PC↔uređaj na **živom mikrofonu** 1,70e-06, račun
704 ms na 10 s zvuka (rezerva 14,2×), `dropped=0`.

Ali AUC izmjeren **preko zvučnika i mikrofona** je 0,716, ne 0,864. Uzrok je
izmjeren, ne pretpostavljen:

| | Score normalnog | Score anomalije |
|---|---:|---:|
| PC, digitalni zvuk | 79 | 117 |
| Uređaj, preko zvučnika | 1 300 – 4 000 | 2 500 – 4 100 |

DCASE anomalija pomjera score za oko **48 %**, a akustički kanal pravi rasipanje
**reda veličine većeg**. Signal nije nestao — zatrpan je. Isti uređaj
zaustavljenu mašinu detektuje bez greške (score 12 000 – 70 000), jer je ta
promjena mnogo grublja od šuma kanala.

**Pouka za tezu:** benchmark AUC i AUC „preko zraka" su dvije različite brojke i
moraju se prijaviti odvojeno. Reprodukcija zvučnikom je konfaund koga u stvarnoj
primjeni nema — tamo uređaj sluša mašinu direktno, bez dvostrukog prolaza kroz
elektroakustiku.

### Koliko kvar mora biti izražen — izmjereno

Kontrolisanim sintetičkim kvarom rastuće jačine (širokopojasni udar jednom po
obrtaju) izmjeren je **prag osjetljivosti cijelog lanca**:

| Jačina kvara | Score digitalno | Preko zvučnika | Alarm |
|---|---:|---:|---|
| ispravan rad | 82 | 433 | — |
| **DCASE anomalija** | **124** | u šumu | ne |
| −30 dB | 135 | 946 | ne |
| −24 dB | 559 | 289 | ne |
| −18 dB | 3 042 | 1 387 | granično |
| −12 dB | 10 448 | **4 843** | **da, 3/3** |

DCASE anomalija odgovara kvaru od **≈ −30 dB**, a preko zvučnika je potrebno
**≈ −15 dB**. Razlika od oko 15 dB objašnjava sve prolaze bez detekcije, i
mjerljivo razdvaja „model ne valja" od „ovaj kvar je pretih za ovaj put zvuka".

Usput su izmjerene i odbačene dvije pogrešne hipoteze (front-end slijep za
udarne kvarove; kanal uništava kvar) — obje u [P14](problemi-i-rjesenja.md#p14).

---

## Faza 6 — šest unaprijed navedenih alternativa, sve slabije

**Datum:** 14.08.2026 · **Alat:** [`evaluate_advanced.py`](../pc/tools/evaluate_advanced.py) ·
**Protokol:** `advanced-evaluation-v1.0.0`, odvojen namespace, kanonski v1.1.0 nije diran

Do ove faze je svaki korak bio pokušaj da se nađe **bolji** feature, i svaki je
bio motivisan onim što je prethodni propustio. Ova faza je prvi put pokušala
suprotno: uzeti šest pravaca koje je plan naveo **unaprijed**, izmjeriti ih sve
odjednom pod istim splitovima, i objaviti rezultat kakav god bio.

Kandidati su bili u kodu prije nego što je ijedan anomalan klip otvoren, i lista
se nije mijenjala prema rezultatu.

| kandidat | ideja | AUC | vs `psd_shape` |
|---|---|---:|---:|
| `psd_shape` | dosadašnji, 96 traka log-PSD | **0,8556 ± 0,0240** | — |
| `psd_order` | PSD u jedinicama reda (f/f0) | 0,6388 | **−0,2168** |
| `psd_regime` | zaseban centar po radnom režimu | 0,8556 | 0,0000 |
| `psd_logratio` | log odnos near/far kanala | 0,7185 | −0,1371 |
| `psd_coherence` | koherencija near↔far po traci | 0,7506 | −0,1050 |
| `psd_masked` | far-izvedena maska buke nad near | 0,4500 | **−0,4056** |
| `transient` | spectral flux, crest, kurtosis | 0,5647 | −0,2909 |
| `psd_plus_transient` | spori PSD + brzi put | 0,8568 | +0,0012 |

**Nijedan ne pobjeđuje.** Jedini pozitivan pomak, +0,0012, je dvadeset puta
manji od sopstvenog rasipanja po splitu (0,024), pa nije poboljšanje nego šum.

### Zašto je svaki pao — mehanizam, ne broj

**Order-warp i režimi (`psd_order`, `psd_regime`).** Cijela ideja stoji na tome
da `spd_1/2/3` znače različitu obrtnu brzinu. Estimator f0 je dao **34,0 Hz za
sve tri**. Prvi refleks je bio da je estimator pokvaren — harmonijska suma po
prirodi vuče ka niskim f0 — pa je urađena kontrola nezavisna od njega: gdje su
tonalni vrhovi iznad spektralne pozadine, po brzini.

| brzina | vrhovi |
|---|---|
| `spd_1` | 68,4 · 76,2 · 78,1 · 93,8 · 99,6 · 101,6 Hz |
| `spd_2` | 68,4 · 76,2 · 78,1 · 93,8 · 99,6 · 101,6 Hz |
| `spd_3` | 68,4 · 76,2 · 78,1 · 95,7 · 99,6 · 101,6 Hz |

Poklapaju se unutar jednog FFT bina. **Brzine se u ovom skupu ne razlikuju po
obrtnoj frekvenciji nego po širokopojasnom nivou.** Estimator je bio ispravan;
68,4 Hz je drugi harmonik od 34,2 Hz. Order-warp je zato samo preskalirao osu i
izgubio rezoluciju traka, a režimsko grupisanje se degenerisalo u jednu grupu —
otud tačno 0,0000 razlike.

**Dual-channel (`psd_logratio`, `psd_coherence`, `psd_masked`).** Svi su slabiji
od near kanala samog. `psd_masked` je pao **ispod slučajnog pogađanja** (0,45), i
razlog je poučan: maska potiskuje trake u kojima je far uporediv sa near, a
ventilator je glasan u **oba** kanala. Maska je time potiskivala baš signal.
Ovo je treći put da neka varijanta near−far pada — prvi je bilo prosto
oduzimanje ([PLAN-NEXT-LEVEL.md](PLAN-NEXT-LEVEL.md), sekcija 2.4).

**Tranzijentni put (`transient`).** Sam po sebi 0,565. Anomalije ovog
ventilatora su tonalne i širokopojasne, a spectral flux i crest mjere udarnost.
Feature mjeri nešto što u ovim podacima ne postoji.

### Šta je ova faza zaista dala

Ne bolji model. Dvije druge stvari:

1. **Potvrdu da su kapabilitetni gate-ovi u firmveru bili ispravni.**
   `asd_events.c` je odbijao da tvrdi `SPEED_CHANGED`, `AMBIENT_NOISE` i
   `MECHANICAL_ANOMALY` jer dokaza nije bilo. Ova faza je dokaze potražila po
   svim trima linijama i nije ih našla. Gate je sada potvrđen mjerenjem, ne
   samo oprezom.
2. **Preusmjeravanje na pravo usko grlo.** Kad šest alternativa ne pomjeri
   feature, a prag se između dvije kalibracije razlikuje 16×
   ([P17](problemi-i-rjesenja.md#p17)), onda dalje ulaganje u feature nema
   smisla. Sljedeći korak je prag, ne model.

---

## Faza 7 — vremenska odluka: standardna tehnika nije prikladna tehnika

**Datum:** 14.08.2026 · **Alat:** [`derive_temporal_policy.py`](../pc/tools/derive_temporal_policy.py)

Ovo nije faza o featureu nego o tome **kako se od niza score-ova pravi alarm**.
Do sada je pravilo bilo „tri uzastopna prozora iznad praga", uvedeno kao razumna
pretpostavka i nikad izmjereno.

Očekivanje je bilo da će EWMA i CUSUM biti nadogradnja. Izmjereno je suprotno:

| pravilo | lažnih/h | reakcija na pobudu od 1 prozora |
|---|---:|---:|
| 3 uzastopna | 0,00 | 0,004 |
| EWMA(0,4) + 3 uzastopna | 5,40 | 0,592 |
| CUSUM k=0,5 h=2 | 5,40 | 0,721 |
| **histereza 1,0/0,7 + 3 uzastopna** | **0,00** | **0,000** |

**Mehanizam.** EWMA i CUSUM po konstrukciji prenose informaciju kroz vrijeme.
U ovom testu sintetička score-pobuda od jednog prozora kod EWMA ostaje u
statistici nekoliko prozora i sama dopuni niz od tri; kod CUSUM-a se akumulira.
Obje tehnike su napravljene da uhvate **mali trajni** pomjeraj u šumu, a ovdje
je zadatak obrnut: odbaciti **veliku kratku** score-pobudu. Govor, vrata i
udarac time nisu akustički testirani. Puno detalja:
[P18](problemi-i-rjesenja.md#p18).

Usvojena je histereza, koja ne unosi memoriju o veličini pobude, a prepolovljuje
alarmne epizode kad se akustika pomjeri (11,16 → 5,40 epizoda na sat na
klipovima drugog fizičkog ventilatora).

---

## Sažetak napretka

| Faza | Najbolji AUC | Šta je bila prava prepreka |
|---|---:|---|
| 1. Neuronske mreže | 0,530 | zadatak učenja ne odgovara zadatku detekcije |
| 2. Statistika nad mel-om | 0,674 | — |
| 3. Scoring backend | 0,716 | uslovljenost kovarijanse (riješeno), pa plato |
| 4. **Front-end** | **0,864** | **rezolucija po frekvenciji** |
| 5. Pločica, preko zvučnika | 0,716 | akustički kanal, ne model |
| 6. Šest alternativa | 0,857 | **nijedna ne pobjeđuje — prepreka nije feature** |
| 7. Vremenska odluka | — | pravilo alarma, ne feature; histereza usvojena |

**Napredak: 0,451 → 0,864** (benchmark), uz potvrđen rad na uređaju.

**Gdje je potraga za featureom stala i zašto.** Faza 6 je prvi put mjerila više
unaprijed navedenih pravaca odjednom, pod istim splitovima, i nijedan nije
nadmašio `psd_shape`. Istovremeno je na uređaju izmjereno da se prag između
dvije kalibracije razlikuje **16×** ([P17](problemi-i-rjesenja.md#p17)), a Faza 7
je sa druge strane pokazala da u 10 od 40 splitova pomjeraj od 3 sd ne dosegne
prag — za svako vremensko pravilo podjednako. Zaključak koji ove tri mjere
zajedno daju: **usko grlo više nije feature nego prag.** To je i sljedeći
pravac, i on je otvoren, ne riješen.

---

## Pouke koje vrijede šire od ovog rada

1. **Feature nosi više od backenda.** Dvanaest varijanti scoring-a dalo je +7
   poena; jedna promjena front-enda dala je +15. Poklapa se sa novijim
   sistematskim poređenjem ASD backenda (arXiv 2606.19269).
2. **Negativan rezultat na bliskim parametrima ne zatvara pravac.** U tabeli
   neuspjeha je stajalo „finiji FFT (4096) i linearne trake → 0,501–0,643", i to
   je zaustavilo istraživanje front-enda na duže vrijeme. Pobjednik je bio dva
   parametra dalje: 8192 umjesto 4096, logaritamske trake umjesto linearnih.
3. **„Verifikovano" ne znači „optimalno".** Log-mel front-end je bio verifikovan
   PC↔uređaj na 7,99·10⁻⁵ i zato tretiran kao nedodirljiv. Verifikacija dokazuje
   da je implementacija tačna, ne da je izbor dobar.
4. **Loše uslovljena kovarijansa liči na lošu ideju.** Prije nego se odbaci
   feature sa mnogo dimenzija, provjeri regularizaciju.
5. **Fizika mašine je bolji vodič od arhitekture modela.** Pitanje „šta kvar
   fizički radi zvuku rotacione mašine" dalo je odgovor koji nijedna promjena
   mreže nije.
6. **Ansambl nije besplatan.** Rang-ansambl slabijeg i jačeg featura je u svakom
   mjerenju pogoršao jačeg.
7. **Standardna tehnika nije ista stvar kao prikladna tehnika.** EWMA i CUSUM su
   udžbenički alat za detekciju pomjeraja i oba su ovdje pogoršala sistem, jer je
   zadatak bio obrnut od onog za koji su pravljeni.
8. **Kad rezultat iznenadi, prvo se provjerava mjerenje.** f0 od 34 Hz za sve
   tri brzine je izgledalo kao pokvaren estimator; kontrola nezavisna od
   estimatora je pokazala da je nalaz tačan. Isti obrazac kao
   [P9](problemi-i-rjesenja.md#p9), [P14](problemi-i-rjesenja.md#p14) i
   [P16](problemi-i-rjesenja.md#p16) — tri puta je artefakt mjerenja bio kriv,
   jednom nije, i samo provjera razlikuje ta dva slučaja.
9. **Negativan rezultat zatvara pravac samo ako je mjeren.** Šest alternativa iz
   Faze 6 nisu odbačene mišljenjem nego brojkom, i svaka ima zapisan mehanizam
   zbog kojeg je pala. Bez toga bi se za pola godine vratile kao „nova ideja".

---

## Gdje je šta

| Sadržaj | Fajl |
|---|---|
| Cilj i kriterij uspjeha | [cilj-modela.md](cilj-modela.md) |
| Finalna odluka + rezerva | [odluka-finalni-model.md](odluka-finalni-model.md) |
| PSD model, detaljno | [istrazivanje-psd-model.md](istrazivanje-psd-model.md) |
| Runde nad scoring backendom | [istrazivanje-preko-0674.md](istrazivanje-preko-0674.md) |
| Rane faze 1–2 | [model-poboljsanje.md](model-poboljsanje.md) |
| Problemi i zamke (P1–P18) | [problemi-i-rjesenja.md](problemi-i-rjesenja.md) |
| Faze 6–7, sirovi rezultati | `results/advanced/advanced_results.json`, `pc/config/asd_temporal_policy_v1.json` |
| Eksperimenti | `pc/tools/bench_periodicity.py`, `bench_research*.py`, `bench_adapt.py`, `bench_blend.py` |
| Rezultati | `results/periodicity_*.json`, `results/research*.json` |
