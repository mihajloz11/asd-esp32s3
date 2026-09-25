# Plan dorade poslije `fan01`

**Datum plana:** 16.08.2026.  
**Status:** spreman za uzastopnu implementaciju  
**Opseg:** softver, PC alati, firmware arhitektura, testovi i dokumentacija  
**Van opsega ovog ciklusa:** lemljenje tastera/LED/otpornika, promjena mikrofona,
drugi mikrofon, konačna fizička potvrda i bilo kakva tvrdnja o stvarnom
mehaničkom kvaru.

Ovaj plan polazi od prvog valjanog fizičkog runa
[`run_20260816T193342_fan01_verify-sw-02`](../../results/physical_fan/run_20260816T193342_fan01_verify-sw-02/)
i njegove analize u
[`rezultat-fan01-2026-08-16.md`](../../docs/rezultat-fan01-2026-08-16.md). Plan ne mijenja
istorijske rezultate i ne koristi papirić ili target anomalije za učenje centra,
izbor feature-a ili izvođenje praga.

---

## 1. Cilj i granica tvrdnje

Cilj je napraviti sistem koji:

1. automatski čeka da se ventilator ustali;
2. uči lokalni centar samo iz potvrđeno normalnog rada;
3. pragove uči iz zasebnog, dužeg normal-only commissioning perioda;
4. odvojeno koristi `T_enter` i `T_exit`;
5. ne proglašava razgovor normalnim radom, nego privremeno prelazi u
   `OBSERVATION_HOLD`/`AMBIENT_UNCERTAIN`;
6. poslije prestanka smetnje alarmira ako odstupanje ostane;
7. čuva dovoljno dijagnostike da se vidi koje PSD trake i podsegmenti nose
   odluku;
8. radi autonomno na ESP32-S3 nakon što je profil valjano napravljen;
9. fail-closed odbija nestabilnu kalibraciju, nevalidan profil i zastoj audio
   toka;
10. jasno razlikuje protokolarnu ispravnost, prihvatljivost kalibracije i
    stvarnu detekcionu metriku.

Ovaj ciklus može završiti implementaciju, PC testove i ESP-IDF build bez novog
fizičkog testa. Ne može legitimno završiti numeričke pragove stabilnosti,
tonalnosti i fizičkog false-alarm rada. Te stavke moraju ostati označene
`DEVELOPMENT/PENDING_PHYSICAL_VALIDATION` dok se ne odradi skraćeni protokol iz
sekcije 15.

Papirić uz usis ostaje **bezbjedno izazvana promjena protoka**, ne dokazani
mehanički kvar.

---

## 2. Trenutni dokazani problem

Postojeći tok u [`psd_live.c`](../../firmware/esp32s3_asd/main/psd_live.c):

```text
fiksni WAIT (~15 s)
  -> 10 CAL klipova (100 s)
  -> isti klipovi daju centar i LOO prag
  -> DET sa jednim pragom i exit_scale=0,7
```

To je neprihvatljivo za stvarni ventilator koji vremenski luta. U validnom runu:

- prag je bio `399,61`;
- 54 od 60 normalnih prozora bila su iznad praga;
- firmware je ušao u jednu dugu lažnu alarmnu epizodu;
- `psd_shape` je ipak veoma dobro rangirao papirić naspram normale;
- razgovor je takođe podizao score, ali je pokazao drugačiji tonalness obrazac.

Zaključak je da se feature zadržava kao zamrznuti baseline, a prvo se popravljaju
kalibracija, commissioning, pragovi, HOLD semantika i razvojna telemetrija.

---

## 3. Nepromjenjive odluke

Ove odluke važe kroz sve faze:

- Globalna normalizacija i Ledoit-Wolf precision i dalje se uče samo na
  `source/train/normal`.
- Lokalni centar se uči samo na potvrđeno normalnom ciljnom ventilatoru.
- Commissioning pragovi koriste samo normalne prozore tog ventilatora.
- Target anomalije i papirić ne biraju feature, centar, prag, tonalness granicu,
  stability granicu ni temporalnu politiku.
- Target anomalije se otvaraju tek nakon što su kandidat, politika, kod i
  verzije zamrznuti; tada služe samo za evaluaciju.
- Centar se nikada ne pomjera automatski tokom nadzora.
- Jedan mikrofon ne smije emitovati dijagnozu `AMBIENT_NOISE`; dozvoljena je samo
  tvrdnja da je opservacija privremeno nepouzdana.
- Aktivni alarm se ne gasi zbog HOLD-a.
- Kanonski `psd_shape` izlaz mora ostati bit-identičan dok razvojni kandidat ne
  prođe zaseban PC i PC↔C protokol.
- Stari run artefakti i njihovi `SUMMARY.md` fajlovi se ne prepisuju.
- Nema `git commit`, `git push`, flashovanja ni rada sa elektronikom u ovom
  softverskom ciklusu.

---

## 4. Phase 0 — dokumentaciono mapiranje — završeno

### Pregledani obrasci

- firmware tok: [`psd_live.c`](../../firmware/esp32s3_asd/main/psd_live.c);
- PSD frontend: [`psd_features_c.c/.h`](../../firmware/esp32s3_asd/main/psd_features_c.c);
- audio sloj: [`audio_i2s.c/.h`](../../firmware/esp32s3_asd/main/audio_i2s.c);
- čisti decision moduli:
  [`audio_quality_state.c`](../../firmware/esp32s3_asd/main/audio_quality_state.c),
  [`asd_events.c`](../../firmware/esp32s3_asd/main/asd_events.c),
  [`asd_temporal.c`](../../firmware/esp32s3_asd/main/asd_temporal.c);
- kanonska granica podataka:
  [`evaluate_canonical.py`](../../pc/tools/evaluate_canonical.py) i
  [`kanonska-evaluacija.md`](../../docs/kanonska-evaluacija.md);
