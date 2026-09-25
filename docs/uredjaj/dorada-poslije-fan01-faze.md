# Dorada poslije FAN01: zapisi po fazama

Šest zapisa pisanih 16–20.08.2026, redom kako su faze rađene, spojeni u
jedan fajl bez izmjene sadržaja. Sažetak svih faza, novi tok sistema i
završna odluka su u [dorada-poslije-fan01.md](dorada-poslije-fan01.md).

- Faza 1: K1 fail-closed ugovor (16.08.)
- Faza 2: više sesija u jednom runu (16.08.)
- Faza 3: research telemetrija 96 + 5×96 (20.08.)
- Faza 4: commissioning iz normalnog rada i PC laboratorija (20.08.)
- Faze 5 i 6: commissioning na uređaju i `OBSERVATION_HOLD` (20.08.)
- Faze 7 i 8: audio liveness i verzionisani NVS profil (20.08.)

---

## Faza 1: K1 fail-closed ugovor (16.08.)

**Datum:** 16.08.2026.  
**Commissioning politika:** `asd-commissioning-policy-v1.0.0`.  
**Novi live UART:** `asd-quality-v1.4.0`.  
**Novi host artefakti:** `physical-fan-v1.7.0`.

### Šta je promijenjeno

- Jedini PC numerički izvor ostaje
  `pc/config/asd_commissioning_policy_v1.json`: `loo_cv <= 0,6` prolazi.
- Firmware kopiju istog verzionisanog pravila sprovodi čisti, host-testabilni
  `asd_calibration_quality.c/.h`; parity test poredi njen prag i policy ID sa
  JSON zapisom.
- K1 se primjenjuje nad istom vrijednošću `loo_cv` zaokruženom na šest decimala
  koja ulazi u `CAL_SUMMARY`. Time binary32 ULP na samoj granici ne može dati
  različitu odluku na uređaju i hostu.
- `psd_live.c` izvršava K1 odmah poslije `CAL_SUMMARY`. Pad emituje postojeći
  terminalni `STATE`/`FLOW_STOPPED` par sa razlogom
  `UNSTABLE_CALIBRATION` i vraća se prije `ADAPTTHR`,
  `CALIBRATION_ACCEPTED` i DET petlje.
- Host parser nezavisno potvrđuje da je primljeni `loo_cv` zaista iznad K1
  granice. Takav kraj je validan protokol sa odbijenom kalibracijom, ali nikad
  rezultat podoban za metrike. `ADAPTTHR` ili `CALIBRATION_ACCEPTED` poslije
  pada K1 tretiraju se kao nevalidna firmware telemetrija.

### Kompatibilnost starih artefakata

Novi live capture zahtijeva `asd-quality-v1.4.0` i piše
`physical-fan-v1.7.0`. Stari UART nije tiho prihvaćen kao novi live ugovor.

Offline `recompute` namjerno nastavlja čitati postojeće
`physical-fan-v1.6.0` run direktorijume nastale uz `asd-quality-v1.3.0`.
Čitanje koristi sačuvani `firmware_protocol_state` i centralnu K1 politiku;
originalni `SUMMARY.md`, `provenance.json`, CSV i UART zapisi se ne mijenjaju.
Korekcija smije nastati samo kao novi sidecar.

Stvarni istorijski `cold-start-04` zato ostaje netaknut, a read-only
rekomputacija ga ispravno klasifikuje kao
`calibration_rejected:loo_cv_above_max` i `Validan fizički rezultat: NE`.

### Granica dokaza

Host-C testovi, literalni UART replay i ESP-IDF build dokazuju implementaciju i
integraciju bez hardvera. Tek flash i stvarni UART replay potvrđuju ponašanje
konkretne pločice; build sam po sebi nije runtime dokaz.

---

## Faza 2: više sesija u jednom runu (16.08.)

**Datum:** 16.08.2026.  
**Implementacioni status:** završeno u kodu i PC replay testovima.  
**Hardverski status:** nije ponovo flashovano niti provjereno na ventilatoru;
to je namjerno ostavljeno za naredni, kraći fizički prolaz.

### 1. Zašto je dorada bila potrebna

Host je ranije praktično tretirao cijeli proces kao jednu firmware sesiju.
Poslije urednog K1 pada (`loo_cv > 0,6`) završio bi capture ili bi naredni
`WAIT` poredio sa brojačem prethodne sesije. Time nova kalibracija u istom host
runu nije bila pouzdano auditabilna. Isto tako, firmware-local `DET window=1`
nije bilo moguće jednoznačno razlikovati od `window=1` naredne sesije.

Faza 2 uvodi eksplicitan ugovor: PC proces je **run**, a svaki par `SESSION
STARTED ... SESSION ENDED` je zasebna **firmware sesija**.

### 2. Razdvojeno stanje

`pc/tools/physical_fan_experiment.py` sada ima dva opsega u istom strogo
provjeravanom trackeru:

| Run-scope, nikad se ne resetuje na `SESSION STARTED` | Session-scope, resetuje se |
|---|---|
| boot handshake | WAIT/CAL/CAL_SUMMARY/DET brojači |
| `run_quality_counts` i `run_det_records` | `wait_ok_count`, `cal_summary` |
| broj otvorenih/zatvorenih sesija | ADAPTTHR/PRESENCE/TEMPORAL i pragovi |
| `session_history` | K1 acceptance/rejection parovi |
| COM i provenance u artefaktu | DET window, alarm total i temporalno stanje |
| prethodno zatvoreni audit zapisi | terminal drain i lokalni state-chain anchor |

Na početku svake sesije state-chain se ponovo otvara iz `NO_MACHINE` i traži se
tačno jedan novi `BOOT_FAIL_CLOSED` neposredno poslije `SESSION STARTED`.
Firmware ga emituje unutar svakog `run_session()`. Host čuva zbirni run-scope
dokaz i broj BOOT zapisa, ali resetuje session-local `session_boot_seen`.
Operatorov condition se nezavisno vraća na `unconfirmed`; ne može se naslijediti
iz prethodne sesije.

