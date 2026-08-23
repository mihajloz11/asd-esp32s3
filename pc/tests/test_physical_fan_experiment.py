from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "pc" / "tools" / "physical_fan_experiment.py"
SPEC = importlib.util.spec_from_file_location("physical_fan_experiment", MODULE_PATH)
assert SPEC and SPEC.loader
physical = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(physical)


def _research_vector() -> np.ndarray:
    return np.linspace(-2.0, 3.0, 96, dtype=np.float32)


def _research_line(
    kind: str, *, phase: str = "CAL", window: int = 1, group: int | None = None,
    corrupt_checksum: bool = False,
) -> str:
    vector = _research_vector()
    checksum = physical.fnv1a_bytes(vector.astype("<f4").tobytes())
    if corrupt_checksum:
        checksum ^= 1
    values = ",".join(format(float(item), ".9g") for item in vector)
    common = (
        f"protocol={physical.RESEARCH_PROTOCOL_VERSION} session=1 phase={phase} "
        f"window={window} "
    )
    if kind == "FEATURE96":
        body = (
            "window_start_ms=1000 window_end_ms=10984 score=0 "
            "level_dbfs=-31.25 quality=OK tonalness_proxy=3 "
            f"dims=96 fnv1a={checksum:08x} values={values}"
        )
    else:
        assert group is not None
        body = (
            f"group={group} segments={physical.RESEARCH_GROUP_SEGMENTS[group - 1]} "
            f"dims=96 fnv1a={checksum:08x} values={values}"
        )
    return f"{kind} {common}{body}"


def _research_quality() -> dict:
    return {
        "kind": "QUALITY", "phase": "CAL", "index": 1, "result": "OK",
        "feature_valid": 1, "rms_dbfs": -31.25, "tonalness_proxy": 3.0,
    }


def _profile_store_line(**changes: object) -> str:
    fields: dict[str, object] = {
        "protocol": physical.QUALITY_PROTOCOL_VERSION,
        "schema": physical.PROFILE_STORE_SCHEMA_VERSION,
        "result": "LOADED",
        "generation": 7,
        "fingerprint": physical.PSD_MODEL_FINGERPRINT_HEX,
        "crc32": "1a2b3c4d",
        "threshold_enter": 900,
        "threshold_exit": 600,
        "center_windows": 10,
        "derive_windows": physical.RUNTIME_COMMISSIONING_POLICY["derive_windows"],
        "verify_windows": physical.RUNTIME_COMMISSIONING_POLICY["verify_windows"],
        "profile_policy_version": physical.PROFILE_POLICY_VERSION,
        **physical.PROFILE_POLICY_IDS,
        "derive_mean": 400,
        "derive_sd": 20,
        "verify_alarm_time_percent": 0,
        "verify_alarm_windows": 0,
        "verify_episodes": 0,
        "verify_chatter": 0,
    }
    fields.update(changes)
    return "PROFILESTORE " + " ".join(
        f"{key}={value}" for key, value in fields.items()
    )


def _consume_complete_research_package(state: dict) -> list[str]:
    lines = [_research_line("FEATURE96")]
    lines.extend(_research_line("SUBSEG96", group=group) for group in range(1, 6))
    for line in lines:
        parsed = physical.parse_serial_line(line)
        assert parsed is not None and parsed["kind"] != "PARSE_ERROR"
        physical.research_consume_record(state, parsed, active_session=1)
    return lines


def test_research_feature_and_subsegment_parser_checks_dimension_checksum_and_metadata() -> None:
    feature = physical.parse_serial_line(_research_line("FEATURE96"))
    subsegment = physical.parse_serial_line(_research_line("SUBSEG96", group=5))
    assert feature is not None and feature["kind"] == "FEATURE96"
    assert feature["values"].shape == (96,)
    assert feature["window_start_ms"] == 1000
    assert feature["window_end_ms"] == 10984
    assert subsegment is not None and subsegment["kind"] == "SUBSEG96"
    assert subsegment["group"] == 5
    assert subsegment["segments"] == 7

    damaged = physical.parse_serial_line(
        _research_line("FEATURE96", corrupt_checksum=True)
    )
    assert damaged is not None and damaged["kind"] == "PARSE_ERROR"
    assert damaged["reason"] == "research_checksum_mismatch"


def test_research_artifact_npz_manifest_shapes_hash_and_external_wav_link(tmp_path: Path) -> None:
    state = physical.new_research_telemetry_state(required=True)
    physical.research_expect_quality(state, _research_quality(), session=1)
    lines = _consume_complete_research_package(state)
    wav = tmp_path / "external.wav"
    wav.write_bytes(b"external-recorder-fixture")
    metadata = {
        "external_wav": str(wav.resolve()),
        "external_wav_sha256_at_start": physical.sha256_file(wav),
        "external_wav_sha256_at_end": physical.sha256_file(wav),
    }
    manifest = physical.write_research_artifact(tmp_path, state, metadata=metadata)

    assert manifest["artifact_valid"] is True
    assert manifest["complete_window_count"] == 1
    assert manifest["feature_record_count"] == 1
    assert manifest["subsegment_record_count"] == 5
    assert manifest["external_wav"]["relationship"] == (
        "linked_external_file_not_recorded_by_host"
    )
    assert manifest["npz"]["sha256"] == physical.sha256_file(
        tmp_path / "window_features.npz"
    )
    with np.load(tmp_path / "window_features.npz", allow_pickle=False) as artifact:
        assert artifact["feature96"].shape == (1, 96)
        assert artifact["subseg96"].shape == (1, 5, 96)
        assert artifact["subseg_welch_segments"].tolist() == [[8, 8, 8, 7, 7]]
        assert np.isfinite(artifact["feature96"]).all()
        assert np.isfinite(artifact["subseg96"]).all()
    # 115200 UART, 10 bits/bajt. Prosjecni 10 s budzet i burst oba imaju rezervu.
    wire_bytes = sum(len((line + "\n").encode("ascii")) for line in lines)
    assert 115200 / (wire_bytes * 10 / 10.0) > 10.0
    assert wire_bytes * 10 / 115200 < 1.0


@pytest.mark.parametrize("failure", ["missing", "duplicate", "malformed"])
def test_required_research_artifact_rejects_missing_duplicate_and_malformed(
    tmp_path: Path, failure: str,
) -> None:
    run_dir = tmp_path / failure
    run_dir.mkdir()
    state = physical.new_research_telemetry_state(required=True)
    physical.research_expect_quality(state, _research_quality(), session=1)
    if failure == "duplicate":
        _consume_complete_research_package(state)
        parsed = physical.parse_serial_line(_research_line("FEATURE96"))
        assert parsed is not None
        physical.research_consume_record(state, parsed, active_session=1)
    elif failure == "malformed":
        parsed = physical.parse_serial_line(
            _research_line("FEATURE96", corrupt_checksum=True)
        )
        assert parsed is not None and parsed["kind"] == "PARSE_ERROR"
        physical.research_consume_record(state, parsed, active_session=1)
    manifest = physical.write_research_artifact(run_dir, state, metadata={})
    assert manifest["artifact_valid"] is False
    assert manifest["gate_passed"] is False
    assert manifest["errors"]


def test_live_research_path_has_no_per_det_pcm_dump_and_preserves_pair_order() -> None:
    source = (ROOT / "firmware" / "esp32s3_asd" / "main" / "psd_live.c").read_text(
        encoding="utf-8",
    )
    assert "asd_dump_pcm_block(" not in source
    quality = source.index('emit_quality("DET"')
    det = source.index('printf("DET %d score=', quality)
    research = source.index('emit_research_window(session_index, "DET"', det)
    assert quality < det < research


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
        "ADAPTTHR n=10 mean=10 sd=2 k=0 theta=0 p=.99 thr=16.125 lo=0 factory=0"
    ) == {
        "kind": "ADAPTTHR", "n": 10, "mean": 10.0, "sd": 2.0,
            "k": 0.0, "theta": 0.0, "p": 0.99, "threshold": 16.125,
        "lo": 0.0, "factory": 0.0,
    }
    assert physical.parse_serial_line(
        "I psdlive: racun po klipu 704 ms, dropped=0"
    ) == {"kind": "DROPPED", "dropped": 0}


def test_parse_quality_state_event_v1_telemetry() -> None:
    quality = physical.parse_serial_line(
        "I psdlive: QUALITY protocol=asd-quality-v1.4.0 phase=CAL index=2 total=10 "
        "result=OK metrics_valid=1 samples=159744 expected=159744 "
        "rms_dbfs=-31.250 dc=2.5 peak=4100 "
        "clipped=0 zeros=3 stuck=7 dropped_delta=0 feature_valid=1 tonalness_proxy=1.125 "
        "tonalness_valid=1 tonal_gate=pending_normal_only"
    )
    assert quality == {
        "kind": "QUALITY", "protocol": "asd-quality-v1.4.0", "phase": "CAL",
        "index": 2, "total": 10, "result": "OK", "samples": 159744,
        "metrics_valid": 1, "feature_valid": 1,
        "expected": 159744, "rms_dbfs": -31.25, "dc": 2.5, "peak": 4100,
        "clipped": 0, "zeros": 3, "stuck": 7, "dropped_delta": 0,
        "tonalness_proxy": 1.125, "tonalness_valid": 1,
        "tonal_gate": "pending_normal_only",
    }
    assert physical.parse_serial_line(
        "STATE protocol=asd-quality-v1.4.0 from=NO_MACHINE "
        "to=CALIBRATION_REJECTED reason=CLIPPING"
    ) == {
        "kind": "STATE", "protocol": "asd-quality-v1.4.0",
        "from_state": "NO_MACHINE", "to_state": "CALIBRATION_REJECTED",
        "reason": "CLIPPING",
    }
    assert physical.parse_serial_line(
        "EVENT protocol=asd-quality-v1.4.0 type=FLOW_STOPPED "
        "state=SENSOR_ERROR phase=CAL reason=DROPPED_SAMPLES "
        "event=SENSOR_FAULT capability=AVAILABLE level=SENSOR_HEALTH"
    ) == {
        "kind": "EVENT", "protocol": "asd-quality-v1.4.0",
        "type": "FLOW_STOPPED", "state": "SENSOR_ERROR", "phase": "CAL",
        "reason": "DROPPED_SAMPLES", "event": "SENSOR_FAULT",
        "capability": "AVAILABLE", "level": "SENSOR_HEALTH",
    }


