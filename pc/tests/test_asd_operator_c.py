"""Host tests for the operator flow core (asd_operator.c).

Covers the debounce/short/long button state machine, the indicator patterns,
and the command table whose central rule is: a short press never discards a
learned centre, and no path produces a new centre without an explicit operator
action.
"""
from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "firmware" / "esp32s3_asd" / "main"
SRC = [MAIN / "asd_operator.c", MAIN / "asd_events.c",
       MAIN / "audio_quality_state.c", MAIN / "asd_temporal.c",
       MAIN / "asd_interference.c"]

# asd_flow_stage_t
STAGE_IDLE, STAGE_LEARNING, STAGE_MONITORING = range(3)
# asd_ui_mode_t
UI_IDLE, UI_LEARNING, UI_READY, UI_ALARM, UI_FAULT = range(5)
UI_HOLD = 5
# asd_button_event_t
BTN_NONE, BTN_SHORT, BTN_LONG = range(3)
# asd_ui_command_t
CMD_NONE, CMD_START, CMD_ABORT = range(3)
# asd_state_t
NO_MACHINE, CAL_REJECTED, CALIBRATED_NORMAL, ANOMALY, SENSOR_ERROR, RECAL_REQUIRED = range(6)
OBSERVATION_HOLD = 6

ALL_STATES = [NO_MACHINE, CAL_REJECTED, CALIBRATED_NORMAL, ANOMALY,
              SENSOR_ERROR, RECAL_REQUIRED]
TERMINAL = {CAL_REJECTED, SENSOR_ERROR, RECAL_REQUIRED}
ALL_MODES = [UI_IDLE, UI_LEARNING, UI_READY, UI_ALARM, UI_FAULT]

DEBOUNCE_MS = 30
LONG_PRESS_MS = 1500


class ButtonPolicy(ctypes.Structure):
    _fields_ = [("debounce_ms", ctypes.c_uint32),
                ("long_press_ms", ctypes.c_uint32)]


class Button(ctypes.Structure):
    _fields_ = [("stable_level", ctypes.c_int),
                ("raw_level", ctypes.c_int),
                ("raw_since_ms", ctypes.c_uint32),
                ("pressed_since_ms", ctypes.c_uint32),
                ("long_fired", ctypes.c_int),
                ("initialised", ctypes.c_int),
                ("policy", ButtonPolicy)]


@pytest.fixture(scope="module")
def lib(tmp_path_factory: pytest.TempPathFactory):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema host C kompajlera")
    out = tmp_path_factory.mktemp("operator_c") / (
        "asd_operator.dll" if sys.platform == "win32" else "asd_operator.so")
    args = [cc, "-std=c99", "-O1", "-shared", "-fPIC", "-I", str(MAIN)]
    args += [str(p) for p in SRC]
    args += ["-o", str(out), "-lm"]
    subprocess.run(args, check=True, capture_output=True, text=True)

    handle = ctypes.CDLL(str(out))
    handle.asd_button_default_policy.restype = ButtonPolicy
    handle.asd_button_init.argtypes = [ctypes.POINTER(Button),
                                       ctypes.POINTER(ButtonPolicy),
                                       ctypes.c_int, ctypes.c_uint32]
    handle.asd_button_update.argtypes = [ctypes.POINTER(Button), ctypes.c_int,
                                         ctypes.c_uint32]
    handle.asd_button_update.restype = ctypes.c_int
    handle.asd_ui_mode.argtypes = [ctypes.c_int, ctypes.c_int]
    handle.asd_ui_mode.restype = ctypes.c_int
    handle.asd_indicator_level.argtypes = [ctypes.c_int, ctypes.c_uint32]
    handle.asd_indicator_level.restype = ctypes.c_int
    handle.asd_alarm_level.argtypes = [ctypes.c_int, ctypes.c_uint32]
    handle.asd_alarm_level.restype = ctypes.c_int
    handle.asd_ui_command.argtypes = [ctypes.c_int, ctypes.c_int]
    handle.asd_ui_command.restype = ctypes.c_int
    handle.asd_ui_command_discards_calibration.argtypes = [ctypes.c_int, ctypes.c_int]
    handle.asd_ui_command_discards_calibration.restype = ctypes.c_int
    for name in ("asd_ui_mode_name", "asd_button_event_name",
                 "asd_ui_command_name", "asd_flow_stage_name"):
        getattr(handle, name).argtypes = [ctypes.c_int]
        getattr(handle, name).restype = ctypes.c_char_p
    return handle


def make_button(lib, initial_pressed=0, now=0, debounce=DEBOUNCE_MS,
                long_ms=LONG_PRESS_MS):
    btn = Button()
    policy = ButtonPolicy(debounce, long_ms)
    lib.asd_button_init(ctypes.byref(btn), ctypes.byref(policy),
                        initial_pressed, now)
    return btn


