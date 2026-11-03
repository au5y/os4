"""Static results explorer: a no-server website over the Task 1-3 results.

``write_site`` copies the HTML/CSS/JS in ``site_template/`` to ``outputs/site/``
and writes the model results next to it as ``data/*.js`` files that assign
plain JSON to ``window.OS4``. Pages load them with ``<script src>``, so the
site opens straight from disk (``file://``) with no fetch, server or CDN.

The tradespace can run to millions of rows, so the browser gets every
road-only and bike-only architecture, every Pareto-front point, and a seeded,
stratified sample of mixed fleets (``mixed_cap`` rows per battery case). Each
case's data records the true totals so the page can say "showing X of Y".

Columns are shipped as they come out of ``tradespace()``: the code iterates over
whatever columns exist, so new metrics appear in the explorer without changes here.
"""

import html
import json
import math
import re
import shutil
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import markdown
import numpy as np
import pandas as pd

from os4.data import load
from os4.model import architecture_table
from os4.plots import LABELS, OUTPUT_DIR, case_table
from os4.scenario import Scenario
from os4.tradespace import FLEET_TYPES, pareto_front, prune_variants, tradespace, utopia_point
from os4.utility import (
    ATTRIBUTES,
    PROPOSED_ATTRIBUTES,
    WEIGHT_SETS,
    compare_weight_sets,
    load_weights,
    sau_table,
    weight_sensitivity,
)
from os4.vehicle import all_variants

TEMPLATE_DIR = Path(__file__).resolve().parent / "site_template"
# Mixed fleets shipped per battery case (front points and per-stratum fronts included in the cap).
MIXED_CAP = 40_000
# Same knee rule as the Task 3 report: first Pareto point with MAU >= 0.94.
KNEE_MAU = 0.94
DECIMALS = 4

ID_COLUMNS = ("road_variant", "n_road", "bike_variant", "n_bike")
CASE_LABELS = {
    "fixed": "Fixed e-bike batteries (Appendix B as given)",
    "removable": "With removable e-bike batteries (team proposal)",
}
PROPOSED_LABELS = {
    "travel_time": ("In-boundary travel time, average Kendall trip", "minutes"),
    "bike_share": ("E-bike share of served trips", "fraction of trips"),
}
# Display names for known columns; anything else is shown under its own name.
COLUMN_LABELS = {
    "architecture": "architecture",
    "fleet_type": "fleet type",
    "road_variant": "road vehicle",
    "n_road": "N road",
    "bike_variant": "e-bike",
    "n_bike": "N bike",
    "road_chassis": "road chassis",
    "bike_frame": "bike frame",
    "battery": "bike battery",
    "fleet_capacity_per_h": "fleet throughput (trips/h)",
    "passenger_volume": "volume (trips/day)",
    "peak_throughput": "peak throughput (trips/h)",
    "wait_time": "avg wait (min)",
    "availability": "availability",
    "travel_time": "travel time, average Kendall trip (min)",
    "bike_share": "bike share",
    "trips_per_vehicle_day": "riders per vehicle per day",
    "road_trips_per_vehicle_day": "riders per road vehicle per day",
    "bike_trips_per_vehicle_day": "riders per bike per day",
    "fleet_cost_usd": "fleet cost",
    "mau": "MAU (Appendix A)",
    "mau_os3a_reweight": "MAU (OS3A reweight, proposed)",
    "meets_thresholds": "meets thresholds",
    "meets_bike_ceiling": "bike ceiling (≤ 15 riders/bike/day)",
    "meets_car_ceiling": "car ceiling (≤ 25 rides/car/day)",
    "car_trips_per_vehicle_day": "rides per car per day",
    "meets_wait_goal": "wait goal (≤ 5 min)",
    "meets_travel_goal": "travel goal (≤ 7 min)",
    "meets_availability_benchmark": "availability ≥ 0.75",
    "road_speed_kmh": "road speed (km/h)",
    "road_range_km": "road range (km)",
    "road_availability": "road availability",
    "road_cost_usd": "road vehicle cost",
    "bike_speed_kmh": "bike speed (km/h)",
    "bike_range_km": "bike range (km)",
    "bike_availability": "bike availability",
    "bike_cost_usd": "bike cost",
}


# --- identifiers -------------------------------------------------------------

def arch_id(row) -> str:
    """Stable architecture key, e.g. ``"12×C2-P2-G3-M2-A3 + 60×B2-E1-G2-K2"`` (the JS builds the same string)."""
    parts = []
    for var, n in (("road_variant", "n_road"), ("bike_variant", "n_bike")):
        count = row[n]
        if count is not None and not pd.isna(count) and int(count) > 0:
            parts.append(f"{int(count)}×{row[var]}")
    return " + ".join(parts)


