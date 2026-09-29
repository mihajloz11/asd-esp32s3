# Vodič za razgovor sa profesorom

**Verzija 6 · 29.09.2026.** Prati osam cjelina dokumenta
[PREZENTACIJA-PROFESORU.md](PREZENTACIJA-PROFESORU.md), istim redoslijedom.
Predviđeno je oko **20 minuta izlaganja**, pa pitanja.

U svakoj cjelini **„Šta kažem profesoru“** predstavlja glavnu priču.
Odvojeni dio **„Ako profesor postavi potpitanje“** služi za proširenje teme;
ne čitam ga tokom osnovnog izlaganja. Tabela **„Kod koji pokazujem“** navodi
tezu, tačan fajl, funkciju i linije koje gledam.

## Prije sastanka

Prezentaciju otvorim u Markdown Preview-u (`Ctrl+Shift+V`), a ovaj vodič
ostavim za sebe. Putanje su relativne prema korijenu repozitorijuma
`asd-esp32s3`. U tabelama kliknem naziv fajla, pa `Ctrl+G` i unesem liniju.
Brojevi linija provjereni su prema kodu komita `0b1f93b`; poslije izmjena
koda provjeravam ih ponovo. Raspon označava dio koji treba pokazati.

Pripremim model, implementaciju ocjene i CSV fizičke probe. Lokalni DCASE
WAV podaci nisu uključeni u ovaj Git klon, pa njihovo puštanje planiram samo
ako ih prethodno obezbijedim. Za demonstraciju uređaja kalibraciju završim
ranije: 76 analiziranih prozora traje oko 12,6 minuta samo za zvuk, a sa
pripremom i obradom duže; približno 13,6 minuta iz ranije evidencije nije
garantovano trajanje svake sesije.

## 1. Cilj i realizovani sistem — 2 minuta

![Od učenja na računaru do odluke uređaja](../../photos/sl_sistem.png)

### Šta kažem profesoru

„Napravio sam uređaj koji sluša ventilator, upozna njegov normalan zvuk i
zatim provjerava da li se zvuk održano promijenio. Koristim ESP32-S3 i jedan
digitalni mikrofon INMP441. Prikupljanje, obrada i konačna odluka rade lokalno.
Računar koristim za razvoj modela i analizu rezultata.“

„Na slici je lijevo priprema globalnog modela iz normalnih snimaka. Naučene
brojeve ugrađujem u firmware. Desno uređaj prikuplja zvuk i prilagođava centar
i pragove konkretnom ventilatoru. Alarm znači odstupanje od normale; još ne
određuje da li je uzrok kvar, drugi režim rada ili spoljašnji zvuk.“

**Šta pokazujem:** sliku sistema iznad, od PC pripreme do odluke.
Oznake `z`, `c` i `P` predstavljaju standardizovani opis zvuka, lokalni centar
i matricu preciznosti.

### Ako profesor postavi potpitanje

**Šta je ovdje autonomno?** Nakon operatorovog pokretanja i uspješne
kalibracije, uređaj sam obrađuje nove prozore i donosi odluku. Računar nije
potreban za računanje ocjene; tokom eksperimenata služi i za evidenciju.
Autonomno ne znači da sistem smije sam da proglasi novu promjenu normalom.

**Zašto jedan mikrofon?** To je obim realizovanog prototipa. Iz jedne
akustičke tačke dobijam koristan signal, ali ograničene informacije o uzroku.
Zato prijava održane promjene u kodu koristi `UNKNOWN_CHANGE`.

### Kod koji pokazujem

| Teza | Fajl, funkcija i linije | Šta gledam |
|---|---|---|
| Pokretanje finalnog toka | [firmware/esp32s3_asd/main/app_main.c](../../firmware/esp32s3_asd/main/app_main.c), `app_main()`, 137; PSD grana 167–176 | inicijalizacija I2S i poziv `psd_live_run()` |
| Lokalni rad uređaja | [firmware/esp32s3_asd/main/psd_live.c](../../firmware/esp32s3_asd/main/psd_live.c), `psd_live_run()`, 1286 | upravljanje radom i zahtjevom operatora |
| Alarm ne dokazuje uzrok | [firmware/esp32s3_asd/main/asd_events.c](../../firmware/esp32s3_asd/main/asd_events.c), `asd_decide()`, 320–326 | stanje anomalije uz događaj `UNKNOWN_CHANGE` |

