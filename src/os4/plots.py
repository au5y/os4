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
    out_dir.mkdir(parents=True, exist_ok=True)
    weights = load_weights()
    full = case_table(weights)
    table = full.round(4)
    csv_path = out_dir / "task1_cases.csv"
    mau_path = out_dir / "task1_mau.csv"
    sens_path = out_dir / "task1_weight_sensitivity.csv"
    md_path = out_dir / "task1_cases.md"
    table.to_csv(csv_path, index=False)
    weight_sets = compare_weight_sets().round(4)
    weight_sets.to_csv(mau_path, index=False)
    sensitivity = weight_sensitivity(weights=weights).round(4)
    sensitivity.to_csv(sens_path, index=False)
    sau_png = plot_sau_curves(out_dir / "task1_sau_curves.png")
    mau_png = plot_mau_breakdown(out_dir / "task1_mau_breakdown.png")

    summary = full[["case", *(f"u_{a}" for a in ATTRIBUTES), "mau", "rank"]].round(3)
    weight_text = ", ".join(f"{LABELS[a][0]} {weights[a]:.2f}" for a in ATTRIBUTES)
    md_path.write_text(
        "# Task 1: Multi-attribute utility\n\n"
        f"Generated by `python -m os4`. Weights: {weight_text}.\n\n"
        "## Cases A–C\n\n"
        f"{_md_table(summary)}\n"
        f"![Single-attribute utility curves with cases A–C]({sau_png.name})\n\n"
        f"![MAU by case, split by weighted attribute]({mau_png.name})\n\n"
        "## Full breakdown\n\n"
        f"{_md_table(table)}\n"
        "## MAU under each weight set\n\n"
        "`appendix_a` is the given weighting; `os3a_reweight` is the team's proposal from OS3A (PLAN.md Q8).\n\n"
        f"{_md_table(weight_sets.round(3))}\n"
        "## Weight sensitivity (each weight ±0.1, others renormalized)\n\n"
        f"{_md_table(sensitivity.round(3))}"
    )
    return [csv_path, mau_path, sens_path, md_path, sau_png, mau_png]
