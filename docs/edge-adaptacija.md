# Adaptacija modela za pločicu i on-edge izvršavanje

> **ISTORIJSKA AE/TFLM PUTANJA — nije finalni detektor.** Dokument čuva
> realizovanu neuralnu deployment fazu i njena mjerenja. Finalni uređaj koristi
> `psd_shape` + Mahalanobis bez TFLM-a; trenutno stanje je u
> [odluka-finalni-model.md](odluka-finalni-model.md) i
> [PREOSTALO.md](../privatno/planovi/PREOSTALO.md).

Kako DCASE AE (PC, fp32, batch) postaje firmware koji radi na 512 KB SRAM-a.
Svaki korak ispod je implementiran u repou; brojevi za tiny32 su IZMJERENI, ostali
se mjere u E4.

## 1. Lanac transformacije modela

```
Keras fp32 (~180 KB tiny32 / ~1.1 MB baseline)
  └─ TFLite konverter: BatchNorm fuzija u Dense, ReLU fuzija u FullyConnected
       └─ PTQ int8 (reprezentativni skup = 2000 trening vektora)
            └─ rezultat: JEDAN op tip u grafu — FULLY_CONNECTED (provjereno)
                 └─ gen_model_header.py → model_data.h → flash (const, ne troši RAM)
```

- tiny32: **67.6 KB int8** (mjereno), ΔAUC ≈ 0 vs fp32 (mjereno na fan)
- baseline (267 k param): ~280 KB int8 (procjena iz plana — mjeri se u E3)
- Kvantizacione parametre (scale/zero-point) firmware čita iz .tflite tensora —
  nema hardkodovanja (rizik B3).

## 2. Streaming umjesto batch obrade (ključna edge odluka)

PC pipeline drži cijeli klip u RAM-u (10 s float = 640 KB — ne staje ni u S3 SRAM).
Firmware zato radi **hop-po-hop** (`asd_stream_*` u features_c.c):

| Bafer | Veličina | Gdje |
|---|---|---|
| I2S DMA deskriptori | ~16 KB | interni SRAM (DMA zahtjev na S3) |
| Audio ring (2 s amortizacija) | 64 KB | PSRAM na S3 / interni na ESP32 |
| Klizni prozor uzoraka (1024 f32) | 4 KB | statički |
| Log-mel ring (P=5 × 128 f32) | 2.5 KB | statički |
| Ulazni vektor (640 f32) | 2.5 KB | statički |
| FFT twiddle + bitrev + radni | ~14 KB | statički |
| Mel težine (sparse) + Hann | ~8 KB | flash (const) |
| Norm mean/std (2×640 f32) | 5 KB | flash (const) |
| TFLM arena tiny32 | ~20–40 KB (mjeriti `arena_used`) | SRAM ili PSRAM |

**Ukupan RAM featuring puta < 25 KB** → identičan firmware radi i na klasičnom
ESP32 bez PSRAM-a. Test `test_streaming_equals_batch`: streaming je **bit-identičan**
batch putu, pa svi PC rezultati važe za uređaj.

Latencijski bonus: obrada je raspoređena tokom snimanja (svakih 32 ms jedan frejm
+ jedna inferenca ~1–3 ms), pa nema špica na kraju klipa — real-time kriterijum
(plan 6.1) se ispunjava kontinuirano, a odluka stiže praktično odmah po isteku klipa.

## 3. Konfiguracije po ploči (automatski kroz sdkconfig + #if)

| | ESP32-S3 N32R16V | ESP32 DevKit V1 |
|---|---|---|
| Uloga | glavni target, svi eksperimenti | E4 kontrola (bez PIE, bez PSRAM-a) |
| Arena | 512 KB PSRAM (default) ili interni (`-DASD_ARENA_INTERNAL`) za E4/E5 | 96 KB interni (automatski) |
| Modeli | svi (i baseline int8, i fp32 iz PSRAM-a) | AE-tiny int8 (baseline tijesno — mjeri se) |
| Kerneli | esp-nn PIE SIMD **on/off** (Kconfig) | generički C |
| Klipovi za eval | 20 MB FAT (~60 klipova) | 1.4 MB FAT (~4 klipa) |

## 4. Šta se još mjeri na uređaju (hooks postoje u app_main)

- `feat` / `inf` / `total` vrijeme po klipu (esp_timer, akumulirano po fazi)
- `arena_used_bytes` poslije init-a; free heap; dropped samples iz ring buffera
- E5 (kad stigne INA226): idle / capture / featuring / inferenca struje,
  duty-cycling projekcija (10 s slušanja / 5 min + light sleep)

## 5. Fallback lestvica ako int8 degradira (rizik A3, redom)

1. per-channel kvantizacija (default u TFLite — provjeriti da je aktivna)
2. veći reprezentativni skup (2000 → 10000 vektora)
3. ulaz/izlaz ostavi u fp32, unutrašnjost int8 (mala cijena na dense mrežama)
4. QAT — tek ako 1–3 ne pomognu (nije u scope-u, ide u future-work)
