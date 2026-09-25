"""Naknadna analiza obiljezja snimljenih u zavrsnim fizickim probama.

Firmware, model i pragovi se ne mijenjaju. Ulaz su FEATURE96 zapisi iz
`window_features.npz` proba od 27.08. i model iz `psd_model_data.h`.

Tri rezultata:
  1. ponovljena ocjena uredjaja, kao provjera da su model i centar isti;
  2. ocjena sa sirokopojasnim nivoom vracenim na kalibracioni: koliko ocjene
     nosi nivo preko osam praznih traka, a koliko oblik spektra;
  3. odstupanje od centra po traci, po uslovu, i vremenski tok traka oko
     1 kHz i 3 kHz u probi sa tonom.

Pokretanje iz korijena repoa:
    python pc/tools/analyze_trial_features.py --output results/trial_features/2026-09-25
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "firmware/esp32s3_asd/main/psd_model_data.h"
RUNS = {
    "paper": "run_20260827T213148_fan02_guided25-20260827-v3recovery5d",
    "tone": "run_20260827T220338_fan02_tone-validation-20260827-final",
}
EMPTY_FLOOR = -20.0
BAND_EDGES_HZ = 10.0 * 400.0 ** (np.arange(97) / 96)
BAND_CENTERS_HZ = np.sqrt(BAND_EDGES_HZ[:-1] * BAND_EDGES_HZ[1:])
TONE_BANDS_HZ = (1000.0, 3000.0)


def header_array(text: str, name: str) -> np.ndarray:
    body = re.search(name + r"\[[^\]]*\]\s*=\s*\{(.*?)\};", text, re.S).group(1)
    values = re.findall(r"-?\d+(?:\.\d*)?(?:e[-+]?\d+)?f", body)
    return np.array([float(v[:-1]) for v in values], dtype=np.float64)


def empty_bands() -> np.ndarray:
    """Iste granice kao postojeca mapa u `psd_features_c.c`."""
    return np.array([b for b in range(96) if not any(
        BAND_EDGES_HZ[b] <= k * 16000 / 8192 < BAND_EDGES_HZ[b + 1] for k in range(4097))])


class Model:
    def __init__(self):
        text = HEADER.read_text(encoding="utf-8")
        self.mean = header_array(text, "asd_psd_norm_mean")
        self.std = header_array(text, "asd_psd_norm_std")
        self.precision = header_array(text, "asd_psd_precision").reshape(96, 96)
        self.empty = empty_bands()
        self.filled = np.setdiff1d(np.arange(96), self.empty)

    def z(self, feature):
        return (feature - self.mean) / self.std

    def score(self, feature, center):
        d = self.z(feature) - center
        return float(d @ self.precision @ d)

    def level(self, feature):
        """Srednji log10 snage popunjenih traka, iz centriranog obiljezja."""
        offset = EMPTY_FLOOR - feature[self.empty].mean()
        return float((feature[self.filled] + offset).mean())

    def at_level(self, feature, target):
        offset = EMPTY_FLOOR - feature[self.empty].mean()
        power = np.full(96, EMPTY_FLOOR)
        power[self.filled] = feature[self.filled] + offset - (self.level(feature) - target)
        return power - power.mean()


class Session:
    """Jedna proba: obiljezja, centar iz prihvacenih CAL prozora i oznake."""

    def __init__(self, model: Model, key: str):
        self.run_dir = ROOT / "results/physical_fan" / RUNS[key]
        data = np.load(self.run_dir / "window_features.npz")
        self.phase, self.window = data["phase"], data["window"]
        self.features = data["feature96"].astype(np.float64)
        self.device_score = data["score"].astype(np.float64)

        self.discarded = discarded_cal_windows(self.run_dir / "serial.log")
        cal = [i for i, p in enumerate(self.phase)
               if p == "CAL" and int(self.window[i]) not in self.discarded]
        self.cal_count = len(cal)
        self.center = np.mean([model.z(self.features[i]) for i in cal], axis=0)
        self.cal_level = float(np.mean([model.level(self.features[i]) for i in cal]))

        with (self.run_dir / "detections.csv").open(encoding="utf-8-sig", newline="") as source:
            self.rows = {int(r["window"]): r for r in csv.DictReader(source)}
        self.det = [i for i, p in enumerate(self.phase) if p == "DET"]

    def eligible(self, i) -> dict | None:
        row = self.rows[int(self.window[i])]
        ok = (row["protocol_valid"] == "1" and row["condition_confirmed"] == "1"
              and row["transition_window"] == "0")
        return row if ok else None


def discarded_cal_windows(serial_log: Path) -> list[int]:
    for line in serial_log.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "CALTRIM" in line:
            return [int(v) for v in re.findall(r"discarded_index_\d+=(\d+)", line)]
    return []


def analyze(model: Model, key: str) -> dict:
    s = Session(model, key)
    rel_error = max(abs(model.score(s.features[i], s.center) - s.device_score[i])
                    / s.device_score[i] for i in s.det)

    groups: dict[str, list] = {}
    for i in s.det:
        row = s.eligible(i)
        if row is None:
            continue
        groups.setdefault(row["condition"], []).append((
            model.score(s.features[i], s.center),
            model.score(model.at_level(s.features[i], s.cal_level), s.center),
            10.0 * (model.level(s.features[i]) - s.cal_level),
            model.z(s.features[i]) - s.center,
        ))

    conditions = {}
    for condition, values in groups.items():
        raw = statistics.median(v[0] for v in values)
        fixed = statistics.median(v[1] for v in values)
        deviation = np.median(np.array([v[3] for v in values]), axis=0)
        top = np.argsort(-np.abs(deviation))[:5]
        conditions[condition] = {
            "windows": len(values),
            "median_score": raw,
            "median_score_at_cal_level": fixed,
            "median_change_percent": 100.0 * (fixed - raw) / raw,
            "median_band_level_change_db": statistics.median(v[2] for v in values),
            "median_band_deviation": [round(float(x), 4) for x in deviation],
            "largest_bands_hz": [round(float(BAND_CENTERS_HZ[b]), 1) for b in top],
        }

    bands = [int(np.argmin(np.abs(BAND_CENTERS_HZ - hz))) for hz in TONE_BANDS_HZ]
    timeline = []
    for i in s.det:
        row = s.rows[int(s.window[i])]
        d = model.z(s.features[i]) - s.center
        timeline.append({
            "elapsed_s": float(row["elapsed_s"]),
            "condition": row["condition"],
            "score": float(row["score"]),
            "deviation_1khz": round(float(d[bands[0]]), 3),
            "deviation_3khz": round(float(d[bands[1]]), 3),
        })

    return {
        "run": RUNS[key],
        "cal_windows_used": s.cal_count,
        "cal_windows_discarded": s.discarded,
        "det_windows": len(s.det),
        "eligible_det_windows": sum(len(v) for v in groups.values()),
        "max_relative_error_vs_device": rel_error,
        "conditions": conditions,
        "tone_band_centers_hz": [round(float(BAND_CENTERS_HZ[b]), 1) for b in bands],
        "timeline": timeline,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    model = Model()
    summary = {
        "analysis": "trial-features-v1",
        "scope": "post-hoc analysis of recorded device features; firmware and thresholds unchanged",
        "model_header_sha256": hashlib.sha256(HEADER.read_bytes()).hexdigest(),
        "empty_band_indices": model.empty.tolist(),
        "band_centers_hz": [round(float(f), 2) for f in BAND_CENTERS_HZ],
        "window_filter": "protocol_valid=1, condition_confirmed=1, transition_window=0",
        "runs": {key: analyze(model, key) for key in RUNS},
    }
    args.output.mkdir(parents=True, exist_ok=True)
    out = args.output / "summary.json"
    out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    for key, run in summary["runs"].items():
        print(f"{key}: device reproduction max rel error {run['max_relative_error_vs_device']:.2e}")
        for condition, v in run["conditions"].items():
            print(f"  {condition:26s} {v['median_score']:9.0f} -> "
                  f"{v['median_score_at_cal_level']:9.0f} ({v['median_change_percent']:+6.1f} %, "
                  f"level {v['median_band_level_change_db']:+5.2f} dB) bands {v['largest_bands_hz'][:3]}")
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
