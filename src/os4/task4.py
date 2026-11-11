"""Task 4: a second operating scenario, the Red Line disruption (PLAN.md Q29), against the standard weekday.

Scenario 1 is the standard weekday and Scenario 2 the Red Line closure (``scenario.weekday_scenario`` and
``scenario.red_line_scenario``), both with e-bikes at the 18 km/h assist (PLAN.md Q30) and fixed e-bike
batteries. Both tradespaces use the same design vector, fleet grid, Table 1 thresholds, riders-per-day
ceilings and Appendix A weights, so they compare directly.

The Task 3 picks are scored in both scenarios. Their road vehicles are A3, which Table 1 does not allow
outside the boundary, so in Scenario 2 each is replaced by its minimum-change "A4 twin" (same chassis,
battery, charger and motor, autonomy A4: +$20,000 and +30 kg per vehicle).

``write_task4`` writes ``outputs/task4_red_line.md`` with its figures in ``outputs/media/``.
"""

from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from os4.fleet import Fleet, cycle_time_min
from os4.model import architecture_table, evaluate
from os4.plots import GRID, INK, INK_2, OUTPUT_DIR, SERIES, SURFACE, _md_table, _style, media_dir, media_link
from os4.scenario import Scenario, primary_scenario, red_line_scenario, weekday_scenario
from os4.tradespace import FLEET_TYPES, _cost_axis, _describe, pareto_front, tradespace
from os4.vehicle import all_variants, get_variant

KNEE_MAU = 0.94  # same knee rule as Task 3: the first Pareto point with MAU >= 0.94
OS3A = "mau_os3a_reweight"
BUS, BIKE = "C8-P1-G3-M4-A3", "B1-E1-G2-K1"
# The Task 3 picks (Task 3-2 slide) and the Scenario 2 knee: (road variant, n road, bike variant, n bike).
PICKS = {
    "Pareto 1: 2 buses": (BUS, 2, None, 0),
    "Pareto 2 (knee): 2 buses + 20 e-bikes": (BUS, 2, BIKE, 20),
    "Pareto 3: 125 e-bikes": (None, 0, BIKE, 125),
    "Reference: 6 small shuttles": ("C4-P2-G3-M2-A3", 6, None, 0),
    "Scenario 2 knee: 6 A4 buses + 30 e-bikes": (BUS.replace("-A3", "-A4"), 6, BIKE, 30),
}


def fixed_batteries(scenario: Scenario) -> Scenario:
    return replace(scenario, bike_spare_options=(0.0,))


def scenarios() -> dict[str, Scenario]:
    """Scenario 1 and Scenario 2, with fixed e-bike batteries (Appendix B as given)."""
    return {"s1": fixed_batteries(weekday_scenario()), "s2": fixed_batteries(red_line_scenario())}


def a4_twin(variant_id: str | None, scenario: Scenario) -> str | None:
    """The variant itself if ``scenario`` allows its autonomy level, else the same vehicle at A4."""
    if variant_id is None or variant_id.rsplit("-", 1)[1] in scenario.allowed_autonomy:
        return variant_id
    return variant_id.rsplit("-", 1)[0] + "-A4"


def score(road: str | None, n_road: int, bike: str | None, n_bike: int, scenario: Scenario) -> dict:
    """``model.evaluate`` for a fleet given by variant ids."""
    fleet = Fleet(road=None if road is None else get_variant(road, scenario), n_road=n_road,
                  bike=None if bike is None else get_variant(bike, scenario), n_bike=n_bike)
    return evaluate(fleet, scenario)


def knee(front: pd.DataFrame, utility: str = "mau") -> pd.Series:
    return front[front[utility] >= KNEE_MAU].iloc[0]


def on_front(row: dict, front: pd.DataFrame, utility: str = "mau") -> bool:
    """True if no front point is at least as good on both cost and utility and strictly better on one."""
    c, u = row["fleet_cost_usd"], row[utility]
    better = (front["fleet_cost_usd"] <= c) & (front[utility] >= u) & (
        (front["fleet_cost_usd"] < c - 1e-6) | (front[utility] > u + 1e-9))
    return not better.any()


