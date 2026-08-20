from __future__ import annotations

import pytest

from pc.asd.runtime_protocol import (
    COMMISSIONING,
    COMMISSIONING_POLICY,
    PROFILE_SCHEMA,
    QUALITY_PROTOCOL,
    RuntimeProtocolError,
    RuntimeSequence,
    parse_runtime_record,
)


def _commission(
    action: str, phase: str, index: int, total: int, *, score_valid: int = 0,
) -> str:
    return (
        f"COMMISSION protocol={QUALITY_PROTOCOL} policy={COMMISSIONING_POLICY} "
        f"developmental=1 action={action} phase={phase} index={index} "
        f"total={total} result=NONE score_valid={score_valid} "
        f"score={1 if score_valid else 0} level_dbfs=-31.25 "
        "tonalness_proxy=1.5 feature_drift=0.01"
    )


PROFILE = (
    f"PROFILE protocol={QUALITY_PROTOCOL} schema={PROFILE_SCHEMA} "
    f"policy={COMMISSIONING_POLICY} developmental=1 valid=1 "
    "policy_version=1 policy_id=434d5631 "
    f"center_windows={COMMISSIONING['center_windows']} "
    f"derive_windows={COMMISSIONING['derive_windows']} "
    f"verify_windows={COMMISSIONING['verify_windows']} "
    "level_mean_dbfs=-31.25 tonalness_reference=1.5 "
    "threshold_enter=20 threshold_exit=15"
)


def _successful_trace() -> list[str]:
    lines = [_commission(
        "STARTED", "SETTLE", 0, COMMISSIONING["max_settle_windows"],
    )]
    for index in range(1, COMMISSIONING["min_settle_windows"] + 1):
        phase = (
            "CENTER_LEARNING"
            if index == COMMISSIONING["min_settle_windows"] else "SETTLE"
        )
        lines.append(_commission(
            "WINDOW", phase, index, COMMISSIONING["max_settle_windows"],
        ))
    lines.append(_commission(
        "PHASE_ENTERED", "CENTER_LEARNING", 0, COMMISSIONING["center_windows"],
    ))
    lines.extend(
        _commission(
            "WINDOW", "COMMISSION_DERIVE", index,
            COMMISSIONING["derive_windows"], score_valid=1,
        )
        for index in range(1, COMMISSIONING["derive_windows"] + 1)
    )
    lines.extend(
        _commission(
            "WINDOW",
            "MONITORING" if index == COMMISSIONING["verify_windows"]
            else "COMMISSION_VERIFY",
            index, COMMISSIONING["verify_windows"], score_valid=1,
        )
        for index in range(1, COMMISSIONING["verify_windows"] + 1)
    )
    lines.append(PROFILE)
    return lines


def test_literal_q15_runtime_replay_matches_source_order_and_profile() -> None:
    sequence = RuntimeSequence()
    for line in _successful_trace():
        sequence.feed(line)
    assert sequence.profile is not None
    assert sequence.profile.fields["threshold_enter"] == 20.0
    assert sequence.profile.fields["threshold_exit"] == 15.0
    assert sequence.state["monitoring"] is True


def test_preregistered_runtime_counts_are_20_min_derive_and_10_min_verify() -> None:
    assert COMMISSIONING["derive_windows"] == 120
    assert COMMISSIONING["verify_windows"] == 60
    assert COMMISSIONING["derive_timeout_ms"] >= 120 * 10_000
    assert COMMISSIONING["verify_timeout_ms"] >= 60 * 10_000


def test_old_or_core_lines_are_ignored_not_reclassified_as_errors() -> None:
    assert parse_runtime_record("DET 1 score=3 hi=5") is None
    assert parse_runtime_record("QUALITY protocol=asd-quality-v1.3.0 phase=DET") is None


@pytest.mark.parametrize(
    "line",
    [
        PROFILE.replace(QUALITY_PROTOCOL, "asd-quality-v1.4.0"),
        PROFILE.replace(PROFILE_SCHEMA, "bogus-profile"),
        PROFILE.replace(COMMISSIONING_POLICY, "bogus-policy"),
        PROFILE.replace("threshold_exit=15", "threshold_exit=20"),
        PROFILE.replace("threshold_exit=15", "threshold_exit=nan"),
        PROFILE + " unexpected=1",
        PROFILE.replace(
            f"verify_windows={COMMISSIONING['verify_windows']}",
            "verify_windows=7",
        ),
    ],
)
def test_profile_is_strict_and_fail_closed(line: str) -> None:
    with pytest.raises(RuntimeProtocolError):
        parse_runtime_record(line)


def test_commission_rejects_missing_extra_bogus_and_wrong_order() -> None:
    start = _successful_trace()[0]
    for line in (
        start.replace(f" protocol={QUALITY_PROTOCOL}", ""),
        start + " extra=1",
        start.replace(QUALITY_PROTOCOL, "bogus"),
        start.replace(COMMISSIONING_POLICY, "bogus"),
    ):
        with pytest.raises(RuntimeProtocolError):
            parse_runtime_record(line)
    with pytest.raises(RuntimeProtocolError, match="does not start"):
        RuntimeSequence().feed(_commission(
            "WINDOW", "COMMISSION_DERIVE", 1, COMMISSIONING["derive_windows"],
            score_valid=1,
        ))


def test_center_entry_requires_the_literal_settle_transition_record() -> None:
    sequence = RuntimeSequence()
    sequence.feed(_commission(
        "STARTED", "SETTLE", 0, COMMISSIONING["max_settle_windows"],
    ))
    for index in range(1, COMMISSIONING["min_settle_windows"] + 1):
        sequence.feed(_commission(
            "WINDOW", "SETTLE", index, COMMISSIONING["max_settle_windows"],
        ))
    with pytest.raises(RuntimeProtocolError, match="CENTER_LEARNING entry"):
        sequence.feed(_commission(
            "PHASE_ENTERED", "CENTER_LEARNING", 0,
            COMMISSIONING["center_windows"],
        ))


def test_no_second_settle_window_is_accepted_after_transition() -> None:
    sequence = RuntimeSequence()
    for line in _successful_trace()[: COMMISSIONING["min_settle_windows"] + 1]:
        sequence.feed(line)
    with pytest.raises(RuntimeProtocolError, match="after transition"):
        sequence.feed(_commission(
            "WINDOW", "CENTER_LEARNING",
            COMMISSIONING["min_settle_windows"] + 1,
            COMMISSIONING["max_settle_windows"],
        ))


def test_public_wire_uses_hold_name_not_ambient_noise() -> None:
    source = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "firmware" / "esp32s3_asd" / "main" / "psd_live.c"
    ).read_text(encoding="utf-8")
    assert "OBSERVATION_HOLD" in source
    assert "AMBIENT_NOISE" not in source
