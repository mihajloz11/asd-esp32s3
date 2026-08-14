"""Host tests for the Faza 4 temporal decision core (asd_temporal.c).

The central test is PC<->C parity: the C implementation must produce the
identical alarm sequence as run_rule() in derive_temporal_policy.py, which is
the reference the policy was derived with. If they ever diverge, the measured
false-alarm and latency numbers stop describing the shipped device.
"""
from __future__ import annotations

import ctypes
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "firmware" / "esp32s3_asd" / "main"
SRC = [MAIN / "asd_temporal.c"]
POLICY_JSON = ROOT / "pc" / "config" / "asd_temporal_policy_v1.json"

sys.path.insert(0, str(ROOT / "pc"))
from tools.derive_temporal_policy import Rule, run_rule  # noqa: E402


class Policy(ctypes.Structure):
    _fields_ = [("min_consecutive", ctypes.c_int),
                ("ewma_alpha", ctypes.c_float),
                ("enter_scale", ctypes.c_float),
                ("exit_scale", ctypes.c_float),
                ("cusum_k", ctypes.c_float),
                ("cusum_h", ctypes.c_float),
                ("fast_scale", ctypes.c_float)]


class Detector(ctypes.Structure):
    _fields_ = [("ewma", ctypes.c_float),
                ("ewma_valid", ctypes.c_int),
                ("run", ctypes.c_int),
                ("cusum", ctypes.c_float),
                ("active", ctypes.c_int),
                ("policy", Policy)]


@pytest.fixture(scope="module")
def lib(tmp_path_factory: pytest.TempPathFactory):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema host C kompajlera")
    out = tmp_path_factory.mktemp("temporal_c") / (
        "asd_temporal.dll" if sys.platform == "win32" else "asd_temporal.so")
    args = [cc, "-std=c99", "-O1", "-shared", "-fPIC", "-I", str(MAIN)]
    args += [str(p) for p in SRC] + ["-o", str(out), "-lm"]
    subprocess.run(args, check=True, capture_output=True, text=True)

    handle = ctypes.CDLL(str(out))
    handle.asd_temporal_default_policy.restype = Policy
    handle.asd_temporal_init.argtypes = [ctypes.POINTER(Detector),
                                         ctypes.POINTER(Policy)]
    handle.asd_temporal_reset.argtypes = [ctypes.POINTER(Detector)]
    handle.asd_temporal_update.argtypes = [ctypes.POINTER(Detector),
                                           ctypes.c_float, ctypes.c_float]
    handle.asd_temporal_update.restype = ctypes.c_int
    return handle


def make(lib, rule: Rule) -> Detector:
    det = Detector()
    policy = Policy(rule.min_consecutive, rule.ewma_alpha, rule.enter_scale,
                    rule.exit_scale, rule.cusum_k, rule.cusum_h, rule.fast_scale)
    lib.asd_temporal_init(ctypes.byref(det), ctypes.byref(policy))
    return det


def c_sequence(lib, rule: Rule, scores, threshold: float) -> list[int]:
    det = make(lib, rule)
    return [lib.asd_temporal_update(ctypes.byref(det), float(s), threshold)
            for s in scores]


# --- politika mora odgovarati onome sto je izvedeno -------------------------

def test_default_policy_matches_the_locked_json(lib):
    record = json.loads(POLICY_JSON.read_text(encoding="utf-8"))
    chosen = record["policy"]
    policy = lib.asd_temporal_default_policy()
    assert policy.min_consecutive == chosen["min_consecutive"]
    assert policy.ewma_alpha == pytest.approx(chosen["ewma_alpha"])
    assert policy.enter_scale == pytest.approx(chosen["enter_scale"])
    assert policy.exit_scale == pytest.approx(chosen["exit_scale"])
    assert policy.fast_scale == pytest.approx(chosen["fast_scale"])
    assert record["target_anomalies_used"] is False


