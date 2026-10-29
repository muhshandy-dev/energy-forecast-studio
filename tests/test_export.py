import json

import numpy as np
import pandas as pd
import pytest

from energy_forecast import export_web


def _fake_reports(tmp_path, publishable: bool):
    rep = tmp_path / "reports"
    rep.mkdir()
    origins = pd.date_range("2019-01-07", periods=2, freq="7D", tz="UTC")
    results = {
        "source": {
            "id": "opsd" if publishable else "mirror-dev",
            "name": "x",
            "license": "CC BY 4.0",
            "url": "u",
            "sha256": {"f": "0"},
            "publishable": publishable,
        },
        "data_quality": {},
        "protocol": {"interval_levels": [0.8, 0.95]},
        "models": {},
        "environment": {},
        "metrics": {},
        "per_horizon_test": {},
        "selection": {},
        "planning": {},
        "errors": {},
    }
    (rep / "results.json").write_text(json.dumps(results))
    pred = np.full((2, 168), 50000.0)
    q = np.tile(np.array([-1000.0, 1000.0, -2000.0, 2000.0])[None, :, None], (2, 1, 168))
    np.savez(
        rep / "test_forecasts.npz",
        origins_ns=origins.as_unit("ns").asi8,
        actual=pred,
        pred_lightgbm=pred,
        q_lightgbm=q,
    )
    return rep


def test_dev_source_is_refused(tmp_path):
    rep = _fake_reports(tmp_path, publishable=False)
    with pytest.raises(SystemExit):
        export_web.export(rep, tmp_path / "out")
    export_web.export(rep, tmp_path / "out", allow_dev=True)
    assert json.loads((tmp_path / "out" / "meta.json").read_text())["dev_data"] is True


def test_replay_keeps_mondays_and_bounds(tmp_path):
    rep = _fake_reports(tmp_path, publishable=True)
    export_web.export(rep, tmp_path / "out")
    replay = json.loads((tmp_path / "out" / "replay.json").read_text())
    assert replay["origins_utc"][0].startswith("2019-01-07")
    b = np.asarray(replay["models"]["lightgbm"]["bounds_mw"])
    assert b.shape == (2, 4, 168)
    assert b[0, 0, 0] == 49000 and b[0, 3, 0] == 52000
