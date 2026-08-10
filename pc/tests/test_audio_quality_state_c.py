"""Host tests for the fail-closed audio quality/state core."""
from __future__ import annotations

import ctypes
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "firmware" / "esp32s3_asd" / "main" / "audio_quality_state.c"
POLICY_JSON = ROOT / "pc" / "config" / "asd_quality_policy_v1.json"


class Policy(ctypes.Structure):
    _fields_ = [
        ("level_floor_dbfs", ctypes.c_float),
        ("clip_level", ctypes.c_int32),
        ("max_clip_fraction", ctypes.c_float),
        ("max_zero_fraction", ctypes.c_float),
        ("max_stuck_fraction", ctypes.c_float),
    ]


class Accumulator(ctypes.Structure):
    _fields_ = [
        ("expected_samples", ctypes.c_uint32),
        ("sample_count", ctypes.c_uint32),
        ("sum", ctypes.c_double),
        ("sumsq", ctypes.c_double),
        ("peak", ctypes.c_int32),
        ("clipped_count", ctypes.c_uint32),
        ("zero_count", ctypes.c_uint32),
        ("stuck_count", ctypes.c_uint32),
        ("previous", ctypes.c_int16),
        ("has_previous", ctypes.c_uint8),
        ("dropped_before", ctypes.c_uint32),
        ("clip_level", ctypes.c_int32),
    ]


class Metrics(ctypes.Structure):
    _fields_ = [
        ("expected_samples", ctypes.c_uint32),
        ("sample_count", ctypes.c_uint32),
        ("dc", ctypes.c_float),
        ("rms", ctypes.c_float),
        ("rms_dbfs", ctypes.c_float),
        ("peak", ctypes.c_int32),
        ("clipped_count", ctypes.c_uint32),
        ("zero_count", ctypes.c_uint32),
        ("stuck_count", ctypes.c_uint32),
        ("dropped_delta", ctypes.c_uint32),
    ]


OK = 0
SHORT_READ = 1
NONFINITE = 2
STUCK_SIGNAL = 3
LOW_LEVEL = 4
INSUFFICIENT_LEVEL = 5
CLIPPING = 6
DROPPED_SAMPLES = 7
INVALID_ARGUMENT = 8
FLOW_CONTINUE = 0
FLOW_STOP = 1
PHASE_WAIT = 0
PHASE_CAL = 1
PHASE_DET = 2


@pytest.fixture(scope="module")
def quality_lib(tmp_path_factory: pytest.TempPathFactory):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema host C kompajlera")
    out = tmp_path_factory.mktemp("quality_c") / (
        "quality.dll" if sys.platform == "win32" else "quality.so"
    )
    args = [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-shared"]
    if sys.platform != "win32":
        args.extend(["-fPIC"])
    args.extend(["-o", str(out), str(SRC)])
    if sys.platform != "win32":
        args.append("-lm")
    subprocess.run(args, check=True, capture_output=True, text=True)
    lib = ctypes.CDLL(str(out))
    lib.asd_quality_default_policy.restype = Policy
    lib.asd_quality_reset.argtypes = [
        ctypes.POINTER(Accumulator), ctypes.c_uint32, ctypes.c_uint32,
        ctypes.POINTER(Policy),
    ]
    lib.asd_quality_add_pcm.argtypes = [
        ctypes.POINTER(Accumulator), ctypes.POINTER(ctypes.c_int16), ctypes.c_size_t,
    ]
    lib.asd_quality_finish.argtypes = [
        ctypes.POINTER(Accumulator), ctypes.c_uint32, ctypes.POINTER(Metrics),
    ]
    lib.asd_quality_evaluate.argtypes = [ctypes.POINTER(Metrics), ctypes.POINTER(Policy)]
    lib.asd_quality_evaluate.restype = ctypes.c_int
    lib.asd_quality_flow_action.argtypes = [ctypes.c_int, ctypes.c_int]
    lib.asd_quality_flow_action.restype = ctypes.c_int
    lib.asd_quality_reject_state.argtypes = [ctypes.c_int, ctypes.c_int]
    lib.asd_quality_reject_state.restype = ctypes.c_int
    lib.asd_quality_floats_finite.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_size_t]
    lib.asd_quality_floats_finite.restype = ctypes.c_int
    lib.asd_quality_reason_name.argtypes = [ctypes.c_int]
    lib.asd_quality_reason_name.restype = ctypes.c_char_p
    lib.asd_state_name.argtypes = [ctypes.c_int]
    lib.asd_state_name.restype = ctypes.c_char_p
    return lib


