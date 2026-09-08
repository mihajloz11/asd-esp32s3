"""Measure gain sensitivity of the unchanged C frontend on synthetic noise."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import random
import shutil
import statistics
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "firmware/esp32s3_asd/main/psd_features_c.c"


def probe():
    compiler = shutil.which("gcc")
    if not compiler:
        raise RuntimeError("gcc is required")
    counts = []
    for band in range(96):
        lo, hi = (10 * 400 ** (i / 96) for i in (band, band + 1))
        counts.append(sum(lo <= k * 16000 / 8192 < hi for k in range(4097)))
    empty = [i for i, count in enumerate(counts) if not count]
    rng = random.Random(20260906)
    signal = [rng.uniform(-0.1, 0.1) for _ in range(160000)]
    with tempfile.TemporaryDirectory(prefix="asd-gain-") as directory:
        library_path = Path(directory) / "psd.dll"
        subprocess.run([compiler, "-O2", "-shared", "-o", str(library_path),
                        str(SOURCE), f"-I{SOURCE.parent}"], check=True, capture_output=True)
        library = ctypes.CDLL(str(library_path))
        pointer = ctypes.POINTER(ctypes.c_float)
        library.asd_psd_extract.argtypes = [pointer, ctypes.c_int, pointer]
        library.asd_psd_extract.restype = ctypes.c_int
        library.asd_psd_init()
        features = []
        segments = []
        for gain in (1, 2):
            samples = (ctypes.c_float * len(signal))(*(gain * x for x in signal))
            output = (ctypes.c_float * 96)()
            segments.append(library.asd_psd_extract(samples, len(signal), output))
            features.append(list(output))
        # unload before the temporary directory is removed on Windows
        if hasattr(ctypes, "windll"):
            ctypes.windll.kernel32.FreeLibrary.argtypes = [ctypes.c_void_p]
            ctypes.windll.kernel32.FreeLibrary(library._handle)
        del library
    shifts = [b-a for a, b in zip(*features)]
    expected_populated = len(empty) / 96 * math.log10(4)
    expected_empty = -(96-len(empty)) / 96 * math.log10(4)
    residual = max(abs(delta - (expected_empty if i in empty else expected_populated))
                   for i, delta in enumerate(shifts))
    return {
        "scope": "synthetic broadband noise; no new model or hardware validation",
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "seed": 20260906, "samples": len(signal), "amplitude_gain": 2,
        "segments": segments, "band_bin_counts": counts, "empty_band_indices": empty,
        "expected_populated_shift": expected_populated, "expected_empty_shift": expected_empty,
        "measured_populated_shift_mean": statistics.mean(v for i,v in enumerate(shifts) if i not in empty),
        "measured_empty_shift_mean": statistics.mean(shifts[i] for i in empty),
        "max_residual": residual,
        "diagnostic_pass": empty == [0, 1, 3, 4, 6, 8, 11, 15]
                           and segments == [38, 38] and residual < 1e-4,
        "interpretation": "fixed empty-band floor leaks gain into all centred features; this does not establish an effect on detection accuracy",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = probe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k,v in result.items() if k != "band_bin_counts"}, indent=2))
    return 0 if result["diagnostic_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
