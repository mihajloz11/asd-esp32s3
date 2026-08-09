"""Neprekidan test: JEDAN snimak, kalibracija na prvom dijelu, detekcija dalje.

Scenario koji je najblizi stvarnoj primjeni: uredjaj se ukljuci pored masine
koja radi ISPRAVNO, sam se kalibrise na njoj, i nastavi da slusa isti tok zvuka.
Poslije nekog vremena masina se pokvari i to mora da prijavi.

Snimak (300 s, sve TARGET ventilator koji model nikad nije cuo):
    0-120 s    normalan rad — uredjaj tu odradi cekanje i kalibraciju
  120-180 s    normalan rad koji kalibracija NIJE cula -> ne smije alarmirati
  180-300 s    ANOMALIJA -> mora alarmirati

Kalibracioni i ocjenjivani normalni klipovi se ne preklapaju, pa lazni alarmi
nisu mjereni na zvuku koji je uredjaj vec ucio.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/psd_continuous_test.py --port COM4
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import winsound
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from psd_live_demo import (CONT_ANOM, CONT_CAL, CONT_NORM,  # noqa: E402
                           build_continuous)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
# Ocjena moze biti "normal", "ALARM" ili "iznad praga" — dakle sa razmakom,
# zato .+? a ne \S+ (inace granicni prozori tiho ispadnu iz analize).
DET_RE = re.compile(r"DET (\d+) score=([\d.]+) lo=[\d.]+ hi=([\d.]+) led=\d+ "
                    r"anom=(\d+) total_anom=(\d+) .+? \(uzastopnih=(\d+) "
                    r"nivo=([-\d.]+)")

NORM_END = (CONT_CAL + CONT_NORM) * 10.0     # 180 s
ANOM_END = (CONT_CAL + CONT_NORM + CONT_ANOM) * 10.0  # 300 s
WIN = 9.984                                   # trajanje prozora uredjaja


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM4")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--speed", default=None)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    wav = build_continuous(args.seed, args.speed)

    import serial  # pyserial
    log_path = ROOT / "results" / f"psd_continuous_log{args.tag}.txt"
    log = open(log_path, "w", encoding="utf-8")
    ser = serial.Serial(args.port, args.baud, timeout=1)
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.15)
    ser.setRTS(False)
    time.sleep(0.3)
    ser.reset_input_buffer()

    t0 = time.time()
    print(f"\n[{args.port}] reset + pustam snimak (jedan tok, {ANOM_END:.0f} s)")
    winsound.PlaySound(str(wav), winsound.SND_FILENAME | winsound.SND_ASYNC)

    det_t0 = None
    rows = []
    while time.time() - t0 < ANOM_END + 90:
        raw = ser.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", errors="replace").rstrip()
        stamp = f"{time.time() - t0:7.1f}s"
        log.write(f"{stamp} {line}\n")
        log.flush()

        if "DETEKCIJA RADI" in line and det_t0 is None:
            det_t0 = time.time() - t0
            print(f"[{stamp}] kalibracija gotova, detekcija krece "
                  f"({det_t0:.0f} s u snimak)")
            continue
        if any(k in line for k in ("LOOALL", "PRAG", "LOO score", "KALIBRACIJA:")):
            print(f"[{stamp}] {line.split(': ', 1)[-1]}")
            continue

        m = DET_RE.search(line)
        if not m or det_t0 is None:
            continue
        i, score, thr, alarm = (int(m.group(1)), float(m.group(2)),
                                float(m.group(3)), int(m.group(4)))
        db = float(m.group(7))
        # gdje se ovaj prozor nalazi U SNIMKU
        end = det_t0 + i * WIN
        start = end - WIN
        if end <= NORM_END:
            truth = "normal"
        elif start >= NORM_END and end <= ANOM_END:
            truth = "ANOMALIJA"
        elif start >= ANOM_END:
            truth = "(kraj snimka)"
        else:
            truth = "prelaz"
        rows.append((i, start, end, score, thr, alarm, truth, db))
        mark = "  <<< ALARM" if alarm else ""
        print(f"[{stamp}] prozor {i:2d}  snimak {start:5.0f}-{end:5.0f}s  "
              f"score={score:8.1f}  prag={thr:7.1f}  {truth:13s}{mark}")
        if start >= ANOM_END + WIN:
            break

    ser.close()
    log.close()
    winsound.PlaySound(None, winsound.SND_PURGE)

    norm = [r for r in rows if r[6] == "normal"]
    anom = [r for r in rows if r[6] == "ANOMALIJA"]
    print(f"\n=== OCJENA ===   log: {log_path}")
    print(f"normalan rad (kalibracija ga nije cula): {len(norm)} prozora, "
          f"laznih alarma {sum(r[5] for r in norm)}")
    print(f"anomalija:                               {len(anom)} prozora, "
          f"alarma {sum(r[5] for r in anom)}")
    if norm:
        s = [r[3] for r in norm]
        print(f"  score normalno : medijana {np.median(s):8.1f}  "
              f"opseg {min(s):.0f}..{max(s):.0f}")
    if anom:
        s = [r[3] for r in anom]
        print(f"  score anomalija: medijana {np.median(s):8.1f}  "
              f"opseg {min(s):.0f}..{max(s):.0f}")
    if norm and anom:
        from sklearn.metrics import roc_auc_score
        y = [0] * len(norm) + [1] * len(anom)
        sc = [r[3] for r in norm] + [r[3] for r in anom]
        print(f"  AUC preko zraka: {roc_auc_score(y, sc):.3f}")
        first = next((r for r in anom if r[5]), None)
        if first:
            print(f"  prvi alarm: {first[1] - NORM_END:.0f} s poslije pocetka kvara")


if __name__ == "__main__":
    main()
