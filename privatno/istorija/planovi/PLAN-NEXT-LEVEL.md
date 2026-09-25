# PLAN NEXT LEVEL — pouzdaniji fan ASD

> **ISTORIJSKI ZAKLJUČANI PLAN — izvršen ili svjesno zatvoren 14.08.2026.**
> Ishodi pojedinih faza su u [DNEVNIK-NEXT-LEVEL.md](../../dnevnici/DNEVNIK-NEXT-LEVEL.md),
> a aktuelni fizički handoff u [PREOSTALO.md](../../PREOSTALO.md). Stavke ispod su
> kriteriji po kojima je rad izveden, ne današnja TODO lista.

**Status:** zatvoren kao plan izvršenja
**Zaključan:** 09.08.2026.  
**Polazna tačka:** kanonski razvojni protokol `canonical-evaluation-v1.1.0`  
**Hardver:** pločica trenutno nije povezana; PC rad i build nisu blokirani, flash i stvarna uređajna mjerenja jesu.

## 1. Cilj i granica tvrdnje

Cilj je nadograditi postojeći normal-only, first-shot PSD/Mahalanobis sistem tako
da pouzdanije:

1. odbije nevalidnu kalibraciju;
2. odvoji stanje senzora i prisustvo mašine od anomalije;
3. prepozna normalne režime rada bez automatskog učenja mogućeg kvara;
4. brže i stabilnije reaguje na trajne i impulsivne promjene;
5. iskoristi near/far kanal za buku;
6. izvještava metrike relevantne stvarnoj upotrebi.

Ovaj plan ne mijenja istorijski kanonski evaluator v1.1.0. Novi kandidati idu u
zaseban developmental namespace/cache/output. Target anomalije ne smiju birati
feature, prag, RPM opseg, rolling parametre, dual-channel varijantu ni teacher
backend. Sve target-anomaly brojke ostaju razvojne zbog ranijeg model-selection
biasa. Ne postoje fizički fan ni nezavisne sesije, pa se ništa iz ovog PC rada
ne smije nazvati potvrdom stvarnog kvara.

## 2. Phase 0 — dokumentaciono mapiranje — ZAVRŠENO

### Pregledani obrasci

- firmware tok: `firmware/esp32s3_asd/main/psd_live.c/.h`;
- audio health API: `audio_i2s.c/.h`, `mic_test.c`, `psd_verify.c`,
  `live_capture.c`;
- PC↔C i host-C testovi: `pc/tests/test_psd_features_c.py`,
  `pc/tests/test_calib_c.py`;
- kanonska granica podataka/provenance: `pc/tools/evaluate_canonical.py`,
  `docs/model/kanonska-evaluacija.md`;
- stari signalni pokušaji: `bench_periodicity.py`, `bench_research*.py`,
  `bench_modes.py`, `check_fault_type.py`;
- fizički capture/parser: `pc/tools/physical_fan_experiment.py`.

### Dozvoljeni postojeći API-ji

Firmware:

- `audio_read`, `audio_dropped_samples`, `audio_raw_peak`,
  `audio_raw_peak_reset`;
- `asd_psd_stream_reset`, `asd_psd_stream_push_hop`,
  `asd_psd_stream_finish`, `asd_psd_score`;
- standardni C `sqrtf`, `log10f`, `fabsf`, `isfinite`, `memcpy`, `memset`;
- ESP-IDF `esp_timer_get_time`, `ESP_LOGI/W/E`, `gpio_set_level`,
  `vTaskDelay`.

PC:

- NumPy, SciPy signal, SoundFile, scikit-learn, pytest;
- source-only LedoitWolf/Mahalanobis i manifest obrazac iz kanonskog evaluatora;
- `ctypes` + host compiler obrazac iz postojećih C testova.

### Već pokušano — ne ponavljati pod novim imenom

- clip-level envelope PSD (`AUC≈0,511`) i njegovo spajanje sa PSD-om
  (`periodic≈0,827`, slabije od `psd_shape`);
- mel temporalna autokorelacija, modulacioni spektar i delta statistike;
- stari mel-diagonalni pooled/oracle/kmeans režimski modeli;
- slijepi rank/score ensemble sa slabijim mel scoreom;
- prosto near-far oduzimanje;
- trimovanje navodnih pojedinačnih doprinosa traka u punoj kvadratnoj formi.

## 3. Faza 1 — fail-closed kalibracija i osnovna stanja

### Implementacija

1. Napraviti čisti host-testabilni C modul za quality/state odluke, odvojen od
   I2S beskonačne petlje.
2. Izdvojiti zajedničke audio metrike iz obrasca `mic_test.c`: broj pročitanih
   uzoraka, RMS/dBFS, peak, clipping count, zero/stuck count i DC.
