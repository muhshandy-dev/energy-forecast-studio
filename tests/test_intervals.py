import numpy as np
import pandas as pd

from energy_forecast.config import HORIZON
from energy_forecast.intervals import _pooled, interval_probs, residual_quantiles


def test_interval_probs():
    assert interval_probs((0.8, 0.95)) == (0.1, 0.9, 0.025, 0.975)


def test_pooled_columns():
    e = np.tile(np.arange(HORIZON, dtype=float), (2, 1))
    p = _pooled(e, 2)
    assert p.shape == (10, HORIZON)
    col = p[:, 10]
    assert set(col[~np.isnan(col)]) == {8.0, 9.0, 10.0, 11.0, 12.0}
    first = p[:, 0]
    assert set(first[~np.isnan(first)]) == {0.0, 1.0, 2.0}


def test_only_complete_past_residuals_are_used():
    origins = pd.date_range("2018-01-01", periods=60, freq="1D", tz="UTC")
    errors = np.zeros((60, HORIZON))
    errors[:40] = np.random.default_rng(0).normal(0, 1, (40, HORIZON))
    target = origins[[47]]
    base = residual_quantiles(errors, origins, target, (0.1, 0.9), window_days=28)
    # origin 41..59 belum lengkap (atau di masa depan) saat origin 47 -> mengubahnya tak berpengaruh
    errors2 = errors.copy()
    errors2[41:] = 1e6
    again = residual_quantiles(errors2, origins, target, (0.1, 0.9), window_days=28)
    np.testing.assert_array_equal(base, again)
    # origin 40 sudah lengkap (40 + 7 hari = 47) -> ikut dipakai
    errors3 = errors.copy()
    errors3[40] = 1e6
    changed = residual_quantiles(errors3, origins, target, (0.1, 0.9), window_days=28)
    assert not np.array_equal(base, changed)


def test_insufficient_history_gives_nan():
    origins = pd.date_range("2018-01-01", periods=10, freq="1D", tz="UTC")
    q = residual_quantiles(np.zeros((10, HORIZON)), origins, origins[[9]], (0.1, 0.9), 28)
    assert np.isnan(q).all()
