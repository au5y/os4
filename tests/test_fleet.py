import numpy as np
import pytest

from os4.fleet import Fleet, average_wait_min, fleet_capacity_per_h, fleet_cost_usd
from os4.scenario import primary_scenario
from os4.vehicle import road_variants

pytestmark = pytest.mark.xfail(raises=NotImplementedError, reason="not implemented yet")


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
