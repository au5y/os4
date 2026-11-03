"""Tasks 3-4: enumerate the design vector, score architectures, plot tradespace.

``tradespace`` scores every road-only, bike-only and mixed fleet on the
fleet-size grids with the same equations as ``os4.fleet`` / ``os4.model``,
vectorized over architectures (``test_tradespace.py`` checks it matches
``model.evaluate``). ``pareto_front`` and ``utopia_point`` summarize it, and
``write_task3`` writes the report to ``outputs/`` and its figures and CSVs to ``outputs/media/``.
"""

from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.cm  # noqa: E402
import matplotlib.colors  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from os4.fleet import Fleet, service_probability  # noqa: E402
from os4.model import (  # noqa: E402
    architecture_table,
    evaluate_many,
    meets_bike_ceiling,
    meets_car_ceiling,
    meets_thresholds,
    reference_and_anchor_table,
    requirement_flags,
)
from os4.plots import (  # noqa: E402
    GRID,
    INK,
    INK_2,
    OUTPUT_DIR,
    SERIES,
    SURFACE,
    _md_table,
    _style,
    media_dir,
    media_link,
)
from os4.data import load  # noqa: E402
from os4.scenario import Scenario  # noqa: E402
from os4.utility import ATTRIBUTES, load_weights, sau  # noqa: E402
from os4.vehicle import all_variants, get_variant  # noqa: E402


def progressive_grid(segments: Iterable[tuple[int, int, int]]) -> tuple[int, ...]:
    """Fleet sizes from (start, stop, step) segments, stop inclusive, with 0 (= that part absent) first."""
    return tuple(sorted({0} | {n for start, stop, step in segments for n in range(start, stop + 1, step)}))


# Q14: steps widen as fleets grow. Small fleets (a few buses, a few bikes next to them) decide where the
# front starts, so they get step 1 (road) or 5 (bikes); past the knee cost rises linearly with N while
# utility is flat, so coarse steps lose nothing.
ROAD_SEGMENTS = ((1, 15, 1), (20, 50, 5), (60, 100, 10), (125, 300, 25))
BIKE_SEGMENTS = ((5, 50, 5), (75, 200, 25), (250, 750, 50))
N_ROAD = progressive_grid(ROAD_SEGMENTS)
N_BIKE = progressive_grid(BIKE_SEGMENTS)
FLEET_TYPES = ("road-only", "bike-only", "mixed")
# Same validated categorical slots as Task 1; shapes are the secondary encoding.
TYPE_STYLE = {
    "road-only": (SERIES[0], "o"),
    "bike-only": (SERIES[1], "^"),
    "mixed": (SERIES[2], "s"),
}


def prune_variants(variants: pd.DataFrame) -> pd.DataFrame:
    """Drop vehicle variants dominated on every vehicle-level metric at equal or higher cost.

    E.g. a bigger motor with no speed gain once the speed cap binds. Within each
    kind, a variant is dropped if another is at least as fast, carries at least
    as many passengers, is at least as available and costs no more (and is
    strictly better on one). Every fleet MoP rises with speed, pax and
    availability, so a dominated vehicle can never make a better fleet.
    """
    keep = []
    for _, group in variants.groupby("kind", sort=False):
        x = np.column_stack([group["speed_kmh"], group["pax"], group["availability"], -group["cost_usd"]])
        at_least = (x[None, :, :] >= x[:, None, :]).all(axis=2)
        better = (x[None, :, :] > x[:, None, :]).any(axis=2)
        dominated = (at_least & better).any(axis=1)
        keep.append(group[~dominated])
    return pd.concat(keep).reset_index(drop=True)


def enumerate_architectures(
    scenario: Scenario,
    n_road: Iterable[int],
    n_bike: Iterable[int],
    variants: pd.DataFrame | None = None,
) -> list[Fleet]:
    """Cross (pruned) road and bike variants with the fleet-size grids (Q14).

    Builds ``Fleet`` objects, which is fine for small grids; use ``tradespace``
    for the full space.
    """
    variants = prune_variants(all_variants(scenario)) if variants is None else variants
    roads = [None] + [row for _, row in variants[variants["kind"] == "road"].iterrows()]
    bikes = [None] + [row for _, row in variants[variants["kind"] == "bike"].iterrows()]
    fleets = []
    for road in roads:
        for bike in bikes:
            for nr in ([0] if road is None else [n for n in n_road if n > 0]):
                for nb in ([0] if bike is None else [n for n in n_bike if n > 0]):
                    if road is None and bike is None:
                        continue
                    fleets.append(Fleet(road=road, n_road=nr, bike=bike, n_bike=nb))
    return fleets


def evaluate_tradespace(fleets: list[Fleet], scenario: Scenario) -> pd.DataFrame:
    """MAU and cost for every architecture (wraps ``model.evaluate_many``)."""
    return evaluate_many(fleets, scenario)


def _part_arrays(rows: pd.DataFrame, n: np.ndarray, trip_km: float, scenario: Scenario) -> dict[str, np.ndarray]:
    """Per-part capacity, departures, availability, cost and travel time; mirrors ``os4.fleet``."""
    speed = rows["speed_kmh"].to_numpy(float)
    cycle = 60.0 * trip_km * (1.0 + scenario.deadhead_fraction) / speed + scenario.dwell_s / 60.0
    per_vehicle = 60.0 / cycle * rows["pax"].to_numpy(float) * rows["load_factor"].to_numpy(float)
    a = rows["availability"].to_numpy(float)
    return {
        "capacity": n * a * per_vehicle,
        "capacity_var": n * a * (1.0 - a) * per_vehicle**2,
        "departures": n * a * 60.0 / cycle,
        "availability": a,
        "cost": n * rows["cost_usd"].to_numpy(float),
        "travel": 60.0 * trip_km / speed,
    }


CHUNK_ROWS = 400_000
PLOT_SAMPLE = 300_000  # points drawn per fleet type in a scatter; fronts are always computed on every row


def tradespace(
    scenario: Scenario,
    n_road: Iterable[int] = N_ROAD,
    n_bike: Iterable[int] = N_BIKE,
    variants: pd.DataFrame | None = None,
    screen: bool = True,
) -> pd.DataFrame:
    """Score every road-only, bike-only and mixed architecture on the fleet-size grids.

    One row per architecture with the same MoPs, SAUs, MAUs and cost as
    ``model.evaluate``, computed with numpy in chunks of ``CHUNK_ROWS``. With
    ``screen``, architectures that miss a Table 1 threshold
    (``model.meets_thresholds``) or a utilization ceiling (``model.meets_bike_ceiling``,
    ``model.meets_car_ceiling``, PLAN.md Q22) are dropped right after capacity and volume are known, before the
    wait and utility calculations. ``df.attrs`` records
    ``screened_out`` and ``threshold_failures`` (counts over the whole grid).
    """
    variants = prune_variants(all_variants(scenario)) if variants is None else variants
    road = variants[variants["kind"] == "road"].reset_index(drop=True)
    bike = variants[variants["kind"] == "bike"].reset_index(drop=True)
    nr = np.array([n for n in n_road if n > 0])
    nb = np.array([n for n in n_bike if n > 0])

    # Index grids: -1 means the part is absent.
    blocks = []
    for r_idx, b_idx in (
        (np.arange(len(road)), np.array([-1])),
        (np.array([-1]), np.arange(len(bike))),
        (np.arange(len(road)), np.arange(len(bike))),
    ):
        if len(r_idx) == 0 or len(b_idx) == 0:
            continue
        nr_opts = nr if r_idx[0] >= 0 else np.array([0])
        nb_opts = nb if b_idx[0] >= 0 else np.array([0])
        blocks.append(np.array(np.meshgrid(r_idx, nr_opts, b_idx, nb_opts, indexing="ij")).reshape(4, -1))
    grid = np.concatenate(blocks, axis=1)

    failures = {"daily_volume": 0, "peak_throughput": 0, "offpeak_throughput": 0, "bike_ceiling": 0,
                "car_ceiling": 0}
    chunks = [_score_chunk(grid[:, i:i + CHUNK_ROWS], road, bike, scenario, screen, failures)
              for i in range(0, grid.shape[1], CHUNK_ROWS)]
    df = pd.concat(chunks, ignore_index=True)
    for col in ("fleet_type", "road_variant", "bike_variant"):
        df[col] = df[col].astype("category")
    df.attrs["screened_out"] = int(grid.shape[1] - len(df))
    df.attrs["grid_size"] = int(grid.shape[1])
    df.attrs["threshold_failures"] = failures
    return df


