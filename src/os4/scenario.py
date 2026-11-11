"""Operating scenarios: everything about *where and how* the fleet runs.

Kept separate from the design vector so Tasks 3-5 can re-run the same model
under a different scenario: ``weekday_scenario`` and ``red_line_scenario`` are Scenarios 1 and 2 of Tasks 4-5.
Values trace to the numbered questions (Q1-Q31) in ``docs/PLAN.md``.
"""

from dataclasses import dataclass, field, replace

import pandas as pd

from os4.data import load


@dataclass(frozen=True)
class Scenario:
    name: str
    # Q4: cap on road-vehicle *average* speed (achieved, not posted).
    speed_limit_kmh: float
    # Q2: node-to-node distances, keyed by (node_a, node_b).
    node_distances_km: dict[tuple[str, str], float]
    # Q3: average passenger trip length and empty-repositioning distance as a fraction of it.
    avg_trip_km: float
    deadhead_fraction: float
    # Q5: demand at the design node (columns: hour, trips_per_hour), one row per bin.
    demand: pd.DataFrame
    # Q6: fixed assisted e-bike speed; None means use the Appendix B formula.
    bike_assisted_speed_kmh: float | None = None
    bike_speed_limit_kmh: float | None = None
    # Q3: bikes follow bike routes, so their trip length can differ; None means avg_trip_km.
    bike_trip_km: float | None = None
    # Q7: road autonomy levels allowed in this scenario.
    allowed_autonomy: tuple[str, ...] = ("A3", "A4", "A5")
    design_node: str = "Kendall"
    # Q17 (decided): "served" = min(capacity, peak demand), the demand the fleet actually serves;
    # "capacity" (what the fleet could carry) is kept as the alternative.
    throughput_measure: str = "served"
    # Q18: wait reported for an empty or overloaded fleet (the wait SAU reaches 0 at 30 min).
    max_wait_min: float = 30.0
    # Table 1 requirements. Thresholds are hard: architectures that miss one are screened out of
    # the tradespace (early exit). "Desired" goals and the competing-system availability benchmark
    # are reported as pass/fail flags instead.
    min_daily_volume: float = 1500.0
    min_peak_throughput: float = 150.0
    min_offpeak_throughput: float = 50.0
    goal_wait_min: float = 5.0
    goal_travel_min: float = 7.0
    benchmark_availability: float = 0.75
    # Removable e-bike batteries (team proposal; a justified deviation from Appendix B). Each option is
    # spare packs per bike, pooled across the fleet (0.5 = one spare per two bikes); 0 = fixed battery
    # as in Appendix B. A swap takes ``bike_swap_h``; the pack then charges off the bike.
    bike_spare_options: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0)
    bike_swap_h: float = 5 / 60
    # Feasibility gate (team, PLAN.md Q22): at most this many riders per bike per day; None turns it off.
    # The model lets every bike cycle without idle time, so cheap bike fleets can claim 40-50 rides a day.
    # Real systems: Bluebikes about 2.5 [[28]](references.md#ref-28), [[29]](references.md#ref-29) and
    # Citi Bike 3.3 [[25]](references.md#ref-25) per bike per day (2024 annual averages; 3-5 is typical),
    # Citi Bike e-bikes about 15 (2018) [[27]](references.md#ref-27), the busiest observed case and our
    # ceiling.
    max_bike_trips_per_day: float | None = 15.0
    # Same gate for small on-demand cars (PLAN.md Q22): at most this many vehicle trips (rides) per car per
    # day, Waymo's observed rate: about 24, from 250,000 paid rides a week [[32]](references.md#ref-32)
    # on over 1,500 vehicles [[33]](references.md#ref-33), spring 2025.
    # "Cars" are road chassis of 1-6 seats (C1-C3, team decision); larger shuttles and buses are in line
    # with transit (MBTA about 300 riders per bus per day [[30]](references.md#ref-30)) and are not gated.
    max_car_trips_per_day: float | None = 25.0
    car_max_seats: int = 6
    # Riders per bike trip as a fraction of seats, by seat count (team fix, PLAN.md Q16). An on-demand bike
    # only moves with someone on it (its empty return is the deadhead), so a 1-seat bike carries 1 rider;
    # a 2-seat bike carries a second rider about one trip in three (2 riders every 3 trips: 4/3 riders,
    # 2/3 of its seats). Appendix B's 0.75 would give 0.75 riders on a 1-seat bike.
    bike_load_factors: tuple[tuple[int, float], ...] = ((1, 1.0), (2, 2 / 3))
    # Appendix B constants. ``load_factor`` applies to road vehicles; bikes use ``bike_load_factors``.
    dwell_s: float = 60.0
    load_factor: float = 0.75
    # Multiplier on every vehicle's battery range (e.g. 0.75 for winter cold); 1.0 is Appendix B as given.
    range_factor: float = 1.0
    notes: list[str] = field(default_factory=list)

    @property
    def demand_bin_h(self) -> float:
        """Width of each demand bin [h] (Appendix B uses 2-hour bins)."""
        hours = self.demand["hour"].to_numpy()
        return float(hours[1] - hours[0])

    @property
    def peak_demand_per_h(self) -> float:
        return float(self.demand["trips_per_hour"].max())


