# Team - H1-13 OS4
## Authors
- Sanjay Bisht
- Yonis Aliyow
- Austin Miller
- Robert Wright

Models for **EM.411 Systems Engineering, Opportunity Set #4: Tradespace Exploration and Concept Selection** (Fall 2026).

The assignment asks for a tradespace exploration of an autonomous, battery-electric surface transportation system serving East Cambridge (Cambridge Crossing/Lechmere, Central Square, MIT/Kendall Square). The system can use autonomous road vehicles, autonomous e-bikes, or both. The full assignment is in [`resources/OS4_FA26_v1.pdf`](resources/OS4_FA26_v1.pdf).

> **Status:** Task 1 (SAU/MAU) is implemented and tested, and writes its table and figures to `outputs/`. The Task 2+ model functions are still stubbed with their signatures and docstrings. Tests for unimplemented functions are marked as expected failures and start passing as each function is filled in.

## Repository layout

```
os4/
├── resources/            Assignment PDF, OS3A report, recitation slides (Git LFS)
├── docs/PLAN.md          Game plan and open team questions for Tasks 1-2
├── docs/references.md    Bibliography for the sources tagged in PLAN.md
├── data/                 Input tables from the assignment, as CSV
│   ├── sau_*.csv           Appendix A: single-attribute utility points
│   │                       (sau_travel_time / sau_bike_share: team-proposed SAUs)
│   ├── mau_weights.csv     Appendix A: stakeholder weights
│   ├── mau_weights_proposed.csv  Team-proposed weight sets from OS3A (PLAN.md Q8)
│   ├── mau_test_cases.csv  Task 1: Cases A, B, C
│   ├── demand_mit_kendall.csv  Appendix B: hourly demand at MIT/Kendall
│   ├── road_*.csv          Appendix C: road vehicle components
│   └── bike_*.csv          Appendix D: e-bike components
├── src/os4/
│   ├── data.py           CSV loaders
│   ├── utility.py        Task 1: SAU / MAU functions, weight sensitivity
│   ├── plots.py          Task 1: case table and figures
│   ├── export.py         Excel backup (outputs/os4_model.xlsx); Task 1 sheets done
│   ├── scenario.py       Operating scenario definitions     (stubbed)
│   ├── vehicle.py        Task 2: EV / e-bike model          (stubbed)
│   ├── fleet.py          Task 2: fleet performance model    (stubbed)
│   ├── model.py          Task 2: (fleet, scenario) -> MoPs, MAU, cost (stubbed)
│   ├── tradespace.py     Tasks 3-4: enumeration, Pareto     (stubbed)
│   ├── site.py           Static results explorer (outputs/site/)
│   ├── site_template/    Its HTML/CSS/JS (vanilla, no build step)
│   ├── export.py         Excel export for the ZIP submission (stubbed)
│   └── __main__.py       Entry point (`python -m os4`)
├── tests/                pytest tests
└── outputs/              Generated plots/tables (git-ignored)
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
```

This loads every input table, prints the Task 1 results, and writes them to `outputs/`:

```
Task 1 (MAU):
case  u_passenger_volume  u_peak_throughput  u_wait_time  u_availability   mau  rank
   A                 0.4               0.35         0.83             0.7 0.613     3
   B                 1.0               0.50         0.61             0.6 0.639     2
   C                 0.3               0.35         0.91             0.8 0.651     1
  wrote outputs/task1_cases.csv
  wrote outputs/task1_mau.csv
  wrote outputs/task1_weight_sensitivity.csv
  wrote outputs/task1_cases.md
  wrote outputs/task1_sau_curves.png
  wrote outputs/task1_mau_breakdown.png
  wrote outputs/os4_model.xlsx
```

| Output | Contents |
|---|---|
| `task1_cases.md` | Task 1 report: summary table, both figures embedded, full breakdown, weight sensitivity |
| `task1_cases.csv` | Cases A–C: raw values, each SAU, weighted contributions kᵢ·uᵢ, MAU, rank |
| `task1_sau_curves.png` | The four Appendix A SAU curves with Cases A–C marked |
| `task1_mau_breakdown.png` | Stacked bars of each case's MAU split by weighted attribute |
| `task1_mau.csv` | MAU and rank of each case under the Appendix A and team-proposed (`os3a_reweight`) weights |
| `task1_weight_sensitivity.csv` | Each weight moved ±0.1 (others rescaled): MAUs, ranking, whether it flipped |
| `os4_model.xlsx` | Excel backup for the submission: SAU tables, weight sets, Cases A–C with live formulas and Python checks, sensitivity |

For the weight sensitivity sweep (each weight ±0.1, others renormalized, with the resulting A/B/C ranking):

```bash
uv run python -c "from os4.utility import weight_sensitivity; print(weight_sensitivity().round(3))"
```

Run the tests:

```bash
uv run pytest      # without uv: pytest
```

## Results explorer

`python -m os4` also writes a static, interactive website to `outputs/site/` (`os4.site.write_site`):

```bash
uv run python -m os4
# then open outputs/site/index.html in a browser (double-click it; no server needed)
```

Or download the `os4-outputs-<sha>` artifact from the latest CI run on GitHub (Actions → model) and open `site/index.html` from it.

- **Task 1:** interactive SAU curves (the four Appendix A ones plus the two proposed ones) with Cases A–C, MAU under each weight set, weight sensitivity.
- **Task 2:** the five current architectures, ~50 highlighted candidates (cheapest per chassis/frame, Pareto knee, evenly spaced front points, best MAU per dollar), each with the reason it was picked, and a filterable table of every vehicle variant.
- **Task 3:** utility-vs-cost scatter (log cost, zoom/pan, hover, click to pin), Pareto front and utopia point, fixed vs. removable battery case, Appendix A vs. extended MAU, color by fleet type or size, filters, and a linked table. All road-only and bike-only architectures and every front point are included; mixed fleets are a seeded stratified sample (the page says "showing X of Y").
- **Selecting:** click ☆ on any architecture; the selection is kept in your browser and can be exported as CSV from the ★ Selected page.

The data sit in `outputs/site/data/*.js` (plain JSON assigned to `window.OS4`), so the pages work from `file://` with no network access.

## Assignment tasks

| Task | Weight | Topic                                              | Module          |
|------|--------|----------------------------------------------------|-----------------|
| 1    | 10%    | Stakeholder utility (SAU → MAU, Cases A–C)         | `utility.py`    |
| 2    | 25%    | Technical system model, 5 architecture instances   | `vehicle.py`, `fleet.py` |
| 3    | 20%    | Tradespace exploration, Pareto frontier            | `tradespace.py` |
| 4    | 15%    | Second operating scenario, sensitivity             | `tradespace.py` |
| 5    | 20%    | Concept recommendation                             | (slides)        |
| 6    | 10%    | Life-cycle / extensibility memo                    | (slides)        |

**Due:** Thursday, November 12, 2026, 10:00am. The slides go to Canvas as a single PDF; the model (this code plus exported data) is submitted separately as a ZIP.