## 2. Podaci i model — 3 minuta

### Šta kažem profesoru

„Globalnu statistiku učim iz 990 normalnih source snimaka ventilatora iz
DCASE 2026 skupa. Svaki snimak pretvaram u 96 brojeva koji opisuju oblik
spektra. Svaku komponentu standardizujem, a Ledoit–Wolf postupkom dobijam
stabilizovanu kovarijansu i njenu inverznu matricu.“

„Uređaj dobija tri tabele: sredine, standardne devijacije i matricu
preciznosti. Na novom ventilatoru ne uči ponovo cijelu matricu, već lokalni
centar i pragove. Zatim računa Mahalanobis ocjenu: koliko novi zvuk odstupa
od tog centra, uz uvažavanje povezanosti između obilježja.“

**Šta pokazujem:** početke tri niza u `psd_model_data.h`. Zajedno zauzimaju
37632 bajta: 36864 za matricu i 768 za normalizaciju. To nije ukupna memorija
firmware-a; lokalni centar zasebno ima 384 bajta, a postoje i radni baferi.

### Ako profesor postavi potpitanje

**Zašto Mahalanobis, a ne obična udaljenost?** Dvije spektralne trake mogu
prirodno da rastu zajedno. Obična udaljenost ne uzima tu vezu u obzir, dok
kovarijansa opisuje koje su zajedničke promjene očekivane. Ledoit–Wolf
stabilizuje procjenu kovarijanse, što je korisno kod povezanih obilježja.

**Šta tačno računa kod?** Za obilježje `x` prvo važi
`z[i] = (x[i] - mean[i]) / std[i]`, pa `delta = z - c`.
Ocjena je `score = deltaᵀ P delta`. Kod ne računa kvadratni korijen: koristi
kvadrat Mahalanobis udaljenosti. Veći broj znači veće odstupanje, a ne
vjerovatnoću kvara. Centar `c` je u standardizovanom prostoru.

**Da li su anomalije korišćene za učenje?** Izvoz ovih tabela koristi samo
normalne source snimke. Ipak, tokom razvoja gledani su rezultati evaluacije
modela. Zato ne tvrdim da je cijeli izbor modela urađen bez ikakvog uvida u
anomalne primjere, niti da je razvojni AUC nezavisna završna potvrda.

### Kod koji pokazujem

| Teza | Fajl, funkcija i linije | Šta gledam |
|---|---|---|
| Izbor 990 source snimaka | [pc/tools/gen_psd_model_header.py](../../pc/tools/gen_psd_model_header.py), `main()`, 49–64 | filter `domains == "source"`, provjera oblika, normalizacija i `LedoitWolf()` |
| Ugrađene tabele | [firmware/esp32s3_asd/main/psd_model_data.h](../../firmware/esp32s3_asd/main/psd_model_data.h), 18, 33 i 48 | `asd_psd_norm_mean`, `asd_psd_norm_std`, `asd_psd_precision` |
| Formula ocjene | [firmware/esp32s3_asd/main/psd_features_c.c](../../firmware/esp32s3_asd/main/psd_features_c.c), `asd_psd_score()`, 245–262 | standardizacija, oduzimanje centra, množenje matricom i skalarni proizvod |
| Spajanje modela i lokalnog centra | [firmware/esp32s3_asd/main/psd_live.c](../../firmware/esp32s3_asd/main/psd_live.c), `score_with_center()`, 501–504 | koje tabele ulaze u račun |

Porijeklo, dimenzije i memorija navedeni su i u
[models/fan_psd_shape_meta.json](../../models/fan_psd_shape_meta.json).
Njegov istorijski benchmark nije isti eksperiment kao 100 podjela iz cjeline 5.

