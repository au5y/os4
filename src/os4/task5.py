"""Task 5: the recommended concept (PLAN.md Q31), from the two Task 4 tradespaces.

The concept is a fleet that scales for closures: own the weekday knee's buses and e-bikes, bought at A4 so
the same buses may run outside the boundary (the "base fleet"), and add a leased "surge kit" of the same
vehicles during Red Line closures, which takes the fleet to the Scenario 2 knee (the "full fleet").

``write_task5`` writes ``outputs/task5_recommendation.md`` with its figure in ``outputs/media/``. It reuses
``task4.run()``'s results when given them.
"""

from pathlib import Path

import pandas as pd

from os4 import task4
from os4.model import reference_and_anchor_table
from os4.plots import OUTPUT_DIR, _md_table, media_dir, media_link
from os4.scenario import winter_scenario
from os4.tradespace import _describe

BUS_A4 = task4.BUS.replace("-A3", "-A4")
BASE = (BUS_A4, 2, task4.BIKE, 20)   # weekday knee, A4 buses
FULL = (BUS_A4, 6, task4.BIKE, 30)   # Scenario 2 knee


def concept(results: dict) -> dict:
    """The base fleet, the full fleet and the checks behind them."""
    s1, s2 = results["s1"]["scenario"], results["s2"]["scenario"]
    base1 = task4.score(*BASE, s1)
    full2 = task4.score(*FULL, s2)
    full1 = task4.score(*FULL, s1)
    base_a3 = task4.score(task4.BUS, 2, task4.BIKE, 20, s1)
    winter = task4.score(*BASE, task4.fixed_batteries(winter_scenario()))
    return {"base1": base1, "full2": full2, "full1": full1, "base_a3": base_a3, "winter": winter,
            "surge_usd": full2["fleet_cost_usd"] - base1["fleet_cost_usd"],
            "base_on_front": task4.on_front(base1, results["s1"]["front"])}


def front_parts(front: pd.DataFrame) -> dict[str, list[str]]:
    """Which components appear on a front: autonomy, road battery and charger, bike frame and battery."""
    road = front["road_variant"].dropna().str.split("-", expand=True)
    bike = front["bike_variant"].dropna().str.split("-", expand=True)
    pick = lambda df, i: sorted(df[i].unique()) if len(df) else []  # noqa: E731
    return {"chassis": pick(road, 0), "road battery": pick(road, 1), "road charger": pick(road, 2),
            "autonomy": pick(road, 4), "bike frame": pick(bike, 0), "bike battery": pick(bike, 1)}


def _attr_rows(c: dict, s1, s2) -> pd.DataFrame:
    b, f = c["base1"], c["full2"]
    return pd.DataFrame([
        {"attribute": "Passenger volume (trips/day)", "Scenario 1: base fleet": f"{b['passenger_volume']:,.0f} (all demand)",
         "Scenario 2: full fleet": f"{f['passenger_volume']:,.0f} (all demand)", "requirement": f"≥ {s1.min_daily_volume:,.0f}"},
        {"attribute": "Peak throughput (trips/h)",
         "Scenario 1: base fleet": f"{b['peak_throughput']:.0f} (capacity {b['fleet_capacity_per_h']:.0f})",
         "Scenario 2: full fleet": f"{f['peak_throughput']:.0f} (capacity {f['fleet_capacity_per_h']:.0f})",
         "requirement": f"≥ {s1.min_peak_throughput:.0f}"},
        {"attribute": "Average wait (min)", "Scenario 1: base fleet": f"{b['wait_time']:.1f}",
         "Scenario 2: full fleet": f"{f['wait_time']:.1f}",
         "requirement": f"≤ {s1.goal_wait_min:g} in / ≤ {s2.goal_wait_min:g} out (goal)"},
        {"attribute": "Availability", "Scenario 1: base fleet": f"{b['availability']:.3f}",
         "Scenario 2: full fleet": f"{f['availability']:.3f}", "requirement": f"≥ {s1.benchmark_availability:g} (benchmark)"},
        {"attribute": "Travel time (min)", "Scenario 1: base fleet": f"{b['travel_time']:.1f}",
         "Scenario 2: full fleet": f"{f['travel_time']:.1f}",
         "requirement": f"≤ {s1.goal_travel_min:g} in / ≤ {s2.goal_travel_min:g} out (goal)"},
        {"attribute": "MAU (Appendix A)", "Scenario 1: base fleet": f"{b['mau']:.3f}",
         "Scenario 2: full fleet": f"{f['mau']:.3f} (knee)", "requirement": "-"},
        {"attribute": "MAU (OS3A reweight)", "Scenario 1: base fleet": f"{b[task4.OS3A]:.3f}",
         "Scenario 2: full fleet": f"{f[task4.OS3A]:.3f}", "requirement": "-"},
        {"attribute": "Fleet cost", "Scenario 1: base fleet": f"${b['fleet_cost_usd']:,.0f} (2 buses + 20 e-bikes)",
         "Scenario 2: full fleet": f"${f['fleet_cost_usd']:,.0f} (6 buses + 30 e-bikes)", "requirement": "-"},
    ])


