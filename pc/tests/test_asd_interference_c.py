"""Host-C fixtures for Faza 6 observation HOLD policy."""
from __future__ import annotations

import ctypes
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "firmware" / "esp32s3_asd" / "main"
PASS, HOLD, WARNING, INVALID = range(4)


class Policy(ctypes.Structure):
    _fields_ = [
        ("enabled", ctypes.c_int),
        ("developmental", ctypes.c_int),
        ("use_tonalness_delta", ctypes.c_int),
        ("max_abs_tonalness_delta", ctypes.c_float),
        ("normal_max_multiplier", ctypes.c_float),
        ("calibration_min_windows", ctypes.c_uint32),
        ("max_subsegment_instability", ctypes.c_float),
        ("long_hold_windows", ctypes.c_uint32),
    ]


class Observation(ctypes.Structure):
    _fields_ = [
        ("tonalness_delta", ctypes.c_float),
        ("subsegment_instability", ctypes.c_float),
        ("score_high", ctypes.c_int),
        ("alarm_active", ctypes.c_int),
    ]


class Gate(ctypes.Structure):
    _fields_ = [
        ("policy", Policy),
        ("hold_windows", ctypes.c_uint32),
        ("hold_active", ctypes.c_int),
        ("warning_emitted", ctypes.c_int),
    ]


@pytest.fixture(scope="module")
def lib(tmp_path_factory: pytest.TempPathFactory):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema host C kompajlera")
    suffix = "dll" if sys.platform == "win32" else "so"
    output = tmp_path_factory.mktemp("interference_c") / f"interference.{suffix}"
    subprocess.run(
        [cc, "-std=c99", "-O1", "-shared", "-fPIC", "-I", str(MAIN),
         str(MAIN / "asd_interference.c"), "-o", str(output), "-lm"],
        check=True, capture_output=True, text=True,
    )
    handle = ctypes.CDLL(str(output))
    handle.asd_interference_default_policy.restype = Policy
    handle.asd_interference_calibrate_normal.argtypes = [
        ctypes.POINTER(Policy), ctypes.c_float, ctypes.c_uint32,
    ]
    handle.asd_interference_calibrate_normal.restype = ctypes.c_int
    handle.asd_interference_init.argtypes = [ctypes.POINTER(Gate), ctypes.POINTER(Policy)]
    handle.asd_interference_update.argtypes = [ctypes.POINTER(Gate), ctypes.POINTER(Observation)]
    handle.asd_interference_update.restype = ctypes.c_int
    return handle


def make_gate(lib, *, long_hold=3) -> Gate:
    gate = Gate()
    policy = Policy(1, 1, 1, 1.0, 1.25, 10, 0.5, long_hold)
    lib.asd_interference_init(ctypes.byref(gate), ctypes.byref(policy))
    return gate


def update(lib, gate: Gate, tonal: float, instability: float,
           *, high=True, alarm=False) -> int:
    observation = Observation(tonal, instability, high, alarm)
    return lib.asd_interference_update(ctypes.byref(gate), ctypes.byref(observation))


def test_default_policy_requires_per_session_normal_calibration(lib) -> None:
    """V3 nosi pravilo, ali namjerno ne prenosi apsolutni prag drugog setapa."""
    policy = lib.asd_interference_default_policy()
    assert policy.developmental == 1
    assert policy.enabled == 1
    assert policy.use_tonalness_delta == 0
    assert policy.max_subsegment_instability == 0.0
    assert policy.normal_max_multiplier > 1.0
    assert policy.calibration_min_windows == 10
    assert policy.long_hold_windows > 0

    frozen = json.loads((ROOT / "pc" / "config" /
                         "asd_interference_policy_v3.json").read_text(encoding="utf-8"))
    assert frozen["target_anomalies_used_for_fit"] is False
    assert frozen["policy"]["use_tonalness_delta"] is False
    assert policy.normal_max_multiplier == pytest.approx(
        frozen["policy"]["normal_max_multiplier"], rel=1e-6)
    assert policy.max_abs_tonalness_delta == pytest.approx(
        frozen["policy"]["max_abs_tonalness_delta"], rel=1e-6)


def test_runtime_threshold_uses_only_normal_max_and_frozen_multiplier(lib) -> None:
    policy = lib.asd_interference_default_policy()
    assert lib.asd_interference_calibrate_normal(
        ctypes.byref(policy), ctypes.c_float(1.4651615), 10,
    ) == 1
    assert policy.max_subsegment_instability == pytest.approx(1.8314519, rel=1e-6)


