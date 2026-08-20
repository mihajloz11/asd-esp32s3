# Dorada Faza 7–8: audio liveness i verzionisani storage profil

**Datum:** 20.08.2026.  
**Status koda/builda:** implementirano i host-testirano; `ASD_PSD_LIVE` build PASS.  
**Fizički status:** prekid I2S-a, restart i nestanak napajanja nisu još testirani
na pločici i ostaju `PENDING_HARDWARE_RUNTIME`.

## Faza 7 — šta je promijenjeno

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

## Faza 8 — šta je promijenjeno

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

## Dokazi

```text
pytest sedam ciljanih F7/F8/integration modula: 272 passed
ESP-IDF 5.5.5 ASD_PSD_LIVE reconfigure build: PASS
esp32s3_asd.bin: 0x55620 B (349728 B), 92% app particije slobodno
git diff --check: bez whitespace greške (samo CRLF upozorenja na Windowsu)
```

Host-C test pokriva round-trip, CRC korupciju, fingerprint mismatch, NaN,
neispravne pragove, truncation/oversize i schema/ownership source guard. Literal
v1.5 test pokriva oba nova audio razloga i očekivani `SENSOR_ERROR`.

## Šta ostaje za fizički test

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
