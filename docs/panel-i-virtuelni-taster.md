# Panel i virtuelni taster — eksperiment bez zalemljenog tastera i dioda

**Datum:** 15.08.2026, ažurirano 20.08.2026.

**Status:** istorijski v1.3 panel/taster provjeren na pločici; trenutni
v1.8/q1.5 softver host- i build-testiran, ali još nije ponovo flashovan.

Firmware traži eksplicitnu operaterovu radnju za svako učenje (P10 — tiha
rekalibracija bi naučila kvar kao normalu). Ta radnja je do sada mogla stići
samo sa tastera na GPIO10, a taster nije zalemljen. Isto važi i za drugu
stranu: uređaj javlja dokle je stigao lampicama na GPIO2/GPIO11, koje takođe
nisu zalemljene (fale otpornici 220–330 Ω).

Ovdje je opisan drugi ulaz i drugi izlaz za **iste** te signale, preko konzole.
Hardver se time ne mijenja i ne zamjenjuje: ako se taster i diode zaleme,
rade paralelno i pokazuju isto.

---

## 1. Šta je dodato

| Sloj | Šta | Fajl |
|---|---|---|
| firmware, ulaz | `PRESS` / `HOLD` sa konzole → `asd_button_event_t` | [asd_cmd.c](../firmware/esp32s3_asd/main/asd_cmd.c) |
| firmware, izlaz | `FLAGS` zapis na svaku promjenu režima lampice | [psd_live.c](../firmware/esp32s3_asd/main/psd_live.c) |
| host, komanda | `press` / `hold` u operaterskom toku | [physical_fan_experiment.py](../pc/tools/physical_fan_experiment.py) |
| host, panel | lampice i dugmad u pregledaču | [asd_panel.py](../pc/tools/asd_panel.py) |

Firmware je narastao **593 B** (`idf.py size-files`, `asd_cmd.c.obj`).

---

## 2. Ulaz — virtuelni taster ide kroz isti put kao fizički

Konzola ubacuje **samo događaj**, nikad odluku:

```c
asd_button_event_t event =
    asd_button_update(&button, gpio_get_level(PIN_BUTTON) == 0, t);
if (event == ASD_BTN_NONE)
    event = asd_cmd_take_event();     /* virtuelni taster */
```

Sve poslije te linije je zajedničko — `asd_ui_command()`, `BUTTON` zapis,
`ui_command`. Zato se dva ulaza ne mogu razići u ponašanju: pravilo da kratak
pritisak nikad ne odbacuje naučeni centar važi za oba, jer živi na jednom
mjestu. `asd_cmd.c` ne zna ni za `asd_ui_command`, ni za `emit_button`, ni za
GPIO — to je provjereno testom.

Fizički taster ima prednost: ako u istom ciklusu stigne pravi pritisak,
virtuelni ostaje da čeka sljedeći.

| Komanda | Odgovara | Značenje |
|---|---|---|
| `PRESS` | kratak pritisak | u IDLE pokreće učenje |
| `HOLD` | dug pritisak (≥ 1,5 s) | odbacuje naučeni centar, pokreće novo učenje |

Čita se sa **oba porta** — native USB (COM3, VID 303A) i CH343 most na UART0
(COM4) — direktno iz RX FIFO-a, bez instaliranja drajvera i bez VFS
preusmjeravanja. TX put ostaje netaknut, jer od njega zavisi zaključani
live protokol `asd-quality-v1.5.0`.

---

## 3. Izlaz — softverski flegovi

Na svaku promjenu režima lampice uređaj ispiše jedan red:

```
FLAGS protocol=asd-quality-v1.5.0 mode=READY state=CALIBRATED_NORMAL waiting=0
      learning=0 learned=1 anomaly=0 hold=0 fault=0 green=on red=off
```

| Fleg | 1 kad | Zelena | Crvena |
|---|---|---|---|
| `waiting` | čeka pritisak | kratak bljesak / 2 s | — |
| `learning` | uči (WAIT + CAL) | treperi 5 Hz | — |
| `learned` | naučio, nadzire | stalno svijetli | — |
| `anomaly` | **trajno odstupanje** | ugašena | svijetli |
| `hold` | opažanje privremeno nepouzdano | spor puls | —, osim ako je alarm već aktivan |
| `fault` | fail-closed stop | dupli bljesak | dupli bljesak |

`learned` ostaje 1 i tokom alarma — centar je i dalje naučen; `anomaly` je ono
što se mijenja.

**Alarm kasni namjerno.** Traži **tri uzastopna pouzdana prozora** iznad
apsolutnog `threshold_enter`, dakle oko 30 s trajne promjene, i gasi se tek
ispod zasebnog apsolutnog `threshold_exit`. Ne postoji više skriveno pravilo
`0,7× enter`. Jedan ili dva izolovana prozora ne pale alarm, ali to samo po
sebi nije dokazana zaštita od razgovora.

`OBSERVATION_HOLD` suspenduje izgradnju novog alarmnog niza, ne proglašava
normalu i ne briše već aktivan alarm ili profil. Arhitektura i UI obrazac su
implementirani, ali je numerička interference politika trenutno
`DEVELOPMENT`, `enabled=false`; zato se HOLD ne smije prikazivati kao fizički
potvrđen speech classifier.

### Zašto ovo ne može pokvariti mjerenje

