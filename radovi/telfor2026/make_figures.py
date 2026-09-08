"""Pravi sve slike za TELFOR rad iz stvarnih podataka iz repozitorijuma.

Nijedna brojka na slikama nije upisana rucno — sve se racuna iz:
  results/false_alarm/*/detections.csv   trase score-a sa uredjaja (3 prolaza)
  results/advanced/*.npz                 keširani psd_shape feature-i

Izlaz: radovi/telfor2026/slike/*.png (600 dpi, sirina jedne kolone).

Pokretanje:
    ..\\..\\.venv\\Scripts\\python.exe make_figures.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "slike"
OUT.mkdir(exist_ok=True)

RUNS = {
    "1": REPO / "results/false_alarm/20260813_233457_spd_1_8.0min",
    "2": REPO / "results/false_alarm/20260814_001246_spd_1_30.0min",
    "3": REPO / "results/false_alarm/20260814_004542_spd_1_20.0min",
}

COL_W = 3.30           # sirina jedne kolone IEEE A4, u incima
DPI = 600

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 7,
    "axes.labelsize": 7,
    "axes.titlesize": 7,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "legend.fontsize": 6.5,
    "axes.linewidth": 0.6,
    "grid.linewidth": 0.4,
    "lines.linewidth": 0.8,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.01,
})


def load_run(path: Path):
    rows = list(csv.DictReader(open(path / "detections.csv", encoding="utf-8")))
    t = np.array([float(r["t_s"]) for r in rows])
    score = np.array([float(r["score"]) for r in rows])
    thr = float(rows[0]["threshold"])
    assert len({r["threshold"] for r in rows}) == 1, "prag se mijenja u toku prolaza"
    return t, score, thr


def max_consecutive(score, thr):
    best = cur = 0
    for s in score:
        cur = cur + 1 if s > thr else 0
        best = max(best, cur)
    return best


# --------------------------------------------------------------------------
# Sl. 1 — blok dijagram: hardver, front-end i hijerarhija odlucivanja
# --------------------------------------------------------------------------

def fig_system():
    """Lanac: hardver -> front-end -> cetiri kapije odlucivanja.

    Raspored je fiksna mreza; visina okvira se racuna iz broja redova teksta
    da tekst nikad ne izadje iz okvira.
    """
    W, H = 100.0, 74.0
    fig, ax = plt.subplots(figsize=(COL_W, COL_W * H / W))
    ax.set_xlim(0, W)
    ax.set_ylim(-4, 70)
    ax.axis("off")

    FS = 5.5
    FS_EDGE = 5.0

    def box(x, y, w, h, lines, bold=False, fill="white", ec="black",
            gate=False):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0,rounding_size=1.2",
            linewidth=0.9 if gate else 0.6, edgecolor=ec, facecolor=fill))
        ax.text(x + w / 2, y + h / 2, "\n".join(lines),
                ha="center", va="center", fontsize=FS, linespacing=1.3,
                fontweight="bold" if bold else "normal")

    def arrow(pts, dashed=False):
        for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
            last = (x2, y2) == pts[-1]
            ax.add_patch(FancyArrowPatch(
                (x1, y1), (x2, y2),
                arrowstyle="-|>" if last else "-",
                mutation_scale=5, linewidth=0.6, color="black",
                linestyle=(0, (2.2, 1.6)) if dashed else "solid",
                shrinkA=0, shrinkB=0))

    def elabel(x, y, text):
        ax.text(x, y, text, ha="center", va="center", fontsize=FS_EDGE,
                style="italic")

    # --- red 1: hardver ---
    box(0, 58, 27, 12, ["INMP441", "MEMS microphone"])
    box(32, 58, 37, 12, ["ESP32-S3-WROOM-1", "240 MHz, 16 MB PSRAM"],
        bold=True)
    box(76, 58, 24, 12, ["push-button", "2 status LEDs"])
    arrow([(27, 64), (32, 64)])
    elabel(29.5, 61.2, "I2S")
    arrow([(76, 64), (69, 64)])
    elabel(72.5, 61.2, "GPIO")

    # --- red 2: front-end; kapije imaju deblji okvir ---
    box(0, 36, 22, 14, ["quality gate", "count, DC, RMS,", "clipping, stuck"],
        gate=True)
    box(25, 36, 22, 14, ["Welch PSD", "8192 samples,", "50 % overlap"])
    box(50, 36, 22, 14, ["96 log bands", "10 Hz - 4 kHz,", "mean removed"])
    box(75, 36, 22, 14, ["standardise +", "Mahalanobis", "(Ledoit-Wolf)"])
    arrow([(22, 43), (25, 43)])
    arrow([(47, 43), (50, 43)])
    arrow([(72, 43), (75, 43)])
    arrow([(50, 58), (50, 54), (11, 54), (11, 50)])
    elabel(21.5, 55.7, "audio")

    # --- kalibracija ---
    box(26, 20, 66, 12,
        ["normal-only: 10 centre + 44 derive + 22 verify,",
         "frozen centre and separate entry / release thresholds"])
    arrow([(85, 58), (98.5, 58), (98.5, 26), (92, 26)], dashed=True)

    # --- red 3: odluka ---
    box(0, 2, 22, 14, ["presence gate", "level >= cal.", "mean - 11 dB"],
        gate=True)
    box(26, 2, 22, 14, ["high score?", "unstable: HOLD"], gate=True)
    box(52, 2, 22, 14, ["3 reliable highs", "release <= exit", "12th alarm: event"],
        gate=True)
    box(78, 2, 22, 14, ["alarm LED"], bold=True)
    arrow([(22, 9), (26, 9)])
    arrow([(48, 9), (52, 9)])
    arrow([(74, 9), (78, 9)])
    arrow([(86, 36), (86, 34), (6, 34), (6, 16)])
    arrow([(37, 20), (37, 16)], dashed=True)
    elabel(13.5, 32.2, "score")

    ax.text(100, -3.4, "bold outline: fail-closed gate", ha="right",
            va="bottom", fontsize=FS_EDGE, style="italic")

    fig.savefig(OUT / "fig1_system.png", dpi=DPI)
    plt.close(fig)
    return "fig1_system.png"


# --------------------------------------------------------------------------
# Sl. 2 — trasa score-a sa uredjaja, cist prolaz
# --------------------------------------------------------------------------

def fig_device_run():
    t, score, thr = load_run(RUNS["3"])
    t_min = (t - t[0]) / 60.0
    above = score > thr
    run = max_consecutive(score, thr)

    fig, ax = plt.subplots(figsize=(COL_W, 1.85))
    ax.plot(t_min, score, color="0.35", lw=0.7, zorder=2)
    ax.plot(t_min[~above], score[~above], "o", ms=1.9, mfc="0.35",
            mec="none", zorder=3)
    ax.plot(t_min[above], score[above], "o", ms=3.4, mfc="white",
            mec="black", mew=0.8, zorder=4,
            label=f"above threshold ({above.sum()} of {len(score)})")
    ax.axhline(thr, color="black", ls="--", lw=0.8, zorder=1,
               label=f"threshold = {thr:.0f}")
    ax.axhline(0.7 * thr, color="0.55", ls=":", lw=0.8, zorder=1,
               label=f"release = 0.7 x threshold")

    ax.set_xlabel("time in detection state (min)")
    ax.set_ylabel("Mahalanobis score")
    ax.set_xlim(-0.3, t_min.max() + 0.3)
    ax.set_ylim(0, max(score.max(), thr) * 1.30)
    ax.grid(True, color="0.85", ls="-", lw=0.4)
    ax.set_axisbelow(True)
    leg = ax.legend(loc="upper right", frameon=True, framealpha=1,
                    borderpad=0.3, handlelength=1.6, labelspacing=0.22)
    leg.get_frame().set_linewidth(0.5)
    leg.get_frame().set_edgecolor("0.6")

    fig.savefig(OUT / "fig2_device_run.png", dpi=DPI)
    plt.close(fig)
    return "fig2_device_run.png", int(above.sum()), run, thr


# --------------------------------------------------------------------------
# Sl. 3 — nestabilnost praga kroz tri kalibracije
# --------------------------------------------------------------------------

def fig_threshold():
    fig, ax = plt.subplots(figsize=(COL_W, 1.95))
    rng = np.random.default_rng(20260814)

    thrs, meds = [], []
    for i, key in enumerate(("1", "2", "3")):
        _, score, thr = load_run(RUNS[key])
        thrs.append(thr)
        meds.append(float(np.median(score)))
        x = i + 1 + rng.uniform(-0.17, 0.17, size=score.size)
        above = score > thr
        ax.plot(x[~above], score[~above], "o", ms=1.8, mfc="0.55",
                mec="none", zorder=2)
        ax.plot(x[above], score[above], "o", ms=1.8, mfc="none",
                mec="black", mew=0.5, zorder=3)
        ax.hlines(thr, i + 1 - 0.33, i + 1 + 0.33, color="black",
                  lw=1.4, zorder=5)
        ax.hlines(np.median(score), i + 1 - 0.33, i + 1 + 0.33,
                  color="0.4", lw=1.0, ls=(0, (3, 1.5)), zorder=4)
        ax.annotate(f"{thr:.0f}", xy=(i + 1 + 0.36, thr), xytext=(2, 0),
                    textcoords="offset points", ha="left", va="center",
                    fontsize=6, fontweight="bold")

    ax.set_yscale("log")
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(["run 1\n(8 min)", "run 2\n(30 min)",
                        "run 3\n(20 min, clean)"])
    ax.set_ylabel("Mahalanobis score")
    ax.set_xlim(0.42, 4.05)
    ax.grid(True, axis="y", color="0.85", ls="-", lw=0.4, which="major")
    ax.set_axisbelow(True)

    ax.plot([], [], "-", color="black", lw=1.4, label="calibrated threshold")
    ax.plot([], [], ls=(0, (3, 1.5)), color="0.4", lw=1.0,
            label="median score")
    ax.plot([], [], "o", ms=2.4, mfc="none", mec="black", mew=0.5,
            ls="none", label="window above threshold")
    leg = ax.legend(loc="upper right", frameon=True, framealpha=1,
                    borderpad=0.3, handlelength=1.5, labelspacing=0.22,
                    ncol=1)
    leg.get_frame().set_linewidth(0.5)
    leg.get_frame().set_edgecolor("0.6")

    spread_thr = max(thrs) / min(thrs)
    spread_med = max(meds) / min(meds)

    fig.savefig(OUT / "fig3_threshold.png", dpi=DPI)
    plt.close(fig)
    return "fig3_threshold.png", spread_thr, spread_med


# --------------------------------------------------------------------------
# Sl. 4 — sta model vidi: normalan naspram anomalnog spektra
# --------------------------------------------------------------------------

def fig_spectrum():
    adv = REPO / "results/advanced"
    src = np.load(adv / "adv_source_train_normal.npz")
    ano = np.load(adv / "adv_target_test_anomaly.npz")
    nor = np.load(adv / "adv_target_test_normal.npz")

    def pick(z):
        key = "psd_shape" if "psd_shape" in z else list(z.keys())[0]
        return z[key]

    s, a, n = pick(src), pick(ano), pick(nor)
    bands = np.geomspace(10, 4000, s.shape[1])

    fig, ax = plt.subplots(figsize=(COL_W, 1.75))
    ax.fill_between(bands, np.percentile(s, 5, axis=0),
                    np.percentile(s, 95, axis=0), color="0.85",
                    label="source normal, 5-95 %")
    ax.plot(bands, n.mean(axis=0), color="black", lw=0.9,
            label="target normal (mean)")
    ax.plot(bands, a.mean(axis=0), color="black", lw=0.9,
            ls=(0, (3, 1.5)), label="target anomalous (mean)")

    ax.set_xscale("log")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("level (dB, mean removed)")
    ax.set_xlim(10, 4000)
    ax.grid(True, color="0.85", ls="-", lw=0.4)
    ax.set_axisbelow(True)
    leg = ax.legend(loc="lower left", frameon=True, framealpha=1,
                    borderpad=0.3, handlelength=1.6, labelspacing=0.25)
    leg.get_frame().set_linewidth(0.5)
    leg.get_frame().set_edgecolor("0.6")

    fig.savefig(OUT / "fig4_spectrum.png", dpi=DPI)
    plt.close(fig)
    return "fig4_spectrum.png"


def fig_fan_tone():
    """Trasa mjerenja sa konstantnim tonom na stvarnom ventilatoru.

    Izvor: results/physical_fan/run_20260827T220338_fan02_tone-validation-*/
    Prag izlaska se cita iz PROFILE zapisa u serijskom logu, ne upisuje rukom.
    """
    run = REPO / ("results/physical_fan/"
                  "run_20260827T220338_fan02_tone-validation-20260827-final")
    rows = list(csv.DictReader(open(run / "detections.csv", encoding="utf-8")))
    t = (np.array([float(r["elapsed_s"]) for r in rows]) -
         float(rows[0]["elapsed_s"])) / 60.0
    score = np.array([float(r["score"]) for r in rows])
    hold = np.array([int(r["hold"]) for r in rows])
    alarm = np.array([int(r["alarm"]) for r in rows])
    enter = float(rows[0]["threshold"])

    exit_thr = None
    for line in open(run / "serial.log", encoding="utf-8", errors="ignore"):
        if "PROFILE protocol" in line and "threshold_exit=" in line:
            for field in line.split():
                if field.startswith("threshold_exit="):
                    exit_thr = float(field.split("=", 1)[1])
            break
    assert exit_thr is not None, "nema threshold_exit u serial.log"

    fig, ax = plt.subplots(figsize=(COL_W, 1.85))
    ax.semilogy(t, score, color="0.4", linewidth=0.7, zorder=2)
    ok = (hold == 0) & (alarm == 0)
    ax.scatter(t[ok], score[ok], s=4, color="black", zorder=3, label="normal")
    ax.scatter(t[hold == 1], score[hold == 1], s=9, facecolors="none",
               edgecolors="0.45", linewidths=0.6, zorder=4, label="held")
    ax.scatter(t[alarm == 1], score[alarm == 1], s=6, color="black",
               marker="^", zorder=5, label="alarm")
    ax.axhline(enter, color="black", linewidth=0.7, linestyle="--")
    ax.axhline(exit_thr, color="0.45", linewidth=0.7, linestyle=":")
    ax.text(t[-1], enter * 1.18, "entry", fontsize=5.5, ha="right")
    ax.text(t[-1], exit_thr * 0.62, "release", fontsize=5.5, ha="right",
            color="0.35")
    ax.set_xlabel("time in monitoring [min]")
    ax.set_ylabel("score")
    ax.grid(alpha=0.25, which="both")
    ax.legend(frameon=False, loc="upper left", ncol=3, fontsize=5.5,
              handletextpad=0.2, columnspacing=0.8, borderpad=0.1)
    fig.savefig(OUT / "fig5_fan_tone.png", dpi=DPI)
    plt.close(fig)
    return "fig5_fan_tone.png"


if __name__ == "__main__":
    print(fig_system())
    print(fig_device_run())
    print(fig_threshold())
    print(fig_fan_tone())
    try:
        print(fig_spectrum())
    except Exception as exc:  # keš anomalija je opcion
        print(f"fig4 preskocena: {exc}")
