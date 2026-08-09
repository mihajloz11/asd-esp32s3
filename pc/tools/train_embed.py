"""Naucena ugradnja preko SVIH masina — pokusaj da se predje 0.674.

DOKLE SMO STIGLI (sve izmjereno, results/):
    autoenkoder, novi ventilator                     AUC 0.451
    sazetak log-mela + naucena kovarijansa           AUC 0.674
    (dijagonalna 0.595, mjesanje ne pomaze, CMN 0.54)

Sirovi log-mel sazetak je iscrpljen. Trebaju bolji featuri.

IDEJA. Umjesto da mreza uci da PREKOPIRA zvuk (autoenkoder), uci je da RAZLIKUJE
masine i njihove radne rezime. Da bi to umjela, mora nauciti sta u zvuku nosi
informaciju o stanju masine — a to je bas ono sto treba za detekciju kvara.
Mreza se onda koristi samo kao pretvarac zvuka u vektor; odluka i dalje pada na
Mahalanobisu oko centra izmjerenog na licu mjesta.

ZASTO PREKO SVIH MASINA. Prvi pokusaj (train_ssl.py) ucio je samo 3 brzine
ventilatora — premalo da se nesto nauci, i pao je na 0.53. Ovdje su klase
tip masine x atribut, ukupno ~50, pa zadatak ima sadrzaja:
    fan spd=3, gearboxEmu pro=10, ToyCarEmu car=8 x speed=5, ostale bez atributa

OCJENA je ista i posteno odvojena: k klipova ciljnog ventilatora ide u
kalibraciju, ocjenjuje se na preostalim normalnim + svim anomalijama.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/train_embed.py --stride 20 --epochs 15
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "dcase2026_dev"
MACHINES = ["fan", "bearingEmu", "gearboxEmu", "sliderEmu", "ToyCar", "ToyCarEmu", "valveEmu"]


def attr_map(machine: str) -> dict[str, str]:
    """ime fajla BEZ nastavka -> string atributa ('' ako masina nema atribute).

    Kljuc je stem, ne puno ime: fan CSV pise '/fan/train/....wav', a ToyCarEmu
    '..._mic_1' bez nastavka. Poredjenje po punom imenu je zato promasivalo i
    ToyCarEmu je ostajao bez atributa (17 klasa umjesto ~50)."""
    p = BASE / machine / "attributes_00.csv"
    out: dict[str, str] = {}
    if not p.is_file():
        return out
    for r in csv.DictReader(open(p)):
        stem = Path(r["file_name"]).stem
        parts = []
        for kp in sorted(k for k in r if k and re.fullmatch(r"d\d+p", k)):
            kv = kp[:-1] + "v"
            if r.get(kp):
                parts.append(f"{r[kp]}={r.get(kv, '')}")
        out[stem] = "|".join(parts)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stride", type=int, default=20)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--emb", type=int, default=128)
    ap.add_argument("--width", type=int, default=256)
    ap.add_argument("--eval-machine", default="fan")
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--repeats", type=int, default=20)
    args = ap.parse_args()

    import tensorflow as tf
    tf.keras.utils.set_random_seed(0)
    cache = ROOT / "results" / "cache"

    # ---- 1. skupljanje trening vektora preko svih masina ----
    xs, labs = [], []
    for m in MACHINES:
        clips = data.list_clips(BASE / m, "train")
        feats = data.load_features(clips, cache / f"{m}_train.npz", f"{m} train")
        am = attr_map(m)
        for f, c in zip(feats, clips):
            v = f[:: args.stride]
            xs.append(v.astype(np.float32))
            labs += [f"{m}#{am.get(c.path.stem, '')}"] * len(v)
        print(f"  {m}: {len(clips)} klipova")

    X = np.concatenate(xs)
    del xs
    classes = sorted(set(labs))
    cls_id = {c: i for i, c in enumerate(classes)}
    Y = np.array([cls_id[l] for l in labs], dtype=np.int32)
    del labs

    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-6
    X = (X - mean) / std

    # OBAVEZNO promijesati: podaci su slagani masina po masina, a Keras uzima
    # validaciju kao ZADNJIH n% — bez mijesanja validacija ispadne jedna jedina
    # klasa, val_accuracy 1.0 vec u prvoj epohi, i rano zaustavljanje vrati
    # tezine iz prve epohe. Tako je prvi pokusaj i propao.
    sh = np.random.default_rng(0).permutation(len(X))
    X, Y = X[sh], Y[sh]
    print(f"\ntrening: {X.shape}, klasa: {len(classes)}")
    print(f"klase: {', '.join(classes[:6])}{' ...' if len(classes) > 6 else ''}")

    # ---- 2. mreza: ugradnja + klasifikacija ----
    L = tf.keras.layers
    inp = L.Input(shape=(X.shape[1],))
    h = L.Dense(args.width, use_bias=False)(inp)
    h = L.BatchNormalization()(h)
    h = L.Activation("relu")(h)
    h = L.Dropout(0.2)(h)
    h = L.Dense(args.width, use_bias=False)(h)
    h = L.BatchNormalization()(h)
    h = L.Activation("relu")(h)
    h = L.Dropout(0.2)(h)
    e = L.Dense(args.emb, name="emb")(h)
    en = L.Lambda(lambda z: tf.math.l2_normalize(z, axis=1), name="embn")(e)
    out = L.Dense(len(classes), activation="softmax")(en)
    model = tf.keras.Model(inp, out)
    embedder = tf.keras.Model(inp, en)
    model.compile(tf.keras.optimizers.Adam(1e-3),
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(),
                  metrics=["accuracy"])
    model.fit(X, Y, batch_size=1024, epochs=args.epochs, validation_split=0.08,
              verbose=2,
              callbacks=[tf.keras.callbacks.EarlyStopping(
                  monitor="val_loss", patience=4, restore_best_weights=True)])
    del X, Y

    # ---- 3. ocjena na ciljnoj masini ----
    em = args.eval_machine
    tr_c = data.list_clips(BASE / em, "train")
    te_c = data.list_clips(BASE / em, "test")
    tr_f = data.load_features(tr_c, cache / f"{em}_train.npz", "train")
    te_f = data.load_features(te_c, cache / f"{em}_test.npz", "test")

    def clip_emb(f):
        z = embedder.predict(((f - mean) / std).astype(np.float32),
                             batch_size=4096, verbose=0)
        return np.concatenate([z.mean(axis=0), z.std(axis=0)])

    E_tr = np.stack([clip_emb(f) for f in tr_f])
    E_te = np.stack([clip_emb(f) for f in te_f])
    tr_dom = np.array([c.domain for c in tr_c])
    te_dom = np.array([c.domain for c in te_c])
    te_lab = np.array([c.label for c in te_c])

    C_learn = np.cov(E_tr[tr_dom == "source"].T)
    Ci = np.linalg.pinv(C_learn + 1e-4 * np.eye(len(C_learn)))

    print("\n--- OCJENA (ugradnja + kalibracija centra) ---")
    res = {}
    for dom in ("target", "source"):
        pool = np.concatenate([E_tr[tr_dom == dom],
                               E_te[(te_dom == dom) & (te_lab == 0)]])
        anom = E_te[(te_dom == dom) & (te_lab == 1)]
        aucs = []
        for rep in range(args.repeats):
            rng = np.random.default_rng(5000 + rep)
            idx = rng.permutation(len(pool))
            k = min(args.k, len(pool) // 3)
            cal, held = pool[idx[:k]], pool[idx[k:]]
            Xe = np.concatenate([held, anom])
            y = np.concatenate([np.zeros(len(held)), np.ones(len(anom))])
            d = Xe - cal.mean(axis=0)
            aucs.append(roc_auc_score(y, np.einsum("ij,jk,ik->i", d, Ci, d)))
        res[dom] = (float(np.mean(aucs)), float(np.std(aucs)))
        print(f"  {dom:7s} k={args.k}  AUC={np.mean(aucs):.3f}±{np.std(aucs):.03f}"
              f"   (bazen={len(pool)}, anom={len(anom)})")

    p = ROOT / "results" / f"embed_{em}.json"
    p.write_text(json.dumps({"classes": len(classes), "res": res}, indent=2))
    print(f"\nzapisano: {p}")
    model.save(ROOT / "models" / "embed_all.keras")
    np.savez(ROOT / "models" / "embed_all_stats.npz", mean=mean, std=std, Ci=Ci)


if __name__ == "__main__":
    main()
