#!/usr/bin/env python3
"""
Line plot: MAX2 KO algebraic propagation — node values vs iteration.

Reads PropagationFigure/data/max2_ko_iteration_trace.csv (full 38-node trace)
and plots the 11 nodes that are on the MAX2-KO propagation spine. Strigolactone
and D14 are dropped from the plot (both stay at 1.0; user can include them
manually if desired).

Outputs:
    figures/iteration_traces.png
    figures/iteration_traces.svg
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRACE_CSV = ROOT / "data" / "max2_ko_iteration_trace.csv"
OUT_PNG = ROOT / "figures" / "iteration_traces.png"
OUT_SVG = ROOT / "figures" / "iteration_traces.svg"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from color_palette import OKABE_ITO, get_all_9_colors  # noqa: E402

PLOT_NODES = [
    "MAX2",
    "SMXL678",
    "BES1",
    "SPL9",
    "BRC1",
    "HB21",
    "NCED3",
    "ABA",
    "PIN1",
    "PIN3",
    "Shoot_Branching",
]
PLOT_ITERATIONS = 60  # convergence at t=19; 60 leaves a clear plateau


def load_trace() -> tuple[list[int], dict[str, list[float]]]:
    with open(TRACE_CSV, encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        cols = rdr.fieldnames or []
        rows = list(rdr)
    iterations = [int(r["iteration"]) for r in rows]
    series = {n: [float(r[n]) for r in rows] for n in PLOT_NODES if n in cols}
    return iterations, series


def assign_colors() -> dict[str, str]:
    pool = [c for c in OKABE_ITO.values() if c not in ("#000000", "#999999")]
    pool.extend([c for c in get_all_9_colors() if c not in pool])
    out: dict[str, str] = {}
    j = 0
    for n in PLOT_NODES:
        if n == "Shoot_Branching":
            out[n] = "#000000"  # phenotype = black, drawn last & thickest
        else:
            out[n] = pool[j % len(pool)]
            j += 1
    return out


def main() -> int:
    iterations, series = load_trace()
    cmap = assign_colors()

    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
        "font.size": 20,
        "axes.facecolor": "#ffffff",
        "figure.facecolor": "#ffffff",
        "axes.edgecolor": "#cccccc",
    })

    fig, ax = plt.subplots(figsize=(18, 6.5), dpi=150)

    xs = iterations[:PLOT_ITERATIONS + 1]
    ordered = [n for n in PLOT_NODES if n != "Shoot_Branching"] + ["Shoot_Branching"]
    for node in ordered:
        ys = series[node][:PLOT_ITERATIONS + 1]
        lw = 3.0 if node == "Shoot_Branching" else 2.0
        ax.plot(
            xs, ys,
            label=node.replace("_", " "),
            color=cmap[node],
            linewidth=lw,
            solid_capstyle="round",
        )

    ax.axhline(1.0, color="#888888", linestyle=":", linewidth=1.2, zorder=0,
               label="WT baseline")

    ax.set_xlim(0, PLOT_ITERATIONS)
    ymax = max(max(s[:PLOT_ITERATIONS + 1]) for s in series.values()) * 1.06
    ax.set_ylim(0, max(ymax, 2.0))
    ax.yaxis.set_major_locator(MultipleLocator(2))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlabel("Iteration", fontsize=24)
    ax.set_ylabel("Node value", fontsize=24)
    ax.tick_params(axis="both", labelsize=20)

    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=True,
        fontsize=18,
        ncol=1,
    )

    plt.tight_layout(rect=(0, 0, 0.79, 1))
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(OUT_SVG, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Wrote {OUT_PNG}")
    print(f"Wrote {OUT_SVG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
