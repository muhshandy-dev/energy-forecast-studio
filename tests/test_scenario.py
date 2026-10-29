import json
from pathlib import Path

import numpy as np
import pytest

from energy_forecast.scenario import exceedance, scale_factor

VECTORS = Path(__file__).parents[1] / "web" / "tests" / "fixtures" / "scenario_vectors.json"


def test_exceedance_interpolates_and_bounds():
    probs = [0.1, 0.5, 0.9]
    q = [100.0, 200.0, 300.0]
    assert exceedance(probs, q, 150) == pytest.approx((0.7, "exact"))
    assert exceedance(probs, q, 50) == pytest.approx((0.9, "atLeast"))
    assert exceedance(probs, q, 300) == pytest.approx((0.1, "atMost"))


def test_scale_factor_rejects_nonsense():
    assert scale_factor(5) == 1.05
    with pytest.raises(ValueError):
        scale_factor(-100)


def test_shared_vectors_match():
    data = json.loads(VECTORS.read_text())
    for c in data["cases"]:
        q = np.asarray(c["quantiles"]) * scale_factor(c["shift_pct"])
        p, b = exceedance(data["probs"], q, c["capacity"])
        assert b == c["bound"]
        assert p == pytest.approx(c["p"], abs=1e-12)
