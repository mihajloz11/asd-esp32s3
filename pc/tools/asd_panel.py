"""Panel u pregledacu: virtuelni taster, virtuelne lampice i vodic kroz run.

ZASTO POSTOJI. Fizicki taster (GPIO10) i dvije diode (GPIO2, GPIO11) nisu
zalemljeni, a bez tastera `ASD_PSD_LIVE` nikad ne pocne ucenje. Panel daje isti
ulaz i isti izlaz preko konzole: klik salje `PRESS`/`HOLD` firmveru
(`firmware/esp32s3_asd/main/asd_cmd.c`), a lampice se crtaju iz `FLAGS` zapisa
koji emituje isti UI task koji pali diode.

VODIC KROZ RUN. Fizicki protokol trazi da svaki uslov traje najmanje pet punih
prozora od 10 s i da se oznaka upise neposredno PRIJE promjene. Oboje je lako
promasiti sa stopericom u ruci, pa panel to vodi sam: odbrojava fazu, pise sta
operater treba da radi, i u trenutku prelaza upisuje `condition` u command file
alata za eksperiment. Operater gleda jedan ekran.

Panel nista ne odlucuje o rezultatu i ne ulazi u metrike. Mjerodavan zapis
ostaje telemetrija uredjaja (`BUTTON`, `STATE`, `EVENT`, `DET`) i `events.csv`
alata.

DVA REZIMA.

  1. Samostalni (`--port COM3`): panel drzi serijski port. Za bring-up i probe.
     Vodic radi kao stoperica, ali `condition` oznake nemaju gdje da odu.

  2. Uz zakljucani protokol (`--command-file ... --follow ...`): port drzi
     `physical_fan_experiment.py`; panel mu dopisuje komande, a lampice cita iz
     `serial.log` tog runa. Ovo je jedini ispravan rezim za valjano mjerenje.

Primjeri:

    python pc/tools/asd_panel.py --port COM3
    python pc/tools/asd_panel.py --command-file results/physical_fan/cmd.txt \
        --follow results/physical_fan/run_.../serial.log --plan full
"""
from __future__ import annotations

import argparse
import json
import math
import re
import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PC_DIR = Path(__file__).resolve().parents[1]
if str(PC_DIR) not in sys.path:
    sys.path.insert(0, str(PC_DIR))

from asd.commissioning_policy import (  # noqa: E402
    MAX_LOO_CV,
    calibration_acceptance,
)
from asd.guided_test import GUIDED25, GUIDED25_PLAN  # noqa: E402

FLAGS_RE = re.compile(r"\bFLAGS\s+(?P<body>.*)$")
VBUTTON_RE = re.compile(r"\bVBUTTON\s+.*?result=(?P<result>\S+)")
DET_RE = re.compile(
    r"^DET\s+(?P<window>\d+)\s+score=(?P<score>\S+)\s+lo=\S+\s+"
    r"hi=(?P<threshold>\S+)\s+.*?\(uzastopnih=(?P<consecutive>\d+)\s+"
    r"nivo=(?P<level>\S+)\s+dBFS"
)
WAIT_RE = re.compile(r"\bWAIT\s+(?P<index>\d+)/(?P<total>\d+)")
CAL_RE = re.compile(r"\bCAL\s+(?P<index>\d+)/(?P<total>\d+)")
SUMMARY_RE = re.compile(r"phase=CAL_SUMMARY\b.*?\bloo_cv=(?P<loo_cv>\S+)")
ADAPT_RE = re.compile(r"\bADAPTTHR\b.*?\bthr=(?P<thr>\S+)")
INTERFERENCE_RE = re.compile(r"^INTERFERENCE\b(?P<body>.*)$")
KV_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\S+)")
PROFILE_RE = re.compile(r"^PROFILE\b.*?derive_windows=(?P<derive>\d+)\s+verify_windows=(?P<verify>\d+)")
SESSION_START_RE = re.compile(r"^SESSION\b.*?action=STARTED\b")
STATE_RE = re.compile(r"^STATE\b.*?\bto=(?P<to>\S+)")
DROPPED_RE = re.compile(r"(?:^DROPPED\s+|\b)dropped=(?P<count>\d+)")
VWORKFLOW_RE = re.compile(r"^VWORKFLOW\s+mode=(?P<mode>\S+)\s+result=(?P<result>\S+)")
DET_ANOM_RE = re.compile(r"^DET\b.*?\banom=(?P<anom>[01])\b")

DEFAULT_PORT = 8772
LOG_LINES = 12

# keep operator events visible; omit repetitive window telemetry.
LOGGED_RECORDS = {
    "VBUTTON", "BUTTON", "SESSION", "STATE", "EVENT", "ADAPTTHR",
    "INTERFERENCE",
}

INTERFERENCE_POLICY = json.loads(
    (PC_DIR / "config" / "asd_interference_policy_v3.json").read_text(
        encoding="utf-8"
    )
)

# Jedini numericki izvor je verzionisana commissioning politika. Panel ovaj
# gate sprovodi server-side; browser je samo prikaz iste odluke.
LOO_CV_GATE = MAX_LOO_CV


RESEARCH_DIMS_RE = re.compile(r"\bdims=(?P<dims>\d+)\b")


def research_line_intact(line: str) -> bool:
    """Da li je FEATURE96/SUBSEG96 red stigao cio i sam.

    Firmware ga sastavlja iz 98 `printf` poziva (`emit_research_vector`), pa je
    22.08.2026 FLAGS iz UI taska upao usred niza brojeva. Host je u istom redu
    vidio dva `protocol=` i odbio 126 zapisa -- ali tek pri finalizaciji, 27
    minuta kasnije. Provjeravaju se bas ta dva traga: tacno jedan `protocol=` i
    onoliko vrijednosti koliko sam red tvrdi u `dims=`.
    """
    if line.count("protocol=") != 1:
        return False
    match = RESEARCH_DIMS_RE.search(line)
    if match is None:
        return False
    _, separator, values = line.partition(" values=")
    if not separator or not values:
        return False
    return values.count(",") + 1 == int(match.group("dims"))


def finite_float_or_none(value: str | float | None) -> float | None:
    """Parse UI telemetry without ever retaining a JSON-nonfinite float."""
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None

