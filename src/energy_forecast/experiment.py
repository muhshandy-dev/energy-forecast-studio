"""Eksperimen lengkap: seleksi di validasi, satu kali evaluasi uji, prakiraan perencanaan.

Urutan (protokol v2):
1. Semua kandidat MSTL + ETS dan LightGBM dijalankan pada origin validasi 2018.
2. Konfigurasi dipilih hanya dari MAE 168 jam validasi. Fungsi seleksi tidak menerima uji.
3. Model terpilih juga dijalankan pada origin pemanasan 2017 (residual interval saja).
4. Bobot gabungan LightGBM + MSTL + ETS per hari horizon dipilih di validasi.
5. Jendela dan jenis residual konformal dipilih per model dari interval score validasi.
6. Konfigurasi terkunci + baseline dijalankan sekali pada origin uji (2019-01 .. 2020-09).
7. Model terpilih dicocokkan ulang pada seluruh data untuk prakiraan perencanaan 7 hari.
"""

from __future__ import annotations

import copy
import hashlib
import json
import platform
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
CONFORMAL_WINDOWS = (28, 56, 91, 182, 364)
RESIDUAL_MODES = ("absolute", "relative")
ENSEMBLE = "ensemble"
ENSEMBLE_PARTS = ("lightgbm", "mstl_ets")
ENSEMBLE_GRID = tuple(round(w, 2) for w in np.arange(0.0, 1.0001, 0.05))
MODEL_ORDER = ("snaive24", "snaive168", "mstl_ets", "lightgbm", ENSEMBLE)


def mstl_candidates() -> list[MstlEts]:
    return [
        MstlEts(window_weeks=w, trend=t, calendar_adjust=c)
        for c in (False, True)
        for t in ("Ad", "N")
        for w in (4, 8, 12)
    ]


def lightgbm_candidates() -> list[LightGbmDirect]:
    return [
        LightGbmDirect(num_leaves=nl, objective=obj) for nl in (31, 127) for obj in ("l2", "l1")
    ] + LIGHTGBM_EXTRA


# v2: dua kandidat tambahan (pohon lebih besar; lebih banyak pohon dengan laju lebih kecil).
LIGHTGBM_EXTRA: list[LightGbmDirect] = [
    LightGbmDirect(num_leaves=255, objective="l2", min_child_samples=50),
    LightGbmDirect(num_leaves=127, objective="l2", n_estimators=1200, learning_rate=0.03),
]


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
    """``q``: (n_origin, 2*len(levels), 168) offset MW terhadap prakiraan titik."""
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


def conformal_offsets(
    actual: np.ndarray,
    pred: np.ndarray,
    origins: pd.DatetimeIndex,
    targets: pd.DatetimeIndex,
    target_pred: np.ndarray,
    probs: tuple[float, ...],
    window_days: int,
    mode: str,
) -> np.ndarray:
    """Offset kuantil (MW) untuk origin ``targets``; bentuk (n_target, n_prob, 168).

    ``absolute``: kuantil dari residual y - ŷ. ``relative``: kuantil dari (y - ŷ) / ŷ,
    lalu dikalikan prakiraan titik origin target (lebar mengikuti level beban).
    """
    if mode == "absolute":
        return intervals.residual_quantiles(actual - pred, origins, targets, probs, window_days)
    if mode == "relative":
        rel = (actual - pred) / pred
        q = intervals.residual_quantiles(rel, origins, targets, probs, window_days)
        return q * target_pred[:, None, :]
    raise ValueError(f"jenis residual tidak dikenal: {mode}")


def select_conformal(
    actual: np.ndarray, pred: np.ndarray, origins: pd.DatetimeIndex, val_mask: np.ndarray
) -> tuple[dict, list[dict]]:
    """Pilih (jendela, jenis residual) dengan rerata interval score 80% & 95% terkecil
    di origin validasi. ``actual``/``pred`` hanya mencakup pemanasan + validasi."""
    probs = intervals.interval_probs(config.INTERVAL_LEVELS)
    rows = []
    for mode in RESIDUAL_MODES:
        for w in CONFORMAL_WINDOWS:
            q = conformal_offsets(
                actual, pred, origins, origins[val_mask], pred[val_mask], probs, w, mode
            )
            im = interval_metrics(actual[val_mask], pred[val_mask], q)
            score = np.mean(
                [im[f"{round(lv * 100)}"]["interval_score"] for lv in config.INTERVAL_LEVELS]
            )
            rows.append({"window_days": w, "mode": mode, "mean_interval_score": float(score), **im})
    full = [r for r in rows if r["n_origins_with_interval"] == int(val_mask.sum())]
    best = min(full or rows, key=lambda r: r["mean_interval_score"])
    return {"window_days": best["window_days"], "mode": best["mode"]}, rows