## 3. Obrada zvuka na uređaju — 2 minuta

### Šta kažem profesoru

„Mikrofon šalje digitalni zvuk preko I2S interfejsa, sa 16000 uzoraka u
sekundi. Uzorke posmatram kroz segmente od 8192 vrijednosti, sa pomakom od
4096. Na segment primjenjujem Hann prozor, računam FFT i usrednjavam snagu
spektara, što je Welch postupak.“

„Iz spektra dobijam 96 traka između približno 10 Hz i 4 kHz. Računam
logaritam njihove snage i oduzimam srednju vrijednost tog opisa. Tako se
fokus pomjera ka obliku spektra. Rezultat je 96 brojeva za oko deset sekundi
zvuka; tek iz njih računam jednu ocjenu odstupanja.“

### Ako profesor postavi potpitanje

**Zašto Hann i preklapanje?** Segment presijeca signal na svojim krajevima.
Hann smanjuje uticaj tih ivica na spektar. Preklapanje omogućava da
susjedni segmenti dijele dio uzoraka; njihov prosjek daje stabilniji opis.
FFT segment traje 0,512 s, a pomak 0,256 s. To nije isto što i prozor odluke.

**Koliko je dug prozor odluke?** Implementacija koristi 39 pomaka:
`39 × 4096 / 16000 = 9,984 s`, odnosno 38 preklopljenih FFT segmenata.
Streaming obrada obrađuje segment kada pristignu uzorci i akumulira spektar;
ne mora da čuva cijeli desetosekundni snimak.

**Da li je opis neosjetljiv na jačinu?** Oduzimanje sredine logaritamskog
opisa uklanja zajednički pomak nivoa. To ne znači potpunu neosjetljivost na
udaljenost: drugačiji položaj, šum i refleksije mogu promijeniti oblik spektra.

### Kod koji pokazujem

| Teza | Fajl, funkcija i linije | Šta gledam |
|---|---|---|
| 16 kHz i prijem uzoraka | [firmware/esp32s3_asd/main/audio_i2s.h](../../firmware/esp32s3_asd/main/audio_i2s.h), 12; [audio_i2s.c](../../firmware/esp32s3_asd/main/audio_i2s.c), `capture_task()`, 43 | `AUDIO_SR` i zadatak za prikupljanje |
| Parametri obrade | [firmware/esp32s3_asd/main/psd_features_c.h](../../firmware/esp32s3_asd/main/psd_features_c.h), 7–9; [psd_live.c](../../firmware/esp32s3_asd/main/psd_live.c), 42–44 | FFT, pomak, broj traka i `HOPS_PER_CLIP` |
| Spektar i PSD-shape | [firmware/esp32s3_asd/main/psd_features_c.c](../../firmware/esp32s3_asd/main/psd_features_c.c), `psd_accumulate_segment()`, 86; `psd_finalize()`, 100–124 | Hann, snaga, logaritam i oduzimanje sredine |
| Obrada pristiglih blokova | [firmware/esp32s3_asd/main/psd_features_c.c](../../firmware/esp32s3_asd/main/psd_features_c.c), `asd_psd_stream_push_hop()`, 209 | prethodni i tekući blok formiraju segment |

## 4. Lokalna kalibracija i odluka — 3 minuta

### Šta kažem profesoru

„U prikazanom GUIDED25 protokolu prvo koristim 10 normalnih prozora za
lokalni centar i provjeru stabilnosti. Zatim 44 nova prozora služe za
pragove. Još 22 prozora provjeravaju normalan rad sa već određenim
pragovima. Poslije uspješne pripreme profil ostaje zamrznut.“

„Jedan visok score nije dovoljan. Alarm traži tri uzastopna pouzdana
prozora iznad ulaznog praga. Ako je posmatranje nestabilno, HOLD prekida taj
niz. Ako alarm već traje, HOLD ga ne briše. Za povratak je potreban pouzdan
prozor na ili ispod nižeg izlaznog praga.“

### Ako profesor postavi potpitanje