def battery_cases(scenario: Scenario) -> dict[str, tuple[str, Scenario]]:
    """The two Task 3 cases, as in ``tradespace.write_task3``: fixed batteries only, and the scenario as given."""
    return {
        "fixed": (CASE_LABELS["fixed"], replace(scenario, bike_spare_options=(0.0,))),
        "removable": (CASE_LABELS["removable"], scenario),
    }


def _variant_lookup(scenario: Scenario) -> tuple[dict[str, str], dict[str, float]]:
    variants = all_variants(scenario)
    spares = variants["spares_per_bike"] if "spares_per_bike" in variants else pd.Series(0.0, index=variants.index)
    return dict(zip(variants["variant_id"], variants["chassis"])), dict(zip(variants["variant_id"], spares))


def add_derived(df: pd.DataFrame, scenario: Scenario) -> pd.DataFrame:
    """Add ``road_chassis``, ``bike_frame`` and ``battery`` (fixed/removable) for the explorer's filters.

    Modifies ``df`` in place (the tradespace can be millions of rows) and returns it.
    """
    chassis, spares = _variant_lookup(scenario)
    out = df
    road = out["road_variant"].where(out["n_road"] > 0)
    bike = out["bike_variant"].where(out["n_bike"] > 0)
    out["road_chassis"] = road.map(chassis)
    out["bike_frame"] = bike.map(chassis)
    removable = bike.map(spares).fillna(0) > 0
    out["battery"] = np.where(bike.isna(), None, np.where(removable, "removable", "fixed"))
    return out


def case_frames(scenario: Scenario, n_road=None, n_bike=None) -> dict[str, pd.DataFrame]:
    """Full tradespace for each battery case, with the derived filter columns."""
    return {key: case_frame(case, n_road, n_bike) for key, (_, case) in battery_cases(scenario).items()}


def case_frame(case: Scenario, n_road=None, n_bike=None) -> pd.DataFrame:
    """``tradespace(case)`` (default grids unless given) plus the derived filter columns."""
    grid = {k: v for k, v in (("n_road", n_road), ("n_bike", n_bike)) if v is not None}
    df = tradespace(case, **grid)
    screened = df.attrs.get("screened_out", 0)
    df = add_derived(df, case)
    df.attrs["screened_out"] = screened
    return df


def utility_columns(df: pd.DataFrame) -> list[str]:
    """Utility columns to plot: ``mau`` first, then any other ``mau_*`` column."""
    cols = [c for c in df.columns if c == "mau" or c.startswith("mau_")]
    return sorted(cols, key=lambda c: (c != "mau", c))


# --- sampling ----------------------------------------------------------------

def sample_rows(df: pd.DataFrame, mixed_cap: int = MIXED_CAP, seed: int = 0) -> pd.Index:
    """Index of the rows shipped to the browser.

    Always every non-mixed row and every point on any utility's overall Pareto
    front. Mixed rows are then added, up to ``mixed_cap`` in total, in priority
    order: the mixed-only fronts; the front of each (road chassis, bike frame,
    battery) stratum, so a chassis/frame filter still shows its true upper edge;
    then a seeded random fill spread evenly over those strata. The cap is only
    exceeded if the overall fronts alone hold more mixed fleets than that.
    """
    utilities = utility_columns(df)
    rng = np.random.default_rng(seed)
    is_mixed = (df["fleet_type"] == "mixed").to_numpy()
    keep = ~is_mixed  # boolean mask over row positions (sets of millions of labels are slow)

    def positions(index):
        return df.index.get_indexer(index)

    for u in utilities:  # the overall fronts always ship, even past the cap
        keep[positions(pareto_front(df, u).index)] = True
    if not is_mixed.any():
        return df.index[keep]
    mixed = df[is_mixed]
    budget = mixed_cap - int((keep & is_mixed).sum())
    strata_cols = [c for c in ("road_chassis", "bike_frame", "battery") if c in mixed]

    def strata(frame):
        return [g for _, g in frame.groupby(strata_cols, dropna=False, sort=True)] if strata_cols else [frame]

    # Optional tiers in priority order, each trimmed to what's left of the cap.
    tiers = [[pareto_front(mixed, u).index for u in utilities],
             [pareto_front(g, utilities[0]).index for g in strata(mixed)]]
    for tier in tiers:
        if budget <= 0:
            break
        cand = np.zeros(len(df), dtype=bool)
        for index in tier:
            cand[positions(index)] = True
        new = np.flatnonzero(cand & ~keep)
        if len(new) > budget:
            new = rng.choice(new, size=budget, replace=False)
        keep[new] = True
        budget -= len(new)
    if budget > 0:
        pool = np.flatnonzero(is_mixed & ~keep)
        if budget >= len(pool):
            keep[pool] = True
        else:
            sub = df.iloc[pool]
            groups = list(sub.groupby(strata_cols, dropna=False, sort=True).indices.values()) if strata_cols \
                else [np.arange(len(pool))]
            quota = _water_fill(np.array([len(g) for g in groups]), budget)
            for group, k in zip(groups, quota):
                chosen = group if k >= len(group) else rng.choice(group, size=k, replace=False)
                keep[pool[chosen]] = True
    return df.index[keep]


