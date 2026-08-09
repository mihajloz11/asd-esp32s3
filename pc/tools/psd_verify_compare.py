"""PC<->uredjaj provjera PSD front-enda na ZIVOM mikrofonu.

Uredjaj (build ASD_PSD_VERIFY=1) snimi 10 s zivog zvuka, izracuna 96-dim
psd_shape TACNO kao zivi rad (streaming) i posalje i feature i sam snimak.
Ovaj alat ponovi racun nad ISTIM uzorcima i uporedi.

Zasto je to potrebno pored pc/tests/test_psd_features_c.py: taj test dokazuje
da se C i Python slazu na DCASE WAV-u, ali ne i da lanac I2S -> shift -> PCM
daje uredjaju iste uzorke. Ovdje se zatvara i taj korak.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/psd_verify_compare.py --port COM4
"""
from __future__ import annotations

import argparse
import base64
import re
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.bench_periodicity import periodic_features  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
BEGIN_RE = re.compile(rb"MICWAV_BEGIN sr=(\d+) n=(\d+) bytes=(\d+) fnv1a=([0-9a-f]+)")
FEAT_RE = re.compile(rb"PSDFEAT segments=(\d+) compute_us=(\d+) dropped=(\d+)")
B64_RE = re.compile(rb"^[A-Za-z0-9+/=]+$")


def fnv1a(data: bytes) -> int:
    h = 0x811C9DC5
    for b in data:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM4")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()

    import serial  # pyserial

    ser = serial.Serial(args.port, args.baud, timeout=1)
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.15)
    ser.setRTS(False)
    ser.reset_input_buffer()

    dev_feat = None
    header = None
    parts: list[bytes] = []
    seg = comp_us = dropped = None
    collecting = False
    t0 = time.time()

    print(f"[{args.port}] cekam snimak sa uredjaja (do {args.timeout:.0f} s)...")
    while time.time() - t0 < args.timeout:
        line = ser.readline()
        if not line:
            continue
        s = line.strip()
        if s.startswith(b"PSDVEC "):
            dev_feat = np.array([float(x) for x in s.split()[1:]], dtype=np.float64)
            print(f"primljen feature sa uredjaja: {len(dev_feat)} traka")
            continue
        m = FEAT_RE.search(s)
        if m:
            seg, comp_us, dropped = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            print(f"segmenata={seg} racun={comp_us/1000:.0f} ms dropped={dropped}")
            continue
        m = BEGIN_RE.search(s)
        if m:
            header = (int(m.group(1)), int(m.group(2)), int(m.group(3)),
                      int(m.group(4), 16))
            collecting = True
            parts = []
            print(f"snimak: sr={header[0]} n={header[1]} bytes={header[2]}")
            continue
        if b"MICWAV_END" in s:
            break
        if collecting and B64_RE.match(s):
            parts.append(s)
    ser.close()

    if dev_feat is None:
        sys.exit("nije stigao PSDVEC — je li build sa ASD_PSD_VERIFY=1?")
    if header is None or not parts:
        sys.exit("nije stigao snimak (MICWAV_BEGIN/END)")

    pcm_bytes = base64.b64decode(b"".join(parts))
    sr, n, nbytes, want_hash = header
    if len(pcm_bytes) != nbytes:
        sys.exit(f"duzina snimka {len(pcm_bytes)} != najavljeno {nbytes}")
    got_hash = fnv1a(pcm_bytes)
    if got_hash != want_hash:
        sys.exit(f"FNV-1a se ne slaze: {got_hash:08x} != {want_hash:08x} "
                 "— snimak je ostecen u prenosu (vidi P4)")
    print(f"FNV-1a provjera snimka OK ({got_hash:08x})")

    pcm = np.frombuffer(pcm_bytes, dtype="<i2")
    wav_path = ROOT / "results" / "psd_verify_live.wav"
    sf.write(wav_path, pcm, sr, subtype="PCM_16")

    pc_feat = periodic_features(wav_path)["psd_shape"].astype(np.float64)
    diff = np.abs(pc_feat - dev_feat)
    denom = max(float(np.max(np.abs(pc_feat))), 1e-12)
    print(f"\nsnimak zapisan: {wav_path}")
    print(f"max |PC - uredjaj|      = {diff.max():.3e}")
    print(f"relativno na opseg      = {diff.max()/denom:.3e}")
    print(f"srednja apsolutna razlika = {diff.mean():.3e}")
    ok = diff.max() < 1e-2
    print(f"\nREZULTAT: {'PROSLO' if ok else 'PAO — razlika je prevelika'}")


if __name__ == "__main__":
    main()
