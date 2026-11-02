"""Task 2 glue: (fleet, scenario) -> MoPs, MAU, and cost.

This is the single entry point Tasks 3-6 call; swap the ``Scenario`` to
re-evaluate the same architectures under different conditions.
"""

import math

import numpy as np
import pandas as pd

from os4.data import load
from os4.fleet import (
    Fleet,
    average_wait_min,
    cycle_time_min,
    daily_passenger_volume,
    _trip_km,
    energy_per_pkm,
    fleet_availability,
    fleet_capacity_per_h,
    fleet_cost_usd,
    fleet_size,
    peak_throughput,
    vehicle_availability,
    vehicle_capacity_per_h,
)
from os4.scenario import Scenario
from os4.utility import load_weights, mau, sau, weighted_mau
from os4.vehicle import get_variant

# One road and one bike variant to work by hand (tests/test_vehicle.py checks them).
HAND_CALC_VARIANTS = ("C2-P2-G3-M2-A3", "B2-E1-G2-K2")

# F (proposed, for the group to confirm): the Task 3 reference architecture, chosen from design
# reasoning rather than from the tradespace. C4: the "small on-demand EV shuttles from a central hub"
# MIT P&T asked for [[15]](references.md#ref-15); A3: the minimum autonomy inside the boundary;
# M2: the smallest motor that reaches the speed cap; G3: the fastest charger, for availability;
# P2: the smallest pack that covers a service day (~18 h at 21 km/h = ~380 km).
REFERENCE_VARIANT = "C4-P2-G3-M2-A3"
# Fleet sized by load management at the peak load point [[5]](references.md#ref-5):
# f >= P / (X * C_car), with X = 0.90 (the textbook example's value; choosing X is open, see
# CLAUDE.md "Fleet sizing").
REFERENCE_MAX_LOAD_RATIO = 0.90


def meets_thresholds(capacity, volume, scenario: Scenario):
    """Table 1 threshold requirements: daily volume, peak and off-peak throughput (vectorized).

    Fleet capacity is the same all day, so it is checked against both throughput thresholds.
    """
    return (
        (np.asarray(volume) >= scenario.min_daily_volume)
        & (np.asarray(capacity) >= scenario.min_peak_throughput)
        & (np.asarray(capacity) >= scenario.min_offpeak_throughput)
    )


def requirement_flags(df: pd.DataFrame, scenario: Scenario) -> pd.DataFrame:
    """Pass/fail columns for the thresholds, the "desired" goals and the availability benchmark."""
    return pd.DataFrame({
        "meets_thresholds": meets_thresholds(df["fleet_capacity_per_h"], df["passenger_volume"], scenario),
        "meets_wait_goal": df["wait_time"] <= scenario.goal_wait_min,
        "meets_travel_goal": df["travel_time"] <= scenario.goal_travel_min,
        "meets_availability_benchmark": df["availability"] >= scenario.benchmark_availability,
    }, index=df.index)


def evaluate(fleet: Fleet, scenario: Scenario) -> dict:
    """Evaluate one architecture.

    Returns a flat dict: fleet composition (variant IDs, counts), vehicle speed
    and range, the four MoPs (``passenger_volume``, ``peak_throughput``,
    ``wait_time``, ``availability``), their SAUs, ``mau``, and ``fleet_cost_usd``.

    Also reports the proposed attributes (``travel_time``, ``energy_per_pkm``, ``fleet_size``;
    ``bike_share`` is parked, not weighted), ``mau_os3a_extended`` and ``mau_os3a_full`` so Task 3
    can compare weightings (PLAN.md Q8, J).
    """
    mops = {
        "passenger_volume": daily_passenger_volume(fleet, scenario),
        "peak_throughput": peak_throughput(fleet, scenario),
        "wait_time": average_wait_min(fleet, scenario),
        "availability": fleet_availability(fleet, scenario),
    }
    capacity = fleet_capacity_per_h(fleet, scenario)
    bike_capacity = fleet_capacity_per_h(Fleet(bike=fleet.bike, n_bike=fleet.n_bike), scenario)
    proposed = {
        "travel_time": _travel_time_min(fleet, scenario),
        "bike_share": bike_capacity / capacity if capacity > 0 else 0.0,
        "energy_per_pkm": energy_per_pkm(fleet, scenario),
        "fleet_size": fleet_size(fleet),
    }
    row = {
        "road_variant": None if fleet.road is None else fleet.road["variant_id"],
        "n_road": fleet.n_road,
        "bike_variant": None if fleet.bike is None else fleet.bike["variant_id"],
        "n_bike": fleet.n_bike,
    }
    for part, vehicle in (("road", fleet.road), ("bike", fleet.bike)):
        for col in ("speed_kmh", "range_km", "availability", "cost_usd"):
            row[f"{part}_{col}"] = np.nan if vehicle is None else float(vehicle[col])
    row["fleet_capacity_per_h"] = capacity
    row["vehicle_availability"] = vehicle_availability(fleet, scenario)
    row |= mops | proposed
    for a, x in (mops | proposed).items():
        row[f"u_{a}"] = float(sau(a, x))
    row["mau"] = float(mau(**mops))
    row["mau_os3a_extended"] = float(weighted_mau(mops | proposed, load_weights("os3a_extended")))
    row["mau_os3a_full"] = float(weighted_mau(mops | proposed, load_weights("os3a_full")))
    row["fleet_cost_usd"] = fleet_cost_usd(fleet)
    row |= requirement_flags(pd.DataFrame([row]), scenario).iloc[0].to_dict()
    return row


def evaluate_many(fleets: list[Fleet], scenario: Scenario) -> pd.DataFrame:
    """``evaluate`` over a list of fleets, one row each."""
    return pd.DataFrame([evaluate(f, scenario) for f in fleets])


