"""Tasks 3-4: enumerate the design vector, score architectures, plot tradespace.

``tradespace`` scores every road-only, bike-only and mixed fleet on the
fleet-size grids with the same equations as ``os4.fleet`` / ``os4.model``,
vectorized over architectures (``test_tradespace.py`` checks it matches
``model.evaluate``). ``pareto_front`` and ``utopia_point`` summarize it, and
``write_task3`` writes the figure and report to ``outputs/``.
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
from os4.model import architecture_table, evaluate_many, meets_thresholds, requirement_flags  # noqa: E402
from os4.plots import GRID, INK, INK_2, OUTPUT_DIR, SERIES, SURFACE, _md_table, _style  # noqa: E402
from os4.scenario import Scenario  # noqa: E402
from os4.utility import ATTRIBUTES, load_weights, sau  # noqa: E402
from os4.vehicle import all_variants  # noqa: E402

# Q10 (decided): road 5-300 step 5, bikes 25-750 step 25 (0 = that part absent).
N_ROAD = tuple(range(0, 301, 5))
N_BIKE = tuple(range(0, 751, 25))
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
    """Cross (pruned) road and bike variants with the fleet-size grids (Q10).

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
    per_vehicle = 60.0 / cycle * rows["pax"].to_numpy(float) * scenario.load_factor
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
    (``model.meets_thresholds``) are dropped right after capacity and volume are
    known, before the wait and utility calculations. ``df.attrs`` records
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

    failures = {"daily_volume": 0, "peak_throughput": 0, "offpeak_throughput": 0}
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

    # Early exit: drop architectures that break a Table 1 threshold before the costlier steps.
    keep = meets_thresholds(capacity, volume, scenario) if screen else np.ones(len(capacity), dtype=bool)
    rp = {k: v[keep] for k, v in rp.items()}
    bp = {k: v[keep] for k, v in bp.items()}
    capacity, volume = capacity[keep], volume[keep]
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
        "fleet_cost_usd": rp["cost"] + bp["cost"],
    })
    weights = load_weights()
    df["mau"] = sum(weights[a] * sau(a, df[a].to_numpy()) for a in ATTRIBUTES)
    extended = load_weights("os3a_extended")
    df["mau_os3a_extended"] = sum(w * sau(a, df[a].to_numpy()) for a, w in extended.items())
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


