# OS4 Model: How to Run It

**EM.411 Opportunity Set #4, H2 Team 13:** Sanjay Bisht, Yonis Aliyow, Austin Miller, Robert Wright
**Model version:** tag `v1.2-final-draft` (Tasks 1–5, the frozen final inputs and outputs; PLAN.md Q28)
**GitHub repository:** https://github.com/au5y/os4 (source, tagged versions, releases; see Section 7)
**Results explorer (GitHub Pages):** https://au5y.github.io/os4/

This ZIP holds the model, its input data and its formulas. The slides, with our answers and diagrams, are submitted separately as a PDF.

## 1. What is in the ZIP

| Item | What it is |
|---|---|
| `os4-windows.exe`, `os4-mac`, `os4-linux` | **Standalone executables** (Windows, Apple Silicon Mac, Linux): double-click to run the model, with no installation (Section 3, Option A). |
| `OS4_How_to_Run.pdf` | This document. |
| `os4_model.xlsx` | **Excel backup with live formulas:** the SAU tables, weights, Cases A–C, the operating scenario, every vehicle variant and the five Task 2 architectures. It opens with no installation, and its values are checked against the Python model. |
| `src/os4/` | The Python model (the formulas). See Section 5 for which file does what. |
| `data/` | All inputs as CSV: the Appendix A SAUs and weights, the Appendix B demand, the Appendix C/D components, the team's proposed SAUs and weight sets, and the anchor architectures. |
| `tests/` | Automated checks (129 tests): Appendix A Table 4 values, hand calculations, and agreement between the vectorized tradespace and the per-architecture model. |
| `scripts/` | Builds the standalone executables, this PDF and the submission ZIP. |
| `pyproject.toml`, `uv.lock` | The dependency list and exact pinned versions. |
| `docs/PLAN.md` | Every modeling decision and assumption, numbered Q1–Q31; code that depends on one is tagged `PLAN.md Q#`. |
| `README.md` | Full developer documentation. |

## 2. Quickest look, no install

1. **Open `os4_model.xlsx`.** Every result cell is a formula you can trace back to the input tables.
2. **Browse the results online** at https://au5y.github.io/os4/: interactive SAU curves, the five architectures, and the tradespace with its Pareto fronts.

## 3. Run the model

Pick one option. Option A needs nothing installed; Options B and C run the source code and need Python 3.10 or newer (uv installs it for you).

### Option A: the standalone executable (no Python at all)

The executables are in the top-level folder of this ZIP: `os4-windows.exe` (Windows), `os4-mac` (Apple Silicon Macs, M1 or later) and `os4-linux`. Each bundles Python, the model and its data. They are also on the Release page https://github.com/au5y/os4/releases/tag/v1.2-final-draft.

- **Double-click the one for your computer** to open the Model Lab in your browser (Section 4). A console window stays open while it runs; close it to stop. It takes a few seconds to start.
- **Run it with `run`** in a terminal for the same batch run as `python -m os4`, for example `os4-windows.exe run` or `./os4-mac run`. It writes `outputs/` next to the executable.
- **Windows:** if SmartScreen says "Windows protected your PC", click **More info → Run anyway**.
- **macOS:** the app isn't signed by Apple, so the first launch shows "Apple can't verify". In Terminal, in the unzipped folder, run `xattr -d com.apple.quarantine os4-mac`, then double-click it again. Or go to System Settings → Privacy & Security → Open Anyway. Intel Macs: use Option B.

### Option B: uv (recommended for running from source; macOS, Windows or Linux)

