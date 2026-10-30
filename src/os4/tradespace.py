"""Tasks 3-4: enumerate the design vector, score architectures, plot tradespace.

TODO: enumerate architectures, compute utility vs. cost, find the Pareto
frontier and utopia point, and plot to ``outputs/``.
"""

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from os4.fleet import Fleet
from os4.scenario import Scenario


def prune_variants(variants: pd.DataFrame) -> pd.DataFrame:
    """Drop vehicle variants dominated on every vehicle-level metric at equal or higher cost.

    E.g. a bigger motor with no speed gain once the speed cap binds.
    """
    raise NotImplementedError


def enumerate_architectures(
    scenario: Scenario,
    n_road: Iterable[int],
    n_bike: Iterable[int],
    variants: pd.DataFrame | None = None,
) -> list[Fleet]:
    """Cross (pruned) road and bike variants with the fleet-size grids (Q10)."""
    raise NotImplementedError


def evaluate_tradespace(fleets: list[Fleet], scenario: Scenario) -> pd.DataFrame:
    """MAU and cost for every architecture (wraps ``model.evaluate_many``)."""
    raise NotImplementedError


def pareto_front(df: pd.DataFrame, utility: str = "mau", cost: str = "fleet_cost_usd") -> pd.DataFrame:
    """Rows not dominated in (higher utility, lower cost), sorted by cost."""
    raise NotImplementedError


def utopia_point(df: pd.DataFrame, utility: str = "mau", cost: str = "fleet_cost_usd") -> tuple[float, float]:
    """(min cost, max utility) over the tradespace."""
    raise NotImplementedError


def plot_tradespace(df: pd.DataFrame, path: Path, highlight: pd.DataFrame | None = None) -> Path:
    """Scatter utility vs. cost with the Pareto front and utopia point; save to ``path``."""
    raise NotImplementedError
