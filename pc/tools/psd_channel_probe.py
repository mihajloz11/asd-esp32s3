"""Sta akusticki kanal uradi udarnom kvaru — mjerenje, ne pretpostavka.

Digitalno, front-end vidi udarni kvar odlicno i monotono (check_fault_type.py:
-12 dB daje score 10448 naspram 82 za ispravan rad). Preko zvucnika isti kvar
ne podigne alarm. Ovaj alat mjeri gdje se signal gubi.

Postupak: pusti se sonda, uredjaj (build ASD_PSD_VERIFY=1) snimi 10 s ZIVOG
zvuka i posalje snimak na PC. Isto se uradi za cistu i za pokvarenu sondu, obje
sa ISTIM pojacanjem i istim RMS-om, pa se poredi:

  - digitalni psd_shape sonde   (ono sto model treba da vidi)
  - psd_shape snimka sa mikrofona (ono sto stvarno vidi)
  - Mahalanobis score za oba

Upotreba (iz pc/, uz ASD_PSD_VERIFY=1 na ploci):
    ../.venv/Scripts/python.exe tools/psd_channel_probe.py --port COM4
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import winsound
from pathlib import Path

import numpy as np
import soundfile as sf
from sklearn.covariance import LedoitWolf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data  # noqa: E402
from tools.bench_periodicity import periodic_features  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
FAN = ROOT / "data" / "dcase2026_dev" / "fan"
OUT = ROOT / "results" / "demo_audio"
BEGIN_RE = re.compile(rb"MICWAV_BEGIN sr=(\d+) n=(\d+) bytes=(\d+) fnv1a=([0-9a-f]+)")
B64_RE = re.compile(rb"^[A-Za-z0-9+/=]+$")


def fnv1a(b: bytes) -> int:
    h = 0x811C9DC5
    for x in b:
        h = ((h ^ x) * 0x01000193) & 0xFFFFFFFF
    return h


def capture(port: str, baud: int, wav: Path, dest: Path, timeout: float = 120.0):
    import serial
    ser = serial.Serial(port, baud, timeout=1)
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.15)
    ser.setRTS(False)
    ser.reset_input_buffer()
    winsound.PlaySound(str(wav), winsound.SND_FILENAME | winsound.SND_ASYNC)

    header, parts, collecting = None, [], False
    t0 = time.time()
    while time.time() - t0 < timeout:
        line = ser.readline()
        if not line:
            continue
        s = line.strip()
        m = BEGIN_RE.search(s)
        if m:
            header = (int(m.group(1)), int(m.group(2)), int(m.group(3)),
                      int(m.group(4), 16))
            collecting, parts = True, []
            continue
        if b"MICWAV_END" in s:
            break
        if collecting and B64_RE.match(s):
            parts.append(s)
    ser.close()
    winsound.PlaySound(None, winsound.SND_PURGE)
    if not header or not parts:
        raise SystemExit(f"nije stigao snimak za {wav.name} "
                         "— je li build sa ASD_PSD_VERIFY=1?")
    pcm = base64.b64decode(b"".join(parts))
    if fnv1a(pcm) != header[3]:
        raise SystemExit("FNV-1a ne odgovara — snimak ostecen u prenosu")
    sf.write(dest, np.frombuffer(pcm, "<i2"), header[0], subtype="PCM_16")
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM4")
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args()

    z = np.load(ROOT / "results" / "cache" / "fan_periodicity.npz")
    psd = z["psd_shape"]
    train = data.list_clips(FAN, "train")
    test = data.list_clips(FAN, "test")
    clips = train + test
    n_tr = len(train)
    dom = np.array([c.domain for c in clips])
    is_test = np.arange(len(clips)) >= n_tr
    src = (dom == "source") & ~is_test
    X = psd[src]
    mu, sd = X.mean(0), X.std(0) + 1e-8
    P = LedoitWolf().fit((X - mu) / sd).precision_

    probes = {t: OUT / f"probe_{t}.wav" for t in ("clean", "m12")}
    for t, p in probes.items():
        if not p.exists():
            raise SystemExit(f"nema {p} — napravi sonde prije mjerenja")

    rec = {}
    for tag, wav in probes.items():
        dest = ROOT / "results" / f"probe_rec_{tag}.wav"
        print(f"pustam {wav.name} i snimam mikrofonom...")
        rec[tag] = capture(args.port, args.baud, wav, dest)
        print(f"  snimljeno: {dest.name}")

    feats = {}
    for tag in probes:
        feats[f"digitalno_{tag}"] = periodic_features(probes[tag])["psd_shape"]
        feats[f"snimljeno_{tag}"] = periodic_features(rec[tag])["psd_shape"]

    # centar iz DIGITALNE ciste sonde za digitalne, iz SNIMLJENE ciste za snimke
    def score(f, center):
        d = (f - mu) / sd - center
        return float(d @ P @ d)

    c_dig = (feats["digitalno_clean"] - mu) / sd
    c_rec = (feats["snimljeno_clean"] - mu) / sd

    print("\nMahalanobis score, kvar naspram sopstvene ciste osnove:")
    print(f"  digitalno: {score(feats['digitalno_m12'], c_dig):10.0f}")
    print(f"  snimljeno: {score(feats['snimljeno_m12'], c_rec):10.0f}")

    lo = np.geomspace(10.0, 4000.0, 97)[:-1]
    hi = np.geomspace(10.0, 4000.0, 97)[1:]
    d_dig = feats["digitalno_m12"] - feats["digitalno_clean"]
    d_rec = feats["snimljeno_m12"] - feats["snimljeno_clean"]

    print("\npromjena po traci koju kvar pravi (log10 snage):")
    print(f"{'traka':>5} {'Hz':>13} {'digitalno':>10} {'snimljeno':>10} {'ostalo %':>9}")
    order = np.argsort(np.abs(d_dig))[::-1][:15]
    for b in sorted(order):
        keep = 100.0 * d_rec[b] / d_dig[b] if abs(d_dig[b]) > 1e-9 else 0.0
        print(f"{b:>5} {lo[b]:>6.0f}-{hi[b]:<6.0f} {d_dig[b]:>10.3f} "
              f"{d_rec[b]:>10.3f} {keep:>8.0f}%")

    keep_all = float(np.sum(np.abs(d_rec)) / (np.sum(np.abs(d_dig)) + 1e-12))
    print(f"\nukupno preziviljelo kroz kanal: {keep_all*100:.1f} % promjene")

    p = ROOT / "results" / "channel_probe.json"
    p.write_text(json.dumps({
        "score_digitalno": score(feats["digitalno_m12"], c_dig),
        "score_snimljeno": score(feats["snimljeno_m12"], c_rec),
        "delta_digitalno": d_dig.tolist(),
        "delta_snimljeno": d_rec.tolist(),
        "udio_prezivio": keep_all,
    }, indent=2), encoding="utf-8")
    print(f"zapisano: {p}")


if __name__ == "__main__":
    main()
