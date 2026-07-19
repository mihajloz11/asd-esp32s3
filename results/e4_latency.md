# E4 — Latencija po platformi (tiny32 int8, fan klipovi, 240 MHz)

Isti firmware, isti model, isti klipovi. Score-ovi **bit-identični** na obje
platforme i PC-u (max rel razlika 1.5e-04) → korektnost očuvana; razlika je
čisto u brzini.

| Faza (po 10 s klipu, 307 vektora) | ESP32-S3 (PIE + esp-nn) | ESP32 klasični (LX6, generic) | Speedup S3 |
|---|---|---|---|
| Featuring (FFT+mel+log) | 665 ms | ~1095 ms | **1.65×** |
| Inferenca (307× AE int8) | ~870 ms | ~3140 ms | **3.6×** |
| **Ukupno** | ~1535 ms | ~4235 ms | **2.76×** |
| TFLM arena | 7960 B | 7960 B | isto |
| PSRAM | 16 MB | nema (SRAM-only) | — |

**Zaključak:** inferenca je gdje S3 dominira (**3.6×**) — esp-nn PIE SIMD int8
kerneli. Featuring (float FFT) dobija 1.65× od LX7 FPU/PIE. Oba čipa daleko
ispod real-time granice (10 s): S3 15 %, ESP32 42 % iskorišćenja — čak i
klasični ESP32 bez PSRAM-a nosi ovaj model komotno.

**Sljedeće za punu E4 matricu:** esp-nn on/off na SAMOM S3 (Kconfig
`CONFIG_NN_OPTIMIZED`) — izoluje čist PIE efekat nezavisno od platformskih
razlika (cache, PSRAM). Ovo mjerenje je S3-esp-nn vs ESP32-esp-nn-generic
(platformsko poređenje).

*Mjereno 19.07.2026. ESP32-S3-WROOM-1 N32R16V (COM4/CH343) vs
ESP32-D0WD-V3 DevKit V1 (COM5/CP2102).*
