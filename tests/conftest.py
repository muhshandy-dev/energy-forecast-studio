"""Deret sintetis untuk tes unit. Hasil resmi tidak pernah memakai data ini."""

import numpy as np
import pandas as pd
import pytest

from energy_forecast.features import calendar


def synthetic(n_days: int = 70, seed: int = 0) -> pd.Series:
    idx = pd.date_range("2018-01-01", periods=n_days * 24, freq="1h", tz="UTC")
    t = np.arange(len(idx))
    rng = np.random.default_rng(seed)
    y = (
        55000
        + 8000 * np.sin(2 * np.pi * (t % 24) / 24 - 1.5)
        - 6000 * (idx.dayofweek >= 5)
        + 30 * t / 24
        + rng.normal(0, 600, len(idx))
    )
    return pd.Series(y, index=idx, name="load_mw")


@pytest.fixture(scope="session")
def series() -> pd.Series:
    return synthetic()


@pytest.fixture(scope="session")
def cal(series) -> pd.DataFrame:
    grid = pd.date_range(series.index[0], periods=len(series) + 168, freq="1h", tz="UTC")
    return calendar(grid)