- normal-only temporalni evaluator:
  [`derive_temporal_policy.py`](../../pc/tools/derive_temporal_policy.py);
- negativni f0/order/dual-channel eksperimenti:
  [`evaluate_advanced.py`](../../pc/tools/evaluate_advanced.py);
- host parser i run artefakti:
  [`physical_fan_experiment.py`](../../pc/tools/physical_fan_experiment.py);
- panel i launcher:
  [`asd_panel.py`](../../pc/tools/asd_panel.py),
  [`start_fan_run.py`](../../pc/tools/start_fan_run.py);
- feature/PCM debug obrasci:
  [`psd_verify.c`](../../firmware/esp32s3_asd/main/psd_verify.c),
  [`mic_test.c`](../../firmware/esp32s3_asd/main/mic_test.c) i
  [`psd_verify_compare.py`](../../pc/tools/psd_verify_compare.py);
- NVS blob obrazac:
  [`ina226_test.c`](../../firmware/esp32s3_asd/main/ina226_test.c).

### Dozvoljeni postojeći API-ji

Firmware:

```text
audio_flush
audio_dropped_samples
audio_raw_peak
audio_raw_peak_reset
asd_quality_reset
asd_quality_add_pcm
asd_quality_finish
asd_quality_evaluate
asd_psd_stream_reset
asd_psd_stream_push_hop
asd_psd_stream_finish
asd_psd_score
asd_temporal_init
asd_temporal_reset
asd_temporal_suspend
asd_temporal_update
asd_decision_init
asd_decide
esp_timer_get_time
vTaskDelay
ESP_LOGI / ESP_LOGW / ESP_LOGE
```

Lokalno potvrđena ESP-IDF infrastruktura koja se smije uvesti:

```text
i2s_channel_read(..., timeout_ms)
vTaskSetTimeOutState
xTaskCheckForTimeOut
nvs_flash_init
nvs_open
nvs_get_blob
nvs_set_blob
nvs_commit
nvs_erase_key
nvs_close
esp_crc32_le
```

PC:

```text
NumPy
SciPy signal
SoundFile
scikit-learn
pytest
ctypes + postojeći host-compiler obrazac
source-only LedoitWolf / Mahalanobis
postojeći manifest, provenance i atomic-output obrasci
```

### Copy-ready izvori

- `evaluate_canonical.py`: `_psd_shape`, `fit_source_only`, `mahalanobis`,
  `PhaseAudit`, manifest/provenance i atomic publish;
- `derive_temporal_policy.py`: `Rule`, `run_rule`, `episodes`;
- `test_psd_features_c.py`: PC↔C compile i parity;
- `psd_verify.c`: `PSDFEAT`/`PSDVEC` telemetrija;
- `mic_test.c::asd_dump_pcm_block`: framed PCM + FNV-1a;
- `audio_quality_state.c` i pripadajući test: čisti host-testabilni C modul;
- `asd_temporal_suspend`: pauza uspona bez brisanja aktivnog alarma;
- `ina226_test.c`: NVS blob read/write obrazac;
- `physical_fan_experiment.py`: strogi parser, provenance i CSV writeri.

---

## 5. Odluke o verzijama i kompatibilnosti

| Sloj | Trenutno | Novo | Odluka |
|---|---|---|---|
| UART/state/quality | `asd-quality-v1.3.0` | `asd-quality-v1.4.0` | obavezan bump zbog K1 firmware rejecta, novih faza/pragova i javnog HOLD stanja |
| Host run/artifacts | `physical-fan-v1.6.0` | `physical-fan-v1.7.0` | session indeks, acceptance status, feature artefakti i episode metrike |
| Temporalna politika | `asd-temporal-policy-v1.0.0` | `asd-temporal-policy-v2.0.0` | API prima nezavisni `T_enter` i `T_exit`; `exit_scale=0,7` više nije autoritet |
| Kalibracija/commissioning | nema | `asd-commissioning-policy-v1.0.0` | novi verzionisani normal-only ugovor |
| Interference gate | nema | `asd-interference-policy-v1.0.0-development` | schema i feature-i mogu biti gotovi; numeričke granice ostaju pending |
| NVS profil | nema | `asd-profile-v1.0.0` | magic, dužina, model fingerprint, policy ID i CRC |

Pravila kompatibilnosti:

- novi live run zahtijeva aktuelni UART protokol;
- offline čitanje starih `physical-fan-v1.6.0` artefakata mora ostati moguće;
- priznati wire zapis ili postojeći `DET` format ne mijenjati bez simultane izmjene
  firmwarea, parsera, literal-replay testova i schema dokumenta;
- razvojna telemetrija smije privremeno koristiti zaseban ignorable prefix, ali
  čim postane ulaz u validnost runa mora postati verzionisani priznati zapis;
- nijedan stari `SUMMARY.md` se ne regeneriše preko originala. Korekcija ide u
  novi dokument ili `SUMMARY.recomputed.md`.

---

## 6. Faza 1 — centralna K1 validnost i tačno izvještavanje

### Status koji se može završiti bez hardvera

`IMPLEMENTABLE_NOW`; fizički replay kasnije samo potvrđuje integraciju.

### Šta implementirati

1. Dodati `pc/config/asd_commissioning_policy_v1.json` sa najmanje:

   ```json
   {
     "schema_version": "asd-commissioning-policy-v1.0.0",
     "calibration": {"max_loo_cv": 0.6},
     "numeric_status": "temporary_preregistered_gate"
   }
   ```

2. Dodati jednu čistu PC funkciju, npr. u
   `pc/asd/commissioning_policy.py`:

   ```python
   calibration_acceptance(protocol_state) -> tuple[bool, str]
   ```

   Ona provjerava postojanje `CAL_SUMMARY`, konačan `loo_cv` i pravilo
   `loo_cv <= 0,6`.

