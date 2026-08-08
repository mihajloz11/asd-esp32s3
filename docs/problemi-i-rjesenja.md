# Problemi i rješenja — baza znanja projekta

> Svaki problem na koji se naiđe ide ovdje, **i onda kad je riješen za 5 minuta**.
> Cilj: (1) da se ista greška ne rješava dvaput, (2) da poglavlje "Implementacija i
> problemi" u radu ima stvarne dokaze umjesto naknadnog prisjećanja.
>
> Format jednog unosa: **simptom → kako je nađen → uzrok → rješenje → dokaz → status**.
> Obavezno se bilježi i **šta nije radilo** (slijepe ulice), jer to je često
> vrednija informacija od konačnog rješenja.
>
> Živi dnevnik rada (šta je urađeno kog dana) je [dnevnik-projekta.md](dnevnik-projekta.md).
> Ovdje idu samo problemi.

## Indeks

| ID | Datum | Oblast | Problem | Status |
|---|---|---|---|---|
| [P1](#p1) | 19.07 | PC pipeline | DCASE 2026 klipovi su stereo, a čitani kao mono | riješeno |
| [P2](#p2) | 19.07 | build | Eval build ostaje "zalijepljen" — env var se ne re-evaluira | riješeno |
| [P3](#p3) | 06.08 | dijagnostika | Konstantan score bez mikrofona izgleda kao ispravan rad | riješeno (dijagnostički potpis) |
| [P4](#p4) | 06.08 | I2S / serijski | Task watchdog upisuje tekst usred base64 toka → pokvaren WAV | riješeno |
| [P5](#p5) | 06.08 | alat | Skript je snimio neispravan WAV bez ijedne greške | riješeno |
| [P6](#p6) | 06.08 | I2S | Rizik C1: da li je `>>14` tačan shift za INMP441 | zatvoreno, potvrđeno |
| [P7](#p7) | 06.08 | I2S | Upozorenje `dma frame num ... limited to 1023` | benigno, dokumentovano |
| [P8](#p8) | 06.08 | I2C / INA226 | Senzor se ne javlja; obje linije tvrdo na 3V3 | **otvoreno — čeka provjeru žica** |
| [P9](#p9) | 06.08 | I2C dijagnostika | Tri testa zaredom dala pogrešan zaključak | riješeno (metodološka pouka) |
| [P10](#p10) | 08.08 | kalibracija | Kalibracija uči ventilator laptopa kao normalno stanje | riješeno (čekanje da se okruženje umiri) |
| [P11](#p11) | 08.08 | detekcija | Jednostrani prag ne vidi pola stvarnih promjena | riješeno (dvostrani opseg) |

---

<a name="p1"></a>
## P1 — DCASE 2026 klipovi su stereo, a pipeline ih je čitao kao mono

**Datum:** 19.07.2026 · **Oblast:** PC pipeline / eval klipovi · **Status:** riješeno

**Simptom.** On-device score-ovi se nisu poklapali sa PC referencom iako je featuring
kod bit-identičan (isti C kod preko ctypes).

**Kako je nađen.** Poređenjem dužine i sadržaja klipova pripremljenih za flash
particiju sa originalima iz dataseta.

**Uzrok.** Klipovi DCASE 2026 su **stereo** — par mikrofona (blizu/daleko).
`prepare_eval_clips.py` ih je tretirao kao mono, pa su se kanali preplitali.

**Rješenje.** `prepare_eval_clips.py` sada eksplicitno vadi **kanal 0** u mono.

**Dokaz.** Poslije ispravke: max relativna razlika score-a uređaj vs PC = **1.5e-04**
na 16 klipova (7× ispod praga tolerancije).

**Pouka.** Ne pretpostavljati broj kanala iz imena dataseta — provjeriti u zaglavlju
WAV-a. Ovo je bio jedini razlog neslaganja; featuring lanac je od početka bio ispravan.

---

<a name="p2"></a>
## P2 — Eval build ostaje "zalijepljen": promjena env varijable ne prekonfiguriše CMake

**Datum:** 19.07.2026, ponovo potvrđeno 06.08 · **Oblast:** build sistem · **Status:** riješeno

**Simptom.** Poslije eval sesije, običan `idf.py build` i dalje pravi binarku koja
pri svakom bootu ulazi u eval mod (čita klipove sa flash particije, nikad ne dira
mikrofon) — iako `ASD_EVAL_MODE` više nije postavljen u shell-u.

**Kako je nađen (06.08).** Prije flešovanja, provjerom stvarnih compile flagova:

```bash
grep -n "ASD_EVAL_MODE" build/compile_commands.json | head -3
```

Izlaz je sadržao `-DASD_EVAL_MODE` iako varijabla nije bila postavljena.

**Uzrok.** U `main/CMakeLists.txt` mod se bira sa `if(DEFINED ENV{ASD_EVAL_MODE})`.
To se evaluira **samo u fazi konfiguracije**. Ninja ne zna da je env varijabla
nestala, pa ne pokreće ponovnu konfiguraciju — build ostaje na starom izboru.

**Rješenje.** Poslije svake promjene moda obavezno:

```bash
idf.py reconfigure
```

pa tek onda `build`. Isto važi i za `ASD_MIC_TEST`.

**Šta nije radilo.** Samo `idf.py build` — tiho zadrži stari mod, bez ijednog
upozorenja. Ovo je najopasnija vrsta greške: build prođe, flash prođe, a ploča
radi nešto treće.

**Pouka.** Kad postoje build modovi preko env varijabli, **verifikovati stvarne
flagove**, ne pamćenje o tome šta je zadnje buildovano.

---

<a name="p3"></a>
## P3 — Konstantan score bez mikrofona izgleda kao potpuno ispravan rad

**Datum:** 06.08.2026 · **Oblast:** dijagnostika · **Status:** riješeno (postao dijagnostički alat)

**Simptom.** Prvi živi build na ploči bez spojenog mikrofona daje uvjerljiv izlaz:

```
score=690.88586 thr=0.77863 ANOMALIJA | feat=663 ms inf=1055 ms total=10049 ms (307 vec) dropped=0
```

Sve izgleda zdravo — nema dropova, vrijeme se poklapa, klasifikacija radi.

**Uzrok.** Bez mikrofona I2S vraća konstantu. Log-mel od konstante ide na `eps`
pod (`1e-12`), standardizacija to pretvori u fiksni vektor, AE da fiksnu grešku
rekonstrukcije. Rezultat: savršeno stabilan, potpuno besmislen broj.

**Rješenje.** Ne rješava se — **koristi se**. `690.88586` je otisak mrtvog ulaza
na ovoj konfiguraciji modela. Ako se taj broj pojavi sa spojenim mikrofonom,
problem je u audio lancu, a ne u modelu.

**Pouka.** Score koji se ne mijenja **uopšte** (na 5 decimala, klip za klipom)
nije stabilnost nego mrtav ulaz. Zato mic-test mod ne gleda score nego sirovu
statistiku signala.

---

<a name="p4"></a>
## P4 — Task watchdog upisuje svoj tekst usred base64 toka

**Datum:** 06.08.2026 · **Oblast:** I2S bring-up / serijski prenos · **Status:** riješeno

**Simptom.** Snimak od 5 s (80 000 uzoraka) stiže na PC kao **80 718** uzoraka.
Statistika se ne poklapa ni blizu:

| | ploča | PC (dekodovano) |
|---|---|---|
| peak | 5436 | 32768 |
| rms | 78.8 | 11787.4 |

Dekodovani WAV zvuči kao jak šum — lako se pogrešno protumači kao loš mikrofon
ili loš lem.

**Kako je nađen.** Prva verzija skripta je samo prijavila neslaganje dužine.
Tek kad je dodata **stroga validacija linija** (svaka linija dumpa mora biti
tačno 76 znakova iz base64 abecede), odbačene linije su otkrile krivca:

```
odbaceno 21 linija koje nisu base64 (prve 3):
  b'8/8IE (19796) task_wdt: Task watchdog got triggered. The following tasks/users did not reset the wat'
  b'E (19796) task_wdt:  - IDLE0 (CPU 0)'
```

**Uzrok.** Dump traje **~19 s** na 115200 bauda (160 KB → 213 KB base64).
Petlja je ispisivala bez ijednog `vTaskDelay`, pa `IDLE0` na jezgru 0 nije dobijao
procesor. Task watchdog se javio i ESP_LOG ga je ispisao **na isti UART, usred
podataka**. Base64 se dekodira u grupama po 4 znaka — svaki višak znaka pomjeri
sve poslije sebe. Zato prvih par stotina milisekundi zvuka bude ispravno, a
ostatak smeće.

**Rješenje.** Ustupanje procesora tokom dumpa, `main/mic_test.c`:

```c
if (++lines % 16 == 0) vTaskDelay(1);
```

Plus, na strani ploče, FNV-1a kontrolna suma preko svih bajtova u `MICWAV_BEGIN`
zaglavlju, koju PC provjerava prije snimanja WAV-a.

**Dokaz poslije ispravke.**

```
dekodovano 160000 B (ocekivano 160000)
kontrolna suma OK (b9ed28b9)
uzoraka=80000  peak=1020  rms=158.7  dc=-0.4      <- identično sa pločom
```

**Pouka.** Kad se podaci i logovi dijele istim UART-om, dugotrajan ispis je
**neizbježno** izložen ubacivanju teksta iz drugih izvora (WDT, panic handler,
drajveri). Binarni prenos preko konzole mora imati i okvir i kontrolnu sumu —
ili ide potpuno odvojenim kanalom.

---

<a name="p5"></a>
## P5 — Skript je snimio neispravan WAV bez ijedne greške

**Datum:** 06.08.2026 · **Oblast:** alat (`pc/tools/mic_capture.py`) · **Status:** riješeno

**Simptom.** Prva verzija skripta je, uprkos oštećenom toku iz [P4](#p4), uredno
napisala `results/mic_test.wav` i ispisala samo blago `UPOZORENJE: ocekivano
80000 uzoraka, dekodovano 80718`. Fajl se otvara, ima 5 s zvuka, izgleda upotrebljivo.

**Uzrok.** `base64.b64decode` u podrazumijevanom režimu **tiho ignoriše** znakove
van base64 abecede. Smeće ubačeno u tok se ne prijavi kao greška — samo pomjeri
sve iza sebe. Skript je zatim snimio taj rezultat jer nije imao pravilo da
neuspjela provjera znači *ne piši izlaz*.

**Rješenje.** `mic_capture.py` sada:
1. reže linije ručno iz bajt-toka (`readline()` sa timeoutom zna vratiti pola linije);
2. prihvata samo linije koje tačno odgovaraju base64 obrascu, ostale prijavljuje;
3. provjerava dužinu **i** FNV-1a sumu sa ploče;
4. **ne snima WAV** ako bilo koja provjera padne, nego izlazi sa greškom.

**Pouka.** Alat koji provjerava ispravnost, pa svejedno napiše izlaz, je gori od
alata koji ne provjerava ništa — jer daje lažno povjerenje u podatke.
Neispravan snimak zvuka izgleda kao realan zvuk.

---

<a name="p6"></a>
## P6 — Rizik C1 zatvoren: `>>14` je tačan shift za INMP441

**Datum:** 06.08.2026 · **Oblast:** I2S · **Status:** zatvoreno, potvrđeno mjerenjem

**Pitanje.** `audio_i2s.c` pretvara 32-bitni I2S slot u 16-bitni PCM sa `raw[i] >> 14`.
Vrijednost je bila odabrana iz datasheeta i nikad provjerena na živom signalu
(rizik C1 u planu). Prejak shift baca bite, preslab klipuje.

**Kako je mjereno.** U `audio_i2s.c` dodato praćenje peaka **sirovog 32-bitnog**
uzorka prije shifta (`audio_raw_peak()`), pa se poredi sa 16-bitnim izlazom.

**Rezultat kroz tri snimka u istoj sobi:**

| sirovi 32-bit peak | zauzeto bita | 16-bit peak poslije `>>14` | dBFS |
|---|---|---|---|
| 89 064 960 | 27 / 31 | 5436 | −15.6 |
| 54 037 376 | 26 / 31 | 3298 | −19.9 |
| 16 724 480 | 24 / 31 | 1020 | −30.1 |

**Zaključak.** Aritmetika je tačna (89 064 960 >> 14 = 5436 ✓). `clipped=0` u svim
snimcima. Najglasniji zabilježen događaj (kucanje prstom po mikrofonu) ostavlja
**15.6 dB rezerve** do klipovanja — izvor bi morao biti ~6× glasniji da zasiječe.
`>>14` ostaje.

**Napomena za rad.** `>>16` bi mapirao puni opseg mikrofona (120 dBSPL AOP) na
pun int16 bez ikakvog rizika od klipovanja, ali bi žrtvovao 12 dB rezolucije na
tihim mašinskim zvucima, koji su ovdje tipičan slučaj. Izbor je svjestan
kompromis u korist rezolucije, a ne podrazumijevana vrijednost.

---

<a name="p7"></a>
## P7 — `i2s_common: dma frame num is out of dma buffer size, limited to 1023`

**Datum:** 06.08.2026 · **Oblast:** I2S drajver · **Status:** benigno, dokumentovano

**Simptom.** Pri svakom `audio_i2s_init()` drajver ispiše upozorenje.

**Uzrok.** `DMA_FRAME_NUM` je 1024, a maksimalna veličina jednog DMA deskriptora
za dati format slota staje u 1023 frejma. Drajver sam skraćuje na 1023.

**Zašto se ne dira.** Posljedica je zanemarljiva (1 frejm po deskriptoru, 4
deskriptora), a `dropped=0` je potvrđen i u eval modu i u živom radu i u mic testu.
Mijenjanje na 1023 bi uklonilo upozorenje ali promijenilo tajminge koji su već
validirani u E4 mjerenjima.

**Status.** Ostaje kako jeste. Zabilježeno da se ne bi ponovo istraživalo.

---

<a name="p8"></a>
## P8 — INA226 se ne javlja: obje I2C linije su tvrdo vezane na 3V3

**Datum:** 06.08.2026 · **Oblast:** I2C bring-up · **Status:** OTVORENO — čeka provjeru žica

**Simptom.** Poslije spajanja INA226 sa 4 žice (VCC, GND, SDA→GPIO 8, SCL→GPIO 9),
skener ne nalazi nijedan uređaj ni na jednoj od 112 adresa. Drajver za svaku
adresu javlja `probe device timeout`, a ne NACK.

**Dijagnostički put** (redom, jer je svaki korak odbacio jednu hipotezu):

| # | Test | Rezultat | Zaključak |
|---|---|---|---|
| 1 | Nivo linija bez internog pull-upa | SDA=1, SCL=1 | *pogrešno protumačeno:* "pull-up postoji, modul napojen" |
| 2 | Skeniranje sa zamijenjenim SDA/SCL | ništa | nije zamjena žica |
| 3 | Obaranje linije, pa mjerenje oporavka | vraća se na 1 odmah | *pogrešno protumačeno:* "pull-up potvrđen" |
| 4 | Kratak spoj između linija | jedna na 0, druga ostaje 1 | *pogrešno protumačeno:* "linije odvojene" |
| 5 | **Bit-bang self-check (open-drain)** | **SDA low=0, SCL low=0** | **master ne može oboriti nijednu liniju** |

**Uzrok (utvrđen).** Open-drain izlaz može samo da *spusti* liniju; protiv tvrde
veze na 3,3 V je nemoćan. Pošto master ne uspijeva da obori ni SDA ni SCL, obje
linije nisu na senzorovim SDA/SCL pinovima nego **na napajanju**.

To retroaktivno objašnjava i sve ranije nalaze: "pull-up" iz testova 1 i 3 nije
pull-up nego kratka veza na 3V3, a test 4 nije mogao ništa pokazati jer nijedna
linija nije mogla biti oborena.

**Zašto timeout, a ne NACK.** Master čeka da linija ode nisko u fazi potvrde;
kako je prikovana na 3,3 V, konačni automat nikad ne završi transakciju i istekne
vrijeme. NACK bi značio "bus radi, ali na toj adresi nema nikoga" — što bi bila
sasvim druga dijagnoza.

**Bisekcija — mjerenja redom.**

| Stanje | GPIO 8 / 9 | Zaključak |
|---|---|---|
| sve spojeno | tvrdo na 3V3, master ne obara | bus mrtav |
| signalne žice skinute sa **S3** | plutaju, master ih obara, skener gotov za 30 ms (umjesto 5,6 s) | **pinovi ploče su ispravni** |
| žice vraćene | opet tvrdo na 3V3 | kvar je na drugom kraju |
| VCC skinut sa modula | i dalje tvrdo na 3V3 | *(mjerenje sumnjivo — vjerovatno nije skinuta prava žica)* |
| **sve 4 žice skinute sa modula** | **slobodni** | **napon je stizao kroz modul** |

**Mapa svih pinova.** Skeniranje svih slobodnih GPIO-a (interni pull-down, pa
open-drain obaranje) dalo je: samo GPIO 8 i 9 spolja visoki, oba tvrdo; **nigdje
nijedan pin sa 10 kΩ pull-upom**. Da SDA/SCL modula stižu do bilo kog pina, taj
pin bi se morao pojaviti kao pull-up jer modul ima otpornike od 10 kΩ.
*(GPIO 0 se javlja kao pull-up — to je BOOT taster na ploči, ne naša žica.
Prvo skeniranje je propustilo strapping pinove 0/45/46; dodati su i oni su slobodni.)*

**Uzrok (utvrđen eliminacijom).** SDA i SCL su na modulu nisko-omski vezani na
VCC. Fotografija potvrđuje da su pull-upovi 10 kΩ (oznaka `103`), što ne može
držati liniju gore protiv izlaza ploče — dakle veza je skoro nulta, a jedini
izvor 3,3 V na modulu je VCC pin.

Pinout modula sa fotke (bitno — **obrnut** od onog u `lemljenje-kratko.md`):
`VCC · GND · SDA · SCL · ALE · UBS · IN− · IN+`. Žice: narandžasta→VCC,
tirkizna→GND, žuta→SDA, lila→SCL.

**Preostalo za potvrdu.** Otpor VCC↔SDA i VCC↔SCL na modulu: 10 kΩ = modul
ispravan (pa je greška negdje drugdje), ~0 Ω = most preko pull-up otpornika ili
oštećen čip.

**Bezbjednosna napomena.** Ranija verzija testa je obarala linije u **push-pull**
režimu. Na liniji vezanoj na 3V3 to je kratak spoj 3V3→GND kroz GPIO (kratko,
strujno ograničeno na ~40 mA, bez očekivane štete). Ispravljeno: sve obaranje
linija ide isključivo open-drain, gdje neuspjeh znači samo da linija ostane visoka.

---

<a name="p9"></a>
## P9 — Tri dijagnostička testa zaredom dala pogrešan zaključak

**Datum:** 06.08.2026 · **Oblast:** metodologija · **Status:** riješeno (pouka)

**Šta se desilo.** U dijagnostici [P8](#p8), testovi 1, 3 i 4 su dali naizgled
jasne odgovore — "pull-up postoji", "modul je napojen", "linije su odvojene" —
i sva tri su bila **pogrešna**. Vodili su ka hipotezama (zamijenjene žice,
kalajni most) koje su potrošile tri ciklusa build→flash→mjerenje.

**Uzrok.** Sva tri testa su pretpostavljala da master **može** da upravlja
linijom. Nijedan to nije prvo provjerio. Kad je ta pretpostavka pala, svi
izvedeni zaključci su pali s njom — a da to nigdje nije bilo vidljivo, jer su
testovi ispisivali samopouzdane poruke bez ograde.

**Pouka.** Dijagnostika ide **od najniže pretpostavke naviše**: prvo "mogu li
uopšte da upravljam pinom", pa tek onda "šta je na drugom kraju". Bit-bang
self-check je sada prvi korak u `ina226_test.c`, prije bilo kakvog skeniranja.

**Druga pouka.** Test koji ispisuje kategoričan zaključak ("PULL-UP POSTOJI")
umjesto sirovog mjerenja aktivno šteti — čita se kao utvrđena činjenica i
usmjerava sljedeći sat rada u pogrešnom pravcu.

---

<a name="p10"></a>
## P10 — Kalibracija uči ventilator laptopa kao „normalno stanje"

**Datum:** 08.08.2026 · **Oblast:** on-device kalibracija · **Status:** riješeno

**Simptom.** Tri uzastopna pokušaja demoa nisu opalila. Svaki put ista slika:
kalibracija izmjeri sredinu 68–74 i postavi prag oko 78–105, a nekoliko minuta
kasnije pozadina padne na 12–27 i ništa više ne može da dosegne prag.

**Kako je nađen.** Ispisom kalibracionih prozora redom, umjesto samo sredine:

```
29.9  42.5  44.8  53.0  63.9  63.0  35.1  68.2  76.7  76.1 ... 77.2  76.8
```

Kalibracija **ne počinje od tišine** — penje se sa 30 na 77 u prvih 18 s i tu
ostaje. Detekcija poslije toga pada na 12.

**Uzrok.** Kalibracija je kretala odmah po bootu, a boot se dešava tačno u
trenutku kad je ploča fleširana ili je pokrenut alat na računaru. Ventilator
laptopa se do tada zavrtio i radi kroz cijelu kalibraciju. Uređaj tako nauči
buku ventilatora kao normalno stanje, a ventilator se poslije minut-dva umiri.

**Rješenje.** `live_adapt.c` prije kalibracije čeka da se okruženje umiri:
najmanje 120 s **i** da se zadnjih 5 prozora razlikuju manje od 15 % relativno.
Tek onda kreće mjerenje normalnog stanja.

**Dokaz.** Prva kalibracija poslije izmjene: 30 prozora u opsegu 61,2–78,5,
sredina 73,1 — stabilno kroz cijeli minut, bez rasta.

**Pouka.** Kad se sistem kalibriše sam, mora se pitati **šta je radilo baš u tom
trenutku**. Alat koji pokreće mjerenje je i sam izvor smetnje.

---

<a name="p11"></a>
## P11 — Jednostrani prag ne vidi pola stvarnih promjena u okruženju

**Datum:** 08.08.2026 · **Oblast:** detekcija · **Status:** riješeno

**Simptom.** Poslije ispravne kalibracije (pozadina 69–77, prag 74,05) pušten je
glasan test zvuk. Detekcija nije prijavila ništa — a score se **jasno promijenio**:

```
73.2  72.8  73.2  73.7  73.5  73.1   <- tisina
56.8  50.8  48.1  50.4  52.6  60.6   <- zvuk krenuo
```

Score je **pao sa 73 na 48**, umjesto da poraste.

**Uzrok.** Greška rekonstrukcije je udaljenost od naučene raspodjele, a ne mjera
jačine zvuka. Model je treniran na zvuku mašine u pogonu, pa mu je tiha soba
*daleka* i daje visok score. Glasan zvuk ulaz približava onome što je model
vidio na treningu, i greška padne.

Prag je bio jednostran (`score > granica` = anomalija), pa je propuštao svaku
promjenu koja pomjera score naniže — a to je, ispostavlja se, polovina slučajeva.

**Rješenje.** Dvostrani opseg: uređaj računa i donju (1. percentil) i gornju
(99. percentil) granicu normalnog rada, a anomalija je izlazak iz opsega u bilo
kom smjeru. Ispis razlikuje `ANOMALIJA(iznad)` od `ANOMALIJA(ispod)`.

**Dokaz — pun ciklus, izmjereno 08.08:**

| Faza | Score | Odluka |
|---|---|---|
| tišina (17 prozora) | 69,0 – 76,7 | normal |
| test zvuk (23 prozora) | **45,2 – 64,8** | **ANOMALIJA (ispod)** |
| poslije zvuka (14 prozora) | 66,9 – 71,6 | normal |

Normalan opseg: **63,16 – 83,78**. Ukupno 20 od 54 prozora označeno kao
anomalija, a prelazi se poklapaju sa početkom i krajem reprodukcije u sekundu.

**Pouka za rad.** Pretpostavka „anomalija = veća greška" ne važi kad se model
raspoređuje u okruženje koje se razlikuje od trening domena. Prag mora biti
dvostran, ili se referentno stanje mora poklapati sa domenom treninga.

---

## Slijepe ulice i odbačene ideje

| Ideja | Zašto je odbačena |
|---|---|
| Snimak preko FAT particije + `parttool` + `fatfsparse.py` | Čita se cijela particija od 20 MB preko serijskog (~7 min) da bi se izvukao fajl od 160 KB. Base64 preko konzole je 20× brži. |
| Podizanje brzine konzole na 921600 radi bržeg dumpa | Mijenja `sdkconfig` za sve modove i rizikuje da postojeći eval tok (već validiran) prestane raditi. 19 s dumpa nije usko grlo. |
| Oslanjanje na score iz živog rada kao provjeru mikrofona | Vidi [P3](#p3) — konstantan score izgleda ispravno. Bring-up mora gledati sirovu statistiku signala. |
