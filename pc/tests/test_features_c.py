"""PC↔C unit test featura (plan, rizik B1): isti signal kroz numpy pipeline
(asd/features.py) i kroz C implementaciju (firmware features_c.c, ctypes).

Kriterijum iz plana: max |razlika| log-mel vrijednosti < 1e-3 dB.
Pokretanje (iz pc/): python -m pytest tests/ -v   (ili direktno: python tests/test_features_c.py)
Zahtijeva C kompajler (gcc/clang/cl) u PATH-u — test se preskače ako ga nema.
"""
from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asd import features  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FW_MAIN = ROOT / "firmware" / "esp32s3_asd" / "main"


def build_lib(tmpdir: Path) -> Path | None:
    src = FW_MAIN / "features_c.c"
    if not (FW_MAIN / "mel_data.h").exists():
        subprocess.run([sys.executable, str(ROOT / "pc" / "tools" / "gen_mel_header.py")], check=True)
    out = tmpdir / ("features_c.dll" if sys.platform == "win32" else "features_c.so")
    for cc in ("gcc", "clang"):
        if shutil.which(cc):
            args = [cc, "-O2", "-shared", "-o", str(out), str(src), f"-I{FW_MAIN}"]
            if sys.platform != "win32":
                args.append("-lm")
            r = subprocess.run(args, capture_output=True, text=True)
            if r.returncode == 0:
                return out
            print(r.stderr)
    return None


@pytest.fixture(scope="module")
def clib(tmp_path_factory):
    lib_path = build_lib(tmp_path_factory.mktemp("cbuild"))
    if lib_path is None:
        pytest.skip("nema C kompajlera (gcc/clang) u PATH-u")
    lib = ctypes.CDLL(str(lib_path))
    lib.asd_features_init()
    lib.asd_logmel.restype = ctypes.c_int
    return lib


def _c_logmel(lib, y: np.ndarray) -> np.ndarray:
    max_frames = 1 + (len(y) - features.N_FFT) // features.HOP
    out = np.zeros((max_frames, features.N_MELS), dtype=np.float32)
    n = lib.asd_logmel(
        y.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), ctypes.c_int(len(y)),
        out.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), ctypes.c_int(max_frames))
    return out[:n]


@pytest.mark.parametrize("kind", ["noise", "sine", "chirp_loud"])
def test_pc_vs_c_logmel(clib, kind):
    """Sintetički signali SA šumnim podom (-60 dB): čisti ton bez šuma ima mel
    binove na float32 FFT error flooru gdje se numpy i C FFT legitimno razilaze
    ispod -100 dB — realan mašinski zvuk tamo nikad nije (rizik B2). Pravi
    kriterijum za deployment je test_pc_vs_c_real_wav."""
    rng = np.random.default_rng(42)
    t = np.arange(features.SR * 2, dtype=np.float32) / features.SR
    floor = rng.standard_normal(len(t)).astype(np.float32) * 1e-3
    if kind == "noise":
        y = rng.standard_normal(len(t)).astype(np.float32) * 0.1
    elif kind == "sine":
        y = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32) + floor
    else:  # glasan chirp — hvata razilaženje na velikim amplitudama
        y = 0.95 * np.sin(2 * np.pi * (100 + 3000 * t) * t).astype(np.float32) + floor

    ref = features.log_mel(y)
    c = _c_logmel(clib, y)
    assert c.shape == ref.shape
    max_diff = float(np.max(np.abs(ref - c)))
    print(f"[{kind}] max|PC-C| = {max_diff:.2e} dB")
    # tonalni signali: 1e-2 (razlika živi u sidelobe binovima >60 dB ispod pika);
    # šum i realni klipovi drže strogi 1e-3 (vidi test_pc_vs_c_real_wav)
    tol = 1e-3 if kind == "noise" else 1e-2
    assert max_diff < tol, f"PC vs C featuri se razilaze: {max_diff}"


def test_pc_vs_c_real_wav(clib):
    """Glavni kriterijum iz plana (sedmica 5): realan DCASE klip kroz oba
    pipeline-a, max |razlika| < 1e-3 dB."""
    import soundfile as sf
    wavs = sorted((ROOT / "data" / "dcase2026_dev" / "fan" / "train").glob("*.wav"))
    if not wavs:
        pytest.skip("fan dataset nije raspakovan")
    y, sr = sf.read(wavs[0], dtype="float32", always_2d=True)
    y = np.ascontiguousarray(y[:, 0])
    assert sr == features.SR
    ref = features.log_mel(y)
    c = _c_logmel(clib, y)
    max_diff = float(np.max(np.abs(ref - c)))
    print(f"[real: {wavs[0].name}] max|PC-C| = {max_diff:.2e} dB")
    assert max_diff < 1e-3


def test_streaming_equals_batch(clib):
    """Streaming put (hop-po-hop, edge arhitektura) mora dati BIT-IDENTIČNE
    featuri kao batch put — isti kod, isti uzorci po frejmu."""
    import soundfile as sf
    wavs = sorted((ROOT / "data" / "dcase2026_dev" / "fan" / "train").glob("*.wav"))
    if not wavs:
        pytest.skip("fan dataset nije raspakovan")
    y, _ = sf.read(wavs[0], dtype="float32", always_2d=True)
    y = np.ascontiguousarray(y[:, 0])

    batch = _c_logmel(clib, y)

    class Stream(ctypes.Structure):
        _fields_ = [("window", ctypes.c_float * features.N_FFT),
                    ("filled", ctypes.c_int),
                    ("lm_hist", (ctypes.c_float * features.N_MELS) * features.N_FRAMES),
                    ("lm_count", ctypes.c_int)]

    clib.asd_stream_push_hop.restype = ctypes.c_int
    s = Stream()
    clib.asd_stream_reset(ctypes.byref(s))
    frames = []
    n_hops = len(y) // features.HOP
    for h in range(n_hops):
        chunk = np.ascontiguousarray(y[h * features.HOP:(h + 1) * features.HOP])
        if clib.asd_stream_push_hop(ctypes.byref(s),
                                    chunk.ctypes.data_as(ctypes.POINTER(ctypes.c_float))):
            idx = (s.lm_count - 1) % features.N_FRAMES
            frames.append(np.array(s.lm_hist[idx], dtype=np.float32))
    stream = np.stack(frames)

    n = min(len(batch), len(stream))
    assert n >= len(batch) - 1
    max_diff = float(np.max(np.abs(batch[:n] - stream[:n])))
    print(f"[streaming] frames={n} max|batch-stream| = {max_diff:.2e}")
    assert max_diff == 0.0, "streaming i batch moraju biti bit-identicni"


def test_numpy_vs_librosa_melfb():
    """Sanity: naša STFT putanja vs librosa (center=False) na istom signalu."""
    import librosa
    rng = np.random.default_rng(1)
    y = rng.standard_normal(features.SR).astype(np.float32) * 0.1
    S = librosa.stft(y, n_fft=features.N_FFT, hop_length=features.HOP,
                     window="hann", center=False)
    mel_l = features.mel_filterbank() @ (np.abs(S) ** 2)
    ref = 10.0 * np.log10(mel_l.T + features.LOG_EPS)
    ours = features.log_mel(y)
    assert np.max(np.abs(ref - ours)) < 1e-3


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-s"]))
