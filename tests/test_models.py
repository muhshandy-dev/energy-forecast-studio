import numpy as np
import pandas as pd
import pytest

from energy_forecast import backtest
from energy_forecast.config import HORIZON
from energy_forecast.features import clean_holidays
from energy_forecast.models import (
    LightGbmDirect,
    MstlEts,
    SeasonalNaive,
    holiday_factors,
    seasonal_naive,
)


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
        MstlEts(window_weeks=4, trend="N", calendar_adjust=True),
        LightGbmDirect(n_estimators=40, feature_set="v2"),
    ],
    ids=lambda m: f"{m.name}-{'-'.join(map(str, m.params().values()))}"[:60],
)
def test_no_future_leakage(model, series, cal_special):
    cal = cal_special
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


def test_clean_holidays_is_causal():
    rng = np.random.default_rng(1)
    y = rng.normal(50000, 3000, 2000)
    special = np.zeros(2200, dtype=np.int8)
    special[[200, 201, 400, 568, 900, 1500, 1668, 1836]] = 1
    full = clean_holidays(y, special)
    for k in (300, 569, 901, 1700, 2000):
        np.testing.assert_array_equal(clean_holidays(y[:k], special), full[:k])
    # jam khusus berantai: 1836 -> 1668 -> 1500 (semuanya khusus) -> nilai asli 1332
    assert full[1836] == y[1332]
    assert np.array_equal(full[special[:2000] == 0], y[special[:2000] == 0])


def test_holiday_factors_recover_known_ratio(series, cal_special):
    special = cal_special["special"].to_numpy()
    hour = cal_special["hour"].to_numpy()
    y = series.to_numpy().copy()
    y[special[: len(y)] == 1] *= 0.8
    f = holiday_factors(y, clean_holidays(y, special), special, hour)
    assert np.allclose(f[0], 1.0)
    assert np.allclose(f[2:], 1.0)  # tidak ada contoh tipe 2 dan 3
    # deret bersih = minggu sebelumnya (bukan nilai asli jam itu), jadi faktor ~0,8 +- derau
    assert np.all(np.abs(f[1] - 0.8) < 0.05)


def test_calendar_adjust_lowers_error_on_holidays(series, cal_special):
    special = cal_special["special"].to_numpy()
    y = series.copy()
    y[special[: len(y)] == 1] *= 0.75
    origin = series.index[24 * 60]  # hari 63 khusus, faktor dari 4 hari khusus sebelumnya
    origins = pd.DatetimeIndex([origin])
    actual = backtest.actuals(y, origins)
    plain = backtest.run_model(MstlEts(window_weeks=4, trend="N"), y, cal_special, origins)
    adj = backtest.run_model(
        MstlEts(window_weeks=4, trend="N", calendar_adjust=True), y, cal_special, origins
    )
    pos = 24 * 60 + np.arange(HORIZON)
    hol = special[pos] == 1
    assert hol.any()
    assert np.abs(actual - adj)[0, hol].mean() < 0.5 * np.abs(actual - plain)[0, hol].mean()
