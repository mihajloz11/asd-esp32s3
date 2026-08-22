"""Host-C fixtures for Faza 5 commissioning and runtime profile contracts."""
from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "firmware" / "esp32s3_asd" / "main"
SRC = [MAIN / "asd_profile_runtime.c", MAIN / "asd_commissioning.c"]

IDLE, SETTLE, CENTER, DERIVE, VERIFY, MONITORING, REJECTED, ABORTED = range(8)
REJECT_NONE, REJECT_TIMEOUT, REJECT_QUALITY, REJECT_UNSTABLE, REJECT_K1, REJECT_PROFILE, REJECT_VERIFY, REJECT_TRANSITION, REJECT_ABORT = range(9)


class Profile(ctypes.Structure):
    _fields_ = [
        ("valid", ctypes.c_int),
        ("developmental", ctypes.c_int),
        ("center", ctypes.c_float * 96),
        ("level_mean_dbfs", ctypes.c_float),
        ("tonalness_reference", ctypes.c_float),
        ("threshold_enter", ctypes.c_float),
        ("threshold_exit", ctypes.c_float),
        ("center_windows", ctypes.c_uint32),
        ("derive_windows", ctypes.c_uint32),
        ("verify_windows", ctypes.c_uint32),
        ("policy_version", ctypes.c_uint32),
        ("policy_id", ctypes.c_uint32),
    ]


class Policy(ctypes.Structure):
    _fields_ = [
        ("min_settle_windows", ctypes.c_uint32),
        ("stable_settle_windows", ctypes.c_uint32),
        ("max_settle_windows", ctypes.c_uint32),
        ("center_windows", ctypes.c_uint32),
        ("derive_windows", ctypes.c_uint32),
        ("verify_windows", ctypes.c_uint32),
        ("settle_timeout_ms", ctypes.c_uint32),
        ("center_timeout_ms", ctypes.c_uint32),
        ("derive_timeout_ms", ctypes.c_uint32),
        ("verify_timeout_ms", ctypes.c_uint32),
        ("max_level_step_db", ctypes.c_float),
        ("max_tonalness_step", ctypes.c_float),
        ("max_feature_drift", ctypes.c_float),
        ("max_verify_episodes", ctypes.c_uint32),
        ("max_verify_alarm_windows", ctypes.c_uint32),
        ("max_verify_chatter", ctypes.c_uint32),
        ("verify_min_consecutive", ctypes.c_uint32),
        ("developmental", ctypes.c_int),
    ]


class Flow(ctypes.Structure):
    _fields_ = [
        ("phase", ctypes.c_int),
        ("reject_reason", ctypes.c_int),
        ("policy", Policy),
        ("phase_started_ms", ctypes.c_uint32),
        ("phase_windows", ctypes.c_uint32),
        ("settle_windows", ctypes.c_uint32),
        ("stable_run", ctypes.c_uint32),
        ("previous_level_dbfs", ctypes.c_float),
        ("previous_tonalness", ctypes.c_float),
        ("previous_settle_valid", ctypes.c_int),
        ("center_ready", ctypes.c_int),
        ("derive_ready", ctypes.c_int),
        ("verify_high_run", ctypes.c_uint32),
        ("verify_alarm_windows", ctypes.c_uint32),
        ("verify_episodes", ctypes.c_uint32),
        ("verify_chatter", ctypes.c_uint32),
        ("verify_active", ctypes.c_int),
        ("verify_had_exit", ctypes.c_int),
    ]


class SettleObservation(ctypes.Structure):
    _fields_ = [
        ("quality_ok", ctypes.c_int),
        ("level_dbfs", ctypes.c_float),
        ("tonalness", ctypes.c_float),
        ("feature_drift", ctypes.c_float),
        ("dropped_delta", ctypes.c_uint32),
    ]


