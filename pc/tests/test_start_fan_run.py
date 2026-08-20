from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "pc" / "tools" / "start_fan_run.py"
SPEC = importlib.util.spec_from_file_location("start_fan_run", MODULE_PATH)
assert SPEC and SPEC.loader
start_fan_run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(start_fan_run)


def test_mount_confirmation_is_routed_to_operator_notes_not_events_claim() -> None:
    args = argparse.Namespace(
        port="COM3",
        fan_id="fan01",
        session_id="two-session-01",
        distance_cm="20",
        angle_deg="90",
        room="soba",
        fan_speed_or_voltage="usb-5v-punjac",
        montaza_potvrdio="Mihajlo; ventilator je bezbjedno montiran",
    )
    command_file = ROOT / "results" / "physical_fan" / "cmd_fan01.txt"

    command = start_fan_run.build_tool_command(
        args, python="python.exe", command_file=command_file,
    )

    notes_index = command.index("--notes")
    assert command[notes_index + 1] == (
        "montazu potvrdio: Mihajlo; ventilator je bezbjedno montiran"
    )
    assert "--ready" in command
    assert "metadata.operator_notes" in (start_fan_run.__doc__ or "")
    assert "To nije\n`events.csv` typed event" in (start_fan_run.__doc__ or "")


def test_research_required_flag_is_forwarded_only_when_requested() -> None:
    base = dict(
        port="COM3", fan_id="fan01", session_id="research-01",
        distance_cm="20", angle_deg="90", room="soba",
        fan_speed_or_voltage="usb-5v-punjac", montaza_potvrdio="Mihajlo",
    )
    command_file = ROOT / "results" / "physical_fan" / "cmd_fan01.txt"
    without = start_fan_run.build_tool_command(
        argparse.Namespace(**base, research_telemetry_required=False),
        python="python.exe", command_file=command_file,
    )
    with_required = start_fan_run.build_tool_command(
        argparse.Namespace(**base, research_telemetry_required=True),
        python="python.exe", command_file=command_file,
    )
    assert "--research-telemetry-required" not in without
    assert with_required[-1] == "--research-telemetry-required"


def test_fan_and_session_ids_are_both_explicit_and_never_default_to_fan01() -> None:
    parser = start_fan_run.build_parser()
    common = ["--montaza-potvrdio", "Mihajlo"]
    with pytest.raises(SystemExit):
        parser.parse_args(["--session-id", "new-session", *common])
    with pytest.raises(SystemExit):
        parser.parse_args(["--fan-id", "fan02", *common])
    parsed = parser.parse_args([
        "--fan-id", "fan02", "--session-id", "new-session", *common,
    ])
    assert (parsed.fan_id, parsed.session_id) == ("fan02", "new-session")
    assert parsed.no_browser is False


def test_existing_unique_command_file_is_preserved_fail_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(start_fan_run, "RESULTS", tmp_path)
    monkeypatch.setattr(start_fan_run, "panel_port_busy", lambda _port: False)
    path = tmp_path / "cmd_fan02_s01_attempt1.txt"
    path.write_text("old evidence\n", encoding="utf-8")
    rc = start_fan_run.main([
        "--fan-id", "fan02", "--session-id", "s01", "--attempt", "1",
        "--montaza-potvrdio", "Mihajlo",
    ])
    assert rc == 2
    assert path.read_text(encoding="utf-8") == "old evidence\n"


def test_guided_start_forces_research_and_registered_workflow() -> None:
    args = start_fan_run.build_parser().parse_args([
        "--fan-id", "fan02", "--session-id", "s01",
        "--montaza-potvrdio", "Mihajlo",
    ])
    command = start_fan_run.build_tool_command(
        args, python="python.exe", command_file=Path("cmd.txt"))
    assert "--research-telemetry-required" in command
    assert command[-2:] == ["--guided-workflow", "guided25"]
