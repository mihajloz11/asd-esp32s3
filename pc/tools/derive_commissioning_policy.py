"""Normal-only chronological commissioning policy derivation (developmental).

This tool deliberately has no target-anomaly input.  It consumes candidate
score rows produced from normal data, keeps CENTER/DERIVE/VERIFY chronological,
fits and selects on DERIVE only, freezes the selected policy, and only then
reports the untouched VERIFY block.

Input JSON schema (``fan-normal-candidate-scores-v1.0.0``)::

    {
      "developmental": true,
      "target_anomalies_used_for_fit": false,
      "feature_manifest_id": "...",
      "feature_candidate_ids": ["baseline_hard_log96"],
      "model_id": "normal-only-model-id",
      "windows": [{
        "window_id": "w0001", "fan_id": "fan-a", "session_id": "s1",
        "phase": "CENTER_LEARNING", "start_s": 0, "end_s": 10,
        "normal_only": true,
        "candidate_scores": {"baseline_hard_log96": 1.2},
        "tonalness_proxy": 4.0, "subsegment_instability": 0.1
      }]
    }

Nothing written by this module is a deployment default.  Physical validation
and a later independent normal run are still required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_VERSION = "commissioning-development-v1.0.0"
INPUT_SCHEMA_VERSION = "fan-normal-candidate-scores-v1.0.0"
OUTPUT_SCHEMA_VERSION = "asd-commissioning-development-result-v1.0.0"
DEVELOPMENTAL = True
PHASE_ORDER = (
    "CENTER_LEARNING",
    "COMMISSION_DERIVE",
    "COMMISSION_VERIFY",
)


@dataclass(frozen=True)
class ThresholdSpec:
    threshold_id: str
    enter_method: str
    enter_parameter: float
    exit_method: str
    exit_parameter: float
    block_windows: int = 6
    min_derive_windows: int = 1


THRESHOLD_SPECS: tuple[ThresholdSpec, ...] = (
    # Aktivno firmware pravilo od 26.08.2026: p99 je samo gornja granica, a
    # ulazni prag je min(p99, median + 3 * 1.4826 * MAD). Firmware prije toga
    # ponovo racuna centar kao koordinatni 10% trimmed mean nad sirovim DERIVE
    # featureima. Ovaj score-only laboratorijski alat moze reprodukovati prag,
    # ali ne i ponovno centriranje bez izvornih featurea.
    #
    # Izlaz je p95, uz ogranicenja `max(p50)` odozdo i `0,5 * enter` odozgo
    # koja zive u `psd_live.c` jer ih ovaj laboratorijski opis ne izrazava.
    #
    # Razlog je izmjeren, ne pretpostavljen: run 23.08.2026 je imao enter 6341 i
    # exit 341, a najtisi ispravan DET prozor 463 -- alarm iz prvog papirica se
    # nikad nije ugasio i sljedeca dva bloka nisu imala u sta da udju. p75 znaci
    # da cetvrtina ispravnih prozora stoji IZNAD izlaza. Izvedeno iskljucivo iz
    # normal-only DERIVE raspodjele; nijedna ciljna anomalija nije otvorena.
    # Aktivno firmware pravilo: posljednji stvarni normal-only VERIFY pokazao
    # je da Hampel 3-sigma granica pravi niz laznih alarma, dok frozen CAL
    # centar + empirical p99 prolazi isti VERIFY.
    ThresholdSpec(
        "empirical-p99_exit-p95-clamped", "percentile", 0.99,
        "percentile", 0.95,
    ),
    # Odbaceni robustni kandidat ostaje samo radi reprodukcije regresije.
    ThresholdSpec(
        "hampel3-capped-p99_exit-p95-clamped", "hampel_capped_percentile", 3.0,
        "percentile", 0.95,
    ),
    ThresholdSpec(
        "empirical-p99_exit-p75", "percentile", 0.99,
        "percentile", 0.75,
    ),
    ThresholdSpec(
        "median-plus-6mad_exit-2mad", "median_mad", 6.0,
        "median_mad", 2.0,
    ),
    ThresholdSpec(
        "blockmax6-p90_exit-p75", "block_max_percentile", 0.90,
        "percentile", 0.75, block_windows=6, min_derive_windows=18,
    ),
    ThresholdSpec(
        "conformal-a05_exit-p75", "conformal", 0.05,
        "percentile", 0.75, min_derive_windows=20,
    ),
)


class PhaseAudit:
    """Fail fast if target anomalies appear before or during normal-only fit."""

    def __init__(self) -> None:
        self.phase = "prepare_and_fit"
        self.target_anomaly_reads = 0
        self.policy_frozen = False

    def record_rows(self, rows: Sequence[Mapping[str, Any]]) -> None:
        anomaly_rows = [
            row for row in rows
            if bool(row.get("target_anomaly", False))
            or int(row.get("label", 0)) != 0
            or not bool(row.get("normal_only", False))
        ]
        if anomaly_rows:
            self.target_anomaly_reads += len(anomaly_rows)
            raise RuntimeError(
                "commissioning fit smije citati samo normal_only redove; "
                "target anomalije su evaluate-only"
            )

    def freeze(self) -> None:
        if self.phase != "prepare_and_fit" or self.target_anomaly_reads:
            raise RuntimeError("policy se ne moze zamrznuti poslije anomaly read-a")
        self.policy_frozen = True
        self.phase = "verify_frozen"


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_candidate_manifest(
    feature_manifest_id: str, feature_candidate_ids: Sequence[str],
) -> dict[str, Any]:
    """Return the complete preregistered candidate list before evaluation."""
    declared_features = tuple(sorted(str(value) for value in feature_candidate_ids))
    if not feature_manifest_id or not declared_features:
        raise ValueError("feature manifest ID i candidate lista su obavezni")
    if len(set(declared_features)) != len(declared_features):
        raise ValueError("feature candidate lista sadrzi duplikate")
    content: dict[str, Any] = {
        "schema_version": "commissioning-candidate-manifest-v1.0.0",
        "protocol_version": PROTOCOL_VERSION,
        "developmental": True,
        "numeric_status": "development_pending_physical_validation",
        "feature_manifest_id": feature_manifest_id,
        "feature_candidate_ids": list(declared_features),
        "policy_candidate_ids": [
            f"{feature_id}__{spec.threshold_id}"
            for feature_id in declared_features for spec in THRESHOLD_SPECS
        ],
        "phase_order": list(PHASE_ORDER),
        "selection_uses_phase": "COMMISSION_DERIVE",
        "verification_uses_phase": "COMMISSION_VERIFY",
        "randomization": "forbidden",
        "threshold_candidates": [asdict(spec) for spec in THRESHOLD_SPECS],
        "selection_objective_lexicographic": [
            "alarm_episodes", "alarm_time_s", "chatter_reentries",
            "longest_above_enter_windows", "block_episode_range",
            "block_alarm_time_std_s", "candidate_id",
        ],
        "constraints": ["T_exit > 0", "T_exit < T_enter"],
        "tonalness": {
            "meaning": "peak_prominence_not_speech_classifier",
            "reference": "median_CENTER_LEARNING_normal",
            "derived_field": "tonalness_delta",
        },
        "subsegment_stability": {
            "role": "gate_not_main_detector",
            "derive_method": "COMMISSION_DERIVE empirical p99",
        },
        "bootstrap_unit": "session_or_fan_not_overlapping_window",
        "target_anomalies_used_for_fit": False,
    }
    return {**content, "manifest_id": sha256_json(content)}


def _finite_number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} nije broj") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} mora biti konacan")
    return number


def validate_score_bundle(bundle: Mapping[str, Any], audit: PhaseAudit) -> list[dict[str, Any]]:
    if bundle.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise ValueError(f"ocekivan input schema {INPUT_SCHEMA_VERSION}")
    if bundle.get("developmental") is not True:
        raise ValueError("input mora eksplicitno imati developmental=true")
    if bundle.get("target_anomalies_used_for_fit") is not False:
        raise ValueError("target_anomalies_used_for_fit mora biti false")
    declared_raw = bundle.get("feature_candidate_ids")
    if not isinstance(declared_raw, list) or not declared_raw:
        raise ValueError("feature_candidate_ids mora biti neprazna lista")
    declared_features = tuple(sorted(str(value) for value in declared_raw))
    if len(set(declared_features)) != len(declared_features):
        raise ValueError("feature_candidate_ids sadrzi duplikate")
    rows_raw = bundle.get("windows")
    if not isinstance(rows_raw, list) or not rows_raw:
        raise ValueError("windows mora biti neprazna lista")
    rows = [dict(row) for row in rows_raw]
    audit.record_rows(rows)

    seen_ids: set[str] = set()
    previous_end = -math.inf
    previous_phase_index = 0
    feature_names: tuple[str, ...] | None = None
    observed_phases: list[str] = []
    for position, row in enumerate(rows):
        window_id = str(row.get("window_id", ""))
        if not window_id or window_id in seen_ids:
            raise ValueError(f"window_id prazan ili dupliran: {window_id!r}")
        seen_ids.add(window_id)
        phase = str(row.get("phase", ""))
        if phase not in PHASE_ORDER:
            raise ValueError(f"nepoznata faza {phase!r}")
        phase_index = PHASE_ORDER.index(phase)
        if position and phase_index < previous_phase_index:
            raise ValueError("commissioning faze nisu hronoloske")
        previous_phase_index = phase_index
        if not observed_phases or observed_phases[-1] != phase:
            observed_phases.append(phase)

        start = _finite_number(row.get("start_s"), f"{window_id}.start_s")
        end = _finite_number(row.get("end_s"), f"{window_id}.end_s")
        if start < previous_end or end <= start:
            raise ValueError("prozori se preklapaju ili nisu strogo hronoloski")
        previous_end = end
        row["start_s"] = start
        row["end_s"] = end
        scores = row.get("candidate_scores")
        if not isinstance(scores, dict) or not scores:
            raise ValueError(f"{window_id}: candidate_scores mora biti objekat")
        names = tuple(sorted(str(name) for name in scores))
        if feature_names is None:
            feature_names = names
        elif names != feature_names:
            raise ValueError("svi prozori moraju imati isti candidate score manifest")
        row["candidate_scores"] = {
            name: _finite_number(scores[name], f"{window_id}.{name}")
            for name in names
        }
        if any(value < 0.0 for value in row["candidate_scores"].values()):
            raise ValueError("candidate score ne smije biti negativan")
        row["tonalness_proxy"] = _finite_number(
            row.get("tonalness_proxy", 0.0), f"{window_id}.tonalness_proxy",
        )
        row["subsegment_instability"] = _finite_number(
            row.get("subsegment_instability", 0.0),
            f"{window_id}.subsegment_instability",
        )
        if row["subsegment_instability"] < 0.0:
            raise ValueError("subsegment_instability ne smije biti negativan")
    if tuple(observed_phases) != PHASE_ORDER:
        raise ValueError(
            "potrebni su nepomijesani CENTER_LEARNING, COMMISSION_DERIVE i "
            "COMMISSION_VERIFY blokovi"
        )
    if feature_names != declared_features:
        raise ValueError("candidate score polja se ne podudaraju sa manifest listom")
    return rows


def _percentile_higher(values: np.ndarray, quantile: float) -> float:
    if not 0.0 < quantile < 1.0:
        raise ValueError("quantile mora biti u (0,1)")
    return float(np.quantile(values, quantile, method="higher"))


def _median_scaled_mad(values: np.ndarray) -> tuple[float, float]:
    median = float(np.median(values))
    scaled_mad = 1.4826 * float(np.median(np.abs(values - median)))
    return median, scaled_mad


def _conformal_upper(values: np.ndarray, alpha: float) -> float | None:
    """Finite-sample normal-only upper order statistic, or unavailable."""
    n = len(values)
    rank = int(math.ceil((n + 1) * (1.0 - alpha)))
    if rank > n:
        return None
    return float(np.sort(values)[rank - 1])


def derive_threshold_pair(values: Sequence[float], spec: ThresholdSpec) -> tuple[float, float] | None:
    scores = np.asarray(values, dtype=np.float64)
    if len(scores) < spec.min_derive_windows or not np.isfinite(scores).all():
        return None
    median, scaled_mad = _median_scaled_mad(scores)
    if spec.enter_method == "percentile":
        enter = _percentile_higher(scores, spec.enter_parameter)
    elif spec.enter_method == "hampel_capped_percentile":
        enter = min(
            _percentile_higher(scores, 0.99),
            median + spec.enter_parameter * scaled_mad,
        )
    elif spec.enter_method == "median_mad":
        enter = median + spec.enter_parameter * scaled_mad
    elif spec.enter_method == "block_max_percentile":
        maxima = np.asarray([
            np.max(scores[index:index + spec.block_windows])
            for index in range(0, len(scores), spec.block_windows)
            if len(scores[index:index + spec.block_windows]) == spec.block_windows
        ])
        if len(maxima) < 3:
            return None
        enter = _percentile_higher(maxima, spec.enter_parameter)
    elif spec.enter_method == "conformal":
        conformal = _conformal_upper(scores, spec.enter_parameter)
        if conformal is None:
            return None
        enter = conformal
    else:  # pragma: no cover - manifest is locked above
        raise ValueError(spec.enter_method)

    if spec.exit_method == "percentile":
        exit_threshold = _percentile_higher(scores, spec.exit_parameter)
    elif spec.exit_method == "median_mad":
        exit_threshold = median + spec.exit_parameter * scaled_mad
    else:  # pragma: no cover
        raise ValueError(spec.exit_method)
    enter = float(enter)
    exit_threshold = float(exit_threshold)
    if not (math.isfinite(enter) and math.isfinite(exit_threshold)):
        return None
    if not (0.0 < exit_threshold < enter):
        return None
    return enter, exit_threshold


def temporal_normal_metrics(
    rows: Sequence[Mapping[str, Any]], *, feature_name: str,
    enter_threshold: float, exit_threshold: float, block_windows: int,
) -> dict[str, Any]:
    """Episode metrics on the complete chronological normal time series."""
    active = False
    episodes = 0
    chatter = 0
    last_exit_index: int | None = None
    alarm_windows = 0
    alarm_time_s = 0.0
    total_time_s = 0.0
    longest_above = 0
    above_run = 0
    episode_by_block: dict[int, int] = {}
    alarm_time_by_block: dict[int, float] = {}
    for index, row in enumerate(rows):
        score = float(row["candidate_scores"][feature_name])
        duration = float(row["end_s"]) - float(row["start_s"])
        total_time_s += duration
        block = index // block_windows
        if score >= enter_threshold:
            above_run += 1
            longest_above = max(longest_above, above_run)
        else:
            above_run = 0
        if not active and score >= enter_threshold:
            active = True
            episodes += 1
            episode_by_block[block] = episode_by_block.get(block, 0) + 1
            if last_exit_index is not None and index - last_exit_index <= block_windows:
                chatter += 1
        elif active and score <= exit_threshold:
            active = False
            last_exit_index = index
        if active:
            alarm_windows += 1
            alarm_time_s += duration
            alarm_time_by_block[block] = alarm_time_by_block.get(block, 0.0) + duration
    blocks = max(1, math.ceil(len(rows) / block_windows))
    episode_counts = [episode_by_block.get(index, 0) for index in range(blocks)]
    block_alarm_times = [alarm_time_by_block.get(index, 0.0) for index in range(blocks)]
    return {
        "window_count": len(rows),
        "alarm_window_count": alarm_windows,
        "alarm_episodes": episodes,
        "alarm_time_s": alarm_time_s,
        "alarm_time_percent": (
            100.0 * alarm_time_s / total_time_s if total_time_s > 0.0 else 0.0
        ),
        "alarm_window_percent": (
            100.0 * alarm_windows / len(rows) if rows else 0.0
        ),
        "chatter_reentries": chatter,
        "longest_above_enter_windows": longest_above,
        "block_episode_range": max(episode_counts) - min(episode_counts),
        "block_alarm_time_std_s": (
            statistics.pstdev(block_alarm_times) if len(block_alarm_times) > 1 else 0.0
        ),
        "ended_in_alarm": active,
    }


def _selection_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    metrics = candidate["derive_metrics"]
    return (
        metrics["alarm_episodes"],
        metrics["alarm_time_s"],
        metrics["chatter_reentries"],
        metrics["longest_above_enter_windows"],
        metrics["block_episode_range"],
        metrics["block_alarm_time_std_s"],
        candidate["candidate_id"],
    )


def derive_commissioning_policy(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Fit/select on DERIVE, freeze, then report untouched VERIFY."""
    audit = PhaseAudit()
    rows = validate_score_bundle(bundle, audit)
    feature_manifest_id = str(bundle.get("feature_manifest_id", ""))
    if not feature_manifest_id:
        raise ValueError("feature_manifest_id je obavezan")
    model_id = str(bundle.get("model_id", ""))
    if not model_id:
        raise ValueError("normal-only model_id je obavezan")
    manifest = build_candidate_manifest(
        feature_manifest_id, bundle["feature_candidate_ids"],
    )
    center = [row for row in rows if row["phase"] == "CENTER_LEARNING"]
    derive = [row for row in rows if row["phase"] == "COMMISSION_DERIVE"]
    verify = [row for row in rows if row["phase"] == "COMMISSION_VERIFY"]
    if not center or not derive or not verify:
        raise ValueError("sve tri commissioning faze moraju biti neprazne")
    center_ids = {row["window_id"] for row in center}
    derive_ids = {row["window_id"] for row in derive}
    verify_ids = {row["window_id"] for row in verify}
    if center_ids & derive_ids or center_ids & verify_ids or derive_ids & verify_ids:
        raise ValueError("CENTER/DERIVE/VERIFY indeksi se preklapaju")

    feature_names = sorted(derive[0]["candidate_scores"])
    candidates: list[dict[str, Any]] = []
    for feature_name in feature_names:
        values = [float(row["candidate_scores"][feature_name]) for row in derive]
        for spec in THRESHOLD_SPECS:
            pair = derive_threshold_pair(values, spec)
            if pair is None:
                continue
            enter, exit_threshold = pair
            candidate_id = f"{feature_name}__{spec.threshold_id}"
            candidates.append({
                "candidate_id": candidate_id,
                "feature_candidate_id": feature_name,
                "threshold_candidate_id": spec.threshold_id,
                "T_enter": enter,
                "T_exit": exit_threshold,
                "derive_metrics": temporal_normal_metrics(
                    derive, feature_name=feature_name,
                    enter_threshold=enter, exit_threshold=exit_threshold,
                    block_windows=spec.block_windows,
                ),
            })
    if not candidates:
        raise RuntimeError("nijedan kandidat nije dao 0 < T_exit < T_enter")
    selected = min(candidates, key=_selection_key)
    audit.freeze()
    verify_metrics = temporal_normal_metrics(
        verify, feature_name=str(selected["feature_candidate_id"]),
        enter_threshold=float(selected["T_enter"]),
        exit_threshold=float(selected["T_exit"]), block_windows=6,
    )
    tonal_reference = float(np.median([
        float(row["tonalness_proxy"]) for row in center
    ]))
    instability_gate = _percentile_higher(np.asarray([
        float(row["subsegment_instability"]) for row in derive
    ]), 0.99)
    selected_policy = {
        **selected,
        "policy_status": "frozen_developmental",
        "tonalness_normal_reference": tonal_reference,
        "subsegment_instability_gate": instability_gate,
        "subsegment_gate_role": "hold_only_not_main_detector",
        "manifest_id": manifest["manifest_id"],
        "model_id": model_id,
    }
    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "developmental": True,
        "numeric_status": "development_pending_physical_validation",
        "target_anomalies_used_for_fit": False,
        "target_anomaly_reads_before_freeze": audit.target_anomaly_reads,
        "model_id": model_id,
        "input_manifest_sha256": sha256_json(bundle),
        "candidate_manifest": manifest,
        "phase_counts": {
            "CENTER_LEARNING": len(center),
            "COMMISSION_DERIVE": len(derive),
            "COMMISSION_VERIFY": len(verify),
        },
        "phase_window_ids": {
            "CENTER_LEARNING": sorted(center_ids),
            "COMMISSION_DERIVE": sorted(derive_ids),
            "COMMISSION_VERIFY": sorted(verify_ids),
        },
        "selection_phase": "COMMISSION_DERIVE",
        "verify_used_for_selection": False,
        "selected_policy": selected_policy,
        "candidate_results": sorted(candidates, key=lambda item: item["candidate_id"]),
        "verify_metrics_frozen_policy": verify_metrics,
        "verify_tonalness_delta": [
            float(row["tonalness_proxy"]) - tonal_reference for row in verify
        ],
        "bootstrap": {
            "performed": False,
            "required_unit_for_future_runs": "session_or_fan",
            "window_bootstrap_forbidden": True,
        },
    }


