from __future__ import annotations

import importlib.util
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[2]


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guided = _module("guided_test", ROOT / "pc" / "asd" / "guided_test.py")
panel = _module("guided_panel", ROOT / "pc" / "tools" / "asd_panel.py")
from asd import runtime_protocol as runtime


class Link:
    def __init__(self): self.lines = []
    def send(self, verb): self.lines.append(verb); return verb
    def send_raw(self, line): self.lines.append(line); return line
    def arm_guided25(self): self.lines.append("GUIDED25"); return "armed"


def test_schedule_is_preregistered_and_under_hard_25_minute_deadline() -> None:
    p = guided.GUIDED25
    assert p["commissioning"] == {
        "max_settle_windows": 8, "center_windows": 10,
        "derive_windows": 44, "verify_windows": 22,
    }
    assert p["worst_case_seconds"] == 1370
    assert p["worst_case_seconds"] <= 1380 < p["hard_deadline_seconds"] == 1500


def test_preflight_requires_fresh_idle_capable_firmware_and_artifact_dir(tmp_path) -> None:
    state = panel.PanelState(panel.PLANS["guided25"], workflow="guided25",
                             report_dir=tmp_path, attempt=1)
    ok, reasons = state.guided_preflight()
    assert not ok and "nema svjeze telemetrije" in reasons
    state.feed("FLAGS protocol=asd-quality-v1.5.0 mode=IDLE state=NO_MACHINE waiting=1 learning=0 "
               "learned=0 anomaly=0 hold=0 fault=0 green=flash_2s red=off "
               "guided25_available=1 workflow_pending=DEFAULT research_telemetry=1 "
               "profile_persistence_allowed=0 dropped=0")
    assert state.guided_preflight() == (True, [])


def test_attempt_four_is_server_side_rejected(tmp_path) -> None:
    state = panel.PanelState(panel.PLANS["guided25"], workflow="guided25",
                             report_dir=tmp_path, attempt=4)
    state.feed("FLAGS protocol=asd-quality-v1.5.0 waiting=1 guided25_available=1 "
               "research_telemetry=1 profile_persistence_allowed=0 dropped=0")
    ok, reasons = state.guided_preflight()
    assert not ok and "dosegnut limit od 3 pokusaja" in reasons


def test_monitoring_start_requires_exact_44_22_and_research(tmp_path) -> None:
    state = panel.PanelState(panel.PLANS["guided25"], workflow="guided25",
                             report_dir=tmp_path)
    state.stage = "READY_TO_GO"; state.loo_cv = 0.3
    state.profile_counts = (120, 60)
    state.research_counts = {"FEATURE96": 1, "SUBSEG96": 1}
    state.flags = {"protocol": "asd-quality-v1.5.0", "guided25_available": "1",
                   "learning": "0", "learned": "1"}
    state.workflow_result = "accepted"; state.dropped_observed = True
    state.calibration_accepted = True; state.last_line_at = __import__("time").time()
    conductor = panel.Conductor(state, Link())
    try:
        conductor.start()
    except panel.CalibrationGateError as exc:
        assert "44/22" in str(exc)
    else:
        raise AssertionError("wrong firmware counts were accepted")


def test_result_is_fail_not_pass_when_paper_is_not_proven(tmp_path) -> None:
    state = panel.PanelState(panel.PLANS["guided25"], workflow="guided25",
                             report_dir=tmp_path)
    state.profile_counts = (44, 22)
    state.research_counts = {"FEATURE96": 1, "SUBSEG96": 5}
    state.confirmed_phases = set(range(len(state.plan)))
    result = state.guided_result()
    assert result["status"] == "FAIL"
    assert any("papiric prosao 0/3" in reason for reason in result["reasons"])


def test_firmware_keeps_default_and_guided_policies_separate() -> None:
    source = (ROOT / "firmware" / "esp32s3_asd" / "main" /
              "asd_commissioning.c").read_text(encoding="utf-8")
    assert "#define DEV_DERIVE_WINDOWS 120u" in source
    assert "#define DEV_VERIFY_WINDOWS 60u" in source
    assert "policy.derive_windows = 44u" in source
    assert "policy.verify_windows = 22u" in source


def test_firmware_uses_preregistered_p99_enter_that_cannot_arm_on_derive() -> None:
    source = (ROOT / "firmware" / "esp32s3_asd" / "main" /
              "psd_live.c").read_text(encoding="utf-8")
    assert "#define COMMISSION_ENTER_QUANTILE 0.99f" in source
    assert "COMMISSION_ENTER_QUANTILE);" in source
    assert "p=%.4f" in source

    # Mirrors firmware percentile_higher. With strict score > threshold,
    # supported DERIVE lengths leave at most one score above p99, so n=3
    # cannot arm on the data used to derive the threshold.
    for count in (44, 120):
        scores = list(range(count))
        threshold = sorted(scores)[math.ceil(0.99 * count) - 1]
        assert sum(score > threshold for score in scores) <= 1


