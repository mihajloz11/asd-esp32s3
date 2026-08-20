# Kritični nalazi — pregled dorade faza 1–8

**Datum:** 20.08.2026.
**Pregledano:** necommit-ovano stanje (`git diff HEAD` + novi untracked moduli), faze 1–8
iz [PLAN-DORADA-POSLIJE-FAN01.md](PLAN-DORADA-POSLIJE-FAN01.md) i završna konsolidacija
[DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md](DORADA-SISTEMA-POSLIJE-FAN01-2026-08-20.md).
**Filter:** samo stvari koje obaraju izvođenje testa ili valjanost rezultata. Sitnice
(stil, duplikacija, latentni footgunovi) namjerno izostavljene.

**Status testova u trenutku pregleda:** `423 passed`. Svi nalazi ispod prolaze kroz
zelene testove — problemi su u *specifikaciji i međusobnoj saglasnosti brojeva*, ne u
kodu koji pada.

---

## 1. KRITIČNO — guided25 acceptance gate je aritmetički nemoguć; svaki run vraća FAIL

Ovo je najozbiljniji nalaz. Podrazumijevani fizički test **ne može proći, nikad, bez
obzira koliko dobro detektor radi.**

### Lanac

`start_fan_run.py` ima `--plan` sa `default="guided25"`
([start_fan_run.py:91](../pc/tools/start_fan_run.py)), panel u guided25 režimu šalje
`GUIDED25` firmveru i tvrdo zahtijeva 60/30 profil
([asd_panel.py:379](../pc/tools/asd_panel.py)). Dakle podrazumijevani operaterski put je
guided25.

Prolaz papirić bloka ([asd_panel.py:384](../pc/tools/asd_panel.py)):

```python
passing = sum(s["alarm_episodes"] >= 1 and s["anomaly_windows"] >= 3 for s in papers)
if passing < 2: reasons.append(f"papiric prosao {passing}/3 blokova; potrebno 2/3")
```

`anomaly_windows` broji DET redove sa `anom=1`. U firmveru
([psd_live.c:1044](../firmware/esp32s3_asd/main/psd_live.c)) `anom` je varijabla
`alarm`, tj. **aktivno alarmno stanje**, a ne „score iznad praga” — to je zaseban ispis
`"iznad praga"` uz `anom=0`.

Temporalna politika ima `min_consecutive = 3`
([asd_temporal_policy_v2.json](../pc/config/asd_temporal_policy_v2.json)), pa alarm
postaje aktivan tek na **trećem uzastopnom** prozoru iznad praga.

### Aritmetika

Da bi jedan papirić blok dao `anomaly_windows >= 3`, treba:

```
3 prozora da se alarm naoruža  +  3 prozora sa aktivnim alarmom  =  6 uzastopnih prozora
```

Prozor traje `HOPS_PER_CLIP 39 × HOP 4096 = 159 744 uzoraka @ 16 kHz = 9,984 s` plus
vrijeme računanja, dakle **≥10 s**. Šest prozora = **≥60 s**.

Papirić blok u planu traje **40 s**
([guided25_workflow_v1.json](../pc/config/guided25_workflow_v1.json)), a faze se
smjenjuju **strogo po tajmeru**, ne na operaterovu potvrdu —
`index, _ = self.state.phase_at(elapsed)` ([asd_panel.py:586](../pc/tools/asd_panel.py)).
Operaterova potvrda ide samo u `confirmed_phases` i utiče isključivo na INCONCLUSIVE.

40 s daje najviše 4 DET prozora. Alarm k tome **mora** biti neaktivan na početku bloka,
jer prethodna `recovery_normal_*` faza pada ako u njoj ima alarma
([asd_panel.py:389](../pc/tools/asd_panel.py)).

```
potrebno: ≥6 prozora (≥60 s)
dostupno:  4 prozora  (40 s)
```

**Ishod:** `passing` je uvijek 0, uslov `passing < 2` uvijek istinit, status uvijek
`FAIL` sa razlogom `papiric prosao 0/3 blokova; potrebno 2/3`.