def test_quality_protocol_is_strict_and_operator_truth_is_separate() -> None:
    assert physical.PROTOCOL_VERSION == "physical-fan-v1.8.0"
    assert physical.LEGACY_READ_PROTOCOL_VERSIONS == frozenset({
        "physical-fan-v1.6.0", "physical-fan-v1.7.0",
    })
    assert physical.SUPPORTED_READ_PROTOCOL_VERSIONS == frozenset({
        "physical-fan-v1.6.0", "physical-fan-v1.7.0",
        "physical-fan-v1.8.0",
    })
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


@pytest.mark.parametrize("result", ["AUDIO_TIMEOUT", "AUDIO_READ_ERROR"])
def test_literal_v15_audio_read_failure_is_fail_closed_sensor_error(result: str) -> None:
    protocol = physical.QUALITY_PROTOCOL_VERSION
    state = physical.new_firmware_protocol_state()
    lines = [
        f"SESSION protocol={protocol} action=STARTED source=BUTTON "
        "reason=OPERATOR_REQUEST discards_calibration=0",
        f"STATE protocol={protocol} from=NO_MACHINE to=NO_MACHINE "
        "reason=BOOT_FAIL_CLOSED",
        f"QUALITY protocol={protocol} phase=WAIT index=1 total=60 result={result} "
        "metrics_valid=0 samples=0 expected=4096 rms_dbfs=-999 dc=0 peak=0 "
        "clipped=0 zeros=0 stuck=0 dropped_delta=0 feature_valid=0 "
        "tonalness_proxy=0 tonalness_valid=0 tonal_gate=not_computed",
    ]
    for line in lines:
        parsed = physical.parse_serial_line(line)
        assert parsed is not None and parsed["kind"] != "PARSE_ERROR"
        state = physical.transition_firmware_protocol(state, parsed)
    assert state["invalid_status"] == "invalid_firmware_terminal"
    assert state["drain_expected_state"] == "SENSOR_ERROR"
    assert state["drain_expected_reason"] == result


def test_development_profile_restore_and_profile_store_are_fail_closed() -> None:
    protocol = physical.QUALITY_PROTOCOL_VERSION
    assert physical.PROFILE_PERSISTENCE_ALLOWED is False

    state = physical.new_firmware_protocol_state()
    restored_session = physical.parse_serial_line(
        f"SESSION protocol={protocol} action=STARTED source=FIRMWARE "
        "reason=PROFILE_RESTORED discards_calibration=0"
    )
    assert restored_session is not None
    rejected = physical.transition_firmware_protocol(state, restored_session)
    assert rejected["invalid_reason"] == "PROFILE_RESTORED_persistence_disabled"

    state = _handshake_state()
    store = physical.parse_serial_line(_profile_store_line())
    assert store is not None and store["kind"] == "PROFILESTORE"
    rejected = physical.transition_firmware_protocol(state, store)
    assert rejected["invalid_reason"] == "PROFILESTORE_persistence_disabled"


def test_fake_restore_state_fails_and_missing_store_relearns() -> None:
    protocol = physical.QUALITY_PROTOCOL_VERSION
    state = _handshake_state()
    state = physical.transition_firmware_protocol(state, {
        "kind": "STATE", "protocol": protocol,
        "from_state": "NO_MACHINE", "to_state": "CALIBRATED_NORMAL",
        "reason": "PROFILE_RESTORED",
    })
    assert state["invalid_reason"] == "PROFILE_RESTORED_without_valid_PROFILESTORE"

    # Missing/corrupt DEVELOPMENT blob is not loaded.  The operator starts a
    # fresh session and the ordinary commissioning path accepts its first WAIT.
    relearn = physical.new_firmware_protocol_state()
    for record in (
        {"kind": "SESSION", "protocol": protocol, "action": "STARTED",
         "source": "BUTTON", "reason": "OPERATOR_REQUEST",
         "discards_calibration": 0},
        {"kind": "STATE", "protocol": protocol, "from_state": "NO_MACHINE",
         "to_state": "NO_MACHINE", "reason": "BOOT_FAIL_CLOSED"},
        _quality("WAIT", 1),
    ):
        relearn = physical.transition_firmware_protocol(relearn, record)
    assert relearn["invalid_status"] is None
    assert relearn["quality_counts"]["WAIT"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"schema": "asd-profile-v9"},
        {"fingerprint": "00" * 32},
        {"generation": 0},
        {"crc32": "xyz"},
        {"threshold_exit": 900},
        {"center_windows": 0},
        {"quality_policy_id": 1},
    ],
)
def test_invalid_profile_store_audit_fields_are_rejected(changes: dict) -> None:
    parsed = physical.parse_serial_line(_profile_store_line(**changes))
    assert parsed is not None and parsed["kind"] == "PARSE_ERROR"
    assert parsed["reason"].startswith((
        "profile_store_", "malformed_numeric_field",
    ))


def test_malformed_v1_telemetry_is_audited_not_raised() -> None:
    malformed = physical.parse_serial_line(
        "QUALITY protocol=asd-quality-v1.4.0 phase=CAL index=x total=10 "
        "result=OK samples=10 expected=10 rms_dbfs=-30 dc=0 peak=1 feature_valid=1 "
        "clipped=0 zeros=0 stuck=0 dropped_delta=0 tonalness_proxy=1 "
        "tonal_gate=pending_normal_only"
    )
    assert malformed["kind"] == "PARSE_ERROR"
    assert malformed["reason"] == "malformed_numeric_field"
    truncated = physical.parse_serial_line(
        "STATE protocol=asd-quality-v1.4.0 from=NO_MACHINE to="
    )
    assert truncated["kind"] == "PARSE_ERROR"
    assert truncated["reason"] == "malformed_key_value_token"
    bare = physical.parse_serial_line("QUALITY")
    assert bare["kind"] == "PARSE_ERROR"
    assert bare["reason"] == "invalid_protocol_missing"


def test_duplicate_keys_and_nonfinite_adapt_are_audited() -> None:
    duplicate = physical.parse_serial_line(
        "QUALITY protocol=asd-quality-v1.4.0 phase=WAIT phase=WAIT"
    )
    assert duplicate["kind"] == "PARSE_ERROR"
    assert duplicate["reason"] == "duplicate_key:phase"
    nonfinite = physical.parse_serial_line(
        "ADAPTTHR n=10 mean=inf sd=2 k=0 theta=0 p=.99 thr=16 lo=0 factory=0"
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
        "kind": "ADAPTTHR",
        "n": physical.RUNTIME_COMMISSIONING_POLICY["derive_windows"],
        "mean": 1.0, "sd": 0.2,
        "k": 0.0, "theta": 0.0, "p": 0.99, "threshold": threshold,
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


def _runtime_profile_line(
    *, threshold_enter: float = 1.6, threshold_exit: float = 1.1,
) -> str:
    policy = physical.RUNTIME_COMMISSIONING_POLICY
    return (
        f"PROFILE protocol={physical.QUALITY_PROTOCOL_VERSION} "
        "schema=asd-runtime-profile-v1.0.0-development "
        "policy=asd-commissioning-policy-v1.0.0-development "
        "developmental=1 valid=1 policy_version=1 policy_id=434d5631 "
        f"center_windows={policy['center_windows']} "
        f"derive_windows={policy['derive_windows']} "
        f"verify_windows={policy['verify_windows']} "
        "level_mean_dbfs=-30 tonalness_reference=1 "
        f"threshold_enter={threshold_enter:.9g} threshold_exit={threshold_exit:.9g}"
    )


def _commission_line(
    action: str, phase: str, index: int, total: int, *, score_valid: int = 0,
) -> str:
    score = 1 if score_valid else 0
    return (
        f"COMMISSION protocol={physical.QUALITY_PROTOCOL_VERSION} "
        "policy=asd-commissioning-policy-v1.0.0-development developmental=1 "
        f"action={action} phase={phase} index={index} total={total} result=NONE "
        f"score_valid={score_valid} score={score} level_dbfs=-30 "
        "tonalness_proxy=1 feature_drift=0"
    )


def _fresh_commission_lines() -> tuple[list[str], list[str]]:
    policy = physical.RUNTIME_COMMISSIONING_POLICY
    prefix_lines = [
        _commission_line("STARTED", "SETTLE", 0, policy["max_settle_windows"]),
    ]
    for index in range(1, policy["min_settle_windows"] + 1):
        phase = (
            "CENTER_LEARNING"
            if index == policy["min_settle_windows"] else "SETTLE"
        )
        prefix_lines.append(_commission_line(
            "WINDOW", phase, index, policy["max_settle_windows"],
        ))
    prefix_lines.append(_commission_line(
        "PHASE_ENTERED", "CENTER_LEARNING", 0, policy["center_windows"],
    ))
    suffix_lines = [
        _commission_line(
            "WINDOW", "COMMISSION_DERIVE", index, policy["derive_windows"],
            score_valid=1,
        )
        for index in range(1, policy["derive_windows"] + 1)
    ]
    suffix_lines.extend(
        _commission_line(
            "WINDOW",
            "MONITORING" if index == policy["verify_windows"] else "COMMISSION_VERIFY",
            index, policy["verify_windows"], score_valid=1,
        )
        for index in range(1, policy["verify_windows"] + 1)
    )
    return prefix_lines, suffix_lines


def _fresh_commission_records() -> tuple[list[dict], list[dict]]:
    prefix_lines, suffix_lines = _fresh_commission_lines()

    def parsed(lines: list[str]) -> list[dict]:
        records = [physical.parse_serial_line(line) for line in lines]
        assert all(record is not None and record["kind"] != "PARSE_ERROR" for record in records)
        return records
    return parsed(prefix_lines), parsed(suffix_lines)


def _temporal(
    *, threshold_enter: float = 1.6, threshold_exit: float = 1.1,
) -> dict:
    policy = physical.TEMPORAL_POLICY
    provenance = physical.TEMPORAL_WIRE_PROVENANCE
    line = _temporal_line(
        threshold_enter=threshold_enter, threshold_exit=threshold_exit,
    )
    record = physical.parse_serial_line(line)
    assert record is not None and record["kind"] != "PARSE_ERROR"
    return record


def _temporal_line(
    *, threshold_enter: float = 1.6, threshold_exit: float = 1.1,
) -> str:
    policy = physical.TEMPORAL_POLICY
    provenance = physical.TEMPORAL_WIRE_PROVENANCE
    return (
        f"TEMPORAL protocol={physical.QUALITY_PROTOCOL_VERSION} "
        f"policy={physical.TEMPORAL_POLICY_RECORD['schema_version']} "
        f"min_consecutive={policy['min_consecutive']} "
        f"ewma_alpha={policy['ewma_alpha']} "
        f"enter_scale={provenance['enter_scale']} "
        f"exit_scale={provenance['exit_scale']} fast_scale={policy['fast_scale']} "
        "threshold_mode=absolute_profile "
        f"threshold_enter={threshold_enter:.9g} threshold_exit={threshold_exit:.9g}"
    )


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        (
            _temporal_line().replace(" threshold_exit=1.1", ""),
            "missing_fields:threshold_exit",
        ),
        (_temporal_line() + " extra=1", "unexpected_fields:extra"),
        (
            _temporal_line().replace("absolute_profile", "scaled"),
            "temporal_threshold_mode_mismatch:scaled",
        ),
        (
            _temporal_line().replace(
                physical.TEMPORAL_POLICY_RECORD["schema_version"], "bogus-policy",
            ),
            "temporal_policy_schema_mismatch:bogus-policy",
        ),
        (
            _temporal_line(threshold_enter=1.0, threshold_exit=1.0),
            "temporal_invalid_absolute_thresholds",
        ),
    ],
)
def test_literal_q15_temporal_v2_is_strict(line: str, reason: str) -> None:
    parsed = physical.parse_serial_line(line)
    assert parsed is not None and parsed["kind"] == "PARSE_ERROR"
    assert parsed["reason"] == reason


