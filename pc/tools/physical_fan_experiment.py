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
import os
import queue
import re
import statistics
import subprocess
import sys
import threading
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PC_DIR = ROOT / "pc"
if str(PC_DIR) not in sys.path:
    sys.path.insert(0, str(PC_DIR))

from asd.commissioning_policy import (  # noqa: E402
    COMMISSIONING_POLICY_RECORD,
    calibration_acceptance,
)
from asd.guided_test import evaluate_guided25_artifact  # noqa: E402
from asd.runtime_protocol import (  # noqa: E402
    COMMISSIONING as RUNTIME_COMMISSIONING_POLICY,
    PROFILE_PERSISTENCE_ALLOWED,
    RuntimeProtocolError,
    RuntimeRecord,
    advance_runtime_sequence,
    new_runtime_sequence_state,
    parse_runtime_record,
)

DEFAULT_OUT = ROOT / "results" / "physical_fan"
FIRMWARE_DIR = ROOT / "firmware" / "esp32s3_asd"
PROTOCOL_VERSION = "physical-fan-v1.9.0"
LEGACY_READ_PROTOCOL_VERSIONS = frozenset({
    "physical-fan-v1.6.0", "physical-fan-v1.7.0", "physical-fan-v1.8.0",
})
SUPPORTED_READ_PROTOCOL_VERSIONS = frozenset({
    PROTOCOL_VERSION,
    *LEGACY_READ_PROTOCOL_VERSIONS,
})
QUALITY_PROTOCOL_VERSION = "asd-quality-v1.6.0"
LEGACY_PARSE_QUALITY_PROTOCOL_VERSIONS = frozenset({
    "asd-quality-v1.4.0", "asd-quality-v1.5.0",
})
SUPPORTED_PARSE_QUALITY_PROTOCOL_VERSIONS = frozenset({
    QUALITY_PROTOCOL_VERSION, *LEGACY_PARSE_QUALITY_PROTOCOL_VERSIONS,
})
ARTIFACT_CONTRACT_VERSION = "physical-fan-artifacts-v1.9.0"
RESEARCH_PROTOCOL_VERSION = "asd-research-v1.0.0"
RESEARCH_ARTIFACT_SCHEMA_VERSION = "asd-research-artifacts-v1.0.0"
RESEARCH_DIMS = 96
RESEARCH_GROUP_SEGMENTS = (8, 8, 8, 7, 7)
VWORKFLOW_ACCEPTED_RE = re.compile(r"\bVWORKFLOW\s+mode=GUIDED25\s+result=accepted\b")
GUIDED_CAPABILITY_RE = re.compile(
    r"\bFLAGS\s+protocol=asd-quality-v1\.6\.0\b.*\bguided25_available=1\b")
PROFILE_STORE_SCHEMA_VERSION = "asd-profile-v1.0.0"
PSD_MODEL_FINGERPRINT_HEX = (
    "7bfbd3eeca1caca074562f6e01f6b374237dcea5c1d2cc097df079d68d9d15fe"
)
PROFILE_POLICY_VERSION = 1
PROFILE_POLICY_IDS = {
    "profile_policy_id": 0x434D5631,
    "quality_policy_id": 0x51555631,
    "commissioning_policy_id": 0x434D5631,
    "temporal_policy_id": 0x54505632,
    "interference_policy_id": 0x49505633,
}
ARTIFACT_QUALITY_PROTOCOL_PAIRS = {
    "physical-fan-v1.6.0": "asd-quality-v1.3.0",
    "physical-fan-v1.7.0": "asd-quality-v1.4.0",
    "physical-fan-v1.8.0": "asd-quality-v1.5.0",
    PROTOCOL_VERSION: QUALITY_PROTOCOL_VERSION,
}
ARTIFACT_CONTRACT_VERSIONS = {
    "physical-fan-v1.7.0": "physical-fan-artifacts-v1.7.0",
    "physical-fan-v1.8.0": "physical-fan-artifacts-v1.8.0",
    PROTOCOL_VERSION: ARTIFACT_CONTRACT_VERSION,
}
CAL_SUMMARY_DECIMALS = 6
CAL_SUMMARY_HALF_QUANTUM = 0.5 * (10.0 ** -CAL_SUMMARY_DECIMALS)

RELEVANT_FILES = (
    ROOT / "pc" / "tools" / "physical_fan_experiment.py",
    FIRMWARE_DIR / "main" / "app_main.c",
    FIRMWARE_DIR / "main" / "psd_live.c",
    FIRMWARE_DIR / "main" / "audio_quality_state.c",
    FIRMWARE_DIR / "main" / "audio_quality_state.h",
    FIRMWARE_DIR / "main" / "audio_i2s.c",
    FIRMWARE_DIR / "main" / "audio_i2s.h",
    FIRMWARE_DIR / "main" / "asd_calibration_quality.c",
    FIRMWARE_DIR / "main" / "asd_calibration_quality.h",
    FIRMWARE_DIR / "main" / "asd_profile_runtime.c",
    FIRMWARE_DIR / "main" / "asd_profile_runtime.h",
    FIRMWARE_DIR / "main" / "asd_profile_store.c",
    FIRMWARE_DIR / "main" / "asd_profile_store.h",
    FIRMWARE_DIR / "main" / "asd_profile_nvs.c",
    FIRMWARE_DIR / "main" / "asd_profile_nvs.h",
    FIRMWARE_DIR / "main" / "asd_commissioning.c",
    FIRMWARE_DIR / "main" / "asd_commissioning.h",
    FIRMWARE_DIR / "main" / "asd_robust_fit.c",
    FIRMWARE_DIR / "main" / "asd_robust_fit.h",
    FIRMWARE_DIR / "main" / "asd_events.c",
    FIRMWARE_DIR / "main" / "asd_events.h",
    FIRMWARE_DIR / "main" / "asd_operator.c",
    FIRMWARE_DIR / "main" / "asd_operator.h",
    FIRMWARE_DIR / "main" / "asd_temporal.c",
    FIRMWARE_DIR / "main" / "asd_temporal.h",
    FIRMWARE_DIR / "main" / "asd_cmd.c",
    FIRMWARE_DIR / "main" / "asd_cmd.h",
    FIRMWARE_DIR / "main" / "psd_features_c.c",
    FIRMWARE_DIR / "main" / "psd_features_c.h",
    FIRMWARE_DIR / "main" / "psd_model_data.h",
    FIRMWARE_DIR / "main" / "psd_model_nonempty_data.h",
    FIRMWARE_DIR / "main" / "audio_pcm.h",
    ROOT / "pc" / "config" / "asd_quality_policy_v1.json",
    ROOT / "pc" / "config" / "asd_presence_policy_v1.json",
    ROOT / "pc" / "config" / "asd_commissioning_policy_v1.json",
    ROOT / "pc" / "config" / "asd_temporal_policy_v2.json",
    ROOT / "pc" / "config" / "asd_interference_policy_v3.json",
    ROOT / "pc" / "asd" / "commissioning_policy.py",
    FIRMWARE_DIR / "main" / "asd_interference.c",
    FIRMWARE_DIR / "main" / "asd_interference.h",
)

QUALITY_POLICY_RECORD = json.loads(
    (ROOT / "pc" / "config" / "asd_quality_policy_v1.json").read_text(encoding="utf-8")
)
QUALITY_POLICY = QUALITY_POLICY_RECORD["policy"]
PRESENCE_POLICY_RECORD = json.loads(
    (ROOT / "pc" / "config" / "asd_presence_policy_v1.json").read_text(encoding="utf-8")
)
PRESENCE_POLICY = PRESENCE_POLICY_RECORD["policy"]
TEMPORAL_POLICY_RECORD = json.loads(
    (ROOT / "pc" / "config" / "asd_temporal_policy_v2.json").read_text(encoding="utf-8")
)
TEMPORAL_POLICY = TEMPORAL_POLICY_RECORD["policy"]
TEMPORAL_WIRE_PROVENANCE = TEMPORAL_POLICY_RECORD["legacy_wire_provenance"]
INTERFERENCE_POLICY_RECORD = json.loads(
    (ROOT / "pc" / "config" / "asd_interference_policy_v3.json").read_text(
        encoding="utf-8"
    )
)
INTERFERENCE_POLICY = INTERFERENCE_POLICY_RECORD["policy"]
RUNTIME_COMMISSIONING_RECORD = json.loads(
    (ROOT / "pc" / "config" / "asd_commissioning_runtime_v1.json").read_text(
        encoding="utf-8"
    )
)
# Samo za citanje istorijskih THRFIT tragova iz kratko probane i odbacene
# robustne verzije. Aktivna politika je frozen CAL + empirical p99 iz configa.
ROBUST_THRESHOLD_POLICY = {
    "center_trim_fraction_each_tail": 0.1,
    "hampel_sigma_multiplier": 3.0,
    "hampel_normal_sigma": 1.4826,
}
LEGACY_TEMPORAL_POLICY_RECORD = json.loads(
    (ROOT / "pc" / "config" / "asd_temporal_policy_v1.json").read_text(encoding="utf-8")
)
LEGACY_TEMPORAL_POLICY = LEGACY_TEMPORAL_POLICY_RECORD["policy"]

ASCII_RECORD_RE = re.compile(
    r"\b(?P<kind>QUALITY|STATE|EVENT|PRESENCE|TEMPORAL|INTERFERENCE|THRFIT|SESSION|BUTTON|PROFILESTORE)"
    r"(?:\s+(?P<body>.*))?$"
)
KEY_VALUE_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\S+)")

QUALITY_FIELDS = [
    "host_utc", "elapsed_s", "firmware_session_index", "protocol", "phase", "index", "total",
    "result", "metrics_valid", "feature_valid", "samples", "expected", "rms_dbfs", "dc", "peak",
    "clipped", "zeros", "stuck", "dropped_delta", "tonalness_proxy",
    "tonalness_valid", "tonal_gate", "loo_mean", "loo_sd", "loo_cv", "loo_range", "loo_gate",
]
STATE_FIELDS = [
    "host_utc", "elapsed_s", "firmware_session_index", "protocol", "from_state", "to_state", "reason",
]
FIRMWARE_EVENT_FIELDS = [
    "host_utc", "elapsed_s", "firmware_session_index", "protocol", "type", "state", "phase", "reason",
    "event", "capability", "level",
]
OPERATOR_FIELDS = [
    "host_utc", "elapsed_s", "firmware_session_index", "protocol", "kind", "action", "source", "reason",
    "discards_calibration", "event", "mode", "command", "discards",
]
PARSE_ERROR_FIELDS = [
    "host_utc", "elapsed_s", "firmware_session_index",
    "record_kind", "reason", "raw_line",
]

# Rjecnik Faze 2. Firmware event/capability/level moraju doci iz zakljucane
# taksonomije; nepoznat token je greska protokola, ne nepoznato polje.
FIRMWARE_EVENTS = {
    "NONE", "FAN_STOPPED", "SPEED_CHANGED", "MECHANICAL_ANOMALY",
    "AMBIENT_NOISE", "SENSOR_FAULT", "UNKNOWN_CHANGE",
}
# Dogadjaji koje uredjaj SMIJE emitovati danas. Ostali su rezervisani i njihova
# pojava u toku znaci da je kapabilitetni gate probijen.
EMITTABLE_EVENTS = {"NONE", "FAN_STOPPED", "SENSOR_FAULT", "UNKNOWN_CHANGE"}
FIRMWARE_CAPABILITIES = {
    "AVAILABLE", "NEEDS_F0", "NEEDS_DUAL_CHANNEL", "NEEDS_TRANSIENT",
}
FIRMWARE_LEVELS = {
    "SENSOR_HEALTH", "MACHINE_PRESENCE", "OPERATING_REGIME", "DEVIATION",
}
SESSION_ACTIONS = {"STARTED", "ENDED", "ABORTED"}
SESSION_SOURCES = {"BUTTON", "FIRMWARE"}
BUTTON_EVENTS = {"NONE", "SHORT", "LONG"}
BUTTON_MODES = {"IDLE", "LEARNING", "READY", "ALARM", "FAULT"}
BUTTON_COMMANDS = {"NONE", "START_LEARNING", "ABORT"}

EXPECTED_QUALITY_COUNTS = {"WAIT": 60, "CAL": 10, "CAL_SUMMARY": 1}
WAIT_EXPECTED_SAMPLES = 4096
CLIP_EXPECTED_SAMPLES = 39 * 4096
N_CONSECUTIVE_ALARM = 3
COMMISSION_ENTER_QUANTILE = 0.99
SCORE_NEGATIVE_TOL = 1.0e-3
PCM_LEVEL_REL_TOL = 1.0e-3
PCM_LEVEL_ABS_TOL = 1.0
TERMINAL_DRAIN_TIMEOUT_S = 2.5
FINAL_BUFFER_DRAIN_TIMEOUT_S = 0.50
FINAL_BUFFER_QUIET_S = 0.10
# a 7507-byte research packet needs about 652 ms at 115200 baud.
# allow bounded completion across inter-line gaps up to 141 ms.
FINAL_BUFFER_OPEN_PACKAGE_TIMEOUT_S = 3.0
TERMINAL_FIRMWARE_STATES = {
    "SENSOR_ERROR", "CALIBRATION_REJECTED", "RECALIBRATION_REQUIRED",
}
FIRMWARE_STATES = TERMINAL_FIRMWARE_STATES | {
    "NO_MACHINE", "CALIBRATED_NORMAL", "ANOMALY",
    # held observations preserve an active alarm; they do not classify noise.
    "OBSERVATION_HOLD",
}
# these events occur within a state, without a paired transition.
UNPAIRED_EVENT_STATES = {
    "OBSERVATION_HOLD_WARNING": {"OBSERVATION_HOLD", "ANOMALY"},
    "ANOMALY_SUSTAINED": {"ANOMALY"},
}
QUALITY_REJECT_RESULTS = {
    "SHORT_READ", "NONFINITE", "STUCK_SIGNAL", "LOW_LEVEL_OBSERVATION",
    "INSUFFICIENT_LEVEL", "CLIPPING", "DROPPED_SAMPLES", "INVALID_ARGUMENT",
    "AUDIO_TIMEOUT", "AUDIO_READ_ERROR",
}
# presence and calibration stops are distinct from invalid audio.
PRESENCE_STOP_REASONS = {"FAN_STOPPED", "PRESENCE_LOST"}
CALIBRATION_STOP_REASONS = {"UNSTABLE_CALIBRATION", "VERIFY_NORMAL_REJECT"}
FLOW_STOP_REASONS = (
    QUALITY_REJECT_RESULTS | PRESENCE_STOP_REASONS | CALIBRATION_STOP_REASONS
)
RESEARCH_RECORD_RE = re.compile(
    r"\b(?P<kind>FEATURE96|SUBSEG96)(?:\s+(?P<body>.*))?$"
)

