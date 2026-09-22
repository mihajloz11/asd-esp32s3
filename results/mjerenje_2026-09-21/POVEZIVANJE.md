# Stvarno prijavljeno povezivanje — 21.09.2026.

Izvor: korisnikov priloženi raniji razgovor i potvrda da je tako spojio sklop.
Ovo je zapis prijavljenog ožičenja, nije potvrda svih lemova multimetrom.

## Mjerna ploča

| Od | Do |
|---|---|
| Ulazni plus spoljnog izvora | AMS1117 VIN |
| Ulazni GND | oba AMS GND + INA226 GND + izlazni GND |
| AMS1117 VOUT | INA226 IN+ + INA226 VCC |
| INA226 IN− | INA226 VBS + prva izlazna nožica → ESP32 3V3 |
| INA226 SDA | treća izlazna nožica → GPIO8 |
| INA226 SCL | četvrta izlazna nožica → GPIO9 |
| Zajednički GND | druga izlazna nožica → ESP32 GND |
| INA226 ALE | nepovezan |

IN− nije masa. Nema žičanog mosta IN+–IN−; struja ide kroz R100 (nominalno 0,1 Ω).
VCC senzora je PRIJE šanta. Ne prebacivati ga na IN− prema starijem avgustovskom planu.
AMS1117 i potrošnja INA226 VCC nisu obuhvaćeni strujom tereta iza šanta.

## Mikrofon INMP441

VDD → 3V3 iza šanta; GND i L/R → zajednički GND;
SCK/BCLK → GPIO4; WS/LRCL → GPIO5; SD/DOUT → GPIO6.

Taster po pin-mapi: GPIO10 ↔ taster ↔ GND; interni pull-up.
LED po pin-mapi: GPIO2 → 100 Ω → zelena → GND;
GPIO11 → 330 Ω → crvena → GND. Fizičke LED veze još nisu potvrđene.

## Kondenzatori i napajanje

Korisnik navodi da nije dodat nijedan kondenzator, uključujući 470 µF na mjernoj ploči.
Stanje ugrađenih kondenzatora na modulima nije vizuelno pregledano.
Trenutno napajanje: samo USB ESP32; eksterni izvor nije priključen.

Za ovu topologiju: laboratorijski izvor na ulaz ploče/AMS VIN = 5,00 V,
početni strujni limit 0,30 A. To je limit, ne nametnuta potrošnja.
Ne dovoditi 5 V direktno na INA IN+, IN−, VCC ili ESP32 3V3.
Prije povezivanja ESP32 napajati samo mjernu ploču i multimetrom potvrditi
približno 3,3 V između izlazne nožice 3V3 (INA IN−) i GND.
Povezivanje mijenjati sa ugašenim izvorom. Za eksterni test USB kablovi ESP32 vani.
Ako izvor uđe u CC ili uređaj resetuje, ugasiti i provjeriti; limit ne podizati naslijepo.

UART: ESP32 GPIO43/TX → RX USB-TTL adaptera, GND ↔ GND.
Za komande i TX adaptera (isključivo 3,3 V logika) → GPIO44/RX.
VCC, 5V, 3V3, DTR i RTS adaptera ostaju nepovezani.

Dopuna korisnika: za UART log koristiće logički analizator (USB u laptop, ulaz na ESP TX), a ne drugi USB priključak ESP ploče. GND analizatora → ESP GND, kanal → GPIO43; dekoder 115200 8N1. Analizator je pasivan; za start koristimo E5ARM, za kasnije preuzimanje E5SAVED.

