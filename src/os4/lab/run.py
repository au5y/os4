"""Model Lab runs: score one config's tradespace and summarize it as JSON, with a disk cache.

``calculate(config)`` returns the summary, the Pareto front, a sample of the tradespace for the scatter
(the explorer's columnar encoding), the reference architecture and anchors (dominated or not), and the
five Task 2 architectures, all under the config's scenario and weights.
"""

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from os4.lab.config import to_scenario, validate
from os4.fleet import Fleet
from os4.model import architecture_table, evaluate_many, reference_and_anchor_table, requirement_flags
from os4.site import _clean, columnar, records, sample_rows
from os4.tradespace import (FLEET_TYPES, _describe, front_comparison, pareto_front, progressive_grid,
                            prune_variants, tradespace)
from os4.utility import ATTRIBUTES, sau
from os4.vehicle import all_variants

SCATTER_CAP = 6000
DEFAULT_LIMIT = 1_500_000   # the page's "limit runs" box (on by default) trims the grid to this many architectures
HARD_LIMIT = 6_000_000      # never score more than this in one run
CORE_SIZES = {"road": 15, "bike": 10}  # trimming never drops the smallest fleets (road 1-15, bikes 5-50)
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
        path.touch()  # mark as recently used, for the cache's size cap
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


def _sizes(segments) -> list[int]:
    return [n for n in progressive_grid([tuple(s) for s in segments]) if n > 0]


def estimate(config: dict) -> dict:
    """How many architectures ``config`` would score: road-only + bike-only + mixed over its fleet grid,
    after the same variant pruning ``tradespace`` does."""
    cfg = validate(config)
    variants = prune_variants(all_variants(to_scenario(cfg)))
    r, b = int((variants["kind"] == "road").sum()), int((variants["kind"] == "bike").sum())
    nr, nb = len(_sizes(cfg["grid"]["road"])), len(_sizes(cfg["grid"]["bike"]))
    return {"road_variants": r, "bike_variants": b, "road_sizes": nr, "bike_sizes": nb,
            "architectures": r * nr + b * nb + r * nr * b * nb}


def limit_grid(config: dict, limit: int = DEFAULT_LIMIT) -> tuple[dict, dict | None]:
    """Trim ``config``'s fleet grid to at most ``limit`` architectures by dropping the largest fleet sizes (the
    flat tail of the front), alternating between road and bikes; returns the config and a note, or the config
    unchanged and ``None`` if it already fits. Raises ``ValueError`` if even the core sizes don't fit."""
    cfg = validate(config)
    est = estimate(cfg)
    if est["architectures"] <= limit:
        return cfg, None
    r, b = est["road_variants"], est["bike_variants"]
    road, bike = _sizes(cfg["grid"]["road"]), _sizes(cfg["grid"]["bike"])
    total = lambda: r * len(road) + b * len(bike) + r * len(road) * b * len(bike)  # noqa: E731
    while total() > limit:
        spare_road, spare_bike = len(road) - CORE_SIZES["road"], len(bike) - CORE_SIZES["bike"]
        if spare_road <= 0 and spare_bike <= 0:
            raise ValueError(f"even the smallest fleets give {total():,} architectures, over {limit:,}")
        # Drop from the list with more sizes beyond its core, so both tails shrink together.
        (road if spare_road * len(bike) >= spare_bike * len(road) and spare_road > 0 else bike).pop()
    clip = lambda segs, top: [[a, min(e, top), s] for a, e, s in segs if a <= top]  # noqa: E731
    trimmed = {**cfg, "grid": {"road": clip(cfg["grid"]["road"], road[-1]), "bike": clip(cfg["grid"]["bike"], bike[-1])}}
    return trimmed, {"from": est["architectures"], "to": total(), "road_max": road[-1], "bike_max": bike[-1],
                     "limit": limit}


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
                        *ATTRIBUTES, "travel_time", "meets_wait_goal", "meets_travel_goal",
                        "meets_availability_benchmark"] if c in sample]
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


