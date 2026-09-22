# E5 — protokol za ovu mjernu ploču

Datum: 21.09.2026. Grana: `measurement/e5-ina226`.
Izvorni zahtjevi: `plan-master-rada.md` §6.2 i
`radno/elektronika/e5-mjerenje-01-rezultat.md`, eksperimenti A–F.
Stvarno prijavljena topologija je u **POVEZIVANJE.md** u ovom folderu.
Svi novi snimci idu u `runs/<UTC vrijeme>/`; stari rezultati se ne prepisuju.

## Napajanje za ovu postavku

**5,00 V na ulaz mjerne ploče koji vodi na AMS1117 VIN; limit 0,30 A.**
AMS1117 VOUT mora biti verzija/izlaz 3,3 V. Izlaz ploče ide iza šanta na ESP32 3V3.
5 V se nikad ne vodi na ESP32 3V3 niti direktno na INA IN+/IN−/VCC.
Ako kasnije koristimo direktno INA IN+, to je druga postavka: 3,30 V uz
odvajanje izlaza AMS1117 od tog čvora, ne paralelno vezivanje izvora.

Prvo sa ugašenim izvorom odspojiti ESP32 napajanje od mjerne ploče, izvući
USB kablove ESP32, provjeriti kratke spojeve, pa napajati samo mjernu ploču.
Multimetar: izlaz INA IN− prema GND približno 3,3 V. Tek poslije toga izvor
OFF, povezati ESP32 3V3/GND, I2C i UART pa uključiti. Ako CC ili reset:
OFF i provjera spojeva/padova napona; ne povećavati limit naslijepo.
0,50 A je eventualni limit tek poslije provjere i ako je 0,30 A stvarno nedovoljno.
Ne podizati napon ka 3,6 V iz starog testa C: to nije cilj ovog protokola.
Bez dodatnog 470 µF; to ne znači uklanjanje ugrađenih kondenzatora modula.

UART (USB-TTL sa 3,3 V signalima): ESP GPIO43 TX → adapter RX;
ESP GPIO44 RX ← adapter TX za komande; zajednički GND.
Adapter VCC/5V/3V3/DTR/RTS nepovezani. 115200, 8N1.

## Šta mjerni firmware mijenja

Model, matrice, pragovi, audio obrada i politike ostaju isti fajlovi.
Build flag ASD_E5_MEASURE dodaje senzor i linker wrappers oko već postojećih
poziva; iste funkcije dobijaju iste argumente i vraćaju iste rezultate.
Markeri GPIO12=čekanje/čitanje audio bloka, GPIO13=PSD DSP,
GPIO14=Mahalanobis score; nisko=ostali rad glavne petlje.
Ovi pinovi su rezervisani za analizator i ne smiju imati drugi teret.
Oznaka CAPTURE_WAIT ne tvrdi da se I2S zaustavlja van nje: I2S radi na drugom jezgru.

E5CHECK: deset očitanja, razmak oko 100 ms; identitet i konfiguracija provjereni pri bootu.
E5RUN: 60 s uzoraka u unaprijed izdvojenom PSRAM baferu, zatim automatski ispis.
E5STOP: prekid uz očuvanje prikupljenih uzoraka; skraćen run nije pun eksperiment.
E5DUMP: ponovni ispis posljednjeg RAM bafera dok ploča nije resetovana.
E5ARM: armira jedno mjerenje za sljedeći POWERON; čeka 15 s pa mjeri 60 s.
E5ARM1800: ista procedura, čeka 1800 s (dozvoljeno 5–3600), npr. dok se
fizičkim tasterom pokrene učenje i sačeka stabilan nadzor.
E5DISARM: poništava armiranje; E5STOP prekida i odbrojavanje.
E5SAVED: čita posljednji trajno sačuvani run, uključujući poslije prekida napajanja.
Armiranje koristi samo novu NVS oblast imena e5_measure i ključ delay_s;
ni ASD profil ni stari INA226 test namespace se ne mijenjaju niti brišu.
Armiranje se troši samo na POWERON, ali firmware ne može dokazati koji ga
izvor napaja — korisnik mora potvrditi da su oba USB priključka ESP32 prazna.

Svi sirovi uzorci se poslije mjernog intervala čuvaju u posljednja slobodna
2 MiB flash-a (0x1E00000–0x1FFFFFF), uz CRC zaglavlja i podataka. Prije prve
upotrebe ta oblast je pročitana, sačuvana u backup/ i provjerena kao potpuno
prazna (0xFF). Registracija provjerava preklapanje postojećih particija;
ne mijenja se tabela particija ni FAT klipovi. Nepoznat sadržaj se ne briše.
Novi run zamjenjuje prethodni E5 run: prvo preuzeti prethodni na PC.
Upis u flash je van mjerenih 60 s. Sačekati E5SAVE result=ESP_OK, ili bez
analizatora bar još 30 s nakon mjernog intervala, prije gašenja.
Prekinut upis ne prolazi CRC; takav rezultat nije validan i traži oporavak
isključivo ove rezervisane oblasti iz njene rezervne kopije.
Postojeća ASD telemetrija i LED i dalje rade i ulaze u potrošnju kompletnog uređaja.