@pytest.mark.parametrize("normal_max,windows", [
    (1.0, 9), (0.0, 10), (float("nan"), 10), (float("inf"), 10),
])
def test_runtime_threshold_fails_closed_on_bad_normal_calibration(
    lib, normal_max, windows,
) -> None:
    policy = lib.asd_interference_default_policy()
    assert lib.asd_interference_calibrate_normal(
        ctypes.byref(policy), ctypes.c_float(normal_max), windows,
    ) == 0
    gate = Gate()
    lib.asd_interference_init(ctypes.byref(gate), ctypes.byref(policy))
    assert update(lib, gate, 0.0, 0.1) == INVALID


def test_enabled_policy_without_any_bound_is_refused(lib) -> None:
    """Politika bez ijednog kriterijuma bi tiho propustala sve."""
    gate = Gate()
    empty = Policy(1, 1, 0, 0.0, 1.25, 10, 0.0, 3)
    lib.asd_interference_init(ctypes.byref(gate), ctypes.byref(empty))
    assert update(lib, gate, 9.0, 9.0) == INVALID


def test_tonalness_is_ignored_while_instability_still_decides(lib) -> None:
    """Sa iskljucenom tonalnoscu odluku nosi samo slaganje podsegmenata."""
    gate = Gate()
    policy = Policy(1, 1, 0, 1.0, 1.25, 10, 0.5, 3)
    lib.asd_interference_init(ctypes.byref(gate), ctypes.byref(policy))
    # Ogromno odstupanje tonalnosti, ali slozni podsegmenti -> prolazi u alarm.
    assert update(lib, gate, 9.0, 0.1) == PASS
    # Mirna tonalnost, razidjeni podsegmenti -> nepouzdan prozor.
    assert update(lib, gate, 0.0, 0.9) == HOLD


def test_unreliable_high_observation_holds_then_warns(lib) -> None:
    gate = make_gate(lib, long_hold=3)
    assert update(lib, gate, 2.0, 0.1) == HOLD
    assert update(lib, gate, 2.0, 0.1) == HOLD
    assert update(lib, gate, 2.0, 0.1) == WARNING
    assert gate.warning_emitted == 1


def test_stable_high_after_hold_passes_and_starts_fresh(lib) -> None:
    gate = make_gate(lib)
    assert update(lib, gate, 2.0, 0.1) == HOLD
    assert gate.hold_windows == 1
    assert update(lib, gate, 0.2, 0.2) == PASS
    assert (gate.hold_windows, gate.hold_active) == (0, 0)


def test_low_score_never_gets_mislabeled_as_interference(lib) -> None:
    gate = make_gate(lib)
    assert update(lib, gate, 9.0, 9.0, high=False) == PASS


def test_frozen_normal_only_rule_regresses_both_physical_setups(lib) -> None:
    """Target uslovi su samo readout poslije fita; ne mijenjaju mnozilac 1.25.

    Brojevi su nezavisno ponovljena firmware mjera iz runova 23.08. i 26.08.
    Prag se u obje grane racuna iskljucivo iz odgovarajuceg CAL maksimuma.
    """
    runs = [
        {
            "cal_max": 1.1201398,
            "papers": [
                [1.1257, 2.7942, 1.0216, 1.0897, 1.0412],
                [1.0020, 2.7434, 1.0715, 1.0234, 1.0562],
                [0.8096, 5.0025, 0.9443, 1.0370, 0.9022],
            ],
            "speech": [1.6278, 3.0612, 2.1760, 1.8890, 1.8470],
            "door_peak": 7.8095,
        },
        {
            "cal_max": 1.4651615,
            "papers": [
                [2.1298, 1.3276, 1.5117, 1.4165, 1.6392],
                [1.9991, 1.5887, 1.9621, 1.8602, 1.3256],
                [2.5136, 1.8618, 1.6076, 1.7506, 1.3605],
            ],
            "speech": [3.3681, 3.3540, 2.8902, 3.2153, 3.1507],
            "door_peak": 8.2583,
        },
    ]
    for run in runs:
        policy = lib.asd_interference_default_policy()
        assert lib.asd_interference_calibrate_normal(
            ctypes.byref(policy), ctypes.c_float(run["cal_max"]), 10,
        ) == 1
        assert policy.max_subsegment_instability == pytest.approx(
            run["cal_max"] * 1.25, rel=1e-6,
        )
        passing_papers = 0
        for block in run["papers"]:
            longest = current = 0
            for value in block:
                if value <= policy.max_subsegment_instability:
                    current += 1
                    longest = max(longest, current)
                else:
                    current = 0
            passing_papers += longest >= 3
        assert passing_papers >= 2
        assert all(value > policy.max_subsegment_instability
                   for value in run["speech"])
        assert run["door_peak"] > policy.max_subsegment_instability

