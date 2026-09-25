# Uputstvo 4 — projekat u sedam koraka

Jedan fajl, jedan redoslijed. Pročitaš ga i znaš projekat; istim redom vodiš
profesora kroz njega.

**Svaki korak ima tri stvari:**

- **Šta je urađeno** — to učiš
- **Otvori** — fajl koji pokazuješ na ekranu
- **> Kaži** — rečenica koju izgovaraš

Brojke su iz revizije 06.09.2026. Ako ti treba dublje: hronologija u 11 etapa je
u [`UPUTSTVO-1`](UPUTSTVO-1-KAKO-JE-NASTAO-PROJEKAT.md), teorija u
[`UPUTSTVO-2`](UPUTSTVO-2-TEORIJA-OD-NULE.md).

> Ne šalji profesoru `privatno/planovi/sazetak-za-mentora.md` — odbačeni prijedlog teme iz jula.

---

## Prije sastanka

```powershell
.\.venv\Scripts\python.exe -m pytest pc/tests -q
```

Očekuješ **478 passed**. Ponesi pločicu na stolu, skrati pola objašnjenja.

**Otvorena rečenica, nauči napamet:**

> „Pločica ESP32-S3 sluša ventilator preko jednog mikrofona, prvih nekoliko
> minuta uči kako taj konkretan ventilator zvuči kad je ispravan, i poslije toga
> sama, bez računara, javlja kad se zvuk trajno promijeni."

---

## 1. Postavka — problem i cilj

**Šta je urađeno.** Nadzor stanja mašine po zvuku, **nenadgledano**: podaci o
kvarovima ne postoje unaprijed, pa se uči samo na normalnom radu. Meta nije
server nego mikrokontroler od par evra. Kriterij je postavljen na početku i
nikad mijenjan: **AUC ≥ 0,80** na ventilatoru, uz protokol bez curenja podataka.

Oprema: ESP32-S3, mikrofon INMP441, ventilator, sve na protobordu MB-102.
Podaci za učenje: DCASE 2026 dev skup, 990 normalnih snimaka ventilatora.

**Otvori:** [`cilj-modela.md`](../../docs/cilj-modela.md)

> **Kaži:** „Kriterij AUC ≥ 0,80 je zapisan na početku i nije mijenjan poslije
> rezultata."

---

## 2. Model — kako je nastao

**Šta je urađeno.** Četiri koraka, i ovo je najjači dio priče:

1. Počeo sam **autoenkoderom** na log-mel obilježjima. Stao na **AUC 0,674**.
2. Dvanaest varijanti scoring backenda dalo je oko **+7 poena** i stalo.
3. Onda sam promijenio **front-end, ne model**: umjesto STFT 1024 + 128 mel
   traka → **Welch PSD sa FFT 8192, 96 logaritamskih traka**. → **0,8556**.
4. Radi jer je to fizika, ne ML: ventilator je rotaciona mašina i potpis su mu
   **uske harmonijske linije** obrtne frekvencije. Stari front-end ima razmak
   binova 15,6 Hz i razmaže ih; novi ima **1,95 Hz** i razdvaja ih.

Kako je posao podijeljen: na PC-u se unaprijed nauči samo *oblik varijacije*
zvuka ventilatora uopšte — kovarijansa 96×96 iz 990 normalnih snimaka. Na licu
mjesta se uči *centar* (kako baš ovaj primjerak zvuči) i prag.

**Otvori:** [`put-do-modela.md`](../../docs/put-do-modela.md) — svi pokušaji,
uključujući neuspjele

> **Kaži:** „Obilježje nosi više od backenda. Dvanaest promjena scoring-a dalo
> je sedam poena, jedna promjena front-enda petnaest."

---

## 3. Firmware — kako to živi na pločici

**Šta je urađeno.** Prati put signala, tim redom otvaraj fajlove:

| Fajl | Šta radi |
|---|---|
| [`audio_i2s.c`](../../firmware/esp32s3_asd/main/audio_i2s.c) | mikrofon → I2S sa DMA → ring buffer |
| [`psd_features_c.c`](../../firmware/esp32s3_asd/main/psd_features_c.c) | proboj iz koraka 2, prepisan u C: FFT 8192, Welch, 96 traka |
| [`psd_model_data.h`](../../firmware/esp32s3_asd/main/psd_model_data.h) | naučena matrica 96×96, generisana sa PC-a |
| [`psd_live.c`](../../firmware/esp32s3_asd/main/psd_live.c) | glavna petlja: prozor → obilježje → Mahalanobis skor → odluka |
| [`asd_commissioning.c`](../../firmware/esp32s3_asd/main/asd_commissioning.c) | `SETTLE → CENTER_LEARNING → DERIVE → VERIFY → MONITORING` |
| [`asd_interference.c`](../../firmware/esp32s3_asd/main/asd_interference.c) | kapija pouzdanosti prozora |
| [`asd_temporal.c`](../../firmware/esp32s3_asd/main/asd_temporal.c) | histereza 1,0/0,7 + tri uzastopna prozora |

