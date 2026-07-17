"""E2 Pareto kriva: hmean AUC vs broj parametara, fp32 vs int8, po mašini.

Upotreba (iz pc/): python tools/plot_pareto.py [--machine fan]
Izlaz: results/pareto_<machine>.png + zbirna tabela u konzoli.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=None)
    args = ap.parse_args()

    df = pd.read_csv(ROOT / "results" / "results.csv")
    machines = [args.machine] if args.machine else sorted(df["machine"].unique())

    for m in machines:
        d = df[df["machine"] == m]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for prec, marker, label in [("fp32", "o", "fp32 (Keras)"), ("int8", "s", "int8 (PTQ)")]:
            sel = d[d["precision"] == prec].sort_values("n_params")
            if len(sel):
                ax.plot(sel["n_params"], sel["hmean"], marker=marker, label=label)
                for _, r in sel.iterrows():
                    ax.annotate(r["variant"], (r["n_params"], r["hmean"]),
                                textcoords="offset points", xytext=(4, 4), fontsize=7)
        ax.set_xscale("log")
        ax.set_xlabel("broj parametara")
        ax.set_ylabel("hmean(AUC_s, AUC_t, pAUC)")
        ax.set_title(f"Pareto: tačnost vs veličina modela — {m}")
        ax.grid(alpha=0.3)
        ax.legend()
        out = ROOT / "results" / f"pareto_{m}.png"
        fig.tight_layout()
        fig.savefig(out, dpi=150)
        print(f"OK: {out}")

    cols = ["machine", "variant", "precision", "n_params", "auc_source", "auc_target", "pauc", "hmean"]
    print(df[df["machine"].isin(machines)][cols].to_string(index=False))


if __name__ == "__main__":
    main()