def git_provenance() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout.strip()
    try:
        status = run("status", "--porcelain=v1")
        return {
            "head_commit": run("rev-parse", "HEAD"),
            "working_tree_dirty": bool(status),
            "status_porcelain_sha256": hashlib.sha256(status.encode()).hexdigest(),
        }
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"unavailable": True, "reason": f"{type(exc).__name__}: {exc}"}


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_bytes(canonical_json(value) + b"\n")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def run_cli(args: argparse.Namespace) -> int:
    input_path = args.input.resolve()
    bundle = json.loads(input_path.read_text(encoding="utf-8"))
    out_dir = args.output_dir.resolve()
    # Manifest is constructed before any candidate is evaluated.
    feature_manifest_id = str(bundle.get("feature_manifest_id", ""))
    manifest = build_candidate_manifest(
        feature_manifest_id, bundle.get("feature_candidate_ids", []),
    )
    write_json_atomic(out_dir / "candidate_manifest.json", manifest)
    result = derive_commissioning_policy(bundle)
    if result["candidate_manifest"]["manifest_id"] != manifest["manifest_id"]:
        raise RuntimeError("manifest se promijenio tokom evaluacije")
    write_json_atomic(out_dir / "frozen_commissioning_policy.json", result)
    write_json_atomic(out_dir / "provenance.json", {
        "schema_version": "commissioning-development-provenance-v1.0.0",
        "developmental": True,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_file": str(input_path),
        "input_sha256": sha256_file(input_path),
        "candidate_manifest_id": manifest["manifest_id"],
        "source_sha256": {
            "pc/tools/derive_commissioning_policy.py": sha256_file(Path(__file__)),
        },
        "git": git_provenance(),
        "target_anomalies_used_for_fit": False,
    })
    print(out_dir / "frozen_commissioning_policy.json")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path,
        default=ROOT / "results" / "commissioning_development",
    )
    parser.set_defaults(func=run_cli)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
