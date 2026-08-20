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
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "sablon" / "IEEE_conference_template_a4.docx"
OUTPUT = HERE / "telfor2026_asd_esp32s3.docx"

TODO = "[TODO] "


# --------------------------------------------------------------------------
# sadrzaj rada
# --------------------------------------------------------------------------

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
    "Anomalous sound detection for machine condition monitoring is almost "
    "always evaluated as an offline benchmark. This paper reports what changes "
    "when the same statistical detector is moved onto a microcontroller and "
    "required to calibrate itself, in the field, on one machine, from normal "
    "sound only. The device is an ESP32-S3 with a single MEMS microphone: a "
    "Welch power spectral density front end, a Ledoit-Wolf Mahalanobis score, "
    "and a local centre learned in about 115 s from ten calibration windows. "
    "Every operating policy - audio quality gate, machine-presence gate, "
    "temporal decision rule and threshold - is derived without reading a "
    "single anomalous recording. With ten calibration windows, we report a "
    "developmental AUC of 0.856 on the DCASE 2026 fan data, 704 ms of "
    "computation per 10 s window, and zero observed alarm episodes during "
    "17.6 min of on-device monitoring. A PC supplied only the loudspeaker "
    "audio stimulus and took no part in inference or decisions. We also "
    "report three measured negative results and one open failure mode: the "
    "calibrated threshold varies by a factor of 16 across repeated "
    "calibrations of the same machine in the same room, which dominates every "
    "downstream figure, the false-alarm rate included."
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
     "That formulation is nearly always evaluated offline. A model is fitted "
     "on a workstation, scored against a labelled test set, and reported as "
     "an area under the ROC curve. The deployment questions stay outside the "
     "loop, and they are not small ones. A device installed next to one "
     "machine has to decide by itself whether the machine is running at all; "
     "whether the audio it has just captured can be trusted; which score is "
     "high enough to be called an anomaly; and how long a deviation has to "
     "persist before anyone is told about it. None of those questions can be "
     "answered with anomalous recordings, because the installation does not "
     "have any."),
    ("p",
     "This paper reports what happened once those questions had to be "
     "answered on the device. The system is a self-contained detector on an "
     "ESP32-S3 "
     "microcontroller with a single MEMS microphone. An operator presses one "
     "button, the device listens to the machine for about 115 s, learns its "
     "normal sound, and monitors it from then on. In the reported bench run, "
     "a PC only replayed the audio stimulus through a loudspeaker; calibration, "
     "inference and decisions remained entirely on the device. The "
     "contributions are:"),
    ("p",
     "1) A complete self-calibrating detector: 704 ms of computation per 10 s "
     "window, a 14.2x real-time margin, 316 kB of firmware and no neural "
     "network. 2) A normal-only design protocol under which every operating "
     "policy is derived, versioned and frozen before any anomalous recording "
     "is read. 3) A fail-closed decision hierarchy in which the device "
     "refuses to produce a score on untrustworthy input instead of producing "
     "a wrong one. 4) Measurements, including three negative results that "
     "removed design options, and one open failure mode: the calibrated "
     "threshold varies by a factor of 16 across repeated calibrations of the "
     "same machine in the same room, and that variation dominates every "
     "downstream number."),
    ("h1", "System Overview"),
    ("h2", "Hardware and signal path"),
    ("p",
     "The platform is an ESP32-S3-WROOM-1 N32R16V (240 MHz dual core, 16 MB "
     "PSRAM) running ESP-IDF v5.5.5. Audio arrives from one INMP441 MEMS "
     "microphone over I2S at 16 kHz, 16 bit, mono. A push-button starts "
     "calibration and two LEDs report the device state, so the complete user "
     "interface is one button and two lamps. Fig. 1 shows the whole chain, "
     "from the microphone to the alarm."),
    ("p",
     "The firmware image is 316 400 B and leaves 92 % of the application "
     "partition free; static RAM use is 293 kB of the 342 kB internal DIRAM. "
     "The front end is computed in streaming fashion, hop by hop, avoiding "
     "the approximately 640 kB full-window float buffer that a 10 s recording "
     "would require, and its result is identical to the batch computation. "
     "One 10 s window "
     "takes 704 ms end to end, feature and score together, which is a 14.2x "
     "real-time margin."),
    ("p",
     "An INA226 shunt monitor on the 3.3 V rail gives 34.7 mA at 3.43 V, or "
     "119 mW, in the lowest active state: 240 MHz, PSRAM on, radios off, no "
     "audio and no scoring. "
     + TODO +
     "the complete pipeline has not been measured; this is a floor, not an "
     "operating figure."),
    ("p",
     "The same C code computes features on the host and on the device. On one "
     "benchmark WAV the host-to-C difference is at most 9.5e-7 feature units, "
     "and on one live microphone capture the host-to-device difference is at "
     "most 1.7e-6. Host results and device results therefore refer to the "
     "same quantity by construction rather than by assumption."),
    ("figure", ("FIG_SYSTEM",
                "Signal path and decision hierarchy. Bold outlines mark the "
                "gates that stop the pipeline instead of producing a score. "
                "The threshold and the local centre come from the on-site "
                "calibration, never from a host.")),
    ("h2", "Feature and model"),
    ("p",
     "The feature is a Welch power spectral density estimate [4] with an "
     "8192-sample segment and 50 % overlap, reduced to 96 logarithmically "
     "spaced bands between 10 Hz and 4 kHz on a logarithmic magnitude scale, "
     "with the mean level subtracted. Subtracting the mean turns the feature "
     "into a spectral shape rather than a loudness measurement, which matters "
     "because microphone distance is not controlled in the field."),
    ("p",
     "The statistical model is deliberately split in two. A per-dimension "
     "standardisation and a Ledoit-Wolf shrinkage precision matrix [5] are "
     "estimated once, on the host, from 990 normal source-domain clips; the "
     "96x96 matrix occupies 36 864 B in flash. Only the local centre, the "
     "arithmetic mean of ten calibration windows, is learned on the deployed "
     "machine. Writing z for the standardised feature, c for that local centre "
     "and P for the precision matrix, the firmware computes the squared "
     "Mahalanobis score s(x) = (z − c)ᵀ P (z − c)."),
    ("p",
     "This split is what makes field calibration feasible. The precision "
     "matrix is the part that needs a large amount of data; the centre is the "
     "part that has to be local. About 115 s of listening is enough for a "
     "centre and nowhere near enough for a covariance in 96 dimensions. This "
     "ten-window configuration is the deployed and demonstrated setting and "
     "reaches an AUC of 0.8556 ± 0.0240 over 20 development splits. A "
     "separate 100-split canonical reference with 20 calibration windows "
     "reaches an AUC of 0.8666 and is not the deployed configuration."),
    ("h2", "Operating flow"),
    ("p",
     "The device moves through three states. In WAIT it idles and the green "
     "LED blinks briefly every 2 s. A button press starts CAL: ten 10 s "
     "windows of the machine running normally, about 115 s in total, during "
     "which the LED blinks at 5 Hz and the machine must not be touched. The "
     "LED then turns solid and the device enters DET, where it scores every "
     "window and raises an alarm only after three consecutive windows above "
     "the threshold, roughly 30 s of sustained change. The alarm is released "
     "once the score falls below 0.7 times the threshold."),

    ("h1", "Normal-Only Design Protocol"),
    ("p",
     "The rule we imposed on ourselves is that any policy shipped to the "
     "device must be derivable from normal data alone, because a deployed "
     "device has nothing else. This is stronger than avoiding test-set "
     "leakage: it forbids using anomalies even to choose a constant."),
    ("p",
     "The rule is enforced mechanically. The quality, presence and temporal "
     "policies each live in a versioned JSON file recording the derivation "
     "data, the decision statistic, the measured properties, the stated "
     "limitation, and a change rule requiring fresh normal-only evidence "
     "before any anomaly data are touched. In the evaluator, anomalous clips "
     "are loaded only in the final scoring stage, after the method list, the "
     "splits, the preprocessing, the global model and the calibration "
     "protocol are frozen. The evaluator stops if an anomaly reaches a "
     "fitting or calibration cohort, if calibration and held-out sets "
     "overlap, or if a feature cache was produced by different code."),
    ("p",
     "The constraint changes what may be tuned, sometimes in ways that are "
     "easy to miss. The presence gate margin of 11 dB had to be derived from "
     "within-clip window variation only: the benchmark clips are "
     "level-normalised, so the standard deviation of level across 60 target "
     "normal clips is 0.02 dB. That figure is a dataset artefact, not "
     "physical variation, and using it would have produced a margin with no "
     "physical meaning."),

    ("h1", "Fail-Closed Decision Hierarchy"),
    ("p",
     "A benchmark script always receives a well-formed clip. A device does "
     "not, so scoring is the third of four ordered stages and never the "
     "first."),
    ("p",
     "The quality gate checks the exact sample count, RMS level, peak, clipped "
     "fraction (at most 1e-3), zero and stuck-sample fractions, and a per-window "
     "dropped-sample delta of exactly zero; it also requires the DC offset, "
     "every metric and every feature to be finite. Any violation stops the "
     "pipeline instead of producing a score, in WAIT, CAL and DET alike. The "
     "presence gate declares the machine present immediately at or above the "
     "calibrated mean minus 11 dB, and declares it stopped only after three "
     "consecutive windows below that level. This separates “machine stopped” "
     "from “machine behaving strangely” - two conditions that a "
     "distance-based score cannot tell apart, since both are far from the "
     "normal centre. Only then is the Mahalanobis score compared against the "
     "threshold, and only then does the temporal rule decide whether the "
     "comparison becomes an alarm."),
    ("p",
     "The calibration itself is fail-closed as well. A rejected window does "
     "not get replaced silently; calibration stops and the operator repeats "
     "it. We prefer a device that refuses to arm over a device that arms on "
     "ten windows of which two were noise."),

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
     "First, explicit rotation-order features collapse to 0.639. The reason "
     "is visible in the normal data alone: the median fundamental is 34 Hz at "
     "all three labelled speeds, and the dominant spectral peaks of the three "
     "speeds coincide to within one FFT bin (1.95 Hz). The labelled operating "
     "speeds are not separable from the spectrum, so a feature built on them "
     "carries no information the shape feature does not already have."),
    ("p",
     "Second, all three dual-microphone variants are worse than the single "
     "channel, and the spatial-mask variant reaches 0.450, below chance. The "
     "shipped device therefore uses one microphone. That is a measured "
     "decision rather than a cost decision, since the second microphone was "
     "already available."),
    ("p",
     "Third, adding a transient channel yields +0.0012 AUC against a "
     "split-to-split standard deviation of 0.024, which is nothing. It was "
     "dropped, keeping the front end at one branch."),
    ("h2", "Scope of the front end"),
    ("p",
     "Under a second, stricter protocol with 100 calibration splits, the same "
     "backend was run with two log-mel front ends for comparison. On the fan, "
     "the PSD shape feature reaches 0.867 against 0.627 for a 1280-dimensional "
     "log-mel front end and 0.590 for a 256-dimensional one. Across the other "
     "six machine types, a log-mel variant wins on five; sliderEmu is the "
     "exception, where PSD reaches 0.585 against 0.559 for the best log-mel "
     "variant. Examples of the reversal are 0.448 against 0.539 on ToyCar, "
     "0.506 against 0.576 on bearing and 0.544 against 0.611 on gearbox. The "
     "front end is specialised to stationary rotating machinery "
     "and we report it as such. For a device that calibrates itself on one "
     "machine and monitors only that machine, specialisation is a defensible "
     "trade; it is not a general-purpose anomalous sound detection result, "
     "and should not be read as one."),
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
     "The selected rule, hysteresis with entry at the threshold, release at "
     "0.7 times the threshold and three consecutive windows, gives no false "
     "alarms, no response at all to a single disturbed window, and roughly "
     "half the response to a foreign machine that the plain three-window rule "
     "gives, at the same detection latency. No candidate satisfied the strict "
     "criterion of zero false alarms and zero response to short disturbances "
     "and no missed sustained shift; we report that as a rejected criterion "
     "rather than relaxing it silently. One reason is structural: a disturbed "
     "window next to one already above the threshold can complete a run of "
     "three, and no consecutive-window rule can exclude that. The other "
     "reason is the threshold itself, the subject of Section VI."),
    ("h2", "Autonomous operation on the device"),
    ("p",
     "The device then calibrated itself and monitored without a host in the "
     "decision path; the PC only supplied the recording replayed through a "
     "loudspeaker. The clean run covers 20 min: 177 measured audio windows "
     "with OK quality verdicts plus one calibration-summary record, 107 "
     "detection windows over 17.6 min, six windows above the threshold (5.6 %), "
     "and zero observed alarm episodes during that exposure. Fig. 2 shows the "
     "whole run. Those six windows "
     "are exactly why the temporal rule exists: without it they would have "
     "been six alarms in 17.6 min, and with it none, because the longest run "
     "above the threshold was two windows and the rule requires three."),
    ("figure", ("FIG_RUN",
                "Mahalanobis score over the clean autonomous run, one point "
                "per 10 s window. Six windows cross the threshold, but never "
                "three in a row, so no alarm is raised.")),
    ("p",
     "One measurement detail must not be compressed. The cumulative "
     "dropped-sample counter reads 122 880 at the end of calibration, but "
     "those samples are dropped while the device idles waiting for the button "
     "and nobody drains the ring buffer. The measured quantity is the "
     "per-window delta, which was zero in all 177 windows; that is the only "
     "claim we make."),
    ("h2", "Trial on a physical fan"),
    ("p",
     "All results above use recordings replayed through a loudspeaker; none "
     "was measured on a physically running fan. Table III defines the later "
     "physical trial. A reversible change - an airflow obstruction or "
     "removable tape on one blade - will be applied so both detection and "
     "recovery can be measured."),
    ("table", "T3"),
    ("figure", ("FIG_PHOTO",
                "Measurement setup: ESP32-S3 board, INMP441 microphone, "
                "button and status LEDs, positioned in front of the fan "
                "under test.")),

    ("h1", "Threshold Instability"),
    ("p",
     "The same board, the same microphone, the same audio source and the same "
     "room produced three calibrations with thresholds of 5687, 347 and 1088. "
     "Fig. 4 shows all three runs on one scale. In the first run none of the "
     "observed normal-operation windows crossed the threshold, indicating an "
     "insensitive calibration in that run. In the contaminated second run, "
     "91 % of windows crossed it and the observed alarm-episode rate was 8.69 "
     "per hour; this is not a clean false-alarm-rate estimate. "
     "Run 2 was contaminated by computing load on the machine playing the "
     "audio; run 3 repeats it on an unloaded machine and is the reference "
     "measurement."),
    ("figure", ("FIG_THRESHOLD",
                "Three calibrations of the same machine in the same room. "
                "The score distributions overlap; the thresholds derived from "
                "them span a factor of 16 while the median score spans a "
                "factor of 4.7. Note the logarithmic scale.")),
    ("p",
     "A cross-check settles what varies. Scoring the windows of run 1 with "
     "the threshold of run 2 puts 92 % of them above it; scoring the windows "
     "of run 2 with the threshold of run 1 leaves 8 % above it. Across the "
     "three runs the threshold spans a factor of 16 while the median score "
     "spans a factor of 4.7, and part of even that is the contamination of "
     "run 2. The scores are comparatively stable; the threshold is not."),
    ("p",
     "The mechanism is the estimator. For the ten leave-one-out calibration "
     "scores l_i, the threshold is τ = max(Q_0.90({l_i}), mean({l_i}) + "
     "3 sd({l_i})). In run 1 a single calibration "
     "window stood out (leave-one-out maximum 5430 against a median of about "
     "384.6) and the standard deviation carried the threshold to 5687. In run 2 "
     "the calibration was clean, standard deviation 60 and threshold 347, "
     "while the normal operation that followed had a standard deviation of "
     "8557: the leave-one-out estimate understated the future spread by two "
     "orders of magnitude. Ten windows recorded back to back do not represent "
     "how much normal operation varies later."),
    ("p",
     "The practical consequence is that a false-alarm rate is not a property "
     "of this detector unless the threshold that produced it is reported "
     "alongside. The fix is not a different constant. It requires a robust "
     "normal-only threshold estimator, derived under the same protocol as the "
     "other policies, and calibration long enough to span the machine's own "
     "regimes. That work is open."),

    ("h1", "Conclusion"),
    ("p",
     "A statistical anomalous sound detector fits comfortably on an ESP32-S3: "
     "704 ms per 10 s window, 316 kB of firmware, one microphone, one button, "
     "and a field calibration of about 115 s. Every operating policy was "
     "derived from normal sound alone, and the decision hierarchy fails "
     "closed rather than scoring untrustworthy audio."),
    ("p",
     "Threshold stability, not benchmark AUC, limits the system. A factor-16 "
     "change across calibrations far exceeds the score changes, so zero alarm "
     "episodes in 17.6 min describes one calibration and a short exposure, "
     "not detector-wide reliability. Remaining work is the physical fan trial, "
     "full-pipeline power and a robust normal-only threshold."),
]

