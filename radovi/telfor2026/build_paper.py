"""Gradi TELFOR 2026 rad iz zvanicnog IEEE A4 sablona.

Ne rekonstruise formatiranje rucno: otvara sablon, brise tijelo i puni ga
stilovima koji vec postoje u sablonu (`paper title`, `Author`, `Abstract`,
`Keywords`, `Heading 1..4`, `Body Text`, `table head`, `figure caption`,
`references`).

Pokretanje:
    ..\\..\\.venv\\Scripts\\python.exe build_paper.py
"""

from __future__ import annotations

import copy
import sys
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from rezultati import summary, number
TEMPLATE = HERE / "sablon" / "IEEE_conference_template_a4.docx"
OUTPUT = HERE / "telfor2026_asd_esp32s3.docx"

TODO = "[TODO] "


# sadrzaj rada

BANNER_LEFT = "34th Telecommunications Forum TELFOR 2026"
BANNER_RIGHT = "Serbia, Belgrade, November 24-26, 2026"

TITLE = (
    "Anomalous Sound Detection on an ESP32-S3: "
    "Normal-Only Design and Measured Failure Modes"
)

AUTHORS = "Mihajlo Živković and Ivan Mezei"

AFFIL = [
    "University of Novi Sad, Faculty of Technical Sciences, Novi Sad, Serbia",
    "mihajlo11zivkovic@gmail.com, imezei@uns.ac.rs",
]

ABSTRACT = (
    "This paper evaluates a normal-only anomalous sound detector on an ESP32-S3"
    " with one MEMS microphone. A Welch spectral feature and a Ledoit-Wolf "
    "Mahalanobis score use a local centre learned from ten normal windows. The "
    "deployed ten-window configuration reaches a developmental AUC of 0.856 on "
    "DCASE 2026 fan data. Feature and score computation takes about 716 ms per "
    "10 s window. Field commissioning additionally derives a threshold from 44 "
    "normal windows and verifies it on 22 later windows; the complete sequence "
    "takes about 13.6 min in two recorded trials. The device detects an added "
    "tone and withholds decisions on unstable speech and door windows. The "
    "paper-strip trial detects only one of three prescribed change blocks and "
    "fails its acceptance criteria. Both trials provide valid telemetry, which "
    "is distinct from passing the experiment. Earlier threshold instability and"
    " a rejected robust estimator are reported alongside these results. The "
    "experiments demonstrate on-device execution, but do not establish fault "
    "diagnosis or long-term reliability."
)

KEYWORDS = (
    "Anomalous sound detection, condition monitoring, embedded systems, "
    "ESP32, Mahalanobis distance, unsupervised learning."
)

COPYRIGHT_FOOTER = (
    TODO
    + "IEEE copyright notice - the exact number is issued by the TELFOR "
    "registration system (registration.telfor.rs) and must be inserted here "
    "before submission."
)

# ---- tijelo -------------------------------------------------------------
# ('h1'|'h2'|'p'|'table'|'figure', sadrzaj)

