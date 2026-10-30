"""Loaders for the assignment input tables in ``data/`` (Appendices A, C, D)."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load(name: str) -> pd.DataFrame:
    """Load ``data/<name>.csv`` as a DataFrame."""
    return pd.read_csv(DATA_DIR / f"{name}.csv")


def load_all() -> dict[str, pd.DataFrame]:
    """Load every CSV in ``data/``, keyed by file stem."""
    return {p.stem: pd.read_csv(p) for p in sorted(DATA_DIR.glob("*.csv"))}
