# Kanonska evaluacija modela

Status: usvojeni razvojni benchmark sa zaštitom od curenja unutar jednog runa

Implementacija: `pc/tools/evaluate_canonical.py`

Verzija protokola: `canonical-evaluation-v1.1.0`

Važno: ovo je **within-run leakage guarded developmental benchmark**, a ne
nezavisna finalna validacija. Poredi tačno tri statistička front-enda
(`mel1280`, `mel256`, `psd_shape`). Ne pokreće i ne predstavlja sve istorijske
metode, autoenkodere ili druge neuronske modele.

## Zašto postoji novi evaluator

Raniji `pc/tools/bench_final_tables.py` bio je koristan istraživački skript, ali
nije bio dovoljno ujednačen za konačno poređenje. Metode nisu imale potpuno
isti backend, pojam "seed" koristio se za ponovljene izbore kalibracionih
klipova, a izlaz nije sadržao trajni manifest stvarno korištenih podjela.

Novi evaluator zamjenjuje taj skript kao kanonski razvojni protokol za ova tri
front-enda. Stari skript se ne briše jer ostaje dio istorije istraživanja i trag
kako su raniji brojevi nastali.

## Nepromjenjiva granica podataka

Za svaku mašinu podaci imaju tačno tri uloge:

1. `source/train/normal` uči globalnu standardizaciju i Ledoit-Wolf precision
   matricu. Nijedan target klip i nijedna anomalija ne ulaze u globalni fit.
2. Target normalni pool čine zajedno `target/train/normal` i
   `target/test/normal`. Za svaku unaprijed definisanu podjelu pool se dijeli na
   lokalnu kalibraciju i odvojene held-out normalne klipove.
3. `target/test/anomaly` učitava se tek u završnoj `evaluate` fazi, nakon što su
   lista metoda, split manifest, preprocessing, globalni modeli i lokalni
   protokol već fiksirani. Anomalije ne smiju uticati na fit, centar, izbor
   splita ili izbor metode.

Skript fail-fast prekida rad ako pronađe anomaliju u fit/kalibracionoj kohorti,
preklapanje kalibracije i held-out skupa, nepotpun split, promijenjen cache ili
različite `calibration_split_id` vrijednosti među metodama. Normalne i anomalne
kohorte imaju fizički odvojene NPZ cacheve, tako da priprema modela ne otvara
legacy cache koji u istom nizu sadrži i anomaly feature-e.

## Provenance dataseta i cache-a

Manifest ne sadrži samo split indekse. Za svaki korišteni klip iz sve tri
kohorte (`source_fit`, `target_normal_pool`, `target_anomaly_evaluate`) zapisuje:

- relativnu putanju;
- indeks unutar kohorte;
- dataset split, domen i labelu;
- veličinu fajla;
- SHA-256 sadržaja WAV fajla.

Glavni `content_sha256` manifesta pokriva sve tri kompletne kohorte i sve
kalibracione podjele. Zbog toga izmjena bilo kojeg korištenog WAV-a mijenja
identitet evaluacije.

Svaki canonical NPZ cache u sebi nosi provenance metadata koja se provjerava
prije čitanja feature-a:

- verziju protokola;
- hash ulazne kohorte;
- kompletne specifikacije metoda i njihov hash;
- SHA-256 evaluatora, `pc/asd/features.py` i relevantnog periodicity koda;
- verzije Pythona, NumPyja, SciPyja, scikit-learna, SoundFilea i librose.

Ako se bilo šta od navedenog promijeni, cache se ne koristi i run se prekida sa
porukom da je stale. Cache se ne regeneriše tiho, jer bi to sakrilo promjenu
računskog okruženja.

## Fiksne metode i zajednički backend

Lista metoda je konstanta u kodu i ne bira se na osnovu rezultata ovog runa:

- `mel1280`: srednja vrijednost i standardna devijacija 640-dimenzionih P=5
  naslaganih log-mel vektora;
- `mel256`: srednja vrijednost i standardna devijacija rekonstruisanih
  128-dimenzionih log-mel frejmova;
- `psd_shape`: Welch 8192, hop 4096, 96 logaritamskih traka 10–4000 Hz i
  uklonjen prosječni nivo spektra.

Sve tri metode zatim koriste isti statistički backend:

1. per-dimenziona standardizacija naučena samo na source/train/normal;
2. Ledoit-Wolf kovarijansa/precision naučena na istim standardizovanim source
   feature-ima;
3. aritmetička sredina kalibracionih target normalnih feature-a kao lokalni
   centar;
4. kvadratna Mahalanobis udaljenost kao anomaly score.

Zato ova tabela poredi prvenstveno kvalitet front-enda, a ne tri različita
backenda.

Za računsku efikasnost evaluator jednom po metodi računa `X @ precision` i
`x^T precision x` za normalne i anomalne feature-e. Svaka nova kalibraciona
podjela zatim mijenja samo lokalni centar, bez ponavljanja punog
`O(broj_klipova × dimenzija²)` prolaza svih score-ova.