K1-odbijena sesija poslije odgovarajućih `STATE`, `FLOW_STOPPED` i `SESSION
ENDED` ostaje u `session_history` kao validan `calibration_rejected` audit bez
DET metrika. Host zatim nastavlja da čita UART i može prihvatiti novu sesiju.
Bounded terminal drain iz Faze 1 ostaje aktivan: nedostajući `SESSION ENDED`
i dalje završava fail-closed timeoutom.

### 3. Novi artifact contract i CSV identitet

Novi v1.7 artefakt eksplicitno nosi:

```text
protocol_version=physical-fan-v1.7.0
quality_protocol_version=asd-quality-v1.4.0
artifact_contract_version=physical-fan-artifacts-v1.7.0
```

Offline reader radi fail-closed:

- istorijski v1.6 prihvata samo par `physical-fan-v1.6.0` ↔
  `asd-quality-v1.3.0` i dobija kompatibilne podrazumijevane indekse jedine
  sesije;
- v1.7 prihvata samo par v1.7 ↔ v1.4 uz tačan artifact contract token;
- missing, nepoznat ili nepodudaran par/token odbija čitanje.

Session-vezani CSV redovi nose `firmware_session_index`. `detections.csv`
dodatno čuva oba identiteta prozora:

- `window`: firmware-local broj, ponovo kreće od 1 u novoj sesiji;
- `run_det_index`: monotono raste kroz cijeli host run.

`events.csv` takođe veže host condition/note/fazu za trenutni session index;
run događaji prije prve sesije imaju indeks 0.

### 4. Metrike bez miješanja sesija

`provenance.json` i `SUMMARY.md` sada imaju tabelu po firmware sesiji i zbir za
cijeli run:

- protocol status i K1 acceptance;
- raw DET, protocol-valid DET i DET prozori podobni za metrike;
- alarmni prozori, alarm entries i alarmne epizode;
- procenat podobnih prozora proveden u alarmu;
- medijanu latencije od posljednjeg alarmnog prozora do prvog normalnog;
- broj izuzetih transition prozora;
- session i run DET totals i provjeru saglasnosti sa CSV redovima.

Alarmni prozori se namjerno ne predstavljaju kao epizode. Npr. tri uzastopna
alarmna prozora su tri alarmna prozora, ali jedna alarmna epizoda. Prvi DET
poslije nove `condition` komande dobija `transition_window=1` i isključuje se iz
metrika, jer desetosekundni prozor može sadržati oba uslova.

K1-odbijena sesija ostaje u session tabeli, ali ne daje metric rows. Valjan run
može nastati tek iz kasnije prihvaćene, kompletne sesije sa ponovo potvrđenim
operator conditionom.

### 5. Provenance hash opseg

Pored ranijih izvora, hash manifest eksplicitno obuhvata:

```text
firmware/esp32s3_asd/main/asd_temporal.c/.h
firmware/esp32s3_asd/main/asd_cmd.c/.h
pc/config/asd_temporal_policy_v2.json
pc/config/asd_commissioning_policy_v1.json
firmware/esp32s3_asd/main/asd_calibration_quality.c/.h
pc/config/asd_interference_policy_v1.json
firmware/esp32s3_asd/main/asd_interference.c/.h
```

Budući policy/modul je naveden i prije nastanka; hash je `null` dok fajl ne
postoji. Tako odsustvo nije prećutano, a kasnije pojavljivanje automatski ulazi
u audit bez promjene semantike starog artefakta.

### 6. `start_fan_run.py` montažna potvrda

Ispravljena je netačna tvrdnja da `--montaza-potvrdio` ide u `events.csv`.
Wrapper je prosljeđuje kao `--notes`, pa stvarna putanja glasi:

```text
provenance.json -> metadata.operator_notes
```

Konzolni ispis ostaje. Dodan je čisti `build_tool_command()` i test koji
provjerava doslovan prenos potvrde i dokumentovanu putanju.

### 7. Verifikacioni replay

Najvažniji test koristi doslovne UART linije i izvodi cio tok:

1. po jedan `BOOT_FAIL_CLOSED` odmah poslije `SESSION STARTED` u svakoj sesiji;
2. sesija 1: puni `WAIT 1..60`, `CAL 1..10`, K1 pad, terminalni par i
   `SESSION ENDED`;
3. sesija 2: ponovo `WAIT 1..60` (ne 61), `CAL 1..10`, ADAPTTHR, PRESENCE,
   TEMPORAL, acceptance par i tri DET prozora;
4. condition iz prve sesije se ne nasljeđuje: prvi DET druge sesije je
   `unconfirmed`;
5. nova condition prije DET 2 čini DET 2 transition prozorom; DET 3 je prvi
   podoban metric row;
6. `SESSION ENDED`, operator stop i provjera svih CSV/provenance/summary
   brojača.

Targetirani rezultat prije punog suitea:

```text
90 passed in 2.61s
```

Puni regresioni prolaz:

```powershell
.\.venv\Scripts\python.exe -m pytest pc\tests -q
```

```text
328 passed in 9.62s
```

Firmware izvor u Fazi 2 nije mijenjan, pa ESP-IDF rebuild nije ponavljan samo
zbog host/CSV/docs promjene. Firmware build iz Faze 1 ostaje zaseban dokaz; nije
dokaz flasha ni fizičkog runtimea.

Stvarni istorijski `cold-start-04` pročitan je ponovo bez pisanja artefakta:

```text
result_status=calibration_rejected:loo_cv_above_max
protocol_valid=True
metrics_eligible=False
firmware_sessions=1
run_det_records=52
```

Originalni `SUMMARY.md` ostao je na SHA-256
`AF9B3E3E22267FE29CD1F391D688EBC814FA0F6DAE1B4FFD88C163A819F8EC24`;
privremeni verifikacioni sidecar je uklonjen i ne ostaje u run direktoriju.

### 8. Šta ovo još ne dokazuje

Ova faza dokazuje parser, state machine, bounded drain, artifact compatibility,
CSV identitet i izvještavanje na PC-u. Ne dokazuje:

