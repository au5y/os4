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


def test_mixed_availability_between_parts(scenario):
    car, bike = get_variant("C2-P2-G3-M2-A3", scenario), get_variant("B2-E1-G2-K2", scenario)
    a = fleet_availability(Fleet(road=car, n_road=8, bike=bike, n_bike=60), scenario)
    assert bike["availability"] < a < car["availability"]


@pytest.mark.parametrize("n", [0, 1, 5, 25, 100, 300])
def test_robustness_sweep(scenario, n):
    """Every feasible variant at each fleet size gives finite, non-negative MoPs."""
    for _, v in all_variants(scenario).iterrows():
        fleet = Fleet(road=v, n_road=n) if v["kind"] == "road" else Fleet(bike=v, n_bike=n)
        values = [fleet_capacity_per_h(fleet, scenario), daily_passenger_volume(fleet, scenario),
                  average_wait_min(fleet, scenario), fleet_availability(fleet, scenario), fleet_cost_usd(fleet)]
        assert np.isfinite(values).all() and min(values) >= 0, v["variant_id"]
        assert average_wait_min(fleet, scenario) <= scenario.max_wait_min
