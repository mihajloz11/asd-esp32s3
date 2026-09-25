# Elektronika: sklop, lemljenje, potrošnja

Stanje 25.09.2026. Odluke su se mijenjale od jula do septembra, pa stariji
dokumenti ponegdje opisuju raspored koji više ne važi. Ovdje je šta važi
sada i gdje je detalj.

## Šta važi sada

- **Uređaj ostaje na protobordu MB-102** i ne lemi se (odluka 02.09.).
  Mikrofon je na žicama kraćim od 10 cm, a LED, otpornici i taster na 3D
  štampanom držaču. Detalj: [uredjaj-na-protobordu.md](sklop/uredjaj-na-protobordu.md).
- **Pinovi (ESP32-S3):** INMP441 SCK→GPIO 4, WS→GPIO 5, SD→GPIO 6, L/R→GND;
  INA226 SDA→GPIO 8, SCL→GPIO 9; zelena LED GPIO 2 preko 100 Ω, crvena LED
  GPIO 11 preko 330 Ω; taster GPIO 10 na GND, interni pull-up. Izvor istine je
  `firmware/esp32s3_asd/main/pins.h`.
- **Mjerna cjelina je odvojena:** AMS1117 → INA226 (šant 0,1 Ω) → 470 µF,
  spaja se sa 4 žice samo za E5. Detalj:
  [lemljenje-cjeline-i-mjerenje.md](sklop/lemljenje-cjeline-i-mjerenje.md).
- **INA226:** `VCC` ide **prije** šanta (na `IN+`), `VBS` na `IN−`. Raniji
  raspored sa `VCC` iza šanta daje nule za napon i snagu
  ([plan-dvije-plocice.md](sklop/plan-dvije-plocice.md), sekcija 4.1).
  Crteži u `seme/sema-povezivanja.svg` i poglavlje 2 u
  [sema-povezivanja.md](sklop/sema-povezivanja.md) još pokazuju stari raspored.
- **Kondenzatori:** nijedan nije obavezan. 470 nF i 10 µF idu na padove
  mikrofona kao osiguranje; 470 µF se ne stavlja za prvo E5 mjerenje
  ([kondenzatori.md](sklop/kondenzatori.md)).
- **E5 potrošnja:** prvo mjerenje 11.08. potvrdilo je strujni kanal, a naponski
  kanal odstupa oko 200 mV zbog oko 2 Ω u razvodu
  ([e5-mjerenje-01-rezultat.md](e5-potrosnja/e5-mjerenje-01-rezultat.md)).
  Mjerni firmware (`ASD_E5_MEASURE`) je na grani `measurement/e5-ina226`,
  build prolazi, ploča nije flešovana. Tamo je i zapis stvarnog ožičenja
  (`results/mjerenje_2026-09-21/POVEZIVANJE.md`: 5,00 V na AMS1117 VIN,
  limit 0,30 A).

## Fajlovi

| Folder | Fajl | Sadržaj |
|---|---|---|
| `sklop/` | [uredjaj-na-protobordu.md](sklop/uredjaj-na-protobordu.md) | **aktuelno**: protobord, 3D držač, otpornici, kako se veže |
| | [lemljenje-cjeline-i-mjerenje.md](sklop/lemljenje-cjeline-i-mjerenje.md) | **aktuelno**: dvije cjeline i spajanje za E5 |
| | [kondenzatori.md](sklop/kondenzatori.md) | **aktuelno**: koji kondenzator gdje i da li treba |
| | [plan-dvije-plocice.md](sklop/plan-dvije-plocice.md) | plan dvije ploče (19.08.); ispravka VBS i provjere prije napajanja važe, lemljenje uređaja je otpalo |
| | [sema-povezivanja.md](sklop/sema-povezivanja.md) | pinout; poglavlja 1, 3, 4, 5 važe, poglavlje 2 ne |
| | [lemljenje.md](sklop/lemljenje.md) | puna procedura lemljenja headera i mjere opreza |
| | [lemljenje-kratko.md](sklop/lemljenje-kratko.md), [.html](sklop/lemljenje-kratko.html) | kratka verzija za štampu, sa slikama modula |
| `e5-potrosnja/` | [e5-mjerenje-01-rezultat.md](e5-potrosnja/e5-mjerenje-01-rezultat.md) | rezultat prvog mjerenja i sljedeći eksperimenti A–F |
| | [e5-povezivanje-i-mjerenje.md](e5-potrosnja/e5-povezivanje-i-mjerenje.md) | postupak mjerenja; šema u njemu je zastarjela |
| | [ina226-provjera.md](e5-potrosnja/ina226-provjera.md) | dijagnostika INA226 multimetrom (problem sa GND riješen 10.08.) |
| `nabavka/` | [inventar.md](nabavka/inventar.md) | šta je na stolu, kompatibilnost, prvobitni plan nabavke |
| | [porudzbina-elektromodul.md](nabavka/porudzbina-elektromodul.md) | porudžbina isporučena 04.08. i analiza rizika |
| | [donijeti-sa-posla.md](nabavka/donijeti-sa-posla.md) | spisak sa posla (20.08.) |
| `seme/` | `sema-sklopa.pdf`, `img/sema-sklopa-s1..7.png` | šema dvije ploče, 7 strana A4 |
| | `make_sema_sklopa.py` | generiše PDF i PNG pored sebe (`python make_sema_sklopa.py`) |
| | `sema-cjeline.svg`, `sema-lemljenje.svg`, `sema-povezivanja.svg` | crteži; `sema-povezivanja.svg` ima stari raspored INA226 |
| | `img/sklop-render-v1.png`, `v2.png` | renderi sklopa |
| `img/` | | fotografije modula (INMP441, INA226, AMS1117, taster, ploča, letvice) |
