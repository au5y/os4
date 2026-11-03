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

from os4.data import load
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
    "spares_per_bike",  # removable-battery option; 0 = fixed battery (always 0 for road)
    "pax",
    "load_factor",  # average riders per trip / seats (road: Appendix B 0.75; bikes: by seats, PLAN.md Q16)
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
    return chassis_kg + battery_kg + charger_kg + motor_kg + autonomy_kg + PAX_WEIGHT_KG * pax


def total_cost_usd(chassis_usd, battery_usd, charger_usd, motor_usd, autonomy_usd):
    """Sum of component costs (bike frame cost already includes L4 autonomy)."""
    return chassis_usd + battery_usd + charger_usd + motor_usd + autonomy_usd


def charge_time_h(battery_kwh, charger_kw):
    """Battery capacity / charger power."""
    return battery_kwh / charger_kw


def power_consumption_wh_per_km(nominal_wh_per_km, total_kg, chassis_kg, autonomy_wh_per_km):
    """Nominal + 0.1 * (total weight - chassis weight) + autonomy add-on."""
    return nominal_wh_per_km + WEIGHT_WH_PER_KM_PER_KG * (total_kg - chassis_kg) + autonomy_wh_per_km


def range_km(battery_kwh, wh_per_km):
    """Battery capacity [Wh] / power consumption [Wh/km]."""
    return battery_kwh * 1000.0 / wh_per_km


def formula_speed_kmh(motor_kw, total_kg):
    """Uncapped Appendix B speed: 700 * motor power [kW] / total weight [kg]."""
    return SPEED_COEFF * motor_kw / total_kg


def road_speed_kmh(motor_kw, total_kg, speed_limit_kmh):
    """Formula speed capped at the posted speed limit."""
    return np.minimum(formula_speed_kmh(motor_kw, total_kg), speed_limit_kmh)


def bike_speed_kmh(motor_kw, total_kg, scenario: Scenario):
    """E-bike average speed with the Q6 modification.

    If ``scenario.bike_assisted_speed_kmh`` is set, use it (capped at the bike
    speed limit); otherwise fall back to the Appendix B formula. The slide shows
    both, so keep ``formula_speed_kmh`` available for comparison.
    """
    if scenario.bike_assisted_speed_kmh is None:
        speed = formula_speed_kmh(motor_kw, total_kg)
    else:
        speed = np.full_like(np.asarray(motor_kw, dtype=float), scenario.bike_assisted_speed_kmh)
    if scenario.bike_speed_limit_kmh is not None:
        speed = np.minimum(speed, scenario.bike_speed_limit_kmh)
    return speed


def uptime_h(range_km, speed_kmh):
    """Range / average speed."""
    return range_km / speed_kmh


def downtime_h(charge_time_h):
    """Charge time + 0.25 h."""
    return charge_time_h + CHARGE_OVERHEAD_H


def availability(uptime_h, downtime_h):
    """Up-time / (up-time + down-time)."""
    return uptime_h / (uptime_h + downtime_h)


# --- Removable e-bike batteries (team proposal) ------------------------------

def swap_availability(uptime_h, charge_time_h, spares_per_bike, swap_h):
    """Riding fraction of a bike whose battery is swapped instead of charged in place.

    The bike rides ``uptime_h``, then a swap takes ``swap_h``. The removed pack
    charges off the bike for ``charge_time_h`` plus the Appendix B 0.25 h
    overhead before it is ready again. With 1 + k packs per bike in rotation
    the bike is limited either by the swap itself, U / (U + s), or by the supply
    of charged packs, (1 + k) * U / (U + s + C + 0.25). With k = 0 and s = 0
    this is the Appendix B availability.
    """
    swap_limited = uptime_h / (uptime_h + swap_h)
    pack_limited = (1 + spares_per_bike) * uptime_h / (uptime_h + swap_h + charge_time_h + CHARGE_OVERHEAD_H)
    return np.minimum(swap_limited, pack_limited)