def test_ewma_and_cusum_are_off_because_they_measured_worse(lib):
    """Nisu izostavljeni nego mjereni i odbaceni; nula je odluka, ne propust."""
    policy = lib.asd_temporal_default_policy()
    assert policy.ewma_alpha == 0.0
    assert policy.cusum_h == 0.0
    record = json.loads(POLICY_JSON.read_text(encoding="utf-8"))
    by_name = {row["rule"]: row for row in record["candidates"]}
    baseline = by_name["baseline_3_consecutive"]
    for worse in ("ewma_0.4_n3", "cusum_k0.5_h2"):
        assert by_name[worse]["short_spike_1_window_alarm_rate"] > \
               baseline["short_spike_1_window_alarm_rate"]


# --- PC <-> C parity --------------------------------------------------------

ALL_RULES = [
    Rule("baseline", min_consecutive=3),
    Rule("n2", min_consecutive=2),
    Rule("n4", min_consecutive=4),
    Rule("hyst", min_consecutive=3, exit_scale=0.7),
    Rule("ewma", min_consecutive=3, ewma_alpha=0.4),
    Rule("ewma_hyst", min_consecutive=3, ewma_alpha=0.4, exit_scale=0.7),
    Rule("cusum", min_consecutive=3, cusum_k=0.5, cusum_h=2.0),
    Rule("fast", min_consecutive=3, exit_scale=0.7, fast_scale=5.0),
]


@pytest.mark.parametrize("rule", ALL_RULES, ids=lambda r: r.name)
def test_c_matches_python_reference_on_random_streams(lib, rule):
    rng = np.random.default_rng(20260814)
    threshold = 1000.0
    for _ in range(20):
        scores = rng.lognormal(mean=6.5, sigma=0.9, size=120)
        expected = list(run_rule(rule, scores, threshold))
        assert c_sequence(lib, rule, scores, threshold) == expected


def test_c_matches_python_on_the_shipped_policy_and_a_sustained_shift(lib):
    rule = Rule("shipped", min_consecutive=3, exit_scale=0.7)
    threshold = 500.0
    scores = np.concatenate([
        np.full(10, 100.0), np.full(10, 900.0), np.full(10, 400.0),
        np.full(5, 360.0), np.full(10, 50.0),
    ])
    assert c_sequence(lib, rule, scores, threshold) == list(
        run_rule(rule, scores, threshold))


# --- ponasanje koje pravilo mora imati --------------------------------------

def test_three_consecutive_windows_are_required(lib):
    rule = Rule("shipped", min_consecutive=3, exit_scale=0.7)
    det = make(lib, rule)
    out = [lib.asd_temporal_update(ctypes.byref(det), s, 100.0)
           for s in (150.0, 150.0)]
    assert out == [0, 0]
    assert lib.asd_temporal_update(ctypes.byref(det), 150.0, 100.0) == 1


def test_single_window_spike_never_alarms(lib):
    """Govor, udarac, zalupljena vrata: jedan prozor ne smije podici alarm."""
    rule = Rule("shipped", min_consecutive=3, exit_scale=0.7)
    det = make(lib, rule)
    for score in (10.0, 10.0, 99999.0, 10.0, 10.0, 10.0):
        assert lib.asd_temporal_update(ctypes.byref(det), score, 100.0) == 0


def test_two_window_spike_never_alarms(lib):
    rule = Rule("shipped", min_consecutive=3, exit_scale=0.7)
    det = make(lib, rule)
    out = [lib.asd_temporal_update(ctypes.byref(det), s, 100.0)
           for s in (10.0, 5000.0, 5000.0, 10.0, 10.0)]
    assert out == [0, 0, 0, 0, 0]


def test_score_exactly_at_threshold_is_normal(lib):
    """Strogo vece, isto pravilo kao ranije u psd_live.c."""
    rule = Rule("shipped", min_consecutive=3, exit_scale=0.7)
    det = make(lib, rule)
    for _ in range(10):
        assert lib.asd_temporal_update(ctypes.byref(det), 100.0, 100.0) == 0


