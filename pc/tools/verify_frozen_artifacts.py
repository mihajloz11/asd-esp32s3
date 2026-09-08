"""Verify that the publication review preserved firmware and recorded evidence."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BIN_HASH = "9ac2caca2c5010747547d4bb942aae96f700221588a4a6863b5c01948d967813"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    protected = [r for r in baseline["inventory"]
                 if r["path"].startswith(("firmware/", "models/", "results/"))]
    changed = [r["path"] for r in protected
               if not (ROOT/r["path"]).is_file() or digest(ROOT/r["path"]) != r["sha256"]]
    host_ast = {}
    for name in ("pc/tools/asd_panel.py", "pc/tools/physical_fan_experiment.py"):
        old = subprocess.check_output(["git", "show", f"{baseline['git_head']}:{name}"], cwd=ROOT)
        current = (ROOT/name).read_bytes()
        host_ast[name] = ast.dump(ast.parse(old)) == ast.dump(ast.parse(current))
    binary = ROOT/"firmware/esp32s3_asd/build/esp32s3_asd.bin"
    current_hash = digest(binary) if binary.exists() else None
    result = {"baseline_git_head": baseline["git_head"], "protected_files": len(protected),
              "changed_protected_files": changed, "host_ast_unchanged": host_ast,
              "firmware_bin_sha256": current_hash, "firmware_bin_matches": current_hash == BIN_HASH}
    result["pass"] = not changed and all(host_ast.values()) and current_hash == BIN_HASH
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
