"""Istrazivacka runda 6: spoj dva nezavisna otkrica ove nedjelje.

  1. psd_shape (bench_periodicity): visokorezolucioni Welch spektar, 96 log
     traka, gain-normalizovan -> target 0.864 (izbor varijante na source).
  2. medijana centra (bench_research3/4): robusni kalibracioni centar
     -> +0.01 do +0.03 nad sredinom, potvrdjeno na 7 masina.

Ovdje: psd_shape sa medijanom centra, rang-ansambl psd_shape + mel256,
k sweep za najbolju kombinaciju. Protokol i seedovi kao sve runde (3000+rep).

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_research6.py --machine fan
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.covariance import LedoitWolf
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def fit_precision(X: np.ndarray):
    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8
    Z = (X - mean) / std
    return mean, std, LedoitWolf().fit(Z).precision_


def maha(X, center, precision):
    d = X - center
    return np.einsum("ij,jk,ik->i", d, precision, d)


def mel_summary(f: np.ndarray) -> np.ndarray:
    lm = np.concatenate([f[:, :128], f[-1, 128:].reshape(4, 128)], axis=0)
    return np.concatenate([lm.mean(axis=0), lm.std(axis=0)]).astype(np.float64)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
    ap.add_argument("--repeats", type=int, default=20)
    args = ap.parse_args()

    mdir = ROOT / "data" / "dcase2026_dev" / args.machine
    cache = ROOT / "results" / "cache"
    train = data.list_clips(mdir, "train")
    test = data.list_clips(mdir, "test")
    tr_dom = np.array([c.domain for c in train])
    te_dom = np.array([c.domain for c in test])
    te_lab = np.array([c.label for c in test])
    n_tr = len(train)

    z = np.load(cache / f"{args.machine}_periodicity.npz")
    PSD = z["psd_shape"]
    tr_f = data.load_features(train, cache / f"{args.machine}_train.npz", "train")
    te_f = data.load_features(test, cache / f"{args.machine}_test.npz", "test")
    MEL = np.stack([mel_summary(f) for f in tr_f + te_f])

    src = np.where(tr_dom == "source")[0]
    pool = np.concatenate([np.where(tr_dom == "target")[0],
                           n_tr + np.where((te_dom == "target") & (te_lab == 0))[0]])
    anom = n_tr + np.where((te_dom == "target") & (te_lab == 1))[0]

    m_p, s_p, P_p = fit_precision(PSD[src])
    Zp = (PSD - m_p) / s_p
    m_m, s_m, P_m = fit_precision(MEL[src])
    Zm = (MEL - m_m) / s_m

    results: dict = {}
    rep = args.repeats

    def run(name, k, score_fn):
        aucs = []
        for rp in range(rep):
            rng = np.random.default_rng(3000 + rp)
            idx = rng.permutation(len(pool))
            cal, held = pool[idx[:k]], pool[idx[k:]]
            X = np.concatenate([held, anom])
            y = np.concatenate([np.zeros(len(held)), np.ones(len(anom))])
            aucs.append(roc_auc_score(y, score_fn(cal, X)))
        results[name] = {"auc": float(np.mean(aucs)), "std": float(np.std(aucs)),
                         "per_rep": [float(a) for a in aucs]}
        print(f"  {name:<30s} {np.mean(aucs):.3f} ± {np.std(aucs):.3f}")

    for k in (10, 20, 40):
        run(f"psd_mean_k{k}", k,
            lambda c, X: maha(Zp[X], Zp[c].mean(0), P_p))
        run(f"psd_median_k{k}", k,
            lambda c, X: maha(Zp[X], np.median(Zp[c], axis=0), P_p))
        run(f"ens_psd+mel_med_k{k}", k,
            lambda c, X: rankdata(maha(Zp[X], np.median(Zp[c], 0), P_p))
            + rankdata(maha(Zm[X], np.median(Zm[c], 0), P_m)))

    p = ROOT / "results" / f"research6_{args.machine}.json"
    p.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nzapisano: {p}")


if __name__ == "__main__":
    main()
