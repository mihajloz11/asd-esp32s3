# Analiza stanja projekta i sljedeći koraci — 09.08.2026.

> **Vrsta dokumenta:** detaljan, datirani audit/snimak stanja. Prvobitni audit
> zaključen je na commitu `5172e37`; stanje Gita je naknadno osvježeno poslije
> revizijskog commita `7cd08ee`. Za **živi, aktuelni plan i redoslijed rada**
> koristi [PLAN.md](PLAN.md). [handoff.md](handoff.md) ostaje kratka predaja za
> nastavak rada, dok ovaj dokument čuva obrazloženja, istoriju i detaljne nalaze.

## 1. Svrha i granice ove analize

Ovaj dokument je trajni snimak stanja projekta `master new` na dan 09.08.2026. Nastao je pregledom Git istorije, izvornog koda, dokumentacije, rezultata, modela, skupa podataka, izgrađenog firmwarea i zapisanih hardverskih testova.

Najvažnije pravilo pri tumačenju rezultata je da se moraju odvojiti četiri nivoa dokaza:

1. **PC/digitalno razvojno poređenje** — DCASE WAV ulazi direktno u Python/C algoritam.
2. **ESP32-S3 numerička i operativna verifikacija** — potvrđuje da uređaj računa isto i dovoljno brzo.
3. **Test preko zvučnika i mikrofona** — DCASE snimak se reprodukuje kroz zvučnik, a INMP441 ga ponovo snima.
4. **Stvarni fizički ventilator** — uređaj sluša pravi ventilator u više sesija i u kontrolisanim normalnim i nenormalnim uslovima.

Prva tri nivoa su djelimično ili potpuno testirana. Četvrti još nije izveden. Zato se ne smije tvrditi da je pouzdana detekcija stvarnog fizičkog kvara već dokazana.

## 2. Glavni zaključak

Projekat više nije samo ideja ili PC prototip. Postoje:

- ASD tok obrade učen samo na normalnim zvukovima ventilatora;
- fizički motivisan PSD/Mahalanobis model;
- C implementacija numerički usklađena sa PC implementacijom;
- samostalna lokalna kalibracija i kontinuirana inferenca na ESP32-S3;
- opsežna evidencija uspješnih i neuspješnih modelskih pokušaja;
- hardverski prototip sa ispravnim INMP441 mikrofonom.

Najbolji potvrđeni digitalni rezultat za fan je približno **AUC 0,864 ± 0,025** pri `k=20`. Aktuelni firmware koristi `k=10`, odnosno 100 s lokalne kalibracije, za šta PC benchmark daje približno **AUC 0,853**.

Najveći preostali rizik više nije sama veličina ili brzina modela, nego:

- nepostojanje jedne zamrznute, kanonske i ponovljive evaluacije svih metoda;
- nepostojanje dovoljno dugog testa lažnih alarma;
- nepostojanje testa uz stvarni fizički ventilator i bezbjedno izazvane promjene;
- nepoznata robusnost na buku, položaj mikrofona i različite sesije;
- nedovršen INA226/E5 i fizička izrada uređaja;
- zastarjela i međusobno neusklađena dokumentacija.

## 3. Inventar projekta

U trenutku audita folder je imao približno 45 hiljada fajlova i oko 17 GB.

| Dio projekta | Približno stanje | Napomena |
|---|---:|---|
| `data/` | 8.414 fajlova, 10,4 GB | raspakovani DCASE podaci i ZIP arhive |
| `results/` | 174 fajla, 2,66 GB | većinom regenerabilni feature-keševi |
| `.venv/` | 32.095 fajlova, 2,20 GB | lokalno Python okruženje |
| `.git/` | oko 1,33 GB | veliki broj loose/unreachable objekata |
| `firmware/` | oko 276 MB | izvorni kod, build i managed components |
| `models/` | 226 fajlova, oko 102 MB | Keras, TFLite, NPZ, JSON i generisani headeri |
| `photos/` | 4 fotografije, oko 5,9 MB | razvojni hardverski prototip |
| `pc/` | 53 Python fajla | trening, evaluacija, konverzija i testovi |

