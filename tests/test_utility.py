import numpy as np
import pytest

from os4.data import load
from os4.utility import ATTRIBUTES, evaluate_cases, mau, sau, weight_sensitivity


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
