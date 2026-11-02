"""Operating scenarios: everything about *where and how* the fleet runs.

Kept separate from the design vector so Tasks 3-4 can re-run the same model
under a different scenario (e.g. the Task 4 Red Line shutdown or winter case, Q20).
Values trace to the team decisions D1-D6 / Q1-Q14 in ``docs/PLAN.md``.
"""

from dataclasses import dataclass, field

import pandas as pd

from os4.data import load


@dataclass(frozen=True)
class Scenario:
    name: str
    # D3 / Q3: cap on road-vehicle *average* speed (achieved, not posted).
    speed_limit_kmh: float
    # D1 / Q1: node-to-node distances, keyed by (node_a, node_b).
    node_distances_km: dict[tuple[str, str], float]
    # Q13: average passenger trip length and empty-repositioning distance as a fraction of it.
    avg_trip_km: float
    deadhead_fraction: float
    # D4 / Q4: demand at the design node (columns: hour, trips_per_hour), one row per bin.
    demand: pd.DataFrame
    # D5 / Q5: fixed assisted e-bike speed; None means use the Appendix B formula.
    bike_assisted_speed_kmh: float | None = None
    bike_speed_limit_kmh: float | None = None
    # Q13: bikes follow bike routes, so their trip length can differ; None means avg_trip_km.
    bike_trip_km: float | None = None
    # D6 / Q6: road autonomy levels allowed in this scenario.
    allowed_autonomy: tuple[str, ...] = ("A3", "A4", "A5")
    design_node: str = "Kendall"
    # Q11 (decided): "served" = min(capacity, peak demand), the demand the fleet actually serves;
    # "capacity" (what the fleet could carry) is kept as the alternative.
    throughput_measure: str = "served"
    # Q12: wait reported for an empty or overloaded fleet (the wait SAU reaches 0 at 30 min).
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
    # Riders per bike trip as a fraction of seats, by seat count (team fix, PLAN.md K). An on-demand bike
    # only moves with someone on it (its empty return is the deadhead), so a 1-seat bike carries 1 rider;
    # a 2-seat bike carries a second rider about one trip in three (2 riders every 3 trips: 4/3 riders,
    # 2/3 of its seats). Appendix B's 0.75 would give 0.75 riders on a 1-seat bike.
    bike_load_factors: tuple[tuple[int, float], ...] = ((1, 1.0), (2, 2 / 3))
    # Appendix B constants. ``load_factor`` applies to road vehicles; bikes use ``bike_load_factors``.
    dwell_s: float = 60.0
    load_factor: float = 0.75
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
    """Weekday a.m.-peak last-mile service from Kendall (D2 / Q2).

    On-demand trips start at the Kendall hub and go to Lechmere or Central;
    vehicles return to the hub empty, because Appendix B only gives
    Kendall-origin demand.
    """
    return Scenario(
        name="primary: weekday on-demand last-mile from Kendall",
        # Q3: 20 mph posted, but signals/congestion hold achieved speed near 13 mph.
        speed_limit_kmh=21.0,
        # Q1: OSRM driving distances, mean of both directions.
        node_distances_km={
            ("Lechmere", "Kendall"): 1.9,
            ("Kendall", "Central"): 1.6,
            ("Lechmere", "Central"): 3.3,
        },
        # Q13: mean of the two Kendall-origin links (1.9 and 1.6 km).
        avg_trip_km=1.75,
        # Q13 (open): every trip returns to Kendall empty. 0.5 would mean half the
        # returns carry a passenger; run it as a sensitivity.
        deadhead_fraction=1.0,
        demand=load("demand_mit_kendall"),
        # Q5: fixed assisted speed, low end of 18-20 km/h (OS3A anchor: 15-18 km/h door to door).
        bike_assisted_speed_kmh=18.0,
        # Class 1/2 e-bike assist cap, 20 mph.
        bike_speed_limit_kmh=32.0,
        # Q13: both Kendall bike links are 1.6 km.
        bike_trip_km=1.6,
        # Q6: inside the boundary, A3 is the minimum; A4/A5 stay in the design vector.
        allowed_autonomy=("A3", "A4", "A5"),
        notes=[
            "Q11, Q12, Q13 deadhead and Q14 use the defaults in fleet.py until the team decides.",
        ],
    )


def task4_scenario() -> Scenario:
    """Alternate scenario for Task 4 (Red Line shutdown or winter, Q20)."""
    raise NotImplementedError