BODY = [
    ("h1", "Introduction"),
    ("p",
     "Monitoring machine condition through sound is attractive because a "
     "microphone is cheap, non-invasive and does not have to touch the "
     "machine. The unsupervised formulation used by the DCASE challenge "
     "series [1]-[3] matches industrial reality: a working machine produces "
     "normal sound continuously while faults are rare, so a detector has to "
     "be fitted on normal sound alone and has to generalise to machines and "
     "operating conditions it has never heard."),
    ("p",
     "Offline AUC measures ranking across thresholds. Deployment additionally "
     "requires a threshold for one installation, checks on audio validity and a "
     "rule for persistent deviations. These decisions must be made without "
     "assuming access to future faults. The present work studies their "
     "implementation and observed limitations on a microcontroller."),
    ("p",
     "The system performs calibration, scoring and alarm decisions on the "
     "ESP32-S3. A PC records telemetry, sends operator commands and, in replay "
     "trials, supplies the acoustic stimulus. Ten windows learn the centre; "
     "threshold derivation and verification follow before monitoring. The "
     "contributions are:"),
    ("p",
     "1) An on-device statistical detector with measured computation cost and "
     "host-to-C checks. 2) A normal-only fitting procedure with separate "
     "threshold derivation and verification. 3) A reliability gate that "
     "withholds decisions on internally unstable high-score windows. 4) Physical"
     " trials with explicit acceptance failures and retained negative results. "
     "These contributions concern a developmental fan detector rather than a "
     "general fault-diagnosis system."),
    ("h1", "System Overview"),
    ("h2", "Hardware and signal path"),
    ("p",
     "The platform is an ESP32-S3 development board at 240 MHz with 16 MB PSRAM, "
     "running ESP-IDF v5.5.5. An INMP441 microphone supplies I2S audio at 16 "
     "kHz, converted to 16-bit mono samples. The intended interface has one "
     "push-button and two LEDs. The recorded trials use a UART virtual button "
     "through the same operator event path; a complete standalone button-and-LED"
     " demonstration remains unverified. Fig. 1 shows the signal path."),
    ("p",
     "The firmware image is 354 784 B including research telemetry. Streaming "
     "processing avoids a 640 kB full-window float buffer. The measured 716 ms "
     "covers feature and score computation per 10 s window, not acquisition, "
     "UART output or alarm latency. The approximately 14× compute margin is not "
     "a worst-case timing guarantee for the full pipeline."),
    ("p",
     "The same C code computes features on the host and on the device. On one "
     "benchmark WAV the host-to-C difference is at most 9.5e-7 feature units, "
     "and on one live microphone capture the host-to-device difference is at "
     "most 1.7e-6. Host results and device results therefore refer to the "
     "same quantity by construction rather than by assumption."),
    ("figure", ("FIG_SYSTEM",
                "Signal path and decision hierarchy. Reliability gating applies to high "
                "scores. Calibration and threshold fitting run on the device; the PC "
                "records telemetry and operator labels.")),
    ("h2", "Feature and model"),
    ("p",
     "The feature uses Welch spectral estimation [4] with 8192-sample periodic "
     "Hann segments and 50 % overlap: 38 complete segments per 10 s window. Band"
     " mean power is mapped through log10 and centred across 96 logarithmic "
     "bands from 10 Hz to 4 kHz. Eight low-frequency bands contain no FFT bin "
     "and receive a fixed log floor before centring, so the implementation is "
     "not exactly invariant to input gain."),
    ("p",
     "Standardisation and a Ledoit-Wolf precision matrix [5] are fitted offline "
     "on 990 source-domain normal clips. The 96×96 float matrix occupies 36 864 "
     "B. On-device calibration collects ten normal windows; up to two may be "
     "rejected by the calibration consistency check before the centre is frozen."
     " For standardised features z, centre c and precision P, the score is the "
     "squared Mahalanobis distance s(x) = (z − c)ᵀ P (z − c)."),
    ("p",
     "The source covariance supplies a prior over normal variation, while the "
     "centre adapts to the installation. Ten-window centre learning reaches AUC "
     "0.8556 ± 0.0240 over 20 development splits. A separate canonical reference"
     " uses 20 calibration windows and 100 splits, reaching 0.8666; it is not "
     "the deployed configuration. Neither comparison is an independent final "
     "test."),
    ("h2", "Operating flow"),
    ("p",
     "The guided profile runs SETTLE, ten centre-learning windows, 44 threshold-"
     "derivation windows and 22 verification windows before MONITORING. The "
     "normal audio alone totals at least 760 s before settling and overhead. "
     "Entry is the empirical higher 99th percentile, equal to the maximum for 44"
     " values. Release is the smaller of p95 and half the entry threshold, "
     "floored at the median; conflicting bounds reject calibration. VERIFY "
     "rejects an alarm, which requires three consecutive high scores, not a "
     "single exceedance. Monitoring also requires three consecutive reliable "
     "high windows. Sustained deviation is emitted at the twelfth measured alarm"
     " window, including entry; HOLD pauses that count."),

    ("h1", "Normal-Only Design Protocol"),
    ("p",
     "Model parameters, calibration centres and thresholds are fitted using "
     "normal recordings only. This data boundary does not imply that the "
     "complete research process was blind to anomalies: results of earlier "
     "labelled and physical trials informed subsequent design choices. The "
     "policies remain developmental."),
    ("p",
     "Versioned JSON policies record fitting data, parameters and limitations. "
     "The evaluator freezes its method list, splits and fitted models before "
     "loading anomaly features for scoring. It rejects anomalous fitting inputs,"
     " overlapping calibration and evaluation cohorts, and incompatible caches. "
     "These checks guard the current computation; they cannot remove bias from "
     "earlier model selection."),

    ("h1", "Fail-Closed Decision Hierarchy"),
    ("p",
     "The runtime separates audio validity, machine presence, reliability and "
     "temporal alarm decisions. Diagnostic scores may still be computed for held"
     " windows; withholding an alarm decision is not the same as omitting all "
     "computation."),
    ("p",
     "The quality gate checks the exact sample count, RMS level, peak, clipped "
     "fraction (at most 1e-3), zero and stuck-sample fractions, and a per-window "
     "dropped-sample delta of exactly zero; it also requires the DC offset, "
     "every metric and every feature to be finite. Any violation stops the "
     "pipeline instead of producing a score, in WAIT, CAL and DET alike. The "
     "presence gate declares the machine present immediately at or above the "
     "calibrated mean minus 11 dB, and declares it stopped only after three "
     "consecutive windows below that level. This separates “machine stopped” "
     "from “machine behaving strangely” — two conditions that a "
     "distance-based score cannot tell apart, since both are far from the "
     "normal centre. Only then is the Mahalanobis score compared against the "
     "threshold, and only then does the temporal rule decide whether the "
     "comparison becomes an alarm."),
    ("p",
     "Invalid audio stops calibration. A separate consistency check may discard "
     "at most two of the ten otherwise valid calibration windows, recomputing "
     "the centre and leave-one-out scores each time. This exception is logged "
     "and must be distinguished from silent replacement of bad audio."),

    ("p",
     "Each 10 s window also yields five sub-window features. For a score above "
     "the entry threshold, excessive disagreement triggers OBSERVATION_HOLD. Its"
     " limit is 1.25 times the largest instability among the ten normal "
     "calibration windows. The gate is conditional on a high score; it does not "
     "reject every internally unstable low-score window."),
    ("p",
     "The gate suspends alarm build-up, but it does not clear an active "
     "alarm and does not modify the learned centre or threshold. It also "
     "makes no claim about the cause of the instability. One microphone "
     "cannot separate speech from an impact or from a change on the "
     "machine, and a system asserting otherwise would be diagnosing "
     "without evidence. Six consecutive held windows raise a warning that "
     "monitoring has been unreliable for some time, which is a claim one "
     "microphone can support."),
    ("h1", "Results"),
    ("p",
     "All benchmark numbers below come from the DCASE 2026 development data "
     "[6] under a leakage-guarded developmental protocol. Table I and the "
     "temporal evaluation are fan-only; the scope comparison covers all seven "
     "machine types. These are not an "
     "independent final validation: the same data guided earlier design "
     "decisions, so historical model-selection bias applies and the figures "
     "should be read as relative comparisons."),
    ("h2", "Feature candidates"),
    ("p",
     "Eight candidates were declared before any of them was run, and each was "
     "evaluated over the same 20 splits. Table I gives the results. Three of "
     "the negative outcomes removed design options and are worth naming."),
    ("table", "T1"),
    ("p",
     "Rotation-order features reach AUC 0.639. The estimated fundamental remains"
     " near 34 Hz across the three labelled speeds, which does not establish "
     "actual shaft speed without a reference tachometer. All three tested dual-"
     "channel variants underperform the first channel. Adding transient features"
     " gives +0.0012 AUC; comparing that difference with an individual standard "
     "deviation is not a paired significance test, so no meaningful advantage is"
     " established."),
    ("h2", "Scope of the front end"),
    ("p",
     "Under a stricter 100-split protocol the same backend was run with two "
     "log-mel front ends. On the fan the PSD shape feature reaches 0.867 "
     "against 0.627 and 0.590; across the other six machine types a log-mel "
     "variant wins on five, with reversals such as 0.448 against 0.539 on "
     "ToyCar and 0.506 against 0.576 on bearing. The front end is "
     "specialised to stationary rotating machinery and we report it as "
     "such. For a device that calibrates itself on one machine and monitors "
     "only that machine the specialisation is a defensible trade; it is not "
     "a general-purpose anomalous sound detection result."),
    ("h2", "Temporal decision rule"),
    ("p",
     "The temporal rule was derived over 40 splits and 2000 normal windows "
     "drawn from held-out normal clips of the same machine. Short "
     "disturbances are synthetic score bumps, so Table II measures the "
     "temporal behaviour of each rule and not acoustic detectability. Clips "
     "of a different physical fan are scored separately as a domain-shift "
     "measure and are never counted as false alarms."),
    ("table", "T2"),
    ("p",
     "In this earlier offline comparison, hysteresis with release at 0.7 times "
     "entry reduced foreign-machine alarm episodes while retaining three-window "
     "latency. No candidate passed every specified criterion. Table II uses "
     "synthetic score perturbations and does not measure speech rejection or "
     "physical detection accuracy. The final firmware retains consecutive-window"
     " hysteresis but uses separately derived absolute entry and release "
     "thresholds."),
    ("h2", "Autonomous operation on the device"),
    ("p",
     "Before a fan was available the device calibrated itself and monitored "
     "with no host in the decision path, a PC only replaying recordings "
     "through a loudspeaker. The clean run covers 107 detection windows over "
     "17.6 min with OK quality verdicts throughout, six windows above the "
     "threshold and no alarm episode, because the longest run above the "
     "threshold was two windows and the rule requires three. The per-window "
     "dropped-sample delta was zero in all 177 measured windows; the "
     "cumulative counter is large only because the ring buffer is not "
     "drained while the device idles waiting for the button, and we make no "
     "claim from it."),
    ("h2", "Trials on a physical fan"),
    ("p",
     "Two final trials use the same firmware image and one fan, with the "
     "microphone 40 cm from the shaft. One applies a hand-held paper strip three"
     " times, then speech and a door disturbance. The other uses a reproduced 1 "
     "kHz tone. Table III uses only protocol-valid, confirmed, non-transition "
     "DET windows: 43/65 and 99/115 respectively. Held windows remain included. "
     "Telemetry validity and experiment acceptance are reported separately. "
     "Neither stimulus is a confirmed fault."),
    ("table", "T3"),
    ("p",
     "Paper-block median scores are 30 255, 62 344 and 19 844 versus baseline "
     "1146, but an alarm appears only in block three. In each of the first two "
     "blocks, three of four eligible windows are held. The GUIDED25 verdict is "
     "FAIL: one of three blocks detected, with a carried alarm in recovery. "
     "Speech and door medians are 38 307 and 49 549, with no alarms in four and "
     "two eligible windows. These short observations do not establish general "
     "noise rejection."),
    ("p",
     "The tone trial produces two alarm episodes and a sustained-deviation "
     "event. Alarm entry follows three reliable high windows; this is not a "
     "measured 30 s delay from initial tone onset. Early tone-labelled windows "
     "remain below threshold. Notes describe a later volume increase, but its "
     "exact time is not recorded. Recovery-labelled scores remain high for much "
     "of the trial and only later fall below entry, without reaching release. "
     "Release latency is therefore unmeasured. Fig. 2 retains all DET windows "
     "for continuity."),
    ("figure", ("FIG_FAN",
                "Score over the tone trial, one point per 10 s window. "
                "The alarm is raised after three consecutive reliable "
                "windows; held windows are excluded from alarm build-up. "
                "Note the logarithmic scale.")),

    ("h1", "Threshold Instability and Revised Commissioning"),
    ("p",
     "Earlier repeated calibration trials expose threshold sensitivity, "
     "with the same board, microphone, audio "
     "source and room produced three calibrations with thresholds of "
     "5687, 347 and 1088. Scoring the windows of run 1 with the threshold "
     "of run 2 puts 92 % of them above it; the reverse leaves 8 % above. "
     "Across the three runs the threshold spans a factor of 16 while the "
     "median score spans a factor of 4.7. The scores were comparatively "
     "stable; the threshold was not."),
    ("p",
     "The earlier estimator used max(Q_0.90, mean + 3 sd) of ten leave-one-out "
     "scores. One outlying window inflated the threshold; a cleaner calibration "
     "underestimated later normal variation. These observations implicate short "
     "calibration and changing acoustics, but do not isolate a single physical "
     "cause."),
    ("p",
     "The revised sequence uses 44 normal derivation windows and 22 later "
     "verification windows. Both final trials pass commissioning, with different"
     " thresholds for their respective sessions. Two accepted sessions cannot "
     "establish calibration repeatability or a low long-term false-alarm rate. "
     "The paper trial still fails its prescribed detection and recovery "
     "criteria."),
    ("p",
     "A robust candidate used the smaller of empirical p99 and median + 3 × "
     "1.4826 × MAD, together with a trimmed centre. Its threshold was 791; later"
     " normal verification scores reached 2083–7766 and commissioning was "
     "rejected. This is evidence that the candidate underestimated variation in "
     "that session. Changing both centre and threshold also prevents attributing"
     " the failure to either component alone. The candidate remains outside the "
     "live firmware path."),
    ("p",
     "The consistency check remains sensitive to narrow-band changes under the "
     "source-domain covariance. Trimming up to two calibration windows improves "
     "acceptance in one final trial, but does not establish robustness across "
     "installations. Eight empty spectral bands and source-to-device covariance "
     "mismatch are candidates for future investigation; changing them would "
     "require retraining and new validation."),

    ("h1", "Conclusion"),
    ("p",
     "A statistical detector executes on the ESP32-S3 with 716 ms of measured "
     "feature-and-score computation per 10 s window and a 355 kB image. It "
     "learns a local centre and derives and verifies alarm thresholds from "
     "normal audio. Its recorded decisions can be checked against retained "
     "telemetry."),
    ("p",
     "The tone experiment demonstrates sustained-change signalling. The paper-"
     "strip experiment detects one of three blocks and fails its acceptance "
     "criteria; speech and door blocks produce no alarms in this short record. "
     "Threshold repeatability, recovery after a strong stimulus, independent "
     "machines and full-pipeline power remain open. Controlled perturbations are"
     " not confirmed mechanical faults."),
    ("h1ack", "Acknowledgment"),
    ("p", "OpenAI Codex assisted with drafting and revising Sections I–VII and "
     "checking tables against recorded project data. Experimental values "
     "come from the retained measurement artifacts."),
]

