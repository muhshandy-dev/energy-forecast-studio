"""Analisis kegagalan pada periode uji: origin terburuk, libur, bias per jam & hari."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import HORIZON

DOW_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def analyse(
    origins: pd.DatetimeIndex,
    actual: np.ndarray,
    forecasts: dict[str, np.ndarray],
    cal: pd.DataFrame,
    n_worst: int = 10,
) -> dict:
    target_pos = cal.index.get_indexer(origins)[:, None] + np.arange(HORIZON)[None, :]
    hour = cal["hour"].to_numpy()[target_pos]
    dow = cal["dow"].to_numpy()[target_pos]
    holiday = cal["is_holiday"].to_numpy()[target_pos].astype(bool)
    special = holiday | cal["xmas"].to_numpy()[target_pos].astype(bool)

    out: dict = {"by_model": {}, "weekly_mae": {}}
    weeks = origins.to_period("W-SUN").start_time
    week_labels = sorted(set(weeks))
    out["weekly_mae"]["week_start"] = [str(w.date()) for w in week_labels]
    for name, f in forecasts.items():
        err = f - actual
        abs_err = np.abs(err)
        per_origin = abs_err.mean(axis=1)
        order = np.argsort(per_origin)[::-1][:n_worst]
        worst = [
            {
                "origin": str(origins[i].date()),
                "mae": float(per_origin[i]),
                "bias": float(err[i].mean()),
                "holiday_hours": int(holiday[i].sum()),
                "special_hours": int(special[i].sum()),
            }
            for i in order
        ]
        out["by_model"][name] = {
            "worst_origins": worst,
            "mae_holiday_hours": float(abs_err[holiday].mean()) if holiday.any() else None,
            "mae_normal_hours": float(abs_err[~special].mean()),
            "mae_special_hours": float(abs_err[special].mean()) if special.any() else None,
            "bias_by_local_hour": [float(err[hour == h].mean()) for h in range(24)],
            "mae_by_local_hour": [float(abs_err[hour == h].mean()) for h in range(24)],
            "bias_by_dow": [float(err[dow == d].mean()) for d in range(7)],
            "mae_by_dow": [float(abs_err[dow == d].mean()) for d in range(7)],
        }
        s = pd.Series(per_origin, index=weeks).groupby(level=0).mean()
        out["weekly_mae"][name] = [round(float(s[w]), 1) for w in week_labels]
    out["dow_labels"] = DOW_ID
    return out
