r"""Duga proba laznih alarma: prag postavljen na 2. minutu, mjeri se do 60.

PITANJE NA KOJE ODGOVARA. `PLAN.md` u "sta NIJE dokazano" navodi lazne alarme
na duze vrijeme -- najduzi prolaz dosad je bio ~6 minuta. Ovdje se mjeri koliko
lazni alarmi zaista traju kroz cio sat, uz prag koji je zamrznut poslije
kalibracije i koji se vise NE osvjezava.

STA OVAJ TEST JESTE. Zvuk je snimak ispravnog TARGET ventilatora (drugi fizicki
primjerak, koji model nikad nije cuo) pusten preko zvucnika. Detekcioni dio je
petlja od 8 klipova koje kalibracija NIJE cula. Posto se isti zvuk ponavlja,
svaka promjena score-a kroz sat dolazi od AKUSTICKOG KANALA i UREDJAJA, ne od
sadrzaja zvuka -- isto razdvajanje kao 06.08. kad je hladan reset pokazao da
drift dolazi od okruzenja, a ne od plocice.

STA OVAJ TEST NIJE. Nije fizicki ventilator i ne smije se tako zvati u radu.
Nije ni mjera otpornosti na nepoznat normalan zvuk, jer se detekcioni snimak
ponavlja. Mjerodavan test ostaje stvarni ventilator sa stvarnim kvarom.

Upotreba (iz korijena repozitorija):

    .venv\Scripts\python.exe pc\tools\false_alarm_test.py --port COM4 --minutes 60
    .venv\Scripts\python.exe pc\tools\false_alarm_test.py --prepare-only

Trazi firmware buildovan sa ASD_PSD_LIVE i flesiran na plocicu.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import time
import winsound
from datetime import datetime
from pathlib import Path

import numpy as np
import serial
import soundfile as sf

# Serijski tok sa ploce je UTF-8; Windows konzola po defaultu nije (pouka P12).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
FAN = ROOT / "data" / "dcase2026_dev" / "fan"
FIRMWARE = ROOT / "firmware" / "esp32s3_asd"
OUT_ROOT = ROOT / "results" / "false_alarm"
SR = 16000
CLIP_S = 10

# Od protokola v1.3.0 uredjaj prvo ceka taster. Prva sesija poslije ukljucenja
# krece sama tek kad istekne grace iz `START_GRACE_MS` u psd_live.c, pa je
# racunica:
#
#   1 s pred-roll + ~2 s boota + 10 s cekanja + 15,4 s WAIT + 100 s kalibracije
#   = ~128,5 s
#
# Kalibracioni snimak je namjerno duzi, da jos svira kad kalibracija zavrsi --
# prelaz na detekcioni snimak se tada radi na granici klipa, a ne u tisini.
# 14 klipova = 140 s, dakle ~11 s rezerve. Manje od toga je opasno: ako
# kalibracioni snimak stane prije zadnjeg CAL klipa, taj klip snimi tisinu,
# padne ispod -60 dBFS i fail-closed gate prekine prolaz.
#
# Gornja granica je tvrda: spd_1 ima 21 target normalan klip, a detekciona
# petlja mora zadrzati najmanje MIN_DET_CLIPS klipova koje kalibracija NIJE
# cula. Zato se grace i drzi kratkim.
CAL_CLIPS = 14
START_GRACE_S = 10.0
PRE_ROLL_S = 1.0
BOOT_S = 2.1
WAIT_S = 15.4
CAL_PHASE_S = 100.0
MIN_DET_CLIPS = 6       # ispod ovoga petlja postaje besmisleno kratka

# Sve sto uredjaj potrosi prije nego kalibracija zavrsi.
DEVICE_LEAD_S = PRE_ROLL_S + BOOT_S + START_GRACE_S + WAIT_S + CAL_PHASE_S


def build_audio(speed: str, out_dir: Path) -> tuple[Path, Path, dict]:
    """Dva snimka od TARGET normalnih klipova, jedne brzine, zajednicko pojacanje.

    Jedna brzina je namjerna: spoj klipova razlicitih brzina (spd_1/2/3) zvuci
    kao nagla promjena rezima i detektor to ispravno prijavi, ali je to artefakt
    montaze, ne kvar. Sa jednom brzinom svaki spoj klipova -- ukljucujuci sav
    petlje -- ostaje unutar istog radnog rezima.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    pat = f"*{speed}.wav"
    normals = sorted(list(FAN.glob(f"train/*target_train_normal{pat}")) +
                     list(FAN.glob(f"test/*target_test_normal{pat}")))
    if len(normals) < CAL_CLIPS + MIN_DET_CLIPS:
        raise SystemExit(
            f"treba najmanje {CAL_CLIPS + MIN_DET_CLIPS} target normalnih klipova "
            f"za {speed}, ima {len(normals)}")

    cal_files = normals[:CAL_CLIPS]
    det_files = normals[CAL_CLIPS:]

    def cat(paths: list[Path]) -> np.ndarray:
        parts = []
        for p in paths:
            y, sr = sf.read(p, dtype="float32", always_2d=True)
            if sr != SR:
                raise SystemExit(f"{p}: {sr} Hz, ocekivano {SR}")
            parts.append(y[:, 0])
        return np.concatenate(parts)

    cal_sig = cat(cal_files)
    det_sig = cat(det_files)
    # Fail-closed provjera trajanja: bolje odmah stati nego potrositi prolaz i
    # tek na kraju otkriti da je zadnji CAL klip snimio tisinu.
    cal_seconds = len(cal_sig) / SR
    if cal_seconds < DEVICE_LEAD_S:
        raise SystemExit(
            f"kalibracioni snimak je {cal_seconds:.0f} s, a uredjaju treba "
            f"{DEVICE_LEAD_S:.0f} s do kraja kalibracije; povecaj CAL_CLIPS ili "
            f"skrati START_GRACE_MS u psd_live.c")
    # Isto pojacanje za oba snimka: da promjena nivoa izmedju kalibracije i
    # detekcije ne pomjeri score sama po sebi.
    gain = float(0.9 / max(np.abs(cal_sig).max(), np.abs(det_sig).max()))

    cal_path = out_dir / f"fa_cal_{speed}.wav"
    det_path = out_dir / f"fa_det_{speed}.wav"
    sf.write(cal_path, cal_sig * gain, SR, subtype="PCM_16")
    sf.write(det_path, det_sig * gain, SR, subtype="PCM_16")

    manifest = {
        "speed": speed,
        "gain": gain,
        "cal_seconds": len(cal_sig) / SR,
        "det_loop_seconds": len(det_sig) / SR,
        "cal_clips": [p.name for p in cal_files],
        "det_clips": [p.name for p in det_files],
        "overlap": sorted(set(p.name for p in cal_files) &
                          set(p.name for p in det_files)),
    }
    if manifest["overlap"]:
        raise SystemExit("kalibracioni i detekcioni klipovi se preklapaju")
    return cal_path, det_path, manifest


