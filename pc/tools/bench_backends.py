"""Gdje uopste ima signala? Poredjenje vise detektora na ISTIM featurima.

Autoenkoder na fan masini daje hmean ~0.54, a prvi pokusaj sa samonadziranim
klasifikatorom 0.53 — dakle oba pogadjaju. Prije nego se bira slozenija
arhitektura, treba izmjeriti da li signal uopste postoji u ovim featurima i
koji ga nacin bodovanja najbolje vadi.

Probaju se, svi nad istim log-mel vektorima:
  ae_mse    rekonstrukciona greska postojeceg autoenkodera (referenca)
  maha_vec  Mahalanobis po vektoru, statistike sa trening skupa
  maha_clip Mahalanobis nad sazetkom klipa (sredina + std po mel traci)
  knn       udaljenost do najblizeg trening klipa (kosinusna, nad sazetkom)
  gmm       negativna log-vjerodostojnost GMM-a nad vektorima
  spec_mean gola sredina log-mela (kontrola: koliko nosi samo nivo/oblik spektra)

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_backends.py --machine fan
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data, eval as ev  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def clip_summary(f: np.ndarray) -> np.ndarray:
    """Sazetak klipa: sredina i std po dimenziji featura."""
    return np.concatenate([f.mean(axis=0), f.std(axis=0)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
    ap.add_argument("--tag", default="fan_tiny32_s0")
    args = ap.parse_args()

    mdir = ROOT / "data" / "dcase2026_dev" / args.machine
    cache = ROOT / "results" / "cache"
    train = data.list_clips(mdir, "train")
    test = data.list_clips(mdir, "test")
    tr_f = data.load_features(train, cache / f"{args.machine}_train.npz", "train")
    te_f = data.load_features(test, cache / f"{args.machine}_test.npz", "test")
    mean, std = data.fit_norm(tr_f)

    labels = np.array([c.label for c in test])
    domains = np.array([c.domain for c in test])
    res = {}

    def report(name: str, scores: np.ndarray) -> None:
        m = ev.dcase_metrics(scores, labels, domains)
        res[name] = m
        print(f"  {name:10s} auc_src={m['auc_source']:.4f}  auc_tgt={m['auc_target']:.4f}"
              f"  pauc={m['pauc']:.4f}  hmean={m['hmean']:.4f}")

    print(f"{args.machine}: {len(train)} train, {len(test)} test\n--- REZULTATI ---")

    # ---- 1. postojeci autoenkoder (referenca) ----
    try:
        from asd.quantize import TFLitePredict
        meta = json.loads((ROOT / "models" / f"{args.tag}_meta.json").read_text())
        m_, s_ = np.array(meta["mean"], np.float32), np.array(meta["std"], np.float32)
        pred = TFLitePredict((ROOT / "models" / f"{args.tag}_int8.tflite").read_bytes())
        sc = np.array([float(np.mean(np.mean(((f - m_) / s_ - pred((f - m_) / s_)) ** 2, axis=1)))
                       for f in te_f])
        report("ae_mse", sc)
    except Exception as e:                                      # noqa: BLE001
        print(f"  ae_mse preskocen: {e}")

    Xtr = np.concatenate([(f - mean) / std for f in tr_f])[::3].astype(np.float64)

    # ---- 2. Mahalanobis po vektoru ----
    mu = Xtr.mean(axis=0)
    C = np.cov(Xtr.T) + 1e-3 * np.eye(Xtr.shape[1])
    Ci = np.linalg.inv(C)
    sc = np.array([float(np.mean(np.einsum("ij,jk,ik->i", (f - mean) / std - mu, Ci,
                                           (f - mean) / std - mu))) for f in te_f])
    report("maha_vec", sc)

    # ---- 3. Mahalanobis nad sazetkom klipa ----
    Str = np.stack([clip_summary((f - mean) / std) for f in tr_f]).astype(np.float64)
    Ste = np.stack([clip_summary((f - mean) / std) for f in te_f]).astype(np.float64)
    mu2 = Str.mean(axis=0)
    C2 = np.cov(Str.T) + 1e-3 * np.eye(Str.shape[1])
    Ci2 = np.linalg.inv(C2)
    d = Ste - mu2
    report("maha_clip", np.einsum("ij,jk,ik->i", d, Ci2, d))

    # ---- 4. kNN nad sazetkom klipa (kosinusna) ----
    A = Str / np.linalg.norm(Str, axis=1, keepdims=True)
    B = Ste / np.linalg.norm(Ste, axis=1, keepdims=True)
    sim = B @ A.T
    k = 5
    report("knn", 1.0 - np.sort(sim, axis=1)[:, -k:].mean(axis=1))

    # ---- 5. GMM nad vektorima ----
    try:
        from sklearn.mixture import GaussianMixture
        g = GaussianMixture(n_components=8, covariance_type="diag", random_state=0,
                            max_iter=200).fit(Xtr[::2])
        report("gmm", np.array([-float(np.mean(g.score_samples((f - mean) / std)))
                                for f in te_f]))
    except Exception as e:                                      # noqa: BLE001
        print(f"  gmm preskocen: {e}")

    # ---- 6. kontrola: gola sredina log-mela ----
    report("spec_mean", np.array([float(np.mean(f)) for f in te_f]))

    out = ROOT / "results" / f"bench_{args.machine}.json"
    out.write_text(json.dumps(res, indent=2))
    best = max(res.items(), key=lambda kv: kv[1]["hmean"])
    print(f"\nnajbolji: {best[0]}  hmean={best[1]['hmean']:.4f}")
    print(f"zapisano: {out}")


if __name__ == "__main__":
    main()