# --- highlights ----------------------------------------------------------------

def _water_fill(sizes: np.ndarray, budget: int) -> np.ndarray:
    """Split ``budget`` across strata as evenly as their sizes allow (small strata are taken whole)."""
    quota = np.zeros(len(sizes), dtype=int)
    remaining = int(budget)
    while remaining > 0:
        open_ = np.flatnonzero(quota < sizes)
        if not len(open_):
            break
        share = remaining // len(open_)
        if share == 0:  # fewer rows left than open strata: one more each for the largest
            for i in open_[np.argsort(-sizes[open_], kind="stable")][:remaining]:
                quota[i] += 1
            break
        add = np.minimum(sizes[open_] - quota[open_], share)
        quota[open_] += add
        remaining -= int(add.sum())
    return quota


def _meets(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["meets_thresholds"]] if "meets_thresholds" in df else df


def _cheapest(df: pd.DataFrame) -> pd.Series | None:
    if df.empty:
        return None
    return df.sort_values(["fleet_cost_usd", "mau"], ascending=[True, False]).iloc[0]


def highlight_architectures(frames: dict[str, pd.DataFrame], n_front: int = 12, n_mixed: int = 5,
                            knee_mau: float = KNEE_MAU) -> pd.DataFrame:
    """~50 candidate architectures for Task 2, each tagged with why it was picked.

    From each battery case: the cheapest threshold-meeting road-only fleet per
    road chassis and bike-only fleet per bike frame (fixed and removable
    batteries), the Pareto knee (first front point with MAU >= ``knee_mau``),
    ``n_front`` evenly spaced Pareto points, and the ``n_mixed`` mixed fleets
    with the highest MAU per dollar. Duplicates are merged and their reasons joined.
    """
    picks = []
    for k, (case, df) in enumerate(frames.items()):
        # Road-only fleets are the same in every battery case, so they are picked once, for all cases.
        picks += highlight_picks(case, df, road_cases=list(frames) if k == 0 else None, n_front=n_front,
                                 n_mixed=n_mixed, knee_mau=knee_mau)
    return merge_picks(picks)


def highlight_picks(case: str, df: pd.DataFrame, road_cases: list[str] | None = None, n_front: int = 12,
                    n_mixed: int = 5, knee_mau: float = KNEE_MAU) -> list[tuple[list[str], str, pd.Series]]:
    """One case's candidate picks as ``(cases, reason, row)``; road-only picks only if ``road_cases`` is given."""
    picks: list[tuple[list[str], str, pd.Series]] = []
    ok = _meets(df)
    road = ok[ok["fleet_type"] == "road-only"]
    if road_cases:
        for chassis in sorted(road["road_chassis"].dropna().unique(), key=_natural):
            row = _cheapest(road[road["road_chassis"] == chassis])
            if row is not None:
                picks.append((road_cases, f"cheapest road-only {chassis} meeting thresholds", row))
    bike = ok[ok["fleet_type"] == "bike-only"]
    for frame in sorted(bike["bike_frame"].dropna().unique(), key=_natural):
        for battery in ("fixed", "removable"):
            row = _cheapest(bike[(bike["bike_frame"] == frame) & (bike["battery"] == battery)])
            if row is not None:
                picks.append(([case], f"cheapest bike-only {frame} ({battery} battery) meeting thresholds", row))
    front = pareto_front(df)
    knee = front[front["mau"] >= knee_mau]
    if len(knee):
        picks.append(([case], f"Pareto knee (first front point with MAU ≥ {knee_mau:g})", knee.iloc[0]))
    if len(front):
        k = min(n_front, len(front))
        for rank, pos in enumerate(np.unique(np.linspace(0, len(front) - 1, k).round().astype(int)), 1):
            picks.append(([case], f"Pareto front point {rank} of {k} (evenly spaced)", front.iloc[pos]))
    mixed = ok[ok["fleet_type"] == "mixed"]
    if len(mixed):
        per_dollar = mixed["mau"] / mixed["fleet_cost_usd"]
        for rank, i in enumerate(per_dollar.nlargest(n_mixed).index, 1):
            picks.append(([case], f"mixed fleet, #{rank} MAU per dollar", mixed.loc[i]))
    return picks


