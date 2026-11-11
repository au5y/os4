"""Model Lab presets: the Tasks 4-5 scenarios, the other Task 4 candidates and the Task 3 sensitivity cases,
as configs.

The Tasks 4-5 presets are the model's own scenarios (``scenario.weekday_scenario`` and
``scenario.red_line_scenario``, PLAN.md Q29-Q30). Numbers in the other candidates are placeholders (each preset
lists its assumptions); edit them in the lab and save your own. The sensitivity presets come from ``speed_sensitivity.variations`` so they stay in
step with ``outputs/task3_speed_sensitivity.md``.
"""

from dataclasses import replace

import pandas as pd

from os4.lab.config import POSTED_LIMIT_KMH, from_scenario
from os4.scenario import (RED_LINE_PEAK_FACTOR, RED_LINE_ROAD_CAP_KMH, RED_LINE_TRIP_KM, primary_scenario,
                          red_line_scenario, weekday_scenario)
from os4.speed_sensitivity import variations


def _demand(base: pd.DataFrame, scale_hours=(), factor: float = 1.0, keep_hours=None) -> pd.DataFrame:
    d = base.copy()
    if keep_hours is not None:
        d = d[d["hour"].isin(keep_hours)].reset_index(drop=True)
    d.loc[d["hour"].isin(scale_hours), "trips_per_hour"] *= factor
    return d


def presets() -> list[dict]:
    """Every preset: ``{id, name, group, description, assumptions, config}``.

    Every preset uses the model's e-bikes (18 km/h assist, removable batteries with spares, PLAN.md Q6/Q15) and
    the OS3A reweight (Q10, editable). "Standard weekday demand" caps road vehicles at the posted 20 mph limit;
    "Task 3 report settings" keeps the model's 21 km/h achieved cap.
    """
    report = primary_scenario()
    base = replace(report, speed_limit_kmh=POSTED_LIMIT_KMH)
    out = [{
        "id": "standard", "group": "Baseline", "name": "Standard weekday demand",
        "description": "The primary scenario: on-demand last-mile service from Kendall, scored over Appendix B's "
                       "full weekday and sized for the 8:00–14:00 peak (PLAN.md Q1), with the lab's default speeds.",
        "assumptions": ["Appendix B demand as given (1,790 trips/day)",
                        "Road vehicles capped at the posted 20 mph limit (32.2 km/h)",
                        "E-bikes at the 18 km/h assist, removable batteries (Q6, Q15)", "Riders-per-day ceilings on (Q22)"],
        "scenario": base,
    }, {
        "id": "report", "group": "Baseline", "name": "Task 3 report settings",
        "description": "Exactly what the Task 3 report runs: the standard weekday scenario with the model's own "
                       "speed choices.",
        "assumptions": ["Road vehicles capped at the 21 km/h achieved speed (Q4)",
                        "E-bikes at the 18 km/h assist, removable batteries (Q6, Q15)", "Riders-per-day ceilings on (Q22)"],
        "scenario": replace(report, name="Task 3 report settings"),
    }]

    s1, red_line = weekday_scenario(), red_line_scenario()
    out.append({
        "id": "weekday_s1", "group": "Tasks 4–5", "name": "Scenario 1: standard weekday",
        "description": "Scenario 1 of Tasks 4–5: the Task 3 report settings.",
        "assumptions": ["Appendix B demand as given (1,790 trips/day)", "Road vehicles capped at 21 km/h (Q4)",
                        "E-bikes at the 18 km/h assist, removable batteries (Q6, Q15)", "Riders-per-day ceilings on (Q22)"],
        "scenario": replace(s1, name="Scenario 1: standard weekday"),
    })
    out.append({
        "id": "red_line", "group": "Tasks 4–5", "name": "Scenario 2: Red Line disruption (Task 4)",
        "description": "The Task 4 scenario (PLAN.md Q29): Red Line service is suspended; riders at Kendall need a "
                       "ride to Park St / South Station, outside the system boundary.",
        "assumptions": [f"Trips {RED_LINE_TRIP_KM:g} km (Kendall to Park St / South Station; team estimate)",
                        f"Peak demand ×{RED_LINE_PEAK_FACTOR:g} (8:00–14:00; team estimate)",
                        f"Road cap {RED_LINE_ROAD_CAP_KMH:g} km/h (arterial roads; team estimate)",
                        "Outside the boundary Table 1 requires L4/L5: A4 and A5 only",
                        "Table 1 outside-boundary goals: 20-min wait, 20-min travel",
                        "E-bikes at the 18 km/h assist, removable batteries (Q6, Q15)"],
        "scenario": replace(red_line, name="Scenario 2: Red Line disruption (Task 4)"),
    })

    links_road = base.node_distances_km.values()
    network = replace(
        base, name="Point-to-point network",
        avg_trip_km=round(sum(links_road) / len(links_road), 2), bike_trip_km=round((1.6 + 1.6 + 3.1) / 3, 2),
        deadhead_fraction=0.33,
    )
    out.append({
        "id": "network", "group": "Other Task 4 candidates", "name": network.name,
        "description": "Trips run between all three stops, not only from Kendall, so vehicles often carry a rider "
                       "on the way back.",
        "assumptions": [f"Average road trip {network.avg_trip_km:g} km: mean of the three links, including "
                        "Lechmere–Central (3.3 km)", f"Average bike trip {network.bike_trip_km:g} km",
                        "PLACEHOLDER: empty return 0.33 of a trip (was 1.0)", "Appendix B demand as given",
                        "Road cap at the posted 20 mph limit; e-bikes at the 18 km/h assist"],
        "scenario": network,
    })

    winter = replace(base, name="Winter", speed_limit_kmh=18.0, bike_assisted_speed_kmh=12.0, range_factor=0.75)
    out.append({
        "id": "winter", "group": "Other Task 4 candidates", "name": winter.name,
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
        "id": "rush", "group": "Other Task 4 candidates", "name": rush.name,
        "description": "Only the 6:00–12:00 rush: the fleet runs for the morning and is scored on it alone.",
        "assumptions": ["Appendix B demand for 6:00–12:00 only (700 trips)",
                        f"Volume threshold scaled to that window: {rush.min_daily_volume:g} trips",
                        "No off-peak minimum; riders-per-day ceilings off (they are daily measures)",
                        "The volume utility is still on Appendix A's trips/day scale, so the MAU ceiling is lower",
                        "Road cap at the posted 20 mph limit; e-bikes at the 18 km/h assist"],
        "scenario": rush,
    })

    for key, (label, scenario) in variations(report).items():
        if key == "baseline":
            continue
        out.append({"id": f"sens_{key}", "group": "Task 3 sensitivity", "name": label,
                    "description": "From the Task 3 speed and ceiling sensitivity, relative to the Task 3 "
                                   "report settings (outputs/task3_speed_sensitivity.md).",
                    "assumptions": [label], "scenario": replace(scenario, name=label)})

    return [{**{k: v for k, v in p.items() if k != "scenario"}, "config": from_scenario(p["scenario"], p["name"])}
            for p in out]
