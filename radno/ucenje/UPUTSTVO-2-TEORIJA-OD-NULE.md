# Uputstvo 2 — teorija od nule: zvuk, Furije, ML, metrike, TFLite, drajver

> Razvojni materijal. Za ispravljeno tumačenje završnih proba i filter prozora
> važi [revizija rezultata od 06.09.2026.](../../docs/rezultat-finalna-validacija-2026-08-27.md). Starije brojke i planovi ovdje nisu novi dokazi.

**Napisano:** 01.09.2026. · **Za koga:** za razumijevanje, ne za citiranje.

Cilj ovog dokumenta je da poslije njega možeš na odbrani objasniti **svaki
pojam koji si upotrijebio**, i da znaš gdje se u kodu taj pojam pretvara u
brojku. Ide od najosnovnijeg ka najsloženijem; slobodno preskači ono što već
znaš.

Prateća uputstva: [`UPUTSTVO-1-KAKO-JE-NASTAO-PROJEKAT.md`](UPUTSTVO-1-KAKO-JE-NASTAO-PROJEKAT.md)
(hronologija i fajlovi) i [`UPUTSTVO-3-LITERATURA.md`](UPUTSTVO-3-LITERATURA.md)
(radovi).

---

## Sadržaj

1. [Zvuk kao brojevi](#1-zvuk-kao-brojevi)
2. [Furijeova transformacija — od tona do spektra](#2-furijeova-transformacija--od-tona-do-spektra)
3. [Od spektra do PSD-a: prozor, curenje, rezolucija, Welch](#3-od-spektra-do-psd-a-prozor-curenje-rezolucija-welch)
4. [Zvuk mašine: šta se tačno sluša kod ventilatora](#4-zvuk-mašine-šta-se-tačno-sluša-kod-ventilatora)
5. [Mel skala i zašto smo je napustili](#5-mel-skala-i-zašto-smo-je-napustili)
6. [Mašinsko učenje — osnovni pojmovi](#6-mašinsko-učenje--osnovni-pojmovi)
7. [Autoenkoder i zašto je ovdje pao](#7-autoenkoder-i-zašto-je-ovdje-pao)
8. [Naš model: Mahalanobis nad PSD otiskom](#8-naš-model-mahalanobis-nad-psd-otiskom)
9. [Od skora do alarma: prag, histereza, HOLD](#9-od-skora-do-alarma-prag-histereza-hold)
10. [Metrike — šta koja stvarno mjeri](#10-metrike--šta-koja-stvarno-mjeri)
11. [TinyML, TensorFlow Lite i TFLite Micro](#11-tinyml-tensorflow-lite-i-tflite-micro)
12. [ESP32-S3 i drajver za mikrofon](#12-esp32-s3-i-drajver-za-mikrofon)
13. [Cio lanac na jednom primjeru](#13-cio-lanac-na-jednom-primjeru)
14. [Rječnik](#14-rječnik)

---

## 1. Zvuk kao brojevi

Zvuk je promjena pritiska vazduha kroz vrijeme. Mikrofon tu promjenu pretvara u
napon, a A/D konverzija u niz brojeva. Tri parametra opisuju to pretvaranje:

**Frekvencija odabiranja (`fs`)** — koliko puta u sekundi se mjeri. Kod nas
**16 000 Hz** (16 kHz), jer je to standard DCASE skupa i sasvim dovoljno za
mašinski zvuk.

**Nyquistova teorema** — signal se može vjerno rekonstruisati samo ako ne sadrži
frekvencije više od `fs/2`. Kod nas je gornja granica **8 kHz**. Sve iznad toga
mora biti filtrirano prije odabiranja, inače se „presavije" u niže frekvencije
kao lažni sadržaj (*aliasing*). Digitalni MEMS mikrofon (INMP441) to rješava u
sebi.

**Rezolucija (broj bita)** — koliko fino se mjeri amplituda. INMP441 daje 24
bita; mi ih svodimo na 16 bita (vidi [odjeljak 12](#12-esp32-s3-i-drajver-za-mikrofon)).

**dBFS** (decibel relative to Full Scale) — nivo u odnosu na maksimum koji format
može da predstavi. 0 dBFS je maksimum, negativne vrijednosti su tiše. Naš tipičan
sobni nivo je oko **−46 dBFS**. Skala je logaritamska: −6 dB je dvostruko manja
amplituda.

> **Gdje je ovo u kodu:** [`audio_i2s.c`](../../firmware/esp32s3_asd/main/audio_i2s.c)
> — `AUDIO_SR` je 16000, konverzija 32→16 bita je u `capture_task`.

---

## 2. Furijeova transformacija — od tona do spektra

### 2.1 Osnovna ideja

Jean-Baptiste Fourier je 1822. pokazao nešto što i danas djeluje neintuitivno:
**svaki periodični signal se može zapisati kao zbir čistih sinusa** različitih
frekvencija, amplituda i faza.

Praktična posljedica: umjesto da gledaš talasni oblik u vremenu („šta je bilo u
svakom trenutku"), možeš gledati **spektar** („koliko ima čega, po
frekvencijama"). Za mašine je spektar mnogo informativniji, jer se svaki
rotacioni dio pojavljuje kao linija na svojoj frekvenciji.

Analogija: talasni oblik je snimak orkestra kao jedan zvuk; spektar je spisak
koji instrument svira koliko glasno.

### 2.2 DFT i FFT

Za digitalni signal koristi se **diskretna Furijeova transformacija (DFT)**. Ona
uzima `N` uzoraka i daje `N` kompleksnih brojeva; svaki od njih nosi amplitudu i
fazu jedne frekvencije.

$$X[k] = \sum_{n=0}^{N-1} x[n] \cdot e^{-j 2\pi kn/N}$$

Naivni račun DFT-a traje `O(N²)` operacija. **FFT (Fast Fourier Transform)** je
algoritam koji isti rezultat daje u `O(N log N)`. Za `N = 8192` to je razlika
između ~67 miliona i ~106 hiljada operacija — otprilike **630×**. Bez FFT-a
ovaj projekat ne bi radio na mikrokontroleru.

Naša implementacija je klasični **radix-2 FFT** sa unaprijed izračunatim
tabelama sinusa/kosinusa (`twiddle` faktori) i bit-reverse permutacijom:
[`psd_features_c.c`](../../firmware/esp32s3_asd/main/psd_features_c.c), nizovi
`tw_re`, `tw_im`, `bitrev`.

### 2.3 Šta znači jedan „bin"

FFT nad `N` uzoraka daje `N/2 + 1` korisnih tačaka (ostatak je simetričan). Svaka
tačka je **bin** — kanta koja pokriva uzak opseg frekvencija. Razmak binova je:

$$\Delta f = \frac{f_s}{N}$$

| N | Δf pri 16 kHz | Trajanje prozora |
|---:|---:|---:|
| 1024 | 15,625 Hz | 64 ms |
| 4096 | 3,91 Hz | 256 ms |
| **8192** | **1,95 Hz** | **512 ms** |

**Ovo je najvažnija tabela u cijelom radu.** Prelazak sa 1024 na 8192 je ono što
je AUC podiglo sa 0,674 na 0,864.

### 2.4 Neizbježan kompromis: vrijeme vs frekvencija

Da bi razdvojio bliske frekvencije, treba ti **dug** prozor. Ali dug prozor znači
da ne znaš *kada* se u tom prozoru nešto desilo. To je fundamentalno ograničenje
(matematički rođak Heisenbergovog principa), ne mana implementacije.

Za nas je izbor lak: kvar ventilatora je **stalno stanje**, ne trenutak. Vrijeme
nam ne treba fino, frekvencija da. Zato biramo dug prozor (512 ms) i mirno
gubimo vremensku rezoluciju.

Za mašinu koja lupa (ventil, udar ležaja) izbor bi bio suprotan — i to je tačno
razlog zašto naš model *ne* generalizuje na `valve` i `slider`
([`put-do-modela.md`](../../docs/put-do-modela.md), faza 4b).

---

## 3. Od spektra do PSD-a: prozor, curenje, rezolucija, Welch

### 3.1 Zašto Hann prozor

FFT pretpostavlja da se signal **periodično ponavlja** izvan prozora. Ako prozor
ne počinje i ne završava istom vrijednošću, na spojevima nastaje vještački skok,
a skok u vremenu je širokopojasan u frekvenciji. Rezultat: energija jednog tona
se „razlije" preko susjednih binova — **curenje spektra (spectral leakage)**.

Rješenje je da se prozor pomnoži funkcijom koja glatko pada na nulu na
krajevima. Mi koristimo **Hannov prozor**:

$$w[n] = 0.5\left(1 - \cos\frac{2\pi n}{N-1}\right)$$

Cijena: glavni „brijeg" oko prave frekvencije postaje malo širi. Dobitak: bočni
listovi padnu za desetine decibela, pa slabu liniju pored jake možeš uopšte da
vidiš. Za mašinu sa mnogo harmonika različite jačine to je presudno.

U kodu: niz `hann` u [`psd_features_c.c`](../../firmware/esp32s3_asd/main/psd_features_c.c).

### 3.2 Periodogram i zašto je previše šuman

Ako uzmeš jedan prozor, uradiš FFT i kvadriraš amplitude, dobiješ **periodogram**
— procjenu snage po frekvenciji. Problem: ta procjena je *ekstremno* šumna.
Varijansa joj se **ne smanjuje** kad povećavaš `N`; samo dobiješ više šumnih
tačaka.

### 3.3 Welchov metod

P. D. Welch je 1967. dao rješenje koje se i danas koristi svuda: signal se
podijeli na **segmente koji se preklapaju**, svaki se prozori i transformiše, a
onda se **periodogrami usrednje**.

Usrednjavanje `K` segmenata smanjuje varijansu procjene otprilike `K` puta.
Cijena je opet rezolucija (segmenti su kraći od cijelog signala), pa je Welch u
suštini podešavanje ravnoteže „koliko glatko vs koliko oštro".

Naši parametri:

| Parametar | Vrijednost | Gdje |
|---|---|---|
| Dužina segmenta (`nperseg`) | 8192 | `ASD_PSD_N_FFT` |
| Pomak (`hop`) | 4096 (preklapanje 50 %) | `ASD_PSD_HOP` |
| Prozor | Hann | `hann[]` |
| Broj segmenata u 10 s | 38 | mjereno u runovima |

**Zašto baš 50 % preklapanja:** Hann prozor priguši krajeve segmenta, pa bi bez
preklapanja dio signala bio potcijenjen. Pomak od pola prozora znači da svaki
uzorak ulazi sa punom težinom bar jednom.

**Zgodna posljedica koja je iskorišćena u firmveru:** pošto je prozor tačno dva
hopa (8192 = 2 × 4096), svaki novi hop zatvara tačno jedan segment. Zato uređaj
ne mora da čuva 10 sekundi zvuka — računa **streaming**, hop po hop, i dobija
**bit-identičan** rezultat kao batch. To je testirano:
`test_psd_features_c.py::test_psd_stream_matches_batch`.

### 3.4 Sažimanje u 96 logaritamskih traka

FFT 8192 daje 4097 binova. Model sa 4097 dimenzija iz 990 snimaka nije moguće
pošteno naučiti (vidi [odjeljak 8.4](#84-zašto-ledoitwolf)). Zato se binovi
grupišu u **96 traka između 10 Hz i 4000 Hz**, sa **logaritamski** raspoređenim
granicama.

**Zašto logaritamski:** harmonici su na `f0, 2f0, 3f0…` — linearno razmaknuti; ali
*relativna* važnost i ljudska/mašinska struktura zvuka su bliže logaritamskoj
skali, a i broj binova po traci ostaje uravnoteženiji. Praktično: niske
frekvencije, gdje živi obrtna frekvencija, dobijaju uže trake i time bolju
rezoluciju.

Za svaku traku uzima se srednja snaga, pa `log10`. Na kraju se od svih 96
vrijednosti oduzme **skalarna sredina klipa** — time se uklanja uticaj toga
koliko je mikrofon blizu ili koliko je pojačanje veliko, a ostaje samo **oblik**
spektra. Otud ime `psd_shape`.

---

## 4. Zvuk mašine: šta se tačno sluša kod ventilatora

Zvuk ventilatora ima dvije potpuno različite komponente:

**1. Tonalne (uske) linije.** Rotacija stvara periodične događaje: svaka lopatica
prođe pored istog mjesta jednom po obrtaju. Ako se osovina vrti `n` puta u
sekundi, u spektru se pojavljuju linije na `f0 = n`, pa `2f0`, `3f0`… i na
*blade pass* frekvenciji `f0 × broj_lopatica`. To su **harmonici**.

**2. Širokopojasni šum.** Turbulencija vazduha nema periodičnost — daje glatku
podlogu preko cijelog spektra.

Kvar mijenja **odnos** ovih komponenti: neuravnotežena lopatica jača `1×f0`,
oštećen ležaj dodaje nove linije i modulacije, začepljen usis mijenja
širokopojasni dio i pomjera radnu tačku.

Zato je fizika ventilatora rekla koji front-end treba: **treba razdvojiti uske
linije**, a za to treba fina frekvencijska rezolucija — 1,95 Hz, ne 15,6 Hz.

Zanimljiv izmjeren detalj iz našeg skupa: tri „brzine" (`spd_1/2/3`) DCASE
ventilatora **imaju istu obrtnu frekvenciju** (vrhovi 68,4 / 76,2 / 78,1 Hz se
poklapaju unutar jednog bina), a razlikuju se samo po širokopojasnom nivou. Zato
je cijela ideja „kalibracija po radnom režimu" pala na nulu razlike
([`put-do-modela.md`](../../docs/put-do-modela.md), faza 6).

---

## 5. Mel skala i zašto smo je napustili

**Mel skala** je perceptivna skala frekvencije: napravljena je tako da jednaki
razmaci u melima odgovaraju jednakim *doživljenim* razmacima visine tona za
ljudsko uho. Ispod ~500 Hz je približno linearna, iznad logaritamska.

**Mel filterbank** grupiše FFT binove u trake po toj skali — standardni prvi
korak u prepoznavanju govora, i standard u DCASE baseline-u (128 traka).

**Zašto je ovdje bila pogrešna:**

1. Mel je napravljen za **ljudsku percepciju govora**. Ventilator ne treba da
   zvuči prirodno, treba da bude mjerljiv.
2. Kombinacija STFT 1024 (Δf = 15,6 Hz) + mel spajanje susjednih binova
   **razmaže** harmonijske linije prije nego što model bilo šta vidi.

Naša zamjena — 96 logaritamskih traka nad FFT 8192 — je konceptualno slična
(grupisanje binova u trake), ali sa 8× finijom polaznom rezolucijom i granicama
biranim za mašinu, ne za uho.

> **Log-mel put nije obrisan** iz repoa: [`features.py`](../../pc/asd/features.py) i
> [`features_c.c`](../../firmware/esp32s3_asd/main/features_c.c) i dalje postoje jer
> su na njima izmjereni svi rezultati autoenkodera koji idu u rad kao poređenje.

---

## 6. Mašinsko učenje — osnovni pojmovi

### 6.1 Šta ML jeste

Umjesto da programer napiše pravilo („ako je nivo na 66 Hz veći od X, kvar je"),
model **izvede pravilo iz podataka**. Programer bira oblik pravila (arhitekturu)
i kriterij (funkciju gubitka), podaci biraju parametre.

### 6.2 Tri vrste učenja

| Vrsta | Šta ima na ulazu | Primjer |
|---|---|---|
| **Nadgledano** | primjeri **sa tačnim odgovorom** | 1000 slika sa oznakom „mačka/pas" |
| **Nenadgledano** | samo primjeri, bez oznaka | grupisanje kupaca po ponašanju |
| **Samonadzirano** | oznake izmišljene iz samih podataka | pogodi sakrivenu riječ u rečenici |

**Naš zadatak je nenadgledan** i to nije stvar ukusa nego stvarnosti: kvarovi su
rijetki, raznovrsni i skupi za izazivanje. Ne možeš prikupiti 500 primjera „ležaj
u kvaru" za svaki ventilator na svijetu. Zato se uči **samo kako izgleda
normalno**, i prijavljuje sve što na to ne liči.

Formalno se to zove **detekcija anomalija** ili **modelovanje jedne klase**
(one-class).

### 6.3 First-shot i domenski pomak

Dva pojma iz DCASE postavke koja moraš znati:

- **Domain shift (domenski pomak)** — model je učen na jednom primjerku mašine
  (`source`), a radi na drugom (`target`): drugi ventilator, druga soba, drugo
  opterećenje. Ono što razlikuje dobar sistem od lošeg nije tačnost na poznatom
  primjerku, nego koliko toga preživi taj pomak.
- **First-shot** — nema *nijednog* prethodnog snimka ciljne mašine za trening;
  najviše nekoliko sekundi za kalibraciju na licu mjesta.

Naš uređaj je tačno taj scenario: pločica nikad prije nije čula taj ventilator.

### 6.4 Curenje podataka (data leakage)

Najopasnija greška u cijelom polju: kad informacija iz test skupa nekako uđe u
učenje. Rezultat je fantastična brojka koja u stvarnosti ne postoji.

U ovom projektu se to desilo jednom, i zapisano je:
kovarijansa je bila učena i ocjenjivana na **istim** klipovima → AUC **0,96**
umjesto stvarnih **0,758**. Otud pravilo koje sad drži cio projekat:

> Klipovi za učenje opšteg modela, za lokalnu kalibraciju i za konačnu ocjenu
> moraju biti razdvojeni. Ciljne anomalije se koriste **samo** za konačnu ocjenu
> — nikad za centar, kovarijansu, prag ili izbor varijante.

CI to čak i mehanički provjerava: sve politike moraju nositi
`target_anomalies_used: false` ([`ci.yml`](../../.github/workflows/ci.yml)).

---

## 7. Autoenkoder i zašto je ovdje pao

### 7.1 Kako radi

**Autoenkoder (AE)** je neuronska mreža koja uči da **prekopira svoj ulaz**, ali
kroz usko grlo. Naš baseline: 640 → 128 → 128 → **8** → 128 → 128 → 640.

Kroz bottleneck od 8 brojeva ne može proći sve, pa mreža mora naučiti da sažme
ono bitno. Ideja detekcije: ako je mreža učena samo na normalnom zvuku, normalan
ulaz će rekonstruisati dobro (mala greška), a anomalan loše (velika greška).
**Greška rekonstrukcije = anomaly score.**

### 7.2 Zašto nije radio

Izmjereno na istom snimku: ispravan ventilator **2,53**, neispravan **2,57** —
razlika **1,6 %**. AUC 0,451, ispod slučajnog pogađanja.

Mehanizam: mreža koja dobro kopira **ne mora razumjeti mašinu**. Dovoljno joj je
da zapamti prosječan oblik spektra. A prosječan oblik se kvarom skoro ne mijenja
— mijenja se fina struktura, koju bottleneck od 8 brojeva ionako baca.

Isto je palo i sa naučenom ugradnjom (embedding, AUC 0,495): mreža učena da
razlikuje *tipove mašina* namjerno odbacuje varijaciju **unutar** jedne mašine —
a baš to je ono što nam treba. Naučila je da ignoriše ono što tražimo.

> **Ovo je dobar materijal za odbranu:** negativan rezultat sa objašnjenim
> mehanizmom vrijedi više od pozitivnog bez objašnjenja.

---

## 8. Naš model: Mahalanobis nad PSD otiskom

Finalni model **nije neuronska mreža**. To je statistika, i to je namjerno.

### 8.1 Šta je „model" ovdje

Tri stvari u flešu i jedna naučena na licu mjesta:

| Šta | Veličina | Gdje se uči |
|---|---|---|
| Precizna matrica 96×96 | 36 864 B | PC, 990 snimaka ispravnih ventilatora |
| Normalizacija (mean/std) | 768 B | PC, isti korpus |
| **Lokalni centar** (96 brojeva) | 384 B | **na uređaju**, ~100 s slušanja |
| Prag (enter/exit) | 2 broja | **na uređaju**, iz normal-only prozora |

Ukupno ~38 KB, bez ijednog množenja matrica dubine mreže.

### 8.2 Euklidska vs Mahalanobisova udaljenost

Ako imaš tačku i „centar", najprostija mjera udaljenosti je euklidska: koren
zbira kvadrata razlika. Problem: ona pretpostavlja da su sve dimenzije jednako
važne i **međusobno nezavisne**.

U spektru ventilatora to nije tačno. Kad se ventilator malo ubrza, *sve* trake
oko harmonika se pomjere zajedno — te dimenzije su jako korelisane. Euklid bi
takvu normalnu varijaciju proglasio velikom promjenom.

**Mahalanobisova udaljenost** to rješava tako što mjeri udaljenost **u
jedinicama sopstvene varijacije podataka**:

$$d^2(x) = (x - \mu)^{\top} \Sigma^{-1} (x - \mu)$$

- `x` — otisak trenutnog prozora (96 brojeva),
- `μ` — lokalni centar (naučen na licu mjesta),
- `Σ⁻¹` — **precizna matrica**, inverz kovarijanse (naučena unaprijed).

Intuicija: podaci se prvo „isprave" tako da oblak varijacije postane sfera, pa se
onda mjeri obična udaljenost. Pomjeraj u smjeru u kojem se zvuk ionako često
mijenja daje malu udaljenost; pomjeraj u smjeru koji se nikad ne dešava daje
veliku.

**Dvostranost dolazi besplatno.** Udaljenost je uvijek pozitivna, pa raste i kad
nešto poraste i kad nešto padne. Zato ovaj skor hvata i „ventilator se ubrzao" i
„ventilator je stao" — što jednostrani prag na grešci rekonstrukcije nije mogao
([P11](../../docs/problemi-i-rjesenja.md#p11)).

### 8.3 Podjela posla: oblik se uči unaprijed, centar na licu mjesta

Ovo je centralna ideja rada i izmjerena je, ne pretpostavljena:

- **Puna kovarijansa: AUC 0,855** vs **dijagonalna: 0,543.** Informacija je u
  **vezama među trakama**, ne u pojedinačnim rasipanjima.
- Za procjenu tih veza treba **stotine** snimaka → radi se na PC-u, jednom.
- Za centar je dovoljno **deset** klipova (100 s) → radi se na uređaju, na
  nepoznatom ventilatoru.

Otud i cio koncept uređaja: težak dio (oblik varijacije) je univerzalan za
ventilatore i ide u fleš; lak dio (gdje je centar) je specifičan za primjerak i
uči se na licu mjesta.

### 8.4 Zašto Ledoit–Wolf

Kovarijansa 96×96 ima 4 656 nezavisnih brojeva. Procijeniti ih iz 990 snimaka
ide, ali procjena je i dalje šumna, a njen **inverz** je osjetljiv: mali šum u
malim sopstvenim vrijednostima postaje ogroman poslije inverzije.

**Ledoit–Wolf skupljanje (shrinkage)** miješa izmjerenu kovarijansu sa
jednostavnom „mirnom" metom:

$$\Sigma_{\text{LW}} = (1-\alpha)\,S + \alpha \cdot \frac{\text{tr}(S)}{p} I$$

Koeficijent `α` se bira analitički, iz samih podataka. Rezultat je matrica koja
je uvijek dobro uslovljena i sigurna za inverziju.

**Izmjereno u projektu:** +3 poena AUC, 19 od 20 pobjeda po podjeli, `p < 10⁻⁴`.

I važnija pouka: raniji zaključak „bogatiji sažetak ne pomaže" **nije bio tačan**
— sažetak od 1280 dimenzija iz 990 klipova je bio matematički neodrživ. Kad se
regularizacija uradi kako treba, više dimenzija prestaje da bude kazna. Otud
pouka: *loše uslovljena kovarijansa liči na lošu ideju.*

---

## 9. Od skora do alarma: prag, histereza, HOLD

Skor je broj. Alarm je odluka. Između njih je četiri sloja, i **svaki od njih je
uveden zato što je nešto konkretno palo**.

### 9.1 Prag iz normal-only podataka

Uređaj sluša ~44 prozora normalnog rada, i uzima **99. percentil** izmjerenih
skorova kao ulazni prag. Nijedan stimulus (papirić, govor, ton) ne ulazi u taj
račun — to je pravilo, i CI ga provjerava.

Istorijski je isprobana i **gamma raspodjela**: skorovi udaljenosti su pozitivni
i asimetrični, pa je gamma prirodan izbor. Parametri se procjenjuju **momentnom
metodom**, a kvantil se računa **Wilson–Hilferty aproksimacijom** (jer na
mikrokontroleru nema `scipy`). Poklapanje sa `scipy` bilo je bolje od 2 %, a
uređaj je fitovao 0,77090 naspram PC-ovih 0,77064.

U finalnom putu je gamma zamijenjena empirijskim p99, jer je robustni fit u
runovima davao prag `791` naspram normalnih VERIFY prozora `2 083–7 766`
([P26](../../docs/problemi-i-rjesenja.md)).

### 9.2 Histereza — dva praga umjesto jednog

Sa jednim pragom, skor koji se šeta oko granice pravi „treperenje" alarma.
Rješenje je da **ulazak** i **izlazak** imaju različite pragove:

- ulaz: `thr_enter` (npr. 8 084),
- izlaz: `thr_exit = 0,7 × thr_enter` (npr. 3 707).

Alarm se ne gasi dok skor ne padne osjetno ispod praga na kojem je nastao.

### 9.3 Tri uzastopna prozora

Alarm se podiže tek poslije **3 uzastopna** prozora iznad praga (~30 s). Jedan
prozor iznad praga ne znači ništa.

**Izmjereno poređenje pravila:**

| Pravilo | Lažnih/h | Reakcija na pobudu od 1 prozora |
|---|---:|---:|
| 3 uzastopna | 0,00 | 0,004 |
| EWMA(0,4) + 3 uzastopna | 5,40 | 0,592 |
| CUSUM k=0,5 h=2 | 5,40 | 0,721 |
| **histereza 1,0/0,7 + 3 uzastopna** | **0,00** | **0,000** |

EWMA i CUSUM su udžbenički alati za detekciju pomjeraja i oba su **pogoršala**
sistem, jer po konstrukciji prenose informaciju kroz vrijeme — a zadatak je bio
obrnut: odbaciti veliku kratku pobudu.

### 9.4 `OBSERVATION_HOLD` — kapija pouzdanosti

Najsuptilniji sloj. Prije nego što se prozor uopšte poredi sa pragom, provjerava
se **da li je taj prozor uopšte pouzdan** — da li je zvuk u njemu bio stabilan.

Pravilo je normal-only i izvodi se **po sesiji**: `max(10 CAL normalnih) × 1,25`.
Nestabilan prozor se ne tumači ni kao normalan ni kao anomalan — **odbacuje se**,
i brojač uzastopnih prekoračenja stoji.

Ovo je razlog zašto u finalnom runu **govor i vrata nisu podigli alarm** iako su
im skorovi bili visoki (36 838 i 4 366): 4 od 5 prozora govora završilo je u
HOLD-u. To je tražena osobina — smetnja se odbija kao nepouzdana, umjesto da se
lažno svrsta u kategoriju.

Isti mehanizam je i razlog zašto je papirić prošao samo u jednom od tri bloka:
drži se rukom, pa stimulus po konstrukciji nije konstantan.

### 9.5 Redoslijed stanja uređaja

```
SETTLE            čeka da se mikrofon i okruženje ustale
   ↓
CENTER_LEARNING   10 prozora → lokalni centar
   ↓
COMMISSION_DERIVE 44 prozora normalnog rada → prag (p99)
   ↓
COMMISSION_VERIFY provjera praga na svježim normalnim prozorima
   ↓                (ako padne → run je odbačen, prag se NE pomjera)
MONITORING        ANOMALY → ANOMALY_SUSTAINED
```

Kod: [`asd_commissioning.c`](../../firmware/esp32s3_asd/main/asd_commissioning.c),
[`asd_temporal.c`](../../firmware/esp32s3_asd/main/asd_temporal.c),
[`asd_interference.c`](../../firmware/esp32s3_asd/main/asd_interference.c).

---

## 10. Metrike — šta koja stvarno mjeri

### 10.1 ROC i AUC

Detektor daje broj; ti biraš prag. Za svaki mogući prag dobiješ par:

- **TPR** (True Positive Rate, odziv) — koliko anomalija je uhvaćeno,
- **FPR** (False Positive Rate) — koliko normalnih je lažno prijavljeno.

**ROC kriva** je skup svih tih parova. **AUC** je površina ispod nje.

Najkorisnija interpretacija AUC-a:

> AUC je vjerovatnoća da nasumično izabrana **anomalija** dobije viši skor od
> nasumično izabranog **normalnog** primjera.

- AUC = 0,5 → slučajno rangiranje,
- AUC = 1,0 → savršeno razdvajanje,
- AUC < 0,5 → sistematski **pogrešno** (detektor je „naopako").

**Šta AUC NIJE:** nije tačnost. AUC 0,864 **ne znači** 86 % tačnih odluka. AUC
mjeri **rangiranje** kroz sve pragove; ne kaže ništa o tome da li tvoj izabrani
prag valja.

Ovo nije akademska napomena — to je najskuplja lekcija projekta. FAN01 je imao
skoro savršeno rangiranje **i istovremeno** 54 od 60 normalnih prozora iznad
praga.

### 10.2 pAUC

**Parcijalni AUC** gleda samo lijevi dio ROC krive — kod DCASE-a `FPR ≤ 0,1`.
Razlog: u praksi sistem sa 40 % lažnih alarma niko neće koristiti, pa i nema
smisla nagrađivati ponašanje u tom dijelu krive.

### 10.3 Harmonijska sredina i DCASE skor

DCASE kombinuje AUC na `source` domenu, AUC na `target` domenu i pAUC
**harmonijskom sredinom**:

$$H = \frac{n}{\frac{1}{x_1} + \frac{1}{x_2} + \dots + \frac{1}{x_n}}$$

Harmonijska sredina je nemilosrdna prema najslabijem članu — jedan loš rezultat
obara cio skor. To je namjerno: sistem koji je odličan na poznatoj mašini i
beskoristan na novoj nije rješenje.

Baš po toj mjeri je izmjereno da naš `psd_shape` (0,537) **gubi** od mel osnove
(0,573) preko svih 7 mašina, iako na ventilatoru dobija ubjedljivo. Zato se
tvrdnja piše sa opsegom važenja.

### 10.4 Metrike koje uređaj zaista treba

AUC je istraživačka metrika. Za uređaj se prijavljuju:

| Metrika | Šta znači | Naša vrijednost |
|---|---|---|
| Lažnih epizoda / h | koliko puta dnevno alarm bez razloga | 0 u VERIFY blokovima |
| Kašnjenje detekcije | koliko traje dok se alarm ne javi | ~30 s (3 prozora) |
| Vrijeme oporavka | koliko traje dok se alarm ne ugasi | medijana 10,08 s |
| % vremena u alarmu | udio alarmnog vremena u runu | 6,98 % (run A) |
| `dropped` | izgubljenih audio uzoraka | **0** |
| `compute_ms` | vrijeme računa po prozoru od 10 s | 716–728 ms |

> Pravilo iz [`cilj-modela.md`](../../docs/cilj-modela.md): *„Za stvarni uređaj AUC nije
> dovoljan."*

### 10.5 Zašto se rezultati prijavljuju kao „± std" i sa uparenim seedovima

Koji klipovi uđu u kalibraciju je slučajno. Zato se svaki eksperiment ponavlja
20–100 puta sa različitim izborom, i prijavljuje sredina ± standardna devijacija.

Naučeno na svojoj koži: isti metod pod seedovima 4000+ daje 0,674, a pod 3000+
0,643 — **tri poena razlike je čist šum izbora klipova**. Prije nego što je to
uočeno, ta razlika je bila zavedena kao razlika *metoda*. Otud pravilo: poređenja
važe samo na **uparenim seedovima**, uz broj pobjeda i upareni t-test.

---

## 11. TinyML, TensorFlow Lite i TFLite Micro

Ovaj dio je u finalnom putu **istorijski** — završni detektor nema neuronsku
mrežu. Ali sve TFLM mjerenje je urađeno, u radu je, i mora se znati objasniti.

### 11.1 Piramida pojmova

| Pojam | Šta je |
|---|---|
| **TensorFlow** | Googleov okvir za pravljenje i treniranje modela (Python, GPU) |
| **Keras** | visoki API iznad TF-a; naši AE modeli su pisani u njemu |
| **TensorFlow Lite (TFLite)** | format i runtime za mobilne uređaje; model se *konvertuje* iz TF-a u `.tflite` |
| **TFLite Micro (TFLM)** | verzija za mikrokontrolere: bez OS-a, bez `malloc`-a, bez fajl sistema, C++ biblioteka reda desetina KB |
| **TinyML** | cijela oblast: ML na uređajima sa KB memorije i mW potrošnje |

### 11.2 Šta TFLite konverzija radi

1. **Zamrzava graf** — treniranje je gotovo, ostaje samo prolaz unaprijed.
2. **Fuzuje slojeve** — npr. BatchNorm se upije u prethodni Dense sloj. Zato na
   uređaju od naše mreže ostaju samo `FullyConnected` + `Relu`.
3. **Serijalizuje** u FlatBuffer — format koji se čita bez raspakivanja.
4. Opciono **kvantizuje**.

### 11.3 int8 kvantizacija

Umjesto 32-bitnih realnih brojeva, težine i aktivacije se čuvaju kao **8-bitni
cijeli brojevi**:

$$r = S \cdot (q - Z)$$

gdje je `r` stvarna vrijednost, `q` cjelobrojna, `S` skala, `Z` nulta tačka.
Dobitak: 4× manje memorije i mnogo brža aritmetika (procesor radi cijele brojeve
brže od realnih, a vektorske instrukcije obrađuju više njih odjednom).

**PTQ (Post-Training Quantization)** — kvantizuje se gotov model, uz mali
reprezentativni skup podataka da bi se odredile skale. To smo radili
([`quantize.py`](../../pc/asd/quantize.py)).

**Izmjereno u ovom radu:** kvantizacija je **besplatna** — ΔhMean ∈ [−0,005;
+0,011] preko svih 35 kombinacija modela i mašina. Čak i Mahalanobis backend nad
int8 greškama preživljava bez gubitka.

### 11.4 Arena

TFLM ne alocira memoriju dinamički. Dobija **jedan blok** (`tensor arena`) i sam
raspoređuje međurezultate u njemu. Programer procijeni veličinu, pa je smanji
kad vidi stvarno `arena_used`.

**Izmjereno:** plan je procjenjivao 50–150 KB, stvarnost je bila **7 960 B**.
Klasična pouka TinyML-a: mali dense modeli troše mnogo manje nego što intuicija
kaže.

### 11.5 esp-nn i PIE

**esp-nn** je Espressifova biblioteka optimizovanih kernela; na S3 koristi
**PIE** (Processor Instruction Extensions) — SIMD instrukcije koje rade više
int8 množenja u jednom taktu.

**Izmjereno:** inferenca 870 ms sa `esp-nn` naspram 1157 ms sa običnim C-om →
**1,33×** čisto od PIE. Puna razlika S3 vs klasični ESP32 je **2,76×** ukupno i
3,6× na inferenci — dakle najveći dio dolazi od platforme (takt, keš, PSRAM), ne
samo od vektorskih instrukcija.

### 11.6 Zašto TFLM nije u finalnom putu

Zato što je izmjereno da statistički model radi **bolje** (0,864 vs 0,451) i
**jeftinije** (38 KB tabela + jedno množenje matricom, bez arene i bez
interpretera). Rad taj put ne skriva — on je i dalje u repou
([`tflm_infer.cc`](../../firmware/esp32s3_asd/main/tflm_infer.cc)) sa svim
mjerenjima, jer negativan rezultat sa mjerenjem je rezultat.

---

## 12. ESP32-S3 i drajver za mikrofon

### 12.1 Platforma

**ESP32-S3-WROOM-1 N32R16V**: dvojezgarni Xtensa LX7 na 240 MHz, ~512 KB
internog SRAM-a, 32 MB fleša, 16 MB PSRAM-a, PIE vektorske instrukcije.

**PSRAM** je vanjska memorija preko SPI-ja: velika, ali sporija od internog
SRAM-a i — bitno — **DMA je ne vidi** direktno. Zato DMA baferi moraju ostati u
internom SRAM-u, a u PSRAM idu veliki baferi kojima se pristupa iz koda.

Finalni build koristi ~293 kB DIRAM-a, ostaje ~342 kB slobodno.

### 12.2 Zašto I2S, a ne analogni mikrofon

**INMP441** je digitalni MEMS mikrofon: A/D konverzija je **u samom mikrofonu**,
pa preko žica ide digitalni tok. Prednost je ogromna — analogni signal na 20 cm
žice pored ESP32 modula pokupio bi smetnje napajanja i Wi-Fi-ja; digitalni ne.

**I2S (Inter-IC Sound)** je serijski protokol za audio, sa tri linije:

| Linija | Puno ime | Šta radi |
|---|---|---|
| **BCLK** | bit clock | takt: jedan impuls po bitu |
| **WS / LRCLK** | word select | kaže da li je uzorak lijevi ili desni kanal |
| **SD / DIN** | serial data | sami bitovi |

Kod nas je **ESP32 master** (on generiše BCLK i WS), a mikrofon slave. Pinovi na
S3: BCLK 4, WS 5, SD 6 ([`pins.h`](../../firmware/esp32s3_asd/main/pins.h)).

INMP441 ima i pin `L/R`: vezan na GND znači „javljaj se u lijevom slotu". Zato
je u kodu `slot_mask = I2S_STD_SLOT_LEFT`.

Format je **Philips standard**: podatak kasni jedan takt za promjenom WS-a. Otud
`I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG` u
[`audio_i2s.c`](../../firmware/esp32s3_asd/main/audio_i2s.c).

### 12.3 24 bita u 32-bitnom slotu i `>>14`

INMP441 daje **24-bitni** uzorak, ali ga šalje u **32-bitnom** slotu, poravnat
uz gornji kraj. Nama trebaju 16-bitni uzorci.

Kod radi `pcm[i] = (int16_t)(raw[i] >> 14)`. Da je pomak bio 16, dobio bi tačno
gornjih 16 bita. Pomak od 14 daje **4× veće** vrijednosti, tj. **12 dB više
osjetljivosti** — svjestan kompromis, jer je mašinski zvuk tih.

Rizik tog izbora je klipovanje na glasnom događaju, i zato je **izmjeren**:
sirovi 32-bitni peak kroz tri snimka bio je 89 064 960 / 54 037 376 / 16 724 480
(27 / 26 / 24 od 31 bita), `clipped = 0` svuda, **rezerva do klipovanja 15,6 dB**.

> **Ovo je uzorak kako projekat radi:** kompromis se ne brani argumentom nego
> mjerenjem koje pokazuje koliko rezerve ima.

### 12.4 DMA i ring buffer

**DMA (Direct Memory Access)** je hardver koji prebacuje podatke iz I2S periferije
u memoriju **bez procesora**. Drajver drži 4 deskriptora po 1024 uzorka; dok
procesor obrađuje jedan, DMA puni sljedeći. Bez toga bi svaki propušteni trenutak
značio izgubljene uzorke.

Iz DMA bafera podaci idu u **ring buffer** (kružni bafer) od 2 s — 64 KB u
PSRAM-u ako ga ima, inače u internom SRAM-u. Ring buffer razdvaja *proizvođača*
(snimanje, mora biti tačno na vrijeme) od *potrošača* (račun, može malo da
kasni).

`dropped` broji uzorke koji nisu stali u ring buffer. **`dropped = 0` je u ovom
projektu obavezan uslov validnog runa** — bez toga se ne zna šta je uređaj
zapravo čuo.

### 12.5 FreeRTOS: taskovi i jezgra

ESP-IDF nosi **FreeRTOS**, mali operativni sistem za realno vrijeme. Posao je
podijeljen:

- `capture_task` — visok prioritet, **pinovan na jezgro 0**, samo čita I2S i
  puni ring buffer;
- glavna petlja — **jezgro 1**, uzima podatke iz ring buffera i računa.

Razdvajanje po jezgrima je namjerno: dug račun na jednom jezgru ne smije da
odgodi snimanje na drugom.

**Watchdog** je tajmer koji restartuje sistem ako task predugo ne ustupi
procesor. Jednom nas je koštao runa: ispis dugačkog base64 toka trajao je 19 s
bez ustupanja, pa je watchdog upisao svoj tekst **usred** toka i pokvario WAV
([P4](../../docs/problemi-i-rjesenja.md#p4)). Rješenje: `vTaskDelay` svakih 16 linija +
kontrolna suma.

### 12.6 Bug koji vrijedi zapamtiti: timeout u tickovima

`i2s_channel_read` prima timeout u **milisekundama**. U kodu je stajalo
`pdMS_TO_TICKS(250)`, što na ticku od 100 Hz daje **25** — a drajver je to
pročitao kao 25 **ms**. Jedan DMA deskriptor traje ~64 ms, pa je svako čitanje
isticalo prije nego što bi stigao ijedan blok, i ring je ostajao prazan.

Podmuklost je bila u tome što je `dropped` i dalje bio 0 (ništa nije stizalo da
se odbaci!), a `level_dbfs` je bio −999. Sve je „izgledalo uredno".

Komentar sa mjerenjem stoji u kodu:
[`audio_i2s.c:60`](../../firmware/esp32s3_asd/main/audio_i2s.c#L60).

### 12.7 Tranzijent pri uključenju

Mikrofon i I2S se sliježu poslije uključenja. Izmjereno: prva tri bloka od 256 ms
daju RMS −4,1 / −18,0 / −35,4 dBFS uz ustaljenih −46 dBFS. To nije zvuk nego
prelazna pojava, i mijenja se od reseta do reseta pa se ne može tolerisati
pragom.

Rješenje: prva **1,0 s** se odbacuje **na izvoru**, prije ring buffera i prije
`raw_peak`. Dva razloga: kapija kvaliteta je padala na `CLIPPING` u tri od četiri
reseta, a `raw_peak` je dokaz rezerve do klipovanja — tranzijent bi tu rezervu
lažno prikazao malom.

### 12.8 NVS — trajni profil

**NVS (Non-Volatile Storage)** je ESP-IDF-ov ključ/vrijednost sistem u flešu,
otporan na gubitak napajanja. Tu se čuva naučeni profil (centar, pragovi,
metapodaci).

Format nosi **schema verziju, otisak (fingerprint) politike, generaciju i CRC32**
([`asd_profile_store.c`](../../firmware/esp32s3_asd/main/asd_profile_store.c)) — da
uređaj nikad ne učita profil koji je snimljen pod drugim pravilima.

Trenutno je politika `DEVELOPMENT`, pa je runtime **RAM-only**: namjerno ne
učitava i ne čuva profil dok pravila ne budu zamrznuta.

---

## 13. Cio lanac na jednom primjeru

Prati jedan prozor od 10 sekundi kroz sistem:

```
1.  Vazduh              zvuk ventilatora
2.  INMP441             24-bitni uzorci, 16 000 puta u sekundi
3.  I2S + DMA           32-bitni slotovi u memoriju, bez procesora
4.  capture_task        >>14 → int16, prvih 1,0 s se odbacuje, u ring buffer
5.  psd_live petlja     uzima hopove od 4096 uzoraka (256 ms)
6.  asd_psd_stream      svaki hop zatvara jedan Welch segment:
                          Hann prozor → FFT 8192 → |X|² → akumulacija
7.  Sažimanje           4097 binova → 96 logaritamskih traka (10–4000 Hz)
                          log10, pa minus skalarna sredina  →  psd_shape[96]
8.  Normalizacija       (x − mean) / std   (iz fleša, PC korpus)
9.  Mahalanobis         d² = (x − centar)ᵀ · Σ⁻¹ · (x − centar)     → SKOR
10. Kapija pouzdanosti  prozor stabilan? ne → OBSERVATION_HOLD, kraj
11. Prag                skor > thr_enter?
12. Vremensko pravilo   3 uzastopna? → ANOMALY;  12 → ANOMALY_SUSTAINED
13. Izlaz               UART telemetrija + LED
```

Vremenski budžet: **716–728 ms računa na 10 s zvuka** — rezerva oko 14×.

---

## 14. Rječnik

| Pojam | Objašnjenje u jednoj rečenici |
|---|---|
| **ASD** | Anomalous Sound Detection — detekcija anomalija zvuka mašina |
| **DCASE** | takmičenje i zajednica za detekciju i klasifikaciju akustičkih scena i događaja |
| **Aliasing** | lažne niske frekvencije kad je odabiranje presporo |
| **Bin** | jedna frekvencijska tačka FFT izlaza |
| **Curenje spektra** | razlivanje energije tona na susjedne binove zbog naglog reza prozora |
| **FFT** | brz algoritam za DFT, `O(N log N)` |
| **PSD** | Power Spectral Density — raspodjela snage po frekvenciji |
| **Welch** | metod procjene PSD-a usrednjavanjem preklapajućih periodograma |
| **STFT** | kratkovremenska Furijeova transformacija — spektar kroz vrijeme |
| **Hann** | prozorska funkcija koja glatko pada na nulu na krajevima |
| **Mel** | perceptivna skala frekvencije, standard u obradi govora |
| **Harmonik** | cjelobrojni umnožak osnovne frekvencije |
| **Mahalanobis** | udaljenost mjerena u jedinicama sopstvene varijacije podataka |
| **Kovarijansa** | matrica koja opisuje kako dimenzije variraju **zajedno** |
| **Ledoit–Wolf** | analitičko skupljanje kovarijanse ka mirnoj meti |
| **AUC** | vjerovatnoća da anomalija dobije viši skor od normalnog primjera |
| **pAUC** | AUC ograničen na mali FPR (kod nas ≤ 0,1) |
| **Domain shift** | model radi na drugom primjerku/uslovima nego što je učio |
| **First-shot** | nijedan snimak ciljne mašine nije bio dostupan za trening |
| **Data leakage** | informacija iz testa procurila u učenje → lažno dobra brojka |
| **Autoenkoder** | mreža koja uči da kopira ulaz kroz usko grlo |
| **TFLite / TFLM** | format i runtime za modele na mobilnim / mikrokontrolerskim uređajima |
| **Arena** | jedan unaprijed zauzet blok memorije koji TFLM sam raspoređuje |
| **PTQ** | kvantizacija gotovog modela, bez ponovnog treniranja |
| **int8** | 8-bitni cjelobrojni format težina i aktivacija |
| **PIE** | vektorske instrukcije ESP32-S3 koje ubrzavaju int8 račun |
| **I2S** | serijski protokol za digitalni audio (BCLK, WS, SD) |
| **DMA** | prenos podataka iz periferije u memoriju bez procesora |
| **Ring buffer** | kružni bafer koji razdvaja snimanje od obrade |
| **NVS** | ESP-IDF trajno skladište ključ/vrijednost u flešu |
| **PSRAM** | vanjska RAM memorija preko SPI-ja, veća ali sporija od internog SRAM-a |
| **Watchdog** | tajmer koji restartuje sistem ako task predugo drži procesor |
| **dBFS** | nivo u decibelima u odnosu na maksimum formata |
| **Histereza** | dva praga (ulazni i izlazni) koja sprečavaju treperenje odluke |
| **EWMA / CUSUM** | standardne tehnike detekcije pomjeraja — ovdje **mjereno i odbačeno** |
