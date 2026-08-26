"""Host tests for the Faza 2 event-semantics core (asd_events.c).

Covers the deterministic transition table, the capability gate that refuses
unsupported diagnoses, and the decision hierarchy
sensor health -> machine presence -> operating regime -> deviation.
"""
from __future__ import annotations

import ctypes
import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "firmware" / "esp32s3_asd" / "main"
SRC = [MAIN / "asd_events.c", MAIN / "audio_quality_state.c",
       MAIN / "asd_temporal.c", MAIN / "asd_interference.c"]
POLICY_JSON = ROOT / "pc" / "config" / "asd_presence_policy_v1.json"

# asd_quality_reason_t
OK, SHORT_READ, NONFINITE, STUCK, LOW_LEVEL, INSUFFICIENT, CLIPPING, DROPPED, INVALID, AUDIO_TIMEOUT, AUDIO_READ_ERROR = range(11)
# asd_quality_phase_t
WAIT, CAL, DET = range(3)
# asd_state_t
NO_MACHINE, CAL_REJECTED, CALIBRATED_NORMAL, ANOMALY, SENSOR_ERROR, RECAL_REQUIRED, OBSERVATION_HOLD = range(7)
# asd_event_t
E_NONE, E_FAN_STOPPED, E_SPEED_CHANGED, E_MECHANICAL, E_AMBIENT, E_SENSOR_FAULT, E_UNKNOWN = range(7)
# asd_capability_t
CAP_AVAILABLE, CAP_NEEDS_F0, CAP_NEEDS_DUAL, CAP_NEEDS_TRANSIENT = range(4)
# asd_decision_level_t
L_SENSOR, L_PRESENCE, L_REGIME, L_DEVIATION = range(4)

ALL_STATES = [NO_MACHINE, CAL_REJECTED, CALIBRATED_NORMAL, ANOMALY,
              SENSOR_ERROR, RECAL_REQUIRED, OBSERVATION_HOLD]
TERMINAL = {CAL_REJECTED, SENSOR_ERROR, RECAL_REQUIRED}

# Jedini autoritet u testu: prepisana tabela, nezavisno od implementacije.
ALLOWED = {
    NO_MACHINE: {CALIBRATED_NORMAL, CAL_REJECTED, SENSOR_ERROR, RECAL_REQUIRED},
    CALIBRATED_NORMAL: {ANOMALY, OBSERVATION_HOLD, NO_MACHINE, SENSOR_ERROR, RECAL_REQUIRED},
    ANOMALY: {CALIBRATED_NORMAL, NO_MACHINE, SENSOR_ERROR, RECAL_REQUIRED},
    CAL_REJECTED: set(),
    SENSOR_ERROR: set(),
    RECAL_REQUIRED: set(),
    OBSERVATION_HOLD: {CALIBRATED_NORMAL, ANOMALY, NO_MACHINE,
                       SENSOR_ERROR, RECAL_REQUIRED},
}


class Policy(ctypes.Structure):
    _fields_ = [("absent_margin_db", ctypes.c_float),
                ("min_consecutive", ctypes.c_int)]


class Calibration(ctypes.Structure):
    _fields_ = [("valid", ctypes.c_int),
                ("level_mean_dbfs", ctypes.c_float),
                ("threshold_enter", ctypes.c_float),
                ("threshold_exit", ctypes.c_float)]


class Observation(ctypes.Structure):
    _fields_ = [("quality", ctypes.c_int),
                ("phase", ctypes.c_int),
                ("rms_dbfs", ctypes.c_float),
                ("score", ctypes.c_float),
                ("tonalness_delta", ctypes.c_float),
                ("subsegment_instability", ctypes.c_float)]


class TemporalPolicy(ctypes.Structure):
    _fields_ = [("min_consecutive", ctypes.c_int),
                ("ewma_alpha", ctypes.c_float),
                ("enter_scale", ctypes.c_float),
                ("exit_scale", ctypes.c_float),
                ("cusum_k", ctypes.c_float),
                ("cusum_h", ctypes.c_float),
                ("fast_scale", ctypes.c_float)]


