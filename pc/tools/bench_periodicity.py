"""Periodični i visokorezolucioni otisci ventilatora, bez neuronske mreže.

Motivacija: log-mel dobro opisuje prosječan spektar, ali kvar rotacione mašine
može prvo promijeniti uske harmonike ili modulaciju amplitude. Ovaj eksperiment
zato dodaje dva mala otiska koja su izvodljiva i na ESP32-S3:

* ``psd``: oblik dugoročnog spektra u 96 logaritamskih traka (10--4000 Hz),
* ``env``: spektar amplitude/envelope u 64 trake (0.5--200 Hz), koji hvata
  periodično podrhtavanje, udarce i bočne komponente.

Konačni detektor i dalje uči samo iz normalnih snimaka. Kovarijansa se uči na
source normalnom korpusu, a na novom ventilatoru se iz k kalibracionih klipova
mjeri samo centar. Ciljne anomalije služe isključivo za AUC ocjenu.

Da izbor varijante ne bi bio napravljen na ciljnoj anomaliji, skript prvo daje
pošten ``source_select`` rezultat: 800 source normalnih klipova uči model, a
preostalih 190 + test-normalni služe kao odvojena kalibracija/ocjena. Tek onda
prijavljuje target rezultate istih unaprijed definisanih varijanti.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import hilbert, resample_poly, welch
from sklearn.covariance import LedoitWolf
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SR = 16000


def _band_log_power(freq: np.ndarray, power: np.ndarray, edges: np.ndarray) -> np.ndarray:
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (freq >= lo) & (freq < hi)
        out.append(np.log10(float(power[mask].mean()) + 1e-20) if np.any(mask) else -20.0)
    return np.asarray(out, np.float64)


def periodic_features(path: Path) -> dict[str, np.ndarray]:
    y, sr = sf.read(path, dtype="float32", always_2d=True)
    if sr != SR:
        raise ValueError(f"{path}: očekivano {SR} Hz, dobijeno {sr}")
    y = y[:, 0].astype(np.float64)  # isti near kanal koji ima stvarni uređaj
    y -= y.mean()

    # Visokorezolucioni dugoročni spektar: 1.95 Hz razmak FFT binova.
    f, p = welch(y, fs=SR, window="hann", nperseg=8192, noverlap=4096,
                 detrend=False, scaling="spectrum")
    psd = _band_log_power(f, p, np.geomspace(10.0, 4000.0, 97))

    # Analitička amplituda je PC referenca. Za uređaj se može aproksimirati
    # apsolutnom vrijednošću + niskopropusnim filtrom prije decimacije.
    env = np.abs(hilbert(y))
    env = resample_poly(env - env.mean(), 1, 32)  # 500 Hz
    fe, pe = welch(env, fs=500, window="hann", nperseg=2048, noverlap=1024,
                   detrend=False, scaling="spectrum")
    env_psd = _band_log_power(fe, pe, np.geomspace(0.5, 200.0, 65))

    # Nekoliko bezdimenzionih kontrolnih deskriptora.
    prob = p / (p.sum() + 1e-20)
    entropy = -float(np.sum(prob * np.log(prob + 1e-20))) / np.log(len(prob))
    flatness = float(np.exp(np.mean(np.log(p + 1e-20))) / (np.mean(p) + 1e-20))
    rms = float(np.sqrt(np.mean(y * y)) + 1e-20)
    crest = float(np.max(np.abs(y)) / rms)
    zcr = float(np.mean(y[1:] * y[:-1] < 0))
    scalars = np.array([entropy, flatness, np.log10(rms), crest, zcr], np.float64)

    return {
        "psd_raw": psd,
        "psd_shape": psd - psd.mean(),
        "env_raw": env_psd,
        "env_shape": env_psd - env_psd.mean(),
        "periodic": np.concatenate([psd - psd.mean(), env_psd - env_psd.mean(), scalars]),
    }


def mel_summary(f: np.ndarray) -> np.ndarray:
    # Rekonstruiši sve originalne 128-dim. mel frejmove iz P=5 naslaganih
    # vektora, bez petostruko redundantnog 1280-dim. sažetka.
    lm = np.concatenate([f[:, :128], f[-1, 128:].reshape(4, 128)], axis=0)
    return np.concatenate([lm.mean(axis=0), lm.std(axis=0)]).astype(np.float64)


def fit_precision(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8
    Z = (X - mean) / std
    return mean, std, LedoitWolf().fit(Z).precision_


def maha(X: np.ndarray, center: np.ndarray, precision: np.ndarray) -> np.ndarray:
    d = X - center
    return np.einsum("ij,jk,ik->i", d, precision, d)


def eval_one(A: np.ndarray, corpus: np.ndarray, pool: np.ndarray, anomalies: np.ndarray,
             k: int, repeats: int) -> tuple[float, float, list[float]]:
    mean, std, precision = fit_precision(A[corpus])
    Z = (A - mean) / std
    values = []
    for rep in range(repeats):
        order = np.random.default_rng(3000 + rep).permutation(len(pool))
        cal, held = pool[order[:k]], pool[order[k:]]
        X = np.concatenate([held, anomalies])
        y = np.concatenate([np.zeros(len(held)), np.ones(len(anomalies))])
        values.append(roc_auc_score(y, maha(Z[X], Z[cal].mean(axis=0), precision)))
    return float(np.mean(values)), float(np.std(values)), [float(x) for x in values]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--repeats", type=int, default=20)
    args = ap.parse_args()

    mdir = ROOT / "data" / "dcase2026_dev" / args.machine
    cache = ROOT / "results" / "cache"
    train = data.list_clips(mdir, "train")
    test = data.list_clips(mdir, "test")
    tr_dom = np.array([c.domain for c in train])
    te_dom = np.array([c.domain for c in test])
    te_lab = np.array([c.label for c in test])

    feature_cache = cache / f"{args.machine}_periodicity.npz"
    if feature_cache.exists():
        z = np.load(feature_cache)
        arrays = {name: z[name] for name in z.files}
    else:
        print(f"izdvajam periodicne feature iz {len(train) + len(test)} WAV klipova...")
        rows = [periodic_features(c.path) for c in train + test]
        arrays = {name: np.stack([r[name] for r in rows]) for name in rows[0]}
        feature_cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(feature_cache, **arrays)

    tr_f = data.load_features(train, cache / f"{args.machine}_train.npz", "train")
    te_f = data.load_features(test, cache / f"{args.machine}_test.npz", "test")
    arrays["mel256"] = np.stack([mel_summary(f) for f in tr_f + te_f])

    n_tr = len(train)
    source = np.where(tr_dom == "source")[0]
    perm = np.random.default_rng(7).permutation(source)
    source_corpus, source_rest = perm[:800], perm[800:]
    target_corpus = source  # opšti oblik se uči iz svih dostupnih dobrih source snimaka

    protocols = {
        "source_select": (
            source_corpus,
            np.concatenate([source_rest,
                            n_tr + np.where((te_dom == "source") & (te_lab == 0))[0]]),
            n_tr + np.where((te_dom == "source") & (te_lab == 1))[0],
        ),
        "target_final": (
            target_corpus,
            np.concatenate([np.where(tr_dom == "target")[0],
                            n_tr + np.where((te_dom == "target") & (te_lab == 0))[0]]),
            n_tr + np.where((te_dom == "target") & (te_lab == 1))[0],
        ),
    }

    out: dict[str, dict] = {}
    for protocol, (corpus, pool, anomalies) in protocols.items():
        print(f"\n{protocol}: corpus={len(corpus)} pool={len(pool)} anom={len(anomalies)}")
        out[protocol] = {}
        for name, A in arrays.items():
            mean, std, per_rep = eval_one(A, corpus, pool, anomalies, args.k, args.repeats)
            out[protocol][name] = {"auc": mean, "std": std, "per_rep": per_rep}
            print(f"  {name:12s} {mean:.3f} ± {std:.3f}")

    selected = max(out["source_select"], key=lambda x: out["source_select"][x]["auc"])
    out["selected_without_target_labels"] = selected
    print(f"\nizabrano bez target oznaka: {selected}")
    print(f"njegov target AUC: {out['target_final'][selected]['auc']:.3f}")

    path = ROOT / "results" / f"periodicity_{args.machine}_k{args.k}.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"zapisano: {path}")


if __name__ == "__main__":
    main()
