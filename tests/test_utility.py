import numpy as np
import pytest

from os4.data import load
from os4.utility import ATTRIBUTES, evaluate_cases, mau, sau

# Stubs raise NotImplementedError -> xfail; a wrong answer still fails.
pytestmark = pytest.mark.xfail(raises=NotImplementedError, reason="not implemented yet")


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
