# Akustička detekcija anomalija na ESP32-S3

Projekat master rada: detektor promjene zvuka ventilatora sa jednim INMP441
mikrofonom. ESP32-S3 računa 96 spektralnih obilježja i kvadriranu
Mahalanobisovu udaljenost. Globalni model uči se na normalnim DCASE snimcima;
lokalni centar i pragovi uče se na uređaju iz normalnog rada konkretne postavke.

<!-- privatno:start -->
> Privatni repo. Lični materijal (uputstva, učenje, planovi, dnevnici,
> elektronika) je u [privatno/](privatno/README.md), rukopisi u [radovi/](radovi/).
> Kopiju za predaju pravi `python pc/tools/napravi_predaju.py`; ovaj blok,
> `privatno/` i `radovi/` u nju ne ulaze.
<!-- privatno:end -->

## Rezultati

| Provjera | Rezultat i obim |
|---|---|
| Razvojni benchmark, fan | AUC 0,8556 ± 0,0240, deset kalibracionih prozora, 20 podjela |
| Odvojena PC referenca | AUC 0,8666 ± 0,0270, dvadeset prozora, 100 podjela; drugi protokol |
| Fizička proba papirićem | Prihvaćena kalibracija; GUIDED25 **FAIL**, detektovan 1/3 blokova i alarm prenesen u oporavak |
| Fizička proba tonom od 1 kHz | Alarm i `ANOMALY_SUSTAINED`; kašnjenje od početka tona i završni oporavak nisu izmjereni |
| Obrada na uređaju | Oko 716 ms za obilježje i ocjenu po prozoru od 10 s; nije vrijeme cijelog toka |
| Naknadna analiza obilježja | Papirić i ton detektovani po obliku spektra; ton je svirao još 36 prozora poslije oznake kraja; [detalji](results/trial_features/2026-09-25/README.md) |
| Automatske provjere | 478 testova prolazi na računaru sa DCASE podacima; provjera protokola prolazi |

Obje završne probe imaju `valid_physical_result`: to označava upotrebljiv
zapis mjerenja, ne prolaz eksperimenta. U njima nema prijavljenih gubitaka
uzoraka. Jedan ventilator, jedna prostorija i vještačke pobude ne potvrđuju
dijagnozu kvara niti dugoročnu pouzdanost. Razvojni rezultati nisu nezavisni
test konačnog izbora modela.

Brojke i izvori: [završne fizičke probe](docs/probe/rezultat-finalna-validacija-2026-08-27.md).
Mapa dokumentacije: [docs/README.md](docs/README.md).

## Struktura

| Putanja | Sadržaj |
|---|---|
| [firmware/esp32s3_asd](firmware/esp32s3_asd/) | ESP-IDF firmware; konačni režim `ASD_PSD_LIVE` |
| [pc/asd](pc/asd/) | obrada, evaluacija, protokol i host alati |
| [pc/tools](pc/tools/README.md) | pokretanje proba, analiza i izvoznici modela; aktuelni i istorijski alati |
| [pc/tests](pc/tests/) | host provjere i poređenje sa C implementacijom |
| [pc/config](pc/config/) | zaključane politike izvedene iz normalnih podataka |
| [results](results/README.md) | rezultati, sirovi zapisi i mapa dokaza |
| [models](models/) | metapodaci modela; veliki modeli i keševi nisu u Gitu |
| [docs](docs/README.md) | odluke, protokoli, rezultati i razvojna istorija |

## PC provjere

Python 3.11 i GCC moraju biti dostupni. Za host testove nije potreban TensorFlow.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r pc/requirements-ci.txt
.\.venv\Scripts\python.exe -m pytest pc/tests -q
.\.venv\Scripts\python.exe pc/tools/check_schema_consistency.py
```

Testovi koji traže DCASE snimke preskaču se u svježem klonu. Za trening i
istorijski autoenkoder koriste se pune zavisnosti iz
[requirements.txt](requirements.txt). DCASE podaci preuzimaju se zasebno iz
[zapisa skupa](https://zenodo.org/records/19336329) u
`data/dcase2026_dev/<masina>/{train,test}` uz uslove licence tog skupa.

## Firmware

Radna verzija koristi ESP-IDF 5.5.5, `ASD_PSD_LIVE=1` i
`ASD_RESEARCH_TELEMETRY=1`. Ista slika od 354 784 B korišćena je u obje
završne probe:

```text
9ac2caca2c5010747547d4bb942aae96f700221588a4a6863b5c01948d967813
```

Build sa drugim verzijama komponenti ne mora dati identičan binarni fajl.
U ESP-IDF PowerShell okruženju:

```powershell
Set-Location firmware/esp32s3_asd
$env:ASD_PSD_LIVE = '1'
$env:ASD_RESEARCH_TELEMETRY = '1'
idf.py -B build -DIDF_TARGET=esp32s3 reconfigure build
```

Poslije svake promjene env varijabli obavezan je `reconfigure`. Ostali režimi
(`ASD_MIC_TEST`, `ASD_INA_TEST`, `ASD_PSD_VERIFY` i TFLM) služe pojedinačnim
provjerama ili ranijim eksperimentima. Pinovi su u
[pins.h](firmware/esp32s3_asd/main/pins.h).