def feed(lib, btn, samples):
    """samples = [(pressed, now_ms), ...] -> list of events."""
    return [lib.asd_button_update(ctypes.byref(btn), p, t) for p, t in samples]


# --- taster: debounce, kratak i dug pritisak --------------------------------

def test_default_policy_values(lib):
    policy = lib.asd_button_default_policy()
    assert policy.debounce_ms == DEBOUNCE_MS
    assert policy.long_press_ms == LONG_PRESS_MS


def test_idle_button_never_fires(lib):
    btn = make_button(lib)
    events = feed(lib, btn, [(0, t) for t in range(0, 5000, 10)])
    assert set(events) == {BTN_NONE}


def test_short_press_fires_once_on_release(lib):
    btn = make_button(lib)
    samples = [(0, 0)]
    samples += [(1, t) for t in range(100, 400, 10)]      # 300 ms drzanja
    samples += [(0, t) for t in range(400, 600, 10)]
    events = feed(lib, btn, samples)
    assert events.count(BTN_SHORT) == 1
    assert BTN_LONG not in events


def test_long_press_fires_once_while_still_held(lib):
    btn = make_button(lib)
    samples = [(0, 0)]
    samples += [(1, t) for t in range(100, 3000, 10)]
    events = feed(lib, btn, samples)
    assert events.count(BTN_LONG) == 1
    assert BTN_SHORT not in events
    # javlja se cim se prag prekoraci, ne tek na pustanju
    first_long = next(i for i, e in enumerate(events) if e == BTN_LONG)
    assert samples[first_long][1] == pytest.approx(100 + LONG_PRESS_MS, abs=20)


def test_long_press_release_does_not_add_short(lib):
    btn = make_button(lib)
    samples = [(0, 0)]
    samples += [(1, t) for t in range(100, 2000, 10)]
    samples += [(0, t) for t in range(2000, 2300, 10)]
    events = feed(lib, btn, samples)
    assert events.count(BTN_LONG) == 1
    assert BTN_SHORT not in events


def test_bounce_shorter_than_debounce_is_ignored(lib):
    btn = make_button(lib)
    # 20 ms odskoka pri debounceu od 30 ms
    samples = [(0, 0), (1, 100), (0, 115), (1, 125), (0, 140)]
    samples += [(0, t) for t in range(150, 400, 10)]
    events = feed(lib, btn, samples)
    assert set(events) == {BTN_NONE}


def test_press_survives_bounce_then_registers(lib):
    btn = make_button(lib)
    samples = [(0, 0), (1, 100), (0, 110), (1, 120)]
    samples += [(1, t) for t in range(130, 400, 10)]
    samples += [(0, t) for t in range(400, 600, 10)]
    events = feed(lib, btn, samples)
    assert events.count(BTN_SHORT) == 1


def test_button_held_at_boot_does_not_start_anything(lib):
    """Zaglavljen ili slucajno pritisnut taster pri ukljucenju ne pokrece ucenje."""
    btn = make_button(lib, initial_pressed=1, now=0)
    events = feed(lib, btn, [(1, t) for t in range(0, 5000, 10)])
    assert set(events) == {BTN_NONE}
    # tek poslije pustanja i novog pritiska tok pocinje
    events = feed(lib, btn, [(0, t) for t in range(5000, 5200, 10)])
    assert set(events) == {BTN_NONE}
    events = feed(lib, btn, [(1, t) for t in range(5200, 5500, 10)] +
                            [(0, t) for t in range(5500, 5700, 10)])
    assert events.count(BTN_SHORT) == 1


def test_two_presses_give_two_events(lib):
    btn = make_button(lib)
    samples = []
    for base in (100, 1000):
        samples += [(1, t) for t in range(base, base + 300, 10)]
        samples += [(0, t) for t in range(base + 300, base + 600, 10)]
    events = feed(lib, btn, samples)
    assert events.count(BTN_SHORT) == 2


def test_uninitialised_button_is_fail_closed(lib):
    btn = Button()
    assert lib.asd_button_update(ctypes.byref(btn), 1, 10_000) == BTN_NONE


def test_null_button_is_fail_closed(lib):
    assert lib.asd_button_update(None, 1, 0) == BTN_NONE


def test_counter_wraparound_is_handled(lib):
    """uint32 milisekunde se prelijevaju poslije ~49 dana neprekidnog rada."""
    start = 0xFFFFFF00
    btn = make_button(lib, now=start)
    samples = [(1, (start + d) & 0xFFFFFFFF) for d in range(0, 2000, 10)]
    events = feed(lib, btn, samples)
    assert events.count(BTN_LONG) == 1


# --- rezim lampice ----------------------------------------------------------

