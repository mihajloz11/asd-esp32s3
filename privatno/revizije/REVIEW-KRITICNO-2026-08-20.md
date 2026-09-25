# Status kritičnih nalaza — dorada faza 1–8

**Datum prvog pregleda:** 20.08.2026.

**Status ažuriran:** 20.08.2026.

**Pregledano stanje:** trenutni `HEAD`, DEVELOPMENT `GUIDED25` put i odvojeni puni
120/60 commissioning put.

## Zaključak

U trenutnom kodu **nema otvorenog aritmetičkog blokera zbog kojeg bi svaki
`GUIDED25` run morao vratiti `FAIL`**. Raniji kritični nalazi opisivali su
međustanje dorade i više nisu važili za kod koji je na kraju commit-ovan. Stare
tvrdnje i računice su uklonjene iz ovog dokumenta da se ne tumače kao aktuelni
status.

Ovo ne znači da će fizički run sigurno proći. Znači samo da je prolaz moguć po
trenutnoj specifikaciji. Stvarni run i dalje smije legitimno pasti na VERIFY-u,
slabom odzivu na papirić, alarmu tokom normalne/speech/door faze, dropped
uzorcima, nepotpunoj telemetriji ili nepotvrđenim fazama.

## Zatvoreni nalazi

### 1. Papirić acceptance gate više nije aritmetički nemoguć

Podrazumijevani operaterski put i dalje je `GUIDED25`, ali aktuelni kriterij ne
traži tri dodatna prozora provedena u već aktivnom alarmu.

- svaki papirić blok traje 50 s;
- prvi `transition_window` ne ulazi u konačne metrike;
- prolaz bloka traži lokalni niz od najmanje tri uzastopna prozora sa
  `score > threshold` i najmanje jedan stvarni ulazak u alarm;
- najmanje 2/3 papirić bloka moraju proći.

Firmware aktivira `n=3` alarm na trećem uzastopnom visokom prozoru. Zato su tri
visoka evaluirana prozora dovoljna za stvarni ulazak u alarm; ne treba šest
prozora. Finalni evaluator tu računicu izvodi direktno iz `score` i `threshold`,
ne vjeruje prenesenom firmware brojaču.

Izvori:

- [guided25_workflow_v1.json](../../pc/config/guided25_workflow_v1.json)
- [asd_panel.py](../../pc/tools/asd_panel.py)
- [guided_test.py](../../pc/asd/guided_test.py)
- pozitivan test `test_finalized_report_accepts_one_alarm_window_with_persistent_paper_run`
  u [test_guided25_workflow.py](../../pc/tests/test_guided25_workflow.py)

### 2. Firmware više ne koristi sirovi p90 kao enter prag

Live commissioning koristi unaprijed registrovani par:

```text
T_enter = p99(DERIVE)
T_exit  = p75(DERIVE)
```

`GUIDED25` ima 44 DERIVE prozora. Uz `percentile_higher`, p99 nad 44 vrijednosti
je maksimum DERIVE bloka. Pošto je poređenje strogo `score > T_enter`, DERIVE
blok ne može napraviti niz od tri prozora iznad enter praga.

Kasnijih 22 VERIFY prozora su nezavisna provjera zamrznutog praga. VERIFY mora
imati 0 epizoda, 0 aktivnih alarmnih prozora i 0 chattera; pad odbija profil i
run. To je strog funkcionalni gate, ali nije aritmetička kontradikcija.

Izvori:

- [psd_live.c](../../firmware/esp32s3_asd/main/psd_live.c)
- [asd_commissioning.c](../../firmware/esp32s3_asd/main/asd_commissioning.c)
- test `test_firmware_uses_preregistered_p99_enter_that_cannot_arm_on_derive`
  u [test_guided25_workflow.py](../../pc/tests/test_guided25_workflow.py)

### 3. Granica PC laboratorije prema uređaju je namjerna i dokumentovana

DEVELOPMENT firmware nema `SETTHR` komandu i ne uvozi laboratorijski profil iz
NVS-a. To nije skriveni deployment put niti blocker za isti fizički run:

- uređaj sam izvodi preregistrovani `psd_shape` p99/p75 par iz svog DERIVE
  bloka;
- PC candidate laboratorija je offline analiza research sidecara;
- alternativni kandidat smije uticati samo na novu, verzionisanu policy/build
  verziju i novi preregistrovani retest;