def merge_picks(picks: list[tuple[list[str], str, pd.Series]]) -> pd.DataFrame:
    """De-duplicate picks by architecture, joining their reasons and cases."""
    merged: dict[str, dict] = {}
    for cases, reason, row in picks:
        key = arch_id(row)
        if key not in merged:
            merged[key] = {"id": key, "cases": [], "reasons": {}, "row": row}
        entry = merged[key]
        entry["cases"] += [c for c in cases if c not in entry["cases"]]
        tagged = entry["reasons"].setdefault(reason, [])
        tagged += [c for c in cases if c not in tagged]
    rows = []
    for entry in merged.values():
        rows.append({"id": entry["id"], "case": ", ".join(entry["cases"]), "reason": "; ".join(f"{r} [{', '.join(c)}]" for r, c in entry["reasons"].items()),
                     **entry["row"].to_dict()})
    return pd.DataFrame(rows).reset_index(drop=True)


def _natural(label: str) -> tuple:
    head = label.rstrip("0123456789")
    tail = label[len(head):]
    return head, int(tail) if tail else 0


# --- JSON encoding -------------------------------------------------------------

def _clean(value):
    """JSON-safe scalar: numpy -> python, NaN/inf -> None, floats rounded."""
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(value):
            return None
        v = round(float(value), DECIMALS)
        return int(v) if v.is_integer() and abs(v) < 2**53 else v
    if pd.isna(value):
        return None
    return value if isinstance(value, (str, list, dict)) else str(value)


def records(df: pd.DataFrame) -> list[dict]:
    """Rows as JSON-safe dicts (all columns)."""
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def columnar(df: pd.DataFrame) -> dict:
    """Compact column-oriented encoding of every column in ``df``.

    Numbers are rounded to ``DECIMALS`` (ints when every value is whole), booleans
    become 0/1, and text columns are dictionary-encoded (index into ``dicts``; -1 = none).
    """
    cols, data, dicts = [], {}, {}
    for name in df.columns:
        s = df[name]
        if pd.api.types.is_bool_dtype(s):
            kind, values = "bool", s.astype(int).tolist()
        elif pd.api.types.is_numeric_dtype(s):
            arr = s.to_numpy(dtype=float)
            finite = np.isfinite(arr)
            rounded = np.round(np.where(finite, arr, 0.0), DECIMALS)
            whole = bool(np.all(rounded[finite] == np.round(rounded[finite])))
            kind = "int" if whole else "num"
            values = [(int(v) if whole else float(v)) if f else None for v, f in zip(rounded.tolist(), finite)]
        else:
            kind = "cat"
            text = s.astype(object).where(s.notna(), None)
            uniques = sorted({v for v in text if v is not None}, key=str)
            lookup = {v: i for i, v in enumerate(uniques)}
            values = [-1 if v is None else lookup[v] for v in text]
            dicts[name] = [str(u) for u in uniques]
        cols.append({"name": name, "kind": kind, "label": COLUMN_LABELS.get(name, name)})
        data[name] = values
    return {"n": len(df), "columns": cols, "data": data, "dicts": dicts}


def _write_js(path: Path, key: str, payload) -> Path:
    """Write ``payload`` as ``window.OS4[key] = <json>;`` (one JSON document per file)."""
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    path.write_text(f'window.OS4 = window.OS4 || {{}};\nwindow.OS4["{key}"] = {body};\n', encoding="utf-8")
    return path


# --- payloads ---------------------------------------------------------------------

def task1_payload() -> dict:
    weights = {name: load_weights(name) for name in WEIGHT_SETS}
    # Only attributes some weight set uses; parked ones (bike share) stay in the data but not on the page.
    weighted = {a for w in weights.values() for a in w}
    proposed = [a for a in PROPOSED_ATTRIBUTES if a in weighted]
    saus = []
    for a in ATTRIBUTES + tuple(proposed):
        raw = sau_table(a)
        label, unit = LABELS.get(a) or PROPOSED_LABELS.get(a, (a, ""))
        saus.append({"attribute": a, "label": label, "unit": unit, "proposed": a in proposed,
                     "x": [_clean(v) for v in raw["x"]], "u": [_clean(v) for v in raw["utility"]]})
    return {
        "attributes": list(ATTRIBUTES),
        "proposed_attributes": proposed,
        "weights": weights,
        "cases": records(case_table()),
        "weight_sets": records(compare_weight_sets()),
        "sensitivity": records(weight_sensitivity()),
        "saus": saus,
    }


