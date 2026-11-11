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
    """One architecture's fleet: at most one road variant and one bike variant (Q14)."""

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
    """Passenger trips/h one vehicle can serve: (60 / cycle) * pax * its load factor (bikes by seats, PLAN.md Q16)."""
    return 60.0 / cycle_time_min(vehicle, scenario) * vehicle["pax"] * vehicle["load_factor"]


def effective_fleet(n: int, availability: float) -> float:
    """Vehicles in service on average (charging vehicles carry no one)."""
    return n * availability


# --- Fleet MoPs -----------------------------------------------------------

def fleet_capacity_per_h(fleet: Fleet, scenario: Scenario) -> float:
    """Total trips/h the fleet can serve: sum of effective vehicles x per-vehicle capacity."""
    return sum(_part_capacity(v, n, scenario) for v, n in fleet.members())


def peak_throughput(fleet: Fleet, scenario: Scenario) -> float:
    """Peak-throughput MoP [trips/h]: capacity, or min(capacity, peak demand) (Q17)."""
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
    """Road-vehicle wait at the design node: headway / 2 plus an overload penalty (Q18)."""
    return _wait_min(_road_part(fleet), scenario)


def bike_self_delivery_min(fleet: Fleet, scenario: Scenario) -> float:
    """Wait for an e-bike [min] (PLAN.md Q18).

    Bikes return to the Kendall hub after each trip (their L4 empty
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


def vehicle_availability(fleet: Fleet, scenario: Scenario) -> float:
    """Capacity-weighted average of the Appendix B vehicle availabilities (the pre-Q19 availability MoP)."""
    parts = [(v["availability"], _part_capacity(v, n, scenario)) for v, n in fleet.members()]
    total = sum(c for _, c in parts)
    if total == 0:
        return 0.0
    return sum(a * c for a, c in parts) / total


def fleet_availability(fleet: Fleet, scenario: Scenario) -> float:
    """Availability MoP as *service* availability (Q19): can a rider get a vehicle when they ask?

    Each vehicle is in service (not charging) with probability equal to its
    Appendix B availability a, independently. In each demand bin the fleet
    serves its demand if the in-service vehicles' capacity covers it, so the
    service availability is P(capacity in service >= demand), averaged over the
    day weighted by demand. That capacity has mean sum(N a c) and variance
    sum(N a (1 - a) c^2), with c = one vehicle's capacity (trips/h); the
    probability uses the normal approximation, which is accurate for the
    fleet sizes modeled. Spare vehicles push it toward 1 even when each
    vehicle's own availability is low.
    """
    parts = [(v["availability"], n, vehicle_capacity_per_h(v, scenario)) for v, n in fleet.members()]
    mean = sum(n * a * c for a, n, c in parts)
    var = sum(n * a * (1 - a) * c**2 for a, n, c in parts)
    demand = scenario.demand["trips_per_hour"].to_numpy(dtype=float)
    return float(service_probability(mean, var, demand) @ demand / demand.sum())


def service_probability(mean, var, demand):
    """P(capacity in service >= demand) under the normal approximation (vectorized over fleets and bins)."""
    mean, var = np.asarray(mean, dtype=float), np.asarray(var, dtype=float)
    sd = np.sqrt(var)[..., None]
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (mean[..., None] - demand) / sd
    return np.where(sd > 0, normal_cdf(z), (mean[..., None] >= demand).astype(float))


def normal_cdf(z):
    """Standard normal CDF, vectorized (Abramowitz & Stegun 7.1.26 erf, error < 1.5e-7)."""
    x = np.abs(np.asarray(z, dtype=float)) / np.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * x)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))
    erf = 1.0 - poly * np.exp(-x * x)
    return 0.5 * (1.0 + np.where(np.asarray(z) >= 0, erf, -erf))


def trips_per_vehicle_day(fleet: Fleet, scenario: Scenario) -> dict[str, float]:
    """Riders served per vehicle per day, overall and for the road and bike parts (0 for an absent part), and
    vehicle trips (rides) per car per day for a road part of at most ``scenario.car_max_seats`` seats.

    A realism check (PLAN.md Q22), not a utility attribute: the model lets every vehicle cycle without
    idle time, so these are upper bounds to compare with real systems (e.g. rides per Bluebike per
    day). Each part serves the day's volume in proportion to its capacity.
    """
    capacity = fleet_capacity_per_h(fleet, scenario)
    volume = daily_passenger_volume(fleet, scenario)
    out = {"trips_per_vehicle_day": volume / fleet_size(fleet) if fleet_size(fleet) else 0.0}
    for part, vehicle, n in (("road", fleet.road, fleet.n_road), ("bike", fleet.bike, fleet.n_bike)):
        if vehicle is None or not n or not capacity:
            out[f"{part}_trips_per_vehicle_day"] = 0.0
            continue
        out[f"{part}_trips_per_vehicle_day"] = volume * _part_capacity(vehicle, n, scenario) / capacity / n
    road = fleet.road
    is_car = road is not None and fleet.n_road and road["pax"] <= scenario.car_max_seats
    out["car_trips_per_vehicle_day"] = (out["road_trips_per_vehicle_day"] / (road["pax"] * road["load_factor"])
                                        if is_car else 0.0)
    return out


def fleet_size(fleet: Fleet) -> int:
    """Vehicles in the fleet, road and bike."""
    return int(sum(n for _, n in fleet.members()))


def fleet_cost_usd(fleet: Fleet) -> float:
    """Vehicle cost x count, summed over vehicle types (Q21: capital cost only)."""
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
    """Demand-weighted mean wait at the design node over the day's demand bins (Q18 default).

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
