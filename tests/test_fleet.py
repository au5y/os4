import math

import numpy as np
import pytest

from os4.fleet import (
    Fleet,
    average_wait_min,
    cycle_time_min,
    daily_passenger_volume,
    fleet_availability,
    fleet_capacity_per_h,
    fleet_cost_usd,
    fleet_size,
    trips_per_vehicle_day,
    normal_cdf,
    vehicle_availability,
    vehicle_capacity_per_h,
)
from os4.scenario import primary_scenario
from os4.vehicle import all_variants, get_variant, road_variants

@pytest.fixture
def scenario():
    return primary_scenario()


@pytest.fixture
def road_vehicle(scenario):
    return road_variants(scenario).iloc[0]


def test_empty_fleet_is_handled(scenario):
    fleet = Fleet()
    assert fleet_capacity_per_h(fleet, scenario) == 0
    assert np.isfinite(average_wait_min(fleet, scenario))


def test_monotone_in_fleet_size(scenario, road_vehicle):
    sizes = [5, 10, 20, 40]
    fleets = [Fleet(road=road_vehicle, n_road=n) for n in sizes]
    capacity = [fleet_capacity_per_h(f, scenario) for f in fleets]
    wait = [average_wait_min(f, scenario) for f in fleets]
    assert capacity == sorted(capacity)
    assert wait == sorted(wait, reverse=True)


def test_cost_linear_in_fleet_size(road_vehicle):
    one = fleet_cost_usd(Fleet(road=road_vehicle, n_road=1))
    assert fleet_cost_usd(Fleet(road=road_vehicle, n_road=7)) == pytest.approx(7 * one)


def test_cycle_and_capacity_hand_calc(scenario):
    # C2-P2-G3-M2-A3: 1.75 km out + 1.75 km back at 21 km/h = 10 min, + 1 min dwell;
    # 60/11 trips/h x 4 pax x 0.75 load factor.
    car = get_variant("C2-P2-G3-M2-A3", scenario)
    assert cycle_time_min(car, scenario) == pytest.approx(11.0)
    assert vehicle_capacity_per_h(car, scenario) == pytest.approx(60 / 11 * 4 * 0.75)


def test_volume_capped_by_demand(scenario):
    car = get_variant("C2-P2-G3-M2-A3", scenario)
    total_demand = scenario.demand["trips_per_hour"].sum() * scenario.demand_bin_h
    assert daily_passenger_volume(Fleet(road=car, n_road=500), scenario) == pytest.approx(total_demand)


def test_vehicle_availability_between_parts(scenario):
    car, bike = get_variant("C2-P2-G3-M2-A3", scenario), get_variant("B2-E1-G2-K2", scenario)
    a = vehicle_availability(Fleet(road=car, n_road=8, bike=bike, n_bike=60), scenario)
    assert bike["availability"] < a < car["availability"]


def test_service_availability_hand_calc(scenario):
    # 12 C2 cars: each in service w.p. a = 0.92206 with c = 60/11 x 4 x 0.75 = 16.36 trips/h.
    # Capacity in service ~ Normal(12 a c, 12 a (1-a) c^2); P(>= demand) per bin, demand-weighted.
    car = get_variant("C2-P2-G3-M2-A3", scenario)
    a, c = car["availability"], vehicle_capacity_per_h(car, scenario)
    mean, sd = 12 * a * c, math.sqrt(12 * a * (1 - a)) * c
    demand = scenario.demand["trips_per_hour"].to_numpy(float)
    expected = sum(d * 0.5 * (1 + math.erf((mean - d) / (sd * math.sqrt(2)))) for d in demand) / demand.sum()
    assert fleet_availability(Fleet(road=car, n_road=12), scenario) == pytest.approx(expected, abs=1e-6)