Ove statističke metode nemaju stohastički trening. Polje `training_seed` je u
JSON-u eksplicitno `null`, a u ravnom CSV-u `not_applicable`. Broj podjele nije
training seed i zove se isključivo `calibration_split_id`.

## Splitovi, metrike i nesigurnost

Podrazumijevani protokol koristi:

- `k=20` target normalnih klipova za lokalnu kalibraciju;
- 100 unaprijed generisanih podjela;
- fiksni `split_random_state=20260809`;
- AUC i standardizovani pAUC pri `FPR <= 0.1` za svaku podjelu;
- srednju vrijednost i `calibration_split_std` preko 100 podjela;
- deterministički bootstrap sa 2.000 resamplovanja i
  `bootstrap_random_state=20260810` za 95% interval srednje vrijednosti preko
  podjela.

Bootstrap interval opisuje nesigurnost srednje vrijednosti preko definisanih
kalibracionih podjela. On nije interval preko nezavisnih treninga, novih
ventilatora ili novih snimljenih sesija i ne smije se tako predstavljati.

## Git i run provenance

Rezultat ne navodi samo trenutni `HEAD`. Zapisuje i dirty flag, potpuni
`git status --porcelain`, hash relevantnog tracked diffa, SHA-256 relevantnih
source fajlova i informaciju da li je svaki source fajl praćen Gitom. Time
necommitovan evaluator ne može biti pogrešno predstavljen kao kod iz samog
HEAD commita.

`run_id` se formira tek nakon provjere kompletnog dataseta i okruženja. Obuhvata
verziju protokola, hash specifikacija metoda, relevantnog source koda,
dependency verzija i kompletnog dataset/split manifesta, zatim skup mašina,
`k`, broj podjela, split random state, broj bootstrap resamplovanja i bootstrap
random state. Dva različita eksperimenta zato ne dijele isti izlazni folder.

Svi izlazi prvo se pišu u skriveni privremeni folder unutar izabranog output
foldera. Tek kada su svi uspješno zapisani, folder se jednim rename potezom
objavljuje pod `run_id`. Postojeći run se nikada ne prepisuje.

## Reproducibilni izlazi

Evaluator zapisuje u zaseban
`results/canonical_evaluation/<run_id>/` folder:

- `dataset_and_split_manifest.json`: sve ulazne kohorte, sadržajni hashovi i
  tačni kalibracioni/held-out splitovi;
- `aggregate_results.json`: konfiguracija, dependency/Git/source provenance,
  audit pristupa anomalijama, rezultati svake podjele i agregati;
- `aggregate_summary.csv`: jedna agregatna vrsta po mašini i front-endu;
- `per_split_metrics.csv`: sirovi AUC i pAUC za svaku mašinu, front-end i
  `calibration_split_id`;
- `SUMMARY.md`: kratka čitljiva tabela sa jasnim upozorenjem o razvojnom
  karakteru rezultata, eksplicitnim `standardized pAUC@FPR<=0.1`, bootstrap
  95% intervalima, brojem bootstrap resamplovanja i bootstrap random stateom.

Ako treba osvježiti samo čitljivi sažetak iz već izračunatog i validnog
`aggregate_results.json`, bez ponovnog feature benchmarka:

```powershell
..\.venv\Scripts\python.exe tools\evaluate_canonical.py `
  --regenerate-summary-from <run-folder>\aggregate_results.json
```

Ova komanda ne mijenja JSON/CSV numeričke rezultate i atomarno zamjenjuje samo
`SUMMARY.md` u istom run folderu.

`--output-dir` može biti relativna ili apsolutna putanja, uključujući folder
izvan repozitorija. U rezultatu se zato koriste imena fajlova unutar run
foldera, bez pretpostavke da se output nalazi ispod project root-a.

Pokretanje iz foldera `pc`:

```powershell
..\.venv\Scripts\python.exe tools\evaluate_canonical.py
```

Testovi bez punog benchmarka:

```powershell
..\.venv\Scripts\python.exe -m pytest tests\test_canonical_evaluation.py -q
```

## Ograničenje koje evaluator ne može izbrisati

Metode su sada fiksirane prije kanonskog runa, ali su PSD i ostale varijante
istorijski pronađene kroz eksperimente tokom kojih su gledani target anomaly
rezultati istog DCASE skupa. Ponovno pokretanje po čistom protokolu sprečava
novo curenje i čini poređenje ujednačenim, ali ne briše istorijski
model-selection bias.

Za stvarno nezavisnu potvrdu potrebni su novi fizički ventilatori i nove sesije
koje nisu učestvovale u razvoju metode. Zato se poslije zamrzavanja ove tabele
prelazi na fizički eksperiment: lokalna kalibracija zdravog ventilatora, duži
normalni rad za false-alarm/h, zatim bezbjedni i ponovljivi kvarni uslovi uz
bilježenje WAV-a, score-a, praga i vremena alarma.