def plot_tradespace(df: pd.DataFrame, path: Path, highlight: pd.DataFrame | None = None,
                    utility: str = "mau", title: str = "Tradespace: utility vs. fleet cost") -> Path:
    """Scatter utility vs. cost with the Pareto front and utopia point; save to ``path``."""
    fig, ax = plt.subplots(figsize=(10, 6.2), facecolor=SURFACE)
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
    _cost_axis(ax)
    ax.set_xlabel("fleet cost ($M, vehicle capital cost, log scale)", fontsize=9, color=INK_2)
    ax.set_ylabel("multi-attribute utility", fontsize=9, color=INK_2)
    ax.set_ylim(max(0, df[utility].min() - 0.05), 1.02)
    ax.set_xlim(df["fleet_cost_usd"].min() / 1e6 * 0.8, df["fleet_cost_usd"].max() / 1e6 * 1.2)
    legend = ax.legend(loc="lower right", frameon=True, fontsize=8.5, markerscale=2.5)
    legend.get_frame().set_edgecolor(GRID)
    for handle in legend.legend_handles:
        handle.set_alpha(1)
    ax.set_title(title, loc="left", fontsize=13, color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _requirement_rows(df: pd.DataFrame, scenario: Scenario) -> pd.DataFrame:
    """How many architectures fail each Table 1 requirement.

    Thresholds are counted over the whole grid during screening (``df.attrs``); the desired goals and
    the availability benchmark are counted over the architectures that pass the thresholds.
    """
    grid, failures, n = df.attrs["grid_size"], df.attrs["threshold_failures"], len(df)
    rows = [
        ("daily volume", f">= {scenario.min_daily_volume:,.0f} trips/day", "threshold", failures["daily_volume"], grid),
        ("peak throughput", f">= {scenario.min_peak_throughput:g} trips/h", "threshold",
         failures["peak_throughput"], grid),
        ("off-peak throughput", f">= {scenario.min_offpeak_throughput:g} trips/h", "threshold",
         failures["offpeak_throughput"], grid),
        ("wait in boundary", f"<= {scenario.goal_wait_min:g} min", "desired", int((~df["meets_wait_goal"]).sum()), n),
        ("travel time, average Kendall trip", f"<= {scenario.goal_travel_min:g} min", "desired",
         int((~df["meets_travel_goal"]).sum()), n),
        ("service availability", f">= {scenario.benchmark_availability:g}", "benchmark",
         int((~df["meets_availability_benchmark"]).sum()), n),
    ]
    return pd.DataFrame([(name, target, kind, f"{fail:,} of {total:,}", f"{fail / total:.1%}")
                         for name, target, kind, fail, total in rows],
                        columns=["requirement", "target", "type", "architectures failing", "share"])


LOAD_FACTORS = (0.25, 0.5, 0.75, 1.0)
LOAD_FACTOR_COLORS = ("#86b6ef", "#3987e5", "#1c5cab", "#0d366b")  # ordinal ramp steps 250/400/550/700


def load_factor_fronts(scenario: Scenario, load_factors=LOAD_FACTORS) -> dict[float, pd.DataFrame]:
    """Pareto front of the full design space at each average load factor (Appendix B uses 0.75)."""
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
    ax.set_title("Pareto front by average load factor (share of seats filled per trip)", loc="left", fontsize=13,
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


def _type_rows(df: pd.DataFrame, front: pd.DataFrame, front_ext: pd.DataFrame) -> pd.DataFrame:
    counts = df["fleet_type"].value_counts()
    on_front, on_front_ext = front["fleet_type"].value_counts(), front_ext["fleet_type"].value_counts()
    return pd.DataFrame({
        "fleet type": FLEET_TYPES,
        "architectures": [f"{counts.get(t, 0):,}" for t in FLEET_TYPES],
        "on Pareto front": [on_front.get(t, 0) for t in FLEET_TYPES],
        "best MAU": [round(df.loc[df["fleet_type"] == t, "mau"].max(), 3) for t in FLEET_TYPES],
        "on extended-MAU front": [on_front_ext.get(t, 0) for t in FLEET_TYPES],
    })


def write_task3(scenario: Scenario, out_dir: Path = OUTPUT_DIR) -> list[Path]:
    """Write the Task 3 report: the tradespace with fixed e-bike batteries (Appendix B as given) and
    with the removable-battery option, each with its scatter, fleet-size charts and Pareto front."""
    out_dir.mkdir(parents=True, exist_ok=True)
    highlight = architecture_table(scenario)
    cases = {
        "fixed": ("Fixed e-bike batteries (Appendix B as given)", replace(scenario, bike_spare_options=(0.0,))),
        "removable": ("With removable e-bike batteries (team proposal)", scenario),
    }
    paths, sections, summary, frames = [], [], [], {}
    for key, (title, case) in cases.items():
        df = tradespace(case)
        frames[key] = df
        front = pareto_front(df)
        front_ext = pareto_front(df, "mau_os3a_extended")
        cost0, util0 = utopia_point(df)
        front_path = out_dir / f"task3_pareto_front_{key}.csv"
        front.round(4).to_csv(front_path, index=False)
        png = plot_tradespace(df, out_dir / f"task3_tradespace_{key}.png", highlight,
                              title=f"Tradespace: {title}")
        png_ext = plot_tradespace(df, out_dir / f"task3_tradespace_{key}_extended.png", highlight,
                                  utility="mau_os3a_extended", title=f"Extended MAU: {title}")
        road_png = plot_fleet_size(df, "road", out_dir / f"task3_fleet_size_road_{key}.png", subtitle=title)
        bike_png = plot_fleet_size(df, "bike", out_dir / f"task3_fleet_size_bike_{key}.png", subtitle=title)
        paths += [front_path, png, png_ext, road_png, bike_png]
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
            f"![Tradespace]({png.name})\n\n"
            f"Utopia point: ${cost0:,.0f} and MAU {util0:.3f}. Circled points are the five Task 2 architectures.\n\n"
            f"{_md_table(_type_rows(df, front, front_ext))}\n"
            "### Fleet size by vehicle type\n\n"
            "Each panel follows one vehicle type up its fleet-size range (light = few vehicles, dark = many) "
            "against the whole tradespace (gray) and this case's Pareto front; ringed points are on the front.\n\n"
            f"![Fleet size by road chassis]({road_png.name})\n\n"
            f"![Fleet size by e-bike frame]({bike_png.name})\n\n"
            f"### Pareto front ({len(front)} architectures)\n\n"
            f"{_md_table(_front_table(front))}\n"
            "### With the team's extended MAU\n\n"
            f"Scored with the `os3a_extended` weights (adds travel time and bike share, PLAN.md Q8); "
            f"the front has {len(front_ext)} architectures.\n\n"
            f"![Tradespace with the extended MAU]({png_ext.name})\n\n"
        )
    requirements = _requirement_rows(frames["removable"], scenario)
    frames.clear()
    fronts = load_factor_fronts(scenario)
    lf_png = plot_load_factor_fronts(fronts, out_dir / "task3_load_factor_fronts.png", scenario.load_factor)
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
        f"Fleet sizes: road {min(n for n in N_ROAD if n)}–{max(N_ROAD)} step {N_ROAD[2] - N_ROAD[1]}, "
        f"bikes {min(n for n in N_BIKE if n)}–{max(N_BIKE)} step {N_BIKE[2] - N_BIKE[1]} (PLAN.md Q10). "
        "Dominated vehicle variants are pruned first (`prune_variants`), so every road vehicle in the space is A3. "
        "Peak throughput is the demand actually served (Q11) and costs are vehicle capital only (Q15).\n\n"
        "The tradespace is run twice: with **fixed e-bike batteries** (Appendix B as given), and with the team's "
        "**removable-battery** option, where a bike swaps packs in "
        f"{scenario.bike_swap_h * 60:g} min and the fleet buys "
        f"{', '.join(f'{k:g}' for k in scenario.bike_spare_options if k > 0)} spare packs per bike (each spare adds "
        "its battery and a charger slot to the bike's cost). Pruning keeps only the spare counts worth buying.\n\n"
        f"{_md_table(pd.DataFrame(summary))}\n"
        "## Requirements (Table 1)\n\n"
        "Thresholds screen architectures out before scoring; desired goals and the availability benchmark are "
        "flags only. Counts are over the whole grid (removable-battery case) before screening.\n\n"
        f"{_md_table(requirements)}\n"
        "Travel time is the average Kendall trip (1.75 km road, 1.6 km bike; team decision): 5.0 min at the "
        f"{scenario.speed_limit_kmh:g} km/h road cap. The longest link (Lechmere–Central, "
        f"{max(scenario.node_distances_km.values()):g} km) would take ≥ 9.4 min and is left for later. "
        "Availability is *service* availability (Q14): the chance the vehicles in service can carry the hour's "
        "demand, so spare vehicles raise it.\n\n"
        "## Load-factor sensitivity\n\n"
        "Appendix B assumes trips average 75% full; the model keeps 0.75 as the baseline. The same design space "
        "scored at 25%, 50%, 75% and 100% (the removable-battery case, which also contains every fixed-battery "
        "option):\n\n"
        f"![Pareto front by load factor]({lf_png.name})\n\n"
        f"{_md_table(lf_rows)}\n"
        + "".join(sections)
    )
    return paths + [md_path]


def _describe(row: pd.Series) -> str:
    parts = [f"{int(row['n_road'])} × {row['road_variant']}" if row["n_road"] else "",
             f"{int(row['n_bike'])} × {row['bike_variant']}" if row["n_bike"] else ""]
    return " + ".join(p for p in parts if p)
