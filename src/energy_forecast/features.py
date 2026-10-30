"""Fitur kalender dan fitur lag untuk model ML multi-horizon langsung (direct).

Untuk origin pada posisi ``p`` (indeks jam pertama yang diprakirakan) dan horizon ``h``,
waktu target ``t = p + h - 1``. Semua fitur nilai beban hanya membaca posisi < ``p``:
lag 168/336/504 jam aman karena ``h <= 168`` sehingga ``t - 168 <= p - 1``.

Deret "bersih libur" (``clean_holidays``) mengganti jam hari khusus dengan nilai seminggu
sebelumnya dari deret bersih itu sendiri, jadi nilai bersih di jam ``t`` hanya bergantung
pada ``y[:t+1]`` (kausal) dan aman dipakai sebagai lag.
"""

from __future__ import annotations

import holidays
import numpy as np
import pandas as pd

from .config import HORIZON, TIMEZONE

MIN_HISTORY = 504  # jam riwayat minimum agar lag 504 tersedia

FEATURES = [
    "h",
    "hour",
    "dow",
    "is_holiday",
    "is_bridge",
    "xmas",
    "doy_sin",
    "doy_cos",
    "lag168_holiday",
    "level_gw",
    "lag168_r",
    "lag336_r",
    "lag504_r",
    "naive24_r",
    "last_r",
    "mean24_r",
]

# Fitur tambahan v2: tipe hari khusus dan lag dari deret bersih libur.
FEATURES_V2 = FEATURES + [
    "special",
    "special_lag168",
    "lag168c_r",
    "lag336c_r",
    "naive24c_r",
]

# Tipe hari khusus (dipakai penyesuaian kalender dan fitur v2).
NORMAL, HOLIDAY, XMAS, BRIDGE = 0, 1, 2, 3


def special_type(cal: pd.DataFrame) -> np.ndarray:
    """0 = biasa, 1 = libur nasional, 2 = 24-31 Des & 1 Jan, 3 = hari kejepit."""
    out = np.zeros(len(cal), dtype=np.int8)
    out[cal["is_bridge"].to_numpy().astype(bool)] = BRIDGE
    out[cal["is_holiday"].to_numpy().astype(bool)] = HOLIDAY
    out[cal["xmas"].to_numpy().astype(bool)] = XMAS
    return out


def clean_holidays(y: np.ndarray, special: np.ndarray) -> np.ndarray:
    """Ganti jam hari khusus dengan nilai bersih 168 jam sebelumnya (berantai, kausal)."""
    c = np.asarray(y, dtype=float).copy()
    idx = np.nonzero(special[: len(c)])[0]
    for t in idx[idx >= 168]:
        c[t] = c[t - 168]
    return c


