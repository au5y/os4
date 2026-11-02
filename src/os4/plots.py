"""Task 1 figures and tables: SAU curves with the A/B/C cases, and the MAU breakdown.

Colors are the validated categorical slots (blue, orange, aqua, yellow); the two
lighter ones are under 3:1 contrast, so every mark also carries a text label.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from os4.utility import (  # noqa: E402
    ATTRIBUTES,
    compare_weight_sets,
    evaluate_cases,
    load_weights,
    sau,
    sau_table,
    weight_sensitivity,
)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
# Reports (Markdown) go in the output folder; figures, CSVs and the workbook in this subfolder.
MEDIA_DIR = "media"


def media_dir(out_dir: Path) -> Path:
    """``out_dir/media``, created if needed."""
    path = out_dir / MEDIA_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def media_link(path: Path) -> str:
    """Link from a report in the output folder to a file in its media folder."""
    return f"{MEDIA_DIR}/{path.name}"

SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
INK, INK_2, GRID, SURFACE = "#1f1f1e", "#5f5e58", "#e4e3de", "#fcfcfb"

LABELS = {
    "passenger_volume": ("Passenger volume", "trips/day"),
    "peak_throughput": ("Peak throughput", "trips/hour"),
    "wait_time": ("Average wait at Kendall", "minutes"),
    "availability": ("Availability", "fraction of time"),
}


def _style(ax: plt.Axes) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def case_table(weights=None) -> pd.DataFrame:
    """Cases A/B/C with raw values, each SAU, weighted contributions, MAU and rank."""
    weights = load_weights() if weights is None else weights
    table = evaluate_cases(weights)
    for a in ATTRIBUTES:
        table[f"k*u_{a}"] = weights[a] * table[f"u_{a}"]
    table["rank"] = table["mau"].rank(ascending=False).astype(int)
    return table


def plot_sau_curves(path: Path) -> Path:
    """2x2 small multiples: each SAU curve with cases A/B/C marked on it."""
    cases = evaluate_cases()
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), facecolor=SURFACE)
    for ax, a in zip(axes.flat, ATTRIBUTES):
        _style(ax)
        table = sau_table(a)
        xs = np.linspace(table["x"].min(), table["x"].max(), 400)
        ax.plot(xs, sau(a, xs), color=INK_2, linewidth=2, zorder=2)
        ax.scatter(table["x"], table["utility"], s=18, color=INK_2, zorder=3)
        for color, (_, row) in zip(SERIES, cases.iterrows()):
            ax.scatter(row[a], row[f"u_{a}"], s=80, color=color, edgecolor=SURFACE, linewidth=2, zorder=4)
        # Cases sharing a point (A and C on throughput) get one combined label
        for (x, u), group in cases.groupby([a, f"u_{a}"]):
            ax.annotate(f"{', '.join(group['case'])}  {u:.2f}", (x, u), xytext=(8, -4),
                        textcoords="offset points", fontsize=9, color=INK)
        title, unit = LABELS[a]
        ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold")
        ax.set_xlabel(unit, fontsize=9, color=INK_2)
        ax.set_ylim(-0.05, 1.08)
    axes[0, 0].set_ylabel("utility", fontsize=9, color=INK_2)
    axes[1, 0].set_ylabel("utility", fontsize=9, color=INK_2)
    handles = [plt.Line2D([], [], marker="o", linestyle="", markersize=9, color=c, label=f"Case {k}")
               for c, k in zip(SERIES, cases["case"])]
    fig.legend(handles=handles, loc="upper right", ncol=3, frameon=False, fontsize=9)
    fig.suptitle("Single-attribute utility curves (Appendix A)", x=0.06, ha="left",
                 fontsize=13, color=INK, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_mau_breakdown(path: Path) -> Path:
    """Horizontal stacked bars: each case's MAU split into k_i * u_i contributions."""
    weights = load_weights()
    table = case_table(weights).sort_values("mau")
    fig, ax = plt.subplots(figsize=(10, 3.6), facecolor=SURFACE)
    _style(ax)
    ax.grid(axis="y", visible=False)
    y = np.arange(len(table))
    left = np.zeros(len(table))
    for color, a in zip(SERIES, ATTRIBUTES):
        width = table[f"k*u_{a}"].to_numpy()
        ax.barh(y, width, left=left, height=0.55, color=color, edgecolor=SURFACE, linewidth=2,
                label=f"{LABELS[a][0]} (k={weights[a]:.2f})")
        for yi, l, w in zip(y, left, width):
            if w >= 0.04:
                ax.text(l + w / 2, yi, f"{w:.2f}", ha="center", va="center", fontsize=8, color=INK)
        left += width
    for yi, total in zip(y, table["mau"]):
        ax.text(total + 0.01, yi, f"{total:.3f}", va="center", fontsize=10, color=INK, fontweight="bold")
    ax.set_yticks(y, [f"Case {c}" for c in table["case"]], fontsize=10, color=INK)
    ax.set_xlim(0, 1)
    ax.set_xlabel("multi-attribute utility  U = Σ kᵢ·uᵢ", fontsize=9, color=INK_2)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=4, frameon=False, fontsize=8)
    ax.set_title("MAU by case, split by weighted attribute", loc="left", fontsize=13,
                 color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _md_table(table: pd.DataFrame) -> str:
    rows = [table.columns.tolist(), ["---"] * len(table.columns), *table.astype(str).to_numpy().tolist()]
    return "".join(f"| {' | '.join(r)} |\n" for r in rows)


def write_task1(out_dir: Path = OUTPUT_DIR) -> list[Path]:
    """Write the Task 1 tables (CSV), both figures, and a Markdown report embedding them."""
    media = media_dir(out_dir)
    weights = load_weights()
    full = case_table(weights)
    table = full.round(4)
    csv_path = media / "task1_cases.csv"
    mau_path = media / "task1_mau.csv"
    sens_path = media / "task1_weight_sensitivity.csv"
    md_path = out_dir / "task1_cases.md"
    table.to_csv(csv_path, index=False)
    weight_sets = compare_weight_sets().round(4)
    weight_sets.to_csv(mau_path, index=False)
    sensitivity = weight_sensitivity(weights=weights).round(4)
    sensitivity.to_csv(sens_path, index=False)
    sau_png = plot_sau_curves(media / "task1_sau_curves.png")
    mau_png = plot_mau_breakdown(media / "task1_mau_breakdown.png")

    summary = full[["case", *(f"u_{a}" for a in ATTRIBUTES), "mau", "rank"]].round(3)
    weight_text = ", ".join(f"{LABELS[a][0]} {weights[a]:.2f}" for a in ATTRIBUTES)
    md_path.write_text(
        "# Task 1: Multi-attribute utility\n\n"
        f"Generated by `python -m os4`. Weights: {weight_text}.\n\n"
        "## Cases A–C\n\n"
        f"{_md_table(summary)}\n"
        f"![Single-attribute utility curves with cases A–C]({media_link(sau_png)})\n\n"
        f"![MAU by case, split by weighted attribute]({media_link(mau_png)})\n\n"
        "## Full breakdown\n\n"
        f"{_md_table(table)}\n"
        "## MAU under each weight set\n\n"
        "`appendix_a` is the given weighting; `os3a_reweight` is the team's proposal from OS3A (PLAN.md Q8).\n\n"
        f"{_md_table(weight_sets.round(3))}\n"
        "## Weight sensitivity (each weight ±0.1, others renormalized)\n\n"
        f"{_md_table(sensitivity.round(3))}"
    )
    return [csv_path, mau_path, sens_path, md_path, sau_png, mau_png]


# --- Task 2 ------------------------------------------------------------------

ARCH_COLUMNS = {
    "architecture": "architecture",
    "road_variant": "road vehicle",
    "n_road": "N road",
    "bike_variant": "bike",
    "n_bike": "N bike",
    "road_speed_kmh": "road speed (km/h)",
    "road_range_km": "road range (km)",
    "bike_speed_kmh": "bike speed (km/h)",
    "bike_range_km": "bike range (km)",
    "fleet_capacity_per_h": "fleet throughput (trips/h)",
    "passenger_volume": "volume (trips/day)",
    "trips_per_vehicle_day": "riders per vehicle per day",
    "wait_time": "avg wait (min)",
    "availability": "availability",
    "road_cost_usd": "road vehicle cost",
    "bike_cost_usd": "bike cost",
    "fleet_cost_usd": "fleet cost",
    "mau": "MAU",
}


def plot_architectures(table: pd.DataFrame, path: Path) -> Path:
    """Two small multiples: each architecture's MAU split by weighted attribute, and its fleet cost."""
    weights = load_weights()
    table = table.sort_values("mau").reset_index(drop=True)
    fig, (ax_u, ax_c) = plt.subplots(1, 2, figsize=(11, 3.9), facecolor=SURFACE, sharey=True,
                                     gridspec_kw={"width_ratios": [3, 2]})
    y = np.arange(len(table))
    left = np.zeros(len(table))
    _style(ax_u)
    ax_u.grid(axis="y", visible=False)
    for color, a in zip(SERIES, ATTRIBUTES):
        width = weights[a] * table[f"u_{a}"].to_numpy()
        ax_u.barh(y, width, left=left, height=0.55, color=color, edgecolor=SURFACE, linewidth=2,
                  label=f"{LABELS[a][0]} (k={weights[a]:.2f})")
        left += width
    for yi, total in zip(y, table["mau"]):
        ax_u.text(total + 0.01, yi, f"{total:.3f}", va="center", fontsize=9, color=INK, fontweight="bold")
    ax_u.set_yticks(y, table["architecture"], fontsize=9, color=INK)
    ax_u.set_xlim(0, 1.12)
    ax_u.set_xlabel("multi-attribute utility  U = Σ kᵢ·uᵢ", fontsize=9, color=INK_2)
    ax_u.set_title("MAU, split by weighted attribute", loc="left", fontsize=11, color=INK, fontweight="bold")
    ax_u.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False, fontsize=8)

    _style(ax_c)
    ax_c.grid(axis="y", visible=False)
    cost = table["fleet_cost_usd"].to_numpy() / 1e3
    ax_c.barh(y, cost, height=0.55, color=INK_2, edgecolor=SURFACE, linewidth=2)
    for yi, c in zip(y, cost):
        ax_c.text(c + cost.max() * 0.02, yi, f"${c:,.0f}k", va="center", fontsize=9, color=INK)
    ax_c.set_xlim(0, cost.max() * 1.3)
    ax_c.set_xlabel("fleet cost ($k, vehicle capital)", fontsize=9, color=INK_2)
    ax_c.set_title("Fleet cost", loc="left", fontsize=11, color=INK, fontweight="bold")
    fig.suptitle("Five Task 2 architectures (primary scenario)", x=0.02, ha="left", fontsize=13, color=INK,
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_variants(variants: pd.DataFrame, scenario, path: Path) -> Path:
    """Availability vs. vehicle cost for every variant, and the uncapped road speeds against the cap."""
    from os4.vehicle import BENCHMARK_AVAILABILITY, formula_speed_kmh

    fig, (ax_a, ax_s) = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=SURFACE)
    _style(ax_a)
    road = variants["kind"] == "road"
    removable = (variants["kind"] == "bike") & (variants["spares_per_bike"] > 0)
    fixed = (variants["kind"] == "bike") & ~removable
    for mask, label, color, marker in ((road, "road EV", SERIES[0], "o"),
                                       (fixed, "e-bike, fixed battery (Appendix B)", SERIES[1], "^"),
                                       (removable, "e-bike, removable battery (team proposal)", SERIES[2], "v")):
        part = variants[mask]
        ax_a.scatter(part["cost_usd"], part["availability"], s=14, marker=marker, color=color, alpha=0.6,
                     linewidths=0, label=f"{label} ({len(part):,})")
    ax_a.axhline(BENCHMARK_AVAILABILITY, color=INK, linewidth=1.2, linestyle=(0, (4, 3)))
    ax_a.annotate("benchmark 0.75", (variants["cost_usd"].min(), BENCHMARK_AVAILABILITY), xytext=(2, 4),
                  textcoords="offset points", fontsize=8.5, color=INK)
    ax_a.set_xscale("log")
    ax_a.set_xlabel("vehicle cost ($, log scale)", fontsize=9, color=INK_2)
    ax_a.set_ylabel("availability", fontsize=9, color=INK_2)
    ax_a.set_ylim(0, 1)
    ax_a.legend(loc="lower right", frameon=False, fontsize=8, markerscale=1.5)
    best_fixed = variants.loc[fixed, "availability"].max()
    ax_a.set_title("Availability: fixed-battery e-bikes " + ("miss" if best_fixed < BENCHMARK_AVAILABILITY else "reach")
                   + " the benchmark", loc="left", fontsize=11, color=INK, fontweight="bold")

    _style(ax_s)
    road = variants[road]
    raw = formula_speed_kmh(np.array([_motor_kw(m) for m in road["motor"]]), road["weight_kg"].to_numpy())
    ax_s.hist(raw, bins=np.arange(0, raw.max() + 5, 5), color=SERIES[0], edgecolor=SURFACE, linewidth=2)
    top = ax_s.get_ylim()[1]
    for x, text, height in ((scenario.speed_limit_kmh, f"model cap {scenario.speed_limit_kmh:.0f} km/h", 0.95),
                            (32.0, "posted 20 mph (32 km/h)", 0.85)):
        ax_s.axvline(x, color=INK, linewidth=1.2, linestyle=(0, (4, 3)))
        ax_s.annotate(text, (x, top * height), xytext=(5, 0), textcoords="offset points",
                      fontsize=8.5, color=INK, va="center",
                      bbox=dict(boxstyle="square,pad=0.15", facecolor=SURFACE, edgecolor="none"))
    share = float((raw > scenario.speed_limit_kmh).mean())
    ax_s.set_xlabel("Appendix B speed 700·P/W before the cap (km/h)", fontsize=9, color=INK_2)
    ax_s.set_ylabel("road variants", fontsize=9, color=INK_2)
    ax_s.set_title(f"Road speed: {share:.0%} of variants hit the cap", loc="left", fontsize=11, color=INK,
                   fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _motor_kw(motor_id: str) -> float:
    from os4.data import load

    motors = load("road_motor").set_index("id")["power_kw"]
    return float(motors[motor_id])


def _swap_table(variants: pd.DataFrame, base: str = "B2-E1-G2-K2") -> pd.DataFrame:
    """Cost and availability of one bike across the spare-pack options."""
    rows = variants[variants["variant_id"].str.match(rf"^{base}(-S[\d.]+)?$")].sort_values("spares_per_bike")
    return pd.DataFrame({
        "variant": rows["variant_id"],
        "spare packs per bike": rows["spares_per_bike"].map(lambda k: "fixed battery" if k == 0 else f"{k:g}"),
        "bike cost": rows["cost_usd"].map(lambda c: f"${c:,.0f}"),
        "availability": rows["availability"].round(3),
    })


def write_task2(scenario, out_dir: Path = OUTPUT_DIR) -> list[Path]:
    """Write the Task 2 CSVs, both figures, and a Markdown report embedding them."""
    from os4.model import architecture_table, hand_calc_check
    from os4.vehicle import all_variants

    media = media_dir(out_dir)
    variants = all_variants(scenario)
    table = architecture_table(scenario)
    var_path = media / "task2_variants.csv"
    arch_path = media / "task2_architectures.csv"
    variants.round(4).to_csv(var_path, index=False)
    table.round(4).to_csv(arch_path, index=False)
    arch_png = plot_architectures(table, media / "task2_architectures.png")
    var_png = plot_variants(variants, scenario, media / "task2_variants.png")
    bikes = variants[variants["kind"] == "bike"]
    fixed_avail = bikes.loc[bikes["spares_per_bike"] == 0, "availability"]
    swap_avail = bikes.loc[bikes["spares_per_bike"] > 0, "availability"]

    shown = table[list(ARCH_COLUMNS)].rename(columns=ARCH_COLUMNS).copy()
    for col in ("road vehicle cost", "bike cost", "fleet cost"):
        shown[col] = shown[col].map(lambda c: "-" if pd.isna(c) else f"${c:,.0f}")
    shown = shown.round(2).fillna("-")
    inputs = pd.DataFrame([
        ("Road average-speed cap", f"{scenario.speed_limit_kmh:g} km/h", "Q3: 20 mph posted; signals hold peak speed near 13 mph"),
        ("E-bike speed", f"{scenario.bike_assisted_speed_kmh:g} km/h", "Q5: fixed assist instead of 700·P/W"),
        ("Trip length (road / bike)", f"{scenario.avg_trip_km:g} / {scenario.bike_trip_km:g} km", "Q13: Kendall links measured on OSRM (Q1)"),
        ("Empty return (deadhead)", f"{scenario.deadhead_fraction:g} × trip", "Q13 (open): vehicles return to Kendall empty"),
        ("Dwell / load factor", f"{scenario.dwell_s:g} s / {scenario.load_factor:g} (road vehicles)", "Appendix B"),
        ("E-bike riders per trip", ", ".join(f"{p}-seat {p * lf:.2g}" for p, lf in scenario.bike_load_factors),
         "Team fix (PLAN.md K): a bike only moves with a rider"),
        ("Throughput MoP", scenario.throughput_measure, "Q11 (decided): demand actually served"),
        ("Demand", f"peak {scenario.peak_demand_per_h:g} trips/h, "
                   f"{scenario.demand['trips_per_hour'].sum() * scenario.demand_bin_h:,.0f} trips/day", "Appendix B, Kendall origin"),
    ], columns=["input", "value", "source"])
    hand = hand_calc_check(scenario)[["variant_id", "weight_kg", "cost_usd", "wh_per_km", "range_km", "speed_kmh",
                                      "availability", "cycle_min", "capacity_per_vehicle_h"]].round(3)
    md_path = out_dir / "task2_model.md"
    md_path.write_text(
        "# Task 2: System model\n\n"
        f"Generated by `python -m os4` for the scenario *{scenario.name}*. "
        f"{len(variants):,} feasible vehicle variants "
        f"({(variants['kind'] == 'road').sum():,} road, {(variants['kind'] == 'bike').sum()} e-bike) after the battery "
        "weight limits.\n\n"
        "## Scenario inputs\n\n"
        f"{_md_table(inputs)}\n"
        "## Equations\n\n"
        "- **Vehicle (Appendix B):** weight = components + 100 kg × pax; Wh/km = nominal + 0.1 × (weight − chassis) "
        "+ autonomy; range = kWh × 1000 / (Wh/km); speed = min(700 × kW / kg, cap); charge = kWh / kW; "
        "up-time = range / speed; down-time = charge + 0.25 h; availability = up / (up + down).\n"
        "- **Fleet:** cycle = trip × (1 + deadhead) / speed + dwell; capacity per vehicle = 60 / cycle × pax × load factor (road 0.75; bikes by seats, PLAN.md K); "
        "fleet capacity = Σ N × availability × capacity per vehicle; volume = Σ over 2-h bins of min(demand, capacity) × 2.\n"
        "- **Wait (Q12):** headway / 2 at the Kendall hub, × 1 / (1 − ρ) as demand nears capacity, capped at "
        f"{scenario.max_wait_min:g} min, demand-weighted over the day. **Availability (Q14):** service availability, the demand-weighted "
        "chance that the vehicles in service (each in service with its Appendix B availability) can carry each "
        "bin's demand (normal approximation); the capacity-weighted vehicle availability is also reported.\n\n"
        "## Five architectures\n\n"
        f"![MAU and fleet cost of the five architectures]({media_link(arch_png)})\n\n"
        f"{_md_table(shown)}\n"
        "## Vehicle variants\n\n"
        f"![Availability vs. cost and uncapped road speeds]({media_link(var_png)})\n\n"
        f"Fixed-battery e-bikes (Appendix B as given) reach only {fixed_avail.min():.2f}–{fixed_avail.max():.2f} "
        "availability: small batteries and slow chargers mean they charge far longer than they ride. With removable "
        f"batteries (below) they reach up to {swap_avail.max():.2f}, depending on spare packs per bike. Most road "
        "variants hit the speed cap, so motors above M2 rarely add speed.\n\n"
        "## Removable e-bike batteries (team proposal)\n\n"
        "Appendix B allows changes to its equations with a justification. We add a removable-battery option for "
        "e-bikes: when a pack runs flat the bike swaps it in "
        f"{scenario.bike_swap_h * 60:g} min (assumed) instead of charging in place, and the flat pack charges off "
        "the bike. The fleet buys k spare packs per bike, pooled (k = 0.5 is one spare per two bikes):\n\n"
        "- **Availability** = min( U / (U + s), (1 + k) · U / (U + s + C + 0.25) ), with U = up-time (range / speed), "
        "s = swap time, C = charge time. The first term is the swap itself; the second is the supply of charged "
        "packs. With k = 0 and s = 0 it is the Appendix B availability.\n"
        "- **Cost** = bike cost + k × (battery cost + charger cost): each spare pack needs its own charger slot.\n"
        "- **Spares beyond (C + 0.25) / (U + s) add nothing,** so the useful number of spares depends on the battery "
        "and charger; `prune_variants` keeps only the spare counts worth buying "
        f"(options {', '.join(f'{k:g}' for k in scenario.bike_spare_options)}).\n\n"
        f"{_md_table(_swap_table(variants))}\n"
        "Not counted: swap labor and swap-station space (operating cost, Q15). Task 3 shows the tradespace with and "
        "without this option.\n\n"
        "## Hand-calculation check\n\n"
        "Worked by hand from Appendix B and asserted in `tests/test_vehicle.py` and `tests/test_fleet.py`:\n\n"
        f"{_md_table(hand)}\n"
        "Full data: `media/task2_variants.csv`, `media/task2_architectures.csv`, and the Variants / Architectures "
        "sheets of `media/os4_model.xlsx` (formulas).\n"
    )
    return [var_path, arch_path, arch_png, var_png, md_path]
