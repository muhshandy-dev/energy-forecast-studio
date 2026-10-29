import numpy as np
import pandas as pd
import pytest

from energy_forecast import data


def _raw(n=48):
    idx = pd.date_range("2018-01-01", periods=n, freq="1h", tz="UTC")
    return pd.Series(np.linspace(50000, 60000, n), index=idx)


def test_short_gap_interpolated_and_counted():
    raw = _raw().drop(_raw().index[10:13])
    y, q = data.clean_hourly(raw)
    assert len(y) == 48 and not y.isna().any()
    assert q["n_missing_raw"] == 3 and q["n_interpolated"] == 3
    np.testing.assert_allclose(y.iloc[11], _raw().iloc[11])


def test_long_gap_rejected():
    raw = _raw().drop(_raw().index[10:15])
    with pytest.raises(ValueError, match="celah"):
        data.clean_hourly(raw)


def test_duplicates_dropped_and_nonpositive_rejected():
    raw = _raw()
    dup = pd.concat([raw, raw.iloc[[5]]])
    _, q = data.clean_hourly(dup)
    assert q["n_duplicates_dropped"] == 1
    bad = raw.copy()
    bad.iloc[3] = 0
    with pytest.raises(ValueError):
        data.clean_hourly(bad)


def test_opsd_reader(tmp_path):
    p = tmp_path / "ts.csv"
    p.write_text(
        "utc_timestamp,cet_cest_timestamp,DE_load_actual_entsoe_transparency,AT_x\n"
        "2015-01-01T00:00:00Z,2015-01-01T01:00:00+0100,41000,1\n"
        "2015-01-01T01:00:00Z,2015-01-01T02:00:00+0100,40000,1\n"
    )
    s = data._read_opsd(p)
    assert s.index.tz is not None and list(s) == [41000.0, 40000.0]


def test_mirror_reader_handles_dst(tmp_path):
    # 27 Okt 2019: jam 02:00-02:59 lokal muncul dua kali
    local = pd.date_range("2019-10-27 00:00", "2019-10-27 05:45", freq="15min")
    stamps = list(local[:12]) + list(local[8:12]) + list(local[12:])
    df = pd.DataFrame({"Timestamp": stamps, "Germany": 50000.0})
    p = tmp_path / "m.csv"
    df.to_csv(p, index=False)
    s = data._read_mirror([p])
    assert s.index.is_unique and len(s) == 7  # 6 jam lokal + 1 jam berulang


def test_verify_detects_hash_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "MANIFEST_PATH", tmp_path / "manifest.json")
    f = data.raw_files("opsd", tmp_path)["time_series_60min_singleindex.csv"]
    f.parent.mkdir(parents=True)
    f.write_text("a")
    hashes = data.verify("opsd", tmp_path)
    data.pin_manifest("opsd", hashes)
    f.write_text("b")
    with pytest.raises(ValueError, match="SHA-256"):
        data.verify("opsd", tmp_path)