# Redoslijed faza. Trajanja su visekratnici prozora od 10 s: alarm trazi tri
# uzastopna prozora, pa ispod sest prozora uslov ne dokazuje nista.
PLANS = {
    "guided25": GUIDED25_PLAN,
    "full": [
        ("Normalna osnova", "normal_baseline", 600,
         "Sjedi mirno. Ne pricaj, ne kucaj, ne prilazi ventilatoru."),
        ("Papiric 1", "airflow_change", 60,
         "Drzi papiric uz USIS (zadnja strana), spolja, bez kontakta."),
        ("Oporavak 1", "recovery_normal", 90,
         "Skloni papiric I ruku. Odmakni se korak. Tisina."),
        ("Papiric 2", "airflow_change", 60,
         "Papiric uz usis, isto mjesto i isti zahvat kao prvi put."),
        ("Oporavak 2", "recovery_normal", 90,
         "Skloni papiric I ruku. Tisina."),
        ("Papiric 3", "airflow_change", 60,
         "Papiric uz usis, treci put."),
        ("Oporavak 3", "recovery_normal", 90,
         "Skloni papiric I ruku. Tisina."),
        ("Razgovor", "ambient_noise", 60,
         "Pricaj normalnim glasom sa oznacenog mjesta, 2 m od mikrofona."),
        ("Oporavak", "recovery_normal", 90,
         "Prestani da pricas. Tisina."),
        ("Gasenje", "controlled_stop", 30,
         "SAD ugasi ventilator. Ne pomjeraj ga."),
    ],
    "short": [
        ("Normalna osnova", "normal_baseline", 300,
         "Sjedi mirno. Ne pricaj, ne kucaj, ne prilazi ventilatoru."),
        ("Papiric 1", "airflow_change", 60,
         "Drzi papiric uz USIS (zadnja strana), spolja, bez kontakta."),
        ("Oporavak 1", "recovery_normal", 90,
         "Skloni papiric I ruku. Odmakni se korak. Tisina."),
        ("Papiric 2", "airflow_change", 60,
         "Papiric uz usis, isto mjesto i isti zahvat kao prvi put."),
        ("Oporavak 2", "recovery_normal", 90,
         "Skloni papiric I ruku. Tisina."),
        ("Razgovor", "ambient_noise", 60,
         "Pricaj normalnim glasom sa oznacenog mjesta, 2 m od mikrofona."),
        ("Oporavak", "recovery_normal", 90,
         "Prestani da pricas. Tisina."),
        ("Gasenje", "controlled_stop", 30,
         "SAD ugasi ventilator. Ne pomjeraj ga."),
    ],
}


