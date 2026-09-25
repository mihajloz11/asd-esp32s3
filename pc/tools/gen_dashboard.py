"""Dashboard: sve eksperimente (results.csv + sweep logovi + meta) pretvara u
jedan samostalan HTML — pregled napretka, tabele po mašini, Pareto grafovi,
ΔAUC (int8 - fp32) analiza.

Upotreba (iz pc/): python tools/gen_dashboard.py
Izlaz: results/dashboard.html (otvori u browseru; regeneriši kad god hoćeš)
"""
from __future__ import annotations

import base64
import io
import re
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
OUT = RESULTS / "dashboard.html"

ALL_MACHINES = ["fan", "bearingEmu", "gearboxEmu", "sliderEmu", "ToyCar", "ToyCarEmu", "valveEmu"]


def sweep_status(machine: str) -> str:
    log = RESULTS / f"sweep_{machine}.log"
    if not log.exists():
        return "u redu čekanja"
    raw = log.read_bytes()  # PowerShell *>> pise UTF-16 LE sa BOM-om
    txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") \
        else raw.decode("utf-8", "ignore")
    if "GOTOVO" in txt:
        return "završeno ✔"
    m_var = re.findall(r"=== \w+ / (\w+) : trening", txt)
    m_ep = re.findall(r"Epoch (\d+)/(\d+)", txt)
    var = m_var[-1] if m_var else "?"
    ep = f"epoha {m_ep[-1][0]}/{m_ep[-1][1]}" if m_ep else "priprema featura"
    return f"vrti se: {var} ({ep})"


def pareto_png_b64(df: pd.DataFrame, machine: str) -> str:
    d = df[df["machine"] == machine]
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    for prec, marker, color in [("fp32", "o", "#0b57d0"), ("int8", "s", "#146c2e")]:
        sel = d[d["precision"] == prec].sort_values("n_params")
        if len(sel):
            ax.plot(sel["n_params"], sel["hmean"], marker=marker, color=color, label=prec)
            for _, r in sel.iterrows():
                ax.annotate(r["variant"], (r["n_params"], r["hmean"]),
                            textcoords="offset points", xytext=(4, 4), fontsize=7)
    ax.set_xscale("log")
    ax.set_xlabel("parametri")
    ax.set_ylabel("hmean")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    df = pd.read_csv(RESULTS / "results.csv") if (RESULTS / "results.csv").exists() else pd.DataFrame()
    css = """
    body{font:15px/1.5 'Segoe UI',sans-serif;margin:0;background:#fafafa;color:#1f2328}
    .wrap{max-width:1000px;margin:0 auto;padding:24px 16px}
    h1{font-size:1.5rem} h2{font-size:1.15rem;margin-top:32px;border-top:1px solid #ddd;padding-top:14px}
    table{border-collapse:collapse;font-size:.85rem;margin:8px 0}
    th,td{border:1px solid #d8dee4;padding:4px 9px;text-align:right}
    th{background:#eef1f4} td:first-child,th:first-child{text-align:left}
    .ok{color:#146c2e;font-weight:600}.run{color:#0b57d0;font-weight:600}.wait{color:#57606a}
    .neg{background:#fde7e9}.pos{background:#e6f4ea}
    .grid{display:flex;flex-wrap:wrap;gap:14px}
    .card{background:#fff;border:1px solid #d8dee4;border-radius:10px;padding:10px 14px}
    img{max-width:100%}
    @media (prefers-color-scheme: dark){
      body{background:#16181c;color:#e6e8eb} th{background:#262b33}
      th,td{border-color:#343a42} .card{background:#1e2126;border-color:#343a42}
      .neg{background:#4a2326}.pos{background:#1d3a26}.wait{color:#9aa4af}
    }"""
    h = ["<!DOCTYPE html><html lang='sr'><head><meta charset='utf-8'>",
         f"<title>ASD dashboard</title><style>{css}</style></head><body><div class='wrap'>",
         "<h1>Master rad — dashboard eksperimenata</h1>",
         f"<p>Generisano: {datetime.now():%d.%m.%Y %H:%M} · regeneracija: <code>python tools/gen_dashboard.py</code></p>"]

    # progres sweep-ova
    h.append("<h2>Napredak po mašinama (E1+E2+E3)</h2><table><tr><th>Mašina</th><th>Status</th><th>Redova u results.csv</th></tr>")
    for m in ALL_MACHINES:
        st = sweep_status(m)
        cls = "ok" if "✔" in st else ("run" if "vrti" in st else "wait")
        n = len(df[df["machine"] == m]) if len(df) else 0
        h.append(f"<tr><td>{m}</td><td class='{cls}'>{st}</td><td>{n}</td></tr>")
    h.append("</table>")

    if len(df):
        done = [m for m in ALL_MACHINES if len(df[df['machine'] == m]) >= 15]

        # zbirna tabela hmean po masini x varijanti (fp32 / int8)
        h.append("<h2>hmean po mašini i varijanti</h2>")
        for prec in ("fp32", "int8"):
            sel = df[(df["precision"] == prec) & (df["score"] == "mse")]
            piv = sel.pivot_table(index="variant", columns="machine",
                                  values="hmean", aggfunc="last")
            piv = piv.reindex(["baseline", "tiny64", "tiny32", "tiny32b4", "tiny16"])
            h.append(f"<h3>{prec}</h3>" + piv.round(4).to_html(border=0, na_rep="—"))

        # ΔAUC int8 - fp32
        h.append("<h2>E3: ΔhMean (int8 − fp32) — gdje kvantizacija boli</h2>")
        mse = df[df["score"] == "mse"]
        f32 = mse[mse["precision"] == "fp32"].set_index(["machine", "variant"])["hmean"]
        i8 = mse[mse["precision"] == "int8"].set_index(["machine", "variant"])["hmean"]
        delta = (i8 - f32).dropna().reset_index()
        piv = delta.pivot_table(index="variant", columns="machine", values="hmean", aggfunc="last")
        piv = piv.reindex(["baseline", "tiny64", "tiny32", "tiny32b4", "tiny16"])
        cells = piv.round(4)
        html_tbl = cells.to_html(border=0, na_rep="—")
        # oboji negativne ispod -0.005 (degradacija) i pozitivne iznad 0.005
        html_tbl = re.sub(r"<td>(-0\.0(0[5-9]|[1-9]\d)\d*)</td>", r"<td class='neg'>\1</td>", html_tbl)
        h.append(html_tbl)
        h.append("<p>Crveno = int8 gubi &gt; 0.005 hmean. Prag iz plana za reakciju (fallback lestvica): 0.05.</p>")

        # pareto grafovi
        h.append("<h2>Pareto krive</h2><div class='grid'>")
        for m in done:
            h.append(f"<div class='card'><b>{m}</b><br><img src='data:image/png;base64,{pareto_png_b64(df, m)}'></div>")
        h.append("</div>")

        # puna tabela
        h.append("<h2>Svi rezultati</h2>")
        cols = ["machine", "variant", "precision", "n_params", "auc_source", "auc_target", "pauc", "hmean"]
        h.append(df[cols].round(4).to_html(border=0, index=False))

    h.append("</div></body></html>")
    OUT.write_text("\n".join(h), encoding="utf-8")
    print(f"OK: {OUT}")


if __name__ == "__main__":
    main()