REFERENCES = [
    "N. Harada, D. Niizumi, Y. Ohishi, D. Takeuchi, and M. Yasuda, "
    "“First-shot anomaly sound detection for machine condition monitoring: A "
    "domain generalization baseline,” in Proc. 31st European Signal "
    "Processing Conf. (EUSIPCO), 2023, pp. 191-195, doi: "
    "10.23919/EUSIPCO58844.2023.10289721.",
    "N. Harada et al., “ToyADMOS2: Another dataset of miniature-machine "
    "operating sounds for anomalous sound detection under domain shift "
    "conditions,” in Proc. DCASE Workshop, Barcelona, Spain, Nov. 2021, "
    "pp. 1-5, doi: 10.5281/zenodo.5770113.",
    "K. Dohi et al., “MIMII DG: Sound dataset for malfunctioning "
    "industrial machine investigation and inspection for domain "
    "generalization task,” in Proc. DCASE Workshop, Nancy, France, "
    "Nov. 2022, pp. 1-5.",
    "P. D. Welch, “The use of the fast Fourier transform for the "
    "estimation of power spectra: A method based on time averaging over "
    "short, modified periodograms,” IEEE Trans. Audio Electroacoust., "
    "vol. 15, no. 2, pp. 70-73, Jun. 1967, doi: "
    "10.1109/TAU.1967.1161901.",
    "O. Ledoit and M. Wolf, “A well-conditioned estimator for "
    "large-dimensional covariance matrices,” J. Multivariate Anal., "
    "vol. 88, no. 2, pp. 365-411, Feb. 2004, doi: "
    "10.1016/S0047-259X(03)00096-4.",
    "T. Nishida et al., “Description and discussion on DCASE 2026 "
    "Challenge Task 2: Noise-aware unsupervised anomalous sound detection "
    "for machine condition monitoring,” arXiv:2606.01578, 2026.",
]