Većina velikih lokalnih podataka, buildova i keševa je ignorisana u Gitu. Git prati projektni kod, dokumentaciju i odabrane rezultate/model metadata fajlove.

## 4. Dataset

Ponovnom provjerom pronađeno je **8.400 WAV fajlova**:

- 7 tipova mašina × 1.200 WAV fajlova;
- po mašini 990 source normalnih trening-klipova;
- po mašini 10 target normalnih trening-klipova;
- po 50 source/target normalnih i anomalnih test-klipova;
- svi fajlovi su stereo, 16 kHz, 16-bitni i traju 10, 11 ili 12 s;
- trenutni glavni tok obrade koristi prvi kanal.

Za kanonsku evaluaciju mora se eksplicitno zapisati koji target normalni fajlovi služe za lokalnu kalibraciju, a koji ostaju kao negativni primjeri evaluacije. Važno ograničenje: postojeći DCASE target rezultati već su korišteni tokom razvoja i izbora PSD metode. Zato je ovo **razvojno poređenje sa pristrasnošću izbora modela**, a ne nezavisan završni dokaz. Novi skript može zamrznuti i učiniti protokol ponovljivim, ali ne može retroaktivno ukloniti istorijski uticaj target rezultata na smjer istraživanja. Nezavisan završni dokaz mora doći iz unaprijed zaključanog fizičkog eksperimenta ili novog skupa podataka.

## 5. Hronologija rada

Originalni snimak na `5172e37` imao je **51 dohvatljiv commit** od 17.07. do 09.08.2026. Trenutno stanje poslije `7cd08ee` ima 52. Raniji broj 53 vjerovatno je uključio resetovane/unreachable pokušaje; u reflogu postoji, između ostalog, resetovan commit `216c0ea` koji je potom ponovljen kao `b6b2ced`.

### 17–20. jul: PC tok obrade i prva verifikacija na uređaju

- postavljen log-mel front-end, autoenkoder i ESP-IDF kostur;
- napravljene varijante `baseline`, `tiny64`, `tiny32`, `tiny16` i `tiny32b4`;
- testirani Keras fp32, TFLite fp32 i TFLite int8 modeli;
- uvedeni MSE i Mahalanobisova ocjena anomalije;
- odrađeni eksperimenti na svih sedam mašina;
- potvrđena PC↔uređaj jednakost za tadašnji neuronski model;
- izmjerena ESP32 naspram ESP32-S3 latencija i esp-nn on/off razlika;
- završena dodatna učenja fan modela sa sjemenima 1–4.

### 3–6. avgust: hardver i živi audio lanac

- nabavljen i pregledan hardver;
- napravljen INMP441 bring-up i potvrđeno I2S skaliranje;
- implementiran INA226 drajver i dijagnostika;
- INA226 kvar/blokada lokalizovana na sam modul ili njegovo ožičenje;
- potvrđena PC↔uređaj usklađenost na živom mikrofonu;
- analiziran drift kalibracije.

### 8. avgust: živi demo

- uvedeni kontinuirani monitoring i lokalni dashboard;
- testirana lokalna kalibracija i alarmna logika;
- DCASE fan zvuk puštan je preko zvučnika i sniman INMP441 mikrofonom.

Naziv commita „Demo sa pravim ventilatorom“ ne smije se tumačiti kao dokaz testa fizičkog ventilatora: dostupna evidencija pokazuje reprodukciju fan snimaka preko zvučnika.

### 9. avgust: istraživanje modela i prenos PSD-a na uređaj

- sprovedeno više rundi alternativnih obilježja i metoda ocjenjivanja;
- postignut PSD rezultat oko 0,864 na fan target domenu;
- generisani model artefakti učeni samo na normalnim podacima i C header;
- PSD implementacija spojena u ESP32-S3 firmware;
- potvrđeni latencija, memorija, `dropped=0` i PC↔C/uređaj slaganje;
- testirana osjetljivost na sintetičke kvarove;
- poređenjem među mašinama potvrđeno da je PSD dobitak specifičan za ventilator;
- dodat je plan za robusnost na buku okoline.