def task3_payload(key: str, label: str, df: pd.DataFrame, mixed_cap: int, seed: int = 0) -> dict:
    idx = sample_rows(df, mixed_cap, seed)
    shipped = df.loc[idx]
    # Order: road-only, bike-only, mixed, then by cost, so drawing order and default table order are stable.
    type_rank = shipped["fleet_type"].map({t: i for i, t in enumerate(FLEET_TYPES)}).fillna(len(FLEET_TYPES))
    shipped = shipped.iloc[np.lexsort((shipped["fleet_cost_usd"].to_numpy(), type_rank.to_numpy()))]
    position = pd.Series(np.arange(len(shipped)), index=shipped.index)
    fronts, utopia = {}, {}
    for u in utility_columns(df):
        fronts[u] = position.loc[pareto_front(df, u).index].tolist()
        cost0, util0 = utopia_point(df, u)
        utopia[u] = [_clean(cost0), _clean(util0)]
    totals = {t: int((df["fleet_type"] == t).sum()) for t in FLEET_TYPES}
    shown = {t: int((shipped["fleet_type"] == t).sum()) for t in FLEET_TYPES}
    return {
        "key": key,
        "label": label,
        "totals": {"all": len(df), **totals, "screened_out": int(df.attrs.get("screened_out", 0))},
        "shown": {"all": len(shipped), **shown},
        "mixed_cap": mixed_cap,
        "sampling": ("All road-only and bike-only architectures and every Pareto-front point are included; "
                     f"mixed fleets are a seeded stratified sample (by road chassis × bike frame × battery, "
                     f"each stratum's own front kept) capped at {mixed_cap:,}."),
        "utilities": utility_columns(df),
        "fronts": fronts,
        "utopia": utopia,
        "table": columnar(shipped.reset_index(drop=True)),
    }


def task2_payload(scenario: Scenario, highlights: pd.DataFrame) -> dict:
    archs = architecture_table(scenario)
    archs.insert(1, "id", [arch_id(r) for _, r in archs.iterrows()])
    variants = all_variants(scenario)
    kept = set(prune_variants(variants)["variant_id"])
    variants = variants.assign(kept_after_pruning=variants["variant_id"].isin(kept))
    return {
        "architectures": records(archs),
        "highlights": records(highlights),
        "variants": columnar(variants),
        "labels": COLUMN_LABELS,
    }


def case_summary(df: pd.DataFrame) -> dict:
    """What the overview page needs from one case's tradespace."""
    return {"architectures": len(df), "front": int(len(pareto_front(df))),
            "sizes": {col: sorted(int(v) for v in df[col].unique() if v > 0) for col in ("n_road", "n_bike")}}


# Appendix C (road) and D (e-bike) component tables, decoded in the explorer: a variant id such as
# C5-P1-G3-M2-A3 is chassis-battery-charger-motor-autonomy; B3-E2-G2-K1-S2 is frame-battery-charger-motor
# plus the removable-battery spares per bike.
COMPONENT_TABLES = {
    "road": [("C", "chassis", "road_chassis", "Chassis (body, seats, base energy use)"),
             ("P", "battery", "road_battery", "Battery pack"),
             ("G", "charger", "road_charger", "Charger"),
             ("M", "motor", "road_motor", "Motor and inverter"),
             ("A", "autonomy", "road_autonomy", "Autonomy system (SAE J3016 level)")],
    "bike": [("B", "frame", "bike_frame", "E-bike frame (Level 4 autonomy for riding empty is built in)"),
             ("E", "battery", "bike_battery", "Battery pack"),
             ("G", "charger", "bike_charger", "Charger"),
             ("K", "motor", "bike_motor", "Motor")],
}
COMPONENT_UNITS = {"pax": "seats", "weight_kg": "kg", "cost_usd": "$", "nominal_wh_per_km": "Wh/km",
                   "capacity_kwh": "kWh", "power_kw": "kW", "added_wh_per_km": "+Wh/km", "sae_level": "SAE level"}


def components_payload() -> dict:
    """Every component table from Appendices C and D, for the explorer's reference page and tooltips."""
    out = {}
    for kind, tables in COMPONENT_TABLES.items():
        out[kind] = [{"prefix": prefix, "part": part, "title": title, "source": "Appendix C" if kind == "road"
                      else "Appendix D", "units": COMPONENT_UNITS, "rows": records(load(name))}
                     for prefix, part, name, title in tables]
    return out


