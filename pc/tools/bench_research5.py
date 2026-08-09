"""Istrazivacka runda 5: robusno OCJENJIVANJE (ne samo robusan centar).

Ideje povrh runde 4 (gwrp995both/mel256 + LW + medijana centra = 0.706-0.716):

  meddist   score(x) = MEDIJANA Mahalanobis udaljenosti do SVAKOG kalibracionog
            klipa (ne do centra). Robusno na outlier kalibracije i djelimicno
            na multimodalnost (3 brzine). Na ploci: k udaljenosti po prozoru.
  p25dist   isto, ali 25. percentil udaljenosti (blize najblizem modu).
  mcd       MinCovDet robusna kovarijansa umjesto LW (odbacuje outlier source
            klipove pri ucenju oblika).

Sve sa zamrznutim featurima iz runde 4, isti protokol i seedovi (3000+rep).

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_research5.py --machine fan
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.covariance import LedoitWolf, MinCovDet
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
    if cfg == "gwrp995both":
        return np.concatenate([gwrp(s, 0.995), gwrp(s[::-1], 0.995), lm.std(0)])
    raise ValueError(cfg)


def lw_inv(X):
    lw = LedoitWolf().fit(X)
    return np.linalg.pinv(lw.covariance_ + 1e-6 * np.eye(X.shape[1]))


def md(X, mu, Ci):
    d = X - mu
    return np.einsum("ij,jk,ik->i", d, Ci, d)


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

    results: dict = {}
    rep, k = args.repeats, args.k

    for cfg in ("mel256", "gwrp995both"):
        F = np.stack([make_feat(x, cfg) for x in lm_all])
        Xsrc = F[:n_tr][src]
        metrics = {"lw": lw_inv(Xsrc)}
        try:
            mcd = MinCovDet(random_state=0, support_fraction=0.8).fit(Xsrc)
            metrics["mcd"] = np.linalg.pinv(
                mcd.covariance_ + 1e-6 * np.eye(F.shape[1]))
        except Exception as e:  # noqa: BLE001
            print(f"  MCD nije prosao za {cfg}: {e}")

        for mname, Ci in metrics.items():
            for scoring in ("center_med", "meddist", "p25dist"):
                aucs = []
                for rp in range(rep):
                    rng = np.random.default_rng(3000 + rp)
                    idx = rng.permutation(len(pool_t))
                    cal_i, held = pool_t[idx[:k]], pool_t[idx[k:]]
                    X = np.concatenate([held, anom_t])
                    y = np.concatenate([np.zeros(len(held)), np.ones(len(anom_t))])
                    if scoring == "center_med":
                        sc = md(F[X], np.median(F[cal_i], axis=0), Ci)
                    else:
                        D = np.stack([md(F[X], F[j], Ci) for j in cal_i], axis=1)
                        sc = (np.median(D, axis=1) if scoring == "meddist"
                              else np.percentile(D, 25, axis=1))
                    aucs.append(roc_auc_score(y, sc))
                nm = f"{cfg}_{mname}_{scoring}"
                results[nm] = {"auc": float(np.mean(aucs)),
                               "std": float(np.std(aucs)),
                               "per_rep": [float(a) for a in aucs]}
                print(f"  {nm:<32s} {np.mean(aucs):.3f} ± {np.std(aucs):.3f}")

    p = ROOT / "results" / f"research5_{args.machine}.json"
    p.write_text(json.dumps(results, indent=2))
    print(f"\nzapisano: {p}")


if __name__ == "__main__":
    main()
