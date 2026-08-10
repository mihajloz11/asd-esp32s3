# DNEVNIK NEXT LEVEL IZVRŠENJA

Ovaj dnevnik je append-style evidencija plana iz
[`PLAN-NEXT-LEVEL.md`](PLAN-NEXT-LEVEL.md). Brojke se unose onakve kakve jesu;
`PASS`, `FAIL`, `BLOCKED_HARDWARE` i `NOT_RUN` nisu međusobno zamjenjivi.

## 09.08.2026. — početno stanje

- Korisnik je odobrio redom izvršenje osam softverskih pravaca.
- Pločica nije povezana; flash i uređajna mjerenja nisu pokrenuti.
- Kanonski v1.1.0 ostaje zamrznut na `mel1280`, `mel256`, `psd_shape`.
- Fan `psd_shape`: AUC `0,8666`, standardized pAUC@FPR≤0,1 `0,6669`;
  developmental rezultat sa istorijskim model-selection biasom.
- PC testovi prije novih izmjena: `32 passed`.
- Radni tree je već dirty zbog canonical, audit i physical-capture rada; nove
  faze moraju dirati samo eksplicitno navedene fajlove.

## Phase 0 — dokumentaciono mapiranje

**Status:** `PASS`

### Potvrđeno

- `psd_live.c` upozorava na tišinu, ali nastavlja kalibraciju.
- PSD live nema clipping, stuck/zero, short-read ni per-phase dropped gate.
- Nema eksplicitne state machine, EWMA, CUSUM, histereze ni rolling odluka.
- Nema f0/RPM/order-normalized PSD implementacije.
- Trenutni kanonski evaluator koristi near kanal.
- Raniji clip-level envelope/scalar/ensemble pravci već su ispitani i bili
  slabiji; neće se ponavljati.

### Otvoreno

- tonalness, LOO-spread, f0-confidence i rolling pragovi moraju se preregistrovati
  samo na normalnim/source fixtureima;
- flash/runtime i fizički događaji čekaju pločicu i fan;
- teacher feasibility zahtijeva poseban inventar prije preuzimanja modela.

## Faza 1 — fail-closed kalibracija i osnovna stanja

**Status:** `PASS_PC_BUILD` / `BLOCKED_HARDWARE`

### Planirani izlazi

- čisti C quality/state modul;
- host unit testovi;
- PSD live integracija;
- parser/schema/protocol bump;
- normal-only threshold provenance;
- ESP-IDF build bez flasha.

### Rezultati

- Dodani su čisti host-testabilni
  `firmware/esp32s3_asd/main/audio_quality_state.c/.h`: PCM accumulator,
  quality policy i stabilni reason/state nazivi. `OK` nastavlja svaku fazu;
  `LOW_LEVEL_OBSERVATION` smije nastaviti samo WAIT observation, dok svaki
  stvarni reject zaustavlja tok.
- Metrike su preuzete iz postojećeg `mic_test.c` obrasca: exact sample count,
  DC, RMS/dBFS, peak, clipping, zero i stuck count. `dropped_delta` prati obrazac
  `psd_verify.c`/`live_capture.c`.
- `psd_live.c` sada fail-closed zaustavlja WAIT/CAL/DET na vraćenom short readu,
  nonfinite vrijednosti, stuck/zero signalu, clippingu i bilo kom dropu. Prenizak
  nivo ne može proći iz WAIT u CAL; tokom CAL/DET završava u `NO_MACHINE`. LED se na
  stop putu gasi. Centar se i dalje nikad automatski ne pomjera.
- Uvedeni su ASCII `QUALITY`, `STATE`, `EVENT` zapisi protokola
  `asd-quality-v1.2.0` i svih šest zaključanih stanja.
- `physical_fan_experiment.py` je bumpovan na `physical-fan-v1.5.0`; operatorov
  `condition` ostaje u `events.csv`/`detections.csv`, dok firmware zapisi idu
  odvojeno u `firmware_quality.csv`, `firmware_states.csv` i
  `firmware_events.csv`; parse greške idu u `firmware_parse_errors.csv`.
- Operator condition sada počinje kao `unconfirmed`; firmware DET poruka ga ne
  mijenja. Metrike prihvataju samo eksplicitno potvrđene condition prozore nakon
  handshakea, očekivanih quality countova i oba `CALIBRATION_ACCEPTED` zapisa.
- Poznati QUALITY/STATE/EVENT sa pogrešnim/missing protokolom, malformed brojem
  ili missing poljem auditira se kao `PARSE_ERROR` i invalidira run. Terminalni
  firmware state/event odmah završava host run kao nevalidan.
- Review P2 je zaključao tačan telemetry redoslijed: WAIT `1..60/60`, CAL
  `1..10/10`, exactly-one CAL_SUMMARY i jednokratni DET QUALITY token uparen sa
  istim sljedećim DET windowom. Duplikat, replay, preskok ili interposed zapis
  invalidira run i ulazi u semantic audit.