**Originalni snimak:** lokalni HEAD je bio `5172e37`, sa 51 dohvatljivim commitom i granom `master` 4 commita ispred `origin/master`.

**Osvježeno poslije revizije:** trenutni HEAD je `7cd08ee` — „PLAN.md: objedinjen plan + usvojeni nalazi vanjske revizije“; istorija ima **52 dohvatljiva commita**, a lokalni `master` je **5 commita ispred** `origin/master`.

## 6. Šta je pokušano na modelima

### 6.1. Neuronski pristupi

Pokušani su:

- autoenkoderi različitih veličina;
- fp32 i int8 deployment;
- MSE i Mahalanobis score u latentnom/rekonstrukcionom prostoru;
- klasifikator brzina ventilatora;
- SSL i zajednički embedding;
- zajednički eksperimenti za sedam mašina.

U `models/` postoji oko 55 glavnih neuronskih treninga i po fp32/int8 TFLite varijanta za većinu njih. PTQ uglavnom nije značajno pokvario AUC. Glavni problem je što reprezentacija nije dobro odvajala suptilnu promjenu normalno/anomalno kod target ventilatora.

Približni zabilježeni ishodi:

| Pristup | Target AUC / zaključak |
|---|---|
| autoenkoder | oko 0,451 |
| zajednički/learned embedding | oko 0,495 |
| klasifikator brzine | oko 0,530 |
| SSL | približno slučajno |

### 6.2. Statistički i signalni pokušaji

Pokušani su log-mel statistički sažeci, puna i dijagonalna kovarijansa, Ledoit–Wolf, CMN, k-means režimi, top-k/GWRP, kNN, podsegmenti, delta obilježja, modulacioni spektar, sprega traka, autokorelacija, robusna kovarijansa, dvojni source i ansambli.

Približni nivoi rezultata iz dnevnika istraživanja:

- CMN oko 0,544;
- bogatiji mel sažetak prije regularizacije oko 0,578;
- k-means/režimi oko 0,582;
- dijagonalna kovarijansa oko 0,595;
- top-k oko 0,645;
- log-mel + puna/Ledoit–Wolf kovarijansa približno 0,67–0,72, zavisno od tačnog preprocessinga i protokola;
- median target centar u jednom protokolu oko 0,716;
- većina dodatnih vremenskih/modulacionih/ensemble pokušaja nije nadmašila PSD.

Ovi brojevi nisu svi direktno uporedivi. Različita predobrada, obilježja i kalibracione podjele znače da objedinjena razvojna tabela mora doći iz novog zajedničkog skripta. Detaljan istorijat pokušaja je u [put-do-modela.md](../../docs/put-do-modela.md).

## 7. Trenutni vodeći model: `psd_shape`

Finalni recept je:

- 16 kHz ulaz;
- Welch/FFT 8192 i hop 4096;
- približno 1,95 Hz frekvencijska rezolucija;
- 96 logaritamskih traka od 10 do 4.000 Hz;
- `log10` srednje snage po traci;
- oduzimanje skalarnog prosjeka klipa radi smanjenja zavisnosti od ukupne glasnoće;
- Ledoit–Wolf preciziona matrica naučena na 990 source normalnih fan klipova;
- lokalni centar novog fan-a iz normalne kalibracije;
- Mahalanobis udaljenost kao anomaly score.

Model meta podatak zapisuje SHA-256 `7bfbd3eeca1caca074562f6e01f6b374237dcea5c1d2cc097df079d68d9d15fe`. NPZ, JSON meta i generisani C header su u auditu imali isti checksum.

### Fan rezultat

- model meta / 50 podjela, `k=20`: **AUC 0,86438 ± 0,02473**;
- novija finalna tabela, 5 grupa × 20 ponavljanja: **AUC 0,86257 ± 0,02626**;
- pAUC pri FPR≤10%: **0,65671 ± 0,06153**.

