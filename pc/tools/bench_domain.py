"""Napad na domain shift: metode koje ne zavise od toga u kom domenu je klip.

Nalaz iz bench_backends.py: Mahalanobis nad sazetkom klipa daje AUC 0.81 na
source domenu, ali 0.46 na target domenu — signal postoji, ali ga domenska
razlika unistava. Trening ima 990 source i samo 10 target klipova, i domen
NIJE poznat pri radu, pa metoda mora biti slijepa na njega.

Tri poluge koje se probaju:

  CMN   od svakog klipa se oduzme NJEGOVA sredina po dimenziji. Time nestaju
        stalni pomak nivoa i nagib spektra — a to su glavne razlike izmedju
        uslova snimanja. Ostaje samo kako se zvuk MIJENJA kroz vrijeme.

  MIX   umjesto jednog modela normalnog stanja, dva: jedan sa source, jedan sa
        target trening klipova. Score = udaljenost do BLIZEG. Deset target
        klipova je premalo za kovarijansu, pa se dijeli source kovarijansa.

  kNN   udaljenost do najblizeg trening klipa bilo kog domena. Sa svega 10
        target primjera ovo je prirodniji izbor od parametarske raspodjele.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_domain.py --machine fan
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data, eval as ev  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def summary(f: np.ndarray, cmn: bool) -> np.ndarray:
    """Sazetak klipa: sredina + std po dimenziji. Uz CMN sredina otpada
    (nula po definiciji), pa ostaje samo dinamika."""
    if cmn:
        f = f - f.mean(axis=0, keepdims=True)
        return f.std(axis=0)
    return np.concatenate([f.mean(axis=0), f.std(axis=0)])


def maha_fit(X: np.ndarray, reg: float = 1e-3):
    mu = X.mean(axis=0)
    C = np.cov(X.T) + reg * np.eye(X.shape[1])
    return mu, np.linalg.inv(C)


def maha_d(X: np.ndarray, mu: np.ndarray, Ci: np.ndarray) -> np.ndarray:
    d = X - mu
    return np.einsum("ij,jk,ik->i", d, Ci, d)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
    args = ap.parse_args()

    mdir = ROOT / "data" / "dcase2026_dev" / args.machine
    cache = ROOT / "results" / "cache"
    train = data.list_clips(mdir, "train")
    test = data.list_clips(mdir, "test")
    tr_f = data.load_features(train, cache / f"{args.machine}_train.npz", "train")
    te_f = data.load_features(test, cache / f"{args.machine}_test.npz", "test")
    mean, std = data.fit_norm(tr_f)

    labels = np.array([c.label for c in test])
    domains = np.array([c.domain for c in test])
    tr_dom = np.array([c.domain for c in train])
    print(f"{args.machine}: train source={np.sum(tr_dom == 'source')} "
          f"target={np.sum(tr_dom == 'target')}\n--- REZULTATI ---")

    res = {}

    def report(name: str, sc: np.ndarray) -> None:
        m = ev.dcase_metrics(sc, labels, domains)
        res[name] = m
        print(f"  {name:16s} auc_src={m['auc_source']:.4f}  auc_tgt={m['auc_target']:.4f}"
              f"  pauc={m['pauc']:.4f}  hmean={m['hmean']:.4f}")

    for cmn in (False, True):
        tag = "cmn" if cmn else "raw"
        Str = np.stack([summary((f - mean) / std, cmn) for f in tr_f]).astype(np.float64)
        Ste = np.stack([summary((f - mean) / std, cmn) for f in te_f]).astype(np.float64)

        src, tgt = Str[tr_dom == "source"], Str[tr_dom == "target"]

        # jedan model (samo source statistike)
        mu_s, Ci_s = maha_fit(src)
        report(f"{tag}_maha", maha_d(Ste, mu_s, Ci_s))

        # dva modela, dijeljena kovarijansa, score = blizi
        mu_t = tgt.mean(axis=0)
        ds = maha_d(Ste, mu_s, Ci_s)
        dt = maha_d(Ste, mu_t, Ci_s)
        report(f"{tag}_maha_mix", np.minimum(ds, dt))

        # kNN preko svih trening klipova, oba domena
        A = Str / np.linalg.norm(Str, axis=1, keepdims=True)
        B = Ste / np.linalg.norm(Ste, axis=1, keepdims=True)
        sim = np.sort(B @ A.T, axis=1)
        for k in (1, 3, 10):
            report(f"{tag}_knn{k}", 1.0 - sim[:, -k:].mean(axis=1))

    out = ROOT / "results" / f"bench_domain_{args.machine}.json"
    out.write_text(json.dumps(res, indent=2))
    best = max(res.items(), key=lambda kv: kv[1]["hmean"])
    print(f"\nnajbolji: {best[0]}  hmean={best[1]['hmean']:.4f}  "
          f"(src {best[1]['auc_source']:.3f} / tgt {best[1]['auc_target']:.3f})")
    print(f"zapisano: {out}")


if __name__ == "__main__":
    main()
