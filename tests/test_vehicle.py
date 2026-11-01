import numpy as np
import pytest

from os4.scenario import primary_scenario
from os4.vehicle import VARIANT_COLUMNS, all_variants, bike_variants, get_variant, road_variants

def test_variant_counts():
    scenario = primary_scenario()
    assert len(bike_variants(scenario)) == 30
    if set(scenario.allowed_autonomy) == {"A3", "A4", "A5"}:
        assert len(road_variants(scenario)) == 1548


def test_variant_columns():
    assert list(all_variants(primary_scenario()).columns) == VARIANT_COLUMNS


def test_variants_are_finite_and_sane():
    df = all_variants(primary_scenario())
    numeric = df.select_dtypes("number")
    assert np.isfinite(numeric.to_numpy()).all()
    assert (numeric >= 0).all().all()
    assert df["availability"].between(0, 1, inclusive="neither").all()


def test_speed_never_exceeds_limit():
    scenario = primary_scenario()
    assert (road_variants(scenario)["speed_kmh"] <= scenario.speed_limit_kmh + 1e-9).all()


# Worked by hand from Appendix B with the primary scenario (21 km/h road cap, 18 km/h bikes).
# C2-P2-G3-M2-A3: weight 1600+220+5+80+30+4*100 = 2335 kg; cost 17000+11000+7000+9800+15000;
# Wh/km 135 + 0.1*(2335-1600) + 1.5 = 210; range 100000/210; formula speed 700*100/2335 = 30.0 -> 21;
# charge 100/60 h; up 476.19/21 h; down charge + 0.25 h.
# B2-E1-G2-K2: weight 17+5+1.2+4+100 = 127.2 kg; cost 3000+600+500+400; Wh/km 25 + 0.1*(127.2-17);
# range 500/36.02; speed 18 (fixed assist); charge 0.5/0.6 h.
HAND_CALC = {
    "C2-P2-G3-M2-A3": dict(weight_kg=2335, cost_usd=59800, wh_per_km=210.0, range_km=476.1905,
                           speed_kmh=21.0, charge_time_h=1.6667, uptime_h=22.6757, availability=0.92206),
    "B2-E1-G2-K2": dict(weight_kg=127.2, cost_usd=4500, wh_per_km=36.02, range_km=13.8812,
                        speed_kmh=18.0, charge_time_h=0.8333, uptime_h=0.77118, availability=0.41585),
}


@pytest.mark.parametrize("variant_id", HAND_CALC)
def test_hand_calc_variants(variant_id):
    row = get_variant(variant_id, primary_scenario())
    for col, expected in HAND_CALC[variant_id].items():
        assert row[col] == pytest.approx(expected, rel=1e-4), col


def test_battery_limit_is_inclusive():
    # C1 is 1350 kg, so the 450 kg P4 battery sits exactly at the 1/3 limit and is allowed.
    ids = set(road_variants(primary_scenario())["variant_id"])
    assert "C1-P4-G1-M1-A3" in ids
    assert "C1-P5-G1-M1-A3" not in ids
