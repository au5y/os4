"""Model Lab configs: a JSON-safe description of one run (scenario, battery case, weights, fleet grid).

A config is a plain dict so it can be saved in the browser, exported as a file and hashed for the cache:

    {"schema_version": 1, "name": ..., "battery_case": "fixed" | "removable",
     "weights": {attribute: weight}, "grid": {"road": [[start, stop, step], ...], "bike": [...]},
     "scenario": {field: value}}

``FIELDS`` describes every editable scenario field for the lab's form; ``to_scenario`` turns a config into
a ``Scenario`` (unset fields keep ``primary_scenario()``'s values) and ``from_scenario`` goes the other way.
"""

from dataclasses import replace

import pandas as pd

from os4.scenario import Scenario, primary_scenario
from os4.tradespace import BIKE_SEGMENTS, ROAD_SEGMENTS
from os4.utility import ATTRIBUTES, DECISION_WEIGHTS, load_weights

SCHEMA_VERSION = 1
BATTERY_CASES = ("fixed", "removable")

# Every editable scenario field: key, form group, label, unit, PLAN.md question, and input limits.
# kind: "num" (number), "opt" (number or off: None), "list" (comma-separated numbers), "autonomy", "demand", "speeds".
FIELDS = [
    {"key": "demand", "group": "Demand", "label": "Trips per hour by 2-hour bin", "kind": "demand", "q": 5},
    # Speeds: the form shows a choice per vehicle kind (kind "speeds"); these are the values behind it.
    {"key": "road_speed_basis", "group": "Speeds", "label": "Road speed", "kind": "speeds", "q": 4,
     "choices": {"posted": "Posted speed limit", "achieved": "Achieved speed cap"}},
    {"key": "road_posted_limit_kmh", "group": "Speeds", "label": "Posted speed limit", "unit": "km/h", "kind": "num",
     "min": 5, "max": 120, "step": 0.1, "q": 4, "sub": True},
    {"key": "road_achieved_cap_kmh", "group": "Speeds", "label": "Achieved speed cap", "unit": "km/h", "kind": "num",
     "min": 5, "max": 120, "step": 0.1, "q": 4, "sub": True},
    {"key": "bike_speed_basis", "group": "Speeds", "label": "E-bike speed", "kind": "speeds", "q": 6,
     "choices": {"assisted": "Fixed assisted speed", "formula": "Appendix B formula (700·P/W)"}},
    {"key": "bike_assisted_speed_kmh", "group": "Speeds", "label": "Assisted speed", "unit": "km/h", "kind": "num",
     "min": 1, "max": 45, "step": 0.5, "q": 6, "sub": True},
    {"key": "bike_speed_limit_kmh", "group": "Speeds", "label": "E-bike speed limit (caps either)", "unit": "km/h",
     "kind": "opt", "off": "none", "min": 5, "max": 45, "step": 0.5, "q": 6, "sub": True},
    {"key": "avg_trip_km", "group": "Trips", "label": "Road trip length", "unit": "km", "kind": "num",
     "min": 0.2, "max": 30, "step": 0.05, "q": 3},
    {"key": "bike_trip_km", "group": "Trips", "label": "Bike trip length", "unit": "km", "kind": "opt",
     "off": "same as road", "min": 0.2, "max": 30, "step": 0.05, "q": 3},
    {"key": "deadhead_fraction", "group": "Trips", "label": "Empty return (share of trip)", "unit": "", "kind": "num",
     "min": 0, "max": 2, "step": 0.05, "q": 3},
    {"key": "dwell_s", "group": "Trips", "label": "Dwell per trip", "unit": "s", "kind": "num",
     "min": 0, "max": 600, "step": 5},
    {"key": "allowed_autonomy", "group": "Vehicles", "label": "Road autonomy levels allowed", "kind": "autonomy", "q": 7},
    {"key": "load_factor", "group": "Vehicles", "label": "Road load factor", "unit": "share of seats", "kind": "num",
     "min": 0.05, "max": 1, "step": 0.05, "q": 27},
    {"key": "bike_load_1", "group": "Vehicles", "label": "1-seat bike riders per seat", "unit": "", "kind": "num",
     "min": 0.05, "max": 1, "step": 0.05, "q": 16},
    {"key": "bike_load_2", "group": "Vehicles", "label": "2-seat bike riders per seat", "unit": "", "kind": "num",
     "min": 0.05, "max": 1, "step": 0.05, "q": 16},
    {"key": "range_factor", "group": "Vehicles", "label": "Battery range factor (winter < 1)", "unit": "×",
     "kind": "num", "min": 0.1, "max": 1.5, "step": 0.05},
    {"key": "bike_spare_options", "group": "Batteries", "label": "Spare packs per bike (removable case)",
     "kind": "list", "q": 15},
    {"key": "bike_swap_min", "group": "Batteries", "label": "Battery swap time", "unit": "min", "kind": "num",
     "min": 0, "max": 60, "step": 1, "q": 15},
    {"key": "min_daily_volume", "group": "Requirements", "label": "Daily volume threshold", "unit": "trips/day",
     "kind": "num", "min": 0, "max": 10000, "step": 10},
    {"key": "min_peak_throughput", "group": "Requirements", "label": "Peak throughput threshold", "unit": "trips/h",
     "kind": "num", "min": 0, "max": 1000, "step": 5},
    {"key": "min_offpeak_throughput", "group": "Requirements", "label": "Off-peak throughput threshold",
     "unit": "trips/h", "kind": "num", "min": 0, "max": 1000, "step": 5},
    {"key": "goal_wait_min", "group": "Requirements", "label": "Wait goal", "unit": "min", "kind": "num",
     "min": 0, "max": 60, "step": 0.5},
    {"key": "goal_travel_min", "group": "Requirements", "label": "Travel-time goal", "unit": "min", "kind": "num",
     "min": 0, "max": 120, "step": 0.5, "q": 11},
    {"key": "benchmark_availability", "group": "Requirements", "label": "Availability benchmark", "unit": "",
     "kind": "num", "min": 0, "max": 1, "step": 0.01},
    {"key": "max_wait_min", "group": "Requirements", "label": "Wait cap (empty or overloaded fleet)", "unit": "min",
     "kind": "num", "min": 1, "max": 120, "step": 1, "q": 18},
    {"key": "max_bike_trips_per_day", "group": "Ceilings", "label": "Max riders per bike per day", "unit": "",
     "kind": "opt", "off": "no ceiling", "min": 1, "max": 200, "step": 1, "q": 22},
    {"key": "max_car_trips_per_day", "group": "Ceilings", "label": "Max rides per small car per day", "unit": "",
     "kind": "opt", "off": "no ceiling", "min": 1, "max": 500, "step": 1, "q": 22},
    {"key": "car_max_seats", "group": "Ceilings", "label": "Largest 'small car' (seats)", "unit": "seats",
     "kind": "num", "min": 1, "max": 30, "step": 1, "q": 22},
]
SCENARIO_KEYS = tuple(f["key"] for f in FIELDS)
# 20 mph, the posted limit in Kendall and Central (PLAN.md Q4); the model's default is the achieved cap.
POSTED_LIMIT_KMH = 20 * 1.609344
# Hard limits on the fleet grid a config may ask for (the lab is shared; a run's memory grows with its grid).
GRID_MAX = {"road": 300, "bike": 500}
GRID_MAX_SIZES = 60
ACHIEVED_CAP_KMH = 21.0
ASSISTED_KMH = 18.0


