"""Entry point: ``python -m os4`` (or ``os4`` once installed)."""

from os4.data import load_all


def main() -> None:
    tables = load_all()
    print(f"Loaded {len(tables)} input tables:")
    for name, df in tables.items():
        print(f"  {name:<24} {len(df):>3} rows")
    print("\nModel not implemented yet (see src/os4/utility.py, vehicle.py, fleet.py, tradespace.py).")


if __name__ == "__main__":
    main()
