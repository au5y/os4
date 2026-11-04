"""Task 3 sensitivity: vehicle speed assumptions (PLAN.md Q4 road cap, Q6 e-bike assist) and the
riders-per-day ceilings (Q22).

Changes from the model baseline, each run with fixed and with removable e-bike batteries:

- **Appendix B e-bike speed:** bikes use the formula 700 * motor kW / total kg (1-8 km/h with a rider)
  instead of the fixed ``Scenario.bike_assisted_speed_kmh`` (18 km/h).
- **Road speed at the posted limit:** road vehicles are capped at 20 mph (32.2 km/h), the posted limit
  in Kendall and Central, instead of the 21 km/h achieved-speed cap.
- **No riders-per-day ceiling:** the Q22 utilization ceilings (bikes and small cars) are switched off,
  alone and together with the posted-limit road cap.

``write_speed_sensitivity`` writes ``outputs/task3_speed_sensitivity.md`` with its figures in ``outputs/media/``.
"""

from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from os4.model import reference_and_anchor_table
from os4.plots import GRID, INK, INK_2, OUTPUT_DIR, SERIES, SURFACE, _md_table, _style, media_dir, media_link
from os4.scenario import Scenario
from os4.tradespace import FLEET_TYPES, TYPE_STYLE, _cost_axis, _describe, front_comparison, pareto_front, tradespace
from os4.vehicle import bike_variants, road_variants

MPH_TO_KMH = 1.609344
POSTED_LIMIT_KMH = 20 * MPH_TO_KMH
BATTERY_CASES = {"fixed": "Fixed batteries", "removable": "Removable batteries"}
FRONT_ZOOM_USD = 1.5e6
COLORS = {"baseline": SERIES[0], "bike_formula": SERIES[1], "road_posted": SERIES[2], "no_ceiling": SERIES[3],
          "road_posted_no_ceiling": SERIES[2]}


def variations(scenario: Scenario) -> dict[str, tuple[str, Scenario]]:
    """Baseline and the two speed changes, each as (label, scenario)."""
    return {
        "baseline": (f"Model baseline (road cap {scenario.speed_limit_kmh:g} km/h, bikes "
                     f"{scenario.bike_assisted_speed_kmh:g} km/h)", scenario),
        "bike_formula": ("Appendix B e-bike speed (700·P/W)", replace(scenario, bike_assisted_speed_kmh=None)),
        "road_posted": (f"Road cap at the 20 mph posted limit ({POSTED_LIMIT_KMH:.1f} km/h)",
                        replace(scenario, speed_limit_kmh=POSTED_LIMIT_KMH)),
        "no_ceiling": ("No riders-per-day ceiling", _no_ceiling(scenario)),
        "road_posted_no_ceiling": ("20 mph road cap and no riders-per-day ceiling",
                                   _no_ceiling(replace(scenario, speed_limit_kmh=POSTED_LIMIT_KMH))),
    }


def _no_ceiling(scenario: Scenario) -> Scenario:
    return replace(scenario, max_bike_trips_per_day=None, max_car_trips_per_day=None)


def _battery(scenario: Scenario, battery: str) -> Scenario:
    return replace(scenario, bike_spare_options=(0.0,)) if battery == "fixed" else scenario


def run(scenario: Scenario) -> dict[tuple[str, str], dict]:
    """Score every (battery case, variation); keep each front, its reference/anchor check and summary numbers."""
    out = {}
    for battery in BATTERY_CASES:
        for key, (_, case) in variations(scenario).items():
            case = _battery(case, battery)
            df = tradespace(case, label=f"sensitivity: {key}, {battery}")
            front = pareto_front(df)
            bikes = df[df["fleet_type"] == "bike-only"]
            markers = reference_and_anchor_table(case)
            out[battery, key] = {
                "front": front,
                "markers": markers,
                "marker_check": front_comparison(df, markers),
                "architectures": len(df),
                "bike_only": len(bikes),
                "bike_only_cheapest": bikes.loc[bikes["fleet_cost_usd"].idxmin()] if len(bikes) else None,
                "car_only_cheapest": _cheapest_cars(df, case),
                "cheapest": df.loc[df["fleet_cost_usd"].idxmin()],
                "knee": front[front["mau"] >= 0.94].iloc[0],
                "max_mau": float(df["mau"].max()),
            }
            del df
    return out


