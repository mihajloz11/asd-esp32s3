"""Agregacija za finalne tabele rada: mean ± std preko seedova (DCASE praksa
je 5 nezavisnih treninga). Grupise results.csv po (machine, variant, precision,
score) i ispisuje/snima tabelu spremnu za rad.

Upotreba (iz pc/): python tools/results_stats.py [--latex]
Izlaz: results/results_stats.csv (+ LaTeX tabela na stdout uz --latex)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--latex", action="store_true")
    args = ap.parse_args()

    df = pd.read_csv(ROOT / "results" / "results.csv")
    metrics = ["auc_source", "auc_target", "pauc", "hmean"]
    g = df.groupby(["machine", "variant", "precision", "score"])
    agg = g[metrics].agg(["mean", "std", "count"]).round(4)
    agg.columns = ["_".join(c) for c in agg.columns]
    agg = agg.reset_index()

    out = ROOT / "results" / "results_stats.csv"
    agg.to_csv(out, index=False)
    print(f"OK: {out}")

    # citljiv pregled: hmean mean±std (n)
    view = agg.assign(hmean_fmt=lambda d: d.apply(
        lambda r: f"{r['hmean_mean']:.4f}±{0 if pd.isna(r['hmean_std']) else r['hmean_std']:.4f} (n={int(r['hmean_count'])})",
        axis=1))
    piv = view.pivot_table(index=["variant", "precision", "score"], columns="machine",
                           values="hmean_fmt", aggfunc="first")
    print(piv.to_string())

    if args.latex:
        print("\n% LaTeX za rad:")
        print(piv.to_latex(na_rep="—"))


if __name__ == "__main__":
    main()
