"""Scan reachable Git blobs for common credential patterns without printing values."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = {
    "private_key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "github_token": rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b",
    "aws_access_key": rb"\bAKIA[A-Z0-9]{16}\b",
    "api_key": rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    objects = subprocess.check_output(["git", "rev-list", "--objects", "--all"], cwd=ROOT).splitlines()
    process = subprocess.Popen(["git", "cat-file", "--batch"], cwd=ROOT,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    hits, blobs, binary, scanned_bytes = [], 0, 0, 0
    try:
        for entry in objects:
            oid, _, name = entry.partition(b" ")
            process.stdin.write(oid + b"\n")
            process.stdin.flush()
            header = process.stdout.readline().split()
            raw = process.stdout.read(int(header[2]))
            assert process.stdout.read(1) == b"\n"
            if header[1] != b"blob":
                continue
            blobs += 1
            if b"\0" in raw:
                binary += 1
                continue
            scanned_bytes += len(raw)
            for kind, pattern in PATTERNS.items():
                if re.search(pattern, raw):
                    hits.append({"object": oid.decode(), "path": name.decode(errors="replace"), "type": kind})
    finally:
        process.stdin.close()
        process.wait()
    result = {"scope": "all locally reachable refs; text blobs only; reflogs and binary containers excluded",
              "objects": len(objects), "blobs": blobs, "binary_blobs_skipped": binary,
              "text_bytes_scanned": scanned_bytes, "patterns": list(PATTERNS), "hits": hits}
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
