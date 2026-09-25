# GUIDED25 — vođeni test ventilatora do 25 minuta

Ovo je **DEVELOPMENT validacija**, ne garancija da je razdvajanje papirića i
svake moguće spoljne buke već dokazano. Finalizovani rezultat je strogo
`PASS` ili `FAIL`; nedostatak dokaza je `FAIL`. Dozvoljeno je najviše **pet**
pokušaja (`attempt_limit` u `pc/config/guided25_workflow_v1.json`; podignuto
`3 → 5` kroz `recovery_amendment` 26.08.2026, vidi
[P27](problemi-i-rjesenja.md#p27--hard-deadline-od-25-min-obara-run-prije-kraja-plana)).

## Prije početka

Za dvoklik pokretanje, preflight, read-only pregled i rezervne komande vidi
`docs/KAKO-SAMOSTALNO-POKRENUTI-GUIDED25.md`. Najkraće je pokrenuti
`POKRENI-GUIDED25.cmd` i izabrati pravi test ili sigurni pregled.

1. Flashuj `ASD_PSD_LIVE` build napravljen sa `ASD_RESEARCH_TELEMETRY=1`.
2. Učvrsti ventilator, mikrofon ostavi 20 cm od njega, označi mjesto papirica
   i mjesto sa kog govoriš. Ne dodiruj lopatice.
3. Zatvori stare panele i pokreni:

```powershell
.\.venv\Scripts\python.exe pc\tools\start_fan_run.py `
  --fan-id fan02 --session-id guided25-01 --attempt 1 `
  --montaza-potvrdio "Mihajlo; ventilator je bezbjedno montiran i radi normalno"
```

Dashboard neće dozvoliti početak ako nema svježe UART telemetrije, GUIDED25
capability-ja, IDLE stanja, run direktorija ili ako je pokušaj veći od 5.
GUIDED25 automatski zahtijeva kompletan `FEATURE96`/`SUBSEG96` zapis.

## Tačni klikovi

Ako taster još nije zalemljen, klikni **„1A. VIRTUELNI TASTER — armiraj
GUIDED25 i pokreni”**. Panel tada šalje isti firmware događaj `PRESS` koji
kratki GPIO pritisak daje poslije debounce-a.
Kad ga zalemiš, klikni **„1B. Armiraj”**, pa jednom kratko pritisni fizički
taster. Oba ulaza poslije pritiska prolaze isti firmware put. Dugi pritisak
tokom učenja prekida sesiju; tokom nadzora traži novo učenje.

Tokom SETTLE/CENTER/DERIVE/VERIFY ništa ne diraj i ne pričaj. Firmware koristi
najviše 8 settle, 10 center, 44 derive i 22 verify prozora od 10 s. Planirani
najgori zbir je 22:50. Hard deadline više ne postoji — `hard_deadline_seconds`
je `null` od 27.08.2026, pa tok nije vremenski ograničen (P27).
Live DEVELOPMENT firmware izvodi `T_enter` kao p99 i `T_exit` kao p75 iz
DERIVE bloka. Nema `SETTHR` komande: kasnija PC laboratorija ne smije
retroaktivno promijeniti ovaj run. Kad panel kaže da je commissioning prošao,
klikni **„2. Kreni sa mjerenjem”**.

Panel zatim sam mijenja oznake i odbrojava 8:50 minuta. Duža faza ostavlja
jedan prelazni prozor van metrike i ipak daje traženi broj punih prozora:

| Faza | Vrijeme | Radnja |
|---|---:|---|
| normalna osnova | 0:50 | miruj |
| papirić 1 | 0:50 | papir uz usis, bez dodira |
| oporavak 1 | 0:50 | skloni papir i ruku |
| papirić 2 | 0:50 | ponovi isto |
| oporavak 2 | 0:50 | tišina |
| papirić 3 | 0:50 | ponovi isto |
| oporavak 3 | 0:50 | tišina |
| razgovor | 0:50 | normalan govor sa označenog mjesta |
| oporavak | 0:50 | tišina |
| vrata | 0:30 | jednom normalno otvori/zatvori; ne lupaj |
| završni oporavak | 0:50 | miruj |

Za svaki papirić, svaki oporavak, razgovor i vrata klikni **„Potvrdi START
faze”** odmah kada započneš radnju i **„Potvrdi END faze”** neposredno prije
kraja odbrojavanja. Potvrde su jednokratne, vezane za trenutno prikazanu fazu
i redoslijed; host u `events.csv` čuva njihov UTC timestamp. Automatska
`condition` oznaka bez oba operaterova klika nije dovoljan dokaz. Ako pogriješiš fazu, nestane telemetrija ili neko pomjeri postavku,
klikni **„Prekini i sačuvaj”**. Pauza tokom mjerenja je namjerno zabranjena jer
bi pokvarila vremenski dokaz. **Automatskog prekida po vremenu nema.** Raniji
hard deadline od 25:00 je uklonjen jer puni commissioning tok (~14 min) sa
planom od 11 faza više nije stajao u 1 500 s i obarao je ispravne runove
(P27). Ime „GUIDED25" je ostalo iz tog perioda. Runovi 27.08. trajali su
`1 509 s` i `2 000 s` i oba su završena planski.

## Lampice i prolaz

- zelena kratko bljeska: IDLE/čeka taster;
- zelena brzo treperi: učenje/commissioning, ništa ne diraj;
- zelena stalno: normalan nadzor;
- zelena sporo pulsira: runtime je u `OBSERVATION_HOLD`; kapija pouzdanosti je
  uključena (v3), ali je i dalje `DEVELOPMENT` — HOLD je vidljiv hostu i nije
  dokaz klasifikacije govora;
- crvena stalno: aktivna anomalija;
- obje daju dvostruki obrazac: fault, test prekini.

Preregistrovani prolaz traži: K1 i VERIFY prolaze; commissioning je tačno
44/22; postoji eksplicitan `DROPPED=0`; bar 2 od 3 papirić bloka dostignu
`consecutive>=3` i imaju stvarni ulazak u alarm. Ne traže se tri dodatna
prozora provedena u već aktivnom alarmu. Normalna osnova, svi oporavci, govor i
vrata moraju imati dovoljan broj izmjerenih prozora, 0 ulazaka u alarm i 0
prozora sa aktivnim — uključujući prenesenim — alarmom. `guided25_report.json`
se pravi tek nakon što host finalizuje kompletan par FEATURE96 + 5xSUBSEG96 za
svaki prozor i provjeri SHA-256 NPZ artefakta. Nedostatak bilo kog obaveznog
dokaza je `FAIL`, ne lažni PASS niti blagi `INCONCLUSIVE`.

Interference politika je `v3` i **uključena** (`enabled = 1`,
`asd_interference.c`), ali označena kao `DEVELOPMENT`. Apsolutna granica se ne
prenosi između sesija: izvodi se u svakoj sesiji kao `max(CAL normal) × 1,25`
iz normal-only prozora, pa papirić, govor i vrata ne ulaze u fit. Na runovima
27.08. je govor i vrata odbila kao nestabilne prozore
([DNEVNIK-NEXT-LEVEL.md](../privatno/dnevnici/DNEVNIK-NEXT-LEVEL.md)). Ovaj test i dalje može
dokazati samo **opaženu toleranciju** na konkretan govor i vrata u ovoj sobi;
ne dokazuje da postoji klasifikator govora/HOLD-a za svaku spoljnu buku.

Za svaki naredni pokušaj promijeni `--session-id` i `--attempt` (`2` do `5`).
Pokušaj se ponavlja samo zbog dokumentovane proceduralne/tehničke greške, ne
da bi se birao najljepši rezultat. Poslije posljednjeg pokušaja ne mijenjati pragove
prema papiriću; analizirati sačuvane 96+5x96 podatke.
