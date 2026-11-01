"""Entry point: ``python -m os4`` (or ``os4`` once installed)."""

from os4.data import load_all
from os4.export import OUTPUT_DIR, export_model
from os4.model import architecture_table
from os4.plots import case_table, write_task1
from os4.scenario import primary_scenario
from os4.utility import ATTRIBUTES
from os4.vehicle import all_variants


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
    variants = all_variants(scenario)
    table = architecture_table(scenario)
    print(f"\nTask 2 ({scenario.name}): {len(variants)} feasible vehicle variants")
    cols = ["architecture", "fleet_capacity_per_h", "passenger_volume", "wait_time", "availability",
            "mau", "fleet_cost_usd"]
    print(table[cols].round(3).to_string(index=False))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in (("task2_variants", variants), ("task2_architectures", table)):
        path = OUTPUT_DIR / f"{name}.csv"
        df.round(4).to_csv(path, index=False)
        print(f"  wrote {path}")
    print(f"  wrote {export_model(scenario)}")


if __name__ == "__main__":
    main()