def primary_scenario() -> Scenario:
    """Standard weekday demand (Q1): on-demand last-mile service from Kendall, scored over
    Appendix B's full weekday and sized for its 8:00-14:00 peak.

    On-demand trips start at the Kendall hub and go to Lechmere or Central;
    vehicles return to the hub empty, because Appendix B only gives
    Kendall-origin demand.
    """
    return Scenario(
        name="Standard weekday demand",
        # Q4: 20 mph posted, but signals/congestion hold achieved speed near 13 mph.
        speed_limit_kmh=21.0,
        # Q2: OSRM driving distances, mean of both directions.
        node_distances_km={
            ("Lechmere", "Kendall"): 1.9,
            ("Kendall", "Central"): 1.6,
            ("Lechmere", "Central"): 3.3,
        },
        # Q3: mean of the two Kendall-origin links (1.9 and 1.6 km).
        avg_trip_km=1.75,
        # Q3: every trip returns to Kendall empty. 0.5 would mean half the
        # returns carry a passenger; run it as a sensitivity.
        deadhead_fraction=1.0,
        demand=load("demand_mit_kendall"),
        # Q6 (Decision, Austin, 2026-11-07): the Appendix B formula speed (700·P/W), as the assignment
        # gives it, even though it is unrealistic; the 18 km/h assist is a sensitivity.
        bike_assisted_speed_kmh=None,
        # Class 1/2 e-bike assist cap, 20 mph.
        bike_speed_limit_kmh=32.0,
        # Q3: both Kendall bike links are 1.6 km.
        bike_trip_km=1.6,
        # Q7: inside the boundary, A3 is the minimum; A4/A5 stay in the design vector.
        allowed_autonomy=("A3", "A4", "A5"),
    )


# PLAN.md Q30: Tasks 4-5 run e-bikes at a fixed 18 km/h assist (the Task 3 sensitivity case, Q6).
ASSISTED_BIKE_KMH = 18.0
# PLAN.md Q29: the Red Line scenario's own assumptions (team estimates, not given data).
RED_LINE_TRIP_KM = 5.0          # Kendall to Park St / South Station
RED_LINE_PEAK_FACTOR = 1.5      # peak demand x1.5 as Red Line riders move to us
RED_LINE_PEAK_HOURS = (8, 10, 12)  # the 8:00-14:00 peak bins
RED_LINE_ROAD_CAP_KMH = 25.0    # arterial roads into Boston


def weekday_scenario() -> Scenario:
    """Scenario 1 for Tasks 4-5 (PLAN.md Q30): the standard weekday with e-bikes at the 18 km/h assist,
    the scenario the Task 3 slides use (the "E-bike assist at 18 km/h" sensitivity case)."""
    return replace(primary_scenario(), name="Scenario 1: standard weekday (18 km/h e-bikes)",
                   bike_assisted_speed_kmh=ASSISTED_BIKE_KMH)


def red_line_scenario() -> Scenario:
    """Scenario 2, the Task 4 scenario (PLAN.md Q29): the Red Line is down, so riders at Kendall need a road
    link to Park St / South Station, outside the system boundary.

    Changes from Scenario 1 (everything else, including the design vector, thresholds, ceilings and
    weights, stays the same): 5 km road and bike trips; peak demand x1.5 (8:00-14:00); road cap 25 km/h;
    A4/A5 only (Table 1: L4 or higher outside the boundary); Table 1's outside-boundary goals, a 20-min
    wait and a 20-min ride.
    """
    base = weekday_scenario()
    demand = base.demand.copy()
    demand.loc[demand["hour"].isin(RED_LINE_PEAK_HOURS), "trips_per_hour"] *= RED_LINE_PEAK_FACTOR
    return replace(
        base, name="Scenario 2: Red Line disruption (Kendall to Park St / South Station)",
        demand=demand, avg_trip_km=RED_LINE_TRIP_KM, bike_trip_km=RED_LINE_TRIP_KM,
        speed_limit_kmh=RED_LINE_ROAD_CAP_KMH, allowed_autonomy=("A4", "A5"),
        goal_wait_min=20.0, goal_travel_min=20.0,
    )


def winter_scenario() -> Scenario:
    """Robustness check for the Task 5 base fleet: Scenario 1 in winter (road cap 18 km/h, bike assist
    12 km/h, battery range x0.75), as in the Model Lab's winter preset."""
    return replace(weekday_scenario(), name="Winter weekday", speed_limit_kmh=18.0, bike_assisted_speed_kmh=12.0,
                   range_factor=0.75)


task4_scenario = red_line_scenario
