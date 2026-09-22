# Spremno za nastavak kada ploča bude dostupna

Radni folder: `Documents\master rad\esp32s3\results\mjerenje_2026-09-21`.
Git grana: `measurement/e5-ina226`. Model i audio algoritam nisu mijenjani.

**Novi mjerni firmware još nije fizički provjeren na ploči.** USB/audio logovi
od 21.09. nastali su na starom firmwareu. Oni nisu dokaz za novi mjerni dodatak.

## 1. Prvi flash i USB provjera (bez eksternog napajanja)

Ploča preko USB-a, power supply odspojen. Iz korijena repoa u PowerShell-u:

```powershell
.\results\mjerenje_2026-09-21\FLASH.ps1 -Port COM3
python pc/tools/e5_capture.py --port COM3 --transport usb --command E5CHECK
```

Stvarni port provjeriti; COM3 je prethodni native USB port. FLASH prvo pravi novu
rezervnu kopiju, upisuje samo aplikaciju i provjerava pročitani flash.
Očekivano: INA226 ID 0x5449/0x2260, adresa 0x44, config readback 0x4527,
cal=1024, deset E5CHECK redova i E5CHECK_END. Ne tumačiti USB struju kao potrošnju ESP32.

## 2. Provjera snimanja i čuvanja dok je još samo USB

```powershell
python pc/tools/e5_capture.py --port COM3 --transport usb --command E5RUN --case USB_PIPELINE_TEST
```

Sačekati 60 s mjerenja, `E5SAVE result=ESP_OK`, zatim kompletan `E5END`.
Ovaj run ostaje diagnostic_only. Izvući i vratiti USB tek poslije čuvanja,
pa pročitati `E5SAVED` i potvrditi da su CSV uzorci identični:

```powershell
python pc/tools/e5_capture.py --port COM3 --transport usb --command E5SAVED --case USB_RELOAD_TEST
```

Posebno provjeriti mikrofon i fizičko dugme uz log, kao i da pri uključenom
sampleru nema audio timeouta/dropped uzoraka u mjernom intervalu. Pisanje flash-a
poslije intervala može poremetiti kontinuiranu audio sesiju; to zabilježiti i
ne uključivati u izmjerenih 60 s. Kalibraciju/model ne mijenjati radi prolaza testa.

## 3. Priprema power supplyja i analizatora

Za tvoju potvrđenu šemu, ulaz mjerne ploče vodi na **AMS1117 VIN**:

**5,00 V; početni strujni limit 0,30 A.** To nije zadavanje stvarne potrošnje.
GND izvora → zajednička masa. 5 V ne smije doći na ESP32 3V3.
Dok je ESP odspojen, napajati samo mjernu ploču i multimetrom potvrditi
približno 3,3 V na izlazu INA IN− prema GND. Isključiti izvor prije povezivanja ESP-a.

Logički analizator: GND → ESP GND; kanal → **GPIO43/TX**; UART **115200, 8N1**,
idle high. Njegov USB ide u laptop. Nikakvo napajanje s analizatora na ESP.
Opciono kanali na GPIO12/13/14 za markere. Oba USB priključka na ESP32 su prazna.

## 4. Prvi eksterni run

Još na USB-u armirati:

```powershell
python pc/tools/e5_capture.py --port COM3 --transport usb --command E5ARM
```

Tek nakon `E5ARM result=ESP_OK`: USB iz ESP-a vani, izvor OFF, povezati mjernu
ploču i analizator; uključiti snimanje analizatora pa power supply.
Prvi run radi bez pritiska dugmeta: 15 s čekanja + 60 s IDLE_WITH_I2S mjerenja.
Sačekati potvrdu čuvanja, odnosno za prvi pokušaj bar 120 s od uključenja.
Ako CC, zagrijavanje ili ponovljeni reset: izvor OFF, provjera spojeva.

Poslije: izvor OFF i odspojen → vratiti USB na ESP → preuzeti rezultat:

```powershell
python pc/tools/e5_capture.py --port COM3 --transport usb --command E5SAVED --external-power --case IDLE_WITH_I2S
```

Za struju/energiju za rad moraju proći nezavisna provjera napona i struje;
vidi **EXPERIMENT.md**. Bez tih očitanja alat namjerno ne daje validan rezultat energije.
Tamo su i tri ponavljanja po stanju, test dodatne potrošnje samog mjerenja,
učenje/nadzor, ograničenja po fazama i šta ostaje za proširenu E5 matricu.

## Ostalo

- `POVEZIVANJE.md`: tačno prijavljeno ožičenje, uključujući VCC prije šanta i bez dodatnog kondenzatora.
- `backup/`: originalna aplikacija i flash kopije, lokalno; binarne kopije nisu na GitHubu.
- `runs/`: svi naredni sirovi logovi, CSV, metapodaci i izvještaji.
- `BUILD.ps1`: ponovni build i automatska provjera modela/izrada firmware-manifest.json prije FLASH.
- Povratak stare aplikacije: `FLASH.ps1 -Port COM3 -RestoreOriginal`.
- Otkazivanje armiranja dok je USB povezan: komanda `E5DISARM` kroz isti alat.

Ne pokretati eksterni eksperiment prije prolaza USB testa novog firmwarea.
