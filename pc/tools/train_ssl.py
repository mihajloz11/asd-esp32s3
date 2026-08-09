"""Samonadzirani klasifikator kao zamjena za autoenkoder (pokusaj E7).

MOTIVACIJA. Autoenkoder na fan masini daje AUC 0.54-0.60 — to je pogadjanje i
nije upotrebljivo. Uzrok je poznat iz literature: rekonstrukciona greska mjeri
koliko ulaz lici na trening raspodjelu UOPSTE, a ne da li masina radi ispravno.
Normalni i neispravni ventilator zvuce vrlo slicno u log-mel domenu, pa im je
greska skoro ista (izmjereno: 2.53 vs 2.57, razlika 1.6%).

IDEJA. Umjesto da ucimo model da rekonstruise zvuk, ucimo ga da rijesi ZADATAK
koji zahtijeva razumijevanje zvuka masine: da pogodi radni rezim (atribut `spd`,
brzina ventilatora, 3 klase). Model tako mora nauciti sta razlikuje rezime, a ne
samo prosjecni spektar. Kad masina pocne da otkazuje, zvuk vise ne pripada cisto
nijednom naucenom rezimu — klasifikator postane nesiguran, ili se ugradjeni
vektor udalji od centra svoje klase. To je mjera anomalije.

Ovo je pristup koji na DCASE takmicenjima redovno pobjedjuje autoenkodere.

Bodovanje (racunaju se sva cetiri, pa se poredi):
  msp      1 - max softmax
  ent      entropija softmaxa
  cos      kosinusna udaljenost ugradjenog vektora od centra najblize klase
  maha     Mahalanobis u prostoru ugradnje, po klasama

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/train_ssl.py --machine fan
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data, eval as ev  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SPD_RE = re.compile(r"spd_(\d+)")


def attr_of(path: Path) -> int:
    """Radni rezim iz imena fajla (spd_1/2/3 -> 0/1/2)."""
    m = SPD_RE.search(path.name)
    if not m:
        raise ValueError(f"nema spd atributa: {path.name}")
    return int(m.group(1)) - 1


def build_classifier(input_dim: int, n_cls: int, emb: int = 64, width: int = 128):
    import tensorflow as tf
    L = tf.keras.layers
    inp = L.Input(shape=(input_dim,))
    x = L.Dense(width, use_bias=False)(inp)
    x = L.BatchNormalization()(x)
    x = L.Activation("relu")(x)
    x = L.Dense(width, use_bias=False)(x)
    x = L.BatchNormalization()(x)
    x = L.Activation("relu")(x)
    e = L.Dense(emb, name="emb")(x)
    en = L.Lambda(lambda z: tf.math.l2_normalize(z, axis=1), name="emb_n")(e)
    out = L.Dense(n_cls, activation="softmax", name="cls")(en)
    m = tf.keras.Model(inp, out)
    m.embedder = tf.keras.Model(inp, en)
    return m


def clip_aggregate(vals: np.ndarray) -> float:
    """Klip score = sredina po vektorima (isto kao kod AE, da poredjenje bude posteno)."""
    return float(np.mean(vals))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
    ap.add_argument("--stride", type=int, default=3, help="uzmi svaki n-ti vektor za trening")
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    import tensorflow as tf
    tf.keras.utils.set_random_seed(args.seed)

    mdir = ROOT / "data" / "dcase2026_dev" / args.machine
    cache = ROOT / "results" / "cache"

    train = data.list_clips(mdir, "train")
    test = data.list_clips(mdir, "test")
    print(f"{args.machine}: {len(train)} train, {len(test)} test")

    tr_f = data.load_features(train, cache / f"{args.machine}_train.npz", "train featuri")
    te_f = data.load_features(test, cache / f"{args.machine}_test.npz", "test featuri")

    mean, std = data.fit_norm(tr_f)

    # ---- trening skup: vektori + oznaka radnog rezima ----
    xs, ys = [], []
    for f, c in zip(tr_f, train):
        v = f[:: args.stride]
        xs.append((v - mean) / std)
        ys.append(np.full(len(v), attr_of(c.path), dtype=np.int32))
    X = np.concatenate(xs).astype(np.float32)
    Y = np.concatenate(ys)
    n_cls = int(Y.max() + 1)
    print(f"trening vektora: {X.shape}, klasa: {n_cls}, po klasi: {np.bincount(Y)}")

    model = build_classifier(X.shape[1], n_cls)
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                  loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    hist = model.fit(X, Y, batch_size=512, epochs=args.epochs, validation_split=0.1,
                     verbose=2)
    acc = hist.history["val_accuracy"][-1]
    print(f"\ntacnost prepoznavanja rezima (validacija): {acc:.4f}")

    # ---- statistike ugradnje po klasama (sa trening skupa) ----
    E = model.embedder.predict(X, batch_size=2048, verbose=0)
    cent, cov_inv = [], []
    for k in range(n_cls):
        Ek = E[Y == k]
        mu = Ek.mean(axis=0)
        cent.append(mu)
        C = np.cov(Ek.T) + 1e-4 * np.eye(Ek.shape[1])
        cov_inv.append(np.linalg.inv(C))
    cent = np.stack(cent)

    # ---- bodovanje test klipova ----
    labels = np.array([c.label for c in test])
    domains = np.array([c.domain for c in test])
    S = {k: np.zeros(len(test)) for k in ("msp", "ent", "cos", "maha")}

    for i, f in enumerate(te_f):
        xn = ((f - mean) / std).astype(np.float32)
        p = model.predict(xn, batch_size=2048, verbose=0)
        e = model.embedder.predict(xn, batch_size=2048, verbose=0)

        S["msp"][i] = clip_aggregate(1.0 - p.max(axis=1))
        S["ent"][i] = clip_aggregate(-np.sum(p * np.log(p + 1e-12), axis=1))

        d = 1.0 - e @ cent.T                       # kosinusna udaljenost (e je L2-norm)
        S["cos"][i] = clip_aggregate(d.min(axis=1))

        md = np.stack([np.einsum("ij,jk,ik->i", e - cent[k], cov_inv[k], e - cent[k])
                       for k in range(n_cls)], axis=1)
        S["maha"][i] = clip_aggregate(md.min(axis=1))

    print("\n--- REZULTAT (samonadzirani klasifikator) ---")
    best = None
    for k, s in S.items():
        m = ev.dcase_metrics(s, labels, domains)
        print(f"  {k:5s}  auc_source={m['auc_source']:.4f}  auc_target={m['auc_target']:.4f}"
              f"  pauc={m['pauc']:.4f}  hmean={m['hmean']:.4f}")
        if best is None or m["hmean"] > best[1]["hmean"]:
            best = (k, m)

    print(f"\nnajbolji backend: {best[0]}  hmean={best[1]['hmean']:.4f}")

    out = ROOT / "results" / f"ssl_{args.machine}_s{args.seed}.json"
    out.write_text(json.dumps({
        "machine": args.machine, "seed": args.seed, "attr_acc": float(acc),
        "scores": {k: v.tolist() for k, v in S.items()},
        "metrics": {k: ev.dcase_metrics(v, labels, domains) for k, v in S.items()},
    }, indent=2))
    print(f"zapisano: {out}")

    model.save(ROOT / "models" / f"ssl_{args.machine}_s{args.seed}.keras")
    np.savez(ROOT / "models" / f"ssl_{args.machine}_s{args.seed}_stats.npz",
             mean=mean, std=std, cent=cent, cov_inv=np.stack(cov_inv))


if __name__ == "__main__":
    main()
