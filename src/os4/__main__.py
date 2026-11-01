"""Entry point: ``python -m os4`` (or ``os4`` once installed)."""

from os4.data import load_all
from os4.export import export_model
from os4.model import architecture_table
from os4.plots import case_table, write_task1, write_task2
from os4.scenario import primary_scenario
from os4.tradespace import write_task3
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

    scenario = primary_scenario()
    print(f"\nTask 2 ({scenario.name}):")
    cols = ["architecture", "fleet_capacity_per_h", "passenger_volume", "wait_time", "availability",
            "mau", "fleet_cost_usd"]
    print(architecture_table(scenario)[cols].round(3).to_string(index=False))
    for path in write_task2(scenario):
        print(f"  wrote {path}")

    print("\nTask 3 (tradespace):")
    for path in write_task3(scenario):
        print(f"  wrote {path}")

    print("\nExcel backup:")
    print(f"  wrote {export_model(scenario)}")


if __name__ == "__main__":
    main()
