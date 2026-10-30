"""Task 2: fleet / transportation system performance model.

Fleet throughput, average wait time, availability, and fleet cost for a given
fleet composition and operating scenario. Takes vehicle rows from
``os4.vehicle`` (see ``VARIANT_COLUMNS``). Open modeling choices are tagged
with their question number in ``docs/PLAN.md``.
"""

from dataclasses import dataclass

import pandas as pd

from os4.scenario import Scenario


@dataclass(frozen=True)
class Fleet:
    """One architecture's fleet: at most one road variant and one bike variant (Q10)."""

    road: pd.Series | None = None
    n_road: int = 0
    bike: pd.Series | None = None
    n_bike: int = 0

    def members(self) -> list[tuple[pd.Series, int]]:
        """(vehicle row, count) pairs for the non-empty parts of the fleet."""
        raise NotImplementedError


# --- Per-vehicle operations -----------------------------------------------

def cycle_time_min(vehicle: pd.Series, scenario: Scenario) -> float:
    """Minutes per trip: (trip + deadhead distance) / speed + dwell."""
    raise NotImplementedError


def vehicle_capacity_per_h(vehicle: pd.Series, scenario: Scenario) -> float:
    """Passenger trips/h one vehicle can serve: (60 / cycle) * pax * load factor."""
    raise NotImplementedError


def effective_fleet(n: int, availability: float) -> float:
    """Vehicles in service on average (charging vehicles carry no one)."""
    raise NotImplementedError


# --- Fleet MoPs -----------------------------------------------------------

def fleet_capacity_per_h(fleet: Fleet, scenario: Scenario) -> float:
    """Total trips/h the fleet can serve: sum of effective vehicles x per-vehicle capacity."""
    raise NotImplementedError


def peak_throughput(fleet: Fleet, scenario: Scenario) -> float:
    """Peak-throughput MoP [trips/h]: capacity, or min(capacity, peak demand) (Q11)."""
    raise NotImplementedError


def daily_passenger_volume(fleet: Fleet, scenario: Scenario) -> float:
    """Passenger-volume MoP [trips/day]: sum over demand bins of min(demand, capacity) x bin width."""
    raise NotImplementedError


def road_wait_min(fleet: Fleet, scenario: Scenario) -> float:
    """Road-vehicle wait at the design node: headway / 2 plus an overload penalty (Q12)."""
    raise NotImplementedError


def bike_self_delivery_min(fleet: Fleet, scenario: Scenario) -> float:
    """Time for the nearest idle bike to ride itself to the passenger (Q12)."""
    raise NotImplementedError


def average_wait_min(fleet: Fleet, scenario: Scenario) -> float:
    """Wait-time MoP [min] at the design node, combining road and bike service.

    Must return a finite (capped) value for an empty or overloaded fleet so the
    robustness sweep never sees inf/NaN.
    """
    raise NotImplementedError


def fleet_availability(fleet: Fleet, scenario: Scenario) -> float:
    """Availability MoP: capacity-weighted average of vehicle availability (Q14)."""
    raise NotImplementedError


def fleet_cost_usd(fleet: Fleet) -> float:
    """Vehicle cost x count, summed over vehicle types (Q15: capital cost only?)."""
    raise NotImplementedError
