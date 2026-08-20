"""Developmental fan-noise feature laboratory with frozen-policy readout.

Two explicit commands keep the data boundary visible:

``prepare-normal``
    Reads source-normal and chronological target-normal spectra, fits every
    candidate only on normal data, writes separate candidate caches and emits
    the score bundle consumed by ``derive_commissioning_policy.py``.

``readout-target``
    Validates an already frozen commissioning policy and the normal-only model
    bundle *before* opening target-anomaly features.  It reports sensitivity;
    it never refits a model, changes a threshold, or selects a candidate.

All outputs are developmental.  This file does not modify the canonical DCASE
evaluator, physical-fan host, firmware, or any historical result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np


PC_DIR = Path(__file__).resolve().parents[1]
ROOT = PC_DIR.parent
if str(PC_DIR) not in sys.path:
    sys.path.insert(0, str(PC_DIR))

from tools.derive_commissioning_policy import (  # noqa: E402
    INPUT_SCHEMA_VERSION,
    canonical_json,
    sha256_file,
    sha256_json,
    temporal_normal_metrics,
    write_json_atomic,
)


PROTOCOL_VERSION = "fan-noise-candidates-v1.0.0-development"
MODEL_SCHEMA_VERSION = "fan-noise-normal-model-v1.0.0-development"
READOUT_SCHEMA_VERSION = "fan-target-readout-v1.0.0-development"
N_BANDS = 96
MIN_HZ = 10.0
MAX_HZ = 4000.0
EPS = 1.0e-20
SHRINKAGE = 0.10
CENTER_MIN_WINDOWS = 10
CENTER_MAX_WINDOWS = 20
NORMAL_ROLES = {"source_normal", "target_normal", "ambient_normal"}
SENSITIVITY_ROLES = {"sensitivity_source_anomaly", "sensitivity_synthetic_shift"}
TARGET_ROLE = "target_anomaly"


@dataclass(frozen=True)
class FeatureSpec:
    candidate_id: str
    family: str
    main_detector: bool
    coefficients: Mapping[str, Any]
    description: str


FEATURE_SPECS: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        "baseline_hard_log96", "spectral_frontend", True,
        {"bands": N_BANDS, "min_hz": MIN_HZ, "max_hz": MAX_HZ,
         "overlap": False, "smoothing": None},
        "Existing non-overlapping log-PSD bands; canonical developmental baseline.",
    ),
    FeatureSpec(
        "triangular_overlap_log96", "spectral_frontend", True,
        {"bands": N_BANDS, "min_hz": MIN_HZ, "max_hz": MAX_HZ,
         "axis": "log_frequency", "overlap": "adjacent_triangles"},
        "Overlapping triangular log-frequency bands.",
    ),
    FeatureSpec(
        "smoothed_hard_log96", "spectral_frontend", True,
        {"bands": N_BANDS, "min_hz": MIN_HZ, "max_hz": MAX_HZ,
         "power_kernel": [0.25, 0.50, 0.25], "padding": "edge"},
        "Fixed mild frequency smoothing followed by baseline hard bands.",
    ),
    FeatureSpec(
        "clipped_standardized_residual_c3", "robust_score", True,
        {"base_frontend": "baseline_hard_log96", "clip_abs": 3.0,
         "operation": "clip_standardized_residual_before_full_precision_quadratic"},
        "Coordinate-wise bounded standardized residual before the full quadratic form.",
    ),
    FeatureSpec(
        "huber_whitened_residual_d1p5", "robust_score", True,
        {"base_frontend": "baseline_hard_log96", "huber_delta": 1.5,
         "aggregation": "sum_coordinate_huber_loss"},
        "Huber loss over the whitened residual.",
    ),
    FeatureSpec(
        "subsegment_stability_gate", "interference_gate", False,
        {"subsegments": 5, "base_frontend": "baseline_hard_log96",
         "center": "coordinate_median",
         "spread": "median_l2_distance_to_coordinate_median"},
        "Within-window stability gate; never replaces the main detector.",
    ),
)
MAIN_CANDIDATES = tuple(spec.candidate_id for spec in FEATURE_SPECS if spec.main_detector)


class PhaseAudit:
    """Track cohort reads and forbid target features before frozen readout."""

    def __init__(self) -> None:
        self.phase = "prepare_normal"
        self.policy_sha256: str | None = None
        self.target_anomaly_metadata_reads = 0
        self.target_anomaly_feature_reads = 0

    def authorize_metadata(self, role: str) -> None:
        if role == TARGET_ROLE:
            self.target_anomaly_metadata_reads += 1
            if self.phase != "target_readout" or not self.policy_sha256:
                raise RuntimeError(
                    "target anomaly metadata/features smiju se otvoriti tek poslije frozen policy"
                )

    def record_feature_read(self, role: str, count: int) -> None:
        if role == TARGET_ROLE:
            if self.phase != "target_readout" or not self.policy_sha256:
                raise RuntimeError("target anomaly feature-i procitani prije frozen policy")
            self.target_anomaly_feature_reads += count

    def enter_target_readout(self, policy_sha256: str) -> None:
        if self.phase != "prepare_normal" or not policy_sha256:
            raise RuntimeError("target readout faza se moze otvoriti samo jednom")
        self.policy_sha256 = policy_sha256
        self.phase = "target_readout"


def build_feature_manifest() -> dict[str, Any]:
    specs = []
    for spec in FEATURE_SPECS:
        item = asdict(spec)
        item["candidate_provenance_id"] = sha256_json(item)
        specs.append(item)
    content: dict[str, Any] = {
        "schema_version": "fan-noise-feature-manifest-v1.0.0",
        "protocol_version": PROTOCOL_VERSION,
        "developmental": True,
        "numeric_status": "development_pending_physical_validation",
        "feature_candidates": specs,
        "main_candidate_order": list(MAIN_CANDIDATES),
        "fit_roles": ["source_normal", "target_normal:CENTER_LEARNING"],
        "threshold_roles": ["target_normal:COMMISSION_DERIVE"],
        "verification_roles": ["target_normal:COMMISSION_VERIFY"],
        "sensitivity_control_roles": sorted(SENSITIVITY_ROLES),
        "target_anomaly_role": "evaluate_only_after_frozen_policy",
        "tonalness": {
            "input": "peak_prominence_proxy",
            "not_a": "speech_classifier",
            "normal_reference": "median_CENTER_LEARNING",
            "output": "tonalness_delta",
        },
        "model": {
            "source_standardization": "per_coordinate_mean_std_source_normal",
            "covariance": "fixed_shrinkage_to_identity",
            "shrinkage": SHRINKAGE,
            "local_center": "mean_standardized_CENTER_LEARNING",
        },
        "cache": {
            "layout": (
                "protocol/manifest/candidate/cohort_role/cohort_sha256/"
                "product__model.npz"
            ),
            "legacy_cache_allowed": False,
            "candidate_specific": True,
            "cohort_specific": True,
        },
        "excluded_negative_results": [
            "psd_order", "psd_regime", "dual_channel_logratio",
            "dual_channel_coherence", "dual_channel_mask", "transient_only",
            "ewma", "cusum", "top_k_band_removal_with_full_precision",
        ],
        "target_anomalies_used_for_fit": False,
    }
    return {**content, "manifest_id": sha256_json(content)}


def _finite_array(value: np.ndarray, name: str, *, ndim: int | None = None) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if ndim is not None and array.ndim != ndim:
        raise ValueError(f"{name} mora imati ndim={ndim}, dobijeno {array.ndim}")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} sadrzi NaN/Inf")
    return array


@dataclass(frozen=True)
class SpectralCohort:
    role: str
    frequency_hz: np.ndarray
    power: np.ndarray
    subsegment_power: np.ndarray | None
    tonalness_proxy: np.ndarray
    window_id: tuple[str, ...]
    fan_id: tuple[str, ...]
    session_id: tuple[str, ...]
    phase: tuple[str, ...]
    start_s: np.ndarray
    end_s: np.ndarray
    input_sha256: str


def _strings(data: Mapping[str, np.ndarray], name: str, n: int, default: str) -> tuple[str, ...]:
    if name not in data:
        return tuple(default for _ in range(n))
    values = tuple(str(value) for value in np.asarray(data[name]).tolist())
    if len(values) != n:
        raise ValueError(f"{name} length mora biti {n}")
    return values


def load_spectral_cohort(
    path: Path, *, expected_role: str, audit: PhaseAudit,
) -> SpectralCohort:
    """Read role metadata first; target feature arrays remain unopened pre-freeze."""
    with np.load(path, allow_pickle=False) as archive:
        if "cohort_role" not in archive.files:
            raise ValueError(f"{path}: nedostaje cohort_role")
        role = str(np.asarray(archive["cohort_role"]).item())
        audit.authorize_metadata(role)
        if role != expected_role:
            raise ValueError(f"{path}: role={role!r}, ocekivano {expected_role!r}")
        allowed = NORMAL_ROLES | SENSITIVITY_ROLES | {TARGET_ROLE}
        if role not in allowed:
            raise ValueError(f"{path}: nepoznat cohort_role {role!r}")
        # The whole-file digest is computed only after the declared role has
        # passed the target-readout authorization boundary.
        input_hash = sha256_file(path)
        frequency = _finite_array(archive["frequency_hz"], "frequency_hz", ndim=1)
        power = _finite_array(archive["power"], "power", ndim=2)
        n, bins = power.shape
        if len(frequency) != bins or n == 0:
            raise ValueError("power/frequency shape mismatch ili prazna kohorta")
        if np.any(np.diff(frequency) <= 0.0) or np.any(power < 0.0):
            raise ValueError("frequency mora rasti, power mora biti nenegativan")
        labels = np.asarray(archive["label"] if "label" in archive.files else np.zeros(n), int)
        expected_label = 1 if role in SENSITIVITY_ROLES | {TARGET_ROLE} else 0
        if labels.shape != (n,) or np.any(labels != expected_label):
            raise ValueError(f"{role}: label mora biti {expected_label} za svaki red")
        subsegments = None
        if "subsegment_power" in archive.files:
            subsegments = _finite_array(
                archive["subsegment_power"], "subsegment_power", ndim=3,
            )
            if subsegments.shape != (n, 5, bins) or np.any(subsegments < 0.0):
                raise ValueError("subsegment_power mora biti (N,5,F) i nenegativan")
        tonalness = _finite_array(
            archive["tonalness_proxy"] if "tonalness_proxy" in archive.files else np.zeros(n),
            "tonalness_proxy", ndim=1,
        )
        if tonalness.shape != (n,):
            raise ValueError("tonalness_proxy shape mismatch")
        phases = _strings(archive, "phase", n, "NOT_APPLICABLE")
        starts = _finite_array(
            archive["start_s"] if "start_s" in archive.files else np.arange(n) * 10.0,
            "start_s", ndim=1,
        )
        ends = _finite_array(
            archive["end_s"] if "end_s" in archive.files else starts + 10.0,
            "end_s", ndim=1,
        )
        cohort = SpectralCohort(
            role=role,
            frequency_hz=frequency,
            power=power,
            subsegment_power=subsegments,
            tonalness_proxy=tonalness,
            window_id=_strings(archive, "window_id", n, ""),
            fan_id=_strings(archive, "fan_id", n, "unknown-fan"),
            session_id=_strings(archive, "session_id", n, "unknown-session"),
            phase=phases,
            start_s=starts,
            end_s=ends,
            input_sha256=input_hash,
        )
    audit.record_feature_read(role, len(cohort.power))
    validate_cohort_timing(cohort)
    return cohort


def validate_cohort_timing(cohort: SpectralCohort) -> None:
    if cohort.start_s.shape != cohort.end_s.shape or len(cohort.start_s) != len(cohort.power):
        raise ValueError("start/end shape mismatch")
    if np.any(cohort.end_s <= cohort.start_s):
        raise ValueError("svaki prozor mora imati end_s > start_s")
    if cohort.role == "target_normal":
        allowed = ("CENTER_LEARNING", "COMMISSION_DERIVE", "COMMISSION_VERIFY")
        previous_end = -math.inf
        previous_phase = 0
        seen: list[str] = []
        for phase, start, end in zip(cohort.phase, cohort.start_s, cohort.end_s):
            if phase not in allowed:
                raise ValueError(f"target_normal nepoznata faza {phase!r}")
            index = allowed.index(phase)
            if index < previous_phase or start < previous_end:
                raise ValueError("target normal nije hronoloski ili se preklapa")
            previous_phase = index
            previous_end = end
            if not seen or seen[-1] != phase:
                seen.append(phase)
        if tuple(seen) != allowed:
            raise ValueError("target normal mora imati CENTER/DERIVE/VERIFY redom")
        center_count = sum(phase == "CENTER_LEARNING" for phase in cohort.phase)
        if not CENTER_MIN_WINDOWS <= center_count <= CENTER_MAX_WINDOWS:
            raise ValueError(
                f"CENTER_LEARNING mora imati {CENTER_MIN_WINDOWS}..{CENTER_MAX_WINDOWS} prozora"
            )


def hard_log_bands(frequency_hz: np.ndarray, power: np.ndarray) -> np.ndarray:
    edges = np.geomspace(MIN_HZ, MAX_HZ, N_BANDS + 1)
    rows = []
    for spectrum in np.asarray(power, np.float64):
        bands = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            mask = (frequency_hz >= lo) & (frequency_hz < hi)
            bands.append(
                math.log10(float(np.mean(spectrum[mask])) + EPS)
                if np.any(mask) else -20.0
            )
        value = np.asarray(bands, np.float64)
        rows.append(value - value.mean())
    return np.stack(rows)


def triangular_log_bands(frequency_hz: np.ndarray, power: np.ndarray) -> np.ndarray:
    centers = np.geomspace(MIN_HZ, MAX_HZ, N_BANDS)
    log_centers = np.log(centers)
    log_frequency = np.log(np.maximum(frequency_hz, np.finfo(float).tiny))
    left = np.empty(N_BANDS)
    right = np.empty(N_BANDS)
    left[1:] = log_centers[:-1]
    right[:-1] = log_centers[1:]
    left[0] = log_centers[0] - (log_centers[1] - log_centers[0])
    right[-1] = log_centers[-1] + (log_centers[-1] - log_centers[-2])
    weights = np.zeros((N_BANDS, len(frequency_hz)), dtype=np.float64)
    for band in range(N_BANDS):
        rising = (log_frequency - left[band]) / (log_centers[band] - left[band])
        falling = (right[band] - log_frequency) / (right[band] - log_centers[band])
        weights[band] = np.maximum(0.0, np.minimum(rising, falling))
    weight_sum = weights.sum(axis=1)
    rows = []
    for spectrum in np.asarray(power, np.float64):
        weighted = weights @ spectrum
        mean_power = np.divide(
            weighted, weight_sum, out=np.zeros_like(weighted), where=weight_sum > 0.0,
        )
        value = np.where(weight_sum > 0.0, np.log10(mean_power + EPS), -20.0)
        rows.append(value - value.mean())
    return np.stack(rows)


def smooth_power(power: np.ndarray) -> np.ndarray:
    padded = np.pad(np.asarray(power, np.float64), ((0, 0), (1, 1)), mode="edge")
    return 0.25 * padded[:, :-2] + 0.50 * padded[:, 1:-1] + 0.25 * padded[:, 2:]


def smoothed_hard_log_bands(frequency_hz: np.ndarray, power: np.ndarray) -> np.ndarray:
    return hard_log_bands(frequency_hz, smooth_power(power))


FRONTEND_EXTRACTORS: dict[str, Callable[[np.ndarray, np.ndarray], np.ndarray]] = {
    "baseline_hard_log96": hard_log_bands,
    "triangular_overlap_log96": triangular_log_bands,
    "smoothed_hard_log96": smoothed_hard_log_bands,
}


@dataclass(frozen=True)
class NormalModel:
    source_mean: np.ndarray
    source_scale: np.ndarray
    precision: np.ndarray
    sqrt_precision: np.ndarray
    local_center: np.ndarray


def fit_normal_model(source_features: np.ndarray, center_features: np.ndarray) -> NormalModel:
    source = _finite_array(source_features, "source_features", ndim=2)
    center = _finite_array(center_features, "center_features", ndim=2)
    if source.shape[1] != center.shape[1] or len(source) < 3:
        raise ValueError("source/center feature shape ili source sample count nije dovoljan")
    source_mean = source.mean(axis=0)
    source_scale = source.std(axis=0)
    source_scale = np.where(source_scale < 1.0e-8, 1.0, source_scale)
    standardized = (source - source_mean) / source_scale
    covariance = np.cov(standardized, rowvar=False)
    covariance = (1.0 - SHRINKAGE) * covariance + SHRINKAGE * np.eye(source.shape[1])
    precision = np.linalg.inv(covariance)
    eigenvalues, eigenvectors = np.linalg.eigh(precision)
    eigenvalues = np.maximum(eigenvalues, 0.0)
    sqrt_precision = (eigenvectors * np.sqrt(eigenvalues)) @ eigenvectors.T
    local_center = ((center - source_mean) / source_scale).mean(axis=0)
    return NormalModel(source_mean, source_scale, precision, sqrt_precision, local_center)


def whitened_residual(features: np.ndarray, model: NormalModel) -> np.ndarray:
    return standardized_residual(features, model) @ model.sqrt_precision


def standardized_residual(features: np.ndarray, model: NormalModel) -> np.ndarray:
    standardized = (np.asarray(features, np.float64) - model.source_mean) / model.source_scale
    return standardized - model.local_center


def score_frontend(features: np.ndarray, model: NormalModel) -> np.ndarray:
    residual = whitened_residual(features, model)
    return np.sum(residual * residual, axis=1)


def score_clipped(features: np.ndarray, model: NormalModel, clip_abs: float = 3.0) -> np.ndarray:
    residual = np.clip(
        standardized_residual(features, model), -clip_abs, clip_abs,
    )
    score = np.einsum("ni,ij,nj->n", residual, model.precision, residual)
    return np.maximum(score, 0.0)


def score_huber(features: np.ndarray, model: NormalModel, delta: float = 1.5) -> np.ndarray:
    absolute = np.abs(whitened_residual(features, model))
    loss = np.where(
        absolute <= delta, 0.5 * absolute * absolute,
        delta * (absolute - 0.5 * delta),
    )
    return np.sum(loss, axis=1)


def subsegment_instability(frequency_hz: np.ndarray, subsegment_power: np.ndarray) -> np.ndarray:
    if subsegment_power.ndim != 3 or subsegment_power.shape[1] != 5:
        raise ValueError("potrebno je tacno pet podsegmenata")
    n, segments, bins = subsegment_power.shape
    features = hard_log_bands(
        frequency_hz, subsegment_power.reshape(n * segments, bins),
    ).reshape(n, segments, N_BANDS)
    coordinate_median = np.median(features, axis=1, keepdims=True)
    distances = np.linalg.norm(features - coordinate_median, axis=2)
    return np.median(distances, axis=1)


class CandidateCache:
    """Candidate/cohort-specific cache; legacy mixed caches are never opened."""

    def __init__(self, root: Path, manifest: Mapping[str, Any]) -> None:
        self.root = root / PROTOCOL_VERSION / str(manifest["manifest_id"])
        self.manifest = dict(manifest)
        self.spec_by_id = {
            str(item["candidate_id"]): dict(item)
            for item in manifest["feature_candidates"]
        }

    def load_or_compute(
        self, *, candidate_id: str, cohort: SpectralCohort,
        value_name: str, compute: Callable[[], np.ndarray],
        model_id: str | None = None,
    ) -> np.ndarray:
        if candidate_id not in self.spec_by_id:
            raise ValueError(f"candidate nije u manifestu: {candidate_id}")
        metadata = {
            "protocol_version": PROTOCOL_VERSION,
            "manifest_id": self.manifest["manifest_id"],
            "candidate_id": candidate_id,
            "candidate_provenance_id": self.spec_by_id[candidate_id]["candidate_provenance_id"],
            "cohort_role": cohort.role,
            "cohort_input_sha256": cohort.input_sha256,
            "model_id": model_id,
            "value_name": value_name,
        }
        # Front-end features and model-dependent scores are different cache
        # products.  The cohort digest permits multiple normal sessions under
        # one manifest, while the model component prevents score reuse across
        # independently fitted normal models.
        model_component = "no-model" if model_id is None else model_id[:16]
        path = (
            self.root / candidate_id / cohort.role / cohort.input_sha256
            / f"{value_name}__{model_component}.npz"
        )
        if path.exists():
            with np.load(path, allow_pickle=False) as archive:
                if "metadata_json" not in archive.files or value_name not in archive.files:
                    raise RuntimeError(f"{path}: stale/legacy candidate cache")
                actual = json.loads(str(np.asarray(archive["metadata_json"]).item()))
                if actual != metadata:
                    raise RuntimeError(f"{path}: cache provenance mismatch")
                value = _finite_array(archive[value_name], value_name)
            return value
        value = _finite_array(compute(), value_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            with temp.open("wb") as handle:
                np.savez_compressed(
                    handle,
                    metadata_json=np.asarray(json.dumps(metadata, sort_keys=True, allow_nan=False)),
                    **{value_name: value},
                )
            os.replace(temp, path)
        finally:
            if temp.exists():
                temp.unlink()
        return value


def model_bundle_id(
    manifest_id: str, source_hash: str, target_hash: str,
) -> str:
    return sha256_json({
        "manifest_id": manifest_id,
        "source_normal_sha256": source_hash,
        "target_normal_sha256": target_hash,
        "fit_roles": ["source_normal", "target_normal:CENTER_LEARNING"],
    })


def save_model_bundle(
    path: Path, *, manifest: Mapping[str, Any], model_id: str,
    models: Mapping[str, NormalModel], tonalness_reference: float,
    source_hash: str, target_hash: str,
) -> None:
    metadata = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "developmental": True,
        "manifest_id": manifest["manifest_id"],
        "model_id": model_id,
        "source_normal_sha256": source_hash,
        "target_normal_sha256": target_hash,
        "target_anomalies_used_for_fit": False,
        "tonalness_normal_reference": tonalness_reference,
    }
    arrays: dict[str, np.ndarray] = {
        "metadata_json": np.asarray(json.dumps(metadata, sort_keys=True, allow_nan=False)),
    }
    for candidate_id, model in models.items():
        for name in ("source_mean", "source_scale", "precision", "sqrt_precision", "local_center"):
            arrays[f"{candidate_id}__{name}"] = np.asarray(getattr(model, name), np.float64)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp.open("wb") as handle:
            np.savez_compressed(handle, **arrays)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def load_model_bundle(
    path: Path, *, expected_manifest_id: str,
) -> tuple[dict[str, Any], dict[str, NormalModel]]:
    with np.load(path, allow_pickle=False) as archive:
        metadata = json.loads(str(np.asarray(archive["metadata_json"]).item()))
        if metadata.get("schema_version") != MODEL_SCHEMA_VERSION:
            raise ValueError("nepodrzan model bundle schema")
        if metadata.get("manifest_id") != expected_manifest_id:
            raise ValueError("model bundle i feature manifest se ne podudaraju")
        if metadata.get("target_anomalies_used_for_fit") is not False:
            raise ValueError("model bundle tvrdi da su target anomalije koristene za fit")
        models: dict[str, NormalModel] = {}
        for candidate_id in FRONTEND_EXTRACTORS:
            fields = {}
            for name in ("source_mean", "source_scale", "precision", "sqrt_precision", "local_center"):
                key = f"{candidate_id}__{name}"
                if key not in archive.files:
                    raise ValueError(f"model bundle nema {key}")
                fields[name] = _finite_array(archive[key], key)
            models[candidate_id] = NormalModel(**fields)
    return metadata, models


def _features_for(
    candidate_id: str, cohort: SpectralCohort, cache: CandidateCache,
) -> np.ndarray:
    extractor = FRONTEND_EXTRACTORS[candidate_id]
    return cache.load_or_compute(
        candidate_id=candidate_id, cohort=cohort, value_name="features",
        compute=lambda: extractor(cohort.frequency_hz, cohort.power),
    )


def score_all_candidates(
    cohort: SpectralCohort, *, models: Mapping[str, NormalModel],
    cache: CandidateCache, model_id: str,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    frontend_features = {
        candidate_id: _features_for(candidate_id, cohort, cache)
        for candidate_id in FRONTEND_EXTRACTORS
    }
    scores: dict[str, np.ndarray] = {}
    for candidate_id in FRONTEND_EXTRACTORS:
        scores[candidate_id] = cache.load_or_compute(
            candidate_id=candidate_id, cohort=cohort, value_name="scores",
            model_id=model_id,
            compute=lambda cid=candidate_id: score_frontend(
                frontend_features[cid], models[cid],
            ),
        )
    baseline_features = frontend_features["baseline_hard_log96"]
    baseline_model = models["baseline_hard_log96"]
    scores["clipped_standardized_residual_c3"] = cache.load_or_compute(
        candidate_id="clipped_standardized_residual_c3", cohort=cohort,
        value_name="scores", model_id=model_id,
        compute=lambda: score_clipped(baseline_features, baseline_model, 3.0),
    )
    scores["huber_whitened_residual_d1p5"] = cache.load_or_compute(
        candidate_id="huber_whitened_residual_d1p5", cohort=cohort,
        value_name="scores", model_id=model_id,
        compute=lambda: score_huber(baseline_features, baseline_model, 1.5),
    )
    if cohort.subsegment_power is None:
        raise ValueError(f"{cohort.role}: subsegment_power je obavezan za stability gate")
    instability = cache.load_or_compute(
        candidate_id="subsegment_stability_gate", cohort=cohort,
        value_name="instability", model_id=model_id,
        compute=lambda: subsegment_instability(
            cohort.frequency_hz, cohort.subsegment_power,
        ),
    )
    if set(scores) != set(MAIN_CANDIDATES):
        raise RuntimeError("score output nije tacno zaključani main candidate set")
    return scores, instability


def score_bundle_from_normal(
    *, source: SpectralCohort, target: SpectralCohort,
    manifest: Mapping[str, Any], cache_root: Path, model_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if source.role != "source_normal" or target.role != "target_normal":
        raise ValueError("normal preparation zahtijeva source_normal i target_normal")
    if not np.array_equal(source.frequency_hz, target.frequency_hz):
        raise ValueError("source/target frequency grid se razlikuje")
    center_mask = np.asarray([phase == "CENTER_LEARNING" for phase in target.phase])
    cache = CandidateCache(cache_root, manifest)
    models: dict[str, NormalModel] = {}
    for candidate_id in FRONTEND_EXTRACTORS:
        source_features = _features_for(candidate_id, source, cache)
        target_features = _features_for(candidate_id, target, cache)
        models[candidate_id] = fit_normal_model(
            source_features, target_features[center_mask],
        )
    identifier = model_bundle_id(
        str(manifest["manifest_id"]), source.input_sha256, target.input_sha256,
    )
    tonal_reference = float(np.median(target.tonalness_proxy[center_mask]))
    save_model_bundle(
        model_path, manifest=manifest, model_id=identifier, models=models,
        tonalness_reference=tonal_reference,
        source_hash=source.input_sha256, target_hash=target.input_sha256,
    )
    scores, instability = score_all_candidates(
        target, models=models, cache=cache, model_id=identifier,
    )
    windows = []
    for index in range(len(target.power)):
        window_id = target.window_id[index] or f"normal-{index:05d}"
        windows.append({
            "window_id": window_id,
            "fan_id": target.fan_id[index],
            "session_id": target.session_id[index],
            "phase": target.phase[index],
            "start_s": float(target.start_s[index]),
            "end_s": float(target.end_s[index]),
            "normal_only": True,
            "label": 0,
            "candidate_scores": {
                candidate_id: float(scores[candidate_id][index])
                for candidate_id in MAIN_CANDIDATES
            },
            "tonalness_proxy": float(target.tonalness_proxy[index]),
            "tonalness_delta": float(target.tonalness_proxy[index] - tonal_reference),
            "subsegment_instability": float(instability[index]),
        })
    bundle = {
        "schema_version": INPUT_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "developmental": True,
        "numeric_status": "development_pending_physical_validation",
        "target_anomalies_used_for_fit": False,
        "feature_manifest_id": manifest["manifest_id"],
        "feature_candidate_ids": list(MAIN_CANDIDATES),
        "model_id": identifier,
        "windows": windows,
    }
    metadata = {
        "model_id": identifier,
        "tonalness_normal_reference": tonal_reference,
        "source_normal_sha256": source.input_sha256,
        "target_normal_sha256": target.input_sha256,
    }
    return bundle, metadata


def _policy_for_readout(policy: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    if policy.get("developmental") is not True:
        raise ValueError("readout zahtijeva developmental frozen policy")
    if policy.get("target_anomalies_used_for_fit") is not False:
        raise ValueError("policy nije normal-only")
    selected = policy.get("selected_policy")
    if not isinstance(selected, dict) or selected.get("policy_status") != "frozen_developmental":
        raise ValueError("policy nije zamrznut prije target readout-a")
    if selected.get("manifest_id") != policy.get("candidate_manifest", {}).get("manifest_id"):
        raise ValueError("policy manifest nije samokonzistentan")
    if not policy.get("model_id") or selected.get("model_id") != policy.get("model_id"):
        raise ValueError("policy i selected policy nemaju isti normal-only model_id")
    if policy.get("candidate_manifest", {}).get("feature_manifest_id") != manifest.get("manifest_id"):
        raise ValueError("frozen policy i feature manifest se ne podudaraju")
    candidate_id = str(selected.get("feature_candidate_id", ""))
    if candidate_id not in MAIN_CANDIDATES:
        raise ValueError("frozen policy candidate nije u feature manifestu")
    enter = float(selected.get("T_enter"))
    exit_threshold = float(selected.get("T_exit"))
    if not (math.isfinite(enter) and math.isfinite(exit_threshold)
            and 0.0 < exit_threshold < enter):
        raise ValueError("frozen policy nema validne apsolutne enter/exit pragove")
    return dict(selected)


def target_readout(
    *, policy: Mapping[str, Any], policy_sha256: str,
    manifest: Mapping[str, Any], model_path: Path, target_path: Path,
    cache_root: Path, audit: PhaseAudit,
) -> dict[str, Any]:
    """Score target anomalies only after policy validation/freeze."""
    selected = _policy_for_readout(policy, manifest)
    metadata, models = load_model_bundle(
        model_path, expected_manifest_id=str(manifest["manifest_id"]),
    )
    if metadata.get("model_id") != policy.get("model_id"):
        raise ValueError("frozen pragovi i normal model bundle imaju razlicit model_id")
    audit.enter_target_readout(policy_sha256)
    target = load_spectral_cohort(
        target_path, expected_role=TARGET_ROLE, audit=audit,
    )
    cache = CandidateCache(cache_root, manifest)
    scores, instability = score_all_candidates(
        target, models=models, cache=cache, model_id=str(metadata["model_id"]),
    )
    selected_scores = scores[str(selected["feature_candidate_id"])]
    rows = []
    tonal_reference = float(selected["tonalness_normal_reference"])
    instability_gate = float(selected["subsegment_instability_gate"])
    for index, score in enumerate(selected_scores):
        rows.append({
            "window_id": target.window_id[index] or f"target-anomaly-{index:05d}",
            "fan_id": target.fan_id[index],
            "session_id": target.session_id[index],
            "start_s": float(target.start_s[index]),
            "end_s": float(target.end_s[index]),
            "candidate_scores": {str(selected["feature_candidate_id"]): float(score)},
            "tonalness_proxy": float(target.tonalness_proxy[index]),
            "tonalness_delta": float(target.tonalness_proxy[index] - tonal_reference),
            "subsegment_instability": float(instability[index]),
            "stability_gate_exceeded": bool(instability[index] > instability_gate),
        })
    metrics = temporal_normal_metrics(
        rows, feature_name=str(selected["feature_candidate_id"]),
        enter_threshold=float(selected["T_enter"]),
        exit_threshold=float(selected["T_exit"]), block_windows=6,
    )
    return {
        "schema_version": READOUT_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "developmental": True,
        "numeric_status": "development_readout_not_fit_or_validation",
        "policy_sha256": policy_sha256,
        "model_id": metadata["model_id"],
        "feature_manifest_id": manifest["manifest_id"],
        "selected_policy_unchanged": selected,
        "target_anomalies_used_for_fit": False,
        "target_anomalies_read_after_policy_frozen": True,
        "target_anomaly_feature_reads": audit.target_anomaly_feature_reads,
        "readout_metrics": metrics,
        "stability_gate_exceeded_windows": sum(
            int(row["stability_gate_exceeded"]) for row in rows
        ),
        "windows": rows,
    }


def git_provenance() -> dict[str, Any]:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain=v1"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout
        return {"head_commit": head, "working_tree_dirty": bool(status.strip())}
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"unavailable": True, "reason": f"{type(exc).__name__}: {exc}"}


def common_provenance(
    *, manifest: Mapping[str, Any], inputs: Mapping[str, Path], audit: PhaseAudit,
) -> dict[str, Any]:
    return {
        "schema_version": "fan-noise-development-provenance-v1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "developmental": True,
        "protocol_version": PROTOCOL_VERSION,
        "feature_manifest_id": manifest["manifest_id"],
        "inputs": {
            name: {"path": str(path.resolve()), "sha256": sha256_file(path.resolve())}
            for name, path in inputs.items()
        },
        "source_sha256": {
            "pc/tools/evaluate_fan_noise_candidates.py": sha256_file(Path(__file__)),
            "pc/tools/derive_commissioning_policy.py": sha256_file(
                Path(__file__).with_name("derive_commissioning_policy.py")
            ),
        },
        "dependency_versions": {
            "python": platform.python_version(), "numpy": np.__version__,
        },
        "git": git_provenance(),
        "phase_audit": {
            "phase": audit.phase,
            "target_anomaly_metadata_reads": audit.target_anomaly_metadata_reads,
            "target_anomaly_feature_reads": audit.target_anomaly_feature_reads,
        },
        "target_anomalies_used_for_fit": False,
    }


def prepare_normal_cli(args: argparse.Namespace) -> int:
    out_dir = args.output_dir.resolve()
    manifest = build_feature_manifest()
    # Candidate list exists on disk before opening any feature cohort.
    write_json_atomic(out_dir / "feature_candidate_manifest.json", manifest)
    audit = PhaseAudit()
    source = load_spectral_cohort(
        args.source_normal.resolve(), expected_role="source_normal", audit=audit,
    )
    target = load_spectral_cohort(
        args.target_normal.resolve(), expected_role="target_normal", audit=audit,
    )
    model_path = out_dir / "normal_model_bundle.npz"
    bundle, metadata = score_bundle_from_normal(
        source=source, target=target, manifest=manifest,
        cache_root=args.cache_dir.resolve(), model_path=model_path,
    )
    write_json_atomic(out_dir / "normal_candidate_scores.json", bundle)
    write_json_atomic(out_dir / "normal_preparation.json", {
        "schema_version": "fan-noise-normal-preparation-v1.0.0",
        "developmental": True,
        "feature_manifest_id": manifest["manifest_id"],
        "target_anomalies_used_for_fit": False,
        **metadata,
    })
    write_json_atomic(out_dir / "provenance.json", common_provenance(
        manifest=manifest,
        inputs={"source_normal": args.source_normal, "target_normal": args.target_normal},
        audit=audit,
    ))
    print(out_dir / "normal_candidate_scores.json")
    return 0


def readout_target_cli(args: argparse.Namespace) -> int:
    out_dir = args.output_dir.resolve()
    manifest = json.loads(args.feature_manifest.read_text(encoding="utf-8"))
    expected = build_feature_manifest()
    if manifest != expected:
        raise ValueError("feature manifest nije tacno zaključani developmental manifest")
    policy_path = args.frozen_policy.resolve()
    policy_bytes = policy_path.read_bytes()
    policy = json.loads(policy_bytes.decode("utf-8"))
    policy_hash = hashlib.sha256(policy_bytes).hexdigest()
    # Validation happens before target_path is hashed or np.load opens it.
    _policy_for_readout(policy, manifest)
    audit = PhaseAudit()
    result = target_readout(
        policy=policy, policy_sha256=policy_hash, manifest=manifest,
        model_path=args.model_bundle.resolve(),
        target_path=args.target_anomaly.resolve(),
        cache_root=args.cache_dir.resolve(), audit=audit,
    )
    write_json_atomic(out_dir / "target_anomaly_readout.json", result)
    write_json_atomic(out_dir / "target_readout_provenance.json", common_provenance(
        manifest=manifest,
        inputs={
            "frozen_policy": policy_path,
            "model_bundle": args.model_bundle,
            "target_anomaly": args.target_anomaly,
        },
        audit=audit,
    ))
    print(out_dir / "target_anomaly_readout.json")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare-normal")
    prepare.add_argument("--source-normal", type=Path, required=True)
    prepare.add_argument("--target-normal", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument(
        "--cache-dir", type=Path,
        default=ROOT / "results" / "commissioning_development" / "cache",
    )
    prepare.set_defaults(func=prepare_normal_cli)

    readout = sub.add_parser("readout-target")
    readout.add_argument("--feature-manifest", type=Path, required=True)
    readout.add_argument("--frozen-policy", type=Path, required=True)
    readout.add_argument("--model-bundle", type=Path, required=True)
    readout.add_argument("--target-anomaly", type=Path, required=True)
    readout.add_argument("--output-dir", type=Path, required=True)
    readout.add_argument(
        "--cache-dir", type=Path,
        default=ROOT / "results" / "commissioning_development" / "cache",
    )
    readout.set_defaults(func=readout_target_cli)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