def evaluate_pcm(quality_lib, samples: list[int], *, expected: int | None = None,
                 dropped_before: int = 0, dropped_after: int = 0):
    policy = quality_lib.asd_quality_default_policy()
    acc = Accumulator()
    expected = len(samples) if expected is None else expected
    quality_lib.asd_quality_reset(
        ctypes.byref(acc), expected, dropped_before, ctypes.byref(policy),
    )
    pcm = (ctypes.c_int16 * len(samples))(*samples)
    quality_lib.asd_quality_add_pcm(ctypes.byref(acc), pcm, len(samples))
    metrics = Metrics()
    quality_lib.asd_quality_finish(ctypes.byref(acc), dropped_after, ctypes.byref(metrics))
    reason = quality_lib.asd_quality_evaluate(ctypes.byref(metrics), ctypes.byref(policy))
    return reason, metrics, policy


def test_default_policy_matches_versioned_normal_only_record(quality_lib) -> None:
    raw = json.loads(POLICY_JSON.read_text(encoding="utf-8"))
    assert raw["target_anomalies_used"] is False
    assert set(raw["pending_normal_only_gates"]) == {"tonalness", "loo_spread"}
    policy = quality_lib.asd_quality_default_policy()
    locked = raw["policy"]
    assert policy.level_floor_dbfs == locked["level_floor_dbfs"]
    assert policy.clip_level == locked["clip_level_pcm16"]
    assert policy.max_clip_fraction == pytest.approx(locked["max_clip_fraction"])
    assert policy.max_zero_fraction == pytest.approx(locked["max_zero_fraction"])
    assert policy.max_stuck_fraction == pytest.approx(locked["max_stuck_fraction"])


def test_valid_normal_pcm_passes_and_metrics_match(quality_lib) -> None:
    samples = [-1000, 1000] * 500
    reason, metrics, _ = evaluate_pcm(quality_lib, samples)
    assert reason == OK
    assert metrics.sample_count == metrics.expected_samples == 1000
    assert metrics.dc == pytest.approx(0.0)
    assert metrics.rms == pytest.approx(1000.0)
    assert metrics.rms_dbfs == pytest.approx(20 * math.log10(1000 / 32768), abs=1e-5)
    assert metrics.peak == 1000
    assert metrics.clipped_count == metrics.zero_count == metrics.stuck_count == 0


@pytest.mark.parametrize(
    ("samples", "expected", "dropped_before", "dropped_after", "want"),
    [
        ([-1000, 1000] * 499, 1000, 0, 0, SHORT_READ),
        ([0] * 1000, 1000, 0, 0, STUCK_SIGNAL),
        ([123] * 1000, 1000, 0, 0, STUCK_SIGNAL),
        ([-1, 1] * 500, 1000, 0, 0, LOW_LEVEL),
        ([32000, -32000] + [-1000, 1000] * 499, 1000, 0, 0, CLIPPING),
        ([-1000, 1000] * 500, 1000, 20, 21, DROPPED_SAMPLES),
    ],
)
def test_pcm_reject_fixtures_are_fail_closed(
    quality_lib, samples, expected, dropped_before, dropped_after, want,
) -> None:
    reason, _, _ = evaluate_pcm(
        quality_lib, samples, expected=expected,
        dropped_before=dropped_before, dropped_after=dropped_after,
    )
    assert reason == want
    phase = PHASE_CAL if reason == LOW_LEVEL else PHASE_WAIT
    assert quality_lib.asd_quality_flow_action(reason, phase) == FLOW_STOP


@pytest.mark.parametrize("field", ["dc", "rms", "rms_dbfs"])
def test_nonfinite_metrics_are_sensor_fault_and_stop(quality_lib, field: str) -> None:
    reason, metrics, policy = evaluate_pcm(quality_lib, [-1000, 1000] * 500)
    assert reason == OK
    setattr(metrics, field, float("nan") if field != "rms" else float("inf"))
    reason = quality_lib.asd_quality_evaluate(ctypes.byref(metrics), ctypes.byref(policy))
    assert reason == NONFINITE
    assert quality_lib.asd_quality_flow_action(reason, PHASE_CAL) == FLOW_STOP
    assert quality_lib.asd_state_name(
        quality_lib.asd_quality_reject_state(reason, PHASE_CAL)
    ) == b"SENSOR_ERROR"