def spares_for_no_waiting(uptime_h, charge_time_h, swap_h):
    """Spare packs per bike above which more spares add nothing: (C + 0.25) / (U + s)."""
    return (charge_time_h + CHARGE_OVERHEAD_H) / (uptime_h + swap_h)


def spare_cost_usd(spares_per_bike, battery_usd, charger_usd):
    """Each spare pack needs its own charger slot at the swap station."""
    return spares_per_bike * (battery_usd + charger_usd)


# --- Constraints -----------------------------------------------------------

def battery_fits(battery_kg, chassis_kg, kind: str) -> bool | np.ndarray:
    """True if the battery is within the weight limit for ``kind`` ("road" or "bike")."""
    limits = {"road": ROAD_BATTERY_WEIGHT_LIMIT, "bike": BIKE_BATTERY_WEIGHT_LIMIT}
    if kind not in limits:
        raise ValueError(f"kind must be 'road' or 'bike', got {kind!r}")
    return battery_kg <= limits[kind] * chassis_kg


# --- Variant enumeration ---------------------------------------------------

def road_variants(scenario: Scenario) -> pd.DataFrame:
    """Every feasible road variant (chassis x battery x charger x motor x autonomy).

    Drops chassis/battery pairs that violate the weight limit and autonomy
    levels not in ``scenario.allowed_autonomy``. Expect 1,548 rows with all
    three autonomy levels allowed. Columns: ``VARIANT_COLUMNS``.
    """
    df = _cross(
        load("road_chassis").add_prefix("chassis_"),
        load("road_battery").add_prefix("battery_"),
        load("road_charger").add_prefix("charger_"),
        load("road_motor").add_prefix("motor_"),
        load("road_autonomy").add_prefix("autonomy_"),
    )
    df = df[battery_fits(df["battery_weight_kg"], df["chassis_weight_kg"], "road")]
    df = df[df["autonomy_id"].isin(scenario.allowed_autonomy)]
    speed = road_speed_kmh(df["motor_power_kw"], _weight(df), scenario.speed_limit_kmh)
    return _finish(df, "road", speed, scenario.speed_limit_kmh, scenario.load_factor)


def bike_variants(scenario: Scenario) -> pd.DataFrame:
    """Every feasible e-bike variant (frame x battery x charger x motor).

    Autonomy is fixed L4 (in the frame). Expect 30 fixed-battery rows, plus 30
    removable-battery rows for each non-zero ``scenario.bike_spare_options``
    (variant IDs end in ``-S<spares>``). Columns: ``VARIANT_COLUMNS``.
    """
    df = _cross(
        load("bike_frame").add_prefix("chassis_"),
        load("bike_battery").add_prefix("battery_"),
        load("bike_charger").add_prefix("charger_"),
        load("bike_motor").add_prefix("motor_"),
    )
    df = df[battery_fits(df["battery_weight_kg"], df["chassis_weight_kg"], "bike")]
    # L4 autonomy is in the frame cost; Appendix D gives it no extra weight or energy use.
    df = df.assign(autonomy_id="L4", autonomy_weight_kg=0.0, autonomy_cost_usd=0.0, autonomy_added_wh_per_km=0.0)
    speed = bike_speed_kmh(df["motor_power_kw"].to_numpy(), _weight(df).to_numpy(), scenario)
    limit = scenario.bike_speed_limit_kmh if scenario.bike_speed_limit_kmh is not None else np.inf
    fixed = _finish(df, "bike", speed, limit, bike_load_factor(df["chassis_pax"].to_numpy(), scenario))
    parts = [fixed] if 0 in scenario.bike_spare_options else []
    for k in (k for k in scenario.bike_spare_options if k > 0):
        swap = fixed.copy()
        swap["variant_id"] = swap["variant_id"] + f"-S{k:g}"
        swap["spares_per_bike"] = float(k)
        swap["cost_usd"] = fixed["cost_usd"] + spare_cost_usd(
            k, df["battery_cost_usd"].to_numpy(), df["charger_cost_usd"].to_numpy())
        avail = swap_availability(fixed["uptime_h"], fixed["charge_time_h"], k, scenario.bike_swap_h)
        swap["availability"] = avail
        # Effective down-time per ride, so that availability = up / (up + down) still holds.
        swap["downtime_h"] = fixed["uptime_h"] * (1 / avail - 1)
        parts.append(swap)
    return pd.concat(parts, ignore_index=True)


