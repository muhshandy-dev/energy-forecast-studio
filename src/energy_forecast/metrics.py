"""Metrik prakiraan titik dan interval, plus interval kepercayaan bootstrap blok.

Definisi (n = jumlah pasangan origin x jam yang dinilai):
- MAE  = mean |y - ŷ|  (MW)
- MASE = MAE / skala, skala = MAE in-sample seasonal naive mingguan (m = 168) pada
  periode latih awal 2015-2017 (satu konstanta, ditulis di results.json).
- Coverage = proporsi y di dalam [batas bawah, batas atas]; lebar = mean (atas - bawah).
- Interval score (Gneiting & Raftery 2007) untuk level 1 - a:
  (u - l) + (2/a)(l - y)[y < l] + (2/a)(y - u)[y > u]; makin kecil makin baik.
"""

from __future__ import annotations

import numpy as np


def mae(y: np.ndarray, yhat: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(y) - np.asarray(yhat))))


def rmse(y: np.ndarray, yhat: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(yhat)) ** 2)))


def mape(y: np.ndarray, yhat: np.ndarray) -> float:
    y = np.asarray(y)
    return float(np.mean(np.abs((y - np.asarray(yhat)) / y)) * 100)


def mase_scale(y_train: np.ndarray, m: int) -> float:
    """MAE in-sample seasonal naive: mean |y_t - y_{t-m}| pada data latih."""
    y_train = np.asarray(y_train, dtype=float)
    if len(y_train) <= m:
        raise ValueError("data latih lebih pendek dari periode musim")
    return float(np.mean(np.abs(y_train[m:] - y_train[:-m])))


def coverage(y: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> float:
    y = np.asarray(y)
    return float(np.mean((y >= lower) & (y <= upper)))


def interval_score(y: np.ndarray, lower: np.ndarray, upper: np.ndarray, alpha: float) -> float:
    y, lower, upper = map(np.asarray, (y, lower, upper))
    below = (lower - y) * (y < lower)
    above = (y - upper) * (y > upper)
    return float(np.mean((upper - lower) + (2 / alpha) * (below + above)))


def block_bootstrap_indices(
    n: int, block: int, resamples: int, rng: np.random.Generator
) -> np.ndarray:
    """Indeks moving-block bootstrap (resamples x n) atas origin berurutan."""
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(resamples, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(resamples, -1)
    return idx[:, :n]


def bootstrap_ci(
    per_origin: np.ndarray, idx: np.ndarray, level: float = 0.95
) -> tuple[float, float]:
    """CI persentil untuk rata-rata nilai per origin."""
    stats = per_origin[idx].mean(axis=1)
    lo, hi = np.quantile(stats, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(lo), float(hi)
