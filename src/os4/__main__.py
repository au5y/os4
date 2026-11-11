"""Entry point: ``python -m os4`` (or ``os4`` once installed, or the standalone ``os4`` executable).

Runs every step by default; ``--only`` / ``--skip`` pick steps, ``--out`` changes the output folder and
``--no-progress`` hides the progress bars. ``python -m os4 --help`` lists them. ``python -m os4 lab [...]``
starts the Model Lab instead (same as ``python -m os4.lab``), so the standalone executable can run both.
"""

import argparse
import sys
from pathlib import Path

from os4 import tradespace as ts
from os4.data import load_all
from os4.export import export_model
from os4.model import architecture_table
from os4.paths import FROZEN
from os4.plots import OUTPUT_DIR, case_table, write_task1, write_task2
from os4.scenario import primary_scenario
from os4.site import write_site
from os4.speed_sensitivity import write_speed_sensitivity
from os4.tradespace import write_task3
from os4.utility import ATTRIBUTES

STEPS = ("task1", "task2", "task3", "sensitivity", "site", "excel")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m os4", description="Run the OS4 model and write its outputs. "
                                     "'python -m os4 lab --help' describes the Model Lab.")
    parser.add_argument("--only", nargs="+", choices=STEPS, metavar="STEP",
                        help=f"run only these steps (choices: {', '.join(STEPS)})")
    parser.add_argument("--skip", nargs="+", choices=STEPS, default=[], metavar="STEP",
                        help="run every step except these")
    parser.add_argument("--out", type=Path, default=OUTPUT_DIR,
                        help=f"output folder (default: {OUTPUT_DIR})")
    parser.add_argument("--no-progress", action="store_true", help="hide the tradespace progress bars")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["lab"]:
        from os4.lab.__main__ import main as lab_main
        return lab_main(argv[1:])
    args = parse_args(argv)
    steps = [s for s in (args.only or STEPS) if s not in args.skip]
    ts.SHOW_PROGRESS = not args.no_progress
    out = args.out
    (out / "media").mkdir(parents=True, exist_ok=True)

    tables = load_all()
    print(f"Loaded {len(tables)} input tables:")
    for name, df in tables.items():
        print(f"  {name:<24} {len(df):>3} rows")

    if "task1" in steps:
        print("\nTask 1 (MAU):")
        print(case_table()[["case", *(f"u_{a}" for a in ATTRIBUTES), "mau", "rank"]].round(3).to_string(index=False))
        for path in write_task1(out):
            print(f"  wrote {path}")

    scenario = primary_scenario()
    if "task2" in steps:
        print(f"\nTask 2 ({scenario.name}):")
        cols = ["architecture", "fleet_capacity_per_h", "passenger_volume", "wait_time", "availability",
                "mau", "fleet_cost_usd"]
        print(architecture_table(scenario)[cols].round(3).to_string(index=False))
        for path in write_task2(scenario, out):
            print(f"  wrote {path}")

    if "task3" in steps:
        print("\nTask 3 (tradespace):")
        for path in write_task3(scenario, out):
            print(f"  wrote {path}")

    if "sensitivity" in steps:
        print("\nTask 3 sensitivity (e-bike speed, road cap at the posted limit, no riders-per-day ceiling):")
        for path in write_speed_sensitivity(scenario, out):
            print(f"  wrote {path}")

    if "site" in steps:
        print(f"\nResults explorer (open {out / 'site' / 'index.html'}):")
        for path in write_site(scenario, out / "site", reports_dir=out):
            print(f"  wrote {path}")

    if "excel" in steps:
        print("\nExcel backup:")
        print(f"  wrote {export_model(scenario, out / 'media' / 'os4_model.xlsx')}")

    print(f"\nDone. Outputs are in {out.resolve()}")
    if FROZEN and sys.platform == "win32" and not argv and sys.stdin and sys.stdin.isatty():
        input("Press Enter to close this window.")  # a double-clicked .exe would otherwise close at once


if __name__ == "__main__":
    main()
