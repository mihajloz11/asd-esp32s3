# E5 povezivanje i mjerenje potrošnje

> **Status 22.09.2026 — šema u ovom fajlu je ZASTARJELA, postupak nije.**
>
> Dvije stvari su se promijenile poslije 11.08.:
>
> 1. **Ožičenje.** `plan-dvije-plocice.md` sekcija 4.1 je ispravila raspored:
>    `VCC` senzora ide **prije** šanta (na `IN+`), a `VBS` na `IN−`. Šema u
>    poglavlju „Konačna šema" ispod stavlja `VCC` na `IN−` i to više ne važi —
>    tako spojeno, `VCC` INA226 troši kroz šant i ulazi u mjerenu struju.
>    Stvarno spojena ploča je zapisana na grani `measurement/e5-ina226`
>    (`results/mjerenje_2026-09-21/POVEZIVANJE.md`) i koristi varijantu sa
>    punjačem: **5,00 V na AMS1117 VIN**, limit `0,30 A`, a ne 3,30 V direktno
>    na `IN+`. Obje varijante su uporedo opisane u
>    [lemljenje-cjeline-i-mjerenje.md](../sklop/lemljenje-cjeline-i-mjerenje.md).
> 2. **Firmware.** „Puni E5 firmware" iz posljednjeg pasusa je napisan
>    21–22.09.2026. i stoji na grani `measurement/e5-ina226`, **nije u
>    `master`-u**: `e5_measure.c` iza `ASD_E5_MEASURE` flaga, sa komandama
>    `E5ARM`, `E5CHECK`, `E5RUN`, `E5DUMP`, `E5SAVED`, `E5STOP`, `E5DISARM`,
>    razdvajanjem energije po fazama `CAPTURE_WAIT`/`DSP`/`SCORE` i markerima na
>    `GPIO 12/13/14`. Build prolazi (381 488 B), **nije flešovan ni testiran na
>    ploči.** Postupak ispod (redoslijed uključivanja, limiti, USB pravila)
>    ostaje važeći.
>
> ---
>
> **Status 11.08.2026: prvo mjerenje je izvedeno.** Rezultat, nalazi i sljedeći
> koraci su u [`e5-mjerenje-01-rezultat.md`](e5-mjerenje-01-rezultat.md), sirovi
> log u [`results/e5_mjerenje_01_uart.log`](../../../results/e5_mjerenje_01_uart.log).
>
> Ukratko: strujni kanal radi i potvrđen je nezavisno (34,73 mA), ali naponski
> kanal čita 3,425 V umjesto ~3,22 V, a napojna grana ima ~2 Ω serijskog otpora.
> Prije ponavljanja mjerenja treba zamijeniti breadboard razvod kratkim
> zalemljenim žicama i svesti sve mase u jednu tačku.
>
> Postupak ispod ostaje važeći za svako naredno mjerenje.

**Status 10.08.2026:** INA226 test firmware je buildovan, flešovan i armiran.
ESP32-S3 je iskopčan sa USB-a. Mjerenje je odloženo do sutra jer treba napraviti
siguran razvod zajedničkih `3V3_LOAD` i GND čvorova; ne treba spajati više žica
na silu na isti pin.

## Šta je potrebno

- laboratorijsko napajanje podešeno na **3,30 V**;
- strujni limit prvo **0,30 A**, po potrebi najviše **0,50 A** ako izvor uđe u
  `CC` režim ili se ESP32 resetuje;
- INA226 sa šantom `R100 = 0,1 Ω`;
- ESP32-S3 i postojeće I2C veze;
- breadboard razvod ili kratke zalemljene žice za zajedničke čvorove.

Baterija i AMS1117 nisu potrebni kada se koristi podesivo laboratorijsko
napajanje. Izlaz izvora mora biti isključen tokom povezivanja.

## Pinovi INA226

Redoslijed na konkretnom modulu:

```text
IN+ · IN− · VBS · ALE · SDA · SCL · GND · VCC
```

`VBS` je ulaz za mjerenje napona magistrale. Za E5 ide na stranu potrošača,
odnosno na isti čvor kao `IN−`. `ALE` je alarmni izlaz i ostaje nepovezan.

## Konačna šema — ZASTARJELO, vidi banner na vrhu

Ispod je raspored iz avgusta. `VCC` je tu na `3V3_LOAD` (iza šanta), što je
sekcija 4.1 u [plan-dvije-plocice.md](../sklop/plan-dvije-plocice.md) ispravila.
Čuva se zato što objašnjava zašto je prvo mjerenje ispalo kako jeste.