# --- serijski tok -----------------------------------------------------------

PROTOCOL_VERSION = "asd-quality-v1.6.0"

THR_RE = re.compile(r"ADAPTTHR n=(\d+) mean=([-\d.eE+]+) sd=([-\d.eE+]+).*?thr=([-\d.eE+]+)")
PRESENCE_RE = re.compile(
    r"PRESENCE protocol=(\S+) level_mean_dbfs=([-\d.eE+]+) margin_db=([-\d.eE+]+) "
    r"gate_dbfs=([-\d.eE+]+) min_consecutive=(\d+)")
DET_RE = re.compile(
    r"DET (\d+) score=([-\d.eE+]+) lo=\S+ hi=([-\d.eE+]+) led=(\d+) anom=(\d+) "
    r"total_anom=(\d+) (.+?) \(uzastopnih=(\d+) nivo=([-\d.eE+]+) dBFS")
QUALITY_RE = re.compile(r"QUALITY protocol=(\S+) phase=(\S+) index=(\d+) total=(\d+) result=(\S+)")
QUALITY_NUM_RE = re.compile(r"(\w+)=([-\d.eE+]+)")
WAIT_RE = re.compile(r"WAIT (\d+)/(\d+) score=([-\d.eE+]+).*?nivo=([-\d.eE+]+) dBFS (\S+)")
CAL_RE = re.compile(r"CAL\s+(\d+)/(\d+) score=\S+ nivo=([-\d.eE+]+) dBFS")
STOP_RE = re.compile(r"fail-closed stop u (\S+): (\S+) -> (\S+)")
K1_STOP_RE = re.compile(r"K1 odbio kalibraciju: (\S+) -> (\S+)")


