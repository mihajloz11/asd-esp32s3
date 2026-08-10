"""Kanonski within-run leakage guarded developmental benchmark.

Ovaj skript zamjenjuje ``bench_final_tables.py`` kao kanonski razvojni protokol
za tri statisticka front-enda. Ne evaluira istorijske AE/neuralne modele i nije
nezavisna finalna potvrda. Stari skript ostaje sacuvan kao istorijski eksperiment.

Granica podataka je namjerno stroga:

* globalna standardizacija i Ledoit-Wolf precision uce se iskljucivo na
  ``source/train/normal`` klipovima;
* lokalni centar koristi samo kalibracioni dio target normalnog poola;
* target anomalni audio/feature-i smiju se ucitati tek u fazi ``evaluate``,
  nakon sto su svi modeli fitovani i svi splitovi zamrznuti;
* lista metoda je konstanta u kodu, a sve metode dobijaju isti manifest
  ``calibration_split_id`` podjela.

Podrazumijevani puni run (iz ``pc/``):

    ../.venv/Scripts/python.exe tools/evaluate_canonical.py

Brza proba jedne masine ne predstavlja finalnu tabelu:

    ../.venv/Scripts/python.exe tools/evaluate_canonical.py --machines fan --n-splits 3 --bootstrap-resamples 100

Prvi puni run pravi odvojene feature cacheve po kohorti. To je sporije, ali
sprjecava da legacy NPZ, koji sadrzi i normalne i anomalne redove, bude ucitan
prije zavrsne evaluacije.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

import numpy as np
import soundfile as sf
from scipy.signal import welch
from sklearn.covariance import LedoitWolf
from sklearn.metrics import roc_auc_score

PC_DIR = Path(__file__).resolve().parents[1]
ROOT = PC_DIR.parent
sys.path.insert(0, str(PC_DIR))

from asd import data, features  # noqa: E402
from tools.bench_periodicity import _band_log_power  # noqa: E402


PROTOCOL_VERSION = "canonical-evaluation-v1.1.0"
METHOD_ORDER = ("mel1280", "mel256", "psd_shape")
MACHINES = (
    "fan",
    "ToyCar",
    "ToyCarEmu",
    "bearingEmu",
    "gearboxEmu",
    "sliderEmu",
    "valveEmu",
)
MAX_FPR = 0.1
DEFAULT_K = 20
DEFAULT_N_SPLITS = 100
DEFAULT_SPLIT_RANDOM_STATE = 20260809
DEFAULT_BOOTSTRAP_RESAMPLES = 2000
DEFAULT_BOOTSTRAP_RANDOM_STATE = 20260810

AGGREGATE_CSV_COLUMNS = (
    "run_id",
    "protocol_version",
    "git_head_commit",
    "working_tree_dirty",
    "machine",
    "method",
    "training_seed",
    "k",
    "calibration_split_count",
    "split_manifest_sha256",
    "auc_mean",
    "auc_calibration_split_std",
    "auc_bootstrap_95ci_of_split_mean_lower",
    "auc_bootstrap_95ci_of_split_mean_upper",
    "standardized_pauc_at_fpr_0_1_mean",
    "pauc_calibration_split_std",
    "pauc_bootstrap_95ci_of_split_mean_lower",
    "pauc_bootstrap_95ci_of_split_mean_upper",
    "bootstrap_resamples",
    "bootstrap_random_state",
)

PER_SPLIT_CSV_COLUMNS = (
    "run_id",
    "protocol_version",
    "git_head_commit",
    "working_tree_dirty",
    "machine",
    "method",
    "training_seed",
    "calibration_split_id",
    "split_manifest_sha256",
    "n_calibration_normal",
    "n_held_out_normal",
    "n_target_anomaly",
    "auc",
    "standardized_pauc_at_fpr_0_1",
)


@dataclass(frozen=True)
class ClipRef:
    relative_path: str
    dataset_split: str
    domain: str
    label: int
    size_bytes: int
    content_sha256: str

    @property
    def filename(self) -> str:
        return Path(self.relative_path).name


@dataclass(frozen=True)
class MachineCohorts:
    source_fit: tuple[ClipRef, ...]
    target_normal_pool: tuple[ClipRef, ...]
    target_anomaly_evaluate: tuple[ClipRef, ...]


@dataclass(frozen=True)
class MethodSpec:
    name: str
    feature_dimension: int
    frontend: str
    standardization: str = "source_train_normal_per_dimension"
    covariance: str = "LedoitWolf_on_source_standardized_features"
    local_center: str = "mean_of_target_normal_calibration_features"
    score: str = "squared_Mahalanobis_distance"
    training_seed: None = None
    training_seed_semantics: str = "not_applicable_deterministic_statistical_method"


METHOD_SPECS: tuple[MethodSpec, ...] = (
    MethodSpec(
        "mel1280",
        1280,
        "mean_and_std_of_640D_P5_stacked_logmel_vectors",
    ),
    MethodSpec(
        "mel256",
        256,
        "mean_and_std_of_reconstructed_128D_logmel_frames",
    ),
    MethodSpec(
        "psd_shape",
        96,
        "Welch8192_hop4096_96_log_bands_10_4000Hz_gain_centered",
    ),
)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dependency_versions() -> dict[str, str]:
    packages = ("numpy", "scipy", "scikit-learn", "soundfile", "librosa")
    versions = {name: importlib.metadata.version(name) for name in packages}
    versions["python"] = platform.python_version()
    return versions


def relevant_source_hashes(
    root: Path = ROOT, relative_paths: Sequence[str] | None = None
) -> dict[str, str]:
    paths = relative_paths or (
        "pc/tools/evaluate_canonical.py",
        "pc/asd/features.py",
        "pc/tools/bench_periodicity.py",
    )
    return {name: _sha256_file(root / name) for name in paths}


def _method_spec_hash() -> str:
    return _sha256_json([asdict(spec) for spec in METHOD_SPECS])


def _clip_manifest_entry(clip: ClipRef, index: int) -> dict:
    return {
        "cohort_index": index,
        "relative_path": clip.relative_path,
        "filename": clip.filename,
        "dataset_split": clip.dataset_split,
        "domain": clip.domain,
        "label": "anomaly" if clip.label else "normal",
        "size_bytes": clip.size_bytes,
        "content_sha256": clip.content_sha256,
    }


def _cohort_input_manifest_hash(clips: Sequence[ClipRef]) -> str:
    return _sha256_json([_clip_manifest_entry(clip, i) for i, clip in enumerate(clips)])


def _clip_ref(clip: data.ClipInfo, dataset_split: str) -> ClipRef:
    resolved = clip.path.resolve()
    return ClipRef(
        relative_path=resolved.relative_to(ROOT.resolve()).as_posix(),
        dataset_split=dataset_split,
        domain=clip.domain,
        label=int(clip.label),
        size_bytes=resolved.stat().st_size,
        content_sha256=_sha256_file(resolved),
    )


def discover_machine(machine: str) -> MachineCohorts:
    machine_dir = ROOT / "data" / "dcase2026_dev" / machine
    train = tuple(_clip_ref(c, "train") for c in data.list_clips(machine_dir, "train"))
    test = tuple(_clip_ref(c, "test") for c in data.list_clips(machine_dir, "test"))
    cohorts = MachineCohorts(
        source_fit=tuple(
            c for c in train if c.domain == "source" and c.label == 0
        ),
        target_normal_pool=tuple(
            c
            for c in train + test
            if c.domain == "target" and c.label == 0
        ),
        target_anomaly_evaluate=tuple(
            c for c in test if c.domain == "target" and c.label == 1
        ),
    )
    validate_cohorts(cohorts)
    return cohorts


def validate_cohorts(cohorts: MachineCohorts) -> None:
    if not cohorts.source_fit:
        raise ValueError("source/train/normal fit kohorta je prazna")
    if not cohorts.target_normal_pool:
        raise ValueError("target normalni pool je prazan")
    if not cohorts.target_anomaly_evaluate:
        raise ValueError("target anomalije za zavrsnu evaluaciju ne postoje")

    if any(
        c.dataset_split != "train" or c.domain != "source" or c.label != 0
        for c in cohorts.source_fit
    ):
        raise ValueError("source fit smije sadrzati samo source/train/normal")
    if any(c.domain != "target" or c.label != 0 for c in cohorts.target_normal_pool):
        raise ValueError("kalibracioni pool smije sadrzati samo target normale")
    if any(
        c.dataset_split != "test" or c.domain != "target" or c.label != 1
        for c in cohorts.target_anomaly_evaluate
    ):
        raise ValueError("evaluate anomalije moraju biti target/test/anomaly")

    for clip in (
        cohorts.source_fit
        + cohorts.target_normal_pool
        + cohorts.target_anomaly_evaluate
    ):
        if clip.size_bytes < 0:
            raise ValueError(f"negativna velicina fajla: {clip.relative_path}")
        if len(clip.content_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in clip.content_sha256.lower()
        ):
            raise ValueError(f"neispravan SHA-256: {clip.relative_path}")

    groups = (
        {c.relative_path for c in cohorts.source_fit},
        {c.relative_path for c in cohorts.target_normal_pool},
        {c.relative_path for c in cohorts.target_anomaly_evaluate},
    )
    if groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2]:
        raise ValueError("fit, target normal i anomaly kohorte se preklapaju")


def _machine_random_state(base_random_state: int, machine: str) -> int:
    machine_hash = int.from_bytes(hashlib.sha256(machine.encode()).digest()[:4], "big")
    return (base_random_state + machine_hash) % (2**32)


def build_split_manifest(
    cohorts_by_machine: Mapping[str, MachineCohorts],
    *,
    k: int,
    n_splits: int,
    split_random_state: int,
) -> dict:
    if k <= 0 or n_splits <= 0:
        raise ValueError("k i n_splits moraju biti pozitivni")
    machines: dict[str, dict] = {}
    for machine in sorted(cohorts_by_machine):
        cohorts = cohorts_by_machine[machine]
        validate_cohorts(cohorts)
        pool = cohorts.target_normal_pool
        if k >= len(pool):
            raise ValueError(f"{machine}: k={k} mora biti manji od pool={len(pool)}")
        source_entries = [_clip_manifest_entry(c, i) for i, c in enumerate(cohorts.source_fit)]
        pool_entries = [_clip_manifest_entry(c, i) for i, c in enumerate(pool)]
        anomaly_entries = [
            _clip_manifest_entry(c, i)
            for i, c in enumerate(cohorts.target_anomaly_evaluate)
        ]
        rng = np.random.default_rng(_machine_random_state(split_random_state, machine))
        splits = []
        all_indices = set(range(len(pool)))
        for split_number in range(n_splits):
            calibration = sorted(int(i) for i in rng.permutation(len(pool))[:k])
            held_out = sorted(all_indices - set(calibration))
            splits.append(
                {
                    "calibration_split_id": f"split-{split_number:03d}",
                    "calibration_pool_indices": calibration,
                    "held_out_normal_pool_indices": held_out,
                    "calibration_clips": [pool_entries[i]["relative_path"] for i in calibration],
                    "held_out_normal_clips": [pool_entries[i]["relative_path"] for i in held_out],
                }
            )
        machines[machine] = {
            "source_fit": source_entries,
            "source_fit_manifest_sha256": _cohort_input_manifest_hash(cohorts.source_fit),
            "target_normal_pool": pool_entries,
            "target_normal_pool_manifest_sha256": _cohort_input_manifest_hash(pool),
            "target_anomaly_evaluate": anomaly_entries,
            "target_anomaly_evaluate_manifest_sha256": _cohort_input_manifest_hash(
                cohorts.target_anomaly_evaluate
            ),
            "splits": splits,
        }

    content = {
        "protocol_version": PROTOCOL_VERSION,
        "k": k,
        "n_splits": n_splits,
        "split_random_state": split_random_state,
        "machines": machines,
    }
    validate_split_manifest(content, cohorts_by_machine)
    return {**content, "content_sha256": _sha256_json(content)}


def validate_split_manifest(
    manifest: Mapping[str, object], cohorts_by_machine: Mapping[str, MachineCohorts]
) -> None:
    if "content_sha256" in manifest:
        unhashed = dict(manifest)
        supplied_hash = unhashed.pop("content_sha256")
        if supplied_hash != _sha256_json(unhashed):
            raise ValueError("manifest content_sha256 ne odgovara sadrzaju")
    if tuple(spec.name for spec in METHOD_SPECS) != METHOD_ORDER:
        raise RuntimeError("fiksna lista metoda i METHOD_ORDER nisu uskladjeni")
    machines = manifest["machines"]
    if not isinstance(machines, dict):
        raise ValueError("manifest machines mora biti objekat")
    for machine, cohorts in cohorts_by_machine.items():
        validate_cohorts(cohorts)
        item = machines[machine]
        pool = cohorts.target_normal_pool
        cohort_fields = {
            "source_fit": cohorts.source_fit,
            "target_normal_pool": cohorts.target_normal_pool,
            "target_anomaly_evaluate": cohorts.target_anomaly_evaluate,
        }
        for field, expected_clips in cohort_fields.items():
            expected_entries = [
                _clip_manifest_entry(c, i) for i, c in enumerate(expected_clips)
            ]
            if item[field] != expected_entries:
                raise ValueError(f"{machine}: manifest {field} ne odgovara datasetu")
            hash_field = f"{field}_manifest_sha256"
            if item[hash_field] != _cohort_input_manifest_hash(expected_clips):
                raise ValueError(f"{machine}: neispravan {hash_field}")
        expected = set(range(len(pool)))
        ids = set()
        for split in item["splits"]:
            split_id = split["calibration_split_id"]
            if split_id in ids:
                raise ValueError(f"{machine}: dupli calibration_split_id {split_id}")
            ids.add(split_id)
            cal = set(split["calibration_pool_indices"])
            held = set(split["held_out_normal_pool_indices"])
            if cal & held:
                raise ValueError(f"{machine}/{split_id}: cal/held overlap")
            if cal | held != expected:
                raise ValueError(f"{machine}/{split_id}: cal/held ne pokrivaju pool")
            if len(cal) != manifest["k"]:
                raise ValueError(f"{machine}/{split_id}: pogresan broj calibration klipova")
            if any(pool[i].label != 0 or pool[i].domain != "target" for i in cal):
                raise ValueError(f"{machine}/{split_id}: kalibracija sadrzi anomaliju")


class PhaseAudit:
    """Fail-fast zabrana pristupa anomalnom audiju prije evaluate faze."""

    def __init__(self) -> None:
        self.phase = "prepare_and_fit"
        self.target_anomaly_feature_reads = 0

    def enter_evaluate(self) -> None:
        if self.phase != "prepare_and_fit":
            raise RuntimeError("evaluate faza je vec otvorena")
        self.phase = "evaluate"

    def record_feature_read(self, clips: Sequence[ClipRef]) -> None:
        has_anomaly = any(c.label == 1 for c in clips)
        if has_anomaly and self.phase != "evaluate":
            raise RuntimeError("target anomaly feature-i se smiju citati samo u evaluate fazi")
        if has_anomaly:
            self.target_anomaly_feature_reads += len(clips)


def _mel_summaries(path: Path) -> tuple[np.ndarray, np.ndarray]:
    stacked = features.wav_to_vectors(str(path)).astype(np.float64)
    mel1280 = np.concatenate([stacked.mean(axis=0), stacked.std(axis=0)])
    reconstructed = np.concatenate(
        [stacked[:, : features.N_MELS], stacked[-1, features.N_MELS :].reshape(4, features.N_MELS)],
        axis=0,
    )
    mel256 = np.concatenate([reconstructed.mean(axis=0), reconstructed.std(axis=0)])
    return mel1280, mel256


def _psd_shape(path: Path) -> np.ndarray:
    audio, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    if sample_rate != features.SR:
        raise ValueError(f"{path}: ocekivano {features.SR} Hz, dobijeno {sample_rate}")
    signal = audio[:, 0].astype(np.float64)
    signal -= signal.mean()
    frequencies, power = welch(
        signal,
        fs=features.SR,
        window="hann",
        nperseg=8192,
        noverlap=4096,
        detrend=False,
        scaling="spectrum",
    )
    raw = _band_log_power(
        frequencies, power, np.geomspace(10.0, 4000.0, 97)
    )
    return raw - raw.mean()


def _extract_clip_feature_bundle(path: Path) -> dict[str, np.ndarray]:
    mel1280, mel256 = _mel_summaries(path)
    return {
        "mel1280": mel1280,
        "mel256": mel256,
        "psd_shape": _psd_shape(path),
    }


class CohortFeatureStore:
    """Odvojeni cachevi garantuju da normalni fit ne otvara anomaly cache."""

    def __init__(
        self,
        machine: str,
        cache_root: Path,
        audit: PhaseAudit,
        *,
        extractor: Callable[[Path], Mapping[str, np.ndarray]] = _extract_clip_feature_bundle,
        dependencies: Mapping[str, str] | None = None,
        extractor_sources: Mapping[str, str] | None = None,
    ) -> None:
        self.machine = machine
        self.cache_root = cache_root / PROTOCOL_VERSION / machine
        self.audit = audit
        self.extractor = extractor
        self.dependencies = dict(dependencies or dependency_versions())
        self.extractor_sources = dict(extractor_sources or relevant_source_hashes())

    def _expected_metadata(
        self, cohort_name: str, clips: Sequence[ClipRef]
    ) -> dict[str, object]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "machine": self.machine,
            "cohort_name": cohort_name,
            "cohort_input_manifest_sha256": _cohort_input_manifest_hash(clips),
            "method_spec_sha256": _method_spec_hash(),
            "method_specs": [asdict(spec) for spec in METHOD_SPECS],
            "extractor_source_sha256": self.extractor_sources,
            "dependency_versions": self.dependencies,
        }

    def load_or_extract(self, cohort_name: str, clips: Sequence[ClipRef]) -> dict[str, np.ndarray]:
        self.audit.record_feature_read(clips)
        expected_paths = [c.relative_path for c in clips]
        cache_path = self.cache_root / f"{cohort_name}.npz"
        expected_metadata = self._expected_metadata(cohort_name, clips)
        if cache_path.exists():
            with np.load(cache_path) as cached:
                if "metadata_json" not in cached.files:
                    raise RuntimeError(
                        f"{cache_path}: legacy/stale cache nema provenance metadata"
                    )
                actual_metadata = json.loads(str(cached["metadata_json"].item()))
                if actual_metadata != expected_metadata:
                    raise RuntimeError(
                        f"{cache_path}: stale cache provenance; ukloni samo ovaj canonical cache "
                        "i ponovi ekstrakciju"
                    )
                cached_paths = [str(x) for x in cached["relative_paths"]]
                if cached_paths != expected_paths:
                    raise RuntimeError(f"{cache_path}: cache putanje ne odgovaraju kohorti")
                arrays = {name: np.asarray(cached[name], np.float64) for name in METHOD_ORDER}
            self._validate_arrays(arrays, len(clips), cache_path)
            return arrays

        rows = {name: [] for name in METHOD_ORDER}
        for number, clip in enumerate(clips, start=1):
            path = ROOT / clip.relative_path
            extracted = self.extractor(path)
            if set(extracted) != set(METHOD_ORDER):
                raise RuntimeError("ekstraktor nije vratio tacno fiksne kanonske metode")
            for method in METHOD_ORDER:
                rows[method].append(np.asarray(extracted[method], np.float64))
            if number % 50 == 0 or number == len(clips):
                print(f"  {self.machine}/{cohort_name}: feature-i {number}/{len(clips)}")
        arrays = {name: np.stack(values) for name, values in rows.items()}
        self._validate_arrays(arrays, len(clips), cache_path)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        temp_path = cache_path.with_name(f".{cache_path.name}.{os.getpid()}.tmp")
        try:
            with temp_path.open("wb") as handle:
                np.savez_compressed(
                    handle,
                    metadata_json=np.asarray(
                        json.dumps(expected_metadata, sort_keys=True, ensure_ascii=False)
                    ),
                    relative_paths=np.asarray(expected_paths),
                    **arrays,
                )
            os.replace(temp_path, cache_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
        return arrays

    @staticmethod
    def _validate_arrays(arrays: Mapping[str, np.ndarray], n_rows: int, source: Path) -> None:
        expected_dims = {spec.name: spec.feature_dimension for spec in METHOD_SPECS}
        if set(arrays) != set(METHOD_ORDER):
            raise RuntimeError(f"{source}: cache nema tacno kanonske metode")
        for name, array in arrays.items():
            if array.shape != (n_rows, expected_dims[name]):
                raise RuntimeError(f"{source}: {name} shape={array.shape}")
            if not np.isfinite(array).all():
                raise RuntimeError(f"{source}: {name} sadrzi NaN/Inf")


@dataclass(frozen=True)
class StatisticalModel:
    source_mean: np.ndarray
    source_scale: np.ndarray
    precision: np.ndarray

    def transform(self, values: np.ndarray) -> np.ndarray:
        return (values - self.source_mean) / self.source_scale


def fit_source_only(values: np.ndarray) -> StatisticalModel:
    source_mean = values.mean(axis=0)
    source_scale = values.std(axis=0)
    source_scale = np.where(source_scale < 1e-8, 1.0, source_scale)
    standardized = (values - source_mean) / source_scale
    precision = LedoitWolf().fit(standardized).precision_
    return StatisticalModel(source_mean, source_scale, precision)


def mahalanobis(values: np.ndarray, center: np.ndarray, precision: np.ndarray) -> np.ndarray:
    difference = values - center
    return np.einsum("ij,jk,ik->i", difference, precision, difference)


def bootstrap_mean_ci(
    values: Sequence[float], bootstrap_indices: np.ndarray
) -> tuple[float, float]:
    array = np.asarray(values, dtype=np.float64)
    if bootstrap_indices.ndim != 2 or bootstrap_indices.shape[1] != len(array):
        raise ValueError("bootstrap_indices shape ne odgovara broju splitova")
    means = array[bootstrap_indices].mean(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return float(low), float(high)


def summarize_metric(
    values: Sequence[float], bootstrap_indices: np.ndarray
) -> dict[str, float | str]:
    low, high = bootstrap_mean_ci(values, bootstrap_indices)
    return {
        "mean": float(np.mean(values)),
        "calibration_split_std": float(np.std(values, ddof=0)),
        "bootstrap_95ci_of_split_mean_lower": low,
        "bootstrap_95ci_of_split_mean_upper": high,
        "bootstrap_unit": "predefined_calibration_splits",
    }


@dataclass(frozen=True)
class QuadraticScoreCache:
    """Precompute the O(n*d^2) part of Mahalanobis scoring once per method."""

    values: np.ndarray
    values_times_precision: np.ndarray
    self_quadratic: np.ndarray
    precision: np.ndarray

    @classmethod
    def build(cls, values: np.ndarray, precision: np.ndarray) -> "QuadraticScoreCache":
        values_times_precision = values @ precision
        self_quadratic = np.einsum("ij,ij->i", values_times_precision, values)
        return cls(values, values_times_precision, self_quadratic, precision)

    def scores_from_center(self, center: np.ndarray) -> np.ndarray:
        center_times_precision = center @ self.precision
        center_quadratic = float(center_times_precision @ center)
        scores = (
            self.self_quadratic
            - 2.0 * (self.values_times_precision @ center)
            + center_quadratic
        )
        # Roundoff can create tiny negative values for an exactly matching center.
        return np.maximum(scores, 0.0)


def _evaluate_method(
    model: StatisticalModel,
    normal_pool: np.ndarray,
    anomalies: np.ndarray,
    splits: Sequence[Mapping[str, object]],
) -> tuple[list[dict], list[float], list[float]]:
    normal_z = model.transform(normal_pool)
    anomaly_z = model.transform(anomalies)
    normal_quadratic = QuadraticScoreCache.build(normal_z, model.precision)
    anomaly_quadratic = QuadraticScoreCache.build(anomaly_z, model.precision)
    per_split: list[dict] = []
    auc_values: list[float] = []
    pauc_values: list[float] = []
    for split in splits:
        calibration = np.asarray(split["calibration_pool_indices"], dtype=int)
        held = np.asarray(split["held_out_normal_pool_indices"], dtype=int)
        if set(calibration) & set(held):
            raise RuntimeError("calibration i held-out indeksi se preklapaju")
        center = normal_z[calibration].mean(axis=0)
        held_scores = normal_quadratic.scores_from_center(center)[held]
        anomaly_scores = anomaly_quadratic.scores_from_center(center)
        labels = np.concatenate([np.zeros(len(held)), np.ones(len(anomalies))])
        scores = np.concatenate([held_scores, anomaly_scores])
        auc = float(roc_auc_score(labels, scores))
        pauc = float(roc_auc_score(labels, scores, max_fpr=MAX_FPR))
        auc_values.append(auc)
        pauc_values.append(pauc)
        per_split.append(
            {
                "calibration_split_id": split["calibration_split_id"],
                "n_calibration_normal": len(calibration),
                "n_held_out_normal": len(held),
                "n_target_anomaly": len(anomalies),
                "auc": auc,
                "standardized_pauc_at_fpr_0_1": pauc,
            }
        )
    return per_split, auc_values, pauc_values


def _git_output(repo: Path, args: Sequence[str], *, binary: bool = False):
    return subprocess.check_output(
        ["git", *args], cwd=repo, text=not binary, stderr=subprocess.STDOUT
    )


def git_provenance(
    repo: Path = ROOT, relevant_paths: Sequence[str] | None = None
) -> dict[str, object]:
    paths = tuple(
        relevant_paths
        or (
            "pc/tools/evaluate_canonical.py",
            "pc/asd/features.py",
            "pc/tools/bench_periodicity.py",
        )
    )
    try:
        commit = _git_output(repo, ["rev-parse", "HEAD"]).strip()
        status_lines = [
            line
            for line in _git_output(
                repo, ["status", "--porcelain=v1", "--untracked-files=all"]
            ).splitlines()
            if line
        ]
        tracked_diff = _git_output(repo, ["diff", "--binary", "HEAD", "--", *paths], binary=True)
        source_records = {}
        for relative in paths:
            path = repo / relative
            tracked = (
                subprocess.run(
                    ["git", "ls-files", "--error-unmatch", "--", relative],
                    cwd=repo,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                ).returncode
                == 0
            )
            source_records[relative] = {
                "content_sha256": _sha256_file(path),
                "git_tracked": tracked,
            }
        return {
            "head_commit": commit,
            "working_tree_dirty": bool(status_lines),
            "status_porcelain": status_lines,
            "relevant_tracked_diff_sha256": hashlib.sha256(tracked_diff).hexdigest(),
            "relevant_source_files": source_records,
            "warning": (
                "Results identify both HEAD and exact source hashes; dirty or untracked "
                "evaluator code must not be attributed to HEAD alone."
            ),
        }
    except (OSError, subprocess.CalledProcessError) as exc:
        return {
            "head_commit": "unavailable",
            "working_tree_dirty": None,
            "status_porcelain": [],
            "relevant_tracked_diff_sha256": None,
            "relevant_source_files": {
                relative: {"content_sha256": _sha256_file(repo / relative), "git_tracked": None}
                for relative in paths
                if (repo / relative).is_file()
            },
            "warning": f"Git provenance unavailable: {exc}",
        }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_flat_csv(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    rows = list(rows)
    if not rows:
        raise ValueError("nema redova za CSV")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def resolve_output_dir(value: str | Path, cwd: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (cwd or Path.cwd()) / path
    return path.resolve()


def build_run_identity(
    args: argparse.Namespace,
    *,
    dependencies: Mapping[str, str],
    manifest_sha256: str,
    source_hashes: Mapping[str, str] | None = None,
) -> tuple[str, dict]:
    machine_set = sorted(args.machines)
    source_bundle_sha256 = _sha256_json(source_hashes or relevant_source_hashes())
    dependency_versions_sha256 = _sha256_json(dict(dependencies))
    config = {
        "protocol_version": PROTOCOL_VERSION,
        "method_spec_sha256": _method_spec_hash(),
        "relevant_source_bundle_sha256": source_bundle_sha256,
        "dependency_versions_sha256": dependency_versions_sha256,
        "dataset_and_split_manifest_sha256": manifest_sha256,
        "machines": machine_set,
        "k": args.k,
        "n_splits": args.n_splits,
        "split_random_state": args.split_random_state,
        "bootstrap_resamples": args.bootstrap_resamples,
        "bootstrap_random_state": args.bootstrap_random_state,
    }
    config_hash = _sha256_json(config)
    machine_hash = _sha256_json(machine_set)[:8]
    run_id = (
        f"{PROTOCOL_VERSION}_m{len(machine_set)}-{machine_hash}_k{args.k}_"
        f"s{args.n_splits}_sr{args.split_random_state}_b{args.bootstrap_resamples}_"
        f"br{args.bootstrap_random_state}_ms{_method_spec_hash()[:8]}_"
        f"src{source_bundle_sha256[:8]}_dep{dependency_versions_sha256[:8]}_"
        f"data{manifest_sha256[:8]}_{config_hash[:12]}"
    )
    return run_id, {**config, "run_config_sha256": config_hash}


def publish_run_directory_atomic(
    output_root: Path, run_id: str, writer: Callable[[Path], None]
) -> Path:
    """Expose a complete run with one same-filesystem rename; never overwrite."""

    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    final_dir = output_root / run_id
    if final_dir.exists():
        raise FileExistsError(f"run vec postoji i nece biti prepisan: {final_dir}")
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{run_id}.tmp-", dir=output_root))
    try:
        writer(temp_dir)
        if final_dir.exists():
            raise FileExistsError(f"run se pojavio tokom pisanja: {final_dir}")
        temp_dir.rename(final_dir)
        return final_dir
    except Exception:
        # temp_dir is guaranteed to be a direct child of the explicitly selected root.
        if temp_dir.exists() and temp_dir.parent == output_root:
            shutil.rmtree(temp_dir)
        raise


def _required_mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{context} mora biti objekt/mapa")
    return value


def _required_text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{context} mora biti neprazan tekst")
    return value


def _finite_number(value: object, context: str) -> float:
    if isinstance(value, bool):
        raise RuntimeError(f"{context} mora biti konacan broj")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{context} mora biti konacan broj") from exc
    if not math.isfinite(number):
        raise RuntimeError(f"{context} mora biti konacan broj")
    return number


def _finite_integer(value: object, context: str, *, minimum: int = 0) -> int:
    number = _finite_number(value, context)
    if not number.is_integer() or number < minimum:
        raise RuntimeError(f"{context} mora biti cijeli broj >= {minimum}")
    return int(number)


def _boolean(value: object, context: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value in {"True", "False"}:
        return value == "True"
    raise RuntimeError(f"{context} mora biti bool/True/False")


def _bounded_metric(value: object, context: str) -> float:
    number = _finite_number(value, context)
    if not 0.0 <= number <= 1.0:
        raise RuntimeError(f"{context} mora biti u intervalu [0, 1]")
    return number


def _validate_metric_summary(metric: object, context: str) -> None:
    values = _required_mapping(metric, context)
    required = {
        "mean",
        "calibration_split_std",
        "bootstrap_95ci_of_split_mean_lower",
        "bootstrap_95ci_of_split_mean_upper",
        "bootstrap_unit",
    }
    missing = required - set(values)
    if missing:
        raise RuntimeError(f"{context} nema polja: {sorted(missing)}")
    mean = _bounded_metric(values["mean"], f"{context}.mean")
    std = _finite_number(
        values["calibration_split_std"], f"{context}.calibration_split_std"
    )
    if std < 0:
        raise RuntimeError(f"{context}.calibration_split_std mora biti >= 0")
    lower = _bounded_metric(
        values["bootstrap_95ci_of_split_mean_lower"], f"{context}.ci_lower"
    )
    upper = _bounded_metric(
        values["bootstrap_95ci_of_split_mean_upper"], f"{context}.ci_upper"
    )
    if not lower <= mean <= upper:
        raise RuntimeError(f"{context}: bootstrap CI ne obuhvata mean")
    if values["bootstrap_unit"] != "predefined_calibration_splits":
        raise RuntimeError(f"{context}: neocekivana bootstrap jedinica")


def _validate_summary_source(result: Mapping[str, object]) -> None:
    config = _required_mapping(result.get("configuration"), "configuration")
    _finite_integer(config.get("k"), "configuration.k", minimum=1)
    n_splits = _finite_integer(
        config.get("n_splits"), "configuration.n_splits", minimum=1
    )
    _finite_integer(
        config.get("bootstrap_resamples"),
        "configuration.bootstrap_resamples",
        minimum=1,
    )
    _finite_integer(
        config.get("bootstrap_random_state"),
        "configuration.bootstrap_random_state",
    )
    _required_text(result.get("run_id"), "run_id")
    _required_text(result.get("protocol_version"), "protocol_version")
    _required_text(result.get("split_manifest_sha256"), "split_manifest_sha256")
    git = _required_mapping(result.get("git_provenance"), "git_provenance")
    _required_text(git.get("head_commit"), "git_provenance.head_commit")
    _boolean(git.get("working_tree_dirty"), "git_provenance.working_tree_dirty")
    machines = _required_mapping(result.get("machines"), "machines")
    run_config = _required_mapping(result.get("run_config"), "run_config")
    configured_machines = run_config.get("machines")
    if (
        not isinstance(configured_machines, list)
        or len(configured_machines) != len(set(configured_machines))
        or set(configured_machines) != set(machines)
    ):
        raise RuntimeError("run_config.machines i result machines nisu isti skup")
    for machine, machine_data in machines.items():
        methods = _required_mapping(
            _required_mapping(machine_data, f"machines.{machine}").get("methods"),
            f"machines.{machine}.methods",
        )
        if set(methods) != set(METHOD_ORDER):
            raise RuntimeError(f"{machine}: metode nisu tacno {list(METHOD_ORDER)}")
        reference_split_ids: list[str] | None = None
        for method in METHOD_ORDER:
            method_data = _required_mapping(methods[method], f"{machine}.{method}")
            _validate_metric_summary(method_data.get("auc"), f"{machine}.{method}.auc")
            _validate_metric_summary(
                method_data.get("standardized_pauc_at_fpr_0_1"),
                f"{machine}.{method}.standardized_pauc_at_fpr_0_1",
            )
            per_split = method_data.get("per_calibration_split")
            if not isinstance(per_split, list) or len(per_split) != n_splits:
                raise RuntimeError(f"{machine}.{method}: pogresan broj splitova")
            split_ids = [
                _required_text(
                    _required_mapping(row, f"{machine}.{method}.split").get(
                        "calibration_split_id"
                    ),
                    f"{machine}.{method}.calibration_split_id",
                )
                for row in per_split
            ]
            if len(split_ids) != len(set(split_ids)):
                raise RuntimeError(f"{machine}.{method}: dupli calibration_split_id")
            if reference_split_ids is None:
                reference_split_ids = split_ids
            elif split_ids != reference_split_ids:
                raise RuntimeError(f"{machine}: metode nemaju isti/redom jednak split_id skup")


def render_summary_markdown(result: Mapping[str, object]) -> str:
    _validate_summary_source(result)
    config = result["configuration"]
    lines = [
        f"# Developmental benchmark `{result['run_id']}`",
        "",
        "> Within-run leakage is guarded, but historical model-selection bias remains. "
        "This is not an independent final validation and covers only mel1280, mel256 and psd_shape.",
        "",
        f"- Protocol: `{result['protocol_version']}`",
        f"- Git HEAD: `{result['git_provenance']['head_commit']}`",
        f"- Dirty working tree: `{result['git_provenance']['working_tree_dirty']}`",
        f"- k / splits: `{config['k']}` / `{config['n_splits']}`",
        "- Metrics: AUC and **standardized pAUC@FPR<=0.1** "
        "(`sklearn` standardized partial AUC with `max_fpr=0.1`).",
        f"- Bootstrap 95% CI: mean across predefined calibration splits, "
        f"`{config['bootstrap_resamples']}` resamples, seed/random state "
        f"`{config['bootstrap_random_state']}`.",
        f"- Manifest SHA-256: `{result['split_manifest_sha256']}`",
        "",
        "| Machine | Front-end | AUC mean | AUC bootstrap 95% CI | split std | "
        "standardized pAUC@FPR<=0.1 mean | pAUC bootstrap 95% CI | split std |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for machine, machine_data in result["machines"].items():
        for method, method_data in machine_data["methods"].items():
            auc = method_data["auc"]
            pauc = method_data["standardized_pauc_at_fpr_0_1"]
            lines.append(
                f"| {machine} | {method} | {auc['mean']:.4f} | "
                f"[{auc['bootstrap_95ci_of_split_mean_lower']:.4f}, "
                f"{auc['bootstrap_95ci_of_split_mean_upper']:.4f}] | "
                f"{auc['calibration_split_std']:.4f} | {pauc['mean']:.4f} | "
                f"[{pauc['bootstrap_95ci_of_split_mean_lower']:.4f}, "
                f"{pauc['bootstrap_95ci_of_split_mean_upper']:.4f}] | "
                f"{pauc['calibration_split_std']:.4f} |"
            )
    lines.extend(["", "Dependency versions:", ""])
    for name, version in result["dependency_versions"].items():
        lines.append(f"- `{name}={version}`")
    lines.append("")
    return "\n".join(lines)


def validate_output_schema(
    result: Mapping[str, object], aggregate_rows: Sequence[Mapping[str, object]], raw_rows: Sequence[Mapping[str, object]]
) -> None:
    required = {
        "run_id",
        "protocol_version",
        "run_config",
        "configuration",
        "git_provenance",
        "dependency_versions",
        "split_manifest_sha256",
        "method_specs",
        "machines",
    }
    missing = required - set(result)
    if missing:
        raise RuntimeError(f"result schema nema polja: {sorted(missing)}")
    _validate_summary_source(result)

    config = _required_mapping(result["configuration"], "configuration")
    run_config = _required_mapping(result["run_config"], "run_config")
    git = _required_mapping(result["git_provenance"], "git_provenance")
    expected_machines = set(run_config["machines"])
    expected_methods = set(METHOD_ORDER)
    expected_split_ids: dict[str, set[str]] = {}
    for machine in expected_machines:
        first_method = result["machines"][machine]["methods"][METHOD_ORDER[0]]
        expected_split_ids[machine] = {
            row["calibration_split_id"]
            for row in first_method["per_calibration_split"]
        }

    expected_aggregate_keys = {
        (machine, method)
        for machine in expected_machines
        for method in expected_methods
    }
    aggregate_keys: list[tuple[str, str]] = []
    for index, row in enumerate(aggregate_rows):
        context = f"aggregate row {index}"
        missing_columns = set(AGGREGATE_CSV_COLUMNS) - set(row)
        if missing_columns:
            raise RuntimeError(f"{context} nema CSV kolone: {sorted(missing_columns)}")
        machine = _required_text(row["machine"], f"{context}.machine")
        method = _required_text(row["method"], f"{context}.method")
        aggregate_keys.append((machine, method))
        _validate_common_csv_metadata(row, result, git, context)
        if _required_text(row["training_seed"], f"{context}.training_seed") != "not_applicable":
            raise RuntimeError(f"{context}: training_seed nije not_applicable")
        if _finite_integer(row["k"], f"{context}.k", minimum=1) != int(config["k"]):
            raise RuntimeError(f"{context}: k nije konzistentan")
        if _finite_integer(row["calibration_split_count"], f"{context}.calibration_split_count", minimum=1) != int(config["n_splits"]):
            raise RuntimeError(f"{context}: broj splitova nije konzistentan")
        if _finite_integer(row["bootstrap_resamples"], f"{context}.bootstrap_resamples", minimum=1) != int(config["bootstrap_resamples"]):
            raise RuntimeError(f"{context}: bootstrap_resamples nije konzistentan")
        if _finite_integer(row["bootstrap_random_state"], f"{context}.bootstrap_random_state") != int(config["bootstrap_random_state"]):
            raise RuntimeError(f"{context}: bootstrap_random_state nije konzistentan")
        mean_pairs = (
            ("auc_mean", "auc_bootstrap_95ci_of_split_mean_lower", "auc_bootstrap_95ci_of_split_mean_upper"),
            ("standardized_pauc_at_fpr_0_1_mean", "pauc_bootstrap_95ci_of_split_mean_lower", "pauc_bootstrap_95ci_of_split_mean_upper"),
        )
        for mean_name, lower_name, upper_name in mean_pairs:
            mean = _bounded_metric(row[mean_name], f"{context}.{mean_name}")
            lower = _bounded_metric(row[lower_name], f"{context}.{lower_name}")
            upper = _bounded_metric(row[upper_name], f"{context}.{upper_name}")
            if not lower <= mean <= upper:
                raise RuntimeError(f"{context}: {lower_name}/{upper_name} ne obuhvata mean")
        for std_name in ("auc_calibration_split_std", "pauc_calibration_split_std"):
            if _finite_number(row[std_name], f"{context}.{std_name}") < 0:
                raise RuntimeError(f"{context}.{std_name} mora biti >= 0")

    if len(aggregate_keys) != len(set(aggregate_keys)):
        raise RuntimeError("aggregate CSV ima duple machine/method kljuceve")
    if set(aggregate_keys) != expected_aggregate_keys:
        raise RuntimeError("aggregate CSV nema ocekivani machine/method skup")

    expected_raw_keys = {
        (machine, method, split_id)
        for machine in expected_machines
        for method in expected_methods
        for split_id in expected_split_ids[machine]
    }
    raw_keys: list[tuple[str, str, str]] = []
    for index, row in enumerate(raw_rows):
        context = f"per-split row {index}"
        missing_columns = set(PER_SPLIT_CSV_COLUMNS) - set(row)
        if missing_columns:
            raise RuntimeError(f"{context} nema CSV kolone: {sorted(missing_columns)}")
        machine = _required_text(row["machine"], f"{context}.machine")
        method = _required_text(row["method"], f"{context}.method")
        split_id = _required_text(
            row["calibration_split_id"], f"{context}.calibration_split_id"
        )
        raw_keys.append((machine, method, split_id))
        _validate_common_csv_metadata(row, result, git, context)
        if _required_text(row["training_seed"], f"{context}.training_seed") != "not_applicable":
            raise RuntimeError(f"{context}: training_seed nije not_applicable")
        for count_name in (
            "n_calibration_normal",
            "n_held_out_normal",
            "n_target_anomaly",
        ):
            _finite_integer(row[count_name], f"{context}.{count_name}", minimum=1)
        _bounded_metric(row["auc"], f"{context}.auc")
        _bounded_metric(
            row["standardized_pauc_at_fpr_0_1"],
            f"{context}.standardized_pauc_at_fpr_0_1",
        )

    if len(raw_keys) != len(set(raw_keys)):
        raise RuntimeError("per-split CSV ima duple machine/method/split_id kljuceve")
    if set(raw_keys) != expected_raw_keys:
        raise RuntimeError("per-split CSV nema ocekivani machine/method/split_id skup")


def _validate_common_csv_metadata(
    row: Mapping[str, object],
    result: Mapping[str, object],
    git: Mapping[str, object],
    context: str,
) -> None:
    expected = {
        "run_id": result["run_id"],
        "protocol_version": result["protocol_version"],
        "git_head_commit": git["head_commit"],
        "split_manifest_sha256": result["split_manifest_sha256"],
    }
    for field, expected_value in expected.items():
        if _required_text(row[field], f"{context}.{field}") != expected_value:
            raise RuntimeError(f"{context}.{field} nije konzistentan")
    expected_dirty = _boolean(
        git["working_tree_dirty"], "git_provenance.working_tree_dirty"
    )
    if (
        _boolean(row["working_tree_dirty"], f"{context}.working_tree_dirty")
        != expected_dirty
    ):
        raise RuntimeError(f"{context}.working_tree_dirty nije konzistentan")


def run(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    unknown = set(args.machines) - set(MACHINES)
    if unknown:
        raise ValueError(f"nepoznate masine: {sorted(unknown)}")
    output_root = resolve_output_dir(args.output_dir)
    selected_machines = sorted(args.machines)
    dependencies = dependency_versions()
    extractor_sources = relevant_source_hashes()
    git_info = git_provenance()
    print("provjera SHA-256 identiteta svih koristenih WAV kohorti...")
    cohorts_by_machine = {machine: discover_machine(machine) for machine in selected_machines}
    manifest = build_split_manifest(
        cohorts_by_machine,
        k=args.k,
        n_splits=args.n_splits,
        split_random_state=args.split_random_state,
    )
    run_id, run_config = build_run_identity(
        args,
        dependencies=dependencies,
        manifest_sha256=manifest["content_sha256"],
        source_hashes=extractor_sources,
    )
    final_dir = output_root / run_id
    if final_dir.exists():
        raise FileExistsError(f"run vec postoji i nece biti prepisan: {final_dir}")

    result: dict = {
        "run_id": run_id,
        "protocol_version": PROTOCOL_VERSION,
        "benchmark_scope": (
            "within-run leakage guarded developmental benchmark of exactly three "
            "statistical front-ends; excludes historical AE/neural systems"
        ),
        "git_provenance": git_info,
        "dependency_versions": dependencies,
        "extractor_source_sha256": extractor_sources,
        "run_config": run_config,
        "historical_model_selection_bias": (
            "Methods were fixed before this canonical run, but they were discovered during "
            "earlier experiments that inspected target anomaly performance. This evaluation "
            "does not erase that historical selection bias; independent fans/sessions are "
            "required for an unbiased confirmation."
        ),
        "split_manifest_file": "dataset_and_split_manifest.json",
        "split_manifest_sha256": manifest["content_sha256"],
        "configuration": {
            "k": args.k,
            "n_splits": args.n_splits,
            "split_random_state": args.split_random_state,
            "bootstrap_resamples": args.bootstrap_resamples,
            "bootstrap_random_state": args.bootstrap_random_state,
            "max_fpr": MAX_FPR,
        },
        "method_specs": [asdict(spec) for spec in METHOD_SPECS],
        "machines": {},
    }
    aggregate_rows: list[dict] = []
    raw_rows: list[dict] = []
    bootstrap_rng = np.random.default_rng(args.bootstrap_random_state)
    bootstrap_indices = bootstrap_rng.integers(
        0, args.n_splits, size=(args.bootstrap_resamples, args.n_splits)
    )

    cache_root = resolve_output_dir(args.cache_dir)
    for machine in selected_machines:
        print(f"\n{machine}: priprema normalnih kohorti i source-only fit")
        cohorts = cohorts_by_machine[machine]
        audit = PhaseAudit()
        store = CohortFeatureStore(
            machine,
            cache_root,
            audit,
            dependencies=dependencies,
            extractor_sources=extractor_sources,
        )
        source_features = store.load_or_extract("source_train_normal", cohorts.source_fit)
        normal_features = store.load_or_extract("target_normal_pool", cohorts.target_normal_pool)
        models = {name: fit_source_only(source_features[name]) for name in METHOD_ORDER}
        if audit.target_anomaly_feature_reads != 0:
            raise RuntimeError("anomaly feature-i su procitani prije kraja fit faze")
        if tuple(models) != METHOD_ORDER:
            raise RuntimeError("nisu fitovane tacno fiksne kanonske metode")

        # Jedina tacka u programu na kojoj se otvara anomaly feature kohorta.
        audit.enter_evaluate()
        anomaly_features = store.load_or_extract(
            "target_anomaly_evaluate", cohorts.target_anomaly_evaluate
        )
        if audit.target_anomaly_feature_reads != len(cohorts.target_anomaly_evaluate):
            raise RuntimeError("anomaly access audit nije konzistentan")

        machine_manifest = manifest["machines"][machine]
        split_ids_reference = [
            split["calibration_split_id"] for split in machine_manifest["splits"]
        ]
        dataset_counts = {
            "source_train_normal_fit": len(cohorts.source_fit),
            "target_train_normal_in_pool": sum(
                c.dataset_split == "train" for c in cohorts.target_normal_pool
            ),
            "target_test_normal_in_pool": sum(
                c.dataset_split == "test" for c in cohorts.target_normal_pool
            ),
            "target_normal_pool_total": len(cohorts.target_normal_pool),
            "target_test_anomaly_evaluate_only": len(cohorts.target_anomaly_evaluate),
        }
        machine_out = {
            "dataset_counts": dataset_counts,
            "access_audit": {
                "target_anomaly_features_before_evaluate": 0,
                "target_anomaly_features_in_evaluate": audit.target_anomaly_feature_reads,
            },
            "methods": {},
        }
        for method in METHOD_ORDER:
            per_split, auc_values, pauc_values = _evaluate_method(
                models[method],
                normal_features[method],
                anomaly_features[method],
                machine_manifest["splits"],
            )
            if [row["calibration_split_id"] for row in per_split] != split_ids_reference:
                raise RuntimeError(f"{machine}/{method}: metode nisu koristile iste splitove")
            auc_summary = summarize_metric(auc_values, bootstrap_indices)
            pauc_summary = summarize_metric(pauc_values, bootstrap_indices)
            method_out = {
                "training_seed": None,
                "training_seed_semantics": "not_applicable_deterministic_statistical_method",
                "split_manifest_sha256": manifest["content_sha256"],
                "auc": auc_summary,
                "standardized_pauc_at_fpr_0_1": pauc_summary,
                "per_calibration_split": per_split,
            }
            machine_out["methods"][method] = method_out
            print(
                f"  {method:10s} AUC={auc_summary['mean']:.3f} "
                f"+/-{auc_summary['calibration_split_std']:.3f}; "
                f"pAUC@0.1={pauc_summary['mean']:.3f} "
                f"+/-{pauc_summary['calibration_split_std']:.3f}"
            )
            aggregate_rows.append(
                {
                    "run_id": run_id,
                    "protocol_version": PROTOCOL_VERSION,
                    "git_head_commit": git_info["head_commit"],
                    "working_tree_dirty": git_info["working_tree_dirty"],
                    "machine": machine,
                    "method": method,
                    "training_seed": "not_applicable",
                    "k": args.k,
                    "calibration_split_count": args.n_splits,
                    "split_manifest_sha256": manifest["content_sha256"],
                    "auc_mean": auc_summary["mean"],
                    "auc_calibration_split_std": auc_summary["calibration_split_std"],
                    "auc_bootstrap_95ci_of_split_mean_lower": auc_summary[
                        "bootstrap_95ci_of_split_mean_lower"
                    ],
                    "auc_bootstrap_95ci_of_split_mean_upper": auc_summary[
                        "bootstrap_95ci_of_split_mean_upper"
                    ],
                    "standardized_pauc_at_fpr_0_1_mean": pauc_summary["mean"],
                    "pauc_calibration_split_std": pauc_summary["calibration_split_std"],
                    "pauc_bootstrap_95ci_of_split_mean_lower": pauc_summary[
                        "bootstrap_95ci_of_split_mean_lower"
                    ],
                    "pauc_bootstrap_95ci_of_split_mean_upper": pauc_summary[
                        "bootstrap_95ci_of_split_mean_upper"
                    ],
                    "bootstrap_resamples": args.bootstrap_resamples,
                    "bootstrap_random_state": args.bootstrap_random_state,
                }
            )
            for split_row in per_split:
                raw_rows.append(
                    {
                        "run_id": run_id,
                        "protocol_version": PROTOCOL_VERSION,
                        "git_head_commit": git_info["head_commit"],
                        "working_tree_dirty": git_info["working_tree_dirty"],
                        "machine": machine,
                        "method": method,
                        "training_seed": "not_applicable",
                        "calibration_split_id": split_row["calibration_split_id"],
                        "split_manifest_sha256": manifest["content_sha256"],
                        "n_calibration_normal": split_row["n_calibration_normal"],
                        "n_held_out_normal": split_row["n_held_out_normal"],
                        "n_target_anomaly": split_row["n_target_anomaly"],
                        "auc": split_row["auc"],
                        "standardized_pauc_at_fpr_0_1": split_row[
                            "standardized_pauc_at_fpr_0_1"
                        ],
                    }
                )
        result["machines"][machine] = machine_out

    validate_output_schema(result, aggregate_rows, raw_rows)

    def write_complete_run(temp_dir: Path) -> None:
        _write_json(temp_dir / "dataset_and_split_manifest.json", manifest)
        _write_json(temp_dir / "aggregate_results.json", result)
        _write_flat_csv(temp_dir / "aggregate_summary.csv", aggregate_rows)
        _write_flat_csv(temp_dir / "per_split_metrics.csv", raw_rows)
        (temp_dir / "SUMMARY.md").write_text(
            render_summary_markdown(result), encoding="utf-8"
        )

    published = publish_run_directory_atomic(output_root, run_id, write_complete_run)
    print(f"\nobjavljen kompletan run: {published}")
    return (
        published / "dataset_and_split_manifest.json",
        published / "aggregate_results.json",
        published / "aggregate_summary.csv",
        published / "per_split_metrics.csv",
        published / "SUMMARY.md",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--machines", nargs="+", choices=MACHINES, default=list(MACHINES))
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--n-splits", type=int, default=DEFAULT_N_SPLITS)
    parser.add_argument("--split-random-state", type=int, default=DEFAULT_SPLIT_RANDOM_STATE)
    parser.add_argument("--bootstrap-resamples", type=int, default=DEFAULT_BOOTSTRAP_RESAMPLES)
    parser.add_argument(
        "--bootstrap-random-state", type=int, default=DEFAULT_BOOTSTRAP_RANDOM_STATE
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=ROOT / "results" / "cache" / "canonical"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "results" / "canonical_evaluation"
    )
    parser.add_argument(
        "--regenerate-summary-from",
        type=Path,
        metavar="AGGREGATE_RESULTS_JSON",
        help=(
            "ne pokrece benchmark; atomarno ponovo renderuje SUMMARY.md iskljucivo "
            "iz postojeceg aggregate_results.json"
        ),
    )
    return parser.parse_args(argv)


def regenerate_summary_from_aggregate_json(path: Path) -> Path:
    aggregate_json = path.expanduser().resolve()
    with aggregate_json.open("r", encoding="utf-8") as handle:
        result = json.load(handle)
    if not isinstance(result, Mapping):
        raise RuntimeError("aggregate_results.json mora sadrzati JSON objekt")
    rendered = render_summary_markdown(result)
    destination = aggregate_json.parent / "SUMMARY.md"
    fd, temporary_name = tempfile.mkstemp(
        prefix=".SUMMARY.md.tmp-", dir=aggregate_json.parent, text=True
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(rendered)
        os.replace(temporary, destination)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    return destination


def main() -> None:
    args = parse_args()
    if args.regenerate_summary_from is not None:
        summary = regenerate_summary_from_aggregate_json(args.regenerate_summary_from)
        print(f"SUMMARY.md regenerisan samo iz aggregate JSON-a: {summary}")
        return
    if args.bootstrap_resamples <= 0:
        raise ValueError("bootstrap_resamples mora biti pozitivan")
    run(args)


if __name__ == "__main__":
    main()
