"""Pravi psd_model_nonempty_data.h iz modela zamrznutog 07.09.2026.

Model nije ponovo ucen: uzima se `results/psd_nonempty/2026-09-07/
nonempty_log96_model.npz`, cija se SHA-256 provjerava prema `frozen.json`.
Zaglavlje ima ista imena kao `psd_model_data.h`, pa ga `psd_live.c` bira
samo zastavicom ASD_PSD_NONEMPTY_BANDS.

Pokretanje iz korijena repoa:
    python pc/tools/export_psd_nonempty.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "results/psd_nonempty/2026-09-07"
MODEL = EXPERIMENT / "nonempty_log96_model.npz"
HEADER = ROOT / "firmware/esp32s3_asd/main/psd_model_nonempty_data.h"
DIM = 96


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


def load_model():
    frozen = json.loads((EXPERIMENT / "frozen.json").read_text(encoding="utf-8"))
    expected = frozen["models"]["nonempty_log96"]
    actual = hashlib.sha256(MODEL.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"model nije zamrznuti: {actual} != {expected}")
    z = np.load(MODEL)
    mean = z["source_mean"].astype(np.float32)
    scale = z["source_scale"].astype(np.float32)
    precision = z["precision"].astype(np.float32)
    if mean.shape != (DIM,) or scale.shape != (DIM,) or precision.shape != (DIM, DIM):
        raise SystemExit("pogresne dimenzije modela")
    if not all(np.isfinite(a).all() for a in (mean, scale, precision)):
        raise SystemExit("model ima nekonacne vrijednosti")
    if not (scale > 0).all():
        raise SystemExit("skala mora biti pozitivna")
    p = precision.astype(np.float64)
    if not np.array_equal(p, p.T) or np.linalg.eigvalsh(p).min() <= 0:
        raise SystemExit("float32 matrica preciznosti nije simetricna pozitivno definitna")
    return mean, scale, precision


def fingerprint(*arrays: np.ndarray) -> str:
    h = hashlib.sha256()
    for array in arrays:
        h.update(np.asarray(array, np.float32).tobytes(order="C"))
    return h.hexdigest()


def render(mean, scale, precision) -> str:
    digest = fingerprint(mean, scale, precision)
    fingerprint_bytes = ", ".join(f"0x{b:02x}" for b in bytes.fromhex(digest))
    return f"""/* AUTO-GENERISANO: pc/tools/export_psd_nonempty.py - NE EDITOVATI.
 * EKSPERIMENT: model za neprazne PSD trake (ASD_PSD_NONEMPTY_BANDS).
 * Izvor: results/psd_nonempty/2026-09-07/nonempty_log96_model.npz,
 * 990 source normalnih snimaka, Ledoit-Wolf; sha256={digest}
 * Centar i pragovi mjere se na uredjaju, iznova za ovaj front-end. */
#ifndef ASD_PSD_MODEL_DATA_H
#define ASD_PSD_MODEL_DATA_H

#define ASD_PSD_MODEL_DIM {DIM}
#define ASD_PSD_MODEL_FINGERPRINT_SIZE 32
#define ASD_PSD_MODEL_FINGERPRINT_HEX "{digest}"

static const unsigned char asd_psd_model_fingerprint[ASD_PSD_MODEL_FINGERPRINT_SIZE] = {{
    {fingerprint_bytes}
}};

static const float asd_psd_norm_mean[{DIM}] = {{
    {floats(mean)}
}};

static const float asd_psd_norm_std[{DIM}] = {{
    {floats(scale)}
}};

static const float asd_psd_precision[{DIM * DIM}] = {{
    {floats(precision)}
}};

#endif
"""


def main():
    arrays = load_model()
    HEADER.write_text(render(*arrays), encoding="utf-8")
    print(f"model {fingerprint(*arrays)}")
    print(f"saved: {HEADER}")


if __name__ == "__main__":
    main()
