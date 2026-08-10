from __future__ import annotations

import copy
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

PC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PC_DIR))

from tools import evaluate_canonical as canonical  # noqa: E402


def _clip(name: str, split: str, domain: str, label: int) -> canonical.ClipRef:
    payload = name.encode()
    return canonical.ClipRef(
        f"data/fake/{split}/{name}.wav",
        split,
        domain,
        label,
        len(payload),
        canonical.hashlib.sha256(payload).hexdigest(),
    )


def _cohorts() -> canonical.MachineCohorts:
    return canonical.MachineCohorts(
        source_fit=tuple(_clip(f"source_train_normal_{i}", "train", "source", 0) for i in range(6)),
        target_normal_pool=tuple(
            [_clip(f"target_train_normal_{i}", "train", "target", 0) for i in range(2)]
            + [_clip(f"target_test_normal_{i}", "test", "target", 0) for i in range(4)]
        ),
        target_anomaly_evaluate=tuple(
            _clip(f"target_test_anomaly_{i}", "test", "target", 1) for i in range(3)
        ),
    )


def test_split_manifest_is_deterministic_disjoint_and_complete() -> None:
    cohorts = {"fan": _cohorts()}
    first = canonical.build_split_manifest(
        cohorts, k=2, n_splits=8, split_random_state=123
    )
    second = canonical.build_split_manifest(
        cohorts, k=2, n_splits=8, split_random_state=123
    )
    assert first == second
    assert first["content_sha256"] == second["content_sha256"]
    machine_manifest = first["machines"]["fan"]
    assert len(machine_manifest["source_fit"]) == 6
    assert len(machine_manifest["target_anomaly_evaluate"]) == 3
    for cohort_name in ("source_fit", "target_normal_pool", "target_anomaly_evaluate"):
        assert all("size_bytes" in row and "content_sha256" in row for row in machine_manifest[cohort_name])
    assert all(entry["label"] == "normal" for entry in first["machines"]["fan"]["target_normal_pool"])
    for split in first["machines"]["fan"]["splits"]:
        calibration = set(split["calibration_pool_indices"])
        held = set(split["held_out_normal_pool_indices"])
        assert not calibration & held
        assert calibration | held == set(range(6))


def test_manifest_and_phase_guard_fail_fast_on_leakage() -> None:
    cohorts = _cohorts()
    leaked = canonical.MachineCohorts(
        source_fit=cohorts.source_fit,
        target_normal_pool=cohorts.target_normal_pool + cohorts.target_anomaly_evaluate[:1],
        target_anomaly_evaluate=cohorts.target_anomaly_evaluate,
    )
    with pytest.raises(ValueError, match="target normale"):
        canonical.validate_cohorts(leaked)

    manifest = canonical.build_split_manifest(
        {"fan": cohorts}, k=2, n_splits=2, split_random_state=123
    )
    broken = copy.deepcopy(manifest)
    broken.pop("content_sha256")
    broken_split = broken["machines"]["fan"]["splits"][0]
    broken_split["held_out_normal_pool_indices"].append(
        broken_split["calibration_pool_indices"][0]
    )
    with pytest.raises(ValueError, match="overlap"):
        canonical.validate_split_manifest(broken, {"fan": cohorts})

    audit = canonical.PhaseAudit()
    with pytest.raises(RuntimeError, match="samo u evaluate"):
        audit.record_feature_read(cohorts.target_anomaly_evaluate)
    audit.enter_evaluate()
    audit.record_feature_read(cohorts.target_anomaly_evaluate)
    assert audit.target_anomaly_feature_reads == 3


def test_statistics_are_deterministic_and_semantically_separated() -> None:
    values = [0.6, 0.7, 0.8, 0.9]
    indices_a = np.random.default_rng(77).integers(0, 4, size=(500, 4))
    indices_b = np.random.default_rng(77).integers(0, 4, size=(500, 4))
    summary_a = canonical.summarize_metric(values, indices_a)
    summary_b = canonical.summarize_metric(values, indices_b)
    assert summary_a == summary_b
    assert summary_a["mean"] == pytest.approx(0.75)
    assert summary_a["calibration_split_std"] == pytest.approx(np.std(values))
    assert summary_a["bootstrap_unit"] == "predefined_calibration_splits"
    assert all(spec.training_seed is None for spec in canonical.METHOD_SPECS)
    assert all("not_applicable" in spec.training_seed_semantics for spec in canonical.METHOD_SPECS)