def from_scenario(scenario: Scenario, name: str | None = None, battery_case: str = "removable",
                  weights: dict[str, float] | None = None, grid: dict | None = None) -> dict:
    """The config for ``scenario`` (default: removable batteries and the decision weights, the OS3A reweight,
    PLAN.md Q10/Q15; the Task 3 fleet grid). Weights stay editable in the lab."""
    loads = dict(scenario.bike_load_factors)
    return {
        "schema_version": SCHEMA_VERSION,
        "name": name or scenario.name,
        "battery_case": battery_case,
        "weights": dict(weights or load_weights(DECISION_WEIGHTS)),
        "grid": grid or {"road": [list(s) for s in ROAD_SEGMENTS], "bike": [list(s) for s in BIKE_SEGMENTS]},
        "scenario": {
            "demand": [[int(h), float(t)] for h, t in scenario.demand[["hour", "trips_per_hour"]].to_numpy()],
            **_road_speed(scenario.speed_limit_kmh),
            "bike_speed_basis": "formula" if scenario.bike_assisted_speed_kmh is None else "assisted",
            "bike_assisted_speed_kmh": scenario.bike_assisted_speed_kmh or ASSISTED_KMH,
            "bike_speed_limit_kmh": scenario.bike_speed_limit_kmh,
            "avg_trip_km": scenario.avg_trip_km,
            "bike_trip_km": scenario.bike_trip_km,
            "deadhead_fraction": scenario.deadhead_fraction,
            "dwell_s": scenario.dwell_s,
            "allowed_autonomy": list(scenario.allowed_autonomy),
            "load_factor": scenario.load_factor,
            "bike_load_1": loads.get(1, 1.0),
            "bike_load_2": loads.get(2, 2 / 3),
            "range_factor": scenario.range_factor,
            "bike_spare_options": [float(k) for k in scenario.bike_spare_options],
            "bike_swap_min": scenario.bike_swap_h * 60,
            "min_daily_volume": scenario.min_daily_volume,
            "min_peak_throughput": scenario.min_peak_throughput,
            "min_offpeak_throughput": scenario.min_offpeak_throughput,
            "goal_wait_min": scenario.goal_wait_min,
            "goal_travel_min": scenario.goal_travel_min,
            "benchmark_availability": scenario.benchmark_availability,
            "max_wait_min": scenario.max_wait_min,
            "max_bike_trips_per_day": scenario.max_bike_trips_per_day,
            "max_car_trips_per_day": scenario.max_car_trips_per_day,
            "car_max_seats": scenario.car_max_seats,
        },
    }


