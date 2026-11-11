"""Task 1: single- and multi-attribute utility functions (Appendix A).

SAUs are piecewise-linear over the ``sau_*.csv`` points and clamp outside the
table range. The MAU is additive: ``U = sum_i k_i * u_i(x_i)`` with the weights
in ``mau_weights.csv`` (must sum to 1).

Besides the Appendix A weights, ``mau_weights_proposed.csv`` holds the team's
proposed weight set traced to our OS3A MOEs (PLAN.md Q9/Q10): ``os3a_reweight``
re-weights the four Appendix A attributes. The ``PROPOSED_ATTRIBUTES`` have SAUs (team
assumptions) but no weights: they are reported, not scored (PLAN.md Q11, Q12).
"""

from collections.abc import Mapping

import numpy as np
import pandas as pd

from os4.data import load

ATTRIBUTES = ("passenger_volume", "peak_throughput", "wait_time", "availability")
# In-boundary travel time (Table 1: 7 min; OS3A MOE 1) and e-bike share of served trips (OS3A MOE 2).
# Neither is in a weight set: travel time stays a pass/fail goal (``meets_travel_goal``), with its SAU kept
# for a scenario with longer trips (PLAN.md Q11); bike share rewards a type of fleet, not an outcome (PLAN.md Q12).
PROPOSED_ATTRIBUTES = ("travel_time", "bike_share")
WEIGHT_SETS = ("appendix_a", "os3a_reweight")


def sau_table(attribute: str) -> pd.DataFrame:
    """Return the SAU points for ``attribute`` as columns ``x``, ``utility``.

    Reads ``data/sau_<attribute>.csv`` and renames its first column to ``x``.
    """
    known = ATTRIBUTES + PROPOSED_ATTRIBUTES
    if attribute not in known:
        raise ValueError(f"unknown attribute {attribute!r}; expected one of {known}")
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


def sau_inverse(attribute: str, u: float | np.ndarray) -> float | np.ndarray:
    """Attribute level ``x`` that gives utility ``u`` (the inverse of ``sau``).

    Every SAU is strictly monotone (rising, or falling for wait time), so each
    utility in [0, 1] maps back to exactly one x on the same straight-line
    segments; ``u`` outside [0, 1] is clamped. Useful for reading a target off a
    curve, e.g. the wait time that still scores 0.9.
    """
    table = sau_table(attribute).sort_values("utility")
    utilities = table["utility"].to_numpy()
    if np.any(np.diff(utilities) <= 0):
        raise ValueError(f"SAU for {attribute!r} is not strictly monotone, so it has no unique inverse")
    x = np.interp(u, utilities, table["x"].to_numpy())
    return float(x) if np.ndim(x) == 0 else x


def load_weights(weight_set: str = "appendix_a") -> dict[str, float]:
    """Return a set of MAU weights keyed by attribute (see ``WEIGHT_SETS``).

    ``appendix_a`` reads ``mau_weights.csv``; the others read their column of
    ``mau_weights_proposed.csv``, skipping attributes the set leaves blank.
    """
    if weight_set == "appendix_a":
        table = load("mau_weights")
        return dict(zip(table["attribute"], table["weight"].astype(float)))
    if weight_set not in WEIGHT_SETS:
        raise ValueError(f"unknown weight set {weight_set!r}; expected one of {WEIGHT_SETS}")
    table = load("mau_weights_proposed").dropna(subset=[weight_set])
    return dict(zip(table["attribute"], table[weight_set].astype(float)))


def _check_weights(weights: Mapping[str, float], attributes: tuple[str, ...] = ATTRIBUTES) -> None:
    if set(weights) != set(attributes):
        raise ValueError(f"weights must have keys {attributes}, got {tuple(weights)}")
    total = sum(weights.values())
    if not np.isclose(total, 1.0):
        raise ValueError(f"weights must sum to 1, got {total}")


def weighted_mau(values: Mapping[str, float | np.ndarray], weights: Mapping[str, float]) -> float | np.ndarray:
    """Additive MAU over whichever attributes ``weights`` names, e.g. the ``os3a_reweight`` set.

    ``values`` maps each weighted attribute to its raw level (extra keys are ignored).
    """
    _check_weights(weights, tuple(weights))
    missing = set(weights) - set(values)
    if missing:
        raise ValueError(f"missing values for {sorted(missing)}")
    return sum(w * sau(a, values[a]) for a, w in weights.items())


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


def compare_weight_sets() -> pd.DataFrame:
    """MAU and rank of each case under every weight set that covers only the Appendix A attributes."""
    rows = evaluate_cases()[["case"]].copy()
    for name in WEIGHT_SETS:
        weights = load_weights(name)
        if set(weights) != set(ATTRIBUTES):
            continue
        mau_col = evaluate_cases(weights)["mau"]
        rows[f"mau_{name}"] = mau_col.to_numpy()
        rows[f"rank_{name}"] = mau_col.rank(ascending=False).astype(int).to_numpy()
    return rows


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
    resulting ranking, so the slide can show where the A/B/C order flips (Q10).
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
