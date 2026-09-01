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
| [P8](#p8) | 06.08 | I2C / INA226 | Senzor se ne javlja; obje linije tvrdo na 3V3 | riješeno (pogrešno spojen GND) |
| [P9](#p9) | 06.08 | I2C dijagnostika | Tri testa zaredom dala pogrešan zaključak | riješeno (metodološka pouka) |
| [P10](#p10) | 08.08 | kalibracija | Kalibracija uči ventilator laptopa kao normalno stanje | riješeno (čekanje da se okruženje umiri) |
| [P11](#p11) | 08.08 | detekcija | Jednostrani prag ne vidi pola stvarnih promjena | riješeno (dvostrani opseg) |
| [P12](#p12) | 09.08 | PC alati | Windows kodna stranica ruši BHS Unicode statusni ispis | riješeno (ASCII status) |
| [P13](#p13) | 09.08 | živi demo | Spojeni DCASE klipovi prave lažnu anomaliju na šavu | riješeno (jedna brzina) |
| [P14](#p14) | 09.08 | eksperiment | Sintetički kvar je bio bas koji zvučnik ne reprodukuje | riješeno |
| [P15](#p15) | 11.08 | I2S / fail-closed | Tranzijent pri uključenju mikrofona ruši prolaz u prvom bloku | riješeno (odbacivanje 1,0 s na izvoru) |
| [P16](#p16) | 11.08 | akustički put | Mikrofon ne čuje zvučnik iako audio stiže na izlaz | riješeno (mikrofon #1 mrtav, zamijenjen) |
| [P17](#p17) | 14.08 | kalibracija / prag | Prag se između dvije kalibracije razlikuje 16× | **otvoreno** |
| [P18](#p18) | 14.08 | vremenska odluka | EWMA i CUSUM propuštaju baš onu buku koju je trebalo da filtriraju | riješeno (odbačeni mjerenjem) |
| [P19](#p19) | 14.08 | mjerenje | Sopstveno računanje na laptopu kontaminiralo probu lažnih alarma | riješeno (metodološka pouka) |
| [P20](#p20) | 22.08 | UART / protokol | FLAGS iz drugog taska upada usred FEATURE96 reda | riješeno u kodu, **nije fizički potvrđeno** |
| [P21](#p21) | 22.08 | operaterski tok | Run traži 20 potvrda faza, a panel ih nije tražio | riješeno (panel vodi klik po klik) |
| [P22](#p22) | 22.08 | protokol mjerenja | Alarm iz prvog papirića progutao sljedeća dva bloka | djelimično (panel upozorava; trajanje oporavka otvoreno) |
| [P23](#p23) | 23.08 | kalibracija / postavka | Jedan klip od deset propadne na 66 Hz i obori K1 | uzrok izmjeren, **otvoreno** |
| [P24](#p24) | 26.08 | kvalitet signala | Apsolutni pod od -60 dBFS postao skrivena kapija prisustva mašine | riješeno |
| [P25](#p25) | 26.08 | kalibracija | K1 pada na jednom klipu od deset, run ne stigne ni do DET-a | riješeno (trim do dva klipa) |
| [P26](#p26) | 27.08 | commissioning | Robustni Hampel prag oborio sopstveni VERIFY | riješeno odbacivanjem robustnog fita |
| [P27](#p27) | 26.08 | operaterski tok | Hard deadline od 25 min obara run prije kraja plana | riješeno |

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

**Datum:** 06.08.2026 · **Oblast:** I2C bring-up · **Status:** RIJEŠENO 10.08.2026

**Konačni uzrok.** GND modula bio je pogrešno spojen na strani ESP32-S3, pa su
SDA i SCL ostajali na 3,3 V i izgledali kao da su kratko spojeni na VCC.
Izolacioni testovi sa svakom žicom posebno pokazali su da GPIO8/9, jumperi i
sam modul rade; kvar se pojavljivao tek dodavanjem pogrešne GND veze. Poslije
ispravke senzor odgovara na adresi `0x44`, vraća ID `0x5449`/`0x2260`, prihvata
config `0x4527` i kalibraciju `1024`.

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

<a name="p12"></a>
## P12 — Windows konzola zaustavila eksperiment na BHS Unicode ispisu

**Datum:** 09.08.2026 · **Oblast:** PC alati · **Status:** riješeno

**Simptom.** `bench_periodicity.py` se zaustavio prije izdvajanja prvog feature-a
sa `UnicodeEncodeError: 'charmap' codec can't encode character '\u010d'`.

**Uzrok.** Aktivna Windows konzola koristila je kodnu stranicu koja ne može
kodirati slovo `č` iz statusnog ispisa. Podaci, WAV fajlovi i računanje nisu bili
problem; pad se desio u prvom `print()` pozivu.

**Rješenje.** Statusni ispis alata koristi ASCII tekst. UTF-8 ostaje eksplicitno
naveden za JSON rezultate i dokumentaciju.

**Dokaz.** Skript poslije izmjene prolazi `py_compile` i kreće u izdvajanje
periodičnih feature-a iz cijelog skupa.

**Pouka.** Batch eksperimenti na Windowsu ne smiju zavisiti od aktivne konzolne
kodne stranice. Statusni izlaz treba biti ASCII ili proces mora eksplicitno
postaviti UTF-8 prije prvog ispisa.

---

<a name="p13"></a>
## P13 — Spojeni DCASE klipovi prave lažnu anomaliju na šavu

**Datum:** 09.08.2026 · **Oblast:** živi demo · **Status:** riješeno

**Simptom.** U prvom akustičkom demou uređaj je prijavio veliko odstupanje
(score 3881 pri pragu 1887) usred dionice koja je trebalo da bude **normalan**
rad. Isto se vidjelo i u kalibraciji: rasipanje LOO score-ova bilo je 53 %
relativno (sredina 1132, sd 599), mnogo veće nego na PC-u.

**Uzrok.** Demo zvuk je napravljen nadovezivanjem DCASE klipova od po 10 s, a
ti klipovi nisu iz istog radnog režima — ime nosi atribut `spd_1`, `spd_2` ili
`spd_3`. Na šavu dva klipa različite brzine zvuk **stvarno** naglo promijeni
karakter. Detektor je to ispravno prijavio; greška je bila u montaži, ne u
modelu. Uz to prozori uređaja (9,98 s + režija) ne padaju na granice klipova,
pa svaki šav upadne usred nekog prozora.

**Rješenje.** `psd_live_demo.py --speed spd_1` bira klipove jedne brzine za
kalibraciju i za normalnu dionicu. To odgovara i stvarnoj primjeni: ventilator
u ustaljenom režimu.

**Dokaz.** Vidi [hardver-verifikacija.md](hardver-verifikacija.md), poređenje
prolaza 1 (miješane brzine) i prolaza 2 (jedna brzina).

**Pouka.** Sintetički demo materijal mora biti provjeren isto kao i kod. Kad
uređaj prijavi anomaliju, prvo pitanje je da li je zvuk stvarno bio normalan —
ovdje nije bio.

---

<a name="p14"></a>
## P14 — Sintetički kvar je bio bas koji zvučnik ne reprodukuje

**Datum:** 09.08.2026 · **Oblast:** eksperiment · **Status:** riješeno

**Simptom.** Sweep jačine kvara preko zvučnika nije dao monoton odziv: −24 dB
je jednom skočilo na 4450, a **jači** kvarovi −18 i −12 dB ostali su na 340–570,
ispod praga. Digitalno je isti front-end davao 559 / 3042 / 10448 — uredno
rastuće.

**Prva (pogrešna) hipoteza.** „Front-end je slijep za udarne kvarove, jer je
`psd_shape` dugoročni prosječni spektar." Provjereno alatom
[`check_fault_type.py`](../pc/tools/check_fault_type.py) i **odbačeno** — udarni
kvar je zapravo onaj na koji je front-end najosjetljiviji.

**Druga (pogrešna) hipoteza.** „Akustički kanal uništava kvar." Provjereno
mjerenjem [`psd_channel_probe.py`](../pc/tools/psd_channel_probe.py): kroz
zvučnik i mikrofon preživi **82,5 %** promjene po trakama, score 10 116 → 4804.
Kanal, dakle, nije krivac.

**Stvarni uzrok — greška u mom kodu.** U `add_fault` su udarima dodavana dva
sinusa fiksne amplitude:

```python
fault += 0.5  * np.sin(2*np.pi*ROT_HZ*t)      # 24 Hz
fault += 0.25 * np.sin(2*np.pi*2*ROT_HZ*t)    # 48 Hz
fault *= amp / rms(fault)                      # normalizuje CIJELI kvar
```

Sinusi nose ~95 % energije kvara, pa su poslije normalizacije udarci ostali
zanemarljivi. Izmjereno na samom snimku: kvar je bio **+9,2 dB samo u 10–50 Hz**
i 0,0 dB u svim ostalim opsezima. Zvučnik laptopa ispod ~150 Hz praktično ne
reprodukuje, pa do mikrofona nije stiglo ništa.

**Rješenje.** Tonska komponenta uklonjena; kvar su samo širokopojasni udarci.
Poslije izmjene isti kvar daje +8,0 dB u 2–4 kHz i +2,5 dB u 1–2 kHz — u opsegu
koji se reprodukuje.

**Pouka.** Sintetički pobuđivač se mora **izmjeriti u spektru prije upotrebe**,
isto kao što se snimak provjerava prije nego se pusti. I: dvije uzastopne
hipoteze o „fizici" bile su pogrešne, a uzrok je bio jedna linija koda. Kad
mjerenje ne prati očekivanje, prvo se provjerava artefakt, pa tek onda teorija.

---

<a name="p15"></a>
## P15 — Tranzijent pri uključenju mikrofona ruši prolaz u prvom bloku

**Datum:** 11.08.2026 · **Oblast:** I2S / fail-closed kalibracija · **Status:** riješeno

**Simptom.** Poslije flešovanja `ASD_PSD_LIVE` sa Fazom 1, uređaj je odmah
padao u `CALIBRATION_REJECTED`:

```
QUALITY phase=WAIT index=1 result=CLIPPING
  rms_dbfs=-5.214  dc=-13286.724  peak=32763  clipped=83  zeros=138  dropped_delta=0
fail-closed stop u WAIT: CLIPPING -> CALIBRATION_REJECTED
```

**Kako je nađen.** Tri od četiri reseta su padala, jedan je slučajno prošao.
Taj jedan je i dao rješenje, jer je pokazao **opadanje** kroz prva tri bloka:

| WAIT blok | rms | dc | peak |
|---|---|---|---|
| 1 | −4,1 dBFS | −6410 | 29968 |
| 2 | −18,0 dBFS | −7378 | 17047 |
| 3 | −35,4 dBFS | −1011 | 2325 |

**Uzrok.** INMP441 i I2S se sliježu poslije `i2s_channel_enable`, a
`audio_i2s.c` nije odbacivao ni jedan uzorak — capture task upisuje u ring
buffer sve, uključujući prvi DMA bafer sa DC skokom. Do Faze 1 to nikad nije
zaboljelo: stari `psd_live.c` je samo upozoravao na tišinu i nastavljao, pa je
tranzijent tiho upadao u WAIT, koji se ionako odbacuje. Fail-closed gate ga je
prvi put **ocijenio**, i ispravno odbio.

Amplituda tranzijenta se mijenja od reseta do reseta (`dc` −13286 / −12183 /
−6577 / −6410), pa se ne može tolerisati pragom.

**Rješenje.** Odbacuje se prva **1,0 s** u `capture_task`, na izvoru, prije nego
uzorci uđu u ring buffer, u `raw_peak` ili u ocjenu kvaliteta. Poslednji
preskočeni blok je obično djelimičan, pa se ostatak istog bloka normalno
obrađuje. `dropped` ne broji odbačene uzorke.

**Zašto na izvoru, a ne popuštanjem gate-a.** Popuštanje bi bilo
`warn and continue`, što je u [PLAN-NEXT-LEVEL.md](PLAN-NEXT-LEVEL.md)
eksplicitno zabranjen anti-patern. Ovako mjerni prozor počinje kad se senzor
ustali, a svaki blok koji uđe u lanac se i dalje ocjenjuje punim gate-om.

**Drugi razlog za istu popravku.** `raw_peak` je dokaz kojim je zatvoren rizik
C1 (rezerva do klipovanja, [P6](#p6)). Tranzijent od 29968 bi tu rezervu
prikazao lažno malom, dakle mjerenje C1 je do sada moglo biti kontaminirano.

**Dokaz.** Tri reseta poslije popravke daju ponovljiv rezultat, bez `CLIPPING` i
bez prekida: blok 1 rms −67 dBFS / dc −26 / peak 65, blok 2 −78 / −7,7 / 21,
blokovi 3–4 −79 / −3 do 0 / 13–18. Razlika između reseta je manja od 1 dB.

**Pouka.** Fail-closed gate nije samo zaštita nego i **mjerni instrument**: prvi
put kad je nešto počelo da ocjenjuje svaki blok, odmah je našlo defekt koji je
mjesecima bio tu i koji nijedan od 88 PC testova nije mogao vidjeti, jer se
tranzijent pojavljuje samo na stvarnom senzoru.

---

<a name="p16"></a>
## P16 — Mikrofon ne čuje zvučnik iako audio stiže na izlaz

**Datum:** 11.08.2026 · **Oblast:** akustički put · **Status:** RIJEŠENO 13.08.2026 — mikrofon #1 je bio mrtav, modul #2 radi

**Simptom.** WAIT faza daje ravnih −77 do −79 dBFS kroz svih 60 blokova, isto sa
puštenim zvukom i bez njega, pa prolaz pada na
`INSUFFICIENT_LEVEL -> NO_MACHINE` (`0/60 validnih blokova iznad -60 dBFS`).

**Šta je isključeno mjerenjem:**

| Provjera | Rezultat | Zaključak |
|---|---|---|
| Default izlazni uređaj | `Speakers (Realtek(R) Audio)`, ne monitor | rutiranje ispravno |
| Stereo Mix (digitalni odvod izlaza) | **−16,03 dBFS, peak 0,230** | audio stvarno stiže na Realtek izlaz, volumen nije problem |
| 1 kHz sinus, amplituda 0,95, volumen 75 % | mikrofon max −68,5 dBFS | ni najglasniji i za zvučnik najpovoljniji signal se ne vidi |
| Snimak ventilatora preko zvučnika | mikrofon −78 dBFS | isto kao prazna soba |
| I2S podatkovni put | dc se sliježe −26 → 0, `zeros` varira 0–450, `stuck` ~350/4095 | linija je živa i daje stvarne male vrijednosti, nije mrtva ni zaglavljena |

Laptopov ugrađeni mikrofon je snimio −95 dBFS uz peak 0,0001, što liči na
hardverski mutiran ulaz, pa taj test **nije** upotrebljiv kao kontrola.

**Zašto sinus a ne snimak.** [P14](#p14) je već izmjerio da zvučnik laptopa
ispod ~150 Hz praktično ne reprodukuje. Sinus na 1 kHz je u opsegu gdje je
zvučnik najjači, pa negativan rezultat na njemu isključuje hipotezu „snimak je
prenizak po frekvenciji".

**Napomena o nivou.** −78 dBFS **sam po sebi nije dokaz kvara.** INMP441 ima
osjetljivost −26 dBFS na 94 dB SPL, pa −78 dBFS odgovara ~42 dB SPL, dakle
stvarno tihoj sobi. Za poređenje, 06.08. je soba bila −46 dBFS (~72 dB SPL), ali
je tada radio ventilator laptopa i dominirao je ([P10](#p10)).

### Vjerovatni uzrok — alkohol u sound portu

Naknadna informacija od 11.08.2026: mikrofon je **tog dana ponovo lemljen**, i
pri čišćenju je **naprskan alkoholom u otvor (sound port)**.

To se poklapa sa svim izmjerenim podacima i objašnjava zašto je nalaz izgledao
protivrječno. Kod MEMS mikrofona membrana je **direktno izložena** kroz sound
port, a ASIC sa I2S izlazom i DC servom je odvojen od nje. Ako je membrana
oštećena ili zaliven port:

- ASIC i dalje radi → I2S daje podatke, `dc` se sliježe, vrijednosti su male ali
  stvarne, `zeros`/`stuck` su normalni. **Točno ono što je izmjereno.**
- membrana ne pretvara zvuk → nikakav akustički signal se ne vidi, ni sinus na
  1 kHz blizu pune skale. **Točno ono što je izmjereno.**

Ovo je i unaprijed predviđen rizik: [lemljenje.md](../radno/elektronika/lemljenje.md) i
[hardver-lista.md](../radno/elektronika/hardver-lista.md) izričito kažu **„ne dirati sound port"**, i
zato su kupljena dva komada. Rastvarači, ultrazvučno čišćenje i bilo koja
tečnost u portu su za MEMS mikrofon zabranjeni — izopropanol može rastvoriti ili
deformisati membranu, a i kad ne ošteti, ostavlja ostatak.

**Redoslijed rješavanja:**

1. **Ne duvati komprimovanim vazduhom u port** — pritisak može probiti membranu i
   od popravljivog napraviti nepopravljivo.
2. Ostaviti modul **24 h na suhom, portom nadole**, bez grijanja. Ako je alkohol
   samo privremeno zapunio port, isparava i mikrofon se vrati. Besplatno, pa se
   probava prvo.
3. Ako i dalje ne reaguje na kucanje — spojiti **drugi INMP441**, sa portom
   zaštićenim (kapton traka) tokom lemljenja i bez ijednog sredstva za čišćenje
   u blizini, pa traku skinuti poslije.

### Preostale hipoteze, ako drugi mikrofon takođe ne radi

1. **Zvučnik ne proizvodi zvuk** iako digitalni miks postoji. Provjera: pusti bilo
   šta i slušaj. Ovo još nije provjereno.
2. Labava `VDD` ili `GND` žica, ili `L/R` nije na GND. Manje vjerovatno, jer bi
   se vidjelo na podatkovnom putu.

### Tap test — mikrofon #1 je akustički mrtav

Izvedeno 11.08.2026, dva WAIT prozora, ~31 s, uz **neprekidno kucanje prstom po
samom modulu**. Prva dva bloka svakog prozora su isključena jer nose rezidualno
slijeganje senzora (rms ~−67, peak ~60) i nisu zvuk.

| | |
|---|---|
| blokova u ocjeni | 116 |
| rms medijana | −78,76 dBFS |
| rms opseg | −79,28 do −77,61 dBFS → **raspon 1,2 dB** |
| peak | 12 do **20** |
| referenca 06.08. (radni mikrofon) | mirna soba peak **1020**, kucanje peak **6675** |

Raspon od 1,2 dB kroz 31 s kucanja nije tiha soba — to je vlastiti šum ASIC-a,
praktično konstanta. Živ mikrofon u sobi pokazuje veću varijaciju već od samog
ambijenta. Peak 20 naspram referentnih 6675 je faktor 330.

**Zaključak:** podatkovni put radi, akustički ne postoji. Uz alkohol u sound
portu, uzrok je time dovoljno utvrđen da se po njemu postupi — modul #1 se
sklanja, ide #2.

> **Metodološka pouka iz same provjere.** Prva verzija tap testa je javila „DA",
> jer je prag bio postavljen na medijana + 8 dB, a blok 1 poslije reseta zbog
> rezidualnog slijeganja uvijek daje ~−67 dBFS. Kriterij je morao biti apsolutni
> `peak` (mehanička pobuda je reda 10³–10⁴, šum je reda 10¹), a blokovi
> slijeganja isključeni. Isti obrazac kao [P14](#p14): kad rezultat ne prati
> očekivanje, prvo se provjerava artefakt mjerenja, pa tek onda hipoteza.

### Preostale hipoteze, ako drugi mikrofon takođe ne radi

**Pouka koja već sada stoji.** Score iz živog rada ne dokazuje da mikrofon radi
([P3](#p3)) — ali ni sirovi RMS to ne dokazuje sam, jer tiha soba i mrtav
akustički put daju sličan broj. Jedini pouzdan bring-up test je **kontrolisana
promjena** koju mikrofon mora vidjeti: kucanje, ili poznat ton na poznatoj
udaljenosti.

---

### Zatvaranje: mikrofon #2 radi

**Datum:** 13.08.2026. Modul #1 je zamijenjen modulom #2, bez ijednog sredstva
za čišćenje u blizini sound porta. Kontrolisani A/B test, isti 1 kHz sinus
preko istog zvučnika na kojem je #1 pao:

| | tišina | ton |
|---|---|---|
| rms medijana | −68,58 dBFS | **−32,71 dBFS** |
| rms raspon | 1,62 dB | — |
| peak | 46 | **1117** (2641 na ataku) |

Razlika **+35,87 dB**, peak **48×**. Ton se pojavio tačno u bloku u kojem je
krenula reprodukcija i nestao tačno u bloku u kojem je WAV završio. Za poređenje,
modul #1 je kroz 31 s neprekidnog kucanja dao raspon 1,2 dB i peak ≤ 20.

Time je potvrđena i dijagnoza: podatkovni put je cijelo vrijeme radio, akustički
nije postojao. Uzrok — izopropanol u sound portu — ostaje najvjerovatnije
objašnjenje, i pravilo „ne dirati sound port" iz [lemljenje.md](../radno/elektronika/lemljenje.md)
stoji.

**Šta je ovo odblokiralo:** validnu kalibraciju na uređaju, cijelu DET fazu i
mjerenje lažnih alarma. Sve troje je isti dan prešlo iz `BLOCKED_HARDWARE` u
`PASS` — vidi [DNEVNIK-NEXT-LEVEL.md](DNEVNIK-NEXT-LEVEL.md), blok A.

**Pouka koja ostaje.** Bring-up mikrofona se ne dokazuje sirovim nivoom, jer
tiha soba i mrtav akustički put daju sličan broj. Dokazuje se **kontrolisanom
promjenom** koju mikrofon mora vidjeti — ton poznate frekvencije, pušten i
zaustavljen u poznatom trenutku. Isti test razlikuje i #1 i #2, bez tumačenja.

---

<a name="p17"></a>
## P17 — Prag se između dvije kalibracije razlikuje 16×

**Datum:** 14.08.2026 · **Oblast:** kalibracija / prag · **Status:** OTVORENO

**Simptom.** Dva prolaza, ista pločica, isti mikrofon, isti snimak preko istog
zvučnika, ista soba, razmak nekoliko sati:

| prolaz | LOO sredina | LOO sd | LOO CV | prag |
|---|---|---|---|---|
| 1 | 899,86 | 1595,75 | **1,77** | **5687,11** |
| 2 | 167,15 | 59,92 | 0,36 | **346,89** |

**Uzrok.** Formula praga je `max(p90 LOO, sredina + 3 sd LOO)`. Sa deset
kalibracionih klipova, `sd` je izuzetno osjetljiv na jedan odskočen klip: u
prolazu 1 najveći LOO score je bio 5430 uz medijanu reda 200, pa je `sd` sam
odnio prag na 5687. Član `sredina + 3 sd` je uveden 09.08. upravo zato što je
`p90` bio sistematski prenizak ([hardver-verifikacija.md](hardver-verifikacija.md)),
i on tu ulogu i dalje ispunjava — ali unosi novu osjetljivost.

**Zašto je ovo važno, a ne kozmetika.** Prag od 5687 na tom prolazu znači da
najveći normalan score dosegne 58,7 % praga. To zvuči kao zdrava rezerva, ali
istovremeno znači da bi stvarna promjena morala biti **skoro dvostruko veća od
najgore normalne varijacije** da bi se uopšte vidjela. Faza 4 je isto izmjerila
sa druge strane: u **10 od 40** splitova pomjeraj score-a od 3 sd nikad ne
dosegne prag, i to za **svako** vremensko pravilo podjednako
([`asd_temporal_policy_v1.json`](../pc/config/asd_temporal_policy_v1.json)).
Dakle nije stvar u pravilu odlučivanja nego u pragu.

**Zašto nije popravljeno odmah.** Svaka zamjena formule je novi prag, a prag se
po pravilima ovog projekta izvodi iz normalnih podataka i zamrzava prije bilo
kakve evaluacije. Kandidati koji se nameću — robustne statistike umjesto
`sd` (MAD, IQR), odbacivanje najgoreg LOO klipa, ili više od 10 kalibracionih
klipova — svi zahtijevaju zaseban normal-only izvod, isto kao što ga je dobila
politika prisustva i vremenska politika. To je zaseban posao, a ne izmjena
konstante.

**Ukrštena provjera koja isključuje sve druge objašnjenje.** Isti prozori,
ocijenjeni tuđim pragom:

| | ocijenjeno svojim pragom | ocijenjeno pragom drugog prolaza |
|---|---|---|
| prozori prolaza 1 (prag 5687) | 0 % iznad praga | **92 %** iznad praga |
| prozori prolaza 2 (prag 347) | 91 % iznad praga | **8 %** iznad praga |

Prag se razlikuje **16×**, a medijana score-a samo 2,8× (568 naspram 1605).
Dakle rasipanje ne dolazi od signala nego od praga, i ishod se okreće naopako
u zavisnosti od toga kojih je deset kalibracionih klipova uređaj slučajno čuo.

**Druga strana istog problema.** U prolazu 2 je LOO javio `sd=60`, a stvarna
varijacija normalnog rada u detekciji je imala `sd=8557` — LOO je potcijenio
buduće rasipanje **za dva reda veličine**. Komentar u `psd_live.c` je tu
pristrasnost predviđao od 09.08; sada je izmjerena.

**Posljedica za rad.** Brojka „lažnih alarma na sat" se ne smije navesti kao
svojstvo sistema dok se prag ne stabilizuje: izmjereno je 0,00/h i 8,69/h na
istoj postavci.

**Sljedeći korak.** Izvesti robustan prag iz normalnih podataka po istom
obrascu kao `derive_temporal_policy.py`, sa kriterijem zaključanim prije
gledanja u rezultat, i tek onda mijenjati `psd_live.c`. Prije toga: izmjeriti
isti CV na **fizičkom ventilatoru**, jer se sve gornje brojke odnose na snimak
preko zvučnika.

---

<a name="p18"></a>
## P18 — EWMA i CUSUM propuštaju baš onu buku koju je trebalo da filtriraju

**Datum:** 14.08.2026 · **Oblast:** vremenska odluka · **Status:** riješeno (odbačeni mjerenjem)

**Očekivanje.** Faza 4 je planirana sa pretpostavkom da će glađenje score-a
(EWMA) i kumulativna suma (CUSUM) biti nadogradnja nad prostim brojanjem tri
uzastopna prozora. Obje tehnike su standardne za detekciju pomjeraja i obje su
bile u planu kao vjerovatni pobjednici.

**Izmjereno je suprotno.** Na 40 splitova i 2000 normalnih prozora:

| pravilo | lažnih alarma/h | reakcija na pobudu od 1 prozora |
|---|---|---|
| 3 uzastopna prozora | **0,00** | **0,004** |
| EWMA(0,4) + 3 uzastopna | 5,40 | 0,592 |
| CUSUM k=0,5 h=2 | 5,40 | 0,721 |

**Uzrok.** Oba pravila po konstrukciji **prenose** informaciju kroz vrijeme, i
to je upravo ono zbog čega ovdje gube. U ovom testu korištena je sintetička
score-pobuda od jednog prozora, kao apstrakcija kratkog događaja. Kod EWMA ona
ostaje u statistici nekoliko prozora i može sama dopuniti niz od tri. Kod
CUSUM-a se akumulira i može prebaciti prag bez ijednog trajnog odstupanja.
Brojanje uzastopnih prozora nema memoriju o
veličini: jedan prozor iznad praga podigne brojač na 1, a sljedeći normalan
prozor ga vrati na 0, bez obzira koliko je pobuda bila glasna.

**Šta je uzeto umjesto toga.** Histereza: isti ulazni prag, izlazni na 0,7
ulaznog. Ne unosi memoriju o veličini pobude, a rješava drugi problem —
treperenje alarma kad score visi oko praga. Uz iste lažne alarme i isto
kašnjenje, prepolovljuje alarmne epizode pri domenskom pomaku (11,16 → 5,40 na
sat na klipovima drugog fizičkog ventilatora).

**Pouka.** Standardna tehnika nije ista stvar kao prikladna tehnika. EWMA i
CUSUM su napravljeni da uhvate **mali trajni** pomjeraj u šumu; ovdje je zadatak
obrnut — odbaciti **veliku kratku** score-pobudu. Ovo nije akustički test
govora, vrata ili udarca; njih treba posebno izvesti u fizičkom protokolu.

**Trag u kodu.** Oba pravila su ostavljena u `asd_temporal_policy_t`, isključena
nulom, sa komentarom zašto. Da se ne „otkriju" ponovo za pola godine kao nova
ideja.

<a name="p19"></a>
## P19 — Sopstveno računanje na laptopu kontaminiralo probu lažnih alarma

**Datum:** 14.08.2026 · **Oblast:** metodologija mjerenja · **Status:** riješeno (pouka)

**Šta se desilo.** Dok je tekla tridesetominutna proba lažnih alarma, na istom
laptopu je pokrenuta evaluacija Faza 3/5/6 nad 1100 klipova. Zvuk ventilatora je
puštan preko zvučnika **tog istog laptopa**, a mikrofon stoji uz njega.

**Trag u podacima.** Nivo u detekciji je porastao sa −46,5 na −40,4 dBFS u
najglasnijem prozoru, a score-ovi opadaju kroz prolaz kako se opterećenje
smanjivalo:

| interval | prozora | score sredina | max |
|---|---|---|---|
| 0–10 min | 61 | 4596 | 100 150 |
| 10–20 min | 60 | 2604 | 9 688 |
| 20–30 min | 46 | 1875 | 7 093 |

Prvih sedam prozora — jedini nad zvukom koji uređaj nikad nije čuo, i jedini
prije nego što je računanje krenulo — imali su sredinu 263 i **nula alarma**.

**Zašto ovo nije kvar uređaja.** Ventilator laptopa je stvarna, trajna promjena
u zvuku sobe. Uređaj ju je vidio i prijavio, i to je tačno ono što treba da radi.
Greška je bila u postavci mjerenja, ne u detektoru.

**Isti obrazac kao [P10](#p10), obrnuto.** Tada je kalibracija naučila ventilator
laptopa kao normalno stanje. Sada je isti ventilator upao u fazu detekcije. Oba
puta je izvor bio isti i oba puta neprimijećen dok se nije pogledao nivo.

**Pravilo koje odsad važi.** Proba lažnih alarma se pušta na **neopterećenoj**
mašini: bez treninga, bez evaluacije, bez builda. Ako to nije moguće, u izvještaj
ide nivo po prozoru i eksplicitna napomena da broj nije čist.

**Šta ostaje da stoji uprkos kontaminaciji.** Zaključak o pragu
([P17](#p17)) je izveden iz **ukrštene** provjere — isti prozori, oba praga — pa
ga promjena u sobi ne dodiruje. Kontaminiran je samo apsolutni broj lažnih
alarma iz tog prolaza.

---

<a name="p20"></a>
## P20 — FLAGS iz drugog taska upada usred FEATURE96 reda

**Datum:** 22.08.2026 · **Oblast:** UART / protokol · **Status:** riješeno u kodu,
**nije fizički potvrđeno** (build 3f80a42a, još nije flashovan)

**Simptom.** Prvi GUIDED25 run koji je stigao do kraja pao je na
`invalid_research_telemetry`. Kalibracija je prošla (K1 `accepted`), detekcija je
radila svih 65 prozora, ali je od očekivanih **75 prozora ostalo kompletnih 12**:
`feature_record_count` 59/75, `subsegment_record_count` 328/375, 126 grešaka u
manifestu, sve `duplicate_key:protocol`.

**Kako je nađen.** `firmware_parse_errors.csv` čuva sirov red. U njemu se vidi
tačno mjesto prekida — niz brojeva se prekine na 28. vrijednosti i odmah nastavi
sa `FLAGS protocol=asd-quality-v1.5.0 ...`, pa host u istom redu vidi dva
`protocol=` i odbija ga.

**Uzrok.** ESP-IDF ostavlja `stdout` bez baferovanja, pa svaka konverzija odlazi
na UART zasebnim upisom. `emit_research_vector` jedan red ispisuje kroz **98**
`printf` poziva (zaglavlje + 96 vrijednosti + novi red), a UI task u tom prozoru
emituje `FLAGS` iz svog konteksta. Isti obrazac kao [P4](#p4), samo je tamo
watchdog upisivao tekst usred base64 toka.

**Rješenje.** `flockfile(stdout)`/`funlockfile(stdout)` oko dva mjesta koja red
sastavljaju iz više poziva — `emit_research_vector` i `LOOALL`. Isti FILE lock
uzimaju `printf` iz drugih taskova i `ESP_LOGx` preko `vprintf`, pa se pod njim
ne može umetnuti ni jedan ni drugi. Potvrđeno da u ovom buildu svi taskovi dijele
isti `FILE`: `CONFIG_LIBC_NEWLIB=y`, a `esp_reent_init` svakom tasku postavlja
`_REENT_STDOUT(r) = _REENT_STDOUT(_GLOBAL_REENT)`.

Ostali `emit_*` pozivi se **ne** diraju: svaki je jedan `printf`, koji newlib
zaključava interno. Potvrda iz istog runa — nijedna od 63 greške nije na kratkom
redu (`FLAGS`, `QUALITY`, `DET`, `COMMISSION`), sve su na dugim research redovima.

**Zašto se to nije vidjelo ranije.** Panel je research redove brojao po prvom
tokenu, a pokvaren red i dalje počinje sa `FEATURE96` — pa su brojači izgledali
uredno dok je host odbijao svaki drugi zapis. Panel sada provjerava da red ima
tačno jedan `protocol=` i onoliko vrijednosti koliko sam tvrdi u `dims=`
(`research_line_intact`). Reprodukovano nad `serial.log` tog runa: panel dobija
`FEATURE96 59`, `SUBSEG96 328`, `research_errors 63` — identično hostu — a **prvu
grešku vidi u 282. redu loga, tj. oko 293 s**, umjesto poslije 27 minuta.

**Ostaje.** `esp_rom_printf` (panic, task watchdog) ne uzima ovaj lock. To se ne
može zaključati odavde i ostaje poznat rizik pri padu.

---

<a name="p21"></a>
## P21 — Run traži 20 potvrda faza, a panel ih nije tražio

**Datum:** 22.08.2026 · **Oblast:** operaterski tok · **Status:** riješeno

**Simptom.** `guided25_report.json` je pao i na
`operator_confirmations_missing_fake_or_out_of_order`. U `events.csv` tog runa
nema nijedne `guided25_confirm` bilješke.

**Uzrok.** `evaluate_guided25_artifact` traži **tačno dvadeset** potvrda —
`start` i `end` za svaku fazu osim normalne osnove — i to u redu, sa host
vremenom koje se poklapa. Panel ih je nudio kao dva obična dugmeta među sedam,
bez brojača, bez oznake koja je potvrda na redu i bez ijedne poruke da run bez
njih ne vrijedi. Operater koji drži papirić uz usis nema kako da pogodi da mu
nedostaje klik.

**Rješenje.** Panel sada vodi potvrde umjesto da ih samo dozvoljava:

- zasebna kartica odmah ispod uputstva faze, sa brojačem `n/20`;
- aktivno je samo dugme koje je stvarno na redu (`confirm_next_edge`), drugo je
  onemogućeno — isti redoslijed koji server već provjerava, sada i vidljiv;
- faza koja je prošla bez oba klika se više ne može potvrditi, pa panel odmah
  ispisuje `PROPUSTENE POTVRDE` i kaže da se pokušaj prekine, umjesto da se
  dovrši mrtav run;
- spisak faza dobija oznaku `OK` / `X` po potvrdi.

**Dokaz.** `pc/tests/test_asd_panel.py::test_panel_asks_for_the_confirmation_that_is_actually_due`
i `::test_snapshot_carries_confirmation_and_research_integrity_to_the_page`.

---

<a name="p22"></a>
## P22 — Alarm iz prvog papirića progutao sljedeća dva bloka

**Datum:** 22.08.2026 · **Oblast:** protokol mjerenja · **Status:** djelimično

**Simptom.** `paper_blocks_passed: 1/3`, uz `alarm_or_carried_alarm` u sva tri
oporavka. Papirić je svaki put jasno podigao skor, ali su blokovi 2 i 3 pali.

**Uzrok.** Blok se ocjenjuje po **ulasku** u alarm, a ulaska nema ako uređaj iz
prethodnog alarma nije izašao. `firmware_states.csv` pokazuje samo dva
`ANOMALY_ENTERED` u cijelom runu: alarm je ušao u `1192,8 s` (papirić 1) i
izašao tek u `1432,4 s` (oporavak 3) — **239,6 s neprekidno**, preko papirića 2 i 3.

Izlaz ide na `threshold_exit`, koji je `p75` od 44 DERIVE prozora i tog runa je
bio `824` (uz `threshold_enter` = `p99` = `4374`). Izmjereni skorovi:

| faza | skorovi |
|---|---|
| normalna osnova | 201 – 602 |
| oporavak 1 | 1924, 1282, 1413, 1002 |
| oporavak 2 | 1030, 968, 1432, 1396 |
| oporavak 3 | 1104, **752**, 622, 452 |
| oporavak poslije govora | 534, 538, 434, 468 |

Oporavci 1 i 2 su stajali dvostruko iznad normalne osnove i iznad `threshold_exit`;
tek kad je skor pao na `752` alarm je nestao u istom prozoru. Oporavak 3 i
oporavak poslije govora, kad se operater stvarno odmakao, padaju odmah. Dakle
akustičko stanje **jeste** bilo podignuto — ruka i papirić su ostajali u blizini
— a ne da je prag pogrešan.

**Rješenje koje je urađeno.** Panel u fazi u kojoj alarm obara run i dalje traje
ispisuje `UREDJAJ JE JOS U ALARMU` i kaže da sljedeći papirić neće imati u šta
da uđe. Ranije je operater imao samo crvenu lampicu, bez posljedice napisane uz nju.

**Šta ostaje otvoreno.** Oporavak u GUIDED25 traje `50 s` (4 mjerena prozora);
stariji `full` plan je za istu fazu imao `90 s`. Produženje na `90 s` bi ukupan
najgori tok podiglo sa `1370 s` na `1490 s`, uz hard stop `1500 s` — što ne
ostavlja ništa operateru. Odluka se **ne** donosi poslije rezultata; ako se
mijenja, mijenja se uz bump verzije politike i novi preregistrovani retest.

---

<a name="p23"></a>
## P23 — Jedan klip od deset propadne na 66 Hz i obori K1

**Datum:** 23.08.2026 · **Oblast:** kalibracija / mjerna postavka · **Status:**
uzrok izmjeren, **otvoreno** (nije eliminisan)

**Simptom.** Tri kalibracije zaredom odbijene sa `UNSTABLE_CALIBRATION`, uz
kapiju `max_loo_cv = 0,6`:

| pokušaj | `loo_cv` | izvor |
|---|---|---|
| 22.08. 16:29 | `1,956` | firmware `CAL_SUMMARY` |
| 23.08. 13:42 | `1,258` | firmware `CAL_SUMMARY` |
| 23.08. provjera | `1,52` | host rekonstrukcija; sirov log je prepisan |
| 23.08. 19:56 | `1,666` | firmware `CAL_SUMMARY`, **operater van sobe** |

Za poređenje, run 22.08.2026 koji je **prošao**: `loo_mean 211,9`, `loo_sd 64,6`,
`loo_cv 0,305`.

**Kako je nađen.** `CAL_SUMMARY` daje samo `mean/sd/cv/range` — ne kaže koji klip
je kriv ni koja traka. Zato je K1 matematika ponovljena na hostu iz `FEATURE96`
telemetrije (`pc/tools/diag_calibration_loo.py`), sa razlaganjem skora po
trakama: doprinos trake je `delta_i * (P delta)_i` i sabira se tačno u skor.
Rekonstrukcija se poklapa sa firmverom — `mean 876,2` / `sd 1714,0` naspram
`876,17` / `1713,97`.

**Uzrok.** Devet od deset klipova je uvijek uredno; strada **tačno jedan**, i
uvijek u istom uskom pojasu — **trake 30–32, `66–75 Hz`**:

| pokušaj | najgori klip | njegov `loo` | koja traka ga nosi |
|---|---|---|---|
| 22.08. 16:29 | 10 | `5731` | 66 Hz `39 %` (uz 141 Hz `16 %`) |
| 23.08. 13:42 | 6 | `1385` | 66 Hz `75 %` |
| 23.08. provjera | 2 | `1911` | 66 Hz `66 %` |
| 23.08. 19:56 | 10 | `2023` | 75 Hz `37 %` (uz 182 Hz `9 %`) |

Ostali klipovi u istim snimcima su `90–470`, a u pokušaju bez operatera u sobi
`106–255` — najčvršće izmjereno. Rasipanje same trake 30 kroz deset
klipova: `0,08 dB` u snimku koji bi prošao, `0,23–0,33 dB` u odbijenima. Dakle
dovoljan je **jedan skok od oko +0,7 dB u jednoj od 96 traka** da `loo_cv`
pređe kapiju.

**Zašto je metrika toliko osjetljiva.** Kovarijansa je naučena na DCASE
ventilatorima, a u toj traci ima vrlo malu varijansu. Mahalanobis zato tamo
kažnjava nesrazmjerno. To je isti mehanizam kao [P17](#p17) — mala promjena u
uskoj dimenziji daje veliku promjenu skora.

**Šta je 66–75 Hz.** Odgovara rotacionoj frekvenciji ventilatora
(~4000 o/min), pa se pobuda tu i sprega.

**Nije operater.** Pokušaj 23.08. 19:56 je pušten sa operaterom u drugoj
prostoriji. Devet klipova je tada bilo čvršće nego u ijednom ranijem snimku
(`106–255`), ali je deseti svejedno otišao na `2023`. Ranija atribucija na
pomjeranje u stolici time **otpada kao nužni uzrok** — prisustvo operatera širi
osnovno rasipanje, ali ne pravi ovaj ispad.

**Nije ni udarac.** Razlaganje tog klipa po pet podsegmenata od 2 s pokazuje da
pobuda **raste kroz osam sekundi i traje do kraja klipa**, umjesto da se pojavi
i nestane:

| podsegment | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 75 Hz | `+0,26` | `-0,02` | `+0,60` | `+1,07` | `+0,98` |
| 182 Hz | `+0,26` | `+0,24` | `+0,47` | `+0,58` | `+0,99` |

Miran klip iz istog snimka ostaje unutar `±0,2` u obje trake. Dakle nešto se
**upalilo i nastavilo da radi** — pumpa, kompresor, voda, lift — i doprlo kroz
konstrukciju, a ne kroz vazduh.

**Šta je urađeno.** Ništa na pragovima — `max_loo_cv = 0,6` ostaje. Dodat je
`pc/tools/diag_calibration_loo.py` da se sljedeći pad ne rješava naslijepo.

Postupak koji odsad važi:

- kalibracija se pušta kad je zgrada mirna, a ne kad je operateru zgodno;
- pločica i mikrofon idu na **mekanu podlogu**, ne direktno na sto — put smetnje
  je strukturni, pa se prekida na tom mjestu, dok zvuk ventilatora kroz vazduh
  ostaje netaknut;
- prije trošenja GUIDED25 pokušaja pušta se jeftina provjera koja ide samo do
  kalibracije (~4 min) i ne troši pokušaj.

**Koliko je to lutrija.** Sva četiri odbijena pokušaja imala su tačno jedan
pogođen klip, što daje vjerovatnoću pogotka po klipu oko `0,1`. Čist niz od
deset klipova ima onda oko `35 %` šanse — što se slaže sa tim da je run
22.08.2026 prošao sa `loo_cv 0,305`. Ponavljanje samo po sebi ima smisla; meka
podloga treba da tu šansu digne.

**Šta ostaje otvoreno.** Da jedan prozor od deset, sa odstupanjem od `0,7 dB` u
jednoj traci, obara cijelu kalibraciju — to je svojstvo Mahalanobisa sa stranom
kovarijansom, i tako se prijavljuje u radu kao ograničenje metode. Nije razlog
da se kapija pomjeri; eventualna izmjena traži bump verzije politike i novi
preregistrovani retest.

---

<a id="p24"></a>
## P24 — Apsolutni pod od -60 dBFS postao skrivena kapija prisustva mašine

**Datum:** 26.08.2026 · **Oblast:** kvalitet signala · **Status:** riješeno

**Simptom.** GUIDED25 run 26.08. u 17:20 (`v3recovery4`) srušen je usred DET
faze, u 19. prozoru:

```
QUALITY phase=DET index=19 result=LOW_LEVEL_OBSERVATION rms_dbfs=-66.709
        stuck=11594 zeros=4177 dropped_delta=0
STATE   from=OBSERVATION_HOLD to=NO_MACHINE reason=LOW_LEVEL_OBSERVATION
EVENT   type=FLOW_STOPPED reason=LOW_LEVEL_OBSERVATION level=MACHINE_PRESENCE
```

Run je time završio kao `invalid_firmware_terminal` i nije dao nijedan
upotrebljiv papirić blok.

**Uzrok.** `DEFAULT_LEVEL_FLOOR_DBFS` je bio `-60 dBFS` i bio je zamišljen kao
provjera da digitalni audio uopšte živi. Ali ta granica je **apsolutna**, a
nivo koji mikrofon vidi zavisi od rastojanja i ugla. Na 40 cm sa ovim
ventilatorom normalan nivo je oko `-52 dBFS`, a normal-only SETTLE mjerenje je
dalo `-66,1637 dBFS`. Pod od `-60 dBFS` je time prestao da bude liveness
provjera i postao skrivena kapija prisustva mašine — koja obara run čim se
ventilator na tren utiša ili se mikrofon pomjeri.

**Rješenje.** Pod je spušten na `-80 dBFS`, sa `13,8 dB` rezerve u odnosu na
izmjereni normal-only SETTLE. Brojka je zamrznuta **prije** nego što je ijedna
target anomalija puštena, i upisana u `pc/config/asd_quality_policy_v1.json`
(`v1.0.0 → v1.1.0`) zajedno sa izvorom mjerenja. `ASD_QUALITY_POLICY_ID` je
bumpovan `0x51555631 → 0x51555632`.

Prisustvo mašine i dalje čuvaju dvije nezavisne provjere koje ne zavise od
rastojanja:

- `PRESENCE` gate izveden po sesiji kao `cal_level_mean − 11 dB`;
- `STUCK` / `ZERO` / `NONFINITE` provjere, koje hvataju stvarno mrtav mikrofon.

**Dokaz.** Runovi 27.08. (`v3recovery5d`, `tone-validation-final`) prošli su
cijeli plan bez ijednog `LOW_LEVEL_OBSERVATION` zapisa, na nivoima
`-53,9 … -33,2 dBFS`.

**Pouka.** Inženjerska kapija koja se poredi sa apsolutnim nivoom je uvijek i
kapija mjerne postavke. Ako granica treba da znači da audio živi, mora imati
rezervu prema najtišem izmjerenom normalnom stanju, a ne prema zdravorazumskom
broju.

---

<a id="p25"></a>
## P25 — K1 pada na jednom klipu od deset, run ne stigne ni do DET-a

**Datum:** 26.08.2026 · **Oblast:** kalibracija · **Status:** riješeno

**Simptom.** Dva runa zaredom (`v3recovery4b` 22:16, `v3recovery4c` 22:38) nisu
dala **nijedan** DET prozor. Oba su ponavljala:

```
calibration rejected: UNSTABLE_CALIBRATION; K1 loo_cv_above_max
```

To je isti mehanizam kao [P23](#p23): devet klipova uredno, deseti strada u
uskom pojasu `66–75 Hz`, i `loo_cv` pređe kapiju `0,6`.

**Zašto se nije rješavalo pomjeranjem kapije.** Kapija `max_loo_cv = 0,6` štiti
od toga da centar nauči nešto što nije normalno stanje ventilatora. Podizanje
kapije bi tu zaštitu ukinulo i pustilo kratki tranzijent u centar.

**Rješenje.** Umjesto pomjeranja kapije, K1 sad smije **izbaciti najviše dva**
najgora CAL klipa. Poslije svakog izbacivanja centar i svi LOO skorovi se
računaju ponovo, i preostali klipovi moraju proći **isti nepromijenjeni** prag
`0,6`. Treća nestabilnost obara kalibraciju kao i ranije.
`K1_MAX_DISCARDED_CAL_CLIPS 2` u `psd_live.c`.

Izbacivanje je auditabilno — emituje se prije `CAL_SUMMARY` zapisa:

```
CALTRIM policy=k1-two-clip-trim-v1 discarded_count=2
  discarded_index_1=9 discarded_loo_1=1616.417358
  discarded_index_2=2 discarded_loo_2=998.927979
  retained=8 raw_loo_cv=0.841676
```

**Dokaz.** Run `v3recovery4d` (26.08.): `raw_loo_cv 0,769753` → jedan klip
izbačen → `0,463238`, K1 prihvaćen. Run `v3recovery5d` (27.08.):
`raw_loo_cv 0,841676` → dva klipa → `0,426058`, K1 prihvaćen i run je otišao do
kraja plana. Bez ove izmjene oba bi pala prije DET faze.

**Šta ostaje.** Ovo liječi posljedicu, ne uzrok. Sam ispad u `66–75 Hz` je i
dalje otvoren i opisan u [P23](#p23) — čuva se kao ograničenje metode u radu.

---

<a id="p26"></a>
## P26 — Robustni Hampel prag oborio sopstveni VERIFY

**Datum:** 27.08.2026 · **Oblast:** commissioning · **Status:** riješeno
odbacivanjem robustnog fita

**Šta se probalo.** Poslije runa u kojem je prag `1 051,74` djelovao pretup,
činilo se da ga vuku pojedinačni visoki DERIVE prozori. Napisan je
`asd_robust_fit.c`: koordinatni 10 % trimmed centar i Hampelova granica
`median + 3 × 1,4826 × MAD`, sa empirijskim p99 kao gornjim plafonom.

**Šta se desilo.** Run `v3recovery5c` (27.08. 20:52) je to izveo na pločici:

```
THRFIT method=trimmed-center-hampel-v1 source=COMMISSION_DERIVE_NORMAL_ONLY n=44
       center_trim=0.1000 median=298.332031 mad=110.771149 robust_sigma=164.229309
       sigma_multiplier=3.0000 p99_ceiling=1548.228516 threshold=791.019958 capped_high=3
```

Prag `791,02`. Ali normalni VERIFY prozori — iz iste sesije, bez ijedne
anomalije — bili su `2 083 … 7 766`. Odvojeni fail-closed VERIFY je zato odbio
kalibraciju:

```
REJECTED result=VERIFY_NORMAL_REJECT
STATE from=NO_MACHINE to=CALIBRATION_REJECTED reason=VERIFY_NORMAL_REJECT
```

**Uzrok.** MAD normal-only DERIVE raspodjele opisuje samo njeno tijelo. Rep te
raspodjele kod ovog ventilatora je znatno duži od `3 × 1,4826 × MAD`, pa
Hampelova granica sječe ispod normalnog radnog opsega. Empirijski p99 taj rep
poštuje jer se računa iz stvarnih vrijednosti.

**Rješenje.** Živi put je vraćen na `frozen CAL center + empirical p99`, uz
`exit = p95` ograničen na `[p50, 0,5 × enter]`. `asd_robust_fit.c/.h` ostaje u
repou sa host parity testom radi reprodukcije, ali je **eksplicitno isključen
iz živog puta** i to čuvaju tri nezavisne provjere:
`pc/tools/check_schema_consistency.py`, `pc/tests/test_guided25_workflow.py` i
imenovani odbačeni kandidat u `pc/tools/derive_commissioning_policy.py`.

**Zašto je ovo dobar ishod.** Kapija koja postoji zbog ovakvih grešaka prvi put
je proradila na stvarnom hardveru, i to prije nego što je nastao ijedan DET
prozor. Loš prag nije mogao da se pretvori u rezultat.

**Nuspojava koja je otkrivena.** Host nije poznavao `VERIFY_NORMAL_REJECT`, pa
je run označio kao `invalid_firmware_telemetry / terminal_STATE_reason_unknown`
umjesto kao ispravno odbijenu kalibraciju. Razlog je dodat u
`CALIBRATION_STOP_REASONS` u `pc/tools/physical_fan_experiment.py`.

---

<a id="p27"></a>
## P27 — Hard deadline od 25 min obara run prije kraja plana

**Datum:** 26.08.2026 · **Oblast:** operaterski tok · **Status:** riješeno

**Simptom.** GUIDED25 je imao `hard_deadline_seconds: 1500` i poseban nadzorni
thread koji na isteku šalje `abort guided25_hard_deadline`. Treći pokušaj je
tako automatski prekinut prije kraja plana, iako ni firmware ni mjerenje nisu
imali problem.

**Uzrok.** Ime „25 minuta" je iz vremena kad je commissioning bio kraći. Puni
tok `SETTLE → CENTER (10) → DERIVE (44) → VERIFY (22) → MONITORING` sam po sebi
traje oko 14 minuta, pa uz 11 uslova plana više ne staje u 1 500 s.

**Rješenje.** Deadline je isključen: `hard_deadline_seconds: null`,
`monitoring_start_guard_seconds: 0`, a limit pokušaja podignut `3 → 5`.
Razlog i obim promjene su upisani kao `recovery_amendment` blok u
`pc/config/guided25_workflow_v1.json`, uz bump `v1.1.0 → v1.2.0` i
`target_anomalies_used_for_fit: false`. Panel (`asd_panel.py`), launcher
(`guided25_launcher.ps1`), `start_fan_run.py` i `pc/asd/guided_test.py` sada
tretiraju deadline kao opcion — kad ga nema, nadzorni thread se ne pokreće i
preflight ga ne traži.

**Dokaz.** Runovi 27.08. traju `1 509 s` i `2 000 s` i oba su završena planski,
bez `guided25_hard_deadline` prekida.

---

## Slijepe ulice i odbačene ideje

| Ideja | Zašto je odbačena |
|---|---|
| Snimak preko FAT particije + `parttool` + `fatfsparse.py` | Čita se cijela particija od 20 MB preko serijskog (~7 min) da bi se izvukao fajl od 160 KB. Base64 preko konzole je 20× brži. |
| Podizanje brzine konzole na 921600 radi bržeg dumpa | Mijenja `sdkconfig` za sve modove i rizikuje da postojeći eval tok (već validiran) prestane raditi. 19 s dumpa nije usko grlo. |
| Oslanjanje na score iz živog rada kao provjeru mikrofona | Vidi [P3](#p3) — konstantan score izgleda ispravno. Bring-up mora gledati sirovu statistiku signala. |
