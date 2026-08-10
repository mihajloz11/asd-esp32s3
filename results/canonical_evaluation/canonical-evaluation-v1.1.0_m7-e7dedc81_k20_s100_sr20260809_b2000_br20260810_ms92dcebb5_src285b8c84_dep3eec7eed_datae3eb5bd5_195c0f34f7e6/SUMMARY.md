# Developmental benchmark `canonical-evaluation-v1.1.0_m7-e7dedc81_k20_s100_sr20260809_b2000_br20260810_ms92dcebb5_src285b8c84_dep3eec7eed_datae3eb5bd5_195c0f34f7e6`

> Within-run leakage is guarded, but historical model-selection bias remains. This is not an independent final validation and covers only mel1280, mel256 and psd_shape.

- Protocol: `canonical-evaluation-v1.1.0`
- Git HEAD: `7cd08ee9dd1403a05cf398f0b2fd1a98f07a57d5`
- Dirty working tree: `True`
- k / splits: `20` / `100`
- Metrics: AUC and **standardized pAUC@FPR<=0.1** (`sklearn` standardized partial AUC with `max_fpr=0.1`).
- Bootstrap 95% CI: mean across predefined calibration splits, `2000` resamples, seed/random state `20260810`.
- Manifest SHA-256: `e3eb5bd5d5ed1d5b92767d2e38aebc974835f172896ca625b5e825f7a1ab07aa`

| Machine | Front-end | AUC mean | AUC bootstrap 95% CI | split std | standardized pAUC@FPR<=0.1 mean | pAUC bootstrap 95% CI | split std |
|---|---|---:|---:|---:|---:|---:|---:|
| ToyCar | mel1280 | 0.5392 | [0.5344, 0.5445] | 0.0258 | 0.5131 | [0.5118, 0.5146] | 0.0071 |
| ToyCar | mel256 | 0.5361 | [0.5313, 0.5414] | 0.0255 | 0.5113 | [0.5097, 0.5129] | 0.0083 |
| ToyCar | psd_shape | 0.4479 | [0.4423, 0.4541] | 0.0305 | 0.4782 | [0.4771, 0.4793] | 0.0057 |
| ToyCarEmu | mel1280 | 0.5524 | [0.5346, 0.5710] | 0.0942 | 0.5323 | [0.5276, 0.5373] | 0.0248 |
| ToyCarEmu | mel256 | 0.5180 | [0.5003, 0.5366] | 0.0942 | 0.5004 | [0.4973, 0.5036] | 0.0163 |
| ToyCarEmu | psd_shape | 0.3756 | [0.3633, 0.3889] | 0.0657 | 0.4873 | [0.4850, 0.4896] | 0.0119 |
| bearingEmu | mel1280 | 0.5760 | [0.5707, 0.5809] | 0.0262 | 0.5902 | [0.5869, 0.5934] | 0.0161 |
| bearingEmu | mel256 | 0.5686 | [0.5636, 0.5735] | 0.0258 | 0.5845 | [0.5805, 0.5883] | 0.0196 |
| bearingEmu | psd_shape | 0.5063 | [0.5010, 0.5115] | 0.0265 | 0.4826 | [0.4794, 0.4862] | 0.0175 |
| fan | mel1280 | 0.6270 | [0.6204, 0.6336] | 0.0346 | 0.5210 | [0.5167, 0.5258] | 0.0235 |
| fan | mel256 | 0.5897 | [0.5833, 0.5959] | 0.0335 | 0.5124 | [0.5078, 0.5173] | 0.0239 |
| fan | psd_shape | 0.8666 | [0.8611, 0.8713] | 0.0265 | 0.6669 | [0.6551, 0.6789] | 0.0613 |
| gearboxEmu | mel1280 | 0.6113 | [0.6020, 0.6206] | 0.0480 | 0.5262 | [0.5211, 0.5311] | 0.0252 |
| gearboxEmu | mel256 | 0.5810 | [0.5719, 0.5904] | 0.0471 | 0.5012 | [0.4963, 0.5058] | 0.0237 |
| gearboxEmu | psd_shape | 0.5435 | [0.5360, 0.5514] | 0.0397 | 0.4753 | [0.4749, 0.4758] | 0.0023 |
| sliderEmu | mel1280 | 0.5593 | [0.5537, 0.5652] | 0.0295 | 0.5096 | [0.5079, 0.5115] | 0.0093 |
| sliderEmu | mel256 | 0.5634 | [0.5580, 0.5691] | 0.0282 | 0.5005 | [0.4990, 0.5022] | 0.0088 |
| sliderEmu | psd_shape | 0.5851 | [0.5795, 0.5908] | 0.0295 | 0.5099 | [0.5079, 0.5121] | 0.0112 |
| valveEmu | mel1280 | 0.7645 | [0.7588, 0.7704] | 0.0307 | 0.5903 | [0.5853, 0.5954] | 0.0276 |
| valveEmu | mel256 | 0.7699 | [0.7637, 0.7760] | 0.0322 | 0.5887 | [0.5832, 0.5949] | 0.0319 |
| valveEmu | psd_shape | 0.7375 | [0.7296, 0.7452] | 0.0405 | 0.5239 | [0.5186, 0.5299] | 0.0291 |

Dependency versions:

- `numpy=2.0.2`
- `scipy=1.17.1`
- `scikit-learn=1.9.0`
- `soundfile=0.14.0`
- `librosa=0.11.0`
- `python=3.11.9`
