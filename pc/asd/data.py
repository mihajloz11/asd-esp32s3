"""DCASE Task 2 dataset discovery i keširanje featura.

Očekivani layout (poslije raspakivanja Zenodo zipova u data/dcase2026_dev/):
    data/dcase2026_dev/<machine>/train/*.wav   (samo normal)
    data/dcase2026_dev/<machine>/test/*.wav    (normal + anomaly)

Imena fajlova: section_00_<source|target>_<train|test>_<normal|anomaly>_XXXX_...wav
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from tqdm import tqdm

from . import features

_FNAME_RE = re.compile(r"section_(\d+)_(source|target)_(?:train|test)_(normal|anomaly)_")


@dataclass
class ClipInfo:
    path: Path
    section: int
    domain: str  # source | target
    label: int   # 0 = normal, 1 = anomaly


def parse_clip(path: Path) -> ClipInfo:
    m = _FNAME_RE.search(path.name)
    if not m:
        raise ValueError(f"unexpected filename: {path.name}")
    return ClipInfo(path, int(m.group(1)), m.group(2), 0 if m.group(3) == "normal" else 1)


def list_clips(machine_dir: Path, split: str) -> list[ClipInfo]:
    d = machine_dir / split
    if not d.is_dir():
        raise FileNotFoundError(d)
    return sorted((parse_clip(p) for p in d.glob("*.wav")), key=lambda c: c.path.name)


def load_features(clips: list[ClipInfo], cache: Path | None = None, desc: str = "features") -> list[np.ndarray]:
    """Featuri po klipu (lista, jer klipovi mogu biti različite dužine). Keš u .npz."""
    if cache is not None and cache.exists():
        z = np.load(cache)
        return [z[f"arr_{i}"] for i in range(len(z.files))]
    feats = [features.wav_to_vectors(str(c.path)) for c in tqdm(clips, desc=desc)]
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, *feats)
    return feats


def fit_norm(train_feats: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Per-dimenziona mean/std normalizacija sa trening skupa (ide u C header)."""
    x = np.concatenate(train_feats, axis=0)
    mean = x.mean(axis=0).astype(np.float32)
    std = x.std(axis=0).astype(np.float32)
    std[std < 1e-6] = 1e-6
    return mean, std