def meta_payload(scenario: Scenario, summaries: dict[str, dict], mixed_cap: int) -> dict:
    grid = {}
    for col in ("n_road", "n_bike"):
        values = sorted({v for s in summaries.values() for v in s["sizes"][col]})
        grid[col] = {"min": values[0], "max": values[-1], "count": len(values)} if values else None
    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "scenario": scenario.name,
        "requirements": {k: _clean(getattr(scenario, k)) for k in (
            "min_daily_volume", "min_peak_throughput", "min_offpeak_throughput", "goal_wait_min",
            "goal_travel_min", "benchmark_availability") if hasattr(scenario, k)},
        "grid": grid,
        "cases": {k: {"label": CASE_LABELS[k], "architectures": s["architectures"], "front": s["front"]}
                  for k, s in summaries.items()},
        "mixed_cap": mixed_cap,
        "labels": COLUMN_LABELS,
        "components": components_payload(),
    }


REPORT_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OS4 · {title}</title>
<link rel="stylesheet" href="assets/style.css">
{math}</head>
<body>
<main class="wrap report" id="main">
{note}
{body}
</main>
<script src="data/meta.js"></script>
<script src="assets/common.js"></script>
<script>OS4.util.header("{current}");</script>
</body>
</html>
"""
IMG_SRC = re.compile(r'<img alt="([^"]*)" src="(?:media/)?([^"/]+)"')
# A page section that shows a report inline: <!-- report:<stem> --> fallback <!-- /report -->.
REPORT_SLOT = re.compile(r"<!-- report:([\w-]+) -->.*?<!-- /report -->", re.S)
HEADING = re.compile(r"<(/?)h([1-5])((?: [^>]*)?)>")
TABLE = re.compile(r'<div class="table-wrap"><table>.*?</table></div>', re.S)
# Tables longer than this (e.g. the Pareto fronts) start collapsed, so the page can be scrolled past them.
LONG_TABLE_ROWS = 12


def write_reports(src_dir: Path, out_dir: Path) -> list[Path]:
    """Render the Markdown reports in ``src_dir`` (``task*.md``) as pages of the explorer.

    Each report becomes ``report_<stem>.html`` (title from its first heading) with its images copied
    to ``img/``; ``reports.html`` lists them. Missing reports are skipped, so the site still builds
    when only part of ``python -m os4`` has run.
    """
    img_dir = out_dir / "img"
    reports, paths = [], []
    for md_path in sorted(Path(src_dir).glob("task*.md")):
        text = md_path.read_text(encoding="utf-8")
        title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")), md_path.stem)
        body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc"])
        body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
        body = TABLE.sub(_collapse_long_table, body).replace('href="../docs/references.md', 'href="references.html')
        for _, src in IMG_SRC.findall(body):
            found = next((p for p in (md_path.parent / "media" / src, md_path.parent / src) if p.exists()), None)
            if found:
                img_dir.mkdir(exist_ok=True)
                shutil.copy2(found, img_dir / src)
                paths.append(img_dir / src)
        body = IMG_SRC.sub(r'<img alt="\1" src="img/\2"', body)
        _embed_report(out_dir, md_path.stem, md_path.name, body)
        page = out_dir / f"report_{md_path.stem}.html"
        page.write_text(REPORT_PAGE.format(title=html.escape(title), note=_report_note(md_path.name),
                                           current="reports.html", body=_with_contents(body, 2), math=""), encoding="utf-8")
        reports.append((page.name, title, md_path.name))
        paths.append(page)
    items = "\n".join(f'<li><a href="{href}">{html.escape(title)}</a> <span class="muted small">({source})</span></li>'
                      for href, title, source in reports) or "<li>No reports yet: run <code>python -m os4</code>.</li>"
    index = out_dir / "reports.html"
    index.write_text(REPORT_PAGE.format(
        title="Reports", note=_report_note("task*.md"), current="reports.html",
        body=f"<h1>Reports</h1>\n<p>The Markdown reports the model writes next to its figures.</p>\n<ul>\n{items}\n</ul>", math=""),
        encoding="utf-8")
    return [index] + paths


def _report_note(source: str) -> str:
    return (f'<p class="muted small">Rendered from <code>outputs/{source}</code>, written by '
            "<code>python -m os4</code>.</p>")


DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
# Team documents shown read-only: source file -> (page, nav entry it highlights).
DOC_PAGES = {"PLAN.md": "plan.html", "references.md": "references.html"}
DOC_LINKS = {'href="references.md': 'href="references.html', 'href="PLAN.md': 'href="plan.html',
             'href="../outputs/': 'href="report_'}
MATH_BLOCK = re.compile(r"^\$\$(.+?)\$\$$", re.M)
# KaTeX renders display math (\[ ... \]) on pages that have it; only \[ \] delimiters, since the text uses $ for dollars.
KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist"
MATH_HEAD = f"""<link rel="stylesheet" href="{KATEX}/katex.min.css">
<script defer src="{KATEX}/katex.min.js"></script>
<script defer src="{KATEX}/contrib/auto-render.min.js"
  onload="renderMathInElement(document.getElementById('main'), {{delimiters: [{{left: '\\\\[', right: '\\\\]', display: true}}]}})"></script>