@pytest.mark.parametrize("state", ALL_STATES)
def test_terminal_state_always_shows_fault(lib, state):
    for stage in (STAGE_IDLE, STAGE_LEARNING, STAGE_MONITORING):
        mode = lib.asd_ui_mode(stage, state)
        if state in TERMINAL:
            assert mode == UI_FAULT
        else:
            assert mode != UI_FAULT


def test_mode_mapping(lib):
    assert lib.asd_ui_mode(STAGE_IDLE, NO_MACHINE) == UI_IDLE
    assert lib.asd_ui_mode(STAGE_LEARNING, NO_MACHINE) == UI_LEARNING
    assert lib.asd_ui_mode(STAGE_MONITORING, CALIBRATED_NORMAL) == UI_READY
    assert lib.asd_ui_mode(STAGE_MONITORING, ANOMALY) == UI_ALARM


def test_monitoring_without_a_machine_is_never_ready(lib):
    """Ventilator je stao: lampica ne smije govoriti 'spreman, nadzirem'."""
    assert lib.asd_ui_mode(STAGE_MONITORING, NO_MACHINE) == UI_IDLE


def test_ready_requires_an_actually_calibrated_state(lib):
    ready_states = [s for s in ALL_STATES
                    if lib.asd_ui_mode(STAGE_MONITORING, s) == UI_READY]
    assert ready_states == [CALIBRATED_NORMAL]


def test_ready_is_solid_and_alarm_is_dark(lib):
    ts = list(range(0, 6000, 7))
    assert all(lib.asd_indicator_level(UI_READY, t) == 1 for t in ts)
    assert all(lib.asd_indicator_level(UI_ALARM, t) == 0 for t in ts)


def rising_edges(lib, mode, span_ms):
    """Broj uzlaznih ivica kroz `span_ms`.

    Mjeri se od t=1, jer ivica u t=0 nema prethodni uzorak s kojim bi se
    poredila; time svaka prebrojana ivica ima definisan prethodnik.
    """
    return sum(1 for t in range(1, span_ms + 1)
               if lib.asd_indicator_level(mode, t) == 1
               and lib.asd_indicator_level(mode, t - 1) == 0)


def test_learning_blinks_fast(lib):
    ts = list(range(0, 4000))
    on = sum(lib.asd_indicator_level(UI_LEARNING, t) for t in ts)
    assert on == pytest.approx(len(ts) / 2, rel=0.05)
    assert rising_edges(lib, UI_LEARNING, 4000) == 20      # 5 Hz kroz 4 s


def test_idle_is_a_rare_short_flash(lib):
    ts = list(range(0, 8000))
    on = sum(lib.asd_indicator_level(UI_IDLE, t) for t in ts)
    assert on / len(ts) < 0.1
    assert rising_edges(lib, UI_IDLE, 8000) == 4           # 1 bljesak na 2 s


def test_fault_is_a_double_flash(lib):
    assert rising_edges(lib, UI_FAULT, 4800) == 6          # 3 perioda x 2 bljeska


def test_every_mode_has_a_distinct_pattern(lib):
    """Golim okom razlucivo: nijedna dva rezima ne daju isti niz kroz 4 s."""
    ts = list(range(0, 4000))
    patterns = {m: tuple(lib.asd_indicator_level(m, t) for t in ts) for m in ALL_MODES}
    assert len(set(patterns.values())) == len(ALL_MODES)


def test_indicator_is_a_pure_function_of_time(lib):
    ts = list(range(0, 3000, 3))
    for mode in ALL_MODES:
        first = [lib.asd_indicator_level(mode, t) for t in ts]
        second = [lib.asd_indicator_level(mode, t) for t in reversed(ts)]
        assert first == list(reversed(second))


# --- komande ----------------------------------------------------------------

def test_no_button_event_is_never_a_command(lib):
    for mode in ALL_MODES:
        assert lib.asd_ui_command(mode, BTN_NONE) == CMD_NONE


def test_short_press_never_discards_a_learned_centre(lib):
    """Jedno od dva pravila koja modul nosi u kodu."""
    for mode in (UI_READY, UI_ALARM, UI_LEARNING):
        assert lib.asd_ui_command(mode, BTN_SHORT) == CMD_NONE


def test_idle_starts_on_any_press(lib):
    assert lib.asd_ui_command(UI_IDLE, BTN_SHORT) == CMD_START
    assert lib.asd_ui_command(UI_IDLE, BTN_LONG) == CMD_START


def test_fault_restarts_on_any_press(lib):
    assert lib.asd_ui_command(UI_FAULT, BTN_SHORT) == CMD_START
    assert lib.asd_ui_command(UI_FAULT, BTN_LONG) == CMD_START


def test_long_press_aborts_learning_but_short_does_not(lib):
    assert lib.asd_ui_command(UI_LEARNING, BTN_LONG) == CMD_ABORT
    assert lib.asd_ui_command(UI_LEARNING, BTN_SHORT) == CMD_NONE


