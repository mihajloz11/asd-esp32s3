"""Zasto je K1 odbio kalibraciju: LOO skorovi razlozeni po trakama.

`CAL_SUMMARY` kaze samo `loo_mean/sd/cv/range`. Kad kapija padne, to ne kaze
KOJI klip je kriv ni KOJA traka ga je odvela -- a bez toga se popravlja naslijepo
(23.08.2026 su tri kalibracije zaredom pale, i sve tri na istoj traci).

Ovaj alat cita `FEATURE96` redove iz `serial.log`-a (razvojni
`ASD_RESEARCH_TELEMETRY` build) i ponavlja tacno onu matematiku koju radi
firmver u `psd_live.c`:

  z      = (feature - norm_mean) / norm_std
  centar = srednja vrijednost svih z, umanjena za sam klip (leave-one-out)
  skor   = delta^T * P * delta,  delta = z_i - centar_bez_i

Doprinos jedne trake je `delta_i * (P delta)_i` i sabira se tacno u skor, pa se
vidi koliko koja traka nosi. Provjereno na runovima 23.08.2026: `loo_mean` i
`loo_sd` se poklapaju sa firmverskim `CAL_SUMMARY` na dvije decimale.

Alat je **dijagnostika, ne kapija**. Ne mijenja nijedan prag i ne pise nista u
`results/`.

    python pc/tools/diag_calibration_loo.py results/physical_fan/run_.../serial.log
    python pc/tools/diag_calibration_loo.py prije=a/serial.log poslije=b/serial.log
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "models" / "fan_psd_shape.npz"

# Iste granice kao u `psd_features_c.c`: 96 logaritamskih traka 10-4000 Hz.
BAND_LOW_HZ = 10.0
BAND_HIGH_HZ = 4000.0
BANDS = 96

FEATURE_RE = re.compile(
    r"FEATURE96 .*?\bphase=(?P<phase>\S+)\s.*?\bvalues=(?P<values>\S+)$")


def band_hz(index: int) -> float:
    return BAND_LOW_HZ * (BAND_HIGH_HZ / BAND_LOW_HZ) ** (index / (BANDS - 1))


def load_calibration_clips(path: Path, phase: str = "CAL") -> np.ndarray:
    """FEATURE96 vektori jedne faze; `serial.log` nosi host prefiks pa se cijepa."""
    clips: list[np.ndarray] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("\t")[-1]
        if not line.startswith("FEATURE96 "):
            continue
        match = FEATURE_RE.search(line)
        if match is None or match.group("phase") != phase:
            continue
        values = np.fromstring(match.group("values"), sep=",", dtype=np.float64)
        # Isprepletan red daje pogresan broj vrijednosti; takav se ne racuna.
        if values.size == BANDS:
            clips.append(values)
    return np.array(clips)


def leave_one_out(clips: np.ndarray, mean: np.ndarray, std: np.ndarray,
                  precision: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Skor po klipu i doprinos svake trake tom skoru."""
    count = len(clips)
    z = (clips - mean) / std
    centre = z.mean(axis=0)
    scores = np.empty(count)
    contributions = np.empty((count, clips.shape[1]))
    for index in range(count):
        without = (centre * count - z[index]) / (count - 1)
        delta = z[index] - without
        contributions[index] = delta * (precision @ delta)
        scores[index] = contributions[index].sum()
    return scores, contributions


def report(name: str, path: Path, top: int) -> None:
    model = np.load(MODEL_PATH)
    clips = load_calibration_clips(path)
    if len(clips) < 3:
        print(f"{name}: samo {len(clips)} CAL FEATURE96 redova -- "
              f"treba razvojni build sa ASD_RESEARCH_TELEMETRY\n")
        return
    scores, contributions = leave_one_out(
        clips, model["mean"].astype(np.float64), model["std"].astype(np.float64),
        model["precision"].astype(np.float64))

    # Firmver racuna `sd` sa ddof=1, pa se i ovdje koristi isti da bi se `cv`
    # moglo direktno porediti sa `CAL_SUMMARY` iz loga.
    sd = scores.std(ddof=1)
    print(f"=== {name} ===  klipova {len(clips)}")
    print("  loo:  " + "  ".join(f"{value:7.1f}" for value in scores))
    print(f"  mean {scores.mean():7.1f}   sd {sd:7.1f}   "
          f"cv {sd / scores.mean():5.3f}   raspon {np.ptp(scores):7.1f}")
    if len(clips) != 10:
        # Firmver uvijek racuna nad N_CAL=10; manje znaci da su neki FEATURE96
        # redovi stigli pokvareni (P20), pa se brojke NE porede sa CAL_SUMMARY.
        print(f"  PAZNJA: firmver racuna nad 10 klipova, ovdje ih je {len(clips)} "
              f"-- {10 - len(clips)} FEATURE96 reda nije stiglo cijelo")

    worst = int(np.argmax(scores))
    share = contributions[worst]
    print(f"  najveci je klip {worst + 1} ({scores[worst]:.0f}); trake koje ga prave:")
    for index in sorted(np.argsort(-share)[:top]):
        print(f"    traka {index:>2}  ~{band_hz(index):7.0f} Hz   "
              f"doprinos {share[index]:8.1f}   "
              f"({100 * share[index] / scores[worst]:4.1f}%)")

    # Traka koja se najvise mrda kroz klipove je obicno i ona koja obori cv.
    spread = clips.std(axis=0)
    noisiest = int(np.argmax(spread))
    print(f"  najnemirnija traka kroz sve klipove: {noisiest} "
          f"(~{band_hz(noisiest):.0f} Hz), sd {spread[noisiest]:.2f} dB")
    print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "logs", nargs="+", metavar="[IME=]serial.log",
        help="jedan ili vise logova; sa `ime=` se ispisuje pod tim imenom")
    parser.add_argument("--top", type=int, default=6,
                        help="koliko traka se ispisuje za najgori klip")
    args = parser.parse_args(argv)
    if not MODEL_PATH.exists():
        print(f"nedostaje model: {MODEL_PATH}")
        return 2
    for item in args.logs:
        name, separator, path = item.partition("=")
        if not separator:
            name, path = Path(item).parent.name or item, item
        report(name, Path(path), args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