Cijeli lanac od zvuka do alarma je **716 ms po prozoru od 10 s** — rezerva oko 14×.

> **Kaži:** „Uređaj nikad nije čuo ovaj ventilator, a globalni model nikad nije
> vidio nijednu anomaliju. Prag se izvodi iz normalnih prozora i **zamrzava
> prije** nego što se pusti bilo kakva pobuda."

---

## 4. Problemi koji su promijenili sistem

**Šta je urađeno.** Ovo je dio koji projekat čini ozbiljnim — nijedan problem
nije obrisan, svaki je zapisan sa simptomom, uzrokom i dokazom.

**Najvažniji, FAN01 od 16.08.** Prvi pravi ventilator. Model je **odlično
rangirao** promjenu protoka: medijana 876 → 29 899. Ali **prag nije radio** —
54 od 60 normalnih prozora bilo je iznad praga. Rangiranje skoro savršeno,
upotrebljivost nula.

Iz toga je nastao ciklus od **osam faza dorade** u kojima se skoro ništa nije
mijenjalo u modelu, a skoro sve u tome *kako se od skora pravi odluka*: K1
kapija kvaliteta kalibracije, odvojeni enter/exit pragovi, `OBSERVATION_HOLD`,
histereza, trajni profil u NVS.

**Dva nalaza suprotna očekivanju:**

- Skor može **pasti** kad se pojavi anomalija, ne samo porasti — model mjeri
  udaljenost od naučenog, ne jačinu zvuka. Zato je prag dvostran.
- EWMA i CUSUM, udžbenički alati za detekciju pomjeraja, **pogoršali** su sistem
  (0 → 5,4 lažnih alarma/h) — pravljeni su za mali trajni pomjeraj, a ovdje
  treba odbaciti veliku kratku pobudu.

**Otvori:** [`problemi-i-rjesenja.md`](../../docs/problemi-i-rjesenja.md) — baza P1–P28

> **Kaži:** „Najvažnija pouka cijelog rada: **AUC nije uređaj.** Imao sam model
> sa AUC 0,86 koji je pravio 90 % lažnih alarma."

---

## 5. Testovi — kako se išta dokazuje

**Šta je urađeno.** Najčešći uzrok pada tačnosti pri prenosu modela na
mikrokontroler je da PC i uređaj računaju obilježja *malo* drugačije. Umjesto
dvije implementacije koje se porede, napisana je **jedna** — C moduli se
kompajliraju u `.dll` i testiraju iz Pythona kroz `ctypes`.

Izmjereno slaganje PC ↔ uređaj na živom mikrofonu: **1,70·10⁻⁶**.

Osim toga: strogi parser UART protokola, zamrznuti fizički runovi kao regresija,
provjera da se politike u `pc/config` poklapaju sa firmverom, i grep kapije u CI
koje obore build ako se ciljna anomalija pojavi u fitu.

**Otvori:** [`pc/tests/test_psd_features_c.py`](../../pc/tests/test_psd_features_c.py)

> **Kaži:** „478 testova prolazi — ali to je softverski dokaz. Fizički dokaz su
> dvije probe iz sljedećeg koraka."

---

## 6. Rezultati — dvije završne probe

**Šta je urađeno.** Devet runova 26–27.08., dva validna, **isti binarni fajl** u oba.

**Run B, ton 1 kHz — prošao.** Uređaj se sam kalibrisao, sam izveo prag
21 809,51, podigao `ANOMALY` poslije tri uzastopna prekoračenja i
`ANOMALY_SUSTAINED` na dvanaestom alarmnom prozoru. Osnova 7 085 → ton 23 574.

**Run A, papirić — FAIL.** Prag 8 084,49. Medijane izazvane promjene **30 255,
62 344 i 19 844** naspram osnove **1 146** — promjena se jasno vidi u skoru. Ali
GUIDED25 je FAIL: detektovan **1 od 3 bloka**. U prva dva bloka kapija
pouzdanosti je odbila tri od četiri prozora kao nestabilne, pa se nikad ne
skupi tri uzastopna prekoračenja.

**Govor i vrata nisu digli alarm** iako su im skorovi bili visoki — odbijeni kao
nestabilni. Tražena osobina, ali četiri prozora govora i dva vrata nisu dokaz
opšte otpornosti.

**Otvori:** [`rezultat-finalna-validacija-2026-08-27.md`](../../docs/rezultat-finalna-validacija-2026-08-27.md)