# ---- tabele -------------------------------------------------------------

TABLES = {
    "T1": {
        "caption": "Feature Candidates, DCASE 2026 Dev Fan, k = 10, 20 Splits",
        "widths": [2.9, 2.2, 1.5, 1.7],
        "head": ["Candidate", "AUC", "pAUC (p=0.1)", "Δ AUC"],
        "rows": [
            ["psd_shape (baseline)", "0.8556 ± 0.0240", "0.6393", "-"],
            ["psd_order (rotation order)", "0.6388 ± 0.0467", "0.5171", "-0.2168"],
            ["psd_regime", "0.8556 ± 0.0240", "0.6393", "0.0000"],
            ["psd_logratio (dual mic)", "0.7185 ± 0.0347", "0.5848", "-0.1371"],
            ["psd_coherence (dual mic)", "0.7506 ± 0.0398", "0.5774", "-0.1050"],
            ["psd_masked (dual mic)", "0.4500 ± 0.0645", "0.4884", "-0.4056"],
            ["transient", "0.5647 ± 0.0267", "0.5062", "-0.2909"],
            ["psd_plus_transient", "0.8568 ± 0.0258", "0.6433", "+0.0012"],
        ],
        "note": None,
    },
    "T2": {
        "caption": "Temporal Decision Rules, 40 Splits, 2000 Normal Windows",
        "widths": [2.3, 1.5, 1.6, 1.5, 1.4],
        "head": ["Rule", "False alarms /h", "Foreign machine /h",
                 "Alarm on 1 window", "Latency (win.)"],
        "rows": [
            ["3 consecutive", "0.00", "11.16", "0.004", "3"],
            ["4 consecutive", "0.00", "10.98", "0.000", "4"],
            ["Hysteresis 1.0/0.7, n = 3", "0.00", "5.40", "0.000", "3"],
            ["EWMA (0.4), n = 3", "5.40", "6.48", "0.592", "3"],
            ["CUSUM k = 0.5, h = 2", "5.40", "11.16", "0.721", "1"],
        ],
        "note": "The selected rule is set in bold. Short disturbances are "
                "synthetic score bumps and probe the rule, not acoustic "
                "detectability.",
        "bold_row": 2,
    },
    "T3": {
        "caption": "Physical Fan Trials, Same Firmware Image",
        "widths": [3.2, 2.5, 2.6],
        "head": ["Measurement", "Paper strip", "Constant tone"],
        "rows": [
            ["Calibration accepted", "yes, 2 clips trimmed", "yes, no trim"],
            ["Leave-one-out CV", "0.84 -> 0.43", "0.43"],
            ["Entry / release threshold", "8084 / 3707", "21 810 / 10 905"],
            ["Normal baseline, median score", "1146", "7085"],
            ["Induced change, median score", "19 844–62 344", "23 574"],
            ["DET total / eligible", "65 / 43", "115 / 99"],
            ["Alarm windows / episodes", "3 / 2", "64 / 2"],
            ["Entry rule", "3 reliable high windows", "3 reliable high windows"],
            ["Median release latency", "10.1 s", "not measured"],
            ["Speech / door response", "no alarm, windows held", "not applied"],
            ["Sustained-deviation event", "no", "yes, at 12th alarm window"],
            ["Per-window dropped samples", "0", "0"],
        ],
        "note": "Counts use eligible windows, including HOLD. Paper trial: GUIDED25 FAIL (1/3 blocks; carried alarm). Tone onset latency and final release latency are unmeasured.",
    },
}


