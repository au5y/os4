import pytest

from os4.scenario import primary_scenario
from os4.speed_sensitivity import POSTED_LIMIT_KMH, bike_comparison, road_comparison, variations


def test_variations_change_one_speed_each():
    base = primary_scenario()
    v = {k: s for k, (_, s) in variations(base).items()}
    assert v["baseline"] == base
    assert v["bike_formula"].bike_assisted_speed_kmh is None
    assert v["bike_formula"].speed_limit_kmh == base.speed_limit_kmh
    assert v["road_posted"].speed_limit_kmh == pytest.approx(32.19, abs=0.01)
    assert v["road_posted"].bike_assisted_speed_kmh == base.bike_assisted_speed_kmh


def test_formula_speed_makes_bikes_slower_and_more_available():
    # Appendix B up-time = range / speed: same range at a lower speed means more up-time.
    b = bike_comparison(primary_scenario())
    assert (b["speed_new"] < b["speed_base"]).all()
    assert (b["availability_new"] > b["availability_base"]).all()
    assert (b["range_km"] > 0).all()


def test_posted_limit_caps_road_speed_at_20_mph():
    r = road_comparison(primary_scenario()).set_index("chassis")
    fastest = r["fastest (km/h)"].str.split(" → ").str[1].astype(float)
    assert fastest.max() == pytest.approx(POSTED_LIMIT_KMH, abs=0.05)
    assert fastest["C8"] < POSTED_LIMIT_KMH  # heavy buses stay motor-limited


def test_no_ceiling_variations_switch_off_both_ceilings():
    v = {k: s for k, (_, s) in variations(primary_scenario()).items()}
    for key in ("no_ceiling", "road_posted_no_ceiling"):
        assert v[key].max_bike_trips_per_day is None and v[key].max_car_trips_per_day is None
    assert v["road_posted_no_ceiling"].speed_limit_kmh == v["road_posted"].speed_limit_kmh
    assert v["no_ceiling"].speed_limit_kmh == v["baseline"].speed_limit_kmh