- da je novi firmware flashovan na ESP32-S3;
- da dvije stvarne sesije rade bez USB/serijskog problema;
- da su prag ili razlika papirić/govor/normalan fan poboljšani;
- da su tonalnost i dvostepena odluka završeni.

To pripada narednim fazama i kratkom fizičkom testu nakon softverskih dorada.

---

## Faza 3: research telemetrija 96 + 5×96 (20.08.)

Datum implementacije: 20.08.2026.

Status: **IMPLEMENTIRANO I PC PROVJERENO** za kod i sintetičke artefakte.
ESP-IDF clean research build je pokrenut i stigao do `1230/1519` bez greške,
ali u trenutku zatvaranja ove faze još nije bio završen; zato se build ne vodi
kao PASS dok se ne dobije završni exit code.
Stvarni sadržaj sa ventilatora ostaje **PENDING_PHYSICAL_CAPTURE**. Ova faza ne
tvrdi da su papirić i govor već razdvojeni; ona prvi put trajno čuva podatke
potrebne da se to pošteno ispita.

### 1. Zaključana granica

Kanonski PSD model nije promijenjen:

- `ASD_PSD_N_FFT=8192`, `ASD_PSD_HOP=4096`, `ASD_PSD_BANDS=96` ostaju isti;
- `asd_psd_stream_reset/push_hop/finish` ostaju produkcijski API;
- stari `asd_psd_stream_finish(out_feature)` i research finish daju
  bit-identičan finalni 96-dim vektor;
- nisu mijenjani model header, norm mean/std, precision, centar ni score;
- u DET petlji nema `asd_dump_pcm_block()` niti kontinuiranog PCM-a.

Research je zaseban, opcion build sloj. Uključuje se samo sa:

```powershell
$env:ASD_PSD_LIVE='1'
$env:ASD_RESEARCH_TELEMETRY='1'
idf.py reconfigure build
```

Bez `ASD_RESEARCH_TELEMETRY` firmware koristi stari capture/finish put i ne
emituje nove zapise.

### 2. Sidecar DSP

U `psd_features_c.h/.c` dodani su:

```c
void asd_psd_stream_reset_sidecar(void);
int asd_psd_stream_finish_sidecar(float *out_feature,
                                  asd_psd_sidecar_t *out_sidecar);
```

Sidecar drži samo `5×96` band akumulatora u statičkoj memoriji, ne PCM bafer i
ne 480 floatova na dubokom stacku. Tačno 38 preklapajućih Welch segmenata ide u
uzastopne grupe:

```text
8 + 8 + 8 + 7 + 7 = 38
```

To nisu pet nezavisnih dvosekundnih klipova. Susjedni Welch segmenti dijele
4.096 uzoraka zbog 50% preklapanja.

Sidecar sabiranje je namjerno u odvojenoj petlji poslije kanonskog `power_sum`
sabiranja. Tako ne mijenja redoslijed binary32 operacija finalnog featurea.
Podsegment i ekvivalentni batch slice se zbog drugačijeg redoslijeda band/bin
sabiranja slažu unutar `5e-5`; finalni research/canonical feature se slaže bit za
bit.

### 3. Firmware wire ugovor

Novi, odvojeni schema token je:

```text
asd-research-v1.0.0
```

Core ostaje `asd-quality-v1.4.0`, host/artifact ostaje
`physical-fan-v1.7.0`; nema lažnog bumpa kanonskog modela. Za svaki validni
CAL/DET prozor firmware emituje:

1. jedan `FEATURE96` sa session/phase/window ključem, monotonic
   `window_start_ms/window_end_ms`, scoreom, nivoom, `quality=OK`,
   `tonalness_proxy`, `dims=96`, checksumom i finalnim vektorom;
2. pet `SUBSEG96` zapisa sa istim ključem, `group=1..5`, pripadajućim brojem
   segmenata, `dims=96`, checksumom i vektorom.

Checksum je FNV-1a preko 96 little-endian binary32 vrijednosti, po istom obrascu
koji `mic_test.c` koristi za framed PCM. Decimalni zapis koristi devet značajnih
cifara, dovoljno za binary32 round-trip.

DET redoslijed je namjerno:

```text
QUALITY phase=DET ...
DET ...
FEATURE96 ...
SUBSEG96 group=1 ...
...
SUBSEG96 group=5 ...
```

Zato debug zapis ne presijeca neposredni `QUALITY DET -> DET` core ugovor.

### 4. Host strict tracker

`physical_fan_experiment.py` parsira research zapise odvojeno od core firmware
state mašine. Provjerava:

- tačan research schema token i tačan skup polja;
- `session>=1`, `window>=1`, fazu CAL/DET i `dims=96`;
- tačno 96 konačnih vrijednosti i checksum;
- `group=1..5` i broj segmenata `8/8/8/7/7`;
- `end_ms>=start_ms` i monotonic prozore;
- tačno jedan FEATURE i pet različitih SUBSEG zapisa po očekivanom validnom
  QUALITY CAL/DET prozoru;
- slaganje nivoa/tonalnosti sa QUALITY i DET scorea sa DET zapisom;
- odsustvo research zapisa između QUALITY DET i pripadajućeg DET reda.

Sa `--research-telemetry-required`, missing, duplicate, malformed, nonfinite,
checksum, shape ili korelacijska greška daje `invalid_research_telemetry`. Bez
tog flag-a core fizički rezultat ostaje odvojen: eventualni nepotpun research
sidecar je označen nevalidnim, ali ne izmišlja kvar fizičkog protokola.

Wrapper `start_fan_run.py` prosljeđuje isti flag. Ako postojeći build nema
`-DASD_RESEARCH_TELEMETRY`, required run se odbija prije otvaranja COM porta.

### 5. Artefakt

Host atomski zapisuje `window_features.npz`, zatim
`window_features.manifest.json`. NPZ sadrži:

| Array | Shape | Dtype |
|---|---:|---|
| `feature96` | `(N, 96)` | `float32` |
| `subseg96` | `(N, 5, 96)` | `float32` |
| `subseg_welch_segments` | `(N, 5)` | `int32` |
| `firmware_session_index` | `(N,)` | `int32` |
| `phase` | `(N,)` | Unicode CAL/DET |
| `window` | `(N,)` | `int32` |
| `window_start_ms`, `window_end_ms` | `(N,)` | `uint64` |
| `score`, `level_dbfs`, `tonalness_proxy` | `(N,)` | `float32` |

Manifest zapisuje shape/dtype svakog arraya i SHA-256 stvarnog NPZ fajla,
očekivani i kompletni broj prozora, broj FEATURE/SUBSEG zapisa, strict greške i
`pcm_per_det=false`.

`--wav-path` je samo veza ka fajlu nezavisnog rekordera. Manifest doslovno piše
`linked_external_file_not_recorded_by_host` i početni/završni SHA-256. Kada putanja
nije data, `external_wav=null`; host ne tvrdi da audio postoji.

### 6. Verifikacija 20.08.2026.

Ciljani testovi:

```text
.venv\Scripts\python.exe -m pytest \
  pc/tests/test_physical_fan_experiment.py \
  pc/tests/test_psd_features_c.py \
  pc/tests/test_start_fan_run.py -q

105 passed
```

Testovi eksplicitno pokrivaju bit-identičan finalni feature, `38 -> 8/8/8/7/7`,
svih `5×96` konačnih vrijednosti, batch-sidecar toleranciju, strict parser,
missing/duplicate/malformed odbijanja, NPZ shape/dtype/hash, eksterni WAV link,
DET redoslijed, odsustvo PCM poziva i sintetički UART budžet. Generisani paket
ima više od `10x` prosječne rezerve na 115200 baud i burst kraći od jedne
sekunde po desetosekundnom prozoru.

### 7. Šta ostaje za naredni stvarni test

- flashovati research build i potvrditi stvarne FEATURE/SUBSEG linije na COM-u;
- snimiti mali broj dobro označenih normal/govor/papirić prozora;
- provjeriti stvarni UART burst i `dropped_delta=0` na uređaju;
- po želji paralelno snimati eksterni WAV i proslijediti njegovu putanju;
- tek iz novih NPZ podataka analizirati koje trake i podsegmenti razdvajaju govor
  od trajne promjene ventilatora.

Nije potrebno ponavljati mnogo puta prije ove provjere. Jedan kratak, uredno
označen research run je dovoljan da prvo potvrdimo da instrumentacija radi i da
li signal za razdvajanje uopšte postoji.

---

## Faza 4: commissioning iz normalnog rada i PC laboratorija (20.08.)

Datum: 2026-08-20

Status: `DEVELOPMENT/PENDING_PHYSICAL_VALIDATION`

Opseg: isključivo novi PC razvojni alati, sintetički testovi i ovaj dokument

### Ishod

Implementiran je razvojni tok koji razdvaja učenje centra, izvođenje pragova i
vremenski kasniju provjeru. Nijedan broj iz ranijeg fizičkog testa nije ugrađen
kao podrazumijevani prag. Target anomalija ne može učestvovati u fitu, izboru
feature-a ili izvođenju pragova; može se otvoriti samo kao readout nakon provjere
zamrznute politike.

Ova faza ne mijenja firmware, fizički host, kanonski evaluator, postojeće
rezultate ni deployment konfiguraciju. Deployment konfiguracija se namjerno ne
generiše dok novi normal-only i skraćeni fizički test ne daju nezavisnu potvrdu.

### Granica prema live firmwareu

Izlaz ove PC laboratorije nije ulaz u isti fizički run. DEVELOPMENT firmware
nema `SETTHR` komandu i ne učitava laboratorijski profil iz NVS-a. To je
namjerna zaštita od post-hoc podešavanja: live GUIDED25 run koristi unaprijed
određeni `psd_shape` p99/p75 pragovni par, a laboratorija samo procjenjuje
alternativne kandidate iz sačuvanog research sidecara.

Ako normal-only DERIVE, nezavisni VERIFY i kasniji frozen readout podrže drugi
kandidat, on se prenosi tek kroz verzionisanu firmware/policy izmjenu i novi
preregistrovani fizički retest. Trenutni run se nikad ne prepravlja njegovim
rezultatom.

### Novi fajlovi

- `pc/tools/evaluate_fan_noise_candidates.py` — normal-only feature laboratorija,
  candidate manifest, izolovani cache, model bundle i zaključani target readout;
- `pc/tools/derive_commissioning_policy.py` — hronološko izvođenje i izbor
  apsolutnih `T_enter`/`T_exit` pragova;
- `pc/tests/test_fan_noise_development.py` — sintetički fixture testovi granica
  podataka, faza, cache-a i frozen-policy readout-a;
- `docs/uredjaj/dorada-poslije-fan01-faze.md` — ovaj zapis.

### Zaključani tok podataka

Normalni target NPZ mora sadržati tri nepomiješana bloka ovim redom:

```text
CENTER_LEARNING -> COMMISSION_DERIVE -> COMMISSION_VERIFY
```

- `CENTER_LEARNING` mora imati 10–20 prozora i služi samo za lokalni centar i
  lokalnu referencu tonalnosti;
- `COMMISSION_DERIVE` izvodi kandidatske pragove i bira razvojnu politiku;
- `COMMISSION_VERIFY` se ne koristi za izbor. Tek nakon zamrzavanja politike
  daje holdout episode metrike;
- prozori moraju biti vremenski rastući, bez preklapanja i bez vraćanja u raniju
  fazu;
- svaki commissioning red mora biti `label=0` i `normal_only=true`;
- nema randomizacije i nema bootstrap-a pojedinačnih/preklapajućih prozora.

Ako VERIFY utiče na izbor, alat više ne smatra taj dio verifikacijom. Test
eksplicitno mijenja sve VERIFY score-ove i potvrđuje da selected policy i
candidate tabela ostaju bitno isti, dok se samo VERIFY izvještaj promijeni.

### Ulazni ugovor za feature laboratoriju

Svaka kohorta je `.npz` sa sljedećim poljima:

