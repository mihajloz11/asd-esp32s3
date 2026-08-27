"""Pravi slike za master rad iz stvarnih podataka iz repozitorijuma.

Nijedna brojka na slikama nije upisana rucno. Izvori:

  data/dcase2026_dev/fan/train/*.wav                spektar u dvije rezolucije
  results/physical_fan/run_20260827T213148_*/       trasa mjerenja sa papiricem
  results/physical_fan/run_20260827T220338_*/       trasa mjerenja sa tonom
  docs/put-do-modela.md                             AUC po fazama razvoja

Izlaz: radovi/master-rad/slike/*.png

    ..\\..\\.venv\\Scripts\\python.exe make_slike.py
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

RUN_PAPIRIC = REPO / ("results/physical_fan/"
                      "run_20260827T213148_fan02_guided25-20260827-v3recovery5d")
RUN_TON = REPO / ("results/physical_fan/"
                  "run_20260827T220338_fan02_tone-validation-20260827-final")

SIRINA = 6.3          # inca; oko 16 cm, staje u marginu rada
DPI = 300

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.linewidth": 0.7,
    "grid.linewidth": 0.4,
    "lines.linewidth": 1.1,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})


def ucitaj_run(putanja: Path):
    redovi = list(csv.DictReader(
        open(putanja / "detections.csv", encoding="utf-8")))
    return {
        "t": np.array([float(x["elapsed_s"]) for x in redovi]),
        "score": np.array([float(x["score"]) for x in redovi]),
        "thr": np.array([float(x["threshold"]) for x in redovi]),
        "alarm": np.array([int(x["alarm"]) for x in redovi]),
        "hold": np.array([int(x["hold"]) for x in redovi]),
        "uslov": [x["condition"] for x in redovi],
    }


def prag_izlaska(putanja: Path) -> float:
    """Cita threshold_exit iz PROFILE zapisa u serijskom logu."""
    for red in open(putanja / "serial.log", encoding="utf-8", errors="ignore"):
        if "PROFILE protocol" in red and "threshold_exit=" in red:
            for polje in red.split():
                if polje.startswith("threshold_exit="):
                    return float(polje.split("=", 1)[1])
    raise SystemExit(f"nema threshold_exit u {putanja}")


# --------------------------------------------------------------------------
def sl_sistem() -> None:
    """Blok sema: sta se uci na racunaru, a sta se mjeri na licu mjesta."""
    fig, ax = plt.subplots(figsize=(SIRINA, 2.9))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 46)
    ax.axis("off")

    def kutija(x, y, w, h, tekst, boja):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.6",
            linewidth=0.9, edgecolor="black", facecolor=boja))
        ax.text(x + w / 2, y + h / 2, tekst, ha="center", va="center",
                fontsize=8, linespacing=1.35)

    def strelica(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9,
            linewidth=0.8, color="black"))

    ax.text(23, 43, "РАЧУНАР  (једном, унапред)", ha="center", fontsize=8.5,
            fontweight="bold")
    ax.text(72, 43, "УРЕЂАЈ  (на лицу места)", ha="center", fontsize=8.5,
            fontweight="bold")
    ax.plot([47, 47], [1, 41], color="0.5", linewidth=0.8, linestyle="--")

    kutija(2, 27, 42, 11,
           "990 исправних снимака\nDCASE 2026, вентилатор", "#eef2f7")
    kutija(2, 13, 42, 11,
           "стандардизација  +  Ledoit–Wolf\nматрица прецизности  96×96", "#eef2f7")
    kutija(2, 1, 42, 9, "уграђене табеле  37 632 B", "#dce6f1")
    strelica(23, 27, 23, 24.4)
    strelica(23, 13, 23, 10.4)

    kutija(52, 33, 46, 8, "INMP441  →  I2S  →  прозор 10 s", "#f7f2ee")
    kutija(52, 24, 46, 7.5, "Welch 8192  →  96 трака  →  z", "#f7f2ee")
    kutija(52, 14.5, 46, 8,
           "локални центар  c   (10 исечака)\nпраг  (44 + 22 прозора)", "#f1e6dc")
    kutija(52, 6, 46, 7,
           "s = (z − c)ᵀ P (z − c)   →   3 узастопна", "#f7f2ee")
    kutija(52, 0.2, 46, 4.5, "НОРМАЛНО  /  ЗАДРЖАНО  /  АНОМАЛИЈА", "#dce6f1")
    for y1, y2 in ((33, 31.9), (24, 22.7), (14.5, 13.2), (6, 4.9)):
        strelica(75, y1, 75, y2)
    strelica(44, 5.5, 52, 9.5)

    fig.savefig(OUT / "sl_sistem.png", dpi=DPI)
    plt.close(fig)


def sl_sema() -> None:
    """Sema povezivanja mikrofona, tastera i dioda."""
    fig, ax = plt.subplots(figsize=(SIRINA, 2.7))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 40)
    ax.axis("off")

    ax.add_patch(FancyBboxPatch((4, 9), 26, 22, boxstyle="round,pad=0.6",
                                linewidth=1.0, edgecolor="black",
                                facecolor="#eef2f7"))
    ax.text(17, 28, "INMP441", ha="center", fontsize=9, fontweight="bold")
    ax.add_patch(FancyBboxPatch((62, 7), 32, 29, boxstyle="round,pad=0.6",
                                linewidth=1.0, edgecolor="black",
                                facecolor="#eef2f7"))
    ax.text(78, 33, "ESP32-S3-WROOM-1", ha="center", fontsize=9,
            fontweight="bold")

    veze = [
        ("VDD", "3V3", 25.0),
        ("GND", "GND", 22.0),
        ("SCK", "GPIO 4", 19.0),
        ("WS", "GPIO 5", 16.0),
        ("SD", "GPIO 6", 13.0),
        ("L/R", "GND", 10.0),
    ]
    for lijevo, desno, y in veze:
        ax.text(28, y, lijevo, ha="right", va="center", fontsize=7.5)
        ax.text(64, y, desno, ha="left", va="center", fontsize=7.5)
        ax.plot([30, 62], [y, y], color="black", linewidth=0.7)

    ax.text(50, 1.6, "GPIO 10 → тастер → GND        "
            "GPIO 2 → зелена LED        GPIO 11 → црвена LED",
            ha="center", fontsize=7.5)
    ax.text(17, 6.4, "100 nF + 10 µF уз VDD", ha="center", fontsize=7,
            style="italic")
    ax.text(17, 4.2, "везе краће од 10 cm", ha="center", fontsize=7,
            style="italic")

    fig.savefig(OUT / "sl_sema.png", dpi=DPI)
    plt.close(fig)


def sl_rezolucija() -> None:
    """Isti snimak ventilatora pri razmaku 15,6 Hz i 1,95 Hz."""
    import soundfile as sf
    from scipy.signal import welch

    klipovi = sorted((REPO / "data/dcase2026_dev/fan/train").glob("*.wav"))
    if not klipovi:
        print("  preskocen sl_rezolucija: nema raspakovan DCASE fan skup")
        return
    x, fs = sf.read(klipovi[0])
    if x.ndim > 1:
        x = x[:, 0]

    fig, ax = plt.subplots(figsize=(SIRINA, 2.6))
    for n, boja, stil in ((1024, "0.62", "-"), (8192, "#1f4e79", "-")):
        f, p = welch(x, fs=fs, nperseg=n, noverlap=n // 2)
        maska = (f >= 20) & (f <= 400)
        ax.plot(f[maska], 10 * np.log10(p[maska] + 1e-20), stil, color=boja,
                linewidth=1.0 if n == 1024 else 1.1,
                label=f"N = {n},  Δf = {fs / n:.2f} Hz")
    ax.set_xlabel("фреквенција [Hz]")
    ax.set_ylabel("густина снаге [dB]")
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, loc="upper right")
    fig.savefig(OUT / "sl_rezolucija.png", dpi=DPI)
    plt.close(fig)


def sl_napredak() -> None:
    """Najbolji izmjereni AUC po fazama razvoja (izvor: docs/put-do-modela.md)."""
    faze = ["1. мреже", "2. mel\nстатистика", "3. оцењивач",
            "4. обележје", "5. шест\nалтернатива"]
    auc = [0.530, 0.674, 0.716, 0.864, 0.857]

    fig, ax = plt.subplots(figsize=(SIRINA, 2.5))
    boje = ["0.75", "0.68", "0.60", "#1f4e79", "0.60"]
    ax.bar(range(len(faze)), auc, color=boje, width=0.6, edgecolor="black",
           linewidth=0.6)
    for i, v in enumerate(auc):
        ax.text(i, v + 0.012, f"{v:.3f}".replace(".", ","), ha="center",
                fontsize=8)
    ax.axhline(0.80, color="#c00000", linewidth=0.9, linestyle="--")
    ax.text(4.45, 0.808, "циљ 0,80", color="#c00000", fontsize=7.5, ha="right")
    ax.set_xticks(range(len(faze)))
    ax.set_xticklabels(faze)
    ax.set_ylim(0.4, 0.93)
    ax.set_ylabel("AUC")
    ax.grid(axis="y", alpha=0.3)
    fig.savefig(OUT / "sl_napredak.png", dpi=DPI)
    plt.close(fig)


def _trasa(putanja: Path, ime: str, granice: list[tuple[str, str]]) -> None:
    d = ucitaj_run(putanja)
    exit_thr = prag_izlaska(putanja)
    t = (d["t"] - d["t"][0]) / 60.0

    fig, ax = plt.subplots(figsize=(SIRINA, 2.8))
    ax.semilogy(t, d["score"], color="0.35", linewidth=0.9, zorder=3)
    normalno = (d["hold"] == 0) & (d["alarm"] == 0)
    ax.scatter(t[normalno], d["score"][normalno], s=9, color="#1f4e79",
               zorder=4, label="поуздан прозор")
    drzano = d["hold"] == 1
    ax.scatter(t[drzano], d["score"][drzano], s=16, facecolors="none",
               edgecolors="#c07000", linewidths=0.9, zorder=5,
               label="непоуздан прозор")
    alarm = d["alarm"] == 1
    ax.scatter(t[alarm], d["score"][alarm], s=16, color="#c00000", marker="^",
               zorder=6, label="аларм")

    ax.axhline(d["thr"][0], color="#c00000", linewidth=0.9, linestyle="--")
    ax.text(t[-1], d["thr"][0] * 1.12, "праг уласка", color="#c00000",
            fontsize=7, ha="right")
    ax.axhline(exit_thr, color="#1f7a1f", linewidth=0.9, linestyle=":")
    ax.text(t[-1], exit_thr * 0.72, "праг изласка", color="#1f7a1f",
            fontsize=7, ha="right")

    for uslov, oznaka in granice:
        gdje = [i for i, c in enumerate(d["uslov"]) if c == uslov]
        if not gdje:
            continue
        x = t[gdje[0]]
        ax.axvline(x, color="0.75", linewidth=0.6, zorder=1)
        ax.text(x, 0.985, oznaka, transform=ax.get_xaxis_transform(),
                rotation=90, fontsize=6.5, color="0.35", va="top", ha="right")

    ax.set_xlabel("време од почетка надзора [min]")
    ax.set_ylabel("оцена одступања")
    ax.grid(alpha=0.25, which="both")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.19),
              ncol=3, handletextpad=0.3, columnspacing=1.4)
    fig.savefig(OUT / ime, dpi=DPI)
    plt.close(fig)


def sl_run_papiric() -> None:
    _trasa(RUN_PAPIRIC, "sl_run_papiric.png", [
        ("normal_baseline", "основа"),
        ("airflow_change_paper_1", "папирић 1"),
        ("recovery_normal_1", "опоравак 1"),
        ("airflow_change_paper_2", "папирић 2"),
        ("recovery_normal_2", "опоравак 2"),
        ("airflow_change_paper_3", "папирић 3"),
        ("recovery_normal_3", "опоравак 3"),
        ("ambient_speech", "разговор"),
        ("ambient_door", "врата"),
        ("final_recovery", "завршни опоравак"),
    ])


def sl_run_ton() -> None:
    _trasa(RUN_TON, "sl_run_ton.png", [
        ("normal_baseline", "основа"),
        ("constant_tone_1khz", "тон укључен"),
        ("recovery_after_tone", "ознака опоравка"),
    ])


def main() -> None:
    for f in (sl_sistem, sl_sema, sl_rezolucija, sl_napredak,
              sl_run_papiric, sl_run_ton):
        f()
        print("  ", f.__name__)
    print("slike u", OUT)


if __name__ == "__main__":
    main()
