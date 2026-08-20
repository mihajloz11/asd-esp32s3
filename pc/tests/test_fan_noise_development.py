from __future__ import annotations

import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


PC_DIR = Path(__file__).resolve().parents[1]
if str(PC_DIR) not in sys.path:
    sys.path.insert(0, str(PC_DIR))

from tools import derive_commissioning_policy as commissioning  # noqa: E402
from tools import evaluate_fan_noise_candidates as candidates  # noqa: E402


def _score_bundle(*, verify_scale: float = 1.0) -> dict[str, object]:
    phases = (
        ["CENTER_LEARNING"] * 10
        + ["COMMISSION_DERIVE"] * 24
        + ["COMMISSION_VERIFY"] * 12
    )
    rows = []
    for index, phase in enumerate(phases):
        if phase == "CENTER_LEARNING":
            offset = index
            base = 0.70 + 0.025 * offset
        elif phase == "COMMISSION_DERIVE":
            offset = index - 10
            base = 1.00 + 0.075 * offset + 0.025 * (offset % 4)
        else:
            offset = index - 34
            base = verify_scale * (0.85 + 0.06 * offset)
        rows.append({
            "window_id": f"normal-{index:03d}",
            "fan_id": "fixture-fan",
            "session_id": "fixture-session",
            "phase": phase,
            "start_s": float(index * 10),
            "end_s": float((index + 1) * 10),
            "normal_only": True,
            "label": 0,
            "candidate_scores": {
                "baseline_hard_log96": base,
                "triangular_overlap_log96": 1.11 * base + 0.01 * (offset % 3),
            },
            "tonalness_proxy": 2.0 + 0.03 * np.sin(index),
            "subsegment_instability": 0.10 + 0.005 * (index % 5),
        })
    return {
        "schema_version": commissioning.INPUT_SCHEMA_VERSION,
        "developmental": True,
        "target_anomalies_used_for_fit": False,
        "feature_manifest_id": "fixture-feature-manifest",
        "feature_candidate_ids": [
            "baseline_hard_log96", "triangular_overlap_log96",
        ],
        "model_id": "fixture-normal-model",
        "windows": rows,
    }


def _write_spectral_fixture(
    path: Path, *, role: str, n: int, phases: list[str] | None = None,
) -> None:
    frequency = np.linspace(0.0, 8000.0, 513, dtype=np.float64)
    base = 0.18 + np.exp(-frequency / 5200.0)
    for harmonic in (430.0, 870.0, 1310.0, 1760.0):
        base += 1.8 * np.exp(-0.5 * ((frequency - harmonic) / 28.0) ** 2)
    power = []
    subsegments = []
    for index in range(n):
        shape = np.exp(
            0.035 * np.sin(frequency / 255.0 + index * 0.21)
            + 0.018 * np.cos(frequency / 83.0 + index * 0.13)
        )
        row = base * shape
        if role == candidates.TARGET_ROLE:
            row = row * np.exp(
                0.18 * np.exp(-0.5 * ((frequency - 1120.0) / 95.0) ** 2)
            )
        power.append(row)
        subsegments.append([
            row * np.exp(
                0.012 * (segment - 2)
                * np.sin(frequency / 190.0 + index * 0.09)
            )
            for segment in range(5)
        ])
    labels = np.ones(n, dtype=np.int64) if role == candidates.TARGET_ROLE else np.zeros(n, dtype=np.int64)
    starts = np.arange(n, dtype=np.float64) * 10.0
    phase_values = phases if phases is not None else ["NOT_APPLICABLE"] * n
    np.savez_compressed(
        path,
        cohort_role=np.asarray(role),
        frequency_hz=frequency,
        power=np.asarray(power),
        subsegment_power=np.asarray(subsegments),
        tonalness_proxy=2.2 + 0.05 * np.sin(np.arange(n)),
        label=labels,
        phase=np.asarray(phase_values),
        start_s=starts,
        end_s=starts + 10.0,
        window_id=np.asarray([f"{role}-{index:03d}" for index in range(n)]),
        fan_id=np.asarray(["fixture-fan"] * n),
        session_id=np.asarray(["fixture-session"] * n),
    )


def test_policy_is_selected_on_derive_then_frozen_before_verify() -> None:
    first = commissioning.derive_commissioning_policy(_score_bundle())
    changed_verify = commissioning.derive_commissioning_policy(
        _score_bundle(verify_scale=50.0),
    )

    assert first["developmental"] is True
    assert first["target_anomalies_used_for_fit"] is False
    assert first["target_anomaly_reads_before_freeze"] == 0
    assert first["verify_used_for_selection"] is False
    assert first["selected_policy"] == changed_verify["selected_policy"]
    assert first["candidate_results"] == changed_verify["candidate_results"]
    assert (
        first["verify_metrics_frozen_policy"]
        != changed_verify["verify_metrics_frozen_policy"]
    )
    selected = first["selected_policy"]
    assert 0.0 < selected["T_exit"] < selected["T_enter"]
    threshold_ids = {
        result["threshold_candidate_id"]
        for result in first["candidate_results"]
    }
    assert {
        "empirical-p99_exit-p75",
        "median-plus-6mad_exit-2mad",
        "blockmax6-p90_exit-p75",
        "conformal-a05_exit-p75",
    } <= threshold_ids
    phase_ids = first["phase_window_ids"]
    assert not (
        set(phase_ids["CENTER_LEARNING"])
        & set(phase_ids["COMMISSION_DERIVE"])
    )
    assert not (
        set(phase_ids["COMMISSION_DERIVE"])
        & set(phase_ids["COMMISSION_VERIFY"])
    )


