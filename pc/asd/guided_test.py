"""Versioned, preregistered policy for the DEVELOPMENT run."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "pc" / "config" / "guided25_workflow_v1.json"


def load_guided25() -> dict:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    phases = policy["phases"]
    commissioning = policy["commissioning"]
    window = int(policy["window_seconds"])
    worst_commissioning = window * sum(
        int(commissioning[key]) for key in (
            "max_settle_windows", "center_windows", "derive_windows", "verify_windows"
        )
    )
    total = worst_commissioning + sum(int(p["seconds"]) for p in phases)
    guarded_total = total + int(policy["monitoring_start_guard_seconds"])
    hard_deadline = policy.get("hard_deadline_seconds")
    if hard_deadline is not None and guarded_total > int(hard_deadline):
        raise ValueError(
            f"guided25 guarded schedule is {guarded_total}s, over hard deadline"
        )
    if [p["condition"] for p in phases] != list(dict.fromkeys(p["condition"] for p in phases)):
        raise ValueError("guided25 condition labels must be unique")
    policy["worst_case_seconds"] = total
    policy["guarded_worst_case_seconds"] = guarded_total
    return policy


GUIDED25 = load_guided25()
GUIDED25_PLAN = [
    (p["name"], p["condition"], int(p["seconds"]), p["prompt"])
    for p in GUIDED25["phases"]
]


def evaluate_guided25_artifact(*, provenance: dict, detections: list[dict],
                               research_manifest: dict,
                               workflow_accepted: bool,
                               dropped_observed: bool,
                               events: list[dict] | None = None) -> dict:
    """Fail-closed verdict from finalized host artifacts, never live UI state."""
    failures: list[str] = []
    if provenance.get("quality_protocol_version") != "asd-quality-v1.6.0":
        failures.append("quality_protocol_not_q1.6")
    if not workflow_accepted:
        failures.append("guided25_capability_not_accepted")
    if not provenance.get("protocol_valid"):
        failures.append("firmware_protocol_invalid")
    if not provenance.get("calibration_accepted"):
        failures.append("k1_or_commissioning_not_accepted")
    if not dropped_observed or provenance.get("max_dropped") != 0:
        failures.append("missing_or_nonzero_DROPPED")

    runtime = provenance.get("firmware_protocol_state", {}).get(
        "runtime_commissioning", {})
    firmware_state = provenance.get("firmware_protocol_state", {})
    if not firmware_state.get("interference_seen", False):
        failures.append("missing_runtime_normal_only_interference_threshold")
    elif firmware_state.get("interference_source") != "CAL_NORMAL_ONLY":
        failures.append("interference_threshold_not_from_cal_normal_only")
    policy = runtime.get("policy") or {}
    if (int(policy.get("derive_windows", -1)), int(policy.get("verify_windows", -1))) != (44, 22):
        failures.append("commissioning_not_registered_44_22")

    expected = int(research_manifest.get("expected_window_count", -1))
    npz = research_manifest.get("npz") or {}
    sha = str(npz.get("sha256", ""))
    research_ok = (
        research_manifest.get("artifact_valid") is True
        and not research_manifest.get("errors")
        and expected > 0
        and int(research_manifest.get("complete_window_count", -1)) == expected
        and int(research_manifest.get("feature_record_count", -1)) == expected
        and int(research_manifest.get("subsegment_record_count", -1)) == 5 * expected
        and len(sha) == 64 and all(c in "0123456789abcdef" for c in sha.lower())
    )
    if not research_ok:
        failures.append("research_pairs_or_checksum_invalid")

    rows = [row for row in detections
            if int(row.get("condition_confirmed", 0)) == 1
            and int(row.get("protocol_valid", 0)) == 1
            and int(row.get("transition_window", 0)) == 0]
    grouped: dict[str, list[dict]] = {}
    entries: dict[str, int] = {}
    previous_alarm = 0
    for row in rows:
        condition = str(row.get("condition", ""))
        grouped.setdefault(condition, []).append(row)
        alarm = int(row.get("alarm", 0))
        if alarm and not previous_alarm:
            entries[condition] = entries.get(condition, 0) + 1
        previous_alarm = alarm

    paper_pass = 0
    minima = GUIDED25["acceptance"]["minimum_measured_windows"]
    for phase in GUIDED25["phases"]:
        condition = phase["condition"]
        phase_rows = grouped.get(condition, [])
        if condition.startswith("airflow_change_paper_"):
            minimum = int(minima["paper"])
            if len(phase_rows) < minimum:
                failures.append(f"too_few_windows:{condition}")
                continue
            run = 0
            max_run = 0
            for row in phase_rows:
                high = float(row.get("score", 0.0)) > float(row.get("threshold", float("inf")))
                run = run + 1 if high else 0
                max_run = max(max_run, run)
            if max_run >= 3 and entries.get(condition, 0) >= 1:
                paper_pass += 1
            continue
        if condition == "normal_baseline": key = "normal_baseline"
        elif condition == "ambient_speech": key = "ambient_speech"
        elif condition == "ambient_door": key = "ambient_door"
        elif condition == "final_recovery": key = "final_recovery"
        else: key = "recovery"
        if len(phase_rows) < int(minima[key]):
            failures.append(f"too_few_windows:{condition}")
        active = sum(int(r.get("alarm", 0)) for r in phase_rows)
        if active or entries.get(condition, 0):
            failures.append(f"alarm_or_carried_alarm:{condition}")
    if paper_pass < int(GUIDED25["acceptance"]["paper_blocks_required"]):
        failures.append(f"paper_blocks_passed:{paper_pass}/3")

    return {
        "schema_version": GUIDED25["schema_version"],
        "status": "FAIL" if failures else "PASS",
        "failures": failures,
        "paper_blocks_passed": paper_pass,
        "evaluated_det_windows": len(rows),
        "research_manifest_sha256": sha or None,
        "note": ("Observed single-microphone noise tolerance. Granice kapije "
                 "pouzdanosti su izvedene iz normal-only prozora "
                 "(asd-interference-policy-v3.0.0-development); prag se po "
                 "sesiji izvodi samo iz CAL normal-only prozora. HOLD odbija "
                 "nepouzdan prozor, ali ne tvrdi sta ga je izazvalo."),
    }
