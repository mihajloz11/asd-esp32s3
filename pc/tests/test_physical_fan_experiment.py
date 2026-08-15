from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "pc" / "tools" / "physical_fan_experiment.py"
SPEC = importlib.util.spec_from_file_location("physical_fan_experiment", MODULE_PATH)
assert SPEC and SPEC.loader
physical = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(physical)


def test_parse_det_line() -> None:
    parsed = physical.parse_serial_line(
        "DET 12 score=1234.50000 lo=0.00000 hi=900.25000 led=0 anom=1 "
        "total_anom=3 ALARM (uzastopnih=4 nivo=-31.2 dBFS racun=704 ms)"
    )
    assert parsed == {
        "kind": "DET",
        "window": 12,
        "score": 1234.5,
        "lo": 0.0,
        "threshold": 900.25,
        "led": 0,
        "alarm": 1,
        "total_alarm": 3,
        "verdict": "ALARM",
        "consecutive": 4,
        "level_dbfs": -31.2,
        "compute_ms": 704,
    }


def test_det_parser_is_anchored_and_rejects_trailing_or_nonzero_lo() -> None:
    base = (
        "DET 1 score=1 lo=0 hi=1.60000002 led=1 anom=0 total_anom=0 "
        "normal (uzastopnih=0 nivo=-30.0 dBFS racun=700 ms)"
    )
    assert physical.parse_serial_line("prefix " + base) is None
    trailing = physical.parse_serial_line(base + " trailing")
    assert trailing["kind"] == "PARSE_ERROR"
    assert trailing["reason"] == "malformed_or_truncated_det"

    ready = _ready_protocol_state()
    pending = physical.transition_firmware_protocol(ready, _quality("DET"))
    parsed = physical.parse_serial_line(base.replace("lo=0", "lo=0.1"))
    invalid = physical.transition_firmware_protocol(pending, parsed)
    assert invalid["invalid_reason"] == "DET_lo_not_zero:0.1"


def test_parse_phases_threshold_and_dropped() -> None:
    assert physical.parse_serial_line(
        "WAIT 1/60 score=-35.00 spread=0.000 nivo=-35.0 dBFS cujem"
    )["kind"] == "WAIT"
    assert physical.parse_serial_line(
        "CAL  2/10 score=0.00000 nivo=-31.5 dBFS racun=711 ms"
    ) == {
        "kind": "CAL", "index": 2, "total": 10,
        "level_dbfs": -31.5, "compute_ms": 711,
    }
    assert physical.parse_serial_line(
        "ADAPTTHR n=10 mean=10 sd=2 k=0 theta=0 p=.9 thr=16.125 lo=0 factory=0"
    ) == {
        "kind": "ADAPTTHR", "n": 10, "mean": 10.0, "sd": 2.0,
        "k": 0.0, "theta": 0.0, "p": 0.9, "threshold": 16.125,
        "lo": 0.0, "factory": 0.0,
    }
    assert physical.parse_serial_line(
        "I psdlive: racun po klipu 704 ms, dropped=0"
    ) == {"kind": "DROPPED", "dropped": 0}


def test_parse_quality_state_event_v1_telemetry() -> None:
    quality = physical.parse_serial_line(
        "I psdlive: QUALITY protocol=asd-quality-v1.3.0 phase=CAL index=2 total=10 "
        "result=OK metrics_valid=1 samples=159744 expected=159744 "
        "rms_dbfs=-31.250 dc=2.5 peak=4100 "
        "clipped=0 zeros=3 stuck=7 dropped_delta=0 feature_valid=1 tonalness_proxy=1.125 "
        "tonalness_valid=1 tonal_gate=pending_normal_only"
    )
    assert quality == {
        "kind": "QUALITY", "protocol": "asd-quality-v1.3.0", "phase": "CAL",
        "index": 2, "total": 10, "result": "OK", "samples": 159744,
        "metrics_valid": 1, "feature_valid": 1,
        "expected": 159744, "rms_dbfs": -31.25, "dc": 2.5, "peak": 4100,
        "clipped": 0, "zeros": 3, "stuck": 7, "dropped_delta": 0,
        "tonalness_proxy": 1.125, "tonalness_valid": 1,
        "tonal_gate": "pending_normal_only",
    }
    assert physical.parse_serial_line(
        "STATE protocol=asd-quality-v1.3.0 from=NO_MACHINE "
        "to=CALIBRATION_REJECTED reason=CLIPPING"
    ) == {
        "kind": "STATE", "protocol": "asd-quality-v1.3.0",
        "from_state": "NO_MACHINE", "to_state": "CALIBRATION_REJECTED",
        "reason": "CLIPPING",
    }
    assert physical.parse_serial_line(
        "EVENT protocol=asd-quality-v1.3.0 type=FLOW_STOPPED "
        "state=SENSOR_ERROR phase=CAL reason=DROPPED_SAMPLES "
        "event=SENSOR_FAULT capability=AVAILABLE level=SENSOR_HEALTH"
    ) == {
        "kind": "EVENT", "protocol": "asd-quality-v1.3.0",
        "type": "FLOW_STOPPED", "state": "SENSOR_ERROR", "phase": "CAL",
        "reason": "DROPPED_SAMPLES", "event": "SENSOR_FAULT",
        "capability": "AVAILABLE", "level": "SENSOR_HEALTH",
    }


def test_quality_protocol_is_strict_and_operator_truth_is_separate() -> None:
    assert physical.PROTOCOL_VERSION == "physical-fan-v1.6.0"
    mismatch = physical.parse_serial_line(
        "STATE protocol=asd-quality-v0 from=NO_MACHINE to=ANOMALY reason=x"
    )
    assert mismatch["kind"] == "PARSE_ERROR"
    assert mismatch["reason"] == "invalid_protocol_mismatch"
    missing = physical.parse_serial_line(
        "EVENT type=FLOW_STOPPED state=SENSOR_ERROR phase=CAL reason=x"
    )
    assert missing["kind"] == "PARSE_ERROR"
    assert missing["reason"] == "invalid_protocol_missing"
    assert "condition" not in physical.QUALITY_FIELDS
    assert "condition" not in physical.STATE_FIELDS
    assert "condition" not in physical.FIRMWARE_EVENT_FIELDS


def test_malformed_v1_telemetry_is_audited_not_raised() -> None:
    malformed = physical.parse_serial_line(
        "QUALITY protocol=asd-quality-v1.3.0 phase=CAL index=x total=10 "
        "result=OK samples=10 expected=10 rms_dbfs=-30 dc=0 peak=1 feature_valid=1 "
        "clipped=0 zeros=0 stuck=0 dropped_delta=0 tonalness_proxy=1 "
        "tonal_gate=pending_normal_only"
    )
    assert malformed["kind"] == "PARSE_ERROR"
    assert malformed["reason"] == "malformed_numeric_field"
    truncated = physical.parse_serial_line(
        "STATE protocol=asd-quality-v1.3.0 from=NO_MACHINE to="
    )
    assert truncated["kind"] == "PARSE_ERROR"
    assert truncated["reason"] == "malformed_key_value_token"
    bare = physical.parse_serial_line("QUALITY")
    assert bare["kind"] == "PARSE_ERROR"
    assert bare["reason"] == "invalid_protocol_missing"


def test_duplicate_keys_and_nonfinite_adapt_are_audited() -> None:
    duplicate = physical.parse_serial_line(
        "QUALITY protocol=asd-quality-v1.3.0 phase=WAIT phase=WAIT"
    )
    assert duplicate["kind"] == "PARSE_ERROR"
    assert duplicate["reason"] == "duplicate_key:phase"
    nonfinite = physical.parse_serial_line(
        "ADAPTTHR n=10 mean=inf sd=2 k=0 theta=0 p=.9 thr=16 lo=0 factory=0"
    )
    assert nonfinite["kind"] == "PARSE_ERROR"
    assert nonfinite["reason"] == "nonfinite_field:ADAPTTHR:mean"


