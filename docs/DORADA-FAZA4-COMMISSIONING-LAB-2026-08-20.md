# Faza 4: normal-only commissioning i PC feature laboratorija

Datum: 2026-08-20

Status: `DEVELOPMENT/PENDING_PHYSICAL_VALIDATION`

Opseg: isključivo novi PC razvojni alati, sintetički testovi i ovaj dokument

## Ishod

Implementiran je razvojni tok koji razdvaja učenje centra, izvođenje pragova i
vremenski kasniju provjeru. Nijedan broj iz ranijeg fizičkog testa nije ugrađen
kao podrazumijevani prag. Target anomalija ne može učestvovati u fitu, izboru
feature-a ili izvođenju pragova; može se otvoriti samo kao readout nakon provjere
zamrznute politike.

Ova faza ne mijenja firmware, fizički host, kanonski evaluator, postojeće
rezultate ni deployment konfiguraciju. Deployment konfiguracija se namjerno ne
generiše dok novi normal-only i skraćeni fizički test ne daju nezavisnu potvrdu.

## Granica prema live firmwareu

Izlaz ove PC laboratorije nije ulaz u isti fizički run. DEVELOPMENT firmware
nema `SETTHR` komandu i ne učitava laboratorijski profil iz NVS-a. To je
namjerna zaštita od post-hoc podešavanja: live GUIDED25 run koristi unaprijed
određeni `psd_shape` p99/p75 pragovni par, a laboratorija samo procjenjuje
alternativne kandidate iz sačuvanog research sidecara.

Ako normal-only DERIVE, nezavisni VERIFY i kasniji frozen readout podrže drugi
kandidat, on se prenosi tek kroz verzionisanu firmware/policy izmjenu i novi
preregistrovani fizički retest. Trenutni run se nikad ne prepravlja njegovim
rezultatom.

## Novi fajlovi

- `pc/tools/evaluate_fan_noise_candidates.py` — normal-only feature laboratorija,
  candidate manifest, izolovani cache, model bundle i zaključani target readout;
- `pc/tools/derive_commissioning_policy.py` — hronološko izvođenje i izbor
  apsolutnih `T_enter`/`T_exit` pragova;
- `pc/tests/test_fan_noise_development.py` — sintetički fixture testovi granica
  podataka, faza, cache-a i frozen-policy readout-a;
- `docs/DORADA-FAZA4-COMMISSIONING-LAB-2026-08-20.md` — ovaj zapis.

## Zaključani tok podataka

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

## Ulazni ugovor za feature laboratoriju

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

## Feature kandidati

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

## Kandidati za prag i način izbora

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

## Target-anomaly zaštita

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

## Cache, manifest i provenance

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

## Pokretanje

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

## Verifikacija ove faze

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

## Šta ostaje PENDING

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