"""


def write_docs(docs_dir: Path, out_dir: Path) -> list[Path]:
    """Render the team's ``docs/PLAN.md`` and ``docs/references.md`` as read-only pages of the explorer.

    Links between them (and to the reports) are pointed at the rendered pages; display math is shown
    with KaTeX (``MATH_HEAD``).
    """
    paths = []
    for name, page_name in DOC_PAGES.items():
        md_path = Path(docs_dir) / name
        if not md_path.exists():
            continue
        text = MATH_BLOCK.sub(lambda m: f'<div class="math">\\[{html.escape(m[1])}\\]</div>',
                              md_path.read_text(encoding="utf-8"))
        body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc"])
        body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
        for old, new in DOC_LINKS.items():
            body = body.replace(old, new)
        body = re.sub(r'href="report_([\w-]+)\.md', r'href="report_\1.html', body)
        note = (f'<p class="view-only"><b>View only.</b> Rendered from <code>docs/{name}</code> when the site is '
                "built; edit the file in the repository and rerun <code>python -m os4</code> to update this page.</p>")
        title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")), name)
        page = out_dir / page_name
        math = MATH_HEAD if '<div class="math">' in body else ""
        page.write_text(REPORT_PAGE.format(title=html.escape(title), note=note, current=page_name,
                                           body=_with_contents(body, 2), math=math), encoding="utf-8")
        paths.append(page)
    return paths


# Each PLAN.md question is a heading "#### <a id="q12"></a>Q12. <the question>?".
QUESTION_DEF = re.compile(r'^#+ <a id="q(\d+)"></a>Q\d+\. (.+)$', re.M)
QUESTION = re.compile(r"\bQ(\d+)\b")
QUESTION_LINK = re.compile(r'<a (class="qref" )?href="((?:plan\.html)?#q(\d+))">')
# Text inside these elements is left unlinked (headings feed the contents list, which is itself links).
NO_LINK_TAGS = {"a", "code", "pre", "h1", "h2", "h3", "h4", "h5", "h6", "title", "script", "style"}


def plan_questions(plan_path: Path) -> dict[str, str]:
    """PLAN.md's questions by number (``{"12": "What counts as peak throughput?", ...}``); empty if it is missing."""
    if not plan_path.exists():
        return {}
    text = plan_path.read_text(encoding="utf-8")
    return {n: re.sub(r"[`*]", "", q).strip() for n, q in QUESTION_DEF.findall(text)}


def link_questions(out_dir: Path, questions: dict[str, str]) -> None:
    """Link every "Q<n>" in the site's pages to its question in plan.html, with the question as a tooltip.

    PLAN.md carries its own anchors and links; this links the plain "Q<n>" in the reports and pages
    (text in links, code and headings is left alone) and gives every question link a ``title``.
    """
    if not questions:
        return
    for page in Path(out_dir).glob("*.html"):
        text = page.read_text(encoding="utf-8")
        linked = _link_text(text, questions, "" if page.name == "plan.html" else "plan.html")
        linked = QUESTION_LINK.sub(lambda m: m[0] if m[3] not in questions else
                                   f'<a class="qref" href="{m[2]}" title="Q{m[3]}. {html.escape(questions[m[3]])}">',
                                   linked)
        if linked != text:
            page.write_text(linked, encoding="utf-8")


def _link_text(html_text: str, known: dict[str, str], base: str) -> str:
    """Wrap "Q<n>" in text outside ``NO_LINK_TAGS`` in a link to ``{base}#q<n>``."""
    out, depth = [], 0
    for part in re.split(r"(<[^>]+>)", html_text):
        if part.startswith("<"):
            name = re.match(r"</?([a-zA-Z0-9]+)", part)
            if name and name[1].lower() in NO_LINK_TAGS and not part.endswith("/>"):
                depth += -1 if part.startswith("</") else 1
        elif depth == 0 and part:
            part = QUESTION.sub(lambda m: f'<a class="qref" href="{base}#q{m[1]}">{m[0]}</a>'
                                if m[1] in known else m[0], part)
        out.append(part)
    return "".join(out)