def calendar(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Fitur kalender lokal Jerman untuk setiap jam UTC (tidak memakai data beban)."""
    local = index.tz_convert(TIMEZONE)
    years = range(local.year.min() - 1, local.year.max() + 2)
    de_holidays = holidays.Germany(years=years)
    dates = local.normalize().tz_localize(None).date
    is_holiday = np.array([d in de_holidays for d in dates])
    dow = local.dayofweek.to_numpy()
    # Hari kejepit: hari kerja yang diapit libur nasional dan akhir pekan.
    prev_day = np.array([(d - pd.Timedelta(days=1)) in de_holidays for d in dates])
    next_day = np.array([(d + pd.Timedelta(days=1)) in de_holidays for d in dates])
    is_bridge = ((dow == 0) & next_day) | ((dow == 4) & prev_day)
    xmas = ((local.month == 12) & (local.day >= 24)) | ((local.month == 1) & (local.day == 1))
    doy = local.dayofyear.to_numpy()
    return pd.DataFrame(
        {
            "hour": local.hour.to_numpy(),
            "dow": dow,
            "is_holiday": is_holiday.astype(np.int8),
            "is_bridge": (is_bridge & ~is_holiday).astype(np.int8),
            "xmas": np.asarray(xmas, dtype=np.int8),
            "doy_sin": np.sin(2 * np.pi * doy / 365.25),
            "doy_cos": np.cos(2 * np.pi * doy / 365.25),
        },
        index=index,
    ).assign(special=lambda d: special_type(d))


def origin_rows(
    y: np.ndarray,
    cal: pd.DataFrame,
    positions: np.ndarray,
    max_target: int | None = None,
    feature_set: str = "v1",
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Bangun baris fitur untuk setiap origin di ``positions`` dan setiap h = 1..168.

    ``y`` adalah larik beban; hanya ``y[:p]`` yang dibaca untuk origin ``p``.
    ``cal`` harus menjangkau sampai ``max(positions) + HORIZON``.
    Jika ``max_target`` diberikan, baris dengan ``t >= max_target`` dibuang (untuk latih).
    Mengembalikan (fitur, posisi target t, level m168 per baris).
    ``feature_set="v2"`` menambah fitur hari khusus dan lag bersih libur, dan level m168
    dihitung dari deret bersih libur agar minggu Natal tidak menurunkan skala target.
    """
    positions = np.asarray(positions, dtype=np.int64)
    if positions.size and positions.min() < MIN_HISTORY:
        raise ValueError("origin terlalu awal untuk lag 504 jam")
    hs = np.arange(1, HORIZON + 1)
    p = np.repeat(positions, HORIZON)
    h = np.tile(hs, positions.size)
    t = p + h - 1
    if max_target is not None:
        keep = t < max_target
        p, h, t = p[keep], h[keep], t[keep]

    if feature_set not in ("v1", "v2"):
        raise ValueError(f"feature_set tidak dikenal: {feature_set}")
    special = cal["special"].to_numpy()
    yc = clean_holidays(y[: positions.max()], special) if feature_set == "v2" else None
    level_src = yc if yc is not None else y[: positions.max()]
    csum = np.concatenate([[0.0], np.cumsum(level_src)])
    m168 = (csum[p] - csum[p - 168]) / 168
    raw_csum = np.concatenate([[0.0], np.cumsum(y[: positions.max()])])
    m24 = (raw_csum[p] - raw_csum[p - 24]) / 24
    k = np.ceil(h / 24).astype(np.int64)
    naive24 = y[t - 24 * k]
    for lag_pos in (t - 168, t - 336, t - 504, p - 1, t - 24 * k):
        if (lag_pos >= p).any():  # pragma: no cover - penjaga invarian
            raise AssertionError("fitur membaca data pada/sesudah origin")

    c = cal.iloc[t]
    X = pd.DataFrame(
        {
            "h": h,
            "hour": c["hour"].to_numpy(),
            "dow": c["dow"].to_numpy(),
            "is_holiday": c["is_holiday"].to_numpy(),
            "is_bridge": c["is_bridge"].to_numpy(),
            "xmas": c["xmas"].to_numpy(),
            "doy_sin": c["doy_sin"].to_numpy(),
            "doy_cos": c["doy_cos"].to_numpy(),
            "lag168_holiday": cal["is_holiday"].to_numpy()[t - 168],
            "level_gw": m168 / 1000.0,
            "lag168_r": y[t - 168] / m168,
            "lag336_r": y[t - 336] / m168,
            "lag504_r": y[t - 504] / m168,
            "naive24_r": naive24 / m168,
            "last_r": y[p - 1] / m168,
            "mean24_r": m24 / m168,
        }
    )
    if yc is None:
        return X[FEATURES], t, m168
    X["special"] = special[t]
    X["special_lag168"] = special[t - 168]
    X["lag168c_r"] = yc[t - 168] / m168
    X["lag336c_r"] = yc[t - 336] / m168
    X["naive24c_r"] = yc[t - 24 * k] / m168
    return X[FEATURES_V2], t, m168