class PanelState:
    """Sve sto panel zna. Jedan lock, jer HTTP handleri idu u vise niti."""

    def __init__(self, plan: list[tuple[str, str, int, str]], *,
                 workflow: str = "legacy", report_dir: Path | None = None,
                 attempt: int = 1, read_only_preview: bool = False) -> None:
        self.lock = threading.Lock()
        self.plan = plan
        self.flags: dict[str, str] = {}
        self.det: dict[str, str] = {}
        self.log: list[str] = []
        self.source = "ceka podatke"
        self.last_line_at = 0.0
        # vodic
        self.stage = "IDLE"  # IDLE | CAL | CAL_REJECTED | READY_TO_GO | RUN | DONE
        self.cal_progress = ""
        self.loo_cv: float | None = None
        self.threshold: float | None = None
        self.interference_threshold: float | None = None
        self.interference_calibrated = False
        self.calibration_accepted = False
        self.calibration_acceptance_reason = "missing_cal_summary"
        self.started_at: float | None = None
        self.phase_index = -1
        self.workflow = workflow
        self.report_dir = report_dir
        self.attempt = attempt
        self.read_only_preview = read_only_preview
        self.workflow_armed = False
        self.workflow_result = "not_armed"
        self.pending_workflow_accepted = False
        self.session_started_at: float | None = None
        self.profile_counts: tuple[int, int] | None = None
        self.research_counts = {"FEATURE96": 0, "SUBSEG96": 0}
        self.research_errors = 0
        self.research_error_example: str | None = None
        self.max_dropped = 0
        self.dropped_observed = False
        self.invalid_reason: str | None = None
        self.phase_stats = [
            {"alarm_episodes": 0, "alarm_windows": 0, "det_windows": 0,
             "max_consecutive": 0, "hold_windows": 0}
            for _ in plan
        ]
        self.final_result: dict | None = None
        self.session_generation = 0

    # --- ulazni tok -------------------------------------------------------
    def feed(self, line: str) -> None:
        line = line.rstrip("\r\n").strip()
        if not line:
            return
        with self.lock:
            self.last_line_at = time.time()

            vm = VWORKFLOW_RE.match(line)
            if vm:
                self.workflow_result = vm.group("result")
                self.workflow_armed = vm.group("result") == "accepted"
                self.pending_workflow_accepted = self.workflow_armed
                self._log(line)
                return
            if SESSION_START_RE.match(line):
                self.session_generation += 1
                self.workflow_result = (
                    "accepted" if self.pending_workflow_accepted else "missing_for_session")
                self.workflow_armed = self.pending_workflow_accepted
                self.pending_workflow_accepted = False
                self.loo_cv = None
                self.threshold = None
                self.interference_threshold = None
                self.interference_calibrated = False
                self.calibration_accepted = False
                self.calibration_acceptance_reason = "missing_cal_summary"
                self.profile_counts = None
                self.research_counts = {"FEATURE96": 0, "SUBSEG96": 0}
                self.research_errors = 0
                self.research_error_example = None
                self.max_dropped = 0
                self.dropped_observed = False
                self.invalid_reason = None
                self.phase_stats = [
                    {"alarm_episodes": 0, "alarm_windows": 0, "det_windows": 0,
                     "max_consecutive": 0, "hold_windows": 0}
                    for _ in self.plan
                ]
                self.det = {}
                self.stage = "CAL"
                self.started_at = None
                self.phase_index = -1
                self.final_result = None
                self.session_started_at = time.monotonic()
                self._log(line)
                return
            pm = PROFILE_RE.match(line)
            if pm:
                self.profile_counts = (int(pm.group("derive")), int(pm.group("verify")))
                self._log(line)
            token = line.split(" ", 1)[0]
            if token in self.research_counts:
                if research_line_intact(line):
                    self.research_counts[token] += 1
                else:
                    # Run 22.08.2026: FLAGS se zalijepio usred FEATURE96 reda,
                    # host je odbio 126 zapisa i cio run pao na
                    # `invalid_research_telemetry` -- ali tek na kraju, poslije
                    # 27 minuta. Panel isto mora da vidi odmah, dok se pokusaj
                    # jos moze prekinuti i ponoviti.
                    self.research_errors += 1
                    if self.research_error_example is None:
                        self.research_error_example = line[:180]
                return
            dm = DROPPED_RE.match(line)
            if dm:
                self.dropped_observed = True
                self.max_dropped = max(self.max_dropped, int(dm.group("count")))
            if line.startswith("PARSE_ERROR") or "AUDIO_TIMEOUT" in line:
                self.invalid_reason = line[:200]
            sm = STATE_RE.match(line)
            if sm and 0 <= self.phase_index < len(self.phase_stats):
                target = sm.group("to")
                if target == "ANOMALY":
                    self.phase_stats[self.phase_index]["alarm_episodes"] += 1
                elif target == "OBSERVATION_HOLD":
                    self.phase_stats[self.phase_index]["hold_windows"] += 1

            match = FLAGS_RE.search(line)
            if match:
                was_learning = self.flags.get("learning") == "1"
                flags = {
                    m.group("key"): m.group("value")
                    for m in KV_RE.finditer(match.group("body"))
                }
                # Uredjaj ponavlja FLAGS na 5 s zbog hosta koji se kasno zakaci;
                # u log ide samo stvarna promjena, da se ostalo ne izgura.
                changed = flags != self.flags
                self.flags = flags
                if "dropped" in flags:
                    try:
                        dropped = int(flags["dropped"])
                    except ValueError:
                        self.invalid_reason = "nevalidan FLAGS dropped"
                    else:
                        self.dropped_observed = True
                        self.max_dropped = max(self.max_dropped, dropped)
                if flags.get("learning") == "1":
                    if not was_learning:
                        self.cal_progress = ""
                        self.loo_cv = None
                        self.threshold = None
                        self.det = {}
                        self.calibration_accepted = False
                        self.calibration_acceptance_reason = "missing_cal_summary"
                    self.stage = "CAL"
                if changed:
                    self._log(line)
                return

            summary = SUMMARY_RE.search(line)
            if summary:
                raw_loo_cv = summary.group("loo_cv")
                # Centralna politika dobija originalni token da bi sacuvala
                # tacan reject razlog (npr. nonfinite_loo_cv), dok stanje za
                # JSON/UI zadrzava samo konacne brojeve.
                accepted, reason = calibration_acceptance({
                    "cal_summary": {"loo_cv": raw_loo_cv},
                })
                self.loo_cv = finite_float_or_none(raw_loo_cv)
                self.calibration_accepted = accepted
                self.calibration_acceptance_reason = reason
                if not accepted:
                    self.stage = "CAL_REJECTED"
                self.cal_progress = "kalibracija gotova"
                self._log(line)
                return

            adapt = ADAPT_RE.search(line)
            if adapt:
                self.threshold = finite_float_or_none(adapt.group("thr"))
                if self.loo_cv is None:
                    accepted = False
                    reason = self.calibration_acceptance_reason
                else:
                    accepted, reason = calibration_acceptance({
                        "cal_summary": {"loo_cv": self.loo_cv},
                    })
                self.calibration_accepted = accepted
                self.calibration_acceptance_reason = reason
                if self.stage in {"CAL", "CAL_REJECTED"}:
                    self.stage = "READY_TO_GO" if accepted else "CAL_REJECTED"
                self._log(line)
                return

            interference = INTERFERENCE_RE.match(line)
            if interference:
                fields = {
                    match.group("key"): match.group("value")
                    for match in KV_RE.finditer(interference.group("body"))
                }
                policy = INTERFERENCE_POLICY["policy"]
                normal_max = finite_float_or_none(fields.get("normal_max"))
                multiplier = finite_float_or_none(fields.get("multiplier"))
                threshold = finite_float_or_none(fields.get("threshold"))
                try:
                    normal_windows = int(fields.get("normal_windows", "-1"))
                    use_tonalness = int(fields.get("use_tonalness_delta", "-1"))
                    long_hold = int(fields.get("long_hold_windows", "-1"))
                except ValueError:
                    normal_windows = use_tonalness = long_hold = -1
                valid = bool(
                    fields.get("protocol") == "asd-quality-v1.6.0"
                    and fields.get("policy") == INTERFERENCE_POLICY["schema_version"]
                    and fields.get("source") == "CAL_NORMAL_ONLY"
                    and normal_windows == int(policy["calibration_min_windows"])
                    and use_tonalness == int(bool(policy["use_tonalness_delta"]))
                    and long_hold == int(policy["long_hold_windows"])
                    and normal_max is not None and normal_max > 0.0
                    and multiplier is not None
                    and math.isclose(
                        multiplier, float(policy["normal_max_multiplier"]),
                        rel_tol=1e-6, abs_tol=1e-6,
                    )
                    and threshold is not None
                    and math.isclose(
                        threshold, normal_max * multiplier,
                        rel_tol=1e-6, abs_tol=1e-6,
                    )
                )
                self.interference_calibrated = valid
                self.interference_threshold = threshold if valid else None
                if not valid:
                    self.invalid_reason = "invalid_INTERFERENCE_normal_only_calibration"
                self._log(line)
                return

            det = DET_RE.match(line)
            if det:
                self.det = det.groupdict()
                if 0 <= self.phase_index < len(self.phase_stats):
                    stats = self.phase_stats[self.phase_index]
                    stats["det_windows"] += 1
                    stats["max_consecutive"] = max(
                        stats["max_consecutive"], int(det.group("consecutive")))
                anomaly = DET_ANOM_RE.match(line)
                if (0 <= self.phase_index < len(self.phase_stats)
                        and anomaly and anomaly.group("anom") == "1"):
                    self.phase_stats[self.phase_index]["alarm_windows"] += 1
                self._log(line)
                return

            wait = WAIT_RE.search(line)
            if wait:
                self.cal_progress = (
                    f"osluskuje {wait.group('index')}/{wait.group('total')}"
                )
                return
            cal = CAL_RE.search(line)
            if cal:
                self.cal_progress = f"uci {cal.group('index')}/{cal.group('total')}"
                return

            if line.split(" ", 1)[0] in LOGGED_RECORDS:
                self._log(line)

    def _log(self, line: str) -> None:
        self.log.append(line)
        del self.log[:-LOG_LINES]

    # --- vodic ------------------------------------------------------------
    def phase_at(self, elapsed: float) -> tuple[int, float]:
        """Indeks faze i koliko je sekundi ostalo u njoj. (-1, 0) = kraj."""
        acc = 0.0
        for index, (_, _, duration, _) in enumerate(self.plan):
            if elapsed < acc + duration:
                return index, acc + duration - elapsed
            acc += duration
        return -1, 0.0

    def snapshot(self) -> dict:
        with self.lock:
            age = time.time() - self.last_line_at if self.last_line_at else None
            elapsed = (
                time.monotonic() - self.started_at
                if self.started_at is not None else None
            )
            index, remaining = (
                self.phase_at(elapsed) if elapsed is not None else (-1, 0.0)
            )
            total = sum(item[2] for item in self.plan)
            hard_deadline = GUIDED25.get("hard_deadline_seconds")
            deadline_remaining = (
                None if self.session_started_at is None or hard_deadline is None
                else max(0.0, hard_deadline -
                         (time.monotonic() - self.session_started_at))
            )
            monitoring_required = total + int(
                GUIDED25["monitoring_start_guard_seconds"]
            )
            phases = [
                {"name": name, "condition": cond, "seconds": secs, "what": what}
                for name, cond, secs, what in self.plan
            ]
            return {
                "flags": dict(self.flags),
                "det": dict(self.det),
                "log": list(self.log),
                "source": self.source,
                "age_s": None if age is None else round(age, 1),
                "stage": self.stage,
                "cal_progress": self.cal_progress,
                "loo_cv": self.loo_cv,
                "loo_cv_gate": LOO_CV_GATE,
                "calibration_accepted": self.calibration_accepted,
                "calibration_acceptance_reason": self.calibration_acceptance_reason,
                "threshold": self.threshold,
                "interference_threshold": self.interference_threshold,
                "interference_calibrated": self.interference_calibrated,
                "phases": phases,
                "phase_index": index,
                "phase_remaining": round(remaining),
                "elapsed": None if elapsed is None else round(elapsed),
                "total": total,
                "workflow": self.workflow,
                "attempt": self.attempt,
                "attempt_limit": GUIDED25["acceptance"]["attempt_limit"],
                "read_only_preview": self.read_only_preview,
                "workflow_armed": self.workflow_armed,
                "workflow_result": self.workflow_result,
                "profile_counts": self.profile_counts,
                "research_counts": dict(self.research_counts),
                "research_errors": self.research_errors,
                "research_error_example": self.research_error_example,
                "max_dropped": self.max_dropped,
                "dropped_observed": self.dropped_observed,
                "deadline_remaining": (
                    None if deadline_remaining is None else round(deadline_remaining)
                ),
                "monitoring_required_seconds": monitoring_required,
                "monitoring_start_allowed": (
                    True if hard_deadline is None
                    else bool(deadline_remaining is not None and
                              deadline_remaining >= monitoring_required)
                ),
                "final_result": self.final_result,
            }

    def guided_preflight(self) -> tuple[bool, list[str]]:
        reasons = []
        if self.workflow != "guided25": reasons.append("panel nije u guided25 rezimu")
        if self.attempt > GUIDED25["acceptance"]["attempt_limit"]:
            reasons.append(
                f"dosegnut limit od {GUIDED25['acceptance']['attempt_limit']} pokusaja"
            )
        if self.last_line_at == 0 or time.time() - self.last_line_at > 15: reasons.append("nema svjeze telemetrije")
        if self.flags.get("guided25_available") != "1": reasons.append("firmware nema GUIDED25")
        if self.flags.get("protocol") != "asd-quality-v1.6.0": reasons.append("pogresna firmware/protocol verzija")
        if self.flags.get("research_telemetry") != "1": reasons.append("research telemetry build nije aktivan")
        if self.flags.get("profile_persistence_allowed") != "0": reasons.append("DEVELOPMENT storage gate nije zatvoren")
        if not self.dropped_observed: reasons.append("DROPPED zapis nije primljen")
        elif self.max_dropped != 0: reasons.append("dropped nije nula")
        if self.flags.get("waiting") != "1": reasons.append("uredjaj nije IDLE")
        if self.report_dir is None or not self.report_dir.exists(): reasons.append("run/artefakt direktorij ne postoji")
        return not reasons, reasons

    def guided_monitoring_gate(self) -> tuple[bool, list[str]]:
        reasons = []
        if self.attempt < 1 or self.attempt > GUIDED25["acceptance"]["attempt_limit"]:
            reasons.append("pokusaj nije 1..3")
        if self.last_line_at == 0 or time.time() - self.last_line_at > 15:
            reasons.append("telemetrija nije svjeza")
        if self.flags.get("protocol") != "asd-quality-v1.6.0":
            reasons.append("nije q1.6")
        if self.flags.get("guided25_available") != "1":
            reasons.append("nema GUIDED25 capability")
        if self.flags.get("learning") == "1" or self.flags.get("learned") != "1":
            reasons.append("uredjaj nije READY poslije commissioninga")
        if self.workflow_result != "accepted":
            reasons.append("GUIDED25 armiranje nije potvrdjeno")
        if not self.dropped_observed or self.max_dropped != 0:
            reasons.append("DROPPED=0 nije potvrdjen")
        if not self.calibration_accepted:
            reasons.append("K1 nije prihvacen")
        if not self.interference_calibrated:
            reasons.append("HOLD prag nije izveden iz CAL normal-only prozora")
        if self.profile_counts != (44, 22):
            reasons.append("firmware nije potvrdio GUIDED25 44/22")
        if not all(self.research_counts.values()):
            reasons.append("nedostaje FEATURE96/SUBSEG96 telemetrija")
        hard_deadline = GUIDED25.get("hard_deadline_seconds")
        if hard_deadline is not None:
            if self.session_started_at is None:
                reasons.append("sesijski hard-stop tajmer nije pokrenut")
            else:
                remaining = hard_deadline - (
                    time.monotonic() - self.session_started_at
                )
                required = sum(item[2] for item in self.plan) + int(
                    GUIDED25["monitoring_start_guard_seconds"]
                )
                if remaining < required:
                    reasons.append(
                        f"nema dovoljno vremena: ostalo {max(0, round(remaining))}s, "
                        f"potrebno najmanje {required}s"
                    )
        return not reasons, reasons

    def guided_result(self) -> dict:
        reasons: list[str] = []
        inconclusive: list[str] = []
        if not self.calibration_accepted: reasons.append("K1 nije prihvacen")
        if self.flags.get("protocol") != "asd-quality-v1.6.0": reasons.append("nije q1.6")
        if self.flags.get("guided25_available") != "1": reasons.append("nema GUIDED25 capability")
        if self.workflow_result != "accepted": reasons.append("GUIDED25 nije prihvacen")
        if self.profile_counts != (44, 22): reasons.append("pogresan commissioning 44/22")
        if not self.dropped_observed: reasons.append("DROPPED zapis nedostaje")
        if self.max_dropped != 0: reasons.append("dropped_samples nije nula")
        if self.invalid_reason: reasons.append(self.invalid_reason)
        if not all(self.research_counts.values()): reasons.append("nedostaje research telemetrija")
        if self.research_errors:
            reasons.append(f"pokvarenih research redova: {self.research_errors}")
        papers = [s for p, s in zip(self.plan, self.phase_stats) if p[1].startswith("airflow_change_paper_")]
        passing = sum(s["alarm_episodes"] >= 1 and s["max_consecutive"] >= 3 for s in papers)
        if passing < 2: reasons.append(f"papiric prosao {passing}/3 blokova; potrebno 2/3")
        for p, stats in zip(self.plan, self.phase_stats):
            cond = p[1]
            minimum = 3
            if cond == "ambient_door": minimum = 1
            if stats["det_windows"] < minimum: reasons.append(f"premalo prozora u {cond}")
            forbidden = (cond.startswith("normal_") or cond.startswith("recovery") or
                         cond == "final_recovery" or cond.startswith("ambient_"))
            if forbidden and (stats["alarm_episodes"] or stats["alarm_windows"]):
                reasons.append(f"alarm ili prenesen alarm u {cond}")
        status = "FAIL" if reasons else ("INCONCLUSIVE" if inconclusive else "PASS")
        return {"schema_version": GUIDED25["schema_version"], "status": status,
                "reasons": reasons, "inconclusive": inconclusive,
                "attempt": self.attempt, "profile_counts": self.profile_counts,
                "research_counts": self.research_counts, "phase_stats": self.phase_stats}