PART = re.compile(r"^\s*(\d+)\s*[×x*]\s*([A-Z][\w.-]*)\s*$")


def parse_arch(arch_id: str) -> list[tuple[int, str]]:
    """``"2×C8-P1-G3-M4-A3 + 20×B1-E1-G2-K1"`` -> ``[(2, "C8-P1-G3-M4-A3"), (20, "B1-E1-G2-K1")]``."""
    parts = []
    for chunk in arch_id.split("+"):
        m = PART.match(chunk)
        if not m:
            raise ValueError(f"cannot read {chunk.strip()!r}: use e.g. 2×C8-P1-G3-M4-A3 + 20×B1-E1-G2-K1")
        parts.append((int(m[1]), m[2]))
    return parts


def evaluate_tags(config: dict, tags: list[dict], front: list[dict]) -> list[dict]:
    """Score each tagged architecture (``{"id", "label"}``) under ``config``: its MoPs, MAU with the config's
    weights, requirement flags, and whether the run's Pareto front dominates it. A tag whose vehicle doesn't
    exist in this scenario (e.g. A3 where only A4/A5 are allowed) comes back with a ``status`` instead."""
    if not tags:
        return []
    cfg = validate(config)
    scenario = to_scenario(cfg)
    variants = all_variants(scenario).set_index("variant_id", drop=False)
    front_pts = [(p["fleet_cost_usd"], p["mau"]) for p in front]
    out = []
    for tag in tags:
        row = {"id": tag.get("id", ""), "label": tag.get("label") or tag.get("id", "")}
        try:
            parts = parse_arch(row["id"])
            missing = [v for _, v in parts if v not in variants.index]
            if missing:
                raise KeyError(f"not available in this scenario: {', '.join(missing)}")
            road = [(n, variants.loc[v]) for n, v in parts if variants.at[v, "kind"] == "road"]
            bike = [(n, variants.loc[v]) for n, v in parts if variants.at[v, "kind"] == "bike"]
            if len(road) > 1 or len(bike) > 1:
                raise ValueError("an architecture has at most one road and one bike variant")
            fleet = Fleet(road=road[0][1] if road else None, n_road=road[0][0] if road else 0,
                          bike=bike[0][1] if bike else None, n_bike=bike[0][0] if bike else 0)
            df = _rescore(evaluate_many([fleet], scenario), cfg["weights"])
            flags = requirement_flags(df, scenario)
            df = df.assign(**{c: flags[c] for c in flags.columns if c not in df.columns})
            r = df.iloc[0]
            cost, mau = float(r["fleet_cost_usd"]), float(r["mau"])
            feasible = bool(r["meets_thresholds"] and r["meets_bike_ceiling"] and r["meets_car_ceiling"])
            # The front's MAU is rounded to 4 decimals for the page, so compare with that tolerance.
            tol = 1e-4
            dominated = any(c <= cost and u >= mau - tol and (c < cost - 0.5 or u > mau + tol) for c, u in front_pts)
            row.update({k: _clean(r[k]) for k in ("fleet_cost_usd", "mau", "passenger_volume", "peak_throughput",
                                                   "wait_time", "availability", "travel_time")},
                       n_road=fleet.n_road, road_variant=road[0][1]["variant_id"] if road else None,
                       n_bike=fleet.n_bike, bike_variant=bike[0][1]["variant_id"] if bike else None,
                       feasible=feasible, dominated=dominated,
                       status="ok" if feasible else "fails a Table 1 threshold or a riders-per-day ceiling")
        except (KeyError, ValueError) as e:
            row["status"] = str(e).strip("'\"")
        out.append(row)
    return out


def _point(row: pd.Series) -> dict:
    return {"fleet": _describe(row), "fleet_type": str(row["fleet_type"]),
            "cost": _clean(row["fleet_cost_usd"]), "mau": _clean(row["mau"]),
            "wait_time": _clean(row["wait_time"]), "travel_time": _clean(row["travel_time"]),
            "availability": _clean(row["availability"])}
