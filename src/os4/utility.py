"""Task 1: single- and multi-attribute utility functions (Appendix A).

SAUs are piecewise-linear over the ``sau_*.csv`` points and clamp outside the
table range. The MAU is additive: ``U = sum_i k_i * u_i(x_i)`` with the weights
in ``mau_weights.csv`` (must sum to 1).
"""

from collections.abc import Mapping

import numpy as np
import pandas as pd

from os4.data import load

ATTRIBUTES = ("passenger_volume", "peak_throughput", "wait_time", "availability")


def sau_table(attribute: str) -> pd.DataFrame:
    """Return the Appendix A points for ``attribute`` as columns ``x``, ``utility``.

    Reads ``data/sau_<attribute>.csv`` and renames its first column to ``x``.
    """
    raise NotImplementedError


def sau(attribute: str, x: float | np.ndarray) -> float | np.ndarray:
    """Single-attribute utility of ``x`` for ``attribute``, in [0, 1].

    Linear interpolation between table points, clamped at the ends. Must handle
    the decreasing wait-time curve (``np.interp`` needs increasing ``xp``).
    Vectorized: accepts scalars or arrays.
    """
    raise NotImplementedError


def load_weights() -> dict[str, float]:
    """Return the MAU weights from ``mau_weights.csv``, keyed by attribute."""
    raise NotImplementedError


def mau(
    passenger_volume: float | np.ndarray,
    peak_throughput: float | np.ndarray,
    wait_time: float | np.ndarray,
    availability: float | np.ndarray,
    weights: Mapping[str, float] | None = None,
) -> float | np.ndarray:
    """Additive multi-attribute utility. ``weights`` defaults to ``load_weights()``.

    Vectorized so the tradespace can call it on whole arrays of architectures.
    Should raise ``ValueError`` if the weights don't sum to 1.
    """
    raise NotImplementedError


def evaluate_cases(weights: Mapping[str, float] | None = None) -> pd.DataFrame:
    """Score the cases in ``mau_test_cases.csv``.

    Returns one row per case with the raw attributes, each ``u_<attribute>``,
    and ``mau``. Expected (default weights): A 0.613, B 0.639, C 0.651.
    """
    raise NotImplementedError


def weight_sensitivity(
    delta: float = 0.1,
    weights: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Sweep each weight by +/- ``delta`` (renormalizing the others) and re-rank the cases.

    Returns one row per (attribute, perturbation) with each case's MAU and the
    resulting ranking, so the slide can show where the A/B/C order flips (Q8).
    """
    raise NotImplementedError