| Polje | Oblik | Namjena |
|---|---:|---|
| `cohort_role` | skalar string | `source_normal`, `target_normal` ili `target_anomaly` |
| `frequency_hz` | `(F,)` | strogo rastuća frekvencijska osa |
| `power` | `(N,F)` | nenegativni PSD/power vektori |
| `subsegment_power` | `(N,5,F)` | tačno pet podsegmenata po prozoru |
| `tonalness_proxy` | `(N,)` | peak-prominence proxy, ne speech classifier |
| `label` | `(N,)` | nula za normalne, jedan za anomaly readout |
| `phase` | `(N,)` | obavezne commissioning faze za `target_normal` |
| `start_s`, `end_s` | `(N,)` | granice prozora bez preklapanja |
| `window_id`, `fan_id`, `session_id` | `(N,)` | auditabilni identitet prozora |

Za stvarni istraživački build `power` treba dobiti iz sačuvanih 96 PSD
vrijednosti ili iz bit-identičnog PSD sidecar toka, a `subsegment_power` iz pet
sinhronizovanih dijelova istog prozora. Ovaj alat ne uvodi kontinuirani PCM
dump i ne rješava firmware prikupljanje podataka; to pripada narednoj fazi.

### Feature kandidati

Kompletan manifest se zapisuje prije otvaranja kohorte. Manifest unaprijed
zaključava koeficijente i zaseban provenance ID za svaki kandidat:

1. `baseline_hard_log96` — 96 tvrdih nepreklapajućih log-traka;
2. `triangular_overlap_log96` — 96 preklapajućih trougaonih log-traka;
3. `smoothed_hard_log96` — fiksni blagi kernel nad power osom pa baseline trake;
4. `clipped_standardized_residual_c3` — coordinate-wise ograničen
   standardizovani rezidual prije pune precision kvadratne forme;
5. `huber_whitened_residual_d1p5` — Huber gubitak u izbijeljenom prostoru;
6. `subsegment_stability_gate` — robustan spread pet podsegmenata, samo HOLD
   gate, nikada zamjena za glavni detector.

Za svaki glavni kandidat model se fituje iz `source_normal`, uz lokalni centar
iz `target_normal:CENTER_LEARNING`. Svaki kandidat nakon toga dobija vlastite
normal-only pragove. Kandidati iz ranijih negativnih eksperimenata su navedeni
u manifestu kao isključeni i nisu ponovo pokretani.

Tonalnost se koristi relativno:

```text
tonalness_reference = median(CENTER_LEARNING.tonalness_proxy)
tonalness_delta = tonalness_proxy - tonalness_reference
```

To nije klasifikator razgovora. Kasnija dvostepena logika smije ga koristiti
samo kao jedan signal za `HOLD/AMBIENT_UNCERTAIN`.

### Kandidati za prag i način izbora

`derive_commissioning_policy.py` unaprijed zaključava četiri porodice:

- visoki empirijski percentil normale;
- `median + k*MAD`;
- percentil maksimuma po fiksnom bloku od šest prozora;
- finite-sample conformalni gornji kvantil kada DERIVE ima najmanje 20 prozora.

`T_enter` i `T_exit` računaju se odvojeno kao apsolutni pragovi. Kandidat se
odbacuje ako ne zadovoljava `0 < T_exit < T_enter`. Nema izvedenog fiksnog
omjera između pragova.

Izbor je leksikografski i koristi cijeli hronološki DERIVE niz:

1. broj alarmnih epizoda;
2. ukupno vrijeme u alarmu;
3. chatter/re-entry;
4. najduži normalni niz iznad enter praga;
5. raspon broja epizoda kroz vremenske blokove;
6. standardnu devijaciju vremena u alarmu kroz blokove;
7. stabilni candidate ID samo kao konačni tie-break.

VERIFY izvještava iste vremenske/episode metrike sa već zamrznutim pragovima.
Window rate se ne koristi kao zamjena za broj epizoda.

### Target-anomaly zaštita

Granica je namjerno tehnička, a ne samo dokumentaciona:

- normal preparation CLI nema argument za target anomaliju;
- policy derivation CLI nema argument za target anomaliju;
- svaki normalni red sa anomaly labelom ili bez `normal_only=true` prekida fit;
- `readout-target` prvo provjerava feature manifest, status zamrznute politike,
  manifest/model ID paritet i `0 < T_exit < T_enter`;
- tek zatim audit prelazi u `target_readout` i dozvoljava otvaranje target NPZ-a;
- readout ne refituje model, ne mijenja prag i vraća
  `selected_policy_unchanged`;
- svi izlazi nose `developmental=true` i
  `target_anomalies_used_for_fit=false`.

Source anomalije i unaprijed definisani sintetički pomaci ostaju dozvoljeni samo
kao razvojne sensitivity kontrole. Trenutna CLI verzija ih ne koristi za izbor;
cilj je spriječiti da sensitivity rezultat neprimjetno postane tuning signal.

### Cache, manifest i provenance

Verzije novih ugovora su namjerno razvojne i ne mijenjaju postojeći wire ili
physical-fan artifact format:

| Ugovor | Verzija |
|---|---|
| feature protokol | `fan-noise-candidates-v1.0.0-development` |
| feature manifest | `fan-noise-feature-manifest-v1.0.0` |
| normal model bundle | `fan-noise-normal-model-v1.0.0-development` |
| score input | `fan-normal-candidate-scores-v1.0.0` |
| commissioning protokol | `commissioning-development-v1.0.0` |
| frozen rezultat | `asd-commissioning-development-result-v1.0.0` |
| target readout | `fan-target-readout-v1.0.0-development` |

Cache putanja uključuje protocol ID, manifest ID, candidate ID, cohort role,
SHA-256 kohorte, tip proizvoda i model ID. Zbog toga feature cache ne može biti
zamijenjen score cache-om, različite kohorte se ne miješaju, a score drugog
normalnog modela se ne koristi kao važeći pogodak. Metadata se poredi u cjelini;
legacy/mixed cache se ne otvara.

Provenance bilježi hash ulaza, hash razvojnih alata, manifest/model ID, Python i
NumPy verziju, Git HEAD/dirty status i audit broja target readova. Stari SUMMARY
i postojeći fizički artefakti se ne prepisuju.

