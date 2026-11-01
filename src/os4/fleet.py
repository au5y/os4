"""Task 2: fleet / transportation system performance model.

Fleet throughput, average wait time, availability, and fleet cost for a given
fleet composition and operating scenario. Takes vehicle rows from
``os4.vehicle`` (see ``VARIANT_COLUMNS``). Open modeling choices are tagged
with their question number in ``docs/PLAN.md``.
"""

from dataclasses import dataclass

import numpy as np
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
        return [(v, n) for v, n in ((self.road, self.n_road), (self.bike, self.n_bike)) if v is not None and n > 0]


# --- Per-vehicle operations -----------------------------------------------

def cycle_time_min(vehicle: pd.Series, scenario: Scenario) -> float:
    """Minutes per trip: (trip + deadhead distance) / speed + dwell."""
    km = _trip_km(vehicle, scenario) * (1.0 + scenario.deadhead_fraction)
    return 60.0 * km / vehicle["speed_kmh"] + scenario.dwell_s / 60.0


def vehicle_capacity_per_h(vehicle: pd.Series, scenario: Scenario) -> float:
    """Passenger trips/h one vehicle can serve: (60 / cycle) * pax * load factor."""
    return 60.0 / cycle_time_min(vehicle, scenario) * vehicle["pax"] * scenario.load_factor


def effective_fleet(n: int, availability: float) -> float:
    """Vehicles in service on average (charging vehicles carry no one)."""
    return n * availability


# --- Fleet MoPs -----------------------------------------------------------

def fleet_capacity_per_h(fleet: Fleet, scenario: Scenario) -> float:
    """Total trips/h the fleet can serve: sum of effective vehicles x per-vehicle capacity."""
    return sum(_part_capacity(v, n, scenario) for v, n in fleet.members())


def peak_throughput(fleet: Fleet, scenario: Scenario) -> float:
    """Peak-throughput MoP [trips/h]: capacity, or min(capacity, peak demand) (Q11)."""
    capacity = fleet_capacity_per_h(fleet, scenario)
    if scenario.throughput_measure == "served":
        return min(capacity, scenario.peak_demand_per_h)
    return capacity


def daily_passenger_volume(fleet: Fleet, scenario: Scenario) -> float:
    """Passenger-volume MoP [trips/day]: sum over demand bins of min(demand, capacity) x bin width."""
    capacity = fleet_capacity_per_h(fleet, scenario)
    demand = scenario.demand["trips_per_hour"].to_numpy(dtype=float)
    return float(np.minimum(demand, capacity).sum() * scenario.demand_bin_h)


def road_wait_min(fleet: Fleet, scenario: Scenario) -> float:
    """Road-vehicle wait at the design node: headway / 2 plus an overload penalty (Q12)."""
    return _wait_min(_road_part(fleet), scenario)


def bike_self_delivery_min(fleet: Fleet, scenario: Scenario) -> float:
    """Time for the nearest idle bike to ride itself to the passenger (Q12).

    Default: bikes return to the Kendall hub after each trip (their L4 empty
    ride), so a waiting rider gets the next returning bike and the same
    headway/queue model applies as for road vehicles.
    """
    return _wait_min(_bike_part(fleet), scenario)


def average_wait_min(fleet: Fleet, scenario: Scenario) -> float:
    """Wait-time MoP [min] at the design node, combining road and bike service.

    Must return a finite (capped) value for an empty or overloaded fleet so the
    robustness sweep never sees inf/NaN.
    """
    return _wait_min(fleet, scenario)


def fleet_availability(fleet: Fleet, scenario: Scenario) -> float:
    """Availability MoP: capacity-weighted average of vehicle availability (Q14)."""
    parts = [(v["availability"], _part_capacity(v, n, scenario)) for v, n in fleet.members()]
    total = sum(c for _, c in parts)
    if total == 0:
        return 0.0
    return sum(a * c for a, c in parts) / total


def fleet_cost_usd(fleet: Fleet) -> float:
    """Vehicle cost x count, summed over vehicle types (Q15: capital cost only)."""
    return float(sum(v["cost_usd"] * n for v, n in fleet.members()))


# --- Helpers ---------------------------------------------------------------

def _trip_km(vehicle: pd.Series, scenario: Scenario) -> float:
    if vehicle["kind"] == "bike" and scenario.bike_trip_km is not None:
        return scenario.bike_trip_km
    return scenario.avg_trip_km


def _part_capacity(vehicle: pd.Series, n: int, scenario: Scenario) -> float:
    return effective_fleet(n, vehicle["availability"]) * vehicle_capacity_per_h(vehicle, scenario)


def _road_part(fleet: Fleet) -> Fleet:
    return Fleet(road=fleet.road, n_road=fleet.n_road)


def _bike_part(fleet: Fleet) -> Fleet:
    return Fleet(bike=fleet.bike, n_bike=fleet.n_bike)


def _wait_min(fleet: Fleet, scenario: Scenario) -> float:
    """Demand-weighted mean wait at the design node over the day's demand bins (Q12 default).

    In each bin, vehicles leave the hub ``departures`` times per hour, so a rider
    who arrives at random waits headway / 2 = 30 / departures minutes. As demand
    approaches capacity (utilization rho -> 1) riders queue, so the wait is
    scaled by 1 / (1 - rho), the M/M/1 queueing factor. Bins at or over capacity,
    and an empty fleet, get ``scenario.max_wait_min``.
    """
    departures = sum(
        effective_fleet(n, v["availability"]) * 60.0 / cycle_time_min(v, scenario) for v, n in fleet.members()
    )
    if departures <= 0:
        return scenario.max_wait_min
    capacity = fleet_capacity_per_h(fleet, scenario)
    demand = scenario.demand["trips_per_hour"].to_numpy(dtype=float)
    rho = demand / capacity
    with np.errstate(divide="ignore"):
        wait = np.where(rho < 1.0, (30.0 / departures) / (1.0 - rho), scenario.max_wait_min)
    wait = np.minimum(wait, scenario.max_wait_min)
    return float((wait * demand).sum() / demand.sum())
