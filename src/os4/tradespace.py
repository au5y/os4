"""Tasks 3-4: enumerate the design vector, score architectures, plot tradespace.

``tradespace`` scores every road-only, bike-only and mixed fleet on the
fleet-size grids with the same equations as ``os4.fleet`` / ``os4.model``,
vectorized over architectures (``test_tradespace.py`` checks it matches
``model.evaluate``). ``pareto_front`` and ``utopia_point`` summarize it, and
``write_task3`` writes the figure and report to ``outputs/``.
"""

from collections.abc import Iterable
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from os4.fleet import Fleet  # noqa: E402
from os4.model import architecture_table, evaluate_many  # noqa: E402
from os4.plots import GRID, INK, INK_2, OUTPUT_DIR, SERIES, SURFACE, _md_table, _style  # noqa: E402
from os4.scenario import Scenario  # noqa: E402
from os4.utility import ATTRIBUTES, load_weights, sau  # noqa: E402
from os4.vehicle import all_variants  # noqa: E402

# Q10 defaults from docs/PLAN.md: road 5-60 step 5, bikes 25-300 step 25 (0 = that part absent).
N_ROAD = tuple(range(0, 61, 5))
N_BIKE = tuple(range(0, 301, 25))
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
    """Per-part capacity, departures, availability and cost; mirrors ``os4.fleet``."""
    speed = rows["speed_kmh"].to_numpy(float)
    cycle = 60.0 * trip_km * (1.0 + scenario.deadhead_fraction) / speed + scenario.dwell_s / 60.0
    effective = n * rows["availability"].to_numpy(float)
    return {
        "capacity": effective * 60.0 / cycle * rows["pax"].to_numpy(float) * scenario.load_factor,
        "departures": effective * 60.0 / cycle,
        "availability": rows["availability"].to_numpy(float),
        "cost": n * rows["cost_usd"].to_numpy(float),
        "speed": np.where(n > 0, speed, np.inf),
    }


def tradespace(
    scenario: Scenario,
    n_road: Iterable[int] = N_ROAD,
    n_bike: Iterable[int] = N_BIKE,
    variants: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Score every road-only, bike-only and mixed architecture on the fleet-size grids.

    One row per architecture with the same MoPs, SAUs, MAUs and cost as
    ``model.evaluate``, computed with numpy over the whole grid.
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
        nr_opts = nr if r_idx[0] >= 0 else np.array([0])
        nb_opts = nb if b_idx[0] >= 0 else np.array([0])
        grid = np.array(np.meshgrid(r_idx, nr_opts, b_idx, nb_opts, indexing="ij")).reshape(4, -1)
        blocks.append(grid)
    ri, n_r, bi, n_b = np.concatenate(blocks, axis=1)

    blank = road.iloc[[0]].copy()  # placeholder row for an absent part (n = 0 zeroes it out)
    road_rows = pd.concat([road, blank], ignore_index=True).iloc[np.where(ri >= 0, ri, len(road))]
    bike_rows = pd.concat([bike, bike.iloc[[0]]], ignore_index=True).iloc[np.where(bi >= 0, bi, len(bike))]
    bike_km = scenario.bike_trip_km if scenario.bike_trip_km is not None else scenario.avg_trip_km
    rp = _part_arrays(road_rows, n_r.astype(float), scenario.avg_trip_km, scenario)
    bp = _part_arrays(bike_rows, n_b.astype(float), bike_km, scenario)

    capacity = rp["capacity"] + bp["capacity"]
    departures = rp["departures"] + bp["departures"]
    demand = scenario.demand["trips_per_hour"].to_numpy(float)
    volume = np.minimum(demand[None, :], capacity[:, None]).sum(axis=1) * scenario.demand_bin_h
    peak = np.minimum(capacity, scenario.peak_demand_per_h) if scenario.throughput_measure == "served" else capacity

    with np.errstate(divide="ignore", invalid="ignore"):
        rho = demand[None, :] / capacity[:, None]
        wait_bins = np.where(rho < 1.0, (30.0 / departures[:, None]) / (1.0 - rho), scenario.max_wait_min)
        wait_bins = np.minimum(wait_bins, scenario.max_wait_min)
        wait = np.where(departures > 0, (wait_bins * demand).sum(axis=1) / demand.sum(), scenario.max_wait_min)
        avail = np.where(capacity > 0,
                         (rp["availability"] * rp["capacity"] + bp["availability"] * bp["capacity"]) / capacity, 0.0)
        bike_share = np.where(capacity > 0, bp["capacity"] / capacity, 0.0)
    slowest = np.minimum(rp["speed"], bp["speed"])
    travel = 60.0 * max(scenario.node_distances_km.values()) / slowest

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
        "availability": avail,
        "travel_time": travel,
        "bike_share": bike_share,
        "fleet_cost_usd": rp["cost"] + bp["cost"],
    })
    weights = load_weights()
    df["mau"] = sum(weights[a] * sau(a, df[a].to_numpy()) for a in ATTRIBUTES)
    extended = load_weights("os3a_extended")
    df["mau_os3a_extended"] = sum(w * sau(a, df[a].to_numpy()) for a, w in extended.items())
    return df


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
        ax.scatter(part["fleet_cost_usd"] / 1e6, part[utility], s=size, marker=marker, color=color,
                   alpha=alpha, linewidths=0, rasterized=True, label=f"{fleet_type} ({len(part):,})")
    front = pareto_front(df, utility)
    ax.step(front["fleet_cost_usd"] / 1e6, front[utility], where="post", color=INK, linewidth=2,
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
        slots = [(cheapest, (0.1, highlight.loc[cheapest, utility] - 0.07))]
        slots += [(i, (1.6, top - 0.055 * k)) for k, i in enumerate(right.index)]
        for i, text_xy in slots:
            row = highlight.loc[i]
            xy = (row["fleet_cost_usd"] / 1e6, row[utility])
            ax.scatter(*xy, s=90, facecolor="none", edgecolor=INK, linewidth=2, zorder=7)
            ax.annotate(row["architecture"], xy, xytext=text_xy, textcoords="data",
                        fontsize=8.5, color=INK, zorder=7, va="center",
                        arrowprops=dict(arrowstyle="-", color=INK_2, linewidth=0.8, shrinkA=2, shrinkB=6))
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:g}M"))
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