3. Koristiti istu odluku u:

   - `physical_fan_experiment.make_summary()`;
   - finalnom `status`/`provenance.json`;
   - CLI exit codeu;
   - `asd_panel.Conductor.start()` kao server-side gate.

4. Razdvojiti:

   ```text
   protocol_valid
   calibration_accepted
   metrics_eligible
   ```

   K1 pad nije `invalid_firmware_telemetry`; to je valjan protokol sa odbijenom
   kalibracijom.

5. U firmware dodati čisti modul:

   ```text
   firmware/esp32s3_asd/main/asd_calibration_quality.c
   firmware/esp32s3_asd/main/asd_calibration_quality.h
   ```

   Modul prima LOO metrike i politiku, a vraća eksplicitan accept/reject razlog.
   `psd_live.c` ne smije emitovati `ADAPTTHR` ni `CALIBRATION_ACCEPTED` kada K1
   padne.

6. Panel pri novoj sesiji čisti stari `loo_cv`, prag, DET prikaz i prethodnu
   odluku.

### Dokumentacioni obrasci

- čisti C modul: `audio_quality_state.c/.h`;
- host-C test: `pc/tests/test_audio_quality_state_c.py`;
- K1 preregistracija: `docs/preregistracija-fan01.md`, pravilo K1;
- trenutni reporting bug: `physical_fan_experiment.py::make_summary`.

### Verifikaciona lista

- [ ] `loo_cv=0,600000` prolazi; `0,600001` pada;
- [ ] missing/NaN/Inf `loo_cv` pada fail-closed;
- [ ] `cold-start-04` offline recomputacija daje `Validan fizički rezultat: NE`;
- [ ] summary, provenance i exit code koriste isti razlog;
- [ ] panel `/start` vraća grešku poslije K1 pada čak i bez JavaScripta;
- [ ] firmware ne ulazi u DET poslije K1 pada;
- [ ] literalni C UART reject slijed prolazi host parser;
- [ ] stari v1.6 artefakti nisu izmijenjeni;
- [ ] ciljani pytest i kompletan PC pytest prolaze;
- [ ] ESP-IDF build prolazi.

### Anti-pattern guards

- Ne kopirati `0,6` na više mjesta bez jednog verzionisanog izvora politike.
- Ne izvoditi K1 iz slobodnog operatorovog `note` teksta.
- Ne popravljati samo `SUMMARY.md` i ostaviti exit code uspješnim.
- Ne praviti K1 pad protokolarnom greškom.
- Ne koristiti samo disabled dugme u browseru kao zaštitu.

---

## 7. Faza 2 — stvarni multi-session host i novi artifact contract

### Status koji se može završiti bez hardvera

`IMPLEMENTABLE_NOW`; testira se potpunim literalnim replayem dvije sesije.

### Šta implementirati

1. Uvesti run-scope i session-scope state odvojeno.
2. Na svakom `SESSION STARTED` resetovati samo session-scope polja:

   - WAIT/CAL/DET brojače;
   - `wait_ok_count`, `cal_summary`, `adapt/presence/temporal_seen`;
   - calibration acceptance par;
   - DET threshold, window, total alarm i temporal counters;
   - operator condition na `unconfirmed`.

3. Ne resetovati boot handshake, COM provenance ni run-total brojače.
4. Dodati `firmware_session_index` u sve session vezane CSV redove i
   `run_det_index` pored firmware-local `window`.
5. Izvještavati po sesiji i za cio run:

   - protocol status;
   - calibration acceptance;
   - DET count;
   - alarm entries/episodes;
   - procenat vremena u alarmu;
   - recovery latency;
   - excluded transition windows.

6. Proširiti provenance hash listu sa:

   ```text
   asd_temporal.c/.h
   asd_cmd.c/.h
   asd_temporal_policy_v2.json
   asd_commissioning_policy_v1.json
   asd_calibration_quality.c/.h
   budući interference policy/modul
   ```

7. Ispraviti `start_fan_run.py` dokumentaciju: montažna potvrda trenutno ide u
   `provenance.metadata.operator_notes`, ne doslovno u `events.csv`. Ako treba i
   u događaje, dodati eksplicitan typed event.

### Verifikaciona lista

- [ ] replay sadrži puni drugi `WAIT 1..60 -> CAL 1..10 -> ... -> DET`;
- [ ] drugi WAIT očekuje indeks 1, ne 61;
- [ ] `firmware_session_index` postaje 2;
- [ ] K1-pala sesija ostaje auditabilna, ali ne ulazi u metrike;
- [ ] druga prihvaćena sesija može dati valjan run;
- [ ] condition je na početku druge sesije ponovo `unconfirmed`;
- [ ] session i run DET totals odgovaraju CSV redovima;
- [ ] alarmni prozori nisu predstavljeni kao broj alarmnih epizoda;
- [ ] v1.6 offline fixtures ostaju čitljivi;
- [ ] `test_physical_fan_experiment.py` pokriva terminal drain i drugi session.

### Anti-pattern guards

- Ne resetovati boot handshake između sesija.
- Ne porediti session DET count sa svim run redovima.
- Ne dozvoliti nasljeđivanje operator conditiona.
- Ne završiti test samo na `SESSION ABORTED/ENDED`; mora se replayovati cio drugi
  mjerni tok.
- Ne dozvoliti da panel i host alat istovremeno otvore isti COM port.

---

## 8. Faza 3 — razvojna telemetrija: 96 vektora, pet podsegmenata i vrijeme

### Status koji se može završiti bez hardvera

`IMPLEMENTABLE_NOW` za kod, PC↔C testove i build. Realni sadržaj novih polja je
`PENDING_PHYSICAL_CAPTURE`.