def _cheapest_cars(df: pd.DataFrame, scenario: Scenario) -> pd.Series | None:
    """Cheapest road-only fleet of small cars (the chassis the car ceiling applies to)."""
    seats = road_variants(scenario).set_index("variant_id")["pax"]
    cars = df[(df["fleet_type"] == "road-only") & (df["road_variant"].map(seats) <= scenario.car_max_seats)]
    return cars.loc[cars["fleet_cost_usd"].idxmin()] if len(cars) else None


def summary_table(results: dict, scenario: Scenario) -> pd.DataFrame:
    labels = {k: label for k, (label, _) in variations(scenario).items()}
    rows = []
    for (battery, key), r in results.items():
        front, bike, cheap, knee = r["front"], r["bike_only_cheapest"], r["cheapest"], r["knee"]
        counts = front["fleet_type"].value_counts()
        rows.append({
            "case": f"{BATTERY_CASES[battery]}: {labels[key]}",
            "feasible": f"{r['architectures']:,}",
            "cheapest feasible": f"{_describe(cheap)}, ${cheap['fleet_cost_usd']:,.0f}",
            "cheapest bike-only": "-" if bike is None else f"{_describe(bike)}, ${bike['fleet_cost_usd']:,.0f}",
            "cheapest small-car fleet": "-" if r["car_only_cheapest"] is None else
            f"{_describe(r['car_only_cheapest'])}, ${r['car_only_cheapest']['fleet_cost_usd']:,.0f}",
            "front (road / bike / mixed)": " / ".join(str(counts.get(t, 0)) for t in FLEET_TYPES),
            "front meeting 7-min travel": f"{front['meets_travel_goal'].mean():.0%}",
            "first front point with MAU ≥ 0.94": f"{_describe(knee)}, {knee['mau']:.3f} at ${knee['fleet_cost_usd']:,.0f}",
            "max MAU": f"{r['max_mau']:.3f}",
        })
    return pd.DataFrame(rows)


# ---------- e-bike formula speed ----------

def bike_comparison(scenario: Scenario) -> pd.DataFrame:
    """Each fixed-battery bike variant at the assisted speed and the formula speed."""
    trip = scenario.bike_trip_km
    a = bike_variants(_battery(scenario, "fixed")).set_index("variant_id")
    b = bike_variants(_battery(variations(scenario)["bike_formula"][1], "fixed")).set_index("variant_id")
    return pd.DataFrame({
        "cost_usd": a["cost_usd"], "range_km": a["range_km"],
        "speed_base": a["speed_kmh"], "speed_new": b["speed_kmh"],
        "trip_min_base": 60 * trip / a["speed_kmh"], "trip_min_new": 60 * trip / b["speed_kmh"],
        "uptime_base": a["uptime_h"], "uptime_new": b["uptime_h"],
        "availability_base": a["availability"], "availability_new": b["availability"],
    }).sort_values("availability_new")


def plot_bike_availability(bikes: pd.DataFrame, path: Path, scenario: Scenario) -> Path:
    """Dumbbell: each bike variant's Appendix B availability at the assisted and the formula speed."""
    fig, ax = plt.subplots(figsize=(10, 8.5), facecolor=SURFACE)
    _style(ax)
    y = range(len(bikes))
    ax.hlines(y, bikes["availability_base"], bikes["availability_new"], color=GRID, linewidth=2, zorder=1)
    for col, key, label in (("availability_base", "baseline", f"{scenario.bike_assisted_speed_kmh:g} km/h assist (model)"),
                            ("availability_new", "bike_formula", "Appendix B formula speed")):
        ax.scatter(bikes[col], y, s=36, color=COLORS[key], zorder=3, label=label)
    for i, (_, row) in enumerate(bikes.iterrows()):
        ax.text(row["availability_new"] + 0.012, i, f"{row['speed_new']:.1f} km/h", va="center", fontsize=7.5,
                color=INK_2)
    ax.axvline(0.75, color=INK_2, linestyle=":", linewidth=1)
    ax.text(0.752, len(bikes) - 0.4, "0.75 benchmark", fontsize=8, color=INK_2, va="top")
    ax.set_yticks(list(y), bikes.index, fontsize=8)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("vehicle availability = up-time / (up-time + down-time), up-time = range / speed", fontsize=9,
                  color=INK_2)
    ax.set_title("E-bike availability rises when the bike is slow (fixed batteries; label = formula speed)",
                 loc="left", fontsize=12, color=INK, fontweight="bold")
    legend = ax.legend(loc="lower right", frameon=True, fontsize=8.5)
    legend.get_frame().set_edgecolor(GRID)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _bike_rows(b: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "variant": b.index,
        "cost": b["cost_usd"].map("${:,.0f}".format),
        "range (km)": b["range_km"].round(1),
        "speed (km/h)": [f"{x:g} → {y:.1f}" for x, y in zip(b["speed_base"], b["speed_new"])],
        "Kendall trip (min)": [f"{x:.1f} → {y:.1f}" for x, y in zip(b["trip_min_base"], b["trip_min_new"])],
        "up-time (h)": [f"{x:.2f} → {y:.1f}" for x, y in zip(b["uptime_base"], b["uptime_new"])],
        "availability": [f"{x:.2f} → {y:.2f}" for x, y in zip(b["availability_base"], b["availability_new"])],
    })


