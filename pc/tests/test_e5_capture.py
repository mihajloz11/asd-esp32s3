import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("e5_capture", Path(__file__).parents[1] / "tools" / "e5_capture.py")
e5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e5)


def fixture():
    lines = ["E5BEGIN protocol=e5-v1 config=0x4123 cal=1024 shunt_mohm=100 samples=6001 errors=0 start_us=1000000 end_us=61000000"]
    for i in range(6001):
        t = 1000000 + i * 10000
        lines.append(f"E5DATA index={i} trigger_us={t} ready_us={t+2500} bus_uv=3300000 "
                     "shunt_nv=10000000 current_ua=100000 power_uw=330000 phase=OTHER sequence=0 mask=0x0008")
    lines += ["E5TIME phase=OTHER duration_us=60000000", "E5END samples=6001 errors=0"]
    meta = dict(transport="uart", external_power=True, wiring_verified=True,
                dmm_v=3.3, reference_current_ma=100, reference_tolerance_ma=1)
    return "\n".join(lines), meta


def test_constant_power_units_and_integral():
    text, meta = fixture()
    rows, summary = e5.analyze(text, meta)
    assert len(rows) == 6001
    assert summary["status"] == "validated_total_energy"
    assert abs(summary["energy_mj"] - 19800) < 1e-6
    assert abs(summary["mean_power_mw"] - 330) < 1e-6


def test_usb_cannot_be_a_valid_energy_result():
    text, meta = fixture()
    meta["transport"] = "usb"
    _, summary = e5.analyze(text, meta)
    assert summary["energy_mj"] is None
    assert "not_external_power_uart" in summary["issues"]


def test_truncated_log_is_rejected():
    text, meta = fixture()
    _, summary = e5.analyze(text.rsplit("E5END", 1)[0], meta)
    assert "missing_begin_or_end" in summary["issues"]
    assert summary["energy_mj"] is None


def test_bad_vbus_reference_is_rejected():
    text, meta = fixture()
    meta["dmm_v"] = 3.1
    _, summary = e5.analyze(text, meta)
    assert "vbus_dmm_check_missing_or_over_10mv" in summary["issues"]


def test_phase_boundary_is_not_assigned_to_score():
    text, meta = fixture()
    text = text.replace("phase=OTHER sequence=0", "phase=SCORE sequence=2", 1)
    _, summary = e5.analyze(text, meta)
    assert "SCORE" not in summary["stable_interval_estimates"]
    assert summary["stable_interval_estimates"]["MIXED"]["covered_s"] == 0.01


def test_duplicate_or_overflow_samples_rejected():
    text, meta = fixture()
    text = text.replace("index=10 ", "index=9 ").replace("mask=0x0008", "mask=0x000c", 1)
    _, summary = e5.analyze(text, meta)
    assert "sample_sequence_gap" in summary["issues"]
    assert "invalid_conversion" in summary["issues"]
    assert summary["energy_mj"] is None


def test_saved_run_can_be_downloaded_over_usb_but_needs_external_power_attestation():
    text, meta = fixture()
    meta.update(transport="usb", command="E5SAVED")
    assert e5.analyze(text, meta)[1]["status"] == "validated_total_energy"
    meta["external_power"] = False
    assert e5.analyze(text, meta)[1]["energy_mj"] is None


def test_arm_and_disarm_acknowledgement():
    assert e5.analyze("E5ARM result=ESP_OK delay_s=15 next=POWERON", {})[1]["status"] == "armed"
    assert e5.analyze("E5ARM result=ESP_OK delay_s=0 next=POWERON", {})[1]["status"] == "disarmed"
    assert e5.analyze("E5ARM result=ESP_FAIL delay_s=15 next=POWERON", {})[1]["status"] == "arm_failed"


def test_large_sampling_gap_is_not_integrated_or_accepted():
    text, meta = fixture()
    lines = text.splitlines()
    text = "\n".join(line for line in lines if not (line.startswith("E5DATA ") and 100 <= int(e5.fields(line)["index"]) < 120))
    summary = e5.analyze(text, meta)[1]
    assert "nonmonotonic_or_large_gap" in summary["issues"]
    assert summary["energy_mj"] is None


def test_boot_before_saved_download_is_not_a_reset_during_measurement():
    text, meta = fixture()
    meta.update(transport="usb", command="E5SAVED")
    summary = e5.analyze("rst:0x15 (USB_UART_CHIP_RESET)\n" + text, meta)[1]
    assert summary["status"] == "validated_total_energy"
    text = "E5START duration_s=60\nrst:0x1 (POWERON)\n" + text
    assert "device_reset_in_capture" in e5.analyze(text, meta)[1]["issues"]


def test_wrong_calibration_or_lost_phase_record_rejects_energy():
    text, meta = fixture()
    assert "unexpected_measurement_configuration" in e5.analyze(text.replace("cal=1024", "cal=2048"), meta)[1]["issues"]
    assert "phase_time_accounting_mismatch" in e5.analyze(text.replace("duration_us=60000000", "duration_us=50000000"), meta)[1]["issues"]
