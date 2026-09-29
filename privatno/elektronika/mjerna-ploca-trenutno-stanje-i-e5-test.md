# Mjerna ploča — stanje, povezivanje i E5 test

**Ažurirano 28.09.2026.** Priprema od 21–22.09. i današnja potvrda korisnika.

## Trenutno stanje i plan dvije cjeline

**Dugme, AMS1117, INA226 i mikrofon povezani su sa ESP32-S3 prema tabelama
ispod. Dodatni kondenzatori, diode/LED i otpornici nisu povezani nigdje.**
Fabrički ugrađene komponente modula se ne uklanjaju.

- **Uređaj:** ESP32-S3 na protobordu MB-102, INMP441 i dugme.
- **Mjerna ploča 4 × 6 cm (A1938):** AMS1117 i INA226, četiri veze ka ESP-u.
- Novija odluka od 02.09. ostavlja uređaj na protobordu. Stara zasebna
  zalemljena ploča U 100 × 50 mm ostaje opcija. LED i dugme su planirani
  na 3D držaču; LED još nisu povezane.

Posljednja provjera: USB napajanje, INA226 odgovara na **0x44**, audio radi.
Dugme je fizički povezano, ali njegov rad treba potvrditi pritiskom uz log.
**Spoljašnje napajanje i novo mjerenje energije tek slijede.**

## Tačne veze mjerne ploče

| Od | Do |
|---|---|
| Spoljašnji izvor **+5,00 V**, tek priključiti | AMS1117 VIN / IN+ |
| Minus izvora i oba GND priključka AMS modula | Zajednički GND |
| AMS1117 VOUT / OUT+ ≈ 3,3 V | INA226 **IN+ i VCC** |
| INA226 **IN−** | INA226 **VBS** i izlaz 1 → ESP **3V3** |
| Zajednička masa, uključujući INA GND | Izlaz 2 → ESP **GND** |
| INA226 SDA | Izlaz 3 → ESP **GPIO8** |
| INA226 SCL | Izlaz 4 → ESP **GPIO9** |
| INA226 ALE | Nepovezan |

```text
5 V → AMS1117 → INA IN+ → [R100 šant 0,1 Ω] → INA IN− → ESP 3V3
                   │                            │
                INA VCC                      INA VBS
minus izvora ───────── zajednički GND ───────────────── ESP GND
```

**IN− senzora nije masa. IN+ i IN− ne premošćivati žicom.** VCC je prije
šanta, VBS poslije njega. To ima prednost nad starim avgustovskim šemama.
Mjerimo sklop iza šanta; gubici AMS1117 i napajanje INA VCC nisu uključeni.
3V3 i GND voditi kratko direktno na ESP pinove, bez glavnog strujnog puta
kroz napojne šine protoborda.

## Mikrofon, dugme i plan LED

| Dio | Veza |
|---|---|
| INMP441 VDD | ESP 3V3, iza šanta |
| INMP441 GND i L/R | GND |
| SCK/BCLK; WS/LRCL; SD/DOUT | **GPIO4; GPIO5; GPIO6** |
| Dugme | **GPIO10 → taster → GND**, interni pull-up |
| Zelena LED — još nije povezana | GPIO2 → **100 Ω** → anoda LED; katoda → GND |
| Crvena LED — još nije povezana | GPIO11 → **330 Ω** → anoda LED; katoda → GND |

Mikrofonske žice držati kraćim od 10 cm. Dugme ostaviti otpušteno pri bootu;
u normalnom radu pokreće učenje. Prvi E5 test radi bez pritiska dugmeta.
LED otpornici su vrijednosti iz plana za predviđene LED: provjeriti tip i
polaritet prije ugradnje. LED ne spajati bez otpornika. Mogu ostati
nepovezane za prvi test; njihovo kasnije dodavanje mijenja potrošnju.

## Kondenzatori koje imamo: gdje idu i šta ne povezujemo

Prema inventaru imamo **470 nF keramiku (A2400)** i **10 µF / 470 µF
 elektrolite iz seta A642K**. Trenutno nijedan dodatni nije povezan.

