# Predaja stanja — ASD na ESP32-S3 (09.08.2026)

Sažetak za nastavak rada u novoj sesiji. Detalji: [dnevnik-projekta.md](dnevnik-projekta.md),
[problemi-i-rjesenja.md](problemi-i-rjesenja.md), [model-poboljsanje.md](model-poboljsanje.md).

Nepromenjivi cilj i kriterij uspjeha zapisani su u
[cilj-modela.md](cilj-modela.md): opšti normalni model iz mnogo ispravnih
ventilatora, kratka lokalna kalibracija novog ventilatora i zatim potpuno
samostalan dvostrani detektor na ESP32-S3, uz istraživački cilj AUC >= 0,80.

> **Počni od [PLAN.md](PLAN.md)** — tamo je stanje, šta je dokazano a šta nije,
> nalazi vanjske revizije i redoslijed rada. Ovaj dokument je detalj.

Finalni izbor modela, rezervna alternativa i kriteriji prihvatanja na
hardveru: [odluka-finalni-model.md](odluka-finalni-model.md).
Otpornost na buku okoline (koraci, razgovor) i dvomikrofonski pristup:
[plan-otpornost-na-buku.md](plan-otpornost-na-buku.md).

## Projekat

Master rad: detekcija anomalija u zvuku mašina (ASD) na ESP32-S3.
Repo `C:\Users\mihaj\Desktop\master new`, grana `master`.
Remote: `github.com/mihajloz11/master-asd-esp32s3`.
**Provjeri `git log origin/master..HEAD` prije nego zaključiš da je sve pushovano** —
rad od 09.08.2026 je neko vrijeme stajao lokalno.
Dataset DCASE 2026 dev, 7 mašina, u `data/` (nije u gitu).

## Hardver

| Komponenta | Stanje |
|---|---|
| ESP32-S3-DEV-KIT-NXRX (N32R16V, 32 MB fleš, 16 MB PSRAM) | radi, COM4 |
| INMP441: BCLK→GPIO4, WS→GPIO5, SD→GPIO6, VDD→3V3, L/R→GND | **radi** |
| INA226 (SDA→GPIO8, SCL→GPIO9) | **radi** — adresa `0x44`, ID i registri potvrđeni |
| LED | nije spojena, fali otpornik 220–330 Ω |
| AMS1117, kondenzatori, ploča 4×6 | faza 2 |

INA226 I2C lanac je potvrđen 10.08.2026. Uzrok ranijeg kvara bio je pogrešno
spojen GND, ne modul. Preostaje E5 povezivanje strujnog puta preko IN+/IN− i
VBS prema [šemi povezivanja](sema-povezivanja.md).

## Firmware — build modovi

⚠️ Pri svakoj promjeni moda **obavezan `idf.py reconfigure`** — `if(DEFINED ENV{...})`
se evaluira samo pri konfiguraciji, inače build tiho ostane u starom modu (P2).

| Env var | Šta radi |
|---|---|
| (bez flega) | živi ASD rad, score svakih 10 s |
| `ASD_MIC_TEST` | mjerač nivoa 8 s + snimak 5 s + WAV na PC |
| `ASD_LIVE_CAPTURE` | klip + score na uređaju + snimak → `live_compare.py` |
| `ASD_LIVE_ADAPT` | čekanje da se soba umiri → kalibracija → neprekidna detekcija |
| `ASD_EVAL_MODE` | klipovi sa flash particije |
| `ASD_INA_TEST` | I2C dijagnostika (mapa pinova, bit-bang scan) |

PC alati u `pc/tools/`: `mic_capture.py`, `live_compare.py`, `live_monitor.py`
(živi grafik na `localhost:8770`), `progress.py` (praćenje eksperimenta na 8771).

## Verifikovano mjerenjem

- **PC ↔ uređaj na živom mikrofonu: 7,99e-05** (ranije 1,5e-04 nad klipovima s flasha)
- Realno vrijeme: 1,72 s računa na 10 s zvuka = **5,8× rezerve**, `dropped=0`
- TFLM arena 7 960 B; E4: S3 vs ESP32 **2,76×**, esp-nn on/off **1,33×**
- Rizik C1 zatvoren: `>>14` potvrđen mjerenjem, 15,6 dB rezerve do klipovanja

