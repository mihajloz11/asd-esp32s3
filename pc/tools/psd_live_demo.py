"""Zivi demo samostalnog PSD detektora na ESP32-S3, sa zvukom preko zvucnika.

SCENARIO (isti kao benchmark, samo akusticki umjesto iz fajla):
  Matrica u firmveru je naucena SAMO na SOURCE ventilatorima. Pusta se TARGET
  ventilator - drugi fizicki primjerak koji model nikad nije cuo.

  1. WARM   ~15 s  pocinje se puštati normalan rad novog ventilatora
  2. CAL    100 s  plocica mjeri centar tog primjerka (10 klipova po 10 s)
  3. DET           i dalje normalan rad  -> ne smije biti alarma
                   pa ANOMALIJA          -> mora se javiti alarm
                   pa opet normalan rad  -> alarm se mora povuci

Klipovi za kalibraciju i klipovi za ocjenu se NE PREKLAPAJU.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/psd_live_demo.py --port COM4
    ../.venv/Scripts/python.exe tools/psd_live_demo.py --port COM4 --prepare-only
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

# Serijski tok sa ploce je UTF-8; Windows konzola po defaultu nije (pouka P12).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
FAN = ROOT / "data" / "dcase2026_dev" / "fan"
OUT = ROOT / "results" / "demo_audio"
SR = 16000

CAL_CLIPS = 14        # 140 s: pokriva 15 s warm-up + 100 s kalibracije + rezerva
DET_NORMAL = 5        # klipova normalnog rada prije kvara
DET_ANOM = 10         # klipova anomalije
DET_RECOVER = 5       # klipova normalnog rada poslije


def build_audio(seed: int = 0, speed: str | None = None) -> tuple[Path, Path]:
    """Dvije WAV datoteke od TARGET klipova; kalibracija i ocjena razdvojene.

    speed=None uzima sve brzine. Klipovi se nadovezuju, pa spoj dva klipa
    RAZLICITE brzine (spd_1/2/3) zvuci kao nagla promjena rezima — detektor to
    ispravno prijavi, ali je to artefakt montaze, ne kvar. speed="spd_1"
    ogranicava demo na jednu brzinu, sto odgovara stvarnom ventilatoru koji
    radi u ustaljenom rezimu."""
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    pat = f"*{speed}.wav" if speed else "*.wav"
    normals = sorted(list(FAN.glob(f"train/*target_train_normal{pat}")) +
                     list(FAN.glob(f"test/*target_test_normal{pat}")))
    anomalies = sorted(FAN.glob(f"test/*target_test_anomaly{pat}"))
    if not normals or not anomalies:
        raise SystemExit("nema target klipova — provjeri data/dcase2026_dev/fan")
    need = CAL_CLIPS + DET_NORMAL + DET_RECOVER
    if len(normals) < need:
        raise SystemExit(f"treba {need} normalnih target klipova, ima {len(normals)}"
                         + (f" za {speed}" if speed else ""))

    idx = rng.permutation(len(normals))
    cal_files = [normals[i] for i in idx[:CAL_CLIPS]]
    det_norm = [normals[i] for i in idx[CAL_CLIPS:CAL_CLIPS + DET_NORMAL]]
    det_rec = [normals[i] for i in
               idx[CAL_CLIPS + DET_NORMAL:CAL_CLIPS + DET_NORMAL + DET_RECOVER]]
    det_anom = [anomalies[i] for i in rng.permutation(len(anomalies))[:DET_ANOM]]

    def cat(paths: list[Path]) -> np.ndarray:
        parts = []
        for p in paths:
            y, sr = sf.read(p, dtype="float32", always_2d=True)
            assert sr == SR, f"{p}: {sr} Hz"
            parts.append(y[:, 0])
        return np.concatenate(parts)

    # Normalizacija na zajednicki vrh: zvucnik mora biti dovoljno glasan, a
    # odnos normalnog i anomalnog se NE smije mijenjati pojacanjem — zato ista
    # skala za obje datoteke.
    cal_sig = cat(cal_files)
    det_sig = np.concatenate([cat(det_norm), cat(det_anom), cat(det_rec)])
    gain = 0.9 / max(np.abs(cal_sig).max(), np.abs(det_sig).max())

    cal_path = OUT / "demo_cal_normal.wav"
    det_path = OUT / "demo_detect.wav"
    sf.write(cal_path, cal_sig * gain, SR, subtype="PCM_16")
    sf.write(det_path, det_sig * gain, SR, subtype="PCM_16")

    (OUT / "demo_manifest.txt").write_text(
        "KALIBRACIJA (normalan rad novog ventilatora):\n" +
        "".join(f"  {p.name}\n" for p in cal_files) +
        f"\nDETEKCIJA — normalan {DET_NORMAL}x10 s:\n" +
        "".join(f"  {p.name}\n" for p in det_norm) +
        f"\nDETEKCIJA — ANOMALIJA {DET_ANOM}x10 s:\n" +
        "".join(f"  {p.name}\n" for p in det_anom) +
        f"\nDETEKCIJA — oporavak {DET_RECOVER}x10 s:\n" +
        "".join(f"  {p.name}\n" for p in det_rec) +
        f"\nzajednicko pojacanje: {gain:.4f}\n", encoding="utf-8")

    print(f"kalibracioni zvuk: {cal_path.name}  {len(cal_sig)/SR:.0f} s")
    print(f"zvuk za detekciju: {det_path.name}  {len(det_sig)/SR:.0f} s "
          f"({DET_NORMAL*10} s normalno | {DET_ANOM*10} s ANOMALIJA | "
          f"{DET_RECOVER*10} s normalno)")
    print(f"spisak klipova:    {OUT / 'demo_manifest.txt'}")
    return cal_path, det_path


DET_RE = re.compile(r"DET (\d+) score=([-\d.]+) lo=[-\d.]+ hi=([-\d.]+) led=\d+ "
                    r"anom=(\d+) total_anom=\d+ (\w+)")

# --- neprekidan snimak: kalibracija i ocjena iz JEDNOG toka zvuka ---
# Uredjaj potrosi ~116 s do pocetka detekcije (15,4 s cekanja + 10 x 9,98 s
# kalibracije), pa prvih 12 klipova pokriva kalibraciju. Tek ono STO SLIJEDI
# se ocjenjuje — normalni klipovi u 120-180 s uredjaj NIJE cuo u kalibraciji.
CONT_CAL = 12        # 120 s: warm-up + kalibracija
CONT_NORM = 6        # 60 s normalnog rada koji kalibracija nije vidjela
CONT_ANOM = 12       # 120 s anomalije


def build_continuous(seed: int, speed: str | None) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    pat = f"*{speed}.wav" if speed else "*.wav"
    normals = sorted(list(FAN.glob(f"train/*target_train_normal{pat}")) +
                     list(FAN.glob(f"test/*target_test_normal{pat}")))
    anomalies = sorted(FAN.glob(f"test/*target_test_anomaly{pat}"))
    need = CONT_CAL + CONT_NORM
    if len(normals) < need or len(anomalies) < CONT_ANOM:
        raise SystemExit(f"treba {need} normalnih i {CONT_ANOM} anomalnih, "
                         f"ima {len(normals)} i {len(anomalies)}")

    idx = rng.permutation(len(normals))
    cal = [normals[i] for i in idx[:CONT_CAL]]
    norm = [normals[i] for i in idx[CONT_CAL:need]]
    anom = [anomalies[i] for i in rng.permutation(len(anomalies))[:CONT_ANOM]]

    def cat(paths):
        out = []
        for p in paths:
            y, sr = sf.read(p, dtype="float32", always_2d=True)
            assert sr == SR
            out.append(y[:, 0])
        return np.concatenate(out)

    sig = np.concatenate([cat(cal), cat(norm), cat(anom)])
    sig = sig * (0.9 / np.abs(sig).max())
    path = OUT / "demo_continuous.wav"
    sf.write(path, sig, SR, subtype="PCM_16")

    (OUT / "demo_continuous_manifest.txt").write_text(
        f"0-{CONT_CAL*10} s  KALIBRACIJA (uredjaj slusa i uci centar):\n" +
        "".join(f"  {p.name}\n" for p in cal) +
        f"\n{CONT_CAL*10}-{(CONT_CAL+CONT_NORM)*10} s  NORMALAN RAD, "
        f"kalibracija ga NIJE cula (mjeri lazne alarme):\n" +
        "".join(f"  {p.name}\n" for p in norm) +
        f"\n{(CONT_CAL+CONT_NORM)*10}-{(CONT_CAL+CONT_NORM+CONT_ANOM)*10} s  "
        f"ANOMALIJA (mjeri odziv):\n" +
        "".join(f"  {p.name}\n" for p in anom), encoding="utf-8")

    print(f"neprekidan snimak: {path.name}  {len(sig)/SR:.0f} s")
    print(f"  0-{CONT_CAL*10} s      normalan rad — tu se uredjaj kalibrise")
    print(f"  {CONT_CAL*10}-{(CONT_CAL+CONT_NORM)*10} s    normalan rad koji nije cuo — ne smije alarmirati")
    print(f"  {(CONT_CAL+CONT_NORM)*10}-{(CONT_CAL+CONT_NORM+CONT_ANOM)*10} s   ANOMALIJA — mora alarmirati")
    return path


def main() -> None:
    global CAL_CLIPS, DET_NORMAL, DET_ANOM, DET_RECOVER
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM4")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--speed", default=None,
                    help="spd_1|spd_2|spd_3 — jedna brzina, bez skoka na spoju")
    ap.add_argument("--tag", default="", help="sufiks za log i ocjenu")
    ap.add_argument("--cal-clips", type=int, default=CAL_CLIPS)
    ap.add_argument("--det-normal", type=int, default=DET_NORMAL)
    ap.add_argument("--det-anom", type=int, default=DET_ANOM)
    ap.add_argument("--det-recover", type=int, default=DET_RECOVER)
    ap.add_argument("--prepare-only", action="store_true")
    args = ap.parse_args()

    CAL_CLIPS, DET_NORMAL = args.cal_clips, args.det_normal
    DET_ANOM, DET_RECOVER = args.det_anom, args.det_recover

    cal_path, det_path = build_audio(args.seed, args.speed)
    if args.prepare_only:
        return

    import serial  # pyserial

    log_path = ROOT / "results" / f"psd_live_demo_log{args.tag}.txt"
    log = open(log_path, "w", encoding="utf-8")
    ser = serial.Serial(args.port, args.baud, timeout=1)

    # reset ploce da demo krene od nule (RTS->EN, DTR->GPIO0)
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.15)
    ser.setRTS(False)
    time.sleep(0.3)
    ser.reset_input_buffer()

    t0 = time.time()
    print(f"\n[{args.port}] resetovano, pustam kalibracioni zvuk...")
    winsound.PlaySound(str(cal_path), winsound.SND_FILENAME | winsound.SND_ASYNC)

    phase = "warm"
    det_rows: list[tuple[int, float, float, int, str]] = []
    det_start_t = None

    while True:
        raw = ser.readline()
        if not raw:
            if phase == "det" and det_start_t and time.time() - det_start_t > 260:
                break
            continue
        line = raw.decode("utf-8", errors="replace").rstrip()
        stamp = f"{time.time() - t0:7.1f}s"
        log.write(f"{stamp} {line}\n")
        log.flush()

        if "KALIBRACIJA:" in line and phase == "warm":
            phase = "cal"
            print(f"[{stamp}] --- kalibracija pocela (100 s) ---")
        elif line.startswith("CAL "):
            print(f"[{stamp}] {line}")
        elif "kalibracija gotova" in line or "LOO score" in line or "PRAG" in line:
            print(f"[{stamp}] {line}")
        elif "DETEKCIJA RADI" in line and phase != "det":
            phase = "det"
            det_start_t = time.time()
            print(f"[{stamp}] --- detekcija pocela, pustam zvuk sa kvarom ---")
            winsound.PlaySound(str(det_path),
                               winsound.SND_FILENAME | winsound.SND_ASYNC)
        elif line.startswith("DET "):
            m = DET_RE.search(line)
            if m:
                i, score, thr, alarm, verdict = (int(m.group(1)), float(m.group(2)),
                                                 float(m.group(3)), int(m.group(4)),
                                                 m.group(5))
                elapsed = time.time() - det_start_t if det_start_t else 0.0
                expect = ("normalno" if elapsed < DET_NORMAL * 10 + 5 else
                          "ANOMALIJA" if elapsed < (DET_NORMAL + DET_ANOM) * 10 + 5
                          else "normalno")
                det_rows.append((i, score, thr, alarm, expect))
                mark = "ALARM" if alarm else "-"
                print(f"[{stamp}] DET {i:2d} score={score:8.2f} prag={thr:7.2f} "
                      f"{mark:5s} ocekivano={expect}")
                if elapsed > (DET_NORMAL + DET_ANOM + DET_RECOVER) * 10 + 20:
                    break
        elif line.strip():
            print(f"[{stamp}] {line}")

    ser.close()
    log.close()
    winsound.PlaySound(None, winsound.SND_PURGE)

    print(f"\n=== OCJENA ===  (log: {log_path})")
    norm = [r for r in det_rows if r[4] == "normalno"]
    anom = [r for r in det_rows if r[4] == "ANOMALIJA"]
    fp = sum(r[3] for r in norm)
    tp = sum(r[3] for r in anom)
    print(f"normalni prozori:  {len(norm):2d}, laznih alarma: {fp}")
    print(f"anomalni prozori:  {len(anom):2d}, uhvaceno:      {tp}")
    if norm:
        print(f"score normalno:  sredina {np.mean([r[1] for r in norm]):8.1f} "
              f"opseg {min(r[1] for r in norm):.0f}..{max(r[1] for r in norm):.0f}")
    if anom:
        print(f"score anomalija: sredina {np.mean([r[1] for r in anom]):8.1f} "
              f"opseg {min(r[1] for r in anom):.0f}..{max(r[1] for r in anom):.0f}")

    # AUC koji je uredjaj stvarno postigao PREKO ZVUCNIKA I MIKROFONA — to je
    # druga brojka od benchmark AUC-a nad ciftim digitalnim zvukom.
    if norm and anom:
        from sklearn.metrics import roc_auc_score
        y = [0] * len(norm) + [1] * len(anom)
        s = [r[1] for r in norm] + [r[1] for r in anom]
        print(f"\nAUC na uredjaju, preko zraka: {roc_auc_score(y, s):.3f} "
              f"({len(norm)} normalnih vs {len(anom)} anomalnih prozora)")
    ok = anom and tp > 0 and fp == 0
    print(f"REZULTAT: {'PROSLO' if ok else 'vidjeti log'}")


if __name__ == "__main__":
    main()
