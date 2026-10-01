"""Slike za TELFOR rad, iz sacuvanih mjerenja.

Nijedna brojka nije upisana rucno:
  results/physical_fan/<run>/serial.log          faze, ocjene DERIVE/VERIFY, pragovi
  results/physical_fan/<run>/detections.csv      DET prozori, oznake, HOLD, alarm
  results/physical_fan/<run>/window_features.npz obiljezja prozora (Sl. 3)

Izlaz: radovi/telfor2026/slike/*.png, 600 dpi, sirina jedne kolone.

Pokretanje iz korijena repoa:
    python radovi/telfor2026/make_figures.py
"""

from __future__ import annotations

import csv
import itertools
import re
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "pc/tools"))
from analyze_trial_features import BAND_CENTERS_HZ, Model, Session  # noqa: E402
OUT = HERE / "slike"
OUT.mkdir(exist_ok=True)

RUNS = {
    "paper": REPO / "results/physical_fan/run_20260827T213148_fan02_guided25-20260827-v3recovery5d",
    "tone": REPO / "results/physical_fan/run_20260827T220338_fan02_tone-validation-20260827-final",
}

COL_W = 3.30           # sirina kolone IEEE A4, in
DPI = 600

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 7,
    "axes.labelsize": 7,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "legend.fontsize": 6.2,
    "axes.linewidth": 0.6,
    "lines.linewidth": 0.8,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.01,
})


# Sl. 1: tok signala i odluke

def fig_system():
    W = 100.0
    fig, ax = plt.subplots(figsize=(COL_W, COL_W * 0.70))
    ax.set_xlim(0, W)
    ax.set_ylim(-3, 70)
    ax.axis("off")
    fs = 5.4

    def box(x, y, w, h, text, bold=False, gate=False):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
            linewidth=1.0 if gate else 0.6, edgecolor="black",
            facecolor="0.93" if gate else "white"))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, linespacing=1.25,
                fontweight="bold" if bold else "normal")

    def arrow(points, dashed=False):
        for (x1, y1), (x2, y2) in zip(points[:-1], points[1:]):
            ax.add_patch(FancyArrowPatch(
                (x1, y1), (x2, y2),
                arrowstyle="-|>" if (x2, y2) == points[-1] else "-",
                mutation_scale=5, linewidth=0.6, color="black",
                linestyle=(0, (2.2, 1.6)) if dashed else "solid",
                shrinkA=0, shrinkB=0))

    def label(x, y, text):
        ax.text(x, y, text, ha="center", va="center", fontsize=5.0,
                style="italic")

    box(0, 58, 26, 11, "INMP441\nMEMS microphone")
    box(31, 58, 36, 11, "ESP32-S3-WROOM-1\n240 MHz, 16 MB PSRAM", bold=True)
    box(74, 58, 26, 11, "push-button\n2 status LEDs")
    arrow([(26, 63.5), (31, 63.5)])
    label(28.5, 60.6, "I2S")
    arrow([(74, 63.5), (67, 63.5)])
    label(70.5, 60.6, "GPIO")

    box(0, 37, 22, 13, "quality gate\nsamples, level,\nclipping, drops", gate=True)
    box(25.5, 37, 22, 13, "Welch PSD\n8192 points,\n50 % overlap")
    box(51, 37, 22, 13, "96 log bands\n10 Hz to 4 kHz,\nmean removed")
    box(76.5, 37, 23.5, 13, "Mahalanobis\nscore with\nLedoit-Wolf")
    arrow([(22, 43.5), (25.5, 43.5)])
    arrow([(47.5, 43.5), (51, 43.5)])
    arrow([(73, 43.5), (76.5, 43.5)])
    arrow([(50, 58), (50, 54), (11, 54), (11, 50)])
    label(22, 55.6, "10 s windows")

    box(22, 20.5, 70, 11.5,
        "commissioning from normal sound only:\n"
        "10 center + 44 derive + 22 verify windows")
    arrow([(87, 58), (97.5, 58), (97.5, 26), (92, 26)], dashed=True)
    label(90.5, 56.2, "start")

    box(0, 2, 22, 14, "presence gate\nat most 11 dB\nbelow cal. level", gate=True)
    box(26, 2, 22, 14, "reliability gate\nunstable high\nwindow: HOLD", gate=True)
    box(52, 2, 23, 14, "temporal rule\n3 reliable highs,\nrelease threshold", gate=True)
    box(79, 2, 21, 14, "alarm LED\nand events", bold=True)
    arrow([(22, 9), (26, 9)])
    arrow([(48, 9), (52, 9)])
    arrow([(75, 9), (79, 9)])
    arrow([(88, 37), (88, 34.5), (6, 34.5), (6, 16)])
    arrow([(47, 20.5), (47, 18), (37, 18), (37, 16)], dashed=True)
    label(14, 32.9, "score")

    ax.text(100, -2.6, "shaded: fail-closed gates", ha="right", va="bottom",
            fontsize=5.0, style="italic")
    fig.savefig(OUT / "fig1_system.png", dpi=DPI)
    plt.close(fig)
    return "fig1_system.png"


