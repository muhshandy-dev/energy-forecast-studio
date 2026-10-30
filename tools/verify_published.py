"""Pemeriksaan independen: angka di website = angka yang dihitung ulang dari prakiraan uji.

Membaca reports/test_forecasts.npz (prakiraan mentah), menghitung ulang MAE, MASE, dan
coverage tanpa memakai kode paket, lalu membandingkannya dengan reports/results.json dan
web/public/data/*.json. Juga memastikan situs tidak menerbitkan data uji coba.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
WEB = ROOT / "web" / "public" / "data"
MAX_BYTES = 25 * 1024 * 1024


def close(a: float, b: float, rel: float = 1e-6) -> bool:
    return abs(a - b) <= rel * max(1.0, abs(a), abs(b))


def main() -> int:
    errors: list[str] = []
    results = json.loads((REPORTS / "results.json").read_text(encoding="utf-8"))
    web_metrics = json.loads((WEB / "metrics.json").read_text(encoding="utf-8"))
    meta = json.loads((WEB / "meta.json").read_text(encoding="utf-8"))
    planning = json.loads((WEB / "planning.json").read_text(encoding="utf-8"))
    replay = json.loads((WEB / "replay.json").read_text(encoding="utf-8"))
    arr = np.load(REPORTS / "test_forecasts.npz")

    if meta["dev_data"] or not results["source"]["publishable"]:
        errors.append("situs memuat data uji coba, bukan OPSD")
    if web_metrics["metrics"] != results["metrics"]:
        errors.append("metrics.json berbeda dari results.json")
    if planning != results["planning"]:
        errors.append("planning.json berbeda dari results.json")

    scale = results["protocol"]["mase_scale_mw"]
    actual = arr["actual"].astype(np.float64)
    test = results["metrics"]["test"]
    for key in arr.files:
        if not key.startswith("pred_"):
            continue
        name = key[5:]
        pred = arr[key].astype(np.float64)
        q = arr[f"q_{name}"].astype(np.float64)
        mae = float(np.mean(np.abs(actual - pred)))
        # npz disimpan float32: toleransi relatif 1e-4
        if not close(mae, test[name]["week_ahead"]["mae"], 1e-4):
            errors.append(f"{name}: MAE {mae} != {test[name]['week_ahead']['mae']}")
        if not close(mae / scale, test[name]["week_ahead"]["mase"], 1e-4):
            errors.append(f"{name}: MASE tidak cocok")
        mae24 = float(np.mean(np.abs(actual[:, :24] - pred[:, :24])))
        if not close(mae24, test[name]["day_ahead"]["mae"], 1e-4):
            errors.append(f"{name}: MAE 24 jam tidak cocok")
        for i, lv in enumerate(("80", "95")):
            lo, hi = pred + q[:, 2 * i], pred + q[:, 2 * i + 1]
            cov = float(np.mean((actual >= lo) & (actual <= hi)))
            want = test[name]["interval"][lv]["coverage"]
            if abs(cov - want) > 2e-3:  # pembulatan float32 di batas interval
                errors.append(f"{name}: coverage {lv}% {cov} != {want}")
        idx = [
            i
            for i, o in enumerate(arr["origins_ns"])
            if str(np.datetime64(int(o), "ns"))[:10] in {o[:10] for o in replay["origins_utc"]}
        ]
        got = np.asarray(replay["models"][name]["point_mw"], dtype=float)
        if np.max(np.abs(got - np.rint(pred[idx]))) > 1:
            errors.append(f"{name}: replay.json tidak cocok dengan prakiraan uji")

    for f in WEB.glob("*.json"):
        if f.stat().st_size > MAX_BYTES:
            errors.append(f"{f.name} melebihi 25 MiB")

    if errors:
        print("GAGAL:\n- " + "\n- ".join(errors))
        return 1
    print(f"OK: {sum(k.startswith('pred_') for k in arr.files)} model, metrik uji dan berkas web konsisten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