def _collapse_long_table(m: re.Match) -> str:
    """Wrap a table longer than ``LONG_TABLE_ROWS`` in a collapsed <details>."""
    rows = m[0].count("<tr>") - 1
    if rows <= LONG_TABLE_ROWS:
        return m[0]
    return (f'<details class="long-table"><summary>Table: {rows} rows (click to expand)</summary>\n'
            f"{m[0]}\n</details>")


def _with_contents(body: str, level: int) -> str:
    """Prepend links to the report's level-``level`` headings, with their level + 1 subsections nested
    (needs the toc extension's ids)."""
    heads = re.findall(rf'<h({level}|{level + 1}) id="([^"]+)">(.*?)</h\1>', body)
    if sum(int(h) == level for h, _, _ in heads) < 3:
        return body
    items, open_sub = [], False
    for h, i, t in heads:
        if int(h) == level:
            if open_sub:
                items.append("</ul></li>")
            elif items:
                items.append("</li>")
            items.append(f'<li><a href="#{i}">{t}</a>')
            open_sub = False
        elif items:
            items.append(("" if open_sub else "<ul>") + f'<li><a href="#{i}">{t}</a></li>')
            open_sub = True
    items.append("</ul></li>" if open_sub else "</li>")
    return f'<nav class="report-toc" aria-label="Contents"><b>Contents</b><ol>{"".join(items)}</ol></nav>\n{body}'


def _embed_report(out_dir: Path, stem: str, source: str, body: str) -> None:
    """Put a rendered report into every page with a ``<!-- report:<stem> -->`` slot (e.g. Task 2's write-up).

    The report's own title is dropped (the page has one) and its headings move down a level to
    sit under the slot's section heading.
    """
    inline = HEADING.sub(lambda m: f"<{m[1]}h{int(m[2]) + 1}{m[3]}>", re.sub(r"<h1[^>]*>.*?</h1>\n?", "", body, count=1))
    inline = _with_contents(inline, 3)
    note = _report_note(source)
    for page in out_dir.glob("*.html"):
        text = page.read_text(encoding="utf-8")
        filled = REPORT_SLOT.sub(lambda m: f"{note}\n{inline}" if m[1] == stem else m[0], text)
        if filled != text:
            page.write_text(filled, encoding="utf-8")


def write_site(scenario: Scenario, out_dir: Path = OUTPUT_DIR / "site", n_road=None, n_bike=None,
               mixed_cap: int = MIXED_CAP, reports_dir: Path | None = OUTPUT_DIR,
               docs_dir: Path | None = DOCS_DIR) -> list[Path]:
    """Write the static results explorer to ``out_dir``; returns the files written.

    ``n_road`` / ``n_bike`` override the tradespace fleet-size grids (``None`` keeps
    ``tradespace``'s defaults); tests pass small grids. The Markdown reports in ``reports_dir``
    are rendered as pages (``write_reports``), and ``docs_dir``'s PLAN.md and references.md as view-only
    pages (``write_docs``); ``None`` skips either.
    """
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(TEMPLATE_DIR, out_dir)
    data_dir = out_dir / "data"
    data_dir.mkdir(exist_ok=True)

    # One case at a time, so only one (possibly multi-million-row) tradespace is in memory.
    paths, picks, summaries = [], [], {}
    cases = battery_cases(scenario)
    for k, (key, (label, case)) in enumerate(cases.items()):
        df = case_frame(case, n_road, n_bike)
        summaries[key] = case_summary(df)
        picks += highlight_picks(key, df, road_cases=list(cases) if k == 0 else None)
        paths.append(_write_js(data_dir / f"task3_{key}.js", f"task3_{key}", task3_payload(key, label, df, mixed_cap)))
        del df
    paths = [
        _write_js(data_dir / "meta.js", "meta", meta_payload(scenario, summaries, mixed_cap)),
        _write_js(data_dir / "task1.js", "task1", task1_payload()),
        _write_js(data_dir / "task2.js", "task2", task2_payload(scenario, merge_picks(picks))),
    ] + paths
    if reports_dir is not None:
        write_reports(reports_dir, out_dir)
    if docs_dir is not None:
        write_docs(docs_dir, out_dir)
        link_questions(out_dir, plan_questions(Path(docs_dir) / "PLAN.md"))
    pages = sorted(p for p in out_dir.rglob("*") if p.is_file() and p.parent != data_dir)
    return pages + paths