### Šta implementirati

1. Proširiti PSD frontend opcionim sidecar izlazom; postojeći
   `asd_psd_stream_finish(out_feature)` mora ostati bit-identičan.
2. Zadržati 38 Welch segmenata u pet uzastopnih grupa približno:

   ```text
   8 + 8 + 8 + 7 + 7
   ```

   Za svaku grupu sačuvati 96 band-power vrijednosti. Ne čuvati veliki PCM bafer.
3. Dodati po prozoru:

   - firmware monotonic `window_start_ms` i `window_end_ms`;
   - finalni 96-dim feature ili standardizovani rezidual;
   - pet podsegmentnih 96-dim vektora;
   - `tonalness_proxy`;
   - score, level, quality i session/window identitet.

4. Kopirati framing/provjeru dimenzije iz `PSDVEC` debug puta. Poželjna su dva
   odvojena zapisa (`FEATURE96`, `SUBSEG96`) sa session/window ključem i checksumom.
5. Host zapisuje novi `window_features.csv` ili kompaktniji `window_features.npz`
   plus manifest sa shapeovima, dtypeom i SHA-256.
6. Parser mora dokazati tačno jedan feature paket za svaki validni CAL/DET
   prozor kada je research telemetry obavezna.
7. Eksterni WAV ostaje opcionalan. `--wav-path` mora jasno zapisati da alat samo
   povezuje već snimani fajl; ne smije tvrditi da ga je sam snimio.

### PCM odluka

Kontinuirani 16 kHz/16-bit PCM ne slati preko 115200 UART-a. Dozvoljene opcije:

- eksterni sinhronizovani recorder;
- one-shot PCM dump poslije zaustavljanja sesije;
- kasniji brži transport, kao zaseban projekat.

### Verifikaciona lista

- [ ] batch i streaming finalni 96 feature ostaju identični;
- [ ] PC↔C feature tolerancija nije pogoršana;
- [ ] tačno 38 segmenata završava u grupama `8/8/8/7/7`;
- [ ] svaki sidecar vektor ima 96 konačnih vrijednosti;
- [ ] missing/duplicate/malformed feature paket invalidira research artefakt;
- [ ] debug zapis ne prekida neposredni `QUALITY DET -> DET` ugovor;
- [ ] sintetički UART throughput test pokazuje rezervu;
- [ ] nema poziva `asd_dump_pcm_block()` u svakoj DET iteraciji;
- [ ] kompletan pytest i ESP-IDF build prolaze.

### Anti-pattern guards

- Ne mijenjati postojeći finalni feature dok sidecar nije zasebno potvrđen.
- Ne zvati pet grupa „pet nezavisnih dvosekundnih klipova”; Welch segmenti se
  preklapaju.
- Ne stavljati 480 floatova na stack u dubokoj live petlji.
- Ne uvoditi priznati wire zapis bez version bumpa i parser testova.
- Ne tvrditi da postoji audio ako je `external_wav=null`.

---

## 9. Faza 4 — PC normal-only commissioning i feature laboratorija

### Status

Algoritmi, evaluator i fixture testovi su `IMPLEMENTABLE_NOW`. Finalni brojevi su
`DEVELOPMENT/PENDING_PHYSICAL_VALIDATION`.

### Novi developmental namespace

Dodati, bez izmjene kanonskog evaluatora:

```text
pc/tools/derive_commissioning_policy.py
pc/tools/evaluate_fan_noise_candidates.py
results/commissioning_development/
pc/config/asd_commissioning_policy_v1.json
pc/config/asd_interference_policy_v1.json
```

Kopirati granicu podataka, `PhaseAudit`, manifest i provenance iz
`evaluate_canonical.py`. Ne koristiti legacy cache koji miješa kohorte.

### Commissioning podjela

Fizički normalni tok uvijek čuvati hronološki:

```text
CENTER_LEARNING: samo centar
COMMISSION_DERIVE: izvodi instance pragove
COMMISSION_VERIFY: vremenski kasniji, netaknuti normalni holdout
```

Ne randomizovati commissioning prozore. Ako se politika bira na verify dijelu,
taj dio više nije verifikacija i mora postojati treći netaknuti blok.

### Unaprijed zaključani kandidati za prag

Evaluator mora odvojeno uporediti:

1. visoki empirijski percentil normalnih scoreova;
2. `median + k * MAD`;
3. percentil maksimuma po unaprijed definisanom vremenskom bloku;
4. normal-only conformalni gornji kvantil, ako je veličina uzorka dovoljna.

`T_enter` i `T_exit` izvode se kao dva apsolutna praga. `T_exit` može koristiti
niži normalni kvantil ili zaseban `median + k_exit*MAD`, ali mora zadovoljiti:

```text
0 < T_exit < T_enter
```

Izbor se radi prema cijelom vremenskom nizu:

- broj alarmnih epizoda;
- vrijeme u alarmu;
- chatter/re-entry;
- najduža normalna epizoda iznad praga;
- stabilnost kroz vremenske blokove.

### Unaprijed zaključani feature kandidati

Uporediti odvojeno, nikada sve odjednom:

1. postojeće tvrde nepreklapajuće log-trake — baseline;
2. 96 preklapajućih trougaonih log-traka;
3. fiksno blago frekvencijsko zaglađivanje;
4. coordinate-wise clipping standardizovanog reziduala prije pune kvadratne
   forme;
5. Huber score nad izbijeljenim rezidualom;
6. podsegmentna stalnost kao gate, ne kao zamjena za glavni detector.

Svaka promjena statistike dobija novi prag izveden samo iz normalnih podataka.

### Tonalness/stability razvoj

`tonalness_proxy` je peak-prominence, ne speech classifier. Kandidati se zato
formulišu relativno prema lokalnoj normalnoj referenci:

```text
tonalness_delta = tonalness - calibration_normal_reference
within_window_instability = robust spread pet podsegmentnih vektora
```

Brojevi `4,55`, `-0,45` i score `2.016` iz `fan01` služe samo kao hipoteza i
regression fixture. Ne smiju biti finalni defaulti.

Za PC selection koristiti:

- source-normal;
- target-normal;
- normalne klipove sa unaprijed definisanim nezavisnim govor/koraci miksom;
- source anomalije ili sintetičke trajne score pomjeraje samo kao razvojnu
  sensitivity kontrolu;
- target/papirić tek nakon zamrzavanja, samo za readout.

### Negativni rezultati koje ne treba ponavljati

- `psd_order`: `0,6388` naspram `0,8556` baselinea;
- `psd_regime`: bez dobitka;
- dual-channel logratio/coherence/mask: svi slabiji od near-only;
- transient sam slab, kombinacija samo `+0,0012`;
- EWMA i CUSUM pogoršali kratke pobude;
- stari winsorizovani mel centar nije isto što i clipping novog reziduala;
- top-k izbacivanje traka je matematički pogrešno uz punu precision matricu.

### Verifikaciona lista

- [ ] target anomaly feature se ne čita prije evaluate faze;
- [ ] lista kandidata i svi koeficijenti postoje u manifestu prije evaluacije;
- [ ] commissioning redoslijed ostaje vremenski;
- [ ] derive i verify indeksi se ne preklapaju;
- [ ] rezultat prijavljuje episode metrike, ne samo window rate;
- [ ] bootstrap jedinica je sesija/ventilator, ne preklapajući prozor;
- [ ] svaki kandidat ima zaseban cache/provenance ID;
- [ ] kanonski evaluator i rezultat nisu prepisani;
- [ ] izlaz jasno nosi `developmental=true` i `target_anomalies_used_for_fit=false`.

### Anti-pattern guards

- Ne birati kandidat po najvećem AUC-u na papiriću.
- Ne koristiti isti normalni blok za derivaciju i tvrdnju o validaciji.
- Ne randomizovati hronologiju stvarnog ventilatora.
- Ne hardkodovati post-hoc granice iz validnog runa.
- Ne izglađivati toliko da se uklone harmonici koji nose korisni signal.
- Ne vraćati f0/order ili dual-channel bez novih podataka koji mijenjaju njihovu
  prethodno oborenu pretpostavku.

---

## 10. Faza 5 — novi firmware tok: SETTLE, CENTER, COMMISSION, MONITOR

### Status

State machine, čisti moduli, fixture testovi i build su `IMPLEMENTABLE_NOW`.
Konačni numeric policy ostaje `PENDING` do rezultata Faze 4 i fizičke Faze 9.

### Ciljni tok

```text
IDLE
  -> SETTLE
  -> CENTER_LEARNING
  -> COMMISSION_DERIVE
  -> COMMISSION_VERIFY
  -> MONITORING
```

Svaka faza ima eksplicitan timeout, quality gate, operator abort i fail-closed
ishod.

### SETTLE

Prije centra ne postoji legitiman lokalni Mahalanobis score. SETTLE koristi:

- RMS/nivo;
- tonalness;
- robustan drift između uzastopnih 96 feature-a;
- kvalitet PCM-a i `dropped_delta`.

Mora imati minimalan broj punih prozora, potreban broj uzastopno stabilnih
prozora i maksimalni timeout. Numeričke granice ostaju iz policy JSON-a; ako
nema zamrznute politike, build/run se označava DEVELOPMENT i ne prihvata trajni
profil.

### CENTER_LEARNING

- 10–20 čistih 10 s klipova;
- centar i referentni nivo/tonalnost;
- K1 firmware gate prije nastavka;
- precision matrica se ne mijenja.

### COMMISSION_DERIVE

- automatizovani normal-only period;
- centar ostaje zamrznut;
- izvode se instance `T_enter` i `T_exit` iz izabrane normal-only formule;
- nema alarma i nema auto-adaptacije centra.

### COMMISSION_VERIFY

- vremenski kasniji normal-only blok;
- pragovi su zamrznuti prije prvog verify prozora;
- mjeri se broj epizoda, vrijeme u alarmu i chatter;
- neuspjeh ne „popravlja” prag u hodu nego odbija profil.

### MONITORING

- koristi samo zamrznuti profil;
- rekalibracija isključivo eksplicitnim operatorovim zahtjevom;
- sve odluke idu kroz host-testabilne module, ne kroz ad-hoc `if` u `psd_live.c`.

### Potrebne strukture/API-ji

Proširiti kalibracioni profil na najmanje:

```c
typedef struct {
    int valid;
    float center[96];
    float level_mean_dbfs;
    float tonalness_reference;
    float threshold_enter;
    float threshold_exit;
    uint32_t center_windows;
    uint32_t derive_windows;
    uint32_t verify_windows;
    uint32_t policy_version;
} asd_profile_runtime_t;
```

Temporalni API promijeniti eksplicitno:

```c
int asd_temporal_update(asd_temporal_t *det,
                        float score,
                        float threshold_enter,
                        float threshold_exit);
```

Ne zadržavati skriveno `threshold * exit_scale` kao autoritet.

### Verifikaciona lista

- [ ] nijedan put ne ulazi u MONITORING bez validnog centra i oba praga;
- [ ] SETTLE ne ispisuje dBFS kao „score”;
- [ ] SETTLE timeout završava imenovanim rejectom;
- [ ] K1 pad sprečava commissioning;
- [ ] derive i verify su nepovratno odvojeni unutar sesije;
- [ ] verify ne mijenja prag;
- [ ] `0 < T_exit < T_enter` se provjerava fail-closed;
- [ ] centar se ne mijenja u COMMISSION_VERIFY/MONITORING;
- [ ] operator abort/relearn radi iz svake faze;
- [ ] čisti C fixture testovi pokrivaju sve tranzicije;
- [ ] host literal replay prati cijeli novi redoslijed;
- [ ] ESP-IDF build prolazi.

