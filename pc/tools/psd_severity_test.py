"""Koliko kvar mora biti izrazen da ga uredjaj cuje kroz zvucnik i mikrofon?

Ranije je izmjereno da akusticki kanal pravi rasipanje reda velicine vece od
DCASE anomalije (docs/uredjaj/hardver-verifikacija.md). Ovaj test odgovara na pitanje
KOLIKO grublji kvar mora biti da bi prosao kroz taj kanal.

Na stvaran snimak ispravnog ventilatora dodaje se KONTROLISAN kvar rastuce
jacine: periodican udar jednom po obrtaju (strano tijelo koje kaci lopaticu)
plus tonska komponenta na istoj frekvenciji (disbalans). Jacina se izrazava u
dB u odnosu na RMS signala.

VAZNO: kvar je sintetican i tako se i prijavljuje. Cilj nije zamijeniti test sa
stvarnim ventilatorom nego izmjeriti PRAG OSJETLJIVOSTI lanca — na kojoj jacini
alarm proradi. Osnovni zvuk je stvaran snimak stvarnog ventilatora.

Snimak (320 s):
    0-120 s   ispravan rad — kalibracija
  120-160 s   ispravan rad (osnova, ne smije alarmirati)
  160-200 s   kvar -30 dB   (jedva cujno)
  200-240 s   kvar -24 dB
  240-280 s   kvar -18 dB
  280-320 s   kvar -12 dB   (jasno cujno)

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/psd_severity_test.py --port COM4
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import winsound
from pathlib import Path

import numpy as np
import soundfile as sf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
FAN = ROOT / "data" / "dcase2026_dev" / "fan"
OUT = ROOT / "results" / "demo_audio"
SR = 16000
CAL_CLIPS = 12          # 120 s kalibracije
BASE_CLIPS = 4          # 40 s ispravnog rada kao osnova
SEV_DB = [-30, -24, -18, -12]
SEV_CLIPS = 4           # 40 s po jacini
ROT_HZ = 24.0           # ~1440 o/min, tipicno za ventilator

# "iznad praga" sadrzi razmak, pa .+? a ne \S+ (vidi psd_continuous_test.py)
DET_RE = re.compile(r"DET (\d+) score=([\d.]+) lo=[\d.]+ hi=([\d.]+) led=\d+ "
                    r"anom=(\d+) total_anom=\d+ .+? \(uzastopnih=(\d+) "
                    r"nivo=([-\d.]+)")
WIN = 9.984


def add_fault(y: np.ndarray, db: float, rng) -> np.ndarray:
    """Periodican udar jednom po obrtaju — strano tijelo koje kaci lopaticu.

    PAZNJA (P14): prva verzija je udarima dodavala sinuse na 24 i 48 Hz sa
    fiksnim amplitudama 0,5 i 0,25. Ti sinusi nose ~95 % energije kvara, pa su
    poslije normalizacije udarci ostali zanemarljivi — a bas ispod ~150 Hz
    zvucnik laptopa ne reprodukuje. Izmjereno: kvar je bio +9,2 dB samo u
    10-50 Hz i 0 dB svuda drugdje, dakle do mikrofona nije stiglo nista.
    Zato je tonska komponenta uklonjena; udarci su sirokopojasni i mjereno
    prezive kanal sa 82,5 % (tools/psd_channel_probe.py).
    """
    n = len(y)
    rms = float(np.sqrt(np.mean(y * y))) + 1e-12
    amp = rms * (10.0 ** (db / 20.0))

    fault = np.zeros(n, dtype=np.float64)
    period = int(SR / ROT_HZ)
    click_len = int(0.004 * SR)                      # 4 ms
    env = np.exp(-np.arange(click_len) / (0.0008 * SR))
    for start in range(0, n - click_len, period):
        fault[start:start + click_len] += rng.standard_normal(click_len) * env

    fault *= amp / (float(np.sqrt(np.mean(fault * fault))) + 1e-12)
    return (y + fault).astype(np.float32)


def build(seed: int) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    normals = sorted(list(FAN.glob("train/*target_train_normal*.wav")) +
                     list(FAN.glob("test/*target_test_normal*.wav")))
    need = CAL_CLIPS + BASE_CLIPS + len(SEV_DB) * SEV_CLIPS
    if len(normals) < need:
        raise SystemExit(f"treba {need} normalnih target klipova, ima {len(normals)}")
    idx = rng.permutation(len(normals))
    pick = [normals[i] for i in idx[:need]]

    def cat(paths):
        return np.concatenate([sf.read(p, dtype="float32", always_2d=True)[0][:, 0]
                               for p in paths])

    parts = [cat(pick[:CAL_CLIPS]), cat(pick[CAL_CLIPS:CAL_CLIPS + BASE_CLIPS])]
    off = CAL_CLIPS + BASE_CLIPS
    for db in SEV_DB:
        seg = cat(pick[off:off + SEV_CLIPS])
        parts.append(add_fault(seg, db, rng))
        off += SEV_CLIPS

    sig = np.concatenate(parts)
    sig = sig * (0.9 / np.abs(sig).max())
    path = OUT / "demo_severity.wav"
    sf.write(path, sig, SR, subtype="PCM_16")
    print(f"snimak sa rastucim kvarom: {path.name}  {len(sig)/SR:.0f} s")
    return path


def region(start: float, end: float) -> str:
    cal = CAL_CLIPS * 10.0
    base = cal + BASE_CLIPS * 10.0
    if end <= base:
        return "ispravan"
    for k, db in enumerate(SEV_DB):
        lo = base + k * SEV_CLIPS * 10.0
        hi = lo + SEV_CLIPS * 10.0
        if start >= lo and end <= hi:
            return f"kvar {db} dB"
    return "prelaz"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM4")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--seed", type=int, default=2)
    args = ap.parse_args()

    wav = build(args.seed)
    total = (CAL_CLIPS + BASE_CLIPS + len(SEV_DB) * SEV_CLIPS) * 10.0

    import serial
    log_path = ROOT / "results" / "psd_severity_log.txt"
    log = open(log_path, "w", encoding="utf-8")
    ser = serial.Serial(args.port, args.baud, timeout=1)
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.15)
    ser.setRTS(False)
    time.sleep(0.3)
    ser.reset_input_buffer()

    t0 = time.time()
    print(f"\n[{args.port}] reset + pustam snimak ({total:.0f} s)")
    winsound.PlaySound(str(wav), winsound.SND_FILENAME | winsound.SND_ASYNC)

    det_t0 = None
    rows = []
    while time.time() - t0 < total + 90:
        raw = ser.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", errors="replace").rstrip()
        log.write(f"{time.time()-t0:7.1f}s {line}\n")
        log.flush()
        if "DETEKCIJA RADI" in line and det_t0 is None:
            det_t0 = time.time() - t0
            print(f"kalibracija gotova na {det_t0:.0f} s snimka")
            continue
        if "PRAG" in line:
            print(line.split(": ", 1)[-1])
            continue
        m = DET_RE.search(line)
        if not m or det_t0 is None:
            continue
        i, score, thr, alarm = (int(m.group(1)), float(m.group(2)),
                                float(m.group(3)), int(m.group(4)))
        end = det_t0 + i * WIN
        start = end - WIN
        reg = region(start, end)
        rows.append((reg, score, alarm))
        print(f"prozor {i:2d}  {start:5.0f}-{end:5.0f}s  score={score:8.1f}  "
              f"prag={thr:7.1f}  {reg:12s}{'  <<< ALARM' if alarm else ''}")
        if start >= total:
            break

    ser.close()
    log.close()
    winsound.PlaySound(None, winsound.SND_PURGE)

    print("\n=== PRAG OSJETLJIVOSTI ===")
    print(f"{'dionica':<14s} {'prozora':>8s} {'alarma':>7s} {'medijana score':>15s}")
    for reg in ["ispravan"] + [f"kvar {d} dB" for d in SEV_DB]:
        sel = [r for r in rows if r[0] == reg]
        if not sel:
            continue
        print(f"{reg:<14s} {len(sel):>8d} {sum(r[2] for r in sel):>7d} "
              f"{np.median([r[1] for r in sel]):>15.1f}")
    hit = [r[0] for r in rows if r[2] and r[0].startswith("kvar")]
    print(f"\nnajslabiji kvar koji je podigao alarm: {hit[0] if hit else 'nijedan'}")


if __name__ == "__main__":
    main()