# physical counts and medians use the same filter as the thesis
_paper, _tone = summary("paper"), summary("tone")
_pg, _tg = _paper["groups"], _tone["groups"]
_change = [_pg[f"airflow_change_paper_{i}"]["median"] for i in (1, 2, 3)]
_rows = TABLES["T3"]["rows"]
_rows[3][1:] = [number(_pg["normal_baseline"]["median"]), number(_tg["normal_baseline"]["median"])]
_rows[4][1:] = [f"{number(min(_change))}–{number(max(_change))}", number(_tg["constant_tone_1khz"]["median"])]
_rows[5][1:] = [f"{r['raw']} / {r['eligible']}" for r in (_paper, _tone)]

# Slike koje postoje kao fajl (pravi se u make_figures.py). Ostale su okviri
# koji rezervisu stvarnu visinu dok se sadrzaj ne napravi.
FIGURE_FILES = {
    "FIG_SYSTEM": "slike/fig1_system.png",
    "FIG_RUN": "slike/fig2_device_run.png",
    "FIG_THRESHOLD": "slike/fig3_threshold.png",
    "FIG_FAN": "slike/fig5_fan_tone.png",
}
FIGURE_WIDTH_CM = 8.3

FIGURE_HEIGHT_CM = {}
FIGURE_PLACEHOLDER = {
}


