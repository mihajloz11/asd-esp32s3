"""Istrazivacka runda 4: validacija robusnog centra (medijana) i generalizacija.

Runda 3 je nasla: medijana kalibracionih sazetaka umjesto sredine podize
target AUC 0.684 -> 0.716. Ovdje se provjerava da to nije slucajnost:

  1. medijana vs sredina vs trimovana sredina (25%) na TARGET domenu,
     za tri feature konfiguracije (mel256+LW, gwrp r=0.99 max+LW, r=0.995 both+LW)
  2. isto na SOURCE domenu (posten korpus 800/190) — ako medijana pomaze i
     tamo, to je svojstvo protokola, ne target-tuning
  3. ansambl dvije najbolje konfiguracije sa medijanom
  4. ista provjera na drugim masinama (--machine ToyCar, bearingEmu...)

Protokol i seedovi kao ranije (3000+rep, 20 ponavljanja, k=20).

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_research4.py --machine fan
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
N_MELS = 128


def gwrp(sorted_desc: np.ndarray, r: float) -> np.ndarray:
    w = r ** np.arange(len(sorted_desc), dtype=np.float64)
    return (sorted_desc * w[:, None]).sum(0) / w.sum()


def make_feat(lm: np.ndarray, cfg: str) -> np.ndarray:
    if cfg == "mel256":
        return np.concatenate([lm.mean(0), lm.std(0)])
    s = np.sort(lm, axis=0)[::-1]
    if cfg == "gwrp99max":
        return np.concatenate([gwrp(s, 0.99), lm.std(0)])
    if cfg == "gwrp995both":
        return np.concatenate([gwrp(s, 0.995), gwrp(s[::-1], 0.995), lm.std(0)])
    raise ValueError(cfg)


def lw_inv(X: np.ndarray) -> np.ndarray:
    lw = LedoitWolf().fit(X)
    return np.linalg.pinv(lw.covariance_ + 1e-6 * np.eye(X.shape[1]))


def md(X, mu, Ci):
    d = X - mu
    return np.einsum("ij,jk,ik->i", d, Ci, d)


def center(cal: np.ndarray, how: str) -> np.ndarray:
    if how == "mean":
        return cal.mean(0)
    if how == "median":
        return np.median(cal, axis=0)
    if how == "trim25":
        lo, hi = np.percentile(cal, [25, 75], axis=0)
        m = np.clip(cal, lo, hi)          # winsorizovana sredina
        return m.mean(0)
    raise ValueError(how)


def protocol(F, Ci, pool_idx, anom_idx, k, repeats, how):
    aucs = []
    for rep in range(repeats):
        rng = np.random.default_rng(3000 + rep)
        idx = rng.permutation(len(pool_idx))
        cal_i, held = pool_idx[idx[:k]], pool_idx[idx[k:]]
        X = np.concatenate([held, anom_idx])
        y = np.concatenate([np.zeros(len(held)), np.ones(len(anom_idx))])
        mu = center(F[cal_i], how)
        aucs.append(roc_auc_score(y, md(F[X], mu, Ci)))
    return float(np.mean(aucs)), float(np.std(aucs)), [float(a) for a in aucs]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--k", type=int, default=20)
    args = ap.parse_args()

    mdir = ROOT / "data" / "dcase2026_dev" / args.machine
    cache = ROOT / "results" / "cache"
    train = data.list_clips(mdir, "train")
    test = data.list_clips(mdir, "test")
    tr_f = data.load_features(train, cache / f"{args.machine}_train.npz", "train")
    te_f = data.load_features(test, cache / f"{args.machine}_test.npz", "test")
    mean, std = data.fit_norm(tr_f)

    tr_dom = np.array([c.domain for c in train])
    te_dom = np.array([c.domain for c in test])
    te_lab = np.array([c.label for c in test])
    src = tr_dom == "source"
    n_tr = len(tr_f)

    m128, s128 = mean[:N_MELS], std[:N_MELS]
    lm_all = [((f[:, :N_MELS]) - m128) / s128 for f in tr_f + te_f]

    pool_t = np.concatenate([np.where(tr_dom == "target")[0],
                             n_tr + np.where((te_dom == "target") & (te_lab == 0))[0]])
    anom_t = n_tr + np.where((te_dom == "target") & (te_lab == 1))[0]

    rng0 = np.random.default_rng(7)
    perm = rng0.permutation(np.where(src)[0])
    corpus, src_rest = perm[:800], perm[800:]
    pool_s = np.concatenate([src_rest,
                             n_tr + np.where((te_dom == "source") & (te_lab == 0))[0]])
    anom_s = n_tr + np.where((te_dom == "source") & (te_lab == 1))[0]

    results: dict = {}
    rep, k = args.repeats, args.k
    cfgs = ("mel256", "gwrp99max", "gwrp995both")
    feats = {c: np.stack([make_feat(x, c) for x in lm_all]) for c in cfgs}
    Ci_t = {c: lw_inv(feats[c][:n_tr][src]) for c in cfgs}
    Ci_s = {c: lw_inv(feats[c][corpus]) for c in cfgs}

    print(f"=== {args.machine}: TARGET (k={k}) ===")
    for c in cfgs:
        for how in ("mean", "median", "trim25"):
            a, s, pr = protocol(feats[c], Ci_t[c], pool_t, anom_t, k, rep, how)
            results[f"tgt_{c}_{how}"] = {"auc": a, "std": s, "per_rep": pr}
            print(f"  {c:<12s} {how:<7s} {a:.3f} ± {s:.3f}")

    print(f"=== {args.machine}: SOURCE sanity (korpus 800) ===")
    for c in cfgs:
        for how in ("mean", "median"):
            a, s, _ = protocol(feats[c], Ci_s[c], pool_s, anom_s, k, rep, how)
            results[f"src_{c}_{how}"] = {"auc": a, "std": s}
            print(f"  {c:<12s} {how:<7s} {a:.3f} ± {s:.3f}")

    # ansambl: dvije najbolje target konfiguracije sa medijanom
    best = sorted(cfgs, key=lambda c: results[f"tgt_{c}_median"]["auc"],
                  reverse=True)[:2]
    print(f"=== ansambl (medijana): {best} ===")
    aucs = []
    for rp in range(rep):
        rng = np.random.default_rng(3000 + rp)
        idx = rng.permutation(len(pool_t))
        cal_i, held = pool_t[idx[:k]], pool_t[idx[k:]]
        X = np.concatenate([held, anom_t])
        y = np.concatenate([np.zeros(len(held)), np.ones(len(anom_t))])
        sc = sum(rankdata(md(feats[c][X], center(feats[c][cal_i], "median"),
                             Ci_t[c])) for c in best)
        aucs.append(roc_auc_score(y, sc))
    results["tgt_ens_median"] = {"auc": float(np.mean(aucs)),
                                 "std": float(np.std(aucs)),
                                 "per_rep": [float(a) for a in aucs]}
    print(f"  ens_median          {np.mean(aucs):.3f} ± {np.std(aucs):.3f}")

    p = ROOT / "results" / f"research4_{args.machine}.json"
    p.write_text(json.dumps(results, indent=2))
    print(f"\nzapisano: {p}")


if __name__ == "__main__":
    main()
