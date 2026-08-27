r"""Faza 8 — provjera da firmware, parser i zaključane politike govore isto.

Ovo je jeftina provjera koja hvata tačno jednu klasu greške: da se verzija
protokola ili neki prag promijeni na jednom mjestu, a ne na drugom. Takva
greška ne obori nijedan test odmah, ali obori fizički prolaz tek kad se
ventilator već vrti — dakle najskuplje moguće.

Ne traži ni pločicu ni DCASE audio, pa može u CI.

    .venv\Scripts\python.exe pc\tools\check_schema_consistency.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "firmware" / "esp32s3_asd" / "main"
CONFIG = ROOT / "pc" / "config"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def define(source: str, name: str) -> str | None:
    match = re.search(rf"#define\s+{re.escape(name)}\s+([^\s/]+)", source)
    return match.group(1) if match else None


def main() -> int:
    problems: list[str] = []

    quality_header = read(MAIN / "audio_quality_state.h")
    events_source = read(MAIN / "asd_events.c")
    temporal_source = read(MAIN / "asd_temporal.c")
    temporal_header = read(MAIN / "asd_temporal.h")
    parser = read(ROOT / "pc" / "tools" / "physical_fan_experiment.py")

    # --- verzija serijskog protokola ---
    firmware_protocol = re.search(
        r'#define\s+ASD_QUALITY_PROTOCOL\s+"([^"]+)"', quality_header)
    parser_protocol = re.search(
        r'QUALITY_PROTOCOL_VERSION\s*=\s*"([^"]+)"', parser)
    if not firmware_protocol or not parser_protocol:
        problems.append("ne mogu procitati verziju protokola sa obje strane")
    elif firmware_protocol.group(1) != parser_protocol.group(1):
        problems.append(
            f"protokol se ne poklapa: firmware {firmware_protocol.group(1)}, "
            f"parser {parser_protocol.group(1)}")

    # --- politika prisustva (Faza 2) ---
    presence = json.loads(read(CONFIG / "asd_presence_policy_v1.json"))
    margin = define(events_source, "DEFAULT_ABSENT_MARGIN_DB")
    consecutive = define(events_source, "DEFAULT_MIN_CONSECUTIVE")
    if margin is None or float(margin.rstrip("f")) != presence["policy"]["absent_margin_db"]:
        problems.append(
            f"margina prisustva: firmware {margin}, "
            f"config {presence['policy']['absent_margin_db']}")
    if consecutive is None or int(consecutive) != presence["policy"]["min_consecutive_windows"]:
        problems.append(
            f"min_consecutive prisustva: firmware {consecutive}, "
            f"config {presence['policy']['min_consecutive_windows']}")
    if presence.get("target_anomalies_used") is not False:
        problems.append("politika prisustva tvrdi da je koristila target anomalije")

    # --- politika vremenske odluke (Faza 4) ---
    temporal = json.loads(read(CONFIG / "asd_temporal_policy_v2.json"))
    chosen = temporal["policy"]
    legacy_wire = temporal["legacy_wire_provenance"]
    schema_in_header = re.search(
        r'#define\s+ASD_TEMPORAL_POLICY\s+"([^"]+)"', temporal_header)
    if not schema_in_header or schema_in_header.group(1) != temporal["schema_version"]:
        problems.append(
            f"schema vremenske politike: firmware "
            f"{schema_in_header.group(1) if schema_in_header else None}, "
            f"config {temporal['schema_version']}")
    for macro, key, expected in (
        ("DEFAULT_MIN_CONSECUTIVE", "min_consecutive", chosen["min_consecutive"]),
        ("DEFAULT_EWMA_ALPHA", "ewma_alpha", chosen["ewma_alpha"]),
        ("DEFAULT_ENTER_SCALE", "legacy_enter_scale", legacy_wire["enter_scale"]),
        ("DEFAULT_EXIT_SCALE", "legacy_exit_scale", legacy_wire["exit_scale"]),
        ("DEFAULT_FAST_SCALE", "fast_scale", chosen["fast_scale"]),
    ):
        raw = define(temporal_source, macro)
        if raw is None:
            problems.append(f"nema {macro} u asd_temporal.c")
            continue
        if abs(float(raw.rstrip("f")) - float(expected)) > 1e-6:
            problems.append(f"{key}: firmware {raw}, config {expected}")
    if temporal.get("target_anomalies_used_for_fit") is not False:
        problems.append("vremenska politika tvrdi da je koristila target anomalije")

    # --- politika kvaliteta (Faza 1) ---
    quality = json.loads(read(CONFIG / "asd_quality_policy_v1.json"))
    if quality.get("target_anomalies_used") is not False:
        problems.append("politika kvaliteta tvrdi da je koristila target anomalije")
    quality_source = read(MAIN / "audio_quality_state.c")
    level_floor = define(quality_source, "DEFAULT_LEVEL_FLOOR_DBFS")
    if level_floor is None or abs(
        float(level_floor.strip("()f")) - float(quality["policy"]["level_floor_dbfs"])
    ) > 1e-6:
        problems.append(
            f"audio liveness floor: firmware {level_floor}, "
            f"config {quality['policy']['level_floor_dbfs']}"
        )

    # --- commissioning prag: ista normal-only politika na svim stranama ---
    live = read(MAIN / "psd_live.c")
    runtime = json.loads(read(CONFIG / "asd_commissioning_runtime_v1.json"))
    fit = runtime["normal_only_threshold_fit"]
    for macro, key in (
        ("COMMISSION_ENTER_QUANTILE", "enter_percentile"),
        ("COMMISSION_EXIT_QUANTILE", "exit_percentile"),
    ):
        raw = define(live, macro)
        if raw is None or abs(float(raw.rstrip("f")) - float(fit[key])) > 1e-6:
            problems.append(f"{key}: firmware {raw}, config {fit[key]}")
    if fit.get("source_phase") != "COMMISSION_DERIVE":
        problems.append("prag nije izveden iz COMMISSION_DERIVE")
    if fit.get("center_method") != "frozen_cal_center":
        problems.append("centar nije zamrznuti CAL centar")
    if fit.get("enter_method") != "empirical_percentile_higher":
        problems.append("ulazni prag nije empirical percentile-higher p99")
    if fit.get("target_anomalies_used_for_fit") is not False:
        problems.append("commissioning prag tvrdi da koristi target anomalije")
    if "asd_robust_fit_center(" in live or "asd_robust_fit_threshold(" in live:
        problems.append("psd_live.c neocekivano primjenjuje odbaceni robust fit")
    if (define(live, "COMMISSION_EXIT_MAX_FRACTION") != "0.5f" or
            define(live, "COMMISSION_EXIT_FLOOR_QUANTILE") != "0.50f"):
        problems.append("izlazni prag u psd_live.c nema ogranicenja p50/0.5*enter")
    physical = read(ROOT / "pc" / "tools" / "physical_fan_experiment.py")
    if "COMMISSION_ENTER_QUANTILE = 0.99" not in physical:
        problems.append("physical_fan_experiment.py nema aktivni p99 commissioning prag")
    laboratory = read(ROOT / "pc" / "tools" / "derive_commissioning_policy.py")
    if '"empirical-p99_exit-p95-clamped", "percentile", 0.99' not in laboratory:
        problems.append("PC commissioning manifest nema aktivni empirical-p99 kandidat")

    # --- kapija pouzdanosti: firmware i zamrznuta politika moraju se poklopiti ---
    interference = json.loads(read(CONFIG / "asd_interference_policy_v3.json"))
    if interference.get("target_anomalies_used_for_fit") is not False:
        problems.append("interference politika tvrdi da je koristila target anomalije")
    gate = read(MAIN / "asd_interference.c")
    header = read(MAIN / "asd_interference.h")
    if interference["schema_version"] not in header:
        problems.append("asd_interference.h ne nosi verziju zamrznute politike")
    numbers = interference["policy"]
    for key, expected in (
            ("enabled", "1"),
            ("use_tonalness_delta", "0"),
            ("calibration_min_windows", f"{int(numbers['calibration_min_windows'])}u"),
            ("long_hold_windows", f"{int(numbers['long_hold_windows'])}u")):
        if f".{key} = {expected}," not in gate:
            problems.append(f"interference {key}: firmware ne nosi {expected}")
    for key in ("max_abs_tonalness_delta", "normal_max_multiplier"):
        if f".{key} = {numbers[key]:.6f}f," not in gate:
            problems.append(
                f"interference {key}: firmware nije {numbers[key]:.6f}")
    if ".max_subsegment_instability = 0.0f," not in gate:
        problems.append("interference runtime prag nije fail-closed prije CAL-a")
    if "asd_interference_calibrate_normal" not in gate:
        problems.append("interference prag se ne izvodi iz sesijskog CAL-a")

    if problems:
        print("NESAGLASNOSTI:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("schema i politike saglasne:")
    print(f"  protokol            {firmware_protocol.group(1)}")
    print(f"  prisustvo           {presence['policy']['absent_margin_db']} dB / "
          f"{presence['policy']['min_consecutive_windows']} prozora")
    print(f"  vremenska odluka    absolute_profile "
          f"(n={chosen['min_consecutive']}, odvojeni enter/exit pragovi)")
    print("  sve politike        target_anomalies_used=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