def build_is_psd_live() -> bool:
    ninja = FIRMWARE / "build" / "build.ninja"
    if not ninja.exists():
        return False
    return "-DASD_PSD_LIVE" in ninja.read_text(encoding="utf-8", errors="replace")


def reset_board(ser: serial.Serial) -> None:
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.15)
    ser.setRTS(False)
    time.sleep(0.3)
    ser.reset_input_buffer()


def run(args: argparse.Namespace) -> int:
    audio_dir = Path(args.audio_dir) if args.audio_dir else OUT_ROOT / "audio"
    cal_path, det_path, manifest = build_audio(args.speed, audio_dir)
    print(f"kalibracioni snimak: {cal_path.name}  {manifest['cal_seconds']:.0f} s "
          f"({len(manifest['cal_clips'])} klipova)")
    print(f"detekciona petlja:   {det_path.name}  {manifest['det_loop_seconds']:.0f} s "
          f"({len(manifest['det_clips'])} klipova, kalibracija ih NIJE cula)")
    print(f"zajednicko pojacanje: {manifest['gain']:.4f}")
    if args.prepare_only:
        print("--prepare-only: zvuk je napravljen, plocica nije dirana")
        return 0

    if not build_is_psd_live() and not args.force:
        raise SystemExit("build nije ASD_PSD_LIVE (provjereno u build.ninja); "
                         "rebuilduj ili pusti sa --force")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUT_ROOT / f"{stamp}_{args.speed}_{args.minutes}min"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "audio_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    raw_path = run_dir / "uart.log"
    det_rows: list[dict] = []
    quality_rows: list[dict] = []
    threshold: float | None = None
    presence_gate: float | None = None
    loo_mean = loo_sd = None
    stop_reason: str | None = None
    switch_index: int | None = None

    deadline = time.time() + args.minutes * 60
    t0 = time.time()
    playing_det = False

    ser = serial.Serial(args.port, args.baud, timeout=0.5)
    raw = raw_path.open("w", encoding="utf-8", newline="\n")
    try:
        # Zvuk krece PRIJE reseta: WAIT faza mora imati sta da cuje, inace
        # fail-closed gate odbije prolaz zbog INSUFFICIENT_LEVEL.
        winsound.PlaySound(str(cal_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        time.sleep(1.0)
        if not args.no_reset:
            reset_board(ser)
        print(f"\nprolaz krece; log: {raw_path}")
        print(f"cekanje na taster {START_GRACE_S:.0f} s (samostalan start), "
              "WAIT ~15 s, kalibracija ~100 s, pa detekcija do kraja\n")

        buf = b""
        while time.time() < deadline:
            chunk = ser.read(4096)
            if chunk:
                buf += chunk
                while b"\n" in buf:
                    line_b, buf = buf.split(b"\n", 1)
                    line = line_b.decode("utf-8", errors="replace").rstrip("\r")
                    elapsed = time.time() - t0
                    raw.write(f"[{elapsed:9.3f}] {line}\n")
                    raw.flush()

                    m = WAIT_RE.search(line)
                    if m:
                        print(f"  WAIT {m.group(1)}/{m.group(2)} "
                              f"nivo={float(m.group(4)):6.1f} dBFS {m.group(5)}")
                    m = CAL_RE.search(line)
                    if m:
                        print(f"  CAL  {m.group(1)}/{m.group(2)} "
                              f"nivo={float(m.group(3)):6.1f} dBFS")

                    m = re.search(r"LOO score: mean=([-\d.]+) sd=([-\d.]+)", line)
                    if m:
                        loo_mean, loo_sd = float(m.group(1)), float(m.group(2))

                    m = THR_RE.search(line)
                    if m:
                        threshold = float(m.group(4))
                        print(f"\n  PRAG = {threshold:.2f} "
                              f"(LOO mean={m.group(2)} sd={m.group(3)})")
                        # Prelaz na detekcionu petlju tacno na granici
                        # kalibracija -> detekcija, dok kalibracioni snimak
                        # jos svira; nema tisine izmedju.
                        winsound.PlaySound(
                            str(det_path),
                            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
                        playing_det = True
                        print("  zvuk prebacen na detekcionu petlju\n")

                    m = PRESENCE_RE.search(line)
                    if m:
                        if m.group(1) != PROTOCOL_VERSION:
                            raise SystemExit(
                                f"protokol se ne poklapa: uredjaj salje {m.group(1)}, "
                                f"alat ocekuje {PROTOCOL_VERSION}")
                        presence_gate = float(m.group(4))
                        print(f"  gate prisustva = {presence_gate:.2f} dBFS "
                              f"(sredina {float(m.group(2)):.2f} - {float(m.group(3)):.1f} dB, "
                              f"{m.group(5)} uzastopna prozora)")

                    m = QUALITY_RE.search(line)
                    if m:
                        row = {"t_s": round(elapsed, 3), "phase": m.group(2),
                               "index": int(m.group(3)), "result": m.group(5)}
                        for key, val in QUALITY_NUM_RE.findall(line):
                            if key in ("rms_dbfs", "dc", "peak", "clipped", "zeros",
                                       "stuck", "dropped_delta", "samples", "expected"):
                                row[key] = float(val)
                        quality_rows.append(row)

                    m = DET_RE.search(line)
                    if m:
                        idx = int(m.group(1))
                        if switch_index is None and playing_det:
                            switch_index = idx
                        row = {
                            "t_s": round(elapsed, 3),
                            "index": idx,
                            "score": float(m.group(2)),
                            "threshold": float(m.group(3)),
                            "anom": int(m.group(5)),
                            "total_anom": int(m.group(6)),
                            "verdict": m.group(7).strip(),
                            "consecutive": int(m.group(8)),
                            "rms_dbfs": float(m.group(9)),
                        }
                        det_rows.append(row)
                        left = (deadline - time.time()) / 60.0
                        print(f"  DET {idx:4d}  score={row['score']:9.2f} "
                              f"prag={row['threshold']:8.2f}  "
                              f"nivo={row['rms_dbfs']:6.1f} dBFS  "
                              f"{row['verdict']:14s} (alarma {row['total_anom']}, "
                              f"ostalo {left:.0f} min)")

                    m = STOP_RE.search(line)
                    if m:
                        stop_reason = f"{m.group(2)} u fazi {m.group(1)} -> {m.group(3)}"
                        print(f"\n  FAIL-CLOSED STOP: {stop_reason}")
                        deadline = 0  # izlazi iz petlje
                        break
                    m = K1_STOP_RE.search(line)
                    if m:
                        stop_reason = f"{m.group(1)} u fazi CAL -> {m.group(2)}"
                        print(f"\n  K1 STOP: {stop_reason}")
                        deadline = 0
                        break
    except KeyboardInterrupt:
        stop_reason = "prekinuto sa tastature"
        print("\nprekid sa tastature")
    finally:
        winsound.PlaySound(None, 0)
        raw.close()
        ser.close()

    return report(run_dir, det_rows, quality_rows, manifest, threshold,
                  presence_gate, loo_mean, loo_sd, stop_reason, switch_index,
                  args)


def report(run_dir: Path, det_rows: list[dict], quality_rows: list[dict],
           manifest: dict, threshold: float | None,
           presence_gate: float | None, loo_mean, loo_sd,
           stop_reason: str | None, switch_index: int | None,
           args: argparse.Namespace) -> int:
    if det_rows:
        with (run_dir / "detections.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(det_rows[0].keys()))
            w.writeheader()
            w.writerows(det_rows)
    if quality_rows:
        keys: list[str] = []
        for row in quality_rows:
            for k in row:
                if k not in keys:
                    keys.append(k)
        with (run_dir / "quality.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(quality_rows)

    lines: list[str] = []
    add = lines.append
    add("# Duga proba laznih alarma\n")
    add(f"- Vrijeme: `{datetime.now().isoformat(timespec='seconds')}`")
    add(f"- Zvuk: TARGET normalan ventilator, brzina `{manifest['speed']}`, "
        f"preko zvucnika")
    add(f"- Kalibracija: {len(manifest['cal_clips'])} klipova "
        f"({manifest['cal_seconds']:.0f} s)")
    add(f"- Detekciona petlja: {len(manifest['det_clips'])} klipova "
        f"({manifest['det_loop_seconds']:.0f} s), kalibracija ih NIJE cula")
    add(f"- Trajanje zahtijevano: {args.minutes} min")
    add(f"- Prag (zamrznut poslije kalibracije): "
        f"{'%.4f' % threshold if threshold is not None else 'NIJE DOBIJEN'}")
    if loo_mean is not None:
        add(f"- LOO kalibracije: mean={loo_mean:.2f} sd={loo_sd:.2f}")
    if stop_reason:
        add(f"- **Prolaz prekinut:** {stop_reason}")
    add("")

    if not det_rows:
        add("## Nema ni jednog DET prozora\n")
        add("Prolaz nije stigao do detekcije. Provjeri `uart.log` -- najcesci "
            "uzrok je fail-closed gate u WAIT/CAL fazi (nivo zvuka ispod "
            "-60 dBFS ili mikrofon nije spojen).")
        (run_dir / "izvjestaj.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines))
        print(f"\nartefakti: {run_dir}")
        return 1

    scores = [r["score"] for r in det_rows]
    det_seconds = det_rows[-1]["t_s"] - det_rows[0]["t_s"]
    det_hours = det_seconds / 3600.0 if det_seconds > 0 else 0.0
    alarm_windows = sum(1 for r in det_rows if r["anom"] == 1)
    over_windows = sum(1 for r in det_rows if r["score"] > r["threshold"])
    episodes = sum(1 for i, r in enumerate(det_rows)
                   if r["anom"] == 1 and (i == 0 or det_rows[i - 1]["anom"] == 0))

    add("## Rezultat\n")
    add("| | |")
    add("|---|---|")
    add(f"| Prozora u detekciji | {len(det_rows)} ({det_seconds / 60:.1f} min) |")
    add(f"| Prozora iznad praga | {over_windows} "
        f"({100.0 * over_windows / len(det_rows):.1f} %) |")
    add(f"| Prozora u alarmu (3 uzastopna) | **{alarm_windows}** |")
    add(f"| Alarmnih epizoda | **{episodes}** |")
    if det_hours > 0:
        add(f"| **Laznih alarma na sat** | **{episodes / det_hours:.2f}** |")
    add(f"| Score | mean={statistics.mean(scores):.2f} "
        f"sd={statistics.pstdev(scores):.2f} "
        f"min={min(scores):.2f} max={max(scores):.2f} |")
    if threshold:
        add(f"| Rezerva do praga | max score je {100.0 * max(scores) / threshold:.1f} % praga |")
    add("")

    # Drift: isti zvuk se ponavlja, pa svaka promjena kroz sat dolazi od kanala
    # i uredjaja, ne od sadrzaja.
    add("## Drift kroz prolaz (isti zvuk u petlji)\n")
    add("| Interval | Prozora | Score mean | sd | max | Alarma |")
    add("|---|---|---|---|---|---|")
    bucket = 10 * 60
    start = det_rows[0]["t_s"]
    b = 0
    while True:
        lo, hi = start + b * bucket, start + (b + 1) * bucket
        rows = [r for r in det_rows if lo <= r["t_s"] < hi]
        if not rows:
            break
        s = [r["score"] for r in rows]
        add(f"| {b * 10}-{(b + 1) * 10} min | {len(rows)} | "
            f"{statistics.mean(s):.2f} | {statistics.pstdev(s):.2f} | "
            f"{max(s):.2f} | {sum(1 for r in rows if r['anom'] == 1)} |")
        b += 1
    add("")

    # Prvi prolaz kroz petlju je jedini u kojem uredjaj slusa zvuk koji nikad
    # nije cuo; sve dalje je ponavljanje istog snimka.
    loop_windows = max(1, round(manifest["det_loop_seconds"] / CLIP_S))
    first = det_rows[:loop_windows]
    rest = det_rows[loop_windows:]
    add("## Prvi prolaz vs ponavljanja\n")
    add(f"Detekciona petlja je {manifest['det_loop_seconds']:.0f} s "
        f"(~{loop_windows} prozora). Prvi prolaz je jedini nad zvukom koji "
        f"uredjaj nikad nije cuo.\n")
    add("| | Prozora | Score mean | max | Alarma |")
    add("|---|---|---|---|---|")
    for name, rows in (("prvi prolaz (nov zvuk)", first), ("ponavljanja", rest)):
        if not rows:
            continue
        s = [r["score"] for r in rows]
        add(f"| {name} | {len(rows)} | {statistics.mean(s):.2f} | {max(s):.2f} | "
            f"{sum(1 for r in rows if r['anom'] == 1)} |")
    add("")

    bad = [r for r in quality_rows if r["result"] != "OK"]
    dropped = sum(r.get("dropped_delta", 0) for r in quality_rows)
    clipped = sum(r.get("clipped", 0) for r in quality_rows)
    add("## Zdravlje lanca\n")
    add(f"- Protokol: `{PROTOCOL_VERSION}`"
        + (f" · gate prisustva: {presence_gate:.2f} dBFS" if presence_gate is not None
           else " · **PRESENCE zapis nije stigao**"))
    add(f"- QUALITY zapisa: {len(quality_rows)}, ne-OK: **{len(bad)}**")
    if bad:
        seen: dict[str, int] = {}
        for r in bad:
            key = f"{r['phase']}/{r['result']}"
            seen[key] = seen.get(key, 0) + 1
        for key, n in sorted(seen.items()):
            add(f"  - `{key}`: {n}")
    add(f"- `dropped` ukupno: **{int(dropped)}** · `clipped` ukupno: **{int(clipped)}**")
    det_q = [r for r in quality_rows if r["phase"] == "DET" and "rms_dbfs" in r]
    if det_q:
        levels = [r["rms_dbfs"] for r in det_q]
        add(f"- nivo u detekciji: {min(levels):.1f} do {max(levels):.1f} dBFS "
            f"(gate je -60 dBFS)")
    add("")

    add("## Ogranicenja ovog prolaza\n")
    add("- Zvuk je snimak preko zvucnika, **nije fizicki ventilator**; u radu se "
        "ne smije navesti kao fizicki test.")
    add(f"- Detekcioni snimak od {manifest['det_loop_seconds']:.0f} s se ponavlja, "
        "pa ovo mjeri stabilnost praga naspram drifta kanala i uredjaja, a ne "
        "otpornost na nepoznat normalan zvuk.")
    add("- Jedna brzina ventilatora; prelazi izmedju brzina nisu testirani.")

    text = "\n".join(lines) + "\n"
    (run_dir / "izvjestaj.md").write_text(text, encoding="utf-8")
    print("\n" + text)
    print(f"artefakti: {run_dir}")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", default="COM4")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--minutes", type=float, default=60.0)
    p.add_argument("--speed", default="spd_1",
                   help="brzina ventilatora; jedna brzina da spoj klipova ne "
                        "napravi laznu promjenu rezima")
    p.add_argument("--audio-dir", default=None)
    p.add_argument("--prepare-only", action="store_true",
                   help="samo napravi snimke, ne diraj plocicu")
    p.add_argument("--no-reset", action="store_true")
    p.add_argument("--force", action="store_true",
                   help="pusti i ako build.ninja ne potvrdjuje ASD_PSD_LIVE")
    args = p.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