def test_hysteresis_holds_the_alarm_between_the_two_thresholds(lib):
    """Score koji visi tik ispod praga ne smije gasiti i paliti alarm."""
    rule = Rule("shipped", min_consecutive=3, exit_scale=0.7)
    det = make(lib, rule)
    for _ in range(3):
        lib.asd_temporal_update(ctypes.byref(det), 150.0, 100.0)
    assert det.active == 1
    # 0,7 * 100 = 70: izmedju izlaznog i ulaznog praga alarm OSTAJE
    for score in (95.0, 80.0, 71.0):
        assert lib.asd_temporal_update(ctypes.byref(det), score, 100.0) == 1
    # tek ispod izlaznog praga se gasi
    assert lib.asd_temporal_update(ctypes.byref(det), 69.0, 100.0) == 0


def test_baseline_without_hysteresis_would_flicker(lib):
    """Zasto je histereza uzeta: bez nje isti niz pali i gasi alarm."""
    plain = Rule("plain", min_consecutive=3, exit_scale=1.0)
    hyst = Rule("hyst", min_consecutive=3, exit_scale=0.7)
    scores = [150.0, 150.0, 150.0, 95.0, 150.0, 95.0, 150.0]
    plain_out = c_sequence(lib, plain, scores, 100.0)
    hyst_out = c_sequence(lib, hyst, scores, 100.0)
    assert plain_out == [0, 0, 1, 0, 0, 0, 0]
    assert hyst_out == [0, 0, 1, 1, 1, 1, 1]


def test_reset_clears_dynamics_but_keeps_policy(lib):
    rule = Rule("shipped", min_consecutive=3, exit_scale=0.7)
    det = make(lib, rule)
    for _ in range(3):
        lib.asd_temporal_update(ctypes.byref(det), 150.0, 100.0)
    assert det.active == 1
    lib.asd_temporal_reset(ctypes.byref(det))
    assert det.active == 0 and det.run == 0
    assert det.policy.min_consecutive == 3 and det.policy.exit_scale == pytest.approx(0.7)


def test_nonfinite_or_nonpositive_threshold_is_fail_closed(lib):
    rule = Rule("shipped", min_consecutive=3, exit_scale=0.7)
    det = make(lib, rule)
    for _ in range(3):
        lib.asd_temporal_update(ctypes.byref(det), 150.0, 100.0)
    assert det.active == 1
    assert lib.asd_temporal_update(ctypes.byref(det), float("nan"), 100.0) == 0
    assert det.active == 0
    for _ in range(3):
        lib.asd_temporal_update(ctypes.byref(det), 150.0, 100.0)
    assert lib.asd_temporal_update(ctypes.byref(det), 150.0, 0.0) == 0
    assert lib.asd_temporal_update(ctypes.byref(det), 150.0, float("inf")) == 0


def test_null_detector_is_fail_closed(lib):
    assert lib.asd_temporal_update(None, 999.0, 1.0) == 0
    lib.asd_temporal_reset(None)


def test_min_consecutive_is_clamped_to_at_least_one(lib):
    det = Detector()
    policy = Policy(0, 0.0, 1.0, 0.7, 0.0, 0.0, 0.0)
    lib.asd_temporal_init(ctypes.byref(det), ctypes.byref(policy))
    assert det.policy.min_consecutive == 1
    assert lib.asd_temporal_update(ctypes.byref(det), 150.0, 100.0) == 1


def test_default_init_uses_the_shipped_policy(lib):
    det = Detector()
    lib.asd_temporal_init(ctypes.byref(det), None)
    default = lib.asd_temporal_default_policy()
    assert det.policy.min_consecutive == default.min_consecutive
    assert det.policy.exit_scale == pytest.approx(default.exit_scale)
