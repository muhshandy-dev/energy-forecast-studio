import numpy as np
import pandas as pd
import pytest

from energy_forecast import backtest
from energy_forecast.config import HORIZON


class Spy:
    name = "spy"
    refit = "weekly"

    def __init__(self):
        self.fits: list[int] = []
        self.calls: list[int] = []

    def fit(self, history, cal):
        self.fits.append(len(history))

    def predict(self, history, cal):
        self.calls.append(len(history))
        assert not np.isnan(history).any()
        return np.full(HORIZON, history[-1])


def test_history_is_cut_at_origin_and_refit_on_monday(series, cal):
    origins = pd.date_range("2018-01-24", "2018-02-06", freq="1D", tz="UTC")
    spy = Spy()
    backtest.run_model(spy, series, cal, origins)
    pos = series.index.get_indexer(origins)
    assert spy.calls == list(pos)
    mondays = [p for o, p in zip(origins, pos, strict=True) if o.dayofweek == 0]
    assert spy.fits == [pos[0], *mondays]


def test_actuals_shape_and_bounds(series):
    origins = pd.DatetimeIndex([series.index[100]])
    a = backtest.actuals(series, origins)
    assert a.shape == (1, HORIZON)
    np.testing.assert_array_equal(a[0], series.to_numpy()[100 : 100 + HORIZON])
    with pytest.raises(ValueError):
        backtest.actuals(series, pd.DatetimeIndex([series.index[-10]]))
