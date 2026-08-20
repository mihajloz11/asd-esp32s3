# Šta donijeti s posla

> Stanje 20.08.2026. Spisak je kratak namjerno — **kondenzatori se ne kupuju i
> ne donose, svi su već na stolu** (set od 120 elektrolita 1 µF–470 µF i 3×
> keramika 470 nF, stiglo 04.08. — [hardver-lista.md](hardver-lista.md)).
> I2C pull-upovi se takođe ne donose: INA226 modul ih ima na sebi, izmjereno je
> `obaranje=0`, `pušteno@5us=1` na obje linije.
>
> **Ventilator se više ne traži.** FAN01 od 16.08. je izveden na prenosivom USB
> ventilatoru koji već imaš, uz mikrofon na 20 cm i 90° na osu duvanja
> ([rezultat-fan01-2026-08-16.md](rezultat-fan01-2026-08-16.md)). Raniji zapisi
> koji su ventilator, 12 V adapter i nosač vodili kao otvorenu nabavku su
> zatvoreni.

---

## Spisak

| # | Šta | Kom | Zašto | Šta odblokira | Prioritet |
|---|---|---|---|---|---|
| 1 | Otpornik **330 Ω**, 1/4 W | 2 + rezerva | Račun i izbor vrijednosti su niže | LED demo — **zelena GPIO2 (status), crvena GPIO11 (alarm)**; firmware je gotov i testiran | **visok** |
| 2 | Otpornik **100 Ω**, 1/4 W | 2 | Rezerva ako je zelena LED visokog `Vf` — vidi zamku niže | Isto; bez toga zelena može ostati tamna a da firmware bude ispravan | **visok** |
| 3 | **Multimetar** (ili 15 min pristupa njemu) | 1 | Sonde direktno na nožice INA226 modula; isti instrument provjerava LED u diodnom režimu | Eksperiment A — lokalizacija greške naponskog kanala | **visok** |
| 4 | **Laboratorijsko napajanje** — koristi se **na poslu**, ne iznosi se | 1 | Podesiv napon + **strujni limit** | E5 po varijanti A: INA226 + 470 µF na MB-102, ploča M se ne lemi | srednji |
| 5 | *(opciono)* Ženski header 2.54 mm | ~1 | Da INMP441 ostane vadiv | Faza 2 (ploča 4×6) — bez toga se moduli leme fiksno | nizak |
| 6 | *(opciono)* Nezavisan audio snimač — hendi rekorder ili USB mik | 1 | Firmware u `ASD_PSD_LIVE` **ne šalje sirovi PCM** dok detektor radi | Paralelni WAV uz fizički run; bez fajla se po protokolu ne smije tvrditi da je sirovi WAV snimljen | nizak |
| 7 | *(opciono)* Drugi **INA226** modul | 1 | Poređenje dva komada na istoj postavci | E5 eksperiment C — razlikuje grešku pojačanja (moguć klon) od greške postavke; sa jednim komadom se ta hipoteza ne može zatvoriti | nizak |

**Napomena uz stavku 4 — E5 se mjeri na poslu, ne kod kuće.** Ranija verzija
ovog spiska je tražila „5 V izvor sa golim žicama" da bi se AMS1117 napojio kod
kuće. [plan-dvije-plocice.md §2.6](plan-dvije-plocice.md) je to zamijenio:
sa laboratorijskim napajanjem na 3,3 V otpadaju i AMS1117 i 5 V ulaz i lemljenje
ploče M — ostaju **INA226 + 470 µF + četiri žice** na MB-102. Zato 5 V izvor
više nije stavka spiska. Podešavanje prije spajanja: **3,30 V** provjereno
multimetrom na krajevima kablova (ne po displeju), strujna granica **300–500 mA**,
nikad preko **3,6 V**.

