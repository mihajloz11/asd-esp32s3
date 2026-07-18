"""MAHALA mod na vec istreniranim modelima (bez retreninga): ucita .keras,
fituje kovarijansu rekonstrukcionih gresaka na treningu, skoruje test
Mahalanobisovom distancom, upise red u results.csv (score=mahala).

DCASE 2024/2026 baseline pokazuje da MAHALA cesto dize target-domain AUC —
ovo je jeftin nacin da to provjerimo na nasim modelima.

Upotreba (iz pc/): python tools/score_mahala.py --data ..\\data\\dcase2026_dev\\fan --tag fan_baseline_s0
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data, eval as ev  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    import tensorflow as tf
    machine_dir = Path(args.data).resolve()
    machine = machine_dir.name
    meta = json.loads((ROOT / "models" / f"{args.tag}_meta.json").read_text())
    mean = np.array(meta["mean"], dtype=np.float32)
    std = np.array(meta["std"], dtype=np.float32)

    cache = ROOT / "results" / "features"
    train_clips = data.list_clips(machine_dir, "train")
    test_clips = data.list_clips(machine_dir, "test")
    train_feats = data.load_features(train_clips, cache / f"{machine}_train.npz")
    test_feats = data.load_features(test_clips, cache / f"{machine}_test.npz")

    m = tf.keras.models.load_model(ROOT / "models" / f"{args.tag}.keras")
    predict = lambda a: m.predict(a, batch_size=1024, verbose=0)

    mu, cov_inv = ev.fit_mahala(predict, train_feats, mean, std)
    scores = ev.clip_scores_mahala(predict, test_feats, mean, std, mu, cov_inv)
    labels = np.array([c.label for c in test_clips])
    domains = np.array([c.domain for c in test_clips])
    met = ev.dcase_metrics(scores, labels, domains)

    row = {"tag": args.tag, "machine": machine, "variant": meta["variant"],
           "seed": meta["seed"], "score": "mahala", "precision": "fp32",
           "n_params": meta["n_params"],
           **{k: round(float(v), 4) for k, v in met.items()}}
    with open(ROOT / "results" / "results.csv", "a", newline="") as f:
        csv.DictWriter(f, fieldnames=list(row)).writerow(row)
    print(f"[{args.tag} MAHALA] " + "  ".join(f"{k}={v:.4f}" for k, v in met.items()))


if __name__ == "__main__":
    main()