def run() -> dict:
    """Score both tradespaces and the picks; everything the report, the figures and Task 5 need."""
    out = {}
    for key, scenario in scenarios().items():
        df = tradespace(scenario, label=f"Task 4: {key}")
        front, front_os3a = pareto_front(df), pareto_front(df, OS3A)
        counts = front["fleet_type"].value_counts()
        out[key] = {
            "scenario": scenario, "feasible": len(df), "front": front, "front_os3a": front_os3a,
            "front_types": {t: int(counts.get(t, 0)) for t in FLEET_TYPES},
            "knee": knee(front), "knee_os3a": knee(front_os3a, OS3A),
            "cheapest": df.loc[df["fleet_cost_usd"].idxmin()], "max_mau": float(df["mau"].max()),
            "min_mau": float(df["mau"].min()),
            "sample": df.sample(min(len(df), 60_000), random_state=0)[["fleet_cost_usd", "mau", "fleet_type"]],
        }
        del df
    out["picks"] = pick_table(out)
    out["task2"] = task2_in_scenario2(out["s2"]["scenario"])
    s2 = out["s2"]["scenario"]
    out["s2_roads_only"] = score(PICKS["Scenario 2 knee: 6 A4 buses + 30 e-bikes"][0], 6, None, 0, s2)
    slow = fixed_batteries(replace(red_line_scenario(), bike_assisted_speed_kmh=None))
    out["s2_formula_bikes_knee"] = knee(pareto_front(tradespace(slow, label="Task 4: s2, formula bikes")))
    return out


def pick_table(results: dict) -> pd.DataFrame:
    """Each pick in both scenarios (Scenario 2 as its A4 twin where A3 isn't allowed)."""
    rows = []
    for name, (road, n_road, bike, n_bike) in PICKS.items():
        row = {"architecture": name}
        for key in ("s1", "s2"):
            scenario, front = results[key]["scenario"], results[key]["front"]
            twin = a4_twin(road, scenario)
            r = score(twin, n_road, bike, n_bike, scenario)
            r["architecture"] = name
            row[key] = r | {"as_built": twin == road, "on_front": on_front(r, front),
                            "on_front_os3a": on_front(r, results[key]["front_os3a"], OS3A)}
        rows.append(row)
    return pd.DataFrame(rows)


def task2_in_scenario2(s2: Scenario) -> pd.DataFrame:
    """The five Task 2 architectures (as sized in Task 2) in Scenario 2; A3 ones are not allowed."""
    rows = []
    for _, a in architecture_table(primary_scenario()).iterrows():
        road = a["road_variant"] if isinstance(a["road_variant"], str) else None
        bike = a["bike_variant"] if isinstance(a["bike_variant"], str) else None
        fleet = _describe(a)
        if road is not None and road.rsplit("-", 1)[1] not in s2.allowed_autonomy:
            rows.append({"architecture": a["architecture"], "fleet": fleet, "Scenario 2": "not allowed (A3)"})
            continue
        r = score(road, int(a["n_road"]), bike, int(a["n_bike"]), s2)
        verdict = "passes Table 1" if r["meets_thresholds"] else "fails Table 1"
        rows.append({"architecture": a["architecture"], "fleet": fleet,
                     "Scenario 2": f"MAU {r['mau']:.3f}, {verdict} ({r['peak_throughput']:.0f} of "
                                   f"{s2.peak_demand_per_h:.0f} trips/h at the peak)"})
    return pd.DataFrame(rows)


# ---------- figures ----------

