"""Model Lab runs: score one config's tradespace and summarize it as JSON, with a disk cache.

``calculate(config)`` returns the summary, the Pareto front, a sample of the tradespace for the scatter
(the explorer's columnar encoding), the reference architecture and anchors (dominated or not), and the
five Task 2 architectures, all under the config's scenario and weights.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from os4.lab.config import to_scenario, validate
from os4.model import architecture_table, reference_and_anchor_table
from os4.site import _clean, columnar, records, sample_rows
from os4.tradespace import (FLEET_TYPES, _describe, front_comparison, pareto_front, progressive_grid,
                            tradespace)
from os4.utility import ATTRIBUTES, sau

SCATTER_CAP = 6000
KNEE_MAU = 0.94
SRC = Path(__file__).resolve().parents[1]
FRONT_COLUMNS = ["fleet_type", "road_variant", "n_road", "bike_variant", "n_bike", "fleet_cost_usd", "mau",
                 "passenger_volume", "peak_throughput", "wait_time", "availability", "travel_time",
                 "trips_per_vehicle_day", "meets_travel_goal", "meets_wait_goal"]
MARKER_COLUMNS = ["architecture", "role", "road_variant", "n_road", "bike_variant", "n_bike", "road_speed_kmh",
                  "bike_speed_kmh", "fleet_capacity_per_h", "passenger_volume", "peak_throughput", "wait_time",
                  "availability", "travel_time", "mau", "fleet_cost_usd", "meets_thresholds"]


def code_version() -> str:
    """Hash of the model's source, so cached results expire when the code changes."""
    h = hashlib.sha256()
    for path in sorted(SRC.glob("*.py")) + sorted((SRC / "lab").glob("*.py")) + sorted(SRC.parent.parent.glob("data/*.csv")):
        h.update(path.read_bytes())
    return h.hexdigest()[:16]


def config_key(config: dict) -> str:
    canonical = json.dumps(validate(config), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((canonical + code_version()).encode()).hexdigest()[:24]


def calculate(config: dict, progress=None, cache_dir: Path | None = None) -> dict:
    """Score ``config`` (cached in ``cache_dir`` if given); ``progress(done, total)`` reports scoring progress."""
    cfg = validate(config)
    key = config_key(cfg)
    path = cache_dir / f"{key}.json" if cache_dir else None
    if path and path.exists():
        result = json.loads(path.read_text(encoding="utf-8"))
        result["cached"] = True
        return result
    result = _calculate(cfg, progress)
    result["key"] = key
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    result["cached"] = False
    return result


def _rescore(df: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Recompute ``mau`` with the config's weights (``model.evaluate`` always uses Appendix A)."""
    if df is None or df.empty:
        return df
    return df.assign(mau=sum(w * sau(a, df[a].to_numpy(dtype=float)) for a, w in weights.items()))


def _safe(fn, *args):
    try:
        return fn(*args), None
    except (KeyError, ValueError) as e:  # e.g. the reference's A3 vehicle is not allowed in this scenario
        return None, str(e).strip("'\"")


def _calculate(cfg: dict, progress) -> dict:
    scenario = to_scenario(cfg)
    weights = cfg["weights"]
    n_road = progressive_grid([tuple(s) for s in cfg["grid"]["road"]])
    n_bike = progressive_grid([tuple(s) for s in cfg["grid"]["bike"]])
    df = tradespace(scenario, n_road, n_bike, label="lab", weights=weights, progress=progress)

    markers, marker_note = _safe(reference_and_anchor_table, scenario)
    markers = _rescore(markers, weights)
    archs, arch_note = _safe(architecture_table, scenario)
    archs = _rescore(archs, weights)

    out = {
        "name": cfg["name"],
        "config": cfg,
        "grid_size": int(df.attrs.get("grid_size", 0)),
        "screened_out": int(df.attrs.get("screened_out", 0)),
        "threshold_failures": {k: int(v) for k, v in df.attrs.get("threshold_failures", {}).items()},
        "notes": [n for n in (marker_note and f"Reference/anchors not scored: {marker_note}",
                              arch_note and f"Task 2 architectures not scored: {arch_note}") if n],
    }
    if df.empty:
        out.update(summary={"feasible": 0}, front=[], scatter=None, markers=[], architectures=[])
        return out

    front = pareto_front(df)
    cheapest = df.loc[df["fleet_cost_usd"].idxmin()]
    knee = front[front["mau"] >= KNEE_MAU]
    knee = knee.iloc[0] if len(knee) else None
    counts = front["fleet_type"].value_counts()
    best = {a: float(sau(a, df[a].to_numpy(dtype=float)).max()) for a in weights}
    out["summary"] = {
        "feasible": len(df),
        "max_mau": float(df["mau"].max()),
        "mau_ceiling": sum(w * best[a] for a, w in weights.items()),
        "cheapest": _point(cheapest),
        "knee": None if knee is None else _point(knee),
        "front_counts": {t: int(counts.get(t, 0)) for t in FLEET_TYPES},
        "front_travel_ok": float(front["meets_travel_goal"].mean()),
        "front_wait_ok": float(front["meets_wait_goal"].mean()),
        "cheapest_by_type": {t: _point(g.loc[g["fleet_cost_usd"].idxmin()])
                             for t, g in df.groupby("fleet_type", observed=True) if len(g)},
    }
    out["front"] = records(front[[c for c in FRONT_COLUMNS if c in front]])

    sample = df.loc[sample_rows(df, SCATTER_CAP)]
    keep = [c for c in ["fleet_type", "road_variant", "n_road", "bike_variant", "n_bike", "fleet_cost_usd", "mau",
                        *ATTRIBUTES, "travel_time"] if c in sample]
    out["scatter"] = columnar(sample[keep].sort_values("fleet_cost_usd"))

    if markers is not None:
        check = front_comparison(df, markers).set_index("architecture")
        rows = records(markers[[c for c in MARKER_COLUMNS if c in markers]])
        for r in rows:
            c = check.loc[r["architecture"]]
            r.update(fleet=c["fleet"], dominated=bool(c["dominated"]), cheaper_same_mau=c["same utility, cheapest"],
                     better_same_cost=c["same cost, best"])
        out["markers"] = rows
    else:
        out["markers"] = []
    out["architectures"] = [] if archs is None else records(archs[[c for c in MARKER_COLUMNS if c in archs]])
    return out


def _point(row: pd.Series) -> dict:
    return {"fleet": _describe(row), "fleet_type": str(row["fleet_type"]),
            "cost": _clean(row["fleet_cost_usd"]), "mau": _clean(row["mau"]),
            "wait_time": _clean(row["wait_time"]), "travel_time": _clean(row["travel_time"]),
            "availability": _clean(row["availability"])}