DET_RE = re.compile(
    r"^DET\s+(?P<window>\d+)\s+"
    r"score=(?P<score>\S+)\s+lo=(?P<lo>\S+)\s+"
    r"hi=(?P<threshold>\S+)\s+led=(?P<led>\S+)\s+"
    r"anom=(?P<alarm>\S+)\s+total_anom=(?P<total_alarm>\S+)\s+"
    # `hold=` postoji od q1.6.0; stariji runovi se i dalje citaju bez njega.
    r"(?:hold=(?P<hold>[01])\s+)?"
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


def fnv1a_bytes(data: bytes) -> int:
    """FNV-1a 32, identicno framed PCM/feature firmware obrascu."""
    value = 0x811C9DC5
    for byte in data:
        value = ((value ^ byte) * 0x01000193) & 0xFFFFFFFF
    return value


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


def build_has_research_telemetry() -> bool:
    ninja = FIRMWARE_DIR / "build" / "build.ninja"
    if not ninja.is_file():
        return False
    return "-DASD_RESEARCH_TELEMETRY" in ninja.read_text(
        encoding="utf-8", errors="replace",
    )


def build_has_nonempty_bands() -> bool:
    """Eksperimentalni front-end; takav run se ne mijesa sa starim buildom."""
    ninja = FIRMWARE_DIR / "build" / "build.ninja"
    if not ninja.is_file():
        return False
    return "-DASD_PSD_NONEMPTY_BANDS" in ninja.read_text(
        encoding="utf-8", errors="replace",
    )


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
        "artifact_contract_version": ARTIFACT_CONTRACT_VERSION,
        "research_protocol_version": RESEARCH_PROTOCOL_VERSION,
        "research_artifact_schema_version": RESEARCH_ARTIFACT_SCHEMA_VERSION,
        "artifact_contract": {
            "scope": "run-with-firmware-sessions",
            "session_key": "firmware_session_index",
            "detection_keys": ["firmware_session_index", "window", "run_det_index"],
        },
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
            "research_telemetry_build_flag_confirmed": build_has_research_telemetry(),
            "psd_nonempty_bands_build_flag_confirmed": build_has_nonempty_bands(),
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


def _vocabulary_error(kind: str, parsed: dict[str, Any]) -> str | None:
    """Tokeni iz zakljucanih rjecnika Faze 2 i operaterskog toka.

    Nepoznat token nije nepoznato polje nego probijen ugovor: taksonomija je
    zakljucana upravo zato da se serijski ugovor ne mijenja u hodu.
    """
    if kind == "EVENT":
        if parsed["event"] not in FIRMWARE_EVENTS:
            return f"unknown_event_token:{parsed['event']}"
        if parsed["capability"] not in FIRMWARE_CAPABILITIES:
            return f"unknown_capability_token:{parsed['capability']}"
        if parsed["level"] not in FIRMWARE_LEVELS:
            return f"unknown_level_token:{parsed['level']}"
        # Kapabilitetni gate: rezervisan dogadjaj se ne smije pojaviti u toku,
        # niti smije stici oznacen kao AVAILABLE.
        if parsed["event"] not in EMITTABLE_EVENTS:
            return f"reserved_event_emitted:{parsed['event']}"
        if parsed["capability"] != "AVAILABLE":
            return f"emitted_event_not_available:{parsed['event']}"
    elif kind == "SESSION":
        if parsed["action"] not in SESSION_ACTIONS:
            return f"unknown_session_action:{parsed['action']}"
        if parsed["source"] not in SESSION_SOURCES:
            return f"unknown_session_source:{parsed['source']}"
        if parsed["discards_calibration"] not in (0, 1):
            return "invalid_session_discards_calibration"
    elif kind == "BUTTON":
        if parsed["event"] not in BUTTON_EVENTS:
            return f"unknown_button_event:{parsed['event']}"
        if parsed["mode"] not in BUTTON_MODES:
            return f"unknown_button_mode:{parsed['mode']}"
        if parsed["command"] not in BUTTON_COMMANDS:
            return f"unknown_button_command:{parsed['command']}"
        if parsed["discards"] not in (0, 1):
            return "invalid_button_discards"
        # Pravilo koje firmware nosi u kodu, provjereno i sa host strane:
        # kratak pritisak nikad ne odbacuje naucen centar.
        if parsed["event"] == "SHORT" and parsed["discards"] == 1:
            return "short_press_discarded_calibration"
    elif kind == "TEMPORAL":
        live_v2 = parsed["protocol"] == QUALITY_PROTOCOL_VERSION
        policy_record = (
            TEMPORAL_POLICY_RECORD if live_v2 else LEGACY_TEMPORAL_POLICY_RECORD
        )
        policy = TEMPORAL_POLICY if live_v2 else LEGACY_TEMPORAL_POLICY
        if parsed["policy"] != policy_record["schema_version"]:
            return f"temporal_policy_schema_mismatch:{parsed['policy']}"
        if live_v2:
            for field in (
                "ewma_alpha", "enter_scale", "exit_scale", "fast_scale",
                "threshold_enter", "threshold_exit",
            ):
                if not math.isfinite(float(parsed[field])):
                    return f"nonfinite_field:TEMPORAL:{field}"
            if parsed["threshold_mode"] != "absolute_profile":
                return f"temporal_threshold_mode_mismatch:{parsed['threshold_mode']}"
            for field, expected in (
                ("min_consecutive", policy["min_consecutive"]),
                ("ewma_alpha", policy["ewma_alpha"]),
                ("fast_scale", policy["fast_scale"]),
                ("enter_scale", TEMPORAL_WIRE_PROVENANCE["enter_scale"]),
                ("exit_scale", TEMPORAL_WIRE_PROVENANCE["exit_scale"]),
            ):
                if not math.isclose(float(parsed[field]), float(expected), abs_tol=1e-6):
                    return f"temporal_policy_off_config:{field}"
            if not (
                0.0 < parsed["threshold_exit"] < parsed["threshold_enter"]
            ):
                return "temporal_invalid_absolute_thresholds"
        else:
            for field, expected in (
                ("min_consecutive", policy["min_consecutive"]),
                ("ewma_alpha", policy["ewma_alpha"]),
                ("enter_scale", policy["enter_scale"]),
                ("exit_scale", policy["exit_scale"]),
                ("fast_scale", policy["fast_scale"]),
            ):
                if not math.isclose(float(parsed[field]), float(expected), abs_tol=1e-6):
                    return f"temporal_policy_off_config:{field}"
            if parsed["exit_scale"] > parsed["enter_scale"]:
                return "temporal_exit_above_enter"
    elif kind == "PRESENCE":
        for field in ("level_mean_dbfs", "margin_db", "gate_dbfs"):
            if not math.isfinite(parsed[field]):
                return f"nonfinite_field:PRESENCE:{field}"
        if parsed["margin_db"] <= 0.0:
            return "nonpositive_presence_margin"
        if parsed["min_consecutive"] < 1:
            return "invalid_presence_min_consecutive"
        expected_gate = parsed["level_mean_dbfs"] - parsed["margin_db"]
        if not math.isclose(parsed["gate_dbfs"], expected_gate, abs_tol=1e-4):
            return "presence_gate_inconsistent"
    elif kind == "INTERFERENCE":
        policy = INTERFERENCE_POLICY
        if parsed["policy"] != INTERFERENCE_POLICY_RECORD["schema_version"]:
            return "interference_policy_schema_mismatch"
        if parsed["source"] != "CAL_NORMAL_ONLY":
            return "interference_non_normal_source"
        if parsed["normal_windows"] != int(policy["calibration_min_windows"]):
            return "interference_normal_window_count_mismatch"
        if parsed["use_tonalness_delta"] != int(bool(policy["use_tonalness_delta"])):
            return "interference_tonalness_policy_mismatch"
        if parsed["long_hold_windows"] != int(policy["long_hold_windows"]):
            return "interference_long_hold_policy_mismatch"
        for field in ("normal_max", "multiplier", "threshold"):
            if not math.isfinite(float(parsed[field])):
                return f"nonfinite_field:INTERFERENCE:{field}"
        if parsed["normal_max"] <= 0.0:
            return "interference_nonpositive_normal_max"
        if not math.isclose(
            parsed["multiplier"], float(policy["normal_max_multiplier"]),
            rel_tol=1e-6, abs_tol=1e-6,
        ):
            return "interference_multiplier_off_policy"
        if not math.isclose(
            parsed["threshold"], parsed["normal_max"] * parsed["multiplier"],
            rel_tol=1e-6, abs_tol=1e-6,
        ):
            return "interference_threshold_not_normal_only_rule"
    elif kind == "THRFIT":
        if parsed["method"] != "trimmed-center-hampel-v1":
            return "threshold_fit_method_mismatch"
        if parsed["source"] != "COMMISSION_DERIVE_NORMAL_ONLY":
            return "threshold_fit_non_normal_source"
        for field in (
            "center_trim", "median", "mad", "robust_sigma",
            "sigma_multiplier", "p99_ceiling", "threshold",
        ):
            if not math.isfinite(float(parsed[field])):
                return f"nonfinite_field:THRFIT:{field}"
        if parsed["n"] < 3 or not 0 <= parsed["capped_high"] <= parsed["n"]:
            return "threshold_fit_invalid_counts"
        expected_trim = float(
            ROBUST_THRESHOLD_POLICY["center_trim_fraction_each_tail"]
        )
        expected_multiplier = float(
            ROBUST_THRESHOLD_POLICY["hampel_sigma_multiplier"]
        )
        expected_normal_sigma = float(
            ROBUST_THRESHOLD_POLICY["hampel_normal_sigma"]
        )
        if not math.isclose(parsed["center_trim"], expected_trim, abs_tol=1e-6):
            return "threshold_fit_trim_off_policy"
        if not math.isclose(
            parsed["sigma_multiplier"], expected_multiplier, abs_tol=1e-6,
        ):
            return "threshold_fit_multiplier_off_policy"
        if not math.isclose(
            parsed["robust_sigma"], expected_normal_sigma * parsed["mad"],
            rel_tol=1e-5, abs_tol=1e-5,
        ):
            return "threshold_fit_sigma_inconsistent"
        expected_threshold = min(
            parsed["p99_ceiling"],
            parsed["median"] + parsed["sigma_multiplier"] * parsed["robust_sigma"],
        )
        if not parsed["threshold"] > 0.0 or not math.isclose(
            parsed["threshold"], expected_threshold, rel_tol=1e-5, abs_tol=1e-5,
        ):
            return "threshold_fit_threshold_inconsistent"
    elif kind == "PROFILESTORE":
        if parsed["schema"] != PROFILE_STORE_SCHEMA_VERSION:
            return "profile_store_schema_mismatch"
        if parsed["result"] != "LOADED":
            return "profile_store_result_not_loaded"
        if parsed["fingerprint"].lower() != PSD_MODEL_FINGERPRINT_HEX:
            return "profile_store_fingerprint_mismatch"
        if parsed["generation"] < 1:
            return "profile_store_invalid_generation"
        for field in (
            "threshold_enter", "threshold_exit", "derive_mean", "derive_sd",
            "verify_alarm_time_percent",
        ):
            if not math.isfinite(float(parsed[field])):
                return f"nonfinite_field:PROFILESTORE:{field}"
        if not (0.0 < parsed["threshold_exit"] < parsed["threshold_enter"]):
            return "profile_store_invalid_thresholds"
        if any(parsed[field] < 1 for field in (
            "center_windows", "derive_windows", "verify_windows",
        )):
            return "profile_store_invalid_counts"
        if parsed["profile_policy_version"] != PROFILE_POLICY_VERSION:
            return "profile_store_policy_version_mismatch"
        for field, expected in PROFILE_POLICY_IDS.items():
            if parsed[field] != expected:
                return f"profile_store_policy_id_mismatch:{field}"
        if parsed["derive_mean"] < 0.0 or parsed["derive_sd"] < 0.0:
            return "profile_store_invalid_summary"
        if not 0.0 <= parsed["verify_alarm_time_percent"] <= 100.0:
            return "profile_store_invalid_verify_percent"
        if parsed["verify_alarm_windows"] > parsed["verify_windows"]:
            return "profile_store_alarm_windows_exceed_verify"
    return None


def parse_serial_line(line: str) -> dict[str, Any] | None:
    """Parse one firmware status line without depending on ESP-IDF log prefix."""
    stripped = line.strip()
    if stripped.startswith(("COMMISSION ", "PROFILE ")):
        kind = stripped.partition(" ")[0]
        try:
            runtime = parse_runtime_record(stripped)
        except RuntimeProtocolError as exc:
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": f"runtime_protocol:{exc}", "raw_line": line,
            }
        assert runtime is not None
        return {"kind": runtime.kind, **runtime.fields}

    research_record = RESEARCH_RECORD_RE.search(line)
    if research_record:
        kind = research_record.group("kind")
        values, parse_error = _parse_strict_key_values(
            kind, research_record.group("body") or "", line,
        )
        if parse_error:
            return parse_error
        assert values is not None
        common = {"protocol", "session", "phase", "window", "dims", "fnv1a", "values"}
        required = (
            common
            | {"window_start_ms", "window_end_ms", "score", "level_dbfs",
               "quality", "tonalness_proxy"}
            if kind == "FEATURE96"
            else common | {"group", "segments"}
        )
        missing = sorted(required - set(values))
        extras = sorted(set(values) - required)
        if missing or extras:
            reason = f"{kind}_schema"
            if missing:
                reason += ":missing=" + ",".join(missing)
            if extras:
                reason += ":extra=" + ",".join(extras)
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": reason, "raw_line": line,
            }
        try:
            parsed_research: dict[str, Any] = {
                "kind": kind,
                "protocol": values["protocol"],
                "session": int(values["session"]),
                "phase": values["phase"],
                "window": int(values["window"]),
                "dims": int(values["dims"]),
                "fnv1a": values["fnv1a"].lower(),
            }
            if kind == "FEATURE96":
                parsed_research.update({
                    "window_start_ms": int(values["window_start_ms"]),
                    "window_end_ms": int(values["window_end_ms"]),
                    "score": float(values["score"]),
                    "level_dbfs": float(values["level_dbfs"]),
                    "quality": values["quality"],
                    "tonalness_proxy": float(values["tonalness_proxy"]),
                })
            else:
                parsed_research.update({
                    "group": int(values["group"]),
                    "segments": int(values["segments"]),
                })
            vector = np.asarray(
                [float(item) for item in values["values"].split(",")],
                dtype="<f4",
            )
        except (ValueError, OverflowError):
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": "malformed_numeric_field", "raw_line": line,
            }
        if parsed_research["protocol"] != RESEARCH_PROTOCOL_VERSION:
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": "invalid_research_protocol_mismatch", "raw_line": line,
            }
        if (
            parsed_research["session"] < 1
            or parsed_research["window"] < 1
            or parsed_research["phase"] not in {"CAL", "DET"}
            or parsed_research["dims"] != RESEARCH_DIMS
            or vector.shape != (RESEARCH_DIMS,)
            or not np.isfinite(vector).all()
            or not re.fullmatch(r"[0-9a-f]{8}", parsed_research["fnv1a"])
        ):
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": "invalid_research_vector_contract", "raw_line": line,
            }
        if kind == "FEATURE96":
            if (
                parsed_research["window_end_ms"] < parsed_research["window_start_ms"]
                or parsed_research["quality"] != "OK"
                or not all(math.isfinite(parsed_research[field]) for field in (
                    "score", "level_dbfs", "tonalness_proxy",
                ))
            ):
                return {
                    "kind": "PARSE_ERROR", "record_kind": kind,
                    "reason": "invalid_research_metadata", "raw_line": line,
                }
        else:
            group = parsed_research["group"]
            if (
                group not in range(1, len(RESEARCH_GROUP_SEGMENTS) + 1)
                or parsed_research["segments"] != RESEARCH_GROUP_SEGMENTS[group - 1]
            ):
                return {
                    "kind": "PARSE_ERROR", "record_kind": kind,
                    "reason": "invalid_research_group_contract", "raw_line": line,
                }
        got_hash = fnv1a_bytes(vector.tobytes(order="C"))
        if parsed_research["fnv1a"] != f"{got_hash:08x}":
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": "research_checksum_mismatch", "raw_line": line,
            }
        parsed_research["values"] = vector
        return parsed_research

    stripped = line.strip()
    if stripped.startswith("FEATURE96") or stripped.startswith("SUBSEG96"):
        kind = stripped.split(maxsplit=1)[0]
        return {
            "kind": "PARSE_ERROR", "record_kind": kind,
            "reason": "malformed_or_truncated_research_record", "raw_line": line,
        }

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
        if protocol not in SUPPORTED_PARSE_QUALITY_PROTOCOL_VERSIONS:
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": "invalid_protocol_mismatch", "raw_line": line,
            }
        integer_fields = {
            "index", "total", "samples", "expected", "peak", "clipped",
            "zeros", "stuck", "dropped_delta", "metrics_valid", "feature_valid",
            "tonalness_valid", "min_consecutive", "discards_calibration",
            "discards", "generation", "center_windows", "derive_windows",
            "verify_windows", "profile_policy_version", "profile_policy_id",
            "quality_policy_id", "commissioning_policy_id",
            "temporal_policy_id", "interference_policy_id",
            "verify_alarm_windows", "verify_episodes", "verify_chatter",
            "normal_windows", "use_tonalness_delta", "long_hold_windows",
            "n", "capped_high",
        }
        float_fields = {
            "rms_dbfs", "dc", "tonalness_proxy", "loo_mean", "loo_sd",
            "loo_cv", "loo_range", "level_mean_dbfs", "margin_db", "gate_dbfs",
            "ewma_alpha", "enter_scale", "exit_scale", "fast_scale",
            "threshold_enter", "threshold_exit", "derive_mean", "derive_sd",
            "verify_alarm_time_percent",
            "normal_max", "multiplier", "threshold",
            "center_trim", "median", "mad", "robust_sigma",
            "sigma_multiplier", "p99_ceiling",
        }
        parsed: dict[str, Any] = {"kind": kind, "protocol": values.pop("protocol")}
        try:
            for key, value in values.items():
                if key in integer_fields:
                    parsed[key] = int(value)
                elif key in float_fields:
                    parsed[key] = float(value)
                elif key == "crc32":
                    if not re.fullmatch(r"[0-9A-Fa-f]{8}", value):
                        raise ValueError("crc32")
                    parsed[key] = int(value, 16)
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
        elif kind == "PRESENCE":
            required = {"protocol", "level_mean_dbfs", "margin_db", "gate_dbfs",
                        "min_consecutive"}
        elif kind == "TEMPORAL":
            required = {
                "protocol", "policy", "min_consecutive", "ewma_alpha",
                "enter_scale", "exit_scale", "fast_scale",
            }
            if parsed["protocol"] == QUALITY_PROTOCOL_VERSION:
                required |= {
                    "threshold_mode", "threshold_enter", "threshold_exit",
                }
        elif kind == "INTERFERENCE":
            required = {
                "protocol", "policy", "source", "normal_windows",
                "normal_max", "multiplier", "threshold",
                "use_tonalness_delta", "long_hold_windows",
            }
        elif kind == "THRFIT":
            required = {
                "protocol", "method", "source", "n", "center_trim",
                "median", "mad", "robust_sigma", "sigma_multiplier",
                "p99_ceiling", "threshold", "capped_high",
            }
        elif kind == "SESSION":
            required = {"protocol", "action", "source", "reason",
                        "discards_calibration"}
        elif kind == "BUTTON":
            required = {"protocol", "event", "mode", "command", "discards"}
        elif kind == "PROFILESTORE":
            required = {
                "protocol", "schema", "result", "generation", "fingerprint",
                "crc32", "threshold_enter", "threshold_exit", "center_windows",
                "derive_windows", "verify_windows", "profile_policy_version",
                "profile_policy_id", "quality_policy_id",
                "commissioning_policy_id", "temporal_policy_id",
                "interference_policy_id", "derive_mean", "derive_sd",
                "verify_alarm_time_percent", "verify_alarm_windows",
                "verify_episodes", "verify_chatter",
            }
        else:
            required = {"protocol", "type", "state", "phase", "reason",
                        "event", "capability", "level"}
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
        vocabulary_error = _vocabulary_error(kind, parsed)
        if vocabulary_error:
            return {
                "kind": "PARSE_ERROR", "record_kind": kind,
                "reason": vocabulary_error, "raw_line": line,
            }
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
                # Stariji runovi (do q1.5.0) nemaju `hold=`; tamo je 0 tacno,
                # jer je kapija pouzdanosti tada bila iskljucena.
                "hold": int(row["hold"] or 0),
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


