"""Kalibracija PO RADNOM REZIMU umjesto jedne raspodjele za sve.

PROBLEM. Ventilator radi na tri brzine. Ako se normalno stanje modeluje kao
jedna Gausova raspodjela, ona pokriva sva tri oblaka i ispada siroka — pa
anomalija lako upadne unutra. Izmjereno: kalibracija na 400 s ciljnog
ventilatora daje AUC svega 0.60, i kriva se ravna, dakle duzina slusanja nije
usko grlo.

IDEJA. Drzati odvojen model po rezimu i klip porediti sa NJEGOVIM rezimom.

Tri varijante:
  pooled   jedna raspodjela za sve (dosadasnje stanje, referenca)
  oracle   po pravom `spd` atributu — gornja granica, rezim se zna
  kmeans   rezimi se otkrivaju grupisanjem kalibracionih klipova, bez oznaka
           — ovo je varijanta koja se stvarno moze izvesti na ploci

Protokol je isti kao u bench_deploy.py: k klipova ide u kalibraciju, ocjenjuje
se na preostalim normalnim + svim anomalijama, 20 ponavljanja.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_modes.py --machine fan --domain target
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SPD = re.compile(r"spd_(\d+)")


def summary(f: np.ndarray) -> np.ndarray:
    return np.concatenate([f.mean(axis=0), f.std(axis=0)])


def diag_score(cal: np.ndarray, X: np.ndarray) -> np.ndarray:
    mu = cal.mean(axis=0)
    var = cal.var(axis=0) + 1e-3
    return np.sum((X - mu) ** 2 / var, axis=1)


def pooled(cal, X, *_):
    return diag_score(cal, X)


def per_mode(cal, X, cal_mode, n_modes):
    """Svaki klip se poredi sa SVAKIM rezimom, uzima se najmanja udaljenost —
    tako se rezim ne mora znati pri radu."""
    d = []
    for m in range(n_modes):
        c = cal[cal_mode == m]
        if len(c) < 2:
            continue
        d.append(diag_score(c, X))
    return np.min(np.stack(d), axis=0) if d else diag_score(cal, X)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
    ap.add_argument("--domain", default="target", choices=["source", "target"])
    ap.add_argument("--repeats", type=int, default=20)
    args = ap.parse_args()

    mdir = ROOT / "data" / "dcase2026_dev" / args.machine
    cache = ROOT / "results" / "cache"
    train = data.list_clips(mdir, "train")
    test = data.list_clips(mdir, "test")
    tr_f = data.load_features(train, cache / f"{args.machine}_train.npz", "train")
    te_f = data.load_features(test, cache / f"{args.machine}_test.npz", "test")
    mean, std = data.fit_norm(tr_f)

    S_tr = np.stack([summary((f - mean) / std) for f in tr_f])
    S_te = np.stack([summary((f - mean) / std) for f in te_f])
    spd = lambda c: int(SPD.search(c.path.name).group(1)) - 1

    tr_ok = [i for i, c in enumerate(train) if c.domain == args.domain]
    te_n = [i for i, c in enumerate(test) if c.domain == args.domain and c.label == 0]
    te_a = [i for i, c in enumerate(test) if c.domain == args.domain and c.label == 1]

    pool = np.concatenate([S_tr[tr_ok], S_te[te_n]])
    pool_m = np.array([spd(train[i]) for i in tr_ok] + [spd(test[i]) for i in te_n])
    anom = S_te[te_a]
    n_modes = int(pool_m.max() + 1)
    print(f"{args.machine} / {args.domain}: bazen normalnih = {len(pool)}, "
          f"anomalija = {len(anom)}, rezima = {n_modes}")

    ks = [k for k in (5, 10, 20, 30, 40) if k < len(pool) - 5]
    print(f"\n{'k':>4s} {'sek':>6s}  {'pooled':>12s} {'oracle':>12s} {'kmeans':>12s}")
    print("-" * 52)
    out = {}

    for k in ks:
        r = {"pooled": [], "oracle": [], "kmeans": []}
        for rep in range(args.repeats):
            rng = np.random.default_rng(2000 + rep)
            idx = rng.permutation(len(pool))
            cal, cal_m = pool[idx[:k]], pool_m[idx[:k]]
            held = pool[idx[k:]]
            X = np.concatenate([held, anom])
            y = np.concatenate([np.zeros(len(held)), np.ones(len(anom))])

            r["pooled"].append(roc_auc_score(y, pooled(cal, X)))
            r["oracle"].append(roc_auc_score(y, per_mode(cal, X, cal_m, n_modes)))

            km = KMeans(n_clusters=min(n_modes, max(2, k // 3)), n_init=10,
                        random_state=0).fit(cal)
            r["kmeans"].append(roc_auc_score(y, per_mode(cal, X, km.labels_,
                                                         km.n_clusters)))

        out[k] = {m: (float(np.mean(v)), float(np.std(v))) for m, v in r.items()}
        print(f"{k:>4d} {k*10:>6d}  " + " ".join(
            f"{np.mean(r[m]):.3f}±{np.std(r[m]):.02f}" for m in ("pooled", "oracle", "kmeans")))

    p = ROOT / "results" / f"modes_{args.machine}_{args.domain}.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"\nzapisano: {p}")


if __name__ == "__main__":
    main()