def validate(config: dict) -> dict:
    """Check a config's shape and fill missing parts from the baseline; raises ``ValueError`` on bad input."""
    if not isinstance(config, dict):
        raise ValueError("config must be a JSON object")
    if config.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version {config.get('schema_version')!r}")
    base = from_scenario(primary_scenario())
    out = {**base, **{k: v for k, v in config.items() if k != "scenario"}}
    given = dict(config.get("scenario") or {})
    if "speed_limit_kmh" in given and "road_speed_basis" not in given:  # configs saved before the speed choice
        given.update(_road_speed(float(given["speed_limit_kmh"])))
    if given.get("bike_assisted_speed_kmh", 0) is None and "bike_speed_basis" not in given:
        given.update(bike_speed_basis="formula", bike_assisted_speed_kmh=ASSISTED_KMH)
    out["scenario"] = {**base["scenario"], **{k: v for k, v in given.items() if k in SCENARIO_KEYS}}
    s = out["scenario"]
    if s["road_speed_basis"] not in ("posted", "achieved") or s["bike_speed_basis"] not in ("assisted", "formula"):
        raise ValueError("road_speed_basis must be posted/achieved and bike_speed_basis assisted/formula")
    if out["battery_case"] not in BATTERY_CASES:
        raise ValueError(f"battery_case must be one of {BATTERY_CASES}")
    weights = {a: float(w) for a, w in out["weights"].items()}
    if set(weights) - set(ATTRIBUTES) or not weights or abs(sum(weights.values()) - 1) > 1e-6:
        raise ValueError(f"weights must cover attributes from {ATTRIBUTES} and sum to 1")
    out["weights"] = weights
    m = out.get("mixed_max")
    if m is not None and not (isinstance(m, (list, tuple)) and len(m) == 2 and all(int(x) > 0 for x in m)):
        raise ValueError("mixed_max must be null or [road, bike] fleet-size caps for mixed fleets")
    for kind in ("road", "bike"):
        segs = out["grid"].get(kind) or []
        if not segs or not all(len(s) == 3 and 0 < s[0] <= s[1] and s[2] > 0 for s in segs):
            raise ValueError(f"grid.{kind} must be [start, stop, step] segments with 0 < start <= stop, step > 0")
        sizes = {n for a, b, step in segs for n in range(int(a), int(b) + 1, int(step))}
        if max(sizes) > GRID_MAX[kind] or len(sizes) > GRID_MAX_SIZES:
            raise ValueError(f"grid.{kind}: at most {GRID_MAX_SIZES} fleet sizes, none above {GRID_MAX[kind]}")
    demand = out["scenario"]["demand"]
    hours = [h for h, _ in demand]
    if len(demand) < 1 or any(t < 0 for _, t in demand) or len(set(hours)) != len(hours):
        raise ValueError("demand must be [hour, trips_per_hour] rows with distinct hours and trips >= 0")
    if len(demand) > 1 and len({b - a for a, b in zip(sorted(hours), sorted(hours)[1:])}) != 1:
        raise ValueError("demand bins must be evenly spaced")
    return out


