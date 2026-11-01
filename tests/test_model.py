import numpy as np

from os4.fleet import Fleet
from os4.model import architecture_table, evaluate, hand_calc_check
from os4.scenario import primary_scenario


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
