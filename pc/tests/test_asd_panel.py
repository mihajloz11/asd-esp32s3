from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import threading
import time

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "pc" / "tools" / "asd_panel.py"
SPEC = importlib.util.spec_from_file_location("asd_panel", MODULE_PATH)
assert SPEC and SPEC.loader
panel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(panel)


class RecordingLink:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def send_raw(self, line: str) -> str:
        self.lines.append(line)
        return line

    def send(self, verb: str) -> str:
        self.lines.append(verb)
        return verb

    def arm_guided25(self) -> str:
        self.lines.append("GUIDED25")
        return "armed"


def _flags(*, learning: int) -> str:
    return (
        "FLAGS protocol=asd-quality-v1.4.0 mode=LEARNING state=NO_MACHINE "
        f"waiting=0 learning={learning} learned=0 anomaly=0 fault=0 "
        "green=blink_5hz red=off"
    )


def test_new_learning_clears_stale_calibration_display() -> None:
    state = panel.PanelState(panel.PLANS["short"])
    state.flags = {"learning": "0"}
    state.loo_cv = 0.2
    state.threshold = 123.0
    state.det = {"window": "9", "score": "500"}
    state.calibration_accepted = True
    state.calibration_acceptance_reason = "accepted"

    state.feed(_flags(learning=1))

    assert state.stage == "CAL"
    assert state.loo_cv is None
    assert state.threshold is None
    assert state.det == {}
    assert state.calibration_accepted is False
    assert state.calibration_acceptance_reason == "missing_cal_summary"


def test_server_side_start_rejects_k1_bypass() -> None:
    state = panel.PanelState(panel.PLANS["short"])
    state.stage = "READY_TO_GO"
    state.loo_cv = 0.600001
    link = RecordingLink()
    conductor = panel.Conductor(state, link)

    with pytest.raises(panel.CalibrationGateError, match="loo_cv_above_max"):
        conductor.start()

    assert conductor.thread is None
    assert link.lines == []


def test_http_start_endpoint_returns_conflict_when_k1_failed() -> None:
    state = panel.PanelState(panel.PLANS["short"])
    state.stage = "READY_TO_GO"
    state.loo_cv = 0.600001
    link = RecordingLink()
    conductor = panel.Conductor(state, link)
    handler_type = panel.make_handler(state, link, conductor)
    handler = object.__new__(handler_type)
    handler.path = "/start"
    response: dict = {}
    handler._json = lambda payload, code=200: response.update(  # type: ignore[method-assign]
        payload=payload, code=code,
    )

    handler.do_POST()

    assert response["code"] == 409
    assert "loo_cv_above_max" in response["payload"]["message"]
    assert link.lines == []


def test_bad_summary_stays_rejected_even_if_adaptthr_arrives() -> None:
    state = panel.PanelState(panel.PLANS["short"])
    state.feed(_flags(learning=1))
    state.feed(
        "QUALITY protocol=asd-quality-v1.4.0 phase=CAL_SUMMARY "
        "result=OBSERVED loo_mean=1 loo_sd=1 loo_cv=0.600001 "
        "loo_range=2 loo_gate=pending_normal_only"
    )
    state.feed("ADAPTTHR n=10 mean=1 sd=1 k=0 theta=0 p=.99 thr=4 lo=0 factory=0")

    assert state.stage == "CAL_REJECTED"
    assert state.calibration_accepted is False
    assert state.calibration_acceptance_reason == "loo_cv_above_max"


def test_http_guided25_virtual_and_physical_start_have_server_side_parity(tmp_path) -> None:
    def invoke(path: str) -> list[str]:
        state = panel.PanelState(panel.PLANS["guided25"], workflow="guided25",
                                 report_dir=tmp_path)
        state.feed("FLAGS protocol=asd-quality-v1.5.0 waiting=1 guided25_available=1 "
                   "research_telemetry=1 profile_persistence_allowed=0 dropped=0")
        link = RecordingLink()
        conductor = panel.Conductor(state, link)
        handler_type = panel.make_handler(state, link, conductor)
        handler = object.__new__(handler_type)
        handler.path = path
        handler._json = lambda payload, code=200: None
        handler.do_POST()
        return link.lines

    assert invoke("/arm-virtual") == ["GUIDED25", "press"]
    assert invoke("/arm-physical") == ["GUIDED25"]


