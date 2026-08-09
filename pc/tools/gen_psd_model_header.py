"""Eksportuje normal-only PSD model u NPZ, JSON i C header za ESP32-S3.

Ulaz je regenerabilni cache koji pravi ``bench_periodicity.py``. U model ulaze
isključivo source/train/normal klipovi; target centar se namjerno ne eksportuje
jer ga svaki uređaj mjeri tokom lokalne kalibracije.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.covariance import LedoitWolf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MACHINE = "fan"
DIM = 96
NPZ_OUT = ROOT / "models" / "fan_psd_shape.npz"
META_OUT = ROOT / "models" / "fan_psd_shape_meta.json"
HEADER_OUT = ROOT / "firmware" / "esp32s3_asd" / "main" / "psd_model_data.h"


def flit(value: float) -> str:
    s = f"{float(value):.9g}"
    if "." not in s and "e" not in s:
        s += ".0"
    return s + "f"


def floats(values: np.ndarray, per_line: int = 8) -> str:
    flat = np.asarray(values).reshape(-1)
    rows = [", ".join(flit(x) for x in flat[i:i + per_line])
            for i in range(0, len(flat), per_line)]
    return ",\n    ".join(rows)


def digest(*arrays: np.ndarray) -> str:
    h = hashlib.sha256()
    for array in arrays:
        h.update(np.asarray(array, np.float32).tobytes(order="C"))
    return h.hexdigest()


def main() -> None:
    clips = data.list_clips(ROOT / "data" / "dcase2026_dev" / MACHINE, "train")
    domains = np.array([c.domain for c in clips])
    cache = ROOT / "results" / "cache" / f"{MACHINE}_periodicity.npz"
    if not cache.exists():
        raise FileNotFoundError(f"prvo pokreni bench_periodicity.py: {cache}")
    all_features = np.load(cache)["psd_shape"]
    train_features = all_features[:len(clips)]
    source = train_features[domains == "source"].astype(np.float64)
    if source.shape != (990, DIM):
        raise ValueError(f"očekivano (990,{DIM}), dobijeno {source.shape}")

    mean = source.mean(axis=0)
    std = source.std(axis=0) + 1e-8
    normalized = (source - mean) / std
    precision = LedoitWolf().fit(normalized).precision_

    mean32 = mean.astype(np.float32)
    std32 = std.astype(np.float32)
    precision32 = precision.astype(np.float32)
    checksum = digest(mean32, std32, precision32)

    NPZ_OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(NPZ_OUT, mean=mean32, std=std32, precision=precision32)

    benchmark_path = ROOT / "results" / "periodicity_fan_k20.json"
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8")) if benchmark_path.exists() else {}
    result = benchmark.get("target_final", {}).get("psd_shape", {})
    meta = {
        "name": "fan_psd_shape_ledoitwolf",
        "trained_only_on": "DCASE2026 fan source/train/normal",
        "n_normal_clips": int(len(source)),
        "feature": {
            "sample_rate": 16000,
            "clip_seconds": 10,
            "welch_n_fft": 8192,
            "welch_hop": 4096,
            "frequency_min_hz": 10.0,
            "frequency_max_hz": 4000.0,
            "bands": DIM,
            "transform": "log10 band mean power, then subtract clip scalar mean",
        },
        "model": {
            "covariance": "LedoitWolf",
            "dimension": DIM,
            "precision_matrix_float32_bytes": int(precision32.nbytes),
            "normalization_float32_bytes": int(mean32.nbytes + std32.nbytes),
            "local_center_float32_bytes": DIM * 4,
            "sha256_float32_arrays": checksum,
        },
        "benchmark_target_auc_k20": result.get("auc"),
        "benchmark_target_auc_std_k20": result.get("std"),
        "note": "Target center and threshold are measured locally and are not part of this file.",
    }
    META_OUT.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    header = f"""/* AUTO-GENERISANO: pc/tools/gen_psd_model_header.py - NE EDITOVATI.
 * Normal-only model: {len(source)} source klipova; sha256={checksum}
 * Target centar i prag mjere se lokalno na uredjaju. */
#ifndef ASD_PSD_MODEL_DATA_H
#define ASD_PSD_MODEL_DATA_H

#define ASD_PSD_MODEL_DIM {DIM}

static const float asd_psd_norm_mean[{DIM}] = {{
    {floats(mean32)}
}};

static const float asd_psd_norm_std[{DIM}] = {{
    {floats(std32)}
}};

static const float asd_psd_precision[{DIM * DIM}] = {{
    {floats(precision32)}
}};

#endif
"""
    HEADER_OUT.write_text(header, encoding="utf-8")
    print(f"OK: {META_OUT}")
    print(f"OK: {NPZ_OUT} (ignored artifact)")
    print(f"OK: {HEADER_OUT} ({HEADER_OUT.stat().st_size} B source header)")


if __name__ == "__main__":
    main()