[uv](https://docs.astral.sh/uv/) installs the right Python and the exact dependency versions from `uv.lock`.

```bash
# Install uv once (macOS/Linux; on Windows see docs.astral.sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh

# From the unzipped folder:
uv sync --extra dev          # install the dependencies (one time)
uv run python -m os4         # run Tasks 1-5; writes everything to outputs/
uv run pytest -q             # optional: run the tests (~1 min)
```

### Option C: plain Python and pip

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m os4
```

### What a run produces

A full run takes about 3–4 minutes and a couple of GB of memory. It scores about 1.75 million feasible weekday architectures (e-bikes at 18 km/h with removable batteries; MAU = the team's OS3A reweight, Appendix A for comparison), the fixed-battery comparison case, and the two Task 4 scenarios. Key tables print as it goes. Task 1 (Cases A–C with the Appendix A weights, the assignment's check) should print:

```
case  u_passenger_volume  u_peak_throughput  u_wait_time  u_availability   mau  rank
   A                 0.4               0.35         0.83             0.7 0.613     3
   B                 1.0               0.50         0.61             0.6 0.639     2
   C                 0.3               0.35         0.91             0.8 0.651     1
```

| Output (in `outputs/`) | Contents |
|---|---|
| `task1_cases.md` | Task 1: Cases A–C, SAU/MAU breakdown, weight sensitivity |
| `task2_model.md` | Task 2: scenario inputs, equations, the five architectures, hand-calculation check |
| `task3_tradespace.md` | Task 3: tradespace, requirements screen, Pareto fronts, reference architecture |
| `task3_speed_sensitivity.md` | Task 3 sensitivity: e-bike assist speed, road speed cap, riders-per-day ceiling |
| `task4_red_line.md` | Task 4: Scenario 2 (Red Line disruption) vs. Scenario 1, both Pareto fronts, the Task 3 picks in each |
| `task5_recommendation.md` | Task 5: the recommended concept (base fleet plus a surge kit for closures), what we rule out |
| `media/` | Every figure (PNG), CSV and the regenerated `os4_model.xlsx` |
| `site/index.html` | The results explorer, offline (double-click to open) |

Useful options: `python -m os4 --only task1` re-runs only Task 1, in about a second. `--out DIR` writes the outputs somewhere else. `python -m os4 --help` lists every option.

## 4. Model Lab: change the weights or inputs

```bash
uv run python -m os4 lab --open     # or double-click an executable (Option A)
```

This opens a local page at http://127.0.0.1:8411. To use it:

1. Pick a preset, such as the standard weekday scenario.
2. Edit any input: the **utility weights**, demand, speeds, trip lengths, requirement thresholds or the fleet grid.
3. Press **Calculate**.

The page shows the tradespace, the Pareto front and the five Task 2 architectures under your inputs. The page starts from the OS3A reweight (the weights every submitted result uses) and lets you edit them; edited weights are what-if runs only.

## 5. Where the formulas are

| Task | File(s) in `src/os4/` | What it computes |
|---|---|---|
| 1 | `utility.py` | Piecewise-linear SAUs from the Appendix A tables, and the additive MAU for Cases A–C |
| 2 | `scenario.py`, `vehicle.py`, `fleet.py`, `model.py` | The operating scenario; the Appendix B vehicle equations; the fleet MoPs (volume, peak throughput, wait time, availability); the five architectures |
| 3 | `tradespace.py`, `speed_sensitivity.py` | The full design grid, the Table 1 requirement screen, the Pareto front and knee, and the sensitivity cases |
| 4 | `scenario.py` (`red_line_scenario`), `task4.py` | Scenario 2, the Red Line disruption; both tradespaces; the Task 3 picks in each scenario |
| 5 | `task5.py` | The recommended concept: base fleet, surge kit, checks and what is ruled out |
| All | `plots.py`, `export.py`, `site.py` | Figures and reports, the Excel workbook, and the results explorer |

Assumptions and deviations from the assignment are in `docs/PLAN.md`, by number. For example, Q17 defines peak throughput, Q19 defines availability, Q21 defines cost, Q28 records the frozen weekday baseline, Q29 sets the Task 4 scenario and Q31 records the Task 5 concept.

## 6. AI disclosure

**Most of the code in this model was generated with an AI coding assistant**: Claude Code, running Anthropic's Claude models. Team members directed the work and made the modeling decisions. They checked the generated code and its outputs before it was merged.

- **Decisions were made by people.** Every scenario choice, assumption and deviation from Appendix B is in `docs/PLAN.md` (Q1–Q31); decisions are labeled with who made them and when.
- **Results were checked by people.** Task 1 was calculated by hand (Yonis Aliyow) independently of the code, and the two agree with each other and with Appendix A Table 4. Team members reviewed the generated equations against Appendix B and corrected them where they were wrong; PLAN.md records those corrections, for example to the first draft of the wait-time equations. The Task 2 report includes a hand-calculation check of one architecture, and the Excel workbook recomputes the results with live formulas as a second implementation to compare against.
- **Automated tests back the checks.** These include the Table 4 values, the hand calculations, and agreement between the vectorized tradespace and the per-architecture model. CI reruns them on every change.

**How to verify this from the Git history.** Each commit that the assistant co-wrote ends with a `Co-Authored-By: Claude …` line. Of the 96 commits up to `v1.1-weekday-final`, 60 carry that line (dated 2026-10-29 to 2026-11-11). This count is a lower bound: a commit without the line may still contain AI-generated code. The others include the team members' own commits, such as the Task 1 hand calculations and the SAU validation table. Tagged versions mark what was frozen: `v1.0-os4` (outputs and executables), `v1.1-weekday-final` (the standard weekday baseline) and `v1.2-final-draft` (Tasks 1–5, this submission). In a clone of the repository:

```bash
# commits co-written with the AI assistant
git log --grep="Co-Authored-By: Claude" --oneline
# commits without the line
git log --invert-grep --grep="Co-Authored-By: Claude" --oneline
# tagged, frozen versions, and what the submitted baseline contains
git tag -n1
git show v1.2-final-draft --stat
```

Pull request descriptions on GitHub (https://github.com/au5y/os4/pulls) also end with "Generated with Claude Code".

## 7. The model on GitHub

Everything in this ZIP comes from the team's public GitHub repository, where each version is tagged and its outputs are published.

| What | Where |
|---|---|
| Source code, data and history | https://github.com/au5y/os4 |
| Tagged versions | https://github.com/au5y/os4/tags: `v1.0-os4`, `v1.1-weekday-final`, `v1.2-final-draft` |
| Releases (outputs, inputs, workbook, executables per tag) | https://github.com/au5y/os4/releases |
| This submission's release | https://github.com/au5y/os4/releases/tag/v1.2-final-draft |
| Modeling decisions Q1–Q31 | https://github.com/au5y/os4/blob/main/docs/PLAN.md (also https://au5y.github.io/os4/plan.html) |
| Results explorer (GitHub Pages) | https://au5y.github.io/os4/: Tasks 1–3 interactive, Tasks 4–5 write-ups |
| Automated runs (tests and model on every change) | https://github.com/au5y/os4/actions |
| Pull requests (each change, with its description) | https://github.com/au5y/os4/pulls?q=is%3Apr |
