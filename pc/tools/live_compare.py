"""PC vs uredjaj na ZIVOM zvuku iz mikrofona.

Uredjaj (firmware build sa ASD_LIVE_CAPTURE=1) snimi jedan klip, izracuna
score svojim lancem, i posalje isti snimak preko UART-a:

    LIVESCORE score=... thr=... n_vec=... feat_ms=... inf_ms=... dropped=...
    MICWAV_BEGIN sr=16000 n=160000 bytes=320000 fnv1a=xxxxxxxx
    <base64>
    MICWAV_END

Ovaj skript to primi, snimi WAV, i boduje ISTE uzorke PC pipeline-om
(features -> standardizacija -> int8 TFLite), pa uporedi.

Razlika u odnosu na compare_eval.py: tamo su klipovi iz dataseta stizali na
uredjaj kao gotovi bajtovi preko flash particije. Ovdje ulaz nastaje NA
uredjaju, iz mikrofona — pa se provjerava i put I2S -> PCM -> featuri.

Upotreba (iz pc/, sa ESP-IDF python okruzenjem zbog pyserial):
    python tools/live_compare.py --port COM4 --tag fan_tiny32_s0
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import features  # noqa: E402
from asd.quantize import TFLitePredict  # noqa: E402

try:
    import serial  # pyserial
except ImportError:
    sys.exit("nema pyserial — pokreni iz ESP-IDF okruzenja (export.ps1)")

ROOT = Path(__file__).resolve().parents[2]

BEGIN_RE = re.compile(rb"MICWAV_BEGIN sr=(\d+) n=(\d+) bytes=(\d+) fnv1a=([0-9a-f]+)")
SCORE_RE = re.compile(
    rb"LIVESCORE score=([-\d.]+) thr=([-\d.]+) n_vec=(\d+) "
    rb"feat_ms=(\d+) inf_ms=(\d+) dropped=(\d+)"
)
FULL_LINE_RE = re.compile(rb"^[A-Za-z0-9+/]{76}$")
LAST_LINE_RE = re.compile(rb"^[A-Za-z0-9+/]{2,75}={0,2}$")


def fnv1a(data: bytes) -> int:
    h = 2166136261
    for b in data:
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


def capture(port: str, baud: int, timeout: float):
    ser = serial.Serial(port, baud, timeout=0.2)
    ser.dtr = False
    ser.rts = True
    time.sleep(0.15)
    ser.rts = False

    dev = None
    hdr = None
    parts: list[bytes] = []
    rejected = 0
    buf = b""
    done = False
    t0 = time.time()

    while time.time() - t0 < timeout and not done:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            continue
        buf += chunk
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            line = raw.strip()

            if hdr is None:
                m = SCORE_RE.search(line)
                if m:
                    dev = {
                        "score": float(m.group(1)),
                        "thr": float(m.group(2)),
                        "n_vec": int(m.group(3)),
                        "feat_ms": int(m.group(4)),
                        "inf_ms": int(m.group(5)),
                        "dropped": int(m.group(6)),
                    }
                    print(f">>> uredjaj: score={dev['score']:.6f} n_vec={dev['n_vec']} "
                          f"feat={dev['feat_ms']} ms inf={dev['inf_ms']} ms "
                          f"dropped={dev['dropped']}")
                    continue
                m = BEGIN_RE.search(line)
                if m:
                    hdr = (int(m.group(1)), int(m.group(2)),
                           int(m.group(3)), int(m.group(4), 16))
                    print(f">>> primam snimak: {hdr[1]} uzoraka @ {hdr[0]} Hz "
                          f"({hdr[1] / hdr[0]:.1f} s)...")
                    continue
                sys.stdout.write(line.decode("utf-8", "replace") + "\n")
                sys.stdout.flush()
                continue

            if b"MICWAV_END" in line:
                done = True
                break
            if FULL_LINE_RE.match(line) or LAST_LINE_RE.match(line):
                parts.append(line)
            elif line:
                rejected += 1

    ser.close()
    if hdr is None:
        sys.exit("nije stigao MICWAV_BEGIN — je li build sa ASD_LIVE_CAPTURE=1?")
    if not done:
        sys.exit("timeout — nije stigao MICWAV_END")
    if rejected:
        print(f"upozorenje: odbaceno {rejected} linija koje nisu base64")

    sr, n_samples, n_bytes, crc_dev = hdr
    pcm = base64.b64decode(b"".join(parts))
    if len(pcm) != n_bytes:
        sys.exit(f"GRESKA: duzina {len(pcm)} != {n_bytes} — prenos pomjeren, ponovi")
    if fnv1a(pcm) != crc_dev:
        sys.exit("GRESKA: kontrolna suma ne valja — prenos ostecen, ponovi")
    print(f"kontrolna suma OK ({crc_dev:08x})")
    return dev, sr, n_samples, pcm


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM4")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--tag", default="fan_tiny32_s0", help="model kao u firmware-u")
    ap.add_argument("--out", default="../results/live_clip.wav")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()

    dev, sr, n_samples, pcm = capture(args.port, args.baud, args.timeout)

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)
    print(f"snimak: {out}")

    meta = json.loads((ROOT / "models" / f"{args.tag}_meta.json").read_text())
    mean = np.array(meta["mean"], dtype=np.float32)
    std = np.array(meta["std"], dtype=np.float32)
    pred = TFLitePredict((ROOT / "models" / f"{args.tag}_int8.tflite").read_bytes())

    vecs = features.wav_to_vectors(str(out))
    xn = (vecs - mean) / std
    rec = pred(xn)
    pc_score = float(np.mean(np.mean((xn - rec) ** 2, axis=1)))

    print("\n--- PC vs uredjaj, ZIVI mikrofon ---")
    print(f"  PC score      : {pc_score:.8f}   ({vecs.shape[0]} vektora)")
    print(f"  uredjaj score : {dev['score']:.8f}   ({dev['n_vec']} vektora)")

    if vecs.shape[0] != dev["n_vec"]:
        print(f"  NAPOMENA: razlicit broj vektora ({vecs.shape[0]} vs {dev['n_vec']})")

    rel = abs(pc_score - dev["score"]) / max(abs(pc_score), 1e-12)
    print(f"  relativna razlika: {rel:.2e}")
    print("  ->", "POKLAPA SE" if rel < 1e-3 else "NE POKLAPA SE — provjeriti lanac")

    x = np.frombuffer(pcm, dtype="<i2").astype(np.float64)
    print(f"\n  snimak: rms={x.std():.1f} peak={int(np.abs(x).max())} "
          f"dc={x.mean():.1f}  prag modela={dev['thr']:.5f}")


if __name__ == "__main__":
    main()
