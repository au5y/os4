import numpy as np
import pandas as pd
import pytest

from os4.fleet import Fleet
from os4.model import evaluate
from os4.scenario import primary_scenario
from os4.tradespace import (
    KNEE_PLATEAU,
    N_BIKE,
    N_ROAD,
    enumerate_architectures,
    front_comparison,
    knee_window,
    pareto_front,
    prune_variants,
    tradespace,
    utopia_point,
)
from os4.vehicle import all_variants, get_variant

COMPARED = ["fleet_capacity_per_h", "passenger_volume", "peak_throughput", "wait_time", "availability",
            "vehicle_availability", "travel_time", "bike_share", "trips_per_vehicle_day",
            "road_trips_per_vehicle_day", "bike_trips_per_vehicle_day", "car_trips_per_vehicle_day",
            "fleet_cost_usd",
            "mau", "mau_os3a_reweight"]


@pytest.fixture(scope="module")
def scenario():
    return primary_scenario()


# A small grid keeps the tests quick; the report uses the full Q14 grid.
SMALL_ROAD, SMALL_BIKE = range(0, 61, 5), range(0, 301, 25)


@pytest.fixture(scope="module")
def space(scenario):
    return tradespace(scenario, SMALL_ROAD, SMALL_BIKE)


def test_vectorized_matches_model_evaluate(scenario, space):
    rows = space.sample(60, random_state=0)
    for _, r in rows.iterrows():
        fleet = Fleet(road=get_variant(r.road_variant, scenario) if r.n_road else None, n_road=int(r.n_road),
                      bike=get_variant(r.bike_variant, scenario) if r.n_bike else None, n_bike=int(r.n_bike))
        expected = evaluate(fleet, scenario)
        for col in COMPARED:
            assert r[col] == pytest.approx(expected[col], rel=1e-9, abs=1e-9), col


def test_small_grid_matches_enumerate(scenario):
    variants = prune_variants(all_variants(scenario))
    subset = pd.concat([variants[variants.kind == "road"].head(2), variants[variants.kind == "bike"].head(2)])
    assert len(tradespace(scenario, [0, 5, 10], [0, 25], subset, screen=False)) == len(
        enumerate_architectures(scenario, [0, 5, 10], [0, 25], subset))


def test_pruning_keeps_only_non_dominated(scenario):
    variants = all_variants(scenario)
    kept = prune_variants(variants)
    assert 0 < len(kept) < len(variants)
    # A4/A5 only add cost and weight in this scenario, so every surviving road variant is A3.
    assert set(kept.loc[kept.kind == "road", "autonomy"]) == {"A3"}


def test_pareto_front_is_non_dominated(space):
    front = pareto_front(space)
    assert front["fleet_cost_usd"].is_monotonic_increasing
    assert front["mau"].is_monotonic_increasing
    # No architecture is at least as cheap and strictly better than a front point.
    for _, p in front.sample(min(20, len(front)), random_state=0).iterrows():
        better = (space["fleet_cost_usd"] <= p["fleet_cost_usd"]) & (space["mau"] > p["mau"] + 1e-12)
        assert not better.any()


def test_utopia_point(space):
    cost, util = utopia_point(space)
    assert cost == space["fleet_cost_usd"].min()
    assert util == space["mau"].max()
    assert np.isfinite(space.select_dtypes("number").to_numpy()).all()


def test_screening_drops_exactly_the_threshold_failures(scenario, space):
    full = tradespace(scenario, SMALL_ROAD, SMALL_BIKE, screen=False)
    failing = ((full["fleet_capacity_per_h"] < scenario.min_peak_throughput)
               | (full["fleet_capacity_per_h"] < scenario.min_offpeak_throughput)
               | (full["passenger_volume"] < scenario.min_daily_volume)
               | (full["bike_trips_per_vehicle_day"] > scenario.max_bike_trips_per_day)
               | (full["car_trips_per_vehicle_day"] > scenario.max_car_trips_per_day))
    assert space.attrs["screened_out"] == failing.sum()
    assert space.attrs["threshold_failures"]["peak_throughput"] == (full["fleet_capacity_per_h"] < 150).sum()
    assert len(space) == (~failing).sum()
    assert space["meets_thresholds"].all() and space["meets_bike_ceiling"].all() and space["meets_car_ceiling"].all()
    assert space.attrs["threshold_failures"]["car_ceiling"] == (~full["meets_car_ceiling"]).sum() > 0
    assert space.attrs["threshold_failures"]["bike_ceiling"] == (~full["meets_bike_ceiling"]).sum() > 0
    # Screening happens before scoring, so the survivors' scores are unchanged.
    kept = full[~failing].reset_index(drop=True)
    flags = ["meets_thresholds", "meets_bike_ceiling", "meets_car_ceiling"]
    pd.testing.assert_frame_equal(kept.drop(columns=flags), space.reset_index(drop=True).drop(columns=flags),
                                  check_dtype=False)


def test_peak_throughput_is_served_demand(scenario, space):
    assert scenario.throughput_measure == "served"
    assert (space["peak_throughput"] <= scenario.peak_demand_per_h + 1e-9).all()


def test_travel_time_is_average_kendall_trip(scenario):
    # A capped road fleet covers the 1.75 km Kendall trip at 21 km/h: 5.0 min.
    row = evaluate(Fleet(road=get_variant("C2-P2-G3-M2-A3", scenario), n_road=12), scenario)
    assert row["travel_time"] == pytest.approx(60 * 1.75 / 21)


def test_front_comparison_flags_dominated_points(space):
    front = pareto_front(space)
    on_front = front.iloc[[len(front) // 2]].assign(architecture="on front")
    worse = on_front.assign(architecture="worse", mau=on_front["mau"] - 0.01,
                            fleet_cost_usd=on_front["fleet_cost_usd"] + 1)
    result = front_comparison(space, pd.concat([on_front, worse]))
    assert list(result["dominated"]) == [False, True]


def test_knee_window_spans_cheapest_point_to_plateau(space):
    (x0, x1), (y0, y1) = knee_window(space)
    front = pareto_front(space)
    assert x0 < space["fleet_cost_usd"].min() and y1 > front["mau"].max()
    plateau = front[front["mau"] >= front["mau"].max() - KNEE_PLATEAU].iloc[0]
    assert x1 > plateau["fleet_cost_usd"] and y0 < plateau["mau"]


def test_fleet_grids_widen_with_size():
    assert N_ROAD[:16] == tuple(range(16))
    assert N_BIKE[:11] == tuple(range(0, 51, 5))
    for grid in (N_ROAD, N_BIKE):
        steps = np.diff(grid)
        assert (np.diff(steps) >= 0).all()
    assert max(N_ROAD) == 200 and max(N_BIKE) == 300
