# Alati

Skripte se pokreću iz korijena repoa, osim gdje docstring kaže drugačije.
Putanje se ne mijenjaju jer na njih upućuju dokumenti i sačuvani rezultati.

## Aktuelni tok

| Namjena | Alati |
|---|---|
| Fizički run na ventilatoru | `start_fan_run.py` (jedna komanda), `physical_fan_experiment.py` (zapis i provjera runa), `asd_panel.py` (panel, virtuelni taster), `guided25_launcher.ps1` |
| Politike iz normalnih podataka | `derive_commissioning_policy.py`, `derive_interference_policy.py`, `derive_presence_policy.py`, `derive_temporal_policy.py` |
| Saglasnost firmvera i politika | `check_schema_consistency.py` (CI) |
| Model za firmware | `gen_psd_model_header.py` → `psd_model_data.h` |
| Razvojna evaluacija | `evaluate_canonical.py` (kanonski protokol), `evaluate_advanced.py`, `evaluate_fan_noise_candidates.py` |
| Analiza fizičkih proba | `analyze_trial_features.py`, `diag_calibration_loo.py`, `probe_psd_gain.py` |
| PC ↔ uređaj | `psd_verify_compare.py`, `live_compare.py`, `mic_capture.py` |
| Revizija repoa | `audit_repository.py`, `audit_git_history.py`, `verify_frozen_artifacts.py` |
| Kopija za predaju | `napravi_predaju.py` (bez `privatno/` i `radovi/`, sa provjerom curenja) |

## Probe preko zvučnika (avgust 2026)

Prije fizičkog ventilatora uređaj je slušao DCASE snimke sa zvučnika:
`psd_live_demo.py`, `psd_continuous_test.py`, `psd_severity_test.py`,
`psd_channel_probe.py`, `false_alarm_test.py`, `check_fault_type.py`.
Rezultati su u `results/false_alarm/` i u `docs/put-do-modela.md`.

## Istorija istraživanja (jul–avgust 2026)

Ne koriste se u finalnom toku; čuvaju se jer rad i dokumenti citiraju
njihove brojke.

| Grupa | Alati |
|---|---|
| Autoenkoder i TFLM (E1–E4) | `gen_model_header.py`, `gen_mel_header.py`, `export_test_vectors.py`, `prepare_eval_clips.py`, `compare_eval.py`, `score_mahala.py`, `score_mahala_int8.py`, `results_stats.py`, `plot_pareto.py` |
| Neuronske alternative | `train_embed.py`, `train_ssl.py` |
| Mahalanobis nad log-mel i PSD | `bench_adapt.py`, `bench_backends.py`, `bench_blend.py`, `bench_deploy.py`, `bench_domain.py`, `bench_frontend.py`, `bench_modes.py`, `bench_pool.py`, `bench_research*.py`, `bench_final*.py`, `bench_periodicity.py` (izvor `psd_shape`) |
| Praćenje sweep-ova | `gen_dashboard.py`, `live_dashboard.py`, `live_monitor.py`, `progress.py`, `fan_seed_dash.py`; PowerShell skripte u `pc/` |

Istorija odluka: [put do modela](../../docs/put-do-modela.md),
[odluka o finalnom modelu](../../docs/odluka-finalni-model.md).
