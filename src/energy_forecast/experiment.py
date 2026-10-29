"""Eksperimen lengkap: seleksi di validasi, satu kali evaluasi uji, prakiraan perencanaan.

Urutan dikunci:
1. Semua kandidat konfigurasi dijalankan pada origin pemanasan + validasi (2017-10 .. 2018).
2. Konfigurasi dipilih hanya dari metrik validasi (MAE 168 jam; interval score untuk
   jendela konformal). Fungsi seleksi tidak menerima data uji.
3. Konfigurasi terpilih + baseline dijalankan pada origin uji (2019-01 .. 2020-09).
4. Model terpilih dicocokkan ulang pada seluruh data untuk prakiraan perencanaan 7 hari.
"""

from __future__ import annotations

import copy
import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path

import lightgbm
import numpy as np
import pandas as pd
import statsmodels

from . import __version__, backtest, config, intervals, metrics
from .data import SOURCES, LoadSeries
from .error_analysis import analyse
from .features import calendar
from .models import LightGbmDirect, MstlEts, SeasonalNaive

BASELINES = ("snaive24", "snaive168")
REFERENCE = "snaive168"
CONFORMAL_WINDOWS = (28, 56, 91)


def mstl_candidates() -> list[MstlEts]:
    return [MstlEts(window_weeks=w) for w in (4, 8, 12)]


def lightgbm_candidates() -> list[LightGbmDirect]:
    return [
        LightGbmDirect(num_leaves=nl, objective=obj) for nl in (31, 127) for obj in ("l2", "l1")
    ]


@dataclass
class Run:
    origins: pd.DatetimeIndex
    actual: np.ndarray
    forecasts: dict[str, np.ndarray]


def _calendar_for(y: pd.Series) -> pd.DataFrame:
    grid = pd.date_range(
        y.index[0], y.index[-1] + pd.Timedelta(hours=config.HORIZON), freq="1h", tz="UTC"
    )
    return calendar(grid)


def point_metrics(actual: np.ndarray, pred: np.ndarray, scale: float) -> dict:
    out = {}
    for label, k in (("day_ahead", config.DAY_AHEAD), ("week_ahead", config.HORIZON)):
        a, p = actual[:, :k], pred[:, :k]
        m = metrics.mae(a, p)
        out[label] = {
            "mae": m,
            "mase": m / scale,
            "rmse": metrics.rmse(a, p),
            "mape": metrics.mape(a, p),
            "bias": float(np.mean(p - a)),
        }
    return out


def interval_metrics(actual: np.ndarray, pred: np.ndarray, q: np.ndarray) -> dict:
    """``q``: (n_origin, 2*len(levels), 168) kuantil residual sesuai ``interval_probs``."""
    ok = ~np.isnan(q).any(axis=(1, 2))
    out = {"n_origins_with_interval": int(ok.sum())}
    for i, lv in enumerate(config.INTERVAL_LEVELS):
        lo, hi = pred + q[:, 2 * i], pred + q[:, 2 * i + 1]
        a = actual[ok]
        key = f"{round(lv * 100)}"
        out[key] = {
            "coverage": metrics.coverage(a, lo[ok], hi[ok]),
            "coverage_day_ahead": metrics.coverage(
                a[:, : config.DAY_AHEAD],
                lo[ok][:, : config.DAY_AHEAD],
                hi[ok][:, : config.DAY_AHEAD],
            ),
            "mean_width": float(np.mean(hi[ok] - lo[ok])),
            "interval_score": metrics.interval_score(a, lo[ok], hi[ok], 1 - lv),
        }
    return out