class SerialLink:
    """Rezim 1: panel drzi port i sam salje komande."""

    def __init__(self, state: PanelState, port: str, baud: int) -> None:
        import serial  # lokalno, da rezim 2 radi i bez pyseriala

        self.state = state
        self.ser = serial.Serial(port, baud, timeout=0.5)
        state.source = f"serijski port {port}"
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self) -> None:
        while True:
            try:
                raw = self.ser.readline()
            except Exception as exc:  # port otkacen usred rada
                self.state.feed(f"[panel] citanje prekinuto: {exc}")
                return
            if raw:
                self.state.feed(raw.decode("utf-8", errors="replace"))

    def send(self, verb: str) -> str:
        wire = b"PRESS\n" if verb == "press" else b"HOLD\n"
        self.ser.write(wire)
        self.ser.flush()
        return f"poslato {wire.decode().strip()} na port"

    def send_raw(self, line: str) -> str:
        # Bez alata za eksperiment `condition` oznaka nema gdje da ode; upisuje
        # se samo u panel log, da se ne pravi privid da je zabiljezena.
        self.state.feed(f"[panel bez zapisa] {line}")
        return f"'{line}' nije zapisano (rezim bez alata)"

    def arm_guided25(self) -> str:
        self.ser.write(b"GUIDED25\n")
        self.ser.flush()
        return "GUIDED25 poslat"


