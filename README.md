# Team - H1-13 OS4

> **📊 Results explorer: https://au5y.github.io/os4/** — interactive Tasks 1–3 (utility curves, architecture candidates, tradespace with Pareto fronts). Rebuilt by CI on every push to `main`.

## Authors
- Sanjay Bisht
- Yonis Aliyow
- Austin Miller
- Robert Wright

Models for **EM.411 Systems Engineering, Opportunity Set #4: Tradespace Exploration and Concept Selection** (Fall 2026).

The assignment asks for a tradespace exploration of an autonomous, battery-electric surface transportation system serving East Cambridge (Cambridge Crossing/Lechmere, Central Square, MIT/Kendall Square). The system can use autonomous road vehicles, autonomous e-bikes (the assignment's "autonomous bicycles", Appendix D), or both. The full assignment is in [`resources/OS4_FA26_v1.pdf`](resources/OS4_FA26_v1.pdf) and the grading rubric in [`resources/rubric.md`](resources/rubric.md).

## Status

| Task | Weight | Topic | Status | Code |
|------|--------|-------|--------|------|
| 1 | 10% | Stakeholder utility (SAU → MAU, Cases A–C) | Done: hand calcs (Yonis) and code agree; Table 4 validation; proposed weights | `utility.py` |
| 2 | 25% | Technical system model, 5 architecture instances | Model done; five architectures picked (Q24) | `scenario.py`, `vehicle.py`, `fleet.py`, `model.py` |
| 3 | 20% | Tradespace, Pareto frontier, reference architecture | Tradespace and fronts done; reference and three picks open (F, G) | `tradespace.py` |
| 4 | 15% | Second operating scenario | On hold | `scenario.task4_scenario` (stub) |
| 5 | 20% | Concept recommendation | Not started | slides |
| 6 | 10% | Life-cycle / extensibility memo | Not started | slides |

**Due:** Thursday, November 12, 2026, 10:00am. The slides go to Canvas as a single PDF; the model (this code plus `outputs/media/os4_model.xlsx`) is submitted separately as a ZIP.

Every modeling decision and open question is in [`docs/PLAN.md`](docs/PLAN.md) (questions are numbered **Q#**; code that depends on one is tagged with its number). The main ones so far:

- **Scenario:** weekday on-demand last-mile service from a Kendall hub to Lechmere and Central; links 1.9 / 1.6 / 3.3 km measured on OpenStreetMap; road speed capped at 21 km/h (20 mph posted, signals); e-bikes a fixed 18 km/h assist.
- **MoPs:** peak throughput is the demand actually served (Q17); availability is *service* availability, the chance the vehicles in service can carry each hour's demand (Q19); travel time is the average Kendall trip; cost is vehicle capital only (Q21).
- **Design space:** every feasible Appendix C/D vehicle, road fleets 1–300 and bike fleets 5–250 with steps that widen as fleets grow (road step 1 up to 15; bikes step 5 up to 50), alone or mixed: ~3.9 million architectures. The reference architecture and anchors (EZRide, MBTA bus and MIT shuttle service levels, `data/anchors.csv`) are plotted on every tradespace. Table 1 thresholds (1,500 trips/day, 150/h peak, 50/h off-peak) screen architectures out before scoring.
- **E-bike batteries:** fixed (Appendix B) and removable with spare packs (team proposal) are both kept as alternate pathways.
- **Weights:** Appendix A for the official MAU; `os3a_reweight` (Task 1 reflection, also plotted on Task 3) as the team proposal. Travel time and bike share are reported but not weighted.

## Repository layout

```
os4/
├── README.md, CLAUDE.md   This file; conventions for Claude Code sessions
├── resources/             Assignment PDF, OS3A report, slides (Git LFS); rubric.md
├── docs/PLAN.md           Game plan, decisions (Q#), open questions, Wikibooks appendix
├── docs/references.md     Bibliography for the sources tagged in PLAN.md
├── data/                  Input tables from the assignment, as CSV
│   ├── sau_*.csv            Appendix A SAU points (sau_travel_time, sau_bike_share: reported, not weighted)
│   ├── mau_weights.csv      Appendix A stakeholder weights
│   ├── mau_weights_proposed.csv  Team weight set (os3a_reweight; PLAN.md Q10)
│   ├── mau_test_cases.csv   Task 1 Cases A, B, C
│   ├── demand_mit_kendall.csv  Appendix B hourly demand at MIT/Kendall
│   ├── road_*.csv           Appendix C road vehicle components
│   └── bike_*.csv           Appendix D e-bike components
├── src/os4/
│   ├── data.py            CSV loaders
│   ├── utility.py         Task 1: SAU / MAU, inverse SAU, weight sets, sensitivity
│   ├── scenario.py        Operating scenarios and Table 1 requirements
│   ├── vehicle.py         Task 2: Appendix B vehicle equations, removable batteries, variants
│   ├── fleet.py           Task 2: capacity, volume, wait, service availability, cost
│   ├── model.py           Task 2: evaluate one architecture; the five architectures
│   ├── tradespace.py      Task 3: pruning, vectorized tradespace, Pareto front, charts, report
│   ├── plots.py           Task 1 and Task 2 figures and reports
│   ├── export.py          Excel backup with live formulas (outputs/media/os4_model.xlsx)
│   ├── site.py            Results explorer generator (outputs/site/)
│   ├── site_template/     Its HTML/CSS/JS (vanilla, no build step)
│   └── __main__.py        Entry point (`python -m os4`)
├── tests/                 pytest tests
├── .github/workflows/     CI: tests, model run, artifacts, GitHub Pages, releases
└── outputs/               Generated (git-ignored): Markdown reports; media/ figures, CSVs, workbook; site/ explorer
```

Costs in the CSVs are in **US dollars** (the PDF lists most of them in $1000s).

## Setup

### 1. Install uv (recommended) or Python

We use [uv](https://docs.astral.sh/uv/) to manage Python and dependencies. It installs the right Python version for you and pins every package version in `uv.lock`, so everyone runs the same environment. Check whether you have it:

```bash
uv --version
```

If not, install it:

- **macOS / Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `brew install uv`)
- **Windows (PowerShell):** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

With uv you can skip the Python install below and steps 4–5.

**Without uv:** you need Python **3.10 or newer** (developed on 3.12). Check what you have:

```bash
python3 --version
```

If it's missing or too old:

- **macOS:** `brew install python@3.12`, or use the installer from [python.org](https://www.python.org/downloads/)
- **Ubuntu/Debian:** `sudo apt install python3 python3-venv python3-pip`
- **Windows:** install from [python.org](https://www.python.org/downloads/) and tick "Add python.exe to PATH". Use `py` in place of `python3` below.

### 2. Install Git LFS

The PDFs and PowerPoint files in `resources/` are stored with [Git LFS](https://git-lfs.com). Without it, those files check out as small text pointers instead of the real documents. Check whether you have it:

```bash
git lfs version
```

If that fails, install it:

- **macOS:** `brew install git-lfs`
- **Ubuntu/Debian:** `sudo apt install git-lfs`
- **Windows:** included with [Git for Windows](https://gitforwindows.org); otherwise download from [git-lfs.com](https://git-lfs.com)

Then enable it once per machine:

```bash
git lfs install
```

### 3. Clone the repository

```bash
git clone git@github.com:au5y/os4.git os4
cd os4
```

If you cloned before installing Git LFS, fetch the real files with:

```bash
git lfs install
git lfs pull
```

New binary files of these types are stored in LFS automatically (see `.gitattributes`). To add another type, run `git lfs track "*.ext"` and commit `.gitattributes`.

### 4. Install dependencies

**With uv** (one command; creates `.venv/` and installs the package plus dev tools from `uv.lock`):

```bash
uv sync --extra dev
```

You don't need to activate anything: prefix commands with `uv run` (see [Running](#running)). After pulling changes that touch `pyproject.toml` or `uv.lock`, run `uv sync --extra dev` again. To add a dependency, use `uv add <package>` (or `uv add --optional dev <package>` for dev tools) and commit both `pyproject.toml` and `uv.lock`.

### 5. Without uv: create a virtual environment and install with pip

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows (PowerShell or cmd)
```

Then install the package in editable mode plus the dev tools:

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

Dependencies (declared in `pyproject.toml`):

| Package    | Used for                                   |
|------------|--------------------------------------------|
| numpy      | Numerical calculations                     |
| pandas     | Data tables, architecture enumeration      |
| matplotlib | Utility curves and tradespace plots        |
| openpyxl   | Exporting model tables to Excel for Canvas |
| pytest     | Tests (dev only)                           |

## Running

```bash
uv run python -m os4      # or: uv run os4   (without uv: python -m os4 inside the activated venv)
uv run pytest             # tests (~20 s; without uv: pytest)
```

`python -m os4` runs Tasks 1–3, the results explorer and the Excel backup, and writes everything to `outputs/`. It takes about 1.5 minutes and a couple of GB of memory, because each battery case scores 1–2.6 million architectures (with a progress bar per run). Options: `--only` / `--skip` steps (`task1 task2 task3 sensitivity site excel`), `--out DIR`, `--no-progress`; see `python -m os4 --help`. It prints the key tables as it goes, for example:

```
Task 1 (MAU):
case  u_passenger_volume  u_peak_throughput  u_wait_time  u_availability   mau  rank
   A                 0.4               0.35         0.83             0.7 0.613     3
   B                 1.0               0.50         0.61             0.6 0.639     2
   C                 0.3               0.35         0.91             0.8 0.651     1
```

| Output | Contents |
|---|---|
| `task1_cases.md` | Task 1 report: Cases A–C, figures, full breakdown, weight sensitivity, MAU under each weight set |
| `task1_*.csv`, `task1_*.png` | Case table, MAU per weight set, weight sensitivity; SAU curves and MAU breakdown figures |
| `task2_model.md` | Task 2 report: scenario inputs, equations, five-architecture table, removable batteries, hand-calc check |
| `task2_variants.csv`, `task2_architectures.csv` | Every feasible vehicle variant; the five architectures |
| `task2_*.png` | MAU and cost of the five architectures; vehicle availability and speed vs. the cap |
| `task3_tradespace.md` | Task 3 report: both battery cases, requirements table, load-factor sensitivity, Pareto fronts |
| `task3_tradespace_*.png` | MAU vs. cost scatter with Pareto front and utopia point (Appendix A and os3a_reweight MAU, each battery case) |
| `task3_fleet_size_*.png` | One panel per vehicle type, colored by fleet size, against the front |
| `task3_load_factor_fronts.png` | Pareto front at 25 / 50 / 75 / 100% load factor |
| `task3_speed_sensitivity.md` | Task 3 sensitivity: Appendix B e-bike speed, the road cap at the 20 mph posted limit, and no riders-per-day ceiling |
| `task3_speed_*.png` | E-bike availability at both speeds; Pareto fronts, baseline vs. each speed change |
| `task3_pareto_front_*.csv` | The Pareto front of each battery case |
| `site/` | The results explorer (see below) |
| `os4_model.xlsx` | Excel backup for the submission: SAU tables, weights, Cases A–C, scenario, every vehicle variant and the five architectures, all with live formulas checked against Python |

## Results explorer

**Online:** https://au5y.github.io/os4/ (published from `main` by CI).

**Locally:** run `uv run python -m os4`, then open `outputs/site/index.html` (double-click it; no server or network needed). Or download the `os4-outputs-<sha>` artifact from any CI run (Actions → model) and open `site/index.html` from it.

- **Task 1:** interactive SAU curves (the four Appendix A attributes) with Cases A–C, MAU under each weight set, weight sensitivity.
- **Task 2:** the five current architectures, ~50 highlighted candidates (cheapest per chassis/frame, Pareto knee, evenly spaced front points, best MAU per dollar) each with the reason it was picked, and a filterable table of every vehicle variant.
- **Task 3:** utility-vs-cost scatter (log cost, zoom/pan, hover, click to pin), Pareto front and utopia point, fixed vs. removable batteries, Appendix A vs. os3a_reweight MAU, color by fleet type or size, filters, and a linked table. Road-only, bike-only and front architectures are all included; mixed fleets are a seeded sample (the page says "showing X of Y").
- **Components:** the Appendix C/D tables and how to read a variant id (`C5-P1-G3-M2-A3` = chassis C5, battery P1, charger G3, motor M2, autonomy A3). Hovering any variant id in a table decodes it.
- **Selecting:** click ☆ on any architecture; the selection is kept in your browser and can be exported as CSV from the ★ Selected page.

## Model Lab (local, optional)

An interactive version of the model for trying scenarios: pick a preset (the standard weekday scenario, the Task 4 candidates (Red Line disruption, point-to-point network, winter, a.m. rush only) and the Task 3 sensitivity cases), change any input (demand bins, speeds, trip lengths, autonomy, thresholds, ceilings, batteries, utility weights, fleet grid), press **Calculate** and watch the progress bar while the server scores the tradespace (a few seconds). Results show the summary, the tradespace with its Pareto front, the reference and anchors, and the five Task 2 architectures under your inputs.

```bash
uv run python -m os4.lab          # or: uv run os4-lab; then open http://127.0.0.1:8411
```

- **Save and compare:** save configs and runs in the browser (localStorage), compare up to four saved runs (overlaid fronts, summary, and only the inputs that differ), and export/import them as JSON files.
- **Cache:** results are cached on disk in `~/.cache/os4-lab` (`--cache-dir`, `--no-cache`), keyed by the config and the model's code, so re-opening a run is instant.
- **Self-hosting:** `--host 0.0.0.0 --port 8411`. There is no login; keep it behind a VPN or a reverse proxy with auth. One run at a time uses up to about 1 GB of memory.
- The lab lives in `src/os4/lab/` and is not part of `outputs/site` or the GitHub Pages explorer.

## Continuous integration

`.github/workflows/model.yml` runs on every pull request and push to `main`: install with uv, run the tests, run the model, and upload `outputs/` as the `os4-outputs-<sha>` artifact (kept 90 days). Pushes to `main` also publish `outputs/site` to GitHub Pages. Pushing a tag such as `v1.0-os4` creates a GitHub Release with the workbook, CSVs, figures and reports attached: use that for the copy we submit.

Generated files are never committed (`outputs/` is git-ignored); rebuild them with `uv run python -m os4`.