# pomocne funkcije za OOXML

def unnumber(paragraph):
    """Uklanja automatsku numeraciju stila (npr. rimski broj uz Heading 1)."""
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = p_pr.makeelement(qn("w:numPr"), {})
    ilvl = num_pr.makeelement(qn("w:ilvl"), {qn("w:val"): "0"})
    num_id = num_pr.makeelement(qn("w:numId"), {qn("w:val"): "0"})
    num_pr.append(ilvl)
    num_pr.append(num_id)
    p_pr.append(num_pr)
    return paragraph


def _borders(el_parent, tag, edges, val, sz, color, space="0"):
    borders = el_parent.makeelement(qn(tag), {})
    for edge in edges:
        el = borders.makeelement(qn(f"w:{edge}"), {})
        el.set(qn("w:val"), val.get(edge, "none"))
        el.set(qn("w:sz"), str(sz if val.get(edge, "none") != "none" else 0))
        el.set(qn("w:space"), space)
        el.set(qn("w:color"), color)
        borders.append(el)
    el_parent.append(borders)


def _tight_cells(table):
    """Uklanja vertikalni padding celija; IEEE tabele su zbijene."""
    tbl_pr = table._tbl.tblPr
    mar = tbl_pr.makeelement(qn("w:tblCellMar"), {})
    for edge, val in (("top", 0), ("bottom", 0), ("left", 57), ("right", 57)):
        el = mar.makeelement(qn(f"w:{edge}"), {})
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tbl_pr.append(mar)


