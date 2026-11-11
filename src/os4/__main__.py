"""Entry point: ``python -m os4`` (or ``os4`` once installed, or the standalone ``os4`` executable).

Runs every step (Tasks 1-5, the explorer, the Excel backup) by default; ``--only`` / ``--skip`` pick steps, ``--out`` changes the output folder and
``--no-progress`` hides the progress bars. ``python -m os4 --help`` lists them. ``python -m os4 lab [...]``
starts the Model Lab instead (same as ``python -m os4.lab``), so the standalone executable can run both.

The standalone executable launched with no arguments (e.g. double-clicked) opens the Model Lab in the browser,
where weights and inputs can be edited; ``os4 run [options]`` (or any option, e.g. ``os4 --only task1``) runs
the batch model as ``python -m os4`` does.
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
from os4.task4 import run as run_task4
from os4.task4 import write_task4
from os4.task5 import write_task5
from os4.tradespace import write_task3
from os4.utility import ATTRIBUTES

STEPS = ("task1", "task2", "task3", "sensitivity", "task4", "task5", "site", "excel")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m os4", description="Run the OS4 model and write its outputs. "
                                     "'python -m os4 lab --help' describes the Model Lab. 'run' before the options is optional.")
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
    if argv[:1] == ["lab"] or (FROZEN and not argv):
        from os4.lab.__main__ import main as lab_main
        return lab_main(argv[1:] if argv else ["--open"])
    if argv[:1] == ["run"]:
        argv = argv[1:]
    for stream in (sys.stdout, sys.stderr):  # a Windows console may not encode every character in the tables
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
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

    scenarios = run_task4() if {"task4", "task5"} & set(steps) else None
    if "task4" in steps:
        print("\nTask 4 (Red Line disruption vs. the standard weekday, e-bikes at 18 km/h):")
        for path in write_task4(out, scenarios):
            print(f"  wrote {path}")

    if "task5" in steps:
        print("\nTask 5 (recommended concept):")
        for path in write_task5(out, scenarios):
            print(f"  wrote {path}")

    if "site" in steps:
        print(f"\nResults explorer (open {out / 'site' / 'index.html'}):")
        for path in write_site(scenario, out / "site", reports_dir=out):
            print(f"  wrote {path}")

    if "excel" in steps:
        print("\nExcel backup:")
        print(f"  wrote {export_model(scenario, out / 'media' / 'os4_model.xlsx')}")

    print(f"\nDone. Outputs are in {out.resolve()}")


if __name__ == "__main__":
    main()