| Dio | Plan | Zašto |
|---|---|---|
| **470 nF keramika** | Dodati direktno uz mikrofon između **VDD i GND**, bez polariteta | Lokalno filtriranje napajanja |
| **10 µF elektrolit** | Dodati paralelno uz keramiku: **plus VDD, minus GND** | Lokalna rezerva napajanja mikrofona |
| **470 µF elektrolit** | **NE povezivati za planirano mjerenje**, prema odluci korisnika | Ublažava kratke strujne vrhove iza šanta koje želimo pratiti |

```text
INMP441 VDD ──┬── 470 nF ──┬── INMP441 GND
              └── +10 µF− ─┘
```

470 nF i 10 µF idu **paralelno, na padove mikrofona**, ne na udaljeni kraj
žica. Spajati uz ugašeno napajanje i izvučen USB. Pruga elektrolita označava
minus; provjeriti oznaku i koristiti nazivni napon veći od 3,3 V.

I mali kondenzatori utiču na brze promjene struje, ali su predviđeni kao dio
stabilnog napajanja mikrofona. **Zabilježiti njihovo dodavanje i zadržati
istu konfiguraciju u svim ponavljanjima.** Ako još nisu dodati u trenutku
testa, zapisati da je mjeren sklop bez njih.

**470 µF ostaje vani.** Ako dolazi do resetovanja, prekinuti test i provjeriti
izvor, kontakte i padove napona. Eventualni kasniji test sa 470 µF bio bi
zasebna konfiguracija: plus INA IN−, minus GND. Ublažavanje vrhova ne znači
automatski pogrešnu ukupnu energiju dugog stabilnog intervala, ali mijenja
vremenski oblik struje. Fabričke kondenzatore na modulima ne skidati.

## Spoljašnje napajanje i UART

**Za ovu šemu: 5,00 V na AMS1117 VIN, početni limit 0,30 A.** Limit nije
zadavanje stvarne potrošnje. **5 V nikad direktno na ESP 3V3 ili INA
IN+/IN−/VCC.** Oba USB priključka ESP-a ostaju prazna tokom eksternog testa.

Prvo, uz izvor OFF, odvojiti ESP od mjerne ploče i provjeriti veze/polaritet.
Napajati samo mjernu ploču i multimetrom potvrditi približno **3,3 V između
INA IN− i GND**. Zatim OFF, povezati ESP i analizator, pa uključiti sklop.
Kod CC režima, zagrijavanja ili resetovanja: OFF i provjera, bez naslijepog
povećavanja limita. Stara opcija 3,30 V direktno na INA IN+ zahtijeva
odvajanje izlaza AMS1117; nije ova postavka.

**Logički analizator:** GND → ESP GND, ulaz → **GPIO43/TX**, USB analizatora
→ laptop. Ne dovoditi njegovo napajanje na ESP. UART **115200, 8N1, idle
high**, ulaz kompatibilan sa 3,3 V; preporučeno uzorkovanje ≥2 MHz.
Analizator sluša, ne šalje komande, pa koristimo armiranje i kasnije USB
preuzimanje. USB–TTL nije potreban za izabrani postupak.

Opciono analizator prati **GPIO12 = CAPTURE_WAIT, GPIO13 = DSP, GPIO14 =
SCORE**. Markeri jesu implementirani u septembarskom E5 dodatku, ali još
nisu fizički provjereni. Analizator daje vremena; INA226 daje struju/napon.

## Naredni test: 60 s IDLE_WITH_I2S

Cilj je provjera mjernog puta, pa potrošnja tokom **60 s čekanja na dugme,
uz aktivan I2S**. To nije deep sleep. E5 firmware je pripremljen 22.09;
prema sačuvanom izvještaju build i 82 relevantna testa su prošli, ali
**nije još potvrđen flash ni provjera na ploči**. Stari firmware samim
priključivanjem UART-a ne daje E5 energiju.

Komande su uputstvo za naredni rad, nisu izvršene pri pisanju dokumenta.
Pokretati iz korijena repoa, Python sa pyserial; COM3 zamijeniti stvarnim
portom. Prvo samo USB na ESP, spoljašnji izvor odspojen:

```powershell
.\results\mjerenje_2026-09-21\FLASH.ps1 -Port COM3
python pc/tools/e5_capture.py --port COM3 --transport usb --command E5CHECK
python pc/tools/e5_capture.py --port COM3 --transport usb --command E5RUN --case USB_PIPELINE_TEST
```

