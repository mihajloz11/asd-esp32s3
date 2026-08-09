# Hardverska verifikacija PSD detektora na ESP32-S3

**Datum:** 09.08.2026 · **Firmware mod:** `ASD_PSD_LIVE` ([psd_live.c](../firmware/esp32s3_asd/main/psd_live.c))

Ovaj dokument bilježi šta je stvarno izmjereno **na pločici**, nasuprot
benchmark brojkama nad digitalnim zvukom ([istrazivanje-psd-model.md](istrazivanje-psd-model.md)).
Kriteriji prihvatanja su postavljeni unaprijed u [odluka-finalni-model.md](odluka-finalni-model.md).

## Šta radi novi mod

Cijeli lanac iz [cilj-modela.md](cilj-modela.md), bez računara:

1. **Čekanje** ~15 s — operater pusti ventilator, uređaj mjeri nivo i javlja
   ako ne čuje ništa (brani od kalibracije na tišini, vidi [P3](problemi-i-rjesenja.md#p3)).
2. **Kalibracija** 10 × 10 s = 100 s — mjeri se samo **centar** novog primjerka;
   matrica 96×96 iz fleša se ne dira.
3. **Prag** — leave-one-out: svaki kalibracioni klip se ocjenjuje centrom koji
   **ne sadrži njega samog**, prag je 90. percentil tih score-ova.
4. **Detekcija** — neprekidno, alarm tek poslije **2 uzastopna** prozora iznad
   praga. Centar se poslije kalibracije **ne pomjera** ([P10](problemi-i-rjesenja.md#p10)).

## Kriteriji prihvatanja — rezultat

| Kriterij | Granica | Izmjereno | |
|---|---|---|---|
| Vrijeme računanja po klipu od 10 s | < 10 s | **704 ms** (rezerva 14,2×) | ✔ |
| Gubitak uzoraka | `dropped=0` | **0** kroz cijeli rad | ✔ |
| Statički RAM | staje u DIRAM | 293 KB / 342 KB (86 %), 103 KiB heap slobodno | ✔ |
| Streaming = batch račun | identično | **razlika 0,0** (bit-identično) | ✔ |
| PC↔C na DCASE WAV-u | ~1e-3 | **9,54e-07** | ✔ |
| PC↔uređaj na živom mikrofonu | ~1e-4 | **1,70e-06** (relativno 1,42e-07) | ✔ |
| Živa sekvenca normalno → kvar → normalno | prelazi jasni | **prolazi**, vidi dolje | ✔ |

### PC↔uređaj na živom mikrofonu — zašto je taj test presudan

Laboratorijski test (`pc/tests/test_psd_features_c.py`) dokazuje da se C i Python
slažu na DCASE WAV-u, ali ne i da lanac **I2S → shift → PCM** daje uređaju iste
uzorke koje PC vidi. Mod `ASD_PSD_VERIFY` snimi 10 s **živog** zvuka, izračuna
feature tačno kao živi rad i pošalje i feature i sam snimak; PC ponovi račun nad
istim uzorcima ([`psd_verify_compare.py`](../pc/tools/psd_verify_compare.py)).

```
segmenata=38  racun=727 ms  dropped=0
FNV-1a provjera snimka OK
max |PC - uredjaj| = 1,698e-06     relativno = 1,418e-07
```

**Posljedica:** front-end na uređaju je numerički tačan i na živom mikrofonu.
Sve što slijedi o slabijem rezultatu preko zvučnika je dakle **fizika kanala,
a ne greška implementacije.**

### Zašto je streaming bio potreban

Prvobitni C modul računa nad baferom od 10 s (640 KB). Da bi se FFT preklopio sa
snimanjem i da ne bi trebao taj bafer, dodat je streaming API: prozor je tačno
dva hopa (8192 = 2 × 4096), pa hop *k* zatvara segment *k−1*. Zbog te podjele
streaming daje **bit-identičan** rezultat batch računu, što je i provjereno
testom `test_psd_stream_matches_batch` — dakle ranija PC↔C verifikacija vrijedi
i za tok koji stvarno radi u firmveru.

## Živi test: kalibracija na ventilatoru koji model nije čuo

Matrica u firmveru je naučena **isključivo na source** ventilatorima. Preko
zvučnika se pušta **target** ventilator — drugi fizički primjerak, prvi put ga
uređaj čuje. Alat: [`pc/tools/psd_live_demo.py`](../pc/tools/psd_live_demo.py).
Klipovi za kalibraciju i klipovi za ocjenu se **ne preklapaju**.

### Prolaz 1 — miješane brzine, jačina zvuka 42 %

| Faza | Score (sredina) | Ponašanje |
|---|---:|---|
| Normalan rad | 1789 | bez alarma (osim jednog šava, vidi [P13](problemi-i-rjesenja.md#p13)) |
| **Anomalija** | 3527 | **ALARM** od 4. prozora anomalije, drži se do kraja |
| Povratak na normalno | ~1400 | alarm se **povlači** u prvom čistom prozoru |
| Zvuk isključen (mašina stala) | 12 380 – 25 486 | alarm, nedvosmisleno |

- Prag izračunat na uređaju: 1887 (LOO sredina 1132, sd 599)
- **AUC preko zraka: 0,716** (9 normalnih vs 9 anomalnih čistih prozora)
- Bez prozora na šavu klipova različitih brzina: **0,778**

Sekvenca koju je trebalo pokazati — *kalibriši na novom ventilatoru → detektuj
sam, bez računara* — **radi**. Prelazi su jasni i u oba smjera.

### Prolaz 2 — jedna brzina (`spd_1`), jačina zvuka 85 %

Podizanje jačine je trebalo popraviti odnos signal/šum (nivo −57 → −44 dBFS),
ali je rezultat bio **lošiji: AUC 0,476**. Uzrok se vidi u nivoima: prozori sa
score 42 021 i 70 590 imaju nivo −40 i −34 dBFS, dok su ostali na −44.
Najvjerovatnije objašnjenje je **izobličenje zvučnika laptopa** na visokoj
jačini: PSD front-end je namjerno osjetljiv na fine spektralne linije, pa
harmonike koje zvučnik sam doda vidi kao veliko odstupanje.

Zaključak: jačina reprodukcije je konfaund, a ne parametar koji treba
maksimizovati.

### Prolaz 3 — jedna brzina, jačina 45 %, popravljen prag

| Prozor | Score | Istina |
|---|---:|---|
| 1–5 | 316–561 | normalan rad |
| 7–15 | 245–1202 | **anomalija** |
| 17–18 | 347–488 | normalan rad |
| 19–21 | 10 486 – 22 152 | zvuk isključen (mašina stala) |

- Prag 879 (sredina + 3σ), alarm poslije 3 uzastopna prozora
- **Lažnih alarma: 0.** Kalibracija znatno mirnija (LOO 211–705).
- **Uhvaćenih suptilnih anomalija: 0** — score anomalije (medijana 541) se
  preklapa sa normalnim (medijana 397).
- Zaustavljena mašina: alarm, nedvosmisleno.
- AUC preko zraka: **0,635**

### Sva tri prolaza zajedno

| Prolaz | Brzine | Jačina | Pravilo praga | Lažni alarmi | Uhvaćena anomalija | AUC |
|---|---|---|---|---|---|---:|
| 1 | miješane | 42 % | p90, 2 prozora | 0 čistih (1 na šavu) | **da**, od 4. prozora | **0,716** |
| 2 | `spd_1` | 85 % | p90, 2 prozora | više | da, ali i lažno | 0,476 |
| 3 | `spd_1` | 45 % | sredina+3σ, 3 prozora | **0** | ne | 0,635 |

Vidi se klasična ROC razmjena: niži prag u prolazu 1 hvata anomaliju ali propušta
lažne na šavu; viši prag u prolazu 3 je potpuno miran ali propušta suptilan kvar.
**Zaustavljena mašina se hvata u sva tri prolaza, bez izuzetka.**

### Provjerena i odbačena hipoteza

Pretpostavio sam da je uspjeh prolaza 1 možda bio artefakt **razlike u brzini**
ventilatora (kalibracija na miješanim brzinama, pa anomalni klip druge brzine
izgleda anomalno bez obzira na kvar). Provjereno na PC-u, sa digitalnim zvukom,
kalibracija i ocjena unutar iste brzine:

| Podskup | AUC |
|---|---:|
| sve brzine zajedno | 0,845 |
| samo `spd_1` | 0,809 |
| samo `spd_2` | 0,835 |
| samo `spd_3` | 0,995 |

Model detektuje kvar jednako dobro **unutar** jedne brzine. Hipoteza je
**odbačena** — razlika između PC-a i uređaja nije konfaund brzine nego
akustički kanal.

## Iskrena razlika: benchmark vs preko zraka

| | AUC |
|---|---:|
| Benchmark, digitalni zvuk, k=20 | 0,864 |
| Benchmark, digitalni zvuk, k=10 | 0,853 |
| Benchmark, digitalni zvuk, samo `spd_1` | 0,809 |
| **Na uređaju, preko zvučnika i mikrofona, k=10** | **0,635 – 0,716** |
| Na uređaju, jačina 85 % (izobličenje) | 0,476 |

### Koliko tačno kanal šteti — mjereno

Poređenje veličine score-a, isti model i isti protokol, jedina razlika je put
zvuka do featura:

| | Score normalnog rada | Score anomalije |
|---|---:|---:|
| PC, digitalni zvuk (k=10) | medijana **79** | medijana **117** |
| Uređaj, preko zvučnika | 1 300 – 4 000 | 2 500 – 4 100 |

Na PC-u anomalija pomjera score sa 79 na 117 — **razlika je oko 48 %**. Na
uređaju sam akustički kanal pravi rasipanje od nekoliko hiljada, dakle
**red veličine veće od signala koji tražimo**. Zato se AUC ruši: nije da model
ne vidi kvar, nego ga kanal zatrpa.

To je ujedno i objašnjenje zašto se **zaustavljena mašina** detektuje savršeno
(score 12 000 – 70 000): ta promjena je mnogo grublja od šuma kanala.

Ostali doprinosi, po veličini:

1. **Reprodukcija zvučnikom.** Dvostruki prolaz kroz elektroakustiku
   (zvučnik + prostorija + mikrofon) kojeg u stvarnoj primjeni **nema** —
   tamo uređaj sluša mašinu direktno.
2. **Montaža demo materijala.** [P13](problemi-i-rjesenja.md#p13) — šav dva
   klipa različite brzine je stvarna promjena zvuka, ne kvar.
3. **Buka okruženja.** Zabilježen je prozor sa score 42 021 uz istovremeni skok
   nivoa — spoljni zvuk (ventilator računara). Stvaran lažni alarm, prijavljen
   kao takav.
4. **Suptilnost DCASE anomalija.** One su namjerno na granici čujnosti; stvaran
   kvar (zaglavljena lopatica, disbalans) je grublji.

Za primjenu je zato mjerodavniji test sa **stvarnim ventilatorom i stvarnim
kvarom**, gdje nema ni zvučnika ni montaže. Ta mjerenja tek predstoje i, na
osnovu gornje tabele, očekuje se rezultat bliži benchmark brojci nego ovom.

## Šta ovo znači za cilj iz `cilj-modela.md`

| Tačka cilja | Status |
|---|---|
| Opšti model iz mnogo ispravnih ventilatora, na računaru | ✔ 990 source klipova, matrica 96×96 |
| Model prilagođen i ugrađen u firmware | ✔ 37 KB u flešu, bez TFLM-a |
| Kalibracija na **novom** ventilatoru, na licu mjesta | ✔ 100 s, mjeri se samo centar |
| Rad **bez računara**, dvostrana detekcija, alarm | ✔ radi, LED + serijski flag |
| Kalibracija se ne nastavlja tiho | ✔ centar zamrznut poslije kalibracije |
| Gruba promjena (mašina stala) | ✔ detektovano u sva tri prolaza |
| Suptilan DCASE kvar **preko zvučnika** | ✖ marginalno (AUC 0,64–0,72) |
| Suptilan DCASE kvar, digitalni zvuk | ✔ AUC 0,81–0,86 |

Arhitektura i lanac rade tačno kako je zamišljeno. Otvoreno pitanje nije više
„da li radi na pločici" nego „koliko kvar mora biti izražen da bi se čuo kroz
stvarni akustički put" — a na to odgovara test sa pravim ventilatorom.

## Popravka praga (prolaz 3)

Prolazi 1 i 2 su pokazali da je polazno pravilo — 90. percentil leave-one-out
score-ova — **sistematski prenisko**. Razlog je metodološki: kalibracioni
klipovi su snimljeni jedan za drugim, u istim uslovima, pa LOO potcjenjuje
koliko normalan rad varira **kasnije**. Izmjereno u prolazu 2: prag 1667, a
normalni prozori u detekciji dosezali 2414.

Izmjena u [psd_live.c](../firmware/esp32s3_asd/main/psd_live.c):

```
prag = max( p90(LOO) ,  sredina(LOO) + 3·sd(LOO) )
alarm = 3 uzastopna prozora iznad praga    (bilo 2)
```

Uz to se sada ispisuju i pojedinačni LOO score-ovi (`LOOALL`), da se prag može
analizirati naknadno iz loga.

Prolaz 3 (jedna brzina, jačina 45 %) — kalibracija je znatno mirnija:

```
LOOALL 705 531 299 491 250 348 453 226 211 484     (sredina ~400, sd ~160)
PRAG = 879  (p90 dao 549, sredina+3sd dao 879)
```

Ti score-ovi su reda veličine bliži PC vrijednostima (medijana 79) nego u
prolazima 1 i 2 (LOO sredina 1132 i 1328) — potvrda da su i jedna brzina i
umjerena jačina zvuka bitni za mirnu kalibraciju.

## Šta ostaje

1. **Test sa stvarnim ventilatorom i fizičkim kvarom** — glavni otvoreni posao.
2. Duža kalibracija (k=20 → 200 s) na uređaju, ako se traži još mirniji prag.
3. LED (fali otpornik 220–330 Ω) i INA226 (u kvaru) — vidi handoff.

## Kako ponoviti

```bash
set ASD_PSD_LIVE=1 && idf.py reconfigure build flash    # P1: reconfigure je obavezan
../.venv/Scripts/python.exe tools/psd_live_demo.py --port COM4 --speed spd_1
```

Za provjeru front-enda na živom mikrofonu:

```bash
set ASD_PSD_VERIFY=1 && idf.py reconfigure build flash
../.venv/Scripts/python.exe tools/psd_verify_compare.py --port COM4
```
