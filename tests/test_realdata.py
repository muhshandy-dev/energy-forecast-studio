"""Tes pada data OPSD asli. Dilewati bila berkas belum diunduh (energy-forecast data)."""

import json
from pathlib import Path

import pytest

from energy_forecast import config, data

pytestmark = pytest.mark.realdata
RAW = data.raw_files("opsd")["time_series_60min_singleindex.csv"]
RESULTS = Path(__file__).parents[1] / "reports" / "results.json"


@pytest.mark.skipif(not RAW.exists(), reason="data OPSD belum diunduh")
def test_opsd_loads_cleanly_and_covers_protocol():
    ls = data.load("opsd")
    y = ls.y
    assert y.index[0] <= config.SCALE_START
    assert y.index[-1] >= config.DATA_END
    assert ls.quality["n_long_gap_hours"] == 0
    # beban Jerman berada di kisaran puluhan GW
    assert 25_000 < y.median() < 80_000


@pytest.mark.skipif(not RESULTS.exists(), reason="hasil OPSD belum ada")
def test_published_results_follow_protocol():
    r = json.loads(RESULTS.read_text(encoding="utf-8"))
    assert r["source"]["id"] == "opsd" and r["source"]["publishable"]
    assert r["protocol"]["data_end_utc"] == config.DATA_END.isoformat()
    test = r["metrics"]["test"]
    for name in ("snaive24", "snaive168", "mstl_ets", "lightgbm"):
        cov = test[name]["interval"]
        assert cov["n_origins_with_interval"] == test["n_origins"]
        assert 0 < cov["80"]["coverage"] <= cov["95"]["coverage"] <= 1