### Šta popraviti (izbor, ne sve)

- produžiti papirić blokove na ≥70 s, **ili**
- brojati prozore iznad praga umjesto prozora sa aktivnim alarmom, **ili**
- spustiti `min_anomaly_windows_per_passing_paper_block` na 1 uz zadržan
  `alarm_episodes >= 1`.

Bez obzira na izbor — treba dodati test koji simulira idealan papirić blok (svi prozori
iznad praga) i tvrdi da gate **prolazi**. Trenutno takav test ne postoji, zato je ovo
prošlo kroz 423 zelena testa.

---

## 2. KRITIČNO — `threshold_enter = p90` normalnih score-ova protivrječi gate-u „0 epizoda”

### Šta kod radi

Poslije DERIVE bloka firmware zamrzava pragove
([psd_live.c:861-866](../firmware/esp32s3_asd/main/psd_live.c)):

```c
threshold_enter = percentile_higher(derive_sorted, derive_windows, 0.90f);
threshold_exit  = percentile_higher(derive_sorted, derive_windows, 0.75f);
```

`percentile_higher(…, 0.90)` nad 120 vrijednosti vraća `values[107]`, pa je **tačno 12
od 120 normalnih prozora (10 %) strogo iznad enter praga — po konstrukciji.**

### Zašto je to u sukobu sam sa sobom

Acceptance gate traži suprotno
([asd_commissioning_runtime_v1.json](../pc/config/asd_commissioning_runtime_v1.json)):

```json
"max_verify_episodes": 0, "max_verify_alarm_windows": 0,
"max_verify_chatter": 0, "verify_min_consecutive": 3
```

U VERIFY bloku (60 prozora iz iste raspodjele) očekuje se ~6 prozora iznad enter praga.
VERIFY pada čim se pojave 3 uzastopna. Uz nezavisnost to je ~5–6 % vjerovatnoće; uz
stvarnu vremensku autokorelaciju šuma ventilatora (termalni drift, promjene u prostoriji)
realno **znatno više**. Prag koji cilja nula lažnih epizoda mora ležati **iznad praktično
svih** normalnih podataka, a p90 leži usred njih.

### Isti fajl već dokumentuje da je p90 premali

[psd_live.c:40-46](../firmware/esp32s3_asd/main/psd_live.c), komentar koji je ostao od
ranije:

> *„Polazno pravilo je bio 90. percentil leave-one-out score-ova kalibracije (izmjereno
> na PC-u: odziv 64 %, lazni alarmi 12,7 % po prozoru). Zivo mjerenje 09.08. je pokazalo
> da je taj prag SISTEMATSKI PRENIZAK…”*

Novi p90 se računa nad 120 prozora kroz 20 minuta umjesto nad 10 uzastopnih LOO klipova,
pa hvata više kasnije varijacije — to je stvarno poboljšanje. Ali osnovna aritmetika
ostaje ista: **p90 znači 10 % normale iznad praga, kakav god skup prozora bio.**

### p90 nije ni među unaprijed registrovanim kandidatima

PC laboratorija ([derive_commissioning_policy.py:70-83](../pc/tools/derive_commissioning_policy.py))
ocjenjuje četiri kandidata:

| Kandidat | enter |
|---|---|
| `empirical-p99_exit-p75` | p99 |
| `median-plus-6mad_exit-2mad` | median + 6·MAD |
| `blockmax6-p90_exit-p75` | p90 **maksimuma po blokovima od 6** |
| `conformal-a05_exit-p75` | konformalni gornji kvantil, α=0,05 |

Sva četiri su drastično konzervativnija od sirovog p90. `blockmax6-p90` samo *liči* na
firmware pravilo — p90 blok-maksimuma je sasvim druga (mnogo viša) vrijednost od p90
sirovih score-ova.

### Firmware ne provjerava ni sopstveni prag na DERIVE bloku