def new_research_telemetry_state(*, required: bool) -> dict[str, Any]:
    """Zaseban research scope; nikad ne mijenja core firmware protocol state."""
    return {
        "required": bool(required),
        "records_seen": 0,
        "expected": {},
        "packages": {},
        "errors": [],
    }


def _research_key(session: int, phase: str, window: int) -> tuple[int, str, int]:
    return int(session), str(phase), int(window)


def research_expect_quality(
    state: dict[str, Any], record: dict[str, Any], *, session: int,
) -> None:
    if (
        record.get("kind") != "QUALITY"
        or record.get("phase") not in {"CAL", "DET"}
        or record.get("result") != "OK"
        or int(record.get("feature_valid", 0)) != 1
    ):
        return
    key = _research_key(session, str(record["phase"]), int(record["index"]))
    if key in state["expected"]:
        state["errors"].append(f"duplicate_expected_quality:{key}")
        return
    state["expected"][key] = {
        "level_dbfs": float(record["rms_dbfs"]),
        "tonalness_proxy": float(record["tonalness_proxy"]),
        "score": None,
    }


def research_note_det(
    state: dict[str, Any], record: dict[str, Any], *, session: int,
) -> None:
    key = _research_key(session, "DET", int(record["window"]))
    expected = state["expected"].get(key)
    if expected is None:
        state["errors"].append(f"DET_without_expected_research_quality:{key}")
        return
    expected["score"] = float(record["score"])


def research_consume_record(
    state: dict[str, Any], record: dict[str, Any], *, active_session: int,
    pending_det_quality: int | None = None,
) -> None:
    kind = str(record.get("kind"))
    if kind == "PARSE_ERROR":
        state["errors"].append(
            f"{record.get('record_kind')}:{record.get('reason')}"
        )
        return
    state["records_seen"] += 1
    if pending_det_quality is not None:
        state["errors"].append(
            f"research_record_between_DET_quality_and_DET:{kind}:window={pending_det_quality}"
        )
    key = _research_key(record["session"], record["phase"], record["window"])
    if record["session"] != active_session:
        state["errors"].append(
            f"research_session_mismatch:wire={record['session']}:active={active_session}"
        )
    if key not in state["expected"]:
        state["errors"].append(f"unexpected_research_window:{key}")
    package = state["packages"].setdefault(key, {"feature": None, "groups": {}})
    if kind == "FEATURE96":
        if package["feature"] is not None:
            state["errors"].append(f"duplicate_FEATURE96:{key}")
        else:
            package["feature"] = record
    elif kind == "SUBSEG96":
        group = int(record["group"])
        if group in package["groups"]:
            state["errors"].append(f"duplicate_SUBSEG96:{key}:group={group}")
        else:
            package["groups"][group] = record


def _atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as handle:
            np.savez_compressed(handle, **arrays)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_research_artifact(
    run_dir: Path, state: dict[str, Any], *, metadata: dict[str, Any],
) -> dict[str, Any]:
    """Zakljuci strict paket i objavi NPZ prije hash manifesta."""
    errors = list(state["errors"])
    expected_keys = set(state["expected"])
    package_keys = set(state["packages"])
    for key in sorted(expected_keys - package_keys):
        errors.append(f"missing_research_package:{key}")
    for key in sorted(package_keys - expected_keys):
        errors.append(f"unexpected_research_package:{key}")

    complete: list[tuple[tuple[int, str, int], dict[str, Any]]] = []
    previous_end: int | None = None
    for key in sorted(expected_keys, key=lambda item: (item[0], item[1] == "DET", item[2])):
        package = state["packages"].get(key)
        if package is None:
            continue
        feature = package["feature"]
        groups = package["groups"]
        if feature is None:
            errors.append(f"missing_FEATURE96:{key}")
        missing_groups = sorted(set(range(1, 6)) - set(groups))
        if missing_groups:
            errors.append(f"missing_SUBSEG96:{key}:groups={missing_groups}")
        if feature is None or missing_groups:
            continue
        expected = state["expected"][key]
        if not math.isclose(
            float(feature["level_dbfs"]), float(expected["level_dbfs"]), abs_tol=6e-4,
        ):
            errors.append(f"research_level_mismatch:{key}")
        if not math.isclose(
            float(feature["tonalness_proxy"]),
            float(expected["tonalness_proxy"]), abs_tol=2e-6,
        ):
            errors.append(f"research_tonalness_mismatch:{key}")
        if key[1] == "CAL":
            if feature["score"] != 0.0:
                errors.append(f"research_CAL_score_not_zero:{key}")
        elif expected["score"] is None:
            errors.append(f"missing_DET_for_research_feature:{key}")
        elif not math.isclose(
            float(feature["score"]), float(expected["score"]), rel_tol=1e-6, abs_tol=1e-6,
        ):
            errors.append(f"research_score_mismatch:{key}")
        if previous_end is not None and feature["window_start_ms"] < previous_end:
            errors.append(f"nonmonotonic_research_window_time:{key}")
        previous_end = int(feature["window_end_ms"])
        complete.append((key, package))

    enabled = state["records_seen"] > 0
    if state["required"] and not enabled:
        errors.append("required_research_telemetry_missing")
    artifact_valid: bool | None = not errors if (enabled or state["required"]) else None
    npz_path = run_dir / "window_features.npz"
    if complete:
        arrays = {
            "firmware_session_index": np.asarray([key[0] for key, _ in complete], dtype=np.int32),
            "phase": np.asarray([key[1] for key, _ in complete], dtype="U3"),
            "window": np.asarray([key[2] for key, _ in complete], dtype=np.int32),
            "window_start_ms": np.asarray([
                package["feature"]["window_start_ms"] for _, package in complete
            ], dtype=np.uint64),
            "window_end_ms": np.asarray([
                package["feature"]["window_end_ms"] for _, package in complete
            ], dtype=np.uint64),
            "score": np.asarray([
                package["feature"]["score"] for _, package in complete
            ], dtype=np.float32),
            "level_dbfs": np.asarray([
                package["feature"]["level_dbfs"] for _, package in complete
            ], dtype=np.float32),
            "tonalness_proxy": np.asarray([
                package["feature"]["tonalness_proxy"] for _, package in complete
            ], dtype=np.float32),
            "feature96": np.stack([
                package["feature"]["values"] for _, package in complete
            ]).astype(np.float32, copy=False),
            "subseg96": np.stack([
                np.stack([package["groups"][group]["values"] for group in range(1, 6)])
                for _, package in complete
            ]).astype(np.float32, copy=False),
            "subseg_welch_segments": np.tile(
                np.asarray(RESEARCH_GROUP_SEGMENTS, dtype=np.int32), (len(complete), 1),
            ),
        }
        _atomic_npz(npz_path, arrays)
        array_contract = {
            name: {"shape": list(value.shape), "dtype": str(value.dtype)}
            for name, value in arrays.items()
        }
    else:
        array_contract = {}

    external_wav = metadata.get("external_wav")
    manifest = {
        "schema_version": RESEARCH_ARTIFACT_SCHEMA_VERSION,
        "wire_protocol_version": RESEARCH_PROTOCOL_VERSION,
        "required": bool(state["required"]),
        "enabled": enabled,
        "artifact_valid": artifact_valid,
        "gate_passed": artifact_valid is not False,
        "expected_window_count": len(expected_keys),
        "complete_window_count": len(complete),
        "feature_record_count": sum(
            package["feature"] is not None for package in state["packages"].values()
        ),
        "subsegment_record_count": sum(
            len(package["groups"]) for package in state["packages"].values()
        ),
        "errors": errors,
        "npz": (
            {"path": npz_path.name, "sha256": sha256_file(npz_path), "arrays": array_contract}
            if complete else None
        ),
        "external_wav": (
            {
                "path": external_wav,
                "relationship": "linked_external_file_not_recorded_by_host",
                "sha256_at_start": metadata.get("external_wav_sha256_at_start"),
                "sha256_at_end": metadata.get("external_wav_sha256_at_end"),
            }
            if external_wav else None
        ),
        "pcm_per_det": False,
    }
    _atomic_json(run_dir / "window_features.manifest.json", manifest)
    return manifest


def new_session_protocol_state(*, firmware_session_index: int = 0) -> dict[str, Any]:
    """Fresh session scope; boot/run evidence deliberately lives elsewhere."""
    return {
        "firmware_session_index": firmware_session_index,
        "quality_counts": {"WAIT": 0, "CAL": 0, "CAL_SUMMARY": 0, "DET": 0},
        "wait_ok_count": 0,
        "cal_summary": None,
        "adapt_seen": False,
        "adapt_threshold": None,
        "profile_store_seen": False,
        "profile_store_valid": False,
        "profile_store_generation": None,
        "profile_store_crc32": None,
        "profile_store_threshold_enter": None,
        "profile_store_threshold_exit": None,
        "profile_store_center_windows": None,
        "profile_store_derive_windows": None,
        "profile_store_verify_windows": None,
        "runtime_commissioning": new_runtime_sequence_state(),
        "runtime_profile_seen": False,
        "runtime_profile_threshold_enter": None,
        "runtime_profile_threshold_exit": None,
        "runtime_profile_level_mean_dbfs": None,
        "runtime_profile_derive_windows": None,
        "calibration_accepted_state": False,
        "calibration_accepted_event": False,
        "calibration_rejected_state": False,
        "calibration_rejected_event": False,
        "calibration_rejection_reason": None,
        "expected_state_transition": None,
        "pending_state_event": None,
        "det_records": 0,
        "pending_det_quality": None,
        "last_det_window": 0,
        "last_total_alarm": 0,
        "last_consecutive": 0,
        "det_threshold": None,
        # Faza 2: host nezavisno ponavlja odluku o prisustvu i odstupanju iz
        # gate-a objavljenog u PRESENCE zapisu, umjesto da vjeruje firmveru.
        "presence_seen": False,
        "presence_gate_dbfs": None,
        "presence_min_consecutive": None,
        "temporal_seen": False,
        "temporal_min_consecutive": None,
        "temporal_threshold_mode": None,
        "temporal_threshold_enter": None,
        "temporal_threshold_exit": None,
        "interference_seen": False,
        "interference_source": None,
        "interference_normal_windows": None,
        "interference_normal_max": None,
        "interference_multiplier": None,
        "interference_threshold": None,
        "robust_fit_seen": False,
        "robust_fit_threshold": None,
        "robust_fit_n": None,
        "absent_run": 0,
        "deviation_run": 0,
        "anomaly_active": False,
        # `run_session()` emituje BOOT_FAIL_CLOSED odmah nakon SESSION STARTED.
        # Ovo je session-local wire anchor, odvojen od run-scope handshake-a.
        "session_boot_seen": False,
        "session_started": False,
        "session_aborted": False,
        "terminal": False,
        "drain_required": False,
        "terminal_state_seen": False,
        "terminal_event_seen": False,
        "drain_expected_phase": None,
        "drain_expected_reason": None,
        "drain_expected_state": None,
        "drain_mismatch": None,
        "last_state": None,
    }


def new_firmware_protocol_state() -> dict[str, Any]:
    """Return separated run/session scopes in one JSON-compatible tracker.

    Flat session keys are retained because they are the strict parser's hot
    path.  ``run_*`` counters and ``session_history`` are never reset by a new
    firmware session.
    """
    return {
        "handshake": False,
        "run_boot_records": 0,
        "run_quality_counts": {"WAIT": 0, "CAL": 0, "CAL_SUMMARY": 0, "DET": 0},
        "run_det_records": 0,
        "sessions": 0,
        "sessions_ended": 0,
        "session_history": [],
        "invalid_status": None,
        "invalid_reason": None,
        **new_session_protocol_state(),
    }


def reset_session_protocol_state(
    state: dict[str, Any], *, firmware_session_index: int,
) -> dict[str, Any]:
    """Reset exactly the firmware-session scope, preserving run evidence."""
    state.update(new_session_protocol_state(
        firmware_session_index=firmware_session_index,
    ))
    return state


def session_boot_seen(state: dict[str, Any]) -> bool:
    """Read the session BOOT anchor, preserving v1.6 offline provenance."""
    if "session_boot_seen" in state:
        return bool(state["session_boot_seen"])
    # Istorijski v1.6 tracker imao je samo run-level `handshake`. Njegov BOOT
    # pripada jedinoj implicitnoj sesiji prilikom offline citanja.
    return bool(state.get("handshake", False))


