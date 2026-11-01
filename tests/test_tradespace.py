import numpy as np
import pandas as pd
import pytest

from os4.fleet import Fleet
from os4.model import evaluate
from os4.scenario import primary_scenario
from os4.tradespace import (
    enumerate_architectures,
    pareto_front,
    prune_variants,
    tradespace,
    utopia_point,
)
from os4.vehicle import all_variants, get_variant

COMPARED = ["fleet_capacity_per_h", "passenger_volume", "peak_throughput", "wait_time", "availability",
            "travel_time", "bike_share", "fleet_cost_usd", "mau", "mau_os3a_extended"]


@pytest.fixture(scope="module")
def scenario():
    return primary_scenario()


@pytest.fixture(scope="module")
def space(scenario):
    return tradespace(scenario)


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
    assert len(tradespace(scenario, [0, 5, 10], [0, 25], subset)) == len(
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
