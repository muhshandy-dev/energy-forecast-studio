"""Uji mundur dengan origin bergulir (rolling origin, expanding window).

Di setiap origin, model hanya menerima ``y[:origin]``. Model ``refit="weekly"`` dicocokkan
ulang pada origin hari Senin (atau origin pertama), memakai riwayat sebelum origin itu.
"""

from __future__ import annotations

import copy
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from .config import HORIZON


def _positions(y: pd.Series, origins: pd.DatetimeIndex) -> np.ndarray:
    pos = y.index.get_indexer(origins)
    if (pos < 0).any():
        raise ValueError("ada origin di luar indeks data")
    return pos


def actuals(y: pd.Series, origins: pd.DatetimeIndex) -> np.ndarray:
    pos = _positions(y, origins)
    idx = pos[:, None] + np.arange(HORIZON)[None, :]
    if idx.max() >= len(y):
        raise ValueError("horizon origin terakhir melewati akhir data")
    return y.to_numpy()[idx]


def _predict_chunk(args) -> np.ndarray:
    model, values, cal, positions = args
    out = np.empty((len(positions), HORIZON))
    for i, p in enumerate(positions):
        out[i] = model.predict(values[:p], cal)
    return out


def run_model(
    model, y: pd.Series, cal: pd.DataFrame, origins: pd.DatetimeIndex, workers: int = 1
) -> np.ndarray:
    """Prakiraan (n_origin x 168) untuk satu model."""
    values = y.to_numpy(dtype=float)
    positions = _positions(y, origins)
    if model.refit in ("never", "origin"):
        if workers > 1 and len(positions) > workers:
            chunks = np.array_split(positions, workers * 4)
            with ProcessPoolExecutor(max_workers=workers) as ex:
                parts = list(ex.map(_predict_chunk, [(model, values, cal, c) for c in chunks]))
            return np.vstack(parts)
        return _predict_chunk((model, values, cal, positions))
    if model.refit != "weekly":
        raise ValueError(f"jadwal refit tidak dikenal: {model.refit}")
    out = np.empty((len(positions), HORIZON))
    fitted = False
    for i, (o, p) in enumerate(zip(origins, positions, strict=True)):
        if not fitted or o.dayofweek == 0:
            model.fit(values[:p], cal)
            fitted = True
        out[i] = model.predict(values[:p], cal)
    return out


def run(
    models: list, y: pd.Series, cal: pd.DataFrame, origins: pd.DatetimeIndex, workers: int = 0
) -> dict[str, np.ndarray]:
    workers = workers or min(4, os.cpu_count() or 1)
    return {m.name: run_model(copy.deepcopy(m), y, cal, origins, workers) for m in models}