def test_feature_nonfinite_guard(quality_lib) -> None:
    values = (ctypes.c_float * 3)(1.0, 2.0, 3.0)
    assert quality_lib.asd_quality_floats_finite(values, 3) == 1
    values[1] = float("nan")
    assert quality_lib.asd_quality_floats_finite(values, 3) == 0


def test_only_ok_can_continue_and_public_tokens_are_stable(quality_lib) -> None:
    assert quality_lib.asd_quality_flow_action(OK, PHASE_CAL) == FLOW_CONTINUE
    reasons = [
        "OK", "SHORT_READ", "NONFINITE", "STUCK_SIGNAL",
        "LOW_LEVEL_OBSERVATION", "INSUFFICIENT_LEVEL", "CLIPPING",
        "DROPPED_SAMPLES", "INVALID_ARGUMENT",
    ]
    for index, expected in enumerate(reasons):
        assert quality_lib.asd_quality_reason_name(index).decode("ascii") == expected
        if index not in {OK, LOW_LEVEL}:
            assert quality_lib.asd_quality_flow_action(index, PHASE_WAIT) == FLOW_STOP
    states = [
        "NO_MACHINE", "CALIBRATION_REJECTED", "CALIBRATED_NORMAL",
        "ANOMALY", "SENSOR_ERROR", "RECALIBRATION_REQUIRED",
    ]
    assert [quality_lib.asd_state_name(i).decode("ascii") for i in range(6)] == states


def test_low_level_is_observation_only_during_wait(quality_lib) -> None:
    assert quality_lib.asd_quality_flow_action(LOW_LEVEL, PHASE_WAIT) == FLOW_CONTINUE
    assert quality_lib.asd_quality_flow_action(LOW_LEVEL, PHASE_CAL) == FLOW_STOP
    assert quality_lib.asd_quality_flow_action(LOW_LEVEL, PHASE_DET) == FLOW_STOP
    assert quality_lib.asd_quality_flow_action(INSUFFICIENT_LEVEL, PHASE_WAIT) == FLOW_STOP
    assert quality_lib.asd_state_name(
        quality_lib.asd_quality_reject_state(INSUFFICIENT_LEVEL, PHASE_WAIT)
    ) == b"NO_MACHINE"


def test_clip_level_is_owned_by_validated_policy(quality_lib) -> None:
    policy = quality_lib.asd_quality_default_policy()
    policy.clip_level = 1000
    acc = Accumulator()
    quality_lib.asd_quality_reset(ctypes.byref(acc), 4, 0, ctypes.byref(policy))
    pcm = (ctypes.c_int16 * 4)(-999, 999, -1000, 1000)
    quality_lib.asd_quality_add_pcm(ctypes.byref(acc), pcm, 4)
    assert acc.clip_level == 1000
    assert acc.clipped_count == 2

    metrics = Metrics(
        expected_samples=4, sample_count=4, dc=0.0, rms=1000.0,
        rms_dbfs=-30.0, peak=1000, clipped_count=0, zero_count=0,
        stuck_count=0, dropped_delta=0,
    )
    for invalid_clip in (0, -1, 32769, -(2**31)):
        policy.clip_level = invalid_clip
        assert quality_lib.asd_quality_evaluate(
            ctypes.byref(metrics), ctypes.byref(policy)
        ) == INVALID_ARGUMENT


def test_phase_specific_stop_state_integration(quality_lib) -> None:
    assert quality_lib.asd_state_name(
        quality_lib.asd_quality_reject_state(LOW_LEVEL, PHASE_CAL)
    ) == b"NO_MACHINE"
    assert quality_lib.asd_state_name(
        quality_lib.asd_quality_reject_state(CLIPPING, PHASE_CAL)
    ) == b"CALIBRATION_REJECTED"
    assert quality_lib.asd_state_name(
        quality_lib.asd_quality_reject_state(CLIPPING, PHASE_DET)
    ) == b"RECALIBRATION_REQUIRED"