Oznaka `seeds=5` u finalnoj tabeli ne predstavlja pet nezavisno treniranih PSD modela. Radi se o grupama kalibracionih podjela istog globalnog modela/dataseta. Standardna devijacija zato uglavnom mjeri osjetljivost na izbor target normalne kalibracije, a ne generalizaciju na pet novih fizičkih ventilatora.

### Rezultat poređenja među mašinama

| Mašina | `psd_shape` target AUC | Zaključak |
|---|---:|---|
| fan | 0,863 | jasan dobitak |
| valveEmu | 0,736 | dobar, ali slabiji od mel alternativa |
| sliderEmu | 0,588 | mali dobitak |
| gearboxEmu | 0,554 | slabije od mel |
| bearingEmu | 0,500 | slučajno |
| ToyCar | 0,450 | ispod slučajnog |
| ToyCarEmu | 0,384 | ispod slučajnog |

PSD pobjeđuje na samo 2 od 7 mašina i ima lošiju ukupnu harmonijsku sredinu od mel pristupa. Ispravna tvrdnja je: **PSD oblik je trenutno najbolji potvrđeni pristup za fan u ovom protokolu**, a ne univerzalno poboljšanje anomalijske detekcije mašina.

## 8. Šta je potvrđeno na ESP32-S3

Detaljni mjerni zapis je u [hardver-verifikacija.md](../../docs/hardver-verifikacija.md), odluka i kriteriji u [odluka-finalni-model.md](../../docs/odluka-finalni-model.md), a aktuelna implementacija u [`psd_live.c`](../../firmware/esp32s3_asd/main/psd_live.c).

Zapisani testovi potvrđuju:

- INMP441 radi;
- `>>14` I2S skaliranje je mjerenjem provjereno;
- PSD streaming i batch račun se slažu;
- maksimalna PC↔C razlika feature-a na DCASE WAV-u približno je `9,54e-07`;
- PC↔uređaj razlika na živom mikrofonu približno je `1,70e-06`;
- račun traje oko **704 ms na 10 s zvuka**, odnosno oko **14,2× rezerve**;
- `dropped=0`;
- DIRAM je približno 86% popunjen;
- uređaj može sam kalibrisati lokalni centar/prag i nastaviti bez računara.

Aktuelni `psd_live.c` koristi:

- 15 s warm-upa;
- `N_CAL=10`, odnosno 100 s kalibracije;
- prag `max(p90 leave-one-out, mean + 3·sd)`;
- alarm poslije **tri uzastopna** prozora iznad praga;
- zamrznut centar, bez tihe rekalibracije.

Odluka u kodu je jedan gornji prag (`score > threshold`). Mahalanobis score reaguje na odstupanje feature-a u različitim smjerovima, ali to nije isto što i eksplicitni dvostruki `low/high` prag.

Postojeći `ASD_PSD_LIVE` build artefakt ima 291.536 B. Factory particija je 4 MiB, pa veličina nije ograničavajući faktor. Build je napravljen uz ESP-IDF 5.5.5; build verzija pokazuje `on-device-verified-31-g9178ad6` jer su kasniji commitovi dokumentacioni.

Tokom ranijeg audita pločica je bila evidentirana kao COM3, dok je dokumentacija ranije navodila COM4. Pri završnoj provjeri za ovaj dokument nijedan serijski port nije bio enumerisan. Zato se COM broj ne smije tretirati kao stalna činjenica niti je u ovom koraku ponovljen flash/live test.

## 9. Test preko zvučnika nije test fizičkog ventilatora

U zabilježenim testovima DCASE fan snimak puštan je preko laptop-zvučnika, a INMP441 ga je hvatao kroz vazduh.