def _quality(phase: str, index: int = 1) -> dict:
    if phase == "CAL_SUMMARY":
        return {
            "kind": "QUALITY", "protocol": physical.QUALITY_PROTOCOL_VERSION,
            "phase": phase, "result": "OBSERVED", "loo_mean": 1.0,
            "loo_sd": 0.2, "loo_cv": 0.2, "loo_range": 0.5,
            "loo_gate": "pending_normal_only",
        }
    expected_samples = (
        physical.WAIT_EXPECTED_SAMPLES
        if phase == "WAIT" else physical.CLIP_EXPECTED_SAMPLES
    )
    total = 60 if phase == "WAIT" else (10 if phase == "CAL" else 0)
    return {
        "kind": "QUALITY", "protocol": physical.QUALITY_PROTOCOL_VERSION,
        "phase": phase, "index": index, "total": total, "result": "OK",
        "metrics_valid": 1, "feature_valid": 0 if phase == "WAIT" else 1,
        "samples": expected_samples, "expected": expected_samples,
        "rms_dbfs": -30.0, "dc": 0.0,
        "peak": 1100, "clipped": 0, "zeros": 0, "stuck": 0,
        "dropped_delta": 0,
        "tonalness_proxy": 0.0 if phase == "WAIT" else 1.0,
        "tonalness_valid": 0 if phase == "WAIT" else 1,
        "tonal_gate": "not_computed" if phase == "WAIT" else "pending_normal_only",
    }


def _adapt(*, threshold: float = 1.6) -> dict:
    return {
        "kind": "ADAPTTHR", "n": 10, "mean": 1.0, "sd": 0.2,
        "k": 0.0, "theta": 0.0, "p": 0.9, "threshold": threshold,
        "lo": 0.0, "factory": 0.0,
    }


def _presence(*, level_mean_dbfs: float = -30.0) -> dict:
    margin = physical.PRESENCE_POLICY["absent_margin_db"]
    return {
        "kind": "PRESENCE", "protocol": physical.QUALITY_PROTOCOL_VERSION,
        "level_mean_dbfs": level_mean_dbfs, "margin_db": margin,
        "gate_dbfs": level_mean_dbfs - margin,
        "min_consecutive": physical.PRESENCE_POLICY["min_consecutive_windows"],
    }


def _temporal() -> dict:
    policy = physical.TEMPORAL_POLICY
    return {
        "kind": "TEMPORAL", "protocol": physical.QUALITY_PROTOCOL_VERSION,
        "policy": physical.TEMPORAL_POLICY_RECORD["schema_version"],
        "min_consecutive": policy["min_consecutive"],
        "ewma_alpha": policy["ewma_alpha"],
        "enter_scale": policy["enter_scale"],
        "exit_scale": policy["exit_scale"],
        "fast_scale": policy["fast_scale"],
    }


def _ready_protocol_state() -> dict:
    state = physical.new_firmware_protocol_state()
    state = physical.transition_firmware_protocol(state, {
        "kind": "STATE", "from_state": "NO_MACHINE", "to_state": "NO_MACHINE",
        "reason": "BOOT_FAIL_CLOSED",
    })
    for phase, count in physical.EXPECTED_QUALITY_COUNTS.items():
        for index in range(1, count + 1):
            state = physical.transition_firmware_protocol(state, _quality(phase, index))
    state = physical.transition_firmware_protocol(state, _adapt())
    state = physical.transition_firmware_protocol(state, _presence())
    state = physical.transition_firmware_protocol(state, _temporal())
    state = physical.transition_firmware_protocol(state, {
        "kind": "STATE", "from_state": "NO_MACHINE",
        "to_state": "CALIBRATED_NORMAL", "reason": "CALIBRATION_ACCEPTED",
    })
    state = physical.transition_firmware_protocol(state, {
        "kind": "EVENT", "type": "CALIBRATION_ACCEPTED",
        "state": "CALIBRATED_NORMAL", "phase": "CAL", "reason": "QUALITY_OK",
    })
    return state


def _handshake_state() -> dict:
    return physical.transition_firmware_protocol(
        physical.new_firmware_protocol_state(),
        {
            "kind": "STATE", "from_state": "NO_MACHINE",
            "to_state": "NO_MACHINE", "reason": "BOOT_FAIL_CLOSED",
        },
    )


def test_literal_firmware_quality_replay_wait_and_reject_contract() -> None:
    wait_line = (
        "QUALITY protocol=asd-quality-v1.3.0 phase=WAIT index=1 total=60 "
        "result=LOW_LEVEL_OBSERVATION metrics_valid=1 feature_valid=0 samples=4096 expected=4096 "
        "rms_dbfs=-70.000 dc=123.000 peak=200 clipped=0 zeros=0 stuck=0 "
        "dropped_delta=0 tonalness_valid=0 tonalness_proxy=0.000000 "
        "tonal_gate=not_computed"
    )
    parsed_wait = physical.parse_serial_line(wait_line)
    assert parsed_wait is not None and parsed_wait["kind"] == "QUALITY"
    state = physical.transition_firmware_protocol(_handshake_state(), parsed_wait)
    assert state["invalid_status"] is None
    assert state["quality_counts"]["WAIT"] == 1
    assert state["wait_ok_count"] == 0

    state = _handshake_state()
    for index in range(1, 61):
        state = physical.transition_firmware_protocol(state, _quality("WAIT", index))
    reject_line = (
        "QUALITY protocol=asd-quality-v1.3.0 phase=CAL index=1 total=10 "
        "result=CLIPPING metrics_valid=1 feature_valid=0 samples=159744 expected=159744 "
        "rms_dbfs=-10.000 dc=0.000 peak=32768 clipped=160 zeros=0 stuck=0 "
        "dropped_delta=0 tonalness_valid=0 tonalness_proxy=0.000000 "
        "tonal_gate=not_computed"
    )
    parsed_reject = physical.parse_serial_line(reject_line)
    assert parsed_reject is not None and parsed_reject["kind"] == "QUALITY"
    state = physical.transition_firmware_protocol(state, parsed_reject)
    assert state["invalid_status"] == "invalid_firmware_terminal"
    assert state["drain_expected_state"] == "CALIBRATION_REJECTED"
    assert state["drain_expected_reason"] == "CLIPPING"


def test_literal_pcm_valid_feature_nonfinite_is_a_firmware_reject() -> None:
    line = (
        "QUALITY protocol=asd-quality-v1.3.0 phase=DET index=1 total=0 "
        "result=NONFINITE metrics_valid=1 samples=159744 expected=159744 "
        "rms_dbfs=-30.000 dc=0.000 peak=1100 clipped=0 zeros=0 stuck=0 "
        "dropped_delta=0 feature_valid=0 tonalness_valid=0 "
        "tonalness_proxy=0.000000 tonal_gate=not_computed"
    )
    parsed = physical.parse_serial_line(line)
    assert parsed is not None and parsed["kind"] == "QUALITY"
    rejected = physical.transition_firmware_protocol(_ready_protocol_state(), parsed)
    assert rejected["invalid_status"] == "invalid_firmware_terminal"
    assert rejected["invalid_reason"] == "quality_reject:DET:NONFINITE"
    assert rejected["drain_expected_state"] == "SENSOR_ERROR"


def test_host_transition_requires_handshake_cal_accept_counts_and_paired_quality() -> None:
    initial = physical.new_firmware_protocol_state()
    changed = physical.transition_firmware_protocol(initial, {"kind": "DET"})
    assert initial["invalid_status"] is None  # pure: input was not mutated
    assert changed["invalid_status"] == "invalid_missing_telemetry"

    ready = _ready_protocol_state()
    assert physical.firmware_protocol_ready(ready)
    missing_pair = physical.transition_firmware_protocol(ready, {"kind": "DET"})
    assert missing_pair["invalid_reason"] == "DET_without_preceding_quality"

    paired = physical.transition_firmware_protocol(ready, _quality("DET"))
    paired = physical.transition_firmware_protocol(paired, _det())
    assert paired["invalid_status"] is None
    assert paired["det_records"] == 1


def test_protocol_mismatch_and_terminal_state_invalidate_host_result() -> None:
    mismatch = physical.transition_firmware_protocol(
        physical.new_firmware_protocol_state(),
        {"kind": "PARSE_ERROR", "reason": "invalid_protocol_mismatch"},
    )
    assert mismatch["invalid_status"] == "invalid_protocol_mismatch"

    ready = _ready_protocol_state()
    terminal = physical.transition_firmware_protocol(ready, {
        "kind": "EVENT", "type": "FLOW_STOPPED", "state": "SENSOR_ERROR",
        "phase": "DET", "reason": "DROPPED_SAMPLES", "event": "SENSOR_FAULT",
        "capability": "AVAILABLE", "level": "SENSOR_HEALTH",
    })
    assert terminal["terminal"] is True
    assert terminal["invalid_status"] == "invalid_firmware_terminal"

    for terminal_state in physical.TERMINAL_FIRMWARE_STATES:
        state = physical.transition_firmware_protocol(ready, {
            "kind": "STATE", "from_state": "CALIBRATED_NORMAL",
            "to_state": terminal_state,
            "reason": (
                "CLIPPING" if terminal_state == "RECALIBRATION_REQUIRED"
                else "DROPPED_SAMPLES"
            ),
        })
        assert state["invalid_status"] in {
            "invalid_firmware_terminal", "invalid_firmware_telemetry",
        }
        assert state["terminal"] is True


