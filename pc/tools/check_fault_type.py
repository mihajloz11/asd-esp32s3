"""Je li front-end uopste OSJETLJIV na vrstu kvara koju sam sintetizovao?

Sweep jacine kvara preko zvucnika (psd_severity_test.py) nije dao monoton
odziv: -24 dB je skocilo na 4450, a jaci -18 i -12 dB su ostali na 340-570.
Dvije moguce krivice:
  (a) akusticki kanal — zvucnik ne reprodukuje kvar
  (b) vrsta kvara — psd_shape je DUGOROCNI PROSJECNI spektar, pa udarne
      (impulsivne) pojave u njemu skoro nestanu, bez obzira na jacinu

Ovaj alat odvaja to dvoje: ista racunica, ali DIGITALNO, bez zvucnika i
mikrofona. Ako score ne raste sa jacinom ni ovdje, kriva je vrsta kvara (b).

Poredi i tri vrste kvara na istim jacinama:
  udar     periodicni udari (ono sto je bilo u testu) — impulsivno
  ton      tonska komponenta na frekvenciji prolaza lopatica ~170 Hz + harmonici
  sirina   sirokopojasni sum dodan preko cijelog opsega

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/check_fault_type.py
"""
from __future__ import annotations

import json
import sys
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
SR = 16000
ROT_HZ = 24.0
BLADE_HZ = 168.0        # ~7 lopatica x 24 o/s
SEV_DB = [-30, -24, -18, -12, -6]
TMP = ROOT / "results" / "demo_audio" / "_fault_tmp.wav"


def make_fault(y, db, kind, rng):
    n = len(y)
    t = np.arange(n) / SR
    rms = float(np.sqrt(np.mean(y * y))) + 1e-12
    amp = rms * (10.0 ** (db / 20.0))

    if kind == "udar":
        f = np.zeros(n)
        period = int(SR / ROT_HZ)
        clen = int(0.004 * SR)
        env = np.exp(-np.arange(clen) / (0.0008 * SR))
        for s in range(0, n - clen, period):
            f[s:s + clen] += rng.standard_normal(clen) * env
    elif kind == "ton":
        f = (np.sin(2 * np.pi * BLADE_HZ * t)
             + 0.5 * np.sin(2 * np.pi * 2 * BLADE_HZ * t)
             + 0.3 * np.sin(2 * np.pi * 3 * BLADE_HZ * t))
    elif kind == "sirina":
        f = rng.standard_normal(n)
    else:
        raise ValueError(kind)

    f *= amp / (float(np.sqrt(np.mean(f * f))) + 1e-12)
    return (y + f).astype(np.float32)


def feat_of(y):
    sf.write(TMP, y, SR, subtype="PCM_16")
    return periodic_features(TMP)["psd_shape"].astype(np.float64)


def main():
    cache = ROOT / "results" / "cache" / "fan_periodicity.npz"
    z = np.load(cache)
    psd = z["psd_shape"]
    train = data.list_clips(FAN, "train")
    test = data.list_clips(FAN, "test")
    clips = train + test
    n_tr = len(train)
    dom = np.array([c.domain for c in clips])
    lab = np.array([c.label for c in clips])
    is_test = np.arange(len(clips)) >= n_tr

    src = (dom == "source") & ~is_test
    X = psd[src]
    mu, sd = X.mean(0), X.std(0) + 1e-8
    P = LedoitWolf().fit((X - mu) / sd).precision_

    tgt_norm_idx = np.where((dom == "target") & (lab == 0))[0]
    rng = np.random.default_rng(0)
    cal_idx = rng.permutation(tgt_norm_idx)[:10]
    center = ((psd[cal_idx] - mu) / sd).mean(axis=0)

    def score(feature):
        d = (feature - mu) / sd - center
        return float(d @ P @ d)

    # osnova: cisti normalni klipovi koji nisu u kalibraciji
    eval_idx = [i for i in tgt_norm_idx if i not in set(cal_idx)][:8]
    base = [score(psd[i]) for i in eval_idx]
    print(f"ispravan rad (digitalno, {len(base)} klipova): "
          f"medijana {np.median(base):8.1f}  opseg {min(base):.0f}..{max(base):.0f}")

    # stvarne DCASE anomalije, za poredjenje
    anom_idx = np.where((dom == "target") & (lab == 1) & is_test)[0][:8]
    ad = [score(psd[i]) for i in anom_idx]
    print(f"stvarna DCASE anomalija ({len(ad)} klipova):     "
          f"medijana {np.median(ad):8.1f}  opseg {min(ad):.0f}..{max(ad):.0f}\n")

    out = {"ispravan": base, "dcase_anomalija": ad, "sinteticki": {}}
    wavs = [clips[i].path for i in eval_idx[:4]]
    print(f"{'kvar':<8s} " + " ".join(f"{d:>8d} dB" for d in SEV_DB))
    print("-" * (9 + 11 * len(SEV_DB)))
    for kind in ("udar", "ton", "sirina"):
        row = []
        for db in SEV_DB:
            sc = []
            for w in wavs:
                y = sf.read(w, dtype="float32", always_2d=True)[0][:, 0]
                sc.append(score(feat_of(make_fault(y, db, kind,
                                                   np.random.default_rng(7)))))
            row.append(float(np.median(sc)))
        out["sinteticki"][kind] = dict(zip(map(str, SEV_DB), row))
        print(f"{kind:<8s} " + " ".join(f"{v:>11.0f}" for v in row))

    if TMP.exists():
        TMP.unlink()
    p = ROOT / "results" / "fault_type_check.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nzapisano: {p}")
    print("\nCitanje: ako 'udar' ne raste sa jacinom a 'ton' raste, front-end je "
          "slijep za impulsivne kvarove — to je svojstvo dugorocnog prosjecnog "
          "spektra, ne greska implementacije.")


if __name__ == "__main__":
    main()