### Anti-pattern guards

- Ne koristiti Mahalanobis score u SETTLE prije centra.
- Ne računati centar i prag iz istog skupa prozora.
- Ne podešavati prag tokom verify ili monitoring faze.
- Ne nastaviti poslije rejecta uz warning.
- Ne staviti svu state logiku direktno u `psd_live.c`.

---

## 11. Faza 6 — dvostepena odluka i HOLD bez lažne dijagnoze

### Status

Arhitektura i testovi su `IMPLEMENTABLE_NOW`; numerička tonalness/stability
politika je `DEVELOPMENT/PENDING_PHYSICAL_VALIDATION`.

### Odluka

Jedno-mikrofonsko stanje nazvati `OBSERVATION_HOLD` u wire ugovoru. UI smije
prikazati tekst „moguća smetnja / čekam”, ali firmware događaj ne smije biti
`AMBIENT_NOISE`.

Ciljna tabela:

| Score | Tonalnost/stalnost | Ishod |
|---|---|---|
| nizak | normalna | `CALIBRATED_NORMAL` |
| visok | stabilan, trajni fan-like pomak | gradi niz ka `ANOMALY` |
| visok | nestabilna/nepouzdana opservacija | `OBSERVATION_HOLD` |
| visok poslije HOLD-a | trajno odstupanje | alarm nakon zaključane potvrde |
| prenizak nivo | trajno | postojeći presence/fan-stopped tok |

### Pravila HOLD-a

- `asd_temporal_suspend()` je referentni obrazac;
- suspenduje uspon ka alarmu;
- ne briše već aktivan alarm;
- ne mijenja centar, prag ni profil;
- po izlasku iz HOLD-a trajni visok score ponovo gradi alarm;
- predug HOLD daje zaseban operator-warning/inspection događaj, ne „normalno”.

Ako je alarm već aktivan, javno stanje ostaje `ANOMALY`, uz dijagnostički flag
da je opservacija trenutno holdovana. HOLD je javno stanje prvenstveno prije
aktivnog alarma.

### Potrebne izmjene

- `asd_state_t` i `asd_state_name`;
- transition tabela u `asd_events.c`;
- `asd_observation_t` dobija tonalness i instability metrike;
- čisti `asd_interference.c/.h` modul;
- UI mapiranje i LED pattern;
- host parser, state/event CSV i literal replay;
- `asd-quality-v1.4.0` dokumentacija.

### Verifikaciona lista

- [ ] jedan nestabilan visok prozor ne povećava alarmni run;
- [ ] aktivni alarm ostaje aktivan tokom HOLD-a;
- [ ] stabilno visoko odstupanje poslije HOLD-a alarmira;
- [ ] HOLD nikad ne mijenja centar/prag;
- [ ] jedan mikrofon nikad ne emituje `AMBIENT_NOISE`;
- [ ] predug HOLD nije prikazan kao normalno;
- [ ] sve nove state tranzicije imaju pozitivne i negativne host-C testove;
- [ ] stari rezervisani capability gate ostaje konzervativan.

### Anti-pattern guards

- Ne nazivati tonalness speech detektorom.
- Ne koristiti `tonalness < 4,55` kao finalno pravilo.
- Ne čistiti aktivni alarm razgovorom.
- Ne preskakati odstupanje zauvijek ako je smetnja duga.
- Ne emitovati uzrok koji jedan mikrofon ne može dokazati.

---

## 12. Faza 7 — audio liveness i total-timeout

### Status koji se može završiti bez hardvera

API, host fixture testovi i build su `IMPLEMENTABLE_NOW`; stvarni prekid I2S-a je
`PENDING_HARDWARE_RUNTIME`.

### Šta implementirati

Zamijeniti beskonačni consumer API rezultatom sa statusom:

```c
esp_err_t audio_read_exact(int16_t *dst,
                           size_t n_samples,
                           uint32_t timeout_ms,
                           size_t *samples_read);
```

Ukupni timeout važi za cijelo čitanje preko `vTaskSetTimeOutState()` i
`xTaskCheckForTimeOut()`. Ne počinje ispočetka nakon svakog parcijalnog komada.

Capture task takođe koristi konačan `i2s_channel_read(..., timeout_ms)` i vodi:

- heartbeat/last-success vrijeme;
- posljednju I2S grešku;
- timeout/error counter.

Consumer timeout se mapira na imenovani fail-closed quality razlog, uz protocol
bump i host semantičku provjeru.

### Verifikaciona lista

- [ ] puni read vraća `ESP_OK` i tačan count;
- [ ] parcijalni read ne resetuje ukupni deadline;
- [ ] silence nije timeout;
- [ ] timeout/error završava u `SENSOR_ERROR`;
- [ ] nijedan production `portMAX_DELAY` ne ostaje na audio data putu;
- [ ] literal UART timeout reject prolazi parser;
- [ ] PC testovi i ESP-IDF build prolaze;
- [ ] dokumentacija ga i dalje označava hardware-unverified do fizičkog testa.

### Anti-pattern guards

- Ne koristiti timeout po komadu koji se stalno obnavlja.
- Ne pretvarati stvarni audio timeout u niz nula.
- Ne nastaviti poslije I2S greške uz warning.
- Ne tvrditi runtime zaštitu samo na osnovu builda.

---

## 13. Faza 8 — NVS profil i autonomni restart

### Status

