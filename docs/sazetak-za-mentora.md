# Prijedlog teme master rada — sažetak (1 strana)

> **ISTORIJSKI DOKUMENT — zamijenjen finalnim PSD/Mahalanobis smjerom.** Ovo je
> prijedlog iz jula 2026. i čuva početni AE/TFLM plan; ne koristiti ga kao
> trenutno stanje, finalnu metodologiju ili spisak otvorenih zadataka. Za
> aktuelno stanje vidi [odluka-finalni-model.md](odluka-finalni-model.md),
> [DNEVNIK-NEXT-LEVEL.md](DNEVNIK-NEXT-LEVEL.md) i
> [PREOSTALO.md](PREOSTALO.md).

**Student:** Mihajlo Živković · MSc Embedded Systems and Algorithms, FTN
**Datum:** jul 2026 · **Ciljana odbrana:** kraj septembra 2026

## Naslov

**Nenadgledana detekcija anomalija zvuka mašina na resursno ograničenim
uređajima: kvantizacija, optimizacija i evaluacija na platformi ESP32-S3**

## Problem i istraživačko pitanje

Detekcija anomalija zvuka mašina (ASD) je etablirana oblast (DCASE Challenge
Task 2, 2020–2026), ali se praktično sva istraživanja izvode na GPU/server
hardveru. Industrijska primjena traži suprotno: jeftin, autonoman senzorski čvor
koji radi offline.

> Koliko detekcione performanse (AUC/pAUC) DCASE-klase sistema preživi migraciju
> na mikrokontroler sa 512 KB SRAM — i kakav je kvantitativni kompromis između
> tačnosti, memorije, latencije i energije?

## Metodologija (standardni DCASE protokol)

- **Dataset:** DCASE 2026 Task 2 dev (7 tipova mašina, samo normalni zvuci u
  treningu); metrike AUC (source/target domen), pAUC, harmonijska sredina.
- **Model:** autoencoder baseline (identičan zvaničnom) + familija manjih
  varijanti; post-training int8 kvantizacija (TFLite).
- **Platforme:** ESP32-S3 (SIMD/PIE instrukcije, 16 MB PSRAM) + klasični ESP32
  kao kontrola — čist hardverski ablation.

## Planirani eksperimenti

| # | Eksperiment | Izlaz |
|---|---|---|
| E1 | Reprodukcija zvaničnog baseline-a (fp32) | sanity check vs objavljeni brojevi |
| E2 | Sweep veličine modela (270k → 22k parametara) | Pareto kriva tačnost↔veličina |
| E3 | int8 kvantizacija svih varijanti | ΔAUC po mašini i domenu |
| E4 | Latencija/RAM na {ESP32, S3} × {SIMD on/off} | speedup tabele, real-time provjera |
| E5 | Energija po fazi (INA226) + projekcija baterijskog rada | mJ po klipu, duty-cycling |
| E6 | (stretch) On-device kalibracija praga (gamma fit u C) | adaptacija bez clouda |

## Šta je već urađeno (status na dan pisanja)

- Kompletan PC pipeline (featuring identičan baseline-u, trening, AUC/pAUC,
  gamma prag, int8 konverzija) — **E1–E3 završeni za prvu mašinu**, ostale u toku.
- Prvi rezultati (fan): baseline hmean 0.540 — u rangu objavljenih DCASE brojeva;
  int8 bez mjerljive degradacije; 12× manji model gubi 2.6 p.p.
- Firmware za ESP32-S3 (ESP-IDF v5): I2S akvizicija, streaming log-mel front-end
  u C-u **bit-identičan** PC putanji (dokazano unit testom preko ctypes),
  TFLM int8 inferenca, evaluacioni mod sa klipovima sa flash particije.
- Repo sa testovima i reproducibilnim eksperimentima (git tag po eksperimentu).

## Doprinosi

1. Prva sistematska evaluacija DCASE ASD protokola na MCU klasi hardvera
   (Pareto: tačnost↔memorija↔latencija↔energija).
2. Kvantizaciona studija po tipu mašine i domenu.
3. Izmjeren efekat SIMD (PIE) instrukcija na identičnom kodu.
4. Open-source reproducibilan artefakt (PC pipeline + firmware).

## Vremenski plan (sedmično, do 30.09)

Već završeno: postavka, dataset, E1–E3 pipeline · **avgust:** hardverska
mjerenja E4–E5 · **do 13.09:** cut-off za nove funkcionalnosti (E6 stretch) ·
**14.–30.09:** pisanje, revizija, priprema odbrane sa live demoom.

*Molim za komentar na obim i fokus — posebno da li je sistemski karakter rada
(ML evaluacija + embedded implementacija + mjerenja) prihvatljiv u ovoj formi.*