| Uslov | Zabilježeni ishod |
|---|---|
| digitalni PC benchmark | AUC oko 0,864 |
| zvučnik + mikrofon, kontrolisaniji prolazi | AUC 0,635–0,716 |
| zvučnik na 85% jačine | AUC 0,476; vjerovatno izobličenje |
| jedan neprekidan prolaz | AUC 0,258, ali permutacioni `p=0,112` |
| zaustavljena reprodukcija | visoki score / detektovano |
| sintetički kvar −12 dB | 3/3 alarmna prozora |
| sintetički kvar −18 dB | granično |
| sintetički kvar −24 dB i slabije | nepouzdano |
| procijenjena DCASE anomalija | približno −30 dB ekvivalent |

AUC 0,258 uz mali uzorak i `p=0,112` nije dokaz „obrnute detekcije“, nego neuspjeh da se dokaže razdvajanje u tom prolazu. Pošten zaključak je da implementacija hvata grube promjene, ali da su suptilne anomalije kroz zvučnik/mikrofon nepouzdane.

## 10. Hardversko stanje

| Komponenta | Stanje |
|---|---|
| ESP32-S3 N32R16V | radi; finalni razvojni target |
| INMP441 | radi i verifikovan je živi ulaz |
| INA226 | drajver postoji i gradi se, ali modul/bus ne radi |
| E5 energija | nije izmjerena zbog INA226 blokade |
| LED | kod postoji na GPIO2; fali otpornik 220–330 Ω |
| finalna pločica/kućište | nije završeno |

Fotografije pokazuju razvojni prototip sa jumper-žicama, ne završenu perfboard izvedbu. Za INA226 je dokumentovano da su SDA/SCL nisko-omski vezani na VCC; treba ponoviti multimetarsku provjeru i, ako je potrebno, zamijeniti modul.

## 11. Git, ponovljivost i tehničke provjere

- originalni snimak je bio 4 commita ispred, a osvježeno stanje na `7cd08ee` je **5 commita ispred** `origin/master`;
- radno stablo je prije dodavanja ovog dokumenta bilo čisto;
- trenutno postoji **788 rasutih (loose) Git objekata** i `.git` zauzima oko 1,24 GiB;
- `git fsck --no-reflogs --unreachable` nalazi stare unreachable objekte/commit pokušaje, ali dohvatljiva istorija je čitljiva;
- najveći dio velikih feature-keševa nije dio aktivne istorije;
- Python zavisnosti nisu potpuno zaključane, a ESP `dependencies.lock` je ignorisan;
- nema CI workflowa.

Ponovljene read-only provjere 09.08.2026:

- svih **53 Python fajla** prolazi `compile()` parsiranje;
- `pytest pc/tests -q`: **12 passed**;
- pronađeno je **8.400 WAV fajlova**;
- finalni PSD JSON/meta i aktuelni firmware parametri pročitani su direktno iz artefakata;
- duplikat u `results.csv` potvrđen je direktno iz CSV-a.

## 12. Nalazi revizije i sadašnje stanje

Commit `7cd08ee` već je usvojio dio nalaza. Oni se zato više ne vode kao aktuelni problemi.

