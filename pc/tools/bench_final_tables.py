"""Finalne tabele za rad: AUC + pAUC, vise seedova, sve masine, staro vs novo.

Zasto postoji: plan-master-rada.md trazi "AUC (source/target posebno), pAUC pri
niskom FPR" kao metrike, a novi PSD model do sada ima samo AUC. Stari AE
rezultati imaju pAUC (results/bench_*.json), pa bez ovoga tabele nisu uporedive.

pAUC se racuna kao standardizovani parcijalni AUC pri FPR <= p (DCASE koristi
p = 0.1), sto je mjera koliko se anomalija hvata u rezimu malo laznih alarma —
bas ono sto je za uredjaj bitno.

Poredi tri varijante, sve na TARGET domenu, isti protokol lokalne kalibracije:
  mel1280     sazetak log-mela 1280 + kovarijansa shrink 0.1 (stara referenca)
  mel256_lw   mel sazetak 256 + Ledoit-Wolf + medijana centra
  psd_shape   finalni model: Welch 8192, 96 log traka, LW, centar

PAZNJA NA IMENA: nijedna od ove tri varijante NE pokrece autoenkoder. Ranije se
prva zvala "ae_mel", sto je bilo pogresno — to je Mahalanobis nad log-mel
sazetkom, ne AE. Rezultati autoenkodera su u results/results.csv.

PAZNJA NA "SEEDOVE": --seeds NE pokrece vise treninga. Nema sta da se trenira —
model je statisticki. Seed mijenja samo IZBOR KALIBRACIONIH KLIPOVA, pa
prijavljena std opisuje osjetljivost na to koji klipovi udju u kalibraciju,
NE generalizaciju na vise razlicitih ventilatora. Za ovo drugo treba vise
fizickih primjeraka, cega u DCASE skupu nema.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_final_tables.py
    ../.venv/Scripts/python.exe tools/bench_final_tables.py --machines fan --seeds 5
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
N_MELS = 128
MAX_FPR = 0.1
MACHINES = ("fan", "ToyCar", "ToyCarEmu", "bearingEmu", "gearboxEmu",
            "sliderEmu", "valveEmu")


def pauc(y, s, max_fpr=MAX_FPR):
    """Standardizovani parcijalni AUC (McClish), isto sto sklearn radi uz
    max_fpr — 0.5 znaci slucajno, 1.0 savrseno, u rezimu FPR <= max_fpr."""
    return roc_auc_score(y, s, max_fpr=max_fpr)


def lw_precision(X):
    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8
    return mean, std, LedoitWolf().fit((X - mean) / std).precision_


def inv_cov_shrink(X, shrink=0.1):
    C = np.cov(X.T)
    C = (1 - shrink) * C + shrink * np.diag(np.diag(C))
    return np.linalg.pinv(C + 1e-6 * np.eye(len(C)))


def maha(X, c, P):
    d = X - c
    return np.einsum("ij,jk,ik->i", d, P, d)


def mel_summary_256(f):
    lm = np.concatenate([f[:, :N_MELS], f[-1, N_MELS:].reshape(4, N_MELS)], axis=0)
    return np.concatenate([lm.mean(axis=0), lm.std(axis=0)]).astype(np.float64)


def build(machine):
    cache = ROOT / "results" / "cache"
    mdir = ROOT / "data" / "dcase2026_dev" / machine
    train = data.list_clips(mdir, "train")
    test = data.list_clips(mdir, "test")
    tr_f = data.load_features(train, cache / f"{machine}_train.npz", "train")
    te_f = data.load_features(test, cache / f"{machine}_test.npz", "test")
    mean, std = data.fit_norm(tr_f)

    feats = {}
    S1280 = np.stack([np.concatenate([((f - mean) / std).mean(0),
                                      ((f - mean) / std).std(0)])
                      for f in tr_f + te_f]).astype(np.float64)
    feats["mel1280"] = S1280
    feats["mel256_lw"] = np.stack([mel_summary_256(f) for f in tr_f + te_f])
    pz = cache / f"{machine}_periodicity.npz"
    if pz.exists():
        feats["psd_shape"] = np.load(pz)["psd_shape"]

    meta = dict(
        n_tr=len(tr_f),
        tr_dom=np.array([c.domain for c in train]),
        te_dom=np.array([c.domain for c in test]),
        te_lab=np.array([c.label for c in test]),
    )
    return feats, meta


def evaluate(F, meta, variant, k, seeds, reps):
    n_tr = meta["n_tr"]
    src = np.where(meta["tr_dom"] == "source")[0]
    pool = np.concatenate([np.where(meta["tr_dom"] == "target")[0],
                           n_tr + np.where((meta["te_dom"] == "target") &
                                           (meta["te_lab"] == 0))[0]])
    anom = n_tr + np.where((meta["te_dom"] == "target") & (meta["te_lab"] == 1))[0]

    if variant == "mel1280":
        P = inv_cov_shrink(F[src], 0.1)
        Z = F
        use_median = False
    else:
        m, s, P = lw_precision(F[src])
        Z = (F - m) / s
        use_median = (variant == "mel256_lw")

    aucs, paucs = [], []
    for seed in range(seeds):
        for rep in range(reps):
            rng = np.random.default_rng(1000 * seed + 3000 + rep)
            idx = rng.permutation(len(pool))
            cal, held = pool[idx[:k]], pool[idx[k:]]
            c = np.median(Z[cal], axis=0) if use_median else Z[cal].mean(axis=0)
            X = np.concatenate([held, anom])
            y = np.concatenate([np.zeros(len(held)), np.ones(len(anom))])
            sc = maha(Z[X], c, P)
            aucs.append(roc_auc_score(y, sc))
            paucs.append(pauc(y, sc))
    return (float(np.mean(aucs)), float(np.std(aucs)),
            float(np.mean(paucs)), float(np.std(paucs)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machines", nargs="*", default=list(MACHINES))
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--seeds", type=int, default=5,
                    help="broj GRUPA kalibracionih podjela, NE broj treninga")
    ap.add_argument("--reps", type=int, default=20)
    args = ap.parse_args()

    out = {}
    hdr = f"{'masina':<12s} {'varijanta':<11s} {'AUC':>14s} {'pAUC(10%)':>14s}"
    print(hdr)
    print("-" * len(hdr))
    for m in args.machines:
        try:
            feats, meta = build(m)
        except FileNotFoundError as e:
            print(f"{m:<12s} preskoceno ({e})")
            continue
        out[m] = {}
        for variant, F in feats.items():
            a, asd, p, psd = evaluate(F, meta, variant, args.k, args.seeds, args.reps)
            out[m][variant] = {"auc": a, "auc_std": asd, "pauc": p, "pauc_std": psd,
                               "k": args.k, "seeds": args.seeds, "reps": args.reps}
            print(f"{m:<12s} {variant:<11s} {a:.3f}±{asd:.03f}   {p:.3f}±{psd:.03f}")
        print()

    path = ROOT / "results" / f"final_tables_k{args.k}.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"zapisano: {path}")


if __name__ == "__main__":
    main()
