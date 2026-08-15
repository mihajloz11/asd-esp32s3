# Zaključani protokol stvarnog fizičkog ventilatora

**Verzija:** `physical-fan-v1.6.0`
**Datum zaključavanja:** 09.08.2026, bumpovano 14.08.2026.
**Firmware:** fail-closed `ASD_PSD_LIVE`, serijski protokol `asd-quality-v1.3.0`,
flešovan i provjeren na pločici 14.08.2026.

> **Izmjene u v1.6.0** (detaljno: [DNEVNIK-NEXT-LEVEL.md](DNEVNIK-NEXT-LEVEL.md),
> blokovi B–D):
>
> - **Operater pokreće učenje.** Nema vremenskog autostarta — nijedna sesija,
>   ni prva poslije uključenja, ne kreće sama (`wait_for_start()` u
>   [psd_live.c](../firmware/esp32s3_asd/main/psd_live.c)). Radnja stiže sa
>   fizičkog tastera **ili** kao `PRESS`/`HOLD` sa konzole; oba ulaza dijele
>   isti put i isti `BUTTON` zapis. Lampica javlja kada je učenje gotovo —
>   puni tok demoa je u [PREOSTALO.md](PREOSTALO.md).
> - `EVENT` nosi `event`, `capability` i `level` (semantika Faze 2).
> - Novi zapisi `PRESENCE`, `TEMPORAL`, `SESSION`, `BUTTON`. Prva dva
>   objavljuju politike kojima host **nezavisno ponavlja** odluku uređaja.
> - Alarm se gasi tek ispod **0,7× praga** (histereza iz Faze 4).
> - Zaustavljanje ventilatora daje `PRESENCE_LOST` → `NO_MACHINE`, ne anomaliju.
>
> **Prije prolaza pročitati [P17](problemi-i-rjesenja.md#p17)** — prag se između
> kalibracija razlikuje i do 16× i to direktno utiče na osjetljivost demoa.

Ovaj protokol je za prvi stvarni test u kojem INMP441 sluša ventilator direktno.
Reprodukcija DCASE WAV-a preko zvučnika nije fizički fan eksperiment. Bezbjedno
izazvana promjena uslova takođe se ne naziva „stvarnim kvarom” bez nezavisne
stručne potvrde.

## 1. Trenutni preflight i prvi pokušaji

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

Stvarni fizički eksperiment je odgođen za drugi dan, dok se ne nabavi fizički
ventilator. Tada treba unaprijed izmjeriti i zapisati stvarnu postavku, pa
ponoviti build/flash/preflight/run. Novi fail-closed firmware još nije na
pločici i stari build se više ne smije koristiti za valjanu kalibraciju.

Ponoviti provjeru nakon spajanja pločice podatkovnim USB kablom:

```powershell
.\.venv\Scripts\python.exe .\pc\tools\physical_fan_experiment.py preflight
```

Preflight zapisuje i blokiran pokušaj u `results/physical_fan/preflight_*`; on
je dokaz stanja hardvera, ali nije eksperimentalni run.

## 2. Fail-closed kalibracioni ugovor

Firmware emituje ASCII zapise `QUALITY`, `STATE` i `EVENT` sa protokolom
`asd-quality-v1.3.0`. Prije ulaska u kalibraciju i za svaki kalibracioni klip
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

Tokom WAIT-a pojedinačni tihi blok je `LOW_LEVEL_OBSERVATION`, a ne reject, jer
je to namjenski period u kojem operater pokreće fan. Ne broji se kao validan;
ako manje od pola blokova prođe, zaseban `INSUFFICIENT_LEVEL` reject završava u
`NO_MACHINE`. Isti low-level rezultat u CAL/DET odmah zaustavlja tok. Guard za
short read postoji i host fixture ga provjerava, ali stvarni `audio_read`
trenutno koristi `portMAX_DELAY`; prekid I2S toka zato može ostati blokiran
umjesto da vrati short read. Timeout/liveness ostaje otvorena hardverska P2
provjera, ne prijavljuje se kao runtime potvrđena zaštita.

Fiksna quality politika i porijeklo pragova zapisani su u
[`pc/config/asd_quality_policy_v1.json`](../pc/config/asd_quality_policy_v1.json).
Target anomalije nisu korištene. Tonalness proxy i LOO mean/sd/CV/range se
zapisuju. Postojeći LOO-derived prag za kasniji anomaly score ostaje aktivan;
ono što je `pending_normal_only` jesu zasebni rejection gateovi koji bi odbili
kalibraciju zbog slabe tonalnosti ili prevelikog LOO rasipanja.

Dozvoljena javna stanja su `NO_MACHINE`, `CALIBRATION_REJECTED`,
`CALIBRATED_NORMAL`, `ANOMALY`, `SENSOR_ERROR` i
`RECALIBRATION_REQUIRED`. Nakon quality rejecta LED se gasi i firmware ne ulazi
u narednu CAL/DET fazu.

Host prihvata DET samo poslije `BOOT_FAIL_CLOSED` handshakea, tačno i redom
`WAIT 1..60/60`, `CAL 1..10/10` i tačno jednog `CAL_SUMMARY`, te oba
`CALIBRATION_ACCEPTED` zapisa (prvo STATE, pa EVENT). Najmanje 30 od 60 WAIT
blokova mora imati host-potvrđen `OK`; pojedinačni low-level observation se
nikada ne računa kao prolaz. Između `CAL_SUMMARY` i acceptancea mora postojati
tačno jedan finite `ADAPTTHR`, saglasan sa summary mean/sd; svaki DET mora
ponoviti upravo taj prag. Svaki `QUALITY phase=DET`
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

Pogrešna/nedostajuća verzija, malformed/truncated v1 telemetrija ili terminalni `FLOW_STOPPED`,
`SENSOR_ERROR`, `CALIBRATION_REJECTED` odnosno `RECALIBRATION_REQUIRED`
prekidaju run sa invalid statusom; greška se ne prećutkuje.
`NO_MACHINE` je legalan samo u početnom `BOOT_FAIL_CLOSED` handshakeu; svaka
kasnija tranzicija u to stanje takođe invalidira run. STATE/EVENT lanac, razlog,
faza i očekivano terminalno stanje moraju međusobno odgovarati.

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

## 5. Redoslijed jedne sesije

1. U tihoj prostoriji fiksirati ventilator i mikrofon, tipično na 10–20 cm.
2. Pokrenuti ventilator u potvrđeno normalnom, stabilnom režimu.
3. Potvrditi da je novi fail-closed build flešovan, pa pokrenuti capture alat.
   Alat resetuje već fleširanu pločicu, ali sam ništa ne flešuje i ne pušta zvuk
   preko zvučnika.
4. Tokom oko 15 s `WAIT` i 100 s `CAL` ništa ne mijenjati. Finalni firmware
   koristi `N_CAL=10`, dakle ukupno oko 115 s do završetka učenja. `k=20`
   ostaje referentni PC benchmark i nije dio ovog fizičkog protokola.
5. Prije prvog prozora koji smije u metrike eksplicitno unijeti
   `condition normal_baseline ...`. Poruka `DETEKCIJA RADI` nikada sama ne
   postavlja operatorovu istinu. Zatim držati isti režim najmanje 30–60 min.
6. Svaki bezbjedni događaj označiti neposredno prije promjene komandom
   `condition`, držati dovoljno dugo za najmanje pet punih prozora, pa označiti
   `recovery_normal` i vratiti normalan režim.
7. Završiti komandom `stop`. Ponoviti kroz više hladnih startova i nezavisnih
   sesija; premještanje mikrofona pripada novoj sesiji.

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
[panel-i-virtuelni-taster.md](panel-i-virtuelni-taster.md). Panel ne drži port
i ne ulazi u metrike; dopisuje u isti command file i čita `serial.log` runa.

## 6. Artefakti i integritet

Svaki stvarni run odmah dobija vlastiti `results/physical_fan/run_*` direktorij:

- `serial.raw` — tačni bajtovi primljeni sa pločice;
- `serial.log` — čitljiv log sa UTC i proteklim vremenom;
- `events.csv` — operatorova istina: ručne oznake uslova, bilješke i host faze;
- `detections.csv` — svi DET zapisi uz `condition_confirmed` i `protocol_valid`;
- `firmware_quality.csv` — quality metrike i razlog accept/reject odluke;
- `firmware_states.csv` — isključivo firmware state tranzicije;
- `firmware_events.csv` — isključivo firmware događaji;
- `firmware_parse_errors.csv` — sirova malformed/protocol-mismatch linija i
  host razlog parse ili semantic invalidacije;
- `provenance.json` — COM identitet, metapodaci, Git stanje, SHA-256 firmvera,
  modela i relevantnog izvornog koda;
- `SUMMARY.md` — deskriptivni rezultat po označenom uslovu.

`stop` prije prvog DET prozora dobija status `aborted_before_detection`, a
eksplicitni `abort` status `aborted_by_operator`. Nijedan zapis sa nula DET
prozora ne smije biti označen kao validan fizički rezultat.

Firmware u ovom modu ne šalje kontinuirani sirovi PCM dok detektor radi. Zato
paralelni WAV zahtijeva nezavisan audio snimač. Ako postoji, njegova putanja se
prosljeđuje sa `--wav-path`; alat bilježi SHA-256 na početku i kraju. Bez tog
fajla ne smije se tvrditi da je sirovi WAV snimljen.

Operatorov `condition` počinje kao `unconfirmed` i nikada se ne popunjava iz
firmware DET/state/event zapisa. Samo prozori poslije eksplicitne `condition`
komande, sa validnim firmware protokolom, ulaze u metrike i validan rezultat.

## 7. Metrike i pošteno tumačenje

Za normalni dio prijaviti trajanje, broj odluka, alarmne prozore i lažne alarme
na sat. Za svaki unaprijed definisan događaj prijaviti broj ponavljanja, broj
uhvaćenih događaja, prvi alarm, kašnjenje, uzastopne prozore, score/prag i
oporavak. Granice uslova su host oznake; 10-sekundni prozor na granici može
sadržati oba stanja i mora ostati označen kao prelaz u naknadnoj analizi.

Jedan ventilator dokazuje samo funkcionalnost prototipa u toj postavci, ne
generalizaciju na nove ventilatore. Za jaču tvrdnju potrebni su različiti fanovi,
nezavisne sesije, unaprijed zaključani uslovi i rezultati bez naknadnog
podešavanja modela ili praga na tim ishodima.