def select_conformal_window(
    actual: np.ndarray, pred: np.ndarray, origins: pd.DatetimeIndex, val_mask: np.ndarray
) -> tuple[int, list[dict]]:
    """Pilih jendela residual dengan rerata interval score 80% & 95% terkecil di validasi."""
    probs = intervals.interval_probs(config.INTERVAL_LEVELS)
    errors = actual - pred
    rows = []
    for w in CONFORMAL_WINDOWS:
        q = intervals.residual_quantiles(errors, origins, origins[val_mask], probs, w)
        im = interval_metrics(actual[val_mask], pred[val_mask], q)
        score = np.mean(
            [im[f"{round(lv * 100)}"]["interval_score"] for lv in config.INTERVAL_LEVELS]
        )
        rows.append({"window_days": w, "mean_interval_score": float(score), **im})
    best = min(rows, key=lambda r: r["mean_interval_score"])
    return best["window_days"], rows


def select_point(candidates: list, val_runs: dict[str, np.ndarray], actual: np.ndarray) -> tuple:
    rows = []
    for c, f in zip(candidates, val_runs.values(), strict=True):
        rows.append({"params": c.params(), "val_mae_week_ahead": metrics.mae(actual, f)})
    best = int(np.argmin([r["val_mae_week_ahead"] for r in rows]))
    return candidates[best], rows


def _log(msg: str) -> None:
    print(f"[energy-forecast] {msg}", flush=True)


def config_hash(params: dict) -> str:
    raw = json.dumps(params, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:8]


