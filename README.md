# os4

Models for **EM.411 Systems Engineering, Opportunity Set #4: Tradespace Exploration and Concept Selection** (Fall 2026).

The assignment asks for a tradespace exploration of an autonomous, battery-electric surface transportation system serving East Cambridge (Cambridge Crossing/Lechmere, Central Square, MIT/Kendall Square). The system can use autonomous road vehicles, autonomous e-bikes, or both. The full assignment is in [`resources/OS4_FA26_v1.pdf`](resources/OS4_FA26_v1.pdf).

> **Status:** project scaffold only. The input data is transcribed and loadable, but no model logic is implemented yet.

## Repository layout

```
os4/
├── resources/            Assignment PDF
├── data/                 Input tables from the assignment, as CSV
│   ├── sau_*.csv           Appendix A: single-attribute utility points
│   ├── mau_weights.csv     Appendix A: stakeholder weights
│   ├── mau_test_cases.csv  Task 1: Cases A, B, C
│   ├── demand_mit_kendall.csv  Appendix B: hourly demand at MIT/Kendall
│   ├── road_*.csv          Appendix C: road vehicle components
│   └── bike_*.csv          Appendix D: e-bike components
├── src/os4/
│   ├── data.py           CSV loaders
│   ├── utility.py        Task 1: SAU / MAU functions        (TODO)
│   ├── vehicle.py        Task 2: EV / e-bike model          (TODO)
│   ├── fleet.py          Task 2: fleet performance model    (TODO)
│   ├── tradespace.py     Tasks 3-4: enumeration, Pareto     (TODO)
│   └── __main__.py       Entry point (`python -m os4`)
├── tests/                pytest tests
└── outputs/              Generated plots/tables (git-ignored)
```

Costs in the CSVs are in **US dollars** (the PDF lists most of them in $1000s).

## Setup

### 1. Install Python

You need Python **3.10 or newer** (developed on 3.12). Check what you have:

```bash
python3 --version
```

If it's missing or too old:

- **macOS:** `brew install python@3.12`, or use the installer from [python.org](https://www.python.org/downloads/)
- **Ubuntu/Debian:** `sudo apt install python3 python3-venv python3-pip`
- **Windows:** install from [python.org](https://www.python.org/downloads/) and tick "Add python.exe to PATH". Use `py` in place of `python3` below.

### 2. Clone the repository

```bash
git clone git@github.com:au5y/os4.git os4
cd os4
```

### 3. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows (PowerShell or cmd)
```

### 4. Install dependencies

This installs the package in editable mode plus the dev tools:

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

Dependencies (declared in `pyproject.toml`):

| Package    | Used for                                   |
|------------|--------------------------------------------|
| numpy      | Numerical calculations                     |
| pandas     | Data tables, architecture enumeration      |
| matplotlib | Tradespace plots                           |
| openpyxl   | Exporting model tables to Excel for Canvas |
| pytest     | Tests (dev only)                           |

## Running

```bash
python -m os4      # or just: os4
```

Right now this loads every input table and prints a summary:

```
Loaded 16 input tables:
  bike_battery               3 rows
  ...
Model not implemented yet (see src/os4/utility.py, vehicle.py, fleet.py, tradespace.py).
```

Run the tests:

```bash
pytest
```

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