def plot_fronts(results: dict, path: Path, stars: dict | None = None,
                title: str = "Pareto fronts: standard weekday vs. Red Line closure") -> Path:
    """Both tradespaces (a sample) and fronts on one log-cost axis; the picks marked in each scenario.

    ``stars`` ({label: (scenario key, row)}) draws star markers instead of the picks (Task 5).
    """
    fig, ax = plt.subplots(figsize=(10, 6.6), facecolor=SURFACE)
    _style(ax)
    colors = {"s1": SERIES[0], "s2": SERIES[1]}
    names = {"s1": "Scenario 1: standard weekday", "s2": "Scenario 2: Red Line closure"}
    for key in ("s1", "s2"):
        r = results[key]
        ax.scatter(r["sample"]["fleet_cost_usd"] / 1e6, r["sample"]["mau"], s=3, color=colors[key], alpha=0.08,
                   linewidths=0, rasterized=True)
        f = r["front"]
        ax.step(f["fleet_cost_usd"] / 1e6, f["mau"], where="post", color=colors[key], linewidth=2.2,
                label=f"{names[key]}: {r['feasible']:,} feasible, front {len(f)}", zorder=4)
    if stars is None:
        markers = {"s1": "o", "s2": "s"}
        for _, p in results["picks"].iterrows():
            for key in ("s1", "s2"):
                r = p[key]
                ax.scatter(r["fleet_cost_usd"] / 1e6, r["mau"], marker=markers[key], s=70, facecolor=SURFACE,
                           edgecolor=colors[key], linewidth=2, zorder=6)
            a, b = p["s1"], p["s2"]
            ax.annotate("", (b["fleet_cost_usd"] / 1e6, b["mau"]), (a["fleet_cost_usd"] / 1e6, a["mau"]),
                        arrowprops=dict(arrowstyle="->", color=INK_2, linewidth=0.8, shrinkA=5, shrinkB=5), zorder=5)
            short = p["architecture"].split(":")[0]
            ax.annotate(short, (b["fleet_cost_usd"] / 1e6, b["mau"]), xytext=(7, -3), textcoords="offset points",
                        fontsize=8.5, color=INK, zorder=7)
        ax.scatter([], [], marker="o", s=60, facecolor=SURFACE, edgecolor=colors["s1"], linewidth=2,
                   label="Task 3 picks in Scenario 1 (arrow: the same pick in Scenario 2, A4 twin)")
        ax.scatter([], [], marker="s", s=60, facecolor=SURFACE, edgecolor=colors["s2"], linewidth=2,
                   label="... in Scenario 2")
    else:
        for label, (key, row) in stars.items():
            ax.scatter(row["fleet_cost_usd"] / 1e6, row["mau"], marker="*", s=360, color=colors[key],
                       edgecolor=INK, linewidth=1, zorder=8)
            ax.annotate(f"{label}\n${row['fleet_cost_usd']:,.0f}, MAU {row['mau']:.3f}",
                        (row["fleet_cost_usd"] / 1e6, row["mau"]), xytext=(-12, 12), textcoords="offset points",
                        ha="right", fontsize=9, color=INK, zorder=9,
                        bbox=dict(boxstyle="round,pad=0.25", facecolor=SURFACE, edgecolor=GRID))
    ax.axhline(results["s2"]["min_mau"], color=INK_2, linewidth=0.8, linestyle="--", zorder=1)
    ax.annotate("lowest MAU that passes Table 1 in Scenario 2", (2.9, results["s2"]["min_mau"]), xytext=(0, 4),
                textcoords="offset points", ha="right", fontsize=8, color=INK_2)
    ax.set_xscale("log")
    _cost_axis(ax)
    ax.set_xlim(0.15, 3.0)
    ax.set_ylim(0.15, 1.02)
    ax.set_xlabel("fleet cost ($M, vehicle capital cost, log scale)", fontsize=9, color=INK_2)
    ax.set_ylabel("multi-attribute utility (Appendix A weights)", fontsize=9, color=INK_2)
    ax.set_title(title, loc="left", fontsize=13, color=INK, fontweight="bold")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=1, frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_mau_change(picks: pd.DataFrame, path: Path, utility: str = OS3A) -> Path:
    """Dumbbell: each pick's MAU in Scenario 1 and Scenario 2 (A4 twin where needed)."""
    fig, ax = plt.subplots(figsize=(10, 5.0), facecolor=SURFACE)
    _style(ax)
    names = list(picks["architecture"])[::-1]
    for i, (_, p) in enumerate(picks.iloc[::-1].iterrows()):
        a, b = p["s1"][utility], p["s2"][utility]
        ax.plot([a, b], [i, i], color=GRID, linewidth=3, zorder=1)
        ax.scatter(a, i, s=80, color=SERIES[0], zorder=3)
        ax.scatter(b, i, s=80, color=SERIES[1], zorder=3)
        ax.annotate(f"{a:.3f}", (a, i), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8.5,
                    color=INK)
        twin = "" if p["s2"]["as_built"] else " (A4 twin)"
        ax.annotate(f"{b:.3f}{twin}", (b, i), xytext=(0, -15), textcoords="offset points", ha="center",
                    fontsize=8.5, color=INK)
    ax.set_yticks(range(len(names)), names, fontsize=9)
    ax.set_xlim(0, 1.05)
    ax.set_ylim(-0.7, len(names) - 0.3)
    ax.set_xlabel(f"MAU ({'OS3A reweight' if utility == OS3A else 'Appendix A'} weights)", fontsize=9, color=INK_2)
    ax.scatter([], [], s=60, color=SERIES[0], label="Scenario 1: standard weekday")
    ax.scatter([], [], s=60, color=SERIES[1], label="Scenario 2: Red Line closure")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False, fontsize=8.5)
    ax.set_title("MAU of each architecture: normal weekday vs. Red Line closure", loc="left", fontsize=13,
                 color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


# ---------- report ----------

def _money(x: float) -> str:
    return f"${x:,.0f}"


def _pick_rows(picks: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, p in picks.iterrows():
        a, b = p["s1"], p["s2"]
        s2_status = ("infeasible (fails Table 1)" if not b["meets_thresholds"] else
                     "on the front" if b["on_front"] else "dominated")
        rows.append({
            "architecture": p["architecture"],
            "Scenario 1 fleet": _describe(pd.Series(a)),
            "cost 1": _money(a["fleet_cost_usd"]),
            "MAU 1": f"{a['mau']:.3f}",
            "front 1": "yes" if a["on_front"] else "no",
            "Scenario 2 fleet": _describe(pd.Series(b)) + ("" if b["as_built"] else " (A4 twin)"),
            "cost 2": _money(b["fleet_cost_usd"]),
            "MAU 2": f"{b['mau']:.3f}",
            "Scenario 2": s2_status,
            "Scenario 2: peak served, wait": f"{b['peak_throughput']:.0f} trips/h, {b['wait_time']:.1f} min",
        })
    return pd.DataFrame(rows)


def write_task4(out_dir: Path = OUTPUT_DIR, results: dict | None = None) -> list[Path]:
    results = results or run()
    media = media_dir(out_dir)
    figs = [plot_fronts(results, media / "task4_fronts.png"),
            plot_mau_change(results["picks"], media / "task4_mau_change.png")]
    s1, s2 = results["s1"], results["s2"]
    sc1, sc2 = s1["scenario"], s2["scenario"]
    k1, k2, k2o = s1["knee"], s2["knee"], s2["knee_os3a"]
    picks = results["picks"].set_index("architecture")
    p2 = picks.loc["Pareto 2 (knee): 2 buses + 20 e-bikes"]
    new = picks.loc["Scenario 2 knee: 6 A4 buses + 30 e-bikes"]
    old = [picks.loc[n]["s2"] for n in picks.index if not n.startswith("Scenario 2")]
    roads = results["s2_roads_only"]
    slow = results["s2_formula_bikes_knee"]
    peak1, peak2 = sc1.peak_demand_per_h, sc2.peak_demand_per_h
    day1, day2 = sc1.demand["trips_per_hour"].sum() * sc1.demand_bin_h, sc2.demand["trips_per_hour"].sum() * sc2.demand_bin_h
    bus = all_variants(sc2).set_index("variant_id").loc[BUS.replace("-A3", "-A4")]
    bus1 = all_variants(sc1).set_index("variant_id").loc[BUS]
    cyc1, cyc2 = cycle_time_min(bus1, sc1), cycle_time_min(bus, sc2)
    types = lambda r: " / ".join(str(r["front_types"][t]) for t in FLEET_TYPES)  # noqa: E731

    lines = [
        "# Task 4: Second operating scenario, Red Line disruption",
        "",
        "Scenario 2 (PLAN.md Q29): the Red Line is down, and riders at Kendall need a road link to Park St / South "
        "Station, outside our system boundary. We picked it because our OS3A interviewee called the Red Line \"the "
        "weakest link\" and Cambridge has Red Line closures planned for 2026 [[21]](../docs/references.md#ref-21). "
        "Both scenarios run e-bikes at the 18 km/h assist (PLAN.md Q30) with fixed e-bike batteries, and keep the same "
        "design vector, fleet grid, Table 1 thresholds, riders-per-day ceilings and Appendix A weights, so the two "
        "tradespaces compare directly.",
        "",
        "## What changes in Scenario 2",
        "",
        _md_table(pd.DataFrame([
            {"input": "Trip length (road / bike)", "Scenario 1": f"{sc1.avg_trip_km:g} / {sc1.bike_trip_km:g} km",
             "Scenario 2": f"{sc2.avg_trip_km:g} / {sc2.bike_trip_km:g} km (Kendall to Park St / South Station)"},
            {"input": "Demand", "Scenario 1": f"{day1:,.0f} trips/day, peak {peak1:.0f}/h",
             "Scenario 2": f"{day2:,.0f} trips/day, peak {peak2:.0f}/h (peak ×1.5, 8:00–14:00)"},
            {"input": "Road speed cap", "Scenario 1": f"{sc1.speed_limit_kmh:g} km/h",
             "Scenario 2": f"{sc2.speed_limit_kmh:g} km/h (arterial roads)"},
            {"input": "Autonomy allowed", "Scenario 1": ", ".join(sc1.allowed_autonomy),
             "Scenario 2": ", ".join(sc2.allowed_autonomy) + " (Table 1: L4 or higher outside the boundary)"},
            {"input": "Wait / travel goals", "Scenario 1": f"{sc1.goal_wait_min:g} / {sc1.goal_travel_min:g} min",
             "Scenario 2": f"{sc2.goal_wait_min:g} / {sc2.goal_travel_min:g} min (Table 1, outside the boundary)"},
            {"input": "E-bike speed", "Scenario 1": f"{sc1.bike_assisted_speed_kmh:g} km/h assist",
             "Scenario 2": f"{sc2.bike_assisted_speed_kmh:g} km/h assist"},
        ])),
        "",
        f"A C8 bus round trip goes from {cyc1:.1f} to {cyc2:.1f} min, so each vehicle moves about "
        f"{cyc2 / cyc1:.1f}× fewer riders an hour while the peak grows 1.5×. The 5 km trip, the ×1.5 peak and the "
        "25 km/h cap are team estimates, not given data.",
        "",
        "## The two tradespaces",
        "",
        _md_table(pd.DataFrame([{
            "scenario": name, "feasible architectures": f"{r['feasible']:,}",
            "front (road / bike / mixed)": types(r),
            "cheapest feasible": f"{_describe(r['cheapest'])}, {_money(r['cheapest']['fleet_cost_usd'])}",
            "knee (first front point with MAU ≥ 0.94)": f"{_describe(r['knee'])}, {_money(r['knee']['fleet_cost_usd'])}, "
                                                      f"MAU {r['knee']['mau']:.3f}",
            "max MAU": f"{r['max_mau']:.3f}",
        } for name, r in (("Scenario 1: weekday", s1), ("Scenario 2: Red Line", s2))])),
        "",
        f"![Both Pareto fronts with the Task 3 picks]({media_link(figs[0])})",
        "",
        "## How the Task 3 architectures do in Scenario 2",
        "",
        "None of the Task 3 picks can run as built: their road vehicles are A3, and A3 isn't allowed once trips "
        "leave the boundary. For a fair test each A3 vehicle is swapped for its A4 twin (+$20,000 per vehicle), "
        "with everything else unchanged.",
        "",
        _md_table(_pick_rows(results["picks"])),
        "",
        f"- **None of the Task 3 picks survives.** Even as A4 twins they serve only "
        f"{min(o['peak_throughput'] for o in old):.0f}–{max(o['peak_throughput'] for o in old):.0f} of "
        f"{peak2:.0f} trips/h at the peak, fail Table 1 and fall to MAU "
        f"{min(o['mau'] for o in old):.2f}–{max(o['mau'] for o in old):.2f}. Bike-only doesn't rescue it: a 5 km "
        "ride at 18 km/h takes about 17 min.",
        f"- **The new knee is {_describe(k2)}, {_money(k2['fleet_cost_usd'])}, MAU {k2['mau']:.3f}**: "
        f"{k2['passenger_volume']:,.0f} trips/day, the full {k2['peak_throughput']:.0f}/h peak, a "
        f"{k2['wait_time']:.1f}-min wait, availability {k2['availability']:.2f} and a {k2['travel_time']:.1f}-min ride. "
        "It uses the same C8 bus and B1 e-bike as the Task 3 knee, just more of them, at A4.",
        f"- **E-bikes matter even more here:** {_describe(pd.Series(roads))} alone scores {roads['mau']:.3f} "
        f"(a {roads['wait_time']:.0f}-min wait); the 30 e-bikes add {k2['mau'] - roads['mau']:+.2f} for "
        f"{_money(k2['fleet_cost_usd'] - roads['fleet_cost_usd'])}.",
        f"- **The ceiling rises to {s2['max_mau']:.2f}:** Scenario 2 demand is above the top of the Appendix A "
        "volume and peak scales, so extra vehicles keep paying off further up the cost axis.",
        f"- **Nothing under {_money(s2['cheapest']['fleet_cost_usd'])} passes Table 1** in Scenario 2 "
        f"({_describe(s2['cheapest'])}); the lowest feasible MAU is {s2['min_mau']:.3f} (dashed line).",
        "",
        "### The Task 2 architectures in Scenario 2",
        "",
        _md_table(results["task2"]),
        "",
        "## Comparing the scenarios and resolving the conflict",
        "",
        f"![MAU of each architecture in both scenarios]({media_link(figs[1])})",
        "",
        "- **The two scenarios are limited by different things.** On a normal weekday demand caps volume and peak "
        "throughput, so cost decides the ranking; in a closure, capacity is the limit.",
        "- **The reference drops the most:** 8-seat shuttles give the least capacity per dollar, the same reason it "
        "was dominated in Task 3.",
        f"- **The new knee holds up in both:** MAU {new['s2'][OS3A]:.3f} in Scenario 2 and {new['s1'][OS3A]:.3f} on a "
        f"normal weekday (OS3A weights), but on a weekday it is overbuilt: the Task 3 knee gets "
        f"{p2['s1'][OS3A]:.3f} for {_money(p2['s1']['fleet_cost_usd'])}.",
        f"- **Two different best answers:** {_money(k1['fleet_cost_usd'])} for a weekday vs. "
        f"{_money(k2['fleet_cost_usd'])} for a closure, a {k2['fleet_cost_usd'] / k1['fleet_cost_usd']:.1f}× gap. "
        "Our resolution (PLAN.md Q31, Task 5): buy the weekday knee with A4 buses, and add a leased surge kit of "
        "the same buses and e-bikes during closure weeks, which are announced weeks ahead "
        "[[21]](../docs/references.md#ref-21).",
        "",
        "### Sensitivity",
        "",
        f"- **OS3A weights:** the Scenario 2 knee is {_describe(k2o)}, {_money(k2o['fleet_cost_usd'])}, "
        f"MAU {k2o[OS3A]:.3f}; the Scenario 1 knee is {_describe(s1['knee_os3a'])}.",
        f"- **E-bikes at the Appendix B formula speed:** the Scenario 2 knee becomes {_describe(slow)}, "
        f"{_money(slow['fleet_cost_usd'])}, MAU {slow['mau']:.3f}.",
        "- **Not in the model:** we count capital cost only (PLAN.md Q21). Running six buses with attendants costs "
        "far more than running two, which this comparison doesn't show.",
        "",
    ]
    path = out_dir / "task4_red_line.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return [path, *figs]