def test_quality_reject_and_out_of_order_telemetry_fail_fast() -> None:
    initial = physical.new_firmware_protocol_state()
    before_handshake = physical.transition_firmware_protocol(initial, _quality("WAIT"))
    assert before_handshake["invalid_reason"] == "QUALITY_before_handshake"

    ready = _ready_protocol_state()
    rejected = physical.transition_firmware_protocol(
        ready, {
            **_quality("DET"), "result": "LOW_LEVEL_OBSERVATION",
            "rms_dbfs": -70.0,
        },
    )
    assert rejected["terminal"] is True
    assert rejected["invalid_status"] == "invalid_firmware_terminal"


def test_summary_excludes_unconfirmed_operator_condition() -> None:
    metadata = {
        "fan_id": "fan01", "session_id": "s1", "port": "COM3", "baud": 115200,
        "distance_cm": 10, "room": "lab",
    }
    row = {
        "condition": "unconfirmed", "condition_confirmed": 0, "protocol_valid": 1,
        "alarm": 0, "score": 1.0,
    }
    summary = physical.make_summary(
        metadata=metadata, status="completed_by_operator", events=[], detections=[row],
        max_dropped=0, protocol_state=_ready_protocol_state(),
    )
    assert "Validan fizički rezultat: **NE**" in summary
    assert "Validnih DET prozora za metrike: 0" in summary

    row = {**row, "condition": "normal_baseline", "condition_confirmed": 1}
    state = _ready_protocol_state()
    state = physical.transition_firmware_protocol(state, _quality("DET"))
    state = physical.transition_firmware_protocol(state, _det())
    summary = physical.make_summary(
        metadata=metadata, status="completed_by_operator", events=[], detections=[row],
        max_dropped=0, protocol_state=state,
    )
    assert "Validan fizički rezultat: **DA**" in summary


def _det(
    *, window: int = 1, score: float = 1.0, threshold: float = 1.6,
    led: int = 1, alarm: int = 0, total_alarm: int = 0,
    consecutive: int = 0, verdict: str = "normal",
) -> dict:
    return {
        "kind": "DET", "window": window, "score": score,
        "lo": 0.0, "threshold": threshold, "led": led, "alarm": alarm,
        "total_alarm": total_alarm, "verdict": verdict,
        "consecutive": consecutive, "level_dbfs": -30.0, "compute_ms": 700,
    }


def _state_waiting_for_anomaly_transition() -> dict:
    state = _ready_protocol_state()
    for window in (1, 2, 3):
        state = physical.transition_firmware_protocol(state, _quality("DET", window))
        state = physical.transition_firmware_protocol(
            state,
            _det(
                window=window, score=3.0, led=0 if window == 3 else 1,
                alarm=1 if window == 3 else 0,
                total_alarm=1 if window == 3 else 0,
                consecutive=window,
                verdict="ALARM" if window == 3 else "iznad praga",
            ),
        )
        assert state["invalid_status"] is None
    return state


def _consume_anomaly_pair(state: dict) -> dict:
    state = physical.transition_firmware_protocol(state, {
        "kind": "STATE", "from_state": "CALIBRATED_NORMAL",
        "to_state": "ANOMALY", "reason": "THRESHOLD_PERSISTENCE",
    })
    return physical.transition_firmware_protocol(state, {
        "kind": "EVENT", "type": "ANOMALY_ENTERED", "state": "ANOMALY",
        "phase": "DET", "reason": "THRESHOLD_PERSISTENCE",
    })


def test_det_requires_exact_state_event_transition_and_clear_pair() -> None:
    waiting = _state_waiting_for_anomaly_transition()
    assert waiting["expected_state_transition"] is not None
    assert physical.firmware_protocol_complete(waiting) is False

    missing = physical.transition_firmware_protocol(waiting, _quality("DET", 4))
    assert missing["invalid_reason"] == "missing_expected_STATE_before:QUALITY"

    state_only = physical.transition_firmware_protocol(waiting, {
        "kind": "STATE", "from_state": "CALIBRATED_NORMAL",
        "to_state": "ANOMALY", "reason": "THRESHOLD_PERSISTENCE",
    })
    assert state_only["expected_state_transition"] is None
    assert state_only["pending_state_event"] is not None
    assert physical.firmware_protocol_complete(state_only) is False
    missing_event = physical.transition_firmware_protocol(state_only, _quality("DET", 4))
    assert missing_event["invalid_reason"] == "missing_paired_EVENT_before:QUALITY"

    state = _consume_anomaly_pair(waiting)
    assert state["last_state"] == "ANOMALY"
    assert physical.firmware_protocol_complete(state)


def test_literal_full_v12_trace_with_roundtrip_det_and_anomaly_pair() -> None:
    q = physical.QUALITY_PROTOCOL_VERSION
    lines = [
        f"STATE protocol={q} from=NO_MACHINE to=NO_MACHINE reason=BOOT_FAIL_CLOSED",
    ]
    for index in range(1, 61):
        lines.append(
            f"QUALITY protocol={q} phase=WAIT index={index} total=60 result=OK "
            "metrics_valid=1 samples=4096 expected=4096 rms_dbfs=-30.000 "
            "dc=0.000 peak=1100 clipped=0 zeros=0 stuck=0 dropped_delta=0 "
            "feature_valid=0 tonalness_valid=0 tonalness_proxy=0.000000 "
            "tonal_gate=not_computed"
        )
    for index in range(1, 11):
        lines.append(
            f"QUALITY protocol={q} phase=CAL index={index} total=10 result=OK "
            "metrics_valid=1 samples=159744 expected=159744 rms_dbfs=-30.000 "
            "dc=0.000 peak=1100 clipped=0 zeros=0 stuck=0 dropped_delta=0 "
            "feature_valid=1 tonalness_valid=1 tonalness_proxy=1.000000 "
            "tonal_gate=pending_normal_only"
        )
    lines.extend([
        f"QUALITY protocol={q} phase=CAL_SUMMARY result=OBSERVED loo_mean=1.000000 "
        "loo_sd=0.200000 loo_cv=0.200000 loo_range=0.500000 "
        "loo_gate=pending_normal_only",
        "ADAPTTHR n=10 mean=1.000000 sd=0.200000 k=0 theta=0 p=0.9000 "
        "thr=1.60000002 lo=0.000000 factory=0.000000",
        f"PRESENCE protocol={q} level_mean_dbfs=-30 margin_db=11 "
        "gate_dbfs=-41 min_consecutive=3",
        f"TEMPORAL protocol={q} policy=asd-temporal-policy-v1.0.0 "
        "min_consecutive=3 ewma_alpha=0 enter_scale=1 exit_scale=0.7 fast_scale=0",
        f"STATE protocol={q} from=NO_MACHINE to=CALIBRATED_NORMAL "
        "reason=CALIBRATION_ACCEPTED",
        f"EVENT protocol={q} type=CALIBRATION_ACCEPTED state=CALIBRATED_NORMAL "
        "phase=CAL reason=QUALITY_OK event=NONE capability=AVAILABLE level=DEVIATION",
    ])
    for window in (1, 2, 3):
        lines.append(
            f"QUALITY protocol={q} phase=DET index={window} total=0 result=OK "
            "metrics_valid=1 samples=159744 expected=159744 rms_dbfs=-30.000 "
            "dc=0.000 peak=1100 clipped=0 zeros=0 stuck=0 dropped_delta=0 "
            "feature_valid=1 tonalness_valid=1 tonalness_proxy=1.000000 "
            "tonal_gate=pending_normal_only"
        )
        alarm = int(window == 3)
        lines.append(
            f"DET {window} score=3 lo=0 hi=1.60000002 led={1 - alarm} "
            f"anom={alarm} total_anom={alarm} "
            f"{'ALARM' if alarm else 'iznad praga'} "
            f"(uzastopnih={window} nivo=-30.0 dBFS racun=700 ms)"
        )
    lines.extend([
        f"STATE protocol={q} from=CALIBRATED_NORMAL to=ANOMALY "
        "reason=THRESHOLD_PERSISTENCE",
        f"EVENT protocol={q} type=ANOMALY_ENTERED state=ANOMALY phase=DET "
        "reason=THRESHOLD_PERSISTENCE event=UNKNOWN_CHANGE capability=AVAILABLE "
        "level=DEVIATION",
    ])

    state = physical.new_firmware_protocol_state()
    for line in lines:
        parsed = physical.parse_serial_line(line)
        assert parsed is not None and parsed["kind"] != "PARSE_ERROR", line
        state = physical.transition_firmware_protocol(state, parsed)
        assert state["invalid_status"] is None, (line, state["invalid_reason"])
    assert state["last_state"] == "ANOMALY"
    assert state["det_records"] == 3
    assert physical.firmware_protocol_complete(state)
    state = physical.transition_firmware_protocol(state, _quality("DET", 4))
    state = physical.transition_firmware_protocol(
        state, _det(window=4, threshold=1.60000002, total_alarm=1),
    )
    assert state["expected_state_transition"]["state"]["to_state"] == "CALIBRATED_NORMAL"
    state = physical.transition_firmware_protocol(state, {
        "kind": "STATE", "from_state": "ANOMALY",
        "to_state": "CALIBRATED_NORMAL", "reason": "ALARM_CLEARED",
    })
    state = physical.transition_firmware_protocol(state, {
        "kind": "EVENT", "type": "ANOMALY_CLEARED",
        "state": "CALIBRATED_NORMAL", "phase": "DET", "reason": "ALARM_CLEARED",
    })
    assert physical.firmware_protocol_complete(state)


