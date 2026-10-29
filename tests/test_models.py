import numpy as np
import pandas as pd
import pytest

from energy_forecast import backtest
from energy_forecast.config import HORIZON
from energy_forecast.models import LightGbmDirect, MstlEts, SeasonalNaive, seasonal_naive


def test_seasonal_naive_formula():
    hist = np.arange(500, dtype=float)
    f = seasonal_naive(hist, 24)
    # h=1..24 -> 24 jam terakhir; h=25..48 mengulang lagi
    assert np.array_equal(f[:24], hist[-24:])
    assert np.array_equal(f[24:48], hist[-24:])
    f168 = seasonal_naive(hist, 168)
    assert np.array_equal(f168, hist[-168:])


def test_seasonal_naive_matches_sktime(series):
    sk = pytest.importorskip("sktime.forecasting.naive")
    hist = series.iloc[:1000].reset_index(drop=True)
    fh = np.arange(1, HORIZON + 1)
    for m in (24, 168):
        theirs = sk.NaiveForecaster(strategy="last", sp=m).fit(hist).predict(fh)
        np.testing.assert_allclose(seasonal_naive(hist.to_numpy(), m), theirs.to_numpy())


@pytest.mark.parametrize(
    "model",
    [
        SeasonalNaive(24),
        SeasonalNaive(168),
        MstlEts(window_weeks=4),
        LightGbmDirect(n_estimators=40),
    ],
    ids=lambda m: m.name,
)
def test_no_future_leakage(model, series, cal):
    """Mengubah nilai sesudah origin tidak boleh mengubah prakiraan."""
    origins = pd.DatetimeIndex([series.index[24 * 40], series.index[24 * 45]])
    base = backtest.run_model(model, series, cal, origins, workers=1)
    poisoned = series.copy()
    poisoned.iloc[24 * 40 :] = poisoned.iloc[24 * 40 :] * 3 + 1e5
    # origin pertama hanya melihat masa lalu, jadi prakiraannya harus identik
    out = backtest.run_model(model, poisoned, cal, origins[:1], workers=1)
    np.testing.assert_allclose(out[0], base[0])


def test_models_track_synthetic_pattern(series, cal):
    origins = pd.DatetimeIndex([series.index[24 * 50]])
    actual = backtest.actuals(series, origins)
    naive = backtest.run_model(SeasonalNaive(168), series, cal, origins)
    for model in (MstlEts(window_weeks=4), LightGbmDirect(n_estimators=200)):
        pred = backtest.run_model(model, series, cal, origins)
        # pola sintetis jelas: model harus sekelas baseline (tidak meledak)
        assert np.abs(actual - pred).mean() < 2 * np.abs(actual - naive).mean()