`asd_commission_record_derive()`
([asd_commissioning.c:194-205](../firmware/esp32s3_asd/main/asd_commissioning.c)) samo
broji prozore — nema praćenja epizoda, high-run niza ni chattera. Episode metrike postoje
isključivo u `record_verify()`. Firmware dakle zamrzne p90 **ne provjerivši** da li taj
prag zadovoljava kriterije na samom DERIVE nizu, pa VERIFY otkriva problem tek kad je
kasno, a protokol tada nalaže odbacivanje cijelog runa.

Za poređenje, DORADA-SISTEMA §7.2 izričito traži da se kandidat bira tako da **na
DERIVE nizu** daje 0 epizoda, najduži high niz ≤2 i 0 chattera. Ta selekcija u firmveru
ne postoji.

---

## 3. KRITIČNO — PC commissioning laboratorija nema nikakav put do uređaja

Cijeli komandni skup firmvera je
([asd_cmd.c:53-64](../firmware/esp32s3_asd/main/asd_cmd.c)):

```
PRESS · HOLD · GUIDED25
```

**Nema komande za postavljanje praga.** Ne postoji ni NVS put za DEVELOPMENT build
(`profile_persistence_allowed = false`).

Posljedica: sve što Faza 4 izračuna — četiri kandidata, episode metrike, chatter,
stabilnost po blokovima, manifest sa hashovima — **ne može stići do uređaja.** Uređaj u
fizičkom runu uvijek sam izvede p90/p75 i to je jedini prag koji stvarno radi.

Faza 4 je time offline analiza koja opisuje sistem koji se ne izvršava. To treba ili
zatvoriti (dodati `SETTHR enter exit` komandu ili NVS import profila) ili eksplicitno
napisati u dokumentaciji da laboratorija ne utiče na live run.

---

## 4. VAŽNO — razgovor blokovi su zagarantovan FAIL, jer HOLD ne može nastati

Interference politika je isključena
([asd_interference.c:10-17](../firmware/esp32s3_asd/main/asd_interference.c),
[asd_interference_policy_v1.json](../pc/config/asd_interference_policy_v1.json)):

```c
.enabled = 0,
```

`asd_interference_update()` pri `enabled = 0` odmah vraća `PASS`
([asd_interference.c:51-53](../firmware/esp32s3_asd/main/asd_interference.c)), pa
**`OBSERVATION_HOLD` ne može nastati ni u jednom živom prozoru.**

*(Napomena: modul jeste ispravno ožičen — poziva se iz `asd_decide()` u
[asd_events.c:276](../firmware/esp32s3_asd/main/asd_events.c), a `psd_live.c` uredno
obrađuje HOLD stanje. Problem je isključivo `enabled = 0`, ne mrtav kod.)*

Posljedice:

1. FAN01 je pokazao da razgovor podiže score. Uz enter prag na p90 (nalaz 2) razgovor
   realno prelazi prag → gradi se obična alarmna epizoda.
2. Panel obara run čim se alarm pojavi u `ambient_*` fazi
   ([asd_panel.py:389](../pc/tools/asd_panel.py)) → `alarm u zabranjenoj fazi
   ambient_speech`.
3. DORADA-SISTEMA §7.3 kao frozen kriterij navodi *„oba 2/2 razgovor bloka na frozen
   interference kandidatu daju HOLD, ne novu anomaly epizodu”* — to **ovaj build ne može
   ispuniti ni u principu.**

Dokument to djelimično priznaje („conversation/HOLD dio je prvo frozen offline readout”),
ali kriterij je i dalje naveden kao uslov prolaza, a panel ga sprovodi kao FAIL. Treba
uskladiti: ili isključiti razgovor iz pass/fail, ili zamrznuti numeričke HOLD granice i
uključiti politiku.

---

## 5. VAŽNO — dva nesaglasna protokola; statistička tvrdnja se odnosi na onaj koji se ne izvršava

