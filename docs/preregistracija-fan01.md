# Preregistracija — prvi fizički test ventilatora (`fan01`)

**Pisano:** 15.08.2026, uveče · **Run planiran:** 16.08.2026
**Protokol:** [protokol-fizicki-ventilator.md](protokol-fizicki-ventilator.md),
`physical-fan-v1.6.0` · **Firmware:** `ASD_PSD_LIVE`, flešovan 15.08.2026

> Ovaj dokument je napisan **prije** nego što je ijedan mjerodavni prozor
> snimljen. Postoji zato da se pravila prihvatanja ne mogu izabrati poslije
> rezultata. Ono što se ovdje ne može popuniti unaprijed označeno je sa
> `POPUNITI NA LICU MJESTA` i upisuje se prije prvog `condition`, ne poslije.

---

## 1. Šta se već zna

Sve što slijedi je izmjereno 15.08.2026, ali **nijedno nije valjan rezultat** —
išlo je kroz panel, van alata za eksperiment, bez zapisa i bez oznaka uslova.
Vrijednosti stoje ovdje samo kao očekivanje reda veličine, ne kao referenca.

| | |
|---|---|
| Prag iz te kalibracije | 529 |
| Normalni prozori | 418 i **592** — jedan iznad praga bez promjene |
| Papirić uz rešetku | 24 873 → 52 046, alarm na trećem uzastopnom prozoru |
| Papirić izvađen | 2 668 — i dalje 7× iznad izlaznog praga (370) |
| Oporavak (`ANOMALY_CLEARED`) | **nikad viđen** — ventilator je ugašen prerano |
| Račun po klipu | 705 ms na 10 s zvuka |

Otuda i dva prioriteta sutrašnjeg runa: **izmjeriti oporavak** i **vidjeti
koliko je margina između normale i praga stvarno tijesna**.

---

## 2. Postavka (zaključati prije prvog `condition`)

Izmjereno 16.08.2026, prije pokretanja runa:

| Stavka | Vrijednost |
|---|---|
| `fan_id` | `fan01` |
| `session_id` | `cold-start-03` |
| Tip ventilatora | prenosivi USB ventilator sa ugrađenom baterijom |
| Napajanje | **USB kabl 5 V** — radi na struji, baterija se ne prazni tokom runa |
| Rastojanje mikrofon–osovina | **20 cm** |
| Ugao | **90°**, mikrofon usmjeren ka osovini |
| Smjer duvanja | **90° od mikrofona** — mikrofon je van struje vazduha |
| Montaža | ventilator i mikrofon na stolici, zalijepljeni; ne pomjeraju se |
| Laptop | **85 cm vodoravno, 30 cm više** (na stolu); mora ostati neopterećen |
| Prostorija | soba, **prozor zatvoren** |
| Pozadinska buka | ulica prigušena zatvorenim prozorom |
| Hladni / topli start | `POPUNITI PRI POKRETANJU` |

Ventilator, mikrofon, rastojanje, ugao i napajanje se **ne pomjeraju** između
kalibracije i ocjene iste sesije.

