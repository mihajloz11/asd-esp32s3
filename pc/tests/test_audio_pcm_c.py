"""Konverzija INMP441 uzorka u int16: isto kao ranije u opsegu, zasicenje van njega."""
from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
FW_MAIN = ROOT / "firmware" / "esp32s3_asd" / "main"

WRAPPER = r"""
#include "audio_pcm.h"
void convert(const int32_t *raw, int16_t *pcm, int32_t *magnitude, int n) {
    for (int i = 0; i < n; i++) {
        pcm[i] = audio_pcm_from_raw(raw[i]);
        magnitude[i] = audio_pcm_raw_magnitude(raw[i]);
    }
}
"""


@pytest.fixture(scope="module")
def lib(tmp_path_factory):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema C kompajlera")
    work = tmp_path_factory.mktemp("audio_pcm")
    source = work / "wrapper.c"
    source.write_text(WRAPPER, encoding="utf-8")
    out = work / ("pcm.dll" if sys.platform == "win32" else "pcm.so")
    args = [cc, "-O2", "-shared", "-ftrapv", "-o", str(out), str(source), f"-I{FW_MAIN}"]
    if sys.platform == "win32":
        args.append("-static-libgcc")
    else:
        args.insert(2, "-fPIC")
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    library = ctypes.CDLL(str(out))
    library.convert.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    return library


def convert(lib, raw):
    raw = np.ascontiguousarray(raw, np.int32)
    pcm = np.empty(len(raw), np.int16)
    magnitude = np.empty(len(raw), np.int32)
    lib.convert(raw.ctypes.data, pcm.ctypes.data, magnitude.ctypes.data, len(raw))
    return pcm, magnitude


def test_every_in_range_value_matches_old_shift(lib):
    """Za svaki int16 izlaz i oba ruba koraka od 2^14 rezultat je raw >> 14."""
    base = np.arange(-32768, 32768, dtype=np.int64) << 14
    raw = np.concatenate([base, base + (1 << 14) - 1]).astype(np.int32)
    pcm, _ = convert(lib, raw)
    np.testing.assert_array_equal(pcm, (raw.astype(np.int64) >> 14).astype(np.int16))


def test_out_of_range_saturates_instead_of_wrapping(lib):
    raw = np.array([32768 << 14, 100000 << 14, np.iinfo(np.int32).max,
                    (-32769) << 14, np.iinfo(np.int32).min], dtype=np.int64).astype(np.int32)
    pcm, _ = convert(lib, raw)
    np.testing.assert_array_equal(pcm, [32767, 32767, 32767, -32768, -32768])


def test_magnitude_is_defined_for_int32_min(lib):
    raw = np.array([0, 5, -5, np.iinfo(np.int32).max, np.iinfo(np.int32).min + 1,
                    np.iinfo(np.int32).min], dtype=np.int32)
    _, magnitude = convert(lib, raw)
    np.testing.assert_array_equal(magnitude, [0, 5, 5, 2**31 - 1, 2**31 - 1, 2**31 - 1])


def test_capture_uses_the_shared_conversion():
    source = (FW_MAIN / "audio_i2s.c").read_text(encoding="utf-8")
    assert "audio_pcm_from_raw(raw[i])" in source
    assert "audio_pcm_raw_magnitude(raw[i])" in source
    assert "(int16_t)(raw[i] >> 14)" not in source
