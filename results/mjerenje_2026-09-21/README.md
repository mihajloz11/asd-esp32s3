# Mjerenje E5 — priprema završena 22.09.2026.

**Počni sa [POCNI-OVDJE.md](POCNI-OVDJE.md).**
Povezivanje je u [POVEZIVANJE.md](POVEZIVANJE.md), puni protokol u
[EXPERIMENT.md](EXPERIMENT.md). Sve se razvija na grani `measurement/e5-ina226`.

## Završene provjere bez ploče

- Build uspješan: `build-final.log`, ESP32-S3 image `firmware-e5.bin`, 381488 B.
- SHA-256: `b6691bfaeefd6f7631304cd178c47b15d9867c92cfdb80c041d0e9e1180ac2ff`.
- ESP image checksum i validation hash prolaze (`image-info.log`).
- Linkovani su svi mjerni wrapperi: audio_read_exact, PSD push/finish i score.
- 82 relevantna testa prolazi (`verification-tests.log`); protokoli/politike usklađeni.
- Zaštićeni PSD model, audio izvor i politike ostali su neizmijenjeni u odnosu
  na master. `make_manifest.py` provjerava hash prije izdavanja novog binara.
- Nije pokrenut puni naučni PSD/data suite: u lokalnom Python okruženju nedostaje
  soundfile, a DCASE skup nije dio ovog checkout-a. Stari neuspjeli pokušaj
  kolekcije je zadržan u `model-regression-tests.log`; nije uračunat u prolazne testove.
- Originalna aplikacija iz ploče je sačuvana i tačno se poklapa sa validiranim
  binarom iz 27.08.2026. (`backup/manifest.json`); raw backupi ostaju lokalni.
- Posljednja 2 MiB flash-a provjerena su prazna i backupovana prije pripreme
  trajnog čuvanja E5 uzoraka (`backup/reserved-e5-before.json`).
- `FLASH.ps1` pravi novu kopiju prije flash-a, upisuje samo app na 0x10000 i
  radi verify_flash. Bootloader, tabela particija i NVS se ne flešuju.

**Novi firmware nije flešovan niti testiran na hardveru.** Korisnik je 22.09.
tražio završetak svih priprema bez ploče. Nisu još izmjereni napon, struja ni
energija na novom firmwareu. Svi donji USB nalazi su sa STAROG firmwarea.

Za potvrđeni ulaz preko AMS1117 VIN: **5,00 V i početni limit 0,30 A**.
Prije ESP-a multimetrom potvrditi izlaz oko 3,3 V. Logički analizator samo
GND + kanal na GPIO43/TX; UART 115200 8N1. Nema USB napajanja ESP-a tokom E5.

---
# USB provjera — 21.09.2026.

## Postavka
Repo: C:\Users\mihajlo.zivkovic\Documents\master rad\esp32s3
Napajanje: samo USB na ESP32-S3; korisnik je potvrdio da eksterni izvor nije priključen.
Mjerna ploča, mikrofon i fizički taster povezani prema izjavi korisnika.
Dodatni kondenzatori nisu postavljeni prema izjavi korisnika; ugrađene komponente modula nisu pregledane.
Firmware nije mijenjan, buildovan niti flešovan.

## Dokazi i nalazi
- 01-usb-boot.log: COM3, 115200 baud; postojeći firmware, build 27.08.2026. 21:25:11, verzija on-device-verified-78-g14aaebb-.
- PSRAM: 16 MiB prepoznato, SPI SRAM memory test OK.
- INA226: uređaj odgovara na I2C adresi 0x44, SDA GPIO8, SCL GPIO9. Ovo je ACK/probe potvrda komunikacije, ne čitanje identifikacionih registara ili provjera tačnosti mjerenja.
- Pri prvom USB čitanju zabilježen USB_UART_CHIP_RESET. Nema dokaza da je to brownout; nema ponavljanja resetovanja u ostatku prvog snimka ni u audio testu.
- 02-audio-check.log: poslat PRESS nakon 5 s, zatim HOLD nakon 38 s; ukupan snimak oko 48 s. Obje komande prihvaćene.
- Četiri obrađena audio prozora: -53.0381165, -53.8618851, -53.7016907 i -53.2862015 dBFS; tonalness_proxy od 2.57302952 do 2.80838823.
- Svi zabilježeni FLAGS redovi audio testa: dropped=0 i fault=0. Nema resetovanja/panike u tom snimku.
- Test zaustavljen tokom početnog učenja, bez završene kalibracije. Završno stanje IDLE / NO_MACHINE, čeka novo pokretanje.
- Početak oba loga sadrži nepotpun red pri priključivanju na postojeći serijski tok; ne tretira se kao potpuna telemetrijska poruka.

## Granice potvrde
Audio akvizicija i obrada daju konačne, promjenljive podatke. Nije urađen kontrolisani zvučni stimulus, poređenje sa referentnim mikrofonom niti završena validacija detektora na ventilatoru.
Fizičko dugme nije pritisnuto tokom ove provjere: VBUTTON pokazuje da su događaji došli sa konzole. Njegovo ožičenje nije potvrđeno.
LED obrasci postoje u telemetriji; stvarno svjetljenje i polaritet nisu vizuelno potvrđeni.
INA226 naponski/strujni registri nisu očitani: finalni PSD tok samo provjerava prisustvo senzora pri bootu, a konzola podržava PRESS, HOLD i GUIDED25. UART sam po sebi neće dodati očitavanje energije.
Nisu provjereni lemovi, raspored žica, VBS, šant, padovi napona niti stabilnost AMS1117 na eksternom izvoru. USB test to ne dokazuje. Nije moguće proglasiti sve fizičke spojeve ispravnim na osnovu ovog loga.

## Nastavak
1. Fizički pritisak tastera uz otvoren serijski snimak i korisničku potvrdu LED indikacije.
2. Prije eksternog napajanja: provjera stvarne topologije i napona multimetrom; USB napajanje isključeno.
3. Za mjerenje bez promjene firmwarea potreban je zaseban dostupan način očitavanja INA226 ili eksterni mjerni instrument. Ne spajati drugi I2C master bez razrađenog povezivanja.
4. UART služi za postojeće logove; adapter VCC ne povezivati na mjereni uređaj.

U ovom folderu čuvati sve naredne logove i rezultate ovog mjerenja; prethodni istorijski rezultati repoa nisu premještani ni mijenjani.