INA226: R100 nominalno 0,1 Ω, CAL=1024, Current_LSB=50 µA.
Jednokratne konverzije AVG=1, bus/shunt po 1,1 ms, config 0x4123.
Timer čeka 2,5 ms, zatim provjerava conversion-ready. Četiri registra ostaju
stabilna do sljedećeg okidanja. Stvarna učestanost zavisi od I2C i raspoređivanja;
računa se iz vremena, ne proglašava unaprijed 450 Hz. I2C je 100 kHz.
Nema UART ispisa svakog E5 uzorka tokom mjernih 60 s; ispis dolazi poslije.
Overflow, komunikaciona greška ili pun bafer prekidaju mjerenje sa errors>0.

## A/B — električna provjera prije rezultata

1. E5CHECK preko USB služi samo za registre i komunikaciju. Struja nije potrošnja ESP32.
2. Na eksternom izvoru snimiti E5CHECK preko UART-a.
3. Multimetrom direktno na modulima izmjeriti:
   - INA GND ↔ ESP GND (cilj 0–2 mV; >20 mV traži otklanjanje greške).
   - INA VBS ↔ INA GND, i ESP 3V3 ↔ ESP GND.
   - AMS VOUT/INA IN+ ↔ GND i INA IN− ↔ GND.
   - pad od AMS VOUT do INA IN+ i povratne mase, odvojeno od šanta.
4. Uporediti INA VBUS s multimetrom: unaprijed zadan kriterij ±10 mV,
   uz upis modela/rezolucije instrumenta. Ako ne prolazi, nema validne energije.
5. Struju tereta provjeriti nezavisnim instrumentom u istoj grani.
   Displej 5 V izvora uključuje AMS1117 i INA VCC prije šanta: nije direktna
   referenca za ESP struju! Ne izjednačavati te dvije vrijednosti.
   DMM strujni opseg se umeće serijski sa isključenim napajanjem;
   nikad ampermetar paralelno između 3V3 i GND. Njegov burden napon zabilježiti.
6. Kriterij iz starog plana 'ukupan pad <5 mV' razdvojiti: šant ima namjerni
   I×0,1 Ω pad (10 mV na 100 mA). Cilj za kontakte/žice je <5 mV mimo šanta.

Ako B ne riješi grešku, C mjeri linearnost na bezbjednim naponima samo uz
posebno pripremljen direktni 3,3 V izvor. Nije dozvoljeno okretati 5 V ulaz
AMS1117 očekujući da izlaz prati te promjene linearno.

## D — primarni 60 s blokovi (najmanje tri ponavljanja)

Uslove zamrznuti: isti izvor, mikrofon, udaljenost ventilatora, brzina,
LED, dodatni kondenzatori, 240 MHz, 16 MB PSRAM, WiFi/BT bez upotrebe.
Zapisati sobu, instrumente, izmjerene napone, temperaturu regulatora ako dostupna.

1. **IDLE_WITH_I2S**: čeka taster; I2S u ovom firmwareu već radi. Ovo nije deep sleep
   niti istorijski idle bez audio drajvera. E5RUN ×3.
2. **LEARNING**: stabilan normalni ventilator, fizički taster ili PRESS,
   E5RUN tokom učenja. Sačuvati i QUALITY/COMMISSION log, imenovati stvarnu fazu.
3. **MONITOR_NORMAL**: tek nakon prihvaćene kalibracije; E5RUN ×3.
4. **MONITOR_ANOMALY** opciono: postojeći protokol promjene protoka, poslije
   završene kalibracije; nikad koristiti anomaliju za fit ili mijenjati prag.
5. **Overhead**: ista IDLE_WITH_I2S postavka, nezavisnim instrumentom uporediti
   60 s bez E5RUN i sa E5RUN; najmanje tri para. Bez eksternog instrumenta
   ne možemo izmjeriti potrošnju ugašenog samomjera — označiti kao nedostajuće.

Integracija trapezima U×I na stvarnim vremenima daje procjenu ukupne energije
pokrivenog intervala. Izvještaj navodi učestanost, rupe, napon, struju i trajanje.
Granice faza i pozadinski I2S sprečavaju tumačenje zbirne potrošnje kao
izolovane potrošnje samo DSP-a/inference. Uzorci/intervali koji prelaze granicu
ostaju MIXED; ne raspodjeljuju se proizvoljno. GPIO analizator daje trajanje,
ne veću vremensku rezoluciju INA226 struje.

