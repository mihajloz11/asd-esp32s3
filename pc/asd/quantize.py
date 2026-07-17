"""E3: PTQ int8 kvantizacija + evaluacija .tflite modela (fp32 i int8) -> ΔAUC.

Upotreba (iz pc/):
    python -m asd.quantize --data ../data/dcase2026_dev/fan --tag fan_baseline_s0

Izlaz: models/<tag>.tflite, models/<tag>_int8.tflite, red u results/results.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from . import data, eval as ev

ROOT = Path(__file__).resolve().parents[2]


def convert(keras_path: Path, rep_data: np.ndarray | None) -> bytes:
    import tensorflow as tf
    m = tf.keras.models.load_model(keras_path)
    conv = tf.lite.TFLiteConverter.from_keras_model(m)
    if rep_data is not None:
        conv.optimizations = [tf.lite.Optimize.DEFAULT]

        def rep():
            for i in range(0, len(rep_data), 1):
                yield [rep_data[i:i + 1].astype(np.float32)]
        conv.representative_dataset = rep
        conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        conv.inference_input_type = tf.int8
        conv.inference_output_type = tf.int8
    return conv.convert()


class TFLitePredict:
    """Batch-predict wrapper oko tf.lite.Interpreter (radi i za int8 i za fp32)."""

    def __init__(self, model_bytes: bytes):
        import tensorflow as tf
        self.it = tf.lite.Interpreter(model_content=model_bytes)
        self.it.allocate_tensors()
        self.inp = self.it.get_input_details()[0]
        self.out = self.it.get_output_details()[0]

    def __call__(self, x: np.ndarray) -> np.ndarray:
        res = np.empty((len(x), self.out["shape"][-1]), dtype=np.float32)
        int8_in = self.inp["dtype"] == np.int8
        if int8_in:
            s_i, z_i = self.inp["quantization"]
            s_o, z_o = self.out["quantization"]
        for i in range(len(x)):
            v = x[i:i + 1].astype(np.float32)
            if int8_in:
                v = np.clip(np.round(v / s_i + z_i), -128, 127).astype(np.int8)
            self.it.set_tensor(self.inp["index"], v)
            self.it.invoke()
            o = self.it.get_tensor(self.out["index"])
            res[i] = (o.astype(np.float32) - z_o) * s_o if int8_in else o
        return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--tag", required=True, help="npr. fan_baseline_s0 (postojeci .keras u models/)")
    ap.add_argument("--rep-size", type=int, default=2000, help="broj vektora za PTQ kalibraciju")
    args = ap.parse_args()

    machine_dir = Path(args.data).resolve()
    machine = machine_dir.name
    models_dir = ROOT / "models"
    meta = json.loads((models_dir / f"{args.tag}_meta.json").read_text())
    mean = np.array(meta["mean"], dtype=np.float32)
    std = np.array(meta["std"], dtype=np.float32)

    cache_dir = ROOT / "results" / "features"
    train_clips = data.list_clips(machine_dir, "train")
    test_clips = data.list_clips(machine_dir, "test")
    train_feats = data.load_features(train_clips, cache_dir / f"{machine}_train.npz")
    test_feats = data.load_features(test_clips, cache_dir / f"{machine}_test.npz")

    xall = np.concatenate([(f - mean) / std for f in train_feats], axis=0)
    rng = np.random.default_rng(0)
    rep = xall[rng.choice(len(xall), min(args.rep_size, len(xall)), replace=False)]

    labels = np.array([c.label for c in test_clips])
    domains = np.array([c.domain for c in test_clips])
    res_csv = ROOT / "results" / "results.csv"

    for precision, rep_arg, suffix in [("fp32_tflite", None, ""), ("int8", rep, "_int8")]:
        blob = convert(models_dir / f"{args.tag}.keras", rep_arg)
        out_path = models_dir / f"{args.tag}{suffix}.tflite"
        out_path.write_bytes(blob)
        pred = TFLitePredict(blob)
        scores = ev.clip_scores_mse(pred, test_feats, mean, std)
        met = ev.dcase_metrics(scores, labels, domains)
        row = {"tag": args.tag, "machine": machine, "variant": meta["variant"],
               "seed": meta["seed"], "score": "mse", "precision": precision,
               "n_params": meta["n_params"],
               **{k: round(float(v), 4) for k, v in met.items()}}
        with open(res_csv, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            w.writerow(row)
        print(f"[{args.tag} {precision}] size={len(blob)/1024:.1f} KB  " +
              "  ".join(f"{k}={v:.4f}" for k, v in met.items()))


if __name__ == "__main__":
    main()