def _fixed_layout(table, widths_cm):
    tbl_pr = table._tbl.tblPr
    layout = tbl_pr.makeelement(qn("w:tblLayout"), {qn("w:type"): "fixed"})
    tbl_pr.append(layout)
    table.autofit = False
    for row in table.rows:
        for cell, w in zip(row.cells, widths_cm):
            cell.width = Cm(w)


def _keep_rows_together(table):
    """Cijela tabela ostaje na jednoj strani i redovi se ne cijepaju."""
    for r, row in enumerate(table.rows):
        tr_pr = row._tr.get_or_add_trPr()
        tr_pr.append(tr_pr.makeelement(qn("w:cantSplit"), {}))
        if r < len(table.rows) - 1:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True


def add_table(doc, spec):
    cap = doc.add_paragraph(style="table head")
    cap.text = spec["caption"]
    cap.paragraph_format.keep_with_next = True

    head = spec["head"]
    rows = spec["rows"]
    widths = spec["widths"]
    table = doc.add_table(rows=len(rows) + 1, cols=len(head))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(table._tbl.tblPr, "w:tblBorders",
             ("top", "left", "bottom", "right", "insideH", "insideV"),
             {"top": "single", "bottom": "single", "insideH": "single"},
             6, "000000")
    _tight_cells(table)
    _fixed_layout(table, widths)

    for j, text in enumerate(head):
        cell = table.cell(0, j)
        cell.text = ""
        p = cell.paragraphs[0]
        p.style = doc.styles["table col head"]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(7.5)

    bold_row = spec.get("bold_row")
    for i, row in enumerate(rows):
        for j, text in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.text = ""
            p = cell.paragraphs[0]
            p.style = doc.styles["table copy"]
            run = p.add_run(text)
            run.font.size = Pt(7.5)
            if bold_row is not None and i == bold_row:
                run.bold = True
            if j > 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    _keep_rows_together(table)

    if spec.get("note"):
        # Sablon ima namjenski stil za napomenu ispod tabele.
        note = doc.add_paragraph(style="table footnote")
        note.alignment = WD_ALIGN_PARAGRAPH.LEFT
        note.paragraph_format.space_before = Pt(2)
        note.paragraph_format.space_after = Pt(6)
        run = note.add_run(spec["note"])
        run.font.size = Pt(7)
        run.italic = True
    else:
        doc.add_paragraph(style="Body Text")


def add_figure(doc, key, caption):
    """Ubacuje pravu sliku ako fajl postoji, inace okvir sa rezervisanom visinom."""
    if key in FIGURE_FILES:
        path = HERE / FIGURE_FILES[key]
        if not path.exists():
            raise FileNotFoundError(
                f"{path} ne postoji — pokreni prvo make_figures.py")
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(str(path), width=Cm(FIGURE_WIDTH_CM))
        cap = doc.add_paragraph(style="figure caption")
        cap.text = caption
        doc.add_paragraph(style="Body Text")
        return

    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(table._tbl.tblPr, "w:tblBorders",
             ("top", "left", "bottom", "right", "insideH", "insideV"),
             {"top": "dashed", "bottom": "dashed",
              "left": "dashed", "right": "dashed"},
             6, "808080", space="4")
    _fixed_layout(table, [8.3])

    row = table.rows[0]
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(tr_pr.makeelement(qn("w:cantSplit"), {}))
    height = tr_pr.makeelement(
        qn("w:trHeight"),
        {qn("w:val"): str(int(FIGURE_HEIGHT_CM[key] * 567)),
         qn("w:hRule"): "exact"},
    )
    tr_pr.append(height)

    p = table.cell(0, 0).paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    run = p.add_run(FIGURE_PLACEHOLDER[key])
    run.font.size = Pt(7.5)
    run.italic = True

    cap = doc.add_paragraph(style="figure caption")
    cap.text = caption
    doc.add_paragraph(style="Body Text")


