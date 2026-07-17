"""Generiše model_data.h za firmware: int8 .tflite kao C niz + mean/std
normalizacija + gamma prag iz meta.json.

Upotreba (iz pc/): python tools/gen_model_header.py --tag fan_baseline_s0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "firmware" / "esp32s3_asd" / "main" / "model_data.h"


def _flit(v: float) -> str:
    s = f"{v:.9g}"
    if "." not in s and "e" not in s and "n" not in s:
        s += ".0"
    return s + "f"


def fmt_floats(arr, per_line: int = 8) -> str:
    vals = [_flit(v) for v in arr]
    return ",\n    ".join(", ".join(vals[i:i + per_line]) for i in range(0, len(vals), per_line))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--int8", action="store_true", default=True)
    args = ap.parse_args()

    tflite_path = ROOT / "models" / f"{args.tag}_int8.tflite"
    meta = json.loads((ROOT / "models" / f"{args.tag}_meta.json").read_text())
    blob = tflite_path.read_bytes()
    mean = np.array(meta["mean"], dtype=np.float32)
    std = np.array(meta["std"], dtype=np.float32)
    thr = meta["gamma"]["threshold_moment"]

    body = ",\n    ".join(
        ", ".join(f"0x{b:02x}" for b in blob[i:i + 16]) for i in range(0, len(blob), 16))
    h = [
        f"/* AUTO-GENERISANO: pc/tools/gen_model_header.py --tag {args.tag} — NE EDITOVATI.",
        f" * model={tflite_path.name}, {len(blob)} B, params={meta['n_params']},",
        f" * hmean(fp32)={meta.get('hmean', 0):.4f} */",
        "#ifndef ASD_MODEL_DATA_H",
        "#define ASD_MODEL_DATA_H",
        "#include <stdint.h>",
        "",
        f"#define ASD_MODEL_INPUT_DIM {meta['input_dim']}",
        f"#define ASD_SCORE_THRESHOLD {thr:.9g}f",
        "",
        f"static const float asd_norm_mean[{len(mean)}] = {{",
        f"    {fmt_floats(mean)}",
        "};",
        f"static const float asd_norm_std[{len(std)}] = {{",
        f"    {fmt_floats(std)}",
        "};",
        "",
        "/* .tflite flatbuffer — 16-bajtno poravnat za TFLM. Uključuje se SAMO u",
        " * tflm_infer.cc (#define ASD_INCLUDE_MODEL_BLOB) da se ne duplira u flash. */",
        "#ifdef ASD_INCLUDE_MODEL_BLOB",
        f"__attribute__((aligned(16))) static const unsigned char asd_model_tflite[{len(blob)}] = {{",
        f"    {body}",
        "};",
        "#endif",
        "",
        "#endif",
        "",
    ]
    OUT.write_text("\n".join(h), encoding="utf-8")
    print(f"OK: {OUT}  (model {len(blob) / 1024:.1f} KB, prag={thr:.5g})")


if __name__ == "__main__":
    main()