| Nalaz revizije | Sadašnje stanje |
|---|---|
| `handoff.md` je tvrdio da je sve pushovano | **Ispravljeno**: sada traži provjeru `origin/master..HEAD`; grana je trenutno 5 commita ispred. |
| Dokumentacija je PSD prag nazivala dvostranim | **Ispravljeno**: [hardver-verifikacija.md](../../docs/hardver-verifikacija.md) sada jasno kaže da je prag jednostran. |
| Dokumentacija je navodila 2, a kod koristio 3 uzastopna prozora | **Ispravljeno** na 3. |
| Status finalnog modela je pisao da čeka hardversku potvrdu | **Ispravljeno** u [odluka-finalni-model.md](../../docs/odluka-finalni-model.md): implementacijski kriteriji su prošli; fizički fan ostaje otvoren. |
| `ae_mel` je bio pogrešan naziv u skriptu | **Ispravljeno** u [`bench_final_tables.py`](../../pc/tools/bench_final_tables.py) u `mel1280`. Stari [`final_tables_k20.json`](../../results/final_tables_k20.json) još nosi istorijski ključ `ae_mel` dok se tabela ne regeneriše. |
| `seeds=5` je zvučalo kao pet treninga | **Dokumentovano u skriptu** kao pet grupa kalibracionih podjela. Stari JSON i dalje ima polje `seeds`, pa ga treba tumačiti na taj način. |
| `results.csv` ima dupli `fan_tiny16_s1/mse/fp32` | **Otvoreno**: dva reda imaju različite rezultate; utvrditi porijeklo ili regenerisati. |
| README prvenstveno opisuje stari AE tok | **Otvoreno**. |
| Više mel brojki potiče iz različitih protokola | **Otvoreno**: riješiti kanonskom razvojnom evaluacijom. |
| Pet stvarnih neuralnih sjemena postoji uglavnom za fan MSE | **Ograničenje ostaje**; Mahalanobis i većina drugih mašina uglavnom su na jednom sjemenu učenja. |
| Poglavlja rada i dio dnevnika ostali su iz AE faze | **Otvoreno**. |
| Python/ESP zavisnosti nisu potpuno zaključane | **Otvoreno**. |
| Git skladište ima mnogo starih rasutih/nedohvatljivih objekata | **Otvoreno, nizak prioritet**; sada 788 rasutih objekata / oko 1,24 GiB. |
| Nema CI-a za 12 testova | **Otvoreno, nizak prioritet**. |
| Commit „pravi ventilator“ može biti pogrešno protumačen | Istorija ostaje, ali u radu se test mora nazvati reprodukcijom preko zvučnika i mikrofona. |

## 13. Prioritet 1 — zamrznuti kanonsku razvojnu evaluaciju

Prije novih modelskih eksperimenata treba napraviti jedan autoritativni skript i protokol za sve metode. Njegova uloga je ponovljiva međusobna usporedba već razvijanih metoda. Pošto su target rezultati već usmjeravali razvoj, ova tabela i dalje ostaje **development benchmark sa pristrasnošću izbora modela**, a ne nezavisan završni test.

### 13.1. Pravila podataka

1. **Source normalni klipovi** uče globalni feature/model/normalizaciju/kovarijansu.
2. **Target normalni klipovi** služe samo za lokalnu kalibraciju centra i praga.
3. Target normalni klipovi koji nisu izabrani za kalibraciju ostaju negativni primjeri evaluacije.
4. **Target anomalije** koriste se samo jednom, za konačno računanje metrika.
5. U novom zamrznutom pokretanju target anomalije koriste se samo za računanje završnih metrika tog pokretanja; skript ih ne koristi za naknadno podešavanje obilježja, `k`, praga ili težina. To ne briše činjenicu da su raniji target rezultati već uticali na izbor PSD pristupa.
6. Sve metode dobijaju identične liste kalibracionih fajlova za isti `calibration_split_id`.

### 13.2. Tri različita izvora slučajnosti

Obavezno razdvojiti i zapisati:

- `training_seed` — inicijalizacija/trening globalnog modela; za deterministički PSD može biti `null` ili fiksan;
- `calibration_split_id` i `calibration_seed` — izbor target normalnih kalibracionih klipova;
- `bootstrap_seed` — resampling finalnih score-ova samo radi intervala pouzdanosti.

Ove tri stvari ne smiju se zajednički nazivati samo „seed“.

### 13.3. Kanonske metode i metrike

Najmanje uporediti:

- neuralni AE reconstruction MSE kao istorijski baseline;
- kanonski log-mel summary + regularizovani Mahalanobis;
- `mel256_lw`;
- `psd_shape`.

Za svaku metodu izvještavati:

- target ROC AUC;
- pAUC pri FPR≤10%;
- 95% bootstrap interval pouzdanosti;
- `k`, broj kalibracionih podjela i broj nezavisnih training seedova;
- threshold protokol, iako AUC nije zavisan od jednog praga;
- kalibracionu veličinu izraženu i u klipovima i u sekundama;
- vrijeme feature-a/inference i memoriju za deployment kandidata.

