"""MAHALA na INT8 modelima — preživljava li target-domain uplift kvantizaciju?
Batched int8 interpreter (resize na batch) radi brzo. Upisuje score=mahala,
precision=int8 u results.csv.

Upotreba (iz pc/): python tools/score_mahala_int8.py --data ..\\data\\dcase2026_dev\\fan --tag fan_baseline_s0
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


class BatchInt8Predict:
    """Brz int8 predictor — resize interpreter na batch pa jedan invoke po grupi."""

    def __init__(self, model_bytes: bytes, batch: int = 512):
        import tensorflow as tf
        self.it = tf.lite.Interpreter(model_content=model_bytes)
        self.inp = self.it.get_input_details()[0]
        self.out = self.it.get_output_details()[0]
        self.batch = batch
        self.it.resize_tensor_input(self.inp["index"], [batch, self.inp["shape"][-1]])
        self.it.allocate_tensors()
        self.s_i, self.z_i = self.inp["quantization"]
        self.s_o, self.z_o = self.out["quantization"]

    def __call__(self, x: np.ndarray) -> np.ndarray:
        out = np.empty((len(x), self.out["shape"][-1]), dtype=np.float32)
        for i in range(0, len(x), self.batch):
            chunk = x[i:i + self.batch]
            n = len(chunk)
            pad = np.zeros((self.batch, chunk.shape[1]), dtype=np.float32)
            pad[:n] = chunk
            q = np.clip(np.round(pad / self.s_i + self.z_i), -128, 127).astype(np.int8)
            self.it.set_tensor(self.inp["index"], q)
            self.it.invoke()
            o = self.it.get_tensor(self.out["index"]).astype(np.float32)
            out[i:i + n] = (o[:n] - self.z_o) * self.s_o
        return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    machine_dir = Path(args.data).resolve()
    machine = machine_dir.name
    meta = json.loads((ROOT / "models" / f"{args.tag}_meta.json").read_text())
    mean = np.array(meta["mean"], dtype=np.float32)
    std = np.array(meta["std"], dtype=np.float32)
    pred = BatchInt8Predict((ROOT / "models" / f"{args.tag}_int8.tflite").read_bytes())

    cache = ROOT / "results" / "features"
    train_clips = data.list_clips(machine_dir, "train")
    test_clips = data.list_clips(machine_dir, "test")
    train_feats = data.load_features(train_clips, cache / f"{machine}_train.npz")
    test_feats = data.load_features(test_clips, cache / f"{machine}_test.npz")

    mu, cov_inv = ev.fit_mahala(pred, train_feats, mean, std)
    scores = ev.clip_scores_mahala(pred, test_feats, mean, std, mu, cov_inv)
    labels = np.array([c.label for c in test_clips])
    domains = np.array([c.domain for c in test_clips])
    met = ev.dcase_metrics(scores, labels, domains)

    row = {"tag": args.tag, "machine": machine, "variant": meta["variant"],
           "seed": meta["seed"], "score": "mahala", "precision": "int8",
           "n_params": meta["n_params"], **{k: round(float(v), 4) for k, v in met.items()}}
    with open(ROOT / "results" / "results.csv", "a", newline="") as f:
        csv.DictWriter(f, fieldnames=list(row)).writerow(row)
    print(f"[{args.tag} MAHALA-int8] " + "  ".join(f"{k}={v:.4f}" for k, v in met.items()))


if __name__ == "__main__":
    main()