> **Laptop na 85 cm je bliže nego što je poželjno.** Njegov ventilator je već
> dvaput kontaminirao mjerenje ([P10](problemi-i-rjesenja.md#p10),
> [P19](problemi-i-rjesenja.md#p19)). Uslov: tokom runa se na laptopu ne
> pokreće ništa osim alata i panela, i njegov ventilator ne smije biti čujan.
> Ako se čuje, stolica se odmiče i run se ponavlja iz početka.

Ventilator, mikrofon, rastojanje, ugao i napajanje se **ne pomjeraju** između
kalibracije i ocjene iste sesije.

---

## 3. Pravila prihvatanja — fiksirana, ne biraju se poslije

**K1 — kalibracija.** Poslije `CAL_SUMMARY` gleda se `loo_cv`. Ako je
**> 0,6**, kalibracija se odbacuje i ponavlja dugim pritiskom. Odluka se donosi
prije nego što se pogleda ijedan `DET` prozor.

> Broj 0,6 je procjena između dva prolaza iz [P17](problemi-i-rjesenja.md#p17)
> (loš prolaz `CV = 1,77`, dobar `CV = 0,36`). **Nije izveden mjerenjem** i tako
> se piše u radu. Upisan unaprijed je pošten; izabran poslije rezultata ne bi
> bio.

**K2 — skraćena osnova.** Normalna osnova traje **10 minuta**, ne 30–60 kako
protokol traži. Posljedica se piše eksplicitno: broj lažnih alarma na sat
izveden iz ~60 prozora ima širok interval i **ne poredi se** sa brojkama iz
punih sesija.

**K3 — ventilator se ne gasi dok run traje.** `controlled_stop` je posljednji
događaj sesije, jer gašenje ruši nivo ispod praga prisustva i završava run kroz
`NO_MACHINE` → `FLOW_STOPPED`.

**K4 — trajanje događaja.** Svaki uslov se drži najmanje **5 punih prozora**
(60 s). Alarm traži tri uzastopna, pa kraće od toga ne dokazuje ništa.

**K5 — oporavak.** Poslije svakog `airflow_change` ide `recovery_normal` u
trajanju od **najmanje 90 s**, i čeka se `ANOMALY_CLEARED`. Ako ne padne, to je
rezultat koji se zapisuje — ne razlog da se prag dira.

**K6 — bez naknadnog podešavanja.** Ni prag, ni model, ni politika se ne mijenjaju
na osnovu ishoda ovog runa. Ako ishod bude loš, to je nalaz, ne kvar.

---

## 4. Redoslijed sesije

| # | Faza | Trajanje | Komanda |
|---|---|---|---|
| 1 | kalibracija | ~115 s | klik **Kratak pritisak** u panelu |
| 2 | provjera K1 | — | pogledati `loo_cv` u `CAL_SUMMARY` |
| 3 | normalna osnova | 10 min | `condition normal_baseline` |
| 4 | papirić uz rešetku | 60 s | `condition airflow_change` |
| 5 | oporavak | 90 s | `condition recovery_normal` |
| 6 | ponoviti 4–5 još dva puta | ~5 min | |
| 7 | razgovor na 2 m | 60 s | `condition ambient_noise` |
| 8 | oporavak | 90 s | `condition recovery_normal` |
| 9 | gašenje ventilatora | — | `condition controlled_stop` |
| 10 | kraj | — | `stop` |

Ukupno oko **22 minuta** od pritiska tastera do `stop`.

**Bezbjednost:** papirić se drži sa **spoljne strane zaštitne rešetke**, bez
kontakta sa lopaticama i bez guranja kroz rešetku. Ventilator se ne oštećuje.

---

## 4b. Šta je palo 16.08.2026 i zašto (četiri runa, nijedan valjan)

Prvi pokušaj mjerenja izvukao je pet grešaka. Nijedna nije bila u modelu; sve su
bile u putevima koje do tada niko nije prošao — jer je operaterski taster nov, a
rekalibracija na zahtjev nikad nije išla kroz strogi host.

| # | Šta je palo | Uzrok | Popravka |
|---|---|---|---|
| 1 | prvi WAIT blok obarao sesiju u `SENSOR_ERROR` | ring bafer se punio od boota dok uređaj čeka pritisak; `dropped_delta=1024` naslijeđen iz čekanja | `audio_flush()` na početku sesije |
| 2 | druga komanda preko native USB-a nikad ne stigne | periferija drži OUT paket dok se status prijema ne obriše | `usb_serial_jtag_ll_clr_intsts_mask` poslije čitanja |
| 3 | `HOLD` stiže kao smeće | jedan bafer reda za oba porta; ista komanda sa dva porta ispreplela bajtove | odvojen bafer po izvoru |
| 4 | run odbačen čim je prag objavljen | host poredio float32 prag sa float64 računom uz apsolutnu toleranciju manju od jednog ulp-a | tolerancija prati veličinu praga |
| 5 | run odbačen pri rekalibraciji | firmware šalje `ABORTED` pa `ENDED`; host je `ABORTED` računao kao zatvaranje | `ABORTED` je razlog, `ENDED` zatvara |
| 6 | **svaka komanda iz alata nestajala** | na Windowsu dodjela `Serial.timeout` odbaci bajtove koji čekaju slanje, a petlja ju je radila u svakom prolazu | postavlja se samo kad se stvarno mijenja |

Šesta je bila uzrok svih „kliknuo sam, ništa se nije desilo": `events.csv` je
bilježio pritisak, `ser.write` nije prijavio grešku, a do pločice nije stizao
nijedan bajt. Izmjereno na istom portu: bez te dodjele 3/3 komande stignu, sa
njom 0/3.

**Nalaz koji ostaje za rad, nezavisno od ovih grešaka:** ventilator na bateriji
usporava, harmonijske linije se pomjeraju, i score skoči preko dvostrukog praga
bez ikakvog kvara (`cold-start-04`: 35 uzastopnih alarmnih prozora, nivo pao sa
−47,6 na −49,0 dBFS). Na punjaču isto rasipanje pada devet puta
(`loo_cv` 0,63 → 0,52). To je mjerljiva osjetljivost PSD modela na promjenu
obrtaja i tako se piše.

## 5. Kako se pokreće

Jednom komandom — pokreće alat, sačeka run direktorij, pa na njega zakači panel:

```bash
.venv\Scripts\python.exe pc\tools\start_fan_run.py --fan-id fan01 --session-id cold-start-07 --montaza-potvrdio "ime, ventilator na punjacu, radi normalno, montaza bezbjedna"
```

`--montaza-potvrdio` zamjenjuje ono ručno `DA`: potvrdu daje čovjek koji gleda
postavku, skripta je samo doslovno prenosi u `provenance.metadata.operator_notes`.
Bez tog argumenta se ništa ne pokreće.

Panel se javi na `http://127.0.0.1:8772/`. Odatle su tri klika:

1. **Pokreni učenje** — pločica kreće u WAIT+CAL, oko 2 minuta
2. provjeri `loo_cv` (pravilo K1) — panel ga pokazuje sa ✓ ili ✗
3. **Kreni sa mjerenjem** — vodič vodi svih deset faza sam do `stop`

Klik u panelu i otkucana komanda u alatu rade isto.

---

## 6. Šta ovaj run može, a šta ne može da tvrdi

**Može:** da prototip u ovoj postavci detektuje bezbjedno izazvanu promjenu
protoka, sa izmjerenim kašnjenjem, oporavkom i brojem lažnih alarma na skraćenoj
osnovi.

**Ne može:** da je to „stvarni kvar" — promjena je izazvana i vraćena, bez
nezavisne stručne potvrde. Ne može ni generalizaciju na druge ventilatore:
jedan primjerak, jedna soba, jedna sesija.
