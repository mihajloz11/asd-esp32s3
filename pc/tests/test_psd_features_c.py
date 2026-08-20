"""PC<->C verifikacija novog PSD front-enda i Mahalanobis score-a."""
from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import data  # noqa: E402
from tools.bench_periodicity import periodic_features  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FW_MAIN = ROOT / "firmware" / "esp32s3_asd" / "main"
FAN_DIR = ROOT / "data" / "dcase2026_dev" / "fan"


class PsdSidecar(ctypes.Structure):
    _fields_ = [
        ("segments", ctypes.c_int),
        ("group_segments", ctypes.c_int * 5),
        ("group_feature", (ctypes.c_float * 96) * 5),
    ]


def fan_clips_or_skip(split: str = "train"):
    """DCASE skup je gitignoreovan, pa ga na CI runneru nema.

    `data.list_clips` baca FileNotFoundError kad direktorijum ne postoji, dakle
    PRIJE nego sto se stigne do provjere `if not clips`. Zato se postojanje
    provjerava ovdje, prije poziva -- inace test pada umjesto da se preskoci.
    """
    if not (FAN_DIR / split).is_dir():
        pytest.skip("fan dataset nije raspakovan")
    clips = data.list_clips(FAN_DIR, split)
    if not clips:
        pytest.skip("fan dataset nije raspakovan")
    return clips


@pytest.fixture(scope="module")
def clib(tmp_path_factory):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema C kompajlera")
    out = tmp_path_factory.mktemp("psd_cbuild") / "psd_features_c.dll"
    args = [cc, "-O2", "-shared", "-o", str(out),
            str(FW_MAIN / "psd_features_c.c"), f"-I{FW_MAIN}"]
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    lib = ctypes.CDLL(str(out))
    lib.asd_psd_init()
    lib.asd_psd_extract.restype = ctypes.c_int
    lib.asd_psd_score.restype = ctypes.c_float
    lib.asd_psd_stream_push_hop.restype = ctypes.c_int
    lib.asd_psd_stream_finish.restype = ctypes.c_int
    lib.asd_psd_stream_finish_sidecar.restype = ctypes.c_int
    return lib


def _synthetic_clip() -> np.ndarray:
    n = 39 * 4096
    t = np.arange(n, dtype=np.float64) / 16000.0
    signal = (
        0.35 * np.sin(2 * np.pi * 173.0 * t)
        + 0.12 * np.sin(2 * np.pi * 521.0 * t)
        + 0.03 * np.sin(2 * np.pi * (83.0 + 0.2 * t) * t)
    )
    return np.ascontiguousarray(signal, dtype=np.float32)


def test_psd_sidecar_keeps_final_feature_bit_identical_and_groups_38_segments(clib):
    y = _synthetic_clip()
    ptr = ctypes.POINTER(ctypes.c_float)

    clib.asd_psd_stream_reset()
    for start in range(0, len(y), 4096):
        clib.asd_psd_stream_push_hop(y[start:start + 4096].ctypes.data_as(ptr))
    canonical = np.zeros(96, np.float32)
    assert clib.asd_psd_stream_finish(canonical.ctypes.data_as(ptr)) == 38

    clib.asd_psd_stream_reset_sidecar()
    for start in range(0, len(y), 4096):
        clib.asd_psd_stream_push_hop(y[start:start + 4096].ctypes.data_as(ptr))
    research_final = np.zeros(96, np.float32)
    sidecar = PsdSidecar()
    assert clib.asd_psd_stream_finish_sidecar(
        research_final.ctypes.data_as(ptr), ctypes.byref(sidecar),
    ) == 38

    assert np.array_equal(canonical, research_final)
    assert sidecar.segments == 38
    assert list(sidecar.group_segments) == [8, 8, 8, 7, 7]
    groups = np.ctypeslib.as_array(sidecar.group_feature).reshape(5, 96)
    assert np.isfinite(groups).all()

    for group, (start_segment, count) in enumerate(
        zip((0, 8, 16, 24, 31), (8, 8, 8, 7, 7), strict=True)
    ):
        first = start_segment * 4096
        group_signal = np.ascontiguousarray(
            y[first:first + (count + 1) * 4096], dtype=np.float32,
        )
        expected = np.zeros(96, np.float32)
        got_segments = clib.asd_psd_extract(
            group_signal.ctypes.data_as(ptr), ctypes.c_int(len(group_signal)),
            expected.ctypes.data_as(ptr),
        )
        assert got_segments == count
        # Sidecar sabira po bandu nakon svakog segmenta da bi zauzeo samo
        # 5x96, dok batch prvo sabira po FFT binu. Razlika je samo float32
        # redoslijed sabiranja; kanonski finalni vektor iznad ostaje bit-identican.
        assert float(np.max(np.abs(groups[group] - expected))) < 5e-5