REFERENCES = [
    "N. Harada, D. Niizumi, Y. Ohishi, D. Takeuchi, and M. Yasuda, "
    "“First-shot anomaly sound detection for machine condition monitoring: A "
    "domain generalization baseline,” in Proc. 31st European Signal "
    "Processing Conf. (EUSIPCO), 2023, pp. 191-195, doi: "
    "10.23919/EUSIPCO58844.2023.10289721.",
    "N. Harada, D. Niizumi, D. Takeuchi, Y. Ohishi, M. Yasuda, and S. Saito, "
    "“ToyADMOS2: Another dataset of miniature-machine operating sounds "
    "for anomalous sound detection under domain shift conditions,” in "
    "Proc. DCASE Workshop, Barcelona, Spain, Nov. 2021, pp. 1-5, doi: "
    "10.5281/zenodo.5770113.",
    "K. Dohi, T. Nishida, H. Purohit, R. Tanabe, T. Endo, M. Yamamoto, "
    "Y. Nikaido, and Y. Kawaguchi, “MIMII DG: Sound dataset for "
    "malfunctioning industrial machine investigation and inspection for "
    "domain generalization task,” in Proc. DCASE Workshop, Nancy, France, "
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
    "T. Nishida, N. Harada, D. Takeuchi, D. Niizumi, K. Imoto, K. Dohi, "
    "H. Purohit, T. Endo, and Y. Kawaguchi, “Description and discussion on "
    "DCASE 2026 Challenge Task 2: Noise-aware unsupervised anomalous sound "
    "detection for machine condition monitoring,” arXiv:2606.01578, 2026.",
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
        "caption": "Physical Fan Trial - Protocol and Measurements",
        "widths": [4.0, 2.3, 2.0],
        "head": ["Measurement", "Criterion", "Result"],
        "rows": [
            ["Calibration accepted on first attempt", "yes", TODO],
            ["Alarm latency after a sustained induced change", "≤ 4 windows", TODO],
            ["Release latency after the change is removed", "≤ 4 windows", TODO],
            ["False alarms during undisturbed running", "0 per hour", TODO],
            ["Response to speech and door noise", "no alarm", TODO],
            ["Response to the fan being switched off", "presence gate, not alarm", TODO],
        ],
        "note": TODO + "fill this table from the physical trial. Until then "
                "no claim in this paper refers to a physically running fan.",
    },
}