def test_all_fixed_methods_consume_identical_split_ids() -> None:
    cohorts = {"fan": _cohorts()}
    manifest = canonical.build_split_manifest(
        cohorts, k=2, n_splits=5, split_random_state=99
    )
    splits = manifest["machines"]["fan"]["splits"]
    expected_ids = [split["calibration_split_id"] for split in splits]
    source = np.random.default_rng(1).normal(size=(20, 3))
    normal = np.random.default_rng(2).normal(size=(6, 3))
    anomaly = np.random.default_rng(3).normal(loc=2.0, size=(3, 3))
    model = canonical.fit_source_only(source)
    for _method in canonical.METHOD_ORDER:
        per_split, _, _ = canonical._evaluate_method(model, normal, anomaly, splits)
        assert [row["calibration_split_id"] for row in per_split] == expected_ids


def test_quadratic_precompute_matches_direct_mahalanobis() -> None:
    rng = np.random.default_rng(8)
    source = rng.normal(size=(30, 7))
    values = rng.normal(size=(12, 7))
    model = canonical.fit_source_only(source)
    standardized = model.transform(values)
    center = standardized[:3].mean(axis=0)
    expected = canonical.mahalanobis(standardized, center, model.precision)
    actual = canonical.QuadraticScoreCache.build(
        standardized, model.precision
    ).scores_from_center(center)
    np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-10)


def test_cache_hit_miss_dimensions_and_stale_invalidation(tmp_path: Path) -> None:
    clips = _cohorts().source_fit[:2]
    calls: list[str] = []

    def fake_extractor(path: Path):
        calls.append(path.name)
        return {
            spec.name: np.full(spec.feature_dimension, len(calls), dtype=np.float64)
            for spec in canonical.METHOD_SPECS
        }

    dependencies = {"python": "test", "numpy": "test"}
    sources = {"fake_extractor.py": "abc123"}
    store = canonical.CohortFeatureStore(
        "fan",
        tmp_path,
        canonical.PhaseAudit(),
        extractor=fake_extractor,
        dependencies=dependencies,
        extractor_sources=sources,
    )
    miss = store.load_or_extract("source_train_normal", clips)
    assert len(calls) == 2
    assert {name: array.shape[1] for name, array in miss.items()} == {
        "mel1280": 1280,
        "mel256": 256,
        "psd_shape": 96,
    }

    def must_not_extract(_path: Path):
        raise AssertionError("cache hit je nepotrebno pokrenuo ekstraktor")

    hit_store = canonical.CohortFeatureStore(
        "fan",
        tmp_path,
        canonical.PhaseAudit(),
        extractor=must_not_extract,
        dependencies=dependencies,
        extractor_sources=sources,
    )
    hit = hit_store.load_or_extract("source_train_normal", clips)
    for method in canonical.METHOD_ORDER:
        np.testing.assert_array_equal(hit[method], miss[method])

    stale_store = canonical.CohortFeatureStore(
        "fan",
        tmp_path,
        canonical.PhaseAudit(),
        extractor=must_not_extract,
        dependencies={**dependencies, "numpy": "changed"},
        extractor_sources=sources,
    )
    with pytest.raises(RuntimeError, match="stale cache provenance"):
        stale_store.load_or_extract("source_train_normal", clips)


def test_atomic_writer_collision_cleanup_and_output_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert canonical.resolve_output_dir("relative-out") == (tmp_path / "relative-out").resolve()
    external = (tmp_path.parent / f"{tmp_path.name}-external").resolve()
    assert canonical.resolve_output_dir(external) == external

    output_root = tmp_path / "published"

    def writer(run_dir: Path) -> None:
        (run_dir / "one.txt").write_text("one", encoding="utf-8")
        (run_dir / "two.txt").write_text("two", encoding="utf-8")

    published = canonical.publish_run_directory_atomic(output_root, "run-a", writer)
    assert sorted(path.name for path in published.iterdir()) == ["one.txt", "two.txt"]
    with pytest.raises(FileExistsError, match="nece biti prepisan"):
        canonical.publish_run_directory_atomic(output_root, "run-a", writer)

    def failing_writer(run_dir: Path) -> None:
        (run_dir / "partial.txt").write_text("partial", encoding="utf-8")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        canonical.publish_run_directory_atomic(output_root, "run-b", failing_writer)
    assert not (output_root / "run-b").exists()
    assert not list(output_root.glob(".run-b.tmp-*"))