class Temporal(ctypes.Structure):
    """Faza 4: brojac odstupanja vise ne zivi u asd_events.c nego ovdje."""
    _fields_ = [("ewma", ctypes.c_float),
                ("ewma_valid", ctypes.c_int),
                ("run", ctypes.c_int),
                ("cusum", ctypes.c_float),
                ("active", ctypes.c_int),
                ("policy", TemporalPolicy)]


class InterferencePolicy(ctypes.Structure):
    _fields_ = [("enabled", ctypes.c_int),
                ("developmental", ctypes.c_int),
                ("use_tonalness_delta", ctypes.c_int),
                ("max_abs_tonalness_delta", ctypes.c_float),
                ("normal_max_multiplier", ctypes.c_float),
                ("calibration_min_windows", ctypes.c_uint32),
                ("max_subsegment_instability", ctypes.c_float),
                ("long_hold_windows", ctypes.c_uint32)]


class Interference(ctypes.Structure):
    _fields_ = [("policy", InterferencePolicy),
                ("hold_windows", ctypes.c_uint32),
                ("hold_active", ctypes.c_int),
                ("warning_emitted", ctypes.c_int)]


class Ctx(ctypes.Structure):
    _fields_ = [("state", ctypes.c_int),
                ("absent_run", ctypes.c_int),
                ("anomaly_windows", ctypes.c_uint32),
                ("sustained_reported", ctypes.c_int),
                ("temporal", Temporal),
                ("interference", Interference),
                ("policy", Policy)]


class Decision(ctypes.Structure):
    _fields_ = [("state", ctypes.c_int),
                ("event", ctypes.c_int),
                ("level", ctypes.c_int),
                ("flow_stop", ctypes.c_int),
                ("state_changed", ctypes.c_int),
                ("observation_hold", ctypes.c_int),
                ("hold_warning", ctypes.c_int),
                ("sustained_anomaly", ctypes.c_int)]


@pytest.fixture(scope="module")
def lib(tmp_path_factory: pytest.TempPathFactory):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema host C kompajlera")
    out = tmp_path_factory.mktemp("events_c") / (
        "asd_events.dll" if __import__("sys").platform == "win32" else "asd_events.so")
    args = [cc, "-std=c99", "-O1", "-shared", "-fPIC", "-I", str(MAIN)]
    args += [str(p) for p in SRC]
    args += ["-o", str(out), "-lm"]
    subprocess.run(args, check=True, capture_output=True, text=True)

    handle = ctypes.CDLL(str(out))
    handle.asd_presence_default_policy.restype = Policy
    handle.asd_decision_init.argtypes = [ctypes.POINTER(Ctx), ctypes.POINTER(Policy)]
    handle.asd_decision_set_interference_policy.argtypes = [
        ctypes.POINTER(Ctx), ctypes.POINTER(InterferencePolicy),
    ]
    handle.asd_decide.argtypes = [ctypes.POINTER(Ctx), ctypes.POINTER(Calibration),
                                  ctypes.POINTER(Observation)]
    handle.asd_decide.restype = Decision
    for name in ("asd_event_capability", "asd_event_is_emittable",
                 "asd_state_is_terminal", "asd_event_for_quality_reject",
                 "asd_level_for_quality_reject"):
        getattr(handle, name).argtypes = [ctypes.c_int]
        getattr(handle, name).restype = ctypes.c_int
    handle.asd_transition_allowed.argtypes = [ctypes.c_int, ctypes.c_int]
    handle.asd_transition_allowed.restype = ctypes.c_int
    for name in ("asd_event_name", "asd_capability_name", "asd_decision_level_name"):
        getattr(handle, name).argtypes = [ctypes.c_int]
        getattr(handle, name).restype = ctypes.c_char_p
    return handle