Serialization, CRC, host testovi i build su `IMPLEMENTABLE_NOW`. Power-loss i
stvarni boot testovi ostaju `PENDING_HARDWARE_RUNTIME`.

### Profil `asd-profile-v1.0.0`

NVS blob sadrži najmanje:

```text
magic
schema_version
struct_size
model_fingerprint
generation
center[96]
level_mean_dbfs
tonalness_reference
T_enter
T_exit
center/derive/verify counts
commissioning summary metrics
quality/commissioning/temporal/interference policy IDs
crc32
```

Koristiti model fingerprint iz generisanog PSD modela, ne samo naziv modela.

### Pravila

- storage/NVS kod držati kompajliranim i testiranim, ali DEVELOPMENT policy
  mora imati compile gate `0` i runtime `developmental=1`, bez init/load/save;
- profil sačuvati samo poslije uspješnog COMMISSION_VERIFY **i** tek kada
  zamrznuti production policy eksplicitno otvori oba persistence gate-a;
- učitavanje provjerava blob length, magic, verziju, fingerprint, CRC, finite
  vrijednosti i `0 < T_exit < T_enter`;
- nevalidan profil vodi u zahtjev za novo učenje;
- ručni relearn pravi novu generaciju tek nakon uspješnog verifya;
- kod nevalidnog ASD ključa obrisati samo ASD ključ;
- nikada automatski ne brisati cijelu NVS particiju, jer je dijeli INA226 zapis.

### Verifikaciona lista

- [ ] round-trip identičnog profila;
- [ ] jedan izmijenjen bajt ruši CRC;
- [ ] pogrešan model fingerprint odbija profil;
- [ ] NaN/Inf i neispravan odnos pragova se odbijaju;
- [ ] truncated/oversized blob se odbija;
- [ ] stari/unknown schema zahtijeva relearn;
- [ ] nevalidan ASD profil ne briše INA226 namespace;
- [ ] write se radi tek nakon verify success;
- [ ] ESP-IDF build prolazi.

### Anti-pattern guards

- Ne čuvati samo centar bez model/policy identiteta.
- Ne učitati blob bez CRC-a i range provjere.
- Ne sačuvati derive prag prije verify faze.
- Ne pozivati `nvs_flash_erase()` kao opšti recovery.
- Ne tvrditi power-loss sigurnost bez stvarnog prekida napajanja.

---

## 14. Faza 9 — dokumentacija i istorijska korekcija

### Status koji se može završiti bez hardvera

`IMPLEMENTABLE_NOW`.

### Ažurirati

- `README.md` — prvi valjani fizički fan run, ali prag i autonomna finalna
  potvrda ostaju otvoreni;
- `privatno/planovi/handoff.md` — odvojiti feature dokaz, threshold problem i hardware
  pending;
- `privatno/planovi/PREOSTALO.md` — ukloniti kontradikciju da je sav softver zatvoren;
- `docs/panel-i-virtuelni-taster.md` — server-side K1 i multi-session;
- `docs/protokol-fizicki-ventilator.md` — v1.7 artefakti, session i acceptance;
- `docs/rezultat-fan01-2026-08-16.md` — datirana korekcija K1 reporting buga i
  razlika alarmnih prozora/epizoda;
- `privatno/dnevnici/DNEVNIK-NEXT-LEVEL.md` — samo novi datirani blok, bez brisanja tada
  tačnih istorijskih tvrdnji.

### Čuvati neizmijenjeno

- pravila K1–K6 u `docs/preregistracija-fan01.md`; dozvoljena je samo jasno
  označena naknadna korekcija/ishod;
- originalne run direktorijume i `SUMMARY.md` fajlove;
- kanonske benchmark rezultate.

### Verifikaciona lista

- [ ] nijedan dokument ne tvrdi da papirić predstavlja potvrđen kvar;
- [ ] PC/build, flash/UART i fizički rezultat su odvojeni;
- [ ] 324 alarmna prozora/h nije nazvano 324 alarmne epizode/h;
- [ ] stari `SUMMARY.md` checksumovi nisu promijenjeni;
- [ ] sve verzije u kodu, configu i dokumentima su saglasne;
- [ ] nema zastarjele tvrdnje „ventilator nije fizički testiran” bez datuma i
  istorijskog konteksta.

---

## 15. Skraćeni naredni fizički protokol

Ovo je jedan kompaktan razvojni run, ne finalna statistička validacija. Ručni dio
je ograničen na najviše **3 papirić bloka i 2 razgovor bloka**. Normal-only dio je
automatizovan i ne traži stalno unošenje oznaka.

### Preduslovi

- sve faze 1–9 završene;
- svi PC testovi i ESP-IDF build zeleni;
- firmware/protocol/policy hashovi zapisani;
- fizička montaža ista i fotografisana/opisana;
- eksterni WAV je opcionalan, ali ako ne postoji, jasno ostaje `null`;
- kandidat i numeric policy zamrznuti prije prvog papirića/razgovora.

### Tok jedne sesije

1. **Automatski SETTLE**

   - firmware čeka stability kriterij;
   - obavezan maksimalni timeout;
   - bez ručnog biranja „najljepše” kalibracije.

2. **CENTER_LEARNING**

   - 10–20 normalnih klipova prema zamrznutoj politici;
   - K1 mora proći automatski;
   - K1 pad završava sesiju, ne prelazi u DET.

3. **Automatizovani normal-only commissioning: 30 minuta ukupno**

   - prvih 20 min: `COMMISSION_DERIVE` (`120` prozora);
   - posljednjih 10 min: `COMMISSION_VERIFY` (`60` prozora);
   - pragovi se zamrzavaju prije verify dijela;
   - operater ne govori, ne prilazi i ne mijenja montažu.

4. **Papirić: najviše 3 bloka**

   - svaki blok 60 s;
   - između blokova najmanje 90 s recovery normale;
   - papirić samo uz spoljnu usisnu rešetku, bez kontakta sa lopaticama.

