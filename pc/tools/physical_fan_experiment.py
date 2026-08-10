r"""Rucni zapis stvarnog testa ventilatora uz ASD_PSD_LIVE firmware.

Alat NE pusta pripremljene WAV-ove i NE generise/simulira kvar. Samo resetuje
vec flesiranu plocicu (osim uz --no-reset), cita njen serijski izlaz i vezuje
DET odluke za vremenski oznacene, rucno unesene uslove fizickog eksperimenta.

Primjeri (iz korijena repozitorija):

    .venv\Scripts\python.exe pc\tools\physical_fan_experiment.py preflight
    .venv\Scripts\python.exe pc\tools\physical_fan_experiment.py run ^
        --port COM3 --fan-id fan01 --session-id cold-start-01 ^
        --distance-cm 15 --room laboratorija

Tokom runa unesite ``condition <oznaka> [biljeska]``, ``note <tekst>``,
``abort <razlog>`` ili ``stop``. Dozvoljene oznake i bezbjednosna ogranicenja su u
docs/protokol-fizicki-ventilator.md.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import queue
import re
import subprocess
import sys
import threading
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "results" / "physical_fan"
FIRMWARE_DIR = ROOT / "firmware" / "esp32s3_asd"
PROTOCOL_VERSION = "physical-fan-v1.5.0"
QUALITY_PROTOCOL_VERSION = "asd-quality-v1.2.0"

RELEVANT_FILES = (
    ROOT / "pc" / "tools" / "physical_fan_experiment.py",
    FIRMWARE_DIR / "main" / "app_main.c",
    FIRMWARE_DIR / "main" / "psd_live.c",
    FIRMWARE_DIR / "main" / "audio_quality_state.c",
    FIRMWARE_DIR / "main" / "audio_quality_state.h",
    FIRMWARE_DIR / "main" / "psd_features_c.c",
    FIRMWARE_DIR / "main" / "psd_model_data.h",
    ROOT / "pc" / "config" / "asd_quality_policy_v1.json",
)

QUALITY_POLICY_RECORD = json.loads(
    (ROOT / "pc" / "config" / "asd_quality_policy_v1.json").read_text(encoding="utf-8")
)
QUALITY_POLICY = QUALITY_POLICY_RECORD["policy"]

ASCII_RECORD_RE = re.compile(
    r"\b(?P<kind>QUALITY|STATE|EVENT)(?:\s+(?P<body>.*))?$"
)
KEY_VALUE_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\S+)")

QUALITY_FIELDS = [
    "host_utc", "elapsed_s", "protocol", "phase", "index", "total",
    "result", "metrics_valid", "feature_valid", "samples", "expected", "rms_dbfs", "dc", "peak",
    "clipped", "zeros", "stuck", "dropped_delta", "tonalness_proxy",
    "tonalness_valid", "tonal_gate", "loo_mean", "loo_sd", "loo_cv", "loo_range", "loo_gate",
]
STATE_FIELDS = [
    "host_utc", "elapsed_s", "protocol", "from_state", "to_state", "reason",
]
FIRMWARE_EVENT_FIELDS = [
    "host_utc", "elapsed_s", "protocol", "type", "state", "phase", "reason",
]
PARSE_ERROR_FIELDS = ["host_utc", "elapsed_s", "record_kind", "reason", "raw_line"]

EXPECTED_QUALITY_COUNTS = {"WAIT": 60, "CAL": 10, "CAL_SUMMARY": 1}
WAIT_EXPECTED_SAMPLES = 4096
CLIP_EXPECTED_SAMPLES = 39 * 4096
N_CONSECUTIVE_ALARM = 3
SCORE_NEGATIVE_TOL = 1.0e-3
PCM_LEVEL_REL_TOL = 1.0e-3
PCM_LEVEL_ABS_TOL = 1.0
TERMINAL_DRAIN_TIMEOUT_S = 2.5
FINAL_BUFFER_DRAIN_TIMEOUT_S = 0.50
FINAL_BUFFER_QUIET_S = 0.10
TERMINAL_FIRMWARE_STATES = {
    "SENSOR_ERROR", "CALIBRATION_REJECTED", "RECALIBRATION_REQUIRED",
}
FIRMWARE_STATES = TERMINAL_FIRMWARE_STATES | {
    "NO_MACHINE", "CALIBRATED_NORMAL", "ANOMALY",
}
QUALITY_REJECT_RESULTS = {
    "SHORT_READ", "NONFINITE", "STUCK_SIGNAL", "LOW_LEVEL_OBSERVATION",
    "INSUFFICIENT_LEVEL", "CLIPPING", "DROPPED_SAMPLES", "INVALID_ARGUMENT",
}

DET_RE = re.compile(
    r"^DET\s+(?P<window>\d+)\s+"
    r"score=(?P<score>\S+)\s+lo=(?P<lo>\S+)\s+"
    r"hi=(?P<threshold>\S+)\s+led=(?P<led>\S+)\s+"
    r"anom=(?P<alarm>\S+)\s+total_anom=(?P<total_alarm>\S+)\s+"
    r"(?P<verdict>.*?)\s+\(uzastopnih=(?P<consecutive>\d+)\s+"
    r"nivo=(?P<level_dbfs>\S+)\s+dBFS\s+"
    r"racun=(?P<compute_ms>\d+)\s+ms\)$"
)
WAIT_RE = re.compile(
    r"\bWAIT\s+(?P<index>\d+)/(?P<total>\d+).*?nivo="
    r"(?P<level_dbfs>[-+\d.eE]+)\s+dBFS\s+(?P<audible>\S+)"
)
CAL_RE = re.compile(
    r"\bCAL\s+(?P<index>\d+)/(?P<total>\d+).*?nivo="
    r"(?P<level_dbfs>[-+\d.eE]+)\s+dBFS\s+racun="
    r"(?P<compute_ms>\d+)\s+ms"
)
ADAPT_RE = re.compile(r"\bADAPTTHR(?:\s+(?P<body>.*))?$")
DROPPED_RE = re.compile(r"\bdropped=(?P<dropped>\d+)")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
    if not slug:
        raise ValueError("oznaka ne smije biti prazna")
    return slug[:80]


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_output(*args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return proc.stdout.rstrip()


def list_ports() -> list[dict[str, Any]]:
    try:
        from serial.tools import list_ports as serial_list_ports
    except ImportError as exc:  # pragma: no cover - environment error
        raise SystemExit("nedostaje pyserial; koristi projektnu .venv") from exc

    ports = []
    for port in sorted(serial_list_ports.comports(), key=lambda item: item.device):
        ports.append({
            "device": port.device,
            "description": port.description,
            "hwid": port.hwid,
            "vid": port.vid,
            "pid": port.pid,
            "serial_number": port.serial_number,
            "manufacturer": port.manufacturer,
            "product": port.product,
        })
    return ports


def build_is_psd_live() -> bool:
    ninja = FIRMWARE_DIR / "build" / "build.ninja"
    if not ninja.is_file():
        return False
    return "-DASD_PSD_LIVE" in ninja.read_text(encoding="utf-8", errors="replace")


def collect_provenance(args: argparse.Namespace, ports: list[dict[str, Any]]) -> dict[str, Any]:
    build_bin = FIRMWARE_DIR / "build" / "esp32s3_asd.bin"
    project_json = FIRMWARE_DIR / "build" / "project_description.json"
    project: dict[str, Any] = {}
    if project_json.is_file():
        try:
            raw = json.loads(project_json.read_text(encoding="utf-8"))
            project = {
                key: raw.get(key)
                for key in ("project_name", "project_version", "idf_path", "git_revision", "target")
            }
        except (OSError, json.JSONDecodeError):
            project = {"parse_error": True}

    return {
        "protocol_version": PROTOCOL_VERSION,
        "quality_protocol_version": QUALITY_PROTOCOL_VERSION,
        "created_utc": utc_now(),
        "command": sys.argv,
        "python": sys.version,
        "git": {
            "head": git_output("rev-parse", "HEAD"),
            "status_porcelain": git_output("status", "--porcelain=v1"),
            "diff_sha256": hashlib.sha256(
                (git_output("diff", "--binary", "HEAD") or "").encode("utf-8")
            ).hexdigest(),
        },
        "serial_ports_seen": ports,
        "requested_port": getattr(args, "port", None),
        "baud": getattr(args, "baud", None),
        "firmware": {
            "psd_live_build_flag_confirmed": build_is_psd_live(),
            "build_bin": str(build_bin.relative_to(ROOT)),
            "build_bin_sha256": sha256_file(build_bin),
            "build_bin_bytes": build_bin.stat().st_size if build_bin.is_file() else None,
            "build_bin_mtime_utc": (
                datetime.fromtimestamp(build_bin.stat().st_mtime, timezone.utc).isoformat()
                if build_bin.is_file() else None
            ),
            "project_description": project,
        },
        "source_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path)
            for path in RELEVANT_FILES
        },
    }


def _parse_strict_key_values(
    record_kind: str, body: str, line: str,
) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    pairs: list[tuple[str, str]] = []
    for token in body.split():
        match = KEY_VALUE_RE.fullmatch(token)
        if not match:
            return None, {
                "kind": "PARSE_ERROR", "record_kind": record_kind,
                "reason": "malformed_key_value_token", "raw_line": line,
            }
        pairs.append((match.group("key"), match.group("value")))
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            return None, {
                "kind": "PARSE_ERROR", "record_kind": record_kind,
                "reason": f"duplicate_key:{key}", "raw_line": line,
            }
        seen.add(key)
    return dict(pairs), None


def parse_serial_line(line: str) -> dict[str, Any] | None:
    """Parse one firmware status line without depending on ESP-IDF log prefix."""
    ascii_record = ASCII_RECORD_RE.search(line)
    if ascii_record:
        kind = ascii_record.group("kind")
        values, parse_error = _parse_strict_key_values(
            kind, ascii_record.group("body") or "", line,
        )
        if parse_error:
            return parse_error
        assert values is not None
        protocol = values.get("protocol")
        if protocol is None:
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": "invalid_protocol_missing", "raw_line": line,
            }
        if protocol != QUALITY_PROTOCOL_VERSION:
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": "invalid_protocol_mismatch", "raw_line": line,
            }
        integer_fields = {
            "index", "total", "samples", "expected", "peak", "clipped",
            "zeros", "stuck", "dropped_delta", "metrics_valid", "feature_valid",
            "tonalness_valid",
        }
        float_fields = {
            "rms_dbfs", "dc", "tonalness_proxy", "loo_mean", "loo_sd",
            "loo_cv", "loo_range",
        }
        parsed: dict[str, Any] = {"kind": kind, "protocol": values.pop("protocol")}
        try:
            for key, value in values.items():
                if key in integer_fields:
                    parsed[key] = int(value)
                elif key in float_fields:
                    parsed[key] = float(value)
                elif kind == "STATE" and key == "from":
                    parsed["from_state"] = value
                elif kind == "STATE" and key == "to":
                    parsed["to_state"] = value
                else:
                    parsed[key] = value
        except (ValueError, OverflowError):
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": "malformed_numeric_field", "raw_line": line,
            }

        required: set[str]
        if kind == "QUALITY":
            phase = parsed.get("phase")
            if phase in {"WAIT", "CAL", "DET"}:
                required = {
                    "protocol", "phase", "index", "total", "result", "samples",
                    "expected", "rms_dbfs", "dc", "peak", "clipped", "zeros",
                    "stuck", "dropped_delta", "metrics_valid", "feature_valid",
                    "tonalness_valid",
                    "tonalness_proxy", "tonal_gate",
                }
            elif phase == "CAL_SUMMARY":
                required = {
                    "protocol", "phase", "result", "loo_mean", "loo_sd",
                    "loo_cv", "loo_range", "loo_gate",
                }
            else:
                return {
                    "kind": "PARSE_ERROR", "record_kind": kind,
                    "reason": "unknown_quality_phase", "raw_line": line,
                }
        elif kind == "STATE":
            required = {"protocol", "from_state", "to_state", "reason"}
        else:
            required = {"protocol", "type", "state", "phase", "reason"}
        missing = sorted(required - parsed.keys())
        if missing:
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": "missing_fields:" + ",".join(missing), "raw_line": line,
            }
        extras = sorted(parsed.keys() - required - {"kind"})
        if extras:
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": "unexpected_fields:" + ",".join(extras), "raw_line": line,
            }
        if kind == "QUALITY":
            if parsed["phase"] == "CAL_SUMMARY":
                for field in ("loo_mean", "loo_sd", "loo_cv", "loo_range"):
                    if -SCORE_NEGATIVE_TOL <= parsed[field] < 0.0:
                        parsed[field] = 0.0
            elif (
                parsed["tonalness_valid"] == 1
                and -SCORE_NEGATIVE_TOL <= parsed["tonalness_proxy"] < 0.0
            ):
                parsed["tonalness_proxy"] = 0.0
        return parsed

    match = DET_RE.fullmatch(line.strip())
    if match:
        row = match.groupdict()
        try:
            parsed_det = {
                "kind": "DET",
                "window": int(row["window"]),
                "score": float(row["score"]),
                "lo": float(row["lo"]),
                "threshold": float(row["threshold"]),
                "led": int(row["led"]),
                "alarm": int(row["alarm"]),
                "total_alarm": int(row["total_alarm"]),
                "verdict": row["verdict"].strip(),
                "consecutive": int(row["consecutive"]),
                "level_dbfs": float(row["level_dbfs"]),
                "compute_ms": int(row["compute_ms"]),
            }
            if -SCORE_NEGATIVE_TOL <= parsed_det["score"] < 0.0:
                parsed_det["score"] = 0.0
            return parsed_det
        except (ValueError, OverflowError):
            return {
                "kind": "PARSE_ERROR", "record_kind": "DET",
                "reason": "malformed_numeric_field", "raw_line": line,
            }
    if line.strip().startswith("DET "):
        return {
            "kind": "PARSE_ERROR", "record_kind": "DET",
            "reason": "malformed_or_truncated_det", "raw_line": line,
        }

    match = WAIT_RE.search(line)
    if match:
        row = match.groupdict()
        return {
            "kind": "WAIT", "index": int(row["index"]), "total": int(row["total"]),
            "level_dbfs": float(row["level_dbfs"]), "audible": row["audible"],
        }

    match = CAL_RE.search(line)
    if match:
        row = match.groupdict()
        return {
            "kind": "CAL", "index": int(row["index"]), "total": int(row["total"]),
            "level_dbfs": float(row["level_dbfs"]), "compute_ms": int(row["compute_ms"]),
        }

    match = ADAPT_RE.search(line)
    if match:
        values, parse_error = _parse_strict_key_values(
            "ADAPTTHR", match.group("body") or "", line,
        )
        if parse_error:
            return parse_error
        assert values is not None
        expected_keys = {"n", "mean", "sd", "k", "theta", "p", "thr", "lo", "factory"}
        if set(values) != expected_keys:
            missing = sorted(expected_keys - set(values))
            extras = sorted(set(values) - expected_keys)
            reason = "ADAPTTHR_schema"
            if missing:
                reason += ":missing=" + ",".join(missing)
            if extras:
                reason += ":extra=" + ",".join(extras)
            return {
                "kind": "PARSE_ERROR", "record_kind": "ADAPTTHR",
                "reason": reason, "raw_line": line,
            }
        try:
            parsed_adapt = {
                "kind": "ADAPTTHR",
                "n": int(values["n"]),
                "mean": float(values["mean"]),
                "sd": float(values["sd"]),
                "k": float(values["k"]),
                "theta": float(values["theta"]),
                "p": float(values["p"]),
                "threshold": float(values["thr"]),
                "lo": float(values["lo"]),
                "factory": float(values["factory"]),
            }
        except (ValueError, OverflowError):
            return {
                "kind": "PARSE_ERROR", "record_kind": "ADAPTTHR",
                "reason": "malformed_numeric_field", "raw_line": line,
            }
        for key in ("mean", "sd", "k", "theta", "p", "threshold", "lo", "factory"):
            if not math.isfinite(float(parsed_adapt[key])):
                return {
                    "kind": "PARSE_ERROR", "record_kind": "ADAPTTHR",
                    "reason": f"nonfinite_field:ADAPTTHR:{key}", "raw_line": line,
                }
        return parsed_adapt

    dropped = DROPPED_RE.search(line)
    if dropped:
        return {"kind": "DROPPED", "dropped": int(dropped.group("dropped"))}
    return None


def new_firmware_protocol_state() -> dict[str, Any]:
    """Return a JSON-serializable, immutable-by-convention host tracker."""
    return {
        "handshake": False,
        "quality_counts": {"WAIT": 0, "CAL": 0, "CAL_SUMMARY": 0, "DET": 0},
        "wait_ok_count": 0,
        "cal_summary": None,
        "adapt_seen": False,
        "adapt_threshold": None,
        "calibration_accepted_state": False,
        "calibration_accepted_event": False,
        "expected_state_transition": None,
        "pending_state_event": None,
        "det_records": 0,
        "pending_det_quality": None,
        "last_det_window": 0,
        "last_total_alarm": 0,
        "last_consecutive": 0,
        "det_threshold": None,
        "terminal": False,
        "drain_required": False,
        "terminal_state_seen": False,
        "terminal_event_seen": False,
        "drain_expected_phase": None,
        "drain_expected_reason": None,
        "drain_expected_state": None,
        "drain_mismatch": None,
        "last_state": None,
        "invalid_status": None,
        "invalid_reason": None,
    }


def firmware_protocol_ready(state: dict[str, Any]) -> bool:
    counts = state["quality_counts"]
    return bool(
        state["handshake"]
        and state["calibration_accepted_state"]
        and state["calibration_accepted_event"]
        and state["adapt_seen"]
        and all(counts[phase] == expected for phase, expected in EXPECTED_QUALITY_COUNTS.items())
        and state["expected_state_transition"] is None
        and state["pending_state_event"] is None
        and not state["terminal"]
        and state["invalid_status"] is None
    )


def firmware_protocol_complete(state: dict[str, Any]) -> bool:
    return bool(
        firmware_protocol_ready(state)
        and state["pending_det_quality"] is None
        and state["expected_state_transition"] is None
        and state["pending_state_event"] is None
        and state["quality_counts"]["DET"] == state["det_records"]
    )


def terminal_drain_decision(
    state: dict[str, Any], elapsed_s: float, timeout_s: float = TERMINAL_DRAIN_TIMEOUT_S,
) -> str:
    """Pure bounded-drain decision used by the serial loop and unit tests."""
    if not state["drain_required"]:
        return "not_required"
    if state["terminal_state_seen"] and state["terminal_event_seen"]:
        return "complete"
    if elapsed_s >= timeout_s:
        return "timeout"
    return "continue"


def final_buffer_drain_decision(elapsed_s: float, quiet_s: float) -> str:
    if elapsed_s >= FINAL_BUFFER_DRAIN_TIMEOUT_S or quiet_s >= FINAL_BUFFER_QUIET_S:
        return "complete"
    return "continue"


def parse_condition_command(rest: str) -> tuple[str, str]:
    label, _, note = rest.partition(" ")
    normalized = safe_slug(label)
    if normalized.lower() == "unconfirmed":
        raise ValueError("oznaka unconfirmed je rezervisana")
    return normalized, note


def _invalidate(
    state: dict[str, Any], status: str, reason: str, *, drain: bool = False,
) -> dict[str, Any]:
    state["invalid_status"] = status
    state["invalid_reason"] = reason
    if drain:
        state["terminal"] = True
        state["drain_required"] = True
    return state


def _expected_terminal_state(reason: str, phase: str) -> str:
    if reason in {"LOW_LEVEL_OBSERVATION", "INSUFFICIENT_LEVEL"}:
        return "NO_MACHINE"
    if reason == "CLIPPING":
        return "RECALIBRATION_REQUIRED" if phase == "DET" else "CALIBRATION_REJECTED"
    return "SENSOR_ERROR"


def _inferred_terminal_phase(state: dict[str, Any]) -> str:
    if state["pending_det_quality"] is not None or state["calibration_accepted_event"]:
        return "DET"
    if state["quality_counts"]["CAL"] > 0 or state["quality_counts"]["CAL_SUMMARY"] > 0:
        return "CAL"
    return "WAIT"


def _quality_semantic_error(state: dict[str, Any], record: dict[str, Any]) -> str | None:
    phase = str(record["phase"])
    float_fields = (
        ("loo_mean", "loo_sd", "loo_cv", "loo_range")
        if phase == "CAL_SUMMARY"
        else ("rms_dbfs", "dc", "tonalness_proxy")
    )
    for field in float_fields:
        if not math.isfinite(float(record[field])):
            return f"nonfinite_field:{phase}:{field}"

    if phase != "CAL_SUMMARY":
        if (
            record["metrics_valid"] not in {0, 1}
            or record["feature_valid"] not in {0, 1}
            or record["tonalness_valid"] not in {0, 1}
        ):
            return "invalid_quality_valid_flag"
        if phase == "WAIT" and record["feature_valid"] != 0:
            return "WAIT_feature_must_be_not_computed"
        if record["feature_valid"] == 0 and record["tonalness_valid"] != 0:
            return f"tonalness_without_valid_feature:{phase}"
        if record["tonalness_valid"] == 0:
            if record["tonalness_proxy"] != 0.0 or record["tonal_gate"] != "not_computed":
                return f"invalid_tonalness_sentinel:{phase}"
        elif phase == "WAIT" or record["tonal_gate"] != "pending_normal_only":
            return f"invalid_tonalness_validity:{phase}"
        if record["tonalness_valid"] == 1 and record["tonalness_proxy"] < 0.0:
            return f"negative_tonalness:{phase}"

    if phase == "WAIT":
        expected_index = state["quality_counts"]["WAIT"] + 1
        if record["total"] != 60 or record["index"] != expected_index:
            return f"WAIT_sequence:expected={expected_index}/60:got={record['index']}/{record['total']}"
        expected_samples = WAIT_EXPECTED_SAMPLES
    elif phase == "CAL":
        expected_index = state["quality_counts"]["CAL"] + 1
        if record["total"] != 10 or record["index"] != expected_index:
            return f"CAL_sequence:expected={expected_index}/10:got={record['index']}/{record['total']}"
        expected_samples = CLIP_EXPECTED_SAMPLES
    elif phase == "CAL_SUMMARY":
        if state["quality_counts"]["CAL_SUMMARY"] != 0:
            return "duplicate_CAL_SUMMARY"
        if any(record[field] < 0.0 for field in ("loo_mean", "loo_sd", "loo_cv", "loo_range")):
            return "negative_CAL_SUMMARY_value"
        expected_cv = (
            record["loo_sd"] / abs(record["loo_mean"])
            if abs(record["loo_mean"]) > 1e-12 else 0.0
        )
        if not math.isclose(record["loo_cv"], expected_cv, rel_tol=2e-5, abs_tol=2e-6):
            return f"CAL_SUMMARY_cv_mismatch:expected={expected_cv}:got={record['loo_cv']}"
        if record["loo_range"] + 1e-6 < record["loo_sd"]:
            return "CAL_SUMMARY_range_smaller_than_sd"
        if (record["loo_sd"] <= 1e-12) != (record["loo_range"] <= 1e-12):
            return "CAL_SUMMARY_zero_spread_mismatch"
        if record["loo_gate"] != "pending_normal_only" or record["result"] != "OBSERVED":
            return "invalid_CAL_SUMMARY_schema_value"
        return None
    elif phase == "DET":
        expected_index = state["det_records"] + 1
        if state["pending_det_quality"] is not None:
            return "duplicate_or_replayed_DET_quality"
        if record["total"] != 0 or record["index"] != expected_index:
            return f"DET_quality_sequence:expected={expected_index}/0:got={record['index']}/{record['total']}"
        expected_samples = CLIP_EXPECTED_SAMPLES
    else:  # parser should already prevent this
        return f"unknown_quality_phase:{phase}"

    if record["expected"] != expected_samples:
        return f"sample_mismatch:{phase}:expected={record['expected']}:want={expected_samples}"
    samples = int(record["samples"])
    if not (0 <= samples <= expected_samples):
        return f"invalid_sample_count:{phase}:{samples}"
    if not (0 <= record["clipped"] <= samples):
        return f"invalid_count:{phase}:clipped"
    if not (0 <= record["zeros"] <= samples):
        return f"invalid_count:{phase}:zeros"
    if not (0 <= record["stuck"] <= max(0, samples - 1)):
        return f"invalid_count:{phase}:stuck"
    if record["dropped_delta"] < 0:
        return f"invalid_count:{phase}:dropped_delta"
    if not (0 <= record["peak"] <= 32768):
        return f"invalid_peak:{phase}:{record['peak']}"
    if record["rms_dbfs"] > 0.0:
        return f"positive_rms_dbfs:{phase}:{record['rms_dbfs']}"
    if abs(record["dc"]) > record["peak"] + 1e-3:
        return f"dc_exceeds_peak:{phase}"
    if record["metrics_valid"] == 1:
        rms_pcm = 32768.0 * (10.0 ** (record["rms_dbfs"] / 20.0))
        rms_limit = (
            record["peak"] * (1.0 + PCM_LEVEL_REL_TOL) + PCM_LEVEL_ABS_TOL
        )
        if rms_pcm > rms_limit:
            return f"rms_exceeds_peak:{phase}"
    zero_fraction = record["zeros"] / samples if samples else 1.0
    stuck_fraction = record["stuck"] / (samples - 1) if samples > 1 else 1.0
    if samples != expected_samples:
        expected_reason = "SHORT_READ"
    elif record["dropped_delta"] > int(QUALITY_POLICY["max_dropped_delta"]):
        expected_reason = "DROPPED_SAMPLES"
    elif (
        zero_fraction > float(QUALITY_POLICY["max_zero_fraction"])
        or stuck_fraction > float(QUALITY_POLICY["max_stuck_fraction"])
    ):
        expected_reason = "STUCK_SIGNAL"
    elif record["metrics_valid"] == 0:
        expected_reason = "NONFINITE"
    elif record["clipped"] / samples > float(QUALITY_POLICY["max_clip_fraction"]):
        expected_reason = "CLIPPING"
    elif record["rms_dbfs"] < float(QUALITY_POLICY["level_floor_dbfs"]):
        expected_reason = "LOW_LEVEL_OBSERVATION"
    elif phase in {"CAL", "DET"} and record["feature_valid"] == 0:
        expected_reason = "NONFINITE"
    else:
        expected_reason = "OK"
    if expected_reason == "OK" and phase in {"CAL", "DET"}:
        if record["feature_valid"] != 1 or record["tonalness_valid"] != 1:
            return f"accepted_observation_without_valid_feature:{phase}"
    if record["result"] != expected_reason:
        return f"quality_reason_mismatch:expected={expected_reason}:got={record['result']}"
    return None


def _det_semantic_error(state: dict[str, Any], record: dict[str, Any]) -> str | None:
    if state["pending_det_quality"] is None:
        return "DET_without_preceding_quality"
    for field in ("score", "lo", "threshold", "level_dbfs"):
        if not math.isfinite(float(record[field])):
            return f"nonfinite_field:DET:{field}"
    expected_window = state["last_det_window"] + 1
    if record["window"] != state["pending_det_quality"] or record["window"] != expected_window:
        return (
            f"DET_window_mismatch:pending={state['pending_det_quality']}:"
            f"expected={expected_window}:got={record['window']}"
        )
    if record["led"] not in {0, 1} or record["alarm"] not in {0, 1}:
        return f"invalid_binary_field:led={record['led']}:alarm={record['alarm']}"
    if record["compute_ms"] < 0 or record["total_alarm"] < 0 or record["consecutive"] < 0:
        return "negative_DET_counter"
    if record["lo"] != 0.0:
        return f"DET_lo_not_zero:{record['lo']}"
    if record["threshold"] < 0.0:
        return f"negative_DET_threshold:{record['threshold']}"
    if record["score"] < 0.0:
        return f"negative_DET_score:{record['score']}"
    if record["level_dbfs"] > 0.0:
        return f"positive_DET_level:{record['level_dbfs']}"
    threshold = float(record["threshold"])
    if state["adapt_threshold"] is None or threshold != state["adapt_threshold"]:
        return f"DET_ADAPTTHR_mismatch:adapt={state['adapt_threshold']}:det={threshold}"
    if state["det_threshold"] is not None and threshold != state["det_threshold"]:
        return f"DET_threshold_changed:{state['det_threshold']}->{threshold}"
    over = float(record["score"]) > threshold
    expected_consecutive = state["last_consecutive"] + 1 if over else 0
    expected_alarm = int(expected_consecutive >= N_CONSECUTIVE_ALARM)
    expected_total = state["last_total_alarm"] + expected_alarm
    expected_led = 1 - expected_alarm
    expected_verdict = "ALARM" if expected_alarm else ("iznad praga" if over else "normal")
    if record["consecutive"] != expected_consecutive:
        return f"consecutive_mismatch:expected={expected_consecutive}:got={record['consecutive']}"
    if record["alarm"] != expected_alarm or record["led"] != expected_led:
        return f"alarm_led_mismatch:alarm={record['alarm']}:led={record['led']}"
    if record["total_alarm"] != expected_total:
        return f"total_alarm_mismatch:expected={expected_total}:got={record['total_alarm']}"
    if record["verdict"] != expected_verdict:
        return f"verdict_mismatch:expected={expected_verdict}:got={record['verdict']}"
    return None


def transition_firmware_protocol(
    previous: dict[str, Any], record: dict[str, Any],
) -> dict[str, Any]:
    """Pure host transition: consume one parsed firmware/DET record."""
    state = {
        **previous,
        "quality_counts": dict(previous["quality_counts"]),
    }

    kind = record.get("kind")
    if state["invalid_status"] is not None:
        if state["drain_required"] and kind == "STATE":
            if record.get("to_state") in TERMINAL_FIRMWARE_STATES or record.get("to_state") == "NO_MACHINE":
                matches = bool(
                    record.get("from_state") == state["last_state"]
                    and (state["drain_expected_state"] is None
                         or record.get("to_state") == state["drain_expected_state"])
                    and (state["drain_expected_reason"] is None
                         or record.get("reason") == state["drain_expected_reason"])
                )
                if matches:
                    state["terminal_state_seen"] = True
                    state["last_state"] = record.get("to_state")
                    state["drain_expected_state"] = record.get("to_state")
                    if state["drain_expected_reason"] is None:
                        state["drain_expected_reason"] = record.get("reason")
                else:
                    state["drain_mismatch"] = "terminal_STATE_does_not_match_chain_or_reason"
        elif state["drain_required"] and kind == "EVENT" and record.get("type") == "FLOW_STOPPED":
            matches = bool(
                (state["drain_expected_state"] is None
                 or record.get("state") == state["drain_expected_state"])
                and (state["drain_expected_reason"] is None
                     or record.get("reason") == state["drain_expected_reason"])
                and (state["drain_expected_phase"] is None
                     or record.get("phase") == state["drain_expected_phase"])
            )
            if matches:
                state["terminal_event_seen"] = True
            else:
                state["drain_mismatch"] = "FLOW_STOPPED_does_not_match_terminal"
        return state

    if kind == "PARSE_ERROR":
        reason = str(record.get("reason", "malformed_firmware_telemetry"))
        state["invalid_status"] = (
            "invalid_protocol_mismatch"
            if reason in {"invalid_protocol_mismatch", "invalid_protocol_missing"}
            else "invalid_firmware_telemetry"
        )
        state["invalid_reason"] = reason
        return state

    pending_terminal_state = bool(
        kind == "STATE"
        and record.get("to_state") in TERMINAL_FIRMWARE_STATES | {"NO_MACHINE"}
    )
    if state["pending_det_quality"] is not None and kind != "DET" and not pending_terminal_state:
        reason = (
            "duplicate_or_replayed_DET_quality"
            if kind == "QUALITY" and record.get("phase") == "DET"
            else f"record_between_DET_quality_and_DET:{kind}"
        )
        return _invalidate(
            state, "invalid_firmware_telemetry", reason,
        )
    if state["expected_state_transition"] is not None and kind != "STATE":
        return _invalidate(
            state, "invalid_missing_telemetry",
            f"missing_expected_STATE_before:{kind}",
        )
    if state["pending_state_event"] is not None and kind != "EVENT":
        return _invalidate(
            state, "invalid_firmware_telemetry",
            f"missing_paired_EVENT_before:{kind}",
        )

    if kind == "QUALITY":
        phase = str(record["phase"])
        result = str(record["result"])
        if not state["handshake"]:
            state["invalid_status"] = "invalid_missing_telemetry"
            state["invalid_reason"] = "QUALITY_before_handshake"
            return state
        allowed_results = {
            "WAIT": {"OK", "LOW_LEVEL_OBSERVATION"},
            "CAL": {"OK"},
            "CAL_SUMMARY": {"OBSERVED"},
            "DET": {"OK"},
        }
        if result not in allowed_results.get(phase, set()) and result not in QUALITY_REJECT_RESULTS:
            return _invalidate(
                state, "invalid_firmware_telemetry",
                f"unknown_quality_result:{phase}:{result}",
            )
        semantic_error = _quality_semantic_error(state, record)
        if semantic_error:
            return _invalidate(state, "invalid_firmware_telemetry", semantic_error)
        if result not in allowed_results.get(phase, set()):
            state["drain_expected_phase"] = phase
            state["drain_expected_reason"] = result
            state["drain_expected_state"] = _expected_terminal_state(result, phase)
            return _invalidate(
                state, "invalid_firmware_terminal",
                f"quality_reject:{phase}:{result}", drain=True,
            )
        if phase == "CAL" and state["quality_counts"]["WAIT"] != EXPECTED_QUALITY_COUNTS["WAIT"]:
            state["invalid_status"] = "invalid_missing_telemetry"
            state["invalid_reason"] = "CAL_before_expected_WAIT_quality"
            return state
        if phase == "CAL" and state["wait_ok_count"] < 30:
            return _invalidate(
                state, "invalid_firmware_telemetry",
                f"CAL_before_sufficient_WAIT_OK:{state['wait_ok_count']}/60",
            )
        if phase == "CAL_SUMMARY" and state["quality_counts"]["CAL"] != EXPECTED_QUALITY_COUNTS["CAL"]:
            state["invalid_status"] = "invalid_missing_telemetry"
            state["invalid_reason"] = "CAL_SUMMARY_before_expected_CAL_quality"
            return state
        if phase == "DET" and not firmware_protocol_ready(state):
            state["invalid_status"] = "invalid_missing_telemetry"
            state["invalid_reason"] = "DET_quality_before_calibration_acceptance"
            return state
        state["quality_counts"][phase] = state["quality_counts"].get(phase, 0) + 1
        if phase == "WAIT" and result == "OK":
            state["wait_ok_count"] += 1
        if phase == "CAL_SUMMARY":
            state["cal_summary"] = {
                key: float(record[key])
                for key in ("loo_mean", "loo_sd", "loo_cv", "loo_range")
            }
        if phase == "DET":
            state["pending_det_quality"] = record["index"]
    elif kind == "ADAPTTHR":
        if state["adapt_seen"]:
            return _invalidate(state, "invalid_firmware_telemetry", "duplicate_ADAPTTHR")
        if state["quality_counts"]["CAL_SUMMARY"] != 1 or state["cal_summary"] is None:
            return _invalidate(
                state, "invalid_missing_telemetry", "ADAPTTHR_before_CAL_SUMMARY",
            )
        if state["calibration_accepted_state"] or state["calibration_accepted_event"]:
            return _invalidate(
                state, "invalid_firmware_telemetry", "ADAPTTHR_after_calibration_acceptance",
            )
        if record["n"] != 10 or record["sd"] < 0.0 or record["threshold"] < 0.0:
            return _invalidate(state, "invalid_firmware_telemetry", "invalid_ADAPTTHR_numeric")
        if not math.isclose(record["mean"], state["cal_summary"]["loo_mean"], abs_tol=1e-6):
            return _invalidate(state, "invalid_firmware_telemetry", "ADAPTTHR_mean_mismatch")
        if not math.isclose(record["sd"], state["cal_summary"]["loo_sd"], abs_tol=1e-6):
            return _invalidate(state, "invalid_firmware_telemetry", "ADAPTTHR_sd_mismatch")
        if not math.isclose(record["p"], 0.9, abs_tol=1e-6):
            return _invalidate(state, "invalid_firmware_telemetry", "ADAPTTHR_p_mismatch")
        if any(record[field] != 0.0 for field in ("k", "theta", "lo", "factory")):
            return _invalidate(state, "invalid_firmware_telemetry", "ADAPTTHR_legacy_field_mismatch")
        minimum_threshold = record["mean"] + 3.0 * record["sd"]
        if record["threshold"] + 2e-5 < minimum_threshold:
            return _invalidate(state, "invalid_firmware_telemetry", "ADAPTTHR_below_mean_plus_3sd")
        state["adapt_seen"] = True
        state["adapt_threshold"] = float(record["threshold"])
    elif kind == "STATE":
        from_state = str(record["from_state"])
        to_state = str(record["to_state"])
        reason = str(record["reason"])
        if from_state not in FIRMWARE_STATES or to_state not in FIRMWARE_STATES:
            return _invalidate(state, "invalid_firmware_telemetry", "unknown_STATE_name")
        is_boot = (
            from_state == "NO_MACHINE" and to_state == "NO_MACHINE"
            and reason == "BOOT_FAIL_CLOSED"
        )
        if state["last_state"] is None:
            if not is_boot:
                return _invalidate(state, "invalid_missing_telemetry", "first_STATE_not_BOOT")
            state["handshake"] = True
            state["last_state"] = "NO_MACHINE"
            return state
        if from_state != state["last_state"]:
            return _invalidate(
                state, "invalid_firmware_telemetry",
                f"STATE_chain_mismatch:expected_from={state['last_state']}:got={from_state}",
            )
        if is_boot:
            return _invalidate(state, "invalid_firmware_telemetry", "duplicate_BOOT_STATE")

        expected_transition = state["expected_state_transition"]
        if expected_transition is not None:
            expected_state = expected_transition["state"]
            actual_state = {
                "from_state": from_state, "to_state": to_state, "reason": reason,
            }
            if actual_state != expected_state:
                return _invalidate(
                    state, "invalid_firmware_telemetry",
                    "DET_STATE_transition_mismatch",
                )
            state["expected_state_transition"] = None
            state["last_state"] = to_state
            state["pending_state_event"] = expected_transition["event"]
            return state

        is_calibration_accept = (
            from_state == "NO_MACHINE" and to_state == "CALIBRATED_NORMAL"
            and reason == "CALIBRATION_ACCEPTED"
        )
        if is_calibration_accept and not all(
            state["quality_counts"][phase] == expected
            for phase, expected in EXPECTED_QUALITY_COUNTS.items()
        ):
            state["invalid_status"] = "invalid_missing_telemetry"
            state["invalid_reason"] = "CALIBRATION_ACCEPTED_before_expected_quality"
            return state
        if is_calibration_accept:
            if not state["adapt_seen"] or state["calibration_accepted_state"]:
                return _invalidate(
                    state, "invalid_missing_telemetry", "CALIBRATION_ACCEPTED_without_unique_ADAPTTHR",
                )
            state["calibration_accepted_state"] = True
            state["last_state"] = to_state
            state["pending_state_event"] = {
                "type": "CALIBRATION_ACCEPTED", "state": "CALIBRATED_NORMAL",
                "phase": "CAL", "reason": "QUALITY_OK",
            }
            return state

        normal_transition_event: dict[str, str] | None = None
        if from_state == "CALIBRATED_NORMAL" and to_state == "ANOMALY" and reason == "THRESHOLD_PERSISTENCE":
            normal_transition_event = {
                "type": "ANOMALY_ENTERED", "state": "ANOMALY",
                "phase": "DET", "reason": "THRESHOLD_PERSISTENCE",
            }
        elif from_state == "ANOMALY" and to_state == "CALIBRATED_NORMAL" and reason == "ALARM_CLEARED":
            normal_transition_event = {
                "type": "ANOMALY_CLEARED", "state": "CALIBRATED_NORMAL",
                "phase": "DET", "reason": "ALARM_CLEARED",
            }
        if normal_transition_event is not None:
            return _invalidate(
                state, "invalid_firmware_telemetry", "spurious_DET_STATE_transition",
            )

        if to_state == "NO_MACHINE" or to_state in TERMINAL_FIRMWARE_STATES:
            if reason not in QUALITY_REJECT_RESULTS:
                return _invalidate(state, "invalid_firmware_telemetry", "terminal_STATE_reason_unknown")
            phase = state["drain_expected_phase"] or _inferred_terminal_phase(state)
            expected_terminal = _expected_terminal_state(reason, phase)
            if to_state != expected_terminal:
                state["drain_expected_phase"] = phase
                state["drain_expected_state"] = expected_terminal
                state["drain_expected_reason"] = reason
                return _invalidate(
                    state, "invalid_firmware_telemetry",
                    f"terminal_STATE_mapping:expected={expected_terminal}:got={to_state}",
                    drain=True,
                )
            state["last_state"] = to_state
            state["drain_expected_state"] = to_state
            state["drain_expected_reason"] = reason
            state["drain_expected_phase"] = phase
            _invalidate(
                state, "invalid_firmware_terminal",
                "terminal_state:" + to_state, drain=True,
            )
            state["terminal_state_seen"] = True
            return state
        return _invalidate(state, "invalid_firmware_telemetry", "illegal_STATE_transition")
    elif kind == "EVENT":
        event_payload = {
            key: str(record[key]) for key in ("type", "state", "phase", "reason")
        }
        if event_payload["state"] not in FIRMWARE_STATES:
            return _invalidate(state, "invalid_firmware_telemetry", "unknown_EVENT_state")
        if state["pending_state_event"] is not None:
            if event_payload != state["pending_state_event"]:
                return _invalidate(state, "invalid_firmware_telemetry", "STATE_EVENT_pair_mismatch")
            state["pending_state_event"] = None
            if event_payload["type"] == "CALIBRATION_ACCEPTED":
                if state["calibration_accepted_event"]:
                    return _invalidate(state, "invalid_firmware_telemetry", "duplicate_CALIBRATION_ACCEPTED_EVENT")
                state["calibration_accepted_event"] = True
            return state
        if event_payload["type"] == "FLOW_STOPPED":
            if event_payload["reason"] not in QUALITY_REJECT_RESULTS:
                return _invalidate(state, "invalid_firmware_telemetry", "FLOW_STOPPED_reason_unknown")
            if event_payload["phase"] not in {"WAIT", "CAL", "DET"}:
                return _invalidate(state, "invalid_firmware_telemetry", "FLOW_STOPPED_phase_unknown")
            expected_terminal = _expected_terminal_state(
                event_payload["reason"], event_payload["phase"],
            )
            if event_payload["state"] != expected_terminal:
                return _invalidate(
                    state, "invalid_firmware_telemetry",
                    f"FLOW_STOPPED_mapping:expected={expected_terminal}:got={event_payload['state']}",
                    drain=True,
                )
            state["drain_expected_state"] = event_payload["state"]
            state["drain_expected_phase"] = event_payload["phase"]
            state["drain_expected_reason"] = event_payload["reason"]
            _invalidate(
                state, "invalid_firmware_terminal",
                "terminal_event:FLOW_STOPPED_without_terminal_STATE", drain=True,
            )
            state["terminal_event_seen"] = True
            return state
        return _invalidate(state, "invalid_firmware_telemetry", "unknown_or_unpaired_EVENT")
    elif kind == "DET":
        if not firmware_protocol_ready(state):
            state["invalid_status"] = "invalid_missing_telemetry"
            state["invalid_reason"] = "DET_before_handshake_calibration_or_expected_counts"
        else:
            semantic_error = _det_semantic_error(state, record)
            if semantic_error:
                return _invalidate(state, "invalid_firmware_telemetry", semantic_error)
            state["det_records"] += 1
            state["pending_det_quality"] = None
            state["last_det_window"] = record["window"]
            state["last_total_alarm"] = record["total_alarm"]
            state["last_consecutive"] = record["consecutive"]
            if state["det_threshold"] is None:
                state["det_threshold"] = float(record["threshold"])
            if state["last_state"] == "CALIBRATED_NORMAL" and record["alarm"] == 1:
                state["expected_state_transition"] = {
                    "state": {
                        "from_state": "CALIBRATED_NORMAL", "to_state": "ANOMALY",
                        "reason": "THRESHOLD_PERSISTENCE",
                    },
                    "event": {
                        "type": "ANOMALY_ENTERED", "state": "ANOMALY",
                        "phase": "DET", "reason": "THRESHOLD_PERSISTENCE",
                    },
                }
            elif state["last_state"] == "ANOMALY" and record["alarm"] == 0:
                state["expected_state_transition"] = {
                    "state": {
                        "from_state": "ANOMALY", "to_state": "CALIBRATED_NORMAL",
                        "reason": "ALARM_CLEARED",
                    },
                    "event": {
                        "type": "ANOMALY_CLEARED", "state": "CALIBRATED_NORMAL",
                        "phase": "DET", "reason": "ALARM_CLEARED",
                    },
                }
    return state


def create_run_dir(base: Path, prefix: str, fan_id: str, session_id: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    stem = f"{prefix}_{stamp}_{safe_slug(fan_id)}_{safe_slug(session_id)}"
    candidate = base / stem
    suffix = 1
    while candidate.exists():
        candidate = base / f"{stem}_{suffix:02d}"
        suffix += 1
    candidate.mkdir(parents=True)
    return candidate


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record_preflight(args: argparse.Namespace) -> int:
    ports = list_ports()
    run_dir = create_run_dir(Path(args.output_dir), "preflight", "no-fan", "hardware")
    provenance = collect_provenance(args, ports)
    status = "ready" if ports else "blocked_no_serial_port"
    payload = {
        "status": status,
        "checked_utc": utc_now(),
        "serial_port_count": len(ports),
        "ports": ports,
        "firmware_build_ready": provenance["firmware"],
        "next_action": (
            "izaberi tacan COM port i pokreni run"
            if ports else "spoji ESP32-S3 podatkovnim USB kablom i ponovi preflight"
        ),
    }
    write_json(run_dir / "preflight.json", payload)
    write_json(run_dir / "provenance.json", provenance)
    (run_dir / "SUMMARY.md").write_text(
        "# Preflight fizickog fan eksperimenta\n\n"
        f"- Status: `{status}`\n"
        f"- Vrijeme (UTC): `{payload['checked_utc']}`\n"
        f"- Broj serijskih portova: **{len(ports)}**\n"
        f"- Postojeci build ima `ASD_PSD_LIVE`: "
        f"**{provenance['firmware']['psd_live_build_flag_confirmed']}**\n"
        f"- Sljedeca radnja: {payload['next_action']}\n\n"
        "Ovo nije fizicki eksperimentalni rezultat; nije snimljen nijedan DET prozor.\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"preflight artefakti: {run_dir}")
    return 0 if ports else 2


def add_event(
    events: list[dict[str, Any]], writer: csv.DictWriter, handle: Any, *,
    started: float, kind: str, label: str, note: str = "",
) -> dict[str, Any]:
    event = {
        "host_utc": utc_now(),
        "elapsed_s": round(time.monotonic() - started, 3),
        "kind": kind,
        "label": label,
        "note": note,
    }
    events.append(event)
    writer.writerow(event)
    handle.flush()
    return event


def input_worker(commands: queue.Queue[str]) -> None:
    while True:
        line = sys.stdin.readline()
        if line == "":
            return
        commands.put(line.strip())


def poll_command_file(path: Path, offset: int) -> tuple[int, list[str]]:
    """Read only commands appended after *offset* (for headless capture)."""
    if not path.exists():
        return offset, []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        handle.seek(offset)
        lines = [line.strip() for line in handle if line.strip()]
        return handle.tell(), lines


def resolve_port(requested: str, ports: list[dict[str, Any]]) -> str:
    devices = [str(port["device"]) for port in ports]
    if requested.lower() == "auto":
        if len(devices) != 1:
            raise SystemExit(
                f"--port auto zahtijeva tacno jedan port; pronadjeno {len(devices)}: {devices}"
            )
        return devices[0]
    match = next((device for device in devices if device.lower() == requested.lower()), None)
    if match is None:
        raise SystemExit(f"trazeni port {requested!r} nije enumerisan; dostupno: {devices}")
    return match


def make_summary(
    *, metadata: dict[str, Any], status: str, events: list[dict[str, Any]],
    detections: list[dict[str, Any]], max_dropped: int | None,
    protocol_state: dict[str, Any] | None = None,
) -> str:
    threshold = (
        protocol_state.get("adapt_threshold")
        if protocol_state is not None else None
    )
    valid_detections = [
        row for row in detections
        if int(row.get("condition_confirmed", 0)) == 1
        and int(row.get("protocol_valid", 0)) == 1
    ]
    protocol_valid_detections = [
        row for row in detections if int(row.get("protocol_valid", 0)) == 1
    ]
    tracker_count_consistent = bool(
        protocol_state is not None
        and protocol_state["det_records"] == len(protocol_valid_detections)
    )
    valid_result = bool(
        status.startswith("completed") and valid_detections
        and protocol_state is not None and firmware_protocol_complete(protocol_state)
        and tracker_count_consistent
    )
    lines = [
        "# Stvarni fizicki fan eksperiment",
        "",
        f"- Status: `{status}`",
        f"- Validan fizički rezultat: **{'DA' if valid_result else 'NE'}**",
        f"- Protokol: `{PROTOCOL_VERSION}`",
        f"- Fan ID: `{metadata['fan_id']}`",
        f"- Sesija: `{metadata['session_id']}`",
        f"- Port: `{metadata['port']}` @ {metadata['baud']} baud",
        f"- Udaljenost: {metadata['distance_cm']} cm",
        f"- Prostorija: {metadata['room']}",
        f"- Prag: {threshold if threshold is not None else 'nije dobijen'}",
        f"- DET prozora: {len(detections)}",
        f"- Validnih DET prozora za metrike: {len(valid_detections)}",
        f"- Protocol-valid DET prozora: {len(protocol_valid_detections)}",
        f"- Tracker/CSV DET count saglasan: **{'DA' if tracker_count_consistent else 'NE'}**",
        f"- Isključenih DET prozora: {len(detections) - len(valid_detections)}",
        f"- Alarmnih validnih DET prozora: {sum(int(row['alarm']) for row in valid_detections)}",
        f"- Najveci prijavljeni `dropped`: {max_dropped if max_dropped is not None else 'nije ispisan'}",
        "",
        "## Rezultati po rucno oznacenom uslovu",
        "",
        "| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |",
        "|---|---:|---:|---:|---:|",
    ]
    labels: list[str] = []
    for row in valid_detections:
        label = str(row["condition"])
        if label not in labels:
            labels.append(label)
    for label in labels:
        rows = [row for row in valid_detections if row["condition"] == label]
        scores = sorted(float(row["score"]) for row in rows)
        mid = len(scores) // 2
        median = scores[mid] if len(scores) % 2 else (scores[mid - 1] + scores[mid]) / 2
        lines.append(
            f"| {label} | {len(rows)} | {sum(int(row['alarm']) for row in rows)} | "
            f"{median:.3f} | {scores[0]:.3f}..{scores[-1]:.3f} |"
        )
    if not labels:
        lines.append("| (nema DET podataka) | 0 | 0 | - | - |")
    lines.extend([
        "",
        "## Ogranicenje",
        "",
        "Samo DET prozori nakon eksplicitne operatorove condition komande i "
        "nakon validnog firmware handshake/CAL ugovora ulaze u metrike. "
        "Uslovi su vremenski oznaceni na PC-u kada je operater unio komandu. "
        "Jedan DET prozor pokriva oko 10 s, pa granicni prozor moze sadrzati "
        "dio prethodnog i dio novog uslova. Ovaj zapis ne naziva bezbjedno "
        "izazvanu promjenu 'stvarnim kvarom' bez nezavisne fizicke potvrde.",
        "",
        "## Dogadjaji",
        "",
    ])
    for event in events:
        lines.append(
            f"- `{event['elapsed_s']:.3f} s` **{event['kind']} / {event['label']}**"
            + (f": {event['note']}" if event["note"] else "")
        )
    return "\n".join(lines) + "\n"


class AuditedExitStack(ExitStack):
    """Preserve a close failure so provenance can be finalized before raising."""

    def __init__(self) -> None:
        super().__init__()
        self.close_error: Exception | None = None

    def __exit__(self, *exc_details: Any) -> bool:
        try:
            return bool(super().__exit__(*exc_details))
        except Exception as exc:
            self.close_error = exc
            return True


def _best_effort_finalize_setup_failure(
    run_dir: Path, provenance: dict[str, Any], metadata: dict[str, Any],
    exc: BaseException,
) -> None:
    """Replace in_progress after import/open/close failure where disk permits."""
    provenance.update({
        "status": "failed",
        "finished_utc": utc_now(),
        "metadata": metadata,
        "failure": f"{type(exc).__name__}: {exc}",
    })
    try:
        write_json(run_dir / "provenance.json", provenance)
    except OSError:
        pass
    try:
        (run_dir / "SUMMARY.md").write_text(
            make_summary(
                metadata=metadata, status="failed", events=[], detections=[],
                max_dropped=None, protocol_state=new_firmware_protocol_state(),
            ),
            encoding="utf-8",
        )
    except OSError:
        pass


def run_experiment(args: argparse.Namespace) -> int:
    ports = list_ports()
    port = resolve_port(args.port, ports)
    if not build_is_psd_live():
        raise SystemExit("postojeci build nije potvrđen kao ASD_PSD_LIVE; ne pokrecem run")

    if not args.ready:
        answer = input(
            "Potvrdi da je ventilator stabilno i bezbjedno montiran, radi NORMALNO, "
            "mikrofon je fiksiran i lopatice se nece dodirivati [upiši DA]: "
        ).strip()
        if answer != "DA":
            raise SystemExit("run otkazan: bez eksplicitne potvrde 'DA'")

    args.port = port
    run_dir = create_run_dir(Path(args.output_dir), "run", args.fan_id, args.session_id)
    metadata = {
        "fan_id": args.fan_id,
        "session_id": args.session_id,
        "port": port,
        "baud": args.baud,
        "distance_cm": args.distance_cm,
        "angle_deg": args.angle_deg,
        "room": args.room,
        "fan_speed_or_voltage": args.fan_speed_or_voltage,
        "ambient": args.ambient,
        "operator_notes": args.notes,
        "external_wav": str(Path(args.wav_path).resolve()) if args.wav_path else None,
        "external_wav_sha256_at_start": sha256_file(Path(args.wav_path)) if args.wav_path else None,
    }
    provenance = collect_provenance(args, ports)
    provenance.update({"status": "in_progress", "metadata": metadata, "run_dir": str(run_dir)})
    write_json(run_dir / "provenance.json", provenance)

    try:
        import serial
    except Exception as exc:
        _best_effort_finalize_setup_failure(run_dir, provenance, metadata, exc)
        raise

    events: list[dict[str, Any]] = []
    detections: list[dict[str, Any]] = []
    max_dropped: int | None = None
    telemetry_counts = {"QUALITY": 0, "STATE": 0, "EVENT": 0}
    last_firmware_state: str | None = None
    protocol_state = new_firmware_protocol_state()
    drain_started: float | None = None
    finalize_requested_status: str | None = None
    finalize_drain_started: float | None = None
    last_serial_data_at: float | None = None
    current_condition = "unconfirmed"
    condition_confirmed = False
    status = "interrupted"
    started = time.monotonic()

    event_fields = ["host_utc", "elapsed_s", "kind", "label", "note"]
    det_fields = [
        "host_utc", "elapsed_s", "condition", "condition_confirmed",
        "protocol_valid", "window", "score", "lo", "threshold",
        "alarm", "total_alarm", "consecutive", "verdict", "level_dbfs", "compute_ms",
    ]

    stack = AuditedExitStack()
    try:
        raw_handle = stack.enter_context((run_dir / "serial.raw").open("wb"))
        text_handle = stack.enter_context(
            (run_dir / "serial.log").open("w", encoding="utf-8", newline=""),
        )
        event_handle = stack.enter_context(
            (run_dir / "events.csv").open("w", encoding="utf-8", newline=""),
        )
        det_handle = stack.enter_context(
            (run_dir / "detections.csv").open("w", encoding="utf-8", newline=""),
        )
        quality_handle = stack.enter_context(
            (run_dir / "firmware_quality.csv").open("w", encoding="utf-8", newline=""),
        )
        state_handle = stack.enter_context(
            (run_dir / "firmware_states.csv").open("w", encoding="utf-8", newline=""),
        )
        firmware_event_handle = stack.enter_context(
            (run_dir / "firmware_events.csv").open("w", encoding="utf-8", newline=""),
        )
        parse_error_handle = stack.enter_context(
            (run_dir / "firmware_parse_errors.csv").open(
                "w", encoding="utf-8", newline="",
            ),
        )
    except Exception as exc:
        stack.close()
        failure = stack.close_error or exc
        _best_effort_finalize_setup_failure(run_dir, provenance, metadata, failure)
        raise failure

    with stack:
        event_writer = csv.DictWriter(event_handle, fieldnames=event_fields)
        det_writer = csv.DictWriter(det_handle, fieldnames=det_fields)
        quality_writer = csv.DictWriter(quality_handle, fieldnames=QUALITY_FIELDS)
        state_writer = csv.DictWriter(state_handle, fieldnames=STATE_FIELDS)
        firmware_event_writer = csv.DictWriter(
            firmware_event_handle, fieldnames=FIRMWARE_EVENT_FIELDS,
        )
        parse_error_writer = csv.DictWriter(parse_error_handle, fieldnames=PARSE_ERROR_FIELDS)
        event_writer.writeheader()
        det_writer.writeheader()
        quality_writer.writeheader()
        state_writer.writeheader()
        firmware_event_writer.writeheader()
        parse_error_writer.writeheader()

        ser: Any | None = None
        commands: queue.Queue[str] = queue.Queue()
        command_file = Path(args.command_file).resolve() if args.command_file else None
        command_offset = 0

        try:
            if command_file:
                command_file.parent.mkdir(parents=True, exist_ok=True)
                if command_file.exists() and command_file.stat().st_size:
                    raise RuntimeError(f"command file mora biti nov ili prazan: {command_file}")
                command_file.touch(exist_ok=True)
            ser = serial.Serial(port, args.baud, timeout=1)
            if not args.non_interactive:
                threading.Thread(target=input_worker, args=(commands,), daemon=True).start()
            add_event(
                events, event_writer, event_handle, started=started, kind="session",
                label="start",
                note="sigurnosna postavka potvrđena; operator condition=unconfirmed",
            )
            if not args.no_reset:
                ser.setDTR(False)
                ser.setRTS(True)
                time.sleep(0.15)
                ser.setRTS(False)
                time.sleep(0.3)
                ser.reset_input_buffer()
                add_event(
                    events, event_writer, event_handle, started=started, kind="device",
                    label="reset", note="RTS reset; pocinje WAIT/CAL/DET",
                )

            print(f"artefakti: {run_dir}")
            print("komande: condition <oznaka> [biljeska] | note <tekst> | abort <razlog> | stop")
            if command_file:
                print(f"headless komande se mogu dopisati u: {command_file}")
            print("tokom WAIT i CAL ne mijenjaj normalno stanje ventilatora")

            while True:
                now = time.monotonic()
                if drain_started is not None:
                    drain_elapsed = now - drain_started
                    if terminal_drain_decision(protocol_state, drain_elapsed) == "timeout":
                        add_event(
                            events, event_writer, event_handle, started=started,
                            kind="protocol", label="terminal_drain_timeout",
                            note=f"nije dobijen FLOW_STOPPED za {drain_elapsed:.3f} s",
                        )
                        break
                elif finalize_drain_started is not None:
                    quiet_since = last_serial_data_at or finalize_drain_started
                    if final_buffer_drain_decision(
                        now - finalize_drain_started, now - quiet_since,
                    ) == "complete":
                        status = str(finalize_requested_status)
                        add_event(
                            events, event_writer, event_handle, started=started,
                            kind="session", label="final_buffer_drain_complete",
                            note="buffered UART je procitan prije finalizacije",
                        )
                        break
                if (
                    drain_started is None and finalize_drain_started is None
                    and args.max_seconds and now - started >= args.max_seconds
                ):
                    finalize_requested_status = "completed_time_limit"
                    finalize_drain_started = now
                    last_serial_data_at = now
                    add_event(
                        events, event_writer, event_handle, started=started,
                        kind="session", label="stop", note="istekao --max-seconds",
                    )

                if command_file and finalize_drain_started is None:
                    command_offset, appended = poll_command_file(command_file, command_offset)
                    for command in appended:
                        commands.put(command)

                while finalize_drain_started is None:
                    try:
                        command = commands.get_nowait()
                    except queue.Empty:
                        break
                    if not command:
                        continue
                    verb, _, rest = command.partition(" ")
                    verb = verb.lower()
                    if verb == "stop":
                        finalize_requested_status = (
                            "completed_by_operator" if detections else "aborted_before_detection"
                        )
                        finalize_drain_started = time.monotonic()
                        last_serial_data_at = finalize_drain_started
                        add_event(
                            events, event_writer, event_handle, started=started,
                            kind="session", label="stop", note=rest,
                        )
                        break
                    if verb == "abort":
                        status = "aborted_by_operator"
                        add_event(
                            events, event_writer, event_handle, started=started,
                            kind="session", label="abort", note=rest,
                        )
                        break
                    if verb == "note" and rest:
                        add_event(
                            events, event_writer, event_handle, started=started,
                            kind="note", label="operator", note=rest,
                        )
                    elif verb == "condition" and rest:
                        try:
                            normalized, note = parse_condition_command(rest)
                        except ValueError as exc:
                            print(f"nevalidna condition komanda: {exc}")
                            add_event(
                                events, event_writer, event_handle, started=started,
                                kind="command_error", label="condition", note=str(exc),
                            )
                            continue
                        current_condition = normalized
                        condition_confirmed = True
                        add_event(
                            events, event_writer, event_handle, started=started,
                            kind="condition", label=current_condition, note=note,
                        )
                    else:
                        print("nepoznata komanda; koristi condition, note ili stop")
                if status == "aborted_by_operator":
                    break

                if drain_started is not None:
                    remaining = TERMINAL_DRAIN_TIMEOUT_S - (time.monotonic() - drain_started)
                    ser.timeout = max(0.01, min(0.10, remaining))
                elif finalize_drain_started is not None:
                    ser.timeout = 0.05
                else:
                    ser.timeout = 1
                raw = ser.readline()
                if not raw:
                    continue
                last_serial_data_at = time.monotonic()
                elapsed = round(time.monotonic() - started, 3)
                host_utc = utc_now()
                raw_handle.write(raw)
                raw_handle.flush()
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                text_handle.write(f"{host_utc}\t{elapsed:.3f}\t{line}\n")
                text_handle.flush()
                print(line)

                parsed = parse_serial_line(line)
                invalid_before = protocol_state["invalid_status"]
                if parsed and parsed["kind"] == "QUALITY":
                    protocol_state = transition_firmware_protocol(protocol_state, parsed)
                    telemetry_counts["QUALITY"] += 1
                    row = {
                        "host_utc": host_utc,
                        "elapsed_s": elapsed,
                        **{key: parsed[key] for key in QUALITY_FIELDS if key in parsed},
                    }
                    quality_writer.writerow(row)
                    quality_handle.flush()
                elif parsed and parsed["kind"] == "STATE":
                    protocol_state = transition_firmware_protocol(protocol_state, parsed)
                    telemetry_counts["STATE"] += 1
                    last_firmware_state = str(parsed["to_state"])
                    row = {
                        "host_utc": host_utc,
                        "elapsed_s": elapsed,
                        **{key: parsed[key] for key in STATE_FIELDS if key in parsed},
                    }
                    state_writer.writerow(row)
                    state_handle.flush()
                elif parsed and parsed["kind"] == "EVENT":
                    protocol_state = transition_firmware_protocol(protocol_state, parsed)
                    telemetry_counts["EVENT"] += 1
                    row = {
                        "host_utc": host_utc,
                        "elapsed_s": elapsed,
                        **{key: parsed[key] for key in FIRMWARE_EVENT_FIELDS if key in parsed},
                    }
                    firmware_event_writer.writerow(row)
                    firmware_event_handle.flush()
                elif parsed and parsed["kind"] == "PARSE_ERROR":
                    protocol_state = transition_firmware_protocol(protocol_state, parsed)
                    parse_error_writer.writerow({
                        "host_utc": host_utc,
                        "elapsed_s": elapsed,
                        "record_kind": parsed["record_kind"],
                        "reason": parsed["reason"],
                        "raw_line": parsed["raw_line"],
                    })
                    parse_error_handle.flush()
                elif parsed and parsed["kind"] == "ADAPTTHR":
                    protocol_state = transition_firmware_protocol(protocol_state, parsed)
                elif parsed and parsed["kind"] == "DROPPED":
                    dropped = int(parsed["dropped"])
                    max_dropped = dropped if max_dropped is None else max(max_dropped, dropped)
                elif parsed and parsed["kind"] == "DET":
                    protocol_state = transition_firmware_protocol(protocol_state, parsed)
                    row = {
                        "host_utc": host_utc,
                        "elapsed_s": elapsed,
                        "condition": current_condition,
                        "condition_confirmed": int(condition_confirmed),
                        "protocol_valid": int(protocol_state["invalid_status"] is None),
                        **{key: parsed[key] for key in det_fields if key in parsed},
                    }
                    detections.append(row)
                    det_writer.writerow(row)
                    det_handle.flush()

                if protocol_state["invalid_status"] is not None:
                    status = str(protocol_state["invalid_status"])
                    newly_invalid = invalid_before is None
                    if (
                        newly_invalid and parsed and parsed["kind"] != "PARSE_ERROR"
                        and status in {"invalid_firmware_telemetry", "invalid_missing_telemetry"}
                    ):
                        parse_error_writer.writerow({
                            "host_utc": host_utc,
                            "elapsed_s": elapsed,
                            "record_kind": parsed["kind"],
                            "reason": protocol_state["invalid_reason"],
                            "raw_line": line,
                        })
                        parse_error_handle.flush()
                    if newly_invalid:
                        add_event(
                            events, event_writer, event_handle, started=started,
                            kind="protocol", label=status,
                            note=str(protocol_state["invalid_reason"]),
                        )
                    if protocol_state["drain_required"]:
                        if drain_started is None:
                            drain_started = time.monotonic()
                        decision = terminal_drain_decision(
                            protocol_state, time.monotonic() - drain_started,
                        )
                        if decision == "complete":
                            add_event(
                                events, event_writer, event_handle, started=started,
                                kind="protocol", label="terminal_drain_complete",
                                note="terminal STATE/FLOW_STOPPED sacuvani",
                            )
                            break
                        continue
                    break

                if "KALIBRACIJA:" in line:
                    add_event(
                        events, event_writer, event_handle, started=started,
                        kind="phase", label="calibration",
                        note="fan mora ostati u potvrđeno normalnom stanju",
                    )
                if "DETEKCIJA RADI" in line:
                    add_event(
                        events, event_writer, event_handle, started=started,
                        kind="phase", label="detection",
                        note="firmware DET faza; operator condition i dalje nije potvrđen"
                        if not condition_confirmed else
                        f"firmware DET faza; operator condition={current_condition}",
                    )
        except KeyboardInterrupt:
            status = "interrupted_by_operator"
            add_event(
                events, event_writer, event_handle, started=started,
                kind="session", label="interrupt", note="KeyboardInterrupt",
            )
        except Exception as exc:
            status = "failed"
            add_event(
                events, event_writer, event_handle, started=started,
                kind="session", label="failure", note=f"{type(exc).__name__}: {exc}",
            )
            raise
        finally:
            serial_close_error: Exception | None = None
            if ser is not None:
                try:
                    ser.close()
                except Exception as exc:
                    serial_close_error = exc
                    status = "failed"
            valid_detections = [
                row for row in detections
                if int(row.get("condition_confirmed", 0)) == 1
                and int(row.get("protocol_valid", 0)) == 1
            ]
            protocol_valid_detections = [
                row for row in detections if int(row.get("protocol_valid", 0)) == 1
            ]
            if status.startswith("completed"):
                if (
                    not firmware_protocol_complete(protocol_state)
                ):
                    status = "invalid_missing_telemetry"
                    protocol_state["invalid_status"] = status
                    protocol_state["invalid_reason"] = "session_completed_before_required_protocol"
                elif protocol_state["det_records"] != len(protocol_valid_detections):
                    status = "invalid_firmware_telemetry"
                    protocol_state["invalid_status"] = status
                    protocol_state["invalid_reason"] = "tracker_detection_csv_count_mismatch"
                elif not valid_detections:
                    status = "invalid_no_confirmed_operator_condition"
            metadata["external_wav_sha256_at_end"] = (
                sha256_file(Path(args.wav_path)) if args.wav_path else None
            )
            if serial_close_error is not None:
                provenance["failure"] = (
                    f"{type(serial_close_error).__name__}: {serial_close_error}"
                )
            provenance.update({
                "status": status,
                "finished_utc": utc_now(),
                "metadata": metadata,
                "threshold": protocol_state["adapt_threshold"],
                "det_window_count": len(detections),
                "valid_det_window_count": len(valid_detections),
                "alarm_window_count": sum(int(row["alarm"]) for row in valid_detections),
                "max_dropped": max_dropped,
                "firmware_telemetry_counts": telemetry_counts,
                "last_firmware_state": last_firmware_state,
                "firmware_protocol_state": protocol_state,
            })
            write_json(run_dir / "provenance.json", provenance)
            (run_dir / "SUMMARY.md").write_text(
                make_summary(
                    metadata=metadata, status=status, events=events,
                    detections=detections, max_dropped=max_dropped,
                    protocol_state=protocol_state,
                ),
                encoding="utf-8",
            )
            if serial_close_error is not None:
                raise serial_close_error

    if stack.close_error is not None:
        _best_effort_finalize_setup_failure(
            run_dir, provenance, metadata, stack.close_error,
        )
        raise stack.close_error

    print(f"run zavrsen sa statusom {status}: {run_dir}")
    return 0 if status.startswith("completed") and valid_detections else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight", help="provjeri port i postojeci PSD build")
    preflight.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    preflight.set_defaults(func=record_preflight)

    run = sub.add_parser("run", help="snimi pravi fizicki eksperiment")
    run.add_argument("--port", default="auto")
    run.add_argument("--baud", type=int, default=115200)
    run.add_argument("--fan-id", required=True)
    run.add_argument("--session-id", required=True)
    run.add_argument("--distance-cm", type=float, required=True)
    run.add_argument("--angle-deg", type=float, default=0.0)
    run.add_argument("--room", required=True)
    run.add_argument("--fan-speed-or-voltage", default="nominal")
    run.add_argument("--ambient", default="quiet")
    run.add_argument("--notes", default="")
    run.add_argument("--wav-path", default=None,
                     help="opciona putanja eksternog paralelnog WAV snimka")
    run.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    run.add_argument("--command-file", default=None,
                     help="opciona datoteka; alat cita komande koje se dopisuju tokom runa")
    run.add_argument("--ready", action="store_true",
                     help="eksplicitna potvrda sigurnosti; preskace DA prompt")
    run.add_argument("--no-reset", action="store_true")
    run.add_argument("--non-interactive", action="store_true",
                     help="bez rucnih oznaka; obavezno kombinovati sa --max-seconds")
    run.add_argument("--max-seconds", type=float, default=None)
    run.set_defaults(func=run_experiment)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "non_interactive", False) and not args.max_seconds:
        parser.error("--non-interactive zahtijeva --max-seconds")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
