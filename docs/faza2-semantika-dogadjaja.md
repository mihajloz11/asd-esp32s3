# Faza 2 — prisustvo mašine, režim i semantika događaja

**Datum:** 11.08.2026 · **Modul:** [`asd_events.c`](../firmware/esp32s3_asd/main/asd_events.c) /
[`.h`](../firmware/esp32s3_asd/main/asd_events.h) · **Protokol:** `asd-events-v1.0.0`
**Testovi:** [`pc/tests/test_asd_events_c.py`](../pc/tests/test_asd_events_c.py) — 89 testova
**Plan:** [PLAN-NEXT-LEVEL.md](PLAN-NEXT-LEVEL.md), sekcija 4

---

## 1. Tri stvari koje se ne smiju mješati

Ovo je razlog zbog kojeg modul postoji. Do sada je firmware imao samo *stanje*,
pa je „ANOMALIJA" implicitno čitano kao „kvar mašine" — a to je tvrdnja koju
sistem ne može opravdati.

| | Šta je | Primjer | Ko ga daje |
|---|---|---|---|
| **status** | činjenica o toku uređaja | `ANOMALY` | Faza 1, stanja uređaja |
| **događaj** | najslabija tvrdnja koju **postojeći** dokazi podnose | `UNKNOWN_CHANGE` | Faza 2, ovaj modul |
| **uzrok** | zašto se to dogodilo | „selotejp na lopatici" | **niko još** — traži Faze 3, 5, 6 |

Posljedica u kodu: trajno odstupanje od kalibrisanog centra daje status
`ANOMALY` (činjenica) uz događaj `UNKNOWN_CHANGE` (konzervativna tvrdnja).
**Nikad `MECHANICAL_ANOMALY`**, jer bi to bila dijagnoza.

## 2. Hijerarhija odlučivanja

Nivoi se ocjenjuju **strogo u ovom redu**, i nivo koji opali **guši sve ispod
sebe** — jer ulaz nižeg nivoa nema smisla kad je viši prekršen.

```
1. zdravlje senzora     je li signal uopšte vjerodostojan?
2. prisustvo mašine     je li kalibrisana mašina još tu?
3. radni režim          u kojem je normalnom režimu?      <- prazno do Faze 3
4. odstupanje           odstupa li od kalibrisanog centra?
```

**Zašto guši, a ne sabira.** Kad mašina utihne, score i tako skoči — izmjereno
08.08. na demou, sa 10 na 59. Bez gušenja bi uređaj prvo emitovao anomaliju
koja ne postoji, i tek onda zaustavljanje. Zato prozor ispod gate-a prisustva
uopšte ne ulazi u ocjenu odstupanja, a brojač odstupanja se resetuje.

**Nivo 3 je namjerno prazan.** Bez f0 sa confidenceom promjena režima se ne može
razlikovati od kvara. To je jedini razlog zbog kojeg nivo 4 daje
`UNKNOWN_CHANGE`, a ne `SPEED_CHANGED` ili `MECHANICAL_ANOMALY`.

## 3. Taksonomija događaja i kapabiliteti

Cijela taksonomija je zaključana sada, da se serijski ugovor ne mijenja kasnije.
Ali događaji koji traže još nedostupan dokaz **ne mogu se emitovati** —
`asd_event_capability()` to nosi u kodu, a `finish()` degradira svaki
nedozvoljen događaj u `UNKNOWN_CHANGE`. Nije stvar discipline nego mehanizma.

| Događaj | Kapabilitet | Zašto |
|---|---|---|
| `FAN_STOPPED` | **dostupan** | nivo naspram kalibrisane sredine je dovoljan dokaz da mašine nema; ne tvrdi zašto |
| `SENSOR_FAULT` | **dostupan** | Faza 1 već razlikuje klase kvara senzora |
| `UNKNOWN_CHANGE` | **dostupan** | namjerno neinformativan, i zato uvijek pošten |
| `NONE` | **dostupan** | nema šta da se javi |
| `SPEED_CHANGED` | `NEEDS_F0` (Faza 3) | `spd_1/2/3` iz imena fajla ne postoji na uređaju |
| `AMBIENT_NOISE` | `NEEDS_DUAL_CHANNEL` (Faza 5) | pripisati energiju okolini traži drugi kanal |
| `MECHANICAL_ANOMALY` | `NEEDS_TRANSIENT` (Faza 6) | smije se tvrditi tek kad se promjena režima i buka mogu **isključiti** |

