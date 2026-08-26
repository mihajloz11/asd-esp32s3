# Kako samostalno pokrenuti GUIDED25 test i sve logove

Ovo je rezervno operatersko uputstvo za slučaj da glavni launcher nije dostupan. Jedan
launcher pokreće host snimanje, obaveznu research telemetriju, dashboard i sve
artefakte. Nijedna komanda ispod sama ne pokreće ventilator; operater potvrđuje
postavku, a učenje počinje tek poslije klika u dashboardu.

## Obavezno prije narednog runa: flashuj popravku

Ploča je 26.08.2026 flešovana buildom koji sadrži P20 telemetrijsku popravku,
normal-only sesijsku HOLD kalibraciju v3 i hard-stop start-gate. Ako se poslije
izmjene koda pravi novi build, `reconfigure` i flash su ponovo obavezni.

```powershell
$env:ASD_PSD_LIVE = "1"; $env:ASD_RESEARCH_TELEMETRY = "1"
. "$HOME\esp\esp-idf\export.ps1"
Set-Location "$HOME\Desktop\master new\firmware\esp32s3_asd"
idf.py reconfigure
idf.py build
idf.py -p COM3 flash
```

`reconfigure` nije opcion — bez njega build tiho ostane u starom modu ([P2](problemi-i-rjesenja.md#p2)).
Poslije flasha provjeri da preflight vidi novi bin:

```powershell
Set-Location "$HOME\Desktop\master new"
.\POKRENI-GUIDED25.cmd preflight
```

SHA-256 trenutno flešovanog builda je
`A1778C599A3E2154D960C197AA34E891531688137A657C01A5D16A1ED5718D17`;
ako preflight ispiše drugi heš, source/build i ploča više nisu isti dokaz.

## Najkraći put

1. Priključi ploču i provjeri da se pojavila kao `COM3`.
2. Ako je ploča već nešto radila od zadnjeg uključenja, **isključi je i vrati
   USB**. Stanje uređaja preživljava otvaranje porta: poslije prekinutog ili
   odbijenog pokušaja ploča ostaje u `FAULT`/`CALIBRATION_REJECTED`, a
   preflight tada uredno odbija start sa `nedostaje 'mode=IDLE'`.
3. Zatvori eventualni stari preview/dashboard PowerShell prozor.
4. Dvaput klikni `POKRENI-GUIDED25.cmd` u korijenu projekta.
5. Izaberi `2`, prihvati ponuđeni `fan02` ili unesi svoj ID, unesi pokušaj
   `1`, `2` ili `3`, pa upiši `DA` tek nakon svoje provjere montaže.
6. Ne zatvaraj PowerShell prozor. On je glavni host proces i u njemu se odmah
   snimaju logovi. Browser se otvara automatski na `http://127.0.0.1:8772/`.

Prije pokretanja launcher otvara COM port samo za read-only provjeru i zahtijeva
tačan `asd-quality-v1.5.0`, `IDLE`, `GUIDED25=1`, research telemetriju,
`workflow_pending=DEFAULT`, zatvoren DEVELOPMENT persistence gate i `dropped=0`.
Ako bilo šta od toga nedostaje, pravi run se ne pokreće.

Za pregled bez testa izaberi `1`. To je server-side read-only režim: svi
klikovi koji bi poslali komandu su blokirani, pokušaj se ne troši, a preview se
sam zatvara poslije 15 minuta.

## Isto iz PowerShella

Iz `C:\Users\mihaj\Desktop\master new`:

```powershell
$env:PYTHONUTF8 = "1"
.\POKRENI-GUIDED25.cmd preflight
.\POKRENI-GUIDED25.cmd preview
```

Za pravi test:

```powershell
$env:PYTHONUTF8 = "1"
.\POKRENI-GUIDED25.cmd test
```

Launcher automatski pravi jedinstven `session-id` iz datuma i vremena. Za
potpuno eksplicitne vrijednosti, bez menija:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\pc\tools\guided25_launcher.ps1 `
  -Mode Test -Port COM3 -FanId fan02 -SessionId guided25-01 -Attempt 1
```

Sirova komanda koju launcher na kraju poziva je:

```powershell
.\.venv\Scripts\python.exe .\pc\tools\start_fan_run.py `
  --port COM3 --fan-id fan02 --session-id guided25-01 --attempt 1 `
  --plan guided25 `
  --montaza-potvrdio "Mihajlo; ventilator je bezbjedno montiran i radi normalno"
```

GUIDED25 sam dodaje `--research-telemetry-required` i zaključani
`--guided-workflow guided25`; nemoj ručno pokretati samo panel za pravi test.

## Klikovi i trajanje

- Bez zalemljenog tastera: klikni **1A. VIRTUELNI TASTER — armiraj GUIDED25 i
  pokreni**. To šalje isti firmware `PRESS` put kao kratki GPIO pritisak.
- Sa zalemljenim tasterom: klikni **1B. Armiraj**, pa kratko pritisni taster.
- Tokom SETTLE/CENTER/DERIVE/VERIFY ne prilazi i ne pričaj.
- Kad piše da je kalibracija gotova, klikni **2. Kreni sa mjerenjem**.
- Dugme ostaje server-side blokirano ako nema validnog
  `INTERFERENCE ... source=CAL_NORMAL_ONLY` zapisa ili ako cijeli plan + 20 s
  rezerve više ne mogu stati u hard stop. To nije upozorenje koje se može
  preskočiti.
- Panel sam vremenski označava svaki uslov i prikazuje odbrojavanje. Ne klikći
  START/END unutar faza: radi radnju u tačno prikazanom okviru.
- Ako nešto nije urađeno tačno po uputstvu, klikni **Prekini i sačuvaj**.

### Crvene poruke na vrhu panela

Panel sada sam prijavljuje ono što run obara, dok se pokušaj još može prekinuti:

| Poruka | Šta znači | Šta uraditi |
|---|---|---|
| `RESEARCH TELEMETRIJA JE POKVARENA` | Bar jedan `FEATURE96`/`SUBSEG96` red je stigao isprepletan; host će run odbiti kao `invalid_research_telemetry` | Odmah **Prekini i sačuvaj**, provjeri da je flashovan build sa [P20](problemi-i-rjesenja.md#p20) popravkom, pa ponovi pokušaj |
| `PROPUSTENE POTVRDE` | Faza je prošla bez `START` i `END` klika i više se ne može potvrditi | Run je već pao; prekini i ponovi |
| `UREDJAJ JE JOS U ALARMU` | U tekućoj fazi alarm obara run, a dok traje, sljedeći papirić nema u šta da uđe | Skloni papirić **i ruku**, odmakni se korak, sačekaj da poruka nestane |
| `KALIBRACIJA JE GOTOVA — KLIKNI "2. KRENI SA MJERENJEM"` | Hard stop teče, a mjerenje još nije počelo | Klikni odmah; vidi budžet ispod |
| `HARD STOP ZA mm:ss` | Manje od tri minuta do automatskog prekida | Ne oklijevaj sa potvrdama |

### Budžet vremena — 22.08. je preživio sa 30 s rezerve

Hard stop od `1500 s` teče od **početka sesije** (pritisak tastera), ne od
početka mjerenja. Izmjereno u runu 22.08.2026:

| Dionica | Trajanje |
|---|---|
| taster → početak kalibracije (WAIT/settle) | `55 s` |
| commissioning (CENTER + DERIVE + VERIFY) | `759 s` |
| **čekanje da operater klikne „Kreni sa mjerenjem"** | **`126 s`** |
| plan od 11 faza | `530 s` |
| ukupno | `1470 s` od `1500 s` |

Najgori dozvoljeni commissioning je `840 s`, a plan je fiksnih `530 s` — znači
operateru za odluku ostaje najviše oko `130 s`, a potrošeno je `126 s`. Prošlo je
samo zato što se ploča tog puta ustalila prije roka. Klikni čim se pojavi poruka
da je kalibracija gotova.

### Naučeno iz runa 22.08.2026 (`paper_blocks_passed: 1/3`)

Tri stvari su tada oborile run, a nijedna nije bila kvar uređaja.

**Potvrde faza nisu dio testa.** Panel automatski vremenski označava uslove;
jedini potreban ručni klik poslije početka kalibracije je **Kreni sa mjerenjem**.

**Papirić blok se ocjenjuje po ULASKU u alarm, ne po jačini.** Traže se tri
uzastopna prozora iznad praga i bar jedan prelaz iz normalnog stanja u alarm
unutar te faze. Blokovi se međusobno **ne** porede, pa papirić ne mora svaki put
biti isti po jačini ni po frekvenciji. Ali ako uređaj još nije izašao iz
prethodnog alarma, novog ulaska nema i blok ne prolazi — tako su 22.08. papirići
2 i 3 propali unutar alarma koji je trajao od papirića 1 do oporavka 3.

**Oporavak je gotov tek kad uređaj to kaže.** Izlaz iz alarma ide na
`threshold_exit`, koji je tog runa bio `824` uz `threshold_enter` `4374`. Dok je
papir bio u blizini, skor je stajao na `1002–1924` i alarm se držao; čim je
papir stvarno sklonjen, skor je pao na `752` i alarm je nestao. Zato: skloni
papirić **i ruku**, sačekaj da `ANOMALIJA` indikator na panelu prestane da
svijetli, pa tek onda potvrdi kraj oporavka.

### Šta ambijentalne faze stvarno mjere

Izmjereni skorovi tog runa, uz prag `4374`:

| Uslov | Skor |
|---|---|
| Normalan rad | `500–1100` |
| Papirić | `10073` |
| Govor | `21162` |
| Vrata | `73319` |

Detektor je jednoklasni: uči šta je normalan spektar ventilatora i prijavljuje
sve što je od njega daleko. Ne traži da smetnja bude stalna ni jednolična —
govor preko cijelog prozora od deset sekundi doda energiju u trake u kojima
ventilator nema ništa, pa vektor odlazi dalje od centra nego kod papirića.

Gate koji bi smetnju razlikovao od kvara postoji (`asd_interference.c`), ali mu
je politika namjerno isključena (`enabled = 0`, pragovi `0.0`) dok se ne izvedu
iz fizičkih normal-only podataka. Dok je tako, `ambient_speech` može oboriti
run, i to je **izmjereno ograničenje jednog mikrofona**, ne kvar. Govori tiše i
dalje od mikrofona nego 22.08.; ako i tada padne, to je rezultat koji se
prijavljuje, a ne popravlja štelovanjem pragova.

Planirani najgori tok traje `22:50`; hard stop je `25:00`. Izmjereno trajanje
jednog prozora je `9,981 s`, pa sa WAIT fazom najgori tok stvarno iznosi
`23:03` — rezerva do hard stopa je oko dva minuta. Zato poslije poruke da je
kalibracija gotova odmah klikni **2. Kreni sa mjerenjem**. Panel dodatno traži
da u tom trenutku preostalih 25 minuta pokriva svih 530 s mjerenja i 20 s
rezerve; ako ne pokriva, odbija start umjesto da svjesno proizvede nepotpun
run. Ne ponavljaj pokušaj zbog lošeg rezultata, nego samo zbog zapisane
tehničke/proceduralne greške. Ukupno su dozvoljena najviše tri pokušaja.

Jedan ishod nije kvar ni greška operatera. `threshold_enter` je `p99` od 44
DERIVE prozora, što za taj broj prozora ispada tačno **najveći** izmjereni
skor. Ali `VERIFY` ne pada na jednom prozoru iznad njega: `verify_alarm_windows`
raste tek kad se upali epizoda, a za to trebaju **tri uzastopna** prozora iznad
praga (`verify_min_consecutive = 3`, `asd_commissioning.c:236` i `:246`).

Simulirano nad tačnom replikom te logike, `400.000` pokušaja: ako su prozori
nezavisni uzorci iste distribucije, `VERIFY_NORMAL_REJECT` pada u `0,12%`
pokušaja. Susjedni prozori sa istog ventilatora ipak nisu nezavisni, a rizik
na to jako reaguje — `0,98%` pri `rho=0,3`, `4,8%` pri `rho=0,6` i `15,4%` pri
`rho=0,85`. Iz DET skorova run-a 16.08. lag-1 autokorelacija normalnih prozora
ispada `0,49`, ali iz samo pet uzastopnih normalnih prozora, što je premalo za
pouzdanu procjenu. Realan opseg je zato **oko jedan do pet posto**, sa
značajnom nesigurnošću dok se ne dobije duži normalni blok sa ploče.

Ako se ipak desi, zapiši `VERIFY_NORMAL_REJECT` i ponovi pokušaj — to je
svojstvo praga, ne kvar uređaja.

## Gdje su logovi

Sve se automatski piše u novi direktorij:

```text
results\physical_fan\run_<UTC>_<fan-id>_<session-id>\
```

Najvažniji fajlovi su:

- `serial.log` — vremenski označena UART telemetrija;
- `events.csv` — komande, uslovi i START/END potvrde operatera;
- `detections.csv` — score, prag i alarm po prozoru;
- `firmware_events.csv` — strukturirani firmware događaji;
- `window_features.npz` i `window_features.manifest.json` — 96 PSD i pet
  podsegmenata sa SHA-256 provjerom;
- `provenance.json` i `SUMMARY.md` — zaključeni metapodaci i sažetak;
- `guided25_report.json` — mjerodavni završni `PASS` ili `FAIL`.

Za živo praćenje u drugom PowerShell prozoru:

```powershell
.\POKRENI-GUIDED25.cmd logs
```

Ili ručno:

```powershell
$run = Get-ChildItem .\results\physical_fan -Directory -Filter 'run_*' |
  Sort-Object LastWriteTimeUtc | Select-Object -Last 1
Get-Content -LiteralPath (Join-Path $run.FullName 'serial.log') -Wait -Tail 40
```

`Ctrl+C` u prozoru koji samo prati log zatvara samo taj prikaz. Nemoj pritiskati
`Ctrl+C` u glavnom prozoru koji je pokrenuo pravi test.

## Završna provjera

Po završetku:

```powershell
$run = Get-ChildItem .\results\physical_fan -Directory -Filter 'run_*' |
  Sort-Object LastWriteTimeUtc | Select-Object -Last 1
Get-Content -Raw (Join-Path $run.FullName 'guided25_report.json')
Get-FileHash -Algorithm SHA256 `
  -LiteralPath (Join-Path $run.FullName 'window_features.npz')
```

Rezultat je važeći samo ako `guided25_report.json` postoji i kaže `PASS`.
Nedostajući report ili dokaz je `FAIL`, ne pretpostavljeni prolaz. Sačuvaj cijeli
run direktorij; ne prepisuj niti ručno uređuj artefakte.

Detaljan redoslijed fizičkih faza i kriterijumi su u
`docs/GUIDED25-TEST-VENTILATORA.md`.
