"""Loaders for the input tables in ``data/``: Appendices A-D, the Task 3 anchors and the team's proposed SAUs and weights."""

import pandas as pd

from os4.paths import DATA_DIR


def load(name: str) -> pd.DataFrame:
    """Load ``data/<name>.csv`` as a DataFrame."""
    return pd.read_csv(DATA_DIR / f"{name}.csv")


def load_all() -> dict[str, pd.DataFrame]:
    """Load every CSV in ``data/``, keyed by file stem."""
    return {p.stem: pd.read_csv(p) for p in sorted(DATA_DIR.glob("*.csv"))}
