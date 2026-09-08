"""Inventory project files and recompute the two final fan summaries."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import statistics
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
FINAL_RUNS = (
    "run_20260827T213148_fan02_guided25-20260827-v3recovery5d",
    "run_20260827T220338_fan02_tone-validation-20260827-final",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fan_summary(name):
    folder = ROOT / "results/physical_fan" / name
    with (folder / "detections.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    eligible = [r for r in rows if r["condition_confirmed"] == "1"
                and r["protocol_valid"] == "1" and r["transition_window"] == "0"]
    conditions = {}
    for condition in dict.fromkeys(r["condition"] for r in eligible):
        group = [r for r in eligible if r["condition"] == condition]
        scores = [float(r["score"]) for r in group]
        conditions[condition] = {
            "windows": len(group), "held": sum(int(r["hold"]) for r in group),
            "alarm_windows": sum(int(r["alarm"]) for r in group),
            "score_median": statistics.median(scores),
            "score_min": min(scores), "score_max": max(scores),
        }
    provenance = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    return {"raw_windows": len(rows), "eligible_windows": len(eligible),
            "excluded_windows": len(rows) - len(eligible),
            "alarm_windows": sum(int(r["alarm"]) for r in eligible),
            "conditions": conditions, "firmware": provenance.get("firmware"),
            "csv_sha256": sha256(folder / "detections.csv")}


def audit(output):
    tracked = subprocess.check_output(["git", "ls-files", "--cached", "--others",
                                       "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    paths = [Path(p) for p in sorted(set(tracked)) if p and (ROOT / p).is_file()
             and (ROOT / p).resolve() != output.resolve()]
    inventory = []
    broken_links = []
    privacy = []
    secret_hits = []
    secret_patterns = {
        "private_key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "github_token": r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b",
        "aws_access_key": r"\bAKIA[A-Z0-9]{16}\b",
        "api_key": r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b",
    }
    for relative in paths:
        path = ROOT / relative
        raw = path.read_bytes()
        item = {"path": relative.as_posix(), "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest()}
        inventory.append(item)
        if b"\0" in raw:
            continue
        text = raw.decode("utf-8", errors="replace")
        for label, pattern in secret_patterns.items():
            if re.search(pattern, text):
                secret_hits.append({"path": relative.as_posix(), "type": label})
        categories = []
        if re.search(r"[A-Za-z]:[\\/]+Users[\\/]+", text):
            categories.append("local_user_path")
        if re.search(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", text):
            categories.append("device_identifier")
        if categories:
            privacy.append({"path": relative.as_posix(), "categories": categories})
        if relative.suffix.lower() != ".md":
            continue
        for match in re.finditer(r"\]\(([^)\n]+)\)", text):
            target = match.group(1).strip().strip("<>").split("#")[0]
            if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            if not (path.parent / unquote(target)).exists():
                broken_links.append({"path": relative.as_posix(), "target": target,
                                     "line": text.count("\n", 0, match.start()) + 1})
    return {
        "scope": "tracked and non-ignored new files, excluding this output; pattern scan is not a security certification",
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "tracked_files": len(paths), "tracked_bytes": sum(p["bytes"] for p in inventory),
        "files_by_root": dict(Counter(p.parts[0] if len(p.parts) > 1 else "." for p in paths)),
        "secret_pattern_hits": secret_hits, "privacy_paths": privacy,
        "broken_markdown_file_links": broken_links,
        "final_fan_runs": {name: fan_summary(name) for name in FINAL_RUNS},
        "inventory": inventory,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for key in ("tracked_files", "tracked_bytes", "files_by_root", "secret_pattern_hits",
                "broken_markdown_file_links", "final_fan_runs"):
        print(key, json.dumps(result[key], ensure_ascii=False))
    print("privacy_paths", len(result["privacy_paths"]))


if __name__ == "__main__":
    main()