**Zašto tri odvojena bloka?** CAL postavlja centar, DERIVE određuje pragove,
a VERIFY ispituje već postavljenu odluku na drugom bloku normalnog rada.
Provjera na istim prozorima iz kojih je prag izračunat bila bi povoljnija
nego provjera na novim podacima. Kratak VERIFY ipak nije dugoročna garancija.

**Kako nastaju pragovi?** Ulaz koristi empirijski p99 DERIVE ocjena.
`percentile_higher()` bira viši rang, pa kod 44 vrijednosti p99 odgovara
maksimumu bloka. To nije dokaz da će buduća stopa lažnih alarma biti 1%.
Izlaz polazi od p95, ograničava se na najviše polovinu ulaza i najmanje
medijanu normale. Ako te granice ne mogu zajedno da važe, kalibracija se
odbija. Ne predstavljam izlaz kao univerzalnih `0,7 × ulaz`: to postoji u
podrazumijevanoj vremenskoj politici, ali ovaj tok koristi lokalne pragove.

**Šta pokreće HOLD?** Razvojna provjera posmatra nestabilnost pet grupa
segmenata unutar istog prozora. Granica se uči iz normalnog CAL bloka kao
maksimalna normalna nestabilnost puta 1,25. Grupe nisu pet nezavisnih
snimaka. HOLD ne zna uzrok smetnje i može odbaciti i stvarnu promjenu.

**Zašto zamrznut centar?** Automatsko pomjeranje centra tokom nadzora moglo
bi postepeno da usvoji nenormalan zvuk. Novo učenje pokreće operator kada
zna da je postavka spremna. Kod može odbaciti nestabilnu kalibraciju; 10
prikupljenih CAL prozora ne znači da svaki bezuslovno ulazi u konačni centar.

### Kod koji pokazujem

| Teza | Fajl, funkcija i linije | Šta gledam |
|---|---|---|
| GUIDED25: 44 + 22 | [firmware/esp32s3_asd/main/asd_commissioning.c](../../firmware/esp32s3_asd/main/asd_commissioning.c), `asd_commission_guided25_policy()`, 37–46 | broj DERIVE i VERIFY prozora; CAL `N_CAL=10` u `psd_live.c`, 44 |
| Izvođenje pragova | [firmware/esp32s3_asd/main/psd_live.c](../../firmware/esp32s3_asd/main/psd_live.c), 1002–1032; `percentile_higher()`, 519 | kvantili, granice izlaza i zamrzavanje pragova |
| Granica pouzdanosti | [firmware/esp32s3_asd/main/asd_interference.c](../../firmware/esp32s3_asd/main/asd_interference.c), `asd_interference_calibrate_normal()`, 23–39; `asd_interference_update()`, 73 | prag iz normalne nestabilnosti i provjera novog prozora |
| HOLD i postojeći alarm | [firmware/esp32s3_asd/main/asd_events.c](../../firmware/esp32s3_asd/main/asd_events.c), `asd_decide()`, 305–318 | `asd_temporal_suspend()` i zadržavanje stanja |
| Tri prozora i histereza | [firmware/esp32s3_asd/main/asd_temporal.c](../../firmware/esp32s3_asd/main/asd_temporal.c), `asd_temporal_update()`, 58–107; `asd_temporal_suspend()`, 50 | ulazni niz, izlazni prag i prekid niza |

## 5. Razvojni rezultati na računaru — 2 minuta

### Šta kažem profesoru

„Raniji autoenkoder imao je AUC 0,4682 u prikazanoj polaznoj referenci.
PSD-shape je u razvojnom eksperimentu sa 20 podjela dao oko 0,856, a u
odvojenoj PC referenci sa 100 podjela oko 0,867. To podržava izbor ovog
pristupa za nastavak rada, ali protokoli nisu isti i ne predstavljam
razliku kao kontrolisano poređenje na jednom testu.“

„AUC govori o rangiranju: da li anomalni snimci dobijaju više ocjene od
normalnih. To nije procenat tačnih alarma. Posebno sam provjerio računanje
istih obilježja i ocjene u Pythonu i C-u. U fizičkim probama računanje je
trajalo približno 716 do 728 ms po prozoru.“