def test_service_availability_rises_with_spares(scenario):
    # Bikes are only ~0.42 available each, but a pool of spares still serves almost every rider.
    bike = get_variant("B2-E1-G2-K2", scenario)
    values = [fleet_availability(Fleet(bike=bike, n_bike=n), scenario) for n in (60, 94, 120, 150, 200)]
    assert values == sorted(values)
    assert values[-1] > 0.99 > bike["availability"]
    assert fleet_availability(Fleet(), scenario) == 0


def test_normal_cdf_matches_erf():
    z = np.linspace(-8, 8, 801)
    exact = np.array([0.5 * (1 + math.erf(v / math.sqrt(2))) for v in z])
    np.testing.assert_allclose(normal_cdf(z), exact, atol=2e-7)


@pytest.mark.parametrize("n", [0, 1, 5, 25, 100, 300])
def test_robustness_sweep(scenario, n):
    """Every feasible variant at each fleet size gives finite, non-negative MoPs."""
    for _, v in all_variants(scenario).iterrows():
        fleet = Fleet(road=v, n_road=n) if v["kind"] == "road" else Fleet(bike=v, n_bike=n)
        values = [fleet_capacity_per_h(fleet, scenario), daily_passenger_volume(fleet, scenario),
                  average_wait_min(fleet, scenario), fleet_availability(fleet, scenario), fleet_cost_usd(fleet)]
        assert np.isfinite(values).all() and min(values) >= 0, v["variant_id"]
        assert average_wait_min(fleet, scenario) <= scenario.max_wait_min


def test_fleet_size_counts_every_vehicle(scenario):
    car, bike = get_variant("C2-P2-G3-M2-A3", scenario), get_variant("B2-E1-G2-K2", scenario)
    assert fleet_size(Fleet(road=car, n_road=8, bike=bike, n_bike=60)) == 68
    assert fleet_size(Fleet()) == 0


@pytest.mark.parametrize("variant, riders", [("B2-E1-G2-K2", 1.0), ("B3-E1-G2-K1", 4 / 3)])
def test_bike_riders_per_trip_by_seats(scenario, variant, riders):
    # PLAN.md Q16: a 1-seat bike always carries its one rider; a 2-seat bike carries 2 riders every 3 trips.
    bike = get_variant(variant, scenario)
    assert bike["pax"] * bike["load_factor"] == pytest.approx(riders)
    assert vehicle_capacity_per_h(bike, scenario) == pytest.approx(60 / cycle_time_min(bike, scenario) * riders)


def test_road_load_factor_stays_appendix_b(scenario):
    assert get_variant("C2-P2-G3-M2-A3", scenario)["load_factor"] == pytest.approx(0.75)


def test_trips_per_vehicle_day_splits_by_capacity(scenario):
    car, bike = get_variant("C2-P2-G3-M2-A3", scenario), get_variant("B2-E1-G2-K2", scenario)
    fleet = Fleet(road=car, n_road=8, bike=bike, n_bike=60)
    t = trips_per_vehicle_day(fleet, scenario)
    volume = daily_passenger_volume(fleet, scenario)
    assert t["trips_per_vehicle_day"] == pytest.approx(volume / 68)
    assert 8 * t["road_trips_per_vehicle_day"] + 60 * t["bike_trips_per_vehicle_day"] == pytest.approx(volume)
    assert trips_per_vehicle_day(Fleet(road=car, n_road=12), scenario)["bike_trips_per_vehicle_day"] == 0.0


def test_car_trips_count_rides_for_small_cars_only(scenario):
    car, shuttle = get_variant("C2-P2-G3-M2-A3", scenario), get_variant("C6-P4-G3-M3-A3", scenario)
    t = trips_per_vehicle_day(Fleet(road=car, n_road=12), scenario)
    # Riders per car / riders per ride (4 seats x 0.75): PLAN.md Q22.
    assert t["car_trips_per_vehicle_day"] == pytest.approx(t["road_trips_per_vehicle_day"] / 3)
    assert trips_per_vehicle_day(Fleet(road=shuttle, n_road=4), scenario)["car_trips_per_vehicle_day"] == 0.0