FLASH pravi backup i provjerava upis aplikacije. Očekivati deset CHECK
uzoraka. Za RUN sačekati 60 s, **E5SAVE result=ESP_OK** i **E5END**.
Tek tada izvući/vratiti USB i provjeriti sačuvane uzorke:

```powershell
python pc/tools/e5_capture.py --port COM3 --transport usb --command E5SAVED --case USB_RELOAD_TEST
```

CSV mora biti isti. USB run je dijagnostika, nije validna potrošnja kroz
šant. Potvrditi fizičko dugme i audio bez grešaka. Nakon uspješne provjere:

1. Još na USB-u armirati:

   ```powershell
   python pc/tools/e5_capture.py --port COM3 --transport usb --command E5ARM
   ```

2. Potvrditi **E5ARM result=ESP_OK**, izvući USB; izvor ostaje OFF.
3. Povezati provjerenu mjernu ploču i analizator. Pokrenuti snimanje
   analizatora, pa izvor **5,00 V / limit 0,30 A**.
4. Bez dugmeta: **15 s čekanja + 60 s mjerenja**, pa čuvanje.
   Sačekati **E5SAVE result=ESP_OK**; za prvi pokušaj ostaviti najmanje
   120 s od uključenja. Pun UART ispis može trajati nekoliko minuta.
5. Izvor OFF i odspojen, vratiti USB, pa preuzeti:

   ```powershell
   python pc/tools/e5_capture.py --port COM3 --transport usb --command E5SAVED --external-power --supply-v 5 --case IDLE_WITH_I2S
   ```

`--external-power` opisuje napajanje tokom mjerenja, ne USB preuzimanja.
Armiranje važi za POWERON; običan reset nije zamjena. `E5DISARM` otkazuje
armiranje. Novi run zamjenjuje prethodni sačuvani run: prvo ga preuzeti.

## Kada rezultat prihvatamo i šta dalje

- Zapisati stvarno stanje 470 nF/10 µF, **bez 470 µF**, te bez LED/otpornika
  dok nisu ugrađeni. Zabilježiti instrumente i uslove.
- Multimetrom provjeriti VBS–GND i ESP 3V3–GND; cilj slaganja INA napona
  sa multimetrom je **±10 mV**. Provjeriti padove vodova i razliku masa.
- Nezavisno provjeriti struju iste grane iza šanta; struja na displeju
  5 V izvora uključuje i potrošače prije šanta. Ampermetar ide serijski
  uz ugašeno napajanje, nikad paralelno između 3V3 i GND.
- Punih 60 s, bez resetovanja i mjernih grešaka, sa uspješnim čuvanjem.

Bez nezavisnih referenci alat ostavlja **diagnostic_only**. Tek nakon
provjere dodati stvarne `--wiring-verified`, `--dmm-v`,
`--reference-current-ma` i `--reference-tolerance-ma` podatke prema protokolu.
Rezultati idu u `results/mjerenje_2026-09-21/runs/<UTC vrijeme>/`;
sačuvati i snimak analizatora.

Nakon prvog uspjeha: najmanje tri ponavljanja za čekanje, učenje i normalni
nadzor u istoj konfiguraciji; zasebno provjeriti potrošnju mjernog dodatka.
Ovaj test ne razrješava energiju pojedinačne vrlo kratke inference:
GPIO markeri ne povećavaju vremensku rezoluciju INA226.

## Izvori

- [Prijavljeno povezivanje 21.09.](../../results/mjerenje_2026-09-21/POVEZIVANJE.md)
- [Priprema 22.09. i nalazi](../../results/mjerenje_2026-09-21/README.md)
- [Detaljan protokol i referentna mjerenja](../../results/mjerenje_2026-09-21/EXPERIMENT.md)
- [Plan dvije ploče](plan-dvije-plocice.md) i [novija odluka za protobord](uredjaj-na-protobordu.md)
- [Šema sklopa](sema-sklopa.pdf) — nacrtane komponente nisu dokaz ugradnje
- [Pin-mapa firmwarea](../../firmware/esp32s3_asd/main/pins.h)