- papirić ili govor iz istog runa ne mogu post-hoc promijeniti prag.

Izvori:

- [DORADA-FAZA4-COMMISSIONING-LAB-2026-08-20.md](../../docs/uredjaj/dorada-poslije-fan01-faze.md)
- [DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md](../../docs/uredjaj/dorada-poslije-fan01.md)

### 4. Razgovor nije uslovljen aktivnim HOLD-om

Numeric interference politika je i dalje `enabled=false`, pa live run ne tvrdi
da ima potvrđen klasifikator govora niti zahtijeva `OBSERVATION_HOLD` za prolaz.
Aktuelni `GUIDED25` kriterij za razgovor i vrata traži da nema ulaska u alarm ni
prenesenog aktivnog alarma.

Zato razgovor nije zagarantovan `FAIL`. Ako konkretna postavka ne alarmira,
blok može proći; ako alarmira, run ispravno pada. Takav prolaz dokazuje samo
opaženu toleranciju te konkretne postavke, ne opštu otpornost na govor.

Izvori:

- [asd_interference_policy_v1.json](../../pc/config/asd_interference_policy_v1.json)
- [guided_test.py](../../pc/asd/guided_test.py)
- [DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md](../../docs/uredjaj/dorada-poslije-fan01.md)

### 5. GUIDED25 i puni commissioning protokol su razdvojeni i brojčano usklađeni

Podrazumijevani `GUIDED25` i puni laboratorijski tok nisu isti eksperiment:

| Stavka | `GUIDED25` | Puni default tok |
|---|---:|---:|
| DERIVE | 44 prozora | 120 prozora |
| VERIFY | 22 prozora | 60 prozora |
| Papirić readout | 3 × 50 s, prolaz 2/3 | nije isti protokol |
| Namjena | kratki funkcionalni gate | duži normal-only commissioning |

Za 22 VERIFY prozora bez epizode jednostrani 95% Poisson gornji limit je oko
49,1 epizoda/h. Ranijih približno 18 epizoda/h odnosi se samo na odvojeni puni
tok sa 60 VERIFY prozora. Obje granice su kratki razvojni rezultati, ne
proizvodne tvrdnje.

Izvori:

- [guided25_workflow_v1.json](../../pc/config/guided25_workflow_v1.json)
- [asd_commissioning.c](../../firmware/esp32s3_asd/main/asd_commissioning.c)
- [DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md](../../docs/uredjaj/dorada-poslije-fan01.md)

## Šta ostaje otvoreno

Ovo su stvarne granice trenutnog dokaza, ali nijedna nije dokaz da je acceptance
gate aritmetički nemoguć:

- trenutni source/build još mora biti flashan i provjeren na stvarnom uređaju;
- novi fizički fan/papirić/govor/vrata run još mora dati svoj stvarni
  `guided25_report.json`;
- p99/p75 i 44/22 su DEVELOPMENT politika i još nemaju dugoročnu fizičku
  validaciju lažnih alarma;
- numeric HOLD politika ostaje isključena i nije dio trenutnog pass/fail gate-a;
- DEVELOPMENT NVS persistence ostaje zatvoren dok policy ne bude fizički
  potvrđen i zasebno verzionisan.

Mjerodavan završni rezultat fizičkog prolaza je samo sačuvani
`guided25_report.json` sa statusom `PASS`, uz važeći protokol, `DROPPED=0`,
kompletnu research telemetriju i uredno potvrđene faze.

## Provjera ovog ažuriranja

Na trenutnom `HEAD`-u je 20.08.2026. pokrenuto:

```powershell
.\.venv\Scripts\python.exe -m pytest pc/tests -q
```

Rezultat: **449 passed**. Zeleni testovi potvrđuju softverske ugovore i zatvorene
aritmetičke/specifikacijske nalaze; ne zamjenjuju novi fizički test ventilatora.

> **Dopuna 22.08.2026.** Tih `449` je broj na mašini sa raspakovanim DCASE `fan`
> skupom u `data/`. Bez skupa isti commit daje **`444 passed, 5 skipped`** — pet
> testova u `test_features_c.py` i `test_psd_features_c.py` traže stvarne klipove
> i tada se preskaču, ne padaju. Oba broja opisuju isto stanje koda; razlika je
> samo prisustvo skupa. Provjereno ponovnim pokretanjem suite-a na `730c2f4`.
