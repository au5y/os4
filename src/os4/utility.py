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
    if attribute not in ATTRIBUTES:
        raise ValueError(f"unknown attribute {attribute!r}; expected one of {ATTRIBUTES}")
    table = load(f"sau_{attribute}")
    return table.rename(columns={table.columns[0]: "x"})[["x", "utility"]]


def sau(attribute: str, x: float | np.ndarray) -> float | np.ndarray:
    """Single-attribute utility of ``x`` for ``attribute``, in [0, 1].

    Linear interpolation between table points, clamped at the ends. Must handle
    the decreasing wait-time curve (``np.interp`` needs increasing ``xp``).
    Vectorized: accepts scalars or arrays.
    """
    table = sau_table(attribute).sort_values("x")
    u = np.interp(x, table["x"].to_numpy(), table["utility"].to_numpy())
    return float(u) if np.ndim(u) == 0 else u


def load_weights() -> dict[str, float]:
    """Return the MAU weights from ``mau_weights.csv``, keyed by attribute."""
    table = load("mau_weights")
    return dict(zip(table["attribute"], table["weight"].astype(float)))


def _check_weights(weights: Mapping[str, float]) -> None:
    if set(weights) != set(ATTRIBUTES):
        raise ValueError(f"weights must have keys {ATTRIBUTES}, got {tuple(weights)}")
    total = sum(weights.values())
    if not np.isclose(total, 1.0):
        raise ValueError(f"weights must sum to 1, got {total}")


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
    weights = load_weights() if weights is None else weights
    _check_weights(weights)
    values = dict(zip(ATTRIBUTES, (passenger_volume, peak_throughput, wait_time, availability)))
    return sum(weights[a] * sau(a, values[a]) for a in ATTRIBUTES)


def evaluate_cases(weights: Mapping[str, float] | None = None) -> pd.DataFrame:
    """Score the cases in ``mau_test_cases.csv``.

    Returns one row per case with the raw attributes, each ``u_<attribute>``,
    and ``mau``. Expected (default weights): A 0.613, B 0.639, C 0.651.
    """
    cases = load("mau_test_cases")
    for a in ATTRIBUTES:
        cases[f"u_{a}"] = sau(a, cases[a].to_numpy())
    cases["mau"] = mau(*(cases[a].to_numpy() for a in ATTRIBUTES), weights=weights)
    return cases


def _perturb(weights: Mapping[str, float], attribute: str, delta: float) -> dict[str, float]:
    """Shift one weight by ``delta`` (clipped to [0, 1]) and rescale the rest to keep the sum at 1."""
    new = float(np.clip(weights[attribute] + delta, 0.0, 1.0))
    rest = 1.0 - weights[attribute]
    scale = (1.0 - new) / rest if rest > 0 else 0.0
    return {a: new if a == attribute else w * scale for a, w in weights.items()}


def weight_sensitivity(
    delta: float = 0.1,
    weights: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Sweep each weight by +/- ``delta`` (renormalizing the others) and re-rank the cases.

    Returns one row per (attribute, perturbation) with each case's MAU and the
    resulting ranking, so the slide can show where the A/B/C order flips (Q8).
    """
    weights = load_weights() if weights is None else weights
    _check_weights(weights)
    baseline = evaluate_cases(weights).set_index("case")["mau"]
    base_rank = "".join(baseline.sort_values(ascending=False).index)

    rows = []
    for a in ATTRIBUTES:
        for d in (-delta, +delta):
            perturbed = _perturb(weights, a, d)
            scores = evaluate_cases(perturbed).set_index("case")["mau"]
            ranking = "".join(scores.sort_values(ascending=False).index)
            rows.append(
                {
                    "attribute": a,
                    "delta": d,
                    "weight": perturbed[a],
                    **{f"mau_{c}": s for c, s in scores.items()},
                    "ranking": ranking,
                    "flipped": ranking != base_rank,
                }
            )
    return pd.DataFrame(rows)
