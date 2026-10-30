"""Task 2: vehicle model for road EVs and autonomous e-bikes (Appendix B).

Weight, cost, power consumption, range, speed, charge time, and availability
for a given component selection (Appendices C and D), including the
battery-to-chassis/frame weight constraints.

The equation functions are vectorized (scalars or arrays). The ``*_variants``
functions return one tidy row per feasible vehicle, which is the interface the
fleet layer consumes.
"""

import numpy as np
import pandas as pd

from os4.scenario import Scenario

PAX_WEIGHT_KG = 100.0
CHARGE_OVERHEAD_H = 0.25
SPEED_COEFF = 700.0
WEIGHT_WH_PER_KM_PER_KG = 0.1
BENCHMARK_AVAILABILITY = 0.75

# Battery weight may be at most this fraction of the chassis/frame weight.
ROAD_BATTERY_WEIGHT_LIMIT = 1 / 3
BIKE_BATTERY_WEIGHT_LIMIT = 1 / 2

# Columns every variant row carries; the fleet layer relies on these.
VARIANT_COLUMNS = [
    "kind",  # "road" or "bike"
    "variant_id",  # e.g. "C2-P3-G2-M1-A3" or "B3-E2-G1-K2"
    "chassis", "battery", "charger", "motor", "autonomy",
    "pax",
    "weight_kg",
    "cost_usd",
    "wh_per_km",
    "range_km",
    "speed_kmh",
    "speed_capped",
    "charge_time_h",
    "uptime_h",
    "downtime_h",
    "availability",
]


# --- Appendix B equations --------------------------------------------------

def total_weight_kg(chassis_kg, battery_kg, charger_kg, motor_kg, autonomy_kg, pax):
    """Chassis + battery + charger + motor + autonomy + 100 kg per passenger."""
    raise NotImplementedError


def total_cost_usd(chassis_usd, battery_usd, charger_usd, motor_usd, autonomy_usd):
    """Sum of component costs (bike frame cost already includes L4 autonomy)."""
    raise NotImplementedError


def charge_time_h(battery_kwh, charger_kw):
    """Battery capacity / charger power."""
    raise NotImplementedError


def power_consumption_wh_per_km(nominal_wh_per_km, total_kg, chassis_kg, autonomy_wh_per_km):
    """Nominal + 0.1 * (total weight - chassis weight) + autonomy add-on."""
    raise NotImplementedError


def range_km(battery_kwh, wh_per_km):
    """Battery capacity [Wh] / power consumption [Wh/km]."""
    raise NotImplementedError


def formula_speed_kmh(motor_kw, total_kg):
    """Uncapped Appendix B speed: 700 * motor power [kW] / total weight [kg]."""
    raise NotImplementedError


def road_speed_kmh(motor_kw, total_kg, speed_limit_kmh):
    """Formula speed capped at the posted speed limit."""
    raise NotImplementedError


def bike_speed_kmh(motor_kw, total_kg, scenario: Scenario):
    """E-bike average speed with the D5 / Q5 modification.

    If ``scenario.bike_assisted_speed_kmh`` is set, use it (capped at the bike
    speed limit); otherwise fall back to the Appendix B formula. The slide shows
    both, so keep ``formula_speed_kmh`` available for comparison.
    """
    raise NotImplementedError


def uptime_h(range_km, speed_kmh):
    """Range / average speed."""
    raise NotImplementedError


def downtime_h(charge_time_h):
    """Charge time + 0.25 h."""
    raise NotImplementedError


def availability(uptime_h, downtime_h):
    """Up-time / (up-time + down-time)."""
    raise NotImplementedError


# --- Constraints -----------------------------------------------------------

def battery_fits(battery_kg, chassis_kg, kind: str) -> bool | np.ndarray:
    """True if the battery is within the weight limit for ``kind`` ("road" or "bike")."""
    raise NotImplementedError


# --- Variant enumeration ---------------------------------------------------

def road_variants(scenario: Scenario) -> pd.DataFrame:
    """Every feasible road variant (chassis x battery x charger x motor x autonomy).

    Drops chassis/battery pairs that violate the weight limit and autonomy
    levels not in ``scenario.allowed_autonomy``. Expect 1,548 rows with all
    three autonomy levels allowed. Columns: ``VARIANT_COLUMNS``.
    """
    raise NotImplementedError


def bike_variants(scenario: Scenario) -> pd.DataFrame:
    """Every feasible e-bike variant (frame x battery x charger x motor).

    Autonomy is fixed L4 (in the frame). Expect 30 rows. Columns: ``VARIANT_COLUMNS``.
    """
    raise NotImplementedError


def all_variants(scenario: Scenario) -> pd.DataFrame:
    """Road and bike variants in one table."""
    raise NotImplementedError


def get_variant(variant_id: str, scenario: Scenario) -> pd.Series:
    """Look up a single variant row by ID (handy for hand-calc checks and the 5-architecture table)."""
    raise NotImplementedError
