"""Protokol eksperimen yang dikunci sebelum melihat hasil uji.

Semua waktu dalam UTC. Origin = saat prakiraan dibuat (00:00 UTC setiap hari); prakiraan
mencakup jam ``origin`` sampai ``origin + 167 jam`` (h = 1..168). Model hanya boleh memakai
data dengan stempel waktu < origin.
"""

from __future__ import annotations

import pandas as pd

HORIZON = 168  # jam (7 hari)
DAY_AHEAD = 24  # h 1..24 dilaporkan sebagai "sehari ke depan"
SEASON_DAY = 24
SEASON_WEEK = 168

DATA_END = pd.Timestamp("2020-09-30 23:00", tz="UTC")  # akhir rilis OPSD 2020-10-06

# Skala MASE: MAE seasonal naive mingguan (m=168) di dalam periode latih awal.
SCALE_START = pd.Timestamp("2015-01-01 00:00", tz="UTC")
SCALE_END = pd.Timestamp("2017-12-31 23:00", tz="UTC")

# Origin pemanasan hanya untuk mengumpulkan residual kalibrasi interval, tidak dinilai.
WARMUP = (pd.Timestamp("2017-10-01", tz="UTC"), pd.Timestamp("2017-12-31", tz="UTC"))
VALIDATION = (pd.Timestamp("2018-01-01", tz="UTC"), pd.Timestamp("2018-12-31", tz="UTC"))
# Origin terakhir yang seluruh 168 jamnya masih punya data aktual.
TEST = (pd.Timestamp("2019-01-01", tz="UTC"), DATA_END - pd.Timedelta(hours=HORIZON - 1))

# Prakiraan perencanaan: dibuat dari seluruh data, untuk 7 hari setelah data terakhir.
PLANNING_ORIGIN = DATA_END + pd.Timedelta(hours=1)

INTERVAL_LEVELS = (0.80, 0.95)
# Grid kuantil prakiraan perencanaan (untuk peluang melampaui batas kapasitas di browser).
QUANTILE_GRID = (0.025, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.975)

BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_BLOCK_DAYS = 7
SEED = 20261029

TIMEZONE = "Europe/Berlin"


def origins(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.date_range(start, end, freq="1D", tz="UTC")


def period_of(origin: pd.Timestamp) -> str:
    if origin < VALIDATION[0]:
        return "warmup"
    if origin < TEST[0]:
        return "validation"
    return "test"