def run_experiment(ls: LoadSeries, raw_sha256: dict[str, str], workers: int = 0) -> dict:
    y = ls.y.loc[: config.DATA_END]
    if y.index[-1] != config.DATA_END:
        raise ValueError(f"data berakhir {y.index[-1]}, protokol butuh {config.DATA_END}")
    cal = _calendar_for(y)
    scale = metrics.mase_scale(y.loc[config.SCALE_START : config.SCALE_END].to_numpy(), 168)

    # 1) Pemanasan + validasi untuk semua kandidat.
    dev_origins = config.origins(config.WARMUP[0], config.VALIDATION[1])
    val_mask = np.asarray(dev_origins >= config.VALIDATION[0])
    dev_actual = backtest.actuals(y, dev_origins)
    val_actual = dev_actual[val_mask]

    mstl_c, lgb_c = mstl_candidates(), lightgbm_candidates()
    _log(f"seleksi: {len(mstl_c)} kandidat MSTL+ETS, {len(lgb_c)} kandidat LightGBM")
    mstl_runs = {
        f"mstl_{i}": backtest.run_model(copy.deepcopy(m), y, cal, dev_origins, workers or 4)
        for i, m in enumerate(mstl_c)
    }
    lgb_runs = {
        f"lgb_{i}": backtest.run_model(copy.deepcopy(m), y, cal, dev_origins, 1)
        for i, m in enumerate(lgb_c)
    }
    # 2) Seleksi hanya dengan data validasi.
    best_mstl, mstl_rows = select_point(
        mstl_c, {k: v[val_mask] for k, v in mstl_runs.items()}, val_actual
    )
    best_lgb, lgb_rows = select_point(
        lgb_c, {k: v[val_mask] for k, v in lgb_runs.items()}, val_actual
    )
    chosen = [SeasonalNaive(24), SeasonalNaive(168), best_mstl, best_lgb]
    dev_forecasts = {
        "snaive24": backtest.run_model(SeasonalNaive(24), y, cal, dev_origins),
        "snaive168": backtest.run_model(SeasonalNaive(168), y, cal, dev_origins),
        "mstl_ets": mstl_runs[f"mstl_{mstl_c.index(best_mstl)}"],
        "lightgbm": lgb_runs[f"lgb_{lgb_c.index(best_lgb)}"],
    }
    windows, window_rows = {}, {}
    for name, f in dev_forecasts.items():
        windows[name], window_rows[name] = select_conformal_window(
            dev_actual, f, dev_origins, val_mask
        )

    # 3) Satu kali evaluasi uji dengan konfigurasi terkunci.
    _log(f"terpilih: {best_mstl.params()} | {best_lgb.params()} | jendela interval {windows}")
    test_origins = config.origins(*config.TEST)
    test_actual = backtest.actuals(y, test_origins)
    test_forecasts = backtest.run(chosen, y, cal, test_origins, workers)

    all_origins = dev_origins.append(test_origins)
    all_actual = np.vstack([dev_actual, test_actual])
    probs = intervals.interval_probs(config.INTERVAL_LEVELS)
    test_q, val_q = {}, {}
    for name in dev_forecasts:
        all_pred = np.vstack([dev_forecasts[name], test_forecasts[name]])
        errors = all_actual - all_pred
        val_q[name] = intervals.residual_quantiles(
            errors, all_origins, dev_origins[val_mask], probs, windows[name]
        )
        test_q[name] = intervals.residual_quantiles(
            errors, all_origins, test_origins, probs, windows[name]
        )

    periods = {
        "validation": (
            np.ones(val_mask.sum(), bool),
            val_actual,
            {k: v[val_mask] for k, v in dev_forecasts.items()},
            val_q,
        ),
        "test": (np.ones(len(test_origins), bool), test_actual, test_forecasts, test_q),
    }
    year = test_origins.year
    periods["test_2019"] = (year == 2019, test_actual, test_forecasts, test_q)
    periods["test_2020"] = (year == 2020, test_actual, test_forecasts, test_q)

    rng = np.random.default_rng(config.SEED)
    results_metrics: dict = {}
    for pname, (mask, act, fc, qs) in periods.items():
        mask = np.asarray(mask)
        a = act[mask]
        idx = metrics.block_bootstrap_indices(
            len(a), config.BOOTSTRAP_BLOCK_DAYS, config.BOOTSTRAP_RESAMPLES, rng
        )
        ref_err = np.abs(a - fc[REFERENCE][mask]).mean(axis=1)
        pm: dict = {"n_origins": int(mask.sum())}
        for name, f in fc.items():
            p = f[mask]
            per_origin = np.abs(a - p).mean(axis=1)
            entry = point_metrics(a, p, scale)
            entry["week_ahead"]["mae_ci95"] = metrics.bootstrap_ci(per_origin, idx)
            diff = per_origin - ref_err
            entry["week_ahead"]["mae_minus_snaive168"] = float(diff.mean())
            entry["week_ahead"]["mae_minus_snaive168_ci95"] = metrics.bootstrap_ci(diff, idx)
            entry["week_ahead"]["skill_vs_snaive168"] = float(
                1 - per_origin.mean() / ref_err.mean()
            )
            entry["interval"] = interval_metrics(a, p, qs[name][mask])
            pm[name] = entry
        results_metrics[pname] = pm

    per_horizon = {
        name: {
            "mae": np.abs(test_actual - f).mean(axis=0).round(2).tolist(),
            "coverage80": _coverage_by_h(test_actual, f, test_q[name], 0).tolist(),
            "coverage95": _coverage_by_h(test_actual, f, test_q[name], 1).tolist(),
        }
        for name, f in test_forecasts.items()
    }

    # 4) Prakiraan perencanaan dari seluruh data.
    _log("uji selesai; membuat prakiraan perencanaan")
    planning = make_planning(
        y, cal, chosen, all_actual, test_forecasts, dev_forecasts, all_origins, windows
    )

    errors = analyse(test_origins, test_actual, test_forecasts, cal)

    model_info = {
        m.name: {"params": m.params(), "version": f"{__version__}+{config_hash(m.params())}"}
        for m in chosen
    }
    for name in model_info:
        model_info[name]["conformal_window_days"] = windows[name]

    return {
        "source": {**SOURCES[ls.source], "id": ls.source, "sha256": raw_sha256},
        "data_quality": ls.quality,
        "protocol": {
            "horizon_h": config.HORIZON,
            "day_ahead_h": config.DAY_AHEAD,
            "origin_time_utc": "00:00",
            "warmup_origins": [str(config.WARMUP[0].date()), str(config.WARMUP[1].date())],
            "validation_origins": [
                str(config.VALIDATION[0].date()),
                str(config.VALIDATION[1].date()),
            ],
            "test_origins": [str(config.TEST[0].date()), str(config.TEST[1].date())],
            "data_end_utc": config.DATA_END.isoformat(),
            "mase_scale_mw": scale,
            "mase_scale_definition": (
                "MAE in-sample seasonal naive m=168, 2015-01-01..2017-12-31 UTC"
            ),
            "interval_method": "rolling split-conformal per horizon, pool +-3 h",
            "interval_levels": list(config.INTERVAL_LEVELS),
            "bootstrap": {
                "resamples": config.BOOTSTRAP_RESAMPLES,
                "block_days": config.BOOTSTRAP_BLOCK_DAYS,
                "seed": config.SEED,
            },
        },
        "selection": {
            "criterion_point": "MAE minggu-ke-depan pada origin validasi 2018",
            "criterion_interval": "rerata interval score 80% & 95% pada origin validasi 2018",
            "mstl_ets": mstl_rows,
            "lightgbm": lgb_rows,
            "conformal_window": window_rows,
        },
        "models": model_info,
        "metrics": results_metrics,
        "per_horizon_test": per_horizon,
        "planning": planning,
        "errors": errors,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "statsmodels": statsmodels.__version__,
            "lightgbm": lightgbm.__version__,
        },
        "_arrays": {
            "test_origins": test_origins,
            "test_actual": test_actual,
            "test_forecasts": test_forecasts,
            "test_q": test_q,
        },
    }


