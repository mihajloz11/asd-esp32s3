# Predaja stanja — ASD na ESP32-S3 (09.08.2026)

Sažetak za nastavak rada u novoj sesiji. Detalji: [dnevnik-projekta.md](dnevnik-projekta.md),
[problemi-i-rjesenja.md](problemi-i-rjesenja.md), [model-poboljsanje.md](model-poboljsanje.md).

## Projekat

Master rad: detekcija anomalija u zvuku mašina (ASD) na ESP32-S3.
Repo `C:\Users\mihaj\Desktop\master new`, grana `master`, sve pushovano.
Dataset DCASE 2026 dev, 7 mašina, u `data/` (nije u gitu).

## Hardver

| Komponenta | Stanje |
|---|---|
| ESP32-S3-DEV-KIT-NXRX (N32R16V, 32 MB fleš, 16 MB PSRAM) | radi, COM4 |
| INMP441: BCLK→GPIO4, WS→GPIO5, SD→GPIO6, VDD→3V3, L/R→GND | **radi** |
| INA226 (SDA→GPIO8, SCL→GPIO9) | **KVAR** — SDA i SCL nisko-omski na VCC |
| LED | nije spojena, fali otpornik 220–330 Ω |
| AMS1117, kondenzatori, ploča 4×6 | faza 2 |

INA226 blokira eksperiment E5 (energija). Utvrđeno eliminacijom: pinovi ploče
ispravni, žice na pravim pinovima, nisu zamijenjene ni kratko spojene,
pull-upovi 10 kΩ ispravni, a kad se sve žice skinu sa modula pinovi propadnu u
slobodno stanje. Lista za multimetar: [ina226-provjera.md](ina226-provjera.md).

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
| **sažetak log-mela + naučena kovarijansa** | **0,674** ✔ |
| sažetak + dijagonalna kovarijansa | 0,595 |
| top-k odstupanja umjesto zbira | 0,645 |
| kalibracija po radnom režimu | 0,582 |
| bogatiji sažetak (percentili, dinamika) | 0,578 |
| CMN normalizacija | 0,544 |
| klasifikator brzina ventilatora | 0,530 |
| naučena ugradnja preko svih 7 mašina | 0,495 |
| autoenkoder (polazno stanje) | 0,451 |
| finiji FFT / linearne trake | 0,501–0,643 |

**0,8 NIJE dostignuto.** Deset pristupa staje na 0,674.

### Pobjednički pristup

Otisak klipa = sredina + std po svakoj mel traci. Kovarijansa se **uči
unaprijed** sa 990 snimaka ispravnih ventilatora (traži stotine primjera).
Na ploči se mjeri **samo centar** novog primjerka (dovoljno 10 klipova).
Score = Mahalanobis od tog centra u naučenom obliku.

Za ploču je **jednostavnije od postojećeg**: nema mreže, nema TFLite, nema
arene — matrica u flešu i jedno množenje po prozoru umjesto 1055 ms inferencije.
Front-end (log-mel) se ne dira, već je verifikovan.

### Zaključci

- Autoenkoder je pogrešan alat: ispravan 2,53 vs neispravan 2,57, razlika 1,6 %
- Signal je u **vezama** između mel traka, ne u pojedinačnim (dijagonalna gubi 8 poena)
- Dužina kalibracije nije usko grlo: 50 s → 0,631, 400 s → 0,639
- Naučena ugradnja pada jer mreža uči da razlikuje *tipove mašina*, pa namjerno
  odbacuje varijaciju *unutar* jedne mašine — a baš ta varijacija nosi kvar
- DCASE anomalije su namjerno suptilne; stvarni kvar (zaglavljena lopatica,
  disbalans) je grublji i vjerovatno se hvata mnogo bolje

## Šta dalje

1. **Prenijeti pobjednički pristup na ploču** (jednostavnije od postojećeg)
2. **Izmjeriti sa stvarnim ventilatorom i stvarnim kvarom** — ta brojka je za
   primjenu mjerodavnija od benchmark broja
3. INA226: multimetar po `ina226-provjera.md`, popraviti ili zamijeniti → E5
4. Otpornik 220–330 Ω → LED demo
5. 5-seed treninzi za finalne tabele; pisanje poglavlja 2 i 3

## Zamke koje su već koštale vremena

Puna lista u [problemi-i-rjesenja.md](problemi-i-rjesenja.md) (P1–P11). Najskuplje:

- **P2** promjena build moda bez `reconfigure` — build tiho ostane u starom modu
- **P4** task watchdog upisuje tekst usred base64 toka → pokvaren WAV
- **P5** alat je snimio neispravan WAV uprkos neuspjeloj provjeri
- **P10** kalibracija tri puta naučila ventilator laptopa kao normalno stanje
- **P11** jednostrani prag propušta pola promjena
- Curenje u mjerenju: kovarijansa učena i ocjenjivana na istim klipovima → 0,96
  umjesto 0,758. Uvijek razdvojiti korpus za učenje od skupa za ocjenu.
- `git add -A` je pokupio 1,2 GB keša featura; sad u `.gitignore`
