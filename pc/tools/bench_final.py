"""Kandidat za zamjenu autoenkodera, provjeren na SVIM masinama.

Put do ovoga (sve izmjereno, results/bench_*.json):
  autoenkoder                              hmean 0.518
  Mahalanobis nad sazetkom, samo source    0.508  (src 0.855 / tgt 0.363)
  + iskoriscenih 10 target trening klipova 0.633  (src 0.844 / tgt 0.557)

Signal je bio tu cijelo vrijeme — autoenkoder ga nije vadio, a target domen ga
je gusio. Ovdje se dodaju jos dvije stvari:

  BOGATIJI SAZETAK  uz sredinu i std i percentili (10/50/90) i dinamika
                    (std prve razlike kroz vrijeme). Anomalije se cesto vide
                    kao promjena raspona i brzine promjene, ne sredine.

  SPOJ DVA POGLEDA  `raw` sazetak je jak na source, `cmn` (sa oduzetom
                    sredinom klipa) na target. Score-ovi se standardizuju
                    prema TRENING raspodjeli, pa saberu — bez gledanja u test.

Provjera na svih 7 masina je namjerna: recept koji dize samo fan bi bio
namjesten na jedan skup.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_final.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data, eval as ev  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MACHINES = ["fan", "bearingEmu", "gearboxEmu", "sliderEmu", "ToyCar", "ToyCarEmu", "valveEmu"]


def summary(f: np.ndarray, cmn: bool) -> np.ndarray:
    if cmn:
        f = f - f.mean(axis=0, keepdims=True)
    d = np.diff(f, axis=0)
    parts = [f.std(axis=0), np.percentile(f, 10, axis=0), np.percentile(f, 90, axis=0),
             d.std(axis=0)]
    if not cmn:
        parts.insert(0, f.mean(axis=0))
    return np.concatenate(parts)


def maha_fit(X: np.ndarray, reg: float = 1e-3):
    mu = X.mean(axis=0)
    C = np.cov(X.T) + reg * np.eye(X.shape[1])
    return mu, np.linalg.inv(C)


def maha_d(X, mu, Ci):
    d = X - mu
    return np.einsum("ij,jk,ik->i", d, Ci, d)


def view_scores(tr_f, te_f, mean, std, tr_dom, cmn):
    """Score za jedan pogled (raw ili cmn), plus isti score nad trening
    klipovima — sluzi za standardizaciju bez gledanja u test."""
    Str = np.stack([summary((f - mean) / std, cmn) for f in tr_f]).astype(np.float64)
    Ste = np.stack([summary((f - mean) / std, cmn) for f in te_f]).astype(np.float64)
    src, tgt = Str[tr_dom == "source"], Str[tr_dom == "target"]
    mu_s, Ci_s = maha_fit(src)
    mu_t = tgt.mean(axis=0)
    f = lambda X: np.minimum(maha_d(X, mu_s, Ci_s), maha_d(X, mu_t, Ci_s))
    return f(Ste), f(Str)


def run(machine: str) -> dict:
    mdir = ROOT / "data" / "dcase2026_dev" / machine
    cache = ROOT / "results" / "cache"
    train = data.list_clips(mdir, "train")
    test = data.list_clips(mdir, "test")
    tr_f = data.load_features(train, cache / f"{machine}_train.npz", f"{machine} train")
    te_f = data.load_features(test, cache / f"{machine}_test.npz", f"{machine} test")
    mean, std = data.fit_norm(tr_f)

    labels = np.array([c.label for c in test])
    domains = np.array([c.domain for c in test])
    tr_dom = np.array([c.domain for c in train])

    out = {}
    parts_te, parts_tr = [], []
    for cmn in (False, True):
        s_te, s_tr = view_scores(tr_f, te_f, mean, std, tr_dom, cmn)
        out["cmn" if cmn else "raw"] = ev.dcase_metrics(s_te, labels, domains)
        # standardizacija prema trening raspodjeli (test se ne gleda)
        m, sd = s_tr.mean(), s_tr.std() + 1e-12
        parts_te.append((s_te - m) / sd)
        parts_tr.append((s_tr - m) / sd)

    out["spoj"] = ev.dcase_metrics(sum(parts_te), labels, domains)
    return out


def main() -> None:
    print(f"{'masina':12s} {'raw':>8s} {'cmn':>8s} {'spoj':>8s}   (hmean)")
    print("-" * 46)
    allr = {}
    for m in MACHINES:
        try:
            r = run(m)
        except Exception as e:                                  # noqa: BLE001
            print(f"{m:12s} preskocen: {e}")
            continue
        allr[m] = r
        print(f"{m:12s} {r['raw']['hmean']:8.4f} {r['cmn']['hmean']:8.4f} "
              f"{r['spoj']['hmean']:8.4f}")

    if allr:
        print("-" * 46)
        for k in ("raw", "cmn", "spoj"):
            v = np.mean([r[k]["hmean"] for r in allr.values()])
            print(f"{'PROSJEK':12s} {k:>8s} {v:8.4f}" if k == "raw" else
                  f"{'':12s} {k:>8s} {v:8.4f}")
        out = ROOT / "results" / "bench_final.json"
        out.write_text(json.dumps(allr, indent=2))
        print(f"\nzapisano: {out}")


if __name__ == "__main__":
    main()