@pytest.fixture(scope="module")
def lib(tmp_path_factory: pytest.TempPathFactory):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema host C kompajlera")
    suffix = "dll" if sys.platform == "win32" else "so"
    output = tmp_path_factory.mktemp("commissioning_c") / f"commissioning.{suffix}"
    command = [cc, "-std=c99", "-O1", "-shared", "-fPIC", "-I", str(MAIN)]
    command += [str(path) for path in SRC] + ["-o", str(output), "-lm"]
    subprocess.run(command, check=True, capture_output=True, text=True)
    handle = ctypes.CDLL(str(output))
    handle.asd_commission_default_policy.restype = Policy
    handle.asd_commission_profile_persistence_allowed.argtypes = [
        ctypes.POINTER(Policy),
    ]
    handle.asd_commission_profile_persistence_allowed.restype = ctypes.c_int
    handle.asd_commission_init.argtypes = [ctypes.POINTER(Flow), ctypes.POINTER(Policy)]
    handle.asd_commission_start.argtypes = [ctypes.POINTER(Flow), ctypes.c_uint32]
    handle.asd_commission_start.restype = ctypes.c_int
    handle.asd_commission_poll.argtypes = [ctypes.POINTER(Flow), ctypes.c_uint32]
    handle.asd_commission_poll.restype = ctypes.c_int
    handle.asd_commission_abort.argtypes = [ctypes.POINTER(Flow)]
    handle.asd_commission_observe_settle.argtypes = [
        ctypes.POINTER(Flow), ctypes.c_uint32, ctypes.POINTER(SettleObservation),
    ]
    handle.asd_commission_observe_settle.restype = ctypes.c_int
    handle.asd_commission_record_center.argtypes = [ctypes.POINTER(Flow), ctypes.c_uint32, ctypes.c_int]
    handle.asd_commission_record_center.restype = ctypes.c_int
    handle.asd_commission_commit_center.argtypes = [
        ctypes.POINTER(Flow), ctypes.c_uint32, ctypes.POINTER(Profile),
        ctypes.POINTER(ctypes.c_float), ctypes.c_float, ctypes.c_float, ctypes.c_int,
    ]
    handle.asd_commission_commit_center.restype = ctypes.c_int
    handle.asd_commission_record_derive.argtypes = [
        ctypes.POINTER(Flow), ctypes.c_uint32, ctypes.c_float, ctypes.c_int,
    ]
    handle.asd_commission_record_derive.restype = ctypes.c_int
    handle.asd_commission_freeze_thresholds.argtypes = [
        ctypes.POINTER(Flow), ctypes.c_uint32, ctypes.POINTER(Profile),
        ctypes.c_float, ctypes.c_float,
    ]
    handle.asd_commission_freeze_thresholds.restype = ctypes.c_int
    handle.asd_commission_record_verify.argtypes = [
        ctypes.POINTER(Flow), ctypes.c_uint32, ctypes.POINTER(Profile),
        ctypes.c_float, ctypes.c_int,
    ]
    handle.asd_commission_record_verify.restype = ctypes.c_int
    handle.asd_profile_runtime_validate.argtypes = [ctypes.POINTER(Profile), ctypes.c_int]
    handle.asd_profile_runtime_validate.restype = ctypes.c_int
    return handle


def test_preregistered_default_is_20_min_derive_10_min_verify_and_ram_only(lib) -> None:
    policy = lib.asd_commission_default_policy()
    assert (policy.derive_windows, policy.verify_windows) == (120, 60)
    assert policy.derive_timeout_ms >= 120 * 10_000
    assert policy.verify_timeout_ms >= 60 * 10_000
    assert policy.developmental == 1
    assert lib.asd_commission_profile_persistence_allowed(
        ctypes.byref(policy),
    ) == 0
    policy.developmental = 0
    # Compile-time gate is still closed in the DEVELOPMENT build.
    assert lib.asd_commission_profile_persistence_allowed(
        ctypes.byref(policy),
    ) == 0


