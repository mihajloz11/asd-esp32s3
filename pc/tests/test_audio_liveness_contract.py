"""Static guards for the production I2S bounded-read contract."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "firmware" / "esp32s3_asd" / "main"


def test_audio_data_path_has_total_deadline_and_no_infinite_wait() -> None:
    source = (MAIN / "audio_i2s.c").read_text(encoding="utf-8")
    header = (MAIN / "audio_i2s.h").read_text(encoding="utf-8")
    assert "esp_err_t audio_read_exact(int16_t *dst, size_t n_samples," in header
    assert "vTaskSetTimeOutState" in source
    assert "xTaskCheckForTimeOut" in source
    assert "AUDIO_I2S_CAPTURE_WAIT_MS" in source
    assert "portMAX_DELAY" not in source


def test_silence_is_not_treated_as_a_read_error() -> None:
    source = (MAIN / "audio_i2s.c").read_text(encoding="utf-8")
    exact = source.split("esp_err_t audio_read_exact", 1)[1].split(
        "size_t audio_read", 1,
    )[0]
    assert "memcpy" in exact
    assert "ESP_OK" in exact
    assert "pcm[" not in exact and "dst[" not in exact


def test_psd_live_maps_bounded_failures_to_named_fail_closed_reasons() -> None:
    source = (MAIN / "psd_live.c").read_text(encoding="utf-8")
    quality = (MAIN / "audio_quality_state.c").read_text(encoding="utf-8")
    assert "audio_read_exact" in source
    assert "ASD_QUALITY_AUDIO_TIMEOUT" in source
    assert "ASD_QUALITY_AUDIO_READ_ERROR" in source
    assert 'return "AUDIO_TIMEOUT"' in quality
    assert 'return "AUDIO_READ_ERROR"' in quality