- Host provjerava finite floatove, fazni sample count, count opsege, nulti drop
  za prihvaćeni observation, binarne LED/alarm vrijednosti i konzistentan
  `window/total_anom/uzastopnih/verdict`. Firmware DET ispis je proširen na 9
  značajnih cifara radi round-trip provjere binary32 poređenja.
- Firmware više ne emituje `nan`/`inf`: `metrics_valid` i `tonalness_valid`
  razdvajaju konačne sentinele od stvarno izračunatih metrika. Host iz metrika
  ponovo računa quality odluku i provjerava da je `result` saglasan sa
  verzionisanom politikom; literalni WAIT i reject ispisi iz `emit_quality`
  pokriveni su replay testovima.
- Najmanje 30/60 WAIT zapisa mora biti stvarni `OK`. CAL summary mora imati
  nenegativan i koherentan mean/sd/CV/range; tačno jedan `ADAPTTHR` mora doći
  poslije summaryja, prije acceptancea, i njegov prag mora ostati isti u svakom
  DET zapisu i u provenance/summary artefaktima.
- Dozvoljena STATE/EVENT gramatika i chain su zatvoreni: samo prvi
  `BOOT_FAIL_CLOSED` smije ostati u `NO_MACHINE`; kasniji NO_MACHINE i svi
  terminalni ishodi invalidiraju rezultat. Terminal drain završava tek kada su
  sačuvani i odgovarajući STATE i `FLOW_STOPPED`.
- `stop`/`--max-seconds` rade kratki final-buffer drain prije validne
  finalizacije. Serial-open i ne-prazan command-file failure i nevalidna
  operator condition više ne mogu preskočiti provenance/summary finalizaciju;
  otvoren port se uvijek zatvara.
- Treća review korekcija dodaje `feature_valid`: PCM quality i PSD
  segment/feature validnost više se ne miješaju. PCM-validan feature failure je
  zakoniti `NONFINITE` reject sa terminalnim drainom; literalni UART test to
  reprodukuje.
- DET alarm sada iz prethodnog statea izvodi tačno očekivani STATE/EVENT par.
  Missing, spurious, pogrešan, state-only i stop-race putevi invalidiraju run;
  full literalni v1.2 trace sa `%.9g` pragom i `ANOMALY_ENTERED` parom prolazi.
- Firmware i host dijele eksplicitnu `1e-3` toleranciju za teorijski
  nenegativne LOO/DET/tonalness vrijednosti. Tiny negative se clampuje na nulu,
  materijalno negativan score se odbija. Host dodatno provjerava anchorovan DET,
  `lo=0`, RMS/DC/peak fiziku i nenegativne summary/tonalness vrijednosti.
- Summary više nema drugi threshold argument: prag se čita samo iz trackerovog
  verifikovanog `ADAPTTHR`. Import, artifact-open, artifact-close i serial-close
  failure putevi best-effort zamjenjuju `in_progress` status i završavaju
  provenance/summary prije ponovnog podizanja greške.
- Poslije quality rejecta host ne prihvata dalji eksperiment, nego najviše 2,5 s
  samo drenira UART do terminalnog STATE + `FLOW_STOPPED`; pure drain odluka i
  terminal/timeout putevi imaju adversarial testove.
- Politika je verzionisana u `pc/config/asd_quality_policy_v1.json` sa
  `target_anomalies_used=false`. Tonalness proxy i LOO mean/sd/CV/range se
  instrumentiraju, ali njihovi gateovi ostaju `pending_normal_only`; nije
  izmišljen prag iz target anomalija.
- Ciljani testovi poslije svih review korekcija: `61 passed in 1.52s`.
- Svi PC testovi poslije svih review korekcija: `88 passed in 6.85s`.
- ESP-IDF 5.5.5: `ASD_PSD_LIVE=1`, `idf.py reconfigure build` — `PASS`.
  `audio_quality_state.c` i `psd_live.c` su kompajlirani; finalni v1.1 schema
  bin ima `295312 B`, SHA-256
  `2eeeb700dc0dc304dccf038053a07de3ba8c3f15101373e7f79925ccdbf24d25`,
  a najmanja app particija ima 93% slobodno.
- `git diff --check` — `PASS`; anti-pattern grep nije našao stari
  „kalibrišem svejedno”, automatsko pomjeranje centra niti target-anomaly prag.

### Otvoreno poslije Faze 1

- Pločica nije povezana: flash, UART schema provjera i runtime valid/invalid
  kalibracije su `BLOCKED_HARDWARE`, ne `PASS`.
- Host short-read fixture prolazi, ali `audio_read(..., portMAX_DELAY)` može na
  stvarnom prekidu I2S toka ostati blokiran umjesto da vrati short read; timeout
  i liveness ostaju P2 hardverski gap.
- Fizički ventilator nije dostupan: nema realne potvrde `NO_MACHINE` naspram
  validnog fana niti false-reject mjerenja.
- Tonalness i LOO-spread **rejection** gate ostaju namjerno neaktivni dok se
  pragovi ne preregistruju samo iz normalnih podataka. Postojeći LOO-derived
  anomaly threshold ostaje aktivan i to nije isti gate.