### Pokretanje

Priprema normalnih feature-a i score bundle-a:

```powershell
.\.venv\Scripts\python.exe pc\tools\evaluate_fan_noise_candidates.py prepare-normal `
  --source-normal <source-normal.npz> `
  --target-normal <target-normal.npz> `
  --output-dir results\commissioning_development\run-001
```

Izvođenje i zamrzavanje politike:

```powershell
.\.venv\Scripts\python.exe pc\tools\derive_commissioning_policy.py `
  --input results\commissioning_development\run-001\normal_candidate_scores.json `
  --output-dir results\commissioning_development\run-001\policy
```

Target readout tek poslije prethodna dva koraka:

```powershell
.\.venv\Scripts\python.exe pc\tools\evaluate_fan_noise_candidates.py readout-target `
  --feature-manifest results\commissioning_development\run-001\feature_candidate_manifest.json `
  --frozen-policy results\commissioning_development\run-001\policy\frozen_commissioning_policy.json `
  --model-bundle results\commissioning_development\run-001\normal_model_bundle.npz `
  --target-anomaly <target-anomaly.npz> `
  --output-dir results\commissioning_development\run-001\readout
```

### Verifikacija ove faze

Pokrenuto 2026-08-20:

```text
.venv\Scripts\python.exe -m pytest -q pc/tests/test_fan_noise_development.py
5 passed
```

Testovi potvrđuju:

- hronološke, nepreklapajuće CENTER/DERIVE/VERIFY indekse;
- odbijanje anomaly reda u normal-only fitu;
- sva četiri threshold kandidata kada je uzorak dovoljan;
- odvojene pozitivne enter/exit pragove;
- selection nezavisnost od VERIFY vrijednosti;
- kompletan sintetički tok za svih pet glavnih feature score kandidata;
- odvojene feature/score cache proizvode;
- zapis feature i threshold manifesta prije prvog candidate evaluation koraka;
- odbijanje target čitanja prije frozen policy;
- nepromijenjenu selected policy u kasnijem target readout-u.

CLI import/help i Python sintaksa oba nova alata su dodatno provjereni.

### Šta ostaje PENDING

- napraviti normal-only snimanje sa stvarnim ventilatorom i hronološkim blokovima;
- odrediti trajanje DERIVE/VERIFY iz realne varijabilnosti, uz skraćeni fizički
  protokol iz glavnog plana;
- procijeniti razgovor/korake kao unaprijed označene normalne interference
  blokove, bez pretvaranja tonalnosti u speech classifier;
- tek nakon zamrzavanja pogledati papiric readout i prijaviti broj epizoda,
  vrijeme alarma, kašnjenje i ponašanje poslije prestanka razgovora;
- izabrati deployment politiku tek ako nezavisni normalni holdout i fizički
  readout podrže isti kandidat;
- zasebno u narednoj fazi povezati odabranu politiku sa firmware stanjem
  `HOLD/AMBIENT_UNCERTAIN` i verzionisanim NVS profilom.

Do završetka tih provjera nijedan **izabrani izlaz laboratorije** nije finalni
firmware default. Live p99/p75 ostaje konzervativni DEVELOPMENT kandidat za
prikupljanje tog dokaza, ne fizički potvrđena proizvodna politika.

---

## Faze 5 i 6: commissioning na uređaju i `OBSERVATION_HOLD` (20.08.)

Datum implementacije: 2026-08-20  
Status softvera: **implementirano i ciljano host-testirano**  
Status numeričke politike: **DEVELOPMENT / PENDING fizička normal-only validacija**  
Status ESP32 builda i fizičkog testa: **nije potvrđeno u ovoj fazi**

### 1. Šta je riješeno

Uveden je jasan runtime tok:

`SETTLE → CENTER_LEARNING → COMMISSION_DERIVE → COMMISSION_VERIFY → MONITORING`

Time su razdvojene tri ranije pomiješane odgovornosti:

1. centar od 96 PSD obilježja uči se samo iz `CENTER_LEARNING` prozora;
2. apsolutni pragovi `threshold_enter` i `threshold_exit` izvode se iz vremenski kasnijeg normal-only `COMMISSION_DERIVE` bloka;
3. `COMMISSION_VERIFY` samo provjerava već zamrznut profil i ne smije mijenjati ni centar ni pragove.

Svaka faza ima timeout i fail-closed završetak (`REJECTED` ili `ABORTED`). Profil postaje važeći tek poslije uspješnog VERIFY bloka. K1 je poseban razlog odbijanja kalibracije, nije UART/protocol greška.

### 2. Čisti moduli i ugovori

#### Runtime profil

Datoteke:

- `firmware/esp32s3_asd/main/asd_profile_runtime.h`
- `firmware/esp32s3_asd/main/asd_profile_runtime.c`

Profil sadrži:

- `center[96]`;
- referentni nivo i `tonalness_reference`;
- odvojene apsolutne `threshold_enter` i `threshold_exit`;
- broj CENTER, DERIVE i VERIFY prozora;
- policy version/ID i DEVELOPMENT oznaku.

Validacija zahtijeva `0 < threshold_exit < threshold_enter`. Centar i pragovi se mogu zamrznuti samo jednom. Nema implicitnog `0,7 × T_enter`, niti VERIFY smije „popraviti” profil poslije lošeg rezultata.

Schema ID je `asd-runtime-profile-v1.0.0-development`. Profil iz ovog builda se namjerno ne čuva u NVS-u dok numerička politika ne prođe fizičku normal-only validaciju.

#### Commissioning state machine

Datoteke:

- `firmware/esp32s3_asd/main/asd_commissioning.h`
- `firmware/esp32s3_asd/main/asd_commissioning.c`
- `pc/config/asd_commissioning_runtime_v1.json`

`asd_commission_observe_settle()` namjerno nema Mahalanobis score argument. SETTLE smije koristiti samo kvalitet zvuka, nivo, tonalnost, drift obilježja i dropped-sample promjenu. Score nema smisla prije nego što postoji centar.

