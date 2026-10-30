"""Ekspor hasil eksperimen menjadi JSON statis kecil untuk website.

Website tidak menghitung ulang model; ia hanya membaca prakiraan tersimpan dan metrik.
Sumber data yang tidak boleh diterbitkan (``mirror-dev``) ditolak kecuali ``allow_dev``,
dan saat diizinkan situs menampilkan pita peringatan "data uji coba".
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

MAX_FILE_BYTES = 5 * 1024 * 1024  # jauh di bawah batas 25 MiB Cloudflare Pages
REPLAY_DOW = 0  # origin hari Senin untuk tayangan ulang uji mundur


def _write(path: Path, obj) -> None:
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(text.encode()) > MAX_FILE_BYTES:
        raise ValueError(f"{path.name} terlalu besar ({len(text)} byte)")
    path.write_text(text + "\n", encoding="utf-8")


def _r(a) -> list:
    a = np.asarray(a, dtype=float)
    if np.isnan(a).any():
        raise ValueError("ada NaN pada prakiraan/interval yang diekspor")
    return np.rint(a).astype(int).tolist()


def export(reports: Path, out: Path, allow_dev: bool = False) -> None:
    results = json.loads((reports / "results.json").read_text(encoding="utf-8"))
    src = results["source"]
    if not src["publishable"] and not allow_dev:
        raise SystemExit(f"sumber '{src['id']}' tidak boleh diterbitkan; pakai data OPSD")
    arr = np.load(reports / "test_forecasts.npz")
    out.mkdir(parents=True, exist_ok=True)

    meta = {
        "dev_data": not src["publishable"],
        "source": {k: src[k] for k in ("id", "name", "license", "url", "sha256")},
        "data_quality": results["data_quality"],
        "protocol": results["protocol"],
        "models": results["models"],
        "environment": results["environment"],
        "export_date": dt.date.today().isoformat(),
    }
    _write(out / "meta.json", meta)

    _write(
        out / "metrics.json",
        {
            "metrics": results["metrics"],
            "per_horizon_test": results["per_horizon_test"],
            "selection": results["selection"],
        },
    )
    _write(out / "planning.json", results["planning"])
    _write(out / "errors.json", results["errors"])

    origins = pd.to_datetime(arr["origins_ns"], utc=True)
    keep = np.flatnonzero(origins.dayofweek == REPLAY_DOW)
    models = [k[5:] for k in arr.files if k.startswith("pred_")]
    replay = {
        "origins_utc": [origins[i].isoformat() for i in keep],
        "actual_mw": _r(arr["actual"][keep]),
        "levels": results["protocol"]["interval_levels"],
        "models": {},
    }
    for m in models:
        pred = arr[f"pred_{m}"][keep].astype(float)
        q = arr[f"q_{m}"][keep].astype(float)
        replay["models"][m] = {
            "point_mw": _r(pred),
            # [origin][batas: lo80, hi80, lo95, hi95][jam]
            "bounds_mw": _r(pred[:, None, :] + q),
        }
    _write(out / "replay.json", replay)
    print(f"ekspor selesai -> {out} ({len(keep)} origin tayangan ulang)")
