import numpy as np
import pytest

from os4.data import load
from os4.utility import (
    ATTRIBUTES,
    PROPOSED_ATTRIBUTES,
    WEIGHT_SETS,
    compare_weight_sets,
    evaluate_cases,
    load_weights,
    mau,
    sau,
    sau_inverse,
    weight_sensitivity,
    weighted_mau,
)


@pytest.mark.parametrize("attribute", ATTRIBUTES)
def test_sau_reproduces_table_points(attribute):
    table = load(f"sau_{attribute}")
    x, u = table.iloc[:, 0].to_numpy(), table["utility"].to_numpy()
    np.testing.assert_allclose(sau(attribute, x), u)


@pytest.mark.parametrize("attribute", ATTRIBUTES)
def test_sau_clamps_to_unit_interval(attribute):
    u = sau(attribute, np.array([-1e6, 1e6]))
    assert np.all((u >= 0) & (u <= 1))


def test_mau_best_and_worst():
    assert mau(1e6, 1e6, 0, 1.0) == pytest.approx(1.0)
    assert mau(0, 0, 1e6, 0.0) == pytest.approx(0.0)


def test_cases_match_hand_calc():
    result = evaluate_cases().set_index("case")["mau"]
    assert result.to_dict() == pytest.approx({"A": 0.613, "B": 0.639, "C": 0.651}, abs=5e-4)


def test_requirements_point_beats_cases():
    assert mau(1500, 150, 5, 0.75) > evaluate_cases()["mau"].max()


@pytest.mark.parametrize("attribute", ATTRIBUTES)
def test_sau_is_monotone(attribute):
    u = sau(attribute, np.linspace(-10, 2500, 1001))
    diffs = np.diff(u)
    assert np.all(diffs <= 1e-12) if attribute == "wait_time" else np.all(diffs >= -1e-12)


def test_sau_scalar_in_scalar_out():
    assert isinstance(sau("wait_time", 8), float)


def test_case_saus_match_hand_calc():
    # Hand calcs from docs/PLAN.md (Task 1 approach)
    cases = evaluate_cases().set_index("case")
    expected = {
        "A": (0.40, 0.35, 0.83, 0.70),
        "B": (1.00, 0.50, 0.61, 0.60),
        "C": (0.30, 0.35, 0.91, 0.80),
    }
    for case, us in expected.items():
        got = [cases.loc[case, f"u_{a}"] for a in ATTRIBUTES]
        np.testing.assert_allclose(got, us)


def test_weights_must_sum_to_one():
    bad = dict.fromkeys(ATTRIBUTES, 0.3)
    with pytest.raises(ValueError):
        mau(1000, 100, 10, 0.5, weights=bad)


def test_weight_sensitivity_keeps_weights_normalized():
    table = weight_sensitivity()
    assert len(table) == 2 * len(ATTRIBUTES)
    assert table["ranking"].str.len().eq(3).all()


@pytest.mark.parametrize("attribute", PROPOSED_ATTRIBUTES)
def test_proposed_saus_reproduce_points_and_clamp(attribute):
    table = load(f"sau_{attribute}")
    np.testing.assert_allclose(sau(attribute, table.iloc[:, 0].to_numpy()), table["utility"].to_numpy())
    u = sau(attribute, np.array([-1e6, 1e6]))
    assert np.all((u >= 0) & (u <= 1))


@pytest.mark.parametrize("weight_set", WEIGHT_SETS)
def test_weight_sets_sum_to_one(weight_set):
    assert sum(load_weights(weight_set).values()) == pytest.approx(1.0)


def test_os3a_reweight_hand_calc():
    # PLAN.md Q10: volume 0.10 / peak 0.25 / wait 0.35 / availability 0.30
    result = compare_weight_sets().set_index("case")
    assert result["mau_os3a_reweight"].to_dict() == pytest.approx({"A": 0.628, "B": 0.6185, "C": 0.676})


def test_weighted_mau_matches_mau_on_appendix_a():
    values = {"passenger_volume": 1000, "peak_throughput": 75, "wait_time": 8, "availability": 0.7}
    assert weighted_mau(values, load_weights()) == pytest.approx(mau(**values))


def test_reweight_mau_best_worst_and_missing_values():
    weights = load_weights("os3a_reweight")
    best = {"passenger_volume": 1e6, "peak_throughput": 1e6, "wait_time": 0, "availability": 1.0}
    worst = {"passenger_volume": 0, "peak_throughput": 0, "wait_time": 1e6, "availability": 0.0}
    assert weighted_mau(best, weights) == pytest.approx(1.0)
    assert weighted_mau(worst, weights) == pytest.approx(0.0)
    with pytest.raises(ValueError):
        weighted_mau({"passenger_volume": 1000}, weights)


@pytest.mark.parametrize("attribute", ATTRIBUTES + PROPOSED_ATTRIBUTES)
def test_sau_inverse_round_trips(attribute):
    table = load(f"sau_{attribute}")
    x = np.linspace(table.iloc[:, 0].min(), table.iloc[:, 0].max(), 201)
    np.testing.assert_allclose(sau_inverse(attribute, sau(attribute, x)), x, atol=1e-9)
    u = np.linspace(0, 1, 101)
    np.testing.assert_allclose(sau(attribute, sau_inverse(attribute, u)), u, atol=1e-12)


def test_sau_inverse_recovers_case_inputs():
    # Yonis's hand-calculated utilities map back to the Task 1 case levels.
    assert sau_inverse("passenger_volume", 0.30) == pytest.approx(750)
    assert sau_inverse("peak_throughput", 0.35) == pytest.approx(75)
    assert sau_inverse("wait_time", 0.83) == pytest.approx(8)
    assert sau_inverse("wait_time", 0.61) == pytest.approx(12)
    assert sau_inverse("availability", 0.70) == pytest.approx(0.7)


def test_proposed_attributes_are_unweighted():
    # Travel time and bike share keep their SAUs but are in no weight set (PLAN.md Q11, Q12).
    for name in WEIGHT_SETS:
        assert set(load_weights(name)) == set(ATTRIBUTES)
    assert sau("travel_time", 7) == pytest.approx(0.8)
    assert sau("bike_share", 0.11) == pytest.approx(0.3)
