"""Model prakiraan: dua baseline seasonal naive, MSTL + ETS (statsmodels), dan LightGBM.

Antarmuka seragam: ``fit(history, cal)`` dipanggil pada jadwal refit, ``predict(history, cal)``
dipanggil di setiap origin dan mengembalikan 168 nilai untuk jam ``len(history) .. +167``.
``history`` adalah larik beban dengan semua nilai sebelum origin, tidak lebih.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import lightgbm as lgb
import numpy as np
import pandas as pd
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.seasonal import MSTL

from .config import HORIZON, SEED
from .features import MIN_HISTORY, clean_holidays, origin_rows


def seasonal_naive(history: np.ndarray, m: int, horizon: int = HORIZON) -> np.ndarray:
    """ŷ(t) = y(t - m * ceil(h / m)): nilai musim terakhir yang sudah teramati."""
    n = len(history)
    h = np.arange(1, horizon + 1)
    return history[n + h - 1 - m * np.ceil(h / m).astype(int)].astype(float)


@dataclass
class SeasonalNaive:
    m: int
    refit: str = "never"

    @property
    def name(self) -> str:
        return f"snaive{self.m}"

    def params(self) -> dict:
        return {"m": self.m}

    def fit(self, history: np.ndarray, cal: pd.DataFrame) -> None:
        pass

    def predict(self, history: np.ndarray, cal: pd.DataFrame) -> np.ndarray:
        return seasonal_naive(history, self.m)


def holiday_factors(
    y: np.ndarray, clean: np.ndarray, special: np.ndarray, hour: np.ndarray, min_days: int = 3
) -> np.ndarray:
    """Faktor hari khusus per (tipe, jam lokal): median y / y_bersih pada riwayat.

    Bentuk (4, 24); baris 0 (hari biasa) selalu 1. Tipe/jam dengan kurang dari
    ``min_days`` contoh memakai faktor 1 (tanpa penyesuaian).
    """
    n = len(y)
    out = np.ones((4, 24))
    idx = np.nonzero(special[:n])[0]
    idx = idx[idx >= 336]
    ratio = y[idx] / clean[idx]
    for k in (1, 2, 3):
        for h in range(24):
            m = (special[idx] == k) & (hour[idx] == h)
            if m.sum() >= min_days:
                out[k, h] = float(np.median(ratio[m]))
    return out


@dataclass
class MstlEts:
    """MSTL (musim 24 & 168 jam) pada jendela terakhir, ETS pada deret tanpa musim.

    Komponen musiman diproyeksikan dengan mengulang siklus terakhirnya; tren + sisa
    diprakirakan oleh ETS(A, Ad, N) atau ETS(A, N, N). Dicocokkan ulang di setiap origin.

    ``calendar_adjust=True`` (v2): jam hari khusus di riwayat diganti nilai seminggu
    sebelumnya sebelum MSTL, lalu prakiraan untuk jam hari khusus dikalikan faktor
    libur per jam lokal yang diestimasi dari seluruh riwayat sebelum origin.
    """

    window_weeks: int = 8
    robust: bool = False
    trend: str = "Ad"
    calendar_adjust: bool = False
    refit: str = "origin"

    name: str = "mstl_ets"

    def params(self) -> dict:
        p = {
            "window_weeks": self.window_weeks,
            "periods": [24, 168],
            "robust_stl": self.robust,
            "ets": "A,Ad,N" if self.trend == "Ad" else "A,N,N",
        }
        if self.calendar_adjust:
            p["calendar_adjust"] = True
        return p

    def fit(self, history: np.ndarray, cal: pd.DataFrame) -> None:
        pass

    def predict(self, history: np.ndarray, cal: pd.DataFrame) -> np.ndarray:
        n = len(history)
        if self.calendar_adjust:
            special = cal["special"].to_numpy()
            series = clean_holidays(history, special)
        else:
            series = history
        w = series[-self.window_weeks * 168 :]
        res = MSTL(w, periods=(24, 168), stl_kwargs={"robust": self.robust}).fit()
        seasonal = np.asarray(res.seasonal)
        h = np.arange(HORIZON)
        future_season = seasonal[len(w) - 24 + h % 24, 0] + seasonal[len(w) - 168 + h % 168, 1]
        adjusted = np.asarray(res.trend) + np.asarray(res.resid)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if self.trend == "Ad":
                ets = ETSModel(adjusted, error="add", trend="add", damped_trend=True)
            elif self.trend == "N":
                ets = ETSModel(adjusted, error="add")
            else:
                raise ValueError(f"tren ETS tidak dikenal: {self.trend}")
            fitted = ets.fit(disp=False)
        out = np.asarray(fitted.forecast(HORIZON)) + future_season
        if self.calendar_adjust:
            hour = cal["hour"].to_numpy()
            f = holiday_factors(history, series, special, hour)
            out = out * f[special[n : n + HORIZON], hour[n : n + HORIZON]]
        return out


@dataclass
class LightGbmDirect:
    """LightGBM multi-horizon langsung dengan target rasio terhadap rata-rata 168 jam terakhir.

    Dicocokkan ulang setiap Senin memakai semua origin harian sebelumnya yang targetnya
    sudah teramati (expanding window).
    """

    num_leaves: int = 63
    objective: str = "l2"
    n_estimators: int = 600
    learning_rate: float = 0.05
    min_child_samples: int = 100
    feature_set: str = "v1"
    refit: str = "weekly"
    name: str = "lightgbm"
    _model: lgb.LGBMRegressor | None = field(default=None, repr=False)

    def params(self) -> dict:
        return {
            "num_leaves": self.num_leaves,
            "objective": self.objective,
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "min_child_samples": self.min_child_samples,
            "target": "y / mean(y[origin-168h : origin])",
        } | ({"feature_set": self.feature_set} if self.feature_set != "v1" else {})

    def fit(self, history: np.ndarray, cal: pd.DataFrame) -> None:
        n = len(history)
        # Origin latih harian pada 00:00 UTC (posisi kelipatan 24 dari awal grid).
        first = MIN_HISTORY + (-(cal.index[0].hour + MIN_HISTORY)) % 24
        positions = np.arange(first, n, 24)
        X, t, m = origin_rows(history, cal, positions, max_target=n, feature_set=self.feature_set)
        target = history[t] / m
        self._model = lgb.LGBMRegressor(
            objective=self.objective,
            num_leaves=self.num_leaves,
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            min_child_samples=self.min_child_samples,
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.9,
            random_state=SEED,
            n_jobs=4,
            deterministic=True,
            force_row_wise=True,
            verbose=-1,
        )
        self._model.fit(X, target)

    def predict(self, history: np.ndarray, cal: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("model belum di-fit")
        X, _, m = origin_rows(history, cal, np.array([len(history)]), feature_set=self.feature_set)
        return self._model.predict(X) * m


def default_models() -> list:
    return [SeasonalNaive(24), SeasonalNaive(168), MstlEts(), LightGbmDirect()]
