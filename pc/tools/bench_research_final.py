"""Finalna tabela istrazivacke runde: stari vs novi recept na svih 7 masina.

Poredi na TARGET domenu, identicni seedovi (3000+rep), k=20, 20 ponavljanja:

  base      sazetak 1280 + kovarijansa shrink 0.1 + SREDINA centra (dosadasnje)
  novo256   sazetak mel256 + Ledoit-Wolf + MEDIJANA centra
  novoGW    gwrp995both (384) + Ledoit-Wolf + MEDIJANA centra

Plus uparena statistika (dobitak, broj pobjeda po seedu, t-test).

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_research_final.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.covariance import LedoitWolf
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
N_MELS = 128
MACHINES = ("fan", "ToyCar", "ToyCarEmu", "bearingEmu", "gearboxEmu",
            "sliderEmu", "valveEmu")


def gwrp(sorted_desc, r):
    w = r ** np.arange(len(sorted_desc), dtype=np.float64)
    return (sorted_desc * w[:, None]).sum(0) / w.sum()


def lw_inv(X):
    lw = LedoitWolf().fit(X)
    return np.linalg.pinv(lw.covariance_ + 1e-6 * np.eye(X.shape[1]))


def inv_cov(X, shrink):
    C = np.cov(X.T)
    C = (1 - shrink) * C + shrink * np.diag(np.diag(C))
    return np.linalg.pinv(C + 1e-6 * np.eye(len(C)))


def md(X, mu, Ci):
    d = X - mu
    return np.einsum("ij,jk,ik->i", d, Ci, d)


def run(machine: str, repeats: int = 20, k: int = 20) -> dict:
    mdir = ROOT / "data" / "dcase2026_dev" / machine
    cache = ROOT / "results" / "cache"
    train = data.list_clips(mdir, "train")
    test = data.list_clips(mdir, "test")
    tr_f = data.load_features(train, cache / f"{machine}_train.npz", "train")
    te_f = data.load_features(test, cache / f"{machine}_test.npz", "test")
    mean, std = data.fit_norm(tr_f)

    tr_dom = np.array([c.domain for c in train])
    te_dom = np.array([c.domain for c in test])
    te_lab = np.array([c.label for c in test])
    src = tr_dom == "source"
    n_tr = len(tr_f)
    m128, s128 = mean[:N_MELS], std[:N_MELS]
    lm_all = [((f[:, :N_MELS]) - m128) / s128 for f in tr_f + te_f]

    S1280 = np.stack([np.concatenate([((f - mean) / std).mean(0),
                                      ((f - mean) / std).std(0)])
                      for f in tr_f + te_f])
    S256 = np.stack([np.concatenate([x.mean(0), x.std(0)]) for x in lm_all])
    SGW = np.stack([np.concatenate([
        gwrp(np.sort(x, axis=0)[::-1], 0.995),
        gwrp(np.sort(x, axis=0), 0.995), x.std(0)]) for x in lm_all])

    variants = {
        "base": (S1280, inv_cov(S1280[:n_tr][src], 0.1), "mean"),
        "novo256": (S256, lw_inv(S256[:n_tr][src]), "median"),
        "novoGW": (SGW, lw_inv(SGW[:n_tr][src]), "median"),
    }

    pool = np.concatenate([np.where(tr_dom == "target")[0],
                           n_tr + np.where((te_dom == "target") & (te_lab == 0))[0]])
    anom = n_tr + np.where((te_dom == "target") & (te_lab == 1))[0]

    out = {}
    for name, (F, Ci, how) in variants.items():
        aucs = []
        for rep in range(repeats):
            rng = np.random.default_rng(3000 + rep)
            idx = rng.permutation(len(pool))
            cal_i, held = pool[idx[:k]], pool[idx[k:]]
            X = np.concatenate([held, anom])
            y = np.concatenate([np.zeros(len(held)), np.ones(len(anom))])
            mu = (np.median(F[cal_i], axis=0) if how == "median"
                  else F[cal_i].mean(0))
            aucs.append(roc_auc_score(y, md(F[X], mu, Ci)))
        out[name] = aucs
    return out


def main() -> None:
    allres = {}
    print(f"{'masina':<12s} {'base':>13s} {'novo256':>13s} {'novoGW':>13s} "
          f"{'dobitak':>8s} {'pobjede':>8s} {'p':>8s}")
    print("-" * 80)
    for m in MACHINES:
        try:
            r = run(m)
        except FileNotFoundError as e:
            print(f"{m:<12s} preskoceno ({e})")
            continue
        allres[m] = {n: {"auc": float(np.mean(a)), "std": float(np.std(a)),
                         "per_rep": a} for n, a in r.items()}
        best_new = max(("novo256", "novoGW"), key=lambda n: np.mean(r[n]))
        diff = np.array(r[best_new]) - np.array(r["base"])
        _, p = stats.ttest_rel(r[best_new], r["base"])
        print(f"{m:<12s} "
              f"{np.mean(r['base']):.3f}±{np.std(r['base']):.03f} "
              f"{np.mean(r['novo256']):.3f}±{np.std(r['novo256']):.03f} "
              f"{np.mean(r['novoGW']):.3f}±{np.std(r['novoGW']):.03f} "
              f"{diff.mean():+.3f} {int((diff > 0).sum()):>5d}/20 {p:8.4f}")

    p = ROOT / "results" / "research_final_all.json"
    p.write_text(json.dumps(allres, indent=2))
    print(f"\nzapisano: {p}")


if __name__ == "__main__":
    main()