def representative_architectures(scenario: Scenario) -> dict[str, Fleet]:
    """The five architectures for the Task 2 deliverable table (Q17).

    Small C2 road fleet, large C6/C7 shuttles, bike-only, mixed road + bike,
    and a high-autonomy or long-range variant.

    Starting picks (Q17 still open): each fleet is sized to cover the 150 trips/h
    peak with some headroom, so the table compares architectures on cost and
    utility rather than on whether they meet demand.
    """
    v = lambda vid: get_variant(vid, scenario)  # noqa: E731
    return {
        "1 small cars (C2)": Fleet(road=v("C2-P2-G3-M2-A3"), n_road=12),
        "2 large shuttles (C6)": Fleet(road=v("C6-P4-G3-M3-A3"), n_road=4),
        "3 bike-only (B2)": Fleet(bike=v("B2-E1-G2-K2"), n_bike=150),
        "4 mixed cars + bikes": Fleet(road=v("C2-P2-G3-M2-A3"), n_road=8, bike=v("B2-E1-G2-K2"), n_bike=60),
        "5 A5 long-range (C4)": Fleet(road=v("C4-P5-G3-M2-A5"), n_road=6),
    }


def architecture_table(scenario: Scenario) -> pd.DataFrame:
    """The 5-architecture table for the slide (``evaluate_many`` on the representatives)."""
    archs = representative_architectures(scenario)
    table = evaluate_many(list(archs.values()), scenario)
    table.insert(0, "architecture", list(archs))
    return table


def reference_architecture(scenario: Scenario) -> Fleet:
    """Task 3 reference architecture (F): ``REFERENCE_VARIANT`` sized by load management.

    Departures needed f = P / (X * pax * load factor) at the peak; vehicles needed
    N = f * cycle / 60 / availability, rounded up.
    """
    vehicle = get_variant(REFERENCE_VARIANT, scenario)
    f = scenario.peak_demand_per_h / (REFERENCE_MAX_LOAD_RATIO * vehicle["pax"] * vehicle["load_factor"])
    n = math.ceil(f * cycle_time_min(vehicle, scenario) / 60.0 / vehicle["availability"])
    return Fleet(road=vehicle, n_road=n)


def anchor_architectures(scenario: Scenario) -> dict[str, Fleet]:
    """Anchors (Q16): today's shuttle and bus services, run through the same model.

    Each anchor (``data/anchors.csv``) is either a published headway or a known fleet size, from OS3A.
    The vehicle is the Appendix C chassis closest to the real one (C8, 30 seats, for buses; C6, 16 seats,
    for the 14-seat MIT shuttles) at its cheapest spec that reaches the speed cap and meets the
    Appendix B 0.75 availability benchmark for competing systems. A headway anchor's fleet is the fewest
    vehicles whose model headway, 60 / departures, is at most the published one.
    """
    fleets = {}
    for _, a in load("anchors").iterrows():
        vehicle = get_variant(a["road_variant"], scenario)
        if pd.notna(a["n_vehicles"]):
            n = int(a["n_vehicles"])
        else:
            n = math.ceil(cycle_time_min(vehicle, scenario) / (a["headway_min"] * vehicle["availability"]))
        fleets[a["name"]] = Fleet(road=vehicle, n_road=n)
    return fleets


def reference_and_anchor_table(scenario: Scenario) -> pd.DataFrame:
    """The reference architecture and the anchors, scored like the Task 2 table.

    Adds ``role`` ("reference" or "anchor"), the model's headway at the Kendall hub and, for anchors,
    the published headway it was sized to.
    """
    fleets = {"Reference: C4 small shuttles": reference_architecture(scenario)} | anchor_architectures(scenario)
    table = evaluate_many(list(fleets.values()), scenario)
    table.insert(0, "architecture", list(fleets))
    table.insert(1, "role", ["reference"] + ["anchor"] * (len(fleets) - 1))
    table["model_headway_min"] = [
        60.0 / sum(n * v["availability"] * 60.0 / cycle_time_min(v, scenario) for v, n in f.members())
        for f in fleets.values()
    ]
    table["published_headway_min"] = [np.nan] + list(load("anchors")["headway_min"].astype(float))
    return table


def hand_calc_check(scenario: Scenario) -> pd.DataFrame:
    """Model outputs for the one road and one bike variant worked by hand in the spreadsheet."""
    rows = []
    for vid in HAND_CALC_VARIANTS:
        vehicle = get_variant(vid, scenario)
        rows.append(vehicle.to_dict() | {
            "cycle_min": cycle_time_min(vehicle, scenario),
            "capacity_per_vehicle_h": vehicle_capacity_per_h(vehicle, scenario),
        })
    return pd.DataFrame(rows)


def _travel_time_min(fleet: Fleet, scenario: Scenario) -> float:
    """In-vehicle time [min] of the average Kendall trip (team decision; was the longest link).

    Each part's time is its trip length / speed (1.75 km road, 1.6 km bike), weighted by the
    share of trips it carries (its capacity). An empty fleet gets the SAU's zero-utility time.
    """
    parts = [(_trip_km(v, scenario) / v["speed_kmh"] * 60.0, fleet_capacity_per_h(Fleet(**_part(v, n)), scenario))
             for v, n in fleet.members()]
    total = sum(c for _, c in parts)
    if total == 0:
        return 20.0
    return sum(t * c for t, c in parts) / total


def _part(vehicle: pd.Series, n: int) -> dict:
    return {"road": vehicle, "n_road": n} if vehicle["kind"] == "road" else {"bike": vehicle, "n_bike": n}
