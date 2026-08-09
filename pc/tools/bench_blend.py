"""Mjesanje naucenog i izmjerenog oblika + POSTENO mjerenje na source domenu.

DVIJE ISPRAVKE U ODNOSU NA bench_adapt.py:

1. CURENJE. Tamo je kovarijansa ucena na 990 source trening klipova, a onda su
   ti isti klipovi koristeni kao "normalni" pri ocjenjivanju — pa je source
   ispao 0.96. Ovdje se korpus za ucenje kovarijanse i skup za ocjenu STROGO
   razdvajaju.

2. MJESANJE. Naucena kovarijansa opisuje ventilatore sa kojih je snimljena.
   Ciljni primjerak varira drugacije. Zato:
       C = alfa * C_naucena + (1 - alfa) * C_izmjerena_na_licu_mjesta
   Za alfa=1 to je cisto naucena (dosadasnje), za alfa=0 cisto izmjerena.
   Trazi se sredina koja koristi oboje: pouzdanu strukturu iz korpusa i
   specificnost ovog primjerka.

Dodaje se i CMN varijanta (od klipa se oduzme njegova sredina) jer je ranije
mjerenje pokazalo da CMN pomaze bas na target domenu.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_blend.py --machine fan
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
ALPHAS = [1.0, 0.9, 0.7, 0.5, 0.3, 0.0]


def summary(f: np.ndarray, cmn: bool) -> np.ndarray:
    if cmn:
        f = f - f.mean(axis=0, keepdims=True)
        return f.std(axis=0)
    return np.concatenate([f.mean(axis=0), f.std(axis=0)])


def md(X, mu, Ci):
    d = X - mu
    return np.einsum("ij,jk,ik->i", d, Ci, d)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--k", type=int, default=20, help="kalibracionih klipova")
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
    src_idx = np.where(tr_dom == "source")[0]

    out = {}
    for cmn in (False, True):
        tag = "cmn" if cmn else "raw"
        S_tr = np.stack([summary((f - mean) / std, cmn) for f in tr_f])
        S_te = np.stack([summary((f - mean) / std, cmn) for f in te_f])

        # korpus za ucenje kovarijanse: 800 source klipova, ostalo se cuva
        rng0 = np.random.default_rng(7)
        perm = rng0.permutation(src_idx)
        corpus, src_rest = perm[:800], perm[800:]
        C_learn = np.cov(S_tr[corpus].T)

        for dom in ("target", "source"):
            if dom == "target":
                pool = np.concatenate([S_tr[tr_dom == "target"],
                                       S_te[(te_dom == "target") & (te_lab == 0)]])
            else:
                # POSTENO: normalni koje kovarijansa NIJE vidjela
                pool = np.concatenate([S_tr[src_rest],
                                       S_te[(te_dom == "source") & (te_lab == 0)]])
            anom = S_te[(te_dom == dom) & (te_lab == 1)]

            res = {}
            for a in ALPHAS:
                aucs = []
                for rep in range(args.repeats):
                    rng = np.random.default_rng(4000 + rep)
                    idx = rng.permutation(len(pool))
                    k = min(args.k, len(pool) // 3)
                    cal, held = pool[idx[:k]], pool[idx[k:]]
                    X = np.concatenate([held, anom])
                    y = np.concatenate([np.zeros(len(held)), np.ones(len(anom))])

                    C_cal = np.cov(cal.T) if k > 1 else np.eye(len(C_learn))
                    C = a * C_learn + (1 - a) * C_cal
                    C = C + 1e-4 * np.eye(len(C))
                    aucs.append(roc_auc_score(y, md(X, cal.mean(axis=0),
                                                    np.linalg.pinv(C))))
                res[a] = (float(np.mean(aucs)), float(np.std(aucs)))

            out[f"{tag}_{dom}"] = res
            best = max(res.items(), key=lambda kv: kv[1][0])
            print(f"{tag:4s} / {dom:7s}  k={args.k}  bazen={len(pool)}  anom={len(anom)}")
            print("   " + "  ".join(f"a={a}:{res[a][0]:.3f}" for a in ALPHAS))
            print(f"   najbolje: alfa={best[0]}  AUC={best[1][0]:.3f}±{best[1][1]:.03f}\n")

    p = ROOT / "results" / f"blend_{args.machine}.json"
    p.write_text(json.dumps({k: {str(a): v for a, v in r.items()}
                             for k, r in out.items()}, indent=2))
    print(f"zapisano: {p}")


if __name__ == "__main__":
    main()