# Sl. 2: cijela sesija na ventilatoru, od kalibracije do nadzora

def read_session(run: Path):
    phases, profile, events = [], {}, []
    cal_times = []
    for line in (run / "serial.log").read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        t, record = float(parts[1]), parts[2]
        if record.startswith("CAL ") and "/10" in record:
            cal_times.append(t)
        elif record.startswith("COMMISSION ") and "action=WINDOW" in record \
                and "score_valid=1" in record:
            phase = re.search(r"phase=(\w+)", record).group(1)
            score = float(re.search(r" score=([-\d.e+]+)", record).group(1))
            phases.append((t, phase, score))
        elif record.startswith("PROFILE ") and "threshold_enter=" in record:
            for key in ("threshold_enter", "threshold_exit"):
                profile[key] = float(re.search(key + r"=([\d.e+]+)", record).group(1))
        elif record.startswith("EVENT ") and "type=ANOMALY_" in record:
            events.append((t, re.search(r"type=(\w+)", record).group(1)))

    with (run / "detections.csv").open(encoding="utf-8-sig", newline="") as source:
        det = list(csv.DictReader(source))
    return cal_times, phases, profile, events, det


CONDITION_STYLE = {
    "airflow_change_paper": ("0.72", "P"),
    "ambient_speech": ("0.86", "S"),
    "ambient_door": ("0.86", "D"),
    "constant_tone_1khz": ("0.80", "1 kHz tone"),
}


def condition_key(condition):
    for key in CONDITION_STYLE:
        if condition.startswith(key):
            return key
    return None


def draw_session(ax, run, label, show_legend):
    cal_times, phases, profile, events, det = read_session(run)
    t0 = cal_times[0] - 10.0
    minutes = lambda t: (t - t0) / 60.0

    # faze prije nadzora
    derive = [(t, s) for t, p, s in phases if p == "COMMISSION_DERIVE"]
    verify = [(t, s) for t, p, s in phases if p in ("COMMISSION_VERIFY", "MONITORING")]
    det_start = float(det[0]["elapsed_s"]) - 10.0
    spans = [("CAL", cal_times[0] - 10.0, cal_times[-1]),
             ("DERIVE", derive[0][0] - 10.0, derive[-1][0]),
             ("VERIFY", verify[0][0] - 10.0, verify[-1][0]),
             ("MONITOR", det_start, float(det[-1]["elapsed_s"]))]
    for name, a, b in spans:
        ax.axvline(minutes(a), color="0.55", lw=0.5, ls=(0, (1, 1.2)), zorder=1)
        ax.text((minutes(a) + minutes(b)) / 2, 1.0, name, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=5.4)

    # oznake uslova u nadzoru
    for condition, group in itertools.groupby(det, key=lambda r: r["condition"]):
        key = condition_key(condition)
        if key is None:
            continue
        rows = list(group)
        a = minutes(float(rows[0]["elapsed_s"]) - 10.0)
        b = minutes(float(rows[-1]["elapsed_s"]))
        color, text = CONDITION_STYLE[key]
        ax.axvspan(a, b, color=color, lw=0, zorder=0)
        ax.text((a + b) / 2, 0.035, text, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=5.0)

    # ocjene
    td = np.array([minutes(t) for t, _ in derive + verify])
    sd = np.array([s for _, s in derive + verify])
    ax.plot(td, sd, color="0.55", lw=0.5, zorder=2)
    ax.scatter(td, sd, s=3.5, color="0.55", zorder=3, lw=0, label="DERIVE / VERIFY")

    t = np.array([minutes(float(r["elapsed_s"])) for r in det])
    score = np.array([float(r["score"]) for r in det])
    hold = np.array([r["hold"] == "1" for r in det])
    alarm = np.array([r["alarm"] == "1" for r in det])
    plain = ~hold & ~alarm
    ax.plot(t, score, color="0.25", lw=0.5, zorder=2)
    ax.scatter(t[plain], score[plain], s=4, color="black", lw=0, zorder=4, label="monitoring")
    ax.scatter(t[hold], score[hold], s=11, facecolors="white", edgecolors="black",
               linewidths=0.6, zorder=5, label="HOLD")
    ax.scatter(t[alarm], score[alarm], s=9, color="black", marker="^", lw=0,
               zorder=6, label="alarm")

    enter, release = profile["threshold_enter"], profile["threshold_exit"]
    x0 = minutes(verify[0][0] - 10.0)
    x1 = minutes(float(det[-1]["elapsed_s"])) + 0.2
    ax.hlines(enter, x0, x1, color="black", lw=0.7, ls="--", zorder=3)
    ax.hlines(release, x0, x1, color="black", lw=0.7, ls=":", zorder=3)
    ax.text(x0 + 0.15, enter * 1.25, "entry", fontsize=5.2, va="bottom")
    ax.text(x0 + 0.15, release * 0.80, "release", fontsize=5.2, va="top")

    for time, kind in events:
        if kind == "ANOMALY_SUSTAINED":
            ax.annotate("sustained", xy=(minutes(time), score.max() * 1.05),
                        xytext=(minutes(time), score.max() * 3.2), fontsize=5.0,
                        ha="center", arrowprops=dict(arrowstyle="-|>", lw=0.5,
                                                     color="black", mutation_scale=5))

    ax.set_yscale("log")
    ax.set_ylim(80, score.max() * 5.0)
    ax.set_xlim(0, x1)
    ax.set_ylabel("score")
    ax.grid(True, axis="y", color="0.88", lw=0.4, which="major")
    ax.set_axisbelow(True)
    ax.text(0.006, 0.97, label, transform=ax.transAxes, ha="left", va="top",
            fontsize=6.5, fontweight="bold")
    if show_legend:
        ax.legend(loc="upper left", bbox_to_anchor=(0.06, 1.0), ncol=1,
                  frameon=False, handletextpad=0.2, borderaxespad=0.2,
                  labelspacing=0.2)


