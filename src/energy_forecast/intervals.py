"""Interval prediksi konformal bergulir (rolling split-conformal per horizon).

Untuk origin ``o`` dan horizon ``h``, kuantil diambil dari residual ``aktual - prakiraan``
model yang sama pada origin sebelumnya ``o'`` yang seluruh 168 jamnya sudah teramati saat
``o`` (``o' + 168 jam <= o``) dan berada dalam ``window_days`` hari terakhir. Residual horizon
``h-pool .. h+pool`` digabung agar kuantil ekor tidak terlalu berisik.

Metode ini tidak menjamin coverage karena deret waktu tidak dapat dipertukarkan
(exchangeable); coverage diukur, bukan diasumsikan.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import HORIZON

POOL = 3


def _pooled(errors: np.ndarray, pool: int) -> np.ndarray:
    """(k, 168) -> (k * (2*pool+1), 168): tiap kolom h berisi residual h-pool..h+pool."""
    k = errors.shape[0]
    out = np.full((2 * pool + 1, k, HORIZON), np.nan)
    for i, shift in enumerate(range(-pool, pool + 1)):
        lo, hi = max(0, shift), HORIZON + min(0, shift)
        out[i, :, lo - shift : hi - shift] = errors[:, lo:hi]
    return out.reshape(-1, HORIZON)


def residual_quantiles(
    errors: np.ndarray,
    origins: pd.DatetimeIndex,
    targets: pd.DatetimeIndex,
    probs: tuple[float, ...],
    window_days: int,
    pool: int = POOL,
) -> np.ndarray:
    """Kuantil residual untuk setiap origin target. Bentuk (n_target, n_prob, 168).

    ``errors`` dan ``origins`` adalah residual uji mundur yang tersedia; ``targets`` adalah
    origin yang butuh interval (boleh di luar ``origins``, misalnya origin perencanaan).
    """
    out = np.full((len(targets), len(probs), HORIZON), np.nan)
    # Satuan eksplisit: pandas 3 bisa memakai resolusi mikrodetik untuk DatetimeIndex.
    o_ns = origins.as_unit("ns").asi8
    full = pd.Timedelta(hours=HORIZON).value
    window = pd.Timedelta(days=window_days).value
    for i, t in enumerate(targets.as_unit("ns").asi8):
        mask = (o_ns + full <= t) & (o_ns >= t - window)
        if mask.sum() < window_days // 2:
            continue  # residual belum cukup: interval dibiarkan kosong (NaN)
        pooled = _pooled(errors[mask], pool)
        out[i] = np.nanquantile(pooled, probs, axis=0)
    return out


def interval_probs(levels: tuple[float, ...]) -> tuple[float, ...]:
    probs: list[float] = []
    for lv in levels:
        probs += [round((1 - lv) / 2, 6), round(1 - (1 - lv) / 2, 6)]
    return tuple(probs)