```text
LAB +3,30 V ───────────── INA226 IN+

INA226 IN− ──┬────────── ESP32-S3 3V3
              ├────────── INA226 VBS
              └────────── INA226 VCC
              
LAB minus ────┬────────── ESP32-S3 GND
               └────────── INA226 GND

INA226 SDA ────────────── ESP32-S3 GPIO8
INA226 SCL ────────────── ESP32-S3 GPIO9
INA226 ALE ────────────── nepovezan
```

Čvor `IN− + VBS + VCC + ESP32 3V3` u nastavku se zove `3V3_LOAD`. Sva struja
koju troše ESP32, INA226 logika i periferije tada prolazi kroz šant od `IN+` do
`IN−`. Plus laboratorijskog izvora ne smije ići direktno na ESP32 `3V3`, jer bi
time zaobišao šant.

## Kako riješiti manjak priključnih mjesta

Najčistije je koristiti jednu slobodnu breadboard šinu ili red kao
`3V3_LOAD`:

1. kratkom žicom spoji ESP32 `3V3` na tu šinu;
2. na istu šinu spoji INA226 `IN−`, `VBS` i `VCC`;
3. drugu šinu koristi kao GND za minus izvora, ESP32 GND i INA226 GND.

Ako breadboard raspored to ne dozvoljava, zalemi kratku izolovanu žicu između
susjednih INA226 pinova `IN−` i `VBS`, a njihov zajednički kraj spoji na
`3V3_LOAD`. Ne praviti kalajni most bez izolovane žice i ne lemiti na napojenom
sklopu. Poslije lemljenja multimetrom potvrditi kontinuitet željenih čvorova i
da nema kratkog spoja između `3V3_LOAD` i GND.

## Kondenzatori

Prvi test se radi **bez dodatnog 470 µF kondenzatora**, jer on ublažava strujne
špiceve koje želimo izmjeriti.

Ako se javi brownout ili reset, dodati 470 µF paralelno na strani potrošača:

```text
470 µF plus  ─────────── 3V3_LOAD / INA226 IN−
470 µF minus ─────────── zajednički GND
```

Pruga i kraća nožica elektrolitskog kondenzatora označavaju minus. Kondenzator
ne ide između `IN+` i `IN−`.

Kondenzatori mikrofona ostaju uz mikrofon:

- 470 nF keramika između VDD i GND, bez polariteta;
- 10 µF elektrolit paralelno, plus na VDD i minus na GND.

## Redoslijed prvog testa

1. USB mora ostati iskopčan.
2. Isključiti izlaz laboratorijskog izvora (`OUTPUT OFF`).
3. Podesiti `3,30 V` i limit `0,30 A`.
4. Napraviti i multimetrom provjeriti sve veze iz šeme.
5. Uključiti izlaz izvora i sačekati najmanje 10 sekundi.
6. Ako izvor pokaže `CC`, napon padne ili se ESP32 resetuje, odmah isključiti
   izlaz i provjeriti spojeve; tek nakon provjere limit se može podići na
   `0,50 A`.
7. Ako test prođe mirno, isključiti izlaz izvora.
8. Tek tada priključiti USB i otvoriti serijski monitor. Firmware ispisuje
   sačuvani izvještaj bez ponavljanja mjerenja.

**Ne priključivati USB prije eksternog testa.** Armirani firmware sljedeće
potpuno uključenje tretira kao mjerni prolaz.

## Šta firmware čuva

Jednokratni `ASD_INA_TEST` prolaz čuva u NVS-u:

- status testa i eventualnu grešku;
- pronađenu I2C adresu;
- konfiguracioni i kalibracioni registar;
- 10 uzoraka napona šanta, napona magistrale, struje i snage.

Mjerenja se prvo drže u RAM-u. Izvještaj se upisuje u flash tek nakon posljednjeg
uzorka, tako da flash-upis ne ulazi u deset sačuvanih očitanja. Ovo je provjera
strujnog puta.

Puni E5 firmware koji integriše energiju odvojeno po fazama **je napisan**
(21–22.09.2026), ali stoji na grani `measurement/e5-ina226` i nije flešovan.
Njegove faze su `CAPTURE_WAIT`, `DSP` i `SCORE` (plus `OTHER`/`MIXED`), a ne
podjela „idle / snimanje / DSP / inferenca" iz avgustovskog plana. Protokol
mjerenja je u `results/mjerenje_2026-09-21/EXPERIMENT.md` na toj grani.