def to_scenario(config: dict) -> Scenario:
    """The ``Scenario`` a config describes, for its battery case."""
    c = validate(config)
    s = c["scenario"]
    demand = pd.DataFrame(sorted(s["demand"]), columns=["hour", "trips_per_hour"])
    if len(demand) == 1:  # a single bin: one hour wide
        demand = pd.concat([demand, pd.DataFrame({"hour": [demand["hour"].iloc[0] + 1], "trips_per_hour": [0.0]})])
    spares = tuple(float(k) for k in s["bike_spare_options"]) if c["battery_case"] == "removable" else (0.0,)
    return replace(
        primary_scenario(),
        name=c["name"],
        demand=demand.reset_index(drop=True),
        speed_limit_kmh=float(s["road_posted_limit_kmh"] if s["road_speed_basis"] == "posted"
                              else s["road_achieved_cap_kmh"]),
        bike_assisted_speed_kmh=float(s["bike_assisted_speed_kmh"]) if s["bike_speed_basis"] == "assisted" else None,
        bike_speed_limit_kmh=_opt(s["bike_speed_limit_kmh"]),
        avg_trip_km=float(s["avg_trip_km"]),
        bike_trip_km=_opt(s["bike_trip_km"]),
        deadhead_fraction=float(s["deadhead_fraction"]),
        dwell_s=float(s["dwell_s"]),
        allowed_autonomy=tuple(s["allowed_autonomy"]),
        load_factor=float(s["load_factor"]),
        bike_load_factors=((1, float(s["bike_load_1"])), (2, float(s["bike_load_2"]))),
        range_factor=float(s["range_factor"]),
        bike_spare_options=spares,
        bike_swap_h=float(s["bike_swap_min"]) / 60,
        min_daily_volume=float(s["min_daily_volume"]),
        min_peak_throughput=float(s["min_peak_throughput"]),
        min_offpeak_throughput=float(s["min_offpeak_throughput"]),
        goal_wait_min=float(s["goal_wait_min"]),
        goal_travel_min=float(s["goal_travel_min"]),
        benchmark_availability=float(s["benchmark_availability"]),
        max_wait_min=float(s["max_wait_min"]),
        max_bike_trips_per_day=_opt(s["max_bike_trips_per_day"]),
        max_car_trips_per_day=_opt(s["max_car_trips_per_day"]),
        car_max_seats=int(s["car_max_seats"]),
    )


def _road_speed(speed_limit_kmh: float) -> dict:
    """The road-speed choice for a scenario's cap: the posted limit if it equals 20 mph, else an achieved cap."""
    posted = abs(speed_limit_kmh - POSTED_LIMIT_KMH) < 1e-6
    return {"road_speed_basis": "posted" if posted else "achieved", "road_posted_limit_kmh": POSTED_LIMIT_KMH,
            "road_achieved_cap_kmh": ACHIEVED_CAP_KMH if posted else speed_limit_kmh}


def _opt(v):
    return None if v is None or v == "" else float(v)
