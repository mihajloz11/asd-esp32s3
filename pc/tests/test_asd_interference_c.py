"""Host-C fixtures for Faza 6 observation HOLD policy."""
from __future__ import annotations

import ctypes
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
        ("max_abs_tonalness_delta", ctypes.c_float),
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
    handle.asd_interference_init.argtypes = [ctypes.POINTER(Gate), ctypes.POINTER(Policy)]
    handle.asd_interference_update.argtypes = [ctypes.POINTER(Gate), ctypes.POINTER(Observation)]
    handle.asd_interference_update.restype = ctypes.c_int
    return handle


def make_gate(lib, *, long_hold=3) -> Gate:
    gate = Gate()
    policy = Policy(1, 1, 1.0, 0.5, long_hold)
    lib.asd_interference_init(ctypes.byref(gate), ctypes.byref(policy))
    return gate


def update(lib, gate: Gate, tonal: float, instability: float,
           *, high=True, alarm=False) -> int:
    observation = Observation(tonal, instability, high, alarm)
    return lib.asd_interference_update(ctypes.byref(gate), ctypes.byref(observation))


def test_development_default_has_no_unvalidated_numeric_gate(lib) -> None:
    policy = lib.asd_interference_default_policy()
    assert policy.developmental == 1
    assert policy.enabled == 0


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

