"""Eksperimentalni front-end sa nepraznim trakama (ASD_PSD_NONEMPTY_BANDS).

Provjere bez DCASE skupa: C mapa se poklapa sa Python referencom iz
eksperimenta 07.09.2026, obiljezje ne zavisi od pojacanja, zaglavlje nosi
tacno zamrznuti model, a podrazumijevani build ostaje nepromijenjen.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.signal import welch

ROOT = Path(__file__).resolve().parents[2]
FW_MAIN = ROOT / "firmware" / "esp32s3_asd" / "main"
EXPERIMENT = ROOT / "results" / "psd_nonempty" / "2026-09-07"
N_SAMPLES = 39 * 4096


def build(tmp_path_factory, name, defines):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema C kompajlera")
    out = tmp_path_factory.mktemp(name) / ("psd.dll" if sys.platform == "win32" else "psd.so")
    args = [cc, "-O2", "-shared", "-fPIC", "-o", str(out),
            str(FW_MAIN / "psd_features_c.c"), f"-I{FW_MAIN}", *defines]
    if sys.platform == "win32":
        args.remove("-fPIC")
    result = subprocess.run(args, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    lib = ctypes.CDLL(str(out))
    ptr = ctypes.POINTER(ctypes.c_float)
    lib.asd_psd_init()
    lib.asd_psd_extract.argtypes = [ptr, ctypes.c_int, ptr]
    lib.asd_psd_extract.restype = ctypes.c_int
    return lib


@pytest.fixture(scope="module")
def nonempty(tmp_path_factory):
    return build(tmp_path_factory, "psd_nonempty", ["-DASD_PSD_NONEMPTY_BANDS=1"])


@pytest.fixture(scope="module")
def default(tmp_path_factory):
    return build(tmp_path_factory, "psd_default", [])


def c_feature(lib, signal):
    signal = np.ascontiguousarray(signal, np.float32)
    out = np.empty(96, np.float32)
    ptr = ctypes.POINTER(ctypes.c_float)
    assert lib.asd_psd_extract(signal.ctypes.data_as(ptr), len(signal),
                               out.ctypes.data_as(ptr)) == 38
    return out


def nonempty_edges():
    """Pravilo iz evaluate_psd_nonempty.py (frozen_sources.zip)."""
    edges = np.ceil(np.geomspace(10.0, 4000.0, 97) * 8192 / 16000).astype(int)
    for i in range(1, len(edges)):
        edges[i] = max(edges[i], edges[i - 1] + 1)
    return edges


def reference_feature(signal):
    _, power = welch(np.asarray(signal, np.float64), fs=16000, window="hann",
                     nperseg=8192, noverlap=4096, detrend=False, scaling="spectrum")
    edges = nonempty_edges()
    logs = np.log10(np.array([power[a:b].mean() for a, b in zip(edges[:-1], edges[1:])]) + 1e-20)
    return logs - logs.mean()


def noise(seed=20260925):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(N_SAMPLES)
    # obojen sum, da trake nemaju istu snagu
    x = np.convolve(x, [1.0, 0.6, 0.3], mode="same")
    return 0.05 * (x - x.mean())


def test_band_map_covers_bins_6_to_2047_without_gaps():
    edges = nonempty_edges()
    assert len(edges) == 97 and edges[0] == 6 and edges[-1] == 2048
    assert np.all(np.diff(edges) >= 1)
    assert json.loads((EXPERIMENT / "bands.json").read_text())["nonempty_log96"]["edges"] == edges.tolist()


def test_c_matches_python_reference(nonempty):
    x = noise()
    np.testing.assert_allclose(c_feature(nonempty, x), reference_feature(x), atol=2e-4)


def test_feature_does_not_depend_on_gain(nonempty):
    x = noise(7)
    base = c_feature(nonempty, x)
    for gain in (0.25, 0.5, 2.0, 4.0):
        assert np.max(np.abs(c_feature(nonempty, gain * x) - base)) < 1e-4


def test_default_build_keeps_eight_empty_bands(default):
    """Bez zastavice firmware racuna tacno kao do sada: osam traka na -20."""
    feature = c_feature(default, noise(3))
    empty = feature.min()
    assert np.sum(np.isclose(feature, empty, atol=1e-5)) == 8
    # u staroj mapi nivo curi: pojacanje pomjera prazne trake
    shifted = c_feature(default, 2.0 * noise(3))
    assert abs((shifted.min() - empty) + 2 * np.log10(2.0) * 88 / 96) < 1e-3


def header_array(text, name):
    body = re.search(name + r"\[[^\]]*\]\s*=\s*\{(.*?)\};", text, re.S).group(1)
    return np.array([float(v[:-1]) for v in re.findall(r"-?\d+(?:\.\d*)?(?:e[-+]?\d+)?f", body)],
                    dtype=np.float32)


def test_header_carries_the_frozen_model():
    model_path = EXPERIMENT / "nonempty_log96_model.npz"
    frozen = json.loads((EXPERIMENT / "frozen.json").read_text())
    assert hashlib.sha256(model_path.read_bytes()).hexdigest() == frozen["models"]["nonempty_log96"]
    z = np.load(model_path)
    text = (FW_MAIN / "psd_model_nonempty_data.h").read_text(encoding="utf-8")
    for name, key in (("asd_psd_norm_mean", "source_mean"),
                      ("asd_psd_norm_std", "source_scale"),
                      ("asd_psd_precision", "precision")):
        np.testing.assert_array_equal(header_array(text, name),
                                      z[key].astype(np.float32).reshape(-1))
    digest = hashlib.sha256()
    for key in ("source_mean", "source_scale", "precision"):
        digest.update(z[key].astype(np.float32).tobytes())
    assert f'ASD_PSD_MODEL_FINGERPRINT_HEX "{digest.hexdigest()}"' in text


def test_live_firmware_selects_model_by_flag():
    source = (FW_MAIN / "psd_live.c").read_text(encoding="utf-8")
    assert re.search(r'#ifdef ASD_PSD_NONEMPTY_BANDS\s*\n#include "psd_model_nonempty_data.h"\s*\n'
                     r'#else\s*\n#include "psd_model_data.h"', source)
    cmake = (FW_MAIN / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "ENV{ASD_PSD_NONEMPTY_BANDS}" in cmake
