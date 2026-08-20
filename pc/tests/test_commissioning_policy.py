from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

PC_DIR = Path(__file__).resolve().parents[1]
if str(PC_DIR) not in sys.path:
    sys.path.insert(0, str(PC_DIR))

from asd.commissioning_policy import (
    COMMISSIONING_POLICY_RECORD,
    MAX_LOO_CV,
    calibration_acceptance,
)


def _state(value):
    return {"cal_summary": {"loo_cv": value}}


def test_k1_boundary_comes_from_versioned_policy() -> None:
    assert COMMISSIONING_POLICY_RECORD["schema_version"] == (
        "asd-commissioning-policy-v1.0.0"
    )
    assert COMMISSIONING_POLICY_RECORD["numeric_status"] == (
        "temporary_preregistered_gate"
    )
    assert MAX_LOO_CV == 0.6
    assert calibration_acceptance(_state(0.6)) == (True, "accepted")
    assert calibration_acceptance(_state(0.600001)) == (
        False, "loo_cv_above_max",
    )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_k1_nonfinite_fails_closed(value: float) -> None:
    assert calibration_acceptance(_state(value)) == (False, "nonfinite_loo_cv")


def test_k1_negative_cv_fails_closed() -> None:
    assert calibration_acceptance(_state(-0.1)) == (False, "negative_loo_cv")


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        (None, "missing_protocol_state"),
        ({}, "missing_cal_summary"),
        ({"cal_summary": None}, "missing_cal_summary"),
        ({"cal_summary": {}}, "missing_loo_cv"),
        ({"cal_summary": {"loo_cv": "bad"}}, "invalid_loo_cv"),
    ],
)
def test_k1_missing_or_malformed_fails_closed(state, reason: str) -> None:
    assert calibration_acceptance(state) == (False, reason)
