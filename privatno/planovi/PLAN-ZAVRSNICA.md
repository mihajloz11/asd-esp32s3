# PLAN ZAVRŠNICE — od radnog mikrofona do spremnog demoa

**Status:** ZATVOREN 14.08.2026.
**Otvoren:** 13.08.2026.
**Polazna tačka:** mikrofon #2 potvrđen kao ispravan (P16 zatvoren), 177 PC testova prolazi,
pločica na COM4, build `on-device-verified-39-gc8833ad`.
**Cilj:** kad se ovaj plan zatvori, jedino što ostaje je **fizički rad** — kompletna
šema (kondenzatori, diode, regulator, senzor, otpornici), kupovina ventilatora
i demo sa ventilatorom.

Ovaj plan **zamjenjuje redoslijed** iz [PLAN-NEXT-LEVEL.md](PLAN-NEXT-LEVEL.md),
ne njegov sadržaj. Faze 1–8 ostaju iste; mijenja se redoslijed i obim, jer je
zamjena mikrofona odblokirala hardverski put koji je bio glavno usko grlo.

---

## 0. Zašto se redoslijed mijenja

`PLAN-NEXT-LEVEL.md` je pisan 09.08., kad pločica nije bila povezana i kad su
sve uređajne provjere bile `BLOCKED_HARDWARE`. Zato je redoslijed bio
Faza 3 → 4 → 5 → 6 → 7 → 8, dakle PC istraživanje prvo, hardver na kraju.

Od 13.08. to više nije tačno stanje. Mikrofon radi, pločica radi, i cijeli
lanac se može mjeriti. Dvije posljedice:

1. **Ono što je hardverski dokazivo mjeri se prvo**, dok je postavka spojena.
   Svaka odgođena hardverska provjera je rizik da se opet zatvori prozor.
2. **Operaterski tok (taster + lampica) ulazi u kritični put**, jer bez njega
   nema demoa sa ventilatorom, a demo je jedan od tri preostala fizička koraka.
   U starom planu ga uopšte nije bilo — dodat je na osnovu zahtjeva od 13.08.

Istraživačke faze (3, 5, 6, 7) ostaju, ali **poslije** demo-kritičnih, i svaka
se ocjenjuje po tome šta stvarno može dokazati, a ne po tome što je u planu.

---

## 1. Redoslijed izvršenja

| # | Blok | Zašto ovim redom | Ishod |
|---|---|---|---|
| **A** | Puni živi lanac na uređaju: `WAIT → CAL → DET` | Najveći blok `BLOCKED_HARDWARE` iz Faze 1; mikrofon je tu sada | ✅ `PASS` — prva prihvaćena kalibracija i puna DET faza na uređaju |
| **B** | Faza 2 uvezana u `psd_live.c`, protokol bump | Gate prisustva sprječava lažnu anomaliju pri gašenju ventilatora | ✅ `PASS` — `asd-quality-v1.3.0`, parser `physical-fan-v1.6.0` |
| **C** | Taster za start učenja + LED signalizacija | Eksplicitan zahtjev; bez njega nema demoa | ✅ logika `PASS` (43 testa), hardver nije zalemljen |
| **D** | Faza 4: vremenska odluka | Jezgro zahtjeva da 1–2 izolovana score-prozora ne pokrenu alarm | ✅ `PASS` na sintetičkim score-pobudama — histereza usvojena, **EWMA i CUSUM odbačeni mjerenjem**; stvarne akustičke smetnje nisu ovim testirane |
| **E** | Faza 3: f0 / režim / order-normalized PSD | Otključava `SPEED_CHANGED` | ⛔ **negativan** — brzine se ne razlikuju po f0 |
| **F** | Faza 6: brzi tranzijentni put | Otključava `MECHANICAL_ANOMALY` | ⛔ **negativan** — +0,0012 AUC, unutar šuma |
| **G** | Faza 5: dual-channel near/far | **Mora prije finalne šeme** | ⛔ **negativan** — **šema ostaje sa jednim mikrofonom** |
| **H** | Faza 7: feasibility gate za PC teacher | Stop uslov je dozvoljen ishod | ⏸ `NOT_RUN` sa zapisanim razlogom |
| **I** | Faza 8: metrike, CI, završni izvještaj | Agregira sve prethodno | ✅ `PASS` — CI + provjera schema |
| **J** | Konsolidacija dokumentacije i putanje modela | Zadnje, da ne piše dva puta | ✅ `PASS` — [PREOSTALO.md](PREOSTALO.md) |