def test_relearn_requires_a_long_press(lib):
    for mode in (UI_READY, UI_ALARM):
        assert lib.asd_ui_command(mode, BTN_LONG) == CMD_START
        assert lib.asd_ui_command(mode, BTN_SHORT) == CMD_NONE


def test_abort_is_only_reachable_from_learning(lib):
    for mode in ALL_MODES:
        for event in (BTN_SHORT, BTN_LONG):
            if lib.asd_ui_command(mode, event) == CMD_ABORT:
                assert mode == UI_LEARNING


def test_discard_flag_marks_exactly_the_modes_that_hold_a_centre(lib):
    for mode in ALL_MODES:
        discards = lib.asd_ui_command_discards_calibration(mode, CMD_START)
        assert bool(discards) == (mode in (UI_READY, UI_ALARM))


def test_non_start_commands_never_discard(lib):
    for mode in ALL_MODES:
        for cmd in (CMD_NONE, CMD_ABORT):
            assert lib.asd_ui_command_discards_calibration(mode, cmd) == 0


def test_names_are_stable_ascii(lib):
    assert lib.asd_ui_mode_name(UI_READY) == b"READY"
    assert lib.asd_button_event_name(BTN_LONG) == b"LONG"
    assert lib.asd_ui_command_name(CMD_START) == b"START_LEARNING"
    assert lib.asd_flow_stage_name(STAGE_MONITORING) == b"MONITORING"
    for mode in ALL_MODES:
        assert lib.asd_ui_mode_name(mode).decode("ascii").isupper()


def test_unknown_enum_values_are_named_not_crashing(lib):
    assert lib.asd_ui_mode_name(99) == b"UNKNOWN_MODE"
    assert lib.asd_button_event_name(99) == b"UNKNOWN_EVENT"
    assert lib.asd_ui_command_name(99) == b"UNKNOWN_COMMAND"
    assert lib.asd_flow_stage_name(99) == b"UNKNOWN_STAGE"


def test_unknown_mode_is_fail_closed_for_commands(lib):
    assert lib.asd_ui_command(99, BTN_LONG) == CMD_NONE


# --- druga lampica: crvena, samo alarm --------------------------------------

def test_red_led_is_on_only_during_an_alarm(lib):
    for mode in ALL_MODES:
        levels = {lib.asd_alarm_level(mode, t) for t in range(0, 4000, 7)}
        if mode == UI_ALARM:
            assert levels == {1}, "u alarmu crvena stalno svijetli"
        elif mode == UI_FAULT:
            assert levels == {0, 1}, "u kvaru crvena treperi"
        else:
            assert levels == {0}, f"crvena ne smije svijetliti u {mode}"


def test_the_two_leds_are_never_both_dark_except_while_idle_or_learning(lib):
    """Kljucni razlog za drugu lampicu: 'ugasena zelena' i 'uredjaj mrtav' se
    inace ne razlikuju. U alarmu i u kvaru bar jedna uvijek gori."""
    for mode in (UI_ALARM, UI_FAULT, UI_READY):
        for t in range(0, 4000, 3):
            green = lib.asd_indicator_level(mode, t)
            red = lib.asd_alarm_level(mode, t)
            assert green or red, (mode, t)


def test_fault_drives_the_two_leds_in_antiphase(lib):
    for t in range(0, 3200, 3):
        green = lib.asd_indicator_level(UI_FAULT, t)
        red = lib.asd_alarm_level(UI_FAULT, t)
        assert green != red


def test_alarm_leds_are_unambiguous_against_ready(lib):
    """READY i ALARM se razlikuju na obje lampice, ne samo na jednoj."""
    for t in range(0, 2000, 11):
        assert (lib.asd_indicator_level(UI_READY, t),
                lib.asd_alarm_level(UI_READY, t)) == (1, 0)
        assert (lib.asd_indicator_level(UI_ALARM, t),
                lib.asd_alarm_level(UI_ALARM, t)) == (0, 1)


def test_observation_hold_has_own_ui_and_requires_long_relearn(lib):
    assert lib.asd_ui_mode(STAGE_MONITORING, OBSERVATION_HOLD) == UI_HOLD
    assert lib.asd_ui_mode_name(UI_HOLD) == b"OBSERVATION_HOLD"
    assert lib.asd_indicator_level(UI_HOLD, 0) == 1
    assert lib.asd_indicator_level(UI_HOLD, 500) == 0
    assert lib.asd_alarm_level(UI_HOLD, 0) == 0
    assert lib.asd_ui_command(UI_HOLD, BTN_SHORT) == CMD_NONE
    assert lib.asd_ui_command(UI_HOLD, BTN_LONG) == CMD_START
    assert lib.asd_ui_command_discards_calibration(UI_HOLD, CMD_START) == 1
