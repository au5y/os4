"""Model Lab presets: the Task 4 candidate scenarios and the Task 3 sensitivity cases, as configs.

Numbers in the Task 4 presets are team placeholders (each preset lists its assumptions); edit them in the
lab and save your own. The sensitivity presets come from ``speed_sensitivity.variations`` so they stay in
step with ``outputs/task3_speed_sensitivity.md``.
"""

from dataclasses import replace

import pandas as pd

from os4.lab.config import from_scenario
from os4.scenario import primary_scenario
from os4.speed_sensitivity import variations


def _demand(base: pd.DataFrame, scale_hours=(), factor: float = 1.0, keep_hours=None) -> pd.DataFrame:
    d = base.copy()
    if keep_hours is not None:
        d = d[d["hour"].isin(keep_hours)].reset_index(drop=True)
    d.loc[d["hour"].isin(scale_hours), "trips_per_hour"] *= factor
    return d


def presets() -> list[dict]:
    """Every preset: ``{id, name, group, description, assumptions, config}``."""
    base = primary_scenario()
    out = [{
        "id": "standard", "group": "Task 3 baseline", "name": "Standard weekday demand",
        "description": "The primary scenario: on-demand last-mile service from Kendall, scored over Appendix B's "
                       "full weekday and sized for the 8:00–14:00 peak (PLAN.md Q1).",
        "assumptions": ["Appendix B demand as given (1,790 trips/day)", "Road cap 21 km/h, bikes 18 km/h",
                        "Riders-per-day ceilings on (Q22)"],
        "scenario": base,
    }]

    peak = (8, 10, 12)
    red_line = replace(
        base, name="Red Line disruption: shuttle to Boston",
        demand=_demand(base.demand, peak, 1.5),
        avg_trip_km=5.0, bike_trip_km=5.0, speed_limit_kmh=25.0,
        allowed_autonomy=("A4", "A5"), goal_wait_min=20.0, goal_travel_min=20.0,
    )
    out.append({
        "id": "red_line", "group": "Task 4 candidates", "name": red_line.name,
        "description": "Red Line service is suspended; riders at Kendall need a ride to Park St / South Station, "
                       "outside the system boundary.",
        "assumptions": ["PLACEHOLDER: trips about 5 km (Kendall to Park St / South Station)",
                        "PLACEHOLDER: peak demand ×1.5 (8:00–14:00)",
                        "PLACEHOLDER: road cap 25 km/h (mix of city streets and arterials)",
                        "Outside the boundary Table 1 requires L4/L5: A4 and A5 only",
                        "Table 1 outside-boundary wait goal: 20 min; travel-time goal 20 min (placeholder)"],
        "scenario": red_line,
    })

    links_road = base.node_distances_km.values()
    network = replace(
        base, name="Point-to-point network",
        avg_trip_km=round(sum(links_road) / len(links_road), 2), bike_trip_km=round((1.6 + 1.6 + 3.1) / 3, 2),
        deadhead_fraction=0.33,
    )
    out.append({
        "id": "network", "group": "Task 4 candidates", "name": network.name,
        "description": "Trips run between all three stops, not only from Kendall, so vehicles often carry a rider "
                       "on the way back.",
        "assumptions": [f"Average road trip {network.avg_trip_km:g} km: mean of the three links, including "
                        "Lechmere–Central (3.3 km)", f"Average bike trip {network.bike_trip_km:g} km",
                        "PLACEHOLDER: empty return 0.33 of a trip (was 1.0)", "Appendix B demand as given"],
        "scenario": network,
    })

    winter = replace(base, name="Winter", speed_limit_kmh=18.0, bike_assisted_speed_kmh=12.0, range_factor=0.75)
    out.append({
        "id": "winter", "group": "Task 4 candidates", "name": winter.name,
        "description": "Snow and cold: slower streets, slower bikes, and batteries that hold less charge.",
        "assumptions": ["PLACEHOLDER: road cap 18 km/h", "PLACEHOLDER: bike assist 12 km/h",
                        "PLACEHOLDER: battery range ×0.75 (cold)", "Appendix B demand as given"],
        "scenario": winter,
    })

    window = (6, 8, 10)
    rush_demand = _demand(base.demand, keep_hours=window)
    share = rush_demand["trips_per_hour"].sum() / base.demand["trips_per_hour"].sum()
    rush = replace(
        base, name="A.m. rush only", demand=rush_demand,
        min_daily_volume=round(base.min_daily_volume * share, -1), min_offpeak_throughput=0.0,
        max_bike_trips_per_day=None, max_car_trips_per_day=None,
    )
    out.append({
        "id": "rush", "group": "Task 4 candidates", "name": rush.name,
        "description": "Only the 6:00–12:00 rush: the fleet runs for the morning and is scored on it alone.",
        "assumptions": ["Appendix B demand for 6:00–12:00 only (700 trips)",
                        f"Volume threshold scaled to that window: {rush.min_daily_volume:g} trips",
                        "No off-peak minimum; riders-per-day ceilings off (they are daily measures)",
                        "The volume utility is still on Appendix A's trips/day scale, so the MAU ceiling is lower"],
        "scenario": rush,
    })

    for key, (label, scenario) in variations(base).items():
        if key == "baseline":
            continue
        out.append({"id": f"sens_{key}", "group": "Task 3 sensitivity", "name": label,
                    "description": "From the Task 3 speed and ceiling sensitivity "
                                   "(outputs/task3_speed_sensitivity.md).",
                    "assumptions": [label], "scenario": replace(scenario, name=label)})

    return [{**{k: v for k, v in p.items() if k != "scenario"}, "config": from_scenario(p["scenario"], p["name"])}
            for p in out]
