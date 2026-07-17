"""Generiše firmware/esp32s3_asd/main/mel_data.h iz Python front-enda:
Hann prozor (periodični) + Slaney mel filterbank u sparse formatu.
Iste vrijednosti koje koristi asd/features.py — jedna tačka istine.

Upotreba (iz pc/): python tools/gen_mel_header.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import features  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "firmware" / "esp32s3_asd" / "main" / "mel_data.h"


def _flit(v: float) -> str:
    s = f"{v:.9g}"
    if "." not in s and "e" not in s and "n" not in s:
        s += ".0"
    return s + "f"


def fmt_floats(arr: np.ndarray, per_line: int = 8) -> str:
    vals = [_flit(v) for v in arr]
    lines = [", ".join(vals[i:i + per_line]) for i in range(0, len(vals), per_line)]
    return ",\n    ".join(lines)


def main() -> None:
    hann = features.hann_window()
    fb = features.mel_filterbank()  # (128, 513)

    starts, lens, offsets, weights = [], [], [0], []
    for m in range(fb.shape[0]):
        nz = np.nonzero(fb[m])[0]
        if len(nz) == 0:  # prazan filter (moguće za visoke mel binove pri malom n_fft)
            starts.append(0); lens.append(0)
        else:
            s, e = int(nz[0]), int(nz[-1]) + 1
            starts.append(s); lens.append(e - s)
            weights.extend(fb[m, s:e].tolist())
        offsets.append(len(weights))

    w = np.array(weights, dtype=np.float32)
    h = [
        "/* AUTO-GENERISANO: pc/tools/gen_mel_header.py — NE EDITOVATI RUČNO.",
        f" * sr={features.SR}, n_fft={features.N_FFT}, n_mels={features.N_MELS},",
        " * Slaney mel (librosa-kompatibilan), periodični Hann. */",
        "#ifndef ASD_MEL_DATA_H",
        "#define ASD_MEL_DATA_H",
        "#include <stdint.h>",
        "",
        f"static const float asd_hann[{len(hann)}] = {{",
        f"    {fmt_floats(hann)}",
        "};",
        "",
        f"static const uint16_t asd_mel_start[{len(starts)}] = {{ {', '.join(map(str, starts))} }};",
        f"static const uint16_t asd_mel_len[{len(lens)}] = {{ {', '.join(map(str, lens))} }};",
        f"static const uint32_t asd_mel_offset[{len(offsets) - 1}] = {{ {', '.join(map(str, offsets[:-1]))} }};",
        "",
        f"static const float asd_mel_weights[{len(w)}] = {{",
        f"    {fmt_floats(w)}",
        "};",
        "",
        "#endif",
        "",
    ]
    OUT.write_text("\n".join(h), encoding="utf-8")
    print(f"OK: {OUT}  (weights={len(w)}, ~{w.nbytes / 1024:.1f} KB u flash)")


if __name__ == "__main__":
    main()