### Ako profesor postavi potpitanje

**Šta znači AUC oko 0,856?** Može se tumačiti kroz vjerovatnoću da slučajno
izabrani anomalni primjer dobije višu ocjenu od normalnog, uz tretman
izjednačenih ocjena. Za stvarni alarm su potrebni konkretan prag, vremensko
pravilo i provjera pouzdanosti. Zato dobar AUC ne garantuje dobar oporavak.

**Šta znači ±?** Standardnu devijaciju rezultata kroz podjele, a ne interval
pouzdanosti. Podjele i izbor modela pripadaju razvojnoj evaluaciji.
PC referenca koristi `k=20` za lokalni centar; firmware započinje sa 10 CAL
prozora. Brojeve ne prenosim direktno kao performanse uređaja.

**Da li je alarm brz 716 ms?** Ne. To je zabilježeno vrijeme računanja.
Treba prikupiti približno deset sekundi zvuka po prozoru i zadovoljiti niz
od tri pouzdana visoka prozora. Tačno kašnjenje zavisi od trenutka nastanka
promjene, obrade i HOLD-a i mora zasebno da se izmjeri.

### Kod i rezultat koji pokazujem

| Teza | Fajl, funkcija i linije | Šta gledam |
|---|---|---|
| PSD razvojni AUC | [results/advanced/advanced_results.json](../../results/advanced/advanced_results.json), 84–89 | `psd_shape`, sredina, standardna devijacija i 20 podjela |
| C i Python obilježja | [pc/tests/test_psd_features_c.py](../../pc/tests/test_psd_features_c.py), `test_psd_real_wav_pc_vs_c()`, 121 | isti WAV ulaz u dvije implementacije |
| Streaming i batch | [pc/tests/test_psd_features_c.py](../../pc/tests/test_psd_features_c.py), `test_psd_stream_matches_batch()`, 138 | slaganje dva načina obrade |
| C i Python ocjena | [pc/tests/test_psd_features_c.py](../../pc/tests/test_psd_features_c.py), `test_psd_score_pc_vs_c()`, 165 | provjera računa Mahalanobis ocjene |

Za 100 podjela otvorim
[aggregate_summary.csv](../../results/canonical_evaluation/canonical-evaluation-v1.1.0_m7-e7dedc81_k20_s100_sr20260809_b2000_br20260810_ms92dcebb5_src285b8c84_dep3eec7eed_datae3eb5bd5_195c0f34f7e6/aggregate_summary.csv)
i pronađem `fan` / `psd_shape`. Postojanje testova ne znači da su oni ponovo
izvršeni prilikom pripreme ovog vodiča.

## 6. Fizičke probe — 4 minuta

### Šta kažem profesoru

„Na oba grafikona X osa predstavlja vrijeme, a Y score na logaritamskoj
skali. Crvena linija je prag ulaska, zelena prag izlaska. Plave tačke su
pouzdani prozori, narandžasti krugovi HOLD, a crveni trouglovi alarm.“

![Score i alarm tokom probe papirićem](../../photos/sl_run_papiric.png)

„Kod papirića se promjena vidi u ocjeni, ali nestabilni prozori često
prekidaju niz potreban za alarm. Alarm je nastao u jednom od tri bloka i
prenio se u oporavak. Zato je ukupni GUIDED25 rezultat FAIL. Ovaj primjer
pokazuje ograničenje konačne odluke, iako score reaguje.“

![Score i alarm tokom tonske probe](../../photos/sl_run_ton.png)

„Kod stabilnog tona od 1 kHz zabilježena su dva ulaska u alarm. Pred kraj
score pada ispod ulaznog praga, ali ostaje iznad izlaznog, pa povratak u
normalu nije potvrđen. Ton je trajao oko šest minuta poslije oznake oporavka
u evidenciji. Zato oznaku faze ne izjednačavam sa tačnim fizičkim prestankom
tona.“