def test_run_identity_covers_every_result_changing_parameter() -> None:
    base = argparse.Namespace(
        machines=["fan", "ToyCar"],
        k=20,
        n_splits=100,
        split_random_state=1,
        bootstrap_resamples=2000,
        bootstrap_random_state=2,
    )
    dependencies = {"python": "3.test", "numpy": "test"}
    source_hashes = {"evaluator.py": "source-hash"}
    manifest_hash = "a" * 64
    base_id, base_config = canonical.build_run_identity(
        base,
        dependencies=dependencies,
        manifest_sha256=manifest_hash,
        source_hashes=source_hashes,
    )
    assert base_config["machines"] == ["ToyCar", "fan"]
    assert canonical._method_spec_hash()[:8] in base_id
    variants = {
        "machines": ["fan"],
        "k": 10,
        "n_splits": 99,
        "split_random_state": 3,
        "bootstrap_resamples": 1000,
        "bootstrap_random_state": 4,
    }
    for field, value in variants.items():
        changed = argparse.Namespace(**vars(base))
        setattr(changed, field, value)
        changed_id, _ = canonical.build_run_identity(
            changed,
            dependencies=dependencies,
            manifest_sha256=manifest_hash,
            source_hashes=source_hashes,
        )
        assert changed_id != base_id, field

    dependency_id, _ = canonical.build_run_identity(
        base,
        dependencies={**dependencies, "numpy": "changed"},
        manifest_sha256=manifest_hash,
        source_hashes=source_hashes,
    )
    dataset_id, _ = canonical.build_run_identity(
        base,
        dependencies=dependencies,
        manifest_sha256="b" * 64,
        source_hashes=source_hashes,
    )
    assert dependency_id != base_id
    assert dataset_id != base_id
    assert base_config["dependency_versions_sha256"] != ""
    assert base_config["dataset_and_split_manifest_sha256"] == manifest_hash


def test_dirty_git_provenance_includes_untracked_source_hash(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "tracked.py").write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True)
    (repo / "untracked.py").write_text("new evaluator\n", encoding="utf-8")

    provenance = canonical.git_provenance(repo, ["tracked.py", "untracked.py"])
    assert provenance["working_tree_dirty"] is True
    assert any("untracked.py" in line for line in provenance["status_porcelain"])
    assert provenance["relevant_source_files"]["untracked.py"]["git_tracked"] is False
    assert len(provenance["relevant_source_files"]["untracked.py"]["content_sha256"]) == 64


