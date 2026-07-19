"""E4 poredjenje: PC referentni score-ovi vs EVALCSV izlaz uredjaja.

Upotreba (iz pc/): python tools/compare_eval.py --machine fan
Cita: results/eval_reference_<machine>.csv + results/eval_device_<machine>.csv
Ispisuje max relativnu razliku score-ova + AUC izracunat iz device score-ova.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", required=True)
    ap.add_argument("--tol", type=float, default=1e-3, help="max dozvoljena relativna razlika")
    args = ap.parse_args()

    ref = {}
    with open(ROOT / "results" / f"eval_reference_{args.machine}.csv") as f:
        for row in csv.DictReader(f):
            ref[row["file"]] = (float(row["pc_score_int8"]), int(row["label"]), row["domain"])

    dev = {}
    dev_path = ROOT / "results" / f"eval_device_{args.machine}.csv"
    for line in dev_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"EVALCSV,(?:/clips/)?([\w.]+\.wav),([\d.eE+-]+),(\d+),(\d+),(\d+)",
                     line, re.IGNORECASE)
        if m:
            # FAT vraca 8.3 imena velikim slovima — normalizuj
            dev[m.group(1).lower()] = (float(m.group(2)), int(m.group(3)), int(m.group(4)))

    if not dev:
        raise SystemExit(f"nema EVALCSV linija u {dev_path}")

    rels, labels, scores, feat_ms, inf_ms = [], [], [], [], []
    for fname, (pc, lab, dom) in sorted(ref.items()):
        if fname not in dev:
            print(f"NEDOSTAJE na uredjaju: {fname}")
            continue
        d, fms, ims = dev[fname]
        rel = abs(d - pc) / max(abs(pc), 1e-12)
        rels.append(rel)
        labels.append(lab)
        scores.append(d)
        feat_ms.append(fms)
        inf_ms.append(ims)
        flag = "  <-- RAZLIKA!" if rel > args.tol else ""
        print(f"{fname}: PC={pc:.6f} dev={d:.6f} rel={rel:.2e}{flag}")

    print(f"\nmax rel razlika: {max(rels):.3e} (prag {args.tol})")
    print(f"AUC iz device score-ova: {roc_auc_score(labels, scores):.4f}")
    print(f"latencija po klipu: feat {np.mean(feat_ms):.0f}±{np.std(feat_ms):.0f} ms, "
          f"inf {np.mean(inf_ms):.0f}±{np.std(inf_ms):.0f} ms")
    if max(rels) > args.tol:
        raise SystemExit("PC i uredjaj se NE poklapaju — vidi registar rizika B1/B3")
    print("POKLAPANJE OK — uredjaj racuna isto sto i PC.")


if __name__ == "__main__":
    main()