**Šta pokazujem:** grafikone iznad. Zatim u CSV-u tonske probe
uporedim normalan red i red tokom tona: `condition`, `score`, `threshold`,
`hold` i `alarm`.

### Ako profesor postavi potpitanje

**Zašto ne smanjiti prag da papirić prođe?** Prag i pravilo ne treba
prilagođavati samo tom poznatom rezultatu. Promjena može povećati osjetljivost,
ali i lažne alarme. Doradu bih provjerio na novim normalnim i promijenjenim
uslovima, uz unaprijed određene kriterijume prolaza.

**Zašto je ton koristan ako nije kvar?** Daje kontrolisanu promjenu zvuka i
pokazuje da cijeli tok može da reaguje na održano odstupanje. Ne dokazuje da
sistem razlikuje mehanički kvar od spoljašnjeg tona ili promjene brzine.

**Šta treba ponoviti?** Tačno evidentirati fizički početak i kraj promjene,
održati položaj mikrofona, provjeriti više ponavljanja i sačekati dovoljno
dug stvarni normalan oporavak. Zasebno pratiti propuštene promjene, lažne
alarme i vrijeme oporavka.

### Dokaz i kod koji pokazujem

| Teza | Fajl i mjesto | Šta gledam |
|---|---|---|
| Papirić: FAIL i 1/3 | [guided25_report.json](../../results/physical_fan/run_20260827T213148_fan02_guided25-20260827-v3recovery5d/guided25_report.json), 3–8 | status i konkretni razlozi pada |
| Tok probe papirićem | [detections.csv — papirić](../../results/physical_fan/run_20260827T213148_fan02_guided25-20260827-v3recovery5d/detections.csv), zaglavlje 1 i redovi po `condition` | score, HOLD i alarm kroz faze |
| Tok tonske probe | [detections.csv — ton](../../results/physical_fan/run_20260827T220338_fan02_tone-validation-20260827-final/detections.csv), zaglavlje 1 i redovi po `condition` | razlikovanje visokog score-a i aktivnog alarma |
| Zašto alarm ostaje | [firmware/esp32s3_asd/main/asd_temporal.c](../../firmware/esp32s3_asd/main/asd_temporal.c), 87–99; [asd_events.c](../../firmware/esp32s3_asd/main/asd_events.c), 305–318 | niži izlazni prag i zadržavanje kroz HOLD |

## 7. Mjerna ploča i potrošnja — 2 minuta

### Šta kažem profesoru

„Pripremio sam posebnu mjernu ploču sa AMS1117 regulatorom i INA226
senzorom. Planirani put je od izvora od 5 V, preko regulatora i šanta, do
ESP32-S3 i mikrofona. Cilj je da izmjerim potrošnju čekanja, učenja i
normalnog nadzora u istoj fizičkoj konfiguraciji.“

„Prema posljednjoj evidenciji povezivanja, novo mjerenje sa spoljašnjim
napajanjem tek slijedi. Prvi korak je 60 sekundi čekanja sa aktivnim I2S-om;
to nije deep sleep. Prije konačnih brojeva provjeriću napon i struju
nezavisnim instrumentima i ponoviti mjerenja. Validna potrošnja kompletnog
detektora još nije završena.“

### Ako profesor postavi potpitanje

**Šta tačno ulazi u rezultat?** Potrošači iza šanta, uključujući mikrofon
ako je napajan sa te grane. Gubici AMS1117 i napajanje INA226 prije šanta
nisu uključeni. Zato rezultat nije automatski snaga uzeta iz izvora od 5 V.

**Zašto bez USB napajanja tokom mjerenja?** USB može da napaja uređaj mimo
šanta. Tada izmjerena struja ne predstavlja cijelu željenu granu. Sačuvani
rezultat može naknadno da se preuzme, po potvrđenom postupku mjerenja.

**Šta je energija?** Snaga je `P = U × I`, a energija je zbir snage puta
trajanje intervala, uz pravilne jedinice. Za kratku pojedinačnu obradu
potrebna je dovoljna vremenska rezolucija senzora; GPIO vremenski markeri
sami ne povećavaju rezoluciju INA226.

