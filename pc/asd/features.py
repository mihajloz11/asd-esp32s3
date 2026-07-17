"""Log-mel feature extraction — DCASE Task 2 baseline front-end.

Parametri prate zvanični baseline: n_fft=1024 (64 ms @ 16 kHz), hop=512 (50 %),
n_mels=128, power=2, log-mel = (20/power)*log10(mel + eps), P=5 konkateniranih
frejmova -> vektor dimenzije 640.

Namjerna odstupanja od librosa defaulta (dokumentovano u radu, pogl. 5):
  - center=False (bez reflect paddinga) — na uređaju nema paddinga, PC mora isto
  - eps = 1e-12 (float32-representable) umjesto sys.float_info.epsilon

Mel filterbank se uzima iz librosa.filters.mel (Slaney, kao baseline) i IDENTIČNA
matrica se eksportuje u C header — PC i C dijele iste težine po konstrukciji.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import get_window

SR = 16000
N_FFT = 1024
HOP = 512
N_MELS = 128
POWER = 2.0
N_FRAMES = 5  # P
LOG_EPS = 1e-12
INPUT_DIM = N_MELS * N_FRAMES  # 640

_mel_fb_cache: dict[tuple, np.ndarray] = {}


def mel_filterbank(sr: int = SR, n_fft: int = N_FFT, n_mels: int = N_MELS) -> np.ndarray:
    """Slaney mel filterbank (librosa-kompatibilan), shape (n_mels, n_fft//2+1), float32."""
    key = (sr, n_fft, n_mels)
    if key not in _mel_fb_cache:
        import librosa
        fb = librosa.filters.mel(sr=sr, n_fft=n_fft, n_mels=n_mels, fmin=0.0, fmax=sr / 2)
        _mel_fb_cache[key] = fb.astype(np.float32)
    return _mel_fb_cache[key]


def hann_window(n_fft: int = N_FFT) -> np.ndarray:
    """Periodični (fftbins=True) Hann — isti kao librosa default."""
    return get_window("hann", n_fft, fftbins=True).astype(np.float32)


def stft_power(y: np.ndarray, n_fft: int = N_FFT, hop: int = HOP) -> np.ndarray:
    """Power spektrogram, center=False. Shape (n_frames, n_fft//2+1), float32."""
    y = np.asarray(y, dtype=np.float32)
    if len(y) < n_fft:
        raise ValueError(f"signal too short: {len(y)} < {n_fft}")
    n_frames = 1 + (len(y) - n_fft) // hop
    win = hann_window(n_fft)
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n_frames)[:, None]
    frames = y[idx] * win[None, :]
    spec = np.fft.rfft(frames, n=n_fft, axis=1)
    return (np.abs(spec) ** 2).astype(np.float32)


def log_mel(y: np.ndarray, sr: int = SR) -> np.ndarray:
    """Log-mel spektrogram. Shape (n_frames, n_mels), float32."""
    if sr != SR:
        raise ValueError(f"expected {SR} Hz, got {sr} — resample upstream")
    p = stft_power(y)
    mel = p @ mel_filterbank().T
    return ((20.0 / POWER) * np.log10(mel + LOG_EPS)).astype(np.float32)


def frame_vectors(lm: np.ndarray, n_frames: int = N_FRAMES) -> np.ndarray:
    """Konkatenacija P uzastopnih log-mel frejmova -> (T-P+1, P*n_mels).

    Redoslijed: [frame_t | frame_t+1 | ... | frame_t+P-1] (frame-major),
    identično DCASE baseline-u i C implementaciji.
    """
    t, f = lm.shape
    n_vec = t - n_frames + 1
    if n_vec < 1:
        raise ValueError("clip too short for frame stacking")
    out = np.empty((n_vec, n_frames * f), dtype=np.float32)
    for i in range(n_frames):
        out[:, i * f:(i + 1) * f] = lm[i:i + n_vec]
    return out


def wav_to_vectors(path: str) -> np.ndarray:
    """WAV fajl -> matrica ulaznih vektora (n_vec, 640)."""
    import soundfile as sf
    y, sr = sf.read(path, dtype="float32", always_2d=True)
    y = y[:, 0]  # mono / prvi kanal
    if sr != SR:
        import librosa
        y = librosa.resample(y, orig_sr=sr, target_sr=SR)
    return frame_vectors(log_mel(y))
