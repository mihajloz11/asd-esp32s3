# Akustička detekcija anomalija na ESP32-S3

## 1. Cilj i realizovani sistem

Cilj je lokalno otkrivanje održane promjene zvuka ventilatora, poslije
upoznavanja njegovog normalnog rada u konkretnoj postavci.

- **Hardver:** ESP32-S3 i jedan digitalni mikrofon INMP441.
- **Računar:** razvoj obilježja, učenje globalne statistike i evaluacija.
- **Uređaj:** prikupljanje zvuka, lokalna kalibracija, računanje ocjene i alarm.
- **Značenje alarma:** zvuk odstupa od naučene normale; uzrok nije utvrđen.

![Od učenja na računaru do odluke uređaja](../../photos/sl_sistem.png)

## 2. Podaci i model

- **DCASE 2026, ventilator:** globalna statistika iz 990 normalnih source snimaka.
- **Opis zvuka:** 96 PSD-shape vrijednosti po klipu od približno 10 s.
- **Model:** standardizacija + Ledoit–Wolf kovarijansa + Mahalanobis ocjena.
- **U firmware-u:** sredine, standardne devijacije i matrica preciznosti.
- **Na lokalnom ventilatoru:** centar normale i pragovi za odluku.

Model uči normalan zvuk. Anomalni snimci služe evaluaciji; razvojni rezultati
nisu isto što i potpuno nezavisna završna provjera.

## 3. Obrada zvuka na uređaju

**Mikrofon → I2S → PCM → Welch spektar → 96 vrijednosti → score**

| Korak | Postavka i uloga |
|---|---|
| Uzorkovanje | 16 kHz; digitalni uzorci zvuka |
| Spektralna obrada | Hann prozor, FFT 8192, pomak 4096 uzoraka |
| Usrednjavanje | Welch: prosjek spektara preklopljenih segmenata |
| Obilježja | 96 logaritamski raspoređenih traka, približno 10 Hz–4 kHz |
| PSD-shape | logaritmovanje snage i oduzimanje sredine opisa |
| Ocjena | odstupanje standardizovanog opisa od lokalnog centra |

Naglasak je na **obliku spektra**. Uklanjanje zajedničkog nivoa smanjuje
uticaj ukupnog pojačanja, ali ne uklanja uticaj položaja mikrofona i okoline.
Obrada se obavlja postepeno, bez čuvanja cijelog desetosekundnog snimka.

## 4. Lokalna kalibracija i odluka

Za prikazani protokol GUIDED25 priprema koristi odvojene blokove normalnog rada:

| Faza | Broj prozora | Uloga |
|---|---:|---|
| CAL | 10 | lokalni centar i provjera stabilnosti normale |
| DERIVE | 44 | izvođenje ulaznog i izlaznog praga |
| VERIFY | 22 | provjera normale sa već određenim pragovima |

- Poslije pripreme centar i pragovi ostaju zamrznuti tokom nadzora.
- **Alarm:** 3 uzastopna pouzdana prozora iznad ulaznog praga.
- **HOLD:** nepouzdan prozor prekida niz; postojeći alarm ostaje zadržan.
- **Oporavak:** pouzdan prozor na ili ispod nižeg izlaznog praga.

Visok score i konačni alarm nisu ista stvar. Provjera pouzdanosti smanjuje
reakciju na nestabilna posmatranja, ali može odložiti otkrivanje promjene.

## 5. Razvojni rezultati na računaru

| Pristup | Fan AUC | Kontekst |
|---|---:|---|
| Raniji autoenkoder, fp32 | 0,4682 | istorijska polazna referenca |
| PSD-shape | 0,8556 ± 0,0240 | 20 razvojnih podjela |
| PSD-shape, k=20 | 0,8666 ± 0,0270 | odvojena PC referenca, 100 podjela |

**AUC mjeri rangiranje anomalnih u odnosu na normalne snimke, a ne procenat
tačnosti.** Oznaka ± ovdje predstavlja standardnu devijaciju kroz podjele.
Protokoli se razlikuju; brojevi nisu kontrolisano poređenje na istom testu.

- Provjereno je slaganje računanja istih obilježja i ocjene u Pythonu i C-u.
- U zabilježenim probama računanje traje približno **716–728 ms** po prozoru.
- To nije ukupno kašnjenje alarma: odluka zavisi i od prikupljanja zvuka,
  tri uzastopna prozora i eventualnog HOLD-a.

## 6. Fizičke probe

### Promjena zvuka papirićem

![Score i alarm tokom probe papirićem](../../photos/sl_run_papiric.png)

- Promjena je vidljiva u score-u, ali brojni prozori završavaju u HOLD-u.
- Alarm je nastao u **1 od 3 bloka** i prenio se u oporavak.
- **GUIDED25: FAIL.** Porast ocjene sam po sebi nije dovoljan za uspješan test.

### Stabilan ton od 1 kHz

![Score i alarm tokom tonske probe](../../photos/sl_run_ton.png)

- Zabilježena su dva ulaska u alarm i prijava održane promjene.
- Ton je trajao oko šest minuta poslije oznake oporavka u evidenciji.
- Završni povratak u normalu nije potvrđen; precizno kašnjenje nije izmjereno.

*X: vrijeme; Y: score na logaritamskoj skali. Crvena linija: ulazni prag;
zelena: izlazni. Plavo: pouzdani prozori; narandžasto: HOLD;
crveni trouglovi: alarm.*

Ove probe pokazuju ponašanje na jednoj fizičkoj postavci. Dodati ton i
papirić nisu dokaz prepoznavanja određenog mehaničkog kvara.

## 7. Mjerna ploča i potrošnja

**Planirani mjerni put:** 5 V → AMS1117 → INA226 sa šantom → ESP32-S3 i mikrofon.

- Mjerna ploča je povezana; provjera sa spoljašnjim napajanjem tek slijedi
  prema evidenciji trenutnog povezivanja od 28.09.2026.
- Mjeri se grana iza šanta; gubici regulatora i napajanje INA226 nisu uključeni.
- Prvi naredni test: **60 s čekanja uz aktivan I2S**; zatim učenje i nadzor.
- Potrebne su nezavisna provjera napona i struje i ponovljena mjerenja.

**Validno mjerenje potrošnje kompletnog detektora još nije završeno.**
Vrijeme računanja nije mjera energije. Stariji test mjernog lanca nije
potvrda potrošnje sadašnje postavke.

## 8. Zaključak i naredni korak

- Realizovan je tok od mikrofona do lokalne kalibracije i autonomne odluke.
- Razvojni PC rezultati podržavaju izbor PSD-shape modela za dalju provjeru.
- Fizičke probe potvrđuju neke održane promjene i otkrivaju slabosti HOLD-a
  i oporavka.
- Otvoreni zadaci: nezavisne probe, pouzdan oporavak i validna potrošnja.

**Za dogovor:** prvo nezavisna proba na drugom ventilatoru ili dorada
kalibracije i oporavka? Koji obim eksperimenata je dovoljan za završni rad?