def test_spurious_or_wrong_det_state_transition_is_rejected() -> None:
    state = _ready_protocol_state()
    state = physical.transition_firmware_protocol(state, _quality("DET", 1))
    state = physical.transition_firmware_protocol(
        state, _det(window=1, score=3.0, consecutive=1, verdict="iznad praga"),
    )
    spurious = physical.transition_firmware_protocol(state, {
        "kind": "STATE", "from_state": "CALIBRATED_NORMAL",
        "to_state": "ANOMALY", "reason": "THRESHOLD_PERSISTENCE",
    })
    assert spurious["invalid_reason"] == "spurious_DET_STATE_transition"

    waiting = _state_waiting_for_anomaly_transition()
    wrong = physical.transition_firmware_protocol(waiting, {
        "kind": "STATE", "from_state": "CALIBRATED_NORMAL",
        "to_state": "ANOMALY", "reason": "ALARM_CLEARED",
    })
    assert wrong["invalid_reason"] == "DET_STATE_transition_mismatch"


def test_stop_race_with_unconsumed_anomaly_pair_cannot_be_valid() -> None:
    state = _state_waiting_for_anomaly_transition()
    rows = [
        {
            "condition": "normal_baseline", "condition_confirmed": 1,
            "protocol_valid": 1, "alarm": int(window == 3), "score": 3.0,
        }
        for window in (1, 2, 3)
    ]
    summary = physical.make_summary(
        metadata={
            "fan_id": "fan01", "session_id": "s1", "port": "COM9",
            "baud": 115200, "distance_cm": 10, "room": "lab",
        },
        status="completed_by_operator", events=[], detections=rows,
        max_dropped=0, protocol_state=state,
    )
    assert physical.firmware_protocol_complete(state) is False
    assert "rezultat: **NE**" in summary


def test_strict_wait_cal_and_summary_sequence_rejects_replay() -> None:
    handshake = physical.transition_firmware_protocol(
        physical.new_firmware_protocol_state(),
        {"kind": "STATE", "from_state": "NO_MACHINE", "to_state": "NO_MACHINE",
         "reason": "BOOT_FAIL_CLOSED"},
    )
    out_of_order = physical.transition_firmware_protocol(handshake, _quality("WAIT", 2))
    assert out_of_order["invalid_status"] == "invalid_firmware_telemetry"
    assert out_of_order["invalid_reason"].startswith("WAIT_sequence")

    state = handshake
    for index in range(1, 61):
        state = physical.transition_firmware_protocol(state, _quality("WAIT", index))
    duplicate_wait = physical.transition_firmware_protocol(state, _quality("WAIT", 60))
    assert duplicate_wait["invalid_reason"].startswith("WAIT_sequence")

    bad_cal = physical.transition_firmware_protocol(state, _quality("CAL", 2))
    assert bad_cal["invalid_reason"].startswith("CAL_sequence")

    for index in range(1, 11):
        state = physical.transition_firmware_protocol(state, _quality("CAL", index))
    state = physical.transition_firmware_protocol(state, _quality("CAL_SUMMARY"))
    duplicate_summary = physical.transition_firmware_protocol(state, _quality("CAL_SUMMARY"))
    assert duplicate_summary["invalid_reason"] == "duplicate_CAL_SUMMARY"


def test_all_low_wait_cannot_enter_calibration() -> None:
    state = _handshake_state()
    for index in range(1, 61):
        state = physical.transition_firmware_protocol(
            state,
            {
                **_quality("WAIT", index),
                "result": "LOW_LEVEL_OBSERVATION", "rms_dbfs": -70.0,
            },
        )
        assert state["invalid_status"] is None
    assert state["wait_ok_count"] == 0
    state = physical.transition_firmware_protocol(state, _quality("CAL", 1))
    assert state["invalid_reason"] == "CAL_before_sufficient_WAIT_OK:0/60"


def test_cal_summary_and_adapt_are_coherent_unique_and_ordered() -> None:
    state = _handshake_state()
    for phase in ("WAIT", "CAL"):
        for index in range(1, physical.EXPECTED_QUALITY_COUNTS[phase] + 1):
            state = physical.transition_firmware_protocol(state, _quality(phase, index))

    negative = physical.transition_firmware_protocol(
        state, {**_quality("CAL_SUMMARY"), "loo_sd": -0.2},
    )
    assert negative["invalid_reason"] == "negative_CAL_SUMMARY_value"
    incoherent = physical.transition_firmware_protocol(
        state, {**_quality("CAL_SUMMARY"), "loo_range": 0.1},
    )
    assert incoherent["invalid_reason"] == "CAL_SUMMARY_range_smaller_than_sd"

    state = physical.transition_firmware_protocol(state, _quality("CAL_SUMMARY"))
    accepted_without_adapt = physical.transition_firmware_protocol(state, {
        "kind": "STATE", "from_state": "NO_MACHINE",
        "to_state": "CALIBRATED_NORMAL", "reason": "CALIBRATION_ACCEPTED",
    })
    assert accepted_without_adapt["invalid_reason"] == (
        "CALIBRATION_ACCEPTED_without_unique_ADAPTTHR"
    )
    mismatch = physical.transition_firmware_protocol(
        state, {**_adapt(), "mean": 2.0},
    )
    assert mismatch["invalid_reason"] == "ADAPTTHR_mean_mismatch"
    state = physical.transition_firmware_protocol(state, _adapt())
    duplicate = physical.transition_firmware_protocol(state, _adapt())
    assert duplicate["invalid_reason"] == "duplicate_ADAPTTHR"


def test_det_threshold_must_equal_unique_adapt_threshold() -> None:
    ready = _ready_protocol_state()
    pending = physical.transition_firmware_protocol(ready, _quality("DET"))
    mismatch = physical.transition_firmware_protocol(
        pending, _det(threshold=1.6001),
    )
    assert mismatch["invalid_reason"].startswith("DET_ADAPTTHR_mismatch:")


def test_quality_numeric_semantics_reject_inf_samples_and_ok_drop() -> None:
    ready = _ready_protocol_state()
    nonfinite = physical.transition_firmware_protocol(
        ready, {**_quality("DET"), "rms_dbfs": float("inf")},
    )
    assert nonfinite["invalid_reason"] == "nonfinite_field:DET:rms_dbfs"

    mismatch = physical.transition_firmware_protocol(
        ready, {**_quality("DET"), "samples": physical.CLIP_EXPECTED_SAMPLES - 1},
    )
    assert mismatch["invalid_reason"] == (
        "quality_reason_mismatch:expected=SHORT_READ:got=OK"
    )

    dropped = physical.transition_firmware_protocol(
        ready, {**_quality("DET"), "dropped_delta": 1},
    )
    assert dropped["invalid_reason"] == (
        "quality_reason_mismatch:expected=DROPPED_SAMPLES:got=OK"
    )


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"rms_dbfs": 0.1}, "positive_rms_dbfs:DET:0.1"),
        ({"dc": 1200.0}, "dc_exceeds_peak:DET"),
        ({"rms_dbfs": -20.0, "peak": 1100}, "rms_exceeds_peak:DET"),
        ({"tonalness_proxy": -0.01}, "negative_tonalness:DET"),
    ],
)
def test_quality_physical_numeric_bounds(changes: dict, reason: str) -> None:
    invalid = physical.transition_firmware_protocol(
        _ready_protocol_state(), {**_quality("DET"), **changes},
    )
    assert invalid["invalid_reason"] == reason