# gradnja dokumenta

def build():
    doc = Document(str(TEMPLATE))

    # IEEE sablon nosi svoja svojstva: naslov "Paper Title (use style: paper
    # title)", autor "IEEE", posljednji urednik "Leonid". Bez ovoga zavrse u
    # svojstvima naseg .docx-a i u PDF-u koji Word izveze iz njega.
    sada = datetime.now()
    cp = doc.core_properties
    cp.title = TITLE
    cp.author = AUTHORS
    cp.last_modified_by = AUTHORS
    cp.keywords = KEYWORDS
    cp.comments = ""
    cp.subject = ""
    cp.category = ""
    cp.created = sada
    cp.modified = sada
    cp.revision = 1
    # Zadrzi IEEE tipografiju, ali ukloni malo suvisnog vertikalnog razmaka
    # kako dopunjeni tekst i reference ostaju unutar ogranicenja od 4 strane.
    doc.styles["Body Text"].paragraph_format.space_after = Pt(5)
    doc.styles["figure caption"].paragraph_format.space_after = Pt(8)
    doc.styles["references"].paragraph_format.space_after = Pt(1)
    body = doc.element.body

    inline_sect_prs = body.xpath("./w:p/w:pPr/w:sectPr")
    final_sect_pr = body.xpath("./w:sectPr")[0]
    title_sect_pr = copy.deepcopy(inline_sect_prs[0])      # 1 kolona, naslov
    body_sect_pr = copy.deepcopy(inline_sect_prs[-1])      # 2 kolone, tijelo

    for child in list(body):
        body.remove(child)

    # --- naslovni blok, jedna kolona ---
    banner = doc.add_paragraph()
    banner.paragraph_format.tab_stops.add_tab_stop(
        Cm(17.8), WD_TAB_ALIGNMENT.RIGHT)
    banner.paragraph_format.space_after = Pt(10)
    r = banner.add_run(f"{BANNER_LEFT}\t{BANNER_RIGHT}")
    r.font.size = Pt(9)

    title = doc.add_paragraph(style="paper title")
    title.text = TITLE

    authors = doc.add_paragraph(style="Author")
    authors.text = AUTHORS
    for line in AFFIL:
        p = doc.add_paragraph(style="Author")
        p.text = line
        for run in p.runs:
            run.font.size = Pt(9)

    closer = doc.add_paragraph()
    closer.paragraph_format.space_after = Pt(0)
    closer._p.get_or_add_pPr().append(title_sect_pr)

    # --- tijelo, dvije kolone ---
    abstract = doc.add_paragraph(style="Abstract")
    r = abstract.add_run("Abstract—")
    r.bold = True
    r.italic = True
    abstract.add_run(ABSTRACT)

    kw = doc.add_paragraph(style="Keywords")
    r = kw.add_run("Keywords—")
    r.bold = True
    r.italic = True
    kw.add_run(KEYWORDS)

    for kind, payload in BODY:
        if kind == "h1":
            doc.add_paragraph(payload, style="Heading 1")
        elif kind == "h1ack":
            unnumber(doc.add_paragraph(payload, style="Heading 1"))
        elif kind == "h2":
            doc.add_paragraph(payload, style="Heading 2")
        elif kind == "p":
            doc.add_paragraph(payload, style="Body Text")
        elif kind == "table":
            add_table(doc, TABLES[payload])
        elif kind == "figure":
            key, caption = payload
            add_figure(doc, key, caption)

    unnumber(doc.add_paragraph("References", style="Heading 1"))
    for ref in REFERENCES:
        p = doc.add_paragraph(style="references")
        p.text = ref

    # balance the final page without changing the two-column body
    body.append(body_sect_pr)
    doc.add_section(WD_SECTION.CONTINUOUS)

    # --- copyright u podnozju prve strane ---
    section = doc.sections[1]
    section.different_first_page_header_footer = True
    footer = section.first_page_footer
    fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = fp.add_run(COPYRIGHT_FOOTER)
    run.font.size = Pt(8)

    doc.save(str(OUTPUT))
    return OUTPUT


if __name__ == "__main__":
    out = build()
    print(f"saved: {out}")
