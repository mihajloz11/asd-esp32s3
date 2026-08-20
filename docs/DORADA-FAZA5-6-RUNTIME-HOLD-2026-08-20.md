# Dorada Faza 5–6: commissioning runtime i `OBSERVATION_HOLD`

Datum implementacije: 2026-08-20  
Status softvera: **implementirano i ciljano host-testirano**  
Status numeričke politike: **DEVELOPMENT / PENDING fizička normal-only validacija**  
Status ESP32 builda i fizičkog testa: **nije potvrđeno u ovoj fazi**

## 1. Šta je riješeno

Uveden je jasan runtime tok:

`SETTLE → CENTER_LEARNING → COMMISSION_DERIVE → COMMISSION_VERIFY → MONITORING`

Time su razdvojene tri ranije pomiješane odgovornosti:

1. centar od 96 PSD obilježja uči se samo iz `CENTER_LEARNING` prozora;
2. apsolutni pragovi `threshold_enter` i `threshold_exit` izvode se iz vremenski kasnijeg normal-only `COMMISSION_DERIVE` bloka;
3. `COMMISSION_VERIFY` samo provjerava već zamrznut profil i ne smije mijenjati ni centar ni pragove.

Svaka faza ima timeout i fail-closed završetak (`REJECTED` ili `ABORTED`). Profil postaje važeći tek poslije uspješnog VERIFY bloka. K1 je poseban razlog odbijanja kalibracije, nije UART/protocol greška.

## 2. Čisti moduli i ugovori

### Runtime profil

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

### Commissioning state machine

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

### Temporalna odluka

Datoteke:

- `firmware/esp32s3_asd/main/asd_temporal.h`
- `firmware/esp32s3_asd/main/asd_temporal.c`
- `pc/config/asd_temporal_policy_v2.json`

Runtime API sada prima oba apsolutna praga:

```c
asd_temporal_update(detector, score, threshold_enter, threshold_exit);
```

Poziv se odbija ako pragovi nisu konačni ili ako ne važi `0 < exit < enter`. Stara scale polja ostavljena su samo kao legacy provenance za postojeći wire/host ugovor i više nisu autoritet odluke. `TEMPORAL` zapis sada dodatno objavljuje `threshold_mode=absolute_profile`, `threshold_enter` i `threshold_exit`.

## 3. Razgovor i spoljašnja smetnja: HOLD, ne lažna dijagnoza

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

## 4. Minimalna firmware i UI integracija

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

## 5. Verifikacija izvršena u ovoj fazi

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

## 6. Šta namjerno još nije proglašeno završenim

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

## 7. Očekivani efekat na problem fan01

Ova dorada sama po sebi ne obećava veću numeričku separaciju dok se ne prikupe novi fizički podaci. Ona uklanja glavne arhitektonske uzroke pogrešne odluke:

- kratki centar više ne određuje i prag;
- razgovor više ne resetuje odstupanje na „normalno”;
- trajno odstupanje poslije razgovora ponovo mora izgraditi alarm;
- enter i exit su odvojeni i auditabilni;
- VERIFY mjeri normalne alarmne epizode na kasnijem vremenskom bloku bez post-hoc podešavanja.

Tek poslije tog zamrznutog normal-only commissioning toka ima smisla porediti koliko su papirić, razgovor i normalan ventilator zaista razdvojeni.
