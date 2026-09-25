# Kondenzatori — koji, gdje i da li uopšte trebaju

**Datum:** 22.09.2026.

Ovaj fajl sabira na jedno mjesto ono što je do sada bilo razbacano po
[`sema-povezivanja.md`](sema-povezivanja.md),
[`e5-povezivanje-i-mjerenje.md`](../e5-potrosnja/e5-povezivanje-i-mjerenje.md),
[`uredjaj-na-protobordu.md`](uredjaj-na-protobordu.md),
[`plan-dvije-plocice.md`](plan-dvije-plocice.md) i
[`inventar.md`](../nabavka/inventar.md). Ne uvodi nijednu novu brojku.

---

## Kratak odgovor

**Nijedan kondenzator nije obavezan, i projekat je do sada radio bez ijednog.**
Dva su korisna kao osiguranje kad se pređe na eksterno napajanje, a treći
(470 µF) namjerno **smeta** mjerenju i ne stavlja se za prvi E5 prolaz.

---

## 1. Tri kondenzatora, tri različita posla

| Kondenzator | Gdje | Čemu služi | Obavezan |
|---|---|---|---|
| **470 nF keramika** (A2400) | padovi mikrofona, VDD ↔ GND | HF dekapling — čist napon za MEMS | ne — lijek za rizik C1 |
| **10 µF elektrolit** (iz seta A642K) | isto tu, paralelno | bulk rezerva za isti posao | ne — isto |
| **470 µF elektrolit** (iz istog seta) | mjerna ploča, čvor `3V3 POTROŠAČ` | brownout kad INA226 i žice podignu impedansu (rizik C7) | ne — **i kvari mjerenje**, vidi 5. |

Keramika hvata brze smetnje, elektrolit spori pad napona. Zato idu **oba**
paralelno na isti par pinova, a ne jedan umjesto drugog.

## 2. Zašto je sve radilo bez njih

Nijedan scenario u kom bi nešto značili se nije desio:

| Razlog | Dokaz |
|---|---|
| Napajanje je bilo USB — kratko, kruto, preko onboard LDO ploče | sve dosadašnje probe |
| Wi-Fi i BT se nikad ne pale, pa nema strujnog špica koji 470 µF hvata | `CONFIG_BT_ENABLED is not set` u `sdkconfig`; `esp_wifi` se ne poziva nigdje u `firmware/esp32s3_asd/main/` |
| Potrošnja je 34,73 mA — premalo da obori napon | [`e5-mjerenje-01-rezultat.md`](../e5-potrosnja/e5-mjerenje-01-rezultat.md) |
| Zvuk je bio čist bez ijednog dodatog kondenzatora | dva validna fizička runa 27.08. ([`rezultat-finalna-validacija-2026-08-27.md`](../../../docs/probe/rezultat-finalna-validacija-2026-08-27.md)) |

Registar rizika u [`plan-master-rada-jul.md`](../../istorija/planovi/plan-master-rada-jul.md) ih ni ne
traži kao obavezne: pod C1 stoji „napajanje mikrofona sa šumnog pina (dodaj
100 nF + 10 µF uz sam mikrofon)" — dakle jedna od stavki **šta probati ako
dobiješ tišinu ili šum**. Taj slučaj se nije desio.

## 3. Šta ide na mikrofon

| Kondenzator | Vrijednost | Polaritet |
|---|---|---|
| keramika | **470 nF** (A2400, imaš 3 kom) | nema ga — svejedno kako se okrene |
| elektrolit | **10 µF** (iz seta A642K) | **ima** — plus na VDD |

```
   INMP441 (6 pinova)

   VDD ●──┬──────┬────────── 3V3
          │      │
      470 nF   10 µF         oba između VDD i GND
      (ker.)  (+ na VDD)
          │      │
   GND ●──┴──────┴────────── GND
   SCK ●──────────────────── GPIO 4
   WS  ●──────────────────── GPIO 5
   SD  ●──────────────────── GPIO 6
   L/R ●──────────────────── GND   ← obavezno, inače firmware čita tišinu
```

**Polaritet elektrolita:** pruga na tijelu i **kraća nožica su minus** → na GND.
Duža nožica je plus → na VDD. Okrenut naopako, elektrolit se vremenom kvari i
može da pukne.

Pin-mapa je iz [`pins.h`](../../../firmware/esp32s3_asd/main/pins.h) i ne mijenja
se — kondenzatori ne diraju nijedan GPIO.

## 4. Mora na sam mikrofon, ne na protobord

Mikrofon stoji na žicama od ~10 cm. Dekapling na drugom kraju te žice ne radi
ništa — pravilo iz [`uredjaj-na-protobordu.md`](uredjaj-na-protobordu.md):

> Kondenzatori mikrofona ostaju zalemljeni na mikrofon, ne na protobord.
> Na 10 cm žice dekapling na drugom kraju ne radi ništa.

