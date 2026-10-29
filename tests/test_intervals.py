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
    assert not np.isnan(base).any()
    # origin 41..59 belum lengkap (atau di masa depan) saat origin 47 -> mengubahnya tak berpengaruh
    errors2 = errors.copy()
    errors2[41:] = 1e6
    again = residual_quantiles(errors2, origins, target, (0.1, 0.9), window_days=28)
    np.testing.assert_array_equal(base, again)
    # origin 40 sudah lengkap (40 + 7 hari = 47) -> ikut dipakai
    errors3 = errors.copy()
    errors3[40] = 1e6
    changed = residual_quantiles(errors3, origins, target, (0.1, 0.9), window_days=28)
    assert not np.isnan(changed).any()
    assert not np.array_equal(base, changed)


def test_microsecond_and_nanosecond_indexes_agree():
    origins = pd.date_range("2018-01-01", periods=60, freq="1D", tz="UTC")
    errors = np.random.default_rng(1).normal(0, 1, (60, HORIZON))
    a = residual_quantiles(errors, origins.as_unit("us"), origins[[50]].as_unit("us"), (0.5,), 28)
    b = residual_quantiles(errors, origins.as_unit("ns"), origins[[50]].as_unit("s"), (0.5,), 28)
    assert not np.isnan(a).any()
    np.testing.assert_array_equal(a, b)


def test_coverage_of_exchangeable_errors_is_near_nominal():
    """Pada residual iid, interval konformal harus mendekati coverage nominal."""
    rng = np.random.default_rng(3)
    origins = pd.date_range("2018-01-01", periods=400, freq="1D", tz="UTC")
    errors = rng.normal(0, 1, (400, HORIZON))
    q = residual_quantiles(errors, origins, origins[100:], (0.1, 0.9), 56)
    inside = (errors[100:] >= q[:, 0]) & (errors[100:] <= q[:, 1])
    assert abs(inside.mean() - 0.8) < 0.02


def test_insufficient_history_gives_nan():
    origins = pd.date_range("2018-01-01", periods=10, freq="1D", tz="UTC")
    q = residual_quantiles(np.zeros((10, HORIZON)), origins, origins[[9]], (0.1, 0.9), 28)
    assert np.isnan(q).all()