def _score_chunk(grid: np.ndarray, road: pd.DataFrame, bike: pd.DataFrame, scenario: Scenario, screen: bool,
                 failures: dict[str, int]) -> pd.DataFrame:
    ri, n_r, bi, n_b = grid
    # Placeholder row for an absent part (its n = 0 zeroes it out).
    road_rows = pd.concat([road, road.iloc[[0]] if len(road) else bike.iloc[[0]]], ignore_index=True).iloc[
        np.where(ri >= 0, ri, len(road))]
    bike_rows = pd.concat([bike, bike.iloc[[0]] if len(bike) else road.iloc[[0]]], ignore_index=True).iloc[
        np.where(bi >= 0, bi, len(bike))]
    bike_km = scenario.bike_trip_km if scenario.bike_trip_km is not None else scenario.avg_trip_km
    rp = _part_arrays(road_rows, n_r.astype(float), scenario.avg_trip_km, scenario)
    bp = _part_arrays(bike_rows, n_b.astype(float), bike_km, scenario)

    capacity = rp["capacity"] + bp["capacity"]
    demand = scenario.demand["trips_per_hour"].to_numpy(float)
    volume = np.minimum(demand[None, :], capacity[:, None]).sum(axis=1) * scenario.demand_bin_h
    failures["daily_volume"] += int((volume < scenario.min_daily_volume).sum())
    failures["peak_throughput"] += int((capacity < scenario.min_peak_throughput).sum())
    failures["offpeak_throughput"] += int((capacity < scenario.min_offpeak_throughput).sum())
    with np.errstate(divide="ignore", invalid="ignore"):
        bike_trips = np.where(n_b > 0, volume * bp["capacity"] / capacity / np.maximum(n_b, 1), 0.0)
        road_trips = np.where(n_r > 0, volume * rp["capacity"] / capacity / np.maximum(n_r, 1), 0.0)
    pax = road_rows["pax"].to_numpy(float)
    car_trips = np.where((n_r > 0) & (pax <= scenario.car_max_seats),
                         road_trips / (pax * road_rows["load_factor"].to_numpy(float)), 0.0)
    bike_ok, car_ok = meets_bike_ceiling(bike_trips, scenario), meets_car_ceiling(car_trips, scenario)
    within_ceiling = bike_ok & car_ok
    failures["bike_ceiling"] += int((~bike_ok).sum())
    failures["car_ceiling"] += int((~car_ok).sum())

    # Early exit: drop architectures that break a Table 1 threshold or a utilization ceiling (PLAN.md Q22)
    # before the costlier steps.
    keep = meets_thresholds(capacity, volume, scenario) & within_ceiling
    if not screen:
        keep = np.ones(len(capacity), dtype=bool)
    rp = {k: v[keep] for k, v in rp.items()}
    bp = {k: v[keep] for k, v in bp.items()}
    capacity, volume = capacity[keep], volume[keep]
    bike_trips, road_trips, car_trips = bike_trips[keep], road_trips[keep], car_trips[keep]
    n_r, n_b = n_r[keep], n_b[keep]
    road_rows, bike_rows = road_rows[keep], bike_rows[keep]

    departures = rp["departures"] + bp["departures"]
    peak = np.minimum(capacity, scenario.peak_demand_per_h) if scenario.throughput_measure == "served" else capacity
    with np.errstate(divide="ignore", invalid="ignore"):
        rho = demand[None, :] / capacity[:, None]
        wait_bins = np.where(rho < 1.0, (30.0 / departures[:, None]) / (1.0 - rho), scenario.max_wait_min)
        wait_bins = np.minimum(wait_bins, scenario.max_wait_min)
        wait = np.where(departures > 0, (wait_bins * demand).sum(axis=1) / demand.sum(), scenario.max_wait_min)
        vehicle_avail = np.where(capacity > 0, (rp["availability"] * rp["capacity"]
                                                + bp["availability"] * bp["capacity"]) / capacity, 0.0)
        bike_share = np.where(capacity > 0, bp["capacity"] / capacity, 0.0)
        travel = np.where(capacity > 0, (rp["travel"] * rp["capacity"] + bp["travel"] * bp["capacity"]) / capacity,
                          20.0)
    service = service_probability(capacity, rp["capacity_var"] + bp["capacity_var"], demand) @ demand / demand.sum()

    df = pd.DataFrame({
        "fleet_type": np.select([n_b == 0, n_r == 0], ["road-only", "bike-only"], "mixed"),
        "road_variant": np.where(n_r > 0, road_rows["variant_id"].to_numpy(), None),
        "n_road": n_r,
        "bike_variant": np.where(n_b > 0, bike_rows["variant_id"].to_numpy(), None),
        "n_bike": n_b,
        "fleet_capacity_per_h": capacity,
        "passenger_volume": volume,
        "peak_throughput": peak,
        "wait_time": wait,
        "availability": service,
        "vehicle_availability": vehicle_avail,
        "travel_time": travel,
        "bike_share": bike_share,
        "trips_per_vehicle_day": volume / (n_r + n_b),
        "road_trips_per_vehicle_day": road_trips,
        "bike_trips_per_vehicle_day": bike_trips,
        "car_trips_per_vehicle_day": car_trips,
        "fleet_cost_usd": rp["cost"] + bp["cost"],
    })
    weights = load_weights()
    df["mau"] = sum(weights[a] * sau(a, df[a].to_numpy()) for a in ATTRIBUTES)
    reweight = load_weights("os3a_reweight")
    df["mau_os3a_reweight"] = sum(w * sau(a, df[a].to_numpy()) for a, w in reweight.items())
    return pd.concat([df, requirement_flags(df, scenario)], axis=1)


def pareto_front(df: pd.DataFrame, utility: str = "mau", cost: str = "fleet_cost_usd") -> pd.DataFrame:
    """Rows not dominated in (higher utility, lower cost), sorted by cost."""
    ordered = df.sort_values([cost, utility], ascending=[True, False])
    best = np.maximum.accumulate(ordered[utility].to_numpy())
    # A row is on the front if its utility beats every cheaper row's.
    previous = np.concatenate([[-np.inf], best[:-1]])
    return ordered[ordered[utility].to_numpy() > previous]


