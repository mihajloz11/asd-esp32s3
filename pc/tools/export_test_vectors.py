"""Eksport "poznato dobrih" test vektora za on-device debug (plan, zlatno pravilo 1
i rizik B3): uzme jedan WAV, izračuna featuri + normalizovan vektor + očekivani
score (tflite int8 na PC-u), snimi binarno u firmware/test_vectors/.

Na uređaju: hardkodovan vektor -> tflm_score_vector() -> poređenje sa expected.

Upotreba (iz pc/):
    python tools/export_test_vectors.py --wav <path.wav> --tag fan_baseline_s0
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import features  # noqa: E402
from asd.quantize import TFLitePredict  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", required=True)
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    meta = json.loads((ROOT / "models" / f"{args.tag}_meta.json").read_text())
    mean = np.array(meta["mean"], dtype=np.float32)
    std = np.array(meta["std"], dtype=np.float32)

    vecs = features.wav_to_vectors(args.wav)
    xn = (vecs - mean) / std

    blob = (ROOT / "models" / f"{args.tag}_int8.tflite").read_bytes()
    pred = TFLitePredict(blob)
    rec = pred(xn)
    per_vec_mse = np.mean((xn - rec) ** 2, axis=1)

    out_dir = ROOT / "firmware" / "test_vectors"
    out_dir.mkdir(exist_ok=True)
    xn[:8].astype(np.float32).tofile(out_dir / "vectors_f32.bin")
    per_vec_mse[:8].astype(np.float32).tofile(out_dir / "expected_mse_f32.bin")
    (out_dir / "info.json").write_text(json.dumps({
        "wav": str(args.wav), "tag": args.tag, "n_vectors": 8,
        "clip_score_int8_pc": float(per_vec_mse.mean()),
        "first_mse": [float(v) for v in per_vec_mse[:8]],
    }, indent=1))
    print(f"OK: {out_dir}  clip score (int8, PC) = {per_vec_mse.mean():.6f}")


if __name__ == "__main__":
    main()