**Šta je već potvrđeno?** Avgustovski test mjernog lanca ima sačuvan rezultat,
ali bilježi problem naponskog kanala i kontakata. Novija bilješka opisuje
izmijenjeno povezivanje i naredni test. Te dvije evidencije ne spajam u
tvrdnju da je sadašnje mjerenje energije već validirano. LED i dodatni
kondenzatori prema novijoj bilješci još nisu povezani.

### Kod i dokument koji pokazujem

| Teza | Fajl, funkcija i linije / odjeljak | Šta gledam |
|---|---|---|
| Čitanje senzora | [firmware/esp32s3_asd/main/ina226.c](../../firmware/esp32s3_asd/main/ina226.c), `ina226_bus_mv()`, 154; `ina226_current_ua()`, 162; `ina226_power_uw()`, 170 | napon, struja, snaga i jedinice |
| Postojeći test mjernog lanca | [firmware/esp32s3_asd/main/ina226_test.c](../../firmware/esp32s3_asd/main/ina226_test.c), `report_prepare()`, 114; `report_finish()`, 166; `ina226_test_run()`, 408 | priprema, čuvanje i tok starijeg testa |
| Sadašnje povezivanje i plan | [mjerna-ploca-trenutno-stanje-i-e5-test.md](../elektronika/mjerna-ploca-trenutno-stanje-i-e5-test.md), „Tačne veze mjerne ploče“ i „Naredni test“ | granica mjerenja i šta još treba potvrditi |
| Ranija ograničenja | [e5-mjerenje-01-rezultat.md](../elektronika/e5-potrosnja/e5-mjerenje-01-rezultat.md), „Ishod u jednoj rečenici“ | odvojiti stari test od nove konfiguracije |

**Za pripremu demonstracije:** novija bilješka pominje `e5_capture.py` i
`results/mjerenje_2026-09-21/FLASH.ps1`, ali ti fajlovi nisu prisutni u ovom
klonu na `0b1f93b`. Njihove komande ne predstavljam kao spremnu demonstraciju;
prvo treba obezbijediti odgovarajući kod i potvrditi firmware na ploči.

## 8. Zaključak i naredni korak — 2 minuta

### Šta kažem profesoru

„Realizovao sam kompletan tok od mikrofona, preko obrade i lokalne
kalibracije, do autonomne odluke. Razvojni rezultati podržavaju korišćenje
PSD-shape modela. Fizičke probe potvrđuju reakciju na neke održane promjene,
ali jasno pokazuju da nestabilne promjene i oporavak još traže provjeru.“

„Kao doprinos bih izdvojio realizaciju i provjeru ovog toka na ograničenom
uređaju, uz odvajanje ocjene odstupanja od pouzdane vremenske odluke.
Ne tvrdim da sam dokazao prepoznavanje uzroka kvara ni dugoročnu pouzdanost.
Sljedeći koraci su nezavisne probe, provjera oporavka i mjerenje potrošnje.“

**Pitam profesora:** „Da li biste prvo uradili nezavisnu probu na drugom
ventilatoru ili doradu kalibracije i oporavka? Koji obim eksperimenata
smatrate dovoljnim i šta biste izdvojili kao glavni doprinos rada?“

### Ako profesor postavi potpitanje

**Kako bih organizovao naredni eksperiment?** Unaprijed bih zapisao uslove,
verziju firmware-a, položaj mikrofona i kriterijume uspjeha. Odvojio bih
kalibraciju od evaluacije, bilježio stvarne trenutke promjene i mjerio
lažne alarme, propuštene promjene, HOLD i oporavak. Poslije izmjene pravila
ponovio bih test i na podacima koji nisu korišćeni za tu doradu.

**Šta pokazati ako traži dokaz doprinosa?** Za računanje otvorim
`asd_psd_score()` iz cjeline 2; za odluku `asd_decide()` i
`asd_temporal_update()` iz cjeline 4; za stvarno ponašanje izvještaj i CSV
iz cjeline 6. Time povezujem metod, implementaciju i ograničenja rezultata.
