"""Istrazivacka runda: pokusaji preko 0.674 na novom ventilatoru.

MOTIVACIJA. Pobjednik (bench_adapt: sazetak 1280 + naucena kovarijansa) staje
na 0.674. Ova runda testira ideje iz literature koje NISU probane, sve bez
neuronskih mreza i sve izvodljive na ESP32-S3:

  mel256    sazetak u prostoru 128 mel traka (256 dim) umjesto 1280.
            Hipoteza: 1280x1280 kovarijansa iz 990 klipova je lose uslovljena,
            a 5 naslaganih frejmova je ~5x redundantno za sazetak.
  shrink    sweep skupljanja kovarijanse (0.02..0.4) + Ledoit-Wolf.
  gwrp      TWFR pooling (Guan i dr., ICASSP 2023, 3. mjesto DCASE 2022):
            po traci se frejmovi sortiraju opadajuce i vagaju r^i — izmedju
            max (r->0) i prosjeka (r=1). Naglasak na glasnije/tranzijentne
            frejmove koje prosti prosjek razvodni.
  subseg    sazetak po pod-segmentu (~2 s) umjesto cijelog klipa; score klipa
            = percentil segmentnih udaljenosti. Kratkotrajna anomalija u 10 s
            klipa prezivi umjesto da se razvodni.
  knn       udaljenost do najblizeg kalibracionog klipa u izbijeljenom
            prostoru (standard u DCASE top sistemima) umjesto do centra.
            Hvata multimodalnost (3 brzine ventilatora).
  lowrank   PPCA kovarijansa (W W^T + s^2 I, rang q) — stabilnija inverzija,
            a na ploci jeftinija (q x d mnozenje umjesto d x d).
  delta     modulacija: sazetku se dodaju mean+std razlika susjednih frejmova
            (kvar lezaja/lopatice = amplitudska modulacija).
  gain      oduzimanje SKALARNOG nivoa klipa (ne po-traci kao CMN koji je pao
            na 0.544) — uklanja razliku u jacini/udaljenosti mikrofona,
            zadrzava oblik spektra.
  dual      score = d(centar cilja) + lambda * d(najblizi source klip):
            anomalija je daleko i od kalibracije i od korpusa ispravnih.
  ens       rang-ansambl najboljih pojedinacnih pristupa.

PROTOKOL identican bench_adapt.py: k klipova u kalibraciju (isti seedovi
3000+rep), ocjena na preostalim normalnim + svim anomalijama, klip iz
kalibracije se ne ocjenjuje, 20 ponavljanja, mean +- std.
Kovarijansa/PCA/whitening se uce ISKLJUCIVO na source treningu (bez curenja).

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/bench_research.py --machine fan
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
N_MELS = 128


# ---------------------------------------------------------------- sazeci

def mel_frames(f: np.ndarray) -> np.ndarray:
    """(T,640) naslagani vektori -> (T,128) log-mel frejmovi (prvi od 5)."""
    return f[:, :N_MELS]


def summ_meanstd(lm: np.ndarray) -> np.ndarray:
    return np.concatenate([lm.mean(axis=0), lm.std(axis=0)])


def summ_gwrp(lm: np.ndarray, r: float) -> np.ndarray:
    """GWRP pooling po traci: sortiraj opadajuce, vagaj r^i. Std ostaje."""
    s = np.sort(lm, axis=0)[::-1]                     # (T,128) opadajuce
    w = r ** np.arange(len(s), dtype=np.float64)
    pooled = (s * w[:, None]).sum(axis=0) / w.sum()
    return np.concatenate([pooled, lm.std(axis=0)])


def summ_delta(lm: np.ndarray) -> np.ndarray:
    d = np.diff(lm, axis=0)
    return np.concatenate([lm.mean(axis=0), lm.std(axis=0),
                           np.abs(d).mean(axis=0), d.std(axis=0)])


def seg_summaries(lm: np.ndarray, seg: int = 62, hop: int = 31) -> np.ndarray:
    """Sazeci preklapajucih pod-segmenata (~2 s / ~1 s) -> (n_seg, 256)."""
    out = []
    for s in range(0, max(1, len(lm) - seg + 1), hop):
        out.append(summ_meanstd(lm[s:s + seg]))
    return np.stack(out)


# ---------------------------------------------------------- kovarijansa

def inv_cov(X: np.ndarray, shrink: float) -> np.ndarray:
    C = np.cov(X.T)
    C = (1 - shrink) * C + shrink * np.diag(np.diag(C))
    return np.linalg.pinv(C + 1e-6 * np.eye(len(C)))


def inv_cov_lw(X: np.ndarray) -> np.ndarray:
    from sklearn.covariance import LedoitWolf
    lw = LedoitWolf().fit(X)
    return np.linalg.pinv(lw.covariance_ + 1e-6 * np.eye(X.shape[1]))


def inv_cov_ppca(X: np.ndarray, q: int) -> np.ndarray:
    """PPCA precizija: C = W W^T + s2 I, inverzija po Woodburyju (egzaktno)."""
    C = np.cov(X.T)
    vals, vecs = np.linalg.eigh(C)
    vals, vecs = vals[::-1], vecs[:, ::-1]
    s2 = max(float(vals[q:].mean()), 1e-6)
    # C_ppca = V_q diag(l_q) V_q^T + s2 (I - V_q V_q^T); inverzija po Woodburyju
    Vq = vecs[:, :q]
    inv_diag = 1.0 / s2
    M = np.diag(1.0 / np.maximum(vals[:q], 1e-6)) - inv_diag * np.eye(q)
    return inv_diag * np.eye(len(C)) + Vq @ M @ Vq.T


def md(X: np.ndarray, mu: np.ndarray, Ci: np.ndarray) -> np.ndarray:
    d = X - mu
    return np.einsum("ij,jk,ik->i", d, Ci, d)


def whiten_mat(Ci: np.ndarray) -> np.ndarray:
    """L takav da ||L(x-y)||^2 = Mahalanobis; Ci = L^T L."""
    vals, vecs = np.linalg.eigh(Ci)
    vals = np.maximum(vals, 0.0)
    return (vecs * np.sqrt(vals)) @ vecs.T


# ------------------------------------------------------------- protokol

def evaluate(name: str, score_fn, pool_idx, anom_idx, k: int, repeats: int,
             results: dict) -> None:
    """score_fn(cal_idx, X_idx) -> score po klipu; veci = anomalnije."""
    aucs = []
    n_pool = len(pool_idx)
    for rep in range(repeats):
        rng = np.random.default_rng(3000 + rep)
        idx = rng.permutation(n_pool)
        cal = pool_idx[idx[:k]]
        held = pool_idx[idx[k:]]
        X = np.concatenate([held, anom_idx])
        y = np.concatenate([np.zeros(len(held)), np.ones(len(anom_idx))])
        aucs.append(roc_auc_score(y, score_fn(cal, X)))
    m, s = float(np.mean(aucs)), float(np.std(aucs))
    results[name] = {"auc": m, "std": s, "per_rep": [float(a) for a in aucs]}
    print(f"  {name:<28s} {m:.3f} ± {s:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="fan")
    ap.add_argument("--domain", default="target", choices=["source", "target"])
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--repeats", type=int, default=20)
    args = ap.parse_args()

    mdir = ROOT / "data" / "dcase2026_dev" / args.machine
    cache = ROOT / "results" / "cache"
    train = data.list_clips(mdir, "train")
    test = data.list_clips(mdir, "test")
    tr_f = data.load_features(train, cache / f"{args.machine}_train.npz", "train")
    te_f = data.load_features(test, cache / f"{args.machine}_test.npz", "test")
    mean, std = data.fit_norm(tr_f)

    tr_dom = np.array([c.domain for c in train])
    te_dom = np.array([c.domain for c in test])
    te_lab = np.array([c.label for c in test])

    # log-mel frejmovi, normalizovani source statistikom prvih 128 dimenzija
    m128, s128 = mean[:N_MELS], std[:N_MELS]
    lm_tr = [(mel_frames(f) - m128) / s128 for f in tr_f]
    lm_te = [(mel_frames(f) - m128) / s128 for f in te_f]

    # sazetak 1280 (referenca, isto kao bench_adapt)
    S1280_tr = np.stack([np.concatenate([((f - mean) / std).mean(0),
                                         ((f - mean) / std).std(0)]) for f in tr_f])
    S1280_te = np.stack([np.concatenate([((f - mean) / std).mean(0),
                                         ((f - mean) / std).std(0)]) for f in te_f])

    S256_tr = np.stack([summ_meanstd(x) for x in lm_tr])
    S256_te = np.stack([summ_meanstd(x) for x in lm_te])

    src = tr_dom == "source"
    d = args.domain
    # indeksi u SPOJENOM nizu [train | test]
    n_tr = len(tr_f)
    pool_idx = np.concatenate([np.where(tr_dom == d)[0],
                               n_tr + np.where((te_dom == d) & (te_lab == 0))[0]])
    anom_idx = n_tr + np.where((te_dom == d) & (te_lab == 1))[0]

    A1280 = np.concatenate([S1280_tr, S1280_te])
    A256 = np.concatenate([S256_tr, S256_te])
    lm_all = lm_tr + lm_te

    print(f"{args.machine}/{d}: pool={len(pool_idx)} anom={len(anom_idx)} "
          f"k={args.k} rep={args.repeats}")
    results: dict = {}
    k, rep = args.k, args.repeats

    # --- 0) referenca: 1280 + shrink 0.1 (mora ~0.674)
    Ci_1280 = inv_cov(S1280_tr[src], 0.1)
    evaluate("base_1280_s0.1", lambda c, X: md(A1280[X], A1280[c].mean(0), Ci_1280),
             pool_idx, anom_idx, k, rep, results)

    # --- 1) mel256 prostor, sweep skupljanja + Ledoit-Wolf
    for sh in (0.02, 0.05, 0.1, 0.2, 0.4):
        Ci = inv_cov(S256_tr[src], sh)
        evaluate(f"mel256_s{sh}", lambda c, X, Ci=Ci: md(A256[X], A256[c].mean(0), Ci),
                 pool_idx, anom_idx, k, rep, results)
    Ci_lw = inv_cov_lw(S256_tr[src])
    evaluate("mel256_ledoitwolf", lambda c, X: md(A256[X], A256[c].mean(0), Ci_lw),
             pool_idx, anom_idx, k, rep, results)

    # --- 2) GWRP pooling
    for r in (0.90, 0.95, 0.98, 0.99):
        G = np.stack([summ_gwrp(x, r) for x in lm_all])
        Ci = inv_cov(G[:n_tr][src], 0.05)
        evaluate(f"gwrp_r{r}", lambda c, X, G=G, Ci=Ci: md(G[X], G[c].mean(0), Ci),
                 pool_idx, anom_idx, k, rep, results)

    # --- 3) pod-segmenti (~2 s, hop ~1 s), percentilna agregacija
    segs = [seg_summaries(x) for x in lm_all]
    seg_src = np.concatenate([segs[i] for i in np.where(src)[0]])
    Ci_seg = inv_cov(seg_src, 0.05)

    def subseg_score(c, X, q):
        mu = np.concatenate([segs[i] for i in c]).mean(axis=0)
        return np.array([np.percentile(md(segs[i], mu, Ci_seg), q) for i in X])

    for q in (50, 75, 90, 100):
        evaluate(f"subseg_p{q}", lambda c, X, q=q: subseg_score(c, X, q),
                 pool_idx, anom_idx, k, rep, results)

    # --- 4) kNN na kalibracione egzemplare u izbijeljenom prostoru
    Ci_best256 = inv_cov(S256_tr[src], 0.05)
    L = whiten_mat(Ci_best256)
    W = A256 @ L.T

    def knn_score(c, X, kk):
        from scipy.spatial.distance import cdist
        D = cdist(W[X], W[c])
        return np.sort(D, axis=1)[:, :kk].mean(axis=1)

    for kk in (1, 2, 3):
        evaluate(f"knn_{kk}", lambda c, X, kk=kk: knn_score(c, X, kk),
                 pool_idx, anom_idx, k, rep, results)

    # --- 5) PPCA nisko-rang kovarijansa
    for q in (32, 64, 128):
        Ci = inv_cov_ppca(S256_tr[src], q)
        evaluate(f"ppca_q{q}", lambda c, X, Ci=Ci: md(A256[X], A256[c].mean(0), Ci),
                 pool_idx, anom_idx, k, rep, results)

    # --- 6) delta (modulacija)
    Sd = np.stack([summ_delta(x) for x in lm_all])
    Ci_d = inv_cov(Sd[:n_tr][src], 0.05)
    evaluate("delta_512", lambda c, X: md(Sd[X], Sd[c].mean(0), Ci_d),
             pool_idx, anom_idx, k, rep, results)

    # --- 7) skalarna gain normalizacija (nivo klipa)
    def degain(S):
        g = S[:, :N_MELS].mean(axis=1, keepdims=True)
        out = S.copy()
        out[:, :N_MELS] -= g
        return out
    Sg = degain(A256)
    Ci_g = inv_cov(degain(S256_tr)[np.where(src)[0]], 0.05)
    evaluate("gain_norm", lambda c, X: md(Sg[X], Sg[c].mean(0), Ci_g),
             pool_idx, anom_idx, k, rep, results)

    # --- 8) dual: + udaljenost do najblizeg source klipa
    from scipy.spatial.distance import cdist
    W_src = S256_tr[src] @ L.T
    D_src = cdist(W, W_src)
    D_src[D_src < 1e-9] = np.inf  # source klip ne smije naci samog sebe
    d_src_all = D_src.min(axis=1)

    def dual_score(c, X, lam):
        d_t = md(A256[X], A256[c].mean(0), Ci_best256)
        return rankdata(d_t) + lam * rankdata(d_src_all[X])
    for lam in (0.3, 1.0):
        evaluate(f"dual_l{lam}", lambda c, X, lam=lam: dual_score(c, X, lam),
                 pool_idx, anom_idx, k, rep, results)

    # --- 9) rang-ansambl: najbolja 3 pojedinacna (bez base)
    singles = {n: v["auc"] for n, v in results.items() if not n.startswith("base")}
    top3 = sorted(singles, key=singles.get, reverse=True)[:3]
    print(f"\n  ansambl od: {top3}")
    fns = {}
    for n in top3:
        if n.startswith("mel256") or n.startswith("ppca"):
            Ci = Ci_lw if "ledoit" in n else (
                inv_cov_ppca(S256_tr[src], int(n.split("_q")[1])) if "ppca" in n
                else inv_cov(S256_tr[src], float(n.split("_s")[1])))
            fns[n] = lambda c, X, Ci=Ci: md(A256[X], A256[c].mean(0), Ci)
        elif n.startswith("gwrp"):
            r = float(n.split("_r")[1])
            G = np.stack([summ_gwrp(x, r) for x in lm_all])
            Ci = inv_cov(G[:n_tr][src], 0.05)
            fns[n] = lambda c, X, G=G, Ci=Ci: md(G[X], G[c].mean(0), Ci)
        elif n.startswith("subseg"):
            q = int(n.split("_p")[1])
            fns[n] = lambda c, X, q=q: subseg_score(c, X, q)
        elif n.startswith("knn"):
            kk = int(n.split("_")[1])
            fns[n] = lambda c, X, kk=kk: knn_score(c, X, kk)
        elif n.startswith("delta"):
            fns[n] = lambda c, X: md(Sd[X], Sd[c].mean(0), Ci_d)
        elif n.startswith("gain"):
            fns[n] = lambda c, X: md(Sg[X], Sg[c].mean(0), Ci_g)
        elif n.startswith("dual"):
            lam = float(n.split("_l")[1])
            fns[n] = lambda c, X, lam=lam: dual_score(c, X, lam)
    if len(fns) >= 2:
        evaluate("ens_top", lambda c, X: sum(rankdata(f(c, X)) for f in fns.values()),
                 pool_idx, anom_idx, k, rep, results)

    p = ROOT / "results" / f"research_{args.machine}_{args.domain}_k{args.k}.json"
    p.write_text(json.dumps(results, indent=2))
    print(f"\nzapisano: {p}")


if __name__ == "__main__":
    main()