def test_http_guided25_rejects_stale_or_wrong_firmware(tmp_path) -> None:
    state = panel.PanelState(panel.PLANS["guided25"], workflow="guided25",
                             report_dir=tmp_path)
    state.feed("FLAGS protocol=asd-quality-v1.5.0 waiting=1 guided25_available=0 "
               "research_telemetry=1 profile_persistence_allowed=0 dropped=0")
    link = RecordingLink()
    conductor = panel.Conductor(state, link)
    handler_type = panel.make_handler(state, link, conductor)
    handler = object.__new__(handler_type)
    handler.path = "/arm-virtual"
    response = {}
    handler._json = lambda payload, code=200: response.update(payload=payload, code=code)
    handler.do_POST()
    assert response["code"] == 409
    assert "firmware nema GUIDED25" in response["payload"]["message"]
    assert link.lines == []


def test_monitoring_gate_rechecks_fresh_capability_and_dropped(tmp_path) -> None:
    state = panel.PanelState(panel.PLANS["guided25"], workflow="guided25",
                             report_dir=tmp_path)
    state.last_line_at = time.time() - 16
    state.flags = {"protocol": "asd-quality-v1.5.0", "guided25_available": "1",
                   "learning": "0", "learned": "1"}
    state.workflow_result = "accepted"; state.calibration_accepted = True
    state.profile_counts = (44, 22); state.research_counts = {"FEATURE96": 1, "SUBSEG96": 5}
    ok, reasons = state.guided_monitoring_gate()
    assert not ok and "telemetrija nije svjeza" in reasons
    assert "DROPPED=0 nije potvrdjen" in reasons


def test_abort_stops_conductor_without_late_stop_or_report_overwrite(tmp_path) -> None:
    state = panel.PanelState([("x", "normal_baseline", 1, "wait")],
                             report_dir=tmp_path)
    state.started_at = time.monotonic(); state.stage = "RUN"
    link = RecordingLink(); conductor = panel.Conductor(state, link)
    conductor.thread = threading.Thread(
        target=conductor._run, args=(state.session_generation,), daemon=True)
    conductor.thread.start(); time.sleep(0.03)
    conductor.abort("test_abort")
    time.sleep(1.05)
    assert "abort test_abort" in link.lines
    assert not any(line.startswith("stop ") for line in link.lines)
    assert not (tmp_path / "guided25_report.json").exists()


def test_retry_after_done_gets_new_generation_and_fresh_watchdog(tmp_path) -> None:
    state = panel.PanelState(panel.PLANS["guided25"], workflow="guided25",
                             report_dir=tmp_path)
    state.session_generation = 1; state.stage = "DONE"
    state.flags = {"protocol": "asd-quality-v1.5.0", "guided25_available": "1",
                   "waiting": "1", "research_telemetry": "1",
                   "profile_persistence_allowed": "0"}
    state.last_line_at = time.time(); state.dropped_observed = True
    link = RecordingLink(); conductor = panel.Conductor(state, link)
    conductor.stop_event.set()
    conductor.arm_guided25(virtual_start=False)
    state.pending_workflow_accepted = True
    state.feed("SESSION protocol=asd-quality-v1.5.0 action=STARTED source=BUTTON "
               "reason=OPERATOR_REQUEST discards_calibration=0")
    time.sleep(0.08)
    assert state.session_generation == 2 and state.stage == "CAL"
    assert state.started_at is None and state.phase_index == -1
    assert state.final_result is None
    assert not any(line.startswith("abort guided25_hard_deadline") for line in link.lines)
    conductor.stop_event.set()