def test_tiny_negative_contract_clamps_but_material_negative_rejects() -> None:
    tiny_line = (
        "DET 1 score=-0.0005 lo=0 hi=1.6 led=1 anom=0 total_anom=0 normal "
        "(uzastopnih=0 nivo=-30 dBFS racun=700 ms)"
    )
    tiny = physical.parse_serial_line(tiny_line)
    assert tiny["score"] == 0.0
    pending = physical.transition_firmware_protocol(
        _ready_protocol_state(), _quality("DET"),
    )
    assert physical.transition_firmware_protocol(pending, tiny)["invalid_status"] is None

    material = physical.parse_serial_line(tiny_line.replace("-0.0005", "-0.002"))
    invalid = physical.transition_firmware_protocol(pending, material)
    assert invalid["invalid_reason"] == "negative_DET_score:-0.002"

    summary = physical.parse_serial_line(
        "QUALITY protocol=asd-quality-v1.3.0 phase=CAL_SUMMARY result=OBSERVED "
        "loo_mean=-0.0005 loo_sd=0 loo_cv=0 loo_range=0 "
        "loo_gate=pending_normal_only"
    )
    assert summary["loo_mean"] == 0.0


def test_det_positive_level_is_rejected() -> None:
    pending = physical.transition_firmware_protocol(
        _ready_protocol_state(), _quality("DET"),
    )
    invalid = physical.transition_firmware_protocol(
        pending, {**_det(), "level_dbfs": 0.1},
    )
    assert invalid["invalid_reason"] == "positive_DET_level:0.1"


def test_det_token_pairing_replay_window_and_binary_semantics() -> None:
    ready = _ready_protocol_state()
    pending = physical.transition_firmware_protocol(ready, _quality("DET"))
    replay = physical.transition_firmware_protocol(pending, _quality("DET"))
    assert replay["invalid_reason"] == "duplicate_or_replayed_DET_quality"

    interposed = physical.transition_firmware_protocol(pending, {
        "kind": "STATE", "from_state": "CALIBRATED_NORMAL",
        "to_state": "ANOMALY", "reason": "THRESHOLD_PERSISTENCE",
    })
    assert interposed["invalid_reason"] == "record_between_DET_quality_and_DET:STATE"

    wrong_window = physical.transition_firmware_protocol(pending, _det(window=2))
    assert wrong_window["invalid_reason"].startswith("DET_window_mismatch")

    alarm_nine = physical.transition_firmware_protocol(pending, _det(alarm=9))
    assert alarm_nine["invalid_reason"] == "invalid_binary_field:led=1:alarm=9"

    nonfinite = physical.transition_firmware_protocol(pending, _det(score=float("inf")))
    assert nonfinite["invalid_reason"] == "nonfinite_field:DET:score"


def test_det_monotonic_counters_and_alarm_consistency() -> None:
    state = _ready_protocol_state()
    state = physical.transition_firmware_protocol(state, _quality("DET", 1))
    state = physical.transition_firmware_protocol(
        state, _det(window=1, score=3.0, consecutive=1, verdict="iznad praga"),
    )
    assert state["invalid_status"] is None
    state = physical.transition_firmware_protocol(state, _quality("DET", 2))
    inconsistent = physical.transition_firmware_protocol(
        state, _det(window=2, score=3.0, consecutive=1, verdict="iznad praga"),
    )
    assert inconsistent["invalid_reason"] == "consecutive_mismatch:expected=2:got=1"

    state = _ready_protocol_state()
    for window, consecutive in ((1, 1), (2, 2)):
        state = physical.transition_firmware_protocol(state, _quality("DET", window))
        state = physical.transition_firmware_protocol(
            state,
            _det(
                window=window, score=3.0, consecutive=consecutive,
                verdict="iznad praga",
            ),
        )
        assert state["invalid_status"] is None
    state = physical.transition_firmware_protocol(state, _quality("DET", 3))
    bad_total = physical.transition_firmware_protocol(
        state,
        _det(
            window=3, score=3.0, led=0, alarm=1, total_alarm=0,
            consecutive=3, verdict="ALARM",
        ),
    )
    assert bad_total["invalid_reason"] == "total_alarm_mismatch:expected=1:got=0"


def test_quality_reject_uses_bounded_terminal_drain() -> None:
    ready = _ready_protocol_state()
    rejected = physical.transition_firmware_protocol(
        ready, {
            **_quality("DET"), "result": "CLIPPING",
            "clipped": 160,
        },
    )
    assert rejected["drain_required"] is True
    assert physical.terminal_drain_decision(rejected, 0.1) == "continue"

    with_state = physical.transition_firmware_protocol(rejected, {
        "kind": "STATE", "from_state": "CALIBRATED_NORMAL",
        "to_state": "RECALIBRATION_REQUIRED", "reason": "CLIPPING",
    })
    assert with_state["terminal_state_seen"] is True
    assert physical.terminal_drain_decision(with_state, 0.2) == "continue"
    assert physical.terminal_drain_decision(
        with_state, physical.TERMINAL_DRAIN_TIMEOUT_S,
    ) == "timeout"

    complete = physical.transition_firmware_protocol(with_state, {
        "kind": "EVENT", "type": "FLOW_STOPPED",
        "state": "RECALIBRATION_REQUIRED", "phase": "DET", "reason": "CLIPPING",
    })
    assert complete["terminal_event_seen"] is True
    assert physical.terminal_drain_decision(complete, 0.3) == "complete"


def test_no_machine_after_detection_is_terminal_and_event_only_needs_state() -> None:
    ready = _ready_protocol_state()
    no_machine = physical.transition_firmware_protocol(ready, {
        "kind": "STATE", "from_state": "CALIBRATED_NORMAL",
        "to_state": "NO_MACHINE", "reason": "INSUFFICIENT_LEVEL",
    })
    assert no_machine["invalid_status"] == "invalid_firmware_terminal"
    assert no_machine["drain_required"] is True
    assert no_machine["terminal_state_seen"] is True

    event_only = physical.transition_firmware_protocol(ready, {
        "kind": "EVENT", "type": "FLOW_STOPPED", "state": "SENSOR_ERROR",
        "phase": "DET", "reason": "NONFINITE",
    })
    assert event_only["invalid_status"] == "invalid_firmware_terminal"
    assert event_only["terminal_event_seen"] is True
    assert event_only["terminal_state_seen"] is False
    assert physical.terminal_drain_decision(event_only, 0.1) == "continue"

    completed = physical.transition_firmware_protocol(event_only, {
        "kind": "STATE", "from_state": "CALIBRATED_NORMAL",
        "to_state": "SENSOR_ERROR", "reason": "NONFINITE",
    })
    assert completed["terminal_state_seen"] is True
    assert physical.terminal_drain_decision(completed, 0.2) == "complete"


def test_terminal_state_while_det_quality_pending_starts_drain() -> None:
    state = physical.transition_firmware_protocol(
        _ready_protocol_state(), _quality("DET"),
    )
    terminal = physical.transition_firmware_protocol(state, {
        "kind": "STATE", "from_state": "CALIBRATED_NORMAL",
        "to_state": "SENSOR_ERROR", "reason": "NONFINITE",
    })
    assert terminal["invalid_status"] == "invalid_firmware_terminal"
    assert terminal["drain_expected_phase"] == "DET"
    assert terminal["terminal_state_seen"] is True


def test_strict_state_event_names_and_terminal_mapping() -> None:
    unknown = physical.transition_firmware_protocol(_handshake_state(), {
        "kind": "EVENT", "type": "MYSTERY", "state": "NO_MACHINE",
        "phase": "WAIT", "reason": "OK",
    })
    assert unknown["invalid_reason"] == "unknown_or_unpaired_EVENT"
    mapping = physical.transition_firmware_protocol(_ready_protocol_state(), {
        "kind": "EVENT", "type": "FLOW_STOPPED", "state": "NO_MACHINE",
        "phase": "DET", "reason": "NONFINITE",
    })
    assert mapping["invalid_reason"] == (
        "FLOW_STOPPED_mapping:expected=SENSOR_ERROR:got=NO_MACHINE"
    )


