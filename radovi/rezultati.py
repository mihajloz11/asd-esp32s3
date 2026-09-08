"""Read publication tables from the unchanged physical-run CSV files."""
from __future__ import annotations

import csv
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
RUNS = {
    "paper": "run_20260827T213148_fan02_guided25-20260827-v3recovery5d",
    "tone": "run_20260827T220338_fan02_tone-validation-20260827-final",
}
LABELS = {
    "normal_baseline": "Normalna osnova",
    "airflow_change_paper_1": "Izazvana promjena 1",
    "airflow_change_paper_2": "Izazvana promjena 2",
    "airflow_change_paper_3": "Izazvana promjena 3",
    "recovery_normal_1": "Oporavak 1",
    "recovery_normal_2": "Oporavak 2",
    "recovery_normal_3": "Oporavak 3",
    "ambient_speech": "Razgovor",
    "recovery_after_speech": "Oporavak poslije razgovora",
    "ambient_door": "Vrata",
    "final_recovery": "Završni oporavak",
    "constant_tone_1khz": "Konstantan ton",
    "recovery_after_tone": "Oznaka oporavka poslije tona",
}


def summary(key):
    with (ROOT / "results/physical_fan" / RUNS[key] / "detections.csv").open(
            encoding="utf-8-sig", newline="") as source:
        raw = list(csv.DictReader(source))
    eligible = [r for r in raw if r["protocol_valid"] == "1"
                and r["condition_confirmed"] == "1" and r["transition_window"] == "0"]
    groups = {}
    for condition in dict.fromkeys(r["condition"] for r in eligible):
        rows = [r for r in eligible if r["condition"] == condition]
        scores = [float(r["score"]) for r in rows]
        groups[condition] = dict(n=len(rows), hold=sum(int(r["hold"]) for r in rows),
                                 alarm=sum(int(r["alarm"]) for r in rows),
                                 median=median(scores), low=min(scores), high=max(scores))
    return dict(raw=len(raw), eligible=len(eligible), groups=groups,
                alarm=sum(int(r["alarm"]) for r in eligible))


def number(value):
    return f"{value:,.0f}".replace(",", " ")


def thesis_rows(key):
    rows = []
    for condition, values in summary(key)["groups"].items():
        row = [LABELS[condition], str(values["n"]), str(values["hold"]),
               str(values["alarm"]), number(values["median"])]
        if key == "tone":
            row.append(f"{number(values['low'])} – {number(values['high'])}")
        rows.append(row)
    return rows