def utopia_point(df: pd.DataFrame, utility: str = "mau", cost: str = "fleet_cost_usd") -> tuple[float, float]:
    """(min cost, max utility) over the tradespace."""
    return float(df[cost].min()), float(df[utility].max())


# Reference architecture and anchors (``model.reference_and_anchor_table``): one marker each. The
# reference is ink; anchors are filled with the fourth categorical slot (unused by the fleet types) so
# they stand apart from both the fleet-type colors and the ringed front points.
MARKER_STYLE = ("D", "h", "p", "X", "P")
LABEL_BOX = dict(boxstyle="round,pad=0.2", facecolor=SURFACE, edgecolor="none", alpha=0.85)
KNEE_LABELS = 6  # front points labeled in the knee zoom


def _draw_markers(ax: plt.Axes, markers: pd.DataFrame, utility: str, view, scale: float = 1e6,
                  label_roles: tuple[str, ...] = ("reference", "anchor"), label_right: bool = False,
                  log_x: bool = False) -> None:
    """Reference (filled diamond) and anchors (filled, fourth palette slot), each with its own legend entry.

    ``view`` is ((cost lo, cost hi), (utility lo, utility hi)) in data units. A marker outside it is
    pinned just inside the nearest edge and its label gives the actual MAU and cost. Rows whose role is
    in ``label_roles`` get a short direct label (pinned markers always do).
    """
    (x0, x1), (y0, y1) = view
    inset_x = (lambda v: v * (x1 / x0) ** 0.03) if log_x else (lambda v: v + 0.03 * (x1 - x0))
    n_pinned = 0  # labels of pinned markers are stacked so neighbors on an edge don't overlap
    for (_, row), marker in zip(markers.iterrows(), MARKER_STYLE):
        filled = row["role"] == "reference"
        note = "" if row["meets_thresholds"] else ", misses Table 1"
        cost = min(max(row["fleet_cost_usd"], inset_x(x0)), x1)
        util = min(max(row[utility], y0 + 0.04 * (y1 - y0)), y1)
        pinned = (cost, util) != (row["fleet_cost_usd"], row[utility])
        xy = (cost / scale, util)
        ax.scatter(*xy, marker=marker, s=130 if filled else 110,
                   facecolor=INK if filled else SERIES[3], edgecolor=INK, linewidth=1.5, zorder=8,
                   label=f"{'' if filled else 'Anchor: '}{row['architecture']}, {_describe(row)}{note}")
        if row["role"] in label_roles or pinned:
            text = row["architecture"].split(" (")[0].split(":")[0]
            lift = 0
            if pinned:
                text += f"\nMAU {row[utility]:.2f}, ${row['fleet_cost_usd'] / 1e3:,.0f}k (off view)"
                lift, n_pinned = 32 * n_pinned, n_pinned + 1
            ax.annotate(text, xy, xytext=(11, lift) if label_right else (0, 12 + lift), textcoords="offset points",
                        ha="left" if label_right else "center", va="center" if label_right else "bottom",
                        fontsize=8.5, color=INK, zorder=8, bbox=LABEL_BOX)


def _shrink_marker_handles(legend) -> None:
    """Undo ``markerscale`` for the reference/anchor entries (it is there to enlarge the tiny scatter dots)."""
    for handle, text in zip(legend.legend_handles, legend.get_texts()):
        if text.get_text().startswith(("Reference", "Anchor")):
            handle.set_sizes([70])