def make_ctx(lib, margin=11.0, n_consec=3, state=CALIBRATED_NORMAL,
             temporal_n=None):
    """`n_consec` je politika PRISUSTVA. Od Faze 4 brojanje odstupanja ima
    vlastitu politiku u `asd_temporal.c`; `temporal_n` je mijenja."""
    ctx = Ctx()
    policy = Policy(margin, n_consec)
    lib.asd_decision_init(ctypes.byref(ctx), ctypes.byref(policy))
    # Produkcijski psd_live ovo radi tek nakon 10 CAL normal-only prozora.
    # Hijerarhijski unit testovi ne izvode cijeli commissioning, pa dobijaju
    # eksplicitno kalibrisanu, inace validnu politiku.
    interference = InterferencePolicy(1, 1, 0, 1.0, 1.25, 10, 0.5, 6)
    lib.asd_decision_set_interference_policy(
        ctypes.byref(ctx), ctypes.byref(interference),
    )
    if temporal_n is not None:
        ctx.temporal.policy.min_consecutive = temporal_n
    ctx.state = state
    return ctx


def obs(rms=-24.0, score=1.0, quality=OK, phase=DET,
        tonalness_delta=0.0, instability=0.0):
    return Observation(quality, phase, rms, score,
                       tonalness_delta, instability)


CAL_OK = Calibration(1, -24.0, 100.0, 70.0)
CAL_INVALID = Calibration(0, float("nan"), 0.0, 0.0)


# --- policy -----------------------------------------------------------------

def test_default_policy_matches_locked_json(lib):
    policy = lib.asd_presence_default_policy()
    data = json.loads(POLICY_JSON.read_text(encoding="utf-8"))
    assert data["target_anomalies_used"] is False
    assert policy.absent_margin_db == pytest.approx(
        data["policy"]["absent_margin_db"])
    assert policy.min_consecutive == data["policy"]["min_consecutive_windows"]


# --- capability gate --------------------------------------------------------

@pytest.mark.parametrize("event,expected", [
    (E_NONE, CAP_AVAILABLE),
    (E_FAN_STOPPED, CAP_AVAILABLE),
    (E_SENSOR_FAULT, CAP_AVAILABLE),
    (E_UNKNOWN, CAP_AVAILABLE),
    (E_SPEED_CHANGED, CAP_NEEDS_F0),
    (E_AMBIENT, CAP_NEEDS_DUAL),
    (E_MECHANICAL, CAP_NEEDS_TRANSIENT),
])
def test_event_capability(lib, event, expected):
    assert lib.asd_event_capability(event) == expected


@pytest.mark.parametrize("event", [E_SPEED_CHANGED, E_AMBIENT, E_MECHANICAL])
def test_reserved_events_are_not_emittable(lib, event):
    """Diagnoze koje traže Faze 3/5/6 se ne smiju emitovati sada."""
    assert lib.asd_event_is_emittable(event) == 0


@pytest.mark.parametrize("event", [E_NONE, E_FAN_STOPPED, E_SENSOR_FAULT, E_UNKNOWN])
def test_available_events_are_emittable(lib, event):
    assert lib.asd_event_is_emittable(event) == 1


def test_event_names_are_stable_ascii(lib):
    for event in range(7):
        name = lib.asd_event_name(event).decode("ascii")
        assert name and name == name.upper()


# --- transition table -------------------------------------------------------

@pytest.mark.parametrize("frm", ALL_STATES)
@pytest.mark.parametrize("to", ALL_STATES)
def test_transition_table_is_exactly_as_specified(lib, frm, to):
    expected = 1 if (frm == to or to in ALLOWED[frm]) else 0
    assert lib.asd_transition_allowed(frm, to) == expected


def test_no_anomaly_without_valid_calibration(lib):
    """Bez validne kalibracije nema od čega da se odstupa."""
    assert lib.asd_transition_allowed(NO_MACHINE, ANOMALY) == 0
    assert lib.asd_transition_allowed(CAL_REJECTED, ANOMALY) == 0


@pytest.mark.parametrize("frm", sorted(TERMINAL))
@pytest.mark.parametrize("to", [NO_MACHINE, CALIBRATED_NORMAL, ANOMALY])
def test_terminal_states_have_no_exit(lib, frm, to):
    assert lib.asd_transition_allowed(frm, to) == 0


@pytest.mark.parametrize("state", ALL_STATES)
def test_terminal_flag(lib, state):
    assert bool(lib.asd_state_is_terminal(state)) == (state in TERMINAL)