class CommandFileLink:
    """Rezim 2: komande idu u command file, telemetrija se cita iz serial.log.

    Time port ostaje kod `physical_fan_experiment.py`, koji je jedini koji
    smije da ga drzi tokom valjanog mjerenja.
    """

    def __init__(self, state: PanelState, command_file: Path,
                 follow: Path | None, cmd_port: str | None = None) -> None:
        self.state = state
        self.command_file = command_file
        self.cmd_ser = None
        command_file.parent.mkdir(parents=True, exist_ok=True)
        command_file.touch(exist_ok=True)
        state.source = f"command file {command_file.name}"
        # Pritisak moze ici direktno na drugi port (CH343/UART0) dok alat drzi
        # prvi (native USB). Firmware slusa oba, pa je to isti ulaz -- a ne
        # zahtijeva da dva procesa dijele isti port.
        if cmd_port:
            import serial

            ser = serial.Serial()
            ser.port = cmd_port
            ser.baudrate = 115200
            ser.timeout = 0.3
            ser.dtr = False   # bez reset impulsa na EN/IO0
            ser.rts = False
            ser.open()
            ser.write(b"\n")  # isprazni zaostali djelimican red na liniji
            ser.flush()
            self.cmd_ser = ser
            state.source += f" + komande na {cmd_port}"
        if follow is not None:
            state.source += f" + {follow.name}"
            threading.Thread(target=self._tail, args=(follow,), daemon=True).start()

    def _tail(self, path: Path) -> None:
        offset = 0
        while True:
            try:
                if path.exists():
                    with path.open("r", encoding="utf-8", errors="replace") as handle:
                        handle.seek(offset)
                        for line in handle:
                            # serial.log je "utc<TAB>elapsed<TAB>linija"
                            self.state.feed(line.split("\t")[-1])
                        offset = handle.tell()
            except OSError:
                pass
            time.sleep(0.3)

    def send(self, verb: str) -> str:
        if self.cmd_ser is not None:
            wire = b"PRESS\n" if verb == "press" else b"HOLD\n"
            self.cmd_ser.write(wire)
            self.cmd_ser.flush()
            # NE upisuje se `press`/`hold`, nego `note`. Alat bi na te verbe
            # poslao istu komandu na SVOJ port, a firmware oba porta sipa u
            # jedan bafer reda -- pa se bajtovi dvije kopije isprepletu i red
            # stigne kao smece (`unknown_command`, izmjereno 16.08.2026).
            # Radnja se i dalje biljezi u `events.csv`, samo kao biljeska.
            self.send_raw(f"note virtuelni taster {verb} -> {self.cmd_ser.port}")
            return f"poslato {wire.decode().strip()} na {self.cmd_ser.port}"
        return self.send_raw(f"{verb} panel")

    def send_raw(self, line: str) -> str:
        with self.command_file.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return f"upisano '{line}' u {self.command_file.name}"

    def arm_guided25(self) -> str:
        return self.send_raw("guided25 panel")


class CalibrationGateError(RuntimeError):
    """Server-side refusal to start measurement after a failed K1 gate."""


class Conductor:
    """Odbrojava faze i upisuje `condition` neposredno prije svake promjene."""

    def __init__(self, state: PanelState, link) -> None:
        self.state = state
        self.link = link
        self.thread: threading.Thread | None = None
        self.deadline_thread: threading.Thread | None = None
        self.stop_event = threading.Event()

    def arm_guided25(self, *, virtual_start: bool) -> str:
        ok, reasons = self.state.guided_preflight()
        if not ok:
            raise CalibrationGateError("preflight: " + "; ".join(reasons))
        message = self.link.arm_guided25()
        self.stop_event.clear()
        if virtual_start:
            message += "; " + self.link.send("press")
        hard_deadline = GUIDED25.get("hard_deadline_seconds")
        if hard_deadline is not None:
            expected_generation = self.state.session_generation + 1
            self.deadline_thread = threading.Thread(
                target=self._deadline, args=(expected_generation,), daemon=True)
            self.deadline_thread.start()
        return message

    def _deadline(self, expected_generation: int) -> None:
        while not self.stop_event.is_set():
            with self.state.lock:
                started = self.state.session_started_at
                done = self.state.stage == "DONE"
                generation = self.state.session_generation
            if generation > expected_generation:
                return
            if generation < expected_generation:
                time.sleep(0.05)
                continue
            if done:
                return
            hard_deadline = GUIDED25.get("hard_deadline_seconds")
            if (hard_deadline is not None and started is not None and
                    time.monotonic() - started >= hard_deadline):
                self.link.send_raw("abort guided25_hard_deadline")
                with self.state.lock:
                    self.state.invalid_reason = "guided25_hard_deadline"
                    self.state.final_result = self.state.guided_result()
                    self.state.stage = "DONE"
                    result = self.state.final_result
                self._write_report(result)
                self.stop_event.set()
                return
            time.sleep(0.2)

    def _write_report(self, result: dict | None) -> None:
        # Mjerodavni report pise physical_fan_experiment tek poslije strict
        # finalizacije FEATURE96/SUBSEG96 paketa i njegovog SHA-256 manifesta.
        return

    def abort(self, reason: str = "operator_panel_abort") -> str:
        self.stop_event.set()
        message = self.link.send_raw(f"abort {reason}")
        with self.state.lock:
            self.state.invalid_reason = reason
            self.state.final_result = (
                self.state.guided_result() if self.state.workflow == "guided25" else None)
            self.state.stage = "DONE"
            result = self.state.final_result
        self._write_report(result)
        if (self.thread is not None and self.thread.is_alive() and
                threading.current_thread() is not self.thread):
            self.thread.join(timeout=1.0)
        return message

    def start(self) -> str:
        if self.thread is not None and self.thread.is_alive():
            return "vodic vec radi"
        with self.state.lock:
            accepted, reason = calibration_acceptance({
                "cal_summary": {"loo_cv": self.state.loo_cv}
                if self.state.loo_cv is not None else None,
            })
            if self.state.stage != "READY_TO_GO" or not accepted:
                raise CalibrationGateError(
                    f"mjerenje odbijeno: K1 {reason}; ponovi kalibraciju"
                )
            if self.state.workflow == "guided25":
                ok, reasons = self.state.guided_monitoring_gate()
                if not ok:
                    raise CalibrationGateError("start gate: " + "; ".join(reasons))
            self.state.started_at = time.monotonic()
            self.state.stage = "RUN"
            self.state.phase_index = -1
            generation = self.state.session_generation
        self.thread = threading.Thread(target=self._run, args=(generation,), daemon=True)
        self.thread.start()
        return "vodic pokrenut"

    def _run(self, generation: int) -> None:
        sent = -1
        while not self.stop_event.is_set():
            with self.state.lock:
                started = self.state.started_at
                current_generation = self.state.session_generation
            if current_generation != generation:
                return
            if started is None:
                return
            elapsed = time.monotonic() - started
            index, _ = self.state.phase_at(elapsed)
            if index == -1:
                self.link.send_raw("stop kraj plana")
                with self.state.lock:
                    self.state.final_result = self.state.guided_result() if self.state.workflow == "guided25" else None
                    self.state.stage = "DONE"
                    result = self.state.final_result
                self._write_report(result)
                self.stop_event.set()
                return
            if index != sent:
                name, condition, _, what = self.state.plan[index]
                self.link.send_raw(f"condition {condition} {name}: {what}")
                with self.state.lock:
                    self.state.phase_index = index
                sent = index
            time.sleep(0.2)