**Zašto stavka 3 nije zamjenjiva softverom:** otvoreni nalaz je da INA226 čita
3,425 V umjesto ~3,22 V, a hipoteza je razlika potencijala između INA-ine i
ESP-ove mase. To je mjerenje na fizičkim nožicama modula i ne može se ustanoviti
iz firmvera. Detalji i tabela A1–A3:
[e5-mjerenje-01-rezultat.md](e5-mjerenje-01-rezultat.md#a-lokalizacija-greške-naponskog-kanala).

### Promjena 14.08.2026 — otpornici su podigli prioritet

Firmware za taster i lampice je napisan, testiran (43 host testa) i flešovan.
Zelena LED nosi cijeli tok demoa kroz pet obrazaca (čekam / učim / **naučio** /
alarm / kvar), a crvena razrješava „ugašena zelena" naspram „uređaj mrtav".
Bez otpornika LED se **ne smije** vezati na GPIO, pa su oni sada na kritičnom
putu za demo, ne više „srednji prioritet".

**Drugi mikrofon se NE lemi.** Faza 5 je izmjerila da su sve dual-channel
varijante slabije od jednog kanala; modul #2 ostaje rezerva. Detalji:
[DNEVNIK-NEXT-LEVEL.md](DNEVNIK-NEXT-LEVEL.md), blok G.

### Otpornik za LED — račun i zamka sa zelenom

Spisak je ranije govorio „220–330 Ω" bez broja koji to opravdava, pa se pred
policom i dalje moralo računati.

| Vrijednost | Kom | Struja i namjena |
|---|---|---|
| **330 Ω**, 1/4 W | 2 + rezerva | Sa crvenom LED (`Vf ≈ 2,0 V`): `(3,3 − 2,0) / 330 = 3,9 mA`. Na 220 Ω je 5,9 mA. Oba su daleko ispod granice GPIO pina, pa se bira veći otpornik |
| **100 Ω**, 1/4 W | 2 | Rezerva za zelenu — vidi zamku ispod |

**Zamka sa zelenom LED.** Kupljena zelena je „prozirna dioda zeleno svetlo"
([porudzbina-elektromodul.md](porudzbina-elektromodul.md), stavka 9), dakle
skoro sigurno InGaN sa `Vf ≈ 3,0–3,2 V`. Na 3,3 V GPIO tada ostaje samo ~0,2 V
na otporniku, kroz 330 Ω teče manje od 1 mA i dioda jedva tinja — a to izgleda
identično kao „firmware ne pali LED". Zelena nosi cijeli tok demoa kroz pet
obrazaca, pa bi ta zamjena poslala traženje greške u pogrešan kod.

Provjera je multimetrom u **diodnom režimu, prije lemljenja**: ako crvena pokaže
~1,8 V a zelena `OL`, njen `Vf` je preko napona diodnog testa i ide joj 100 Ω
umjesto 330 Ω.

> Otpornici za ploču U se ionako **kupuju** sa Mikro Princa (ident 32004, 10 kom
> za ≈ 23 din — [plan-dvije-plocice.md §7](plan-dvije-plocice.md)). Ovaj spisak
> ih drži zato što je nekoliko komada s posla najbrži put do provjere lampica
> prije nego porudžbina stigne, i zato što 100 Ω nije u toj porudžbini.

### Kondenzatori — samo 100 nF, i to iz kupovine

Jedini kondenzator koji ovom sklopu fali je **100 nF keramika, raster 2,54 mm**,
i ide između `VDD` i `GND` mikrofona, **manje od 5 mm od INMP441**
([sema-povezivanja.md](sema-povezivanja.md)). Ne donosi se s posla: onaj s posla
je SMD i bez nožica ne ulazi u perfboard, pa je i on u porudžbini sa Mikro
Princa. **10 µF** (bulk uz mikrofon) i **470 µF** (poslije INA, samo ako se javi
brownout) vade se iz kupljenog seta od 120 elektrolita, a INA226 modul ima svoj
dekapling na sebi.

## Šta NE treba donositi

- **Kondenzatori.** 10 µF i 470 µF su u kupljenom setu elektrolita; 100 nF za
  mikrofon je u porudžbini sa Mikro Princa, a onaj s posla je SMD i ne ulazi u
  perfboard.
- **Pull-up otpornici za I2C** — na INA226 modulu su, potvrđeno mjerenjem.
- **Lemilica, kalaj, fluks, pletenica, ESD narukvica** — lemljenje se radi na
  poslu ([lemljenje-kratko.md §2](lemljenje-kratko.md)); kući se vraćaju
  zalemljeni moduli, ne alat.
- **USB-UART adapter** — CH340 je već tu i korišćen je u E5 prolazu (COM7).
- **5 V izvor i AMS1117 put** — otpali su sa varijantom A, vidi napomenu uz
  stavku 4.
- **Ventilator, 12 V adapter, nosač za mikrofon** — postavka iz FAN01 radi i
  ponavlja se; nabavka je zatvorena.
- **Ništa za mikrofon.** INMP441 radi bez ijedne dodatne komponente; kondenzatori
  uz njega su poboljšanje, ne uslov. Živi lanac je radio bez njih 06.08.
  (rms 158,7 / peak 1020 / clipped 0 / dropped 0).

## Šta se ovim otključava

Ovaj spisak pokriva samo nabavni dio. Šta se radi kad komponente budu na stolu i
kojim redom stoji u [PREOSTALO.md](PREOSTALO.md); redoslijed lemljenja ploče U je
u [plan-dvije-plocice.md §5](plan-dvije-plocice.md), a vođeni test u
[GUIDED25-TEST-VENTILATORA.md](GUIDED25-TEST-VENTILATORA.md).

Dvije granice koje ovaj spisak **ne** ukida: build v1.8/q1.5 nije flashovan ni
runtime-potvrđen na pločici, a commissioning pragovi su još
`DEVELOPMENT/PENDING`. Nijedna komponenta sa spiska ne mijenja te dvije stavke.

---

## Kako povezati INA226 sada, bez spoljnog napajanja

Dva slučaja. Za **dugu probu lažnih alarma senzor uopšte ne treba** — taj test
koristi samo mikrofon i USB.

### A) Samo I2C — senzor je živ, ali ne mjeri ništa korisno

Ovo je stanje u kojem je senzor bio potvrđen 10.08. Radi bez spoljnog napajanja.

```text
INA226 VCC ────────────── ESP32-S3 3V3
INA226 GND ────────────── ESP32-S3 GND
INA226 SDA ────────────── ESP32-S3 GPIO8
INA226 SCL ────────────── ESP32-S3 GPIO9
INA226 IN+ ────────────── NEPOVEZANO
INA226 IN− ────────────── NEPOVEZANO
INA226 VBS ────────────── NEPOVEZANO
INA226 ALE ────────────── NEPOVEZANO
```

Senzor odgovara na `0x44`, vraća `manuf=0x5449`/`die=0x2260`, prima config i
kalibraciju. Šant tada čita šum od −10 do −7 µV, jer kroz njega ne teče struja.

**Za ovo nema šta da se mjeri od potrošnje** — ploča se napaja s USB-a, mimo
šanta. Ako ti je muka da diraš žice, ostavi ovako; ništa ne kvari.

> ⚠️ `IN+` i `IN−` ne ostavljati spojene na žice koje vise u vazduh, posebno ne
> pored mikrofona — vise kao antena. Ili ih spoji po šemi, ili skini.

### B) Puni E5 bez laboratorijskog napajanja — traži stavku 1 sa spiska

Ovo je razlog zbog kojeg je AMS1117 i kupljen (rizik D2 iz plana).

```text
5 V punjač +  ──────────── AMS1117 IN
5 V punjač −  ──────────── AMS1117 GND ──┐
                                          │
AMS1117 OUT (3,3 V) ────── INA226 IN+     │
                                          │
INA226 IN− ──┬─────────── ESP32-S3 3V3    │
             ├─────────── INA226 VBS      │  ZVJEZDASTA MASA
             └─────────── INA226 VCC      │  (sve u JEDNU tačku)
                                          │
INA226 GND ───────────────────────────────┤
ESP32-S3 GND ─────────────────────────────┘

470 µF elektrolit:  + na čvor IN−/3V3   ·  − na zajednički GND
INA226 SDA → GPIO8  ·  SCL → GPIO9  ·  ALE nepovezan
```

**Tri stvari koje se ne smiju preskočiti:**

1. **USB pločice mora biti iskopčan.** Inače napaja ESP32 mimo šanta i mjerenje
   nema smisla. Zato test i čuva rezultat u NVS — vidi
   [e5-povezivanje-i-mjerenje.md](e5-povezivanje-i-mjerenje.md).
2. **Zvjezdasta masa, kratke zalemljene žice, ne breadboard razvod.** Ovo je
   direktno rješenje otvorenog nalaza: sadašnja postavka ima ~2 Ω u napojnoj
   grani (66 mV pada na kontaktima) i vjerovatno razliku potencijala između
   masa. Kriterij uspjeha: pad izvor → potrošač **ispod 5 mV**, `VBUS` se
   poklapa sa multimetrom unutar **±10 mV**.
3. **Prije bilo kakvog mjerenja treba re-arm u firmveru** — vidi ispod.

**Za praćenje uživo:** CH340 USB-UART adapter (bio na COM7), samo
`adapter RX ← ESP32 TX (GPIO43)` + zajednički GND. **`VCC` adaptera ostaje
nespojen**, inače zaobiđe šant.

**Razlika naspram laboratorijskog napajanja:** AMS1117 daje fiksnih ~3,3 V i
**nema strujni limit**. Za poređenje potrošnje po fazama rada je dovoljan, jer
INA226 mjeri i stvarni napon. Za prvi prolaz posle prelemljivanja je ipak
sigurnije laboratorijsko napajanje sa limitom 0,30 A (stavka 4).

---

## Softverski blokator koji ide prije svega ovoga

`ASD_INA_TEST` je trenutno u stanju `READY` i **odbija da ponovi mjerenje**.
Guard je `esp_reset_reason() != ESP_RST_POWERON`
([ina226_test.c:147](../firmware/esp32s3_asd/main/ina226_test.c:147)), a reset
preko EN pina se prijavljuje kao `rst:0x1 (POWERON)` — izmjereno 11.08.
Posljedice:

- dok je test `ARMED`, **svako ubadanje USB-a troši armirani prolaz** i sačuva
  mjerenje napravljeno na USB napajanju, mimo šanta;
- iz `READY` (ili iz `RUNNING`, ako brownout prekine prolaz — brownout se
  prijavljuje kao `RTC_SW_SYS_RST`, pa stanje ostane zaglavljeno) jedini izlaz je
  `erase-flash`, što briše i FAT particiju s klipovima.

**Znači: mjerenje #2 nije izvodljivo bez re-arm puta.** ~15 min koda, i mora ući
prije nego što se diraju žice.