# --- hijerarhija: zdravlje senzora guši sve ispod ---------------------------

@pytest.mark.parametrize(
    "reason",
    [SHORT_READ, NONFINITE, STUCK, DROPPED, INVALID, AUDIO_TIMEOUT, AUDIO_READ_ERROR],
)
def test_sensor_fault_wins_over_presence_and_deviation(lib, reason):
    ctx = make_ctx(lib)
    # nivo je uredan i score je ispod praga, pa bi bez ovog nivoa sve bilo normal
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=-24.0, score=1.0, quality=reason)))
    assert d.event == E_SENSOR_FAULT
    assert d.level == L_SENSOR
    assert d.flow_stop == 1
    assert d.state == SENSOR_ERROR


def test_clipping_in_det_requires_recalibration_not_sensor_error(lib):
    """Faza 1 mapira clipping u DET na RECALIBRATION_REQUIRED; ostaje tako."""
    ctx = make_ctx(lib)
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK),
                       ctypes.byref(obs(quality=CLIPPING, phase=DET)))
    assert d.state == RECAL_REQUIRED
    assert d.event == E_SENSOR_FAULT
    assert d.flow_stop == 1


def test_nonfinite_metrics_are_a_sensor_fault(lib):
    ctx = make_ctx(lib)
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=float("nan"))))
    assert d.state == SENSOR_ERROR and d.flow_stop == 1
    ctx = make_ctx(lib)
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK),
                       ctypes.byref(obs(score=float("inf"))))
    assert d.state == SENSOR_ERROR and d.flow_stop == 1


# --- hijerarhija: prisustvo mašine -----------------------------------------

def test_presence_needs_min_consecutive_windows(lib):
    ctx = make_ctx(lib, n_consec=3)
    quiet = obs(rms=-40.0, score=1.0)          # 16 dB ispod, gate je 11 dB
    for i in range(2):
        d = lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(quiet))
        assert d.event == E_NONE, f"prozor {i+1} ne smije emitovati"
        assert d.state == CALIBRATED_NORMAL
        assert d.flow_stop == 0
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(quiet))
    assert d.event == E_FAN_STOPPED
    assert d.state == NO_MACHINE
    assert d.level == L_PRESENCE
    assert d.flow_stop == 1


def test_presence_run_resets_on_one_good_window(lib):
    ctx = make_ctx(lib, n_consec=3)
    quiet, good = obs(rms=-40.0), obs(rms=-24.0)
    lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(quiet))
    lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(quiet))
    lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(good))
    assert ctx.absent_run == 0
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(quiet))
    assert d.event == E_NONE, "brojač se morao resetovati"


def test_normal_dip_just_inside_margin_is_not_a_stop(lib):
    """Najgori izmjereni normalan pad po trojki je -7,9 dB; margina je 11 dB."""
    ctx = make_ctx(lib, margin=11.0, n_consec=3)
    dip = obs(rms=-24.0 - 7.9, score=1.0)
    for _ in range(6):
        d = lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(dip))
        assert d.event == E_NONE
        assert d.state == CALIBRATED_NORMAL


def test_presence_suppresses_deviation(lib):
    """Kad mašina utihne, score skoči (08.08: 10 -> 59). Ne smije se emitovati
    anomalija prije zaustavljanja."""
    ctx = make_ctx(lib, n_consec=3)
    collapsing = obs(rms=-45.0, score=9999.0)   # i nivo pao i score iznad praga
    events = []
    for _ in range(3):
        d = lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(collapsing))
        events.append(d.event)
    assert events == [E_NONE, E_NONE, E_FAN_STOPPED]
    assert ctx.state == NO_MACHINE, "nikad se ne smije proći kroz ANOMALY"
    assert ctx.temporal.run == 0


def test_machine_return_requires_recalibration(lib):
    """Centar se nikad ne pomjera automatski (P10): nema tihog nastavka."""
    ctx = make_ctx(lib, n_consec=1, state=CALIBRATED_NORMAL)
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(obs(rms=-45.0)))
    assert d.state == NO_MACHINE and d.event == E_FAN_STOPPED
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(obs(rms=-24.0)))
    assert d.state == RECAL_REQUIRED
    assert d.flow_stop == 1
    assert d.state != CALIBRATED_NORMAL