def _valid_output_fixture() -> tuple[dict, list[dict], list[dict]]:
    metric = {
        "mean": 0.8,
        "calibration_split_std": 0.1,
        "bootstrap_95ci_of_split_mean_lower": 0.75,
        "bootstrap_95ci_of_split_mean_upper": 0.85,
        "bootstrap_unit": "predefined_calibration_splits",
    }
    split_metric = {
        "calibration_split_id": "split-000",
        "n_calibration_normal": 2,
        "n_held_out_normal": 4,
        "n_target_anomaly": 3,
        "auc": 0.8,
        "standardized_pauc_at_fpr_0_1": 0.7,
    }
    method_data = {
        "auc": metric,
        "standardized_pauc_at_fpr_0_1": {
            **metric,
            "mean": 0.7,
            "bootstrap_95ci_of_split_mean_lower": 0.65,
            "bootstrap_95ci_of_split_mean_upper": 0.75,
        },
        "per_calibration_split": [split_metric],
    }
    result = {
        "run_id": "test-run",
        "protocol_version": canonical.PROTOCOL_VERSION,
        "run_config": {"run_config_sha256": "x", "machines": ["fan"]},
        "configuration": {
            "k": 2,
            "n_splits": 1,
            "bootstrap_resamples": 100,
            "bootstrap_random_state": 77,
        },
        "git_provenance": {"head_commit": "abc", "working_tree_dirty": True},
        "dependency_versions": {"python": "test"},
        "split_manifest_sha256": "manifest",
        "method_specs": [canonical.asdict(spec) for spec in canonical.METHOD_SPECS],
        "machines": {
            "fan": {"methods": {method: copy.deepcopy(method_data) for method in canonical.METHOD_ORDER}}
        },
    }
    aggregate = []
    raw = []
    for method in canonical.METHOD_ORDER:
        aggregate.append(
            {
                "run_id": "test-run",
                "protocol_version": canonical.PROTOCOL_VERSION,
                "git_head_commit": "abc",
                "working_tree_dirty": True,
                "machine": "fan",
                "method": method,
                "training_seed": "not_applicable",
                "k": 2,
                "calibration_split_count": 1,
                "split_manifest_sha256": "manifest",
                "auc_mean": 0.8,
                "auc_calibration_split_std": 0.1,
                "auc_bootstrap_95ci_of_split_mean_lower": 0.75,
                "auc_bootstrap_95ci_of_split_mean_upper": 0.85,
                "standardized_pauc_at_fpr_0_1_mean": 0.7,
                "pauc_calibration_split_std": 0.1,
                "pauc_bootstrap_95ci_of_split_mean_lower": 0.65,
                "pauc_bootstrap_95ci_of_split_mean_upper": 0.75,
                "bootstrap_resamples": 100,
                "bootstrap_random_state": 77,
            }
        )
        raw.append(
            {
                "run_id": "test-run",
                "protocol_version": canonical.PROTOCOL_VERSION,
                "git_head_commit": "abc",
                "working_tree_dirty": True,
                "machine": "fan",
                "method": method,
                "training_seed": "not_applicable",
                "calibration_split_id": "split-000",
                "split_manifest_sha256": "manifest",
                "n_calibration_normal": 2,
                "n_held_out_normal": 4,
                "n_target_anomaly": 3,
                "auc": 0.8,
                "standardized_pauc_at_fpr_0_1": 0.7,
            }
        )
    return result, aggregate, raw


def test_output_schema_and_summary_writer(tmp_path: Path) -> None:
    result, aggregate, raw = _valid_output_fixture()
    canonical.validate_output_schema(result, aggregate, raw)
    summary = canonical.render_summary_markdown(result)
    assert "not an independent final validation" in summary
    assert "mel1280" in summary and "psd_shape" in summary
    assert "standardized pAUC@FPR<=0.1" in summary
    assert "Bootstrap 95% CI" in summary
    assert "`100` resamples" in summary and "`77`" in summary
    assert "[0.7500, 0.8500]" in summary

    canonical._write_json(tmp_path / "result.json", result)
    canonical._write_flat_csv(tmp_path / "aggregate.csv", aggregate)
    assert json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))["run_id"] == "test-run"
    assert (tmp_path / "aggregate.csv").read_text(encoding="utf-8").startswith("run_id")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda _r, aggregate, _raw: aggregate[0].pop("auc_mean"), "nema CSV kolone"),
        (
            lambda _r, aggregate, _raw: aggregate[0].update(auc_mean=float("nan")),
            "konacan broj",
        ),
        (
            lambda _r, aggregate, _raw: aggregate.__setitem__(1, copy.deepcopy(aggregate[0])),
            "duple machine/method",
        ),
        (
            lambda _r, _aggregate, raw: raw[0].update(calibration_split_id="split-999"),
            "ocekivani machine/method/split_id skup",
        ),
    ],
)
def test_output_schema_rejects_malformed_csv_rows(mutation, message: str) -> None:
    result, aggregate, raw = _valid_output_fixture()
    mutation(result, aggregate, raw)
    with pytest.raises(RuntimeError, match=message):
        canonical.validate_output_schema(result, aggregate, raw)


def test_summary_regeneration_uses_aggregate_json_without_changing_it(
    tmp_path: Path,
) -> None:
    result, _aggregate, _raw = _valid_output_fixture()
    aggregate_json = tmp_path / "aggregate_results.json"
    canonical._write_json(aggregate_json, result)
    before = canonical._sha256_file(aggregate_json)
    summary_path = canonical.regenerate_summary_from_aggregate_json(aggregate_json)
    assert canonical._sha256_file(aggregate_json) == before
    assert summary_path == tmp_path / "SUMMARY.md"
    summary = summary_path.read_text(encoding="utf-8")
    assert "standardized pAUC@FPR<=0.1" in summary
    assert "[0.6500, 0.7500]" in summary
    assert not list(tmp_path.glob(".SUMMARY.md.tmp-*"))