> **Kaži:** „Ton je prošao, papirić je FAIL. Model je promjenu vidio, pravilo
> odlučivanja je nije propustilo dalje."

---

## 7. Ograničenja — reci ih sam, prije nego što pita

- **Nije dokazano da je detektovana promjena mehanički kvar.** Papirić i ton su
  kontrolisane promjene; jedan mikrofon to ne može tvrditi.
- Jedan ventilator, jedna prostorija. Nema nezavisnog finalnog testa — razvojne
  rezultate sam vidio prije konačnog izbora modela.
- Pragovi su još `DEVELOPMENT`; profil se ne čuva, poslije restarta ide novo učenje.
- Nisu fizički provjereni: prekid I2S, nestanak napajanja, potrošnja, dug rad.
- Taster i LED nisu zalemljeni; INA226 strujni put nije završen.
- **Osam PSD traka je praznih** i unose osjetljivost na pojačanje. Nađeno mojom
  revizijom 06.09., potvrđeno numerički, uticaj na tačnost nije izmjeren —
  **model nisam mijenjao pred predaju.**

**Otvori:** [`PREOSTALO.md`](../planovi/PREOSTALO.md)

> **Kaži:** „Zadnju stavku sam našao sam, pregledom sopstvenog rada pred predaju.
> Nisam je krpio da rezultat izgleda bolje."

---

## Brojke — jedina lista koju citiraš

| Šta | Koliko | Obim |
|---|---|---|
| Razvojni AUC, fan | 0,8556 ± 0,0240 | 10 prozora, 20 podjela |
| Polazna tačka prije proboja | 0,674 | log-mel front-end |
| Obrada na uređaju | ~716 ms po prozoru od 10 s | samo obilježje i ocjena |
| Kalibracija | ~13,57 min, pun postupak | ne 2 min — to je samo centar |
| Run A, papirić | 1 146 → 30 255 / 62 344 / 19 844 | **GUIDED25 FAIL**, 1 od 3 bloka |
| Run B, ton | 7 085 → 23 574 | alarm i `SUSTAINED` |
| Slaganje PC ↔ uređaj | 1,70·10⁻⁶ | živi mikrofon |
| Testovi | 478 prošlo | softverski dokaz |
| Master rad | 42 strane, 20 tabela, 12 referenci | obje varijante pisma |

---

## Šta ne smiješ reći

| ❌ | ✅ |
|---|---|
| „Detektuje kvar." | „Detektuje **trajnu promjenu zvuka**. Da je to kvar nije dokazano." |
| „Obje probe su prošle." | „Ton je prošao, **papirić je FAIL** — 1 od 3 bloka." |
| „Otporan je na buku." | „Četiri prozora govora i dva vrata bez alarma. Mali uzorak." |
| „PSD je bolji za ovakvu detekciju." | „Bolji je **za ventilator**. Preko svih sedam mašina je lošiji." |
| „478 testova prolazi, znači radi." | „To je softverski dokaz, ne fizički." |

---

## Pitanja koja će postaviti

**„Zašto papirić nije detektovan?"** — Kapija pouzdanosti je odbila tri od četiri
prozora. Skorovi su bili 30 255 i 62 344 naspram osnove 1 146, dakle model je
promjenu vidio. Papirić se drži rukom, ali to nisam izolovao kao jedini uzrok.

**„Znači kapija je prestroga?"** — Moguće. Ali ista kapija je razlog što govor i
vrata nisu digli lažni alarm. Pragovi su zamrznuti prije pobuda i nisam ih dirao
da bi papirić prošao.

**„Zašto FFT 8192, to je skupo?"** — Jer harmonike ventilatora traže tu
rezoluciju. I nije ispalo skupo: 716 ms na 10 s zvuka.

**„Šta bi uradio drugačije?"** — Ranije bih mijenjao front-end. Držao sam log-mel
kao nedodirljiv jer je bio verifikovan — a verifikacija dokazuje da je
implementacija tačna, ne da je izbor dobar.

**„Znači, radi?"** ← zamka, ne odgovaraj sa „da"
„Radi u smislu da se sam kalibriše na ventilatoru koji nikad nije čuo, sam izvede
prag i digne alarm na trajnu promjenu. Ne radi kao upotrebljiv proizvod: jedna od
dvije probe je FAIL, ne znam da li je promjena kvar, i nisam testirao dug rad."

---

## Pitanja za profesora

1. **Komisija** — predsjednik i član za KDI/KWD.
2. **Izjava o čestitosti** — obrazac iz uputstva v8 sadrži izjavu o nekorišćenju
   alata za generisanje sadržaja, a AI je korišćen u sastavljanju teksta. Kako da
   se formuliše. *Ovo otvori sam.*
3. **Uslov publikacije** — da li TELFOR rukopis zadovoljava ili treba Zbornik FTN.
