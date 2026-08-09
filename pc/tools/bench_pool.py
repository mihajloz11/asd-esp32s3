"""Gdje se gubi kvar: usrednjavanje preko 256 dimenzija.

DOSADASNJI REZULTATI (novi ventilator, posteno mjereno):
    autoenkoder                      0.451
    naucena ugradnja (sve masine)    0.495
    klasifikator brzina              0.530
    sazetak + naucena kovarijansa    0.674   <- najbolje

SUMNJA. Kvar lezaja ili disbalans mijenja dvije-tri frekvencijske trake, a ne
cijeli spektar. Mahalanobis sabira odstupanje preko svih 256 dimenzija, pa se
jak signal u par traka utopi u sumu preko svih ostalih. Isto kao kad prosjek
odjeljenja sakrije jednog djaka sa jedinicom.

RJESENJE bez ikakvog treninga: umjesto zbira, uzeti NAJVECA odstupanja.
Prakticno: dekorelisati sazetak naucenom kovarijansom (kao dosad), pa umjesto
sume po dimenzijama uzeti sredinu najvecih m.

Probaju se:
  sum        zbir svih (dosadasnje, referenca)
  max        samo najveca dimenzija
  topN       sredina najvecih N (N = 3, 8, 16, 32, 64)

Isti protokol: k klipova u kalibraciju, ocjena na preostalim + anomalijama.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_pool.py --machine fan
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def summary(f: np.ndarray) -> np.ndarray:
    return np.concatenate([f.mean(axis=0), f.std(axis=0)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
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

    S_tr = np.stack([summary((f - mean) / std) for f in tr_f])
    S_te = np.stack([summary((f - mean) / std) for f in te_f])
    tr_dom = np.array([c.domain for c in train])
    te_dom = np.array([c.domain for c in test])
    te_lab = np.array([c.label for c in test])

    # bjeljenje naucenom kovarijansom: poslije ovoga su dimenzije nezavisne,
    # pa se odstupanje po dimenziji moze gledati pojedinacno
    C = np.cov(S_tr[tr_dom == "source"].T) + 1e-4 * np.eye(S_tr.shape[1])
    w, V = np.linalg.eigh(np.linalg.pinv(C))
    W = V @ np.diag(np.sqrt(np.maximum(w, 0))) @ V.T

    Z_tr, Z_te = S_tr @ W, S_te @ W

    pools = {"sum": None, "max": 1, "top3": 3, "top8": 8, "top16": 16,
             "top32": 32, "top64": 64}

    print(f"{args.machine}: k={args.k}, dimenzija={Z_tr.shape[1]}\n")
    print(f"{'domen':8s} " + " ".join(f"{p:>7s}" for p in pools))
    print("-" * 68)
    out = {}

    for dom in ("target", "source"):
        pool_n = np.concatenate([Z_tr[tr_dom == dom],
                                 Z_te[(te_dom == dom) & (te_lab == 0)]])
        anom = Z_te[(te_dom == dom) & (te_lab == 1)]
        r = {p: [] for p in pools}
        for rep in range(args.repeats):
            rng = np.random.default_rng(6000 + rep)
            idx = rng.permutation(len(pool_n))
            k = min(args.k, len(pool_n) // 3)
            cal, held = pool_n[idx[:k]], pool_n[idx[k:]]
            X = np.concatenate([held, anom])
            y = np.concatenate([np.zeros(len(held)), np.ones(len(anom))])
            d2 = (X - cal.mean(axis=0)) ** 2
            for p, n in pools.items():
                s = d2.sum(axis=1) if n is None else np.sort(d2, axis=1)[:, -n:].mean(axis=1)
                r[p].append(roc_auc_score(y, s))
        out[dom] = {p: (float(np.mean(v)), float(np.std(v))) for p, v in r.items()}
        print(f"{dom:8s} " + " ".join(f"{np.mean(r[p]):7.3f}" for p in pools))

    p = ROOT / "results" / f"pool_{args.machine}.json"
    p.write_text(json.dumps(out, indent=2))
    best = max(out["target"].items(), key=lambda kv: kv[1][0])
    print(f"\nnajbolje na novom ventilatoru: {best[0]}  "
          f"AUC={best[1][0]:.3f}±{best[1][1]:.03f}")
    print(f"zapisano: {p}")


if __name__ == "__main__":
    main()
