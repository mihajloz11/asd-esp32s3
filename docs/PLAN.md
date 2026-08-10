# PLAN — gdje smo i šta je sljedeće

**Zadnje ažuriranje:** 09.08.2026 · Ovo je **jedini** dokument koji treba
pročitati da bi se znalo stanje i redoslijed. Ostali dokumenti su detalji.

---

## 1. Gdje smo — u tri rečenice

Model je izabran, izmjeren i prenesen na pločicu; ESP32-S3 se sam kalibriše na
ventilatoru koji nikad nije čuo i sam javlja odstupanje, bez računara.
Benchmark cilj je pređen **za ventilator** (AUC 0,863, pAUC 0,657), ali model
**ne generalizuje** na druge tipove mašina i to je pošteno zapisano.
Najveća preostala rupa nije model nego **dokaz da to radi uz stvaran ventilator,
stvaran kvar i stvarnu buku**.

### Šta je dokazano (brojke, ne utisci)

| | |
|---|---|
| PSD model, ventilator, digitalno | AUC 0,863 ± 0,026 · pAUC(10 %) 0,657 ± 0,062 |
| Račun na S3 | 704 ms na 10 s zvuka → rezerva 14,2× · `dropped=0` |
| PC↔uređaj, DCASE WAV | 9,54e-07 |
| PC↔uređaj, **živi mikrofon** | 1,70e-06 |
| Streaming vs batch na uređaju | bit-identično (razlika 0,0) |
| Samostalni rad | kalibracija 100 s → detekcija → alarm, bez računara |
| Zaustavljena mašina | detektovano u **svim** prolazima |
| Prag osjetljivosti preko zvučnika | −12 dB pouzdano · −18 dB granično · −24 dB ne |
| DCASE anomalija na toj skali | ≈ −30 dB → zato se preko zvučnika ne hvata |

### Šta NIJE dokazano

- Ponašanje uz **fizički ventilator** (dosad se puštao snimak preko zvučnika).
- Lažni alarmi na **duže vrijeme** (najduži test je bio ~6 minuta).
- **Potrošnja** (E5) — INA226 I2C je potvrđen; strujni put još nije spojen.
- Da model radi za bilo šta osim ventilatora (izmjereno da **ne** radi).

---

## 2. Vanjska revizija — šta je provjereno i usvojeno

Nezavisna revizija projekta (09.08.2026) dala je niz nalaza. **Svaki sam
provjerio u repou**; evo presude.

### Tačno i ispravljeno odmah

| Nalaz | Provjera | Stanje |
|---|---|---|
| 4 komita nisu pushovana | `git log origin/master..HEAD` → 4 | ⚠ **treba push** |
| `handoff.md` tvrdi „sve pushovano" | tačno | ✔ ispravljeno |
| Dokumentacija kaže „dvostrani prag", kod ima `s > thr` | tačno | ✔ ispravljeno |
| `hardver-verifikacija.md` još piše „2 uzastopna prozora" | tačno, kod ima 3 | ✔ ispravljeno |
| `odluka-finalni-model.md` status „čeka potvrdu" iako su kriteriji prošli | tačno | ✔ ispravljeno |
| `results.csv` ima dupli red `fan_tiny16_s1/mse/fp32` sa **različitim** brojkama | tačno (0,4652 vs 0,4396) | ⚠ **treba riješiti** |
| Ime `ae_mel` je zbunjujuće — nije autoenkoder | tačno | ✔ preimenovano u `mel1280` |
| „5 seedova" nisu 5 treninga nego 5 grupa kalibracionih podjela | tačno | ✔ dokumentovano u kodu |
| `README.md` star od 18.07., opisuje AE tok | tačno | ⚠ **treba prepisati** |
| `.git` 777 rasutih objekata, 1,24 GiB | tačno | ⚠ čišćenje, nizak prioritet |
| Nema CI-a za 12 postojećih testova | tačno | ⚠ nizak prioritet |
| Reset/rekomit 09.08. | stvaran (216c0ea → b6b2ced), **ništa izgubljeno** | ✔ provjereno |

### Najvrjedniji nalaz — greška u mom planu

