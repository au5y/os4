# CLAUDE.md

EM.411 OS4 (H2 Team 13): tradespace exploration for an autonomous surface transportation system in East Cambridge / Kendall Square. Python model in `src/os4/`; the assignment is `resources/OS4_FA26_v1.pdf` and the team's game plan is `docs/PLAN.md`.

## Commands

```bash
uv sync --extra dev        # install
uv run pytest -q           # tests (~1 min)
uv run python -m os4       # run Tasks 1-5 and write everything to outputs/
uv sync --extra dev --extra build && uv run python scripts/build_exe.py   # standalone executable -> dist/os4
```

## Layout

- `data/`: assignment tables as CSV (Appendix A SAUs and weights, Appendix B demand, Appendix C/D components) plus the team's proposed SAUs and weight sets.
- `src/os4/`: `utility.py` (Task 1 SAU/MAU), `scenario.py` (operating scenarios), `vehicle.py` (Appendix B vehicle equations), `fleet.py` (fleet performance), `model.py` (`evaluate`, five architectures, Task 3 reference architecture and anchors from `data/anchors.csv`, requirement checks), `tradespace.py` (Task 3 grid, pruning, Pareto front, knee zoom), `speed_sensitivity.py` (Task 3 sensitivity: 18 km/h e-bike assist, road cap at the posted limit, no riders-per-day ceiling), `task4.py` (Task 4: Scenario 2, the Red Line disruption, vs. Scenario 1, both with 18 km/h e-bikes), `task5.py` (Task 5 recommended concept), `plots.py` (figures and Markdown reports), `export.py` (Excel backup with live formulas), `site.py` + `site_template/` (static results explorer written to `outputs/site/`; vanilla JS, data as `data/*.js` globals so it opens from `file://`; it iterates over whatever tradespace columns exist; each task page has a "Write-up" section, filled from `outputs/<report>.md` through a `<!-- report:<stem> -->` slot, and an "Interactive" section).
- `src/os4/paths.py`: `DATA_DIR`, `DOCS_DIR`, `OUTPUT_DIR` for a checkout or the PyInstaller executable (`scripts/build_exe.py` with entry point `scripts/os4_entry.py`; it bundles `data/` and `docs/`, and outputs go next to the executable). Resolve repo-root files (`data/`, `docs/`, `outputs/`) through it, never `Path(__file__).parents[2]`, or the executable breaks; files inside the package (`site_template/`, `lab/static/`) are bundled and can stay relative to `__file__`. `python -m os4 lab` dispatches to the Lab so the one executable runs both.
- `src/os4/lab/`: the Model Lab, a local server (`python -m os4.lab`, standard library only) with presets (`presets.py`), JSON configs (`config.py`), cached runs (`run.py`) and its own page (`static/`); not part of `outputs/site` or GitHub Pages.
- `outputs/`: generated; git-ignored. Markdown reports at the top level (also rendered into the explorer's Reports page), figures/CSVs/workbook in `outputs/media/`, the explorer in `outputs/site/`. CI (`.github/workflows/model.yml`) uploads it as an artifact on every PR and push to `main`; a `v*` tag publishes a Release.
- `resources/`: PDFs and slides in Git LFS; `resources/rubric.md` is the grading rubric (check deliverables against it).

## Conventions

- Modeling decisions live in `docs/PLAN.md` as **Q1–Q31**, numbered in document order. Each is a heading `#### <a id="qN"></a>QN. <the question>?` followed by **Answer** (labeled Decision / From OS3A / Assumption / Deviation from Appendix B) and **Discussion**; other mentions link to it as `[QN](#qN)`. Code that depends on one is tagged `PLAN.md QN`. Renumbering means updating every tag in `src/`, `tests/`, README and this file. Open questions are the group's call: implement a clearly labeled default, don't decide them.
- Sources are numbered in `docs/references.md` and tagged in line as `[[n]](references.md#ref-n)`.
- Any change to an equation must keep `tradespace.tradespace` (vectorized) in step with `fleet.py` / `model.evaluate`; `tests/test_tradespace.py` checks they match.
- Work on a branch and open a PR into `main`.

## Appendix: Fundamentals of Transportation extracts

Transcribed from the extracts appended to the assignment (OS4 PDF pp. 10–11) [[1]](docs/references.md#ref-1), which reproduce sections of the Wikibooks *Fundamentals of Transportation* pages [[4]](docs/references.md#ref-4), [[5]](docs/references.md#ref-5). Wikibooks text is licensed CC BY-SA 4.0.

### Frequency determination (*Network Design and Frequency* [[4]](docs/references.md#ref-4))

There are a number of ways that planners may determine a reasonable frequency of service on a route. The most common methods are:

- **Policy headways.** Many transit agencies will determine specific headways that meet policy goals, usually related to providing a minimum level of service along a route when demand on the route is low. This could include 30-minute or 60-minute headways, for example.
- **Minimum headways.** As discussed in the unit on transit operations, bus and rail systems have minimum headways, based on capacity limitations. In cases when demand on a route is very high, these minimum headways can be used to assign the maximum frequencies on the route.
- **Load management.** In many cases where policy headways or minimum headways do not apply, the typical way of determining frequencies is based on managing load at the *peak load point* along the route. The peak load point is that point along the route that experiences the largest number of passengers per hour. Let X be the highest allowable ratio of demand to supply (volume to capacity), with values between 0 and 1 (with 1 when volume = capacity). Then:

$$\frac{P}{f \cdot N_{car} \cdot C_{car}} \le X \quad\text{or}\quad f \ge \frac{P}{X \cdot N_{car} \cdot C_{car}}$$

with P = volume at peak load point (passengers/hr); X = maximum allowable volume-to-capacity ratio, 0 ≤ X ≤ 1; N<sub>car</sub> = number of cars in a train (= 1 for buses); C<sub>car</sub> = number of passengers per car.

For a bus route operated with 55-passenger buses, a demand of 360 passengers per hour past the peak load point, and an allowable load factor of X = 0.90, the frequency must be

$$f \ge \frac{360\ \text{passengers/hr}}{0.90 \cdot 1 \cdot (55\ \text{passengers/bus})} = 7.27\ \text{buses/hr}$$

This would give the planner options for this route such as 7.5 buses/hr (8-min headways) or 8 buses/hr (7.5-min headways), or even higher frequencies.

### Capacity (*Transit Operations and Capacity* [[5]](docs/references.md#ref-5))

Capacity in transit operations is measured as the maximum number of passengers that can be carried past a single point on a fixed route, in a given period of time. The most common measure of capacity is in terms of passengers per hour.

In transit operations, we define the time between vehicles past a given point as the *headway* (or time headway), usually in minutes. The inverse of the headway is called the *frequency*, essentially capturing the number of vehicles per unit time past a certain point on a route, usually measured in vehicles per hour.

$$\text{Frequency (veh/hr)}\quad f = \frac{60\ \text{min/hr}}{h} \qquad\qquad \text{Headway (in min)}\quad h = \frac{60\ \text{min/hr}}{f}$$

As an example, a route with a 10-minute headway has a frequency of 6 vehicles per hour.

With this in mind, the capacity of a transit route is given as the product of the frequency and the maximum number of persons per vehicle:

$$\text{Capacity (passengers/hr) on the route} = C_{route} = f \cdot N_{car} \cdot C_{car}$$

where f = frequency on the route (veh/hr); N<sub>car</sub> = number of cars per train (= 1 for bus); C<sub>car</sub> = maximum number of persons per car (or bus).

As examples, a bus route with a frequency of 6 buses/hr and a maximum of 55 persons on each bus has a capacity of 330 passengers per hour. A rail line with a frequency of 15 trains/hr (4 min headways) with 6 cars per train and a maximum of 150 persons per car has a capacity of 13,500 passengers per hour.

### Sample problem (*Transit Operations and Capacity* [[5]](docs/references.md#ref-5))

**Problem:** A transit agency has an existing 8.5-mile bus route (in one direction) where the average speed "between" stops is 16.9 miles per hour. The route has 22 stops along the route. If the average dwell time at each stop is 18 seconds, what is the average bus speed along the route as a whole? And, if a 5-minute layover is required at the far end of the route, what is the total round-trip travel time? Assume the time for the inbound trip is identical in time to the outbound trip.

**Solution:**
- Total travel time = (8.5 mi) / (16.9 mi/hr) + (22 stops)·(18 sec/stop)·(1 hr / 3600 sec) = 0.613 hr = 37 minutes (rounded up to the nearest minute)
- The average speed = (8.5 mi / 0.613 hr) = 13.9 mph.
- The total round-trip time = 37 min + 5 min layover + 37 min = 79 min

### How the model uses these

- **Capacity:** `fleet.vehicle_capacity_per_h` is C<sub>route</sub> = f · N<sub>car</sub> · C<sub>car</sub> per vehicle, with f = 60 / cycle time, N<sub>car</sub> = 1, and C<sub>car</sub> = pax × the vehicle's load factor: Appendix B's 0.75 for road vehicles; for e-bikes, riders per trip by seats (1-seat 1 rider, 2-seat 4/3 riders; `Scenario.bike_load_factors`, PLAN.md Q16).
- **Cycle time:** `fleet.cycle_time_min` follows the sample problem: running time at the average speed plus dwell, with the empty return leg in place of the inbound trip (Q3 deadhead).
- **Headway:** the wait model (Q18) starts from headway / 2, with headway = 60 / departures per hour at the Kendall hub.
- **Fleet sizing:** load management gives a cited rule. Departures needed f ≥ P / (X · 1 · C<sub>car</sub>); vehicles needed N = f × cycle / 60 / availability. For the C2 car (4 pax × 0.75 = 3 riders per trip, 11-min cycle, availability 0.922) at P = 150 trips/h: X = 1 gives f ≥ 50/h and N = 10, the capacity-only minimum; X = 0.8 gives f ≥ 62.5/h and N = 13. The model uses X = 0.90 only to size the reference architecture; a utilization factor X on every architecture's capacity was not adopted (PLAN.md Q22). Instead, the utilization ceilings (PLAN.md Q22) screen out overworked fleets: at most 25 rides per car per day for C1–C3, so the smallest feasible C2 fleet is 24, not 10.
- The *Network Design and Frequency* page also gives Mohring's cost-minimizing frequency, f = √(VOT · p / (2 · C · T)), which trades waiting time against operating cost. It is not in the assignment's extracts, and we don't model operating cost (Q21).
