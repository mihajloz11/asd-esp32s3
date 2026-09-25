# Zaključani protokol stvarnog fizičkog ventilatora

**Verzija:** `physical-fan-v1.9.0`

**Datum zaključavanja:** 09.08.2026, bumpovano 16.08.2026, 20.08.2026. i 24.08.2026.
**Firmware:** fail-closed `ASD_PSD_LIVE`, serijski protokol `asd-quality-v1.6.0`.
V1.6 je potvrđen i na pločici: isti binarni fajl (354 784 B, SHA-256
`9ac2caca…8d967813`) pustio je oba validna runa 27.08.2026.

> **Izmjene u v1.9.0** (24.08.2026, detaljno:
> [DNEVNIK-NEXT-LEVEL.md](../../privatno/dnevnici/DNEVNIK-NEXT-LEVEL.md)): kapija pouzdanosti je
> uključena (`asd_interference` v3, `enabled = 1`), ali HOLD sada postaje
> **vidljiv hostu** umjesto da mu obori run. Ranija verzija bi oborila svaki
> naredni run kroz dva nezavisna lanca: `asd_temporal_suspend()` je pri HOLD-u
> postavljao `run = 0`, pa je host replay očekivao `uzastopnih=1` i prijavljivao
> `invalid_firmware_telemetry`; a `STATE ... to=OBSERVATION_HOLD` je bio naziv
> koji host nije poznavao. `ANOMALY_SUSTAINED` i `OBSERVATION_HOLD_WARNING` se
> javljaju dok stanje stoji, pa nemaju upareni `STATE` red i više se ne obaraju
> kao `unknown_or_unpaired_EVENT`. Novi zapis koristi
> `physical-fan-artifacts-v1.9.0`; offline reader i dalje čuva istorijske parove
> v1.6↔q1.3, v1.7↔q1.4 i v1.8↔q1.5, kao i `THRFIT` rječnik koji firmware više ne
> emituje, ali ga runovi 26–27.08. sadrže.
>
> **GUIDED25 hard deadline je uklonjen 27.08.** (`hard_deadline_seconds: null`,
> limit pokušaja `3 → 5`) — vidi
> [P27](../problemi-i-rjesenja.md#p27--hard-deadline-od-25-min-obara-run-prije-kraja-plana).

> **Izmjene u v1.8.0:** bounded audio read uvodi imenovane razloge
> `AUDIO_TIMEOUT` i `AUDIO_READ_ERROR`, oba fail-closed u `SENSOR_ERROR`.
> Novi zapis koristi `physical-fan-artifacts-v1.8.0`; offline reader strogo
> čuva istorijske parove v1.6↔quality-v1.3 i v1.7↔quality-v1.4, te dodaje samo
> novi v1.8↔quality-v1.5 par. Firmware ima testiran, verzionisan storage modul
> `asd-profile-v1.0.0`, ali trenutna DEVELOPMENT politika je RAM-only:
> compile-time gate je `0`, a runtime dodatno zahtijeva non-developmental
> policy. Zato ovaj build ne radi NVS init/load/save i ne emituje
> `PROFILESTORE`; takav zapis ili lažni `PROFILE_RESTORED` host odbija.
> Svježi commissioning ima razvojni sidecar
> `SETTLE → CENTER_LEARNING → COMMISSION_DERIVE → COMMISSION_VERIFY →
> MONITORING`, zamrznut centar i odvojene apsolutne enter/exit pragove. Broj
> prozora i numeričke granice još su `DEVELOPMENT/PENDING` i ne smiju se
> proglasiti finalnim bez novog normal-only fizičkog runa.

> **Izmjene u v1.7.0:** K1 commissioning pravilo `loo_cv <= 0,6` sada je
> centralna, verzionisana odluka. Pad emituje terminalni
> `CALIBRATION_REJECTED`/`FLOW_STOPPED`, nikada `ADAPTTHR` ili DET. Host čeka i
> odgovarajući `SESSION ENDED`; ako nedostaje, bounded drain završava
> fail-closed timeoutom umjesto da visi ili prerano proglasi kompletan protokol.
> Offline reader prihvata samo parove `physical-fan-v1.6.0` ↔
> `asd-quality-v1.3.0` i `physical-fan-v1.7.0` ↔ `asd-quality-v1.4.0`;
> novi v1.7 zapis dodatno mora imati
> `artifact_contract_version=physical-fan-artifacts-v1.7.0`.
> Jedan host run sada može sadržati više firmware sesija. Svaki `SESSION
> STARTED` resetuje samo session-scope brojače, pragove i operator condition,
> dok boot handshake, provenance i run totals ostaju sačuvani.

> **Izmjene u v1.6.0** (detaljno: [DNEVNIK-NEXT-LEVEL.md](../../privatno/dnevnici/DNEVNIK-NEXT-LEVEL.md),
> blokovi B–D):
>
> - **Operater pokreće učenje.** Nema vremenskog autostarta — nijedna sesija,
>   ni prva poslije uključenja, ne kreće sama (`wait_for_start()` u
>   [psd_live.c](../../firmware/esp32s3_asd/main/psd_live.c)). Radnja stiže sa
>   fizičkog tastera **ili** kao `PRESS`/`HOLD` sa konzole; oba ulaza dijele
>   isti put i isti `BUTTON` zapis. Lampica javlja kada je učenje gotovo —
>   puni tok demoa je u [PREOSTALO.md](../../privatno/PREOSTALO.md).
> - `EVENT` nosi `event`, `capability` i `level` (semantika Faze 2).
> - Novi zapisi `PRESENCE`, `TEMPORAL`, `SESSION`, `BUTTON`. Prva dva
>   objavljuju politike kojima host **nezavisno ponavlja** odluku uređaja.
> - Tadašnja v1.6 politika gasila je alarm ispod **0,7× praga**. V1.8 runtime
>   umjesto toga koristi zaseban apsolutni `threshold_exit` iz profila.
> - Zaustavljanje ventilatora daje `PRESENCE_LOST` → `NO_MACHINE`, ne anomaliju.
>
> **Prije prolaza pročitati [P17](../problemi-i-rjesenja.md#p17)** — prag se između
> kalibracija razlikuje i do 16× i to direktno utiče na osjetljivost demoa.

Ovaj protokol je nastao za prvi stvarni test u kojem INMP441 sluša ventilator direktno.
Reprodukcija DCASE WAV-a preko zvučnika nije fizički fan eksperiment. Bezbjedno
izazvana promjena uslova takođe se ne naziva „stvarnim kvarom” bez nezavisne
stručne potvrde.

## 1. Istorijski preflight, prvi pokušaji i FAN01

Početna provjera 09.08.2026. nije vidjela serijski port. Nakon spajanja pločice,
zapisani preflight u 22:35 je pronašao COM3 (ESP32-S3, VID:PID `303A:1001`) i
COM4 (CH343); COM3 je potvrđen kao port uređaja. Taj istorijski build je imao
291.536 B. Novi fail-closed build iz Faze 1 napravljen je bez pločice i ima
295.312 B; to nije dokaz flasha ni runtime rada.

Dva capture pokušaja su prekinuta prije prvog DET prozora i nisu fizički
rezultati. Korisnik je naknadno potvrdio da fizički ventilator uopšte nije bio
dostupan; zato su uneseni `fan01`, udaljenost i tvrdnja da fan radi bili pogrešni
preflight metapodaci, a ne opis stvarne postavke:

- `cold-start-01`: `invalid_no_physical_fan`, prekinut tokom kalibracije, bez DET
  prozora;
- `cold-start-02`: `invalid_no_physical_fan`; samo 6/60 WAIT mjerenja bilo je
  iznad `-60 dBFS`, što je očekivano jer fan nije postojao u postavci.

Fizički ventilator je zatim nabavljen i 16.08.2026. je završen prvi valjan
v1.6/q1.3 FAN01 run. On je dokazao stvarni capture i separaciju papirića, ali ne
i upotrebljiv prag. Trenutni v1.8/q1.5 build od 349 728 B prolazi ESP-IDF build,
ali još nije flashovan niti fizički validiran. Istorijski run se ne prepisuje;
novi run uvijek dobija novi direktorij i novi verzioni par.

Ponoviti provjeru nakon spajanja pločice podatkovnim USB kablom:

```powershell
.\.venv\Scripts\python.exe .\pc\tools\physical_fan_experiment.py preflight
```

Preflight zapisuje i blokiran pokušaj u `results/physical_fan/preflight_*`; on
je dokaz stanja hardvera, ali nije eksperimentalni run.

## 2. Fail-closed kalibracioni ugovor

Firmware emituje ASCII zapise `QUALITY`, `STATE` i `EVENT` sa protokolom
`asd-quality-v1.6.0`. Prije ulaska u kalibraciju i za svaki kalibracioni klip
provjeravaju se broj vraćenih uzoraka, konačne numeričke vrijednosti, stuck/zero signal,
nivo, clipping i `dropped_delta`. Nevalidan rezultat zaustavlja tok; ne postoji
više put „upozori i nastavi“.

UART numerika je uvijek konačna. Kada metrika nije računljiva, firmware ne
ispisuje `nan`/`inf`, nego konačan sentinel uz `metrics_valid=0`; zaseban
`feature_valid` dokazuje da je PSD imao tačno 38 segmenata i konačan feature
vektor. Zato PCM-validan, ali feature-nevalidan klip zakonito nosi
`result=NONFINITE`, `metrics_valid=1`, `feature_valid=0` i fail-closed stop,
umjesto parser kontradikcije. Tonalnost koja
u toj fazi nije računata ima `tonalness_valid=0`, `tonalness_proxy=0` i
`tonal_gate=not_computed`. Razlog u `result` ostaje autoritativan za firmware,
ali host ga nezavisno ponovo izračunava iz verzionisane quality politike i
odbija nemoguće kombinacije metrike i razloga.

Poslije deset CAL klipova firmware prvo emituje `CAL_SUMMARY`, pa primjenjuje
K1 nad istom šestodecimalnom `loo_cv` vrijednošću. Host koherentnost
`loo_cv = loo_sd / |loo_mean|` provjerava iz tačnih intervala koje predstavlja
šestodecimalni UART ispis (±0,5×10⁻⁶), a ne proizvoljnom relativnom tolerancijom.
K1 reject je validan, ali metrički nepodoban protokol tek kada su upareni
terminalni STATE/EVENT i otvoreni `SESSION STARTED` zatvoren sa `SESSION ENDED`.

Tokom WAIT-a pojedinačni tihi blok je `LOW_LEVEL_OBSERVATION`, a ne reject, jer
je to namjenski period u kojem operater pokreće fan. Ne broji se kao validan;
ako manje od pola blokova prođe, zaseban `INSUFFICIENT_LEVEL` reject završava u
`NO_MACHINE`. Isti low-level rezultat u CAL/DET odmah zaustavlja tok. Guard za
V1.8 production put koristi bounded `audio_read_exact()` sa jednim ukupnim
deadlineom. Timeout i read error imaju odvojene javne razloge i završavaju u
`SENSOR_ERROR`; host fixture i ESP-IDF build to potvrđuju. Stvarno odspajanje
I2S-a i timeout na pločici još nisu izvršeni, pa ostaju hardverska provjera.

Fiksna quality politika i porijeklo pragova zapisani su u
[`pc/config/asd_quality_policy_v1.json`](../../pc/config/asd_quality_policy_v1.json).
Target anomalije nisu korištene. Tonalness proxy i LOO mean/sd/CV/range se
zapisuju. K1 ostaje quality gate centra, ali više nije izvor runtime praga.
Svježi profil prvo zamrzava centar, zatim iz vremenski odvojenog normal-only
DERIVE bloka izvodi dva apsolutna praga, a kasniji VERIFY ih samo provjerava.
Numeričke vrijednosti su DEVELOPMENT dok novi fizički normal-only run ne prođe.

Dozvoljena javna stanja uključuju `NO_MACHINE`, `CALIBRATION_REJECTED`,
`CALIBRATED_NORMAL`, `ANOMALY`, `OBSERVATION_HOLD`, `SENSOR_ERROR` i
`RECALIBRATION_REQUIRED`. HOLD ne znači da je uzrok dokazano razgovor: jedan
mikrofon ne emituje dijagnozu `AMBIENT_NOISE`. HOLD suspenduje buildup i ne
briše aktivan alarm ni profil. Numeric policy je trenutno isključen do fizičke
normal-only validacije. Nakon quality rejecta firmware ne ulazi u narednu fazu.

Za novi live v1.8/q1.5 tok host prihvata DET samo poslije
`BOOT_FAIL_CLOSED` handshakea i literalnog firmware redoslijeda: `COMMISSION
STARTED`, dinamički SETTLE do stabilnosti (unutar konfigurisanih min/max
granica), ulazak u CENTER, `WAIT 1..60`, `CAL 1..10`, jedan `CAL_SUMMARY` i K1,
zatim tačno 120 `COMMISSION_DERIVE` prozora (20 min) i 60 kasnijih VERIFY
prozora (10 min), čiji posljednji
zapis prelazi u `MONITORING`, pa strogi `PROFILE`. Poslije svježeg profila slijede
`ADAPTTHR n=120` iz DERIVE statistike, `PRESENCE`, `TEMPORAL` v2 sa
`threshold_mode=absolute_profile` i pragovima jednakim profilu, te oba
`CALIBRATION_ACCEPTED` zapisa (prvo STATE, pa EVENT). Najmanje 30 od 60 WAIT
blokova mora imati host-potvrđen `OK`; pojedinačni low-level observation se
nikada ne računa kao prolaz. ADAPTTHR mean/sd su DERIVE statistike, nisu
CAL_SUMMARY LOO identity. Svaki DET mora ponoviti objavljeni apsolutni enter
prag. Svaki `QUALITY phase=DET`
je jednokratni token: njegov `index` mora biti sljedeći window i odmah ga mora
potrošiti odgovarajući DET zapis. Duplikat, replay, preskočen indeks ili drugi
firmware zapis između tog para invalidira run.

Host dodatno zahtijeva finite numeriku, fazno tačan broj uzoraka, validne
countove i `dropped_delta=0` za prihvaćen observation. Za DET nezavisno
provjerava binarne `led/anom`, monoton `window`, `total_anom` i `uzastopnih`,
njihovu saglasnost sa `score > threshold`, alarmom i verdictom. Firmware DET
ispis koristi devet značajnih cifara kako bi binary32 poređenje bilo
rekonstruktivno na hostu.

Host prihvata samo fizički moguće metrike: `rms_dbfs <= 0`,
`abs(dc) <= peak <= 32768`, a RMS rekonstruisan iz dBFS ne smije preći peak uz
toleranciju od 0,1% + 1 PCM zbog zaokruživanja UART ispisa. Validna tonalnost i
Mahalanobis/LOO score moraju biti nenegativni. Firmware i host koriste isti
eksplicitni numerički prag `1e-3`: samo vrijednost u `[-1e-3, 0)` smije se
clampovati na nulu; veća negativna vrijednost je `NONFINITE`/invalid. DET linija
je potpuno anchorovana, nema trailing teksta, a `lo` mora biti konačan i tačno
nula.

Prihvaćeni DET određuje i obaveznu state tranziciju. Ako je prethodno stanje
`CALIBRATED_NORMAL` i DET alarm postane 1, sljedeći protokolarni zapis mora biti
tačan `CALIBRATED_NORMAL -> ANOMALY`, pa odmah `ANOMALY_ENTERED`. Ako je prethodno
stanje `ANOMALY` i alarm postane 0, mora slijediti tačan povratak i
`ANOMALY_CLEARED`. Kada se alarm-state ne mijenja, STATE tranzicija je
zabranjena. Run nije kompletan dok očekivani par nije potrošen; time `stop`
između DET-a i njegovog STATE/EVENT para ne može proizvesti validan rezultat.

Pogrešna/nedostajuća verzija, malformed/truncated v1 telemetrija, `SENSOR_ERROR`
i neupareni ili neočekivani terminalni zapisi prekidaju run sa invalid statusom;
greška se ne prećutkuje. Jedini kalibracioni reject koji je validan i auditabilan
terminalni protokol jeste upareni `CALIBRATION_REJECTED` + `FLOW_STOPPED` sa
razlogom `UNSTABLE_CALIBRATION`, poslije K1 pada i prije `ADAPTTHR`/DET. Ta sesija
ne ulazi u metrike, ali host može prihvatiti sljedeću novu sesiju.

`NO_MACHINE -> NO_MACHINE / BOOT_FAIL_CLOSED` obavezan je tačno jednom odmah
poslije svakog `SESSION STARTED`, jer ga firmware emituje unutar svakog
`run_session()`. Ostale tranzicije u `NO_MACHINE` prihvataju se samo kada ih
tačno dozvoljava state/event ugovor, na primjer uredno upareni `PRESENCE_LOST`.
STATE/EVENT lanac, razlog, faza i očekivano terminalno stanje uvijek moraju
međusobno odgovarati.

Ako QUALITY već prijavi reject, eksperiment je odmah nevalidan i nijedan DET se
više ne prihvata. Host tada samo nastavlja bounded UART drain najviše 2,5 s da
sačuva završni STATE i `FLOW_STOPPED` EVENT; to nije nastavak eksperimenta. Ako
ne stignu oba zapisa, zapisuje se `terminal_drain_timeout` i zadržava invalid
status. Serijski timeout se tokom tog drena skraćuje tako da ne probije ukupnu
granicu od 2,5 s.

Komanda `stop` i vremensko ograničenje prvo rade kratki, odvojeni drain već
bufferovane UART telemetrije. Zato reject koji je već stigao u OS buffer ne može
biti preskočen kao uredan završetak. Greška otvaranja porta, ne-prazan command
file ili nevalidna `condition` oznaka ostaju auditabilni u provenance/summary;
isto važi za grešku otvaranja/zatvaranja izlaznog artefakta i zatvaranja porta.
Status `in_progress` se u tim failure putevima zamjenjuje sa `failed` kad god je
run direktorij i dalje upisiv, a port se zatvara kad god je bio otvoren.

## 3. Fiksirati prije gledanja rezultata

Za svaki run unaprijed zapisati:

- jedinstven `fan_id` i `session_id`;
- tip ventilatora, nominalni napon/brzinu i način napajanja;
- prostoriju i relevantnu pozadinsku buku;
- udaljenost mikrofona u cm i ugao;
- način fiksiranja ventilatora i mikrofona;
- hladni ili topli start;
- temperaturu, ako je dostupna;
- tačan bezbjedni uslov i očekivano trajanje svakog događaja.

Ventilator, mikrofon, nosač, udaljenost, ugao i napajanje ne pomjeraju se između
kalibracije i ocjene iste sesije.

## 4. Obavezna sigurnost

- Ne dodirivati rotirajuće lopatice, ne gurati predmet kroz rešetku i ne
  namjerno oštećivati ventilator.
- Koristiti samo niskonaponski ventilator i napajanje unutar deklarisanih
  granica proizvođača.
- Promjenu nosača raditi samo kada je ventilator ugašen; prije ponovnog
  uključivanja provjeriti da ništa ne može ući u lopatice.
- Dopuštene promjene su ugrađena brzina, djelimična promjena protoka sa spoljne
  strane zaštitne rešetke, bezbjedno gašenje, dodatna ambijentalna buka i
  promjena oslonca urađena dok je uređaj ugašen.
- Ako ima vibracija, zagrijavanja, mirisa, oštećenog kabla ili nestabilnog
  nosača, odmah prekinuti napajanje i run označiti kao prekinut.

## 5. Redoslijed jedne ili više sesija u host runu

Host ostaje aktivan poslije uredno zatvorene K1-odbijene sesije, tako da
operater može pokrenuti novo učenje bez ponovnog pokretanja PC alata. Druga
svježa sesija ponovo mora emitovati puni q1.5 commissioning slijed opisan iznad,
uključujući `WAIT 1..60`, `CAL 1..10`, `CAL_SUMMARY`, DERIVE/VERIFY i PROFILE;
brojači se ne nastavljaju iz prethodne sesije. Condition oznaka se na
svakom `SESSION STARTED` vraća na `unconfirmed` i mora se ponovo zadati prije
prozora koji ulaze u metrike.

1. U tihoj prostoriji fiksirati ventilator i mikrofon, tipično na 10–20 cm.
2. Pokrenuti ventilator u potvrđeno normalnom, stabilnom režimu.
3. Potvrditi da je novi fail-closed build flešovan, pa pokrenuti capture alat.
   Alat resetuje već fleširanu pločicu, ali sam ništa ne flešuje i ne pušta zvuk
   preko zvučnika.
4. Tokom SETTLE/CENTER ništa ne mijenjati. `N_CAL=10` ostaje lokalni centar;
   SETTLE nema Mahalanobis score prije centra. DEVELOPMENT firmware counts nisu
   završna vremenska politika.
5. Prije prvog prozora koji smije u metrike eksplicitno unijeti
   `condition normal_baseline ...`. Poruka `DETEKCIJA RADI` nikada sama ne
   postavlja operatorovu istinu. Snimiti tačno 30 min normal-only podataka i
   hronološki ih podijeliti: prvih 20 min DERIVE, posljednjih 10 min VERIFY,
   bez overlap-a ili randomizacije. Ako firmware DEVELOPMENT count završi prije
   toga, research sidecar i host vrijeme ostaju autoritet ovog commissioning
   eksperimenta; profile se ne proglašava production defaultom.
6. Prije target readouta zamrznuti manifest, centar, oba praga i policy ID/hash.
   VERIFY ne smije mijenjati nijednu od tih vrijednosti.
7. Tek poslije prolaza uraditi najviše tri `airflow_change` papirić bloka i dva
   `ambient_noise` conversation bloka. Svaki označiti prije promjene, držati
   najmanje pet punih prozora, pa označiti `recovery_normal`.
8. Završiti komandom `stop`. Prag/HOLD granica se ne podešavaju iz ovog target
   readouta; neuspio kandidat pripada novoj verziji i novoj sesiji.

Primjer pokretanja:

```powershell
.\.venv\Scripts\python.exe .\pc\tools\physical_fan_experiment.py run `
  --port COM3 `
  --fan-id fan01 `
  --session-id cold-start-01 `
  --distance-cm 15 `
  --angle-deg 0 `
  --room laboratorija `
  --fan-speed-or-voltage nominal
```

Ručne komande tokom rada:

```text
press                     virtuelni taster: kratak pritisak (pokrece ucenje)
hold                      virtuelni taster: dug pritisak (nova kalibracija)
condition normal_baseline pocetak stabilnog normalnog mjerenja
condition speed_change ugrađena brzina 2
condition airflow_change djelimično pokrivena spoljna rešetka, bez kontakta
condition controlled_stop ventilator bez napajanja
condition ambient_noise razgovor na 2 m
condition recovery_normal vracen isti normalni režim
note proizvoljna biljeska bez promjene uslova
abort razlog prekida prije valjane detekcije
stop
```

Za headless pokretanje može se dodati `--command-file <putanja>` i iste komande
dopisivati u tu datoteku. Alat čita samo novodopisane redove i čuva ih u
`events.csv`.

Umjesto kucanja, isti `press`/`hold` mogu doći iz panela u pregledaču — vidi
[panel-i-virtuelni-taster.md](../uredjaj/panel-i-virtuelni-taster.md). Panel ne drži port
i ne ulazi u metrike; dopisuje u isti command file i čita `serial.log` runa.

## 6. Artefakti i integritet

Svaki stvarni run odmah dobija vlastiti `results/physical_fan/run_*` direktorij:

- `serial.raw` — tačni bajtovi primljeni sa pločice;
- `serial.log` — čitljiv log sa UTC i proteklim vremenom;
- `events.csv` — operatorova istina: ručne oznake uslova, bilješke i host faze,
  uz `firmware_session_index`; potvrda montaže iz `start_fan_run.py` nije typed
  event nego `provenance.metadata.operator_notes`;
- `detections.csv` — svi DET zapisi uz `firmware_session_index`, firmware-local
  `window`, run-global `run_det_index`, `condition_confirmed`,
  `transition_window` i `protocol_valid`;
- `firmware_quality.csv` — quality metrike i razlog accept/reject odluke;
- `firmware_states.csv` — isključivo firmware state tranzicije;
- `firmware_events.csv` — isključivo firmware događaji;
- `firmware_parse_errors.csv` — sirova malformed/protocol-mismatch linija i
  host razlog parse ili semantic invalidacije;
- `window_features.npz` — opcioni razvojni binary32 sidecar: finalni `feature96`,
  pet `subseg96` vektora, monotonic vrijeme, score, nivo, tonalnost i ključ
  sesija/prozor;
- `window_features.manifest.json` — research schema, shape/dtype ugovor, SHA-256
  NPZ-a, strict validnost i eventualna veza ka eksternom WAV-u;
- `provenance.json` — COM identitet, metapodaci, Git stanje, SHA-256 firmvera,
  modela i relevantnog izvornog koda;
- `SUMMARY.md` — deskriptivni rezultat po označenom uslovu, po firmware sesiji
  i za cio run (DET totals, alarmni prozori/epizode, alarm-time, oporavak i
  isključeni prelazni prozori).

`stop` prije prvog DET prozora dobija status `aborted_before_detection`, a
eksplicitni `abort` status `aborted_by_operator`. Nijedan zapis sa nula DET
prozora ne smije biti označen kao validan fizički rezultat.

Firmware u ovom modu ne šalje kontinuirani sirovi PCM dok detektor radi. Zato
paralelni WAV zahtijeva nezavisan audio snimač. Ako postoji, njegova putanja se
prosljeđuje sa `--wav-path`; alat bilježi SHA-256 na početku i kraju. Bez tog
fajla ne smije se tvrditi da je sirovi WAV snimljen.

Research build se eksplicitno uključuje sa `ASD_RESEARCH_TELEMETRY=1`. Njegov
zasebni wire ugovor je `asd-research-v1.0.0`: jedan `FEATURE96` i tačno pet
`SUBSEG96` zapisa (`8/8/8/7/7` preklapajućih Welch segmenata) za svaki validni
CAL/DET prozor. Svaki vektor ima `dims=96` i FNV-1a checksum. U DET fazi ovi
zapisi dolaze tek poslije neposrednog `QUALITY DET -> DET` para. Host opcija
`--research-telemetry-required` fail-closed odbija missing, duplicate, malformed,
checksum ili shape grešku research artefakta; bez te opcije research greška ne
mijenja zaključani fizički protokol.

Operatorov `condition` počinje kao `unconfirmed`, vraća se na `unconfirmed` na
svakom novom `SESSION STARTED` i nikada se ne popunjava iz firmware
DET/state/event zapisa. Prvi prozor nakon nove `condition` komande označava se
kao `transition_window=1` i ne ulazi u metrike. Tek naredni prozori sa potvrđenim
uslovom i validnim firmware protokolom ulaze u validan rezultat.

## 7. Metrike i pošteno tumačenje

Za normalni dio prijaviti trajanje, broj odluka, alarmne prozore, alarmne
epizode, alarm-time i chatter odvojeno. `324/h` iz FAN01 znači 54/60 alarmnih
prozora skaliranih na sat, ne 324 alarmne epizode/h. Za svaki unaprijed definisan događaj prijaviti broj ponavljanja, broj
uhvaćenih događaja, prvi alarm, kašnjenje, uzastopne prozore, score/prag i
oporavak. Granice uslova su host oznake; 10-sekundni prozor na granici može
sadržati oba stanja i mora ostati označen kao prelaz u naknadnoj analizi.

VERIFY go/no-go u ovom skraćenom testu traži nula alarmnih prozora, nula
alarmnih epizoda i nula chatter prelaza u posljednjih 10 minuta. To nije dokaz
niske proizvodne stope: uz nula epizoda za 1/6 h jednostrani 95% Poisson gornji
limit je približno 18 epizoda/h. Rezultat je funkcionalni gate, ne procjena
dugoročne pouzdanosti.

Jedan ventilator dokazuje samo funkcionalnost prototipa u toj postavci, ne
generalizaciju na nove ventilatore. Za jaču tvrdnju potrebni su različiti fanovi,
nezavisne sesije, unaprijed zaključani uslovi i rezultati bez naknadnog
podešavanja modela ili praga na tim ishodima.