def select_point(candidates: list, val_runs: dict[str, np.ndarray], actual: np.ndarray) -> tuple:
    rows = []
    for c, f in zip(candidates, val_runs.values(), strict=True):
        rows.append({"params": c.params(), "val_mae_week_ahead": metrics.mae(actual, f)})
    best = int(np.argmin([r["val_mae_week_ahead"] for r in rows]))
    return candidates[best], rows


def combine(weights: list[float], a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Gabungan per hari horizon: w_d * a + (1 - w_d) * b untuk jam hari ke-d."""
    w = np.repeat(np.asarray(weights, dtype=float), 24)
    return w * a + (1 - w) * b


def select_ensemble(actual: np.ndarray, a: np.ndarray, b: np.ndarray) -> tuple[list, list]:
    """Bobot per hari horizon (7) yang meminimalkan MAE validasi; grid 0..1 langkah 0,05.

    MAE terpisah per blok 24 jam, jadi bobot tiap hari dapat dipilih sendiri-sendiri.
    """
    weights, rows = [], []
    for d in range(config.HORIZON // 24):
        sl = slice(24 * d, 24 * (d + 1))
        maes = [
            float(np.mean(np.abs(actual[:, sl] - (w * a[:, sl] + (1 - w) * b[:, sl]))))
            for w in ENSEMBLE_GRID
        ]
        best = int(np.argmin(maes))
        weights.append(ENSEMBLE_GRID[best])
        rows.append(
            {
                "day": d + 1,
                "weight_lightgbm": ENSEMBLE_GRID[best],
                "val_mae": maes[best],
                "val_mae_lightgbm_only": maes[-1],
                "val_mae_mstl_only": maes[0],
            }
        )
    return weights, rows


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
    nproc = workers or 4

    # 1) Kandidat hanya pada origin validasi.
    val_origins = config.origins(*config.VALIDATION)
    val_actual = backtest.actuals(y, val_origins)
    mstl_c, lgb_c = mstl_candidates(), lightgbm_candidates()
    _log(f"seleksi: {len(mstl_c)} kandidat MSTL+ETS, {len(lgb_c)} kandidat LightGBM")
    mstl_runs = {}
    for i, m in enumerate(mstl_c):
        mstl_runs[f"mstl_{i}"] = backtest.run_model(copy.deepcopy(m), y, cal, val_origins, nproc)
        _log(f"MSTL {m.params()} MAE val {metrics.mae(val_actual, mstl_runs[f'mstl_{i}']):.0f}")
    lgb_runs = {}
    for i, m in enumerate(lgb_c):
        lgb_runs[f"lgb_{i}"] = backtest.run_model(copy.deepcopy(m), y, cal, val_origins, 1)
        _log(f"LightGBM {m.params()} MAE val {metrics.mae(val_actual, lgb_runs[f'lgb_{i}']):.0f}")

    # 2) Seleksi hanya dengan data validasi.
    best_mstl, mstl_rows = select_point(mstl_c, mstl_runs, val_actual)
    best_lgb, lgb_rows = select_point(lgb_c, lgb_runs, val_actual)
    chosen = [SeasonalNaive(24), SeasonalNaive(168), best_mstl, best_lgb]
    val_fc = {
        "snaive24": backtest.run_model(SeasonalNaive(24), y, cal, val_origins),
        "snaive168": backtest.run_model(SeasonalNaive(168), y, cal, val_origins),
        "mstl_ets": mstl_runs[f"mstl_{mstl_c.index(best_mstl)}"],
        "lightgbm": lgb_runs[f"lgb_{lgb_c.index(best_lgb)}"],
    }

    # 3) Pemanasan 2017 untuk model terpilih (residual interval saja, tidak dinilai).
    _log("pemanasan 2017 untuk model terpilih")
    warm_origins = config.origins(*config.WARMUP)
    warm_fc = backtest.run(chosen, y, cal, warm_origins, workers)
    dev_origins = warm_origins.append(val_origins)
    val_mask = np.asarray(dev_origins >= config.VALIDATION[0])
    dev_actual = np.vstack([backtest.actuals(y, warm_origins), val_actual])
    dev_fc = {k: np.vstack([warm_fc[k], val_fc[k]]) for k in val_fc}

    # 4) Bobot gabungan per hari horizon, dipilih di validasi.
    weights, ens_rows = select_ensemble(val_actual, val_fc["lightgbm"], val_fc["mstl_ets"])
    dev_fc[ENSEMBLE] = combine(weights, dev_fc["lightgbm"], dev_fc["mstl_ets"])

    # 5) Interval: jendela dan jenis residual per model, dipilih di validasi.
    conf, conf_rows = {}, {}
    for name, f in dev_fc.items():
        conf[name], conf_rows[name] = select_conformal(dev_actual, f, dev_origins, val_mask)
    _log(f"terpilih: {best_mstl.params()} | {best_lgb.params()} | gabungan {weights} | {conf}")

    # 6) Satu kali evaluasi uji dengan konfigurasi terkunci.
    test_origins = config.origins(*config.TEST)
    test_actual = backtest.actuals(y, test_origins)
    test_forecasts = backtest.run(chosen, y, cal, test_origins, workers)
    test_forecasts[ENSEMBLE] = combine(
        weights, test_forecasts["lightgbm"], test_forecasts["mstl_ets"]
    )
    test_forecasts = {k: test_forecasts[k] for k in MODEL_ORDER}
    dev_fc = {k: dev_fc[k] for k in MODEL_ORDER}

    all_origins = dev_origins.append(test_origins)
    all_actual = np.vstack([dev_actual, test_actual])
    probs = intervals.interval_probs(config.INTERVAL_LEVELS)
    test_q, val_q = {}, {}
    for name in MODEL_ORDER:
        all_pred = np.vstack([dev_fc[name], test_forecasts[name]])
        w, mode = conf[name]["window_days"], conf[name]["mode"]
        val_q[name] = conformal_offsets(
            all_actual,
            all_pred,
            all_origins,
            dev_origins[val_mask],
            dev_fc[name][val_mask],
            probs,
            w,
            mode,
        )
        test_q[name] = conformal_offsets(
            all_actual, all_pred, all_origins, test_origins, test_forecasts[name], probs, w, mode
        )

    periods = {
        "validation": (
            np.ones(val_mask.sum(), bool),
            val_actual,
            {k: v[val_mask] for k, v in dev_fc.items()},
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
        lgb_err = np.abs(a - fc["lightgbm"][mask]).mean(axis=1)
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
            if name == ENSEMBLE:
                d_lgb = per_origin - lgb_err
                entry["week_ahead"]["mae_minus_lightgbm"] = float(d_lgb.mean())
                entry["week_ahead"]["mae_minus_lightgbm_ci95"] = metrics.bootstrap_ci(d_lgb, idx)
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

    # 7) Prakiraan perencanaan dari seluruh data.
    _log("uji selesai; membuat prakiraan perencanaan")
    planning = make_planning(
        y, cal, chosen, weights, all_actual, all_origins, dev_fc, test_forecasts, conf
    )

    errors = analyse(test_origins, test_actual, test_forecasts, cal)

    model_info = {
        m.name: {"params": m.params(), "version": f"{__version__}+{config_hash(m.params())}"}
        for m in chosen
    }
    ens_params = {"components": list(ENSEMBLE_PARTS), "weight_lightgbm_by_day": weights}
    ens_hash = config_hash(ens_params | {"parts": [best_lgb.params(), best_mstl.params()]})
    model_info[ENSEMBLE] = {"params": ens_params, "version": f"{__version__}+{ens_hash}"}
    model_info = {k: model_info[k] for k in MODEL_ORDER}
    for name in model_info:
        model_info[name]["conformal_window_days"] = conf[name]["window_days"]
        model_info[name]["conformal_residual"] = conf[name]["mode"]

    return {
        "source": {**SOURCES[ls.source], "id": ls.source, "sha256": raw_sha256},
        "data_quality": ls.quality,
        "protocol": {
            "version": config.PROTOCOL_VERSION,
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
            "interval_method": (
                "rolling split-conformal per horizon, pool +-3 h, residual absolut atau relatif"
            ),
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
            "criterion_ensemble": "MAE per hari horizon pada origin validasi 2018",
            "mstl_ets": mstl_rows,
            "lightgbm": lgb_rows,
            "ensemble": ens_rows,
            "conformal_window": conf_rows,
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


def make_planning(y, cal, chosen, weights, all_actual, all_origins, dev_fc, test_fc, conf):
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
    points = {}
    for m in chosen:
        model = copy.deepcopy(m)
        model.fit(values, cal)
        points[m.name] = model.predict(values, cal)
    points[ENSEMBLE] = combine(weights, points["lightgbm"], points["mstl_ets"])
    for name in MODEL_ORDER:
        point = points[name]
        all_pred = np.vstack([dev_fc[name], test_fc[name]])
        q = conformal_offsets(
            all_actual,
            all_pred,
            all_origins,
            pd.DatetimeIndex([origin]),
            point[None, :],
            config.QUANTILE_GRID,
            conf[name]["window_days"],
            conf[name]["mode"],
        )[0]
        quantiles = np.sort(point[None, :] + q, axis=0)  # jaga monoton antar-kuantil
        out["models"][name] = {
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
        "origins_ns": arrays["test_origins"].as_unit("ns").asi8,
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
