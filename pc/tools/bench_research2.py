"""Istrazivacka runda 2: nove familije featura preko mel256+LW (0.673).

Runda 1 (bench_research.py) je pokazala: problem NIJE bio u pristupu nego u
uslovljenosti kovarijanse — Ledoit-Wolf skupljanje u 256-dim prostoru daje
+0.030 nad referencom na uparenim seedovima (19/20, p<1e-4). Sve ispod su
featuri koje sazetak mean+std UOPSTE ne vidi:

  lw1280     LW i na starom 1280 prostoru (mozda i tamo pomaze)
  gwrp99lw   GWRP pooling r=0.99 + LW
  pctl       percentili p10/p50/p90 po traci + LW (ranije palo BEZ LW)
  coup       sprega medju trakama UNUTAR klipa: korelacija traka b i b+lag
             (lag 1,2) preko vremena. Dokumentovano je da je "signal u vezama
             izmedju mel traka" — ovo mjeri te veze po klipu, gain-invarijantno.
  tautoc     temporalna autokorelacija svake trake (lag 1,2,4,8) — glatkoca
             i periodicnost kolebanja energije.
  modspec    modulacioni spektar: snaga kolebanja energije trake u 4 opsega
             (0.25-1, 1-4, 4-8, 8-15.6 Hz) — disbalans/lezaj = modulacija.
  ens_*      rang-ansambli komplementarnih familija.

Protokol i seedovi identicni rundi 1 (3000+rep, k=20, 20 ponavljanja,
kalibracioni klip se ne ocjenjuje, ucenje iskljucivo na source treningu).

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_research2.py --machine fan
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
FPS = 16000 / 512  # frejmova u sekundi


def summ_meanstd(lm: np.ndarray) -> np.ndarray:
    return np.concatenate([lm.mean(axis=0), lm.std(axis=0)])


def summ_gwrp(lm: np.ndarray, r: float) -> np.ndarray:
    s = np.sort(lm, axis=0)[::-1]
    w = r ** np.arange(len(s), dtype=np.float64)
    return np.concatenate([(s * w[:, None]).sum(0) / w.sum(), lm.std(0)])


def summ_pctl(lm: np.ndarray) -> np.ndarray:
    return np.percentile(lm, [10, 50, 90], axis=0).ravel()


def summ_coup(lm: np.ndarray) -> np.ndarray:
    """Korelacija trake b sa trakom b+lag preko vremena, lag 1 i 2."""
    x = lm - lm.mean(axis=0, keepdims=True)
    n = np.sqrt((x * x).sum(axis=0)) + 1e-9
    out = []
    for lag in (1, 2):
        out.append((x[:, :-lag] * x[:, lag:]).sum(0) / (n[:-lag] * n[lag:]))
    return np.concatenate(out)


def summ_tautoc(lm: np.ndarray) -> np.ndarray:
    """Temporalna autokorelacija svake trake na lagovima 1,2,4,8 frejmova."""
    x = lm - lm.mean(axis=0, keepdims=True)
    n = (x * x).sum(axis=0) + 1e-9
    out = []
    for lag in (1, 2, 4, 8):
        out.append((x[:-lag] * x[lag:]).sum(0) / n)
    return np.concatenate(out)


def summ_modspec(lm: np.ndarray) -> np.ndarray:
    """Log snaga modulacije energije trake u 4 opsega (do Nyquista 15.6 Hz)."""
    x = lm - lm.mean(axis=0, keepdims=True)
    P = np.abs(np.fft.rfft(x, axis=0)) ** 2
    freqs = np.fft.rfftfreq(len(x), d=1.0 / FPS)
    out = []
    for lo, hi in ((0.25, 1.0), (1.0, 4.0), (4.0, 8.0), (8.0, FPS / 2)):
        m = (freqs >= lo) & (freqs < hi)
        out.append(np.log10(P[m].mean(axis=0) + 1e-9))
    return np.concatenate(out)


def lw_inv(X: np.ndarray) -> np.ndarray:
    lw = LedoitWolf().fit(X)
    return np.linalg.pinv(lw.covariance_ + 1e-6 * np.eye(X.shape[1]))


def md(X: np.ndarray, mu: np.ndarray, Ci: np.ndarray) -> np.ndarray:
    d = X - mu
    return np.einsum("ij,jk,ik->i", d, Ci, d)


def evaluate(name, score_fn, pool_idx, anom_idx, k, repeats, results):
    aucs = []
    for rep in range(repeats):
        rng = np.random.default_rng(3000 + rep)
        idx = rng.permutation(len(pool_idx))
        cal = pool_idx[idx[:k]]
        held = pool_idx[idx[k:]]
        X = np.concatenate([held, anom_idx])
        y = np.concatenate([np.zeros(len(held)), np.ones(len(anom_idx))])
        aucs.append(roc_auc_score(y, score_fn(cal, X)))
    m, s = float(np.mean(aucs)), float(np.std(aucs))
    results[name] = {"auc": m, "std": s, "per_rep": [float(a) for a in aucs]}
    print(f"  {name:<28s} {m:.3f} ± {s:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
    ap.add_argument("--domain", default="target", choices=["source", "target"])
    ap.add_argument("--k", type=int, default=20)
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
    d = args.domain
    pool_idx = np.concatenate([np.where(tr_dom == d)[0],
                               n_tr + np.where((te_dom == d) & (te_lab == 0))[0]])
    anom_idx = n_tr + np.where((te_dom == d) & (te_lab == 1))[0]

    m128, s128 = mean[:N_MELS], std[:N_MELS]
    lm_all = [( (f[:, :N_MELS]) - m128) / s128 for f in tr_f + te_f]

    S1280 = np.stack([np.concatenate([((f - mean) / std).mean(0),
                                      ((f - mean) / std).std(0)])
                      for f in tr_f + te_f])

    fams = {
        "mel256_lw": np.stack([summ_meanstd(x) for x in lm_all]),
        "gwrp99_lw": np.stack([summ_gwrp(x, 0.99) for x in lm_all]),
        "pctl_lw": np.stack([summ_pctl(x) for x in lm_all]),
        "coup_lw": np.stack([summ_coup(x) for x in lm_all]),
        "tautoc_lw": np.stack([summ_tautoc(x) for x in lm_all]),
        "modspec_lw": np.stack([summ_modspec(x) for x in lm_all]),
        "lw1280": S1280,
    }

    print(f"{args.machine}/{d}: pool={len(pool_idx)} anom={len(anom_idx)} "
          f"k={args.k} rep={args.repeats}")
    results: dict = {}
    k, rep = args.k, args.repeats

    score_fns = {}
    for name, F in fams.items():
        Ci = lw_inv(F[:n_tr][src])
        fn = lambda c, X, F=F, Ci=Ci: md(F[X], F[c].mean(0), Ci)
        score_fns[name] = fn
        evaluate(name, fn, pool_idx, anom_idx, k, rep, results)

    # rang-ansambli: mel256 kao osnova + svaka nova familija
    base_fn = score_fns["mel256_lw"]
    for name in ("coup_lw", "tautoc_lw", "modspec_lw", "gwrp99_lw", "pctl_lw",
                 "lw1280"):
        fn2 = score_fns[name]
        evaluate(f"ens_mel+{name}",
                 lambda c, X, f2=fn2: rankdata(base_fn(c, X)) + rankdata(f2(c, X)),
                 pool_idx, anom_idx, k, rep, results)

    # troclani ansambl: mel256 + dvije najbolje nove
    singles = {n: results[n]["auc"] for n in fams if n != "mel256_lw"}
    b1, b2 = sorted(singles, key=singles.get, reverse=True)[:2]
    f1, f2 = score_fns[b1], score_fns[b2]
    print(f"\n  troclani: mel256_lw + {b1} + {b2}")
    evaluate("ens3", lambda c, X: (rankdata(base_fn(c, X)) + rankdata(f1(c, X))
                                   + rankdata(f2(c, X))),
             pool_idx, anom_idx, k, rep, results)

    p = ROOT / "results" / f"research2_{args.machine}_{args.domain}_k{args.k}.json"
    p.write_text(json.dumps(results, indent=2))
    print(f"\nzapisano: {p}")


if __name__ == "__main__":
    main()