def _coverage_by_h(actual: np.ndarray, pred: np.ndarray, q: np.ndarray, i: int) -> np.ndarray:
    ok = ~np.isnan(q).any(axis=(1, 2))
    lo, hi = pred[ok] + q[ok, 2 * i], pred[ok] + q[ok, 2 * i + 1]
    a = actual[ok]
    return ((a >= lo) & (a <= hi)).mean(axis=0).round(4)


def make_planning(y, cal, chosen, all_actual, test_fc, dev_fc, all_origins, windows) -> dict:
    values = y.to_numpy(dtype=float)
    origin = config.PLANNING_ORIGIN
    out = {
        "origin_utc": origin.isoformat(),
        "hours_utc": [(origin + pd.Timedelta(hours=h)).isoformat() for h in range(config.HORIZON)],
        "quantile_probs": list(config.QUANTILE_GRID),
        "history_utc_start": (origin - pd.Timedelta(days=14)).isoformat(),
        "history_mw": np.round(values[-14 * 24 :]).tolist(),
        "models": {},
    }
    for m in chosen:
        model = copy.deepcopy(m)
        model.fit(values, cal)
        point = model.predict(values, cal)
        errors = all_actual - np.vstack([dev_fc[m.name], test_fc[m.name]])
        q = intervals.residual_quantiles(
            errors, all_origins, pd.DatetimeIndex([origin]), config.QUANTILE_GRID, windows[m.name]
        )[0]
        quantiles = np.sort(point[None, :] + q, axis=0)  # jaga monoton antar-kuantil
        out["models"][m.name] = {
            "point_mw": np.round(point).tolist(),
            "quantiles_mw": np.round(quantiles).tolist(),
        }
    return out


def write_outputs(results: dict, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    arrays = results.pop("_arrays")
    (reports_dir / "results.json").write_text(
        json.dumps(results, indent=1, ensure_ascii=False, default=_json_default) + "\n",
        encoding="utf-8",
    )
    payload = {
        "origins_ns": arrays["test_origins"].asi8,
        "actual": arrays["test_actual"].astype(np.float32),
    }
    for name, f in arrays["test_forecasts"].items():
        payload[f"pred_{name}"] = f.astype(np.float32)
        payload[f"q_{name}"] = arrays["test_q"][name].astype(np.float32)
    np.savez_compressed(reports_dir / "test_forecasts.npz", **payload)
    results["_arrays"] = arrays


def _json_default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(type(o))
