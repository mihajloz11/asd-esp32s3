"""E6 pre-validacija na PC-u: C gamma kalibracija (Welford + momentna metoda +
Wilson–Hilferty) protiv scipy reference. Kriterijum: prag unutar 2 % od
scipy gamma.ppf sa momentnim parametrima.
"""
from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "firmware" / "esp32s3_asd" / "main" / "calib_gamma.c"


class GammaCalib(ctypes.Structure):
    _fields_ = [("n", ctypes.c_int), ("mean", ctypes.c_double), ("m2", ctypes.c_double)]


@pytest.fixture(scope="module")
def clib(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("cbuild")
    out = tmp / ("calib.dll" if sys.platform == "win32" else "calib.so")
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema C kompajlera")
    args = [cc, "-O2", "-shared", "-o", str(out), str(SRC)]
    if sys.platform != "win32":
        args.append("-lm")
    subprocess.run(args, check=True)
    lib = ctypes.CDLL(str(out))
    lib.gamma_calib_threshold.restype = ctypes.c_float
    lib.gamma_calib_threshold.argtypes = [ctypes.POINTER(GammaCalib), ctypes.c_float]
    lib.gamma_calib_add.argtypes = [ctypes.POINTER(GammaCalib), ctypes.c_float]
    return lib


@pytest.mark.parametrize("k,theta", [(2.0, 0.5), (0.8, 3.0), (10.0, 0.01)])
def test_gamma_threshold_vs_scipy(clib, k, theta):
    rng = np.random.default_rng(7)
    scores = rng.gamma(k, theta, size=60).astype(np.float32)  # N=60 kao u planu 5.5

    c = GammaCalib()
    clib.gamma_calib_reset(ctypes.byref(c))
    for s in scores:
        clib.gamma_calib_add(ctypes.byref(c), ctypes.c_float(float(s)))
    thr_c = clib.gamma_calib_threshold(ctypes.byref(c), ctypes.c_float(0.9))

    m, v = scores.mean(), scores.var(ddof=1)
    k_mm, th_mm = m * m / v, v / m
    thr_ref = stats.gamma.ppf(0.9, k_mm, scale=th_mm)
    rel = abs(thr_c - thr_ref) / thr_ref
    print(f"k={k} theta={theta}: C={thr_c:.5f} scipy={thr_ref:.5f} rel={rel:.4%}")
    assert rel < 0.02


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-s"]))