# ---------- road speed at the posted limit ----------

def road_comparison(scenario: Scenario) -> pd.DataFrame:
    """Road variants by chassis at the achieved-speed cap and at the posted limit."""
    a = road_variants(scenario).set_index("variant_id")
    b = road_variants(variations(scenario)["road_posted"][1]).set_index("variant_id")
    t = pd.DataFrame({"chassis": a["chassis"], "speed_base": a["speed_kmh"], "speed_new": b["speed_kmh"],
                      "availability_base": a["availability"], "availability_new": b["availability"],
                      "capped_new": b["speed_capped"]})
    g = t.groupby("chassis")
    return pd.DataFrame({
        "variants": g.size(),
        "fastest (km/h)": [f"{x:g} → {y:.1f}" for x, y in zip(g["speed_base"].max(), g["speed_new"].max())],
        "median speed (km/h)": [f"{x:.1f} → {y:.1f}" for x, y in zip(g["speed_base"].median(), g["speed_new"].median())],
        "reach the posted limit": g["capped_new"].mean().map("{:.0%}".format),
        "median availability": [f"{x:.2f} → {y:.2f}" for x, y in
                                zip(g["availability_base"].median(), g["availability_new"].median())],
    }).reset_index()


def _marker_rows(results: dict, battery: str, key: str) -> pd.DataFrame:
    base, new = results[battery, "baseline"], results[battery, key]
    m0, m1 = base["markers"].set_index("architecture"), new["markers"].set_index("architecture")
    c1 = new["marker_check"].set_index("architecture")
    return pd.DataFrame({
        "architecture": m0.index,
        "fleet": [_describe(r) for _, r in m1.iterrows()],
        "road speed (km/h)": [f"{x:.1f} → {y:.1f}" for x, y in zip(m0["road_speed_kmh"], m1["road_speed_kmh"])],
        "wait (min)": [f"{x:.1f} → {y:.1f}" for x, y in zip(m0["wait_time"], m1["wait_time"])],
        "MAU": [f"{x:.3f} → {y:.3f}" for x, y in zip(m0["mau"], m1["mau"])],
        "cost": m1["fleet_cost_usd"].map("${:,.0f}".format).to_numpy(),
        "dominated": c1["dominated"].to_numpy(),
        "same utility, cheapest": c1["same utility, cheapest"].to_numpy(),
    })


# ---------- shared ----------