def test_presence_not_judged_without_calibration(lib):
    ctx = make_ctx(lib, state=NO_MACHINE)
    d = lib.asd_decide(ctx, ctypes.byref(CAL_INVALID),
                       ctypes.byref(obs(rms=-90.0, score=9999.0)))
    assert d.state == NO_MACHINE
    assert d.event == E_NONE
    assert d.level == L_PRESENCE
    assert d.flow_stop == 0


# --- hijerarhija: odstupanje -----------------------------------------------

def test_deviation_needs_min_consecutive_and_reports_unknown_change(lib):
    ctx = make_ctx(lib, n_consec=3)
    high = obs(rms=-24.0, score=150.0)
    for _ in range(2):
        d = lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(high))
        assert d.event == E_NONE and d.state == CALIBRATED_NORMAL
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(high))
    assert d.state == ANOMALY
    assert d.level == L_DEVIATION
    assert d.flow_stop == 0, "anomalija nije fail-closed; nastavlja se praćenje"


def test_deviation_never_claims_a_cause(lib):
    """Status je činjenica, događaj je najslabija tvrdnja. Nikad MECHANICAL_ANOMALY."""
    ctx = make_ctx(lib, temporal_n=1)
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=-24.0, score=150.0)))
    assert d.state == ANOMALY
    assert d.event == E_UNKNOWN
    assert d.event not in (E_MECHANICAL, E_SPEED_CHANGED, E_AMBIENT)


def test_anomaly_clears_without_inventing_an_event(lib):
    ctx = make_ctx(lib, temporal_n=1)
    lib.asd_decide(ctx, ctypes.byref(CAL_OK),
                   ctypes.byref(obs(rms=-24.0, score=150.0)))
    assert ctx.state == ANOMALY
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=-24.0, score=1.0)))
    assert d.state == CALIBRATED_NORMAL
    assert d.event == E_NONE
    assert d.state_changed == 1


def test_score_exactly_at_threshold_is_normal(lib):
    ctx = make_ctx(lib, temporal_n=1)
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=-24.0, score=CAL_OK.threshold_enter)))
    assert d.state == CALIBRATED_NORMAL, "prag je strogo veće, kao u psd_live.c"


def test_low_level_observation_is_not_a_sensor_fault(lib):
    """Prenizak nivo je podatak o mašini, ne kvar senzora."""
    ctx = make_ctx(lib, n_consec=3)
    d = lib.asd_decide(ctx, ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=-40.0, quality=LOW_LEVEL)))
    assert d.event != E_SENSOR_FAULT
    assert d.level == L_PRESENCE


# --- determinizam i rollback ----------------------------------------------

def test_terminal_state_absorbs_every_later_observation(lib):
    ctx = make_ctx(lib, state=SENSOR_ERROR)
    for _ in range(5):
        d = lib.asd_decide(ctx, ctypes.byref(CAL_OK), ctypes.byref(obs()))
        assert d.state == SENSOR_ERROR
        assert d.flow_stop == 1
        assert d.state_changed == 0


def test_same_inputs_give_same_decision(lib):
    """Determinizam: isti kontekst i isti niz uvijek daju isti niz odluka,
    u svakom polju rezultata, ne samo u stanju."""
    seq = [obs(rms=-24.0, score=1.0), obs(rms=-24.0, score=150.0),
           obs(rms=-24.0, score=150.0), obs(rms=-40.0, score=150.0),
           obs(rms=-40.0, score=150.0), obs(rms=-24.0, score=1.0)]

    def replay():
        ctx = make_ctx(lib, n_consec=2)
        out = []
        for o in seq:
            d = lib.asd_decide(ctypes.byref(ctx), ctypes.byref(CAL_OK),
                               ctypes.byref(o))
            out.append((d.state, d.event, d.level, d.flow_stop, d.state_changed))
        return out

    first = replay()
    assert first == replay() == replay()
    # Niz mora i stvarno proći kroz više stanja, inače test ne dokazuje ništa.
    assert len({row[0] for row in first}) >= 3