3. Za svaku fazu mjeriti `dropped_delta`, ne samo kumulativni counter, po obrascu
   iz `psd_verify.c` i `live_capture.c`.
4. Fail-closed odbiti WAIT/CAL za: nepotpun read, nefinite vrijednosti, mrtav ili
   zaglavljen signal, prenizak nivo, clipping iznad unaprijed fiksirane granice
   i bilo koji `dropped_delta > 0`.
5. Instrumentirati tonalnost i LOO spread. Pragove koji nisu sigurnosno
   očigledni prvo izvesti samo iz normalnih source/target-normal podataka i
   zapisati u verzionisani JSON; ne koristiti target anomalije.
6. Uvesti eksplicitna stanja:

```text
NO_MACHINE
CALIBRATION_REJECTED
CALIBRATED_NORMAL
ANOMALY
SENSOR_ERROR
RECALIBRATION_REQUIRED
```

7. Dodati stabilan ASCII serijski ugovor `QUALITY`, `STATE`, `EVENT`; bumpovati
   verziju fizičkog protokola i parser, uz odvojena polja za operatorovu istinu
   i firmware zaključak.

### Reference za kopiranje

- clipping/zeros/RMS/DC: `mic_test.c`;
- dropped delta: `psd_verify.c`, `live_capture.c`;
- host-C test: `pc/tests/test_calib_c.py`;
- parser/provenance: `physical_fan_experiment.py` i njegovi testovi.

### Kriteriji prolaza

- silence, clipping, stuck-zero, short-read, NaN/Inf i dropped fixtures završavaju
  u tačno definisanom reject/fault stanju;
- nijedan reject put ne ulazi u CAL ili DET;
- validni normalni fixtures zadržavaju stari feature/score;
- parser čuva state/event/quality odvojeno od operator condition;
- svi PC testovi prolaze;
- ESP-IDF build prolazi bez pločice;
- flash/UART/runtime ostaju `BLOCKED_HARDWARE`.

### Zabranjeni anti-patterni

- `warn and continue`;
- anomaly score kao dokaz zdravog mikrofona;
- prag iz target anomalija;
- state logika direktno u I2S petlji bez unit testova;
- automatska rekalibracija ili pomjeranje centra.

## 4. Faza 2 — prisustvo fana, režim i semantika događaja

### Implementacija

1. Napraviti hijerarhiju `sensor health → machine present → operating regime →
   deviation`.
2. Uvesti konzervativne događaje:

```text
FAN_STOPPED
SPEED_CHANGED
MECHANICAL_ANOMALY
AMBIENT_NOISE
SENSOR_FAULT
UNKNOWN_CHANGE
```

3. Dok faze 3/5/6 ne daju dokaz, nepoznatu promjenu emitovati kao
   `UNKNOWN_CHANGE`/`RECALIBRATION_REQUIRED`, ne kao dijagnozu kvara.
4. Operator ground truth ostaje zaseban zapis i nikada se ne popunjava iz
   firmware predikcije.

### Verifikacija

- deterministička tabela svih dozvoljenih i zabranjenih tranzicija;
- unit testovi za svaku tranziciju i rollback;
- nema ulaska u normal/anomaly stanje bez validne kalibracije;
- dokumentacija jasno razlikuje status, događaj i uzrok.

## 5. Faza 3 — f0/režim i order-normalized PSD na PC-u

### Implementacija

1. Napraviti zaseban `advanced` modul/evaluator; ne mijenjati canonical v1.1.0.
2. Implementirati estimator fundamentalne frekvencije sa confidence vrijednošću
   koristeći Welch PSD i unaprijed zaključan harmonic-summation/peak postupak.
3. `spd_1/2/3` koristiti samo kao kategorije za provjeru konzistentnosti; bez
   poznatog broja lopatica i ground trutha ne tvrditi stvarni RPM.
4. Napraviti order-warp PSD i režimske centre; f0 opseg, broj harmonika i prag
   confidencea zaključati source-normal validacijom.
5. Tek poslije zamrzavanja jednom izračunati target-anomaly AUC/pAUC i objaviti
   sve unaprijed navedene varijante, uključujući negativne rezultate.

### Kriteriji prolaza

- stabilan f0/confidence na normalnim klipovima;
- mjerljivo razlikovanje `spd_1/2/3` iz normalnih klipova;
- manje normalno rasipanje između režima bez pada fan AUC/pAUC izvan unaprijed
  definisane tolerancije;
- isti split manifest za sve kandidate;
- potpuni provenance/cache hashovi.

## 6. Faza 4 — rolling score i vremenska odluka

### Implementacija

