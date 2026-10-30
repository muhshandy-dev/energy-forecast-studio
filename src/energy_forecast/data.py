"""Pengambilan, verifikasi, dan pemuatan data beban listrik Jerman per jam.

Sumber resmi: Open Power System Data (OPSD), paket ``time_series`` versi 2020-10-06,
kolom ``DE_load_actual_entsoe_transparency`` (MW, rata-rata per jam, UTC). Lisensi CC BY 4.0.

Sumber ``mirror-dev`` hanya untuk pengembangan saat host OPSD tidak bisa dijangkau.
Hasil dari sumber itu tidak boleh diterbitkan (lihat ``export_web``).
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

OPSD_VERSION = "2020-10-06"
OPSD_URL = (
    "https://data.open-power-system-data.org/time_series/"
    f"{OPSD_VERSION}/time_series_60min_singleindex.csv"
)
OPSD_COLUMN = "DE_load_actual_entsoe_transparency"

MIRROR_URL = (
    "https://huggingface.co/datasets/ken1711/DE_electricity_load-data/resolve/main/"
    "Germany/Germany_ENTSO-E_{year}.csv"
)
MIRROR_YEARS = range(2015, 2021)

DEFAULT_DATA_DIR = Path("data/raw")
MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "manifest.json"

# Celah sampai 3 jam diisi interpolasi linear; celah lebih panjang dianggap rusak.
MAX_INTERPOLATED_GAP_H = 3

SOURCES = {
    "opsd": {
        "name": "Open Power System Data, Time series " + OPSD_VERSION,
        "license": "CC BY 4.0",
        "url": OPSD_URL,
        "publishable": True,
    },
    "mirror-dev": {
        "name": "Salinan ENTSO-E Jerman di HuggingFace (ken1711), khusus pengembangan",
        "license": "tidak dicantumkan oleh pengunggah",
        "url": MIRROR_URL.format(year="{2015..2020}"),
        "publishable": False,
    },
}


@dataclass(frozen=True)
class LoadSeries:
    """Deret beban per jam (UTC) beserta catatan kualitas datanya."""

    y: pd.Series
    source: str
    quality: dict


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path, retries: int = 4) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:  # noqa: S310
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            tmp.replace(dest)
            return
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(2 * 2**attempt)


def raw_files(source: str, data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, Path]:
    data_dir = Path(data_dir)
    if source == "opsd":
        return {"time_series_60min_singleindex.csv": data_dir / "opsd" / OPSD_URL.rsplit("/")[-1]}
    if source == "mirror-dev":
        return {
            f"Germany_ENTSO-E_{y}.csv": data_dir / "mirror-dev" / f"Germany_ENTSO-E_{y}.csv"
            for y in MIRROR_YEARS
        }
    raise ValueError(f"sumber tidak dikenal: {source}")


def _urls(source: str) -> dict[str, str]:
    if source == "opsd":
        return {"time_series_60min_singleindex.csv": OPSD_URL}
    return {f"Germany_ENTSO-E_{y}.csv": MIRROR_URL.format(year=y) for y in MIRROR_YEARS}


def read_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def fetch(source: str = "opsd", data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, str]:
    """Unduh berkas mentah lalu cocokkan SHA-256 dengan manifest yang dikunci (bila ada)."""
    files = raw_files(source, data_dir)
    urls = _urls(source)
    for name, dest in files.items():
        if not dest.exists():
            _download(urls[name], dest)
    return verify(source, data_dir)


def verify(source: str = "opsd", data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, str]:
    """Hitung SHA-256 tiap berkas. Jika manifest sudah mengunci hash, ketidakcocokan = galat."""
    hashes = {name: sha256_of(p) for name, p in raw_files(source, data_dir).items()}
    pinned = read_manifest().get(source, {}).get("sha256", {})
    for name, digest in hashes.items():
        if name in pinned and pinned[name] != digest:
            raise ValueError(f"SHA-256 {name} berbeda dari manifest: {digest} != {pinned[name]}")
    return hashes


def pin_manifest(source: str, hashes: dict[str, str]) -> None:
    manifest = read_manifest()
    manifest[source] = {**SOURCES[source], "sha256": hashes}
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


def _read_opsd(path: Path) -> pd.Series:
    df = pd.read_csv(path, usecols=["utc_timestamp", OPSD_COLUMN])
    idx = pd.to_datetime(df["utc_timestamp"], utc=True)
    return pd.Series(df[OPSD_COLUMN].to_numpy(dtype=float), index=idx)


def _read_mirror(paths: list[Path]) -> pd.Series:
    # Berkas salinan memakai waktu lokal Jerman (jam berulang saat DST berakhir) per 15 menit.
    parts = []
    for p in paths:
        df = pd.read_csv(p, parse_dates=["Timestamp"])
        ts = df["Timestamp"].dt.tz_localize(
            "Europe/Berlin", ambiguous="infer", nonexistent="shift_forward"
        )
        parts.append(pd.Series(df["Germany"].to_numpy(dtype=float), index=ts.dt.tz_convert("UTC")))
    s = pd.concat(parts).sort_index()
    s = s[~s.index.duplicated(keep="first")]
    return s.resample("1h").mean()


def clean_hourly(raw: pd.Series) -> tuple[pd.Series, dict]:
    """Susun ulang ke grid per jam penuh, isi celah pendek, dan catat kualitasnya."""
    raw = raw.sort_index()
    n_dup = int(raw.index.duplicated().sum())
    raw = raw[~raw.index.duplicated(keep="first")]
    first, last = raw.first_valid_index(), raw.last_valid_index()
    raw = raw.loc[first:last]
    grid = pd.date_range(first, last, freq="1h", tz="UTC")
    y = raw.reindex(grid)
    missing = y.isna()
    # Panjang tiap celah berurutan.
    run_id = (missing != missing.shift()).cumsum()
    run_len = missing.groupby(run_id).transform("sum")
    long_gap = missing & (run_len > MAX_INTERPOLATED_GAP_H)
    y = y.interpolate(method="time", limit_area="inside")
    y[long_gap] = np.nan
    nonpositive = int((y <= 0).sum())
    quality = {
        "start_utc": first.isoformat(),
        "end_utc": last.isoformat(),
        "n_hours": int(len(y)),
        "n_duplicates_dropped": n_dup,
        "n_missing_raw": int(missing.sum()),
        "n_interpolated": int((missing & ~long_gap).sum()),
        "n_long_gap_hours": int(long_gap.sum()),
        "n_nonpositive": nonpositive,
        "max_interpolated_gap_h": MAX_INTERPOLATED_GAP_H,
    }
    if long_gap.any():
        raise ValueError(f"ada celah > {MAX_INTERPOLATED_GAP_H} jam: {quality}")
    if nonpositive:
        raise ValueError(f"ada nilai beban <= 0: {quality}")
    y.name = "load_mw"
    return y, quality


def load(source: str = "opsd", data_dir: Path = DEFAULT_DATA_DIR) -> LoadSeries:
    files = list(raw_files(source, data_dir).values())
    missing = [str(p) for p in files if not p.exists()]
    if missing:
        raise FileNotFoundError(f"data belum diunduh ({missing}); jalankan: energy-forecast data")
    raw = _read_opsd(files[0]) if source == "opsd" else _read_mirror(files)
    y, quality = clean_hourly(raw)
    return LoadSeries(y=y, source=source, quality=quality)
