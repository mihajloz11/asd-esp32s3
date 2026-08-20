"""Normal-only commissioning acceptance policy shared by PC tools.

The numeric K1 limit is versioned in ``pc/config``.  This module deliberately
does not decide whether UART telemetry is valid: it only decides whether an
otherwise parsed calibration is acceptable for physical-result metrics.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any


CONFIG_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "asd_commissioning_policy_v1.json"
)
COMMISSIONING_POLICY_RECORD = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
COMMISSIONING_POLICY = COMMISSIONING_POLICY_RECORD["calibration"]
MAX_LOO_CV = float(COMMISSIONING_POLICY["max_loo_cv"])


def calibration_acceptance(
    protocol_state: Mapping[str, Any] | None,
) -> tuple[bool, str]:
    """Return the preregistered K1 calibration decision and stable reason.

    Equality passes because the locked rule rejects only ``loo_cv > max``.
    Missing, malformed and non-finite values fail closed without changing the
    independent firmware-protocol validity.
    """
    if protocol_state is None:
        return False, "missing_protocol_state"
    cal_summary = protocol_state.get("cal_summary")
    if not isinstance(cal_summary, Mapping):
        return False, "missing_cal_summary"
    if "loo_cv" not in cal_summary:
        return False, "missing_loo_cv"
    try:
        loo_cv = float(cal_summary["loo_cv"])
    except (TypeError, ValueError, OverflowError):
        return False, "invalid_loo_cv"
    if not math.isfinite(loo_cv):
        return False, "nonfinite_loo_cv"
    if loo_cv < 0.0:
        return False, "negative_loo_cv"
    if loo_cv > MAX_LOO_CV:
        return False, "loo_cv_above_max"
    return True, "accepted"