Revizija je uočila da moj predlog „odbaci pet najvećih odstupanja po trakama
prije sabiranja" **matematički ne stoji**: Mahalanobisov score nije zbir po
trakama nego kvadratna forma `dᵀ P d` sa punom matricom, i baš unakrsni članovi
nose signal. Isto je uočila da `kanal0 − kanal1` poništava i sam ventilator.

**Oba ispravljena** u [plan-otpornost-na-buku.md](plan-otpornost-na-buku.md), sa
tri ispravne varijante umjesto pogrešne jedne.

### Gdje se ne slažem / precizirano

- **Redoslijed.** Revizija stavlja „kanonska evaluacija" na prvo mjesto. Slažem
  se da je to najveći *metodološki* rizik, ali fizički test je jedini koji može
  promijeniti *zaključak*. Rješenje: idu **paralelno** — kanonska evaluacija ne
  traži hardver, fizički test ne traži računar.
- **„Test nazvan pravi ventilator nije bio fizički ventilator".** Tačno kao
  primjedba na *ime commita* od 08.08.; u dokumentaciji je od početka pisalo da
  se pušta snimak preko zvučnika. Ime commita ostaje kakvo jeste (istorija se ne
  prepravlja), ali se u radu nigdje ne smije pojaviti kao „fizički test".
- Sitne nepodudarnosti u brojanju (53 vs 51 komita, 331 vs 332 fajla) — nebitno.
- **COM port:** revizija kaže COM3, dokumentacija COM4. Trenutno se **nijedan
  port ne vidi** — pločica je odspojena. Provjeriti prije sljedećeg testa.

---

## 3. Redoslijed rada

### A. Fizički ventilator — *jedino što mijenja zaključak rada*

Blokirano na nabavci. Sve ostalo je spremno.

**Treba:** 120 mm PC ventilator + 12 V adapter (~500–800 din) ili stoni koji već
imaš · fiksni nosač za mikrofon (10–20 cm, **ne smije se pomjerati** između
kalibracije i testa).

**Protokol:**
1. `ASD_PSD_LIVE` je već fleširan; provjeri COM port.
2. Kalibracija na ispravnom radu — po jednom sa 100 s i sa 200 s.
3. **Normalan rad 30–60 min** → mjeri se *lažnih alarma na sat*, ne AUC.
4. Ponovljivi i bezbjedni kvarovi, jedan po jedan, sa zapisanim vremenom:
   selotejp na lopaticu (disbalans) · vezica koja lagano struže · djelimično
   pokrivena rešetka · labaviji nosač · gašenje.
5. Više hladnih startova i više sesija (mikrofon se ponovo namjesti) — mjeri se
   ponovljivost kalibracije.
6. Istovremeno snimati WAV + serijski log, da se poslije može ponoviti na PC-u.

**Izvještava se:** lažnih alarma na sat · odziv po tipu kvara · kašnjenje
detekcije · gdje kvar pada na skali −30…−12 dB.

**Treba alat:** ručni mod za `psd_live_demo.py` gdje se rukom označi trenutak
kvara (sad alat sam pušta zvuk i zna gdje je anomalija). Pola sata posla.

### B. Kanonska evaluacija — *najveći metodološki rizik*

Ne traži hardver, može odmah.

1. **Jedan protokol za sve metode**, jedan skript, isti kalibracioni splitovi:
   source normalni uče model · target normalni samo za kalibraciju · target
   anomalije **samo** za konačnu ocjenu.
2. **Razdvojiti tri izvora rasipanja** i imenovati ih u tabelama: trening seed ·
   izbor kalibracionih klipova · bootstrap interval. Sadašnjih „5 seedova" je
   samo drugo od toga.
3. **Jedna kanonska mel implementacija.** Sad postoji pet brojeva za „mel"
   (0,716 · 0,706 · 0,674 · 0,634 · 0,607) iz različitih tokova. Izabrati jednu i
   ponoviti **sva** poređenja identično.
4. Riješiti dupli red u `results.csv` (utvrditi koji je tačan, ne brisati naslijepo).
5. Ponovo napraviti finalnu tabelu: AUC + pAUC, source i target odvojeno.

