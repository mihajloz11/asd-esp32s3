# Šta je ostalo poslije FAN01

**Ažurirano:** 22.08.2026. (sadržaj od 20.08.2026, osvježen broj PC testova)

**Live ugovor:** `physical-fan-v1.8.0` / `physical-fan-artifacts-v1.8.0` ↔ `asd-quality-v1.5.0`

**Status:** softverska arhitektura i build završeni; numerička politika i novi
fizički runtime još nisu potvrđeni.

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

PC suite 22.08.2026. daje `444 passed, 5 skipped`; pet preskočenih traže
raspakovan DCASE `fan` skup, pa ih mašina sa `data/` vrti kao `449 passed`.
Raniji `423 passed` iz ovog dokumenta bio je broj prije posljednjih komitova.
ESP-IDF 5.5.5 `ASD_PSD_LIVE`
reconfigure build je PASS; bin je 349 728 B. To su softverski dokazi, ne dokaz
flasha ili rada na fizičkom ventilatoru.

## Šta stvarno ostaje

| # | Stavka | Trenutna granica dokaza |
|---|---|---|
| 1 | Zalemiti taster, dvije LED i 220–330 Ω otpornike | Softverski pandan radi; kompletan samostalan sklop bez PC-a nije potvrđen. |
| 2 | Flashovati v1.8/q1.5 build | Build prolazi, ali ovaj bump nije boot/runtime potvrđen na pločici. |
| 3 | Zamrznuti commissioning pragove iz novog normal-only perioda | Trenutni brojevi su `DEVELOPMENT/PENDING`; target anomalije se ne koriste za fit. |
| 4 | Izvesti skraćeni fizički run | 30 min normal-only: prvih 20 min DERIVE, kasnijih 10 min VERIFY; zatim najviše 3 papirić + 2 razgovor bloka. |
| 5 | Zamrznuti ili odbiti interference policy | HOLD arhitektura postoji, ali je `enabled=false`; jedan mikrofon ne smije tvrditi `AMBIENT_NOISE`. |
| 6 | I2S liveness na hardveru | Odspojiti/prekinuti I2S i potvrditi stvarni timeout, terminalni UART i oporavak. |
| 7 | Persistence/power-loss | Sada potvrditi da DEVELOPMENT restart zahtijeva relearn i da nema ASD NVS zapisa; save/restore/power-loss testirati tek uz frozen production policy bump. |
| 8 | Završni autonoman demo | Hladan/topao start, rad bez PC-a, LED/taster i više sesija. |
| 9 | INA226/E5 | Završiti mjernu ploču i provjeriti da ASD NVS postupak nije dirao INA226 namespace. |

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

Plan ostaje u [plan-dvije-plocice.md](plan-dvije-plocice.md) i
[sema-sklopa.pdf](sema-sklopa.pdf). Za uređajnu ploču trebaju jedan INMP441,
zelena LED na GPIO2, crvena LED na GPIO11, po jedan otpornik 220–330 Ω i taster
GPIO10↔GND. Drugi mikrofon nije dio finalne šeme; raniji dual-channel kandidati
nisu opravdali dodatnu složenost.

Elektronika se može završiti narednih dana nezavisno od ovih dokumentacionih
izmjena. Nijedan softverski PASS u ovom dokumentu ne zamjenjuje fizičku provjeru
ožičenja, napajanja ili bezbjednosti ventilatora.