API zatim zahtijeva eksplicitne pozive za CENTER, commit centra/K1, DERIVE, zamrzavanje pragova i VERIFY. Pogrešan redoslijed, loš kvalitet, timeout, K1, operator abort ili nevažeći profil završavaju tok fail-closed.

Policy ID je `asd-commissioning-policy-v1.0.0-development` / `0x434d5631`.
Za naredni unaprijed registrovani normal-only prolaz zaključano je 120 DERIVE
prozora (20 min) i 60 vremenski kasnijih VERIFY prozora (10 min). To određuje
trajanje i hronologiju, ne bira prag po anomalijama; numeričke granice i dalje
nisu proizvodno potvrđene.

#### Temporalna odluka

Datoteke:

- `firmware/esp32s3_asd/main/asd_temporal.h`
- `firmware/esp32s3_asd/main/asd_temporal.c`
- `pc/config/asd_temporal_policy_v2.json`

Runtime API sada prima oba apsolutna praga:

```c
asd_temporal_update(detector, score, threshold_enter, threshold_exit);
```

Poziv se odbija ako pragovi nisu konačni ili ako ne važi `0 < exit < enter`. Stara scale polja ostavljena su samo kao legacy provenance za postojeći wire/host ugovor i više nisu autoritet odluke. `TEMPORAL` zapis sada dodatno objavljuje `threshold_mode=absolute_profile`, `threshold_enter` i `threshold_exit`.

### 3. Razgovor i spoljašnja smetnja: HOLD, ne lažna dijagnoza

Datoteke:

- `firmware/esp32s3_asd/main/asd_interference.h`
- `firmware/esp32s3_asd/main/asd_interference.c`
- `pc/config/asd_interference_policy_v1.json`

Javno stanje je isključivo `OBSERVATION_HOLD`. Naziv `AMBIENT_NOISE` se ne emituje jer jedan mikrofon ne može pouzdano dokazati da je uzrok baš razgovor ili spoljašnja buka.

Semantika HOLD-a:

- suspenduje izgradnju novog alarmnog niza;
- ne proglašava stanje normalnim;
- ne briše već aktivan alarm;
- ne mijenja centar, pragove ni profil;
- po povratku pouzdanog high score-a alarmni niz se gradi iznova;
- dug HOLD emituje upozorenje, ali i dalje nije normalno stanje.

Čisti `asd_interference` modul podržava relativnu promjenu tonalnosti i nestabilnost podsegmenata. Međutim, policy je sada `enabled=false`: fizičke granice nisu izmišljene iz fan01 target anomalija. U minimalnoj firmware integraciji tonalnost je proslijeđena relativno prema profilu, dok je podsegment instability još `0.0` dok Faza 3/4 podaci ne omoguće normal-only zamrzavanje metrike i granice.

### 4. Minimalna firmware i UI integracija

Izmijenjene su:

- `firmware/esp32s3_asd/main/psd_live.c` i `CMakeLists.txt`;
- `firmware/esp32s3_asd/main/audio_quality_state.h/.c`;
- `firmware/esp32s3_asd/main/asd_events.h/.c`;
- `firmware/esp32s3_asd/main/asd_operator.h/.c`.

`psd_live` sada stvarno izvodi pet commissioning faza. Legacy WAIT/QUALITY, CAL/DET i Faza 3 research telemetry ostavljeni su radi postojećeg host ugovora. Novi sidecar zapisi su:

- `COMMISSION ...` — faza, redni broj, rezultat i metrike;
- `PROFILE ...` — schema/policy, brojevi prozora, reference i apsolutni pragovi.

LED/UI model ima posebnu HOLD prezentaciju (spor puls zelene, crvena ugašena dok alarm već nije aktivan). Dugi pritisak i dalje znači eksplicitnu rekalibraciju; HOLD sam nikada ne briše profil.

Za host je dodat `pc/asd/runtime_protocol.py` i integrisan u stvarni
`physical_fan_experiment.py` v1.8/q1.5 state machine. Parser strogo provjerava
tačna `COMMISSION`/`PROFILE` polja, finite brojeve, schema/policy ID, dinamički
SETTLE i hronološki redoslijed do `MONITORING`. Stari v1.6/v1.7 artefakti
ostaju podržani samo kroz eksplicitni offline read/recompute ugovor; nisu
prećutni fallback za novi live q1.5 tok.

### 5. Verifikacija izvršena u ovoj fazi

Pokrenuto:

```text
.venv\Scripts\python.exe -m pytest -q \
  pc/tests/test_runtime_protocol.py \
  pc/tests/test_asd_commissioning_c.py \
  pc/tests/test_asd_interference_c.py \
  pc/tests/test_asd_temporal_c.py \
  pc/tests/test_asd_events_c.py \
  pc/tests/test_asd_operator_c.py
```

Rezultat:

```text
203 passed in 4.83s
```

Testovi pokrivaju:

- pun commissioning tok i nedozvoljene prelaze;
- timeout, quality reject, K1, abort i nevažeće pragove;
- nemjenjivost centra/pragova tokom VERIFY;
- eksplicitni enter/exit temporalni ugovor;
- HOLD suspend, nastavak high score-a poslije HOLD-a, očuvanje aktivnog alarma i long-hold warning;
- literalni novi UART replay, strogi parser i ignorisanje starih/core linija;
- zabranu javnog `AMBIENT_NOISE` naziva.

### 6. Šta namjerno još nije proglašeno završenim

Sljedeće ostaje **PENDING**, a ne skriveno kao „gotovo”:

1. ESP-IDF full build i cijeli PC test suite treba izvršiti u završnom root checkpointu.
2. Fizički ventilator još nije testirao novi commissioning/HOLD runtime.
3. SETTLE, DERIVE/VERIFY i interference brojevi nisu proizvodno zamrznuti.
4. Interference policy ostaje isključen dok normal-only podaci ne odrede granice tonalnosti i podsegment nestabilnosti.
5. NVS profil, CRC i model fingerprint su naknadno implementirani u Fazi 8;
   fizički power-loss recovery i hardverske LED/taster provjere ostaju otvoreni.
