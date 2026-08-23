"""Versioned, preregistered policy for the <=25 minute DEVELOPMENT run."""
from __future__ import annotations

import json
import re
from datetime import datetime
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
    if total > int(policy["hard_deadline_seconds"]):
        raise ValueError(f"guided25 schedule is {total}s, over hard deadline")
    if [p["condition"] for p in phases] != list(dict.fromkeys(p["condition"] for p in phases)):
        raise ValueError("guided25 condition labels must be unique")
    policy["worst_case_seconds"] = total
    return policy


GUIDED25 = load_guided25()
GUIDED25_PLAN = [
    (p["name"], p["condition"], int(p["seconds"]), p["prompt"])
    for p in GUIDED25["phases"]
]


CONFIRM_RE = re.compile(
    r"^guided25_confirm phase=(?P<phase>[A-Za-z0-9._-]+) "
    r"edge=(?P<edge>start|end) host_utc=(?P<utc>\S+)$")


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

    # POTVRDE VISE NISU KAPIJA, i to je namjerna izmjena od 23.08.2026.
    #
    # Klik u pretrazivacu nije nezavisan dokaz da se fizicka radnja desila --
    # dokazuje samo da je neko kliknuo. Isto vazi za raspored: on je tvrdnja o
    # namjeri. Vezati PASS/FAIL za nesto sto se ne moze provjeriti dodaje
    # ceremoniju, ne strogost, a izmjereno je da kosta cijele runove: 23.08. je
    # operater kliknuo START za svih deset faza, ali END ni za jednu, jer se END
    # trazi dok obje ruke drze papiric uz ventilator.
    #
    # Sta OSTAJE strogo: potvrda koja POSTOJI mora biti vjerodostojna. Krivotvoren
    # ili ispremjestan zapis i dalje obara run, jer je to lazan zapis, a ne
    # nedostatak zapisa. Broj potvrda ide u izvjestaj kao `operator_marks`, pa se
    # kvalitet dokaza vidi umjesto da se pretpostavlja.
    required_phases = [p["condition"] for p in GUIDED25["phases"]
                       if p["condition"] != "normal_baseline"]
    observed_confirms: list[tuple[str, str]] = []
    previous_confirmation_at: datetime | None = None
    confirmation_invalid = False
    for event in events or []:
        if event.get("kind") != "note":
            continue
        note = str(event.get("note", ""))
        if not note.startswith("guided25_confirm "):
            continue
        match = CONFIRM_RE.fullmatch(note)
        if not match:
            confirmation_invalid = True
            continue
        try:
            claimed = datetime.fromisoformat(match.group("utc"))
            persisted = datetime.fromisoformat(str(event["host_utc"]))
        except (KeyError, ValueError):
            confirmation_invalid = True
            continue
        if claimed.tzinfo is None or persisted.tzinfo is None or persisted < claimed:
            confirmation_invalid = True
        if (persisted - claimed).total_seconds() > 5.0:
            confirmation_invalid = True
        if previous_confirmation_at is not None and persisted <= previous_confirmation_at:
            confirmation_invalid = True
        previous_confirmation_at = persisted
        observed_confirms.append((match.group("phase"), match.group("edge")))
    marked_phases = {phase for phase, _ in observed_confirms}
    order = {phase: index for index, phase in enumerate(required_phases)}
    if marked_phases - set(required_phases):
        confirmation_invalid = True            # oznaka za fazu koja ne postoji
    else:
        # Oznake smiju da nedostaju, ali ne smiju da idu unazad kroz plan, i
        # nijedna faza ne smije poceti sa `end` -- to bi bio zapis o radnji koja
        # nije zapoceta.
        indices = [order[phase] for phase, _ in observed_confirms]
        if any(later < earlier
               for earlier, later in zip(indices, indices[1:])):
            confirmation_invalid = True
        first_edge: dict[str, str] = {}
        for phase, edge in observed_confirms:
            first_edge.setdefault(phase, edge)
        if any(edge != "start" for edge in first_edge.values()):
            confirmation_invalid = True
    if confirmation_invalid:
        failures.append("operator_confirmations_fake_or_out_of_order")

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
        "operator_marks": f"{len(marked_phases)}/{len(required_phases)}",
        "evaluated_det_windows": len(rows),
        "research_manifest_sha256": sha or None,
        "note": ("Observed single-microphone noise tolerance. Granice kapije "
                 "pouzdanosti su izvedene iz normal-only prozora "
                 "(asd-interference-policy-v2.0.0-development); HOLD odbija "
                 "nepouzdan prozor, ali ne tvrdi sta ga je izazvalo."),
    }
