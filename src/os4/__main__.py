"""Entry point: ``python -m os4`` (or ``os4`` once installed)."""

from os4.data import load_all
from os4.plots import case_table, write_task1
from os4.utility import ATTRIBUTES


def main() -> None:
    tables = load_all()
    print(f"Loaded {len(tables)} input tables:")
    for name, df in tables.items():
        print(f"  {name:<24} {len(df):>3} rows")

    print("\nTask 1 (MAU):")
    print(case_table()[["case", *(f"u_{a}" for a in ATTRIBUTES), "mau", "rank"]].round(3).to_string(index=False))
    for path in write_task1():
        print(f"  wrote {path}")

    print("\nTask 2 model not implemented yet (see src/os4/vehicle.py, fleet.py, tradespace.py).")


if __name__ == "__main__":
    main()