6. Live v1.8/q1.5 host koristi jedan strogi commissioning/profile autoritet;
   istorijski v1.6/v1.7 ugovor ostaje samo offline kompatibilnost artefakata.

Target anomalije (papirić/razgovor) nisu korištene za fit centra ili pragova. Kada se uradi kraći naredni fizički test, one smiju služiti samo za readout nad unaprijed zamrznutom normal-only politikom.

### 7. Očekivani efekat na problem fan01

Ova dorada sama po sebi ne obećava veću numeričku separaciju dok se ne prikupe novi fizički podaci. Ona uklanja glavne arhitektonske uzroke pogrešne odluke:

- kratki centar više ne određuje i prag;
- razgovor više ne resetuje odstupanje na „normalno”;
- trajno odstupanje poslije razgovora ponovo mora izgraditi alarm;
- enter i exit su odvojeni i auditabilni;
- VERIFY mjeri normalne alarmne epizode na kasnijem vremenskom bloku bez post-hoc podešavanja.

Tek poslije tog zamrznutog normal-only commissioning toka ima smisla porediti koliko su papirić, razgovor i normalan ventilator zaista razdvojeni.

---

## Faze 7 i 8: audio liveness i verzionisani NVS profil (20.08.)

**Datum:** 20.08.2026.  
**Status koda/builda:** implementirano i host-testirano; `ASD_PSD_LIVE` build PASS.  
**Fizički status:** prekid I2S-a, restart i nestanak napajanja nisu još testirani
na pločici i ostaju `PENDING_HARDWARE_RUNTIME`.

### Faza 7: šta je promijenjeno

- `audio_read_exact(dst, n, timeout_ms, &got)` vraća `esp_err_t` i stvarni count.
- Jedan FreeRTOS deadline važi za cijelo čitanje; parcijalni ring-buffer komad
  ga ne pokreće iznova (`vTaskSetTimeOutState`/`xTaskCheckForTimeOut`).
- I2S capture i consumer čekaju konačno; production audio put nema
  `portMAX_DELAY`.
- Liveness snapshot nosi heartbeat, posljednju grešku, uspješne readove i
  timeout/error brojače. Niz nula nije timeout: sadržaj PCM-a ne odlučuje da li
  je read uspio.
- PSD `SETTLE`, `WAIT`, `CAL`, `DERIVE`, `VERIFY` i `DET` koriste bounded API.
  `AUDIO_TIMEOUT` i `AUDIO_READ_ERROR` završavaju fail-closed u `SENSOR_ERROR`.
- Zbog novih javnih wire razloga novi live par je
  `physical-fan-v1.8.0` ↔ `asd-quality-v1.5.0`, uz
  `physical-fan-artifacts-v1.8.0`. Stari artefakti se samo čitaju kroz tačne
  parove v1.6↔q1.3 i v1.7↔q1.4; ne prepisuju se.

### Faza 8: šta je promijenjeno

- Čisti `asd_profile_store` definiše blob `asd-profile-v1.0.0`: magic, schema i
  struct size, SHA-256 model fingerprint, generation, center[96], reference,
  oba apsolutna praga, window counts, commissioning summary, četiri policy ID-a
  i CRC32.
- Encode/decode odbija nefinalizovan profil, NaN/Inf, pogrešan fingerprint,
  CRC/schema/veličinu, nepoznate policy ID-e i odnos koji ne zadovoljava
  `0 < T_exit < T_enter`.
- `asd_profile_nvs` otvara samo namespace `asd` i ključ `profile_v1`. Ne postoji
  `nvs_flash_erase()` niti brisanje INA226 namespacea; nevalidan blob uklanja
  samo ASD ključ.
- Storage encode/decode i uski NVS wrapper ostaju kompajlirani i testirani, ali
  DEVELOPMENT profil se ne smije trajno čuvati. Autoritet je dvostruk:
  `ASD_PROFILE_PERSISTENCE_ALLOWED=0` i runtime policy `developmental=1`.
  Zbog toga trenutni build ne radi NVS init/load/save i profil ostaje samo u
  RAM-u aktivne sesije.
- Tek budući verzionisani production policy smije eksplicitno otvoriti compile
  gate i istovremeno nositi `developmental=0`. Tada save ostaje dozvoljen samo
  poslije uspješnog VERIFY, a load mora proći postojeće schema/fingerprint/CRC,
  finite, policy i `0 < exit < enter` provjere.
- Trenutni host fail-closed odbija `PROFILESTORE` i `PROFILE_RESTORED`; storage
  wire put mora dobiti zamrznutu policy/schema reviziju prije aktiviranja.

### Dokazi

```text
pytest sedam ciljanih F7/F8/integration modula: 272 passed
ESP-IDF 5.5.5 ASD_PSD_LIVE reconfigure build: PASS
esp32s3_asd.bin: 0x55620 B (349728 B), 92% app particije slobodno
git diff --check: bez whitespace greške (samo CRLF upozorenja na Windowsu)
```

Host-C test pokriva round-trip, CRC korupciju, fingerprint mismatch, NaN,
neispravne pragove, truncation/oversize i schema/ownership source guard. Literal
v1.5 test pokriva oba nova audio razloga i očekivani `SENSOR_ERROR`.

### Šta ostaje za fizički test

1. Prekinuti/odspojiti I2S tokom aktivnog read-a i izmjeriti stvarni timeout,
   terminalni UART par i oporavak poslije restarta.
2. Potvrditi tišinu kao validan read na stvarnom mikrofonu (quality gate je
   smije zasebno klasifikovati kao stuck/low-level, ali ne kao read timeout).
3. Potvrditi da DEVELOPMENT build ni poslije uspješnog commissioning-a ne pravi
   ASD NVS ključ i da restart zahtijeva novo učenje.
4. Tek poslije zamrzavanja production politike testirati prekid prije/tokom/
   poslije commita, validan restore, CRC/fingerprint reject i očuvanje INA226
   podataka.

Build i host testovi dokazuju kodni ugovor, ne stvarno ponašanje napajanja,
fleša, I2S periferije ili ventilatora.