def fig_trials():
    fig, axes = plt.subplots(2, 1, figsize=(COL_W, 3.05), sharex=False)
    draw_session(axes[0], RUNS["paper"], "(a)", show_legend=True)
    draw_session(axes[1], RUNS["tone"], "(b)", show_legend=False)
    axes[1].set_xlabel("time since calibration start (min)")
    fig.subplots_adjust(hspace=0.36)
    fig.savefig(OUT / "fig2_trials.png", dpi=DPI)
    plt.close(fig)
    return "fig2_trials.png"


# Sl. 3: gdje u spektru pobuda pomjera obiljezje

def fig_bands():
    model = Model()
    curves = {}
    for key, prefix in (("paper", "airflow_change_paper"),
                        ("paper", "ambient_speech"),
                        ("tone", "constant_tone_1khz")):
        session = Session(model, key)
        rows = [model.z(session.features[i]) - session.center for i in session.det
                if (r := session.eligible(i)) and r["condition"].startswith(prefix)]
        curves[prefix] = (np.median(np.array(rows), axis=0), len(rows))

    fig, ax = plt.subplots(figsize=(COL_W, 1.55))
    styles = {
        "airflow_change_paper": dict(color="black", lw=0.9, ls="-", label="paper strip"),
        "ambient_speech": dict(color="0.55", lw=0.9, ls="-", label="speech"),
        "constant_tone_1khz": dict(color="black", lw=0.8, ls=(0, (3, 1.5)), label="1 kHz tone"),
    }
    for prefix, (median, n) in curves.items():
        style = dict(styles[prefix])
        style["label"] += f" ({n})"
        ax.plot(BAND_CENTERS_HZ, median, **style)
    ax.axhline(0, color="0.6", lw=0.5)
    empty = model.empty
    ax.plot(BAND_CENTERS_HZ[empty], np.full(len(empty), -27), "|", color="black",
            ms=3.5, mew=0.6, label="empty bands")
    ax.set_xscale("log")
    ax.set_xlim(10, 4000)
    ax.set_ylim(-30, 50)
    ax.set_xlabel("band center frequency (Hz)")
    ax.set_ylabel("median $z - c$")
    ax.grid(True, color="0.88", lw=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, ncol=2, handlelength=1.8,
              columnspacing=0.8, borderaxespad=0.2, labelspacing=0.2)
    fig.savefig(OUT / "fig3_bands.png", dpi=DPI)
    plt.close(fig)
    return "fig3_bands.png"


if __name__ == "__main__":
    print(fig_system())
    print(fig_trials())
    print(fig_bands())