def test_commissioning_rejects_overlap_and_anomaly_rows() -> None:
    overlap = _score_bundle()
    overlap["windows"][10]["start_s"] = overlap["windows"][9]["end_s"] - 1.0
    with pytest.raises(ValueError, match="preklapaju"):
        commissioning.derive_commissioning_policy(overlap)

    contaminated = _score_bundle()
    contaminated["windows"][15]["label"] = 1
    contaminated["windows"][15]["target_anomaly"] = True
    with pytest.raises(RuntimeError, match="samo normal_only"):
        commissioning.derive_commissioning_policy(contaminated)


def test_feature_lab_keeps_target_closed_until_frozen_policy(tmp_path: Path) -> None:
    source_path = tmp_path / "source_normal.npz"
    normal_path = tmp_path / "target_normal.npz"
    anomaly_path = tmp_path / "target_anomaly.npz"
    phases = (
        ["CENTER_LEARNING"] * 10
        + ["COMMISSION_DERIVE"] * 24
        + ["COMMISSION_VERIFY"] * 12
    )
    _write_spectral_fixture(source_path, role="source_normal", n=30)
    _write_spectral_fixture(normal_path, role="target_normal", n=len(phases), phases=phases)
    _write_spectral_fixture(anomaly_path, role=candidates.TARGET_ROLE, n=7)

    denied_audit = candidates.PhaseAudit()
    with pytest.raises(RuntimeError, match="tek poslije frozen policy"):
        candidates.load_spectral_cohort(
            anomaly_path,
            expected_role=candidates.TARGET_ROLE,
            audit=denied_audit,
        )
    assert denied_audit.target_anomaly_feature_reads == 0

    manifest = candidates.build_feature_manifest()
    audit = candidates.PhaseAudit()
    source = candidates.load_spectral_cohort(
        source_path, expected_role="source_normal", audit=audit,
    )
    normal = candidates.load_spectral_cohort(
        normal_path, expected_role="target_normal", audit=audit,
    )
    model_path = tmp_path / "normal_model.npz"
    cache_root = tmp_path / "cache"
    bundle, metadata = candidates.score_bundle_from_normal(
        source=source,
        target=normal,
        manifest=manifest,
        cache_root=cache_root,
        model_path=model_path,
    )
    assert bundle["target_anomalies_used_for_fit"] is False
    assert set(bundle["windows"][0]["candidate_scores"]) == set(
        candidates.MAIN_CANDIDATES
    )
    assert all(
        "tonalness_delta" in row and "subsegment_instability" in row
        for row in bundle["windows"]
    )
    assert metadata["model_id"]

    cache_names = {path.name for path in cache_root.rglob("*.npz")}
    assert any(name.startswith("features__") for name in cache_names)
    assert any(name.startswith("scores__") for name in cache_names)

    frozen = commissioning.derive_commissioning_policy(bundle)
    frozen_before = copy.deepcopy(frozen["selected_policy"])
    readout_audit = candidates.PhaseAudit()
    readout = candidates.target_readout(
        policy=frozen,
        policy_sha256=commissioning.sha256_json(frozen),
        manifest=manifest,
        model_path=model_path,
        target_path=anomaly_path,
        cache_root=cache_root,
        audit=readout_audit,
    )
    assert readout["developmental"] is True
    assert readout["target_anomalies_used_for_fit"] is False
    assert readout["target_anomalies_read_after_policy_frozen"] is True
    assert readout["target_anomaly_feature_reads"] == 7
    assert readout["selected_policy_unchanged"] == frozen_before
    assert frozen["selected_policy"] == frozen_before


def test_target_path_is_not_opened_when_policy_is_not_frozen(tmp_path: Path) -> None:
    manifest = candidates.build_feature_manifest()
    invalid = {
        "developmental": True,
        "target_anomalies_used_for_fit": False,
        "selected_policy": {"policy_status": "still_selecting"},
    }
    audit = candidates.PhaseAudit()
    with pytest.raises(ValueError, match="nije zamrznut"):
        candidates.target_readout(
            policy=invalid,
            policy_sha256="not-a-frozen-policy",
            manifest=manifest,
            model_path=tmp_path / "missing-model.npz",
            target_path=tmp_path / "must-not-be-opened.npz",
            cache_root=tmp_path / "cache",
            audit=audit,
        )
    assert audit.target_anomaly_metadata_reads == 0
    assert audit.target_anomaly_feature_reads == 0


def test_manifests_are_written_before_any_candidate_evaluation(tmp_path: Path) -> None:
    feature_output = tmp_path / "feature-output"
    with pytest.raises(FileNotFoundError):
        candidates.prepare_normal_cli(SimpleNamespace(
            output_dir=feature_output,
            source_normal=tmp_path / "missing-source.npz",
            target_normal=tmp_path / "missing-target.npz",
            cache_dir=tmp_path / "cache",
        ))
    feature_manifest = feature_output / "feature_candidate_manifest.json"
    assert feature_manifest.is_file()
    assert b"candidate_provenance_id" in feature_manifest.read_bytes()

    contaminated = _score_bundle()
    contaminated["windows"][12]["label"] = 1
    score_input = tmp_path / "contaminated.json"
    score_input.write_bytes(commissioning.canonical_json(contaminated))
    policy_output = tmp_path / "policy-output"
    with pytest.raises(RuntimeError, match="samo normal_only"):
        commissioning.run_cli(SimpleNamespace(
            input=score_input,
            output_dir=policy_output,
        ))
    policy_manifest = policy_output / "candidate_manifest.json"
    assert policy_manifest.is_file()
    assert b"policy_candidate_ids" in policy_manifest.read_bytes()
