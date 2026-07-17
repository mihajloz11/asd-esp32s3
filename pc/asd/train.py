"""Trening + evaluacija jedne AE varijante na jednoj mašini (E1/E2).

Upotreba (iz pc/):
    python -m asd.train --data ../data/dcase2026_dev/fan --variant baseline
    python -m asd.train --data ../data/dcase2026_dev/fan --variant tiny32 --epochs 100

Izlaz: models/<machine>_<variant>.keras, models/<machine>_<variant>_meta.json,
       results/results.csv (append red sa metrikama).
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np

from . import data, eval as ev, model as mdl

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="machine dir, npr. ../data/dcase2026_dev/fan")
    ap.add_argument("--variant", default="baseline", choices=list(mdl.SWEEP))
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--score", default="mse", choices=["mse", "mahala"])
    args = ap.parse_args()

    import tensorflow as tf
    tf.keras.utils.set_random_seed(args.seed)

    machine_dir = Path(args.data).resolve()
    machine = machine_dir.name
    tag = f"{machine}_{args.variant}_s{args.seed}"
    cache_dir = ROOT / "results" / "features"

    train_clips = data.list_clips(machine_dir, "train")
    test_clips = data.list_clips(machine_dir, "test")
    train_feats = data.load_features(train_clips, cache_dir / f"{machine}_train.npz", "train feats")
    test_feats = data.load_features(test_clips, cache_dir / f"{machine}_test.npz", "test feats")

    mean, std = data.fit_norm(train_feats)
    x = np.concatenate([(f - mean) / std for f in train_feats], axis=0)

    m = mdl.build_ae(input_dim=x.shape[1], **mdl.SWEEP[args.variant])
    n_params = m.count_params()
    t0 = time.time()
    m.fit(x, x, epochs=args.epochs, batch_size=args.batch, validation_split=0.1,
          shuffle=True, verbose=2)
    train_time = time.time() - t0

    predict = lambda a: m.predict(a, batch_size=1024, verbose=0)
    if args.score == "mahala":
        mu, cov_inv = ev.fit_mahala(predict, train_feats, mean, std)
        scores = ev.clip_scores_mahala(predict, test_feats, mean, std, mu, cov_inv)
        train_scores = ev.clip_scores_mahala(predict, train_feats, mean, std, mu, cov_inv)
    else:
        scores = ev.clip_scores_mse(predict, test_feats, mean, std)
        train_scores = ev.clip_scores_mse(predict, train_feats, mean, std)

    labels = np.array([c.label for c in test_clips])
    domains = np.array([c.domain for c in test_clips])
    met = ev.dcase_metrics(scores, labels, domains)
    thr = ev.gamma_threshold(train_scores)

    models_dir = ROOT / "models"
    models_dir.mkdir(exist_ok=True)
    m.save(models_dir / f"{tag}.keras")
    meta = {"tag": tag, "machine": machine, "variant": args.variant, "seed": args.seed,
            "score_mode": args.score, "n_params": int(n_params), "epochs": args.epochs,
            "train_time_s": round(train_time, 1), "input_dim": int(x.shape[1]),
            "mean": mean.tolist(), "std": std.tolist(), **{k: float(v) for k, v in met.items()},
            "gamma": {k: float(v) for k, v in thr.items()}}
    (models_dir / f"{tag}_meta.json").write_text(json.dumps(meta, indent=1))

    res_csv = ROOT / "results" / "results.csv"
    res_csv.parent.mkdir(exist_ok=True)
    row = {"tag": tag, "machine": machine, "variant": args.variant, "seed": args.seed,
           "score": args.score, "precision": "fp32", "n_params": n_params,
           **{k: round(float(v), 4) for k, v in met.items()}}
    write_header = not res_csv.exists()
    with open(res_csv, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if write_header:
            w.writeheader()
        w.writerow(row)

    print(f"\n[{tag}] params={n_params}  " +
          "  ".join(f"{k}={v:.4f}" for k, v in met.items()))
    print(f"gamma prag (MLE)={thr['threshold']:.5g}  (momentna metoda)={thr['threshold_moment']:.5g}")


if __name__ == "__main__":
    main()
