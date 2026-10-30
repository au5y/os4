"""Operating scenarios: everything about *where and how* the fleet runs.

Kept separate from the design vector so Tasks 3-4 can re-run the same model
under a different scenario (e.g. the Task 4 Red Line shutdown or winter case, Q20).
Values marked TBD depend on team decisions D1-D6 in ``docs/PLAN.md``.
"""

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class Scenario:
    name: str
    # D3 / Q3: posted speed limit that caps road-vehicle average speed.
    speed_limit_kmh: float
    # D1 / Q1: node-to-node distances, keyed by (node_a, node_b).
    node_distances_km: dict[tuple[str, str], float]
    # Q13: average passenger trip length and empty-repositioning fraction.
    avg_trip_km: float
    deadhead_fraction: float
    # D4 / Q4: hourly demand at the design node (columns: hour, trips_per_hour).
    demand: pd.DataFrame
    # D5 / Q5: fixed assisted e-bike speed; None means use the Appendix B formula.
    bike_assisted_speed_kmh: float | None = None
    bike_speed_limit_kmh: float | None = None
    # D6 / Q6: road autonomy levels allowed in this scenario.
    allowed_autonomy: tuple[str, ...] = ("A3", "A4", "A5")
    design_node: str = "Kendall"
    # Appendix B constants.
    dwell_s: float = 60.0
    load_factor: float = 0.75
    notes: list[str] = field(default_factory=list)


def primary_scenario() -> Scenario:
    """Weekday a.m.-peak last-mile service from Kendall (D2 / Q2).

    Demand comes from ``demand_mit_kendall.csv``; the other fields need the
    team's answers to Q1, Q3, Q5, Q6 and Q13.
    """
    raise NotImplementedError


def task4_scenario() -> Scenario:
    """Alternate scenario for Task 4 (Red Line shutdown or winter, Q20)."""
    raise NotImplementedError
