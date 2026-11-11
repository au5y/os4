"""Task 5: the recommended concept (PLAN.md Q31), from the two Task 4 tradespaces.

The concept is a fleet that scales for closures, built from the Scenario 2 (Red Line) knee's vehicles: its A4
road vehicle (allowed outside the boundary) and its e-bike with removable batteries. The **full fleet** is that
knee. The **base fleet** is the cheapest fleet of the same two vehicles, no larger than the full fleet, that meets
Table 1 on a normal weekday with MAU >= 0.94 (the knee rule). The **surge kit** is the difference, leased or
shared during closure weeks. MAU is the decision MAU, the OS3A reweight (PLAN.md Q10).

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

APPX = task4.APPX


def base_fleet(results: dict) -> dict:
    """The cheapest weekday fleet of the closure knee's two vehicles that passes Table 1 with MAU >= 0.94."""
    s1, k2 = results["s1"]["scenario"], results["s2"]["knee"]
    road, n_road, bike, n_bike = task4._ids(k2)
    best = None
    for nr in range(0 if bike else 1, n_road + 1):
        for nb in ([0] if bike is None else range(0, n_bike + 1, 5)):
            if nr == 0 and nb == 0:
                continue
            r = task4.score(road if nr else None, nr, bike if nb else None, nb, s1)
            ok = r["meets_thresholds"] and r["meets_bike_ceiling"] and r["meets_car_ceiling"] and r["mau"] >= task4.KNEE_MAU
            if ok and (best is None or r["fleet_cost_usd"] < best["fleet_cost_usd"]):
                best = r
    return best


def concept(results: dict) -> dict:
    """The base fleet, the full fleet, the surge kit and the checks behind them."""
    s1, s2 = results["s1"]["scenario"], results["s2"]["scenario"]
    k2 = results["s2"]["knee"]
    road, n_road, bike, n_bike = task4._ids(k2)
    base = base_fleet(results)
    full2 = task4.score(road, n_road, bike, n_bike, s2)
    full1 = task4.score(road, n_road, bike, n_bike, s1)
    winter = task4.score(task4.a4_twin(base["road_variant"], s1), base["n_road"], base["bike_variant"],
                         base["n_bike"], winter_scenario())
    return {"base1": base, "full2": full2, "full1": full1, "winter": winter, "knee1": results["s1"]["knee"],
            "surge_road": n_road - base["n_road"], "surge_bike": n_bike - base["n_bike"],
            "surge_usd": full2["fleet_cost_usd"] - base["fleet_cost_usd"],
            "base_on_front": task4.on_front(base, results["s1"]["front"])}


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
        {"attribute": "Passenger volume (trips/day)", "Scenario 1: base fleet": f"{b['passenger_volume']:,.0f}",
         "Scenario 2: full fleet": f"{f['passenger_volume']:,.0f}", "requirement": f"≥ {s1.min_daily_volume:,.0f}"},
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
        {"attribute": "MAU (OS3A reweight, decision)", "Scenario 1: base fleet": f"{b['mau']:.3f}",
         "Scenario 2: full fleet": f"{f['mau']:.3f} (knee)", "requirement": "-"},
        {"attribute": "MAU (Appendix A, comparison)", "Scenario 1: base fleet": f"{b[APPX]:.3f}",
         "Scenario 2: full fleet": f"{f[APPX]:.3f}", "requirement": "-"},
        {"attribute": "Fleet cost", "Scenario 1: base fleet": f"${b['fleet_cost_usd']:,.0f} ({_describe(pd.Series(b))})",
         "Scenario 2: full fleet": f"${f['fleet_cost_usd']:,.0f} ({_describe(pd.Series(f))})", "requirement": "-"},
    ])


def _count(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 'es' if word.endswith('s') else 's'}"


