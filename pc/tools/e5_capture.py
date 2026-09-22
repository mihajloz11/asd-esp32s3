"""Capture E5 logs and integrate calibrated, externally powered runs only.

All files for each run live below results/mjerenje_2026-09-21/runs/.
Python dependency for capture: pyserial. Analysis/tests use only stdlib.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import time
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "results" / "mjerenje_2026-09-21"


def fields(line):
    pairs = [part.split("=", 1) for part in line.split()[1:] if "=" in part]
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate keys")
    return result


def analyze(text, metadata):
    arm_lines = [line for line in text.splitlines() if line.startswith("E5ARM result=")]
    if arm_lines and not any(line.startswith("E5BEGIN ") for line in text.splitlines()):
        f = fields(arm_lines[-1])
        return [], {"status": "armed" if f.get("result") == "ESP_OK" and f.get("delay_s") != "0" else
                              "disarmed" if f.get("result") == "ESP_OK" else "arm_failed",
                    "reply": f, "energy_mj": None}
    if "E5BEGIN " not in text and any(line.startswith("E5CHECK ") for line in text.splitlines()):
        checks = []
        problems = []
        for line in text.splitlines():
            if line.startswith("E5ERROR"):
                problems.append(line)
            if line.startswith("E5CHECK "):
                try:
                    f = fields(line)
                    checks.append({k: f[k] if k == "phase" else int(f[k], 0)
                                   for k in ("index", "trigger_us", "ready_us", "bus_uv",
                                             "shunt_nv", "current_ua", "power_uw", "phase",
                                             "sequence", "mask")})
                except (ValueError, KeyError):
                    problems.append("malformed_check")
        if len(checks) != 10 or "E5CHECK_END" not in text:
            problems.append("incomplete_check")
        return checks, {"status": "diagnostic_only", "check_count": len(checks),
                        "issues": problems,
                        "mean_bus_v": statistics.mean(s["bus_uv"] for s in checks)/1e6 if checks else None,
                        "mean_current_ma": statistics.mean(s["current_ua"] for s in checks)/1000 if checks else None,
                        "energy_mj": None,
                        "limitation": "Register readout only; USB bypasses the load shunt. External reference required."}
    samples, phase_times, begin, end = [], {}, None, None
    issues = []
    measuring = False
    for line in text.splitlines():
        if line.startswith("E5START "):
            measuring = True
        if line.startswith("E5SAVE ") or line.startswith("E5END "):
            measuring = False
        if line.startswith("E5ERROR") or "Brownout" in line or "Guru Meditation" in line:
            issues.append(line)
        if line.startswith("rst:") and measuring:
            issues.append("device_reset_in_capture")
        try:
            if line.startswith("E5BEGIN "):
                if begin is not None:
                    issues.append("multiple_runs_in_log")
                begin = fields(line)
            elif line.startswith("E5END "):
                end = fields(line)
            elif line.startswith("E5TIME "):
                f = fields(line)
                phase_times[f["phase"]] = int(f["duration_us"])
            elif line.startswith("E5DATA "):
                f = fields(line)
                samples.append({k: f[k] if k == "phase" else int(f[k], 0)
                                for k in ("index", "trigger_us", "ready_us", "bus_uv",
                                          "shunt_nv", "current_ua", "power_uw", "phase",
                                          "sequence", "mask")})
        except (ValueError, KeyError) as exc:
            issues.append(f"malformed_record:{exc}")
    if not begin or not end:
        issues.append("missing_begin_or_end")
    else:
        try:
            if any(begin.get(k) != v for k, v in {"protocol": "e5-v1", "config": "0x4123", "cal": "1024", "shunt_mohm": "100"}.items()):
                issues.append("unexpected_measurement_configuration")
            if int(begin["samples"]) != len(samples) or int(end["samples"]) != len(samples):
                issues.append("sample_count_mismatch")
            if int(begin["errors"]) or int(end["errors"]):
                issues.append("device_measurement_errors")
            duration = (int(begin["end_us"]) - int(begin["start_us"])) / 1e6
            if not 59.5 <= duration <= 60.5:
                issues.append("not_a_complete_60s_run")
            if not phase_times or any(t < 0 for t in phase_times.values()) or sum(phase_times.values()) != int(begin["end_us"]) - int(begin["start_us"]):
                issues.append("phase_time_accounting_mismatch")
        except (ValueError, KeyError):
            issues.append("invalid_envelope")
    if len(samples) < 2:
        issues.append("insufficient_samples")
    for i, s in enumerate(samples):
        if s["index"] != i:
            issues.append("sample_sequence_gap")
        if s["ready_us"] <= s["trigger_us"] or not s["mask"] & 8 or s["mask"] & 4:
            issues.append("invalid_conversion")
        if not 3000000 <= s["bus_uv"] <= 3500000:
            issues.append("bus_voltage_out_of_test_range")
        if s["current_ua"] < 0:
            issues.append("reverse_current")
        # Independent raw shunt vs calibrated current register, nominal R100.
        if abs(s["shunt_nv"] / 100 - s["current_ua"]) > 100:
            issues.append("shunt_current_inconsistent")
    energy_uj = 0.0
    covered_s = 0.0
    gaps = []
    by_phase = {}
    for a, b in zip(samples, samples[1:]):
        dt = (b["trigger_us"] - a["trigger_us"]) / 1e6
        gaps.append(dt)
        if dt <= 0 or dt > 0.1:
            issues.append("nonmonotonic_or_large_gap")
            continue
        # Signed U*I avoids unsigned power register ambiguity on reverse flow.
        pa = a["bus_uv"] * a["current_ua"] / 1e6
        pb = b["bus_uv"] * b["current_ua"] / 1e6
        e = (pa + pb) * 0.5 * dt
        energy_uj += e
        covered_s += dt
        phase = a["phase"] if a["phase"] == b["phase"] and a["sequence"] == b["sequence"] else "MIXED"
        bucket = by_phase.setdefault(phase, {"covered_s": 0.0, "energy_mj": 0.0})
        bucket["covered_s"] += dt
        bucket["energy_mj"] += e / 1000
    if covered_s < 59:
        issues.append("insufficient_time_coverage")
    mean_v = statistics.mean(s["bus_uv"] for s in samples) / 1e6 if samples else None
    mean_ma = statistics.mean(s["current_ua"] for s in samples) / 1000 if samples else None
    saved_readout = metadata.get("command") == "E5SAVED"
    if (metadata.get("transport") != "uart" and not saved_readout) or not metadata.get("external_power"):
        issues.append("not_external_power_uart")
    if not metadata.get("wiring_verified"):
        issues.append("wiring_not_independently_verified")
    dmm = metadata.get("dmm_v")
    reference = metadata.get("reference_current_ma")
    if dmm is None or mean_v is None or abs(dmm - mean_v) > 0.010:
        issues.append("vbus_dmm_check_missing_or_over_10mv")
    tolerance = metadata.get("reference_tolerance_ma")
    if reference is None or tolerance is None or tolerance <= 0 or mean_ma is None or abs(reference - mean_ma) > tolerance:
        issues.append("current_reference_check_missing_or_failed")
    issues = sorted(set(issues))
    valid = not issues
    return samples, {
        "protocol": "e5-analysis-v1", "status": "validated_total_energy" if valid else "diagnostic_only",
        "firmware_sha": begin.get("firmware_sha") if begin else None,
        "issues": issues, "sample_count": len(samples), "covered_s": covered_s,
        "mean_bus_v": mean_v, "mean_current_ma": mean_ma,
        "effective_hz": (len(samples)-1)/covered_s if covered_s else None,
        "max_gap_ms": max(gaps)*1000 if gaps else None,
        "energy_mj": energy_uj/1000 if valid else None,
        "mean_power_mw": energy_uj/1000/covered_s if valid else None,
        "phase_time_us": phase_times,
        "stable_interval_estimates": by_phase if valid else None,
        "limitations": ["Energy is a sampled estimate, not a peak-current measurement.",
                        "Phase labels describe main-task work; I2S continues on the other core.",
                        "Mixed intervals are not allocated to DSP or score.",
                        "Short score calls require a separate repeated workload for energy per call.",
                        "Timing includes measurement overhead; polling-off comparison is required.",
                        "No extrapolation over missing first/last samples or gaps."],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port")
    ap.add_argument("--transport", choices=["usb", "uart"])
    ap.add_argument("--analyze-run", type=Path, help="Reanalyze a captured folder; preserve raw logs and original metadata")
    ap.add_argument("--command", default="E5CHECK", help="E5CHECK, E5RUN, E5DUMP, E5SAVED, E5ARM[5..3600], E5DISARM, LISTEN")
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--case", default="diagnostic")
    ap.add_argument("--external-power", action="store_true")
    ap.add_argument("--wiring-verified", action="store_true")
    ap.add_argument("--supply-v", type=float)
    ap.add_argument("--dmm-v", type=float)
    ap.add_argument("--reference-current-ma", type=float)
    ap.add_argument("--reference-tolerance-ma", type=float)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()
    if args.analyze_run:
        run = args.analyze_run.resolve()
        metadata = json.loads((run / "metadata.json").read_text(encoding="utf-8"))
        for key in ("dmm_v", "reference_current_ma", "reference_tolerance_ma"):
            if getattr(args, key) is not None:
                metadata[key] = getattr(args, key)
        if args.wiring_verified:
            metadata["wiring_verified"] = True
        if args.notes:
            metadata["reference_notes"] = args.notes
        _, summary = analyze((run / "serial.log").read_text(encoding="utf-8"), metadata)
        review = {"reviewed_utc": datetime.now(timezone.utc).isoformat(), "metadata": metadata, "summary": summary}
        review_name = "review-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
        (run / review_name).write_text(json.dumps(review, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return
    if not args.port or not args.transport:
        ap.error("capture requires --port and --transport")
    allowed = {"E5CHECK", "E5RUN", "E5DUMP", "E5SAVED", "E5ARM", "E5DISARM", "LISTEN"}
    if args.command not in allowed and not (args.command.startswith("E5ARM") and args.command[5:].isdigit() and 5 <= int(args.command[5:]) <= 3600):
        ap.error("unsupported measurement command")
    import serial
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run = ROOT / "runs" / stamp
    run.mkdir(parents=True)
    metadata = vars(args) | {"created_utc": stamp}
    metadata["git_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    metadata["git_diff_sha256"] = hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD"], cwd=REPO)).hexdigest()
    metadata["firmware_source_sha256"] = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((REPO / "firmware/esp32s3_asd/main").iterdir()) if p.is_file()
    }
    (run / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    port = serial.Serial(port=None, baudrate=115200, timeout=0.2)
    port.dtr = port.rts = False
    port.port = args.port
    pending_line = b""
    print(f"Saving to {run}", flush=True)
    try:
        port.open()
        start = time.monotonic()
        sent = args.command == "LISTEN"
        done = False
        with (run / "serial.raw").open("wb") as raw:
            while time.monotonic()-start < args.seconds and not done:
                chunk = port.read(max(1, port.in_waiting))
                raw.write(chunk)
                raw.flush()
                pending_line += chunk
                while b"\n" in pending_line:
                    line, pending_line = pending_line.split(b"\n", 1)
                    decoded = line.decode("utf-8", errors="replace").strip()
                    if not decoded.startswith("E5DATA "):
                        print(decoded, flush=True)
                    if sent and args.command != "LISTEN" and (decoded.startswith("E5END ") or decoded == "E5CHECK_END" or decoded.startswith("E5ERROR op=COMMAND") or decoded.startswith("E5ERROR op=LOAD") or decoded.startswith("E5ARM result=")):
                        done = True
                if not sent and time.monotonic()-start >= 4:
                    port.write((args.command+"\n").encode())
                    port.flush()
                    sent = True
    finally:
        port.close()
    text = (run / "serial.raw").read_bytes().decode("utf-8", errors="replace")
    (run / "serial.log").write_text(text, encoding="utf-8")
    samples, summary = analyze(text, metadata)
    if samples:
        with (run / "samples.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(samples[0]))
            writer.writeheader()
            writer.writerows(samples)
    (run / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
