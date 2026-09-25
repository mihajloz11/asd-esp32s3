# GUIDED25: vođeni test ventilatora

Jedno uputstvo za pokretanje, tok, kriterije i zapise testa. Spaja ranija
`GUIDED25-TEST-VENTILATORA.md` i `KAKO-SAMOSTALNO-POKRENUTI-GUIDED25.md`
(25.09.2026); dijelovi koji su se razilazili sa kodom su ispravljeni prema
`pc/config/guided25_workflow_v1.json` i `psd_live.c`.

Ovo je **DEVELOPMENT validacija**, ne garancija da je razdvajanje papirića i
svake spoljne buke dokazano. Rezultat je strogo `PASS` ili `FAIL`; nedostatak
dokaza je `FAIL`. Dozvoljeno je najviše **pet** pokušaja (`attempt_limit`;
podignuto `3 → 5` kroz `recovery_amendment` 26.08.2026, vidi
[P27](../problemi-i-rjesenja.md#p27--hard-deadline-od-25-min-obara-run-prije-kraja-plana)).
Ishod proba od 27.08. je u
[rezultat-finalna-validacija-2026-08-27.md](rezultat-finalna-validacija-2026-08-27.md).

## 1. Build i flash

Mjerodavan je build od 27.08.2026; isti binarni fajl je pustio oba validna
runa tog dana. Sadrži P20 telemetrijsku popravku, sesijsku HOLD kalibraciju v3
iz normalnog rada, frozen CAL centar sa empirijskim p99 pragom (P26) i uklonjen
hard-stop start-gate (P27). Poslije svake izmjene koda `reconfigure` i flash su
ponovo obavezni.

```powershell
$env:ASD_PSD_LIVE = "1"; $env:ASD_RESEARCH_TELEMETRY = "1"
. "$HOME\esp\esp-idf\export.ps1"
Set-Location "$HOME\Desktop\master new\firmware\esp32s3_asd"
idf.py reconfigure
idf.py build
idf.py -p COM3 flash
```

`reconfigure` nije opcion; bez njega build tiho ostane u starom modu
([P2](../problemi-i-rjesenja.md#p2)). Poslije flasha provjeri da preflight vidi
novi bin:

```powershell
Set-Location "$HOME\Desktop\master new"
.\POKRENI-GUIDED25.cmd preflight
```

SHA-256 mjerodavnog builda je
`9AC2CACA2C5010747547D4BB942AAE96F700221588A4A6863B5C01948D967813`
(354 784 B; `provenance.json` oba validna runa 27.08.). Ako preflight ispiše
drugi heš, source/build i ploča više nisu isti dokaz.

## 2. Postavka

- Učvrsti ventilator. Probe 27.08. su rađene sa `fan02`, mikrofon na 40 cm i
  9° (prvi test FAN01: 20 cm, 90° na osu duvanja).
- Označi mjesto papirića i mjesto sa kog se govori. Ne dodiruj lopatice.
- Ako je ploča već nešto radila od zadnjeg uključenja, **isključi je i vrati
  USB**. Stanje uređaja preživljava otvaranje porta: poslije prekinutog ili
  odbijenog pokušaja ploča ostaje u `FAULT`/`CALIBRATION_REJECTED`, a preflight
  tada odbija start sa `nedostaje 'mode=IDLE'`.
- Zatvori stare preview/dashboard PowerShell prozore.

## 3. Pokretanje

### Dvoklik

1. Priključi ploču i provjeri da je `COM3`.
2. Dvaput klikni `POKRENI-GUIDED25.cmd` u korijenu projekta.
3. Izaberi `2`, prihvati ponuđeni `fan02` ili unesi svoj ID, unesi broj
   pokušaja (`1` do `5`), pa upiši `DA` tek poslije svoje provjere montaže.
4. Ne zatvaraj PowerShell prozor. To je glavni host proces i u njemu se odmah
   snimaju logovi. Browser se otvara sam na `http://127.0.0.1:8772/`.

Prije pokretanja launcher otvara COM port samo za čitanje i traži tačno
`asd-quality-v1.6.0`, `IDLE`, `GUIDED25=1`, research telemetriju,
`workflow_pending=DEFAULT`, zatvoren DEVELOPMENT persistence gate i
`dropped=0`. Ako bilo šta fali, pravi run se ne pokreće. Dashboard takođe
odbija početak bez svježe UART telemetrije, run direktorija ili ako je pokušaj
veći od 5. GUIDED25 sam zahtijeva kompletan `FEATURE96`/`SUBSEG96` zapis.

Za pregled bez testa izaberi `1`. To je read-only režim na serveru: svi
klikovi koji bi poslali komandu su blokirani, pokušaj se ne troši, a preview
se sam zatvara poslije 15 minuta.

### Iz PowerShella

Iz korijena repoa:

```powershell
$env:PYTHONUTF8 = "1"
.\POKRENI-GUIDED25.cmd preflight
.\POKRENI-GUIDED25.cmd preview
.\POKRENI-GUIDED25.cmd test
```

Launcher pravi jedinstven `session-id` iz datuma i vremena. Sa eksplicitnim
vrijednostima, bez menija:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\pc\tools\guided25_launcher.ps1 `
  -Mode Test -Port COM3 -FanId fan02 -SessionId guided25-01 -Attempt 1
```

Sirova komanda koju launcher na kraju poziva:

```powershell
.\.venv\Scripts\python.exe .\pc\tools\start_fan_run.py `
  --port COM3 --fan-id fan02 --session-id guided25-01 --attempt 1 `
  --plan guided25 `
  --montaza-potvrdio "Mihajlo; ventilator je bezbjedno montiran i radi normalno"
```

GUIDED25 sam dodaje `--research-telemetry-required` i zaključani
`--guided-workflow guided25`. Za pravi test ne pokreći samo panel.

## 4. Klikovi i tok

- Bez zalemljenog tastera klikni **„1A. VIRTUELNI TASTER: armiraj GUIDED25 i
  pokreni"**. Panel šalje isti firmware događaj `PRESS` koji daje kratak GPIO
  pritisak poslije debounce-a.
- Sa tasterom klikni **„1B. Armiraj"**, pa jednom kratko pritisni taster. Dugi
  pritisak tokom učenja prekida sesiju; tokom nadzora traži novo učenje.
- Tokom SETTLE/CENTER/DERIVE/VERIFY ne prilazi i ne pričaj. Firmware koristi
  najviše 8 settle, 10 center, 44 derive i 22 verify prozora od 10 s.
- `T_enter` je p99 DERIVE ocjena (za 44 prozora to je maksimum), `T_exit` je
  p95, ograničen na opseg od p50 do polovine `T_enter`. Nema `SETTHR`
  komande: kasnija PC analiza ne smije retroaktivno promijeniti run.
- Kad panel javi da je kalibracija gotova, klikni **„2. Kreni sa mjerenjem"**.
  Dugme ostaje blokirano bez validnog
  `INTERFERENCE ... source=CAL_NORMAL_ONLY` zapisa; to se ne može preskočiti.
- Panel sam vremenski označava svaki uslov i odbrojava. Potvrde START/END po
  fazi više ne postoje; radnju radi u tačno prikazanom okviru.
- Ako faza krene pogrešno, nestane telemetrija ili se pomjeri postavka, klikni
  **„Prekini i sačuvaj"**. Pauza tokom mjerenja je namjerno zabranjena.

Plan mjerenja traje 8:50 minuta:

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
| vrata | 0:30 | jednom normalno otvori i zatvori; ne lupaj |
| završni oporavak | 0:50 | miruj |

Svaka faza ostavlja jedan prelazni prozor van metrike i ipak daje traženi broj
punih prozora.

**Vremenskog roka više nema.** `hard_deadline_seconds` je `null` od
27.08.2026, nadzorni thread se ne pokreće i preflight ne traži rezervu (P27).
Ime „GUIDED25" je ostalo iz perioda roka od 25 minuta. Runovi 27.08. trajali
su 1 509 s i 2 000 s i oba su završena planski. Planirani najgori tok je
22:50; sa izmjerenim prozorom od 9,981 s i WAIT fazom stvarno je 23:03.

### Crvene poruke na vrhu panela

| Poruka | Značenje | Šta uraditi |
|---|---|---|
| `RESEARCH TELEMETRIJA JE POKVARENA` | bar jedan `FEATURE96`/`SUBSEG96` red je stigao isprepletan; host će run odbiti kao `invalid_research_telemetry` | odmah **Prekini i sačuvaj**, provjeri da je flešovan build sa [P20](../problemi-i-rjesenja.md#p20) popravkom, pa ponovi pokušaj |
| `UREDJAJ JE JOS U ALARMU` | alarm u tekućoj fazi obara run, a sljedeći papirić nema u šta da uđe | skloni papirić **i ruku**, odmakni se korak, sačekaj da poruka nestane |
| `KALIBRACIJA JE GOTOVA ...` | commissioning je prošao, mjerenje nije počelo | klikni odmah da postavka ne odstoji |

## 5. Lampice

- zelena kratko bljeska: IDLE, čeka taster;
- zelena brzo treperi: učenje, ništa ne diraj;
- zelena stalno: normalan nadzor;
- zelena sporo pulsira: `OBSERVATION_HOLD`; kapija pouzdanosti je uključena
  (v3), ali je `DEVELOPMENT` i nije dokaz klasifikacije govora;
- crvena stalno: aktivna anomalija;
- obje u dvostrukom obrascu: fault, test prekini.

## 6. Kriterij prolaza

Preregistrovani prolaz traži:

- K1 i VERIFY prolaze, commissioning je tačno 44/22, postoji eksplicitan
  `DROPPED=0`;
- bar 2 od 3 papirić bloka dostignu `consecutive>=3` i imaju stvarni **ulazak**
  u alarm unutar faze. Ne traže se tri dodatna prozora u već aktivnom alarmu;
- normalna osnova, svi oporavci, govor i vrata imaju dovoljno izmjerenih
  prozora, 0 ulazaka u alarm i 0 prozora sa aktivnim, uključujući prenesenim,
  alarmom.

`guided25_report.json` nastaje tek kad host finalizuje kompletan par
FEATURE96 + 5×SUBSEG96 za svaki prozor i provjeri SHA-256 NPZ artefakta.

Interference politika `v3` je uključena (`enabled = 1`, `asd_interference.c`),
ali `DEVELOPMENT`. Granica se ne prenosi između sesija: računa se u svakoj
sesiji kao `max(CAL normal) × 1,25` iz normalnih prozora, pa papirić, govor i
vrata ne ulaze u fit. Test dokazuje samo **opaženu toleranciju** na konkretan
govor i vrata u ovoj sobi, ne klasifikator za svaku spoljnu buku.

Novi pokušaj (novi `--session-id`, `--attempt` 2 do 5) samo zbog zapisane
tehničke ili proceduralne greške, nikad zbog lošeg rezultata. Poslije
posljednjeg pokušaja pragovi se ne štimaju prema papiriću; analiziraju se
sačuvani 96 + 5×96 podaci.

`VERIFY_NORMAL_REJECT` na ispravnom ventilatoru nije kvar ni greška
operatera. `T_enter` je najveća od 44 DERIVE ocjena, a VERIFY pada tek na tri
uzastopna prozora iznad njega (`verify_min_consecutive = 3`,
`asd_commissioning.c`). Simulacija nad replikom te logike (400 000 pokušaja)
daje 0,12 % odbijanja za nezavisne prozore, 0,98 % pri `rho=0,3`, 4,8 % pri
`rho=0,6` i 15,4 % pri `rho=0,85`. Lag-1 autokorelacija iz DET ocjena runa
16.08. je 0,49, ali iz samo pet prozora. Realno je oko jedan do pet posto.
Zapiši ishod i ponovi pokušaj.

## 7. Zapisi

Sve ide u novi direktorij:

```text
results\physical_fan\run_<UTC>_<fan-id>_<session-id>\
```

- `serial.log`: vremenski označena UART telemetrija;
- `events.csv`: komande i uslovi;
- `detections.csv`: ocjena, prag i alarm po prozoru;
- `firmware_events.csv`: strukturirani firmware događaji;
- `window_features.npz` i `window_features.manifest.json`: 96 PSD vrijednosti
  i pet podsegmenata, sa SHA-256 provjerom;
- `provenance.json` i `SUMMARY.md`: metapodaci i sažetak;
- `guided25_report.json`: mjerodavni završni `PASS` ili `FAIL`.

Praćenje uživo u drugom PowerShell prozoru:

```powershell
.\POKRENI-GUIDED25.cmd logs
```

ili ručno:

```powershell
$run = Get-ChildItem .\results\physical_fan -Directory -Filter 'run_*' |
  Sort-Object LastWriteTimeUtc | Select-Object -Last 1
Get-Content -LiteralPath (Join-Path $run.FullName 'serial.log') -Wait -Tail 40
```

`Ctrl+C` u prozoru koji prati log zatvara samo taj prikaz. Ne pritiskaj ga u
glavnom prozoru testa.

Po završetku:

```powershell
$run = Get-ChildItem .\results\physical_fan -Directory -Filter 'run_*' |
  Sort-Object LastWriteTimeUtc | Select-Object -Last 1
Get-Content -Raw (Join-Path $run.FullName 'guided25_report.json')
Get-FileHash -Algorithm SHA256 `
  -LiteralPath (Join-Path $run.FullName 'window_features.npz')
```

Rezultat važi samo ako `guided25_report.json` postoji i kaže `PASS`. Sačuvaj
cijeli run direktorij i ne uređuj artefakte ručno.

## 8. Naučeno iz runa 22.08.2026 (`paper_blocks_passed: 1/3`)

Tri stvari su oborile run, a nijedna nije bila kvar uređaja.

**Ručne potvrde faza nisu dio testa.** Panel sam označava uslove; jedini ručni
klik poslije početka kalibracije je „Kreni sa mjerenjem".

**Papirić blok se ocjenjuje po ulasku u alarm, ne po jačini.** Ako uređaj još
nije izašao iz prethodnog alarma, novog ulaska nema. Tako su papirići 2 i 3
propali unutar alarma koji je trajao od papirića 1 do oporavka 3.

**Oporavak je gotov kad uređaj to kaže.** Izlaz ide na `threshold_exit`
(tada 824, uz `threshold_enter` 4374). Dok je papir bio blizu, ocjena je
stajala na 1002–1924; kad je sklonjen, pala je na 752 i alarm je nestao.

Budžet vremena tog runa, kad je rok od 1 500 s još važio:

| Dionica | Trajanje |
|---|---|
| taster do početka kalibracije (WAIT/settle) | 55 s |
| commissioning (CENTER + DERIVE + VERIFY) | 759 s |
| čekanje na „Kreni sa mjerenjem" | 126 s |
| plan od 11 faza | 530 s |
| ukupno | 1 470 s od 1 500 s |

Rezerva od 30 s je bila razlog da se rok ukine.

Ocjene tog runa, uz prag 4374, prije kapije pouzdanosti:

| Uslov | Ocjena |
|---|---|
| normalan rad | 500–1100 |
| papirić | 10 073 |
| govor | 21 162 |
| vrata | 73 319 |

Detektor je jednoklasni: sve što je daleko od normalnog spektra ventilatora
diže ocjenu. Govor preko cijelog prozora dodaje energiju u trake u kojima
ventilator nema ništa, pa ide dalje od centra nego papirić. Na runovima 27.08.
kapija v3 je nestabilne prozore govora i vrata poslala u `OBSERVATION_HOLD`
umjesto u alarm. Ako `ambient_speech` ipak obori run, to se prijavljuje kao
rezultat, ne popravlja štimanjem pragova.
