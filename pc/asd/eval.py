"""Scoring i metrike: MSE / Mahalanobis anomaly score, AUC, pAUC, gamma prag.

DCASE protokol: AUC posebno za source i target domen (anomalije dijeljene),
pAUC pri FPR <= 0.1 preko svih domena, zvanični skor = harmonijska sredina.
Prag se NIKAD ne tunira na test skupu (fituje se gamma na trening score-ovima).
"""
from __future__ import annotations

import numpy as np
from scipy import stats
from sklearn.metrics import roc_auc_score

P_AUC_FPR = 0.1


def clip_scores_mse(model_predict, feats: list[np.ndarray], mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    """Anomaly score po klipu = mean MSE rekonstrukcije preko vektora klipa."""
    out = np.empty(len(feats), dtype=np.float64)
    for i, x in enumerate(feats):
        xn = (x - mean) / std
        rec = model_predict(xn)
        out[i] = float(np.mean((xn - rec) ** 2))
    return out


def fit_mahala(model_predict, train_feats: list[np.ndarray], mean: np.ndarray, std: np.ndarray):
    """Kovarijansa rekonstrukcionih grešaka na treningu (za MAHALA mod)."""
    errs = []
    for x in train_feats:
        xn = (x - mean) / std
        errs.append(xn - model_predict(xn))
    e = np.concatenate(errs, axis=0)
    mu = e.mean(axis=0)
    cov = np.cov(e, rowvar=False) + 1e-6 * np.eye(e.shape[1])
    return mu, np.linalg.pinv(cov)


def clip_scores_mahala(model_predict, feats, mean, std, mu, cov_inv) -> np.ndarray:
    out = np.empty(len(feats), dtype=np.float64)
    for i, x in enumerate(feats):
        xn = (x - mean) / std
        e = (xn - model_predict(xn)) - mu
        out[i] = float(np.mean(np.einsum("ij,jk,ik->i", e, cov_inv, e)))
    return out


def dcase_metrics(scores: np.ndarray, labels: np.ndarray, domains: np.ndarray) -> dict:
    """AUC_source, AUC_target (normal iz domena + SVE anomalije), pAUC, harmonijska sredina."""
    res = {}
    for dom in ("source", "target"):
        mask = ((domains == dom) & (labels == 0)) | (labels == 1)
        res[f"auc_{dom}"] = roc_auc_score(labels[mask], scores[mask])
    res["pauc"] = roc_auc_score(labels, scores, max_fpr=P_AUC_FPR)
    vals = [res["auc_source"], res["auc_target"], res["pauc"]]
    res["hmean"] = stats.hmean(vals)
    return res


def gamma_threshold(train_scores: np.ndarray, percentile: float = 0.9) -> dict:
    """Gamma fit na trening score-ovima; prag = 90. percentil (DCASE praksa).

    Vraća i momentnu procjenu (zatvorena forma — ovo računa C na uređaju, E6)
    radi poređenja sa scipy MLE fitom.
    """
    shape, loc, scale = stats.gamma.fit(train_scores, floc=0)
    thr_mle = float(stats.gamma.ppf(percentile, shape, loc=loc, scale=scale))
    m, v = float(np.mean(train_scores)), float(np.var(train_scores))
    k_mm, theta_mm = m * m / v, v / m
    thr_mm = float(stats.gamma.ppf(percentile, k_mm, scale=theta_mm))
    return {"shape": shape, "scale": scale, "threshold": thr_mle,
            "k_moment": k_mm, "theta_moment": theta_mm, "threshold_moment": thr_mm}