### 13.4. Obavezni izlazi skripta

Skript treba deterministički proizvesti:

- manifest dataseta sa relativnim putanjama/hashom;
- manifest svih kalibracionih splitova;
- sirovu tabelu jednog reda po metodi/training seedu/splitu;
- agregatnu CSV i JSON tabelu;
- Markdown tabelu spremnu za rad;
- podatke za ROC/Pareto grafike;
- zapis verzija koda, zavisnosti i parametara.

Postojeći dupli CSV red treba ukloniti uz dokumentovanje koji je zapis ispravan ili potpunom regeneracijom rezultata. Stari fajlovi mogu ostati kao istorijski artefakti, ali samo jedan novi izlaz treba proglasiti kanonskim.

### 13.5. Kriterij završetka

Kanonska evaluacija je završena tek kada:

- isti command ponovo daje iste splitove i iste brojke;
- nema duplih ključeva;
- manifest jasno označava da je DCASE rezultat razvojni i zabranjuje novo podešavanje na target anomalijama unutar zamrznutog pokretanja;
- sjeme učenja, kalibraciona podjela i interval ponovnog uzorkovanja jasno su odvojeni;
- finalna tabela ima jedan jasan broj/protokol po metodi;
- postojeći testovi i novi testovi protokola prolaze.

## 14. Prioritet 2 — pravi fizički eksperiment

Tek poslije zamrzavanja protokola treba izvesti eksperiment sa stvarnim niskonaponskim ventilatorom.

### 14.1. Minimalni dizajn

- fiksirati ventilator, mikrofon, udaljenost, ugao i prostoriju;
- označiti fan ID, datum, sesiju, temperaturu i napon/brzinu;
- uraditi odvojene kalibracije od 100 s (`k=10`) i 200 s (`k=20`);
- ponoviti više hladnih startova i nezavisnih sesija;
- snimiti najmanje 30–60 min normalnog rada po reprezentativnom uslovu;
- testirati više udaljenosti i položaja mikrofona;
- paralelno čuvati sirovi WAV, serijski log, score, threshold, alarm i tačno vrijeme promjene.

### 14.2. Bezbjedni test-uslovi

- normalan stabilan rad;
- druga dozvoljena brzina ili napon u sigurnim granicama;
- promijenjen protok vazduha bez dodirivanja lopatica;
- promjena oslonca/nosača koja ne ugrožava uređaj;
- kontrolisano gašenje;
- dodatna buka u prostoriji.

Ne treba stvarati opasan mehanički kvar, dodirivati rotirajuće lopatice niti namjerno oštetiti uređaj. Simulisanu promjenu ne treba u radu nazivati stvarnim kvarom bez odgovarajuće stručne potvrde.

### 14.3. Metrike stvarnog eksperimenta

Pored AUC-a izvještavati:

- lažne alarme na sat;
- broj normalnih sati bez alarma;
- event-level sensitivity;
- vrijeme do detekcije;
- broj uzastopnih prozora do alarma;
- propuštene događaje;
- rezultate po sesiji, udaljenosti, fan ID-u i uslovu;
- `dropped`, RAM i latenciju tokom dugog rada.

Trenutno pravilo od tri prozora znači približno 30 s minimalnog kašnjenja za potpuno nepreklapajuće 10-sekundne odluke. Treba porediti „3 uzastopna“ sa `N od M` logikom i izmjeriti ponašanje na buci od 20–60 s.

Jedan ventilator može dokazati funkcionalnost prototipa, ali ne i generalizaciju na populaciju novih ventilatora. **Dva fizički različita ventilatora samo su apsolutni minimum iznad jednog i još daju slab dokaz.** Za ozbiljniju tvrdnju treba koristiti više raznovrsnih ventilatora i više nezavisnih sesija koji nisu korišteni za razvoj obilježja. Protokol i način izvještavanja moraju se zaključati prije gledanja njihovih ishoda.

## 15. Prioritet 3 — robusnost na buku

