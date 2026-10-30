import numpy as np
import pandas as pd
import pytest

from energy_forecast import metrics


def test_mae_rmse_mape_manual():
    y = np.array([100.0, 200.0, 300.0])
    p = np.array([110.0, 190.0, 330.0])
    assert metrics.mae(y, p) == pytest.approx((10 + 10 + 30) / 3)
    assert metrics.rmse(y, p) == pytest.approx(np.sqrt((100 + 100 + 900) / 3))
    assert metrics.mape(y, p) == pytest.approx((0.1 + 0.05 + 0.1) / 3 * 100)


def test_mase_scale_manual():
    y = np.array([1.0, 2.0, 4.0, 3.0, 7.0])
    # m=2: |4-1| + |3-2| + |7-4| = 7 over 3
    assert metrics.mase_scale(y, 2) == pytest.approx(7 / 3)
    with pytest.raises(ValueError):
        metrics.mase_scale(y, 5)


def test_mase_matches_sktime():
    sk = pytest.importorskip("sktime.performance_metrics.forecasting")
    rng = np.random.default_rng(1)
    train = pd.Series(rng.normal(100, 10, 400))
    test = pd.Series(rng.normal(100, 10, 50), index=range(400, 450))
    pred = test + rng.normal(0, 5, 50)
    ours = metrics.mae(test, pred) / metrics.mase_scale(train.to_numpy(), 168)
    theirs = sk.MeanAbsoluteScaledError(sp=168)(test, pred, y_train=train)
    assert ours == pytest.approx(theirs, rel=1e-9)


def test_coverage_and_interval_score():
    y = np.array([0.0, 5.0, 10.0, 20.0])
    lo = np.full(4, 2.0)
    hi = np.full(4, 12.0)
    assert metrics.coverage(y, lo, hi) == 0.5
    alpha = 0.2
    # lebar 10; penalti (2/0.2)*2 untuk y=0 dan (2/0.2)*8 untuk y=20
    expected = (10 * 4 + 10 * 2 + 10 * 8) / 4
    assert metrics.interval_score(y, lo, hi, alpha) == pytest.approx(expected)


def test_block_bootstrap_shape_and_contiguity():
    rng = np.random.default_rng(0)
    idx = metrics.block_bootstrap_indices(30, 7, 50, rng)
    assert idx.shape == (50, 30)
    assert idx.min() >= 0 and idx.max() < 30
    # blok pertama berurutan
    assert np.all(np.diff(idx[:, :7], axis=1) == 1)


def test_bootstrap_ci_contains_mean():
    rng = np.random.default_rng(0)
    x = rng.normal(5, 1, 200)
    idx = metrics.block_bootstrap_indices(200, 7, 500, rng)
    lo, hi = metrics.bootstrap_ci(x, idx)
    assert lo < x.mean() < hi
