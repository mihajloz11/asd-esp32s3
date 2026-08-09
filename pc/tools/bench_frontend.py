"""Zadnja poluga: da li front-end gubi kvar prije nego sto model pocne?

Sve dosad je radjeno nad postojecim featurima: FFT 1024, 128 mel traka. Mel
skala je logaritamska — na 4 kHz jedna traka pokriva stotine herca. Kvarovi
rotacionih masina se cesto javljaju kao USKE bocne linije oko harmonika
(disbalans, ostecen lezaj), i takve linije mel skala razmaze i izbrise prije
nego model uopste dobije podatak.

Ovdje se poredi vise front-endova, uz isti nacin bodovanja koji je pobijedio
(sazetak sredina+std, naucena kovarijansa, Mahalanobis oko izmjerenog centra):

  mel128_1024   postojeci (referenca)
  mel256_4096   vise traka i cetiri puta finiji FFT
  lin256_4096   LINEARNE trake — ravnomjerna rezolucija po cijelom opsegu
  lin512_4096   jos finije linearne trake

Ako neki od finijih front-endova osjetno digne AUC, to znaci da je uska
gubila informaciju bila front-end, a ne model — i onda se mijenja on, ne mreza.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_frontend.py --machine fan
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data, features  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SR = 16000


def spec_bands(y: np.ndarray, n_fft: int, hop: int, n_bands: int, mel: bool) -> np.ndarray:
    """|STFT|^2 sazet u n_bands traka, u dB. mel=False -> linearne trake."""
    w = np.hanning(n_fft + 1)[:-1].astype(np.float32)
    n = 1 + (len(y) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n)[:, None]
    P = np.abs(np.fft.rfft(y[idx] * w, axis=1)) ** 2

    if mel:
        fb = features.mel_filterbank(SR, n_fft, n_bands)
        B = P @ fb.T
    else:
        edges = np.linspace(0, P.shape[1], n_bands + 1).astype(int)
        B = np.stack([P[:, a:b].mean(axis=1) for a, b in zip(edges[:-1], edges[1:])],
                     axis=1)
    return np.log(B + 1e-12).astype(np.float32)


def clip_summary(lm: np.ndarray) -> np.ndarray:
    return np.concatenate([lm.mean(axis=0), lm.std(axis=0)])


CONFIGS = {
    "mel128_1024": dict(n_fft=1024, hop=512, n_bands=128, mel=True),
    "mel256_4096": dict(n_fft=4096, hop=1024, n_bands=256, mel=True),
    "lin256_4096": dict(n_fft=4096, hop=1024, n_bands=256, mel=False),
    "lin512_4096": dict(n_fft=4096, hop=1024, n_bands=512, mel=False),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--repeats", type=int, default=20)
    args = ap.parse_args()

    mdir = ROOT / "data" / "dcase2026_dev" / args.machine
    train = data.list_clips(mdir, "train")
    test = data.list_clips(mdir, "test")
    tr_dom = np.array([c.domain for c in train])
    te_dom = np.array([c.domain for c in test])
    te_lab = np.array([c.label for c in test])

    def load(p):
        y, sr = sf.read(p, dtype="float32", always_2d=True)
        return y[:, 0]

    print(f"{args.machine}: ucitavam {len(train)}+{len(test)} klipova...")
    wav_tr = [load(c.path) for c in train]
    wav_te = [load(c.path) for c in test]

    print(f"\n{'front-end':14s} {'dim':>6s} {'target':>9s} {'source*':>9s}")
    print("-" * 44)
    out = {}

    for name, cfg in CONFIGS.items():
        S_tr = np.stack([clip_summary(spec_bands(y, **cfg)) for y in wav_tr])
        S_te = np.stack([clip_summary(spec_bands(y, **cfg)) for y in wav_te])
        mu = S_tr.mean(axis=0)
        sd = S_tr.std(axis=0) + 1e-6
        S_tr, S_te = (S_tr - mu) / sd, (S_te - mu) / sd

        C = np.cov(S_tr[tr_dom == "source"].T) + 1e-4 * np.eye(S_tr.shape[1])
        Ci = np.linalg.pinv(C)

        row = {}
        for dom in ("target", "source"):
            pool = np.concatenate([S_tr[tr_dom == dom],
                                   S_te[(te_dom == dom) & (te_lab == 0)]])
            anom = S_te[(te_dom == dom) & (te_lab == 1)]
            aucs = []
            for rep in range(args.repeats):
                rng = np.random.default_rng(7000 + rep)
                idx = rng.permutation(len(pool))
                k = min(args.k, len(pool) // 3)
                cal, held = pool[idx[:k]], pool[idx[k:]]
                X = np.concatenate([held, anom])
                y = np.concatenate([np.zeros(len(held)), np.ones(len(anom))])
                d = X - cal.mean(axis=0)
                aucs.append(roc_auc_score(y, np.einsum("ij,jk,ik->i", d, Ci, d)))
            row[dom] = (float(np.mean(aucs)), float(np.std(aucs)))
        out[name] = row
        print(f"{name:14s} {S_tr.shape[1]:6d} {row['target'][0]:9.3f} "
              f"{row['source'][0]:9.3f}")

    print("\n* source je optimisticki (kovarijansa ucena na dijelu tih klipova)")
    best = max(out.items(), key=lambda kv: kv[1]["target"][0])
    print(f"najbolje na novom ventilatoru: {best[0]}  AUC={best[1]['target'][0]:.3f}")
    p = ROOT / "results" / f"frontend_{args.machine}.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"zapisano: {p}")


if __name__ == "__main__":
    main()
