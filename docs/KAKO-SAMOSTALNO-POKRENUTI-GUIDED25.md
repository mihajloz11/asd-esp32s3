# Kako samostalno pokrenuti GUIDED25 test i sve logove

Ovo je rezervno operatersko uputstvo za slučaj da glavni launcher nije dostupan. Jedan
launcher pokreće host snimanje, obaveznu research telemetriju, dashboard i sve
artefakte. Nijedna komanda ispod sama ne pokreće ventilator; operater potvrđuje
postavku, a učenje počinje tek poslije klika u dashboardu.

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
- Za svaku prikazanu aktivnu fazu klikni **Potvrdi START faze** kada radnju
  počneš i **Potvrdi END faze** neposredno prije kraja odbrojavanja.
- Ako nešto nije urađeno tačno po uputstvu, klikni **Prekini i sačuvaj**.

Planirani najgori tok traje `22:50`; hard stop je `25:00`. Izmjereno trajanje
jednog prozora je `9,981 s`, pa sa WAIT fazom najgori tok stvarno iznosi
`23:03` — rezerva do hard stopa je oko dva minuta. Zato poslije poruke da je
kalibracija gotova odmah klikni **2. Kreni sa mjerenjem** i ne oklijevaj sa
potvrdama faza. Ne ponavljaj pokušaj zbog lošeg rezultata, nego samo zbog
zapisane tehničke/proceduralne greške. Ukupno su dozvoljena najviše tri
pokušaja.

Jedan ishod nije kvar ni greška operatera. `threshold_enter` je `p99` od 44
DERIVE prozora, što za taj broj prozora ispada tačno **najveći** izmjereni
skor, a `VERIFY` zatim ne dozvoljava nijedan prozor iznad njega. Ako su DERIVE
i VERIFY prozori uzorci iste normalne distribucije, kalibracija padne na
`VERIFY_NORMAL_REJECT` kad god globalni maksimum svih 66 prozora padne u
VERIFY dio — dakle u oko `22/66 = 33%` pokušaja. To je svojstvo praga, ne
kvar; zapiši ga i ponovi pokušaj.

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
