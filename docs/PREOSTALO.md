# Šta je ostalo poslije FAN01

**Ažurirano:** 27.08.2026. (poslije dva validna fizička runa)

**Live ugovor:** `physical-fan-v1.9.0` / `physical-fan-artifacts-v1.9.0` ↔ `asd-quality-v1.6.0`

**Status:** **firmware je funkcionalno završen i potvrđen na pločici.** Ostaje
elektronika, hardverski runtime testovi i sitno čišćenje koda. Puna analiza
finalne validacije:
[rezultat-finalna-validacija-2026-08-27.md](rezultat-finalna-validacija-2026-08-27.md).

Prvi fizički test ventilatora više nije otvorena stavka. FAN01 je pokazao da
`psd_shape` veoma dobro rangira bezbjedno izazvanu promjenu protoka papirićem,
ali i da prag iz kratke kalibracije praktično ne radi. Papirić nije potvrđen
kvar. Detalji: [rezultat-fan01-2026-08-16.md](rezultat-fan01-2026-08-16.md).

## Šta je softverski završeno

- centralni K1 gate i read-only ispravka istorijskog `cold-start-04`;
- više firmware sesija u jednom host runu, bez nasljeđivanja conditiona i
  session brojača;
- research telemetrija: finalni `feature96`, pet `subseg96` vektora i manifest;
- razvojni alati za hronološki CENTER/DERIVE/VERIFY i threshold kandidate;
- runtime tok `SETTLE → CENTER_LEARNING → COMMISSION_DERIVE →
  COMMISSION_VERIFY → MONITORING`;
- apsolutni `threshold_enter` i `threshold_exit`, bez skrivenog exit scale-a;
- `OBSERVATION_HOLD` semantika koja suspenduje buildup i ne briše aktivan alarm
  ni profil;
- bounded audio read sa fail-closed `AUDIO_TIMEOUT`/`AUDIO_READ_ERROR`;
- NVS storage profil sa schema/version, model fingerprintom, generation,
  policy ID-ima i CRC32; DEVELOPMENT integracija je namjerno RAM-only i ne
  radi load/save;
- backward offline read v1.6/q1.3 i v1.7/q1.4 uz novi v1.8/q1.5 par.

PC suite 27.08.2026. daje `478 passed` na mašini sa raspakovanim DCASE `fan`
skupom. ESP-IDF 5.5.5 `ASD_PSD_LIVE` + `ASD_RESEARCH_TELEMETRY` build je PASS;
bin je 354 784 B, SHA-256 `9ac2caca…8d967813`. Taj isti bin je pustio oba
validna fizička runa 27.08., pa ovdje **jeste** i flash/runtime dokaz — ali samo
za ono što ti runovi pokrivaju.

## Šta stvarno ostaje

| # | Stavka | Trenutna granica dokaza |
|---|---|---|
| 1 | Zalemiti taster, dvije LED i 220–330 Ω otpornike | Softverski pandan radi; kompletan samostalan sklop bez PC-a nije potvrđen. |
| ~~2~~ | ~~Flashovati q1.6 build~~ | **Završeno 27.08.** — isti bin (`9ac2caca…`) je boot/runtime potvrđen u oba validna runa. |
| ~~3~~ | ~~Izvesti fizički run sa normal-only DERIVE/VERIFY~~ | **Završeno 27.08.** — dva `valid_physical_result` runa, prag izveden na uređaju iz 44 normal-only prozora, VERIFY prošao. |
| ~~4~~ | ~~Zamrznuti ili odbiti interference policy~~ | **Odlučeno 27.08.** — `enabled=true`, prag se izvodi po sesiji (`max(10 CAL normal-only) × 1,25`). HOLD i dalje ne tvrdi kategoriju smetnje. |
| 5 | Zamrznuti commissioning brojeve za proizvodnju | Pravilo (`p99` enter / `p95` exit, frozen CAL centar) je potvrđeno na dva runa, ali politika je i dalje `DEVELOPMENT`. Zamrzavanje traži bump verzije i novi preregistrovani retest. |
| 6 | I2S liveness na hardveru | Odspojiti/prekinuti I2S i potvrditi stvarni timeout, terminalni UART i oporavak. |
| 7 | Persistence/power-loss | Sada potvrditi da DEVELOPMENT restart zahtijeva relearn i da nema ASD NVS zapisa; save/restore/power-loss testirati tek uz frozen production policy bump. |
| 8 | Završni autonoman demo | Hladan/topao start, rad bez PC-a, LED/taster i više sesija. |
| 9 | INA226/E5 | Završiti mjernu ploču i provjeriti da ASD NVS postupak nije dirao INA226 namespace. |
| 10 | Čišćenje koda i sitne finese | `CALTRIM` ispisuje `discarded_loo_2=nan` kad je izbačen jedan klip; istorijski demo modovi (`live_adapt.c`, `live_capture.c`, `eval_mode.c`, `tflm_infer.cc`) i dalje stoje van finalnog puta. |

## Skraćeni naredni test

Puni zaključani opis je u
[protokol-fizicki-ventilator.md](protokol-fizicki-ventilator.md), a konsolidovan
go/no-go protokol u
[DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md](DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md).

Minimalni redoslijed:

1. Fiksirati fan/mikrofon i zapisati montažu; pokrenuti v1.8/q1.5 research run.
2. SETTLE i CENTER završiti bez diranja postavke.
3. Snimiti 20 min normal-only DERIVE, zamrznuti centar/politiku/enter/exit i
   njihove hash/ID vrijednosti.
4. Na vremenski kasnijih 10 min normal-only VERIFY zahtijevati nula alarmnih
   epizoda, nula alarmnih prozora i nula chatter prelaza. Ne mijenjati prag ako
   VERIFY ne prođe; sesija je reject.
5. Tek poslije prolaza uraditi najviše tri bezbjedna papirić bloka i dva
   conversation bloka, svaki sa transition oznakom i normalnim oporavkom.
6. Prijaviti alarmne prozore i alarmne epizode odvojeno. Ranijih `324/h` je
   broj prozora iznad praga po satu, nije epizoda/h.
7. Ne podešavati prag ili HOLD granicu iz papirić/razgovor ishoda. Ako readout
   ne prođe, zamrznuta verzija pada i nova politika pripada novoj sesiji.

Nula epizoda u samo 10 minuta VERIFY-a nije dokaz male proizvodne stope: njen
jednostrani 95% Poisson gornji limit je približno 18 epizoda/h. Zato je ovo
strogi funkcionalni go/no-go sa malo pokušaja, a ne procjena dugoročne
pouzdanosti ili generalizacije.

## Elektronika

Plan ostaje u [plan-dvije-plocice.md](../radno/elektronika/plan-dvije-plocice.md) i
[sema-sklopa.pdf](../radno/elektronika/sema-sklopa.pdf). Za uređajnu ploču trebaju jedan INMP441,
zelena LED na GPIO2, crvena LED na GPIO11, po jedan otpornik 220–330 Ω i taster
GPIO10↔GND. Drugi mikrofon nije dio finalne šeme; raniji dual-channel kandidati
nisu opravdali dodatnu složenost.

Elektronika se može završiti narednih dana nezavisno od ovih dokumentacionih
izmjena. Nijedan softverski PASS u ovom dokumentu ne zamjenjuje fizičku provjeru
ožičenja, napajanja ili bezbjednosti ventilatora.