**Plan je zatvoren 14.08.2026.** Sve što je ostalo je fizički rad i nabrojano je
u [PREOSTALO.md](PREOSTALO.md). Jedna otvorena softverska stavka nije bila u
ovom planu jer je otkrivena tokom njegovog izvršenja: nestabilnost praga
([P17](../../docs/problemi-i-rjesenja.md#p17)), i ona je sada najvažniji sljedeći korak.

**G prije šeme, ne poslije.** Ovo je jedina stavka koja mijenja hardver.
Ako near/far donese mjerljiv dobitak na buci, finalna šema mora imati dva
INMP441 modula i drugi I2S slot. Ako ne donese, šema ostaje sa jednim i to je
zabilježen negativan rezultat, ne propust.

---

## 2. Kriteriji prolaza po bloku

Svaki blok se zatvara samo sa `PASS`, `FAIL` ili `BLOCKED_HARDWARE`.
`NOT_RUN` nije prolaz. Nijedan blok se ne zatvara na osnovu toga što je kod
napisan — traži se izmjerena vrijednost ili prošao test.

### A — puni živi lanac

- validna kalibracija prihvaćena na uređaju, `CALIBRATION_ACCEPTED` emitovan;
- DET faza radi bez `dropped`, bez `clipped`, bez ne-`OK` QUALITY zapisa;
- prijavljen prag, LOO statistika i rezerva do praga;
- izmjeren broj lažnih alarma na sat na ponovljenom normalnom zvuku.

### B — Faza 2 u živom toku

- `asd_decide()` je jedini izvor odluke; nema više ad-hoc brojača u petlji;
- `EVENT` nosi `event`, `capability` i `decision_level`;
- protokol bumpovan, parser i host validacija usklađeni;
- svi postojeći testovi i dalje prolaze, plus novi za uvezivanje.

### C — taster i lampica

- taster pokreće učenje; ponovni pritisak ne može tiho pomjeriti centar;
- lampica razlikuje najmanje: čekam / učim / naučio / anomalija;
- logika je host-testabilna, sa unit testovima na svaki prelaz;
- provjereno na uređaju, ne samo u testu.

### D — Faza 4

- parametri zaključani **samo** na normalnim podacima, prije bilo kakvog
  gledanja u anomalije;
- prijavljena latencija alarma i vrijeme oporavka;
- izmjereno odbijanje sintetičke score-pobude od 1–2 prozora; govor, udarac
  i prolazna akustička buka ostaju za fizički protokol;
- PC referenca i C implementacija se numerički poklapaju.

### E, F, G — istraživačke faze

- isti split manifest i provenance kao kanonski evaluator;
- target anomalije se otvaraju **tek poslije** zamrzavanja;
- negativan rezultat se objavljuje isto kao pozitivan;
- ništa se ne preimenuje u novi pravac ako je već probano i palo.

### H — teacher

- inventar prije instalacije: download, disk, RAM, runtime, licenca;
- stop uslov je legitiman kraj faze.

### I — metrike i CI

- bootstrap jedinica je ventilator/sesija, ne preklapajući prozor;
- CI vrti PC testove, schema provjeru i C parity;
- nijedan dokument ne miješa digitalni, zvučnik/mikrofon i fizički fan.

---

## 3. Šta ovaj plan namjerno NE radi

- **Ne dira kanonski evaluator v1.1.0.** Svi novi kandidati idu u zaseban
  developmental namespace.
- **Ne uvodi automatsku rekalibraciju.** Centar se ne pomjera bez operatera
  ([P10](../../docs/problemi-i-rjesenja.md#p10)).
- **Ne ponavlja već pale pravce** iz sekcije 2.4 `PLAN-NEXT-LEVEL.md`:
  clip-level envelope PSD, mel temporalna autokorelacija, slijepi rank ansambl,
  prosto near-far oduzimanje.
- **Ne naziva zvučnik ventilatorom.** Sve što je pušteno preko zvučnika ostaje
  označeno kao akustična reprodukcija snimka.

---

## 4. Evidencija

Rezultat svakog bloka ide u [DNEVNIK-NEXT-LEVEL.md](../dnevnici/DNEVNIK-NEXT-LEVEL.md)
istog dana kad je izmjeren, sa brojkama kakve jesu. Problemi i njihovi uzroci
idu u [problemi-i-rjesenja.md](../../docs/problemi-i-rjesenja.md). Putanja modela — šta je
probano, zašto je palo i šta je sljedeći korak riješio — ide u
[put-do-modela.md](../../docs/put-do-modela.md).