**Energija jedne veoma kratke Mahalanobis inference nije razriješena ovom
instrumentacijom.** Za nju treba zaseban kontrolisani ponavljani workload
na zamrznutom ulazu, uz nezavisno mjerenje idle razlike; nije dozvoljeno
izmisliti J/inferenca iz jednog uzorka koji preklapa više faza.
Originalni E (neuronski/PSD i SRAM/PSRAM poređenje), čisti capture-only/DSP-only
bench i projekcija duty-cycle baterije ostaju zasebni eksperimenti sa svojim
buildovima. Ova grana priprema prvi validan mjerni put za postojeći finalni model;
ne tvrdi da je cijela izvorna E5 matrica time završena.

## Pokretanje alata

Iz korijena repoa, Python sa pyserial:

```powershell
python pc/tools/e5_capture.py --port COM3 --transport usb --command E5CHECK
python pc/tools/e5_capture.py --port COM7 --transport uart --command E5CHECK --external-power --supply-v 5 --notes "zamijeni COM7 stvarnim UART portom"
python pc/tools/e5_capture.py --port COM7 --transport uart --command E5RUN --external-power --supply-v 5 --case IDLE_WITH_I2S
```

Posljednja komanda namjerno još daje diagnostic_only dok nema nezavisnih
referenci. Dodati `--wiring-verified --dmm-v <izmjereno> --reference-current-ma
<izmjereno> --reference-tolerance-ma <tolerancija instrumenta>` tek poslije
stvarne provjere. Ne unositi očekivane vrijednosti umjesto mjerenih.
Sačekati E5END i zapis summary.json prije gašenja napajanja.
Pun ispis može potrajati nekoliko minuta na 115200 baud; uzorkovanje traje 60 s.

### Korisnikova varijanta: logički analizator umjesto USB–TTL adaptera

Analizator GND → ESP GND, jedan ulaz → GPIO43/TX; dekoder UART 115200 8N1,
normalna polarizacija (idle high), preporučeno uzorkovanje najmanje 2 MHz.
Analizator mora podržavati 3,3 V ulaze. Njegov USB ide u laptop; nijedan
napojni izlaz se ne veže na ESP. Po želji dodatni ulazi → GPIO12/13/14 za markere.
Analizator uglavnom ne šalje komande, zato koristimo armiranje i trajni zapis:

1. Dok je samo USB na ESP: `python pc/tools/e5_capture.py --port COM3 --transport usb --command E5ARM`.
2. Potvrditi E5ARM result=ESP_OK. Isključiti USB sa ESP-a; izvor i dalje OFF.
3. Spojiti provjerenu mjernu ploču i analizator. Uključiti snimanje analizatora,
   pa izvor 5,00 V / limit 0,30 A. Firmware čeka 15 s, mjeri 60 s, zatim čuva.
4. Prvi run je IDLE_WITH_I2S, bez pritiskanja tastera. Ne gasiti izvor dok
   zapis nije potvrđen; za prvi pokušaj ostaviti najmanje 120 s od uključenja.
5. Izvor OFF, odvojiti eksterno napajanje, tek zatim vratiti ESP USB.
6. `python pc/tools/e5_capture.py --port COM3 --transport usb --command E5SAVED --external-power --case IDLE_WITH_I2S`.
   `--external-power` ovdje opisuje napajanje TOKOM mjerenja, ne tokom USB preuzimanja.
   Dodati stvarne nezavisne reference kao gore; bez njih ostaje diagnostic_only.

Na početku se armiranje ne aktivira automatski dok korisnik nije spreman.

## Povratak i izvori

Backup originalne aplikacije je `backup/original-app.bin`; SHA-256 u manifest.json
mora odgovarati ranije validiranom binaru. Vraća se samo na 0x10000, bez erase_flash,
bez promjene bootloadera, particija i NVS-a. BUILD.ps1 samo kompajlira.

Tehnička referenca za registre/jedinice/ready flag:
[TI INA226 datasheet](https://www.ti.com/lit/ds/symlink/ina226.pdf).

Naknadno dodavanje stvarnih referentnih očitanja bez mijenjanja sirovog snimka:

```powershell
python pc/tools/e5_capture.py --analyze-run results/mjerenje_2026-09-21/runs/ODABRANI_RUN --wiring-verified --dmm-v IZMJERENI_NAPON --reference-current-ma IZMJERENA_STRUJA --reference-tolerance-ma TOLERANCIJA --notes "instrument, uslovi i vrijeme referentnog mjerenja"
```

PLACEHOLDER vrijednosti zamijeniti stvarnim brojkama. Nastaje novi review-*.json;
metadata.json, serial.raw i serial.log ostaju nepromijenjeni. Električna validacija
ne potvrđuje automatski označeno stanje modela: za to sačuvati odvojeni log
analizatora i njegove vremenske oznake.