def write_task3(scenario: Scenario, out_dir: Path = OUTPUT_DIR) -> list[Path]:
    """Write the tradespace CSVs, the scatter plots and the Task 3 Markdown report."""
    out_dir.mkdir(parents=True, exist_ok=True)
    df = tradespace(scenario)
    highlight = architecture_table(scenario)
    front = pareto_front(df)
    front_ext = pareto_front(df, "mau_os3a_extended")
    cost0, util0 = utopia_point(df)

    csv_path = out_dir / "task3_tradespace.csv"
    front_path = out_dir / "task3_pareto_front.csv"
    df.round(4).to_csv(csv_path, index=False)
    front.round(4).to_csv(front_path, index=False)
    png = plot_tradespace(df, out_dir / "task3_tradespace.png", highlight)
    png_ext = plot_tradespace(df, out_dir / "task3_tradespace_extended.png", highlight, utility="mau_os3a_extended",
                              title="Tradespace with the team's extended MAU (os3a_extended weights)")

    cols = ["fleet_type", "road_variant", "n_road", "bike_variant", "n_bike", "fleet_capacity_per_h",
            "wait_time", "availability", "mau", "fleet_cost_usd"]
    counts = df["fleet_type"].value_counts()
    on_front = front["fleet_type"].value_counts()
    on_front_ext = front_ext["fleet_type"].value_counts()
    type_rows = pd.DataFrame({
        "fleet type": FLEET_TYPES,
        "architectures": [counts.get(t, 0) for t in FLEET_TYPES],
        "on Pareto front": [on_front.get(t, 0) for t in FLEET_TYPES],
        "best MAU": [round(df.loc[df["fleet_type"] == t, "mau"].max(), 3) for t in FLEET_TYPES],
        "on extended-MAU front": [on_front_ext.get(t, 0) for t in FLEET_TYPES],
    })
    fmt = front[cols].copy()
    fmt["fleet_cost_usd"] = fmt["fleet_cost_usd"].map(lambda c: f"${c:,.0f}")
    fmt = fmt.fillna("-").round(3)
    md_path = out_dir / "task3_tradespace.md"
    md_path.write_text(
        "# Task 3: Tradespace\n\n"
        f"Generated by `python -m os4` for the scenario *{scenario.name}*. "
        f"Fleet sizes: road {min(n for n in N_ROAD if n)}–{max(N_ROAD)} step {N_ROAD[2] - N_ROAD[1]}, "
        f"bikes {min(n for n in N_BIKE if n)}–{max(N_BIKE)} step {N_BIKE[2] - N_BIKE[1]} (PLAN.md Q10). "
        "Dominated vehicle variants are pruned first (`prune_variants`), so every road vehicle in the space is A3.\n\n"
        f"![Tradespace: MAU vs. fleet cost]({png.name})\n\n"
        f"**{len(df):,} architectures.** Utopia point (cheapest cost, highest MAU): "
        f"${cost0:,.0f} and {util0:.3f}. Circled points are the five Task 2 architectures "
        "(they are scored with `model.evaluate`, so the A5 example appears even though A5 is pruned here).\n\n"
        f"{_md_table(type_rows)}\n"
        f"## Pareto front (Appendix A weights, {len(front)} architectures)\n\n"
        f"{_md_table(fmt)}\n"
        "## With the team's extended MAU\n\n"
        "Same architectures scored with the `os3a_extended` weights (adds travel time and bike share, PLAN.md Q8). "
        f"The front has {len(front_ext)} architectures, and mixed fleets now dominate it (see the table above): "
        "rewarding bike share and travel time changes which architectures are worth considering.\n\n"
        f"![Tradespace with the extended MAU]({png_ext.name})\n"
    )
    return [csv_path, front_path, png, png_ext, md_path]