PAGE = """<!doctype html>
<meta charset="utf-8"><title>ASD panel</title>
<style>
 body{background:#14171c;color:#dfe4ea;font:15px/1.5 system-ui,sans-serif;
      margin:0;padding:24px;display:flex;justify-content:center}
 .wrap{width:min(760px,100%)}
 h1{font-size:16px;font-weight:600;margin:0 0 3px}
 .sub{color:#8b949e;font-size:12.5px;margin-bottom:18px}
 .card{background:#1b1f26;border-radius:10px;padding:20px 22px;margin-bottom:14px}
 .lamps{display:flex;gap:32px;align-items:center}
 .bulb{width:48px;height:48px;border-radius:50%;margin:0 auto 6px;
       border:2px solid #2c323c;background:#22262e}
 .bulb.green{background:#2ee06a;border-color:#2ee06a;box-shadow:0 0 20px #2ee06a88}
 .bulb.red{background:#ff4d4d;border-color:#ff4d4d;box-shadow:0 0 20px #ff4d4d88}
 .lamp{text-align:center}.lamp span{font-size:11.5px;color:#8b949e}
 .verdict{margin-left:auto;text-align:right}
 .verdict b{font-size:19px;display:block}
 .chips{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:14px}
 .chip{padding:4px 10px;border-radius:20px;background:#1b1f26;color:#5c636d;
       font-size:12px;border:1px solid #262b33}
 .chip.on{background:#1f3d2b;color:#7ee2a4;border-color:#2f5d40}
 .chip.alarm{background:#43201f;color:#ff8e8e;border-color:#6d2f2d}
 #banner{text-align:center}
 #phase{font-size:13px;color:#8b949e;letter-spacing:.08em;text-transform:uppercase}
 #what{font-size:23px;font-weight:600;margin:8px 0 14px;line-height:1.35}
 #clock{font-size:60px;font-weight:700;font-variant-numeric:tabular-nums;
        line-height:1;margin-bottom:6px}
 #total{font-size:12.5px;color:#5c636d}
 .bar{height:7px;background:#22262e;border-radius:4px;overflow:hidden;margin-top:14px}
 .bar i{display:block;height:100%;background:#2f6feb;width:0}
 .act .bar i{background:#ff9f43}
 .act #clock{color:#ff9f43}
 ol{list-style:none;margin:0;padding:0;font-size:13px}
 ol li{padding:6px 10px;border-radius:6px;color:#5c636d;display:flex;gap:10px}
 ol li.done{color:#41505f}
 ol li.now{background:#22303f;color:#dfe4ea;font-weight:600}
 ol li b{margin-left:auto;font-variant-numeric:tabular-nums;font-weight:400}
 .btns{display:flex;gap:9px;margin-bottom:14px}
 button{flex:1;padding:12px;border:0;border-radius:8px;font-size:14px;
        font-weight:600;cursor:pointer;background:#2b313a;color:#dfe4ea}
 button.go{background:#2f6feb;color:#fff}
 button:disabled{opacity:.42;cursor:not-allowed;transform:none}
 button:active{transform:translateY(1px)}
 table{width:100%;border-collapse:collapse;font-size:13px}
 td{padding:4px 0;border-bottom:1px solid #232830;color:#8b949e}
 td+td{text-align:right;color:#dfe4ea;font-variant-numeric:tabular-nums}
 pre{background:#101318;border-radius:8px;padding:11px;font-size:11px;
     color:#7d8896;max-height:150px;overflow:auto;margin:0}
 .foot{color:#5c636d;font-size:12px;margin-top:9px}
 .warn{color:#ff8e8e}.ok{color:#7ee2a4}
 .alert{border-radius:10px;padding:11px 15px;margin-bottom:12px;font-size:13px;
        background:#43201f;border:1px solid #6d2f2d;color:#ffb3b3}
 .alert.soft{background:#3b3320;border-color:#6b5a2c;color:#ffd79a}
 .alert b{display:block;font-size:14.5px;margin-bottom:3px}
 #deadline{font-size:12.5px;color:#5c636d;margin-top:4px}
 #deadline.warn{color:#ff8e8e;font-weight:600}
 ol li i{font-style:normal;width:13px;color:#5c636d}
</style>
<div class="wrap">
 <h1>ASD panel &mdash; vodic kroz run</h1>
 <div class="sub" id="source">&nbsp;</div>

 <div id="alerts"></div>

 <div class="card" id="banner">
  <div id="phase">&mdash;</div>
  <div id="what">Ceka pocetak</div>
  <div id="clock">--:--</div>
  <div id="total">&nbsp;</div>
  <div class="bar"><i id="bar"></i></div>
  <div id="deadline">&nbsp;</div>
 </div>

 <div class="card lamps">
  <div class="lamp"><div class="bulb" id="green"></div><span>zelena</span></div>
  <div class="lamp"><div class="bulb" id="red"></div><span>crvena</span></div>
  <div class="verdict"><b id="mode">&mdash;</b><span id="state">&nbsp;</span></div>
 </div>

 <div class="chips">
  <div class="chip" id="c-waiting">ceka taster</div>
  <div class="chip" id="c-learning">uci</div>
  <div class="chip" id="c-learned">naucio</div>
  <div class="chip" id="c-anomaly">ANOMALIJA</div>
  <div class="chip" id="c-fault">kvar</div>
 </div>

 <div class="btns">
  <button onclick="post('arm-virtual')">1A. VIRTUELNI TASTER — armiraj GUIDED25 i pokreni</button>
  <button onclick="post('arm-physical')">1B. Armiraj, pa kratko pritisni fizicki taster</button>
  <button class="go" id="gobtn" onclick="post('start')">2. Kreni sa mjerenjem</button>
  <button onclick="post('hold')">Virtuelni DUGI pritisak — ponovi kalibraciju</button>
  <button onclick="post('abort')">Prekini i sacuvaj</button>
 </div>

 <div class="card"><ol id="plan"></ol></div>

 <div class="card">
  <table>
   <tr><td>kalibracija</td><td id="d-cal">&mdash;</td></tr>
   <tr><td>loo_cv (prag <span id="d-gate"></span>)</td><td id="d-cv">&mdash;</td></tr>
   <tr><td>prag odlucivanja</td><td id="d-thr">&mdash;</td></tr>
   <tr><td>prozor</td><td id="d-window">&mdash;</td></tr>
   <tr><td>score / prag</td><td id="d-score">&mdash;</td></tr>
   <tr><td>uzastopnih</td><td id="d-cons">&mdash;</td></tr>
   <tr><td>nivo</td><td id="d-level">&mdash;</td></tr>
  </table>
 </div>

 <pre id="log"></pre>
 <div class="foot" id="foot">&nbsp;</div>
</div>
<script>
let flags = {}, t0 = performance.now(), S = null;
const csrfToken = '__CSRF_TOKEN__';

function post(what){
  fetch('/'+what, {method:'POST', headers:{'X-CSRF-Token':csrfToken}}).then(r=>r.json())
   .then(j => document.getElementById('foot').textContent = j.message)
   .catch(e => document.getElementById('foot').textContent = 'greska: '+e);
}

function mmss(s){
  if (s === null || s === undefined) return '--:--';
  s = Math.max(0, Math.round(s));
  return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');
}

/* Obrasci su isti kao u asd_operator.c, pa lampica na ekranu titra kao dioda. */
function level(pattern, t){
  switch(pattern){
    case 'on': return true;
    case 'off': return false;
    case 'blink_5hz': return Math.floor(t/100) % 2 === 0;
    case 'flash_2s': return (t % 2000) < 60;
    case 'double_blink': {const p=t%1000; return p<120 || (p>240 && p<360);}
    default: return false;
  }
}

function paint(){
  const t = performance.now() - t0;
  document.getElementById('green').className =
    'bulb' + (level(flags.green || 'off', t) ? ' green' : '');
  document.getElementById('red').className =
    'bulb' + (level(flags.red || 'off', t) ? ' red' : '');
  requestAnimationFrame(paint);
}
requestAnimationFrame(paint);

function chip(id, on, alarm){
  const el = document.getElementById(id);
  el.className = 'chip' + (on ? (alarm ? ' alarm' : ' on') : '');
}

function renderPlan(s){
  const ol = document.getElementById('plan');
  if (ol.dataset.n != s.phases.length){
    ol.innerHTML = '';
    s.phases.forEach(p => {
      const li = document.createElement('li');
      li.innerHTML = '<i></i><span>'+p.name+'</span><b>'+mmss(p.seconds)+'</b>';
      ol.appendChild(li);
    });
    ol.dataset.n = s.phases.length;
  }
  [...ol.children].forEach((li, i) => {
    li.className = s.phase_index < 0 ? '' :
      (i < s.phase_index ? 'done' : (i === s.phase_index ? 'now' : ''));
    const mark = li.querySelector('i');
    if (!mark) return;
    mark.textContent = '';
  });
}

/* Alarm u ovim fazama obara run, i sprjecava novi ULAZAK u alarm u sljedecoj
   papiric fazi -- tako su 22.08.2026 propala dva od tri papiric bloka. */
function alarmForbidden(condition){
  return !condition.startsWith('airflow_change');
}

function renderAlerts(items){
  const box = document.getElementById('alerts');
  const signature = items.map(a => a[0]).join('|');
  if (box.dataset.sig === signature) return;
  box.dataset.sig = signature;
  box.innerHTML = '';
  items.forEach(item => {
    const div = document.createElement('div');
    div.className = 'alert' + (item[2] ? ' soft' : '');
    const title = document.createElement('b');
    title.textContent = item[0];
    div.appendChild(title);
    div.appendChild(document.createTextNode(item[1]));
    box.appendChild(div);
  });
}

function poll(){
  fetch('/state').then(r=>r.json()).then(s => {
    S = s; flags = s.flags || {};
    document.getElementById('source').textContent =
      s.source + (s.age_s === null ? '' : '  ·  zadnji red prije ' + s.age_s + ' s');
    if(s.read_only_preview) document.getElementById('source').textContent +=
      ' · SIGURNI READ-ONLY PREGLED (test se ne moze pokrenuti)';
    if(s.workflow === 'guided25') document.getElementById('source').textContent +=
      ' · pokusaj '+s.attempt+'/'+s.attempt_limit+' · rok '+mmss(s.deadline_remaining);
    document.getElementById('mode').textContent = flags.mode || '—';
    document.getElementById('state').textContent = flags.state || '';
    chip('c-waiting',  flags.waiting  === '1');
    chip('c-learning', flags.learning === '1');
    chip('c-learned',  flags.learned  === '1');
    chip('c-anomaly',  flags.anomaly  === '1', true);
    chip('c-fault',    flags.fault    === '1', true);

    const alerts = [];
    if (s.research_errors > 0)
      alerts.push(['RESEARCH TELEMETRIJA JE POKVARENA (' + s.research_errors + ' redova)',
        'Host ce ovaj run odbiti kao invalid_research_telemetry bez obzira na '
        + 'mjerenje. Klikni "Prekini i sacuvaj" i ponovi pokusaj.', false]);
    if (s.stage === 'RUN' && s.phase_index >= 0 && flags.anomaly === '1'
        && alarmForbidden(s.phases[s.phase_index].condition))
      alerts.push(['UREDJAJ JE JOS U ALARMU',
        'U ovoj fazi alarm obara run, a dok traje, sljedeci papiric nema u sta '
        + 'da udje pa se ne broji. Skloni papiric I ruku i odmakni se korak.', true]);
    if (s.stage === 'READY_TO_GO' && s.monitoring_start_allowed)
      alerts.push(['KALIBRACIJA JE GOTOVA -- KLIKNI "2. KRENI SA MJERENJEM"',
        'Server je potvrdio da cijeli plan i sigurnosna rezerva jos staju u '
        + 'hard stop. Nemoj cekati.', true]);
    if (s.stage === 'READY_TO_GO' && !s.monitoring_start_allowed)
      alerts.push(['START JE BLOKIRAN -- CIJELI PLAN VISE NE STAJE U HARD STOP',
        'Ostalo je ' + mmss(s.deadline_remaining) + ', a treba najmanje '
        + mmss(s.monitoring_required_seconds) + '. Prekini i sacuvaj; panel '
        + 'nece pustiti nepotpun run.', false]);
    if (!s.interference_calibrated && s.stage === 'READY_TO_GO')
      alerts.push(['HOLD PRAG NIJE POTVRDJEN',
        'Nedostaje validan INTERFERENCE zapis izveden iz 10 CAL normal-only '
        + 'prozora. Mjerenje je server-side blokirano.', false]);
    if (s.deadline_remaining !== null && s.deadline_remaining < 180)
      alerts.push(['HARD STOP ZA ' + mmss(s.deadline_remaining),
        'Poslije toga se run automatski prekida i pokusaj je potrosen.',
        s.deadline_remaining >= 60]);
    renderAlerts(alerts);

    const dl = document.getElementById('deadline');
    dl.textContent = s.deadline_remaining === null ? ''
      : 'hard stop za ' + mmss(s.deadline_remaining);
    dl.className = (s.deadline_remaining !== null && s.deadline_remaining < 180)
      ? 'warn' : '';

    const b = document.getElementById('banner');
    const ph = document.getElementById('phase');
    const wh = document.getElementById('what');
    b.className = 'card';

    /* Ako telemetrija stane, alat je pao ili je run odbacen. Vodic tada ne
       smije mirno da odbrojava dalje -- to izgleda kao da mjerenje traje. */
    if (s.age_s !== null && s.age_s > 30){
      b.className = 'card act';
      ph.textContent = 'NEMA TELEMETRIJE';
      wh.textContent = 'Alat je stao prije ' + Math.round(s.age_s) +
                       ' s. Mjerenje NE traje. Javi se.';
      document.getElementById('clock').textContent = '!!';
      document.getElementById('total').textContent = '';
      renderPlan(s);
      return;
    }
    if (s.stage === 'RUN' && s.phase_index >= 0){
      const p = s.phases[s.phase_index];
      ph.textContent = 'FAZA ' + (s.phase_index+1) + '/' + s.phases.length
                       + ' · ' + p.name;
      wh.textContent = p.what;
      document.getElementById('clock').textContent = mmss(s.phase_remaining);
      document.getElementById('total').textContent =
        'ukupno ' + mmss(s.elapsed) + ' / ' + mmss(s.total);
      document.getElementById('bar').style.width =
        (100*(1 - s.phase_remaining/p.seconds)).toFixed(1)+'%';
      if (p.condition !== 'normal_baseline' && p.condition !== 'recovery_normal')
        b.className = 'card act';
    } else if (s.stage === 'CAL'){
      ph.textContent = 'KALIBRACIJA';
      wh.textContent = 'Ne prilazi, ne pricaj. ' + (s.cal_progress || '');
      document.getElementById('clock').textContent = '··';
      document.getElementById('total').textContent = '';
      document.getElementById('bar').style.width = '0';
    } else if (s.stage === 'READY_TO_GO'){
      ph.textContent = 'KALIBRACIJA GOTOVA';
      wh.textContent = s.monitoring_start_allowed
        ? 'K1 i normal-only HOLD prag su prošli. Možeš pokrenuti mjerenje.'
        : 'Cijeli plan više ne staje u hard stop. Start je blokiran.';
      document.getElementById('clock').textContent = '00:00';
      document.getElementById('total').textContent = '';
      document.getElementById('bar').style.width = '0';
    } else if (s.stage === 'CAL_REJECTED'){
      b.className = 'card act';
      ph.textContent = 'KALIBRACIJA ODBIJENA';
      wh.textContent = 'K1 nije prošao (' + s.calibration_acceptance_reason +
                       '). Ponovi kalibraciju.';
      document.getElementById('clock').textContent = '!!';
      document.getElementById('total').textContent = '';
      document.getElementById('bar').style.width = '0';
    } else if (s.stage === 'DONE'){
      ph.textContent = 'GOTOVO';
      wh.textContent = 'Run zavrsen. Ventilator mozes ugasiti.';
      document.getElementById('clock').textContent = '00:00';
      document.getElementById('bar').style.width = '100%';
    } else {
      ph.textContent = '—';
      wh.textContent = 'Klikni "Pokreni ucenje" kad ventilator radi normalno';
      document.getElementById('clock').textContent = '--:--';
    }

    renderPlan(s);
    document.getElementById('d-gate').textContent = s.loo_cv_gate;
    document.getElementById('d-cal').textContent = s.cal_progress || '—';
    const cv = document.getElementById('d-cv');
    if (s.loo_cv === null){ cv.textContent = '—'; cv.className=''; }
    else {
      cv.textContent = s.loo_cv.toFixed(3)
        + (s.loo_cv > s.loo_cv_gate ? '  ✗ ponovi' : '  ✓');
      cv.className = s.loo_cv > s.loo_cv_gate ? 'warn' : 'ok';
    }
    document.getElementById('d-thr').textContent =
      s.threshold === null ? '—' : s.threshold.toFixed(1);
    document.getElementById('gobtn').disabled =
      !(s.calibration_accepted && s.interference_calibrated
        && s.monitoring_start_allowed && s.stage === 'READY_TO_GO');
    if(s.read_only_preview){
      document.querySelectorAll('button').forEach(button => button.disabled = true);
      if(s.stage === 'IDLE'){
        ph.textContent = 'PREGLED DASHBOARDA';
        wh.textContent = 'Read-only: tasteri su prikazani, ali su aktivni tek u pravom runu.';
      }
    }
    const d = s.det || {};
    document.getElementById('d-window').textContent = d.window || '—';
    document.getElementById('d-score').textContent =
      d.score ? (d.score + '  /  ' + d.threshold) : '—';
    document.getElementById('d-cons').textContent = d.consecutive || '—';
    document.getElementById('d-level').textContent =
      d.level ? d.level + ' dBFS' : '—';
    document.getElementById('log').textContent = (s.log || []).join('\\n');
  }).catch(()=>{});
}
setInterval(poll, 300); poll();
</script>
"""