def test_virtual_and_physical_start_share_press_path() -> None:
    source = (ROOT / "firmware" / "esp32s3_asd" / "main" /
              "psd_live.c").read_text(encoding="utf-8")
    assert "event = asd_cmd_take_event()" in source
    assert "asd_ui_command(mode, event)" in source
    assert "gpio_get_level(PIN_BUTTON) == 0" in source


def test_strict_runtime_registers_guided25_without_weakening_default() -> None:
    line = (
        "COMMISSION protocol=asd-quality-v1.5.0 "
        "policy=asd-commissioning-policy-v1.0.0-development developmental=1 "
        "action=STARTED phase=SETTLE index=0 total=8 result=NONE "
        "score_valid=0 score=0 level_dbfs=0 tonalness_proxy=0 feature_drift=0"
    )
    state = runtime.new_runtime_sequence_state()
    runtime.advance_runtime_sequence(state, runtime.parse_runtime_record(line))
    assert state["policy"]["derive_windows"] == 44
    assert runtime.COMMISSIONING["derive_windows"] == 120


def test_literal_guided25_44_22_runtime_sequence_is_strictly_accepted() -> None:
    def commission(action, phase, index, total, score_valid=0):
        return ("COMMISSION protocol=asd-quality-v1.5.0 "
                "policy=asd-commissioning-policy-v1.0.0-development developmental=1 "
                f"action={action} phase={phase} index={index} total={total} result=NONE "
                f"score_valid={score_valid} score={1 if score_valid else 0} "
                "level_dbfs=-40 tonalness_proxy=5 feature_drift=0")
    seq = runtime.RuntimeSequence()
    seq.feed(commission("STARTED", "SETTLE", 0, 8))
    for index in range(1, 5):
        seq.feed(commission("WINDOW", "CENTER_LEARNING" if index == 4 else "SETTLE", index, 8))
    seq.feed(commission("PHASE_ENTERED", "CENTER_LEARNING", 0, 10))
    for index in range(1, 45):
        seq.feed(commission("WINDOW", "COMMISSION_DERIVE", index, 44, 1))
    for index in range(1, 23):
        seq.feed(commission("WINDOW", "MONITORING" if index == 22 else "COMMISSION_VERIFY", index, 22, 1))
    seq.feed("PROFILE protocol=asd-quality-v1.5.0 schema=asd-runtime-profile-v1.0.0-development "
             "policy=asd-commissioning-policy-v1.0.0-development developmental=1 valid=1 "
             "policy_version=1 policy_id=434d5631 center_windows=10 derive_windows=44 "
             "verify_windows=22 level_mean_dbfs=-40 tonalness_reference=5 "
             "threshold_enter=100 threshold_exit=50")
    assert seq.profile is not None


def _finalized_fixture():
    provenance = {
        "quality_protocol_version": "asd-quality-v1.5.0", "protocol_valid": True,
        "calibration_accepted": True, "max_dropped": 0,
        "firmware_protocol_state": {"runtime_commissioning": {"policy": {
            "derive_windows": 44, "verify_windows": 22}}},
    }
    manifest = {
        "artifact_valid": True, "errors": [], "expected_window_count": 100,
        "complete_window_count": 100, "feature_record_count": 100,
        "subsegment_record_count": 500, "npz": {"sha256": "a" * 64},
    }
    rows = []
    for phase in guided.GUIDED25["phases"]:
        cond = phase["condition"]
        count = 4 if cond.startswith("airflow_change_paper_") or cond == "ambient_speech" else 3
        if cond == "ambient_door": count = 2
        for index in range(count):
            paper = cond.startswith("airflow_change_paper_")
            rows.append({"condition": cond, "condition_confirmed": 1,
                         "protocol_valid": 1, "transition_window": 0,
                         "consecutive": min(index + 1, 3) if paper else 0,
                         "score": 200 if paper else 10, "threshold": 100,
                         "alarm": 1 if paper and index == 2 else 0})
    events = []
    at = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    for phase in guided.GUIDED25["phases"]:
        cond = phase["condition"]
        if cond == "normal_baseline":
            continue
        for edge in ("start", "end"):
            stamp = at.isoformat(timespec="milliseconds")
            events.append({"kind": "note", "host_utc": stamp,
                           "note": f"guided25_confirm phase={cond} edge={edge} host_utc={stamp}"})
            at += timedelta(seconds=1)
    return provenance, manifest, rows, events


def test_finalized_report_accepts_one_alarm_window_with_persistent_paper_run() -> None:
    provenance, manifest, rows, events = _finalized_fixture()
    result = guided.evaluate_guided25_artifact(
        provenance=provenance, detections=rows, research_manifest=manifest,
        workflow_accepted=True, dropped_observed=True, events=events)
    assert result["status"] == "PASS"
    assert result["paper_blocks_passed"] == 3