def write_task5(out_dir: Path = OUTPUT_DIR, results: dict | None = None) -> list[Path]:
    results = results or task4.run()
    c = concept(results)
    r1, r2 = results["s1"], results["s2"]
    s1, s2 = r1["scenario"], r2["scenario"]
    fig = task4.plot_fronts(results, media_dir(out_dir) / "task5_fronts.png", stars={
        "Base fleet (Scenario 1)": ("s1", c["base1"]), "Full fleet (Scenario 2)": ("s2", c["full2"])},
        title="The recommended concept on both Pareto fronts")
    b, f, w, k1 = c["base1"], c["full2"], c["winter"], c["knee1"]
    road_v, bike_v = f["road_variant"], f["bike_variant"]
    road_cost = task4.score(road_v, 1, None, 0, s1)["fleet_cost_usd"] if isinstance(road_v, str) else 0
    bike_cost = task4.score(None, 0, bike_v, 1, s1)["fleet_cost_usd"] if isinstance(bike_v, str) else 0
    spares = bike_v.rsplit("-S", 1)[1] if isinstance(bike_v, str) and "-S" in bike_v else "0"
    p1, p2 = front_parts(r1["front"]), front_parts(r2["front"])
    markers = reference_and_anchor_table(s1)
    ref = markers.iloc[0]
    mit = markers[markers["architecture"].str.contains("MIT", case=False)]
    mit_note = "" if mit.empty else f" and today's MIT shuttles ({_describe(mit.iloc[0])}, MAU {mit.iloc[0]['mau']:.3f})"
    ref2 = results["picks"].set_index("architecture").iloc[3]["s2"]
    bike_only = {k: r["front_types"]["bike-only"] for k, r in (("s1", r1), ("s2", r2))}
    join = ", ".join
    seen = {x for parts in (p1, p2) for k in ("autonomy", "road battery") for x in parts[k]}
    never = [x for x in ("A5", "P5", "P6", "P7") if x not in seen]
    kit = " + ".join(x for x in (_count(c["surge_road"], "bus") if c["surge_road"] else "",
                                 _count(c["surge_bike"], "e-bike") if c["surge_bike"] else "") if x)
    base_txt = _describe(pd.Series(b))

    lines = [
        "# Task 5: Recommended concept, a fleet that scales for closures",
        "",
        f"**Own {base_txt} for every weekday (${b['fleet_cost_usd']:,.0f}); add a surge kit of {kit} when the Red "
        f"Line closes (${f['fleet_cost_usd']:,.0f} in all).** PLAN.md Q31 records the decision; Task 4 "
        "(`task4_red_line.md`) has the two tradespaces it comes from. MAU is the team's OS3A reweight (PLAN.md Q10); "
        "Appendix A is shown for comparison.",
        "",
        "## The concept",
        "",
        "- **What it is:** an on-demand service out of a hub at the Kendall T. Large electric buses carry the "
        "peak; in a closure a pool of e-bikes at the hub takes the riders who would otherwise wait for the next bus"
        + (", and on weekdays too." if b["n_bike"] else ".")
        ,
        f"- **The road vehicle:** {road_v}, ${road_cost:,.0f}, at A4 so the same vehicle may run into Boston.",
        f"- **The e-bike:** {bike_v}, ${bike_cost:,.0f} including its share of spare packs: a removable battery "
        f"with {spares} spare packs per bike, swapped at the hub (PLAN.md Q15), at the 18 km/h assist (Q6).",
        f"- **Normal weekdays (Scenario 1):** the base fleet, {base_txt}, ${b['fleet_cost_usd']:,.0f}, between "
        "Kendall, Lechmere and Central.",
        f"- **Closure weeks (Scenario 2):** a surge kit of {kit} (+${c['surge_usd']:,.0f}, leased or shared) brings "
        "the fleet to the Scenario 2 knee and runs Kendall to Park St / South Station. Closures are announced weeks "
        "ahead [[21]](../docs/references.md#ref-21), so there is time to set it up.",
        "- **Who is on board:** an attendant on every bus until Massachusetts allows driverless operation.",
        "",
        _md_table(_attr_rows(c, s1, s2)),
        "",
        f"![The recommended concept on both fronts]({media_link(fig)})",
        "",
        "## How we got here",
        "",
        f"1. **Task 3:** out of {r1['feasible']:,} feasible weekday fleets, {len(r1['front'])} are on the front. The "
        f"knee is {_describe(k1)} (${k1['fleet_cost_usd']:,.0f}, MAU {k1['mau']:.3f}).",
        f"2. **Task 4:** the Red Line closure breaks the Task 3 picks that rely on A3 road vehicles or a small fleet. "
        f"The closure knee is {_describe(r2['knee'])} (${r2['knee']['fleet_cost_usd']:,.0f}, MAU "
        f"{r2['knee']['mau']:.3f}).",
        f"3. **Our call:** build the weekday fleet from the closure knee's vehicles, so one fleet can grow into the "
        f"other. The cheapest such fleet that passes Table 1 with MAU ≥ 0.94 on a weekday is {base_txt} "
        f"(${b['fleet_cost_usd']:,.0f}, MAU {b['mau']:.3f}), "
        + (f"${b['fleet_cost_usd'] - k1['fleet_cost_usd']:,.0f} more than the weekday knee for "
           f"{b['mau'] - k1['mau']:+.3f} MAU" if b["fleet_cost_usd"] != k1["fleet_cost_usd"] else "the weekday knee itself")
        + f" ({'on' if c['base_on_front'] else 'just off'} the weekday front). We see that as the price of a fleet "
        "that can grow into the closure knee instead of being replaced.",
        f"4. **Why not buy everything now:** the full fleet scores {c['full1']['mau']:.3f} on a weekday, only "
        f"{c['full1']['mau'] - b['mau']:+.3f} for {f['fleet_cost_usd'] / b['fleet_cost_usd']:.1f}× the money, and the "
        "extra vehicles would sit idle most of the year.",
        "",
        "**Decision rule:** weight each scenario by how often it happens. Closures are planned and announced, so a "
        "leased surge kit works; if closures became frequent or unplanned, we would buy more of the fleet outright.",
        "",
        "**Did it hold up?**",
        "",
        f"- With the Appendix A weights (comparison) the knees are {_describe(r1['knee_appx'])} on a weekday and "
        f"{_describe(r2['knee_appx'])} in a closure.",
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
        f"- **Never on either front:** {join(never) or 'none'}. On 1.75–5 km trips the extra range or autonomy is "
        "never used, so it is just cost.",
        f"- **Small shuttles:** our reference ({_describe(ref)}, MAU {ref['mau']:.3f}){mit_note} are dominated on a "
        f"weekday; in a closure the reference (as its A4 twin) falls to {ref2['mau']:.3f}"
        f"{'' if ref2['meets_thresholds'] else ' and fails Table 1'}.",
        f"- **Bike-only fleets:** {bike_only['s1']} points on the weekday front, {bike_only['s2']} in a closure: a 5 km "
        "ride at 18 km/h takes about 17 min, and a bike-only fleet leaves out riders who can't ride.",
        "- **A3, even though it wins on weekdays:** it can never serve the closure, so it would lock us out of the "
        "surge plan.",
        "",
        "## Would it work in Kendall Square?",
        "",
        "- **Why we think yes:** nothing in it is exotic. Electric buses are on the road today, people here already "
        "use bike share (Bluebikes has about 5,500 bikes [[28]](../docs/references.md#ref-28)), and a couple of big "
        "buses is close to what EZRide runs now (PLAN.md Q23).",
        "- **What makes us doubt it:** driverless operation isn't legal in Massachusetts yet, so the buses run with "
        "attendants, and their wages are the biggest cost our capital-only model leaves out (PLAN.md Q21). Swapping "
        "packs needs hub staff, also outside the model. E-bikes don't serve riders with disabilities, so the buses "
        "must be wheelchair-accessible.",
        "- **Our view on autonomy:** in the model it is a cost, not a benefit: A5 never appears on either front, and "
        "the closure front is A4 only because Table 1 requires it. Its real value, taking the attendant off the bus, "
        "is an operating saving the model can't see. We pay for A4 because the closure needs it, but plan on a "
        "person on board.",
        "- **Verdict:** yes, as a staged, staffed pilot. The surge plan only works if the MBTA or a leasing company "
        "can supply buses during closures, so that partnership comes first.",
        "- **Limits of our method:** capital cost only, a fixed 75% load factor that flatters big buses, and our own "
        "Scenario 2 estimates (5 km, ×1.5 peak, 25 km/h).",
        "",
    ]
    path = out_dir / "task5_recommendation.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return [path, fig]