## 4. Tabela tranzicija

Deterministička i jedini autoritet. Ostajanje u istom stanju je uvijek
dozvoljeno. `✔` = dozvoljeno, prazno = zabranjeno.

| iz ↓ / u → | `NO_MACHINE` | `CALIBRATION_REJECTED` | `CALIBRATED_NORMAL` | `ANOMALY` | `SENSOR_ERROR` | `RECALIBRATION_REQUIRED` |
|---|---|---|---|---|---|---|
| `NO_MACHINE` | ✔ | ✔ | ✔ | | ✔ | ✔ |
| `CALIBRATION_REJECTED` | | ✔ | | | | |
| `CALIBRATED_NORMAL` | ✔ | | ✔ | ✔ | ✔ | ✔ |
| `ANOMALY` | ✔ | | ✔ | ✔ | ✔ | ✔ |
| `SENSOR_ERROR` | | | | | ✔ | |
| `RECALIBRATION_REQUIRED` | | | | | | ✔ |

**Dva pravila koja tabela nosi:**

1. **`NO_MACHINE → ANOMALY` je zabranjeno.** Bez validne kalibracije nema od
   čega da se odstupa. Isto važi za `CALIBRATION_REJECTED → ANOMALY`.
2. **Iz terminalnog stanja nema izlaza.** `CALIBRATION_REJECTED`,
   `SENSOR_ERROR` i `RECALIBRATION_REQUIRED` apsorbuju svaku dalju opservaciju.
   Tihi nastavak bi bio `warn and continue`, a automatska rekalibracija bi mogla
   naučiti kvar kao normalu ([P10](problemi-i-rjesenja.md#p10)).

Ako bi odluka ipak napravila nedozvoljen prelaz, to je greška u modulu, i
fail-closed odgovor je `SENSOR_ERROR`, ne tiho prihvatanje.

**Vraćanje mašine poslije zaustavljanja** ide u `RECALIBRATION_REQUIRED`, nikad
natrag u `CALIBRATED_NORMAL` — centar se ne pomjera automatski.

## 5. Gate prisustva mašine

```
prisutna  ⟺  rms_dbfs ≥ kalibrisana_sredina − 11,0 dB,  kroz 3 uzastopna prozora
```

Izvedeno **samo iz normalnih podataka**
([`derive_presence_policy.py`](../pc/tools/derive_presence_policy.py)), zaključano u
[`asd_presence_policy_v1.json`](../pc/config/asd_presence_policy_v1.json) uz
`target_anomalies_used=false`.

**Kako je dobijeno 11 dB, i zašto nije sigma račun:**

| Mjereno | Vrijednost | Uloga |
|---|---|---|
| sd nivoa **po klipu** (60 target klipova) | **0,02 dB** | **odbačeno** — DCASE je normalizovao nivo, to je artefakt skupa, ne fizika |
| sd po prozoru unutar klipa | 0,67–0,94 dB | stvarna akustička varijacija |
| sd po **trojki** prozora | 0,65 dB | prava statistika odluke |
| 6σ po trojki | 3,87 dB | **premalo** — lažno bi palilo |
| najgori normalan pojedinačni prozor | −8,32 dB | težak rep raspodjele |
| **najgori normalan pad po trojki** | **−7,90 dB** | source kontrola, 7400 trojki |
| + 3 dB rezerve | **11,0 dB** | usvojeno |

Odluka se donosi po tri uzastopna prozora, pa je mjerodavan minimum po
trojkama, a ne najniži pojedinačni prozor — trojka usrednji rep. Čisti 6σ
račun bi dao 3,87 dB i normalan rad bi sam sebe prijavljivao kao odsutnu mašinu.

**Ograničenje.** Margina je izvedena iz snimaka, ne iz fizičkog ventilatora.
Mora se ponovo izvesti kad ventilator bude dostupan — na stvarnoj mašini nivo
varira sa udaljenošću i opterećenjem, što DCASE normalizacija skriva.

## 6. Šta je pokriveno testovima

89 host testova, `gcc` preko `ctypes`, isti obrazac kao Faza 1:

- **kapabiliteti** — svaki rezervisan događaj je neemitljiv, svaki dostupan je emitljiv;
- **tabela tranzicija** — svih 36 parova stanja provjereno naspram tabele prepisane
  nezavisno u testu, plus zabrana ulaska u `ANOMALY` bez kalibracije i
  neprobojnost terminalnih stanja;
- **hijerarhija** — kvar senzora nadjačava prisustvo i odstupanje; prenizak nivo
  **nije** kvar senzora; clipping u DET ostaje `RECALIBRATION_REQUIRED` kao u Fazi 1;
- **prisustvo** — traži 3 uzastopna prozora, brojač se resetuje na jedan dobar
  prozor, normalan pad od −7,9 dB (najgori izmjereni) **ne** pali događaj,
  gušenje odstupanja pri padu nivoa, vraćanje mašine traži rekalibraciju,
  prisustvo se ne ocjenjuje bez kalibracije;
- **odstupanje** — traži 3 uzastopna prozora, nikad ne tvrdi uzrok, čisti se bez
  izmišljanja događaja, score tačno na pragu je normalan (strogo veće, kao
  `psd_live.c`);
- **determinizam** — isti niz daje identičan niz odluka u svim poljima kroz tri
  ponavljanja; terminalno stanje apsorbuje svaku dalju opservaciju; `NULL`
  argumenti su fail-closed.

## 7. Zatvaranje Faze 2 — 14.08.2026.

Sve četiri preostale stavke su urađene i provjerene na uređaju
([DNEVNIK-NEXT-LEVEL.md](DNEVNIK-NEXT-LEVEL.md), blok B):

1. ✅ `asd_decide()` je **jedini izvor odluke u DET fazi**; ad-hoc brojači iz
   `psd_live.c` su uklonjeni. Faza 1 i dalje drži WAIT/CAL gate-ove — namjerna
   granica, jer tamo još nema kalibracije od koje bi se odstupalo.
2. ✅ `EVENT` nosi `event`, `capability` i `level`.
3. ✅ Protokol bumpovan na `asd-quality-v1.3.0`, parser na
   `physical-fan-v1.6.0`. Uz to su dodani zapisi `PRESENCE` i `TEMPORAL`, koji
   objavljuju politike da ih host može **nezavisno ponoviti** umjesto da vjeruje
   firmveru.
4. ✅ Operatorova istina ostaje u odvojenom zapisu; pritisci tastera i sesije
   idu u `firmware_operator.csv`, nikad u firmware zaključak.

### Šta su Faze 3, 5 i 6 rekle o kapabilitetnom gate-u

Gate je odbijao `SPEED_CHANGED`, `AMBIENT_NOISE` i `MECHANICAL_ANOMALY` jer
dokaza nije bilo. Sve tri faze su te dokaze potražile i **nisu ih našle**:

| događaj | faza koja ga je tražila | ishod |
|---|---|---|
| `SPEED_CHANGED` | 3 — f0 / režim | brzine se ne razlikuju po f0 (34,0 Hz za sve tri) |
| `AMBIENT_NOISE` | 5 — dual-channel | sve tri varijante slabije od jednog kanala |
| `MECHANICAL_ANOMALY` | 6 — tranzijent | +0,0012 AUC, unutar šuma |

Sva tri ostaju neemitljiva, sada **potvrđena mjerenjem**, a ne samo oprezom.
`UNKNOWN_CHANGE` ostaje najjača tvrdnja koju sistem smije izreći.

### Preostalo ograničenje

Margina prisustva od 11 dB je i dalje izvedena iz snimaka. Mora se ponovo
izvesti kad ventilator bude dostupan.