def plot_tradespace(df: pd.DataFrame, path: Path, highlight: pd.DataFrame | None = None,
                    utility: str = "mau", title: str = "Tradespace: utility vs. fleet cost",
                    markers: pd.DataFrame | None = None) -> Path:
    """Scatter utility vs. cost with the Pareto front and utopia point; save to ``path``.

    ``highlight`` rows (the Task 2 table) are circled and labeled; ``markers`` (reference and anchors)
    get their own symbols and legend entries.
    """
    fig, ax = plt.subplots(figsize=(10, 7.4), facecolor=SURFACE)
    _style(ax)
    # Draw the (huge) mixed set first so the rarer road-only and bike-only points stay visible on top.
    for fleet_type, size, alpha in (("mixed", 5, 0.25), ("road-only", 14, 0.7), ("bike-only", 22, 0.85)):
        part = df[df["fleet_type"] == fleet_type]
        color, marker = TYPE_STYLE[fleet_type]
        drawn = part.sample(PLOT_SAMPLE, random_state=0) if len(part) > PLOT_SAMPLE else part
        ax.scatter(drawn["fleet_cost_usd"] / 1e6, drawn[utility], s=size, marker=marker, color=color,
                   alpha=alpha, linewidths=0, rasterized=True, label=f"{fleet_type} ({len(part):,})")
    front = pareto_front(df, utility)
    ax.step(front["fleet_cost_usd"] / 1e6, front[utility], where="post", color=INK, linewidth=2, alpha=0.5,
            label=f"Pareto front ({len(front)} architectures)", zorder=4)
    cost0, util0 = utopia_point(df, utility)
    ax.scatter([cost0 / 1e6], [util0], marker="*", s=220, color=INK, edgecolor=SURFACE, linewidth=1.5, zorder=6)
    ax.annotate("utopia point", (cost0 / 1e6, util0), xytext=(8, -14), textcoords="offset points",
                fontsize=9, color=INK)
    if highlight is not None:
        # Leader lines to label slots: the cheapest point goes to the empty area left of the front,
        # the rest to a column at the right, ordered by utility so the lines don't cross.
        cheapest = highlight["fleet_cost_usd"].idxmin()
        right = highlight.drop(index=cheapest).sort_values(utility, ascending=False)
        top = highlight[utility].min() - 0.12  # below the cluster, whichever MAU is plotted
        left_x = df["fleet_cost_usd"].min() / 1e6 * 0.85  # just inside the left axis limit
        slots = [(cheapest, (left_x, highlight.loc[cheapest, utility] - 0.07))]
        slots += [(i, (1.6, top - 0.055 * k)) for k, i in enumerate(right.index)]
        for i, text_xy in slots:
            row = highlight.loc[i]
            xy = (row["fleet_cost_usd"] / 1e6, row[utility])
            ax.scatter(*xy, s=90, facecolor="none", edgecolor=INK, linewidth=2, zorder=7)
            ax.annotate(row["architecture"], xy, xytext=text_xy, textcoords="data",
                        fontsize=8.5, color=INK, zorder=7, va="center",
                        arrowprops=dict(arrowstyle="-", color=INK_2, linewidth=0.8, shrinkA=2, shrinkB=6))
    # Axis ranges cover the tradespace and the markers that meet Table 1; the rest are pinned to an edge.
    shown = df if markers is None else pd.concat([df[["fleet_cost_usd", utility]],
                                                  markers.loc[markers["meets_thresholds"], ["fleet_cost_usd", utility]]])
    view = ((shown["fleet_cost_usd"].min() * 0.8, shown["fleet_cost_usd"].max() * 1.2),
            (max(0, shown[utility].min() - 0.05), 1.02))
    if markers is not None:
        _draw_markers(ax, markers, utility, view, label_roles=("anchor",), label_right=True, log_x=True)
    _cost_axis(ax)
    ax.set_xlabel("fleet cost ($M, vehicle capital cost, log scale)", fontsize=9, color=INK_2)
    ax.set_ylabel("multi-attribute utility", fontsize=9, color=INK_2)
    ax.set_ylim(*view[1])
    ax.set_xlim(view[0][0] / 1e6, view[0][1] / 1e6)
    legend = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=2, frameon=False, fontsize=8.5,
                       markerscale=2.5)
    for handle in legend.legend_handles:
        handle.set_alpha(1)
    _shrink_marker_handles(legend)
    ax.set_title(title, loc="left", fontsize=13, color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


KNEE_DEPTH = 0.08  # the knee window shows utility from (best MAU - KNEE_DEPTH) up
KNEE_PLATEAU = 0.002  # ... and cost up to where the front comes within this of the best MAU


def knee_window(df: pd.DataFrame, utility: str = "mau",
                markers: pd.DataFrame | None = None) -> tuple[tuple[float, float], tuple[float, float]]:
    """(cost range, utility range) of the knee: from the cheapest feasible point to where the front plateaus.

    The x range also covers the reference and the anchors that meet Table 1, so they can be read against
    the front; anchors that miss it are pinned to the window's edge instead of stretching it.
    """
    front = pareto_front(df, utility)
    best = front[utility].max()
    plateau = front.loc[front[utility] >= best - KNEE_PLATEAU, "fleet_cost_usd"].iloc[0]
    costs = [df["fleet_cost_usd"].min(), plateau]
    if markers is not None:
        costs += list(markers.loc[markers["meets_thresholds"], "fleet_cost_usd"])
    lo, hi = min(costs), max(costs)
    pad = 0.08 * (hi - lo)
    return (lo - pad, hi + pad), (best - KNEE_DEPTH, best + 0.25 * KNEE_DEPTH)


def plot_knee(df: pd.DataFrame, path: Path, markers: pd.DataFrame | None = None, utility: str = "mau",
              title: str = "Tradespace knee") -> Path:
    """Zoom on the knee of the front on linear axes, with the reference and anchors.

    Front points are labeled with their fleet; markers outside the window are pinned to its edge
    with their actual utility and cost in the label.
    """
    (x0, x1), (y0, y1) = knee_window(df, utility, markers)
    fig, ax = plt.subplots(figsize=(10, 7), facecolor=SURFACE)
    _style(ax)
    window = df[df["fleet_cost_usd"].between(x0, x1) & df[utility].between(y0, y1)]
    for fleet_type, size, alpha in (("mixed", 8, 0.3), ("road-only", 20, 0.7), ("bike-only", 26, 0.85)):
        part = window[window["fleet_type"] == fleet_type]
        color, marker = TYPE_STYLE[fleet_type]
        drawn = part.sample(PLOT_SAMPLE, random_state=0) if len(part) > PLOT_SAMPLE else part
        ax.scatter(drawn["fleet_cost_usd"] / 1e3, drawn[utility], s=size, marker=marker, color=color,
                   alpha=alpha, linewidths=0, rasterized=True, label=f"{fleet_type} ({len(part):,} in view)")
    front = pareto_front(df, utility)
    ax.step(front["fleet_cost_usd"] / 1e3, front[utility], where="post", color=INK, linewidth=2, alpha=0.5,
            label="Pareto front", zorder=4)
    shown = front[front["fleet_cost_usd"].between(x0, x1) & front[utility].between(y0, y1)]
    ax.scatter(shown["fleet_cost_usd"] / 1e3, shown[utility], s=40, facecolor="none", edgecolor=INK,
               linewidth=1.2, zorder=5)
    # Label up to KNEE_LABELS front points: the first to reach each of evenly spaced utility levels above
    # the window's lowest front point (its label would sit among the pinned anchors). Points in the right
    # 40% of the window get their label on the left so it stays inside the axes.
    levels = np.linspace(shown[utility].min(), shown[utility].max(), KNEE_LABELS + 1)[1:]
    picks = sorted({int(np.argmax(shown[utility].to_numpy() >= level)) for level in levels})
    for _, row in shown.iloc[picks].iterrows():
        right = row["fleet_cost_usd"] > x0 + 0.6 * (x1 - x0)
        ax.annotate(_describe(row), (row["fleet_cost_usd"] / 1e3, row[utility]), xytext=(-8 if right else 8, -8),
                    textcoords="offset points", ha="right" if right else "left", va="top", fontsize=7.5,
                    color=INK_2, zorder=6, bbox=LABEL_BOX)
    cost0, util0 = utopia_point(df, utility)
    ax.scatter([cost0 / 1e3], [util0], marker="*", s=220, color=INK, edgecolor=SURFACE, linewidth=1.5, zorder=6,
               label="utopia point")
    if markers is not None:
        _draw_markers(ax, markers, utility, ((x0, x1), (y0, y1)), scale=1e3)
    ax.set_xlim(x0 / 1e3, x1 / 1e3)
    ax.set_ylim(y0, y1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}k"))
    ax.set_xlabel("fleet cost ($k, vehicle capital cost, linear scale)", fontsize=9, color=INK_2)
    ax.set_ylabel("multi-attribute utility", fontsize=9, color=INK_2)
    legend = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=2, frameon=False, fontsize=8)
    for handle in legend.legend_handles:
        handle.set_alpha(1)
    _shrink_marker_handles(legend)
    ax.set_title(title, loc="left", fontsize=13, color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _requirement_rows(df: pd.DataFrame, scenario: Scenario) -> pd.DataFrame:
    """How many architectures fail each Table 1 requirement and the utilization ceilings (PLAN.md Q22).

    Thresholds and the ceiling are counted over the whole grid during screening (``df.attrs``); the desired goals and
    the availability benchmark are counted over the architectures that pass the thresholds.
    """
    grid, failures, n = df.attrs["grid_size"], df.attrs["threshold_failures"], len(df)
    rows = [
        ("daily volume", f">= {scenario.min_daily_volume:,.0f} trips/day", "threshold", failures["daily_volume"], grid),
        ("peak throughput", f">= {scenario.min_peak_throughput:g} trips/h", "threshold",
         failures["peak_throughput"], grid),
        ("off-peak throughput", f">= {scenario.min_offpeak_throughput:g} trips/h", "threshold",
         failures["offpeak_throughput"], grid),
        *([("riders per bike per day", f"<= {scenario.max_bike_trips_per_day:g}", "realism gate (PLAN.md Q22)",
            failures["bike_ceiling"], grid)] if scenario.max_bike_trips_per_day is not None else []),
        *([(f"rides per car (1–{scenario.car_max_seats} seats) per day", f"<= {scenario.max_car_trips_per_day:g}",
            "realism gate (PLAN.md Q22)", failures["car_ceiling"], grid)]
          if scenario.max_car_trips_per_day is not None else []),
        ("wait in boundary", f"<= {scenario.goal_wait_min:g} min", "desired", int((~df["meets_wait_goal"]).sum()), n),
        ("travel time, average Kendall trip", f"<= {scenario.goal_travel_min:g} min", "desired",
         int((~df["meets_travel_goal"]).sum()), n),
        ("service availability", f">= {scenario.benchmark_availability:g}", "benchmark",
         int((~df["meets_availability_benchmark"]).sum()), n),
    ]
    return pd.DataFrame([(name, target, kind, f"{fail:,} of {total:,}", f"{fail / total:.1%}")
                         for name, target, kind, fail, total in rows],
                        columns=["requirement", "target", "type", "architectures failing", "share"])


def _bike_only_floor(scenario: Scenario) -> str:
    """Why the smallest bike-only fleets never reach the map: the best fleet at the grid's smallest size against
    each screen, and the smallest size that clears the thresholds and the bike ceiling (PLAN.md Q22)."""
    if scenario.max_bike_trips_per_day is None:
        return ""
    variants = prune_variants(all_variants(scenario))
    df = tradespace(scenario, n_road=(), variants=variants[variants["kind"] == "bike"], screen=False)
    df = df.assign(thresholds=meets_thresholds(df["fleet_capacity_per_h"], df["passenger_volume"], scenario),
                   ceiling=meets_bike_ceiling(df["bike_trips_per_vehicle_day"], scenario))
    n0 = int(df["n_bike"].min())
    best = df[df["n_bike"] == n0].sort_values("fleet_capacity_per_h").iloc[-1]
    n_thresholds = int(df.loc[df["thresholds"], "n_bike"].min())
    n_both = int(df.loc[df["thresholds"] & df["ceiling"], "n_bike"].min())
    table = pd.DataFrame([
        ("daily volume", f">= {scenario.min_daily_volume:,.0f} trips/day", f"{best['passenger_volume']:,.0f}"),
        ("peak throughput", f">= {scenario.min_peak_throughput:g} trips/h", f"{best['fleet_capacity_per_h']:.0f}"),
        ("off-peak throughput", f">= {scenario.min_offpeak_throughput:g} trips/h",
         f"{best['fleet_capacity_per_h']:.0f}"),
        ("riders per bike per day", f"<= {scenario.max_bike_trips_per_day:g}",
         f"{best['bike_trips_per_vehicle_day']:.0f}"),
    ], columns=["requirement", "target", f"{n0} × {best['bike_variant']}"])
    return (
        "### Why bike-only fleets start at "
        f"{n_both} bikes\n\n"
        f"The bike grid starts at {n0}, but no bike-only fleet that small is feasible, so none appear on the map or "
        f"in the explorer (screened fleets are not exported). The highest-capacity {n0}-bike fleet fails every "
        "screen:\n\n"
        f"{_md_table(table)}\n"
        f"Bike-only fleets first meet the Table 1 thresholds at {n_thresholds} bikes, but the ceiling of "
        f"{scenario.max_bike_trips_per_day:g} riders per bike per day (PLAN.md Q22) binds until {n_both}, the "
        f"smallest bike-only fleet in the tradespace. Small bike counts ({n0}+) appear only in mixed fleets, "
        "where the road vehicles carry most of the demand.\n\n"
    )


LOAD_FACTORS = (0.25, 0.5, 0.75, 1.0)
LOAD_FACTOR_COLORS = ("#86b6ef", "#3987e5", "#1c5cab", "#0d366b")  # ordinal ramp steps 250/400/550/700


def load_factor_fronts(scenario: Scenario, load_factors=LOAD_FACTORS) -> dict[float, pd.DataFrame]:
    """Pareto front of the full design space at each road-vehicle load factor (Appendix B uses 0.75).

    Bikes keep their per-seat riders (``Scenario.bike_load_factors``, PLAN.md Q16): an on-demand bike
    always carries its rider, so its occupancy isn't the open question this sweep explores.
    """
    fronts = {}
    for lf in load_factors:
        df = tradespace(replace(scenario, load_factor=lf))
        front = pareto_front(df).copy()
        front.attrs = {"architectures": len(df), "screened_out": df.attrs["screened_out"]}
        fronts[lf] = front
        del df
    return fronts


def plot_load_factor_fronts(fronts: dict[float, pd.DataFrame], path: Path, baseline: float = 0.75) -> Path:
    """One chart: the Pareto front at each load factor, points shaped by fleet type."""
    fig, ax = plt.subplots(figsize=(10, 6), facecolor=SURFACE)
    _style(ax)
    for (lf, front), color in zip(fronts.items(), LOAD_FACTOR_COLORS):
        x, y = front["fleet_cost_usd"] / 1e6, front["mau"]
        ax.step(x, y, where="post", color=color, linewidth=2.6 if lf == baseline else 1.6,
                label=f"{lf:.0%} full{' (Appendix B)' if lf == baseline else ''}: {len(front)} on front", zorder=3)
        for fleet_type in FLEET_TYPES:
            part = front[front["fleet_type"] == fleet_type]
            ax.scatter(part["fleet_cost_usd"] / 1e6, part["mau"], s=22, marker=TYPE_STYLE[fleet_type][1],
                       color=color, edgecolor=SURFACE, linewidth=0.6, zorder=4)
    handles, labels = ax.get_legend_handles_labels()
    handles += [plt.Line2D([], [], marker=TYPE_STYLE[t][1], linestyle="", color=INK_2, label=t) for t in FLEET_TYPES]
    legend = ax.legend(handles=handles, loc="lower right", frameon=True, fontsize=8.5)
    legend.get_frame().set_edgecolor(GRID)
    _cost_axis(ax)
    ax.set_xlabel("fleet cost ($M, vehicle capital cost, log scale)", fontsize=9, color=INK_2)
    ax.set_ylabel("multi-attribute utility", fontsize=9, color=INK_2)
    ax.set_title("Pareto front by road-vehicle load factor (share of seats filled per trip)", loc="left", fontsize=13,
                 color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


# Ordinal blue ramp (palette steps 250-700): light = small fleet, dark = large fleet.
FLEET_SIZE_RAMP = ("#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95",
                   "#104281", "#0d366b")


def plot_fleet_size(df: pd.DataFrame, kind: str, path: Path, utility: str = "mau", subtitle: str = "") -> Path:
    """Small multiples, one panel per vehicle type: that type's single-type fleets colored by fleet size.

    ``kind`` "road" gives one panel per chassis (road-only fleets); "bike" one per frame (bike-only
    fleets, fixed battery as circles, removable as triangles). Every panel shows the whole tradespace
    in gray and the Pareto front, so you can follow a vehicle type up its fleet-size range and see
    where it meets the front.
    """
    fleet_type, n_col, var_col = (("road-only", "n_road", "road_variant") if kind == "road"
                                  else ("bike-only", "n_bike", "bike_variant"))
    own = df[df["fleet_type"] == fleet_type].copy()
    own["type"] = own[var_col].str.split("-").str[0]
    own["removable"] = own[var_col].str.contains("-S")
    types = sorted(own["type"].unique(), key=lambda t: (t[0], int(t[1:])))
    sizes = sorted(own[n_col].unique())
    ramp = matplotlib.colors.LinearSegmentedColormap.from_list("fleet", FLEET_SIZE_RAMP)
    norm = matplotlib.colors.BoundaryNorm(np.append(sizes, sizes[-1] + (sizes[-1] - sizes[-2])) - 0.5 * (sizes[1] - sizes[0]),
                                          ramp.N)
    front = pareto_front(df, utility)
    background = df.sample(min(len(df), 40_000), random_state=0)

    cols = 4 if len(types) > 3 else len(types)
    rows = int(np.ceil(len(types) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(3.4 * cols + 1.2, 3.1 * rows + 1.4), facecolor=SURFACE,
                             sharex=True, sharey=True, squeeze=False, layout="constrained")
    for ax, t in zip(axes.flat, types):
        _style(ax)
        ax.scatter(background["fleet_cost_usd"] / 1e6, background[utility], s=2, color=GRID, linewidths=0,
                   rasterized=True)
        ax.step(front["fleet_cost_usd"] / 1e6, front[utility], where="post", color=INK, linewidth=1.4, alpha=0.5,
                zorder=4)
        part = own[own["type"] == t].sort_values(n_col)
        for removable, marker in ((False, "o"), (True, "^")):
            sub = part[part["removable"] == removable]
            ax.scatter(sub["fleet_cost_usd"] / 1e6, sub[utility], c=sub[n_col], cmap=ramp, norm=norm, s=16,
                       marker=marker, linewidths=0, zorder=5, rasterized=True)
        on_front = part.index.intersection(front.index)
        ax.scatter(part.loc[on_front, "fleet_cost_usd"] / 1e6, part.loc[on_front, utility], s=60,
                   facecolor="none", edgecolor=INK, linewidth=1.3, zorder=6)
        ax.set_title(f"{t}: {len(on_front)} on front", loc="left", fontsize=10, color=INK, fontweight="bold")
        _cost_axis(ax)
    for ax in axes.flat[len(types):]:
        ax.set_visible(False)
    for ax in axes[-1]:
        ax.set_xlabel("fleet cost (log)", fontsize=8.5, color=INK_2)
    for ax in axes[:, 0]:
        ax.set_ylabel("MAU", fontsize=8.5, color=INK_2)
    ax0 = axes.flat[0]
    ax0.set_ylim(max(0, df[utility].min() - 0.03), 1.0)
    bar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=ramp), ax=axes, shrink=0.8,
                       ticks=sizes[:: max(1, len(sizes) // 6)])
    bar.set_label(f"fleet size ({'road vehicles' if kind == 'road' else 'bikes'})", fontsize=9, color=INK_2)
    bar.outline.set_visible(False)
    handles = [plt.Line2D([], [], color=INK, linewidth=1.4, alpha=0.5, label="Pareto front (all fleets)"),
               plt.Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor="none",
                          markeredgecolor=INK, label="this type on the front")]
    if kind == "bike":
        handles.append(plt.Line2D([], [], marker="o", linestyle="", color=INK_2, label="fixed battery"))
        if own["removable"].any():
            handles.append(plt.Line2D([], [], marker="^", linestyle="", color=INK_2, label="removable battery"))
    fig.legend(handles=handles, loc="outside lower center", ncol=len(handles), frameon=False, fontsize=8.5)
    label = "road chassis (road-only fleets)" if kind == "road" else "e-bike frame (bike-only fleets)"
    fig.suptitle(f"Fleet size along the tradespace, by {label}" + (f"\n{subtitle}" if subtitle else ""), x=0.01,
                 ha="left", fontsize=12, color=INK, fontweight="bold")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _cost_axis(ax: plt.Axes) -> None:
    """Log cost axis in $M with fixed 1-3-10 ticks and no minor labels."""
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(matplotlib.ticker.FixedLocator([0.1, 0.3, 1, 3, 10, 30]))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:g}M"))
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())


def _front_table(front: pd.DataFrame) -> pd.DataFrame:
    cols = ["fleet_type", "road_variant", "n_road", "bike_variant", "n_bike", "fleet_capacity_per_h",
            "wait_time", "availability", "mau", "fleet_cost_usd"]
    fmt = front[cols].astype({"fleet_type": str, "road_variant": object, "bike_variant": object})
    fmt["fleet_cost_usd"] = fmt["fleet_cost_usd"].map(lambda c: f"${c:,.0f}")
    return fmt.fillna("-").round(3)


def _type_rows(df: pd.DataFrame, front: pd.DataFrame, front_rw: pd.DataFrame) -> pd.DataFrame:
    counts = df["fleet_type"].value_counts()
    on_front, on_front_rw = front["fleet_type"].value_counts(), front_rw["fleet_type"].value_counts()
    return pd.DataFrame({
        "fleet type": FLEET_TYPES,
        "architectures": [f"{counts.get(t, 0):,}" for t in FLEET_TYPES],
        "on Pareto front": [on_front.get(t, 0) for t in FLEET_TYPES],
        "best MAU": [round(df.loc[df["fleet_type"] == t, "mau"].max(), 3) for t in FLEET_TYPES],
        "on os3a_reweight front": [on_front_rw.get(t, 0) for t in FLEET_TYPES],
    })


def write_task3(scenario: Scenario, out_dir: Path = OUTPUT_DIR) -> list[Path]:
    """Write the Task 3 report: the tradespace with fixed e-bike batteries (Appendix B as given) and
    with the removable-battery option, each with its scatter, fleet-size charts and Pareto front."""
    media = media_dir(out_dir)
    highlight = architecture_table(scenario)
    markers = reference_and_anchor_table(scenario)
    cases = {
        "fixed": ("Fixed e-bike batteries (Appendix B as given)", replace(scenario, bike_spare_options=(0.0,))),
        "removable": ("With removable e-bike batteries (team proposal)", scenario),
    }
    paths, sections, summary, frames = [], [], [], {}
    for key, (title, case) in cases.items():
        df = tradespace(case)
        frames[key] = df
        front = pareto_front(df)
        front_rw = pareto_front(df, "mau_os3a_reweight")
        cost0, util0 = utopia_point(df)
        front_path = media / f"task3_pareto_front_{key}.csv"
        front.round(4).to_csv(front_path, index=False)
        png = plot_tradespace(df, media / f"task3_tradespace_{key}.png", highlight,
                              title=f"Tradespace: {title}", markers=markers)
        knee_png = plot_knee(df, media / f"task3_knee_{key}.png", markers, title=f"Knee of the front: {title}")
        png_rw = plot_tradespace(df, media / f"task3_tradespace_{key}_reweight.png", highlight,
                                 utility="mau_os3a_reweight", title=f"OS3A reweight MAU: {title}", markers=markers)
        road_png = plot_fleet_size(df, "road", media / f"task3_fleet_size_road_{key}.png", subtitle=title)
        bike_png = plot_fleet_size(df, "bike", media / f"task3_fleet_size_bike_{key}.png", subtitle=title)
        paths += [front_path, png, knee_png, png_rw, road_png, bike_png]
        knee = front[front["mau"] >= 0.94].iloc[0]
        summary.append({
            "case": title,
            "architectures": f"{len(df):,}",
            "screened out": f"{df.attrs['screened_out']:,}",
            "front (road / bike / mixed)": " / ".join(str((front["fleet_type"] == t).sum())
                                                      for t in ("road-only", "bike-only", "mixed")),
            "cheapest feasible": f"${cost0:,.0f}",
            "first MAU >= 0.94": f"{_describe(knee)}: {knee['mau']:.3f} at ${knee['fleet_cost_usd']:,.0f}",
        })
        sections.append(
            f"## {title}\n\n"
            f"![Tradespace]({media_link(png)})\n\n"
            f"Utopia point: ${cost0:,.0f} and MAU {util0:.3f}. Circled points are the five Task 2 architectures; "
            "the filled diamond is the reference architecture and the yellow-filled symbols are the anchors.\n\n"
            f"{_md_table(_type_rows(df, front, front_rw))}\n"
            "### Knee of the front\n\n"
            "Linear axes, from the cheapest feasible fleet to where the front comes within "
            f"{KNEE_PLATEAU} of its best MAU. Labeled front points each add a visible step in utility; "
            "anchors outside the window are pinned to its edge, with their actual values in the label.\n\n"
            f"![Knee of the front]({media_link(knee_png)})\n\n"
            "### Reference architecture and anchors against the front\n\n"
            f"{_md_table(front_comparison(df, markers))}\n"
            "### Fleet size by vehicle type\n\n"
            "Each panel follows one vehicle type up its fleet-size range (light = few vehicles, dark = many) "
            "against the whole tradespace (gray) and this case's Pareto front; ringed points are on the front.\n\n"
            f"![Fleet size by road chassis]({media_link(road_png)})\n\n"
            f"![Fleet size by e-bike frame]({media_link(bike_png)})\n\n"
            f"### Pareto front ({len(front)} architectures)\n\n"
            f"{_md_table(_front_table(front))}\n"
            "### With the team's OS3A weights\n\n"
            "Scored with the `os3a_reweight` weights (volume 0.10 / peak 0.25 / wait 0.35 / availability 0.30, "
            f"PLAN.md Q10): the same four attributes, weighted by our OS3A stakeholder priorities; "
            f"the front has {len(front_rw)} architectures.\n\n"
            f"![Tradespace with the OS3A reweight MAU]({media_link(png_rw)})\n\n"
        )
    requirements = _requirement_rows(frames["removable"], scenario)
    plateau = _mau_plateau(frames["removable"], scenario)
    frames.clear()
    fronts = load_factor_fronts(scenario)
    lf_png = plot_load_factor_fronts(fronts, media / "task3_load_factor_fronts.png", scenario.load_factor)
    lf_rows = pd.DataFrame([{
        "load factor": f"{lf:.0%}",
        "architectures meeting thresholds": f"{f.attrs['architectures']:,}",
        "front (road / bike / mixed)": " / ".join(str((f["fleet_type"] == t).sum())
                                                  for t in ("road-only", "bike-only", "mixed")),
        "cheapest on front": f"{_describe(f.iloc[0])}: ${f.iloc[0]['fleet_cost_usd']:,.0f}",
        "best MAU": round(f["mau"].max(), 3),
    } for lf, f in fronts.items()])
    paths.append(lf_png)
    md_path = out_dir / "task3_tradespace.md"
    md_path.write_text(
        "# Task 3: Tradespace\n\n"
        f"Generated by `python -m os4` for the scenario *{scenario.name}*. "
        f"Fleet sizes (PLAN.md Q14), steps widening as fleets grow: road {_segments_text(ROAD_SEGMENTS)}; "
        f"bikes {_segments_text(BIKE_SEGMENTS)}. "
        "Dominated vehicle variants are pruned first (`prune_variants`), so every road vehicle in the space is A3. "
        "Peak throughput is the demand actually served (Q17) and costs are vehicle capital only (Q21).\n\n"
        "The tradespace is run twice: with **fixed e-bike batteries** (Appendix B as given), and with the team's "
        "**removable-battery** option, where a bike swaps packs in "
        f"{scenario.bike_swap_h * 60:g} min and the fleet buys "
        f"{', '.join(f'{k:g}' for k in scenario.bike_spare_options if k > 0)} spare packs per bike (each spare adds "
        "its battery and a charger slot to the bike's cost). Pruning keeps only the spare counts worth buying.\n\n"
        f"{_md_table(pd.DataFrame(summary))}\n"
        f"{plateau}"
        "## Reference architecture and anchors\n\n"
        "The **reference** (PLAN.md Q26) was chosen from design reasoning before reading the "
        "tradespace: C4 8-seat shuttles (MIT P&T's \"small on-demand EV shuttles from a central hub\"), A3 (the "
        "minimum inside the boundary), M2 (smallest motor at the speed cap), G3 (fastest charger) and P2 (about a "
        "service day of range), sized by load management at the peak, f >= P / (X * C_car) with X = 0.90. "
        "The **anchors** (Q23) are today's services run through the same model (`data/anchors.csv`): the "
        "Appendix C chassis closest to the real vehicle (C8, 30 seats, for buses; C6, 16 seats, for the 14-seat "
        "MIT shuttles) at its cheapest spec that reaches the speed cap and the 0.75 availability benchmark. A "
        "headway anchor gets the fewest vehicles whose model headway is at most the published one; the MIT "
        "shuttles use their known fleet of 5.\n\n"
        f"{_md_table(_marker_table(markers))}\n"
        f"{_reference_vs_shuttles(markers, scenario)}"
        "## Requirements (Table 1)\n\n"
        "Thresholds screen architectures out before scoring; desired goals and the availability benchmark are "
        "flags only. Counts are over the whole grid (removable-battery case) before screening.\n\n"
        f"{_md_table(requirements)}\n"
        "Travel time is the average Kendall trip (1.75 km road, 1.6 km bike; team decision): 5.0 min at the "
        f"{scenario.speed_limit_kmh:g} km/h road cap. The longest link (Lechmere–Central, "
        f"{max(scenario.node_distances_km.values()):g} km) would take ≥ 9.4 min and is left for later. "
        "Availability is *service* availability (Q19): the chance the vehicles in service can carry the hour's "
        "demand, so spare vehicles raise it.\n\n"
        f"{_bike_only_floor(scenario)}"
        "## Load-factor sensitivity\n\n"
        "Appendix B assumes trips average 75% full; the model keeps 0.75 as the baseline for road vehicles. "
        "E-bikes use riders per trip by seats instead (PLAN.md Q16): a 1-seat bike carries its 1 rider, a 2-seat "
        "bike 2 riders every 3 trips (4/3 riders, 67% of seats), so this sweep varies road vehicles only. The "
        "same design space scored at 25%, 50%, 75% and 100% (the removable-battery case, which also contains "
        "every fixed-battery option):\n\n"
        f"![Pareto front by load factor]({media_link(lf_png)})\n\n"
        f"{_md_table(lf_rows)}\n"
        + "".join(sections)
    )
    return paths + [md_path]


def _mau_plateau(df: pd.DataFrame, scenario: Scenario) -> str:
    """Why the Appendix A front levels off below 1: the best SAU any architecture reaches, attribute by
    attribute. Throughput and volume count demand served (Q17), so demand caps them."""
    weights = load_weights()
    best = {a: float(sau(a, df[a].to_numpy()).max()) for a in weights}
    rows = pd.DataFrame([{
        "attribute": a,
        "weight": w,
        "best in tradespace": _fmt_best(df[a].min() if a == "wait_time" else df[a].max()),
        "best SAU": round(best[a], 3),
        "weight × SAU": round(w * best[a], 4),
    } for a, w in weights.items()])
    ceiling = sum(w * best[a] for a, w in weights.items())
    ceiling_rw = sum(w * best[a] for a, w in load_weights("os3a_reweight").items())
    return (
        "### Why the front levels off below 1\n\n"
        "Demand caps two of the four Appendix A attributes. Peak throughput counts the demand actually served "
        f"(Q17), so no fleet scores past the {scenario.peak_demand_per_h:g} trips/h peak, and passenger volume "
        f"stops at the {scenario.demand['trips_per_hour'].sum() * scenario.demand_bin_h:,.0f} trips/day of "
        "Appendix B demand. Only wait and service availability keep improving as vehicles are added, and both "
        "approach their best SAU of 1. The MAU ceiling is the weighted sum of each attribute's best SAU:\n\n"
        f"{_md_table(rows)}\n"
        f"Ceiling {ceiling:.3f}; the best front MAU is {df['mau'].max():.4f}. Once a fleet meets demand, extra "
        "vehicles only buy seconds of wait, so the front runs flat and the cheapest fleet that meets demand is "
        "the practical choice. The `os3a_reweight` weights score the same four attributes, so they level off "
        f"the same way (ceiling {ceiling_rw:.3f}). Past that point extra vehicles only add cost, and cost is "
        "the other axis of the tradespace, so they fall off the front without a separate fleet-size "
        "attribute.\n\n"
    )


def _fmt_best(x: float) -> str:
    return f"{x:,.0f}" if x >= 10 else f"{x:.3f}"


def _reference_vs_shuttles(markers: pd.DataFrame, scenario: Scenario) -> str:
    """The reference (PLAN.md Q26) beside the MIT-shuttle anchor (Q23): why the anchor scores higher for less."""
    shuttles = load("anchors").set_index("id").loc["mit_shuttle", "name"]
    ref = markers[markers["role"] == "reference"].iloc[0]
    mit = markers[markers["architecture"] == shuttles].iloc[0]
    rv, mv = get_variant(ref["road_variant"], scenario), get_variant(mit["road_variant"], scenario)
    parts = {t: load(f"road_{t}").set_index("id")["cost_usd"] for t in ("chassis", "battery", "motor")}
    delta = {t: parts[t][mv[t]] - parts[t][rv[t]] for t in parts}
    rows = [
        ("represents", "our design, chosen before reading the tradespace", "today's service, run through the model"),
        ("vehicle", f"{rv['variant_id']} ({rv['pax']} seats)", f"{mv['variant_id']} ({mv['pax']} seats)"),
        ("fleet size from", "load management at the peak, X = 0.90", "the known fleet [[15]](../docs/references.md#ref-15)"),
        ("components from", "design reasoning (all-day pack, fastest charger)",
         "cheapest spec at the speed cap and the 0.75 benchmark"),
        ("vehicles × seats", f"{int(ref['n_road'])} × {rv['pax']} = {int(ref['n_road']) * rv['pax']}",
         f"{int(mit['n_road'])} × {mv['pax']} = {int(mit['n_road']) * mv['pax']}"),
        ("range", f"{rv['range_km']:.0f} km", f"{mv['range_km']:.0f} km"),
        ("cost per vehicle", f"${rv['cost_usd']:,.0f}", f"${mv['cost_usd']:,.0f}"),
        ("fleet cost", f"${ref['fleet_cost_usd']:,.0f}", f"${mit['fleet_cost_usd']:,.0f}"),
        ("capacity (trips/h)", f"{ref['fleet_capacity_per_h']:.0f}", f"{mit['fleet_capacity_per_h']:.0f}"),
        ("wait (min)", f"{ref['wait_time']:.1f}", f"{mit['wait_time']:.1f}"),
        ("service availability", f"{ref['availability']:.3f}", f"{mit['availability']:.3f}"),
        ("MAU (Appendix A / os3a_reweight)", f"{ref['mau']:.3f} / {ref['mau_os3a_reweight']:.3f}",
         f"{mit['mau']:.3f} / {mit['mau_os3a_reweight']:.3f}"),
    ]
    table = pd.DataFrame(rows, columns=["", "reference", shuttles])
    return (
        "### Reference vs. MIT shuttles\n\n"
        "Both are small road-shuttle fleets, but they answer different questions: the reference is our design, "
        "sized to the demand; the anchor is the service MIT runs today, sized by its known fleet.\n\n"
        f"{_md_table(table)}\n"
        f"Per vehicle they cost about the same: the {mv['chassis']} chassis costs ${delta['chassis']:,.0f} more "
        f"and needs the {mv['motor']} motor (${delta['motor']:,.0f} more) to reach the speed cap, while the "
        f"reference's {rv['battery']} pack, bought for a full day of range, costs ${-delta['battery']:,.0f} more "
        f"than {mv['battery']}. The {mv['chassis']} carries {mv['pax'] // rv['pax']}× the seats, so the anchor "
        "has more capacity for less money. The model cannot see the reason the reference chose 8 seats, MIT "
        "P&T's warning against half-empty large shuttles [[15]](../docs/references.md#ref-15): every road "
        f"vehicle runs at the fixed {scenario.load_factor:g} load factor (Appendix B), so a larger vehicle is "
        "always more capacity per dollar, and no weighted attribute credits the smaller vehicle.\n\n"
        "Making the reference the MIT shuttles would be defensible, a status-quo "
        "reference, but would lose the designed-vs.-existing comparison and the anchor's role as a "
        "check on the model. If empty seats matter, the fix is an attribute or a demand-based load factor "
        "that measures them.\n\n"
    )


def _marker_table(markers: pd.DataFrame) -> pd.DataFrame:
    """Reference and anchors in the Task 2 table's terms, plus model vs. published headway."""
    t = pd.DataFrame({
        "architecture": markers["architecture"],
        "role": markers["role"],
        "fleet": markers.apply(_describe, axis=1),
        "published headway (min)": markers["published_headway_min"].map(lambda h: "-" if pd.isna(h) else f"{h:g}"),
        "model headway (min)": markers["model_headway_min"].round(1),
        "capacity (trips/h)": markers["fleet_capacity_per_h"].round(0),
        "wait (min)": markers["wait_time"].round(1),
        "riders per vehicle per day": markers["trips_per_vehicle_day"].round(0),
        "availability": markers["availability"].round(3),
        "MAU": markers["mau"].round(3),
        "fleet cost": markers["fleet_cost_usd"].map(lambda c: f"${c:,.0f}"),
        "meets thresholds": markers["meets_thresholds"],
    })
    return t


def front_comparison(df: pd.DataFrame, markers: pd.DataFrame, utility: str = "mau") -> pd.DataFrame:
    """Where each reference/anchor sits against the Pareto front of ``df``.

    ``same utility, cheapest`` is the cheapest front architecture with at least the marker's utility;
    ``same cost, best`` is the best front architecture costing no more. The marker is dominated if
    either beats it (the first strictly on cost, the second strictly on utility).
    """
    front = pareto_front(df, utility)
    rows = []
    for _, m in markers.iterrows():
        cheaper = front[front[utility] >= m[utility]].head(1)
        better = front[front["fleet_cost_usd"] <= m["fleet_cost_usd"]].tail(1)
        dominated = ((len(cheaper) and cheaper["fleet_cost_usd"].iloc[0] < m["fleet_cost_usd"])
                     or (len(better) and better[utility].iloc[0] > m[utility]))
        rows.append({
            "architecture": m["architecture"],
            "fleet": _describe(m),
            "MAU": round(m[utility], 3),
            "cost": f"${m['fleet_cost_usd']:,.0f}",
            "meets thresholds": bool(m["meets_thresholds"]),
            "dominated": bool(dominated),
            "same utility, cheapest": "-" if cheaper.empty else
            f"{_describe(cheaper.iloc[0])}: ${cheaper['fleet_cost_usd'].iloc[0]:,.0f}",
            "same cost, best": "-" if better.empty else
            f"{_describe(better.iloc[0])}: MAU {better[utility].iloc[0]:.3f}",
        })
    return pd.DataFrame(rows)


def _segments_text(segments) -> str:
    return ", ".join(f"{a}–{b} step {c}" for a, b, c in segments)


def _describe(row: pd.Series) -> str:
    parts = [f"{int(row['n_road'])} × {row['road_variant']}" if row["n_road"] else "",
             f"{int(row['n_bike'])} × {row['bike_variant']}" if row["n_bike"] else ""]
    return " + ".join(p for p in parts if p)