def test_finalized_report_missing_k1_or_research_is_strict_fail() -> None:
    provenance, manifest, rows, events = _finalized_fixture()
    provenance["calibration_accepted"] = False
    manifest["complete_window_count"] = 99
    result = guided.evaluate_guided25_artifact(
        provenance=provenance, detections=rows, research_manifest=manifest,
        workflow_accepted=True, dropped_observed=True, events=events)
    assert result["status"] == "FAIL"
    assert "k1_or_commissioning_not_accepted" in result["failures"]
    assert "research_pairs_or_checksum_invalid" in result["failures"]


def test_finalized_report_rejects_active_or_carried_alarm_during_speech() -> None:
    provenance, manifest, rows, events = _finalized_fixture()
    next(row for row in rows if row["condition"] == "ambient_speech")["alarm"] = 1
    result = guided.evaluate_guided25_artifact(
        provenance=provenance, detections=rows, research_manifest=manifest,
        workflow_accepted=True, dropped_observed=True, events=events)
    assert "alarm_or_carried_alarm:ambient_speech" in result["failures"]


def test_missing_operator_marks_are_recorded_but_do_not_fail_the_run() -> None:
    """Klik nije nezavisan dokaz radnje, pa njegovo odsustvo ne obara mjerenje.

    23.08.2026 je operater kliknuo START za svih deset faza i nijedan END, jer
    se END trazi dok obje ruke drze papiric uz ventilator. Run je tada pao na
    ceremoniji, a ne na mjerenju.
    """
    provenance, manifest, rows, events = _finalized_fixture()
    starts = [item for item in events if "edge=start" in item["note"]]

    for partial in ([], starts, events[:-1]):
        result = guided.evaluate_guided25_artifact(
            provenance=provenance, detections=rows, research_manifest=manifest,
            workflow_accepted=True, dropped_observed=True, events=partial)
        assert "operator_confirmations_fake_or_out_of_order" not in result["failures"]
        assert result["status"] == "PASS"

    empty = guided.evaluate_guided25_artifact(
        provenance=provenance, detections=rows, research_manifest=manifest,
        workflow_accepted=True, dropped_observed=True, events=[])
    assert empty["operator_marks"] == "0/10"
    marked = guided.evaluate_guided25_artifact(
        provenance=provenance, detections=rows, research_manifest=manifest,
        workflow_accepted=True, dropped_observed=True, events=starts)
    assert marked["operator_marks"] == "10/10"


def test_falsified_or_reordered_operator_marks_still_fail_the_run() -> None:
    """Nedostatak zapisa je dozvoljen; lazan zapis nije."""
    provenance, manifest, rows, events = _finalized_fixture()
    end_first = [{**events[0],
                  "note": events[0]["note"].replace("edge=start", "edge=end")},
                 *events[1:]]
    unknown = [{**events[0],
                "note": events[0]["note"].replace(
                    "phase=airflow_change_paper_1", "phase=izmisljena_faza")}]
    for broken in (list(reversed(events)), end_first, unknown):
        result = guided.evaluate_guided25_artifact(
            provenance=provenance, detections=rows, research_manifest=manifest,
            workflow_accepted=True, dropped_observed=True, events=broken)
        assert "operator_confirmations_fake_or_out_of_order" in result["failures"]


def test_paper_high_run_is_local_not_carried_firmware_consecutive() -> None:
    provenance, manifest, rows, events = _finalized_fixture()
    for row in rows:
        if row["condition"].startswith("airflow_change_paper_"):
            row["score"] = 50
            row["consecutive"] = 99
    result = guided.evaluate_guided25_artifact(
        provenance=provenance, detections=rows, research_manifest=manifest,
        workflow_accepted=True, dropped_observed=True, events=events)
    assert result["paper_blocks_passed"] == 0


def test_session_started_resets_stale_guided_evidence(tmp_path) -> None:
    state = panel.PanelState(panel.PLANS["guided25"], workflow="guided25",
                             report_dir=tmp_path)
    state.pending_workflow_accepted = True; state.profile_counts = (44, 22)
    state.research_counts = {"FEATURE96": 7, "SUBSEG96": 35}
    state.dropped_observed = True; state.max_dropped = 9
    state.calibration_accepted = True; state.invalid_reason = "old"
    state.feed("SESSION protocol=asd-quality-v1.5.0 action=STARTED source=BUTTON "
               "reason=OPERATOR_REQUEST discards_calibration=0")
    assert state.workflow_result == "accepted"
    assert state.profile_counts is None and state.research_counts["FEATURE96"] == 0
    assert not state.dropped_observed and state.max_dropped == 0
    assert not state.calibration_accepted and state.invalid_reason is None
