# Plan: otpornost na buku okoline

> Problem: uređaj treba da razlikuje **prolazan zvuk u prostoriji** (koraci,
> razgovor, zalupljena vrata, saobraćaj) od **trajne promjene na mašini** koja
> je stvarna anomalija. Prvo je smetnja, drugo je alarm.
>
> Status: temporalna politika je zaključana na **sintetičkim score-pobudama**,
> a dual-channel kandidati su ispitani i nisu usvojeni. Kontrolisani akustički
> testovi govora, koraka i vrata nisu izvedeni i ostaju dio fizičkog protokola.
> Ostali odjeljci su istorijski prijedlozi, ne tvrdnje o završenoj validaciji.

## Šta već postoji i koliko vrijedi (izmjereno)

### Pravilo od N uzastopnih prozora

Alarm se javlja tek kad **3 uzastopna prozora** od po 10 s pređu prag, dakle
score mora ostati iznad praga oko **30 s**. To samo po sebi ne dokazuje kako
stvarni ljudski zvuk, vrata ili druga smetnja utiču na feature i score.

Izmjereno u živim prolazima ([hardver-verifikacija.md](hardver-verifikacija.md)):

| Postavka | Ishod |
|---|---|
| 2 uzastopna prozora (prolaz 2) | spoljni zvuk dao score 42 021 i 70 590 → **lažni alarmi** |
| 3 uzastopna prozora (prolazi 3–5) | prozor sa 1104 pri pragu 1052 **progutan**, 0 lažnih alarma u 17 normalnih prozora |

Zaključak: pravilo odbacuje izolovan score-prozor i najjeftinija je odbrana
koju imamo. Akustička otpornost se potvrđuje tek kontrolisanim fizičkim testom.

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

**Rizik koji se mora izmjeriti.** Kvar ne mora početi postepeno — zaglavljena
lopatica počinje **naglo**, i baš taj prvi prozor izgleda „nestabilno". Kapija
bi ga mogla odbaciti. Zato mjerenje mora obuhvatiti i **kašnjenje detekcije**,
ne samo broj lažnih alarma; ako kapija odbacuje prvi prozor kvara, treba je
vezati samo za prozore koji se **ne ponavljaju** (nestabilan pa se vrati u
normalu), a ne za one poslije kojih stanje ostaje promijenjeno.

### 2. Robusnija agregacija po trakama

**Ideja.** Govor jako pogodi nekoliko traka; kvar tipično pomjera mnogo traka
pomalo. Ako se doprinos najjače pogođenih traka ograniči, govor gubi uticaj a
kvar preživi.

> **Ispravka ranije verzije ovog plana (09.08.2026).** Prvo je pisalo „odbaci
> pet najvećih odstupanja prije sabiranja". **To je matematički neispravno za
> ovaj score.** Mahalanobisov score nije zbir po trakama nego kvadratna forma
> `dᵀ P d` sa **punom** matricom `P` (96×96). Ne postoji „doprinos trake *i*"
> koji bi se prosto izbacio — postoje unakrsni članovi između traka, i baš oni
> nose signal (izmjereno: dijagonalna kovarijansa gubi 8 poena, vidi
> [put-do-modela.md](put-do-modela.md) #6). Nalaz iz vanjske revizije, tačan.

**Kako se to radi ispravno** — tri varijante koje treba izmjeriti, sve zadržavaju
punu matricu:

1. **Ograničiti odstupanje prije forme.** Vinsorizovati vektor `d` po
   koordinatama (`clip` na ±c·σ iz kalibracije), pa tek onda `dᵀ P d`. Time se
   traka koju je govor „zabio" ograničava, a struktura matrice ostaje.
2. **Odbaciti trake, ali dosljedno.** Izbaciti podskup traka *i iz vektora i iz
   matrice* (uzeti podmatricu `P` nad preostalim trakama — nije isto što i
   nuliranje koordinate). Ako se podskup bira **fiksno unaprijed** (npr. trake
   u kojima ventilator ima malo energije), to je legitimno i može se
   pripremiti na PC-u; ako se bira po prozoru, mijenja se raspodjela score-a
   pa i prag.
3. **Robusna udaljenost.** Zamijeniti kvadratnu formu njenim „blažim" oblikom
   (npr. Huber nad izbijeljenim koordinatama `L d`, gdje je `P = LᵀL`). Tu
   pojedina velika koordinata ne dominira, a matrica se i dalje koristi cijela.

**Cijena.** Varijanta 1 je trivijalna (jedno ograničavanje po prozoru).
Varijanta 2 traži pripremljenu podmatricu u flešu. Varijanta 3 traži izbjeljivanje
`L d` (isto množenje kao sada) pa nelinearnost — takođe jeftino.

**Pažnja.** Ranije je mjereno da zadržavanje samo najvećih odstupanja („top-k")
daje 0,645 naspram 0,674 — dakle najveća odstupanja nisu ono što nosi kvar. To
ide u prilog ograničavanju, ali detekciju treba ponovo izmjeriti za svaku od tri
varijante gore.

### 3. Pravilo „N od M" umjesto N uzastopnih

**Ideja.** Traži npr. 5 od 8 prozora iznad praga umjesto 3 uzastopna. Otpornije
je na to da jedan prozor slučajno padne ispod praga — što se već desilo: u
prolazu 5 je niz pukao na 702,3 pri pragu 707,9, dakle za 6 jedinica.

**Cijena.** Kružni bafer od 8 bita.

### 4. Dva mikrofona  *(pravo rješenje, podaci već postoje)*

**Ideja.** Jedan mikrofon uz mašinu, drugi okrenut prostoriji. Što **oba** čuju
je soba; što čuje **samo bliži** je mašina.

> **Ne prosto oduzimanje.** `kanal0 − kanal1` u vremenskom domenu poništava i
> sam ventilator, jer ga oba mikrofona čuju (izmjerena korelacija 0,873). Dva
> mikrofona nisu „ukloni buku" nego „imaš dvije mjere pa vidi šta se razlikuje".
> Nalaz iz vanjske revizije, tačan.

**Šta zapravo treba isprobati** (redom, od najjeftinijeg):

1. samo kanal 0 (sadašnje stanje) — osnova za poređenje,
2. samo kanal 1,
3. prosjek kanala (bolji odnos signal/šum ako je buka nekorelisana),
4. **odnos spektara** kanal0/kanal1 po traci — buka koja dolazi izdaleka pogađa
   oba slično pa se u odnosu poništi, dok mašina diže odnos u svojim trakama,
5. kalibrisani rezidual: naučiti na ispravnom radu kako se kanali odnose, pa
   mjeriti odstupanje **od tog odnosa**.

Varijanta 4 je vjerovatno najbolji odnos koristi i truda i uklapa se u postojeći
front-end (radi se nad istim 96 traka).

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