Nožice se skraćuju na par milimetara i leme direktno preko `VDD` i `GND` pada
na modulu.

### Radi to na rezervnom mikrofonu

Imaš **dva** INMP441 (A1477). Drugi stoji neiskorišćen otkako je Faza 5
izmjerila da se dual-channel ne isplati — *„finalna šema ostaje sa jednim
INMP441"* ([`DNEVNIK-NEXT-LEVEL.md`](../../dnevnici/DNEVNIK-NEXT-LEVEL.md)).

Radni mikrofon je proizveo oba validna runa od 27.08. MEMS je krhak (rizik C1),
a lemljenje je jedini način da ga pokvariš. Zalemi na rezervni, provjeri, pa
zamijeni. Ako spržiš rezervu — izgubio si komad koji ti ionako ne treba, a
dokazi ostaju netaknuti.

### Postupak

1. Zalemi 470 nF i 10 µF na `VDD`/`GND` padove **rezervnog** modula. Kratko,
   bez zadržavanja lemilice. Ne diraj akustični otvor na tijelu mikrofona.
2. Multimetrom provjeri da **nema kratkog spoja** `VDD`–`GND` prije uključenja.
3. Zamijeni mikrofone i pusti audio provjeru.
4. Uporedi sa izmjerenim baseline-om ispod.

### Kriterij provjere

Brojke iz snimka 21.09.2026. na **starom** mikrofonu bez ijednog kondenzatora
(`results/mjerenje_2026-09-21/02-audio-check.log`, grana `measurement/e5-ina226`):

| Veličina | Izmjereno |
|---|---|
| `level_dbfs` | −53,0381165 · −53,8618851 · −53,7016907 · −53,2862015 |
| `tonalness_proxy` | 2,57302952 do 2,80838823 |
| `dropped` | 0 u svim `FLAGS` redovima |

Ako novi mikrofon uđe u isti opseg — ispravan je i kondenzatori ne smetaju.
Grubo odstupanje znači loš lem, ne loš kondenzator: vrati stari.

## 5. 470 µF — mjerna ploča, i zašto NE za prvo mjerenje

Ide na čvor `3V3 POTROŠAČ` (isti kao INA226 `IN−` i `VBS`), plus na 3V3, minus
na GND. Ostaje **vadiv**.

Ali se za prvi E5 prolaz **ne stavlja**, iz razloga koji stoji u
[`sema-povezivanja.md`](sema-povezivanja.md):

> 470 µF je **mjerni kompromis**: ublažava strujni špic koji baš pokušavaš
> izmjeriti (INA226 ga vidi kao odgođeno punjenje → energija se pripiše
> pogrešnoj fazi).

E5 firmware sa grane `measurement/e5-ina226` razdvaja energiju na
`CAPTURE_WAIT` / `DSP` / `SCORE`. Kondenzator od 470 µF razmazuje granice
između tih faza — pokvario bi tačno onu brojku zbog koje se mjerenje i radi.

**Dodaj ga samo ako vidiš brownout reset u logu, i tada dokumentuj oba slučaja
odvojeno** („bez" i „sa 470 µF").

## 6. Kad bi ovo moglo da zatreba

E5 mjerenje mijenja napajanje iz temelja: nema USB-a, ide lab izvor →
AMS1117 → šant 0,1 Ω → žice. U tim žicama je izmjereno **~2 Ω serijskog
otpora**, odnosno 66 mV pada na 34,73 mA
([`e5-mjerenje-01-rezultat.md`](../e5-potrosnja/e5-mjerenje-01-rezultat.md), nalaz 3).

Brownout ni tada nije realan — detektor okida znatno ispod radnog napona. Ono
što **jeste** otvoreno: detektor je PSD otisak spektra, pa ako slabije napajanje
unese šum u napon mikrofona, to sleti pravo u obilježja. Pod USB-om je zvuk bio
čist i to je izmjereno; **pod eksternim napajanjem nije provjereno.** To je
jedini stvarni razlog da se ova dva kondenzatora drže pri ruci.

## 7. Šta imaš na stolu

| Stavka | Kom | Cijena | Koristi projekat |
|---|---|---|---|
| Keramika 470 nF MLCC 50 V (A2400) | 3 | 48 RSD | 1 kom, opciono |
| Set 120 elektrolita 1 µF–470 µF, 12 vrijednosti (A642K) | 1 | 500 RSD | 2 kom (10 µF i 470 µF), oba opciona |

Izvor cijena: [`inventar.md`](../nabavka/inventar.md) (porudžbina isporučena
04.08.2026, ukupno 3.118 RSD). Set elektrolita je opšta zaliha — ostalih deset
vrijednosti ovaj projekat ne koristi.

Datasheet INMP441 traži 100 nF; 470 nF radi isto za digitalni MEMS i nema
potrebe kupovati 100 nF
([`uredjaj-na-protobordu.md`](uredjaj-na-protobordu.md), sekcija 3).
