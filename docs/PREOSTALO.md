# Šta je ostalo — tri fizička koraka

> **Ažurirano 16.08.2026: sva tri koraka su izvršena.** Ventilator je nabavljen,
> demo i mjerenje su odrađeni bez lemljenja (taster i lampice imaju softverski
> pandan), i postoji prvi valjan fizički rezultat:
> [rezultat-fan01-2026-08-16.md](rezultat-fan01-2026-08-16.md) — AUC 0,999 na
> izazvanoj promjeni protoka, uz 90 % lažnih alarma zbog praga.
> Ostatak ovog dokumenta opisuje stanje prije toga i lemljenje koje i dalje
> predstoji za čvrst sklop i snimak odbrane.

**Stanje:** 14.08.2026. · **Softver:** zatvoren · **Hardver:** otvoren

Sve softverske faze iz [PLAN-NEXT-LEVEL.md](PLAN-NEXT-LEVEL.md) su izvršene i
zapisane u [DNEVNIK-NEXT-LEVEL.md](DNEVNIK-NEXT-LEVEL.md). Ovaj dokument je
spisak onoga što još **nije** urađeno, i namjerno je kratak.

| # | Korak | Blokira | Trajanje |
|---|---|---|---|
| 1 | **Zalemiti kompletnu šemu** | demo, E5 mjerenje | pola dana |
| 2 | **Kupiti ventilator** | svaku tvrdnju o stvarnom kvaru | — |
| 3 | **Demo i mjerenje sa ventilatorom** | završno poglavlje rada | 2–3 h |

Sve troje je fizički rad. Nijedan od njih ne čeka nijednu softversku odluku.

---

## 1. Kompletna šema

Puni tabelarni i grafički prikaz: [sema-povezivanja.md](sema-povezivanja.md) ·
[sema-povezivanja.svg](sema-povezivanja.svg). Redoslijed i mjere opreza:
[lemljenje.md](lemljenje.md). Ovdje je samo spisak i ono što je novo.

### Mikrofon — **jedan, ne dva**

Ovo je pitanje bilo otvoreno i **zatvoreno je mjerenjem 14.08.** Faza 5 je
ispitala tri dual-channel varijante i sve tri su slabije od jednog kanala; maska
izvedena iz drugog mikrofona pada čak ispod slučajnog pogađanja (AUC 0,45).
Drugi INMP441 ostaje **rezerva**, ne dio šeme.

| Komponenta | Kom | Gdje |
|---|---|---|
| INMP441 | 1 | VDD→3V3, GND→GND, SCK→GPIO4, WS→GPIO5, SD→GPIO6, **L/R→GND** |
| keramika 470 nF | 1 | VDD↔GND mikrofona, **što bliže modulu** |
| elektrolit 10 µF | 1 | isti čvor |