def test_null_arguments_fail_closed(lib):
    ctx = make_ctx(lib)
    d = lib.asd_decide(ctypes.byref(ctx), None, ctypes.byref(obs()))
    assert d.state == SENSOR_ERROR and d.flow_stop == 1


# --- semantika Faze 2 za fail-closed odbijanja iz Faze 1 --------------------

SENSOR_FAULT_REASONS = [
    SHORT_READ, NONFINITE, STUCK, CLIPPING, DROPPED, INVALID,
    AUDIO_TIMEOUT, AUDIO_READ_ERROR,
]
LEVEL_REASONS = [LOW_LEVEL, INSUFFICIENT]


@pytest.mark.parametrize("reason", SENSOR_FAULT_REASONS)
def test_sensor_fault_reject_maps_to_sensor_fault(lib, reason):
    assert lib.asd_event_for_quality_reject(reason) == E_SENSOR_FAULT
    assert lib.asd_level_for_quality_reject(reason) == L_SENSOR


@pytest.mark.parametrize("reason", LEVEL_REASONS)
def test_low_level_never_claims_the_fan_stopped(lib, reason):
    """Bez kalibracije uredjaj masinu nije ni cuo, pa ne smije tvrditi da je stala."""
    assert lib.asd_event_for_quality_reject(reason) == E_NONE
    assert lib.asd_level_for_quality_reject(reason) == L_PRESENCE


def test_ok_is_not_an_event(lib):
    assert lib.asd_event_for_quality_reject(OK) == E_NONE


def test_every_reject_event_is_actually_emittable(lib):
    """Preslikavanje ne smije proizvesti dogadjaj koji kapabilitetni gate zabranjuje."""
    for reason in range(11):
        event = lib.asd_event_for_quality_reject(reason)
        assert lib.asd_event_is_emittable(event) == 1


# --- Faza 4: vremenska odluka je odvojena politika -------------------------

def test_presence_policy_no_longer_controls_the_deviation_counter(lib):
    """Prije Faze 4 je isti broj upravljao i prisustvom i odstupanjem.
    Sada su odvojeni, pa `min_consecutive=1` u politici prisustva NE cini da
    jedan prozor iznad praga podigne alarm."""
    ctx = make_ctx(lib, n_consec=1)
    high = obs(rms=-24.0, score=150.0)
    d = lib.asd_decide(ctypes.byref(ctx), ctypes.byref(CAL_OK), ctypes.byref(high))
    assert d.state == CALIBRATED_NORMAL
    assert ctx.temporal.policy.min_consecutive == 3


def test_short_disturbance_does_not_alarm_through_the_hierarchy(lib):
    """Govor ili udarac: jedan glasan prozor kroz cijelu hijerarhiju ostaje normalan."""
    ctx = make_ctx(lib)
    for score in (1.0, 1.0, 99999.0, 1.0, 1.0):
        d = lib.asd_decide(ctypes.byref(ctx), ctypes.byref(CAL_OK),
                           ctypes.byref(obs(rms=-24.0, score=score)))
        assert d.state == CALIBRATED_NORMAL, score


def test_alarm_survives_a_short_level_dip(lib):
    """Masina na trenutak utihne dok alarm traje: alarm se ne smije obrisati.

    Suspend, ne reset -- nista nije ponistilo odstupanje koje je uredjaj
    stvarno izmjerio."""
    ctx = make_ctx(lib)
    for _ in range(3):
        lib.asd_decide(ctypes.byref(ctx), ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=-24.0, score=150.0)))
    assert ctx.state == ANOMALY
    # jedan prozor ispod gate-a prisustva (-24 - 11 = -35 dBFS)
    d = lib.asd_decide(ctypes.byref(ctx), ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=-40.0, score=150.0)))
    assert d.state == ANOMALY
    assert d.level == L_PRESENCE
    assert ctx.temporal.run == 0, "uspon ka alarmu se pauzira"
    assert ctx.temporal.active == 1, "alarm koji traje se NE brise"
    # nivo se vrati, score i dalje iznad izlaznog praga -> alarm i dalje traje
    d = lib.asd_decide(ctypes.byref(ctx), ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=-24.0, score=150.0)))
    assert d.state == ANOMALY


