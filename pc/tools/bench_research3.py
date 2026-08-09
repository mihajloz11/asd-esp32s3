"""Istrazivacka runda 3: fino oko GWRP+LW pobjednika (0.686) i posten izbor r.

Novo u odnosu na rundu 2:
  - sweep r za GWRP, ali se r BIRA NA SOURCE DOMENU (validacija na zadatku
    koji smijemo gledati), pa se zamrznut primijeni na target. Bez curenja.
  - soft-min pooling (GWRP na rastuce sortiranim frejmovima): kvar moze biti
    i NESTANAK energije, ne samo visak.
  - kombinovani sazetak [soft-max | soft-min | std] (384 dim) + LW.
  - robusni centar: medijana kalibracionih sazetaka umjesto sredine.
  - parcijalna standardizacija: dimenzije se skaliraju kalibracionim std-om
    skupljenim ka 1 (beta*s_cal + (1-beta)) — jeftino na ploci.
  - k sweep (10/20/40) za pobjednika.

Protokol i seedovi kao runde 1-2 (3000+rep, kalibracioni klip se ne ocjenjuje,
kovarijansa iskljucivo sa source treninga).

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_research3.py --machine fan
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.covariance import LedoitWolf
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
N_MELS = 128


def gwrp(sorted_desc: np.ndarray, r: float) -> np.ndarray:
    w = r ** np.arange(len(sorted_desc), dtype=np.float64)
    return (sorted_desc * w[:, None]).sum(0) / w.sum()


def summ(lm: np.ndarray, r: float, mode: str) -> np.ndarray:
    s = np.sort(lm, axis=0)[::-1]          # opadajuce po traci
    parts = []
    if mode in ("max", "both"):
        parts.append(gwrp(s, r))           # soft-max
    if mode in ("min", "both"):
        parts.append(gwrp(s[::-1], r))     # soft-min
    parts.append(lm.std(axis=0))
    return np.concatenate(parts)


def lw_inv(X: np.ndarray) -> np.ndarray:
    lw = LedoitWolf().fit(X)
    return np.linalg.pinv(lw.covariance_ + 1e-6 * np.eye(X.shape[1]))


def md(X, mu, Ci):
    d = X - mu
    return np.einsum("ij,jk,ik->i", d, Ci, d)


def run_protocol(F, Ci, pool_idx, anom_idx, k, repeats, center="mean",
                 beta=0.0):
    aucs = []
    for rep in range(repeats):
        rng = np.random.default_rng(3000 + rep)
        idx = rng.permutation(len(pool_idx))
        cal_i = pool_idx[idx[:k]]
        held = pool_idx[idx[k:]]
        X = np.concatenate([held, anom_idx])
        y = np.concatenate([np.zeros(len(held)), np.ones(len(anom_idx))])
        cal = F[cal_i]
        mu = np.median(cal, axis=0) if center == "median" else cal.mean(0)
        Xf = F[X]
        if beta > 0.0:
            sc = beta * cal.std(axis=0) + (1.0 - beta)
            Xf = mu + (Xf - mu) / sc
        aucs.append(roc_auc_score(y, md(Xf, mu, Ci)))
    return float(np.mean(aucs)), float(np.std(aucs)), [float(a) for a in aucs]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
    ap.add_argument("--repeats", type=int, default=20)
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

    def pools(dom):
        p = np.concatenate([np.where(tr_dom == dom)[0],
                            n_tr + np.where((te_dom == dom) & (te_lab == 0))[0]])
        a = n_tr + np.where((te_dom == dom) & (te_lab == 1))[0]
        return p, a

    # POSTEN izbor: za source domen kovarijansa se uci na 800 source klipova,
    # a bazen za ocjenu su preostalih 190 + source test normalni (kao blend).
    rng0 = np.random.default_rng(7)
    perm = rng0.permutation(np.where(src)[0])
    corpus, src_rest = perm[:800], perm[800:]
    pool_s = np.concatenate([src_rest,
                             n_tr + np.where((te_dom == "source") & (te_lab == 0))[0]])
    anom_s = n_tr + np.where((te_dom == "source") & (te_lab == 1))[0]
    pool_t, anom_t = pools("target")

    results: dict = {}
    rep = args.repeats

    print("=== izbor r i moda na SOURCE domenu (kovarijansa sa 800, bazen 190+50) ===")
    configs = [(r, mode) for r in (0.97, 0.98, 0.985, 0.99, 0.995, 1.0)
               for mode in ("max", "both")]
    src_auc = {}
    feats = {}
    for r, mode in configs:
        F = np.stack([summ(x, r, mode) for x in lm_all])
        feats[(r, mode)] = F
        Ci_s = lw_inv(F[corpus])
        a, s, _ = run_protocol(F, Ci_s, pool_s, anom_s, 20, rep)
        src_auc[(r, mode)] = a
        print(f"  r={r:<6} mode={mode:<5} source AUC={a:.3f}")

    best_r, best_mode = max(src_auc, key=src_auc.get)
    print(f"\nizabrano na source: r={best_r}, mode={best_mode} "
          f"(AUC={src_auc[(best_r, best_mode)]:.3f})")
    results["izbor"] = {"r": best_r, "mode": best_mode,
                        "source_auc": src_auc[(best_r, best_mode)],
                        "source_sweep": {f"{r}_{m}": a for (r, m), a in src_auc.items()}}

    print("\n=== TARGET domen, zamrznuti hiperparametri ===")
    F = feats[(best_r, best_mode)]
    Ci = lw_inv(F[:n_tr][src])          # sada svih 990 source za kovarijansu
    for name, kw in (("frozen_k20", {}),
                     ("frozen_k20_median", {"center": "median"}),
                     ("frozen_k20_beta0.3", {"beta": 0.3}),
                     ("frozen_k20_med_b0.3", {"center": "median", "beta": 0.3})):
        a, s, pr = run_protocol(F, Ci, pool_t, anom_t, 20, rep, **kw)
        results[name] = {"auc": a, "std": s, "per_rep": pr}
        print(f"  {name:<22s} {a:.3f} ± {s:.3f}")

    for k in (10, 40):
        a, s, pr = run_protocol(F, Ci, pool_t, anom_t, k, rep)
        results[f"frozen_k{k}"] = {"auc": a, "std": s, "per_rep": pr}
        print(f"  frozen_k{k:<17d} {a:.3f} ± {s:.3f}")

    # referentne tacke na istim seedovima
    F256 = np.stack([np.concatenate([x.mean(0), x.std(0)]) for x in lm_all])
    a, s, pr = run_protocol(F256, lw_inv(F256[:n_tr][src]), pool_t, anom_t, 20, rep)
    results["ref_mel256_lw"] = {"auc": a, "std": s, "per_rep": pr}
    print(f"  {'ref_mel256_lw':<22s} {a:.3f} ± {s:.3f}")

    p = ROOT / "results" / f"research3_{args.machine}.json"
    p.write_text(json.dumps(results, indent=2))
    print(f"\nzapisano: {p}")


if __name__ == "__main__":
    main()
