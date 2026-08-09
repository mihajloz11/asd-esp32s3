# Plan: otpornost na buku okoline

> Problem: uređaj treba da razlikuje **prolazan zvuk u prostoriji** (koraci,
> razgovor, zalupljena vrata, saobraćaj) od **trajne promjene na mašini** koja
> je stvarna anomalija. Prvo je smetnja, drugo je alarm.
>
> Status: dio je već ugrađen i izmjeren, ostalo je predlog sa procjenom koristi.
> Ništa iz odjeljka „Predlozi" još **nije** implementirano ni izmjereno.

## Šta već postoji i koliko vrijedi (izmjereno)

### Pravilo od N uzastopnih prozora

Alarm se javlja tek kad **3 uzastopna prozora** od po 10 s pređu prag, dakle
odstupanje mora trajati **30 s**. Ljudski zvuci traju sekundama; kvar ne prolazi.

Izmjereno u živim prolazima ([hardver-verifikacija.md](hardver-verifikacija.md)):

| Postavka | Ishod |
|---|---|
| 2 uzastopna prozora (prolaz 2) | spoljni zvuk dao score 42 021 i 70 590 → **lažni alarmi** |
| 3 uzastopna prozora (prolazi 3–5) | prozor sa 1104 pri pragu 1052 **progutan**, 0 lažnih alarma u 17 normalnih prozora |

Zaključak: pravilo radi i najjeftinija je odbrana koju imamo.

### Usrednjavanje unutar prozora

Score je Welch prosjek preko 38 preklapajućih segmenata u 10 s. Dvosekundni
događaj time već biva razblažen. To je posljedica front-enda, ne posebna mjera.

---

## Predlozi, poređani po odnosu korist/trud

### 1. Provjera stalnosti unutar prozora  *(preporučeno prvo)*

**Ideja.** Mašina zvuči isto iz sekunde u sekundu — to joj je priroda. Prolazan
događaj u prostoriji nije stalan. Podijeliti 10 s na ~5 pod-segmenata, izračunati
spektar svakog i izmjeriti koliko se međusobno razlikuju. Velika razlika
**unutar** prozora znači da se nešto desilo u sobi, a ne da se mašina promijenila
→ prozor se preskače (ne ulazi ni u alarm ni u kalibraciju).

**Zašto baš ovo prvo.** Fizički je ispravno, ne traži novi hardver, i hvata
upravo ono što pravilo od 3 prozora propušta: događaj koji traje dovoljno dugo
da pokrije prozor ali nije trajan.

**Cijena na ploči.** Zanemarljiva — segmentni spektri se ionako računaju u
Welch petlji; treba ih samo zadržati i uporediti umjesto odmah usrednjiti.
Dodatna memorija ~5 × 96 float = 1,9 KB.