def test_hysteresis_is_visible_through_the_hierarchy(lib):
    ctx = make_ctx(lib)
    for _ in range(3):
        lib.asd_decide(ctypes.byref(ctx), ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=-24.0, score=150.0)))
    assert ctx.state == ANOMALY
    # izmedju izlaznog (0,7 * 100 = 70) i ulaznog praga alarm ostaje
    d = lib.asd_decide(ctypes.byref(ctx), ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=-24.0, score=80.0)))
    assert d.state == ANOMALY
    d = lib.asd_decide(ctypes.byref(ctx), ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=-24.0, score=60.0)))
    assert d.state == CALIBRATED_NORMAL


def test_sensor_fault_fully_resets_the_detector(lib):
    """Kvar senzora nije 'visi nivo preuzeo odluku' nego 'nema podatka'."""
    ctx = make_ctx(lib)
    for _ in range(3):
        lib.asd_decide(ctypes.byref(ctx), ctypes.byref(CAL_OK),
                       ctypes.byref(obs(rms=-24.0, score=150.0)))
    assert ctx.temporal.active == 1
    lib.asd_decide(ctypes.byref(ctx), ctypes.byref(CAL_OK),
                   ctypes.byref(obs(rms=-24.0, score=150.0, quality=STUCK)))
    assert ctx.temporal.active == 0 and ctx.temporal.run == 0


# --- Faza 6: observation HOLD ----------------------------------------------

def enable_interference(lib, ctx, *, long_hold=3):
    policy = InterferencePolicy(1, 1, 1, 1.0, 1.25, 10, 0.5, long_hold)
    lib.asd_decision_set_interference_policy(
        ctypes.byref(ctx), ctypes.byref(policy),
    )


def test_unreliable_high_window_suspends_alarm_buildup(lib):
    ctx = make_ctx(lib, temporal_n=3)
    enable_interference(lib, ctx)
    d = lib.asd_decide(
        ctypes.byref(ctx), ctypes.byref(CAL_OK),
        ctypes.byref(obs(score=150.0, tonalness_delta=2.0)),
    )
    assert d.state == OBSERVATION_HOLD
    assert d.observation_hold == 1 and d.event == E_NONE
    assert ctx.temporal.run == 0 and ctx.temporal.active == 0


def test_stable_high_after_hold_builds_a_fresh_alarm(lib):
    ctx = make_ctx(lib, temporal_n=3)
    enable_interference(lib, ctx)
    held = obs(score=150.0, tonalness_delta=2.0)
    stable = obs(score=150.0, tonalness_delta=0.1, instability=0.1)
    assert lib.asd_decide(
        ctypes.byref(ctx), ctypes.byref(CAL_OK), ctypes.byref(held),
    ).state == OBSERVATION_HOLD
    states = [
        lib.asd_decide(
            ctypes.byref(ctx), ctypes.byref(CAL_OK), ctypes.byref(stable),
        ).state
        for _ in range(3)
    ]
    assert states == [OBSERVATION_HOLD, OBSERVATION_HOLD, ANOMALY]


def test_active_alarm_is_not_cleared_by_hold_and_long_hold_warns(lib):
    ctx = make_ctx(lib, temporal_n=1)
    enable_interference(lib, ctx, long_hold=2)
    stable = obs(score=150.0, tonalness_delta=0.1, instability=0.1)
    assert lib.asd_decide(
        ctypes.byref(ctx), ctypes.byref(CAL_OK), ctypes.byref(stable),
    ).state == ANOMALY
    held = obs(score=150.0, tonalness_delta=3.0, instability=1.0)
    first = lib.asd_decide(
        ctypes.byref(ctx), ctypes.byref(CAL_OK), ctypes.byref(held),
    )
    second = lib.asd_decide(
        ctypes.byref(ctx), ctypes.byref(CAL_OK), ctypes.byref(held),
    )
    assert first.state == second.state == ANOMALY
    assert ctx.temporal.active == 1
    assert first.observation_hold == 1 and second.hold_warning == 1
    assert first.event == second.event == E_NONE