## Živi demo (radi)

Pušten zvuk preko zvučnika, mikrofon hvata kroz vazduh:

| Faza | Greška | Odluka |
|---|---|---|
| tišina | 69–77 | normal |
| pušten zvuk | 45–65 | **ANOMALIJA** |
| zvuk ugašen | 67–72 | normal |

Prelazi tačni u sekundu. Sa DCASE snimkom ventilatora: normalan 0 alarma/75
prozora, neispravan 5/30, **mašina stala 7/7** (score 10 → 59).

**Ključno: score PADA kad se pusti zvuk, ne raste.** Greška rekonstrukcije je
udaljenost od naučene raspodjele, ne mjera jačine. Zato je prag **dvostran**
(1. i 99. percentil), inače propušta pola promjena (P11).

## Model — glavni dio posla

Cilj: naučiti na gomili ispravnih ventilatora, spustiti na ploču, kalibrisati
na **novom** ventilatoru koji model nije čuo, i detektovati njegove kvarove.

**Protokol (pošten):** k klipova ciljne mašine u kalibraciju, ocjena na
preostalim normalnim + svim anomalijama, klip iz kalibracije se nikad ne
ocjenjuje, 20 ponavljanja. Mjera: AUC na novom ventilatoru.

| Pristup | AUC |
|---|---|
| **visokorezolucioni PSD oblik + naučena kovarijansa** | **0,864** ✔ |
| sažetak log-mela + naučena kovarijansa | 0,674 (stari rezultat) |
| sažetak + dijagonalna kovarijansa | 0,595 |
| top-k odstupanja umjesto zbira | 0,645 |
| kalibracija po radnom režimu | 0,582 |
| bogatiji sažetak (percentili, dinamika) | 0,578 |
| CMN normalizacija | 0,544 |
| klasifikator brzina ventilatora | 0,530 |
| naučena ugradnja preko svih 7 mašina | 0,495 |
| autoenkoder (polazno stanje) | 0,451 |
| finiji FFT / linearne trake | 0,501–0,643 |

**Cilj 0,8 je pređen na PC benchmarku 09.08.2026 — za ventilator.**
Visokorezolucioni PSD otisak + Ledoit–Wolf kovarijansa + lokalni centar daje
**target AUC 0,864 ± 0,025** (k=20, 50 ponavljanja; pAUC 10 % = 0,657 ± 0,062).
Stari pristup pod istim seedovima daje 0,669 ± 0,031.
Detalji: [istrazivanje-psd-model.md](istrazivanje-psd-model.md).

> **Naknadno ažuriranje 14.08.2026. — finalni implementacijski izbor je `k=10`,
> ne `k=20`.** To je 10 validnih prozora, 100 s mjerenja i oko 115 s zajedno
> sa `WAIT` fazom. Razvojna evaluacija te konfiguracije daje 0,856 ± 0,024 na
> 20 podjela; `k=20` ostaje referentni jači PC rezultat i ne opisuje trenutni
> firmware.

**Ne generalizuje na druge tipove mašina.** Na svih 7 mašina psd_shape pobjeđuje
samo na 2, a po harmonijskoj sredini (0,537) je lošiji od mel osnove (0,573).
Razlog je fizički: uske harmonijske linije ima rotaciona mašina, ne ventil ili
klizač. Uređaj je namijenjen ventilatorima, pa odluka stoji, ali se tvrdnja piše
kao „za ventilator". Tabela: [put-do-modela.md](put-do-modela.md), faza 4b.

### Novi pobjednički pristup

Otisak klipa = dugoročni spektar dobijen sa FFT 8192, sažet u 96
logaritamskih traka 10–4000 Hz i normalizovan po ukupnom nivou. Kovarijansa se
uči sa 990 ispravnih source snimaka, a na pločici se mjeri samo centar novog
ventilatora. Matrica 96 × 96 zauzima 36 864 B; TFLite i neuronska mreža nisu
potrebni. PC float32 provjera daje isti AUC kao float64.

Float32 model header i C front-end/score su pripremljeni. Na realnom WAV-u
PC↔C razlika feature-a je 9,54e-07, a score-a relativno 4,37e-07.

