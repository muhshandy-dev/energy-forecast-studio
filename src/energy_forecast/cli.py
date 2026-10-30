"""CLI: ``energy-forecast data | run | export-web``."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from . import data, experiment, export_web

REPORTS = {"opsd": Path("reports"), "mirror-dev": Path("reports/dev")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="energy-forecast")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_data = sub.add_parser("data", help="unduh dan verifikasi data mentah")
    p_data.add_argument("--source", default="opsd", choices=sorted(data.SOURCES))
    p_data.add_argument("--data-dir", type=Path, default=data.DEFAULT_DATA_DIR)
    p_data.add_argument("--pin", action="store_true", help="kunci SHA-256 ke data/manifest.json")

    p_run = sub.add_parser("run", help="seleksi validasi, evaluasi uji, prakiraan perencanaan")
    p_run.add_argument("--source", default="opsd", choices=sorted(data.SOURCES))
    p_run.add_argument("--data-dir", type=Path, default=data.DEFAULT_DATA_DIR)
    p_run.add_argument("--workers", type=int, default=0)

    p_web = sub.add_parser("export-web", help="tulis JSON statis untuk website")
    p_web.add_argument("--reports", type=Path, default=REPORTS["opsd"])
    p_web.add_argument("--out", type=Path, default=Path("web/public/data"))
    p_web.add_argument("--allow-dev", action="store_true", help="izinkan data uji coba")

    args = ap.parse_args(argv)
    if args.cmd == "data":
        hashes = data.fetch(args.source, args.data_dir)
        if args.pin:
            data.pin_manifest(args.source, hashes)
        print(json.dumps(hashes, indent=2))
    elif args.cmd == "run":
        t0 = time.time()
        hashes = data.verify(args.source, args.data_dir)
        ls = data.load(args.source, args.data_dir)
        results = experiment.run_experiment(ls, hashes, args.workers)
        experiment.write_outputs(results, REPORTS[args.source])
        print(f"selesai dalam {time.time() - t0:.0f} s -> {REPORTS[args.source]}")
    elif args.cmd == "export-web":
        export_web.export(args.reports, args.out, allow_dev=args.allow_dev)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