def test_temporal_v2_must_follow_profile_adapt_and_presence() -> None:
    state = _fresh_profile_state()
    state = physical.transition_firmware_protocol(state, _adapt())
    out = physical.transition_firmware_protocol(state, _temporal())
    assert out["invalid_reason"] == "TEMPORAL_before_PRESENCE"


@pytest.mark.parametrize("line", [_fresh_commission_lines()[0][0], _runtime_profile_line()])
def test_q15_runtime_sidecar_cannot_precede_session_boot(line: str) -> None:
    parsed = physical.parse_serial_line(line)
    assert parsed is not None and parsed["kind"] != "PARSE_ERROR"
    out = physical.transition_firmware_protocol(
        physical.new_firmware_protocol_state(), parsed,
    )
    assert out["invalid_reason"] == f"{parsed['kind']}_without_open_SESSION"


def _fresh_profile_state() -> dict:
    state = _handshake_state()
    commission_prefix, commission_suffix = _fresh_commission_records()
    for record in commission_prefix:
        state = physical.transition_firmware_protocol(state, record)
    for phase, count in physical.EXPECTED_QUALITY_COUNTS.items():
        for index in range(1, count + 1):
            state = physical.transition_firmware_protocol(state, _quality(phase, index))
    for record in commission_suffix:
        state = physical.transition_firmware_protocol(state, record)
    profile = physical.parse_serial_line(_runtime_profile_line())
    assert profile is not None and profile["kind"] == "PROFILE"
    return physical.transition_firmware_protocol(state, profile)


def _ready_protocol_state() -> dict:
    state = _fresh_profile_state()
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
    state = physical.transition_firmware_protocol(
        physical.new_firmware_protocol_state(), {
            "kind": "SESSION", "protocol": physical.QUALITY_PROTOCOL_VERSION,
            "action": "STARTED", "source": "BUTTON",
            "reason": "OPERATOR_REQUEST", "discards_calibration": 0,
        },
    )
    return physical.transition_firmware_protocol(state, {
        "kind": "STATE", "from_state": "NO_MACHINE",
        "to_state": "NO_MACHINE", "reason": "BOOT_FAIL_CLOSED",
    })


