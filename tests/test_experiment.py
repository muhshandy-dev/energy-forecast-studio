import numpy as np
import pandas as pd

from energy_forecast import config, intervals
from energy_forecast.experiment import (
    combine,
    conformal_offsets,
    select_conformal,
    select_ensemble,
)


def test_combine_uses_one_weight_per_day():
    a, b = np.ones((2, 168)), np.zeros((2, 168))
    out = combine([1, 0, 0.5, 0, 0, 0, 0.25], a, b)
    assert np.all(out[:, :24] == 1) and np.all(out[:, 24:48] == 0)
    assert np.all(out[:, 48:72] == 0.5) and np.all(out[:, 144:] == 0.25)


def test_select_ensemble_finds_the_better_part_per_day():
    rng = np.random.default_rng(0)
    actual = rng.normal(50000, 3000, (50, 168))
    a = actual + rng.normal(0, 100, actual.shape)  # a akurat
    b = actual + rng.normal(0, 5000, actual.shape)  # b berisik
    b[:, :24] = actual[:, :24]  # hari 1: b sempurna
    weights, rows = select_ensemble(actual, a, b)
    assert weights[0] == 0.0
    assert all(w >= 0.9 for w in weights[1:])
    assert rows[0]["val_mae"] == 0.0


def test_relative_offsets_scale_with_forecast_level():
    origins = config.origins(
        pd.Timestamp("2018-01-01", tz="UTC"), pd.Timestamp("2018-06-30", tz="UTC")
    )
    rng = np.random.default_rng(1)
    pred = np.full((len(origins), 168), 50000.0)
    actual = pred * (1 + rng.normal(0, 0.02, pred.shape))
    targets = origins[-5:]
    probs = intervals.interval_probs(config.INTERVAL_LEVELS)
    low = conformal_offsets(
        actual, pred, origins, targets, np.full((5, 168), 40000.0), probs, 56, "relative"
    )
    high = conformal_offsets(
        actual, pred, origins, targets, np.full((5, 168), 80000.0), probs, 56, "relative"
    )
    np.testing.assert_allclose(high, 2 * low)
    absolute = conformal_offsets(actual, pred, origins, targets, pred[-5:], probs, 56, "absolute")
    np.testing.assert_allclose(
        absolute,
        conformal_offsets(actual, pred, origins, targets, pred[-5:], probs, 56, "relative"),
        rtol=1e-9,
    )


def test_select_conformal_returns_window_and_mode():
    origins = config.origins(
        pd.Timestamp("2017-01-01", tz="UTC"), pd.Timestamp("2018-03-31", tz="UTC")
    )
    rng = np.random.default_rng(2)
    pred = np.full((len(origins), 168), 50000.0)
    actual = pred + rng.normal(0, 1000, pred.shape)
    val_mask = np.asarray(origins >= pd.Timestamp("2018-01-01", tz="UTC"))
    best, rows = select_conformal(actual, pred, origins, val_mask)
    assert best["window_days"] in (28, 56, 91, 182, 364)
    assert best["mode"] in ("absolute", "relative")
    assert len(rows) == 10
    assert all(r["n_origins_with_interval"] == val_mask.sum() for r in rows)