1. PC referenca: 10 s kontekst, odluka svakih 2,56 s i 5,12 s.
2. Implementirati i odvojeno izvještavati:
   - postojeći 3-consecutive baseline;
   - EWMA;
   - CUSUM;
   - ulazni/izlazni prag (histereza);
   - fast alarm samo za ekstremni, unaprijed definisan score.
3. Parametre zaključati na normalnim/sintetičkim source fixtureima, bez target
   anomalija.
4. Za firmware koristiti kružni bafer per-segment band-power doprinosa, ne veliki
   10-sekundni PCM bafer.

### Kriteriji prolaza

- rolling 10 s feature numerički odgovara batch referenci;
- nema regresije PC↔C;
- prijavljeni latency/recovery nad fixture sekvencama;
- preklapajući prozori nisu bootstrap jedinice;
- RAM/build mjerenja označena kao build procjena dok nema pločice.

## 7. Faza 5 — dual-channel near/far

### Unaprijed fiksne varijante

1. near-only canonical PSD baseline;
2. log-PSD near/far odnos;
3. cross-spectrum/coherence descriptor;
4. far-derived noise mask pa PSD nad očišćenim near kanalom.

### Pravila

- nema `channel0-channel1` baselinea kao navodnog univerzalnog poništavanja buke;
- sve četiri varijante koriste iste kohorte/splitove;
- izbor se radi source-side/noise-normal kriterijima, ne fan target anomalijama;
- objaviti korelaciju, normalni false-positive shift i sve rezultate.

### Kriteriji prolaza

- poboljšanje noise robustness bez značajnog gubitka čistog near signala;
- nema target leakagea;
- zaseban cache/provenance namespace;
- za deployment eksplicitno zapisati da stvarni dual-mic zahtijeva dodatni
  hardver i RAM verifikaciju.

## 8. Faza 6 — slow PSD + fast transient događaj

### Implementacija

1. Slow put ostaje postojeći PSD/Mahalanobis.
2. Fast put radi na kratkim okvirima i testira samo nove event-level feature-e:
   spectral flux, frame crest/impulsivity, spectral/envelope kurtosis i kratke
   envelope-band energije.
3. Fast put dobija vlastiti normal-only prag i event izlaz.
4. Izlazi su `TONAL_DRIFT`, `TRANSIENT_IMPACT`, `BOTH`; scoreovi se ne sabiraju
   naslijepo.

### Kriteriji prolaza

- regression fixtures za periodične udare, ton/harmonike i broadband promjenu;
- posebno mjeriti false event rate na normalnim klipovima;
- sintetički kvar se ne naziva fizičkim kvarom;
- nema ponavljanja ranijeg clip-level envelope/scalar ansambla.

## 9. Faza 7 — frozen PC teacher kao upper bound

### Feasibility gate

1. Inventarisati lokalne modele/dependencies/licence i procijeniti download,
   disk, RAM i runtime prije instalacije.
2. Ako je razumno, pokrenuti zamrznuti BEATs/EAT embedding bez fine-tuninga;
   normal-only Mahalanobis i kNN su unaprijed navedeni backendovi.
3. Teacher je PC upper bound, ne ESP32 kandidat.
4. Distilacija se planira samo ako teacher daje velik, ponovljiv dobitak na
   unaprijed definisanom protokolu i robustnosti na buku.

### Stop uslov

- Ako teacher ne nadmaši PSD ili je dobitak mali/nekonzistentan, zabilježiti
  negativan rezultat i završiti fazu bez distilacije.

## 10. Faza 8 — pouzdanije metrike, CI i završni izvještaj

### Implementacija

- event/session schema: false alarms/hour, missed events, first-alarm latency,
  recovery latency, calibration rejection rate;
- agregacija po fizičkom ventilatoru i nezavisnoj sesiji kada podaci postoje;
- bootstrap jedinica je fan/sesija, ne overlapping prozor;
- GitHub Actions za PC testove, schema i C parity;
- commitovati canonical/advanced izvore i rezultate uz tačan provenance;
- uskladiti `README`, `PLAN`, hardver i rad sa nivoima dokaza.

### Završna verifikacija

- svi testovi i build prolaze;
- grep anti-pattern provjera;
- nijedan dokument ne miješa digitalni, zvučnik/mikrofon i fizički fan;
- hardverski nedokazane stavke ostaju eksplicitno otvorene.

## 11. Hardverski handoff kada pločica/fan budu dostupni

Redom: reconfigure/build → flash → UART schema → valid/invalid calibration →
runtime dropped/RAM/latency → stabilni normalni baseline → bezbjedno označeni
događaji → false alarms/hour i latency. Bez fizičkog fana ne postoji validna
završna potvrda, bez obzira na broj PC testova.