> ⚠️ **Ne dirati sound port.** Mikrofon #1 je uništen alkoholom u otvoru
> ([P16](problemi-i-rjesenja.md#p16)). Kapton traka preko porta tokom lemljenja,
> skida se poslije.

### Lampice i taster — **novo, ovo do sada nije bilo zalemljeno**

| Komponenta | Kom | Gdje | Uloga |
|---|---|---|---|
| LED zelena 5 mm | 1 | GPIO2 → otpornik → LED → GND | status, pet obrazaca |
| LED crvena 5 mm | 1 | GPIO11 → otpornik → LED → GND | alarm |
| otpornik 220–330 Ω | 2 | u seriji sa svakom LED | **jedino što još fali** |
| taster arkadni | 1 | GPIO10 ↔ GND, bez otpornika | interni pull-up je uključen u kodu |

**Otpornici su jedina stavka koja se još nabavlja** —
[donijeti-sa-posla.md](donijeti-sa-posla.md), stavka 3. LED se ne smije vezati
direktno na GPIO.

> Ništa od ovoga više ne blokira eksperiment. Taster i obje lampice imaju
> softverski pandan u panelu
> ([panel-i-virtuelni-taster.md](panel-i-virtuelni-taster.md)), pa se demo i
> mjerenje mogu izvesti sa samo ESP32-S3 i mikrofonom na breadboardu.
> Lemljenje ostaje za čvrst sklop i snimak odbrane.

Šta lampice pokazuju (firmware je gotov i testiran, 43 testa):

| režim | zelena | crvena | značenje |
|---|---|---|---|
| čekanje | kratak bljesak na 2 s | — | pritisni taster |
| učenje | treperi 5 Hz | — | ne diraj ventilator |
| **naučio** | **stalno svijetli** | — | nadzire, sve normalno |
| alarm | ugašena | **svijetli** | trajno odstupanje |
| kvar | dupli bljesak | dupli bljesak u protivfazi | fail-closed stop |

Ako se zalemi samo zelena, ponašanje je nepromijenjeno i potpuno — crvena samo
razrješava „ugašena zelena" naspram „uređaj mrtav", što se na snimku demoa
inače ne vidi.

### Napajanje i senzor — samo za E5 mjerenje potrošnje

Ovo **nije potrebno** za demo sa ventilatorom; demo radi sa USB napajanjem.

| Komponenta | Kom | Gdje |
|---|---|---|
| AMS1117 3.3 V modul | 1 | 5 V ulaz → OUT na INA226 `IN+` |
| INA226 | 1 | `IN−`→3V3 ploče, VCC→3V3, SDA→GPIO8, SCL→GPIO9, **zvjezdasta masa** |
| elektrolit 470 µF | 1 | čvor `IN−`/3V3 ↔ GND (rizik C7, brownout) |

Dva blokatora koja ostaju i nemaju veze sa ventilatorom:

1. **5 V izvor sa golim žicama** — [donijeti-sa-posla.md](donijeti-sa-posla.md),
   stavka 1.
2. **`ASD_INA_TEST` je zaglavljen u `READY`** i odbija ponoviti mjerenje;
   treba re-arm put u firmveru (~15 min koda) prije nego što se diraju žice.

---

## 2. Ventilator

Bilo koji AC ili DC ventilator na kojem se može **bezbjedno** izazvati promjena
zvuka: selotejp na lopatici, lagana prepreka toku vazduha, promjena brzine.
Kriterij nije marka nego to da se promjena može napraviti i **vratiti**, i da
se može opisati u radu bez tvrdnje da je to stvarni kvar.

Do tada važi pravilo koje se ne pregovara: **sve dosadašnje je zvučnik.** Ni
jedan rezultat iz repozitorija se ne smije nazvati fizičkim testom ventilatora.

---

## 3. Demo i mjerenje

Protokol je zaključan: [protokol-fizicki-ventilator.md](protokol-fizicki-ventilator.md),
verzija parsera `physical-fan-v1.6.0`.

Tok demoa, onako kako ga operater vidi:

1. Pusti ventilator, sačekaj da radi normalno.
2. **Pritisni taster — ili klikni `press` u panelu.** Zelena počne da treperi.
   Uređaj **nikad** ne kreće sam, ni prva sesija poslije uključenja. Oba ulaza
   su ravnopravna i daju isti `BUTTON` zapis:
   [panel-i-virtuelni-taster.md](panel-i-virtuelni-taster.md).
3. Finalnih `k=10`: oko 15 s `WAIT` + 10 validnih prozora po 10 s, ukupno
   približno 115 s. Uređaj sluša i uči; ne dirati ništa. `k=20` ostaje
   referentni PC benchmark, nije konfiguracija ovog firmwarea.
4. **Zelena pređe u stalno svjetlo** — naučio je.
5. Izazovi promjenu. Alarm traži **tri uzastopna prozora**, dakle ~30 s trajne
   promjene. Faza 4 je sintetičkim score-pobudama potvrdila samo da jedan ili
   dva izolovana prozora iznad praga ne pale alarm. Govor, zalupljena vrata i
   druge stvarne akustičke smetnje tek se mjere u ovom fizičkom protokolu.
6. Vrati ventilator u normalu; alarm se gasi tek kad score padne ispod
   **0,7× praga** (histereza).

Šta se mjeri i zapisuje:

```bash
.venv\Scripts\python.exe pc\tools\physical_fan_experiment.py --port COM4 --fan-id fan01
```

### Prije nego što se ventilator upali — pročitati

**[P17](problemi-i-rjesenja.md#p17) je otvoren i utiče baš na ovaj demo.** Prag
se između kalibracija razlikuje i do 16× (izmjereno 5687 / 1088 / 347 u tri
prolaza). Praktična posljedica: **ako alarm ne reaguje na očiglednu promjenu,
prvo pogledaj prag u `ADAPTTHR` zapisu, pa tek onda sumnjaj na model.** Ako je
prag visok, ponovi kalibraciju dugim pritiskom tastera — druga kalibracija često
da mnogo niži prag.

**[P19](problemi-i-rjesenja.md#p19):** mašina na kojoj se mjeri mora biti
neopterećena. Ventilator laptopa je jednom već upao u kalibraciju
([P10](problemi-i-rjesenja.md#p10)) i jednom u detekciju.

---

## Šta ostaje otvoreno i poslije ova tri koraka

Ovo nisu prepreke za demo, ali se ne smiju prećutati u radu:

| # | Stavka | Zašto nije zatvoreno |
|---|---|---|
| 1 | **Prag** ([P17](problemi-i-rjesenja.md#p17)) | Traži zaseban normal-only izvod robusne statistike, isto kao politika prisustva i vremenska politika. Zaseban posao, ne izmjena konstante. |
| 2 | `audio_read(..., portMAX_DELAY)` liveness | Nikad testirano na stvarnom prekidu I2S toka. |
| 3 | Faza 7, PC teacher | Zaustavljeno na feasibility gate-u; pokreće se čim se instalira PyTorch, bez ijedne dalje odluke. |
| 4 | Margina prisustva od 11 dB | Izvedena iz snimaka. Mora se ponovo izvesti na fizičkom ventilatoru, gdje nivo varira sa udaljenošću i opterećenjem. |