**Spojeno na pločicu 09.08.2026** — mod `ASD_PSD_LIVE`
([psd_live.c](../firmware/esp32s3_asd/main/psd_live.c)), radi cijeli lanac:
čekanje → kalibracija na novom ventilatoru → samostalna detekcija sa alarmom.
Izmjereno: **704 ms po klipu od 10 s** (rezerva 14,2×), `dropped=0`,
PC↔uređaj na **živom mikrofonu 1,70e-06** (mod `ASD_PSD_VERIFY`).
Svi unaprijed postavljeni kriteriji prihvatanja prošli —
[hardver-verifikacija.md](hardver-verifikacija.md), [odluka-finalni-model.md](odluka-finalni-model.md).

Preko zvučnika AUC je 0,716 (ne 0,864): akustički kanal pravi rasipanje reda
veličine većeg od signala DCASE anomalije. Zaustavljena mašina se detektuje
bez greške. Mjerodavan test ostaje stvarni ventilator sa stvarnim kvarom.

### Prethodni pobjednički pristup

Otisak klipa = sredina + std po svakoj mel traci. Kovarijansa se **uči
unaprijed** sa 990 snimaka ispravnih ventilatora (traži stotine primjera).
Na ploči se mjeri **samo centar** novog primjerka (dovoljno 10 klipova).
Score = Mahalanobis od tog centra u naučenom obliku.

Za ploču je **jednostavnije od postojećeg**: nema mreže, nema TFLite, nema
arene — matrica u flešu i jedno množenje po prozoru umjesto 1055 ms inferencije.
Za ovaj prethodni pristup front-end (log-mel) se nije dirao i bio je
verifikovan. U vrijeme ovog zapisa novi PSD pobjednik je mijenjao front-end i
zato je tražio novu PC↔C provjeru. Ta potreba je naknadno zatvorena posebnim
PSD test-vektorima, PC↔C parity testom i on-device speaker/microphone prolazom;
fizički ventilator time nije testiran.

### Zaključci

- Autoenkoder je pogrešan alat: ispravan 2,53 vs neispravan 2,57, razlika 1,6 %
- Signal je u **vezama** između mel traka, ne u pojedinačnim (dijagonalna gubi 8 poena)
- Kod novog PSD modela: 50 s kalibracije → 0,834, 200 s → 0,864,
  400 s → 0,875; dobitak poslije 200 s je mali
- Naučena ugradnja pada jer mreža uči da razlikuje *tipove mašina*, pa namjerno
  odbacuje varijaciju *unutar* jedne mašine — a baš ta varijacija nosi kvar
- DCASE anomalije su namjerno suptilne; stvarni kvar (zaglavljena lopatica,
  disbalans) je grublji i vjerovatno se hvata mnogo bolje

## Šta dalje

1. **Izmjeriti sa stvarnim ventilatorom i stvarnim kvarom** — to je sada glavni
   otvoreni posao; benchmark i „preko zraka" brojke su zatvorene
2. INA226: multimetar po `ina226-provjera.md`, popraviti ili zamijeniti → E5
3. Otpornik 220–330 Ω → LED demo (kod već upravlja GPIO2)
4. 5-seed treninzi za finalne tabele; pisanje poglavlja 2 i 3
   (materijal: [put-do-modela.md](put-do-modela.md))

*(Urađeno 09.08.2026: PSD modul spojen u `ASD_PSD_LIVE`, latencija/RAM/`dropped`
izmjereni, PC↔uređaj zatvoren na živom mikrofonu.)*

## Zamke koje su već koštale vremena

Puna lista u [problemi-i-rjesenja.md](problemi-i-rjesenja.md) (P1–P12). Najskuplje:

- **P2** promjena build moda bez `reconfigure` — build tiho ostane u starom modu
- **P4** task watchdog upisuje tekst usred base64 toka → pokvaren WAV
- **P5** alat je snimio neispravan WAV uprkos neuspjeloj provjeri
- **P10** kalibracija tri puta naučila ventilator laptopa kao normalno stanje
- **P11** jednostrani prag propušta pola promjena
- Curenje u mjerenju: kovarijansa učena i ocjenjivana na istim klipovima → 0,96
  umjesto 0,758. Uvijek razdvojiti korpus za učenje od skupa za ocjenu.
- `git add -A` je pokupio 1,2 GB keša featura; sad u `.gitignore`