def make_handler(state: PanelState, link, conductor: Conductor,
                 csrf_token: str | None = None):
    token = csrf_token or secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # bez pristupnog loga u konzoli
            pass

        def _json(self, payload: dict, code: int = 200) -> None:
            # Standardni JSON nema NaN/Infinity. Ako se ikad provuce nova
            # nefiltrirana vrijednost, endpoint pada vidljivo umjesto da salje
            # browseru nestandardni JavaScript literal.
            body = json.dumps(payload, allow_nan=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path.startswith("/state"):
                self._json(state.snapshot())
                return
            body = PAGE.replace("__CSRF_TOKEN__", token).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if hasattr(self, "headers"):
                host = self.headers.get("Host", "")
                origin = self.headers.get("Origin", "")
                allowed_hosts = {
                    f"127.0.0.1:{self.server.server_address[1]}",
                    f"localhost:{self.server.server_address[1]}",
                }
                if (host not in allowed_hosts or origin not in {
                        f"http://{host}", f"https://{host}"} or
                        self.headers.get("X-CSRF-Token") != token):
                    self._json({"message": "odbijen ne-lokalni ili CSRF zahtjev"}, 403)
                    return
            if state.read_only_preview:
                self._json({"message": "read-only preview: komande su blokirane"}, 409)
                return
            verb = self.path.strip("/").lower()
            try:
                if verb in ("press", "hold"):
                    message = link.send(verb)
                elif verb in ("arm-virtual", "arm-physical"):
                    message = conductor.arm_guided25(
                        virtual_start=verb == "arm-virtual")
                elif verb == "abort":
                    message = conductor.abort()
                elif verb == "pause":
                    raise CalibrationGateError("pauza bi pokvarila vremenski dokaz; koristi prekid")
                elif verb == "start":
                    message = conductor.start()
                else:
                    self._json({"message": "nepoznata komanda"}, 404)
                    return
            except CalibrationGateError as exc:
                self._json({"message": f"greska: {exc}"}, 409)
                return
            except Exception as exc:
                self._json({"message": f"greska: {exc}"}, 500)
                return
            print(message)
            self._json({"message": message})

    return Handler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", help="serijski port (rezim 1: panel drzi port)")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument(
        "--command-file", type=Path,
        help="rezim 2: dopisuj komande za physical_fan_experiment.py",
    )
    parser.add_argument(
        "--follow", type=Path,
        help="rezim 2: serial.log runa iz kojeg se citaju lampice",
    )
    parser.add_argument(
        "--cmd-port",
        help="rezim 2: port na koji idu PRESS/HOLD (npr. COM4), dok alat drzi drugi",
    )
    parser.add_argument("--plan", choices=sorted(PLANS), default="full")
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--http-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--read-only-preview", action="store_true",
        help="prikazi zivu telemetriju, ali server-side blokiraj sve komande",
    )
    parser.add_argument(
        "--preview-auto-stop-seconds", type=int, default=0,
        help="u read-only pregledu automatski oslobodi port poslije N sekundi",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if bool(args.port) == bool(args.command_file):
        print("izaberi tacno jedno: --port (rezim 1) ili --command-file (rezim 2)")
        return 2
    if args.read_only_preview and not args.port:
        print("read-only preview zahtijeva direktni --port")
        return 2
    if args.preview_auto_stop_seconds and not args.read_only_preview:
        print("--preview-auto-stop-seconds vrijedi samo uz --read-only-preview")
        return 2

    state = PanelState(PLANS[args.plan], workflow=args.plan,
                       report_dir=args.run_dir, attempt=args.attempt,
                       read_only_preview=args.read_only_preview)
    if args.port:
        link = SerialLink(state, args.port, args.baud)
    else:
        link = CommandFileLink(state, args.command_file, args.follow,
                               args.cmd_port)
    conductor = Conductor(state, link)
    csrf_token = secrets.token_urlsafe(32)

    url = f"http://127.0.0.1:{args.http_port}/"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.http_port),
                                     make_handler(state, link, conductor, csrf_token))
    except OSError as exc:
        # Bez ovoga stari panel ostane da drzi port, novi tiho umre, a u
        # pregledacu se i dalje vidi ZASTARJELO stanje iz proslog runa --
        # sto je 16.08.2026 dvaput izgledalo kao da uredjaj ne reaguje.
        print(f"port {args.http_port} je zauzet ({exc}).")
        print("Vjerovatno stari panel jos radi. Ugasi ga pa pokreni ponovo, "
              "ili zadaj --http-port drugi broj.")
        return 2
    print(f"panel: {url}   ({state.source}, plan '{args.plan}')")
    if not args.no_browser:
        threading.Timer(0.4, webbrowser.open, args=(url,)).start()
    if args.preview_auto_stop_seconds > 0:
        timer = threading.Timer(args.preview_auto_stop_seconds, server.shutdown)
        timer.daemon = True
        timer.start()
        print(f"read-only preview se automatski zatvara za "
              f"{args.preview_auto_stop_seconds} s")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nzatvaram panel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
