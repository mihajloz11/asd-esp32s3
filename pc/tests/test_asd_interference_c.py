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
    policy = Policy(1, 1, 1, 1.0, 0.5, long_hold)
    lib.asd_interference_init(ctypes.byref(gate), ctypes.byref(policy))
    return gate


def update(lib, gate: Gate, tonal: float, instability: float,
           *, high=True, alarm=False) -> int:
    observation = Observation(tonal, instability, high, alarm)
    return lib.asd_interference_update(ctypes.byref(gate), ctypes.byref(observation))


def test_default_policy_is_derived_and_never_leans_on_tonalness(lib) -> None:
    """Ukljucena politika mora nositi izvedenu granicu, ne izmisljenu nulu.

    Do v2 je ovaj test cuvao suprotno -- da je gate iskljucen dok granice ne
    postoje. Granice su 23.08.2026 izvedene iz 18 normal-only prozora, pa se
    cuva ono sto je sada opasno: da neko ukljuci politiku bez brojke, ili da
    vrati tonalnost u odluku (ona se pomjeri i na stvarnoj promjeni masine, pa
    bi gusila bas ono sto treba da se prijavi).
    """
    policy = lib.asd_interference_default_policy()
    assert policy.developmental == 1
    assert policy.enabled == 1
    assert policy.use_tonalness_delta == 0
    assert policy.max_subsegment_instability > 0.0
    assert policy.long_hold_windows > 0

    frozen = json.loads((ROOT / "pc" / "config" /
                         "asd_interference_policy_v2.json").read_text(encoding="utf-8"))
    assert frozen["target_anomalies_used_for_fit"] is False
    assert frozen["policy"]["use_tonalness_delta"] is False
    assert policy.max_subsegment_instability == pytest.approx(
        frozen["policy"]["max_subsegment_instability"], rel=1e-6)
    assert policy.max_abs_tonalness_delta == pytest.approx(
        frozen["policy"]["max_abs_tonalness_delta"], rel=1e-6)


def test_enabled_policy_without_any_bound_is_refused(lib) -> None:
    """Politika bez ijednog kriterijuma bi tiho propustala sve."""
    gate = Gate()
    empty = Policy(1, 1, 0, 0.0, 0.0, 3)
    lib.asd_interference_init(ctypes.byref(gate), ctypes.byref(empty))
    assert update(lib, gate, 9.0, 9.0) == INVALID


def test_tonalness_is_ignored_while_instability_still_decides(lib) -> None:
    """Sa iskljucenom tonalnoscu odluku nosi samo slaganje podsegmenata."""
    gate = Gate()
    policy = Policy(1, 1, 0, 1.0, 0.5, 3)
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

