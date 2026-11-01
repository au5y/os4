import numpy as np

from os4.data import load
from os4.fleet import Fleet
from os4.model import (
    architecture_table,
    evaluate,
    hand_calc_check,
    reference_and_anchor_table,
    reference_architecture,
)
from os4.scenario import primary_scenario
from os4.vehicle import all_variants


def test_architecture_table_is_complete_and_finite():
    table = architecture_table(primary_scenario())
    assert len(table) == 5
    numeric = table.select_dtypes("number")
    # Per-part vehicle specs are NaN when the fleet has no road (or no bike) part.
    numeric = numeric[[c for c in numeric if not c.startswith(("road_", "bike_"))]]
    assert np.isfinite(numeric.to_numpy()).all()
    assert table["mau"].between(0, 1).all()
    # Every starting architecture covers the 150 trips/h peak (they were sized to).
    assert (table["fleet_capacity_per_h"] >= 150).all()


def test_empty_fleet_scores_low_but_finite():
    row = evaluate(Fleet(), primary_scenario())
    assert row["fleet_capacity_per_h"] == 0
    assert row["fleet_cost_usd"] == 0
    assert 0 <= row["mau"] < 0.1


def test_hand_calc_check_rows():
    assert list(hand_calc_check(primary_scenario())["variant_id"]) == ["C2-P2-G3-M2-A3", "B2-E1-G2-K2"]


def test_reference_is_sized_by_load_management():
    # f >= 150 / (0.90 * 8 pax * 0.75) = 27.8 departures/h; N = 27.8 * 11 min / 60 / 0.904 = 5.6 -> 6.
    scenario = primary_scenario()
    fleet = reference_architecture(scenario)
    assert fleet.road["variant_id"] == "C4-P2-G3-M2-A3"
    assert fleet.n_road == 6
    assert evaluate(fleet, scenario)["meets_thresholds"]


def test_anchor_vehicles_are_cheapest_of_their_chassis_at_speed_cap_and_benchmark():
    scenario = primary_scenario()
    v = all_variants(scenario)
    for variant in load("anchors")["road_variant"]:
        chassis = variant.split("-")[0]
        ok = v[v["variant_id"].str.match(rf"{chassis}-.*-A3$") & (v["speed_kmh"] >= scenario.speed_limit_kmh)
               & (v["availability"] >= scenario.benchmark_availability)]
        assert ok.sort_values("cost_usd").iloc[0]["variant_id"] == variant


def test_anchors_match_their_published_headway_or_fleet_size():
    scenario = primary_scenario()
    table = reference_and_anchor_table(scenario)
    anchors = table[table["role"] == "anchor"].reset_index(drop=True)
    data = load("anchors")
    assert len(anchors) == len(data)
    sized = data["n_vehicles"].notna()
    assert (anchors.loc[sized, "n_road"] == data.loc[sized, "n_vehicles"]).all()
    headway = anchors[~sized]
    assert (headway["model_headway_min"] <= headway["published_headway_min"]).all()
    # One vehicle fewer would miss the published headway.
    fewer = headway["model_headway_min"] * headway["n_road"] / (headway["n_road"] - 1)
    assert (fewer > headway["published_headway_min"]).all()
