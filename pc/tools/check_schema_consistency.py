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
    temporal = json.loads(read(CONFIG / "asd_temporal_policy_v1.json"))
    chosen = temporal["policy"]
    schema_in_header = re.search(
        r'#define\s+ASD_TEMPORAL_POLICY\s+"([^"]+)"', temporal_header)
    if not schema_in_header or schema_in_header.group(1) != temporal["schema_version"]:
        problems.append(
            f"schema vremenske politike: firmware "
            f"{schema_in_header.group(1) if schema_in_header else None}, "
            f"config {temporal['schema_version']}")
    for macro, key in (
        ("DEFAULT_MIN_CONSECUTIVE", "min_consecutive"),
        ("DEFAULT_EWMA_ALPHA", "ewma_alpha"),
        ("DEFAULT_ENTER_SCALE", "enter_scale"),
        ("DEFAULT_EXIT_SCALE", "exit_scale"),
        ("DEFAULT_FAST_SCALE", "fast_scale"),
    ):
        raw = define(temporal_source, macro)
        if raw is None:
            problems.append(f"nema {macro} u asd_temporal.c")
            continue
        if abs(float(raw.rstrip("f")) - float(chosen[key])) > 1e-6:
            problems.append(f"{key}: firmware {raw}, config {chosen[key]}")
    if temporal.get("target_anomalies_used") is not False:
        problems.append("vremenska politika tvrdi da je koristila target anomalije")

    # --- politika kvaliteta (Faza 1) ---
    quality = json.loads(read(CONFIG / "asd_quality_policy_v1.json"))
    if quality.get("target_anomalies_used") is not False:
        problems.append("politika kvaliteta tvrdi da je koristila target anomalije")

    # --- prag: ista formula na obje strane ---
    live = read(MAIN / "psd_live.c")
    if define(live, "CAL_P_HI") != "0.90f" or define(live, "CAL_K_SIGMA") != "3.0f":
        problems.append("formula praga u psd_live.c nije p90 / sredina+3sd")
    if "CAL_P_HI = 0.90" not in read(ROOT / "pc" / "tools" / "derive_temporal_policy.py"):
        problems.append("derive_temporal_policy.py ne koristi isti prag kao firmware")

    if problems:
        print("NESAGLASNOSTI:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("schema i politike saglasne:")
    print(f"  protokol            {firmware_protocol.group(1)}")
    print(f"  prisustvo           {presence['policy']['absent_margin_db']} dB / "
          f"{presence['policy']['min_consecutive_windows']} prozora")
    print(f"  vremenska odluka    {chosen['rule']} "
          f"(n={chosen['min_consecutive']}, izlaz {chosen['exit_scale']}x)")
    print("  sve politike        target_anomalies_used=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