def test_persistence_opt_in_still_requires_a_frozen_runtime_policy(tmp_path: Path) -> None:
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema host C kompajlera")
    suffix = "dll" if sys.platform == "win32" else "so"
    output = tmp_path / f"commissioning_persistence_opt_in.{suffix}"
    command = [
        cc, "-std=c99", "-O1", "-shared", "-fPIC",
        "-DASD_PROFILE_PERSISTENCE_ALLOWED=1", "-I", str(MAIN),
        *[str(path) for path in SRC], "-o", str(output), "-lm",
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    handle = ctypes.CDLL(str(output))
    handle.asd_commission_default_policy.restype = Policy
    handle.asd_commission_profile_persistence_allowed.argtypes = [
        ctypes.POINTER(Policy),
    ]
    handle.asd_commission_profile_persistence_allowed.restype = ctypes.c_int
    policy = handle.asd_commission_default_policy()
    assert handle.asd_commission_profile_persistence_allowed(
        ctypes.byref(policy),
    ) == 0
    policy.developmental = 0
    assert handle.asd_commission_profile_persistence_allowed(
        ctypes.byref(policy),
    ) == 1


def small_policy(lib, *, verify_min=2, max_episodes=0) -> Policy:
    policy = lib.asd_commission_default_policy()
    policy.min_settle_windows = 3
    policy.stable_settle_windows = 2
    policy.max_settle_windows = 6
    policy.center_windows = 2
    policy.derive_windows = 2
    policy.verify_windows = 3
    policy.settle_timeout_ms = 100
    policy.center_timeout_ms = 100
    policy.derive_timeout_ms = 100
    policy.verify_timeout_ms = 100
    policy.verify_min_consecutive = verify_min
    policy.max_verify_episodes = max_episodes
    return policy


def reach_center(lib, policy: Policy) -> Flow:
    flow = Flow()
    lib.asd_commission_init(ctypes.byref(flow), ctypes.byref(policy))
    assert lib.asd_commission_start(ctypes.byref(flow), 0) == 1
    for now, level, tonal, drift in [
        (1, -30.0, 2.0, 0.2),
        (2, -29.9, 2.1, 0.2),
        (3, -29.8, 2.1, 0.2),
    ]:
        observation = SettleObservation(1, level, tonal, drift, 0)
        assert lib.asd_commission_observe_settle(
            ctypes.byref(flow), now, ctypes.byref(observation),
        ) == 1
    assert flow.phase == CENTER
    return flow


def test_full_flow_freezes_center_and_thresholds_before_verify(lib) -> None:
    policy = small_policy(lib)
    flow = reach_center(lib, policy)
    profile = Profile()
    center = (ctypes.c_float * 96)(*[index / 100.0 for index in range(96)])
    assert lib.asd_commission_record_center(ctypes.byref(flow), 4, 1) == 1
    assert lib.asd_commission_record_center(ctypes.byref(flow), 5, 1) == 1
    assert flow.center_ready == 1
    assert lib.asd_commission_commit_center(
        ctypes.byref(flow), 6, ctypes.byref(profile), center, -30.0, 2.0, 1,
    ) == 1
    assert flow.phase == DERIVE and profile.valid == 0
    assert lib.asd_commission_record_derive(ctypes.byref(flow), 7, 4.0, 1) == 1
    assert lib.asd_commission_record_derive(ctypes.byref(flow), 8, 6.0, 1) == 1
    assert flow.derive_ready == 1
    assert lib.asd_commission_freeze_thresholds(
        ctypes.byref(flow), 9, ctypes.byref(profile), 10.0, 5.0,
    ) == 1
    assert flow.phase == VERIFY
    frozen_center = list(profile.center)
    frozen_thresholds = profile.threshold_enter, profile.threshold_exit
    for now, score in [(10, 3.0), (11, 4.0), (12, 2.0)]:
        assert lib.asd_commission_record_verify(
            ctypes.byref(flow), now, ctypes.byref(profile), score, 1,
        ) == 1
    assert flow.phase == MONITORING
    assert profile.valid == 1 and lib.asd_profile_runtime_validate(ctypes.byref(profile), 1) == 1
    assert list(profile.center) == frozen_center
    assert (profile.threshold_enter, profile.threshold_exit) == frozen_thresholds
    assert (profile.center_windows, profile.derive_windows, profile.verify_windows) == (2, 2, 3)
    assert profile.developmental == 1


def test_k1_invalid_threshold_verify_alarm_and_timeout_reject(lib) -> None:
    policy = small_policy(lib, verify_min=1)
    flow = reach_center(lib, policy)
    profile = Profile()
    center = (ctypes.c_float * 96)(*[0.0] * 96)
    for now in (4, 5):
        assert lib.asd_commission_record_center(ctypes.byref(flow), now, 1) == 1
    assert lib.asd_commission_commit_center(
        ctypes.byref(flow), 6, ctypes.byref(profile), center, -30.0, 2.0, 0,
    ) == 0
    assert (flow.phase, flow.reject_reason) == (REJECTED, REJECT_K1)

    flow = reach_center(lib, policy)
    profile = Profile()
    for now in (4, 5):
        lib.asd_commission_record_center(ctypes.byref(flow), now, 1)
    lib.asd_commission_commit_center(
        ctypes.byref(flow), 6, ctypes.byref(profile), center, -30.0, 2.0, 1,
    )
    for now in (7, 8):
        lib.asd_commission_record_derive(ctypes.byref(flow), now, 5.0, 1)
    assert lib.asd_commission_freeze_thresholds(
        ctypes.byref(flow), 9, ctypes.byref(profile), 5.0, 5.0,
    ) == 0
    assert (flow.phase, flow.reject_reason) == (REJECTED, REJECT_PROFILE)

    flow = reach_center(lib, policy)
    assert lib.asd_commission_poll(ctypes.byref(flow), 200) == 0
    assert (flow.phase, flow.reject_reason) == (REJECTED, REJECT_TIMEOUT)


def test_verify_failure_never_repairs_thresholds(lib) -> None:
    policy = small_policy(lib, verify_min=1, max_episodes=0)
    flow = reach_center(lib, policy)
    profile = Profile()
    center = (ctypes.c_float * 96)(*[0.0] * 96)
    for now in (4, 5):
        lib.asd_commission_record_center(ctypes.byref(flow), now, 1)
    lib.asd_commission_commit_center(
        ctypes.byref(flow), 6, ctypes.byref(profile), center, -30.0, 2.0, 1,
    )
    for now in (7, 8):
        lib.asd_commission_record_derive(ctypes.byref(flow), now, 4.0, 1)
    lib.asd_commission_freeze_thresholds(
        ctypes.byref(flow), 9, ctypes.byref(profile), 10.0, 5.0,
    )
    before = profile.threshold_enter, profile.threshold_exit, list(profile.center)
    for now in (10, 11, 12):
        lib.asd_commission_record_verify(
            ctypes.byref(flow), now, ctypes.byref(profile), 20.0, 1,
        )
    assert (flow.phase, flow.reject_reason) == (REJECTED, REJECT_VERIFY)
    assert profile.valid == 0
    assert (profile.threshold_enter, profile.threshold_exit, list(profile.center)) == before


def reach_verify(lib, policy: Policy, *, enter: float, exit_: float) -> tuple:
    """Dovede tok do VERIFY faze sa zadatim zamrznutim pragovima."""
    flow = reach_center(lib, policy)
    profile = Profile()
    center = (ctypes.c_float * 96)(*[0.0] * 96)
    for now in (4, 5):
        lib.asd_commission_record_center(ctypes.byref(flow), now, 1)
    lib.asd_commission_commit_center(
        ctypes.byref(flow), 6, ctypes.byref(profile), center, -30.0, 2.0, 1,
    )
    for now in (7, 8):
        lib.asd_commission_record_derive(ctypes.byref(flow), now, 4.0, 1)
    assert lib.asd_commission_freeze_thresholds(
        ctypes.byref(flow), 9, ctypes.byref(profile), enter, exit_,
    ) == 1
    return flow, profile


def test_verify_needs_min_consecutive_not_a_single_high_window(lib) -> None:
    """Jedan ili dva prozora iznad praga ne otvaraju epizodu.

    `verify_alarm_windows` raste samo dok je `verify_active`, a taj se pali tek
    na `verify_min_consecutive` UZASTOPNIH prozora iznad `threshold_enter`.
    Bez ovoga se `max_verify_alarm_windows = 0` lako procita kao "nijedan
    prozor ne smije preci prag", sto bi za GUIDED25 politiku (prag = maksimum
    44 DERIVE skora) davalo dramaticno vecu procjenu rizika nego sto jeste.
    """
    policy = small_policy(lib, verify_min=3)
    policy.verify_windows = 9
    enter, exit_ = 10.0, 5.0

    # Dva iznad, jedan ispod, pa opet dva iznad: nijedna epizoda se ne otvara.
    flow, profile = reach_verify(lib, policy, enter=enter, exit_=exit_)
    pattern = [20.0, 20.0, 1.0, 20.0, 20.0, 1.0, 1.0, 1.0, 1.0]
    for offset, score in enumerate(pattern):
        assert lib.asd_commission_record_verify(
            ctypes.byref(flow), 10 + offset, ctypes.byref(profile), score, 1,
        ) == 1
    assert flow.verify_episodes == 0
    assert flow.verify_alarm_windows == 0
    assert (flow.phase, flow.reject_reason) == (MONITORING, REJECT_NONE)
    assert profile.valid == 1

    # Tri uzastopna iznad praga otvaraju epizodu. Odbijanje se ne prijavljuje
    # odmah nego tek kad se VERIFY faza napuni (asd_commissioning.c:248), pa
    # se i ovdje dovrsi svih `verify_windows` prozora.
    flow, profile = reach_verify(lib, policy, enter=enter, exit_=exit_)
    pattern = [1.0, 20.0, 20.0, 20.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    for offset, score in enumerate(pattern):
        lib.asd_commission_record_verify(
            ctypes.byref(flow), 10 + offset, ctypes.byref(profile), score, 1,
        )
    assert flow.verify_episodes == 1
    assert (flow.phase, flow.reject_reason) == (REJECTED, REJECT_VERIFY)
    assert profile.valid == 0


def test_operator_abort_is_terminal_and_settle_api_has_no_score(lib) -> None:
    header = (MAIN / "asd_commissioning.h").read_text(encoding="utf-8")
    declaration = header.split("asd_commission_observe_settle", 1)[1].split(");", 1)[0]
    assert "score" not in declaration
    policy = small_policy(lib)
    flow = Flow()
    lib.asd_commission_init(ctypes.byref(flow), ctypes.byref(policy))
    assert lib.asd_commission_start(ctypes.byref(flow), 0) == 1
    lib.asd_commission_abort(ctypes.byref(flow))
    assert (flow.phase, flow.reject_reason) == (ABORTED, REJECT_ABORT)
    assert lib.asd_commission_poll(ctypes.byref(flow), 1) == 0
