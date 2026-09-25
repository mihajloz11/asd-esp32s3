# Eksperimentalni FW sa nepraznim trakama

> **Dopuna 25.09.2026. — implementacija je sada u ovom repou**, na grani
> `claude/psd-nonempty-bands`, iza zastavice `ASD_PSD_NONEMPTY_BANDS`.
> Codex grane i `package_psd_nonempty.py` iz teksta ispod nisu potrebni.
>
> - Zaglavlje modela pravi `pc/tools/export_psd_nonempty.py` iz
>   `nonempty_log96_model.npz` (hash iz `frozen.json`); otisak `9018365b…`,
>   isti kao u paketu od 07.09.
> - ESP-IDF v5.5.5, `ASD_PSD_LIVE` + `ASD_RESEARCH_TELEMETRY` + zastavica:
>   build prolazi, aplikacija 354 480 B. Tri niza modela u ELF-u su
>   bit-identična zamrznutom modelu; bin sadrži
>   `EXPERIMENTAL frontend=nonempty_log96` i novi otisak, a ne stari.
>   (Komponente u toj provjeri su sa GitHub-a, pa veličina ne mora biti ista
>   kao u lokalnom buildu.)
> - Bez zastavice ista grana daje stari front-end i stari model; jedina razlika
>   prema `master`-u je zasićenje audio uzoraka (`audio_pcm.h`, +48 B).
> - Host upisuje `psd_nonempty_bands_build_flag_confirmed` u `provenance.json`.
> - Host testovi: `pc/tests/test_psd_nonempty_c.py`, `pc/tests/test_audio_pcm_c.py`.
>
> Build za probu, u ESP-IDF PowerShell okruženju:
>
> ```powershell
> Set-Location firmware/esp32s3_asd
> $env:ASD_PSD_LIVE = '1'; $env:ASD_RESEARCH_TELEMETRY = '1'; $env:ASD_PSD_NONEMPTY_BANDS = '1'
> idf.py -B build reconfigure build flash monitor
> ```
>
> Za povratak na testirani firmware: ukloniti `ASD_PSD_NONEMPTY_BANDS` iz
> okruženja i ponovo `idf.py reconfigure build` (P2), ili flešovati sačuvani
> rollback paket. Fizička proba još nije urađena.

Build je prošao. Aplikacija ima **355 104 B**, a SHA-256 je
`c78770f2552e6c8fc6e53e2d4fd539020e5765d16504706499a728ca90beeb8c`.
Esptool potvrđuje checksum i validacioni hash slike. Provjerene su sve tri
zastavice builda, tekstualna oznaka eksperimenta i prisustvo tačnih float32
parametara novog modela u samom binu. Uređaj nije flešovan.

Grana `codex/psd-nonempty-bands` sadrži novi frontend i zasebno generisano
zaglavlje `psd_model_nonempty_data.h`. Standardni build i dalje bira staru
mapu i `psd_model_data.h`. Eksperiment se uključuje samo sa
`ASD_PSD_NONEMPTY_BANDS=1`, uz `ASD_PSD_LIVE`.

Nisu mijenjani prihvat zvuka, pragovi kvaliteta, GUIDED25 raspored, HOLD,
vremensko pravilo, NVS ni komande hosta. Centar i numerički pragovi biće
drugačiji jer uređaj uči novi profil nad novim obilježjima.

## Build i sačuvani paketi

U ESP-IDF PowerShell okruženju, iz firmware direktorijuma eksperimentalne grane:

```powershell
$env:ASD_PSD_LIVE = '1'
$env:ASD_RESEARCH_TELEMETRY = '1'
$env:ASD_PSD_NONEMPTY_BANDS = '1'
idf.py -B build reconfigure build
```

Prije ponovne gradnje modela, iz korijena grane:

```powershell
python pc/tools/export_psd_nonempty.py
```

Izvoznik uzima samo model zamrznut u eksperimentu i provjerava njegov hash,
dimenzije, konačnost i pozitivnu definitnost float32 matrice preciznosti.
Novi header je posebno provjeren kroz C kompajler: sve ugrađene float32
vrijednosti jednake su vrijednostima zamrznutog modela nakon konverzije.

Lokalni paket je u `dist/psd-nonempty-2026-09-07/` eksperimentalnog foldera:

- `candidate/`: eksperimentalna aplikacija, bootloader i particiona tabela;
- `rollback/`: kopija stvarno testirane stare aplikacije i njenih pratećih fajlova;
- `manifest.json`: adrese, veličine, hash-evi, provjerene zastavice i otisak modela.

Isti manifest je sačuvan kao [firmware_package.json](firmware_package.json).
Paket je napravljen alatom `pc/tools/package_psd_nonempty.py`; on ne otvara COM
port niti flešuje uređaj. **Taj alat nije u `master`-u** — stoji na granama
`codex/psd-nonempty-bands` i `codex/psd-covariance-study`, pa se paket u ovom
checkoutu ne može ponovo napraviti bez prelaska na jednu od njih. Stari app SHA-256 mora biti
`9ac2caca2c5010747547d4bb942aae96f700221588a4a6863b5c01948d967813`.

## Naredna fizička proba

U ovoj sesiji uređaj nije flešovan. Prilikom buduće probe:

1. Provjeriti izabrani COM port i hash paketa prije flešovanja.
2. Sačuvati početni boot zapis. Novi build ispisuje
   `EXPERIMENTAL frontend=nonempty_log96_experimental` i otisak modela
   `9018365b6ceccc6b2a285b7a3b7ccf703425b3ac528e1e1feddf2d03ba3c12b1`.
3. Ponovo naučiti profil samo na normalnom radu. Ne unositi stare pragove
   niti prenositi stari centar. Prvo pratiti CAL, DERIVE, VERIFY i normalni nadzor.
4. Host za mjerenje pokrenuti iz **eksperimentalnog radnog foldera**, njegovim
   `pc/tools/start_fan_run.py`, uz postojeći Python interpreter. Host čita
   `firmware/esp32s3_asd/build/esp32s3_asd.bin` svog repoa radi porijekla mjerenja.
   Pokretanje iz starog foldera pripisalo bi snimku hash starog lokalnog bina.
5. Ako se bude ponavljala proba, zadržati istu postavku i unaprijed definisan
   protokol. Potrebno je zabilježiti stvarni početak/kraj pobude i ostaviti
   dovoljno normalnog rada za izlaz iz alarma. Ne mijenjati pragove tokom probe.

Novi boot, kalibracija, fizička detekcija, oporavak i vrijeme računanja još
nisu izmjereni na ploči. Prolaz računarskih provjera i builda to ne zamjenjuje.
Za povratak koristiti sačuvani `rollback` paket, bez ponovne gradnje starog FW-a.
