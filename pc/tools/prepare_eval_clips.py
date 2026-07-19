"""E4 priprema: bira klipove iz test skupa (stratifikovano po label x domen),
kopira ih u folder za FAT sliku, i racuna PC REFERENTNE score-ove (int8 tflite)
za bit-poredjenje sa izlazom uredjaja (eval_mode.c -> EVALCSV linije).

Upotreba (iz pc/):
    python tools/prepare_eval_clips.py --data ..\\data\\dcase2026_dev\\fan --tag fan_baseline_s0 --n 48

Izlaz:
    results/eval_clips/<machine>/          — odabrani WAV-ovi (kratka DOS imena!)
    results/eval_reference_<machine>.csv   — fajl,label,domen,PC score
    + ispis komandi za pravljenje/upis FAT slike (fatfsgen + parttool)
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data, features  # noqa: E402
from asd.quantize import TFLitePredict  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--n", type=int, default=48, help="ukupno klipova (djeljivo sa 4)")
    args = ap.parse_args()

    machine_dir = Path(args.data).resolve()
    machine = machine_dir.name
    meta = json.loads((ROOT / "models" / f"{args.tag}_meta.json").read_text())
    mean = np.array(meta["mean"], dtype=np.float32)
    std = np.array(meta["std"], dtype=np.float32)
    pred = TFLitePredict((ROOT / "models" / f"{args.tag}_int8.tflite").read_bytes())

    clips = data.list_clips(machine_dir, "test")
    rng = np.random.default_rng(0)
    per_cell = args.n // 4
    chosen = []
    for lab in (0, 1):
        for dom in ("source", "target"):
            cell = [c for c in clips if c.label == lab and c.domain == dom]
            idx = rng.choice(len(cell), min(per_cell, len(cell)), replace=False)
            chosen += [cell[i] for i in sorted(idx)]

    out_dir = ROOT / "results" / "eval_clips" / machine
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    ref_csv = ROOT / "results" / f"eval_reference_{machine}.csv"
    with open(ref_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "label", "domain", "pc_score_int8", "orig_name"])
        for i, c in enumerate(chosen):
            # kratko 8.3 ime (FAT bez LFN podrške u fatfsgen-u zna praviti probleme)
            short = f"{'n' if c.label == 0 else 'a'}{c.domain[0]}{i:03d}.wav"
            # mono kanal 0, PCM16 — isto što PC pipeline koristi (DCASE 2026
            # klipovi su stereo: blizu/daleko mikrofon), firmware čita mono
            import soundfile as sf
            y, sr = sf.read(c.path, dtype="int16", always_2d=True)
            sf.write(out_dir / short, y[:, 0], sr, subtype="PCM_16")
            vecs = features.wav_to_vectors(str(c.path))
            xn = (vecs - mean) / std
            rec = pred(xn)
            score = float(np.mean(np.mean((xn - rec) ** 2, axis=1)))
            w.writerow([short, c.label, c.domain, f"{score:.8f}", c.path.name])
            print(f"{short}  label={c.label} dom={c.domain}  score={score:.6f}")

    total_mb = sum(p.stat().st_size for p in out_dir.glob("*.wav")) / 1e6
    print(f"\nOK: {len(chosen)} klipova ({total_mb:.1f} MB) u {out_dir}")
    print(f"Referenca: {ref_csv}\n")
    print("Sljedeci koraci (na masini sa ESP-IDF, iz firmware/esp32s3_asd):")
    print(f"  python $IDF_PATH/components/fatfs/fatfsgen.py --output_file fatfs.img "
          f"--partition_size 20971520 '{out_dir}'")
    print("  python $IDF_PATH/components/partition_table/parttool.py -p PORT "
          "write_partition --partition-name=storage --input fatfs.img")
    print("Zatim boot sa drzanim tasterom -> EVALCSV linije na monitoru:")
    print("  idf.py monitor | tee ../../results/eval_device_" + machine + ".csv")
    print("Poredjenje: python tools/compare_eval.py --machine " + machine)


if __name__ == "__main__":
    main()
