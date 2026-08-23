"""Strict q1.5 commissioning/profile UART parser and sequence validator."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from asd.guided_test import GUIDED25


QUALITY_PROTOCOL = "asd-quality-v1.6.0"
PROFILE_SCHEMA = "asd-runtime-profile-v1.0.0-development"
_CONFIG = json.loads(
    (Path(__file__).resolve().parents[1] / "config" / "asd_commissioning_runtime_v1.json")
    .read_text(encoding="utf-8")
)
COMMISSIONING_POLICY = str(_CONFIG["schema_version"])
COMMISSIONING_POLICY_ID = int(_CONFIG["policy_id_u32"])
COMMISSIONING_POLICY_VERSION = int(_CONFIG["policy_version"])
COMMISSIONING = dict(_CONFIG["policy"])
GUIDED_COMMISSIONING = dict(GUIDED25["commissioning"])
PROFILE_PERSISTENCE_ALLOWED = bool(_CONFIG["profile_persistence_allowed"])

COMMISSION_KEYS = frozenset({
    "protocol", "policy", "developmental", "action", "phase", "index",
    "total", "result", "score_valid", "score", "level_dbfs",
    "tonalness_proxy", "feature_drift",
})
PROFILE_KEYS = frozenset({
    "protocol", "schema", "policy", "developmental", "valid",
    "policy_version", "policy_id", "center_windows", "derive_windows",
    "verify_windows", "level_mean_dbfs", "tonalness_reference",
    "threshold_enter", "threshold_exit",
})
REJECT_RESULTS = frozenset({
    "PHASE_TIMEOUT", "QUALITY_REJECT", "SETTLE_UNSTABLE", "K1_REJECT",
    "INVALID_PROFILE", "VERIFY_NORMAL_REJECT", "INVALID_TRANSITION",
    "OPERATOR_ABORT",
})


class RuntimeProtocolError(ValueError):
    """A recognized q1.5 runtime record violates its locked contract."""


def _fields(line: str, prefix: str, expected: frozenset[str]) -> dict[str, str]:
    parts = line.rstrip("\r\n").split(" ")
    if not parts or parts[0] != prefix or any(not part for part in parts):
        raise RuntimeProtocolError(f"invalid {prefix} framing")
    parsed: dict[str, str] = {}
    for token in parts[1:]:
        if token.count("=") != 1:
            raise RuntimeProtocolError(f"invalid {prefix} token")
        key, value = token.split("=", 1)
        if not key or not value or key in parsed:
            raise RuntimeProtocolError(f"duplicate/empty {prefix} field")
        parsed[key] = value
    if parsed.keys() != expected:
        missing = sorted(expected - parsed.keys())
        extra = sorted(parsed.keys() - expected)
        raise RuntimeProtocolError(
            f"{prefix} fields missing={missing} extra={extra}"
        )
    return parsed


def _integer(fields: dict[str, str], key: str, *, minimum: int = 0) -> int:
    text = fields[key]
    if not text.isdecimal():
        raise RuntimeProtocolError(f"{key} is not an unsigned integer")
    value = int(text)
    if value < minimum:
        raise RuntimeProtocolError(f"{key} is below minimum")
    return value


def _number(fields: dict[str, str], key: str) -> float:
    try:
        value = float(fields[key])
    except ValueError as exc:
        raise RuntimeProtocolError(f"{key} is not numeric") from exc
    if not math.isfinite(value):
        raise RuntimeProtocolError(f"{key} is not finite")
    return value


@dataclass(frozen=True)
class RuntimeRecord:
    kind: str
    fields: dict[str, Any]


def parse_runtime_record(line: str) -> RuntimeRecord | None:
    """Parse q1.5 COMMISSION/PROFILE; return None for all other records."""

    prefix = line.partition(" ")[0]
    if prefix == "COMMISSION":
        raw = _fields(line, prefix, COMMISSION_KEYS)
        if raw["protocol"] != QUALITY_PROTOCOL:
            raise RuntimeProtocolError("commission protocol mismatch")
        if raw["policy"] != COMMISSIONING_POLICY:
            raise RuntimeProtocolError("commission policy mismatch")
        if raw["developmental"] != "1":
            raise RuntimeProtocolError("commission must remain developmental")
        if raw["action"] not in {"STARTED", "PHASE_ENTERED", "WINDOW"}:
            raise RuntimeProtocolError("unknown commissioning action")
        if raw["phase"] not in {
            "SETTLE", "CENTER_LEARNING", "COMMISSION_DERIVE",
            "COMMISSION_VERIFY", "MONITORING", "REJECTED", "ABORTED",
        }:
            raise RuntimeProtocolError("unknown commissioning phase")
        if raw["result"] not in {"NONE", *REJECT_RESULTS}:
            raise RuntimeProtocolError("unknown commissioning result")
        if raw["score_valid"] not in {"0", "1"}:
            raise RuntimeProtocolError("invalid score_valid flag")
        fields: dict[str, Any] = dict(raw)
        fields["developmental"] = int(raw["developmental"])
        fields["index"] = _integer(raw, "index")
        fields["total"] = _integer(raw, "total", minimum=1)
        fields["score_valid"] = int(raw["score_valid"])
        for key in ("score", "level_dbfs", "tonalness_proxy", "feature_drift"):
            fields[key] = _number(raw, key)
        if fields["score"] < 0.0 or fields["feature_drift"] < 0.0:
            raise RuntimeProtocolError("negative commissioning metric")
        return RuntimeRecord(prefix, fields)

    if prefix == "PROFILE":
        raw = _fields(line, prefix, PROFILE_KEYS)
        if raw["protocol"] != QUALITY_PROTOCOL:
            raise RuntimeProtocolError("profile protocol mismatch")
        if raw["schema"] != PROFILE_SCHEMA:
            raise RuntimeProtocolError("profile schema mismatch")
        if raw["policy"] != COMMISSIONING_POLICY:
            raise RuntimeProtocolError("profile policy mismatch")
        if raw["developmental"] != "1" or raw["valid"] != "1":
            raise RuntimeProtocolError("profile flags are not accepted")
        fields = dict(raw)
        for key in (
            "developmental", "valid", "policy_version", "center_windows",
            "derive_windows", "verify_windows",
        ):
            fields[key] = _integer(raw, key, minimum=1)
        if fields["policy_version"] != COMMISSIONING_POLICY_VERSION:
            raise RuntimeProtocolError("profile policy version mismatch")
        if len(raw["policy_id"]) != 8 or any(
            char not in "0123456789abcdefABCDEF" for char in raw["policy_id"]
        ):
            raise RuntimeProtocolError("policy_id must be eight hexadecimal digits")
        fields["policy_id"] = int(raw["policy_id"], 16)
        if fields["policy_id"] != COMMISSIONING_POLICY_ID:
            raise RuntimeProtocolError("profile policy id mismatch")
        for key in (
            "level_mean_dbfs", "tonalness_reference", "threshold_enter",
            "threshold_exit",
        ):
            fields[key] = _number(raw, key)
        if not 0.0 < fields["threshold_exit"] < fields["threshold_enter"]:
            raise RuntimeProtocolError("profile requires 0 < exit < enter")
        counts = tuple(fields[key] for key in (
            "center_windows", "derive_windows", "verify_windows"))
        allowed = {
            tuple(int(COMMISSIONING[key]) for key in (
                "center_windows", "derive_windows", "verify_windows")),
            tuple(int(GUIDED_COMMISSIONING[key]) for key in (
                "center_windows", "derive_windows", "verify_windows")),
        }
        if counts not in allowed:
            raise RuntimeProtocolError("profile counts off registered policy")
        return RuntimeRecord(prefix, fields)
    return None


def new_runtime_sequence_state() -> dict[str, Any]:
    """JSON-serializable accepted fresh-commissioning tracker."""
    return {
        "started": False,
        "settle_windows": 0,
        "settle_transitioned": False,
        "center_entered": False,
        "derive_windows": 0,
        "verify_windows": 0,
        "monitoring": False,
        "profile_seen": False,
        "terminal": False,
        "policy": None,
    }


def advance_runtime_sequence(
    state: dict[str, Any], record: RuntimeRecord,
) -> dict[str, Any]:
    """Validate the literal successful source order emitted by psd_live.c."""
    if state["terminal"]:
        raise RuntimeProtocolError("runtime record after terminal profile/reject")
    fields = record.fields
    if record.kind == "PROFILE":
        policy = state["policy"] or COMMISSIONING
        if not state["monitoring"] or state["verify_windows"] != int(policy["verify_windows"]):
            raise RuntimeProtocolError("profile arrived before MONITORING")
        for key in ("center_windows", "derive_windows", "verify_windows"):
            if int(fields[key]) != int(policy[key]):
                raise RuntimeProtocolError(f"profile {key} mismatches selected workflow")
        state["profile_seen"] = True
        state["terminal"] = True
        return state

    phase = fields["phase"]
    action = fields["action"]
    result = fields["result"]
    if phase in {"REJECTED", "ABORTED"}:
        if action != "WINDOW" or result not in REJECT_RESULTS:
            raise RuntimeProtocolError("invalid terminal commissioning record")
        state["terminal"] = True
        return state
    if result != "NONE":
        raise RuntimeProtocolError("success commissioning record has reject result")

    if not state["started"]:
        if not (action == "STARTED" and phase == "SETTLE" and fields["index"] == 0):
            raise RuntimeProtocolError("commissioning does not start with SETTLE")
        if fields["total"] == int(COMMISSIONING["max_settle_windows"]):
            state["policy"] = COMMISSIONING
        elif fields["total"] == int(GUIDED_COMMISSIONING["max_settle_windows"]):
            state["policy"] = GUIDED_COMMISSIONING
        else:
            raise RuntimeProtocolError("unregistered SETTLE total")
        policy = state["policy"]
        if not (
            action == "STARTED" and phase == "SETTLE" and fields["index"] == 0
            and fields["total"] == int(policy["max_settle_windows"])
            and fields["score_valid"] == 0
        ):
            raise RuntimeProtocolError("commissioning does not start with SETTLE")
        state["started"] = True
        return state

    policy = state["policy"]

    if not state["center_entered"]:
        if action == "WINDOW":
            if state["settle_transitioned"]:
                raise RuntimeProtocolError("SETTLE record after transition")
            expected = state["settle_windows"] + 1
            if fields["index"] != expected or fields["total"] != int(policy["max_settle_windows"]):
                raise RuntimeProtocolError("SETTLE window sequence mismatch")
            if fields["score_valid"] != 0 or fields["score"] != 0.0:
                raise RuntimeProtocolError("SETTLE must not expose a score")
            if phase not in {"SETTLE", "CENTER_LEARNING"}:
                raise RuntimeProtocolError("SETTLE transitioned to unexpected phase")
            if phase == "CENTER_LEARNING" and expected < int(COMMISSIONING["min_settle_windows"]):
                raise RuntimeProtocolError("SETTLE ended before minimum")
            if phase == "SETTLE" and expected >= int(policy["max_settle_windows"]):
                raise RuntimeProtocolError("SETTLE exceeded maximum without transition")
            state["settle_windows"] = expected
            state["settle_transitioned"] = phase == "CENTER_LEARNING"
            return state
        if not (
            action == "PHASE_ENTERED" and phase == "CENTER_LEARNING"
            and fields["index"] == 0
            and fields["total"] == int(policy["center_windows"])
            and state["settle_transitioned"]
            and state["settle_windows"] >= int(COMMISSIONING["min_settle_windows"])
        ):
            raise RuntimeProtocolError("invalid CENTER_LEARNING entry")
        state["center_entered"] = True
        return state

    if state["derive_windows"] < int(policy["derive_windows"]):
        expected = state["derive_windows"] + 1
        if not (
            action == "WINDOW" and phase == "COMMISSION_DERIVE"
            and fields["index"] == expected
            and fields["total"] == int(policy["derive_windows"])
            and fields["score_valid"] == 1
        ):
            raise RuntimeProtocolError("COMMISSION_DERIVE sequence mismatch")
        state["derive_windows"] = expected
        return state

    expected = state["verify_windows"] + 1
    final = expected == int(policy["verify_windows"])
    expected_phase = "MONITORING" if final else "COMMISSION_VERIFY"
    if not (
        action == "WINDOW" and phase == expected_phase
        and fields["index"] == expected
        and fields["total"] == int(policy["verify_windows"])
        and fields["score_valid"] == 1
    ):
        raise RuntimeProtocolError("COMMISSION_VERIFY sequence mismatch")
    state["verify_windows"] = expected
    state["monitoring"] = final
    return state


class RuntimeSequence:
    """Compatibility wrapper around the serializable production tracker."""

    def __init__(self) -> None:
        self.state = new_runtime_sequence_state()
        self.profile: RuntimeRecord | None = None

    def feed(self, line: str) -> RuntimeRecord | None:
        record = parse_runtime_record(line)
        if record is None:
            return None
        advance_runtime_sequence(self.state, record)
        if record.kind == "PROFILE":
            self.profile = record
        return record