**Pažnja.** Postoji ranije mjerenje da pod-segmentna agregacija **ne pomaže
detekciji** (0,504–0,544, vidi [put-do-modela.md](put-do-modela.md) #18). To je
druga stvar: tamo se pod-segment koristio da se anomalija **nađe**, ovdje da se
prolazan događaj **odbaci**. Ne treba ih pomiješati.

### 2. Robusnija agregacija po trakama

**Ideja.** Score je zbir odstupanja preko svih 96 traka. Govor jako pogodi
nekoliko traka; kvar tipično pomjera mnogo traka pomalo. Ako se prije sabiranja
odbaci nekoliko najvećih odstupanja (trimovani zbir), govor gubi uticaj a kvar
preživi.

**Cijena.** Jedno sortiranje 96 brojeva po prozoru. Zanemarljivo.

**Pažnja.** Ranije je mjereno **suprotno** — zadržavanje samo najvećih odstupanja
(„top-k") dalo je 0,645 naspram 0,674, dakle malo lošije za detekciju. To
posredno potkrepljuje ideju: ako najveća odstupanja nisu ono što nosi kvar, onda
se smiju odbaciti. Ali treba izmjeriti koliko se detekcija gubi.

### 3. Pravilo „N od M" umjesto N uzastopnih

**Ideja.** Traži npr. 5 od 8 prozora iznad praga umjesto 3 uzastopna. Otpornije
je na to da jedan prozor slučajno padne ispod praga — što se već desilo: u
prolazu 5 je niz pukao na 702,3 pri pragu 707,9, dakle za 6 jedinica.

**Cijena.** Kružni bafer od 8 bita.

### 4. Dva mikrofona  *(pravo rješenje, podaci već postoje)*

**Ideja.** Jedan mikrofon uz mašinu, drugi okrenut prostoriji. Što **oba** čuju
je soba; što čuje **samo bliži** je mašina. Oduzimanjem se buka poništava.

**Zašto je ovo ozbiljno.** To je i razlog zašto je DCASE 2026 „noise-aware"
izdanje, a **snimci su dvokanalni** — i cijela naša obrada koristi samo prvi
kanal (`features.py`, `y[:, 0]`). Drugi kanal stoji neiskorišćen, pa se pristup
može isprobati **odmah, bez ijednog novog dijela**.

Izmjereno na 8 klipova ventilatora:

| | kanal 0 naspram kanala 1 |
|---|---|
| razlika nivoa | −2,8 dB |
| korelacija | 0,873 |
| po opsezima | −2,7 dB (10–100 Hz), −4,2 dB (100–1500 Hz), −1,9 dB (1,5–4 kHz) |

**Iskreno ograničenje:** kanali su prilično slični (korelacija 0,87), dakle
drugi mikrofon nije daleko od mašine. Na ovim podacima se puna korist neće
vidjeti. Princip ipak stoji i vrijedi ga izmjeriti.

**Na ploči.** Drugi INMP441 ide na **isti** I2S bus; pin L/R se veže suprotno,
pa jedan mikrofon puni lijevi a drugi desni kanal istog okvira. Bez novih
pinova. Traži izmjenu u `audio_i2s.c` (čitanje oba slota umjesto jednog) i
provjeru da DMA baferi stanu.

---

## Šta NE raditi

**Ne učiti buku kao dio normalnog stanja.** Zvuči logično — „nauči i korake pa
ih neće prijavljivati" — ali otvara rupu koja nas je već koštala
([P10](problemi-i-rjesenja.md#p10)): ako uređaj uči šta je normalno dok mašina
već ima kvar, naučiće kvar kao normalu i nikad neće alarmirati. Kalibracija
mora ostati svjesno pokrenuta i samo na potvrđeno ispravnoj mašini.

---

## Eksperiment koji ovo mjeri

Da se ne bi biralo po osjećaju, mjerenje je jednostavno i ne traži prisustvo:

1. Uzeti target normalne klipove ventilatora (ispravan rad).
2. Umiješati **govor i korake** u nekoliko jačina (npr. −20, −12, −6 dB u
   odnosu na RMS mašine). Izvor: bilo koji snimak govora; koraci se mogu i
   sintetizovati kao niz udara, uz provjeru spektra prije upotrebe
   ([P14](problemi-i-rjesenja.md#p14) — sintetički pobuđivač se **mora**
   izmjeriti u spektru).
3. Za svaku zaštitu izmjeriti dvije brojke:
   - **lažni alarmi** na normalnom radu sa umiješanom bukom,
   - **gubitak detekcije** na stvarnim anomalijama (da zaštita ne ubije korist).

Očekivani izlaz je tabela oblika:

| Zaštita | Lažnih alarma sa bukom | Detekcija anomalije |
|---|---|---|
| sadašnje stanje (3 uzastopna) | *mjeriti* | *mjeriti* |
| + stalnost unutar prozora | | |
| + trimovani zbir po trakama | | |
| + N od M | | |
| dva kanala (kanal 0 − kanal 1) | | |

Bez te tabele svaka od gornjih mjera je samo razumna pretpostavka.

**Procjena:** nekoliko sati računanja na PC-u, bez hardvera. Tek ono što se
pokaže vrijednim ide u firmware.

---

## Redoslijed

1. Eksperiment gore — daje tabelu i odlučuje šta uopšte vrijedi ugraditi.
2. Ugraditi ono što je prošlo, po redu: stalnost unutar prozora → N od M →
   trimovani zbir.
3. Dva kanala samo ako eksperiment pokaže korist na dvokanalnim snimcima; to je
   najveći zahvat (hardver + `audio_i2s.c`).
4. Ponoviti živi test sa puštenom bukom u prostoriji i uporediti sa tabelom.