5. **Razgovor: najviše 2 bloka**

   - svaki blok 60 s na unaprijed fiksiranoj udaljenosti;
   - između blokova najmanje 90 s recovery normale;
   - isti govor/jačina koliko je praktično moguće;
   - ne dodavati nove pokušaje zato što je rezultat „ružan”.

6. **Kontrolisano gašenje i završetak**

   - sačekati očekivani presence/fan-stop ishod;
   - sačuvati sve raw/CSV/NPZ/provenance artefakte;
   - ne mijenjati prag i ne ponavljati sesiju radi boljeg rezultata.

### Unaprijed definisani razvojni kriteriji

Run prolazi kao **development smoke test** samo ako:

- K1 i commissioning verify prođu bez ručne intervencije;
- `dropped_delta=0` u svim mjernim prozorima;
- nema parser/schema greške;
- COMMISSION_VERIFY ima **0 novih alarmnih epizoda** i 0 vremena u aktivnom
  alarmu;
- sva 3 papirić bloka proizvedu trajno odstupanje/alarm u unaprijed definisanom
  latency limitu;
- nijedan od 2 razgovor bloka ne proizvede novu mehaničku/unknown-change alarmnu
  epizodu; HOLD je dozvoljen i očekivan;
- poslije svakog bloka sistem izađe iz HOLD-a/recoveryja prema zamrznutoj
  politici;
- aktivni alarm se ne briše samo zato što je nastupio HOLD.

Tačan latency limit mora biti u policy manifestu prije runa. Ako nije zamrznut,
run se ne koristi za pass/fail tvrdnju o latenciji.

### Statistička granica — obavezno navesti u rezultatu

Ovaj skraćeni protokol nije dovoljan za produkcionu tvrdnju:

- 10 min verify vremena sa 0 alarmnih epizoda daje približno jednostranu 95%
  Poisson gornju granicu od **18 epizoda/h**;
- 3/3 uspješna papirić bloka imaju vrlo široku 95% binomnu donju granicu
  (približno 29% za dvostrani Clopper-Pearson interval);
- 2/2 razgovor bloka bez alarma imaju još širu donju granicu specifičnosti
  (približno 16%).

Zato rezultat smije biti samo:

```text
DEVELOPMENT_SMOKE_PASS
DEVELOPMENT_SMOKE_FAIL
INVALID_RUN
```

Ne smije se iz ovog runa tvrditi „90% pouzdano”, „0 false alarma u radu” ili
generalizacija na druge ventilatore/prostorije.

Dozvoljen je najviše jedan novi kompletan pokušaj samo ako prvi run postane
`INVALID_RUN` zbog unaprijed definisane tehničke greške prije prvog validnog DET
prozora. Ne ponavljati validan, ali loš rezultat.

---

## 16. Završna softverska verifikacija prije fizičkog runa

### Testovi

Pokrenuti iz korijena repozitorijuma:

```powershell
.venv\Scripts\python.exe -m pytest pc\tests -q
```

Uz kompletan paket obavezno posebno dokazati:

- calibration-quality host-C parity;
- threshold derive/verify razdvajanje;
- dva puna firmware session replaya;
- `T_enter/T_exit` PC↔C temporalni niz;
- HOLD ne briše aktivni alarm;
- feature sidecar shape/checksum/parity;
- audio total-timeout fixture;
- NVS serialization/CRC fixture;
- v1.6 backward artifact read;
- v1.4 literal C UART tekst, uključujući granične float32 vrijednosti.

### Build

- ESP-IDF reconfigure i build za ESP32-S3;
- zapisati bin veličinu i slobodan flash;
- zapisati statičku RAM procjenu za `5 × 96` sidecar i novi profil;
- build nije flash/UART/runtime dokaz.

### Grep anti-pattern provjera

Provjeriti da nema:

```text
portMAX_DELAY na production audio read putu
automatskog pomjeranja center[] u MONITORING
nvs_flash_erase() u ASD recovery putu
hardkodovanih 2016 / 4.55 / -0.45 kao finalne politike
AMBIENT_NOISE emitovanja iz jedno-mikrofonskog gate-a
target anomaly pristupa prije evaluate faze
prepisivanja istorijskih SUMMARY.md fajlova
```

### Dokazni nivo na kraju softverskog ciklusa

Ako su sve stavke iznad zelene, dozvoljena tvrdnja je:

```text
PASS_PC_TESTS_AND_BUILD
PENDING_FLASH_UART_AND_PHYSICAL_VALIDATION
```

Ne koristiti riječ „završen sistem” dok skraćeni fizički protokol i kasnija duža
nezavisna validacija ne prođu.

---

## 17. Redoslijed izvršavanja i checkpointi

Faze se izvršavaju redom:

```text
1 K1/validnost
  -> 2 multi-session/artifacts
  -> 3 razvojna telemetrija
  -> 4 PC normal-only policy laboratorija
  -> 5 commissioning state machine
  -> 6 HOLD odluka
  -> 7 audio timeout
  -> 8 NVS profil
  -> 9 dokumentacija
  -> kompletna softverska verifikacija
  -> jedan skraćeni fizički run kasnije
```

Poslije svake faze implementator mora u ovom dokumentu ili posebnom datiranom
izvještaju zapisati:

- izmijenjene fajlove;
- koje testove je pokrenuo i tačan rezultat;
- šta je dokazano;
- šta je ostalo pending;
- da li je wire/artifact verzija promijenjena;
- poznate probleme bez uljepšavanja.

Ako faza padne verifikaciju, ne prelaziti na sljedeću dok se uzrok ne dokumentuje
i ne zatvori ili eksplicitno označi kao blokiran fizičkim hardverom.
