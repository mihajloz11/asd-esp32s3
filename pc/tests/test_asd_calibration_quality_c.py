"""Host-C parity and integration tests for the firmware K1 gate."""
from __future__ import annotations

import ctypes
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PC_DIR = ROOT / "pc"
if str(PC_DIR) not in sys.path:
    sys.path.insert(0, str(PC_DIR))

from asd.commissioning_policy import calibration_acceptance


SRC = ROOT / "firmware" / "esp32s3_asd" / "main" / "asd_calibration_quality.c"
LIVE_SRC = ROOT / "firmware" / "esp32s3_asd" / "main" / "psd_live.c"
POLICY_JSON = ROOT / "pc" / "config" / "asd_commissioning_policy_v1.json"

ACCEPTED = 0
INVALID_ARGUMENT = 1
NONFINITE = 2
NEGATIVE_METRIC = 3
UNSTABLE = 4


class Policy(ctypes.Structure):
    _fields_ = [("max_loo_cv", ctypes.c_float)]


class Metrics(ctypes.Structure):
    _fields_ = [
        ("loo_mean", ctypes.c_float),
        ("loo_sd", ctypes.c_float),
        ("loo_cv", ctypes.c_float),
        ("loo_range", ctypes.c_float),
    ]


@pytest.fixture(scope="module")
def calibration_lib(tmp_path_factory: pytest.TempPathFactory):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema host C kompajlera")
    out = tmp_path_factory.mktemp("calibration_quality_c") / (
        "calibration_quality.dll" if sys.platform == "win32"
        else "calibration_quality.so"
    )
    args = [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-shared"]
    if sys.platform != "win32":
        args.extend(["-fPIC"])
    args.extend(["-o", str(out), str(SRC)])
    if sys.platform != "win32":
        args.append("-lm")
    subprocess.run(args, check=True, capture_output=True, text=True)

    lib = ctypes.CDLL(str(out))
    lib.asd_calibration_quality_default_policy.restype = Policy
    lib.asd_calibration_quality_evaluate.argtypes = [
        ctypes.POINTER(Metrics), ctypes.POINTER(Policy),
    ]
    lib.asd_calibration_quality_evaluate.restype = ctypes.c_int
    lib.asd_calibration_quality_reason_name.argtypes = [ctypes.c_int]
    lib.asd_calibration_quality_reason_name.restype = ctypes.c_char_p
    lib.asd_calibration_quality_policy_protocol.restype = ctypes.c_char_p
    return lib


def evaluate(calibration_lib, value: float) -> int:
    metrics = Metrics(loo_mean=1.0, loo_sd=0.2, loo_cv=value, loo_range=0.5)
    policy = calibration_lib.asd_calibration_quality_default_policy()
    return calibration_lib.asd_calibration_quality_evaluate(
        ctypes.byref(metrics), ctypes.byref(policy),
    )


def test_c_policy_matches_versioned_pc_policy(calibration_lib) -> None:
    record = json.loads(POLICY_JSON.read_text(encoding="utf-8"))
    policy = calibration_lib.asd_calibration_quality_default_policy()
    assert calibration_lib.asd_calibration_quality_policy_protocol() == (
        record["schema_version"].encode("ascii")
    )
    assert policy.max_loo_cv == pytest.approx(record["calibration"]["max_loo_cv"])


def test_c_k1_exact_boundary_and_public_reason(calibration_lib) -> None:
    assert evaluate(calibration_lib, 0.600000) == ACCEPTED
    assert evaluate(calibration_lib, 0.600001) == UNSTABLE
    assert calibration_lib.asd_calibration_quality_reason_name(UNSTABLE) == (
        b"UNSTABLE_CALIBRATION"
    )


def test_c_k1_uses_the_same_six_decimal_value_emitted_on_uart(
    calibration_lib,
) -> None:
    for internal_value, expected_c in (
        (0.6000004, ACCEPTED),
        (0.6000006, UNSTABLE),
    ):
        c_result = evaluate(calibration_lib, internal_value)
        wire_value = float(f"{ctypes.c_float(internal_value).value:.6f}")
        pc_accepted, _ = calibration_acceptance({
            "cal_summary": {"loo_cv": wire_value},
        })
        assert c_result == expected_c
        assert (c_result == ACCEPTED) is pc_accepted


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_c_k1_nonfinite_fails_closed(calibration_lib, value: float) -> None:
    assert evaluate(calibration_lib, value) == NONFINITE


def test_c_k1_invalid_and_negative_inputs_fail_closed(calibration_lib) -> None:
    metrics = Metrics(loo_mean=1.0, loo_sd=0.2, loo_cv=0.2, loo_range=0.5)
    policy = calibration_lib.asd_calibration_quality_default_policy()
    assert calibration_lib.asd_calibration_quality_evaluate(
        None, ctypes.byref(policy),
    ) == INVALID_ARGUMENT
    policy.max_loo_cv = float("nan")
    assert calibration_lib.asd_calibration_quality_evaluate(
        ctypes.byref(metrics), ctypes.byref(policy),
    ) == INVALID_ARGUMENT
    policy = calibration_lib.asd_calibration_quality_default_policy()
    metrics.loo_cv = -0.1
    assert calibration_lib.asd_calibration_quality_evaluate(
        ctypes.byref(metrics), ctypes.byref(policy),
    ) == NEGATIVE_METRIC


def test_live_gate_precedes_threshold_acceptance_and_det() -> None:
    source = LIVE_SRC.read_text(encoding="utf-8")
    summary = source.index("phase=CAL_SUMMARY")
    gate = source.index("asd_calibration_quality_evaluate", summary)
    unstable_return = source.index("return stop_unstable_calibration", gate)
    threshold = source.index('printf("ADAPTTHR', gate)
    accepted = source.index('emit_state(state, ASD_STATE_CALIBRATED_NORMAL', gate)
    det_loop = source.index("/* --- 3) detekcija", gate)
    assert summary < gate < unstable_return < threshold < accepted < det_loop