def plot_fronts(results: dict, keys: tuple[str, ...], path: Path, scenario: Scenario) -> Path:
    """Pareto fronts, baseline vs. one variation, one panel per battery case; hollow points miss the 7-min goal."""
    labels = {k: label for k, (label, _) in variations(scenario).items()}
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), facecolor=SURFACE, sharey=True)
    # Zoom to where the fronts rise: past FRONT_ZOOM_USD they are flat at the MAU ceiling.
    shown = ("baseline", *keys)
    lo = min(results[b, k]["front"]["fleet_cost_usd"].min() for b in BATTERY_CASES for k in shown)
    for ax, battery in zip(axes, BATTERY_CASES):
        _style(ax)
        for k in shown:
            front, color = results[battery, k]["front"], COLORS[k]
            ax.step(front["fleet_cost_usd"] / 1e6, front["mau"], where="post", color=color, linewidth=1.8, zorder=2,
                    linestyle="--" if k.endswith("_no_ceiling") and k != "no_ceiling" else "-",
                    label=f"{labels[k]}: {len(front)} on front")
            for fleet_type in FLEET_TYPES:
                part = front[front["fleet_type"] == fleet_type]
                for ok, face in ((True, color), (False, "none")):
                    sel = part[part["meets_travel_goal"] == ok]
                    ax.scatter(sel["fleet_cost_usd"] / 1e6, sel["mau"], s=20, marker=TYPE_STYLE[fleet_type][1],
                               facecolor=face, edgecolor=color, linewidth=0.8, zorder=3)
        _cost_axis(ax)
        ax.set_xlim(lo / 1e6 * 0.92, FRONT_ZOOM_USD / 1e6)
        ax.set_title(BATTERY_CASES[battery], loc="left", fontsize=11, color=INK, fontweight="bold")
        ax.set_xlabel("fleet cost ($M, vehicle capital cost, log scale)", fontsize=9, color=INK_2)
    axes[0].set_ylabel("multi-attribute utility (Appendix A)", fontsize=9, color=INK_2)
    handles, _ = axes[1].get_legend_handles_labels()
    handles += [plt.Line2D([], [], marker=TYPE_STYLE[t][1], linestyle="", color=INK_2, label=t) for t in FLEET_TYPES]
    handles.append(plt.Line2D([], [], marker="o", linestyle="", markerfacecolor="none", markeredgecolor=INK_2,
                              label="misses 7-min travel goal"))
    legend = axes[1].legend(handles=handles, loc="lower right", frameon=True, fontsize=8)
    legend.get_frame().set_edgecolor(GRID)
    fig.suptitle(f"Pareto front up to ${FRONT_ZOOM_USD / 1e6:g}M: model baseline vs. "
                 f"{'; '.join(labels[k] for k in keys)}", x=0.01, ha="left", fontsize=13, color=INK,
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def _money(row: pd.Series) -> str:
    return f"{_describe(row)} (${row['fleet_cost_usd']:,.0f})"


def write_speed_sensitivity(scenario: Scenario, out_dir: Path = OUTPUT_DIR) -> list[Path]:
    """Write ``task3_speed_sensitivity.md``: availability and tradespace under the two speed changes."""
    media = media_dir(out_dir)
    results = run(scenario)
    bikes = bike_comparison(scenario)
    roads = road_comparison(scenario)
    bike_png = plot_bike_availability(bikes, media / "task3_speed_bike_availability.png", scenario)
    bike_fronts = plot_fronts(results, ("bike_formula",), media / "task3_speed_bike_fronts.png", scenario)
    road_fronts = plot_fronts(results, ("road_posted",), media / "task3_speed_road_fronts.png", scenario)
    ceiling_fronts = plot_fronts(results, ("no_ceiling", "road_posted_no_ceiling"),
                                 media / "task3_speed_ceiling_fronts.png", scenario)

    base, bf, rp, nc, rpc = (results["fixed", k] for k in
                             ("baseline", "bike_formula", "road_posted", "no_ceiling", "road_posted_no_ceiling"))
    nc_check = nc["marker_check"].iloc[0]
    rem_base, rem_nc = results["removable", "baseline"], results["removable", "no_ceiling"]
    ref_check = rp["marker_check"].iloc[0]
    ref_status = (f"still dominated (same utility for less: {ref_check['same utility, cheapest']})"
                  if ref_check["dominated"] else "no longer dominated")
    md_path = out_dir / "task3_speed_sensitivity.md"
    md_path.write_text(
        "# Task 3 sensitivity: vehicle speed and utilization ceilings\n\n"
        "The model caps road vehicles at the achieved urban speed "
        f"(**{scenario.speed_limit_kmh:g} km/h**, PLAN.md Q4), rides e-bikes at a fixed assisted "
        f"**{scenario.bike_assisted_speed_kmh:g} km/h** (Q6), and screens out fleets whose vehicles carry more riders "
        "per day than real systems do (Q22). This page reruns the model with these changed, every other input "
        "unchanged:\n\n"
        "- **Appendix B e-bike speed:** bikes use the formula 700 × motor kW / total kg.\n"
        f"- **Road cap at the posted limit:** road vehicles are capped at 20 mph ({POSTED_LIMIT_KMH:.1f} km/h), the "
        "posted limit in Kendall and Central, with no allowance for signals or congestion.\n"
        "- **No riders-per-day ceiling:** the Q22 utilization ceilings are off, alone and with the 20 mph road cap.\n\n"
        f"{_md_table(summary_table(results, scenario))}\n"
        "## Appendix B e-bike speed\n\n"
        "With a 100 kg rider, the formula gives bikes "
        f"**{bikes['speed_new'].min():.1f}–{bikes['speed_new'].max():.1f} km/h**. Appendix B's up-time is range / "
        "speed, so a slower bike takes longer to drain the same battery and spends more of the day \"up\". Range "
        "and charge time don't change.\n\n"
        f"![E-bike availability at both speeds]({media_link(bike_png)})\n\n"
        f"- Fixed-battery availability goes from **{bikes['availability_base'].min():.2f}–"
        f"{bikes['availability_base'].max():.2f}** to **{bikes['availability_new'].min():.2f}–"
        f"{bikes['availability_new'].max():.2f}**; {int((bikes['availability_new'] >= 0.75).sum())} of {len(bikes)} "
        "variants now pass the 0.75 benchmark, against none at the assisted speed.\n"
        "- The gain comes from the formula, not a better bike: the slowest variants (K1 motors, 2-seat B3 "
        f"frames) score highest because they barely move. A Kendall trip takes {bikes['trip_min_new'].min():.0f}–"
        f"{bikes['trip_min_new'].max():.0f} min instead of {bikes['trip_min_base'].iloc[0]:.1f}.\n"
        f"- **More bike fleets pass the thresholds** ({base['bike_only']} → {bf['bike_only']} bike-only, fixed "
        "batteries), but the utilization ceiling (Q22) still sets the floor at "
        f"{bf['bike_only_cheapest']['n_bike']:.0f} bikes.\n"
        f"- **Bike fleets cost more:** the cheapest bike-only fleet goes from {_money(base['bike_only_cheapest'])} to "
        f"{_money(bf['bike_only_cheapest'])}. The front now favors the biggest motor (K3), because slow bikes have "
        "long cycles and carry fewer riders per hour.\n"
        f"- **The knee moves toward road vehicles:** the first front point with MAU ≥ 0.94 goes from "
        f"{_money(base['knee'])} to {_money(bf['knee'])}. Just below the knee, small mixed fleets score slightly "
        "higher with formula speeds, because their more-available bikes raise service availability.\n"
        "- **The MAU doesn't see the slow trip.** Travel time is reported, not weighted (Q11), so a bike-only fleet "
        f"whose riders take {bf['bike_only_cheapest']['travel_time']:.0f} min still scores "
        f"{bf['bike_only_cheapest']['mau']:.3f}. Only {bf['front']['meets_travel_goal'].mean():.0%} of the front meets "
        "the 7-minute travel goal. Adopting the formula speed would need travel time weighted.\n\n"
        f"![Pareto fronts, e-bike speed]({media_link(bike_fronts)})\n\n"
        f"{_bike_md(bikes)}\n"
        "## Road cap at the 20 mph posted limit\n\n"
        f"Raising the cap from {scenario.speed_limit_kmh:g} to {POSTED_LIMIT_KMH:.1f} km/h lets small chassis run "
        "at the limit; heavy buses stay motor-limited (C8 tops out below it). Faster vehicles finish each cycle "
        "sooner, so each one carries more riders per hour. Vehicle availability falls where vehicles speed up, "
        "since up-time = range / speed shrinks; small chassis lose the most.\n\n"
        f"{_md_table(roads)}\n"
        f"- **Road fleets get cheaper:** the cheapest feasible fleet goes from {_money(base['cheapest'])} to "
        f"{_money(rp['cheapest'])}, and the knee from {_money(base['knee'])} to {_money(rp['knee'])}.\n"
        f"- **More road-only fleets reach the front** ({base['front']['fleet_type'].eq('road-only').sum()} → "
        f"{rp['front']['fleet_type'].eq('road-only').sum()}), and the knee's average trip drops to "
        f"{rp['knee']['travel_time']:.1f} min.\n"
        f"- **The MAU ceiling doesn't move** ({base['max_mau']:.3f} → {rp['max_mau']:.3f}): the plateau is set by "
        "demand served, not speed.\n"
        f"- **The reference** goes from MAU {base['markers']['mau'].iloc[0]:.3f} to {rp['markers']['mau'].iloc[0]:.3f} "
        f"and is {ref_status}.\n"
        "- This is the optimistic bound: real vehicles stop at signals and in traffic, which is why the model "
        "uses the achieved speed (Q4).\n\n"
        f"![Pareto fronts, road speed]({media_link(road_fronts)})\n\n"
        "Reference and anchors, fixed batteries (model baseline → posted limit):\n\n"
        f"{_md_table(_marker_rows(results, 'fixed', 'road_posted'))}\n"
        "## Without the riders-per-day ceiling\n\n"
        f"The Q22 ceilings screen out fleets whose vehicles would carry more than "
        f"{scenario.max_bike_trips_per_day:g} riders per bike or {scenario.max_car_trips_per_day:g} rides per small "
        f"car (1–{scenario.car_max_seats} seats) per day. They count each vehicle's riders over the whole service "
        "day: the model's daily volume, summed over every demand bin, divided by the fleet. The peak hour drives "
        "throughput and wait, not this count. Shuttles and buses were never capped. Here both ceilings are off, "
        "alone and with the 20 mph road cap.\n\n"
        f"![Pareto fronts, no ceiling]({media_link(ceiling_fronts)})\n\n"
        "With fixed batteries:\n\n"
        f"- **Bike-only fleets get smaller:** the cheapest goes from {_money(base['bike_only_cheapest'])} to "
        f"{_money(nc['bike_only_cheapest'])}, at {nc['bike_only_cheapest']['bike_trips_per_vehicle_day']:.0f} riders "
        f"per bike per day (MAU {base['bike_only_cheapest']['mau']:.3f} → {nc['bike_only_cheapest']['mau']:.3f}). "
        "Bluebikes run about 2.5 and Citi Bike e-bikes about 15.\n"
        f"- **Small-car fleets get much smaller:** the cheapest goes from {_money(base['car_only_cheapest'])} to "
        f"{_money(nc['car_only_cheapest'])}, at {nc['car_only_cheapest']['car_trips_per_vehicle_day']:.0f} rides per "
        "car per day, against Waymo's observed 24.\n"
        f"- **The knee doesn't move** ({_money(nc['knee'])}): it is built on buses, which were never capped. The front "
        f"goes from {len(base['front'])} to {len(nc['front'])} points, mostly mixed fleets with fewer, busier bikes.\n"
        f"- **The reference** is still dominated; the cheapest front fleet at its utility is now "
        f"{nc_check['same utility, cheapest']}.\n"
        f"- **With the 20 mph road cap too,** the cheapest feasible fleet is {_money(rpc['cheapest'])}, the knee "
        f"{_money(rpc['knee'])}, and the cheapest small-car fleet {_money(rpc['car_only_cheapest'])} at "
        f"{rpc['car_only_cheapest']['car_trips_per_vehicle_day']:.0f} rides per car per day.\n"
        "\nWith removable batteries the change is much larger:\n\n"
        f"- **The ceiling is what keeps cheap bike fleets off the front.** Swappable packs make bikes about 0.9 "
        f"available, so without the ceiling the cheapest bike-only fleet is {_money(rem_nc['bike_only_cheapest'])} "
        f"and the first front point with MAU ≥ 0.94 is {_money(rem_nc['knee'])}, MAU {rem_nc['knee']['mau']:.3f}, "
        f"down from {_money(rem_base['knee'])}. That fleet needs "
        f"{rem_nc['knee']['bike_trips_per_vehicle_day']:.0f} riders per bike per day.\n"
        f"- The cheapest feasible fleet becomes mixed: {_money(rem_nc['cheapest'])}.\n"
        "- Without the ceiling, the cheapest bike and car fleets rely on each vehicle cycling all day with no idle "
        "time (Q18), which is the overstatement the ceiling was added to catch.\n",
        encoding="utf-8",
    )
    return [bike_png, bike_fronts, road_fronts, ceiling_fronts, md_path]


def _bike_md(bikes: pd.DataFrame) -> str:
    return "Each fixed-battery bike variant (assisted → formula speed):\n\n" + _md_table(_bike_rows(bikes))