def test_confirmations_are_single_use_and_bound_to_current_phase_order(tmp_path) -> None:
    state = panel.PanelState(panel.PLANS["guided25"], workflow="guided25",
                             report_dir=tmp_path)
    state.stage = "RUN"; state.phase_index = 1
    link = RecordingLink(); conductor = panel.Conductor(state, link)
    with pytest.raises(panel.CalibrationGateError, match="END prije START"):
        conductor.confirm("end")
    conductor.confirm("start")
    with pytest.raises(panel.CalibrationGateError, match="single-use"):
        conductor.confirm("start")
    conductor.confirm("end")
    with pytest.raises(panel.CalibrationGateError, match="single-use"):
        conductor.confirm("end")
    assert len(state.operator_confirmations) == 2
    assert "phase=airflow_change_paper_1 edge=start" in link.lines[0]
    assert "phase=airflow_change_paper_1 edge=end" in link.lines[1]


def test_post_rejects_bad_origin_host_or_csrf() -> None:
    state = panel.PanelState(panel.PLANS["short"])
    link = RecordingLink(); conductor = panel.Conductor(state, link)
    handler_type = panel.make_handler(state, link, conductor, "secret")
    handler = object.__new__(handler_type)
    handler.path = "/press"
    handler.server = SimpleNamespace(server_address=("127.0.0.1", 8772))
    handler.headers = {"Host": "evil.example", "Origin": "http://evil.example",
                       "X-CSRF-Token": "wrong"}
    response = {}
    handler._json = lambda payload, code=200: response.update(payload=payload, code=code)
    handler.do_POST()
    assert response["code"] == 403 and link.lines == []


def test_read_only_preview_blocks_every_command_server_side() -> None:
    state = panel.PanelState(
        panel.PLANS["guided25"], workflow="guided25", read_only_preview=True,
    )
    link = RecordingLink()
    handler_type = panel.make_handler(state, link, panel.Conductor(state, link))
    handler = object.__new__(handler_type)
    handler.path = "/hold"
    response = {}
    handler._json = lambda payload, code=200: response.update(payload=payload, code=code)

    handler.do_POST()

    assert response == {
        "payload": {"message": "read-only preview: komande su blokirane"},
        "code": 409,
    }
    assert link.lines == []
    assert state.snapshot()["read_only_preview"] is True
    assert "document.querySelectorAll('button')" in panel.PAGE


@pytest.mark.parametrize("wire_value", ["nan", "inf", "-inf"])
def test_panel_rejects_nonfinite_calibration_without_storing_or_emitting_it(
    wire_value: str,
) -> None:
    state = panel.PanelState(panel.PLANS["short"])
    state.feed(_flags(learning=1))
    state.feed(
        "QUALITY protocol=asd-quality-v1.4.0 phase=CAL_SUMMARY "
        f"result=OBSERVED loo_mean=1 loo_sd=1 loo_cv={wire_value} "
        "loo_range=2 loo_gate=pending_normal_only"
    )
    state.feed("ADAPTTHR n=10 mean=1 sd=1 k=0 theta=0 p=.99 thr=inf lo=0 factory=0")

    snapshot = state.snapshot()
    assert state.loo_cv is None
    assert state.threshold is None
    assert snapshot["loo_cv"] is None
    assert snapshot["threshold"] is None
    assert snapshot["stage"] == "CAL_REJECTED"
    assert snapshot["calibration_accepted"] is False
    assert snapshot["calibration_acceptance_reason"] == "nonfinite_loo_cv"
    assert "s.calibration_acceptance_reason" in panel.PAGE

    # I direktni strict encoder i stvarni HTTP helper moraju proizvesti
    # standardni JSON bez NaN/Infinity literala.
    json.dumps(snapshot, allow_nan=False)
    handler_type = panel.make_handler(state, RecordingLink(), panel.Conductor(state, RecordingLink()))
    handler = object.__new__(handler_type)
    handler.send_response = lambda _code: None  # type: ignore[method-assign]
    handler.send_header = lambda _key, _value: None  # type: ignore[method-assign]
    handler.end_headers = lambda: None  # type: ignore[method-assign]
    handler.wfile = io.BytesIO()
    handler._json(snapshot)
    encoded = handler.wfile.getvalue()
    assert b"NaN" not in encoded
    assert b"Infinity" not in encoded
    assert json.loads(encoded)["calibration_acceptance_reason"] == "nonfinite_loo_cv"