def bike_load_factor(pax, scenario: Scenario) -> np.ndarray:
    """Riders per bike trip / seats for each bike's seat count (``scenario.bike_load_factors``, PLAN.md Q16)."""
    factors = dict(scenario.bike_load_factors)
    pax = np.asarray(pax)
    missing = set(np.unique(pax)) - set(factors)
    if missing:
        raise ValueError(f"no bike load factor for {sorted(missing)} seats; add it to Scenario.bike_load_factors")
    return np.array([factors[p] for p in pax], dtype=float)


def all_variants(scenario: Scenario) -> pd.DataFrame:
    """Road and bike variants in one table."""
    return pd.concat([road_variants(scenario), bike_variants(scenario)], ignore_index=True)


def get_variant(variant_id: str, scenario: Scenario) -> pd.Series:
    """Look up a single variant row by ID (handy for hand-calc checks and the 5-architecture table)."""
    df = all_variants(scenario)
    match = df[df["variant_id"] == variant_id]
    if match.empty:
        raise KeyError(f"no feasible variant {variant_id!r} in scenario {scenario.name!r}")
    return match.iloc[0]


# --- Helpers ---------------------------------------------------------------

def _cross(*tables: pd.DataFrame) -> pd.DataFrame:
    """Cartesian product of the component tables."""
    out = tables[0]
    for t in tables[1:]:
        out = out.merge(t, how="cross")
    return out


def _weight(df: pd.DataFrame) -> pd.Series:
    return total_weight_kg(
        df["chassis_weight_kg"], df["battery_weight_kg"], df["charger_weight_kg"],
        df["motor_weight_kg"], df["autonomy_weight_kg"], df["chassis_pax"],
    )


def _finish(df: pd.DataFrame, kind: str, speed, speed_limit_kmh: float, load_factor) -> pd.DataFrame:
    """Apply the Appendix B equations to a table of component selections."""
    weight = _weight(df)
    wh_per_km = power_consumption_wh_per_km(
        df["chassis_nominal_wh_per_km"], weight, df["chassis_weight_kg"], df["autonomy_added_wh_per_km"]
    )
    rng = range_km(df["battery_capacity_kwh"], wh_per_km)
    charge = charge_time_h(df["battery_capacity_kwh"], df["charger_power_kw"])
    speed = np.asarray(speed, dtype=float)
    up, down = uptime_h(rng, speed), downtime_h(charge)
    ids = [df["chassis_id"], df["battery_id"], df["charger_id"], df["motor_id"]]
    if kind == "road":
        ids.append(df["autonomy_id"])
    out = pd.DataFrame({
        "kind": kind,
        "variant_id": pd.concat(ids, axis=1).agg("-".join, axis=1),
        "chassis": df["chassis_id"],
        "battery": df["battery_id"],
        "charger": df["charger_id"],
        "motor": df["motor_id"],
        "autonomy": df["autonomy_id"],
        "spares_per_bike": 0.0,
        "pax": df["chassis_pax"],
        "load_factor": np.broadcast_to(np.asarray(load_factor, dtype=float), len(df)),
        "weight_kg": weight,
        "cost_usd": total_cost_usd(
            df["chassis_cost_usd"], df["battery_cost_usd"], df["charger_cost_usd"],
            df["motor_cost_usd"], df["autonomy_cost_usd"],
        ),
        "wh_per_km": wh_per_km,
        "range_km": rng,
        "speed_kmh": speed,
        "speed_capped": speed >= speed_limit_kmh - 1e-9,
        "charge_time_h": charge,
        "uptime_h": up,
        "downtime_h": down,
        "availability": availability(up, down),
    })
    return out[VARIANT_COLUMNS].reset_index(drop=True)
