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
    "developmental AUC of 0.856 on the DCASE 2026 fan data and 716 ms "
    "of computation per 10 s window. On a physical fan the device learns "
    "the normal state of a machine it has never heard, derives its own "
    "threshold from a normal-only period, verifies that threshold on a "
    "later normal-only period, and reports a sustained acoustic change "
    "while rejecting speech and door noise as unreliable rather than "
    "interpreting them. An earlier version of the same system produced "
    "thresholds differing by a factor of 16 across repeated calibrations "
    "of the same machine in the same room; we report both that failure "
    "and the measured fix, together with four negative results, one of "
    "which the device itself rejected during verification."
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
     "1) A complete self-calibrating detector: 716 ms of computation per "
     "10 s window, an about 14x real-time margin, 355 kB of firmware and "
     "no neural network. 2) A normal-only design protocol under which "
     "every operating policy is derived, versioned and frozen before any "
     "anomalous recording is read. 3) A fail-closed decision hierarchy in "
     "which the device refuses to score untrustworthy input, and a "
     "reliability gate that rejects an internally unstable window instead "
     "of attributing it to a cause a single microphone cannot identify. "
     "4) A threshold derived on the device from one normal-only period "
     "and verified on a later one, which removes the factor-16 "
     "calibration instability we previously reported as an open failure "
     "mode. 5) Measurements on a physical fan, and four negative results, "
     "one of which the verification stage rejected on the device before "
     "it could reach monitoring."),
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
     "The firmware image is 354 784 B with research telemetry included "
     "and leaves most of the application partition free. "
     "The front end is computed in streaming fashion, hop by hop, avoiding "
     "the approximately 640 kB full-window float buffer that a 10 s recording "
     "would require, and its result is identical to the batch computation. "
     "One 10 s window "
     "takes 716 ms end to end, feature and score together, which is an "
     "about 14x real-time margin."),
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
     "A button press starts a fixed sequence: SETTLE, then ten 10 s "
     "windows that fix the local centre, then 44 normal-only windows from "
     "which the threshold is derived, then 22 later normal-only windows "
     "on which that threshold is verified, and only then MONITORING. The "
     "entry threshold is the empirical 99th percentile of the derivation "
     "window scores and the release threshold the 95th, clamped below by "
     "the median and above by half the entry threshold. Derivation and "
     "verification are separated in time and in data: if any alarm occurs "
     "during verification the calibration is rejected and the device does "
     "not arm. The threshold is never adjusted to make verification pass, "
     "which would defeat its purpose. In monitoring an alarm needs three "
     "consecutive reliable windows above the entry threshold, roughly "
     "30 s, and twelve further alarm windows raise a separate "
     "sustained-deviation event."),

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

    ("p",
     "A fourth stage was added after the first physical trial. Each 10 s "
     "window is split into five sub-windows and a feature is computed for "
     "each. If those five disagree by more than a per-session limit, the "
     "window is internally unstable, its score is not a reliable measure "
     "of machine state, and it is excluded from alarm build-up. The limit "
     "is derived per session as 1.25 times the largest instability seen "
     "among the ten calibration windows; an earlier absolute limit "
     "carried the scale of one microphone position and stopped being "
     "valid as soon as the setup moved."),
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
     "Three outcomes removed design options. Rotation-order features collapse "
     "to 0.639: the median fundamental is 34 Hz at all three labelled "
     "speeds and their dominant peaks coincide to within one 1.95 Hz bin, "
     "so the labelled speeds carry nothing the shape feature does not "
     "already have. All three dual-microphone variants are worse than the "
     "single channel and the spatial-mask variant reaches 0.450, below "
     "chance, so the shipped device uses one microphone by measurement "
     "rather than by cost. Adding a transient channel yields +0.0012 AUC "
     "against a split-to-split standard deviation of 0.024, which is "
     "nothing."),
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
     "Two valid trials were then run on a physical fan, both from the "
     "same firmware image, with the microphone 40 cm from the shaft. In "
     "the first, the induced change was a strip of paper held against the "
     "intake grille, repeated three times, followed by speech and a door. "
     "In the second, the change was a constant 1 kHz tone from a "
     "loudspeaker at a fixed level and position. Table III reports both. "
     "The induced changes are controlled, reversible disturbances; "
     "neither is a confirmed fault, and we do not call them one."),
    ("table", "T3"),
    ("p",
     "The paper trial is the more informative of the two. The feature saw "
     "the change in all three blocks - median scores of 26 399, 60 050 "
     "and 14 389 against a normal baseline of 1190 - but an alarm was "
     "raised only in the third. In the first two the reliability gate "
     "held four and three of five windows, so the run of three "
     "consecutive reliable windows never completed. A strip of paper held "
     "by hand is not a constant stimulus, and the device refuses to call "
     "an unstable window an anomaly. Speech and the door produced high "
     "scores, 36 838 and 4366, and no alarm, for the same reason."),
    ("p",
     "The tone trial supplies the constant stimulus the paper trial lacked. "
     "The alarm was raised after three consecutive reliable windows, about "
     "30 s, and the sustained-deviation event followed twelve alarm windows "
     "later. The first nine tone windows scored within the normal range "
     "because the loudspeaker was too quiet: the change has to be loud "
     "enough relative to the fan's own noise. After the tone was switched "
     "off the score fell below the entry threshold but stayed above the "
     "release threshold until the trial ended, so that release latency was "
     "not measured."),
    ("figure", ("FIG_FAN",
                "Score over the tone trial, one point per 10 s window. "
                "The alarm is raised after three consecutive reliable "
                "windows; held windows are excluded from alarm build-up. "
                "Note the logarithmic scale.")),

    ("h1", "Threshold Instability and Its Fix"),
    ("p",
     "The failure mode we previously reported as open is worth restating "
     "because the fix follows from it. The same board, microphone, audio "
     "source and room produced three calibrations with thresholds of "
     "5687, 347 and 1088. Scoring the windows of run 1 with the threshold "
     "of run 2 puts 92 % of them above it; the reverse leaves 8 % above. "
     "Across the three runs the threshold spans a factor of 16 while the "
     "median score spans a factor of 4.7. The scores were comparatively "
     "stable; the threshold was not."),
    ("p",
     "The mechanism was the estimator, not the machine. The threshold was "
     "taken from the ten leave-one-out calibration scores as "
     "max(Q_0.90, mean + 3 sd). In one run a single window stood out and "
     "the standard deviation carried the threshold to 5687; in another "
     "the calibration was clean with a standard deviation of 60 while the "
     "normal operation that followed had a standard deviation of 8557. "
     "Ten windows recorded back to back do not represent how much normal "
     "operation varies later."),
    ("p",
     "The fix is the derive-and-verify sequence of Section II.C: the "
     "threshold comes from 44 normal-only windows as an empirical "
     "percentile rather than from a mean and a standard deviation over "
     "ten, and it is then verified on 22 later normal-only windows. In "
     "both physical trials the derived threshold passed verification and "
     "the resulting monitoring produced two alarm episodes in the paper "
     "trial and two in the tone trial, each attributable to an induced "
     "change rather than to normal operation."),
    ("p",
     "The fourth negative result belongs here, because the verification "
     "stage produced it. A more robust estimator was tried on the device, "
     "the smaller of the empirical 99th percentile and a Hampel bound of "
     "median + 3 x 1.4826 x MAD. It returned a threshold of 791 while the "
     "normal verification windows of the same session scored between 2083 "
     "and 7766, and verification rejected the calibration before a single "
     "monitoring window existed. The median absolute deviation describes "
     "only the body of the distribution, and the tail of normal operation "
     "on this fan is far longer than three robust deviations. The robust "
     "estimator was removed from the live path; a gate that fires rarely "
     "still earns its place."),
    ("p",
     "One limitation is unchanged. The calibration quality gate rejects a "
     "session whose ten clips disagree, and a single clip deviating by "
     "about 0.7 dB in one of 96 bands is enough to trigger it, always in "
     "the narrow band around the rotation frequency. The device may discard "
     "at most the two worst clips and recompute, which treats the symptom "
     "rather than the small variance the borrowed covariance assigns to "
     "that band."),

    ("h1", "Conclusion"),
    ("p",
     "A statistical anomalous sound detector fits comfortably on an "
     "ESP32-S3: 716 ms per 10 s window, 355 kB of firmware, one "
     "microphone, one button, and a field calibration that ends with a "
     "threshold the device derived and verified by itself. Every "
     "operating policy was derived from normal sound alone, and the "
     "decision hierarchy fails closed rather than scoring untrustworthy "
     "audio."),
    ("p",
     "On a physical fan the device reports a constant acoustic change "
     "reliably and rejects speech and a door as unreliable rather than "
     "interpreting them. What limits the claim is no longer threshold "
     "stability but coverage: one fan, one room, and induced changes that "
     "are controlled disturbances rather than confirmed faults. A second "
     "machine, a longer normal-only run for a meaningful false-alarm "
     "interval, and full-pipeline power remain open."),
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
            ["Normal baseline, median score", "1190", "7164"],
            ["Induced change, median score", "14 389 - 60 050", "22 629"],
            ["Monitoring windows", "65", "115"],
            ["Alarm windows / episodes", "3 / 2", "64 / 2"],
            ["Alarm latency", "3 windows", "3 windows"],
            ["Median release latency", "10.1 s", "not measured"],
            ["Speech / door response", "no alarm, windows held", "not applied"],
            ["Sustained-deviation event", "no", "yes, after 12 windows"],
            ["Per-window dropped samples", "0", "0"],
        ],
        "note": "Both trials come from the same firmware image. The induced changes are controlled disturbances, not confirmed faults.",
    },
}

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