# Slike koje postoje kao fajl (pravi se u make_figures.py). Ostale su okviri
# koji rezervisu stvarnu visinu dok se sadrzaj ne napravi.
FIGURE_FILES = {
    "FIG_SYSTEM": "slike/fig1_system.png",
    "FIG_RUN": "slike/fig2_device_run.png",
    "FIG_THRESHOLD": "slike/fig3_threshold.png",
}
FIGURE_WIDTH_CM = 8.3

FIGURE_HEIGHT_CM = {"FIG_PHOTO": 3.0}
FIGURE_PLACEHOLDER = {
    "FIG_PHOTO": TODO + "photograph of the finished board; it cannot be taken "
                 "until the board with the button and the LEDs is soldered. "
                 "Frame it so the microphone, the button and both LEDs are "
                 "visible, with the fan in the background.",
}


# --------------------------------------------------------------------------
# pomocne funkcije za OOXML
# --------------------------------------------------------------------------

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
        note = doc.add_paragraph()
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


# --------------------------------------------------------------------------
# gradnja dokumenta
# --------------------------------------------------------------------------

def build():
    doc = Document(str(TEMPLATE))
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

    # Bez zavrsne sekcije za balansiranje kolona: kad tekst tacno ispuni
    # cetvrtu stranu, prazan pasus iza prelaza otvori praznu petu stranu.
    body.append(body_sect_pr)

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
