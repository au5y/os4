"""Tasks 4-5: the Red Line scenario (PLAN.md Q29), the 18 km/h e-bike setting (Q30) and the concept (Q31).

The numbers are the ones on the Task 4 and Task 5 slides.
"""

import pytest

from os4 import task4, task5
from os4 import tradespace as ts
from os4.scenario import red_line_scenario, weekday_scenario


@pytest.fixture(scope="module")
def results():
    ts.SHOW_PROGRESS = False
    return task4.run()


def test_red_line_scenario_changes_only_its_own_inputs():
    s1, s2 = weekday_scenario(), red_line_scenario()
    assert s1.bike_assisted_speed_kmh == s2.bike_assisted_speed_kmh == 18.0
    assert s2.peak_demand_per_h == 225 and s2.demand["trips_per_hour"].sum() * s2.demand_bin_h == 2240
    assert (s2.avg_trip_km, s2.bike_trip_km, s2.speed_limit_kmh) == (5.0, 5.0, 25.0)
    assert s2.allowed_autonomy == ("A4", "A5") and (s2.goal_wait_min, s2.goal_travel_min) == (20.0, 20.0)
    for field in ("min_daily_volume", "min_peak_throughput", "max_bike_trips_per_day", "max_car_trips_per_day",
                  "load_factor", "dwell_s"):
        assert getattr(s1, field) == getattr(s2, field)


def test_both_tradespaces_match_the_slides(results):
    s1, s2 = results["s1"], results["s2"]
    assert (s1["feasible"], len(s1["front"])) == (1_052_974, 403)
    assert (s2["feasible"], len(s2["front"])) == (1_004_532, 347)
    assert s2["front_types"] == {"road-only": 3, "bike-only": 0, "mixed": 344}
    k1, k2 = s1["knee"], s2["knee"]
    assert (k1["road_variant"], k1["n_road"], k1["bike_variant"], k1["n_bike"]) == (task4.BUS, 2, task4.BIKE, 20)
    assert k1["fleet_cost_usd"] == 259_200
    assert (k2["road_variant"], k2["n_road"], k2["bike_variant"], k2["n_bike"]) == ("C8-P1-G3-M4-A4", 6, task4.BIKE, 30)
    assert k2["fleet_cost_usd"] == 795_600 and k2["mau"] == pytest.approx(0.944, abs=5e-4)
    assert s2["cheapest"]["fleet_cost_usd"] == 462_400


def test_tradespace_and_evaluate_agree_on_the_scenario_2_knee(results):
    k2 = results["s2"]["knee"]
    row = task4.score(k2["road_variant"], int(k2["n_road"]), k2["bike_variant"], int(k2["n_bike"]),
                      results["s2"]["scenario"])
    for col in ("mau", "wait_time", "availability", "peak_throughput", "fleet_cost_usd"):
        assert row[col] == pytest.approx(k2[col], rel=1e-9)


def test_no_task3_pick_survives_the_closure(results):
    for _, p in results["picks"].iterrows():
        if p["architecture"].startswith("Scenario 2"):
            assert p["s2"]["meets_thresholds"] and p["s2"]["on_front"]
        else:
            assert p["s1"]["meets_thresholds"] and not p["s2"]["meets_thresholds"]
    assert task4.a4_twin("C8-P1-G3-M4-A3", results["s2"]["scenario"]) == "C8-P1-G3-M4-A4"
    assert task4.a4_twin("C8-P1-G3-M4-A3", results["s1"]["scenario"]) == "C8-P1-G3-M4-A3"


def test_concept_base_fleet_and_surge_kit(results):
    c = task5.concept(results)
    assert c["base1"]["fleet_cost_usd"] == 299_200 and c["base1"]["meets_thresholds"]
    assert c["base1"]["mau"] == pytest.approx(0.942, abs=5e-4)
    assert c["surge_usd"] == 496_400
    assert c["winter"]["meets_thresholds"] and c["winter"]["mau"] == pytest.approx(0.919, abs=5e-4)
    assert not c["base_on_front"]  # dominated only by its A3 twin, the Task 3 knee
    assert c["base_a3"]["mau"] > c["base1"]["mau"]


def test_reports_are_written(results, tmp_path):
    paths = task4.write_task4(tmp_path, results) + task5.write_task5(tmp_path, results)
    for path in paths:
        assert path.exists()
    assert "6 × C8-P1-G3-M4-A4 + 30 × B1-E1-G2-K1" in (tmp_path / "task4_red_line.md").read_text(encoding="utf-8")
    assert "$496,400" in (tmp_path / "task5_recommendation.md").read_text(encoding="utf-8")