`FLAGS` i `VBUTTON` su namjerno **izvan** zaključanog rječnika. Host parser ih
ne prepoznaje i preskače prije nego što uđu u lanac telemetrije, pa ne mogu
pasti između `QUALITY phase=DET` i njegovog `DET` reda i poništiti ispravan
prolaz. Ostaju u `serial.raw` i `serial.log` kao dokaz. Sam pritisak se i dalje
prijavljuje **običnim `BUTTON` redom**, isto kao fizički, pa mjerodavan zapis
operaterove radnje ne zavisi ni od čega novog.

Dvije stvari koje to drže na mjestu:
`test_virtual_button_records_cannot_invalidate_a_run` i
`test_virtual_button_shares_the_physical_button_path`
([test_physical_fan_experiment.py](../pc/tests/test_physical_fan_experiment.py)).

---

## 4. Panel

```bash
.venv\Scripts\python.exe pc\tools\asd_panel.py --port COM3
```

Otvara `http://127.0.0.1:8772/`: dvije lampice koje titraju istim obrascem kao
diode, statusni flegovi, dva dugmeta i posljednji `score / prag / uzastopnih`.

**Rezim 1 (`--port`)** — panel drži serijski port. Za bring-up i probe, kad
`physical_fan_experiment.py` ne radi.

**Rezim 2 (`--command-file`)** — port drži alat za eksperiment, panel mu
dopisuje komande i čita `serial.log` tog runa. Ovo je jedini ispravan način
tokom valjanog mjerenja, jer port smije držati samo jedan proces:

```bash
.venv\Scripts\python.exe pc\tools\asd_panel.py --command-file results\physical_fan\cmd.txt --follow results\physical_fan\run_XXXX\serial.log
```

Klik u panelu tada radi isto što i otkucano `press` u konzoli alata.

---

## 5. Istorijski provjereno na pločici, 15.08.2026

Flešovan build od 317 552 B na COM3 (native USB, `303A:1001`).
Sljedeći redovi su istorijski dokaz tadašnjeg v1.3 wire toka, ne primjer
aktuelnog live v1.4 ugovora.

**Kratak pritisak** — `PRESS` poslat sa hosta:

```
VBUTTON protocol=asd-quality-v1.3.0 source=console event=SHORT result=accepted
BUTTON  protocol=asd-quality-v1.3.0 event=SHORT mode=IDLE command=START_LEARNING discards=0
SESSION protocol=asd-quality-v1.3.0 action=STARTED source=BUTTON reason=OPERATOR_REQUEST
FLAGS   protocol=asd-quality-v1.3.0 mode=LEARNING ... green=blink_5hz red=off
WAIT 1/60 ...
```

**Dug pritisak** — klik u panelu tokom učenja: `VBUTTON ... event=LONG
result=accepted`, sesija prekinuta, `mode=IDLE` u roku od 4 s. `ABORT` se
konzumira na sljedećoj kontrolnoj tački toka, ne trenutno.

Serijski ispis se nije pokvario ni u jednom trenutku — tadašnji zaključani
v1.3 protokol je prošao kroz WAIT/CAL/DET. To nije runtime dokaz za nove
COMMISSION/PROFILE/PROFILESTORE, HOLD ili q1.5 zapise.

## 6. Vodič kroz run i pokretanje

Panel ne samo da pokazuje stanje nego i vodi mjerenje: odbrojava fazu, piše šta
operater radi, i u trenutku prelaza upisuje `condition` u command file alata.
Time se dvije stvari koje je lako promašiti sa štopericom — trajanje od najmanje
pet prozora i oznaka **prije** promjene — više ne mogu promašiti.

Sve se pokreće jednom komandom, [start_fan_run.py](../pc/tools/start_fan_run.py):
podigne alat, sačeka run direktorij, zakači panel na njegov `serial.log` i odbije
da krene ako stari panel još drži port. `--fan-id` i `--session-id` su obavezni;
launcher nikada ne nasljeđuje istorijski `fan01` kao podrazumijevani uređaj.

Panel prikazuje centralni K1 razlog i server-side odbija `/start` ako
kalibracija nije prihvaćena; disabled dugme u browseru nije sigurnosna granica.
`nan`/`inf` iz oštećene telemetrije nikada se ne zadržavaju kao brojevi u stanju:
UI ostaje u `CAL_REJECTED`, pokazuje npr. `nonfinite_loo_cv`, a `/state` koristi
strict standardni JSON (`allow_nan=False`). Novi početak učenja čisti prethodni
`loo_cv`, prag, DET prikaz i odluku.

## 7. Šta još nije provjereno

1. **Ponašanje ako alat i panel oba drže port** — ne smije se raditi, ali nije
   testirano šta se desi ako se ipak pokuša.
2. Panel čita `serial.log` sa 0,3 s kašnjenja; za lampicu je to nevidljivo, za
   dugme nebitno.
3. **Rekalibracija i puna detekcija nisu izvršene uživo poslije popravki.** Oba
   puta su provjerena ponovnim puštanjem stvarno snimljene telemetrije kroz
   ispravljeni host i jediničnim testovima, ali ne i na ventilatoru koji radi —
   za to treba sljedeći fizički run.
4. Browser panel nema zaseban dokaz stvarnog HOLD ulaza; firmware/operator
   testovi pokrivaju obrazac, dok je numeric HOLD policy još isključen.
5. NVS restore, cold/warm start, prekid napajanja i q1.5 bounded-audio terminalni
   tok nisu provjereni sa ovim panelom na pločici.
