"""Hvata mic-test snimak sa ESP32-S3 preko serijskog porta i pravi WAV.

Firmware: build sa ASD_MIC_TEST=1 (main/mic_test.c) izbacuje
    MICWAV_BEGIN sr=16000 n=80000 bytes=160000 fnv1a=xxxxxxxx
    <base64 linije, tacno 76 znakova osim zadnje>
    MICWAV_END

Upotreba (iz pc/, sa ESP-IDF python okruzenjem zbog pyserial):
    python tools/mic_capture.py --port COM4 --out ../results/mic_test.wav

Prenos se provjerava: linije koje nisu ciste base64 duzine 76 se odbacuju i
prijavljuju, a dekodovani bajtovi se verifikuju FNV-1a sumom sa ploce. Bez
tog poklapanja WAV se NE snima — pokvaren snimak izgleda kao realan sum i
lako se pogresno protumaci kao problem sa mikrofonom.
"""
from __future__ import annotations

import argparse
import base64
import re
import struct
import sys
import time
import wave
from pathlib import Path

try:
    import serial  # pyserial
except ImportError:
    sys.exit("nema pyserial — pokreni iz ESP-IDF okruzenja (export.ps1) ili: pip install pyserial")

BEGIN_RE = re.compile(rb"MICWAV_BEGIN sr=(\d+) n=(\d+) bytes=(\d+) fnv1a=([0-9a-f]+)")
FULL_LINE_RE = re.compile(rb"^[A-Za-z0-9+/]{76}$")
LAST_LINE_RE = re.compile(rb"^[A-Za-z0-9+/]{2,75}={0,2}$")


def fnv1a(data: bytes) -> int:
    h = 2166136261
    for b in data:
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM4")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--out", default="../results/mic_test.wav")
    ap.add_argument("--timeout", type=float, default=120.0, help="ukupno cekanje [s]")
    ap.add_argument("--no-reset", action="store_true", help="ne resetuj plocu pri otvaranju")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    ser = serial.Serial(args.port, args.baud, timeout=0.2)
    if not args.no_reset:
        ser.dtr = False
        ser.rts = True
        time.sleep(0.15)
        ser.rts = False

    sr = n_samples = n_bytes = crc_dev = None
    b64_parts: list[bytes] = []
    rejected: list[bytes] = []
    buf = b""
    done = False
    t0 = time.time()

    # Citanje bajt po bajt sa rucnim rezanjem linija — readline() sa timeoutom
    # zna vratiti pola linije, sto bi pokvarilo strogu validaciju duzine.
    while time.time() - t0 < args.timeout and not done:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            continue
        buf += chunk
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            line = raw.strip()

            if sr is None:
                m = BEGIN_RE.search(line)
                if m:
                    sr, n_samples = int(m.group(1)), int(m.group(2))
                    n_bytes, crc_dev = int(m.group(3)), int(m.group(4), 16)
                    print(f"\n>>> snimak: {n_samples} uzoraka @ {sr} Hz "
                          f"({n_samples / sr:.1f} s), {n_bytes} B — primam...")
                else:
                    sys.stdout.write(line.decode("utf-8", "replace") + "\n")
                    sys.stdout.flush()
                continue

            if b"MICWAV_END" in line:
                done = True
                break
            if FULL_LINE_RE.match(line) or LAST_LINE_RE.match(line):
                b64_parts.append(line)
            elif line:
                rejected.append(line)

    ser.close()

    if sr is None:
        sys.exit("nije nadjen MICWAV_BEGIN — je li firmware buildovan sa ASD_MIC_TEST=1?")
    if not done:
        sys.exit("timeout — nije stigao MICWAV_END")

    if rejected:
        print(f"\nodbaceno {len(rejected)} linija koje nisu base64 (prve 3):")
        for r in rejected[:3]:
            print(f"  {r[:100]!r}")

    pcm = base64.b64decode(b"".join(b64_parts))
    print(f"dekodovano {len(pcm)} B (ocekivano {n_bytes})")

    if len(pcm) != n_bytes:
        sys.exit(f"GRESKA: duzina se ne poklapa ({len(pcm)} vs {n_bytes}) — prenos je pomjeren, "
                 f"WAV nije snimljen. Ponovi hvatanje.")

    crc_pc = fnv1a(pcm)
    if crc_pc != crc_dev:
        sys.exit(f"GRESKA: kontrolna suma ne valja (ploca {crc_dev:08x}, PC {crc_pc:08x}) — "
                 f"WAV nije snimljen. Ponovi hvatanje.")
    print(f"kontrolna suma OK ({crc_pc:08x})")

    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)

    vals = struct.unpack(f"<{n_samples}h", pcm)
    peak = max(abs(v) for v in vals)
    dc = sum(vals) / n_samples
    rms = (sum((v - dc) ** 2 for v in vals) / n_samples) ** 0.5

    print(f"\nsnimljeno: {out}")
    print(f"  uzoraka={n_samples}  peak={peak}  rms={rms:.1f}  dc={dc:.1f}")
    if peak == 0:
        print("  SVE NULE — mikrofon ne salje podatke (SD linija, L/R->GND, VDD)")


if __name__ == "__main__":
    main()
