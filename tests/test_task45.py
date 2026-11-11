"""Tasks 4-5: the Red Line scenario (PLAN.md Q29) and the recommended concept (Q31), under the model's inputs:
18 km/h e-bikes (Q6), removable batteries with spare packs (Q15) and the OS3A reweight as the MAU (Q10).
"""

import pytest

from os4 import task4, task5
from os4 import tradespace as ts
from os4.scenario import primary_scenario, red_line_scenario, weekday_scenario

BUS_A4, BIKE_S2 = "C8-P1-G3-M4-A4", "B1-E1-G2-K1-S1.5"


@pytest.fixture(scope="module")
def results():
    ts.SHOW_PROGRESS = False
    return task4.run()


def _fleet(row) -> tuple:
    return task4._ids(row)


def test_model_inputs_everywhere():
    for s in (primary_scenario(), weekday_scenario(), red_line_scenario()):
        assert s.bike_assisted_speed_kmh == 18.0
        assert min(s.bike_spare_options) > 0  # every e-bike has a removable battery with spares


def test_red_line_scenario_changes_only_its_own_inputs():
    s1, s2 = weekday_scenario(), red_line_scenario()
    assert s2.peak_demand_per_h == 225 and s2.demand["trips_per_hour"].sum() * s2.demand_bin_h == 2240
    assert (s2.avg_trip_km, s2.bike_trip_km, s2.speed_limit_kmh) == (5.0, 5.0, 25.0)
    assert s2.allowed_autonomy == ("A4", "A5") and (s2.goal_wait_min, s2.goal_travel_min) == (20.0, 20.0)
    for field in ("min_daily_volume", "min_peak_throughput", "max_bike_trips_per_day", "max_car_trips_per_day",
                  "load_factor", "dwell_s", "bike_assisted_speed_kmh", "bike_spare_options"):
        assert getattr(s1, field) == getattr(s2, field)


def test_both_tradespaces(results):
    s1, s2 = results["s1"], results["s2"]
    assert (s1["feasible"], len(s1["front"])) == (1_754_320, 460)
    assert (s2["feasible"], len(s2["front"])) == (1_852_174, 432)
    assert _fleet(s1["knee"]) == ("C7-P2-G3-M3-A3", 3, "B1-E1-G1-K1-S0.5", 5)
    assert s1["knee"]["fleet_cost_usd"] == 272_200 and s1["knee"]["mau"] == pytest.approx(0.941, abs=5e-4)
    assert _fleet(s2["knee"]) == (BUS_A4, 5, BIKE_S2, 35)
    assert s2["knee"]["fleet_cost_usd"] == 754_750 and s2["knee"]["mau"] == pytest.approx(0.941, abs=5e-4)
    assert s2["cheapest"]["fleet_cost_usd"] == 462_400


def test_tradespace_and_evaluate_agree_on_the_scenario_2_knee(results):
    k2 = results["s2"]["knee"]
    row = task4.score(*_fleet(k2), results["s2"]["scenario"])
    for col in ("mau", "mau_appendix_a", "wait_time", "availability", "peak_throughput", "fleet_cost_usd"):
        assert row[col] == pytest.approx(k2[col], rel=1e-9)


def test_no_task3_pick_survives_the_closure(results):
    for _, p in results["picks"].iterrows():
        if p["architecture"] == task4.S2_KNEE:
            assert p["s2"]["meets_thresholds"] and p["s2"]["on_front"]
        else:
            assert p["s1"]["meets_thresholds"] and not p["s2"]["meets_thresholds"]
    assert task4.a4_twin("C8-P1-G3-M4-A3", results["s2"]["scenario"]) == BUS_A4
    assert task4.a4_twin("C8-P1-G3-M4-A3", results["s1"]["scenario"]) == "C8-P1-G3-M4-A3"


def test_concept_base_fleet_and_surge_kit(results):
    c = task5.concept(results)
    b = c["base1"]
    assert _fleet(pd_row(b)) == (BUS_A4, 3, None, 0) and b["fleet_cost_usd"] == 346_800
    assert b["meets_thresholds"] and b["mau"] >= task4.KNEE_MAU
    assert (c["surge_road"], c["surge_bike"], c["surge_usd"]) == (2, 35, 407_950)
    assert c["winter"]["meets_thresholds"]


def pd_row(d: dict):
    import pandas as pd
    return pd.Series(d)


def test_reports_are_written(results, tmp_path):
    paths = task4.write_task4(tmp_path, results) + task5.write_task5(tmp_path, results)
    for path in paths:
        assert path.exists()
    assert f"5 × {BUS_A4} + 35 × {BIKE_S2}" in (tmp_path / "task4_red_line.md").read_text(encoding="utf-8")
    assert "$407,950" in (tmp_path / "task5_recommendation.md").read_text(encoding="utf-8")