| Stavka | DORADA-SISTEMA §7.2–7.3 | guided25 (podrazumijevani) |
|---|---|---|
| DERIVE | 120 prozora / 20 min | **60 / 10 min** |
| VERIFY | 60 prozora / 10 min | **30 / 5 min** |
| Papirić blokovi | 3, svaki ≥5 punih prozora | 3, svaki **40 s** (≈4 prozora) |
| Prolaz papirića | **3/3** | **2/3** |
| Razgovor | 2 bloka, moraju dati HOLD | 1 blok, ne smije dati alarm |
| Vrata | — | **postoji, 20 s** |

Firmware `asd_commission_default_policy()` jeste 120/60 i poklapa se s dokumentom, ali
`asd_commission_guided25_policy()` je 60/30
([asd_commissioning.c:37-46](../firmware/esp32s3_asd/main/asd_commissioning.c)), a
podrazumijevani operaterski put vodi u guided25.

Konkretna posljedica po tvrdnju u dokumentu — DORADA-SISTEMA §7.2 kaže:

> *„Ako u 10 minuta nema nijedne epizode, jednostrani 95% Poisson gornji limit je
> `-ln(0,05)/(1/6 h) ≈ 18 epizoda/h”*

Uz guided25 VERIFY traje **5 minuta**, pa je tačna granica `-ln(0,05)/(1/12 h) ≈ 36
epizoda/h` — dvostruko lošija od napisane.

Takođe, §7.2 tvrdi da „research sidecar i host commissioning alat rade 20+10 podjelu”
iako firmware isporuči samo 90 prozora ukupno (60+30). Host ne može napraviti 120/60
podjelu iz 90 prozora.

---

## Šta je provjereno i **jeste** ispravno

Da ne bi ispalo da je sve loše — ovo su stvari koje sam ciljano provjerio i drže:

- **Kanonski `psd_shape` je ostao bit-identičan.** Sidecar koristi zasebnu petlju i
  zaseban akumulator, `asd_psd_stream_reset()` gasi sidecar, a produkcijski
  `finish()` put je netaknut ([psd_features_c.c](../firmware/esp32s3_asd/main/psd_features_c.c)).
  Ovo je bio najveći rizik za istorijske rezultate i uredno je izbjegnut.
- **Sidecar nije na stacku** — `static asd_psd_sidecar_t research_sidecar`
  ([psd_live.c:70](../firmware/esp32s3_asd/main/psd_live.c)), tačno kako plan traži.
- **HOLD semantika je kompletno ožičena** kroz `asd_decide()`; suspenduje buildup, ne
  briše aktivan alarm.
- **Nijedan istorijski artefakt nije prepisan** — svi `results/physical_fan/` unosi su
  novi; `recompute` ima eksplicitan guard protiv pisanja preko originalnog `SUMMARY.md`.
- **Research telemetrija je iza build flag-a** (`ASD_RESEARCH_TELEMETRY`), pa ne opterećuje
  produkcijski build. Ring buffer je 2 s, burst po prozoru ≈0,7 s na 115200 — staje.
- **423 testa prolaze**, ESP-IDF build prolazi, bin 349 728 B.

---

## Redoslijed kojim bih popravljao

1. **Nalaz 1** — bez toga fizički test ne može proći ni u najboljem slučaju. Uz popravku
   obavezno dodati test „idealan papirić blok ⇒ gate PASS”.
2. **Nalaz 2 + 3** — isti korijen: pravilo praga na uređaju ne odgovara ni gate-u ni
   laboratoriji, i nema mehanizma prenosa. Minimalno: podići enter na konformalni/p99
   kandidat i dodati provjeru na DERIVE nizu prije zamrzavanja.
3. **Nalaz 5** — uskladiti brojeve u dokumentu sa onim što podrazumijevana komanda
   stvarno pokreće i ispraviti Poisson granicu.
4. **Nalaz 4** — odlučiti da li razgovor ulazi u pass/fail u ovoj verziji.

Nalazi 1–3 su blokirajući za sljedeći fizički run. Nalazi 4–5 su blokirajući za tvrdnje
koje se iz tog runa smiju izvesti.
