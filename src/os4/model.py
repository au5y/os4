"""Task 2 glue: (fleet, scenario) -> MoPs, MAU, and cost.

This is the single entry point Tasks 3-6 call; swap the ``Scenario`` to
re-evaluate the same architectures under different conditions.
"""

import pandas as pd

from os4.fleet import Fleet
from os4.scenario import Scenario


def evaluate(fleet: Fleet, scenario: Scenario) -> dict:
    """Evaluate one architecture.

    Returns a flat dict: fleet composition (variant IDs, counts), vehicle speed
    and range, the four MoPs (``passenger_volume``, ``peak_throughput``,
    ``wait_time``, ``availability``), their SAUs, ``mau``, and ``fleet_cost_usd``.
    """
    raise NotImplementedError


def evaluate_many(fleets: list[Fleet], scenario: Scenario) -> pd.DataFrame:
    """``evaluate`` over a list of fleets, one row each."""
    raise NotImplementedError


def representative_architectures(scenario: Scenario) -> dict[str, Fleet]:
    """The five architectures for the Task 2 deliverable table (Q17).

    Small C2 road fleet, large C6/C7 shuttles, bike-only, mixed road + bike,
    and a high-autonomy or long-range variant.
    """
    raise NotImplementedError


def architecture_table(scenario: Scenario) -> pd.DataFrame:
    """The 5-architecture table for the slide (``evaluate_many`` on the representatives)."""
    raise NotImplementedError


def hand_calc_check(scenario: Scenario) -> pd.DataFrame:
    """Model outputs for the one road and one bike variant worked by hand in the spreadsheet."""
    raise NotImplementedError
