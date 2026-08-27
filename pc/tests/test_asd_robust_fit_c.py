"""Host-C tests for normal-only robust centre and threshold fitting."""
from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "firmware" / "esp32s3_asd" / "main" / "asd_robust_fit.c"


class ThresholdFit(ctypes.Structure):
    _fields_ = [
        ("median", ctypes.c_float),
        ("mad", ctypes.c_float),
        ("robust_sigma", ctypes.c_float),
        ("percentile_ceiling", ctypes.c_float),
        ("threshold", ctypes.c_float),
        ("capped_high_windows", ctypes.c_uint32),
    ]


@pytest.fixture(scope="module")
def robust_lib(tmp_path_factory: pytest.TempPathFactory):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema host C kompajlera")
    out = tmp_path_factory.mktemp("robust_fit_c") / (
        "robust_fit.dll" if sys.platform == "win32" else "robust_fit.so"
    )
    args = [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-shared"]
    if sys.platform != "win32":
        args.append("-fPIC")
    args.extend(["-o", str(out), str(SRC)])
    if sys.platform != "win32":
        args.append("-lm")
    subprocess.run(args, check=True, capture_output=True, text=True)
    lib = ctypes.CDLL(str(out))
    fp = ctypes.POINTER(ctypes.c_float)
    lib.asd_robust_fit_center.argtypes = [
        fp, ctypes.c_size_t, ctypes.c_size_t, fp, fp,
        ctypes.c_float, fp, fp,
    ]
    lib.asd_robust_fit_center.restype = ctypes.c_int
    lib.asd_robust_fit_threshold.argtypes = [
        fp, ctypes.c_size_t, ctypes.c_float, ctypes.c_float,
        ctypes.POINTER(ThresholdFit), fp,
    ]
    lib.asd_robust_fit_threshold.restype = ctypes.c_int
    return lib


def floats(values):
    return (ctypes.c_float * len(values))(*values)


def test_threshold_caps_isolated_high_normal_windows_from_physical_run(
    robust_lib,
) -> None:
    scores = floats([
        413.275574, 3599.81665, 584.594482, 697.962158, 351.033264,
        405.779907, 463.03775, 622.526306, 330.205261, 480.435791,
        516.226135, 675.70282, 2905.31665, 659.35498, 593.063843,
        789.945435, 444.867676, 915.63385, 741.107605, 1056.13672,
        1108.729, 345.86319, 804.347717, 1373.66553, 1306.46204,
        1175.0625, 1997.59448, 867.195129, 568.313049, 693.27417,
        676.941956, 615.878113, 444.669373, 813.92157, 722.125793,
        1542.89587, 1187.36743, 659.693176, 829.459778, 773.358276,
        735.594604, 1047.86475, 2878.9585, 3410.08008,
    ])
    scratch = floats([0.0] * len(scores))
    fit = ThresholdFit()
    assert robust_lib.asd_robust_fit_threshold(
        scores, len(scores), 0.99, 3.0, ctypes.byref(fit), scratch,
    ) == 1
    assert fit.median == pytest.approx(728.8602, rel=1e-5)
    assert fit.mad == pytest.approx(230.52924, rel=1e-5)
    assert fit.percentile_ceiling == pytest.approx(3599.81665, rel=1e-5)
    assert fit.threshold == pytest.approx(1754.2081, rel=1e-5)
    assert fit.capped_high_windows == 5


def test_trimmed_center_ignores_each_band_extremes(robust_lib) -> None:
    # Redovi su prozori, kolone PSD trake. Po jedan ekstrem na oba kraja se
    # uklanja; preostala cetiri prozora odredjuju centar.
    features = floats([
        -100.0, 1000.0,
        10.0, 20.0,
        11.0, 22.0,
        12.0, 24.0,
        13.0, 26.0,
        500.0, -200.0,
    ])
    mean = floats([1.5, 3.0])
    std = floats([2.0, 4.0])
    center = floats([0.0, 0.0])
    scratch = floats([0.0] * 6)
    assert robust_lib.asd_robust_fit_center(
        features, 6, 2, mean, std, 0.2, center, scratch,
    ) == 1
    assert list(center) == pytest.approx([(11.5 - 1.5) / 2.0,
                                          (23.0 - 3.0) / 4.0])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0])
def test_threshold_fit_fails_closed_on_invalid_scores(robust_lib, bad) -> None:
    scores = floats([1.0, 2.0, bad, 4.0])
    scratch = floats([0.0] * 4)
    fit = ThresholdFit()
    assert robust_lib.asd_robust_fit_threshold(
        scores, 4, 0.99, 3.0, ctypes.byref(fit), scratch,
    ) == 0

