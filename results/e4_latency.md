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

## esp-nn on/off na ISTOM S3 — čist PIE ablation (19.07)

Kontrola: `CONFIG_NN_ANSI_C=y` (generic C) vs default (S3 asm kerneli). Isti čip,
isti klipovi, score-ovi bit-identični (0.75074988...).

| Faza (po 10 s klipu) | esp-nn ON (asm) | esp-nn OFF (ANSI C) | PIE speedup |
|---|---|---|---|
| Featuring | 665 ms | 671 ms | 1.0× (očekivano — FFT je NAŠ C kod, ne esp-nn) |
| **Inferenca (int8 AE)** | 870 ms | 1157 ms | **1.33×** |

**Zaključak (čist ablation):** esp-nn PIE kerneli daju **1.33×** na inferenci
(≈25 % manje vremena) na istom S3. To je PRAVI PIE efekat. Ranija 3.6× razlika
S3 vs klasični ESP32 je VEĆA jer uključuje i arhitekturu (cache, memorijska
propusnost, LX7 vs LX6), ne samo esp-nn — dva mjerenja zajedno razdvajaju
"platforma" od "SIMD kerneli". Featuring se ne mijenja jer FFT ne ide kroz
esp-nn (potencijal: prebaciti na esp-dsp `dsps_fft2r_fc32` — future-work).

*Mjereno 19.07.2026. ESP32-S3-WROOM-1 N32R16V (COM4/CH343) vs
ESP32-D0WD-V3 DevKit V1 (COM5/CP2102).*