def test_psd_real_wav_pc_vs_c(clib):
    clips = fan_clips_or_skip()
    path = clips[0].path
    y, sr = sf.read(path, dtype="float32", always_2d=True)
    assert sr == 16000
    y = np.ascontiguousarray(y[:, 0])
    out = np.zeros(96, np.float32)
    segments = clib.asd_psd_extract(
        y.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), ctypes.c_int(len(y)),
        out.ctypes.data_as(ctypes.POINTER(ctypes.c_float)))
    ref = periodic_features(path)["psd_shape"].astype(np.float32)
    max_diff = float(np.max(np.abs(ref - out)))
    print(f"segments={segments} max|PC-C|={max_diff:.3e}")
    assert segments == 38
    assert max_diff < 2e-3


def test_psd_stream_matches_batch(clib):
    """Zivi rad koristi streaming (FFT po hopu, bez bafera od 10 s). Mora dati
    isti rezultat kao batch, inace verifikacija PC<->C ne vazi za firmware."""
    clips = fan_clips_or_skip()
    y, sr = sf.read(clips[0].path, dtype="float32", always_2d=True)
    assert sr == 16000
    y = np.ascontiguousarray(y[:, 0])
    ptr = ctypes.POINTER(ctypes.c_float)

    batch = np.zeros(96, np.float32)
    n_batch = clib.asd_psd_extract(y.ctypes.data_as(ptr), ctypes.c_int(len(y)),
                                   batch.ctypes.data_as(ptr))

    hop = 4096
    clib.asd_psd_stream_reset()
    for start in range(0, len(y) - hop + 1, hop):
        chunk = np.ascontiguousarray(y[start:start + hop])
        clib.asd_psd_stream_push_hop(chunk.ctypes.data_as(ptr))
    stream = np.zeros(96, np.float32)
    n_stream = clib.asd_psd_stream_finish(stream.ctypes.data_as(ptr))

    max_diff = float(np.max(np.abs(batch - stream)))
    print(f"segmenti batch={n_batch} stream={n_stream} max|batch-stream|={max_diff:.3e}")
    assert n_stream == n_batch
    assert max_diff == 0.0


def test_psd_score_pc_vs_c(clib):
    model_path = ROOT / "models" / "fan_psd_shape.npz"
    if not model_path.exists():
        # Generator cita DCASE skup; bez njega nema sta da se generise.
        if not (FAN_DIR / "train").is_dir():
            pytest.skip("fan dataset nije raspakovan")
        subprocess.run([sys.executable, str(ROOT / "pc" / "tools" /
                                            "gen_psd_model_header.py")], check=True)
    model = np.load(model_path)
    mean = np.ascontiguousarray(model["mean"], np.float32)
    std = np.ascontiguousarray(model["std"], np.float32)
    precision = np.ascontiguousarray(model["precision"], np.float32)
    feature = np.ascontiguousarray(mean + 0.25 * std, np.float32)
    center = np.ascontiguousarray(np.linspace(-0.1, 0.1, 96), np.float32)
    delta = (feature - mean) / std - center
    ref = float(delta @ precision @ delta)
    ptr = ctypes.POINTER(ctypes.c_float)
    got = clib.asd_psd_score(
        feature.ctypes.data_as(ptr), mean.ctypes.data_as(ptr), std.ctypes.data_as(ptr),
        precision.ctypes.data_as(ptr), center.ctypes.data_as(ptr), ctypes.c_int(96))
    rel = abs(got - ref) / max(abs(ref), 1e-12)
    print(f"score C={got:.7g} PC={ref:.7g} rel={rel:.3e}")
    assert rel < 2e-6
