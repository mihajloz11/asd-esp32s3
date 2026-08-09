"""Simulacija stvarne primjene: ploca pored NOVOG ventilatora.

POSTAVKA KOJA NAS ZANIMA (drugacija od DCASE takmicarske):
  Model je unaprijed naucen na korpusu ispravnih ventilatora. Ploca se postavi
  pored ventilatora KOJI MODEL NIJE CUO, snimi njegov normalan rad nekoliko
  minuta (kalibracija), i od tada pazi bas na taj primjerak.

  DCASE mjeri generalizaciju naslijepo — model dobije 10 klipova i mora raditi
  na nepoznatom domenu. Ovdje se mjeri prilagodjavanje na poznato, sto je
  laksi i realniji zadatak za ugradjeni uredjaj.

PROTOKOL (posten, bez curenja):
  Bazen normalnih target klipova = 10 (train) + 50 (test normal) = 60.
  Iz njega se uzme k klipova za KALIBRACIJU. Ocjenjuje se na PREOSTALIM
  normalnim target klipovima + svih 50 target anomalija. Klip koji je usao u
  kalibraciju nikad se ne ocjenjuje. Vise ponavljanja sa razlicitim izborom.

MJERI SE: AUC u zavisnosti od k, tj. koliko sekundi normalnog rada treba
snimiti da bi uredjaj postao upotrebljiv.

Predstave (sve rade sa istim log-mel featurima kao firmware):
  summary   sazetak klipa: sredina, std, percentili, dinamika
  ae_err    profil rekonstrukcione greske postojeceg autoenkodera po dimenziji

Bodovanje:
  maha_diag  dijagonalna kovarijansa (na MCU: 2 vektora, trivijalno)
  maha_full  puna kovarijansa (na MCU: 640x640 = 1.6 MB u PSRAM)
  knn        udaljenost do najblizeg kalibracionog klipa

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_deploy.py --machine fan
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
    d = np.diff(f, axis=0)
    return np.concatenate([f.mean(axis=0), f.std(axis=0),
                           np.percentile(f, 10, axis=0), np.percentile(f, 90, axis=0),
                           d.std(axis=0)])


def score_maha_diag(cal: np.ndarray, X: np.ndarray) -> np.ndarray:
    mu = cal.mean(axis=0)
    var = cal.var(axis=0) + 1e-6
    return np.sum((X - mu) ** 2 / var, axis=1)


def score_maha_full(cal: np.ndarray, X: np.ndarray, shrink: float = 0.3) -> np.ndarray:
    mu = cal.mean(axis=0)
    C = np.cov(cal.T) if len(cal) > 1 else np.eye(cal.shape[1])
    # skupljanje ka dijagonali — sa malo klipova puna kovarijansa je nepouzdana
    C = (1 - shrink) * C + shrink * np.diag(np.diag(C) + 1e-6)
    C += 1e-4 * np.eye(len(C))
    Ci = np.linalg.pinv(C)
    d = X - mu
    return np.einsum("ij,jk,ik->i", d, Ci, d)


def score_knn(cal: np.ndarray, X: np.ndarray, k: int = 1) -> np.ndarray:
    A = cal / (np.linalg.norm(cal, axis=1, keepdims=True) + 1e-12)
    B = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)
    sim = np.sort(B @ A.T, axis=1)
    kk = min(k, sim.shape[1])
    return 1.0 - sim[:, -kk:].mean(axis=1)


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

    S_tr = np.stack([summary((f - mean) / std) for f in tr_f])
    S_te = np.stack([summary((f - mean) / std) for f in te_f])

    tr_dom = np.array([c.domain for c in train])
    te_dom = np.array([c.domain for c in test])
    te_lab = np.array([c.label for c in test])

    # bazen normalnih klipova ciljnog ventilatora
    pool = np.concatenate([S_tr[tr_dom == "target"],
                           S_te[(te_dom == "target") & (te_lab == 0)]])
    anom = S_te[(te_dom == "target") & (te_lab == 1)]
    print(f"{args.machine}: bazen normalnih target klipova = {len(pool)}, "
          f"anomalija = {len(anom)}")

    methods = {"maha_diag": score_maha_diag,
               "maha_full": score_maha_full,
               "knn1": lambda c, x: score_knn(c, x, 1),
               "knn3": lambda c, x: score_knn(c, x, 3)}

    ks = [5, 10, 20, 30, 40]
    print(f"\n{'k klipova':>10s} {'sekundi':>8s}  " +
          "  ".join(f"{m:>10s}" for m in methods))
    print("-" * 62)
    out = {}

    for k in ks:
        if k >= len(pool) - 5:
            continue
        accs = {m: [] for m in methods}
        for r in range(args.repeats):
            rng = np.random.default_rng(1000 + r)
            idx = rng.permutation(len(pool))
            cal, held = pool[idx[:k]], pool[idx[k:]]
            X = np.concatenate([held, anom])
            y = np.concatenate([np.zeros(len(held)), np.ones(len(anom))])
            for m, fn in methods.items():
                accs[m].append(roc_auc_score(y, fn(cal, X)))
        out[k] = {m: (float(np.mean(v)), float(np.std(v))) for m, v in accs.items()}
        print(f"{k:>10d} {k*10:>8d}  " +
              "  ".join(f"{np.mean(accs[m]):.3f}±{np.std(accs[m]):.02f}" for m in methods))

    p = ROOT / "results" / f"deploy_{args.machine}.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"\nzapisano: {p}")


if __name__ == "__main__":
    main()
