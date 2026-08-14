r"""Faze 3, 5 i 6 — developmental evaluator u ODVOJENOM namespaceu.

Kanonski protokol `canonical-evaluation-v1.1.0` se ovim NE dira. Ovdje se
ispituju kandidati koje plan navodi unaprijed, po istoj granici podataka:

  Faza 3 (f0 / rezim):     `psd_order`, `psd_regime`
  Faza 5 (dual-channel):   `psd_logratio`, `psd_coherence`, `psd_masked`
  Faza 6 (tranzijent):     `transient`, `psd_plus_transient`

GRANICA PODATAKA, ista kao kanonska:

* standardizacija i Ledoit-Wolf precision uce se SAMO na `source/train/normal`;
* centar uci SAMO kalibracioni dio target normalnog poola;
* target anomalni klipovi se ucitavaju TEK u zavrsnoj fazi, kad su svi modeli
  fitovani i svi splitovi zamrznuti;
* lista kandidata je konstanta u kodu i ne mijenja se prema rezultatu;
* svi kandidati dobijaju IDENTICNE splitove.

Sve brojke ostaju razvojne. Ranije je vec bio istorijski model-selection bias,
pa se nijedan rezultat odavde ne smije zvati nezavisnom finalnom potvrdom.

Upotreba (iz korijena repozitorija):

    .venv\Scripts\python.exe pc\tools\evaluate_advanced.py
    .venv\Scripts\python.exe pc\tools\evaluate_advanced.py --n-splits 10
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import coherence, welch
from sklearn.covariance import LedoitWolf
from sklearn.metrics import roc_auc_score

PC_DIR = Path(__file__).resolve().parents[1]
ROOT = PC_DIR.parent
sys.path.insert(0, str(PC_DIR))

from asd import features  # noqa: E402

FAN = ROOT / "data" / "dcase2026_dev" / "fan"
OUT = ROOT / "results" / "advanced"
PROTOCOL = "advanced-evaluation-v1.0.0"
SR = features.SR
MAX_FPR = 0.1
N_CAL = 10
DEFAULT_SPLITS = 20
SPLIT_SEED = 20260814

# Zakljucano PRIJE gledanja u rezultat.
BAND_EDGES = np.geomspace(10.0, 4000.0, 97)
F0_RANGE = (20.0, 200.0)      # lopatasti ventilator: osnovna i njeni harmonici
F0_HARMONICS = 6
ORDER_EDGES = np.linspace(0.5, 24.5, 97)   # u jedinicama f0

CANDIDATES = (
    "psd_shape",        # kanonski baseline, ponovljen ovdje radi poredjenja
    "psd_order",        # Faza 3
    "psd_regime",       # Faza 3
    "psd_logratio",     # Faza 5
    "psd_coherence",    # Faza 5
    "psd_masked",       # Faza 5
    "transient",        # Faza 6
    "psd_plus_transient",  # Faza 6
)


# --- osnovni spektralni alat -------------------------------------------------

def band_log_power(freq, power, edges):
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (freq >= lo) & (freq < hi)
        out.append(np.log10(float(power[mask].mean()) + 1e-20) if np.any(mask) else -20.0)
    return np.asarray(out, np.float64)


def welch_psd(signal):
    return welch(signal, fs=SR, window="hann", nperseg=8192, noverlap=4096,
                 detrend=False, scaling="spectrum")


def estimate_f0(freq, power):
    """Harmonic summation: f0 sa najvecim zbirom snage na svojim harmonicima.

    Confidence je odnos najbolje i medijalne harmonijske sume; iznad 1 znaci da
    se kandidat izdvaja iz pozadine. Postupak, opseg i broj harmonika su
    zakljucani prije bilo kakve evaluacije.
    """
    grid = np.linspace(F0_RANGE[0], F0_RANGE[1], 361)
    linear = np.maximum(power, 1e-20)
    scores = np.empty(len(grid))
    for index, f0 in enumerate(grid):
        total = 0.0
        for harmonic in range(1, F0_HARMONICS + 1):
            target = f0 * harmonic
            if target >= freq[-1]:
                break
            total += float(np.log10(linear[np.argmin(np.abs(freq - target))]))
        scores[index] = total
    best = int(np.argmax(scores))
    median = float(np.median(scores))
    spread = float(np.std(scores)) or 1e-12
    return float(grid[best]), float((scores[best] - median) / spread)


def order_warped(freq, power, f0):
    """PSD preslikan u jedinice reda (f / f0). Ako f0 nije upotrebljiv, vraca
    ravan vektor -- pozivalac to vidi kroz confidence."""
    if not np.isfinite(f0) or f0 <= 0:
        return np.zeros(len(ORDER_EDGES) - 1)
    raw = band_log_power(freq / f0, power, ORDER_EDGES)
    return raw - raw.mean()


def transient_features(signal):
    """Faza 6: brzi put na kratkim okvirima. Namjerno NE koristi Welch.

    Spectral flux, frame crest i kurtosis su osjetljivi na udare i impulse,
    a ne na sporu promjenu oblika spektra koju vec hvata PSD.
    """
    frame, hop = 512, 256
    count = 1 + (len(signal) - frame) // hop
    window = np.hanning(frame)
    spectra = np.empty((count, frame // 2 + 1))
    crest = np.empty(count)
    for i in range(count):
        chunk = signal[i * hop : i * hop + frame]
        spectra[i] = np.abs(np.fft.rfft(chunk * window))
        rms = float(np.sqrt(np.mean(chunk ** 2))) or 1e-12
        crest[i] = float(np.max(np.abs(chunk))) / rms
    flux = np.sqrt(np.sum(np.diff(spectra, axis=0) ** 2, axis=1))
    envelope = spectra.sum(axis=1)
    envelope = envelope / (envelope.mean() + 1e-12)

    def moments(values):
        mean = float(values.mean())
        sd = float(values.std()) or 1e-12
        centred = (values - mean) / sd
        return [mean, sd, float(np.percentile(values, 95)),
                float((centred ** 4).mean())]

    return np.asarray(moments(flux) + moments(crest) + moments(envelope),
                      dtype=np.float64)


# --- ekstrakcija svih kandidata iz jednog klipa ------------------------------

def extract(path: Path) -> dict[str, np.ndarray]:
    audio, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    if sample_rate != SR:
        raise ValueError(f"{path}: ocekivano {SR} Hz, dobijeno {sample_rate}")
    near = audio[:, 0].astype(np.float64)
    near = near - near.mean()
    far = audio[:, -1].astype(np.float64)
    far = far - far.mean()

    freq, power_near = welch_psd(near)
    _, power_far = welch_psd(far)

    psd = band_log_power(freq, power_near, BAND_EDGES)
    psd = psd - psd.mean()

    f0, confidence = estimate_f0(freq, power_near)

    log_near = band_log_power(freq, power_near, BAND_EDGES)
    log_far = band_log_power(freq, power_far, BAND_EDGES)
    ratio = log_near - log_far
    ratio = ratio - ratio.mean()

    # Coherence: koliko je energija u traci zajednicka oba kanala. Blizu 1 =
    # dolazi iz okoline (oba mikrofona je cuju isto), blizu 0 = lokalno.
    cfreq, coh = coherence(near, far, fs=SR, nperseg=4096, noverlap=2048)
    coherence_bands = band_log_power(cfreq, np.clip(coh, 1e-6, 1.0), BAND_EDGES)

    # Maska: trake u kojima je far uporediv sa near su vjerovatno okolina i
    # potiskuju se. Ovo NIJE prosto near-far oduzimanje (vec probano i palo).
    weight = np.clip(1.0 - 10.0 ** (log_far - log_near), 0.0, 1.0)
    masked = log_near + np.log10(weight + 1e-3)
    masked = masked - masked.mean()

    fast = transient_features(near)

    return {
        "psd_shape": psd,
        "psd_order": order_warped(freq, power_near, f0),
        "psd_regime": psd,          # isti feature; razlika je u centru, vidi nize
        "psd_logratio": ratio,
        "psd_coherence": coherence_bands - coherence_bands.mean(),
        "psd_masked": masked,
        "transient": fast,
        "psd_plus_transient": np.concatenate([psd, fast]),
        "_f0": np.asarray([f0, confidence]),
    }


# --- kohorte -----------------------------------------------------------------

def harmonic_structure_by_speed(paths: list[Path], per_speed: int = 40) -> dict:
    """Kontrolna provjera Faze 3, prije nego se f0 nalaz proglasi negativnim.

    Ako f0 ispadne isti za sve tri brzine, prvo pitanje NIJE 'da li rezimi
    postoje' nego 'da li estimator radi'. Zato se nezavisno od estimatora
    gleda gdje su tonalni vrhovi iznad spektralne pozadine, po brzini. Ako su
    vrhovi na istim frekvencijama, f0 zaista jeste isti i nalaz stoji; ako
    nisu, greska je u estimatoru. Isti obrazac kao P9/P14/P16 u
    docs/problemi-i-rjesenja.md: prvo artefakt mjerenja, pa tek onda hipoteza.
    """
    from scipy.ndimage import uniform_filter1d

    out: dict[str, dict] = {}
    for speed in ("spd_1", "spd_2", "spd_3"):
        files = [p for p in paths if p.name.endswith(f"{speed}.wav")][:per_speed]
        if not files:
            continue
        accumulated = None
        for path in files:
            audio, _ = sf.read(path, dtype="float32", always_2d=True)
            signal = audio[:, 0].astype(np.float64)
            signal -= signal.mean()
            freq, power = welch_psd(signal)
            log_power = np.log10(power + 1e-20)
            accumulated = log_power if accumulated is None else accumulated + log_power
        mean_log = accumulated / len(files)
        background = uniform_filter1d(mean_log, size=51)
        residual = mean_log - background
        band = (freq >= 15.0) & (freq <= 500.0)
        top = np.argsort(-residual[band])[:6]
        out[speed] = {
            "n": len(files),
            "peak_hz": sorted(float(f) for f in freq[band][top]),
            "max_prominence_decades": float(residual[band].max()),
        }
    # Poredjenje sa tolerancijom od jednog FFT bina. Welch sa nperseg=8192 na
    # 16 kHz daje razmak 1,95 Hz, pa se vrhovi udaljeni manje od toga NE
    # razlikuju fizicki, nego samo padaju u susjedni bin.
    bin_hz = float(freq[1] - freq[0])
    peak_lists = [row["peak_hz"] for key, row in out.items() if key.startswith("spd_")]
    reference = peak_lists[0]
    identical = all(
        len(other) == len(reference)
        and all(abs(a - b) <= bin_hz * 1.01 for a, b in zip(reference, other))
        for other in peak_lists[1:]
    )
    out["fft_bin_hz"] = bin_hz
    out["peaks_identical_across_speeds"] = bool(identical)
    out["comparison"] = f"peaks match within one FFT bin ({bin_hz:.2f} Hz)"
    return out


def cohort_paths() -> dict[str, list[Path]]:
    return {
        "source_train_normal": sorted(FAN.glob("train/*source_train_normal*.wav")),
        "target_train_normal": sorted(FAN.glob("train/*target_train_normal*.wav")),
        "target_test_normal": sorted(FAN.glob("test/*target_test_normal*.wav")),
        "target_test_anomaly": sorted(FAN.glob("test/*target_test_anomaly*.wav")),
    }


def load_cohort(name: str, paths: list[Path], cache_root: Path) -> dict[str, np.ndarray]:
    cache = cache_root / f"adv_{name}.npz"
    if cache.exists():
        data = np.load(cache)
        return {key: data[key] for key in data.files}
    print(f"  {name}: {len(paths)} klipova", flush=True)
    bundles = [extract(p) for p in paths]
    stacked = {key: np.stack([b[key] for b in bundles]) for key in bundles[0]}
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, **stacked)
    return stacked


def fit_source_only(values):
    mean = values.mean(axis=0)
    scale = values.std(axis=0)
    scale = np.where(scale < 1e-8, 1.0, scale)
    precision = LedoitWolf().fit((values - mean) / scale).precision_
    return mean, scale, precision


def mahalanobis(values, center, precision):
    difference = values - center
    return np.einsum("ij,jk,ik->i", difference, precision, difference)


def partial_auc(labels, scores, max_fpr=MAX_FPR):
    """Standardizovan pAUC, isti oblik kao u kanonskom evaluatoru."""
    return float(roc_auc_score(labels, scores, max_fpr=max_fpr))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n-splits", type=int, default=DEFAULT_SPLITS)
    parser.add_argument("--cache", default=str(OUT))
    args = parser.parse_args()
    cache_root = Path(args.cache)

    paths = cohort_paths()
    print("faza 1 — normalne kohorte (anomalne se JOS ne otvaraju):")
    source = load_cohort("source_train_normal", paths["source_train_normal"], cache_root)
    target_normal_a = load_cohort("target_train_normal", paths["target_train_normal"], cache_root)
    target_normal_b = load_cohort("target_test_normal", paths["target_test_normal"], cache_root)
    target_normal = {key: np.concatenate([target_normal_a[key], target_normal_b[key]])
                     for key in target_normal_a}

    # --- normal-only dijagnostika Faze 3 ---
    f0_source = source["_f0"]
    f0_target = target_normal["_f0"]
    speeds = [p.name.rsplit("_", 2)[-2] + "_" + p.name.rsplit("_", 1)[-1].replace(".wav", "")
              for p in paths["source_train_normal"]]
    by_speed: dict[str, list[float]] = {}
    for speed, (f0, _) in zip(speeds, f0_source):
        by_speed.setdefault(speed, []).append(f0)
    f0_report = {
        "source_f0_median_hz": float(np.median(f0_source[:, 0])),
        "source_confidence_median": float(np.median(f0_source[:, 1])),
        "target_f0_median_hz": float(np.median(f0_target[:, 0])),
        "target_confidence_median": float(np.median(f0_target[:, 1])),
        "per_speed": {speed: {"n": len(values),
                              "median_hz": float(np.median(values)),
                              "sd_hz": float(np.std(values))}
                      for speed, values in sorted(by_speed.items())},
    }
    print("\nFaza 3 — f0 na NORMALNIM klipovima (bez anomalija):")
    print(f"  source medijana {f0_report['source_f0_median_hz']:.1f} Hz, "
          f"confidence {f0_report['source_confidence_median']:.2f}")
    for speed, row in f0_report["per_speed"].items():
        print(f"  {speed}: n={row['n']:4d} medijana {row['median_hz']:6.1f} Hz "
              f"sd {row['sd_hz']:5.1f} Hz")
    speed_medians = [row["median_hz"] for row in f0_report["per_speed"].values()]
    speed_sds = [row["sd_hz"] for row in f0_report["per_speed"].values()]
    separable = (len(speed_medians) > 1
                 and (max(speed_medians) - min(speed_medians)) > 2.0 * max(speed_sds))
    f0_report["speeds_separable_from_normal_only"] = bool(separable)
    print(f"  rezimi razdvojivi iz normalnih klipova: "
          f"{'DA' if separable else 'NE'}")

    # Kontrola: da li je isti f0 nalaz ili artefakt estimatora?
    structure = harmonic_structure_by_speed(paths["source_train_normal"])
    f0_report["harmonic_structure_control"] = structure
    print("  kontrola tonalnih vrhova, nezavisno od estimatora:")
    for speed in ("spd_1", "spd_2", "spd_3"):
        if speed in structure:
            peaks = ", ".join(f"{f:.1f}" for f in structure[speed]["peak_hz"])
            print(f"    {speed}: {peaks} Hz")
    print(f"    vrhovi identicni preko brzina: "
          f"{'DA' if structure['peaks_identical_across_speeds'] else 'NE'}"
          f"  -> f0 nalaz {'stoji' if structure['peaks_identical_across_speeds'] else 'treba provjeriti'}")

    # --- modeli i splitovi se zamrzavaju PRIJE otvaranja anomalija ---
    models = {}
    for name in CANDIDATES:
        models[name] = fit_source_only(source[name])
    rng = np.random.default_rng(SPLIT_SEED)
    n_target = len(target_normal["psd_shape"])
    splits = [rng.permutation(n_target) for _ in range(args.n_splits)]
    print(f"\nmodeli fitovani, {len(splits)} splitova zamrznuto")

    # --- tek sada anomalije ---
    print("\nfaza 2 — otvaram target anomalne klipove:")
    anomaly = load_cohort("target_test_anomaly", paths["target_test_anomaly"], cache_root)

    results = {}
    for name in CANDIDATES:
        mean, scale, precision = models[name]
        aucs, paucs = [], []
        for order in splits:
            cal = target_normal[name][order[:N_CAL]]
            held = target_normal[name][order[N_CAL:]]
            center = ((cal - mean) / scale).mean(axis=0)
            if name == "psd_regime":
                # Faza 3: centar po rezimu. Rezim se bira iz f0 kalibracionih
                # klipova, pa se svaki test klip poredi sa NAJBLIZIM centrom.
                cal_f0 = target_normal["_f0"][order[:N_CAL], 0]
                edges = np.quantile(cal_f0, [0.0, 1 / 3, 2 / 3, 1.0])
                centers = []
                for lo, hi in zip(edges[:-1], edges[1:]):
                    mask = (cal_f0 >= lo) & (cal_f0 <= hi)
                    if mask.sum() >= 2:
                        centers.append(((cal[mask] - mean) / scale).mean(axis=0))
                if not centers:
                    centers = [center]
                normal_scores = np.min([mahalanobis((held - mean) / scale, c, precision)
                                        for c in centers], axis=0)
                anomaly_scores = np.min(
                    [mahalanobis((anomaly[name] - mean) / scale, c, precision)
                     for c in centers], axis=0)
            else:
                normal_scores = mahalanobis((held - mean) / scale, center, precision)
                anomaly_scores = mahalanobis((anomaly[name] - mean) / scale,
                                             center, precision)
            labels = np.concatenate([np.zeros(len(normal_scores)),
                                     np.ones(len(anomaly_scores))])
            scores = np.concatenate([normal_scores, anomaly_scores])
            aucs.append(float(roc_auc_score(labels, scores)))
            paucs.append(partial_auc(labels, scores))
        results[name] = {
            "auc_mean": float(np.mean(aucs)),
            "auc_sd": float(np.std(aucs)),
            "pauc_mean": float(np.mean(paucs)),
            "pauc_sd": float(np.std(paucs)),
            "n_splits": len(splits),
        }

    baseline = results["psd_shape"]["auc_mean"]
    print(f"\n{'kandidat':<22} {'faza':<8} {'AUC':>16} {'pAUC@0.1':>16} {'vs baseline':>12}")
    print("-" * 78)
    phase_of = {
        "psd_shape": "baseline", "psd_order": "3", "psd_regime": "3",
        "psd_logratio": "5", "psd_coherence": "5", "psd_masked": "5",
        "transient": "6", "psd_plus_transient": "6",
    }
    for name in CANDIDATES:
        row = results[name]
        delta = row["auc_mean"] - baseline
        print(f"{name:<22} {phase_of[name]:<8} "
              f"{row['auc_mean']:.4f} ± {row['auc_sd']:.4f}  "
              f"{row['pauc_mean']:.4f} ± {row['pauc_sd']:.4f}  "
              f"{delta:+11.4f}")

    record = {
        "protocol": PROTOCOL,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "developmental only; canonical-evaluation-v1.1.0 is untouched",
        "warning": "Historical model-selection bias applies. These numbers are not an "
                   "independent final validation and must not be reported as one.",
        "n_splits": args.n_splits,
        "split_seed": SPLIT_SEED,
        "candidates_declared_before_running": list(CANDIDATES),
        "faza3_f0_normal_only": f0_report,
        "results": results,
        "baseline_auc": baseline,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "advanced_results.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nzapisano: {OUT / 'advanced_results.json'}")


if __name__ == "__main__":
    main()