def test_safe_slug_rejects_empty_and_normalizes() -> None:
    assert physical.safe_slug(" Fan 01 / cold start ") == "Fan-01-cold-start"
    try:
        physical.safe_slug("///")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("prazna oznaka mora biti odbijena")
    with pytest.raises(ValueError):
        physical.parse_condition_command("///")
    with pytest.raises(ValueError):
        physical.parse_condition_command("unconfirmed")
    assert physical.parse_condition_command("normal_baseline stabilan") == (
        "normal_baseline", "stabilan",
    )


def test_poll_command_file_reads_only_appended_lines(tmp_path: Path) -> None:
    path = tmp_path / "commands.txt"
    path.write_text("note prvi\n", encoding="utf-8")
    offset, commands = physical.poll_command_file(path, 0)
    assert commands == ["note prvi"]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("condition airflow test\n")
    new_offset, commands = physical.poll_command_file(path, offset)
    assert new_offset > offset
    assert commands == ["condition airflow test"]


def _run_args(tmp_path: Path, command_file: Path):
    return physical.build_parser().parse_args([
        "run", "--port", "COM9", "--fan-id", "fan01", "--session-id", "s1",
        "--distance-cm", "10", "--room", "lab", "--output-dir", str(tmp_path),
        "--command-file", str(command_file), "--ready", "--no-reset",
        "--non-interactive", "--max-seconds", "5",
    ])


def _mock_ready_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(physical, "list_ports", lambda: [{"device": "COM9"}])
    monkeypatch.setattr(physical, "build_is_psd_live", lambda: True)


def test_serial_open_failure_still_finalizes_provenance_and_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import serial

    _mock_ready_host(monkeypatch)
    monkeypatch.setattr(
        serial, "Serial",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("fixture open failure")),
    )
    with pytest.raises(OSError, match="fixture open failure"):
        physical.run_experiment(_run_args(tmp_path, tmp_path / "commands.txt"))
    run_dir = next(tmp_path.glob("run_*"))
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["status"] == "failed"
    assert (run_dir / "SUMMARY.md").is_file()
    assert "fixture open failure" in (run_dir / "events.csv").read_text(encoding="utf-8")


def test_serial_import_failure_replaces_in_progress_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    _mock_ready_host(monkeypatch)
    real_import = builtins.__import__

    def fail_serial_import(name, *args, **kwargs):
        if name == "serial":
            raise ImportError("fixture import failure")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_serial_import)
    with pytest.raises(ImportError, match="fixture import failure"):
        physical.run_experiment(_run_args(tmp_path, tmp_path / "commands.txt"))
    run_dir = next(tmp_path.glob("run_*"))
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["status"] == "failed"
    assert "fixture import failure" in provenance["failure"]
    assert (run_dir / "SUMMARY.md").is_file()


def test_output_open_failure_replaces_in_progress_and_closes_partial_stack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_ready_host(monkeypatch)
    real_open = Path.open

    def fail_serial_log(path: Path, *args, **kwargs):
        if path.name == "serial.log":
            raise OSError("fixture artifact open failure")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_serial_log)
    with pytest.raises(OSError, match="fixture artifact open failure"):
        physical.run_experiment(_run_args(tmp_path, tmp_path / "commands.txt"))
    run_dir = next(tmp_path.glob("run_*"))
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["status"] == "failed"
    assert "fixture artifact open failure" in provenance["failure"]
    assert (run_dir / "SUMMARY.md").is_file()


def test_output_close_failure_replaces_in_progress_before_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import serial

    _mock_ready_host(monkeypatch)
    real_open = Path.open

    class CloseFailFile:
        def __init__(self, inner):
            self.inner = inner

        def __enter__(self):
            return self

        def __exit__(self, *exc_details):
            self.inner.close()
            raise OSError("fixture artifact close failure")

        def __getattr__(self, name):
            return getattr(self.inner, name)

    def wrap_raw(path: Path, *args, **kwargs):
        handle = real_open(path, *args, **kwargs)
        return CloseFailFile(handle) if path.name == "serial.raw" else handle

    monkeypatch.setattr(Path, "open", wrap_raw)
    monkeypatch.setattr(
        serial, "Serial",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("fixture body failure")),
    )
    with pytest.raises(OSError, match="fixture artifact close failure"):
        physical.run_experiment(_run_args(tmp_path, tmp_path / "commands.txt"))
    run_dir = next(tmp_path.glob("run_*"))
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["status"] == "failed"
    assert "fixture artifact close failure" in provenance["failure"]
    assert (run_dir / "SUMMARY.md").is_file()


def test_serial_close_failure_is_finalized_before_it_is_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import serial

    class FakeSerial:
        def __init__(self, *args, **kwargs):
            self.timeout = 1
            self.lines = [
                b"STATE protocol=asd-quality-v1.3.0 from=NO_MACHINE "
                b"to=NO_MACHINE reason=BOOT_FAIL_CLOSED\n",
                b"STATE protocol=asd-quality-v1.3.0 from=NO_MACHINE "
                b"to=NO_MACHINE reason=INSUFFICIENT_LEVEL\n",
                b"EVENT protocol=asd-quality-v1.3.0 type=FLOW_STOPPED "
                b"state=NO_MACHINE phase=WAIT reason=INSUFFICIENT_LEVEL "
                b"event=NONE capability=AVAILABLE level=MACHINE_PRESENCE\n",
            ]

        def readline(self):
            return self.lines.pop(0) if self.lines else b""

        def close(self):
            raise OSError("fixture serial close failure")

    poll_count = 0

    def poll_stop(path, offset):
        nonlocal poll_count
        poll_count += 1
        return offset, ["stop"] if poll_count == 1 else []

    _mock_ready_host(monkeypatch)
    monkeypatch.setattr(serial, "Serial", FakeSerial)
    monkeypatch.setattr(physical, "poll_command_file", poll_stop)
    with pytest.raises(OSError, match="fixture serial close failure"):
        physical.run_experiment(_run_args(tmp_path, tmp_path / "commands.txt"))
    run_dir = next(tmp_path.glob("run_*"))
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["status"] == "failed"
    assert "fixture serial close failure" in provenance["failure"]


def test_nonempty_command_file_fails_safely_before_serial_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import serial

    _mock_ready_host(monkeypatch)
    command_file = tmp_path / "commands.txt"
    command_file.write_text("stop\n", encoding="utf-8")
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("serial must not open")

    monkeypatch.setattr(serial, "Serial", unexpected_open)
    with pytest.raises(RuntimeError, match="mora biti nov ili prazan"):
        physical.run_experiment(_run_args(tmp_path, command_file))
    assert opened is False
    run_dir = next(tmp_path.glob("run_*"))
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["status"] == "failed"
    assert (run_dir / "SUMMARY.md").is_file()


def test_stop_drains_buffered_terminal_telemetry_and_bad_condition_does_not_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import serial

    lines = [
        "STATE protocol=asd-quality-v1.3.0 from=NO_MACHINE to=NO_MACHINE "
        "reason=BOOT_FAIL_CLOSED\n",
        "STATE protocol=asd-quality-v1.3.0 from=NO_MACHINE to=NO_MACHINE "
        "reason=INSUFFICIENT_LEVEL\n",
        "EVENT protocol=asd-quality-v1.3.0 type=FLOW_STOPPED state=NO_MACHINE "
        "phase=WAIT reason=INSUFFICIENT_LEVEL "
        "event=NONE capability=AVAILABLE level=MACHINE_PRESENCE\n",
    ]

    class FakeSerial:
        def __init__(self, *args, **kwargs):
            self.timeout = kwargs.get("timeout", 1)
            self.lines = [line.encode("ascii") for line in lines]
            self.closed = False

        def readline(self):
            return self.lines.pop(0) if self.lines else b""

        def close(self):
            self.closed = True

    fake_instances: list[FakeSerial] = []

    def open_fake(*args, **kwargs):
        instance = FakeSerial(*args, **kwargs)
        fake_instances.append(instance)
        return instance

    poll_count = 0

    def poll_once(path, offset):
        nonlocal poll_count
        poll_count += 1
        return offset, ["condition ///", "stop"] if poll_count == 1 else []

    _mock_ready_host(monkeypatch)
    monkeypatch.setattr(serial, "Serial", open_fake)
    monkeypatch.setattr(physical, "poll_command_file", poll_once)
    rc = physical.run_experiment(_run_args(tmp_path, tmp_path / "commands.txt"))
    assert rc == 1
    assert fake_instances and fake_instances[0].closed is True
    run_dir = next(tmp_path.glob("run_*"))
    raw = (run_dir / "serial.raw").read_text(encoding="ascii")
    assert "BOOT_FAIL_CLOSED" in raw
    assert "FLOW_STOPPED" in raw
    events = (run_dir / "events.csv").read_text(encoding="utf-8")
    assert "command_error" in events
    assert "terminal_drain_complete" in events
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["status"] == "invalid_firmware_terminal"
    state = provenance["firmware_protocol_state"]
    assert state["terminal_state_seen"] is True
    assert state["terminal_event_seen"] is True


