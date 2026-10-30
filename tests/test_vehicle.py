import numpy as np
import pytest

from os4.scenario import primary_scenario
from os4.vehicle import VARIANT_COLUMNS, all_variants, bike_variants, road_variants

pytestmark = pytest.mark.xfail(raises=NotImplementedError, reason="not implemented yet")


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


@pytest.mark.skip(reason="fill in once the hand-calc spreadsheet exists")
def test_hand_calc_variants():
    ...
