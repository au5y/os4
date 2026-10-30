"""Write the model to ``outputs/os4_model.xlsx`` for the ZIP submission."""

from pathlib import Path

from os4.scenario import Scenario

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"


def export_model(scenario: Scenario, path: Path = OUTPUT_DIR / "os4_model.xlsx") -> Path:
    """Write tabs: inputs, SAU/MAU tables and test cases, vehicle variants,
    the 5 architectures, and the hand-calc check. Returns the written path.
    """
    raise NotImplementedError