def firmware_calibration_source_accepted(state: dict[str, Any]) -> bool:
    return bool(
        state.get("profile_store_valid", False)
        or calibration_acceptance(state)[0]
    )


def firmware_protocol_ready(state: dict[str, Any]) -> bool:
    counts = state["quality_counts"]
    calibration_source_complete = bool(
        state.get("profile_store_valid", False)
        or all(counts[phase] == expected
               for phase, expected in EXPECTED_QUALITY_COUNTS.items())
    )
    return bool(
        state["handshake"]
        and session_boot_seen(state)
        and state["calibration_accepted_state"]
        and state["calibration_accepted_event"]
        and state["adapt_seen"]
        and state.get("runtime_profile_seen", False)
        and state["presence_seen"]
        and state["temporal_seen"]
        and calibration_source_complete
        and state["expected_state_transition"] is None
        and state["pending_state_event"] is None
        and not state["terminal"]
        and state["invalid_status"] is None
    )


def firmware_protocol_complete(state: dict[str, Any]) -> bool:
    accepted_complete = bool(
        firmware_protocol_ready(state)
        and state["pending_det_quality"] is None
        and state["expected_state_transition"] is None
        and state["pending_state_event"] is None
        and state["quality_counts"]["DET"] == state["det_records"]
    )
    return accepted_complete or firmware_protocol_calibration_rejected(state)


def firmware_protocol_calibration_rejected(state: dict[str, Any]) -> bool:
    """A K1 rejection is a valid terminal protocol, not malformed telemetry."""
    counts = state["quality_counts"]
    return bool(
        state["handshake"]
        and session_boot_seen(state)
        and state["cal_summary"] is not None
        and state.get("calibration_rejected_state", False)
        and state.get("calibration_rejected_event", False)
        and state.get("calibration_rejection_reason") == "UNSTABLE_CALIBRATION"
        and state.get("sessions", 0) > 0
        and state.get("sessions_ended", 0) == state.get("sessions", 0)
        and not state.get("session_started", False)
        and all(counts[phase] == expected
                for phase, expected in EXPECTED_QUALITY_COUNTS.items())
        and counts["DET"] == 0
        and state["det_records"] == 0
        and not state["adapt_seen"]
        and not state["presence_seen"]
        and not state["temporal_seen"]
        and not state["calibration_accepted_state"]
        and not state["calibration_accepted_event"]
        and state["pending_det_quality"] is None
        and state["expected_state_transition"] is None
        and state["pending_state_event"] is None
        and state["terminal"]
        and state["terminal_state_seen"]
        and state["terminal_event_seen"]
        and state["drain_mismatch"] is None
        and state["invalid_status"] is None
    )


def session_protocol_record(
    state: dict[str, Any], *, closed: bool | None = None,
) -> dict[str, Any]:
    """Freeze the protocol verdict for the current firmware-local session."""
    if state.get("profile_store_valid", False):
        accepted, acceptance_reason = True, "restored_profile_valid"
    else:
        accepted, acceptance_reason = calibration_acceptance(state)
    rejected = firmware_protocol_calibration_rejected(state)
    accepted_complete = bool(
        firmware_protocol_ready(state)
        and state["pending_det_quality"] is None
        and state["expected_state_transition"] is None
        and state["pending_state_event"] is None
        and state["quality_counts"]["DET"] == state["det_records"]
    )
    protocol_complete = accepted_complete or rejected
    protocol_valid = bool(protocol_complete and state["invalid_status"] is None)
    if rejected:
        protocol_status = "calibration_rejected"
    elif accepted_complete:
        protocol_status = "accepted"
    elif state["invalid_status"] is not None:
        protocol_status = str(state["invalid_status"])
    else:
        protocol_status = "incomplete"
    index = int(state.get("firmware_session_index") or state.get("sessions") or 0)
    return {
        "firmware_session_index": index,
        "closed": (not state.get("session_started", False)) if closed is None else bool(closed),
        "session_aborted": bool(state.get("session_aborted", False)),
        "protocol_status": protocol_status,
        "protocol_complete": protocol_complete,
        "protocol_valid": protocol_valid,
        "session_boot_seen": session_boot_seen(state),
        "calibration_accepted": accepted,
        "calibration_acceptance_reason": acceptance_reason,
        "quality_counts": dict(state["quality_counts"]),
        "det_records": int(state["det_records"]),
        "alarm_windows_reported": int(state["last_total_alarm"]),
        "threshold": state["adapt_threshold"],
    }