Plan robusnosti na buku prvo treba testirati na PC-u, sa zaključanim splitovima.

Redoslijed:

1. stationarity/noise gate i bilježenje koliko normalnih i anomalnih prozora odbacuje;
2. `N od M` alarmna logika;
3. poređenje kanala 0, kanala 1, prosjeka i stabilnih dvokanalnih odnosa;
4. tek nakon mjerljivog dobitka dual-mic firmware.

Svi DCASE fajlovi su stereo, a za fan je ranije izmjerena visoka korelacija kanala. Prosto `kanal0 - kanal1` može poništiti i signal ventilatora, pa prvo treba provjeriti fizičko značenje kanala. Trimovanje PSD traka uz punu Mahalanobis matricu nije samo uklanjanje pojedinačnih traka, jer postoje cross-termovi. Stationarity gate takođe može odbaciti početak stvarnog kvara. Dual-mic implementacija mora voditi računa da je DIRAM već oko 86%.

## 16. Prioritet 4 — završetak uređaja i rada

### Hardver

- multimetrom ponoviti INA226 provjeru ili zamijeniti modul;
- završiti E5 mjerenje energije;
- dodati LED otpornik 220–330 Ω;
- prenijeti prototip na perfboard i rasteretiti kablove;
- dokumentovati finalnu šemu i fotografije.

### Repozitorij i dokumentacija

- ažurirati README, handoff, odluku o modelu i poglavlja rada;
- svuda koristiti fan-specific formulaciju;
- dosljedno razlikovati PC, uređaj, zvučnik i fizički fan;
- zaključati verzije zavisnosti;
- dodati CI za testove;
- pushovati lokalne nepushovane commitove nakon provjere;
- tek uz sigurnosnu provjeru očistiti stari Git garbage i velike lokalne kopije.

## 17. Kanonske tvrdnje za dalji rad

Do novog dokaza bezbjedno je tvrditi:

- source normalni fan zvukovi uče globalni PSD oblik/precizionu matricu;
- novi fan se lokalno kalibriše samo normalnim zvukom;
- digitalni fan benchmark daje oko 0,864 AUC pri `k=20`;
- trenutni `k=10` firmware ima oko 0,853 PC benchmark i radi samostalno;
- PC↔C/uređaj numerika, real-time latencija i `dropped=0` su potvrđeni;
- zvučnik/mikrofon eksperiment daje znatno slabije i promjenljive rezultate;
- PSD nije univerzalni pobjednik na svih sedam mašina;
- detekcija stvarnog fizičkog ventilatora i stvarnog kvara još nije dokazana.

Ne treba tvrditi:

- da je 0,864 izmjereno na fizičkom ventilatoru;
- da pet „seedova“ znači pet novih ventilatora;
- da je test preko zvučnika terenska validacija;
- da je riješena robusnost na buku;
- da je E5 energija izmjerena;
- da je uređaj završen kao finalni proizvod.

## 18. Konačna procjena

Istraživačka vrijednost projekta je jaka: dokumentovan je neuspjeh opšteg autoenkoderskog pristupa, pronađen je fizički smislen PSD opis za ventilator, implementacija je prenesena na ESP32-S3 i pošteno je pokazano da isti feature ne pobjeđuje na svim mašinama.

Sljedeći najvažniji rezultat nije još jedan nekontrolisan model. To su, ovim redom:

1. jedna kanonska, deterministička razvojna evaluacija bez duplih rezultata, uz otvoreno priznatu pristrasnost izbora modela;
2. ponovljiv test uz stvarni fizički ventilator;
3. dugotrajno mjerenje lažnih alarma i vremena detekcije;
4. robusnost na buku potvrđena prvo na PC-u, pa na uređaju;
5. završen hardver, E5 i usklađena dokumentacija.

Tako projekat prelazi iz dobrog istraživačkog prototipa u rezultat koji se može jasno i odbranjivo predstaviti kao normal-only, first-shot, fan-specific edge ASD sistem.
