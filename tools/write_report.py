"""Tulis docs/laporan-evaluasi.md langsung dari reports/results.json (angka tidak diketik tangan)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL = {
    "ensemble": "Gabungan",
    "lightgbm": "LightGBM",
    "mstl_ets": "MSTL + ETS",
    "snaive168": "Naive mingguan",
    "snaive24": "Naive harian",
}
PERIOD = {
    "validation": "Validasi 2018",
    "test": "Uji 2019 s.d. Sep 2020",
    "test_2019": "Uji 2019",
    "test_2020": "Uji 2020 (Jan s.d. Sep)",
}


def f0(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def f2(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def p1(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def sgn(x: float) -> str:
    return ("+" if x > 0 else "−" if x < 0 else "") + f0(abs(x))


def table(period: dict) -> list[str]:
    rows = [
        "| Model | MAE 24 jam | MAE 7 hari (CI 95%) | MASE 7 hari | Selisih vs naive mingguan (CI 95%) "
        "| Coverage 80% | Coverage 95% | Lebar 80% |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for m in LABEL:
        if m not in period:
            continue
        r = period[m]
        w = r["week_ahead"]
        diff = (
            "acuan"
            if m == "snaive168"
            else f"{sgn(w['mae_minus_snaive168'])} ({sgn(w['mae_minus_snaive168_ci95'][0])} s.d. "
            f"{sgn(w['mae_minus_snaive168_ci95'][1])})"
        )
        rows.append(
            f"| {LABEL[m]} | {f0(r['day_ahead']['mae'])} | {f0(w['mae'])} ({f0(w['mae_ci95'][0])}–"
            f"{f0(w['mae_ci95'][1])}) | {f2(w['mase'])} | {diff} | {p1(r['interval']['80']['coverage'])} "
            f"| {p1(r['interval']['95']['coverage'])} | {f0(r['interval']['80']['mean_width'])} |"
        )
    return rows


def comparison(r: dict, v1: dict) -> list[str]:
    out = [
        "## Perbandingan dengan v1 (uji 2019 s.d. Sep 2020)",
        "",
        "v1 adalah hasil resmi pertama dengan protokol yang dikunci sebelum uji pernah dilihat. "
        "v2 dirancang **sesudah** hasil uji v1 terlihat (terutama kegagalan MSTL + ETS di hari "
        "libur), walaupun semua pilihan v2 tetap diambil hanya dari validasi 2018. Karena itu "
        "kenaikan v2 di periode uji bukan estimasi holdout buta; angka validasi v2 di atas adalah "
        "pembanding yang lebih adil.",
        "",
        "| Model | Versi | MAE 24 jam | MAE 7 hari | MASE 7 hari | Coverage 80% | Coverage 95% |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for m in LABEL:
        for tag, res in (("v1", v1), ("v2", r)):
            t = res["metrics"]["test"].get(m)
            if t is None:
                continue
            out.append(
                f"| {LABEL[m]} | {tag} | {f0(t['day_ahead']['mae'])} | {f0(t['week_ahead']['mae'])} "
                f"| {f2(t['week_ahead']['mase'])} | {p1(t['interval']['80']['coverage'])} "
                f"| {p1(t['interval']['95']['coverage'])} |"
            )
    return out + [""]


def main(reports: Path) -> str:
    r = json.loads((reports / "results.json").read_text(encoding="utf-8"))
    pr = r["protocol"]
    v1_path = reports / "v1" / "results.json"
    v1 = json.loads(v1_path.read_text(encoding="utf-8")) if v1_path.exists() else None
    out = [
        "# Laporan evaluasi",
        "",
        "Dibuat otomatis oleh `tools/write_report.py` dari `reports/results.json`. Jangan diedit tangan.",
        "",
        f"- Protokol: {pr.get('version', 'v1')}",
        f"- Sumber data: {r['source']['name']} ({r['source']['license']})",
        f"- SHA-256: {', '.join(f'`{k}` `{v}`' for k, v in r['source']['sha256'].items())}",
        f"- Origin validasi: {pr['validation_origins'][0]} s.d. {pr['validation_origins'][1]}; "
        f"origin uji: {pr['test_origins'][0]} s.d. {pr['test_origins'][1]} (harian, 00:00 UTC, "
        f"horizon {pr['horizon_h']} jam)",
        f"- Skala MASE: {f0(pr['mase_scale_mw'])} MW ({pr['mase_scale_definition']})",
        f"- Interval: {pr['interval_method']}; CI: bootstrap blok {pr['bootstrap']['block_days']} hari, "
        f"{pr['bootstrap']['resamples']} ulangan, seed {pr['bootstrap']['seed']}",
        "",
        "MAE dan lebar dalam MW. Selisih negatif berarti lebih akurat daripada naive mingguan.",
        "",
    ]
    for key, title in PERIOD.items():
        out += [
            f"## {title} ({r['metrics'][key]['n_origins']} origin)",
            "",
            *table(r["metrics"][key]),
            "",
        ]
    if v1 is not None:
        out += comparison(r, v1)
    out += ["## Seleksi di validasi", "", "| Kandidat | MAE 7 hari validasi |", "|---|---:|"]
    for fam in ("mstl_ets", "lightgbm"):
        for row in r["selection"][fam]:
            params = ", ".join(f"{k}={v}" for k, v in row["params"].items() if k != "target")
            out.append(f"| {LABEL[fam]} {params} | {f0(row['val_mae_week_ahead'])} |")
    if "ensemble" in r["selection"]:
        out += [
            "",
            "Bobot gabungan per hari horizon (porsi LightGBM; sisanya MSTL + ETS), dipilih di validasi:",
            "",
            "| Hari | Bobot LightGBM | MAE validasi gabungan | Hanya LightGBM | Hanya MSTL + ETS |",
            "|---:|---:|---:|---:|---:|",
        ]
        for row in r["selection"]["ensemble"]:
            out.append(
                f"| {row['day']} | {f2(row['weight_lightgbm'])} | {f0(row['val_mae'])} "
                f"| {f0(row['val_mae_lightgbm_only'])} | {f0(row['val_mae_mstl_only'])} |"
            )
        t = r["metrics"]["test"]["ensemble"]["week_ahead"]
        if "mae_minus_lightgbm" in t:
            out += [
                "",
                f"Uji: selisih MAE 7 hari gabungan dikurangi LightGBM {sgn(t['mae_minus_lightgbm'])} MW "
                f"(CI 95% {sgn(t['mae_minus_lightgbm_ci95'][0])} s.d. "
                f"{sgn(t['mae_minus_lightgbm_ci95'][1])}).",
            ]
    out += ["", "| Model | Jendela interval terpilih (hari) | Jenis residual |", "|---|---:|---|"]
    for m, info in r["models"].items():
        mode = {"absolute": "absolut", "relative": "relatif"}.get(
            info.get("conformal_residual", "absolute")
        )
        out.append(f"| {LABEL[m]} | {info['conformal_window_days']} | {mode} |")
    out += ["", "## Analisis kegagalan (uji)", ""]
    for m in [
        x for x in ("ensemble", "lightgbm", "mstl_ets", "snaive168") if x in r["errors"]["by_model"]
    ]:
        e = r["errors"]["by_model"][m]
        worst = ", ".join(f"{w['origin']} ({f0(w['mae'])})" for w in e["worst_origins"][:5])
        out.append(
            f"- **{LABEL[m]}**: MAE jam biasa {f0(e['mae_normal_hours'])}, jam libur nasional "
            f"{f0(e['mae_holiday_hours'] or 0)}, libur + 24–31 Des {f0(e['mae_special_hours'] or 0)}. "
            f"Origin terburuk: {worst}."
        )
    out += [
        "",
        "## Lingkungan",
        "",
        ", ".join(f"{k} {v}" for k, v in r["environment"].items()),
        "",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    reports = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "reports"
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs" / "laporan-evaluasi.md"
    target.write_text(main(reports), encoding="utf-8")
    print(f"ditulis: {target}")