def write_task5(out_dir: Path = OUTPUT_DIR, results: dict | None = None) -> list[Path]:
    results = results or task4.run()
    c = concept(results)
    r1, r2 = results["s1"], results["s2"]
    s1, s2 = r1["scenario"], r2["scenario"]
    fig = task4.plot_fronts(results, media_dir(out_dir) / "task5_fronts.png", stars={
        "Base fleet (Scenario 1)": ("s1", c["base1"]), "Full fleet (Scenario 2)": ("s2", c["full2"])},
        title="The recommended concept on both Pareto fronts")
    b, f, a3, w = c["base1"], c["full2"], c["base_a3"], c["winter"]
    p1, p2 = front_parts(r1["front"]), front_parts(r2["front"])
    markers = reference_and_anchor_table(s1)
    ref = markers.iloc[0]
    mit = markers[markers["architecture"].str.contains("MIT", case=False)]
    mit_note = "" if mit.empty else f" and today's MIT shuttles ({_describe(mit.iloc[0])}, MAU {mit.iloc[0]['mau']:.3f})"
    ref2 = results["picks"].set_index("architecture").loc["Reference: 6 small shuttles", "s2"]
    bike_only = {k: r["front_types"]["bike-only"] for k, r in (("s1", r1), ("s2", r2))}
    join = ", ".join

    lines = [
        "# Task 5: Recommended concept, a fleet that scales for closures",
        "",
        f"**Own 2 A4 buses and 20 e-bikes for every weekday (${b['fleet_cost_usd']:,.0f}); add 4 buses and 10 "
        f"e-bikes when the Red Line closes (${f['fleet_cost_usd']:,.0f} in all).** PLAN.md Q31 records the decision; "
        "Task 4 (`task4_red_line.md`) has the two tradespaces it comes from.",
        "",
        "## The concept",
        "",
        "- **What it is:** an on-demand service out of a hub at the Kendall T. Two 30-seat electric buses carry the "
        "peak, and a pool of e-bikes at the hub takes the riders who would otherwise wait for the next bus. That "
        "combination is what kept showing up on both Pareto fronts.",
        f"- **The bus:** {BUS_A4}, 30 seats, ${task4.score(BUS_A4, 1, None, 0, s1)['fleet_cost_usd']:,.0f}: the "
        "smallest pack (P1, 92 km), because no bus drives that far in a day here; the G3 fast charger, the first "
        "upgrade that moved MAU in Task 3; and A4 (+$20,000) so the same bus may run into Boston.",
        f"- **The e-bike:** {task4.BIKE}, one seat, fixed battery, ${task4.score(None, 0, task4.BIKE, 1, s1)['fleet_cost_usd']:,.0f}: "
        "the cheapest frame and pack, on almost every front point.",
        f"- **Normal weekdays (Scenario 1):** the base fleet, 2 buses + 20 e-bikes, ${b['fleet_cost_usd']:,.0f}, "
        "between Kendall, Lechmere and Central.",
        f"- **Closure weeks (Scenario 2):** a surge kit of 4 buses + 10 e-bikes (+${c['surge_usd']:,.0f}, leased or "
        "shared) runs Kendall to Park St / South Station. Closures are announced weeks ahead "
        "[[21]](../docs/references.md#ref-21), so there is time to set it up.",
        "- **Who is on board:** an attendant on every bus until Massachusetts allows driverless operation.",
        "",
        _md_table(_attr_rows(c, s1, s2)),
        "",
        f"![The recommended concept on both fronts]({media_link(fig)})",
        "",
        "## How we got here",
        "",
        f"1. **Task 3:** out of {r1['feasible']:,} feasible weekday fleets, {len(r1['front'])} are on the front. The "
        f"knee, {_describe(r1['knee'])} (${r1['knee']['fleet_cost_usd']:,.0f}, MAU {r1['knee']['mau']:.3f}), is where "
        "extra money stops buying more than seconds of wait.",
        f"2. **Task 4:** the Red Line closure breaks every Task 3 pick (A3 isn't allowed outside the boundary, and "
        f"even as A4 they can't carry the peak). The new knee, {_describe(r2['knee'])} "
        f"(${r2['knee']['fleet_cost_usd']:,.0f}, MAU {r2['knee']['mau']:.3f}), uses the same bus and e-bike.",
        f"3. **Our call:** buy the weekday knee with A4 buses. On paper its A3 twin beats it "
        f"(MAU {a3['mau']:.4f} vs. {b['mau']:.4f} for ${a3['fleet_cost_usd']:,.0f} vs. ${b['fleet_cost_usd']:,.0f}); "
        f"{'the A4 base fleet is dominated only by that twin' if not c['base_on_front'] else 'the A4 base fleet is on the front'}. "
        f"We see the ${b['fleet_cost_usd'] - a3['fleet_cost_usd']:,.0f} as the price of a fleet that can grow into the "
        "closure knee instead of being replaced.",
        f"4. **Why not buy everything now:** the full fleet scores {c['full1']['mau']:.3f} on a weekday, only "
        f"{c['full1']['mau'] - b['mau']:+.3f} for {f['fleet_cost_usd'] / b['fleet_cost_usd']:.1f}× the money, and four "
        "buses would sit idle most of the year.",
        "",
        "**Decision rule:** weight each scenario by how often it happens. Closures are planned and announced, so a "
        "leased surge kit works; if closures became frequent or unplanned, we would buy more of the fleet outright.",
        "",
        "**Did it hold up?**",
        "",
        f"- With the OS3A weights the weekday knee doesn't move ({_describe(r1['knee_os3a'])}); the closure knee "
        f"needs 5 more e-bikes ({_describe(r2['knee_os3a'])}).",
        f"- In a winter run (road cap 18 km/h, e-bikes 12 km/h, battery range ×0.75) the base fleet "
        f"{'still passes' if w['meets_thresholds'] else 'fails'} Table 1 at MAU {w['mau']:.3f} "
        f"(wait {w['wait_time']:.1f} min, availability {w['availability']:.2f}).",
        "",
        "## What we rule out",
        "",
        f"Almost everything is dominated: {len(r1['front'])} of {r1['feasible']:,} feasible fleets are on the weekday "
        f"front and {len(r2['front'])} of {r2['feasible']:,} on the closure front.",
        "",
        _md_table(pd.DataFrame([{"component on the front": k, "Scenario 1": join(p1[k]) or "-",
                                 "Scenario 2": join(p2[k]) or "-"} for k in p1])),
        "",
        "- **A5 and big batteries:** on 1.75–5 km trips the extra range is never used, so it is just cost.",
        f"- **Small shuttles:** our reference ({_describe(ref)}, MAU {ref['mau']:.3f}){mit_note} "
        f"are dominated on a weekday; in a closure the reference (as its A4 twin) falls to {ref2['mau']:.3f} and fails "
        "Table 1. Small shuttles were our starting idea, so this was the hardest lesson.",
        f"- **Bike-only fleets:** {bike_only['s1']} points on the weekday front, {bike_only['s2']} in a closure: a 5 km "
        "ride takes about 17 min.",
        "- **A3, even though it wins on weekdays:** it can never serve the closure, so it would lock us out of the "
        "surge plan.",
        "",
        "## Would it work in Kendall Square?",
        "",
        "- **Why we think yes:** nothing in it is exotic. 30-seat electric buses are on the road today, people here "
        "already use bike share (Bluebikes has about 5,500 bikes [[28]](../docs/references.md#ref-28)), and our "
        "cheapest front point, two big buses, is close to what EZRide runs now (PLAN.md Q23).",
        "- **What makes us doubt it:** driverless operation isn't legal in Massachusetts yet, so the buses run with "
        "attendants, and their wages are the biggest cost our capital-only model leaves out (PLAN.md Q21). E-bikes "
        "don't serve riders with disabilities, so the buses must be wheelchair-accessible.",
        "- **Our view on autonomy:** in the model it is a cost, not a benefit: every bus on the weekday front is A3 "
        "and A5 never appears; the closure front is A4 only because Table 1 requires it. Its real value, taking the "
        "attendant off the bus, is an operating saving the model can't see. We pay for A4 because the closure needs "
        "it, but plan on a person on board.",
        "- **Verdict:** yes, as a staged, staffed pilot. The surge plan only works if the MBTA or a leasing company "
        "can supply buses during closures, so that partnership comes first.",
        "- **Limits of our method:** capital cost only, a fixed 75% load factor that flatters big buses, and our own "
        "Scenario 2 estimates (5 km, ×1.5 peak, 25 km/h).",
        "",
    ]
    path = out_dir / "task5_recommendation.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return [path, fig]