def test_literal_firmware_quality_replay_wait_and_reject_contract() -> None:
    wait_line = (
            "QUALITY protocol=asd-quality-v1.5.0 phase=WAIT index=1 total=60 "
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
        "QUALITY protocol=asd-quality-v1.5.0 phase=CAL index=1 total=10 "
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


def test_literal_v14_k1_reject_is_valid_terminal_protocol_without_det() -> None:
    state = _handshake_state()
    for index in range(1, 61):
        state = physical.transition_firmware_protocol(
            state, _quality("WAIT", index),
        )
    for index in range(1, 11):
        state = physical.transition_firmware_protocol(
            state, _quality("CAL", index),
        )
    summary = _quality("CAL_SUMMARY")
    summary.update(loo_sd=0.600001, loo_cv=0.600001, loo_range=1.0)
    state = physical.transition_firmware_protocol(state, summary)
    assert state["invalid_status"] is None

    state_line = (
        f"STATE protocol={physical.QUALITY_PROTOCOL_VERSION} from=NO_MACHINE "
        "to=CALIBRATION_REJECTED reason=UNSTABLE_CALIBRATION"
    )
    event_line = (
        f"EVENT protocol={physical.QUALITY_PROTOCOL_VERSION} type=FLOW_STOPPED "
        "state=CALIBRATION_REJECTED phase=CAL reason=UNSTABLE_CALIBRATION "
        "event=NONE capability=AVAILABLE level=DEVIATION"
    )
    parsed_state = physical.parse_serial_line(state_line)
    parsed_event = physical.parse_serial_line(event_line)
    assert parsed_state is not None and parsed_state["kind"] == "STATE"
    assert parsed_event is not None and parsed_event["kind"] == "EVENT"

    state = physical.transition_firmware_protocol(state, parsed_state)
    assert state["invalid_status"] is None
    assert state["calibration_rejected_state"] is True
    state = physical.transition_firmware_protocol(state, parsed_event)

    assert state["invalid_status"] is None
    assert state["calibration_rejected_event"] is True
    assert physical.firmware_protocol_calibration_rejected(state) is False
    assert physical.firmware_protocol_complete(state) is False
    assert physical.terminal_drain_decision(state, 0.1) == "continue"
    assert physical.terminal_drain_decision(
        state, physical.TERMINAL_DRAIN_TIMEOUT_S,
    ) == "timeout"
    assert physical.terminal_drain_timeout_reason(state) == (
        "terminal_drain_timeout:missing_SESSION_ENDED"
    )

    state = physical.transition_firmware_protocol(state, {
        "kind": "SESSION", "protocol": physical.QUALITY_PROTOCOL_VERSION,
        "action": "ENDED", "source": "FIRMWARE",
        "reason": "SESSION_RETURNED", "discards_calibration": 0,
    })
    assert state["session_started"] is False
    assert state["sessions"] == state["sessions_ended"] == 1
    assert physical.terminal_drain_decision(state, 0.2) == "complete"
    assert physical.firmware_protocol_calibration_rejected(state)
    assert physical.firmware_protocol_complete(state)
    validity = physical.evaluate_run_validity(
        status="completed_calibration_rejected", detections=[],
        protocol_state=state,
    )
    assert validity["protocol_valid"] is True
    assert validity["calibration_accepted"] is False
    assert validity["calibration_acceptance_reason"] == "loo_cv_above_max"
    assert validity["metrics_eligible"] is False
    assert validity["result_status"] == "calibration_rejected:loo_cv_above_max"

    det_after_reject = physical.transition_firmware_protocol(
        state, _quality("DET"),
    )
    assert det_after_reject["invalid_status"] == "invalid_missing_telemetry"
    assert det_after_reject["invalid_reason"] == (
        "QUALITY_without_open_SESSION"
    )


def test_session_started_resets_exact_session_scope_but_preserves_run_scope() -> None:
    state = _handshake_state()
    state.update({
        "sessions": 1,
        "sessions_ended": 1,
        "session_history": [{"firmware_session_index": 1, "protocol_status": "accepted"}],
        "run_quality_counts": {"WAIT": 60, "CAL": 10, "CAL_SUMMARY": 1, "DET": 9},
        "run_det_records": 9,
        "quality_counts": {"WAIT": 60, "CAL": 10, "CAL_SUMMARY": 1, "DET": 9},
        "wait_ok_count": 60,
        "cal_summary": {"loo_mean": 1.0, "loo_sd": 0.2, "loo_cv": 0.2,
                        "loo_range": 0.5},
        "adapt_seen": True,
        "adapt_threshold": 1.6,
        "presence_seen": True,
        "presence_gate_dbfs": -41.0,
        "temporal_seen": True,
        "calibration_accepted_state": True,
        "calibration_accepted_event": True,
        "det_records": 9,
        "last_det_window": 9,
        "last_total_alarm": 4,
        "det_threshold": 1.6,
        "absent_run": 2,
        "deviation_run": 3,
        "anomaly_active": True,
        "terminal": True,
        "last_state": "ANOMALY",
        "session_started": False,
    })

    reset = physical.transition_firmware_protocol(state, {
        "kind": "SESSION", "protocol": physical.QUALITY_PROTOCOL_VERSION,
        "action": "STARTED", "source": "BUTTON",
        "reason": "OPERATOR_REQUEST", "discards_calibration": 1,
    })

    assert reset["handshake"] is True
    assert reset["sessions"] == 2
    assert reset["sessions_ended"] == 1
    assert reset["session_history"] == [
        {"firmware_session_index": 1, "protocol_status": "accepted"},
    ]
    assert reset["run_quality_counts"] == {
        "WAIT": 60, "CAL": 10, "CAL_SUMMARY": 1, "DET": 9,
    }
    assert reset["run_det_records"] == 9
    assert reset["firmware_session_index"] == 2
    assert reset["quality_counts"] == {
        "WAIT": 0, "CAL": 0, "CAL_SUMMARY": 0, "DET": 0,
    }
    assert reset["wait_ok_count"] == 0
    assert reset["cal_summary"] is None
    assert reset["adapt_seen"] is False
    assert reset["adapt_threshold"] is None
    assert reset["presence_seen"] is False
    assert reset["temporal_seen"] is False
    assert reset["calibration_accepted_state"] is False
    assert reset["calibration_accepted_event"] is False
    assert reset["det_records"] == reset["last_det_window"] == 0
    assert reset["last_total_alarm"] == 0
    assert reset["det_threshold"] is None
    assert reset["absent_run"] == reset["deviation_run"] == 0
    assert reset["anomaly_active"] is False
    assert reset["terminal"] is False
    assert reset["session_boot_seen"] is False
    assert reset["last_state"] is None
    assert reset["run_boot_records"] == 1


def test_each_session_requires_exactly_one_boot_after_started() -> None:
    boot = {
        "kind": "STATE", "from_state": "NO_MACHINE", "to_state": "NO_MACHINE",
        "reason": "BOOT_FAIL_CLOSED",
    }
    started = {
        "kind": "SESSION", "protocol": physical.QUALITY_PROTOCOL_VERSION,
        "action": "STARTED", "source": "BUTTON",
        "reason": "OPERATOR_REQUEST", "discards_calibration": 0,
    }
    ended = {
        "kind": "SESSION", "protocol": physical.QUALITY_PROTOCOL_VERSION,
        "action": "ENDED", "source": "FIRMWARE",
        "reason": "SESSION_RETURNED", "discards_calibration": 0,
    }

    before_session = physical.transition_firmware_protocol(
        physical.new_firmware_protocol_state(), boot,
    )
    assert before_session["invalid_reason"] == "BOOT_without_open_SESSION"

    state = physical.transition_firmware_protocol(
        physical.new_firmware_protocol_state(), started,
    )
    before_boot = physical.transition_firmware_protocol(state, _quality("WAIT", 1))
    assert before_boot["invalid_reason"] == "QUALITY_before_session_BOOT"
    ended_before_boot = physical.transition_firmware_protocol(state, ended)
    assert ended_before_boot["invalid_reason"] == "SESSION_ENDED_before_BOOT"

    state = physical.transition_firmware_protocol(state, boot)
    assert state["invalid_status"] is None
    assert state["handshake"] is True
    assert state["session_boot_seen"] is True
    assert state["run_boot_records"] == 1
    duplicate = physical.transition_firmware_protocol(state, boot)
    assert duplicate["invalid_reason"] == "duplicate_BOOT_STATE"

    state = physical.transition_firmware_protocol(state, ended)
    state = physical.transition_firmware_protocol(state, started)
    assert state["handshake"] is True
    assert state["session_boot_seen"] is False
    assert state["last_state"] is None
    state = physical.transition_firmware_protocol(state, boot)
    assert state["invalid_status"] is None
    assert state["firmware_session_index"] == 2
    assert state["run_boot_records"] == 2


def test_v14_host_rejects_threshold_or_acceptance_after_failed_k1() -> None:
    state = _handshake_state()
    for index in range(1, 61):
        state = physical.transition_firmware_protocol(state, _quality("WAIT", index))
    for index in range(1, 11):
        state = physical.transition_firmware_protocol(state, _quality("CAL", index))
    summary = _quality("CAL_SUMMARY")
    summary.update(loo_sd=0.600001, loo_cv=0.600001, loo_range=1.0)
    state = physical.transition_firmware_protocol(state, summary)

    invalid = physical.transition_firmware_protocol(
        state, {
            "kind": "ADAPTTHR", "n": 10, "mean": 1.0, "sd": 0.600001,
            "k": 0.0, "theta": 0.0, "p": 0.99, "threshold": 2.800003,
            "lo": 0.0, "factory": 0.0,
        },
    )
    assert invalid["invalid_status"] == "invalid_firmware_telemetry"
    assert invalid["invalid_reason"] == "ADAPTTHR_after_failed_K1:loo_cv_above_max"


def test_literal_pcm_valid_feature_nonfinite_is_a_firmware_reject() -> None:
    line = (
            "QUALITY protocol=asd-quality-v1.5.0 phase=DET index=1 total=0 "
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
    assert before_handshake["invalid_reason"] == "QUALITY_without_open_SESSION"

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


def test_alarm_windows_episodes_recovery_and_transition_exclusion_are_distinct() -> None:
    rows = [
        {"run_det_index": 1, "elapsed_s": 10.0, "alarm": 0,
         "transition_window": 1},
        {"run_det_index": 2, "elapsed_s": 20.0, "alarm": 1,
         "transition_window": 0},
        {"run_det_index": 3, "elapsed_s": 30.0, "alarm": 1,
         "transition_window": 0},
        {"run_det_index": 4, "elapsed_s": 40.0, "alarm": 1,
         "transition_window": 0},
        {"run_det_index": 5, "elapsed_s": 50.0, "alarm": 0,
         "transition_window": 0},
        {"run_det_index": 6, "elapsed_s": 60.0, "alarm": 1,
         "transition_window": 0},
    ]

    metrics = physical.detection_metrics(rows)

    assert metrics["det_count"] == 5
    assert metrics["alarm_window_count"] == 4
    assert metrics["alarm_entries"] == 2
    assert metrics["alarm_episodes"] == 2
    assert metrics["alarm_window_count"] != metrics["alarm_episodes"]
    assert metrics["alarm_time_percent"] == pytest.approx(100.0 * 4 / 5)
    assert metrics["recovery_latency_s"] == 10.0
    assert metrics["excluded_transition_windows"] == 1


def test_metrics_never_bridge_alarm_episode_or_recovery_across_sessions() -> None:
    two_alarm_sessions = [
        {"firmware_session_index": 1, "run_det_index": 1,
         "elapsed_s": 10.0, "alarm": 1, "transition_window": 0},
        {"firmware_session_index": 1, "run_det_index": 2,
         "elapsed_s": 20.0, "alarm": 1, "transition_window": 0},
        {"firmware_session_index": 2, "run_det_index": 3,
         "elapsed_s": 200.0, "alarm": 1, "transition_window": 0},
        {"firmware_session_index": 2, "run_det_index": 4,
         "elapsed_s": 210.0, "alarm": 1, "transition_window": 0},
    ]
    metrics = physical.detection_metrics(two_alarm_sessions)
    assert metrics["alarm_window_count"] == 4
    assert metrics["alarm_entries"] == metrics["alarm_episodes"] == 2

    alarm_then_next_session_normal = [
        {"firmware_session_index": 1, "run_det_index": 1,
         "elapsed_s": 10.0, "alarm": 1, "transition_window": 0},
        {"firmware_session_index": 2, "run_det_index": 2,
         "elapsed_s": 200.0, "alarm": 0, "transition_window": 0},
    ]
    no_cross_session_recovery = physical.detection_metrics(
        alarm_then_next_session_normal,
    )
    assert no_cross_session_recovery["alarm_episodes"] == 1
    assert no_cross_session_recovery["recovery_latencies_s"] == []
    assert no_cross_session_recovery["recovery_latency_s"] is None


def test_metrics_do_not_bridge_recovery_across_excluded_transition_gap() -> None:
    rows = [
        {"firmware_session_index": 1, "run_det_index": 1,
         "elapsed_s": 10.0, "alarm": 1, "transition_window": 0},
        {"firmware_session_index": 1, "run_det_index": 2,
         "elapsed_s": 20.0, "alarm": 0, "transition_window": 1},
        {"firmware_session_index": 1, "run_det_index": 3,
         "elapsed_s": 30.0, "alarm": 0, "transition_window": 0},
    ]

    metrics = physical.detection_metrics(rows)

    assert metrics["det_count"] == 2
    assert metrics["excluded_transition_windows"] == 1
    assert metrics["recovery_latencies_s"] == []
    assert metrics["recovery_latency_s"] is None


def test_cold_start_04_recompute_rejects_k1_without_overwriting_original(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run_20260816T130444_fan01_cold-start-04"
    run_dir.mkdir()
    original = "istorijski summary mora ostati netaknut\n"
    (run_dir / "SUMMARY.md").write_text(original, encoding="utf-8")

    state = _ready_protocol_state()
    state["cal_summary"]["loo_cv"] = 0.627538
    state = physical.transition_firmware_protocol(state, _quality("DET"))
    state = physical.transition_firmware_protocol(state, _det())
    metadata = {
        "fan_id": "fan01", "session_id": "cold-start-04", "port": "COM3",
        "baud": 115200, "distance_cm": 20, "room": "soba",
    }
    (run_dir / "provenance.json").write_text(
        json.dumps({
            "protocol_version": "physical-fan-v1.6.0",
            "quality_protocol_version": "asd-quality-v1.3.0",
            "status": "completed_by_operator",
            "metadata": metadata,
            "max_dropped": 0,
            "firmware_protocol_state": state,
        }),
        encoding="utf-8",
    )
    row = {
        "condition": "normal_baseline", "condition_confirmed": 1,
        "protocol_valid": 1, "alarm": 0, "score": 1.0,
    }
    with (run_dir / "detections.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)

    recomputed, validity = physical.recompute_run_summary(run_dir)

    assert validity["protocol_valid"] is True
    assert validity["calibration_accepted"] is False
    assert validity["calibration_acceptance_reason"] == "loo_cv_above_max"
    assert validity["metrics_eligible"] is False
    assert validity["valid_result"] is False
    assert "Validan fizički rezultat: **NE**" in recomputed
    assert "Protokol izvještaja: `physical-fan-v1.8.0`" in recomputed
    assert "Izvorni protokol artefakta: `physical-fan-v1.6.0`" in recomputed
    assert "Validnih DET prozora za metrike: 0" in recomputed
    assert "Condition+protocol validnih DET kandidata: 1" in recomputed
    assert (run_dir / "SUMMARY.md").read_text(encoding="utf-8") == original
    assert not (run_dir / "SUMMARY.recomputed.md").exists()


@pytest.mark.parametrize(
    "version",
    [None, "", "physical-fan-v1.5.0", "physical-fan-v2.0.0"],
)
def test_offline_artifact_read_rejects_missing_or_unknown_protocol(
    version: str | None,
) -> None:
    provenance = {} if version is None else {
        "protocol_version": version,
        "quality_protocol_version": "asd-quality-v1.4.0",
    }
    with pytest.raises(ValueError, match="offline citanje podrzava"):
        physical.artifact_protocol_version_for_read(provenance)


@pytest.mark.parametrize(
    ("version", "quality"), [
        ("physical-fan-v1.6.0", "asd-quality-v1.3.0"),
        ("physical-fan-v1.7.0", "asd-quality-v1.4.0"),
        ("physical-fan-v1.8.0", "asd-quality-v1.5.0"),
    ],
)
def test_offline_artifact_read_accepts_only_explicit_contracts(
    version: str, quality: str,
) -> None:
    provenance = {
        "protocol_version": version,
        "quality_protocol_version": quality,
    }
    if version in physical.ARTIFACT_CONTRACT_VERSIONS:
        provenance["artifact_contract_version"] = (
            physical.ARTIFACT_CONTRACT_VERSIONS[version]
        )
    assert physical.artifact_protocol_version_for_read(provenance) == version


@pytest.mark.parametrize(
    ("version", "quality", "error"), [
        ("physical-fan-v1.6.0", None, "nedostajuci quality_protocol_version"),
        ("physical-fan-v1.7.0", None, "nedostajuci quality_protocol_version"),
        ("physical-fan-v1.6.0", "asd-quality-v1.4.0", "nepodudaran host/UART"),
        ("physical-fan-v1.7.0", "asd-quality-v1.3.0", "nepodudaran host/UART"),
        ("physical-fan-v1.7.0", "asd-quality-v9.0.0", "nepodudaran host/UART"),
    ],
)
def test_offline_artifact_read_rejects_missing_unknown_or_mismatched_quality(
    version: str, quality: str | None, error: str,
) -> None:
    provenance = {"protocol_version": version}
    if quality is not None:
        provenance["quality_protocol_version"] = quality
    with pytest.raises(ValueError, match=error):
        physical.artifact_protocol_version_for_read(provenance)


@pytest.mark.parametrize("contract", [None, "", "physical-fan-artifacts-v9.0.0"])
def test_v17_offline_read_requires_exact_artifact_contract(
    contract: str | None,
) -> None:
    provenance = {
        "protocol_version": physical.PROTOCOL_VERSION,
        "quality_protocol_version": physical.QUALITY_PROTOCOL_VERSION,
    }
    if contract is not None:
        provenance["artifact_contract_version"] = contract
    with pytest.raises(ValueError, match="artifact contract"):
        physical.artifact_protocol_version_for_read(provenance)


def test_phase2_provenance_hash_scope_is_explicit_even_for_future_files() -> None:
    relative = {
        path.relative_to(physical.ROOT).as_posix()
        for path in physical.RELEVANT_FILES
    }
    assert {
        "firmware/esp32s3_asd/main/asd_temporal.c",
        "firmware/esp32s3_asd/main/asd_temporal.h",
        "firmware/esp32s3_asd/main/asd_cmd.c",
        "firmware/esp32s3_asd/main/asd_cmd.h",
        "pc/config/asd_temporal_policy_v2.json",
        "pc/config/asd_commissioning_policy_v1.json",
        "firmware/esp32s3_asd/main/asd_calibration_quality.c",
        "firmware/esp32s3_asd/main/asd_calibration_quality.h",
        "pc/config/asd_interference_policy_v1.json",
        "firmware/esp32s3_asd/main/asd_interference.c",
        "firmware/esp32s3_asd/main/asd_interference.h",
    } <= relative


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


def test_literal_full_q15_fresh_trace_with_roundtrip_det_and_anomaly_pair() -> None:
    q = physical.QUALITY_PROTOCOL_VERSION
    commission_prefix, commission_suffix = _fresh_commission_lines()
    lines = [
        f"SESSION protocol={q} action=STARTED source=BUTTON "
        "reason=OPERATOR_REQUEST discards_calibration=0",
        f"STATE protocol={q} from=NO_MACHINE to=NO_MACHINE reason=BOOT_FAIL_CLOSED",
        *commission_prefix,
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
        *commission_suffix,
        _runtime_profile_line(threshold_enter=1.60000002, threshold_exit=1.1),
        f"ADAPTTHR n={physical.RUNTIME_COMMISSIONING_POLICY['derive_windows']} "
        "mean=1.000000 sd=0.200000 k=0 theta=0 p=0.9900 "
        "thr=1.60000002 lo=0.000000 factory=0.000000",
        f"PRESENCE protocol={q} level_mean_dbfs=-30 margin_db=11 "
        "gate_dbfs=-41 min_consecutive=3",
        _temporal_line(threshold_enter=1.60000002, threshold_exit=1.1),
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
    handshake = _handshake_state()
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
    commission_prefix, commission_suffix = _fresh_commission_records()
    for record in commission_prefix:
        state = physical.transition_firmware_protocol(state, record)
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
    for record in commission_suffix:
        state = physical.transition_firmware_protocol(state, record)
    profile = physical.parse_serial_line(_runtime_profile_line())
    assert profile is not None
    state = physical.transition_firmware_protocol(state, profile)
    mismatch = physical.transition_firmware_protocol(
        state, {**_adapt(), "threshold": 2.0},
    )
    assert mismatch["invalid_reason"] == "ADAPTTHR_PROFILE_threshold_mismatch"
    # DERIVE statistika je vremenski kasnija od CAL_SUMMARY LOO statistike.
    state = physical.transition_firmware_protocol(state, {**_adapt(), "mean": 2.0})
    assert state["invalid_status"] is None
    duplicate = physical.transition_firmware_protocol(state, _adapt())
    assert duplicate["invalid_reason"] == "duplicate_ADAPTTHR"


def test_cal_summary_cv_consistency_uses_six_decimal_wire_intervals() -> None:
    # 1e-6/1e-6 izgleda kao CV=1 iz prikazanih centara, ali oba wire bina
    # predstavljaju [0.5e-6, 1.5e-6]. Stvarne 1.4e-6 i 0.6e-6 daju emitovani
    # CV=0.428571, pa je zapis matematicki moguc i mora proci.
    assert physical.cal_summary_cv_is_quantization_consistent(
        0.000001, 0.000001, 0.428571,
    )
    # Stvarni cold-start-04 zapis ostaje koherentan pod istim pravilom.
    assert physical.cal_summary_cv_is_quantization_consistent(
        2197.673828, 1379.123047, 0.627538,
    )

    # Materijalni mismatch-i nemaju presjek kvantizacionih intervala.
    assert not physical.cal_summary_cv_is_quantization_consistent(1.0, 0.2, 0.3)
    assert not physical.cal_summary_cv_is_quantization_consistent(
        2197.673828, 1379.123047, 0.637538,
    )

    def before_summary() -> dict:
        state = _handshake_state()
        for phase in ("WAIT", "CAL"):
            for index in range(1, physical.EXPECTED_QUALITY_COUNTS[phase] + 1):
                state = physical.transition_firmware_protocol(
                    state, _quality(phase, index),
                )
        return state

    quantized_example = physical.transition_firmware_protocol(
        before_summary(), {
            **_quality("CAL_SUMMARY"),
            "loo_mean": 0.000001, "loo_sd": 0.000001,
            "loo_cv": 0.428571, "loo_range": 0.000002,
        },
    )
    assert quantized_example["invalid_status"] is None
    material_mismatch = physical.transition_firmware_protocol(
        before_summary(), {
            **_quality("CAL_SUMMARY"),
            "loo_mean": 1.0, "loo_sd": 0.2,
            "loo_cv": 0.3, "loo_range": 1.0,
        },
    )
    assert material_mismatch["invalid_reason"].startswith("CAL_SUMMARY_cv_mismatch")


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
        "QUALITY protocol=asd-quality-v1.4.0 phase=CAL_SUMMARY result=OBSERVED "
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
                b"SESSION protocol=asd-quality-v1.4.0 action=STARTED source=BUTTON "
                b"reason=OPERATOR_REQUEST discards_calibration=0\n",
                b"STATE protocol=asd-quality-v1.4.0 from=NO_MACHINE "
                b"to=NO_MACHINE reason=BOOT_FAIL_CLOSED\n",
                b"STATE protocol=asd-quality-v1.4.0 from=NO_MACHINE "
                b"to=NO_MACHINE reason=INSUFFICIENT_LEVEL\n",
                b"EVENT protocol=asd-quality-v1.4.0 type=FLOW_STOPPED "
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
            "SESSION protocol=asd-quality-v1.5.0 action=STARTED source=BUTTON "
        "reason=OPERATOR_REQUEST discards_calibration=0\n",
            "STATE protocol=asd-quality-v1.5.0 from=NO_MACHINE to=NO_MACHINE "
        "reason=BOOT_FAIL_CLOSED\n",
            "STATE protocol=asd-quality-v1.5.0 from=NO_MACHINE to=NO_MACHINE "
        "reason=INSUFFICIENT_LEVEL\n",
            "EVENT protocol=asd-quality-v1.5.0 type=FLOW_STOPPED state=NO_MACHINE "
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


@pytest.mark.parametrize(
    ("loo_cv", "expected_rc", "expected_accepted", "expected_result_status"),
    [
        (0.2, 0, True, "valid_physical_result"),
        (0.600001, 1, False, "calibration_rejected:loo_cv_above_max"),
    ],
)
def test_run_experiment_dispatches_temporal_and_uses_k1_for_final_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, loo_cv: float,
    expected_rc: int, expected_accepted: bool, expected_result_status: str,
) -> None:
    """Regresija za stvarnu serijsku petlju, ne samo cisti state-machine."""
    import serial

    q = physical.QUALITY_PROTOCOL_VERSION
    commission_prefix, commission_suffix = _fresh_commission_lines()
    lines = [
        f"SESSION protocol={q} action=STARTED source=BUTTON "
        "reason=OPERATOR_REQUEST discards_calibration=0",
        f"STATE protocol={q} from=NO_MACHINE to=NO_MACHINE reason=BOOT_FAIL_CLOSED",
        *commission_prefix,
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
    threshold = 1.0 + 3.0 * loo_cv
    lines.append(
        f"QUALITY protocol={q} phase=CAL_SUMMARY result=OBSERVED "
        f"loo_mean=1.000000 loo_sd={loo_cv:.6f} loo_cv={loo_cv:.6f} "
        "loo_range=1.000000 loo_gate=pending_normal_only"
    )
    if expected_accepted:
        threshold_exit = threshold * 0.7
        lines.extend([
            *commission_suffix,
            _runtime_profile_line(
                threshold_enter=threshold, threshold_exit=threshold_exit,
            ),
            f"ADAPTTHR n={physical.RUNTIME_COMMISSIONING_POLICY['derive_windows']} "
            f"mean=1.000000 sd={loo_cv:.6f} k=0 theta=0 p=0.9900 "
            f"thr={threshold:.8f} lo=0.000000 factory=0.000000",
            f"PRESENCE protocol={q} level_mean_dbfs=-30 margin_db=11 "
            "gate_dbfs=-41 min_consecutive=3",
            _temporal_line(
                threshold_enter=threshold, threshold_exit=threshold_exit,
            ),
            f"STATE protocol={q} from=NO_MACHINE to=CALIBRATED_NORMAL "
            "reason=CALIBRATION_ACCEPTED",
            f"EVENT protocol={q} type=CALIBRATION_ACCEPTED state=CALIBRATED_NORMAL "
            "phase=CAL reason=QUALITY_OK event=NONE capability=AVAILABLE level=DEVIATION",
            f"QUALITY protocol={q} phase=DET index=1 total=0 result=OK "
            "metrics_valid=1 samples=159744 expected=159744 rms_dbfs=-30.000 "
            "dc=0.000 peak=1100 clipped=0 zeros=0 stuck=0 dropped_delta=0 "
            "feature_valid=1 tonalness_valid=1 tonalness_proxy=1.000000 "
            "tonal_gate=pending_normal_only",
            f"DET 1 score=0.5 lo=0 hi={threshold:.8f} led=1 anom=0 total_anom=0 "
            "normal (uzastopnih=0 nivo=-30.0 dBFS racun=700 ms)",
            f"QUALITY protocol={q} phase=DET index=2 total=0 result=OK "
            "metrics_valid=1 samples=159744 expected=159744 rms_dbfs=-30.000 "
            "dc=0.000 peak=1100 clipped=0 zeros=0 stuck=0 dropped_delta=0 "
            "feature_valid=1 tonalness_valid=1 tonalness_proxy=1.000000 "
            "tonal_gate=pending_normal_only",
            f"DET 2 score=0.5 lo=0 hi={threshold:.8f} led=1 anom=0 total_anom=0 "
            "normal (uzastopnih=0 nivo=-30.0 dBFS racun=700 ms)",
            f"SESSION protocol={q} action=ENDED source=FIRMWARE "
            "reason=SESSION_RETURNED discards_calibration=0",
        ])
    else:
        lines.extend([
            f"STATE protocol={q} from=NO_MACHINE to=CALIBRATION_REJECTED "
            "reason=UNSTABLE_CALIBRATION",
            f"EVENT protocol={q} type=FLOW_STOPPED state=CALIBRATION_REJECTED "
            "phase=CAL reason=UNSTABLE_CALIBRATION event=NONE "
            "capability=AVAILABLE level=DEVIATION",
            f"SESSION protocol={q} action=ENDED source=FIRMWARE "
            "reason=SESSION_RETURNED discards_calibration=0",
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
        if (
            expected_accepted and not condition_sent and fake_instances
            and fake_instances[0].lines
            and b"phase=DET index=1" in fake_instances[0].lines[0]
        ):
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

    assert rc == expected_rc
    assert fake_instances and fake_instances[0].closed is True
    run_dir = next(tmp_path.glob("run_*"))
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["status"] == (
        "completed_by_operator" if expected_accepted
        else "completed_calibration_rejected"
    )
    assert provenance["calibration_accepted"] is expected_accepted
    assert provenance["calibration_acceptance_reason"] == (
        "accepted" if expected_accepted else "loo_cv_above_max"
    )
    assert provenance["physical_result_status"] == expected_result_status
    assert provenance["metrics_eligible"] is expected_accepted
    assert provenance["firmware_telemetry_counts"]["TEMPORAL"] == (
        1 if expected_accepted else 0
    )
    assert provenance["firmware_telemetry_counts"]["SESSION"] == 2
    state = provenance["firmware_protocol_state"]
    assert state["temporal_seen"] is expected_accepted
    assert state["calibration_rejected_event"] is (not expected_accepted)
    assert state["sessions_ended"] == 1
    assert physical.firmware_protocol_complete(state)
    assert provenance["valid_det_window_count"] == (1 if expected_accepted else 0)
    summary = (run_dir / "SUMMARY.md").read_text(encoding="utf-8")
    assert f"Status fizičkog rezultata: `{expected_result_status}`" in summary


def test_full_literal_two_session_run_resets_session_scope_and_keeps_run_totals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """K1 reject ostaje audit, a cijeli drugi tok daje valjan multi-session run."""
    import serial

    q = physical.QUALITY_PROTOCOL_VERSION
    commission_prefix, commission_suffix = _fresh_commission_lines()

    def session_line(action: str) -> str:
        source = "BUTTON" if action == "STARTED" else "FIRMWARE"
        reason = "OPERATOR_REQUEST" if action == "STARTED" else "SESSION_RETURNED"
        return (
            f"SESSION protocol={q} action={action} source={source} "
            f"reason={reason} discards_calibration=0"
        )

    def wait_line(index: int) -> str:
        return (
            f"QUALITY protocol={q} phase=WAIT index={index} total=60 result=OK "
            "metrics_valid=1 samples=4096 expected=4096 rms_dbfs=-30.000 "
            "dc=0.000 peak=1100 clipped=0 zeros=0 stuck=0 dropped_delta=0 "
            "feature_valid=0 tonalness_valid=0 tonalness_proxy=0.000000 "
            "tonal_gate=not_computed"
        )

    def cal_line(index: int) -> str:
        return (
            f"QUALITY protocol={q} phase=CAL index={index} total=10 result=OK "
            "metrics_valid=1 samples=159744 expected=159744 rms_dbfs=-30.000 "
            "dc=0.000 peak=1100 clipped=0 zeros=0 stuck=0 dropped_delta=0 "
            "feature_valid=1 tonalness_valid=1 tonalness_proxy=1.000000 "
            "tonal_gate=pending_normal_only"
        )

    def det_pair(index: int) -> list[str]:
        return [
            f"QUALITY protocol={q} phase=DET index={index} total=0 result=OK "
            "metrics_valid=1 samples=159744 expected=159744 rms_dbfs=-30.000 "
            "dc=0.000 peak=1100 clipped=0 zeros=0 stuck=0 dropped_delta=0 "
            "feature_valid=1 tonalness_valid=1 tonalness_proxy=1.000000 "
            "tonal_gate=pending_normal_only",
            f"DET {index} score=0.5 lo=0 hi=1.60000000 led=1 anom=0 "
            "total_anom=0 normal (uzastopnih=0 nivo=-30.0 dBFS racun=700 ms)",
        ]

    lines = [
        session_line("STARTED"),
        f"STATE protocol={q} from=NO_MACHINE to=NO_MACHINE reason=BOOT_FAIL_CLOSED",
        *commission_prefix,
        *[wait_line(index) for index in range(1, 61)],
        *[cal_line(index) for index in range(1, 11)],
        f"QUALITY protocol={q} phase=CAL_SUMMARY result=OBSERVED "
        "loo_mean=1.000000 loo_sd=0.600001 loo_cv=0.600001 "
        "loo_range=1.000000 loo_gate=pending_normal_only",
        f"STATE protocol={q} from=NO_MACHINE to=CALIBRATION_REJECTED "
        "reason=UNSTABLE_CALIBRATION",
        f"EVENT protocol={q} type=FLOW_STOPPED state=CALIBRATION_REJECTED "
        "phase=CAL reason=UNSTABLE_CALIBRATION event=NONE "
        "capability=AVAILABLE level=DEVIATION",
        session_line("ENDED"),
        session_line("STARTED"),
        f"STATE protocol={q} from=NO_MACHINE to=NO_MACHINE reason=BOOT_FAIL_CLOSED",
        *commission_prefix,
        *[wait_line(index) for index in range(1, 61)],
        *[cal_line(index) for index in range(1, 11)],
        f"QUALITY protocol={q} phase=CAL_SUMMARY result=OBSERVED "
        "loo_mean=1.000000 loo_sd=0.200000 loo_cv=0.200000 "
        "loo_range=0.500000 loo_gate=pending_normal_only",
        *commission_suffix,
        _runtime_profile_line(),
        f"ADAPTTHR n={physical.RUNTIME_COMMISSIONING_POLICY['derive_windows']} "
        "mean=1.000000 sd=0.200000 k=0 theta=0 p=0.9900 "
        "thr=1.60000000 lo=0.000000 factory=0.000000",
        f"PRESENCE protocol={q} level_mean_dbfs=-30 margin_db=11 "
        "gate_dbfs=-41 min_consecutive=3",
        _temporal_line(),
        f"STATE protocol={q} from=NO_MACHINE to=CALIBRATED_NORMAL "
        "reason=CALIBRATION_ACCEPTED",
        f"EVENT protocol={q} type=CALIBRATION_ACCEPTED state=CALIBRATED_NORMAL "
        "phase=CAL reason=QUALITY_OK event=NONE capability=AVAILABLE level=DEVIATION",
        *det_pair(1),
        *det_pair(2),
        *det_pair(3),
        session_line("ENDED"),
    ]

    class FakeSerial:
        def __init__(self, *args, **kwargs):
            self.timeout = kwargs.get("timeout", 1)
            self.lines = [(line + "\n").encode("ascii") for line in lines]
            self.started_count = 0
            self.closed = False

        def readline(self):
            if not self.lines:
                return b""
            line = self.lines.pop(0)
            if line.startswith(b"SESSION ") and b"action=STARTED" in line:
                self.started_count += 1
            return line

        def close(self):
            self.closed = True

    fake_instances: list[FakeSerial] = []

    def open_fake(*args, **kwargs):
        instance = FakeSerial(*args, **kwargs)
        fake_instances.append(instance)
        return instance

    stale_condition_sent = False
    second_condition_sent = False
    stop_sent = False

    def poll_commands(path, offset):
        nonlocal stale_condition_sent, second_condition_sent, stop_sent
        if (
            fake_instances and fake_instances[0].started_count == 1
            and not stale_condition_sent
        ):
            stale_condition_sent = True
            return offset, ["condition airflow_change first-session-only"]
        if (
            fake_instances and fake_instances[0].started_count == 2
            and not second_condition_sent and fake_instances[0].lines
            and b"phase=DET index=2" in fake_instances[0].lines[0]
        ):
            second_condition_sent = True
            return offset, ["condition normal_baseline second-session"]
        if fake_instances and not fake_instances[0].lines and not stop_sent:
            stop_sent = True
            return offset, ["stop"]
        return offset, []

    _mock_ready_host(monkeypatch)
    monkeypatch.setattr(serial, "Serial", open_fake)
    monkeypatch.setattr(physical, "poll_command_file", poll_commands)

    rc = physical.run_experiment(_run_args(tmp_path, tmp_path / "commands.txt"))

    assert rc == 0
    run_dir = next(tmp_path.glob("run_*"))
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    detections = list(csv.DictReader(
        (run_dir / "detections.csv").open(encoding="utf-8", newline=""),
    ))
    quality = list(csv.DictReader(
        (run_dir / "firmware_quality.csv").open(encoding="utf-8", newline=""),
    ))
    events = list(csv.DictReader(
        (run_dir / "events.csv").open(encoding="utf-8", newline=""),
    ))
    firmware_states = list(csv.DictReader(
        (run_dir / "firmware_states.csv").open(encoding="utf-8", newline=""),
    ))

    assert provenance["status"] == "completed_by_operator"
    assert provenance["artifact_contract_version"] == physical.ARTIFACT_CONTRACT_VERSION
    assert provenance["physical_result_status"] == "valid_physical_result"
    assert provenance["run_quality_counts"] == {
        "WAIT": 120, "CAL": 20, "CAL_SUMMARY": 2, "DET": 3,
    }
    assert provenance["run_det_records"] == len(detections) == 3
    assert provenance["valid_det_window_count"] == 1
    assert provenance["excluded_transition_window_count"] == 1

    sessions = provenance["firmware_sessions"]
    assert [item["firmware_session_index"] for item in sessions] == [1, 2]
    assert sessions[0]["protocol_status"] == "calibration_rejected"
    assert sessions[0]["protocol_valid"] is True
    assert sessions[0]["calibration_accepted"] is False
    assert sessions[0]["raw_det_count"] == sessions[0]["det_count"] == 0
    assert sessions[0]["metrics_eligible"] is False
    assert sessions[1]["protocol_status"] == "accepted"
    assert sessions[1]["protocol_valid"] is True
    assert sessions[1]["calibration_accepted"] is True
    assert sessions[1]["raw_det_count"] == 3
    assert sessions[1]["protocol_valid_det_count"] == 3
    assert sessions[1]["det_count"] == 1

    assert [row["firmware_session_index"] for row in detections] == ["2", "2", "2"]
    assert [row["window"] for row in detections] == ["1", "2", "3"]
    assert [row["run_det_index"] for row in detections] == ["1", "2", "3"]
    assert detections[0]["condition"] == "unconfirmed"
    assert detections[0]["condition_confirmed"] == "0"
    assert detections[1]["condition"] == "normal_baseline"
    assert detections[1]["transition_window"] == "1"
    assert detections[2]["condition"] == "normal_baseline"
    assert detections[2]["transition_window"] == "0"
    condition_events = [row for row in events if row["kind"] == "condition"]
    assert [row["firmware_session_index"] for row in condition_events] == ["1", "2"]

    wait_rows = [row for row in quality if row["phase"] == "WAIT"]
    assert wait_rows[0]["firmware_session_index"] == "1"
    second_wait = next(
        row for row in wait_rows if row["firmware_session_index"] == "2"
    )
    assert second_wait["index"] == "1"
    assert sum(row["firmware_session_index"] == "1" for row in wait_rows) == 60
    assert sum(row["firmware_session_index"] == "2" for row in wait_rows) == 60
    boot_rows = [
        row for row in firmware_states if row["reason"] == "BOOT_FAIL_CLOSED"
    ]
    assert [row["firmware_session_index"] for row in boot_rows] == ["1", "2"]

    state = provenance["firmware_protocol_state"]
    assert state["handshake"] is True
    assert state["sessions"] == state["sessions_ended"] == 2
    assert state["firmware_session_index"] == 2
    assert state["det_records"] == 3
    assert state["run_det_records"] == 3
    assert state["run_boot_records"] == 2
    assert state["session_boot_seen"] is True
    assert physical.firmware_protocol_complete(state)

    summary = (run_dir / "SUMMARY.md").read_text(encoding="utf-8")
    assert "Firmware sesija: 2" in summary
    assert "| 1 | calibration_rejected (valid)" in summary
    assert "| 2 | accepted (valid)" in summary


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
    state = _fresh_profile_state()
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
    replayed = {
        **_ready_protocol_state(),
        "presence_seen": False,
        "temporal_seen": False,
        "temporal_threshold_enter": None,
        "temporal_threshold_exit": None,
    }
    out = physical.transition_firmware_protocol(replayed, _presence())
    assert out["invalid_reason"] == "PRESENCE_after_calibration_acceptance"


def test_presence_margin_must_match_the_locked_policy() -> None:
    state = _fresh_profile_state()
    state = physical.transition_firmware_protocol(state, _adapt())
    tampered = dict(_presence())
    tampered["margin_db"] = 3.0
    tampered["gate_dbfs"] = tampered["level_mean_dbfs"] - 3.0
    out = physical.transition_firmware_protocol(state, tampered)
    assert out["invalid_reason"] == "PRESENCE_margin_off_policy"


def test_presence_gate_arithmetic_is_checked_at_parse_time() -> None:
    bad = physical.parse_serial_line(
        "PRESENCE protocol=asd-quality-v1.4.0 level_mean_dbfs=-30 margin_db=11 "
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
        "EVENT protocol=asd-quality-v1.4.0 type=ANOMALY_ENTERED state=ANOMALY "
        "phase=DET reason=THRESHOLD_PERSISTENCE event=MECHANICAL_ANOMALY "
        "capability=NEEDS_TRANSIENT level=DEVIATION"
    )
    assert parsed["kind"] == "PARSE_ERROR"
    assert parsed["reason"] == "reserved_event_emitted:MECHANICAL_ANOMALY"


def test_reserved_event_relabelled_as_available_is_still_rejected() -> None:
    parsed = physical.parse_serial_line(
        "EVENT protocol=asd-quality-v1.4.0 type=ANOMALY_ENTERED state=ANOMALY "
        "phase=DET reason=THRESHOLD_PERSISTENCE event=SPEED_CHANGED "
        "capability=AVAILABLE level=DEVIATION"
    )
    assert parsed["kind"] == "PARSE_ERROR"
    assert parsed["reason"] == "reserved_event_emitted:SPEED_CHANGED"


def test_event_without_faza2_fields_is_a_protocol_error() -> None:
    parsed = physical.parse_serial_line(
        "EVENT protocol=asd-quality-v1.4.0 type=FLOW_STOPPED state=NO_MACHINE "
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
            "BUTTON protocol=asd-quality-v1.5.0 event=LONG mode=READY "
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
        "BUTTON protocol=asd-quality-v1.4.0 event=SHORT mode=READY "
        "command=START_LEARNING discards=1"
    )
    assert parsed["kind"] == "PARSE_ERROR"
    assert parsed["reason"] == "short_press_discarded_calibration"


def test_session_records_must_be_paired() -> None:
    started = physical.parse_serial_line(
            "SESSION protocol=asd-quality-v1.5.0 action=STARTED source=BUTTON "
        "reason=OPERATOR_REQUEST discards_calibration=0"
    )
    assert started["kind"] == "SESSION"
    state = physical.transition_firmware_protocol(
        physical.new_firmware_protocol_state(), started)
    assert state["session_started"] is True and state["sessions"] == 1
    assert physical.transition_firmware_protocol(
        state, started)["invalid_reason"] == "SESSION_STARTED_twice"

    orphan = physical.parse_serial_line(
        "SESSION protocol=asd-quality-v1.5.0 action=ENDED source=FIRMWARE "
        "reason=NO_MACHINE discards_calibration=0"
    )
    out = physical.transition_firmware_protocol(
        physical.new_firmware_protocol_state(), orphan)
    assert out["invalid_reason"] == "SESSION_ENDED_without_START"


def test_autostart_session_source_is_rejected() -> None:
    parsed = physical.parse_serial_line(
        "SESSION protocol=asd-quality-v1.4.0 action=STARTED source=AUTOSTART "
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
        ("SESSION protocol=asd-quality-v1.4.0 action=RESUMED source=BUTTON "
         "reason=X discards_calibration=0", "unknown_session_action:RESUMED"),
        ("SESSION protocol=asd-quality-v1.4.0 action=STARTED source=TIMER "
         "reason=X discards_calibration=0", "unknown_session_source:TIMER"),
        ("BUTTON protocol=asd-quality-v1.4.0 event=DOUBLE mode=IDLE "
         "command=NONE discards=0", "unknown_button_event:DOUBLE"),
        ("BUTTON protocol=asd-quality-v1.4.0 event=LONG mode=SLEEPING "
         "command=NONE discards=0", "unknown_button_mode:SLEEPING"),
        ("BUTTON protocol=asd-quality-v1.4.0 event=LONG mode=IDLE "
         "command=RECALIBRATE discards=0", "unknown_button_command:RECALIBRATE"),
    ]
    for line, expected in cases:
        parsed = physical.parse_serial_line(line)
        assert parsed["kind"] == "PARSE_ERROR", line
        assert parsed["reason"] == expected


def test_virtual_button_records_cannot_invalidate_a_run() -> None:
    """`FLAGS`/`VBUTTON` su izvan zakljucanog rjecnika i moraju biti nevidljivi.

    Oba reda emituje firmware zbog panela (virtuelni taster i lampice). Ako bi
    ih parser prepoznao kao telemetriju, pali bi izmedju `QUALITY phase=DET` i
    njegovog `DET` reda i ponistavali inace ispravan prolaz. Zato se traktiraju
    kao nepoznat tekst: `None`, pa ih petlja u `run_experiment` preskoci prije
    `transition_firmware_protocol`.
    """
    ignored = [
        "FLAGS protocol=asd-quality-v1.4.0 mode=READY state=CALIBRATED_NORMAL "
        "waiting=0 learning=0 learned=1 anomaly=0 fault=0 green=on red=off",
        "FLAGS protocol=asd-quality-v1.4.0 mode=ALARM state=ANOMALY waiting=0 "
        "learning=0 learned=1 anomaly=1 fault=0 green=off red=on",
        "VBUTTON protocol=asd-quality-v1.4.0 source=console event=SHORT "
        "result=accepted",
        "VBUTTON protocol=asd-quality-v1.4.0 source=console event=NONE "
        "result=unknown_command",
    ]
    for line in ignored:
        assert physical.parse_serial_line(line) is None, line

    # Virtuelni pritisak se i dalje prijavljuje obicnim `BUTTON` redom, pa
    # dokaz o operaterovoj radnji ostaje u zakljucanoj telemetriji.
    parsed = physical.parse_serial_line(
        "BUTTON protocol=asd-quality-v1.4.0 event=SHORT mode=IDLE "
        "command=START_LEARNING discards=0"
    )
    assert parsed["kind"] == "BUTTON"
    assert parsed["command"] == "START_LEARNING"


def test_virtual_button_shares_the_physical_button_path() -> None:
    """Konzola smije da ubaci samo dogadjaj, nikad odluku.

    Ako bi virtuelni pritisak imao svoj `asd_ui_command`/`emit_button`, dva
    ulaza bi mogla da se raziđu u ponasanju. Zato se `asd_cmd_take_event`
    cita na istom mjestu gdje i pin, i sve dalje je zajednicko.
    """
    source = (
        ROOT / "firmware" / "esp32s3_asd" / "main" / "psd_live.c"
    ).read_text(encoding="utf-8")
    assert "event = asd_cmd_take_event();" in source
    assert source.count("asd_ui_command(mode, event)") == 1
    assert source.count("emit_button(") == 2  # definicija + jedan poziv

    console = (
        ROOT / "firmware" / "esp32s3_asd" / "main" / "asd_cmd.c"
    ).read_text(encoding="utf-8")
    for forbidden in ("asd_ui_command", "emit_button", "gpio_"):
        assert forbidden not in console, forbidden


def test_adaptthr_tolerance_follows_threshold_magnitude() -> None:
    """Float32 zaokruzenje ne smije da obori tacan prag.

    Firmware racuna `mean + 3*sd` u binary32, host u binary64. Kad prag dodje
    sa te grane, razlika je par ulp-a i mora proci; stvarno nizi prag mora pasti.
    Brojke su iz runa `cold-start-05` (16.08.2026), koji je bio odbacen ovdje.
    """
    mean, sd = 285.661469, 149.634216
    minimum = mean + 3.0 * sd
    device_threshold = 734.564087       # binary32 ispis uredjaja
    assert device_threshold < minimum   # strogo manji, razlika ~3e-5

    tolerance = max(2e-5, 1e-6 * abs(minimum))
    assert device_threshold + tolerance >= minimum, "float32 zaokruzenje palo"

    # Prag nizi za promil je stvarno krsenje politike i mora pasti.
    assert not (minimum * 0.999 + tolerance >= minimum)


def test_operator_relearn_emits_aborted_then_ended() -> None:
    """Rekalibracija na zahtjev operatera ne smije da obori prolaz.

    Firmware pri dugom pritisku emituje `SESSION ABORTED` (razlog) pa
    `SESSION ENDED` (zatvaranje). Host je `ABORTED` ranije racunao kao
    zatvaranje, pa je `ENDED` visio bez para. Put je izvrsen prvi put
    16.08.2026 u runu `cold-start-06` i tada ga je host odbacio.
    """
    state = physical.new_firmware_protocol_state()
    for line in (
        "SESSION protocol=asd-quality-v1.5.0 action=STARTED source=BUTTON "
        "reason=OPERATOR_REQUEST discards_calibration=0",
        "STATE protocol=asd-quality-v1.5.0 from=NO_MACHINE to=NO_MACHINE "
        "reason=BOOT_FAIL_CLOSED",
        "SESSION protocol=asd-quality-v1.5.0 action=ABORTED source=BUTTON "
        "reason=OPERATOR_RELEARN discards_calibration=1",
        "SESSION protocol=asd-quality-v1.5.0 action=ENDED source=FIRMWARE "
        "reason=CALIBRATED_NORMAL discards_calibration=0",
    ):
        parsed = physical.parse_serial_line(line)
        assert parsed is not None and parsed["kind"] in {"SESSION", "STATE"}, line
        state = physical.transition_firmware_protocol(state, parsed)
        assert state["invalid_status"] is None, (line, state["invalid_reason"])

    assert state["sessions"] == 1
    assert state["session_started"] is False

    # Zatvaranje bez otvorene sesije i dalje mora pasti.
    orphan = physical.parse_serial_line(
        "SESSION protocol=asd-quality-v1.5.0 action=ENDED source=FIRMWARE "
        "reason=CALIBRATED_NORMAL discards_calibration=0"
    )
    state = physical.transition_firmware_protocol(state, orphan)
    assert state["invalid_reason"] == "SESSION_ENDED_without_START"


def test_serial_timeout_is_not_reassigned_when_unchanged() -> None:
    """Ponovna dodjela `timeout` na Windowsu odbaci bajtove koji cekaju slanje.

    Petlja je u svakom prolazu pisala `ser.timeout = 1`, pa je svaka komanda
    poslata uredjaju nestajala prije nego sto izadje iz racunara -- uzrok svih
    "kliknuo sam, nista se nije desilo" 16.08.2026. Mjereno na istom portu:
    bez dodjele 3/3 komande stignu, sa dodjelom 0/3.
    """
    class FakeSerial:
        def __init__(self) -> None:
            self._timeout = 1
            self.reconfigures = 0

        @property
        def timeout(self):
            return self._timeout

        @timeout.setter
        def timeout(self, value):
            self._timeout = value
            self.reconfigures += 1   # na Windowsu ovdje ide _reconfigure_port()

    ser = FakeSerial()
    for _ in range(100):
        assert physical.apply_serial_timeout(ser, 1) is False
    assert ser.reconfigures == 0, "ustaljeni rad ne smije da konfigurise port"

    assert physical.apply_serial_timeout(ser, 0.05) is True
    assert ser.reconfigures == 1
    assert physical.apply_serial_timeout(ser, 0.05) is False
    assert ser.reconfigures == 1


def test_drain_waits_for_a_research_package_that_is_still_arriving() -> None:
    """Tisina izmedju redova jednog paketa nije kraj prenosa.

    Izmjereno 23.08.2026: paket je 7507 bajta = 652 ms na 115200 baud, a razmak
    izmedju njegovih redova ide do 141 ms -- vise od FINAL_BUFFER_QUIET_S. Bez
    ovoga je posljednji DET prozor ostajao bez grupa 4 i 5 i cio run je padao na
    `research_pairs_or_checksum_invalid` uz ispravno mjerenje.
    """
    # Zatvoren paket: tisina od 100 ms i dalje zatvara drenazu.
    assert physical.final_buffer_drain_decision(0.2, 0.15) == "complete"
    # Otvoren paket: ista tisina se ignorise dok paket ne stigne.
    assert physical.final_buffer_drain_decision(
        0.2, 0.15, package_open=True) == "continue"
    assert physical.final_buffer_drain_decision(
        0.7, 0.15, package_open=True) == "continue"
    # Cekanje je ograniceno; nepotpun paket se poslije toga i dalje odbija.
    assert physical.final_buffer_drain_decision(
        physical.FINAL_BUFFER_OPEN_PACKAGE_TIMEOUT_S, 0.0,
        package_open=True) == "complete"
    assert (physical.FINAL_BUFFER_OPEN_PACKAGE_TIMEOUT_S
            > physical.FINAL_BUFFER_DRAIN_TIMEOUT_S)


def test_research_package_open_sees_exactly_the_unfinished_window() -> None:
    key = (1, "DET", 55)
    state = {"expected": {key: {}}, "packages": {}}
    assert physical.research_package_open(state) is True

    state["packages"][key] = {"feature": {"values": []},
                              "groups": {index: {} for index in range(1, 5)}}
    assert physical.research_package_open(state) is True

    state["packages"][key]["groups"][5] = {}
    assert physical.research_package_open(state) is False

    state["packages"][key]["feature"] = None
    assert physical.research_package_open(state) is True
    assert physical.research_package_open(None) is False
