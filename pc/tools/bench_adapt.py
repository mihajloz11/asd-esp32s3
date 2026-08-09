"""Naucena kovarijansa + kalibracija centra na ploci — kandidat za rjesenje.

ODAKLE OVO. Izmjereno je da puna kovarijansa daje AUC 0.855 na source domenu,
a dijagonalna svega 0.543. Signal je dakle u VEZAMA izmedju dimenzija, ne u
njihovom pojedinacnom raspršenju. Ali punu kovarijansu (256x256) nije moguce
procijeniti iz 10-40 klipova koje uredjaj snimi pri postavljanju.

RJESENJE. Razdvojiti sta se uci unaprijed od onoga sto se mjeri na licu mjesta:

  UNAPRIJED (na racunaru, veliki korpus ispravnih ventilatora)
      kovarijansa — kako normalan ventilator uopste varira

  NA PLOCI (k klipova novog primjerka, nekoliko minuta)
      samo centar — gdje je sredina bas ovog primjerka

Na uredjaju ostaje: 256 brojeva centra (mjeri se) + gotova matrica iz firmvera.
Bez treninga, bez backpropa, samo sabiranje i mnozenje.

Varijante koje se porede:
  tgt_diag    sve sa ciljne masine, dijagonalna kovarijansa
  tgt_full    sve sa ciljne masine, puna kovarijansa uz skupljanje
  adapt       NAUCENA kovarijansa (source) + centar sa ciljne masine
  adapt_mode  isto, ali odvojen centar po radnom rezimu (k-means)

Protokol: k klipova u kalibraciju, ocjena na preostalim normalnim + svim
anomalijama, 20 ponavljanja. Klip iz kalibracije se nikad ne ocjenjuje.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_adapt.py --machine fan
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def summary(f: np.ndarray) -> np.ndarray:
    """Jednostavan sazetak: sredina + std po dimenziji. Bogatiji sazetak je
    izmjeren i bio je LOSIJI (0.578 vs 0.633), pa se ne koristi."""
    return np.concatenate([f.mean(axis=0), f.std(axis=0)])


def inv_cov(X: np.ndarray, shrink: float) -> np.ndarray:
    C = np.cov(X.T)
    C = (1 - shrink) * C + shrink * np.diag(np.diag(C))
    return np.linalg.pinv(C + 1e-6 * np.eye(len(C)))


def md(X: np.ndarray, mu: np.ndarray, Ci: np.ndarray) -> np.ndarray:
    d = X - mu
    return np.einsum("ij,jk,ik->i", d, Ci, d)


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
    tr_dom = np.array([c.domain for c in train])
    te_dom = np.array([c.domain for c in test])
    te_lab = np.array([c.label for c in test])

    # kovarijansa naucena unaprijed sa velikog korpusa (source trening)
    Ci_learned = inv_cov(S_tr[tr_dom == "source"], shrink=0.1)

    d = args.domain
    pool = np.concatenate([S_tr[tr_dom == d], S_te[(te_dom == d) & (te_lab == 0)]])
    anom = S_te[(te_dom == d) & (te_lab == 1)]
    print(f"{args.machine} / {d}: normalnih u bazenu = {len(pool)}, anomalija = {len(anom)}")
    print(f"dimenzija sazetka = {pool.shape[1]}, kovarijansa naucena sa "
          f"{np.sum(tr_dom == 'source')} klipova\n")

    print(f"{'k':>4s} {'sek':>6s}  {'tgt_diag':>11s} {'tgt_full':>11s} "
          f"{'adapt':>11s} {'adapt_mode':>11s}")
    print("-" * 62)
    out = {}

    for k in (5, 10, 20, 30, 40):
        if k >= len(pool) - 5:
            continue
        r = {m: [] for m in ("tgt_diag", "tgt_full", "adapt", "adapt_mode")}
        for rep in range(args.repeats):
            rng = np.random.default_rng(3000 + rep)
            idx = rng.permutation(len(pool))
            cal, held = pool[idx[:k]], pool[idx[k:]]
            X = np.concatenate([held, anom])
            y = np.concatenate([np.zeros(len(held)), np.ones(len(anom))])
            mu = cal.mean(axis=0)

            r["tgt_diag"].append(roc_auc_score(y, np.sum(
                (X - mu) ** 2 / (cal.var(axis=0) + 1e-3), axis=1)))
            r["tgt_full"].append(roc_auc_score(y, md(X, mu, inv_cov(cal, 0.5))))
            r["adapt"].append(roc_auc_score(y, md(X, mu, Ci_learned)))

            n_cl = min(3, max(2, k // 4))
            km = KMeans(n_clusters=n_cl, n_init=10, random_state=0).fit(cal)
            ds = [md(X, cal[km.labels_ == c].mean(axis=0), Ci_learned)
                  for c in range(n_cl) if np.sum(km.labels_ == c) >= 2]
            r["adapt_mode"].append(roc_auc_score(y, np.min(np.stack(ds), axis=0)))

        out[k] = {m: (float(np.mean(v)), float(np.std(v))) for m, v in r.items()}
        print(f"{k:>4d} {k*10:>6d}  " + " ".join(
            f"{np.mean(r[m]):.3f}±{np.std(r[m]):.02f}" for m in r))

    p = ROOT / "results" / f"adapt_{args.machine}_{args.domain}.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"\nzapisano: {p}")


if __name__ == "__main__":
    main()