def test_run_experiment_dispatches_temporal_and_completes_valid_protocol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regresija za stvarnu serijsku petlju, ne samo cisti state-machine."""
    import serial

    q = physical.QUALITY_PROTOCOL_VERSION
    lines = [
        f"STATE protocol={q} from=NO_MACHINE to=NO_MACHINE reason=BOOT_FAIL_CLOSED",
        f"SESSION protocol={q} action=STARTED source=BUTTON "
        "reason=OPERATOR_REQUEST discards_calibration=0",
    ]
    for index in range(1, 61):
        lines.append(
            f"QUALITY protocol={q} phase=WAIT index={index} total=60 result=OK "
            "metrics_valid=1 samples=4096 expected=4096 rms_dbfs=-30.000 "
            "dc=0.000 peak=1100 clipped=0 zeros=0 stuck=0 dropped_delta=0 "
            "feature_valid=0 tonalness_valid=0 tonalness_proxy=0.000000 "
            "tonal_gate=not_computed"
        )
    for index in range(1, 11):
        lines.append(
            f"QUALITY protocol={q} phase=CAL index={index} total=10 result=OK "
            "metrics_valid=1 samples=159744 expected=159744 rms_dbfs=-30.000 "
            "dc=0.000 peak=1100 clipped=0 zeros=0 stuck=0 dropped_delta=0 "
            "feature_valid=1 tonalness_valid=1 tonalness_proxy=1.000000 "
            "tonal_gate=pending_normal_only"
        )
    lines.extend([
        f"QUALITY protocol={q} phase=CAL_SUMMARY result=OBSERVED "
        "loo_mean=1.000000 loo_sd=0.200000 loo_cv=0.200000 "
        "loo_range=0.500000 loo_gate=pending_normal_only",
        "ADAPTTHR n=10 mean=1.000000 sd=0.200000 k=0 theta=0 p=0.9000 "
        "thr=1.60000002 lo=0.000000 factory=0.000000",
        f"PRESENCE protocol={q} level_mean_dbfs=-30 margin_db=11 "
        "gate_dbfs=-41 min_consecutive=3",
        f"TEMPORAL protocol={q} policy=asd-temporal-policy-v1.0.0 "
        "min_consecutive=3 ewma_alpha=0 enter_scale=1 exit_scale=0.7 fast_scale=0",
        f"STATE protocol={q} from=NO_MACHINE to=CALIBRATED_NORMAL "
        "reason=CALIBRATION_ACCEPTED",
        f"EVENT protocol={q} type=CALIBRATION_ACCEPTED state=CALIBRATED_NORMAL "
        "phase=CAL reason=QUALITY_OK event=NONE capability=AVAILABLE level=DEVIATION",
        f"QUALITY protocol={q} phase=DET index=1 total=0 result=OK "
        "metrics_valid=1 samples=159744 expected=159744 rms_dbfs=-30.000 "
        "dc=0.000 peak=1100 clipped=0 zeros=0 stuck=0 dropped_delta=0 "
        "feature_valid=1 tonalness_valid=1 tonalness_proxy=1.000000 "
        "tonal_gate=pending_normal_only",
        "DET 1 score=0.5 lo=0 hi=1.60000002 led=1 anom=0 total_anom=0 "
        "normal (uzastopnih=0 nivo=-30.0 dBFS racun=700 ms)",
    ])

    class FakeSerial:
        def __init__(self, *args, **kwargs):
            self.timeout = kwargs.get("timeout", 1)
            self.lines = [(line + "\n").encode("ascii") for line in lines]
            self.closed = False

        def readline(self):
            return self.lines.pop(0) if self.lines else b""

        def close(self):
            self.closed = True

    fake_instances: list[FakeSerial] = []

    def open_fake(*args, **kwargs):
        instance = FakeSerial(*args, **kwargs)
        fake_instances.append(instance)
        return instance

    condition_sent = False
    stop_sent = False

    def poll_until_consumed(path, offset):
        nonlocal condition_sent, stop_sent
        if not condition_sent:
            condition_sent = True
            return offset, ["condition normal_baseline"]
        if fake_instances and not fake_instances[0].lines and not stop_sent:
            stop_sent = True
            return offset, ["stop"]
        return offset, []

    _mock_ready_host(monkeypatch)
    monkeypatch.setattr(serial, "Serial", open_fake)
    monkeypatch.setattr(physical, "poll_command_file", poll_until_consumed)
    rc = physical.run_experiment(_run_args(tmp_path, tmp_path / "commands.txt"))

    assert rc == 0
    assert fake_instances and fake_instances[0].closed is True
    run_dir = next(tmp_path.glob("run_*"))
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["status"] == "completed_by_operator"
    assert provenance["firmware_telemetry_counts"]["TEMPORAL"] == 1
    state = provenance["firmware_protocol_state"]
    assert state["temporal_seen"] is True
    assert physical.firmware_protocol_complete(state)
    assert provenance["valid_det_window_count"] == 1


def test_final_buffer_drain_is_bounded_by_quiet_or_total_time() -> None:
    assert physical.final_buffer_drain_decision(0.1, 0.01) == "continue"
    assert physical.final_buffer_drain_decision(
        0.1, physical.FINAL_BUFFER_QUIET_S,
    ) == "complete"
    assert physical.final_buffer_drain_decision(
        physical.FINAL_BUFFER_DRAIN_TIMEOUT_S, 0.0,
    ) == "complete"


def test_summary_never_calls_zero_det_run_valid() -> None:
    summary = physical.make_summary(
        metadata={
            "fan_id": "fan01", "session_id": "s1", "port": "COM3", "baud": 115200,
            "distance_cm": 10, "room": "lab",
        },
        status="completed_by_operator", events=[], detections=[], max_dropped=None,
    )
    assert "Validan fizički rezultat: **NE**" in summary


# --- Faza 2 u zivom toku: prisustvo, semantika dogadjaja, operaterski zapisi ---

def test_presence_record_is_required_before_any_det() -> None:
    """Bez objavljenog gate-a host ne moze nezavisno ponoviti odluku Faze 2."""
    state = physical.new_firmware_protocol_state()
    state = physical.transition_firmware_protocol(state, {
        "kind": "STATE", "from_state": "NO_MACHINE", "to_state": "NO_MACHINE",
        "reason": "BOOT_FAIL_CLOSED",
    })
    for phase, count in physical.EXPECTED_QUALITY_COUNTS.items():
        for index in range(1, count + 1):
            state = physical.transition_firmware_protocol(state, _quality(phase, index))
    state = physical.transition_firmware_protocol(state, _adapt())
    assert not physical.firmware_protocol_ready(state)
    assert state["presence_seen"] is False


def test_presence_must_follow_adapt_and_precede_acceptance() -> None:
    early = physical.transition_firmware_protocol(_handshake_state(), _presence())
    assert early["invalid_reason"] == "PRESENCE_before_ADAPTTHR"

    twice = physical.transition_firmware_protocol(_ready_protocol_state(), _presence())
    assert twice["invalid_reason"] == "duplicate_PRESENCE"

    # Gate poslije prihvacene kalibracije: nedostizno u praksi jer prihvatanje
    # trazi PRESENCE, ali se cuva kao odbrana u dubinu i zato se provjerava.
    replayed = {**_ready_protocol_state(), "presence_seen": False}
    out = physical.transition_firmware_protocol(replayed, _presence())
    assert out["invalid_reason"] == "PRESENCE_after_calibration_acceptance"


def test_presence_margin_must_match_the_locked_policy() -> None:
    state = _handshake_state()
    for phase, count in physical.EXPECTED_QUALITY_COUNTS.items():
        for index in range(1, count + 1):
            state = physical.transition_firmware_protocol(state, _quality(phase, index))
    state = physical.transition_firmware_protocol(state, _adapt())
    tampered = dict(_presence())
    tampered["margin_db"] = 3.0
    tampered["gate_dbfs"] = tampered["level_mean_dbfs"] - 3.0
    out = physical.transition_firmware_protocol(state, tampered)
    assert out["invalid_reason"] == "PRESENCE_margin_off_policy"


def test_presence_gate_arithmetic_is_checked_at_parse_time() -> None:
    bad = physical.parse_serial_line(
        "PRESENCE protocol=asd-quality-v1.3.0 level_mean_dbfs=-30 margin_db=11 "
        "gate_dbfs=-35 min_consecutive=3"
    )
    assert bad["kind"] == "PARSE_ERROR"
    assert bad["reason"] == "presence_gate_inconsistent"


def test_level_below_gate_suppresses_deviation_instead_of_alarming() -> None:
    """Kad masina utihne score skoci (08.08: 10 -> 59). Brojac odstupanja se
    resetuje, a stanje se drzi -- anomalija koja ne postoji se ne emituje."""
    state = _ready_protocol_state()          # gate = -41 dBFS
    state = physical.transition_firmware_protocol(state, _quality("DET", 1))
    quiet = _det(window=1, score=3.0, threshold=1.6, led=1, alarm=0,
                 total_alarm=0, consecutive=0, verdict="iznad praga")
    quiet["level_dbfs"] = -55.0
    state = physical.transition_firmware_protocol(state, quiet)
    assert state["invalid_status"] is None
    assert state["deviation_run"] == 0
    assert state["absent_run"] == 1
    assert state["expected_state_transition"] is None


def test_sustained_absence_requires_the_presence_lost_pair() -> None:
    state = _ready_protocol_state()
    for window in (1, 2, 3):
        state = physical.transition_firmware_protocol(state, _quality("DET", window))
        row = _det(window=window, score=0.5, threshold=1.6, led=1, alarm=0,
                   total_alarm=0, consecutive=0, verdict="normal")
        row["level_dbfs"] = -55.0
        state = physical.transition_firmware_protocol(state, row)
        assert state["invalid_status"] is None
    assert state["absent_run"] == 3
    expected = state["expected_state_transition"]
    assert expected["state"] == {
        "from_state": "CALIBRATED_NORMAL", "to_state": "NO_MACHINE",
        "reason": "PRESENCE_LOST",
    }
    assert expected["event"]["type"] == "PRESENCE_LOST"


def test_presence_lost_without_a_level_drop_is_rejected() -> None:
    """Firmware ne smije tvrditi da masine nema ako nivo to ne pokazuje."""
    state = physical.transition_firmware_protocol(_ready_protocol_state(), {
        "kind": "STATE", "from_state": "CALIBRATED_NORMAL",
        "to_state": "NO_MACHINE", "reason": "PRESENCE_LOST",
    })
    assert state["invalid_reason"] == "spurious_PRESENCE_LOST"


def test_reserved_event_cannot_appear_on_the_wire() -> None:
    """Kapabilitetni gate: MECHANICAL_ANOMALY trazi Fazu 6 i ne smije se emitovati."""
    parsed = physical.parse_serial_line(
        "EVENT protocol=asd-quality-v1.3.0 type=ANOMALY_ENTERED state=ANOMALY "
        "phase=DET reason=THRESHOLD_PERSISTENCE event=MECHANICAL_ANOMALY "
        "capability=NEEDS_TRANSIENT level=DEVIATION"
    )
    assert parsed["kind"] == "PARSE_ERROR"
    assert parsed["reason"] == "reserved_event_emitted:MECHANICAL_ANOMALY"


def test_reserved_event_relabelled_as_available_is_still_rejected() -> None:
    parsed = physical.parse_serial_line(
        "EVENT protocol=asd-quality-v1.3.0 type=ANOMALY_ENTERED state=ANOMALY "
        "phase=DET reason=THRESHOLD_PERSISTENCE event=SPEED_CHANGED "
        "capability=AVAILABLE level=DEVIATION"
    )
    assert parsed["kind"] == "PARSE_ERROR"
    assert parsed["reason"] == "reserved_event_emitted:SPEED_CHANGED"


def test_event_without_faza2_fields_is_a_protocol_error() -> None:
    parsed = physical.parse_serial_line(
        "EVENT protocol=asd-quality-v1.3.0 type=FLOW_STOPPED state=NO_MACHINE "
        "phase=WAIT reason=INSUFFICIENT_LEVEL"
    )
    assert parsed["kind"] == "PARSE_ERROR"
    assert parsed["reason"].startswith("missing_fields:")


def test_button_record_never_breaks_the_det_pair() -> None:
    """BUTTON pise zaseban UI task; pritisak u pogresnoj milisekundi ne smije
    ponistiti inace ispravan prolaz."""
    state = _ready_protocol_state()
    state = physical.transition_firmware_protocol(state, _quality("DET", 1))
    assert state["pending_det_quality"] == 1
    button = physical.parse_serial_line(
        "BUTTON protocol=asd-quality-v1.3.0 event=LONG mode=READY "
        "command=START_LEARNING discards=1"
    )
    assert button["kind"] == "BUTTON"
    state = physical.transition_firmware_protocol(state, button)
    assert state["invalid_status"] is None
    assert state["pending_det_quality"] == 1
    state = physical.transition_firmware_protocol(state, _det(window=1, threshold=1.6))
    assert state["invalid_status"] is None


def test_short_press_claiming_a_discard_is_a_protocol_error() -> None:
    parsed = physical.parse_serial_line(
        "BUTTON protocol=asd-quality-v1.3.0 event=SHORT mode=READY "
        "command=START_LEARNING discards=1"
    )
    assert parsed["kind"] == "PARSE_ERROR"
    assert parsed["reason"] == "short_press_discarded_calibration"


def test_session_records_must_be_paired() -> None:
    started = physical.parse_serial_line(
        "SESSION protocol=asd-quality-v1.3.0 action=STARTED source=BUTTON "
        "reason=OPERATOR_REQUEST discards_calibration=0"
    )
    assert started["kind"] == "SESSION"
    state = physical.transition_firmware_protocol(
        physical.new_firmware_protocol_state(), started)
    assert state["session_started"] is True and state["sessions"] == 1
    assert physical.transition_firmware_protocol(
        state, started)["invalid_reason"] == "SESSION_STARTED_twice"

    orphan = physical.parse_serial_line(
        "SESSION protocol=asd-quality-v1.3.0 action=ENDED source=FIRMWARE "
        "reason=NO_MACHINE discards_calibration=0"
    )
    out = physical.transition_firmware_protocol(
        physical.new_firmware_protocol_state(), orphan)
    assert out["invalid_reason"] == "SESSION_ENDED_without_START"


def test_autostart_session_source_is_rejected() -> None:
    parsed = physical.parse_serial_line(
        "SESSION protocol=asd-quality-v1.3.0 action=STARTED source=AUTOSTART "
        "reason=BOOT_GRACE_EXPIRED discards_calibration=0"
    )
    assert parsed["kind"] == "PARSE_ERROR"
    assert parsed["reason"] == "unknown_session_source:AUTOSTART"


def test_button_only_firmware_checks_ui_task_creation() -> None:
    source = (
        ROOT / "firmware" / "esp32s3_asd" / "main" / "psd_live.c"
    ).read_text(encoding="utf-8")
    assert "BaseType_t ui_task_result" in source
    assert "if (ui_task_result != pdPASS)" in source
    assert "ESP_ERROR_CHECK(ESP_ERR_NO_MEM);" in source
    assert "AUTOSTART" not in source
    assert "BOOT_GRACE_EXPIRED" not in source


def test_unknown_operator_tokens_are_protocol_errors() -> None:
    cases = [
        ("SESSION protocol=asd-quality-v1.3.0 action=RESUMED source=BUTTON "
         "reason=X discards_calibration=0", "unknown_session_action:RESUMED"),
        ("SESSION protocol=asd-quality-v1.3.0 action=STARTED source=TIMER "
         "reason=X discards_calibration=0", "unknown_session_source:TIMER"),
        ("BUTTON protocol=asd-quality-v1.3.0 event=DOUBLE mode=IDLE "
         "command=NONE discards=0", "unknown_button_event:DOUBLE"),
        ("BUTTON protocol=asd-quality-v1.3.0 event=LONG mode=SLEEPING "
         "command=NONE discards=0", "unknown_button_mode:SLEEPING"),
        ("BUTTON protocol=asd-quality-v1.3.0 event=LONG mode=IDLE "
         "command=RECALIBRATE discards=0", "unknown_button_command:RECALIBRATE"),
    ]
    for line, expected in cases:
        parsed = physical.parse_serial_line(line)
        assert parsed["kind"] == "PARSE_ERROR", line
        assert parsed["reason"] == expected