### C. Otpornost na buku — *PC prvo, firmware tek poslije*

Pun plan: [plan-otpornost-na-buku.md](plan-otpornost-na-buku.md).

Redoslijed: eksperiment na PC-u (umiješati govor i korake, mjeriti **i** lažne
alarme **i** gubitak detekcije) → ugraditi samo ono što se pokazalo → tek na
kraju dvokanalno, jer DIRAM je već na 86 %.

### D. Fizički uređaj i mjerenja koja fale

1. INA226: I2C i registri su potvrđeni → spojiti IN+/IN− i VBS prema
   [šemi povezivanja](sema-povezivanja.md) → izmjeriti **E5 potrošnju**.
   Bez toga je Pareto analiza iz plana rada nepotpuna (tri od četiri ose).
2. Otpornik 220–330 Ω → LED (kod već upravlja GPIO2).
3. Perfboard umjesto jumper žica, rasterećenje kablova, fotografija i šema.

### E. Rad i repozitorij

1. **Uskladiti plan rada sa stvarnošću.** `plan-master-rada.md` još kao doprinos
   br. 2 navodi kvantizacionu studiju — a pobjednik je float32 model bez TFLM-a.
   Doprinos br. 4 („on-device kalibracija") je bio *stretch*, a sad je centralni
   rezultat. Tu listu treba prepisati.
2. Prepisati `README.md` (star od 18.07., opisuje AE tok).
3. Terminologija zaključana: **„za ventilator"**, nikad „za ASD uopšte"; jasno
   razdvojiti *digitalni benchmark* / *preko zvučnika* / *fizički ventilator*.
4. Zaključati verzije zavisnosti (Python raspони su široki; ESP-IDF 5.5.5,
   esp-dsp 1.8.2, esp-nn 1.2.3, esp-tflite-micro 1.3.7 nisu fiksirani u repou).
5. **Pushovati 4 lokalna komita.**
6. Nizak prioritet: CI za 12 testova · `git gc` · izmjestiti ZIP kopije dataseta.

---

## 4. Šta bih uradio sljedeće — po prioritetu

| # | Šta | Traži | Zašto baš to |
|---|---|---|---|
| 1 | **Push 4 komita** | 1 min | rad od danas postoji samo na ovom disku |
| 2 | **Kanonska evaluacija (B)** | PC, nekoliko sati | bez toga finalne tabele u radu nisu odbranjive |
| 3 | **Fizički ventilator (A)** | ventilator | jedino što mijenja zaključak |
| 4 | **INA226 → E5 (D1)** | multimetar | zatvara četvrtu osu Pareto analize |
| 5 | Buka, PC dio (C) | PC, nekoliko sati | odlučuje šta uopšte ide u firmware |
| 6 | Plan rada + README (E1, E2) | pisanje | usklađivanje priče sa rezultatom |

**Ako se bira samo jedno:** stavka 1 pa 2. Prvo traje minut, drugo je jedini
posao koji je i hitan i moguć bez nabavke.

---

## 5. Gdje je šta

| Sadržaj | Fajl |
|---|---|
| Cilj i kriterij uspjeha | [cilj-modela.md](cilj-modela.md) |
| **Ovaj plan** | `PLAN.md` |
| Svi pokušaji sa brojkama (materijal za rad) | [put-do-modela.md](put-do-modela.md) |
| Finalna odluka o modelu + rezerva | [odluka-finalni-model.md](odluka-finalni-model.md) |
| Sva hardverska mjerenja i živi prolazi | [hardver-verifikacija.md](hardver-verifikacija.md) |
| PSD model, detaljno | [istrazivanje-psd-model.md](istrazivanje-psd-model.md) |
| Runde nad scoring backendom | [istrazivanje-preko-0674.md](istrazivanje-preko-0674.md) |
| Otpornost na buku | [plan-otpornost-na-buku.md](plan-otpornost-na-buku.md) |
| Zamke koje su koštale vremena (P1–P14) | [problemi-i-rjesenja.md](problemi-i-rjesenja.md) |
| Hronologija | [dnevnik-projekta.md](dnevnik-projekta.md) |
| Ideje bez roka | [../future-work.md](../future-work.md) |