def protocol_session_records(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return closed history plus the current/legacy active session once."""
    records = [dict(item) for item in state.get("session_history", [])]
    current_index = int(
        state.get("firmware_session_index") or state.get("sessions") or 0
    )
    if current_index == 0 and (
        state.get("cal_summary") is not None
        or any(int(value) for value in state.get("quality_counts", {}).values())
    ):
        # Host-unit fixtures and v1.6 artefacts predate the explicit index.
        current_index = 1
    if current_index > 0 and not any(
        int(item.get("firmware_session_index", 0)) == current_index
        for item in records
    ):
        current = session_protocol_record(state)
        current["firmware_session_index"] = current_index
        records.append(current)
    return records


def _detection_session_index(row: dict[str, Any]) -> int:
    """v1.6 rows predate the explicit key and belong to their sole session."""
    try:
        return max(1, int(row.get("firmware_session_index", 1)))
    except (TypeError, ValueError):
        return 1


def detection_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Window metrics without bridging sessions or excluded time gaps."""
    excluded_transition_windows = sum(
        int(row.get("transition_window", 0)) for row in rows
    )
    metric_rows = [
        row for row in rows if int(row.get("transition_window", 0)) == 0
    ]
    ordered = sorted(
        metric_rows,
        key=lambda row: (
            _detection_session_index(row),
            int(row.get("run_det_index") or row.get("window") or 0),
        ),
    )
    alarm_windows = sum(int(row.get("alarm", 0)) for row in ordered)
    alarm_entries = 0
    alarm_episodes = 0
    previous_alarm = 0
    recovery_latencies: list[float] = []
    previous_elapsed: float | None = None
    previous_session: int | None = None
    previous_index: int | None = None
    for row in ordered:
        session_index = _detection_session_index(row)
        row_index = int(row.get("run_det_index") or row.get("window") or 0)
        # Nova firmware sesija i rupa u run indeksima predstavljaju stvarni
        # commissioning/condition gap. Alarm, epizoda i recovery ne smiju se
        # povezati preko vremena koje nije podobno za metrike.
        if (
            previous_session is not None
            and (
                session_index != previous_session
                or (previous_index is not None and row_index != previous_index + 1)
            )
        ):
            previous_alarm = 0
            previous_elapsed = None
        alarm = int(row.get("alarm", 0))
        try:
            elapsed = float(row.get("elapsed_s"))
        except (TypeError, ValueError):
            elapsed = None
        if alarm and not previous_alarm:
            alarm_entries += 1
            alarm_episodes += 1
        if previous_alarm and not alarm:
            recovery_latencies.append(
                max(0.0, elapsed - previous_elapsed)
                if elapsed is not None and previous_elapsed is not None
                else 10.0
            )
        previous_alarm = alarm
        previous_elapsed = elapsed
        previous_session = session_index
        previous_index = row_index
    return {
        "det_count": len(ordered),
        "alarm_window_count": alarm_windows,
        "alarm_entries": alarm_entries,
        "alarm_episodes": alarm_episodes,
        "alarm_time_percent": (
            100.0 * alarm_windows / len(ordered) if ordered else 0.0
        ),
        "recovery_latency_s": (
            statistics.median(recovery_latencies) if recovery_latencies else None
        ),
        "recovery_latencies_s": recovery_latencies,
        "excluded_transition_windows": excluded_transition_windows,
    }


def evaluate_run_validity(
    *, status: str, detections: list[dict[str, Any]],
    protocol_state: dict[str, Any] | None,
) -> dict[str, Any]:
    """Central multi-session verdict with K1 and metrics kept separate."""
    if protocol_state is None:
        session_protocols: list[dict[str, Any]] = []
    else:
        session_protocols = protocol_session_records(protocol_state)

    status_completed = status.startswith("completed")
    session_summaries: list[dict[str, Any]] = []
    metric_detections: list[dict[str, Any]] = []
    condition_protocol_detections: list[dict[str, Any]] = []
    protocol_valid_detections = [
        row for row in detections if int(row.get("protocol_valid", 0)) == 1
    ]
    protocol_by_index = {
        int(record["firmware_session_index"]): record
        for record in session_protocols
    }
    for index in sorted(protocol_by_index):
        protocol = protocol_by_index[index]
        session_rows = [
            row for row in detections if _detection_session_index(row) == index
        ]
        protocol_rows = [
            row for row in session_rows if int(row.get("protocol_valid", 0)) == 1
        ]
        candidates = [
            row for row in protocol_rows
            if int(row.get("condition_confirmed", 0)) == 1
            and int(row.get("transition_window", 0)) == 0
        ]
        condition_protocol_detections.extend(candidates)
        count_consistent = int(protocol["det_records"]) == len(protocol_rows)
        eligible = bool(
            status_completed and protocol["protocol_valid"]
            and protocol["calibration_accepted"] and count_consistent
        )
        eligible_rows = candidates if eligible else []
        metric_detections.extend(eligible_rows)
        session_summaries.append({
            **protocol,
            "tracker_count_consistent": count_consistent,
            "metrics_eligible": bool(eligible and eligible_rows),
            **detection_metrics(eligible_rows),
            "raw_det_count": len(session_rows),
            "protocol_valid_det_count": len(protocol_rows),
            "excluded_transition_windows": sum(
                int(row.get("transition_window", 0)) for row in session_rows
            ),
        })

    run_det_records = (
        int(protocol_state.get("run_det_records", protocol_state.get("det_records", 0)))
        if protocol_state is not None else -1
    )
    tracker_count_consistent = run_det_records == len(protocol_valid_detections)
    protocol_complete = bool(
        session_summaries
        and all(item["protocol_complete"] for item in session_summaries)
    )
    protocol_valid = bool(
        protocol_complete and tracker_count_consistent
        and all(item["protocol_valid"] for item in session_summaries)
    )
    accepted_sessions = [
        item for item in session_summaries if item["calibration_accepted"]
    ]
    calibration_accepted = bool(accepted_sessions)
    calibration_reason = (
        "accepted" if calibration_accepted
        else (
            session_summaries[-1]["calibration_acceptance_reason"]
            if session_summaries else "missing_protocol_state"
        )
    )
    metrics_eligible = bool(
        status_completed and protocol_valid and metric_detections
    )

    if not status_completed:
        result_status = f"run_status:{status}"
    elif not protocol_valid:
        result_status = "protocol_not_complete_or_inconsistent"
    elif not calibration_accepted:
        result_status = f"calibration_rejected:{calibration_reason}"
    elif not metric_detections:
        result_status = "no_confirmed_metric_detections"
    else:
        result_status = "valid_physical_result"

    return {
        "valid_result": metrics_eligible,
        "result_status": result_status,
        "protocol_valid": protocol_valid,
        "protocol_complete": protocol_complete,
        "tracker_count_consistent": tracker_count_consistent,
        "calibration_accepted": calibration_accepted,
        "calibration_acceptance_reason": calibration_reason,
        "metrics_eligible": metrics_eligible,
        "condition_protocol_detections": condition_protocol_detections,
        "protocol_valid_detections": protocol_valid_detections,
        "metric_detections": metric_detections if metrics_eligible else [],
        "sessions": session_summaries,
        "run_metrics": detection_metrics(metric_detections if metrics_eligible else []),
        "run_det_records": run_det_records,
    }


def terminal_drain_decision(
    state: dict[str, Any], elapsed_s: float, timeout_s: float = TERMINAL_DRAIN_TIMEOUT_S,
) -> str:
    """Pure bounded-drain decision used by the serial loop and unit tests."""
    if not state["drain_required"]:
        return "not_required"
    terminal_pair_seen = bool(
        state["terminal_state_seen"] and state["terminal_event_seen"]
    )
    is_k1_rejection = bool(
        state.get("calibration_rejected_state")
        or state.get("calibration_rejected_event")
        or state.get("calibration_rejection_reason") == "UNSTABLE_CALIBRATION"
    )
    session_pair_closed = bool(
        state.get("sessions", 0) > 0
        and state.get("sessions_ended", 0) == state.get("sessions", 0)
        and not state.get("session_started", False)
    )
    if terminal_pair_seen and (not is_k1_rejection or session_pair_closed):
        return "complete"
    if elapsed_s >= timeout_s:
        return "timeout"
    return "continue"


def terminal_drain_timeout_reason(state: dict[str, Any]) -> str:
    """Stable audit reason for the first missing part of a bounded drain."""
    if not state.get("terminal_state_seen"):
        return "terminal_drain_timeout:missing_STATE"
    if not state.get("terminal_event_seen"):
        return "terminal_drain_timeout:missing_FLOW_STOPPED"
    if (
        state.get("calibration_rejection_reason") == "UNSTABLE_CALIBRATION"
        and (
            state.get("session_started", False)
            or state.get("sessions", 0) <= 0
            or state.get("sessions_ended", 0) != state.get("sessions", 0)
        )
    ):
        return "terminal_drain_timeout:missing_SESSION_ENDED"
    return "terminal_drain_timeout:incomplete_terminal_pair"


def research_package_open(state: dict[str, Any] | None) -> bool:
    """Da li je bar jedan najavljeni research prozor jos nedovrsen.

    Prozor se najavljuje `QUALITY ... result=OK feature_valid=1`, pa tek onda
    stize FEATURE96 i pet SUBSEG96 redova. Izmedju najave i posljednje grupe
    paket je otvoren i tisina na liniji ne znaci kraj prenosa.
    """
    if not state:
        return False
    packages = state.get("packages", {})
    for key in state.get("expected", {}):
        package = packages.get(key)
        if package is None:
            return True
        if package.get("feature") is None or len(package.get("groups", {})) < 5:
            return True
    return False


def final_buffer_drain_decision(
    elapsed_s: float, quiet_s: float, *, package_open: bool = False,
) -> str:
    if package_open:
        # Tisina se ne smije tumaciti kao kraj dok paket nije zatvoren; ceka se
        # ograniceno, pa se svejedno finalizuje i nepotpun paket obara run.
        return ("complete" if elapsed_s >= FINAL_BUFFER_OPEN_PACKAGE_TIMEOUT_S
                else "continue")
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
    # Faza 2: kad gate prisustva trajno padne, tok se zaustavlja u NO_MACHINE.
    # Nije kvar senzora nego izostanak masine, pa se i ne mapira u SENSOR_ERROR.
    if reason in {"FAN_STOPPED", "PRESENCE_LOST"}:
        return "NO_MACHINE"
    if reason in {"LOW_LEVEL_OBSERVATION", "INSUFFICIENT_LEVEL"}:
        return "NO_MACHINE"
    if reason in CALIBRATION_STOP_REASONS:
        return "CALIBRATION_REJECTED"
    if reason == "CLIPPING":
        return "RECALIBRATION_REQUIRED" if phase == "DET" else "CALIBRATION_REJECTED"
    return "SENSOR_ERROR"


def _inferred_terminal_phase(state: dict[str, Any]) -> str:
    if state["pending_det_quality"] is not None or state["calibration_accepted_event"]:
        return "DET"
    if state["quality_counts"]["CAL"] > 0 or state["quality_counts"]["CAL_SUMMARY"] > 0:
        return "CAL"
    return "WAIT"


def cal_summary_cv_is_quantization_consistent(
    loo_mean: float, loo_sd: float, loo_cv: float,
) -> bool:
    """Check ``cv = sd / abs(mean)`` using the actual six-decimal wire bins.

    Every value printed with ``%.6f`` represents an interval of half a decimal
    quantum around the received number.  A record is coherent when the possible
    ratio interval for mean/sd overlaps the possible interval for the emitted
    CV.  This is scale-aware and does not hide material mismatches behind an
    arbitrary relative tolerance.
    """
    values = (loo_mean, loo_sd, loo_cv)
    if not all(math.isfinite(value) and value >= 0.0 for value in values):
        return False

    half = CAL_SUMMARY_HALF_QUANTUM
    mean_lo = max(0.0, loo_mean - half)
    mean_hi = loo_mean + half
    sd_lo = max(0.0, loo_sd - half)
    sd_hi = loo_sd + half
    cv_lo = max(0.0, loo_cv - half)
    cv_hi = loo_cv + half

    # Firmware explicitly reports CV=0 when the unrounded mean is effectively
    # zero.  The all-zero point is therefore a valid member of these bins.
    if mean_lo <= 1e-12 and sd_lo <= 0.0 and cv_lo <= 0.0:
        return True
    if mean_hi <= 0.0:
        return False

    ratio_lo = sd_lo / mean_hi
    ratio_hi = math.inf if mean_lo <= 0.0 else sd_hi / mean_lo
    epsilon = max(math.ulp(ratio_lo), math.ulp(cv_lo), math.ulp(cv_hi))
    return max(ratio_lo, cv_lo) <= min(ratio_hi, cv_hi) + epsilon


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
        if not cal_summary_cv_is_quantization_consistent(
            record["loo_mean"], record["loo_sd"], record["loo_cv"],
        ):
            expected_cv = (
                record["loo_sd"] / abs(record["loo_mean"])
                if abs(record["loo_mean"]) > 1e-12 else 0.0
            )
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
    if record["result"] in {"AUDIO_TIMEOUT", "AUDIO_READ_ERROR"}:
        if samples >= expected_samples:
            return f"audio_failure_without_short_read:{phase}"
        if record["feature_valid"] != 0 or record["tonalness_valid"] != 0:
            return f"audio_failure_with_valid_feature:{phase}"
        return None
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
    if state["presence_gate_dbfs"] is None:
        return "DET_before_PRESENCE"

    # Hijerarhija Faze 2, ponovljena ovdje nezavisno od firmvera: prisustvo
    # masine gusi ocjenu odstupanja. Kad nivo padne ispod gate-a, brojac
    # odstupanja se resetuje i stanje se DRZI, umjesto da se emituje anomalija
    # koja ne postoji (score skoci kad masina utihne — izmjereno 08.08: 10 -> 59).
    present = float(record["level_dbfs"]) >= state["presence_gate_dbfs"]
    min_consecutive = state["presence_min_consecutive"] or N_CONSECUTIVE_ALARM

    # Faza 4: histereza. Iz alarma se izlazi tek ISPOD nizeg praga, pa score
    # koji visi oko praga ne pali i gasi alarm iz prozora u prozor.
    enter = state["temporal_threshold_enter"]
    leave = state["temporal_threshold_exit"]
    if enter is None or leave is None:
        return "DET_before_absolute_TEMPORAL_thresholds"
    temporal_n = state["temporal_min_consecutive"] or min_consecutive
    over = float(record["score"]) > enter

    if present:
        if int(record.get("hold", 0)):
            # Kapija je prozor proglasila nemjerljivim: niz se prekida
            # (`asd_temporal_suspend` postavlja run = 0), a aktivan alarm se NE
            # gasi -- HOLD nije dokaz da je masina u redu.
            if not over:
                return "hold_on_window_below_enter_threshold"
            expected_consecutive = 0
            expected_anomaly = state["anomaly_active"]
        elif state["anomaly_active"]:
            expected_anomaly = float(record["score"]) > leave
            expected_consecutive = 0 if not expected_anomaly else state["deviation_run"]
        else:
            expected_consecutive = state["deviation_run"] + 1 if over else 0
            expected_anomaly = expected_consecutive >= temporal_n
    else:
        expected_consecutive = 0
        # Odstupanje se ne ocjenjuje: prethodno stanje se zadrzava dok gate
        # prisustva ne odluci trajno.
        expected_anomaly = state["anomaly_active"]

    expected_alarm = int(expected_anomaly)
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
        "run_quality_counts": dict(previous.get(
            "run_quality_counts", previous["quality_counts"],
        )),
        "session_history": [
            dict(item) for item in previous.get("session_history", [])
        ],
        "runtime_commissioning": dict(previous.get(
            "runtime_commissioning", new_runtime_sequence_state(),
        )),
    }

    kind = record.get("kind")
    if (
        kind in {"QUALITY", "STATE", "EVENT", "PRESENCE", "TEMPORAL", "INTERFERENCE",
                 "SESSION", "BUTTON", "PROFILESTORE", "COMMISSION", "PROFILE"}
        and record.get("protocol") not in {None, QUALITY_PROTOCOL_VERSION}
    ):
        return _invalidate(
            state, "invalid_protocol_mismatch", "invalid_protocol_mismatch",
        )
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

    # `BUTTON` pise UI task, asinhrono u odnosu na mjerni tok, pa smije pasti
    # bilo gdje — i izmedju DET QUALITY zapisa i njegovog DET reda. Operaterski
    # zapis ne smije prekinuti lanac telemetrije, jer bi pritisak tastera u
    # pogresnoj milisekundi ponistio inace ispravan prolaz.
    if kind == "BUTTON":
        return state

    if kind in {"QUALITY", "ADAPTTHR", "TEMPORAL", "PRESENCE", "INTERFERENCE", "DET",
                "EVENT", "PROFILESTORE", "COMMISSION", "PROFILE"}:
        if not state.get("session_started", False):
            return _invalidate(
                state, "invalid_missing_telemetry",
                f"{kind}_without_open_SESSION",
            )
        if not session_boot_seen(state):
            return _invalidate(
                state, "invalid_missing_telemetry",
                f"{kind}_before_session_BOOT",
            )

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

    if kind == "COMMISSION":
        if state.get("profile_store_seen", False):
            return _invalidate(
                state, "invalid_firmware_telemetry",
                "COMMISSION_after_PROFILESTORE_restore",
            )
        try:
            advance_runtime_sequence(
                state["runtime_commissioning"], RuntimeRecord(kind, {
                    key: value for key, value in record.items() if key != "kind"
                }),
            )
        except RuntimeProtocolError as exc:
            return _invalidate(
                state, "invalid_firmware_telemetry",
                f"runtime_sequence:{exc}",
            )
        if record.get("phase") == "COMMISSION_DERIVE":
            accepted, reason = calibration_acceptance(state)
            if not accepted:
                return _invalidate(
                    state, "invalid_firmware_telemetry",
                    f"COMMISSION_DERIVE_before_K1:{reason}",
                )
    elif kind == "THRFIT":
        if state["robust_fit_seen"]:
            return _invalidate(
                state, "invalid_firmware_telemetry", "duplicate_THRFIT",
            )
        runtime = state["runtime_commissioning"]
        if (
            int(runtime.get("derive_windows", 0)) != int(record["n"])
            or int(runtime.get("verify_windows", 0)) != 0
            or bool(runtime.get("monitoring", False))
        ):
            return _invalidate(
                state, "invalid_missing_telemetry", "THRFIT_before_complete_DERIVE",
            )
        state["robust_fit_seen"] = True
        state["robust_fit_threshold"] = float(record["threshold"])
        state["robust_fit_n"] = int(record["n"])
    elif kind == "PROFILE":
        if state["runtime_profile_seen"]:
            return _invalidate(
                state, "invalid_firmware_telemetry", "duplicate_PROFILE",
            )
        if state.get("profile_store_valid", False):
            if state["runtime_commissioning"].get("started", False):
                return _invalidate(
                    state, "invalid_firmware_telemetry",
                    "restored_PROFILE_after_fresh_COMMISSION",
                )
            for record_key, state_key in (
                ("threshold_enter", "profile_store_threshold_enter"),
                ("threshold_exit", "profile_store_threshold_exit"),
                ("center_windows", "profile_store_center_windows"),
                ("derive_windows", "profile_store_derive_windows"),
                ("verify_windows", "profile_store_verify_windows"),
            ):
                if not math.isclose(
                    float(record[record_key]), float(state[state_key]),
                    rel_tol=1e-6, abs_tol=1e-6,
                ):
                    return _invalidate(
                        state, "invalid_firmware_telemetry",
                        f"PROFILE_PROFILESTORE_mismatch:{record_key}",
                    )
        else:
            try:
                advance_runtime_sequence(
                    state["runtime_commissioning"], RuntimeRecord(kind, {
                        key: value for key, value in record.items() if key != "kind"
                    }),
                )
            except RuntimeProtocolError as exc:
                return _invalidate(
                    state, "invalid_firmware_telemetry",
                    f"runtime_sequence:{exc}",
                )
            accepted, reason = calibration_acceptance(state)
            if not accepted:
                return _invalidate(
                    state, "invalid_firmware_telemetry",
                    f"PROFILE_before_K1:{reason}",
                )
        state["runtime_profile_seen"] = True
        state["runtime_profile_threshold_enter"] = float(record["threshold_enter"])
        state["runtime_profile_threshold_exit"] = float(record["threshold_exit"])
        state["runtime_profile_level_mean_dbfs"] = float(record["level_mean_dbfs"])
        state["runtime_profile_derive_windows"] = int(record["derive_windows"])
        if (
            state["robust_fit_seen"]
            and not state.get("profile_store_valid", False)
            and not math.isclose(
                float(record["threshold_enter"]),
                float(state["robust_fit_threshold"]),
                rel_tol=1e-6, abs_tol=1e-6,
            )
        ):
            return _invalidate(
                state, "invalid_firmware_telemetry", "PROFILE_THRFIT_threshold_mismatch",
            )
    elif kind == "QUALITY":
        if (
            state.get("profile_store_seen", False)
            and record.get("phase") in {"WAIT", "CAL", "CAL_SUMMARY"}
        ):
            return _invalidate(
                state, "invalid_firmware_telemetry",
                "QUALITY_after_PROFILESTORE_restore",
            )
        phase = str(record["phase"])
        result = str(record["result"])
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
        state["run_quality_counts"][phase] = (
            state["run_quality_counts"].get(phase, 0) + 1
        )
        if phase == "WAIT" and result == "OK":
            state["wait_ok_count"] += 1
        if phase == "CAL_SUMMARY":
            state["cal_summary"] = {
                key: float(record[key])
                for key in ("loo_mean", "loo_sd", "loo_cv", "loo_range")
            }
        if phase == "DET":
            state["pending_det_quality"] = record["index"]
    elif kind == "PROFILESTORE":
        if not PROFILE_PERSISTENCE_ALLOWED:
            return _invalidate(
                state, "invalid_firmware_telemetry",
                "PROFILESTORE_persistence_disabled",
            )
        if state.get("profile_store_seen", False):
            return _invalidate(
                state, "invalid_firmware_telemetry", "duplicate_PROFILESTORE",
            )
        if (
            any(int(value) for value in state["quality_counts"].values())
            or state["adapt_seen"] or state["presence_seen"]
            or state["temporal_seen"] or state["calibration_accepted_state"]
            or state["calibration_accepted_event"]
        ):
            return _invalidate(
                state, "invalid_firmware_telemetry",
                "PROFILESTORE_after_commissioning_started",
            )
        state["profile_store_seen"] = True
        state["profile_store_valid"] = True
        state["profile_store_generation"] = int(record["generation"])
        state["profile_store_crc32"] = int(record["crc32"])
        state["profile_store_threshold_enter"] = float(record["threshold_enter"])
        state["profile_store_threshold_exit"] = float(record["threshold_exit"])
        state["profile_store_center_windows"] = int(record["center_windows"])
        state["profile_store_derive_windows"] = int(record["derive_windows"])
        state["profile_store_verify_windows"] = int(record["verify_windows"])
        # Restored profile is the v1.8 threshold authority.  Reuse the legacy
        # threshold slots so all DET arithmetic stays single-source.
        state["adapt_seen"] = True
        state["adapt_threshold"] = float(record["threshold_enter"])
    elif kind == "ADAPTTHR":
        if state["adapt_seen"]:
            return _invalidate(state, "invalid_firmware_telemetry", "duplicate_ADAPTTHR")
        if state["quality_counts"]["CAL_SUMMARY"] != 1 or state["cal_summary"] is None:
            return _invalidate(
                state, "invalid_missing_telemetry", "ADAPTTHR_before_CAL_SUMMARY",
            )
        k1_accepted, k1_reason = calibration_acceptance(state)
        if not k1_accepted:
            return _invalidate(
                state, "invalid_firmware_telemetry",
                f"ADAPTTHR_after_failed_K1:{k1_reason}",
            )
        if not state["runtime_profile_seen"]:
            return _invalidate(
                state, "invalid_missing_telemetry", "ADAPTTHR_before_PROFILE",
            )
        if state["calibration_accepted_state"] or state["calibration_accepted_event"]:
            return _invalidate(
                state, "invalid_firmware_telemetry", "ADAPTTHR_after_calibration_acceptance",
            )
        if (
            record["n"] != state["runtime_profile_derive_windows"]
            or record["sd"] < 0.0 or record["mean"] < 0.0
            or record["threshold"] <= 0.0
        ):
            return _invalidate(state, "invalid_firmware_telemetry", "invalid_ADAPTTHR_numeric")
        if not math.isclose(
            record["p"], COMMISSION_ENTER_QUANTILE, abs_tol=1e-6,
        ):
            return _invalidate(state, "invalid_firmware_telemetry", "ADAPTTHR_p_mismatch")
        if any(record[field] != 0.0 for field in ("k", "theta", "lo", "factory")):
            return _invalidate(state, "invalid_firmware_telemetry", "ADAPTTHR_legacy_field_mismatch")
        if not math.isclose(
            record["threshold"], state["runtime_profile_threshold_enter"],
            rel_tol=1e-6, abs_tol=1e-6,
        ):
            return _invalidate(
                state, "invalid_firmware_telemetry",
                "ADAPTTHR_PROFILE_threshold_mismatch",
            )
        if state["robust_fit_seen"] and not state.get("profile_store_valid", False) and (
            not math.isclose(
                record["threshold"], float(state["robust_fit_threshold"]),
                rel_tol=1e-6, abs_tol=1e-6,
            )
        ):
            return _invalidate(
                state, "invalid_firmware_telemetry", "ADAPTTHR_THRFIT_threshold_mismatch",
            )
        state["adapt_seen"] = True
        state["adapt_threshold"] = float(record["threshold"])
    elif kind == "TEMPORAL":
        if state["temporal_seen"]:
            return _invalidate(state, "invalid_firmware_telemetry", "duplicate_TEMPORAL")
        if not state["adapt_seen"]:
            return _invalidate(
                state, "invalid_missing_telemetry", "TEMPORAL_before_ADAPTTHR")
        if not state["presence_seen"]:
            return _invalidate(
                state, "invalid_missing_telemetry", "TEMPORAL_before_PRESENCE")
        if not state["runtime_profile_seen"]:
            return _invalidate(
                state, "invalid_missing_telemetry", "TEMPORAL_before_PROFILE")
        if state["calibration_accepted_state"] or state["calibration_accepted_event"]:
            return _invalidate(
                state, "invalid_firmware_telemetry",
                "TEMPORAL_after_calibration_acceptance")
        threshold_enter = float(record["threshold_enter"])
        threshold_exit = float(record["threshold_exit"])
        if not math.isclose(
            threshold_enter, float(state["adapt_threshold"]), rel_tol=1e-6,
            abs_tol=1e-6,
        ):
            return _invalidate(
                state, "invalid_firmware_telemetry",
                "TEMPORAL_enter_mismatch_threshold_source",
            )
        if (
            not math.isclose(
                threshold_enter, float(state["runtime_profile_threshold_enter"]),
                rel_tol=1e-6, abs_tol=1e-6,
            )
            or not math.isclose(
                threshold_exit, float(state["runtime_profile_threshold_exit"]),
                rel_tol=1e-6, abs_tol=1e-6,
            )
        ):
            return _invalidate(
                state, "invalid_firmware_telemetry",
                "TEMPORAL_PROFILE_threshold_mismatch",
            )
        state["temporal_seen"] = True
        state["temporal_min_consecutive"] = int(record["min_consecutive"])
        state["temporal_threshold_mode"] = str(record["threshold_mode"])
        state["temporal_threshold_enter"] = threshold_enter
        state["temporal_threshold_exit"] = threshold_exit
    elif kind == "PRESENCE":
        # Gate prisustva mora stici tacno jednom, poslije praga i prije nego
        # sto kalibracija bude prihvacena — isti razlog kao za ADAPTTHR: da
        # nijedan DET prozor ne bude ocijenjen gate-om koji host nije vidio.
        if state["presence_seen"]:
            return _invalidate(state, "invalid_firmware_telemetry", "duplicate_PRESENCE")
        if state["temporal_seen"]:
            return _invalidate(
                state, "invalid_firmware_telemetry", "PRESENCE_after_TEMPORAL",
            )
        if not state["adapt_seen"]:
            return _invalidate(
                state, "invalid_missing_telemetry", "PRESENCE_before_ADAPTTHR",
            )
        if not state["runtime_profile_seen"]:
            return _invalidate(
                state, "invalid_missing_telemetry", "PRESENCE_before_PROFILE",
            )
        if state["calibration_accepted_state"] or state["calibration_accepted_event"]:
            return _invalidate(
                state, "invalid_firmware_telemetry",
                "PRESENCE_after_calibration_acceptance",
            )
        if record["level_mean_dbfs"] > 0.0:
            return _invalidate(
                state, "invalid_firmware_telemetry", "positive_PRESENCE_level",
            )
        if not math.isclose(
            record["level_mean_dbfs"], state["runtime_profile_level_mean_dbfs"],
            rel_tol=1e-6, abs_tol=1e-6,
        ):
            return _invalidate(
                state, "invalid_firmware_telemetry", "PRESENCE_PROFILE_level_mismatch",
            )
        if not math.isclose(record["margin_db"], PRESENCE_POLICY["absent_margin_db"],
                            abs_tol=1e-4):
            return _invalidate(
                state, "invalid_firmware_telemetry", "PRESENCE_margin_off_policy",
            )
        if record["min_consecutive"] != PRESENCE_POLICY["min_consecutive_windows"]:
            return _invalidate(
                state, "invalid_firmware_telemetry",
                "PRESENCE_min_consecutive_off_policy",
            )
        state["presence_seen"] = True
        state["presence_gate_dbfs"] = float(record["gate_dbfs"])
        state["presence_min_consecutive"] = int(record["min_consecutive"])
    elif kind == "INTERFERENCE":
        if state["interference_seen"]:
            return _invalidate(
                state, "invalid_firmware_telemetry", "duplicate_INTERFERENCE",
            )
        if not state["temporal_seen"]:
            return _invalidate(
                state, "invalid_missing_telemetry", "INTERFERENCE_before_TEMPORAL",
            )
        if state["calibration_accepted_state"] or state["calibration_accepted_event"]:
            return _invalidate(
                state, "invalid_firmware_telemetry",
                "INTERFERENCE_after_calibration_acceptance",
            )
        state["interference_seen"] = True
        state["interference_source"] = str(record["source"])
        state["interference_normal_windows"] = int(record["normal_windows"])
        state["interference_normal_max"] = float(record["normal_max"])
        state["interference_multiplier"] = float(record["multiplier"])
        state["interference_threshold"] = float(record["threshold"])
    elif kind == "SESSION":
        action = str(record["action"])
        if action == "STARTED":
            if (
                not PROFILE_PERSISTENCE_ALLOWED
                and (
                    record.get("source") == "FIRMWARE"
                    or record.get("reason") == "PROFILE_RESTORED"
                )
            ):
                return _invalidate(
                    state, "invalid_firmware_telemetry",
                    "PROFILE_RESTORED_persistence_disabled",
                )
            if state["session_started"]:
                return _invalidate(
                    state, "invalid_firmware_telemetry", "SESSION_STARTED_twice",
                )
            next_index = int(state.get("sessions", 0)) + 1
            reset_session_protocol_state(
                state, firmware_session_index=next_index,
            )
            state["session_started"] = True
            state["sessions"] = next_index
        elif action in {"ENDED", "ABORTED"} and not state["session_started"]:
            return _invalidate(
                state, "invalid_firmware_telemetry", f"SESSION_{action}_without_START",
            )
        elif action in {"ENDED", "ABORTED"} and not session_boot_seen(state):
            return _invalidate(
                state, "invalid_missing_telemetry",
                f"SESSION_{action}_before_BOOT",
            )
        elif action == "ABORTED":
            # `ABORTED` je RAZLOG, ne zatvaranje. Firmware ga emituje iz
            # `run_session()` kad operater dugim pritiskom trazi novo ucenje, a
            # sesiju zatim uredno zatvara sa `ENDED` iz glavne petlje. Host je
            # ranije `ABORTED` racunao kao zatvaranje, pa je sljedeci `ENDED`
            # visio bez para i rusio prolaz sa `SESSION_ENDED_without_START`
            # (izmjereno 16.08.2026, `cold-start-06`). Ovo je bio put koji do
            # tada nikad nije prosao kroz strogi host: rekalibracija na zahtjev.
            #
            # Strogost ostaje ista -- i dalje se trazi tacno jedan `ENDED` po
            # `STARTED`; `ABORTED` samo vise ne trosi otvorenu sesiju.
            state["session_aborted"] = True
        else:
            state["session_started"] = False
            state["sessions_ended"] = state.get("sessions_ended", 0) + 1
            state["session_history"].append(
                session_protocol_record(state, closed=True)
            )
            state["session_aborted"] = False
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
        if is_boot:
            if not state.get("session_started", False):
                return _invalidate(
                    state, "invalid_missing_telemetry", "BOOT_without_open_SESSION",
                )
            if session_boot_seen(state):
                return _invalidate(
                    state, "invalid_firmware_telemetry", "duplicate_BOOT_STATE",
                )
            if state["last_state"] is not None:
                return _invalidate(
                    state, "invalid_firmware_telemetry", "BOOT_after_session_STATE",
                )
            state["handshake"] = True
            state["session_boot_seen"] = True
            state["run_boot_records"] = int(state.get("run_boot_records", 0)) + 1
            state["last_state"] = "NO_MACHINE"
            return state
        if not state.get("session_started", False):
            return _invalidate(
                state, "invalid_missing_telemetry", "STATE_without_open_SESSION",
            )
        if not session_boot_seen(state):
            return _invalidate(state, "invalid_missing_telemetry", "first_STATE_not_BOOT")
        if from_state != state["last_state"]:
            return _invalidate(
                state, "invalid_firmware_telemetry",
                f"STATE_chain_mismatch:expected_from={state['last_state']}:got={from_state}",
            )
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
        is_profile_restore = (
            from_state == "NO_MACHINE" and to_state == "CALIBRATED_NORMAL"
            and reason == "PROFILE_RESTORED"
        )
        if is_profile_restore:
            if (
                not state.get("profile_store_valid", False)
                or not state["adapt_seen"] or not state["presence_seen"]
                or not state["temporal_seen"]
                or any(int(value) for value in state["quality_counts"].values())
                or state["calibration_accepted_state"]
            ):
                return _invalidate(
                    state, "invalid_missing_telemetry",
                    "PROFILE_RESTORED_without_valid_PROFILESTORE",
                )
            state["calibration_accepted_state"] = True
            state["last_state"] = to_state
            state["pending_state_event"] = {
                "type": "PROFILE_RESTORED", "state": "CALIBRATED_NORMAL",
                "phase": "PROFILE", "reason": "PROFILE_VALID",
            }
            return state
        if is_calibration_accept and not all(
            state["quality_counts"][phase] == expected
            for phase, expected in EXPECTED_QUALITY_COUNTS.items()
        ):
            state["invalid_status"] = "invalid_missing_telemetry"
            state["invalid_reason"] = "CALIBRATION_ACCEPTED_before_expected_quality"
            return state
        if is_calibration_accept:
            k1_accepted, k1_reason = calibration_acceptance(state)
            if not k1_accepted:
                return _invalidate(
                    state, "invalid_firmware_telemetry",
                    f"CALIBRATION_ACCEPTED_after_failed_K1:{k1_reason}",
                )
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

        is_k1_reject = (
            from_state == "NO_MACHINE" and to_state == "CALIBRATION_REJECTED"
            and reason == "UNSTABLE_CALIBRATION"
        )
        if is_k1_reject:
            if not all(
                state["quality_counts"][phase] == expected
                for phase, expected in EXPECTED_QUALITY_COUNTS.items()
            ):
                return _invalidate(
                    state, "invalid_missing_telemetry",
                    "UNSTABLE_CALIBRATION_before_expected_quality",
                )
            k1_accepted, k1_reason = calibration_acceptance(state)
            if k1_accepted or k1_reason != "loo_cv_above_max":
                return _invalidate(
                    state, "invalid_firmware_telemetry",
                    f"UNSTABLE_CALIBRATION_without_failed_K1:{k1_reason}",
                )
            if not state.get("session_started", False):
                return _invalidate(
                    state, "invalid_firmware_telemetry",
                    "UNSTABLE_CALIBRATION_without_open_SESSION",
                )
            if (
                state["adapt_seen"] or state["presence_seen"]
                or state["temporal_seen"] or state["calibration_accepted_state"]
                or state["calibration_accepted_event"]
                or state["calibration_rejected_state"]
            ):
                return _invalidate(
                    state, "invalid_firmware_telemetry",
                    "UNSTABLE_CALIBRATION_after_acceptance_or_duplicate",
                )
            state["calibration_rejected_state"] = True
            state["calibration_rejection_reason"] = reason
            state["last_state"] = to_state
            state["terminal"] = True
            state["drain_required"] = True
            state["terminal_state_seen"] = True
            state["drain_expected_state"] = to_state
            state["drain_expected_reason"] = reason
            state["drain_expected_phase"] = "CAL"
            return state

        # Nenajavljen PRESENCE_LOST: firmware tvrdi da masine nema, a host je iz
        # nivoa u DET zapisima izveo da gate prisustva nije pao. To nije
        # dozvoljen kraj toka nego neslaganje sa telemetrijom.
        if to_state == "NO_MACHINE" and reason == "PRESENCE_LOST":
            return _invalidate(
                state, "invalid_firmware_telemetry", "spurious_PRESENCE_LOST",
            )

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
            if reason not in FLOW_STOP_REASONS:
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
            elif event_payload["type"] == "PROFILE_RESTORED":
                if (
                    not state.get("profile_store_valid", False)
                    or state["calibration_accepted_event"]
                ):
                    return _invalidate(
                        state, "invalid_firmware_telemetry",
                        "invalid_or_duplicate_PROFILE_RESTORED_EVENT",
                    )
                state["calibration_accepted_event"] = True
            return state
        if event_payload["type"] == "FLOW_STOPPED":
            if event_payload["reason"] not in FLOW_STOP_REASONS:
                return _invalidate(state, "invalid_firmware_telemetry", "FLOW_STOPPED_reason_unknown")
            if event_payload["phase"] not in {"WAIT", "CAL", "DET"}:
                return _invalidate(state, "invalid_firmware_telemetry", "FLOW_STOPPED_phase_unknown")
            if event_payload["reason"] == "UNSTABLE_CALIBRATION":
                expected = {
                    "type": "FLOW_STOPPED", "state": "CALIBRATION_REJECTED",
                    "phase": "CAL", "reason": "UNSTABLE_CALIBRATION",
                }
                if (
                    event_payload != expected
                    or not state["calibration_rejected_state"]
                    or state["calibration_rejected_event"]
                ):
                    return _invalidate(
                        state, "invalid_firmware_telemetry",
                        "invalid_or_duplicate_UNSTABLE_CALIBRATION_EVENT",
                    )
                state["calibration_rejected_event"] = True
                state["terminal_event_seen"] = True
                return state
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
        allowed_states = UNPAIRED_EVENT_STATES.get(str(record.get("type", "")))
        if allowed_states is not None:
            # `OBSERVATION_HOLD_WARNING` i `ANOMALY_SUSTAINED` se javljaju DOK
            # stanje stoji, pa po prirodi nemaju upareni STATE red. Prihvataju se
            # samo ako tvrde bas ono stanje u kojem uredjaj vec jeste.
            if (str(record.get("state")) == str(state["last_state"])
                    and str(record.get("state")) in allowed_states):
                return state
            return _invalidate(
                state, "invalid_firmware_telemetry",
                f"unpaired_EVENT_state_mismatch:{record.get('type')}:"
                f"{record.get('state')}:last={state['last_state']}",
            )
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
            state["run_det_records"] = state.get("run_det_records", 0) + 1
            state["pending_det_quality"] = None
            state["last_det_window"] = record["window"]
            state["last_total_alarm"] = record["total_alarm"]
            state["last_consecutive"] = record["consecutive"]
            if state["det_threshold"] is None:
                state["det_threshold"] = float(record["threshold"])

            # Brojaci hijerarhije Faze 2, vodjeni nezavisno od firmvera.
            present = float(record["level_dbfs"]) >= state["presence_gate_dbfs"]
            min_consecutive = state["presence_min_consecutive"] or N_CONSECUTIVE_ALARM
            if present:
                state["absent_run"] = 0
                state["deviation_run"] = record["consecutive"]
            else:
                state["absent_run"] += 1
                state["deviation_run"] = 0
            state["anomaly_active"] = record["alarm"] == 1

            if not present and state["absent_run"] >= min_consecutive:
                # Gate prisustva je trajno pao: masine nema. Ovo NIJE anomalija
                # i ne smije se emitovati kao takva, bez obzira sto score skoci.
                state["expected_state_transition"] = {
                    "state": {
                        "from_state": str(state["last_state"]),
                        "to_state": "NO_MACHINE", "reason": "PRESENCE_LOST",
                    },
                    "event": {
                        "type": "PRESENCE_LOST", "state": "NO_MACHINE",
                        "phase": "DET", "reason": "PRESENCE_LOST",
                    },
                }
            elif int(record.get("hold", 0)) and state["last_state"] == "CALIBRATED_NORMAL":
                # Prvi nemjerljiv prozor iz normale objavljuje HOLD. Ako alarm
                # vec traje, firmware ostaje u ANOMALY i ne emituje nista.
                state["expected_state_transition"] = {
                    "state": {
                        "from_state": "CALIBRATED_NORMAL",
                        "to_state": "OBSERVATION_HOLD",
                        "reason": "OBSERVATION_UNCERTAIN",
                    },
                    "event": {
                        "type": "OBSERVATION_HOLD", "state": "OBSERVATION_HOLD",
                        "phase": "DET", "reason": "OBSERVATION_UNCERTAIN",
                    },
                }
            elif (state["last_state"] == "OBSERVATION_HOLD"
                  and not int(record.get("hold", 0)) and record["alarm"] == 0
                  and record["consecutive"] == 0):
                # Pouzdano mjerenje se vratilo i nije u usponu ka alarmu.
                state["expected_state_transition"] = {
                    "state": {
                        "from_state": "OBSERVATION_HOLD",
                        "to_state": "CALIBRATED_NORMAL",
                        "reason": "OBSERVATION_RESUMED",
                    },
                    "event": {
                        "type": "OBSERVATION_RESUMED", "state": "CALIBRATED_NORMAL",
                        "phase": "DET", "reason": "OBSERVATION_RESUMED",
                    },
                }
            elif (state["last_state"] == "OBSERVATION_HOLD" and record["alarm"] == 1):
                # Iz HOLD-a se u alarm ulazi tek poslije tri pouzdana prozora;
                # dotle uredjaj ostaje u HOLD i ne emituje prelaz.
                state["expected_state_transition"] = {
                    "state": {
                        "from_state": "OBSERVATION_HOLD", "to_state": "ANOMALY",
                        "reason": "THRESHOLD_PERSISTENCE",
                    },
                    "event": {
                        "type": "ANOMALY_ENTERED", "state": "ANOMALY",
                        "phase": "DET", "reason": "THRESHOLD_PERSISTENCE",
                    },
                }
            elif state["last_state"] == "CALIBRATED_NORMAL" and record["alarm"] == 1:
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
    firmware_session_index: int = 0,
) -> dict[str, Any]:
    event = {
        "host_utc": utc_now(),
        "elapsed_s": round(time.monotonic() - started, 3),
        "firmware_session_index": firmware_session_index,
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


def apply_serial_timeout(ser: Any, desired: float) -> bool:
    """Postavi `timeout` SAMO ako se stvarno mijenja. Vraca True ako jeste.

    Na Windowsu dodjela `Serial.timeout` poziva `_reconfigure_port()`, a to
    odbaci bajtove koji jos cekaju na slanje. Petlja koja je u svakom prolazu
    pisala `ser.timeout = 1` zato je gutala svaku komandu poslatu uredjaju:
    izmjereno 16.08.2026, isti kod i isti port -- bez te dodjele 3/3 komande
    stignu, sa njom 0/3. To je bio uzrok svih danasnjih "kliknuo sam, nista se
    nije desilo": `events.csv` je biljezio pritisak, `ser.write` nije prijavio
    gresku, a do plocice nije stizao nijedan bajt.

    U ustaljenom radu timeout je konstantan, pa se port ne konfigurise nijednom
    i pisanje je bezbjedno. Tokom terminalnog drena vrijednost se stvarno
    mijenja i port se rekonfigurise -- ali tada se komande vise i ne salju.
    """
    if ser.timeout == desired:
        return False
    ser.timeout = desired
    return True


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
    source_protocol_version: str = PROTOCOL_VERSION,
) -> str:
    if source_protocol_version not in SUPPORTED_READ_PROTOCOL_VERSIONS:
        raise ValueError(
            "nepodrzan physical-fan protokol izvornog artefakta: "
            f"{source_protocol_version!r}"
        )
    threshold = (
        protocol_state.get("adapt_threshold")
        if protocol_state is not None else None
    )
    validity = evaluate_run_validity(
        status=status, detections=detections, protocol_state=protocol_state,
    )
    valid_detections = validity["metric_detections"]
    condition_protocol_detections = validity["condition_protocol_detections"]
    protocol_valid_detections = validity["protocol_valid_detections"]
    run_metrics = validity["run_metrics"]
    lines = [
        "# Stvarni fizicki fan eksperiment",
        "",
        f"- Status: `{status}`",
        f"- Status fizičkog rezultata: `{validity['result_status']}`",
        f"- Validan fizički rezultat: **{'DA' if validity['valid_result'] else 'NE'}**",
        f"- Protokol izvještaja: `{PROTOCOL_VERSION}`",
        f"- Izvorni protokol artefakta: `{source_protocol_version}`",
        f"- Firmware protokol validan i kompletan: **{'DA' if validity['protocol_valid'] else 'NE'}**",
        f"- Kalibracija prihvaćena (K1): **{'DA' if validity['calibration_accepted'] else 'NE'}** "
        f"(`{validity['calibration_acceptance_reason']}`; politika "
        f"`{COMMISSIONING_POLICY_RECORD['schema_version']}`)",
        f"- Prozori podobni za metrike: **{'DA' if validity['metrics_eligible'] else 'NE'}**",
        f"- Fan ID: `{metadata['fan_id']}`",
        f"- Sesija: `{metadata['session_id']}`",
        f"- Port: `{metadata['port']}` @ {metadata['baud']} baud",
        f"- Udaljenost: {metadata['distance_cm']} cm",
        f"- Prostorija: {metadata['room']}",
        f"- Prag: {threshold if threshold is not None else 'nije dobijen'}",
        f"- DET prozora: {len(detections)}",
        f"- Validnih DET prozora za metrike: {len(valid_detections)}",
        f"- Condition+protocol validnih DET kandidata: {len(condition_protocol_detections)}",
        f"- Protocol-valid DET prozora: {len(protocol_valid_detections)}",
        f"- Tracker/CSV DET count saglasan: **{'DA' if validity['tracker_count_consistent'] else 'NE'}**",
        f"- Isključenih DET prozora: {len(detections) - len(valid_detections)}",
        f"- Alarmnih validnih DET prozora: {sum(int(row['alarm']) for row in valid_detections)}",
        f"- Firmware sesija: {len(validity['sessions'])}",
        f"- Run DET total (tracker/CSV): {validity['run_det_records']}/{len(protocol_valid_detections)}",
        f"- Alarmnih prozora / ulazaka / epizoda: "
        f"{run_metrics['alarm_window_count']} / {run_metrics['alarm_entries']} / "
        f"{run_metrics['alarm_episodes']}",
        f"- Vrijeme u alarmu: {run_metrics['alarm_time_percent']:.2f}%",
        f"- Medijana oporavka: "
        f"{run_metrics['recovery_latency_s'] if run_metrics['recovery_latency_s'] is not None else 'nije izmjerena'} s",
        f"- Isključenih prelaznih prozora: "
        f"{sum(item['excluded_transition_windows'] for item in validity['sessions'])}",
        f"- Najveci prijavljeni `dropped`: {max_dropped if max_dropped is not None else 'nije ispisan'}",
        "",
        "## Rezultati po firmware sesiji",
        "",
        "| Sesija | Protokol | K1 | DET raw/metric | Alarm prozori/epizode | Alarm % | Oporavak s | Prelazni isključeni |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for session in validity["sessions"]:
        recovery = session["recovery_latency_s"]
        lines.append(
            f"| {session['firmware_session_index']} | {session['protocol_status']} "
            f"({'valid' if session['protocol_valid'] else 'invalid'}) | "
            f"{session['calibration_acceptance_reason']} | "
            f"{session['raw_det_count']}/{session['det_count']} | "
            f"{session['alarm_window_count']}/{session['alarm_episodes']} | "
            f"{session['alarm_time_percent']:.2f} | "
            f"{recovery if recovery is not None else '-'} | "
            f"{session['excluded_transition_windows']} |"
        )
    if not validity["sessions"]:
        lines.append("| - | nema | - | 0/0 | 0/0 | 0.00 | - | 0 |")
    lines.extend([
        "",
        "## Rezultati po rucno oznacenom uslovu",
        "",
        "| Uslov | Prozora | Alarmnih | Score medijana | Score opseg |",
        "|---|---:|---:|---:|---:|",
    ])
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
        "nakon validnog firmware handshake/CAL ugovora i prihvaćene K1 "
        "kalibracije ulaze u metrike. "
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


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def artifact_protocol_version_for_read(provenance: dict[str, Any]) -> str:
    """Validate the locked host/UART artifact pair before offline reading."""
    version = provenance.get("protocol_version")
    if not isinstance(version, str) or version not in SUPPORTED_READ_PROTOCOL_VERSIONS:
        supported = ", ".join(sorted(SUPPORTED_READ_PROTOCOL_VERSIONS))
        raise ValueError(
            "nepodrzan ili nedostajuci physical-fan protocol_version "
            f"{version!r}; offline citanje podrzava: {supported}"
        )
    quality_version = provenance.get("quality_protocol_version")
    expected_quality = ARTIFACT_QUALITY_PROTOCOL_PAIRS[version]
    if not isinstance(quality_version, str):
        raise ValueError(
            "nedostajuci quality_protocol_version za offline artefakt; "
            f"{version} zahtijeva {expected_quality}"
        )
    if quality_version != expected_quality:
        raise ValueError(
            "nepodudaran host/UART protokolarni par za offline artefakt: "
            f"{version} zahtijeva {expected_quality}, dobijeno {quality_version!r}"
        )
    if version in ARTIFACT_CONTRACT_VERSIONS:
        contract = provenance.get("artifact_contract_version")
        expected_contract = ARTIFACT_CONTRACT_VERSIONS[version]
        if contract != expected_contract:
            raise ValueError(
                "nedostajuci ili nepodudaran artifact contract: "
                f"ocekivano {expected_contract}, dobijeno {contract!r}"
            )
    return version


def recompute_run_summary(run_dir: Path) -> tuple[str, dict[str, Any]]:
    """Re-evaluate an existing run without changing any original artifact."""
    provenance_path = run_dir / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    source_protocol_version = artifact_protocol_version_for_read(provenance)
    detections = _read_csv_rows(run_dir / "detections.csv")
    if source_protocol_version == "physical-fan-v1.6.0":
        for run_index, row in enumerate(detections, start=1):
            row.setdefault("firmware_session_index", "1")
            row.setdefault("run_det_index", str(run_index))
            row.setdefault("transition_window", "0")
    for row in detections:
        # Do q1.5.0 kapija pouzdanosti nije postojala, pa je 0 tacno, a ne
        # pretpostavka.
        row.setdefault("hold", "0")
    events = _read_csv_rows(run_dir / "events.csv")
    for event in events:
        event["elapsed_s"] = float(event["elapsed_s"])
    status = str(provenance["status"])
    protocol_state = provenance.get("firmware_protocol_state")
    validity = evaluate_run_validity(
        status=status, detections=detections, protocol_state=protocol_state,
    )
    summary = make_summary(
        metadata=provenance["metadata"],
        status=status,
        events=events,
        detections=detections,
        max_dropped=provenance.get("max_dropped"),
        protocol_state=protocol_state,
        source_protocol_version=source_protocol_version,
    )
    return summary, validity


def recompute_summary_command(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    output_name = str(args.output_name)
    if Path(output_name).name != output_name or output_name == "SUMMARY.md":
        raise SystemExit("recompute smije pisati samo novi sidecar, ne originalni SUMMARY.md")
    summary, validity = recompute_run_summary(run_dir)
    output_path = run_dir / output_name
    try:
        with output_path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(summary)
    except FileExistsError as exc:
        raise SystemExit(f"recompute sidecar vec postoji: {output_path}") from exc
    print(
        f"recompute: {validity['result_status']} "
        f"(K1={validity['calibration_acceptance_reason']}): {output_path}"
    )
    return 0


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
    protocol_state = new_firmware_protocol_state()
    validity = evaluate_run_validity(
        status="failed", detections=[], protocol_state=protocol_state,
    )
    provenance.update({
        "status": "failed",
        "finished_utc": utc_now(),
        "metadata": metadata,
        "failure": f"{type(exc).__name__}: {exc}",
        "physical_result_status": validity["result_status"],
        "protocol_valid": validity["protocol_valid"],
        "calibration_accepted": validity["calibration_accepted"],
        "calibration_acceptance_reason": validity["calibration_acceptance_reason"],
        "metrics_eligible": validity["metrics_eligible"],
        "commissioning_policy": COMMISSIONING_POLICY_RECORD,
        "firmware_protocol_state": protocol_state,
    })
    try:
        write_json(run_dir / "provenance.json", provenance)
    except OSError:
        pass
    try:
        (run_dir / "SUMMARY.md").write_text(
            make_summary(
                metadata=metadata, status="failed", events=[], detections=[],
                max_dropped=None, protocol_state=protocol_state,
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
    if args.research_telemetry_required and not build_has_research_telemetry():
        raise SystemExit(
            "--research-telemetry-required trazi build sa ASD_RESEARCH_TELEMETRY"
        )

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
        "research_telemetry_required": bool(args.research_telemetry_required),
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
    dropped_observed = False
    guided_workflow_accepted = False
    guided_workflow_pending = False
    guided_capability_seen = False
    telemetry_counts = {"QUALITY": 0, "STATE": 0, "EVENT": 0,
                        "PRESENCE": 0, "TEMPORAL": 0, "INTERFERENCE": 0,
                        "THRFIT": 0,
                        "SESSION": 0, "BUTTON": 0, "PROFILESTORE": 0,
                        "COMMISSION": 0, "PROFILE": 0,
                        "FEATURE96": 0, "SUBSEG96": 0}
    last_firmware_state: str | None = None
    protocol_state = new_firmware_protocol_state()
    research_state = new_research_telemetry_state(
        required=bool(args.research_telemetry_required),
    )
    drain_started: float | None = None
    finalize_requested_status: str | None = None
    finalize_drain_started: float | None = None
    last_serial_data_at: float | None = None
    current_condition = "unconfirmed"
    condition_confirmed = False
    transition_window_pending = False
    status = "interrupted"
    final_validity: dict[str, Any] | None = None
    guided_report: dict[str, Any] | None = None
    started = time.monotonic()

    event_fields = [
        "host_utc", "elapsed_s", "firmware_session_index",
        "kind", "label", "note",
    ]
    det_fields = [
        "host_utc", "elapsed_s", "firmware_session_index", "run_det_index",
        "condition", "condition_confirmed", "transition_window",
        "protocol_valid", "window", "score", "lo", "threshold",
        "alarm", "total_alarm", "consecutive", "hold", "verdict",
        "level_dbfs", "compute_ms",
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
        # Operaterski tok ide u ODVOJEN zapis, kao i do sada operatorova
        # condition: sesije i pritisci tastera se nikad ne mijesaju sa
        # firmverskim zakljuckom.
        operator_handle = stack.enter_context(
            (run_dir / "firmware_operator.csv").open("w", encoding="utf-8", newline=""),
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
        operator_writer = csv.DictWriter(operator_handle, fieldnames=OPERATOR_FIELDS)
        event_writer.writeheader()
        det_writer.writeheader()
        quality_writer.writeheader()
        state_writer.writeheader()
        firmware_event_writer.writeheader()
        parse_error_writer.writeheader()
        operator_writer.writeheader()

        def record_event(*, kind: str, label: str, note: str = "") -> dict[str, Any]:
            """Attach every host event to the active firmware session (or run 0)."""
            return add_event(
                events, event_writer, event_handle, started=started,
                kind=kind, label=label, note=note,
                firmware_session_index=int(
                    protocol_state.get("firmware_session_index", 0)
                ),
            )

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
            record_event(
                kind="session", label="start",
                note="sigurnosna postavka potvrđena; operator condition=unconfirmed",
            )
            if not args.no_reset:
                ser.setDTR(False)
                ser.setRTS(True)
                time.sleep(0.15)
                ser.setRTS(False)
                time.sleep(0.3)
                ser.reset_input_buffer()
                record_event(
                    kind="device", label="reset",
                    note="RTS reset; pocinje WAIT/CAL/DET",
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
                        timeout_reason = terminal_drain_timeout_reason(protocol_state)
                        if protocol_state["invalid_status"] is None:
                            protocol_state = _invalidate(
                                protocol_state, "invalid_missing_telemetry",
                                timeout_reason,
                            )
                            status = "invalid_missing_telemetry"
                        record_event(
                            kind="protocol", label="terminal_drain_timeout",
                            note=f"{timeout_reason}; elapsed={drain_elapsed:.3f} s",
                        )
                        break
                elif finalize_drain_started is not None:
                    quiet_since = last_serial_data_at or finalize_drain_started
                    package_open = research_package_open(research_state)
                    if final_buffer_drain_decision(
                        now - finalize_drain_started, now - quiet_since,
                        package_open=package_open,
                    ) == "complete":
                        status = str(finalize_requested_status)
                        drained = now - finalize_drain_started
                        record_event(
                            kind="session", label="final_buffer_drain_complete",
                            note=("buffered UART je procitan prije finalizacije; "
                                  f"trajanje={drained:.3f} s; "
                                  f"paket_jos_otvoren={int(package_open)}"),
                        )
                        break
                if (
                    drain_started is None and finalize_drain_started is None
                    and args.max_seconds and now - started >= args.max_seconds
                ):
                    finalize_requested_status = "completed_time_limit"
                    finalize_drain_started = now
                    last_serial_data_at = now
                    record_event(
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
                        if detections:
                            finalize_requested_status = "completed_by_operator"
                        elif any(
                            item.get("protocol_status") == "calibration_rejected"
                            for item in protocol_session_records(protocol_state)
                        ):
                            # Host nije automatski prekinuo na K1: ostao je
                            # spreman za novu sesiju. Ako operater ipak zavrsi
                            # run bez DET-a, zatvoreni K1 ishod ostaje tacan
                            # completion status, ali nikad nije fizicka metrika.
                            finalize_requested_status = "completed_calibration_rejected"
                        else:
                            finalize_requested_status = "aborted_before_detection"
                        finalize_drain_started = time.monotonic()
                        last_serial_data_at = finalize_drain_started
                        record_event(
                            kind="session", label="stop", note=rest,
                        )
                        break
                    if verb == "abort":
                        status = "aborted_by_operator"
                        record_event(
                            kind="session", label="abort", note=rest,
                        )
                        break
                    if verb in ("press", "hold", "guided25"):
                        # Virtuelni taster: isti ulaz kao fizicki pritisak, samo
                        # preko konzole (firmware/main/asd_cmd.c). Postoji da bi
                        # se protokol mogao izvesti dok taster nije zalemljen.
                        # Uredjaj na pritisak odgovara `VBUTTON` pa `BUTTON`
                        # zapisom, tako da dokaz ostaje u telemetriji, a ne samo
                        # u host logu.
                        wire = {"press": b"PRESS\n", "hold": b"HOLD\n",
                                "guided25": b"GUIDED25\n"}[verb]
                        try:
                            ser.write(wire)
                            ser.flush()
                        except serial.SerialException as exc:
                            print(f"slanje komande nije uspjelo: {exc}")
                            record_event(
                                kind="command_error", label=verb, note=str(exc),
                            )
                            continue
                        record_event(
                            kind="virtual_button", label=verb, note=rest,
                        )
                    elif verb == "note" and rest:
                        record_event(
                            kind="note", label="operator", note=rest,
                        )
                    elif verb == "condition" and rest:
                        try:
                            normalized, note = parse_condition_command(rest)
                        except ValueError as exc:
                            print(f"nevalidna condition komanda: {exc}")
                            record_event(
                                kind="command_error", label="condition", note=str(exc),
                            )
                            continue
                        current_condition = normalized
                        condition_confirmed = True
                        transition_window_pending = True
                        record_event(
                            kind="condition", label=current_condition, note=note,
                        )
                    else:
                        print("nepoznata komanda; koristi press, hold, guided25, "
                              "condition, note ili stop")
                if status == "aborted_by_operator":
                    break

                if drain_started is not None:
                    remaining = TERMINAL_DRAIN_TIMEOUT_S - (time.monotonic() - drain_started)
                    desired_timeout = max(0.01, min(0.10, remaining))
                elif finalize_drain_started is not None:
                    desired_timeout = 0.05
                else:
                    desired_timeout = 1
                apply_serial_timeout(ser, desired_timeout)
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

                if VWORKFLOW_ACCEPTED_RE.search(line):
                    guided_workflow_pending = True
                guided_capability_seen = (
                    guided_capability_seen or bool(GUIDED_CAPABILITY_RE.search(line)))

                parsed = parse_serial_line(line)
                invalid_before = protocol_state["invalid_status"]
                if parsed and parsed["kind"] in {"FEATURE96", "SUBSEG96"}:
                    telemetry_counts[parsed["kind"]] += 1
                    research_consume_record(
                        research_state, parsed,
                        active_session=int(protocol_state.get("firmware_session_index", 0)),
                        pending_det_quality=protocol_state.get("pending_det_quality"),
                    )
                elif (
                    parsed and parsed["kind"] == "PARSE_ERROR"
                    and parsed.get("record_kind") in {"FEATURE96", "SUBSEG96"}
                ):
                    research_consume_record(
                        research_state, parsed,
                        active_session=int(protocol_state.get("firmware_session_index", 0)),
                    )
                    parse_error_writer.writerow({
                        "host_utc": host_utc,
                        "elapsed_s": elapsed,
                        "firmware_session_index": protocol_state.get(
                            "firmware_session_index", 0,
                        ),
                        "record_kind": parsed["record_kind"],
                        "reason": parsed["reason"],
                        "raw_line": parsed["raw_line"],
                    })
                    parse_error_handle.flush()
                elif parsed and parsed["kind"] == "QUALITY":
                    protocol_state = transition_firmware_protocol(protocol_state, parsed)
                    telemetry_counts["QUALITY"] += 1
                    if protocol_state["invalid_status"] is None:
                        research_expect_quality(
                            research_state, parsed,
                            session=int(protocol_state.get("firmware_session_index", 0)),
                        )
                    row = {
                        "host_utc": host_utc,
                        "elapsed_s": elapsed,
                        "firmware_session_index": protocol_state.get(
                            "firmware_session_index", 0,
                        ),
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
                        "firmware_session_index": protocol_state.get(
                            "firmware_session_index", 0,
                        ),
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
                        "firmware_session_index": protocol_state.get(
                            "firmware_session_index", 0,
                        ),
                        **{key: parsed[key] for key in FIRMWARE_EVENT_FIELDS if key in parsed},
                    }
                    firmware_event_writer.writerow(row)
                    firmware_event_handle.flush()
                elif parsed and parsed["kind"] in (
                    "SESSION", "BUTTON", "PRESENCE", "TEMPORAL", "INTERFERENCE", "THRFIT", "PROFILESTORE",
                    "COMMISSION", "PROFILE",
                ):
                    protocol_state = transition_firmware_protocol(protocol_state, parsed)
                    telemetry_counts[parsed["kind"]] += 1
                    if parsed["kind"] == "SESSION" and parsed["action"] == "STARTED":
                        guided_workflow_accepted = guided_workflow_pending
                        guided_workflow_pending = False
                        guided_capability_seen = False
                        dropped_observed = False
                        current_condition = "unconfirmed"
                        condition_confirmed = False
                        transition_window_pending = False
                    if parsed["kind"] in ("SESSION", "BUTTON"):
                        operator_writer.writerow({
                            "host_utc": host_utc,
                            "elapsed_s": elapsed,
                            "firmware_session_index": protocol_state.get(
                                "firmware_session_index", 0,
                            ),
                            **{key: parsed[key] for key in OPERATOR_FIELDS
                               if key in parsed},
                            "kind": parsed["kind"],
                        })
                        operator_handle.flush()
                elif parsed and parsed["kind"] == "PARSE_ERROR":
                    protocol_state = transition_firmware_protocol(protocol_state, parsed)
                    parse_error_writer.writerow({
                        "host_utc": host_utc,
                        "elapsed_s": elapsed,
                        "firmware_session_index": protocol_state.get(
                            "firmware_session_index", 0,
                        ),
                        "record_kind": parsed["record_kind"],
                        "reason": parsed["reason"],
                        "raw_line": parsed["raw_line"],
                    })
                    parse_error_handle.flush()
                elif parsed and parsed["kind"] == "ADAPTTHR":
                    protocol_state = transition_firmware_protocol(protocol_state, parsed)
                elif parsed and parsed["kind"] == "DROPPED":
                    dropped_observed = True
                    dropped = int(parsed["dropped"])
                    max_dropped = dropped if max_dropped is None else max(max_dropped, dropped)
                elif parsed and parsed["kind"] == "DET":
                    protocol_state = transition_firmware_protocol(protocol_state, parsed)
                    if protocol_state["invalid_status"] is None:
                        research_note_det(
                            research_state, parsed,
                            session=int(protocol_state.get("firmware_session_index", 0)),
                        )
                    row = {
                        "host_utc": host_utc,
                        "elapsed_s": elapsed,
                        "firmware_session_index": protocol_state.get(
                            "firmware_session_index", 0,
                        ),
                        "run_det_index": protocol_state.get("run_det_records", 0),
                        "condition": current_condition,
                        "condition_confirmed": int(condition_confirmed),
                        "transition_window": int(transition_window_pending),
                        "protocol_valid": int(protocol_state["invalid_status"] is None),
                        **{key: parsed[key] for key in det_fields if key in parsed},
                    }
                    detections.append(row)
                    det_writer.writerow(row)
                    det_handle.flush()
                    transition_window_pending = False

                # I validan K1 reject je terminalni drain. Ne prekidamo nakon
                # STATE/FLOW_STOPPED para: firmware mora zatvoriti isti otvoreni
                # SESSION sa ENDED, a čekanje je ograničeno timeoutom iznad.
                if protocol_state["drain_required"] and drain_started is None:
                    drain_started = time.monotonic()

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
                            "firmware_session_index": protocol_state.get(
                                "firmware_session_index", 0,
                            ),
                            "record_kind": parsed["kind"],
                            "reason": protocol_state["invalid_reason"],
                            "raw_line": line,
                        })
                        parse_error_handle.flush()
                    if newly_invalid:
                        record_event(
                            kind="protocol", label=status,
                            note=str(protocol_state["invalid_reason"]),
                        )
                    if protocol_state["drain_required"]:
                        decision = terminal_drain_decision(
                            protocol_state, time.monotonic() - drain_started,
                        )
                        if decision == "complete":
                            record_event(
                                kind="protocol", label="terminal_drain_complete",
                                note="terminal STATE/FLOW_STOPPED sacuvani",
                            )
                            break
                        continue
                    break

                if protocol_state["drain_required"]:
                    decision = terminal_drain_decision(
                        protocol_state, time.monotonic() - drain_started,
                    )
                    if decision != "complete":
                        continue
                    record_event(
                        kind="protocol", label="terminal_drain_complete",
                        note="terminal STATE/FLOW_STOPPED/SESSION ENDED sacuvani",
                    )

                if firmware_protocol_calibration_rejected(protocol_state):
                    record_event(
                        kind="calibration", label="rejected",
                        note=(
                            f"session={protocol_state['firmware_session_index']}; "
                            "UNSTABLE_CALIBRATION; K1 loo_cv_above_max; "
                            "host ostaje aktivan za novu sesiju"
                        ),
                    )
                    protocol_state["drain_required"] = False
                    drain_started = None
                    continue

                if "KALIBRACIJA:" in line:
                    record_event(
                        kind="phase", label="calibration",
                        note="fan mora ostati u potvrđeno normalnom stanju",
                    )
                if "DETEKCIJA RADI" in line:
                    record_event(
                        kind="phase", label="detection",
                        note="firmware DET faza; operator condition i dalje nije potvrđen"
                        if not condition_confirmed else
                        f"firmware DET faza; operator condition={current_condition}",
                    )
        except KeyboardInterrupt:
            status = "interrupted_by_operator"
            record_event(
                kind="session", label="interrupt", note="KeyboardInterrupt",
            )
        except Exception as exc:
            status = "failed"
            record_event(
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
            condition_protocol_detections = [
                row for row in detections
                if int(row.get("condition_confirmed", 0)) == 1
                and int(row.get("protocol_valid", 0)) == 1
                and int(row.get("transition_window", 0)) == 0
            ]
            protocol_valid_detections = [
                row for row in detections if int(row.get("protocol_valid", 0)) == 1
            ]
            metadata["external_wav_sha256_at_end"] = (
                sha256_file(Path(args.wav_path)) if args.wav_path else None
            )
            research_manifest = write_research_artifact(
                run_dir, research_state, metadata=metadata,
            )
            if status.startswith("completed"):
                if (
                    not firmware_protocol_complete(protocol_state)
                ):
                    status = "invalid_missing_telemetry"
                    protocol_state["invalid_status"] = status
                    protocol_state["invalid_reason"] = "session_completed_before_required_protocol"
                elif protocol_state.get("run_det_records", 0) != len(protocol_valid_detections):
                    status = "invalid_firmware_telemetry"
                    protocol_state["invalid_status"] = status
                    protocol_state["invalid_reason"] = "tracker_detection_csv_count_mismatch"
                elif (
                    firmware_calibration_source_accepted(protocol_state)
                    and not condition_protocol_detections
                ):
                    status = "invalid_no_confirmed_operator_condition"
                elif (
                    args.research_telemetry_required
                    and not research_manifest["gate_passed"]
                ):
                    status = "invalid_research_telemetry"
            final_validity = evaluate_run_validity(
                status=status, detections=detections, protocol_state=protocol_state,
            )
            metric_detections = final_validity["metric_detections"]
            run_metrics = final_validity["run_metrics"]
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
                "run_det_records": final_validity["run_det_records"],
                "run_quality_counts": protocol_state.get("run_quality_counts", {}),
                "firmware_sessions": final_validity["sessions"],
                "condition_protocol_det_window_count": len(condition_protocol_detections),
                "valid_det_window_count": len(metric_detections),
                "metrics_eligible_det_window_count": len(metric_detections),
                "alarm_window_count": run_metrics["alarm_window_count"],
                "alarm_entry_count": run_metrics["alarm_entries"],
                "alarm_episode_count": run_metrics["alarm_episodes"],
                "alarm_time_percent": run_metrics["alarm_time_percent"],
                "recovery_latency_s": run_metrics["recovery_latency_s"],
                "excluded_transition_window_count": sum(
                    item["excluded_transition_windows"]
                    for item in final_validity["sessions"]
                ),
                "physical_result_status": final_validity["result_status"],
                "protocol_valid": final_validity["protocol_valid"],
                "calibration_accepted": final_validity["calibration_accepted"],
                "calibration_acceptance_reason": final_validity["calibration_acceptance_reason"],
                "metrics_eligible": final_validity["metrics_eligible"],
                "commissioning_policy": COMMISSIONING_POLICY_RECORD,
                "max_dropped": max_dropped,
                "dropped_observed": dropped_observed,
                "guided_workflow_accepted": guided_workflow_accepted,
                "guided_capability_seen": guided_capability_seen,
                "firmware_telemetry_counts": telemetry_counts,
                "research_telemetry": research_manifest,
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
            if getattr(args, "guided_workflow", "none") == "guided25":
                guided_report = evaluate_guided25_artifact(
                    provenance=provenance,
                    detections=detections,
                    research_manifest=research_manifest,
                    workflow_accepted=(guided_workflow_accepted and guided_capability_seen),
                    dropped_observed=dropped_observed,
                    events=events,
                )
                write_json(run_dir / "guided25_report.json", guided_report)
            if serial_close_error is not None:
                raise serial_close_error

    if stack.close_error is not None:
        _best_effort_finalize_setup_failure(
            run_dir, provenance, metadata, stack.close_error,
        )
        raise stack.close_error

    assert final_validity is not None
    print(
        f"run zavrsen sa statusom {status}; "
        f"fizicki rezultat={final_validity['result_status']}: {run_dir}"
    )
    return 0 if (final_validity["valid_result"] and
                 (guided_report is None or guided_report["status"] == "PASS")) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight", help="provjeri port i postojeci PSD build")
    preflight.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    preflight.set_defaults(func=record_preflight)

    recompute = sub.add_parser(
        "recompute", help="napravi novi summary sidecar bez izmjene originalnog runa",
    )
    recompute.add_argument("--run-dir", type=Path, required=True)
    recompute.add_argument("--output-name", default="SUMMARY.recomputed.md")
    recompute.set_defaults(func=recompute_summary_command)

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
                     help=("opciona veza ka WAV-u koji snima nezavisni recorder; "
                           "ovaj alat ga ne snima"))
    run.add_argument(
        "--research-telemetry-required", action="store_true",
        help=("fail-closed zahtijevaj FEATURE96 + pet SUBSEG96 zapisa za svaki "
              "validni CAL/DET prozor"),
    )
    run.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    run.add_argument("--command-file", default=None,
                     help="opciona datoteka; alat cita komande koje se dopisuju tokom runa")
    run.add_argument("--ready", action="store_true",
                     help="eksplicitna potvrda sigurnosti; preskace DA prompt")
    run.add_argument("--no-reset", action="store_true")
    run.add_argument("--non-interactive", action="store_true",
                     help="bez rucnih oznaka; obavezno kombinovati sa --max-seconds")
    run.add_argument("--max-seconds", type=float, default=None)
    run.add_argument("--guided-workflow", choices=("none", "guided25"), default="none")
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
