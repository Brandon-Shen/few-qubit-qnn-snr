"""Figure 5 (fig:q1-comparison): configuration-8-beats-best-single win/loss
grid, depth x budget, pooled vs. end-to-end-only data side by side --
visualizing the narrowing from 9/20 (pooled) to 4/20 (end-to-end-only),
and specifically that the end-to-end-only wins collapse to the
block-count-3 cluster.

Data: results/production_confirmatory/exploratory_results.csv (pooled, the historical record) and
verification/_q1_endtoend_recompute.csv (end-to-end-only, computed earlier
in this verification pass directly from
qnn_snr.stats.exploratory.exploratory_configuration_8_comparisons) -- both
real pipeline outputs, not retyped from prose.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

import sys
sys.path.insert(0, str(Path(__file__).parent))
from plot_style import COLOR_SERIES_A, COLOR_SERIES_B, TEXT_WIDTH_IN, apply_style

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig5_q1_comparison.pdf"

pooled = pd.read_csv(REPO_ROOT / "results" / "production_confirmatory" / "exploratory_results.csv")
e2e = pd.read_csv(REPO_ROOT / "verification" / "_q1_endtoend_recompute.csv")

DEPTHS = [1, 2, 3, 4, 6]
BUDGETS = [250, 500, 1000, 2000]


def grid(df: pd.DataFrame) -> np.ndarray:
    g = np.zeros((len(DEPTHS), len(BUDGETS)))
    for i, d in enumerate(DEPTHS):
        for j, b in enumerate(BUDGETS):
            row = df[(df["depth"] == d) & (df["budget"] == b)]
            g[i, j] = 1.0 if bool(row["config8_exceeds_best_single_SNR"].iloc[0]) else 0.0
    return g


pooled_grid = grid(pooled)
e2e_grid = grid(e2e)

cmap = ListedColormap(["#eaeaea", COLOR_SERIES_B])

apply_style()
fig, axes = plt.subplots(1, 2, figsize=(TEXT_WIDTH_IN * 0.72, 2.5))

for ax, g, title, n_win in [
    (axes[0], pooled_grid, "Pooled (superseded)", int(pooled_grid.sum())),
    (axes[1], e2e_grid, "End-to-end-only (adopted)", int(e2e_grid.sum())),
]:
    ax.imshow(g, cmap=cmap, vmin=0, vmax=1, aspect="auto", origin="upper")
    ax.set_xticks(range(len(BUDGETS)))
    ax.set_xticklabels([str(b) for b in BUDGETS])
    ax.set_yticks(range(len(DEPTHS)))
    ax.set_yticklabels([str(d) for d in DEPTHS])
    ax.set_xlabel("Budget $B$")
    ax.set_title(f"{title}\n(config. 8 wins {n_win}/20)", fontsize=8.5)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.5)
    ax.set_xticks(np.arange(-0.5, len(BUDGETS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(DEPTHS), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.2)
    ax.tick_params(which="minor", length=0)

axes[0].set_ylabel("Block count $D$")

legend_handles = [
    plt.Rectangle((0, 0), 1, 1, color="#eaeaea", label="Best single wins"),
    plt.Rectangle((0, 0), 1, 1, color=COLOR_SERIES_B, label="Config. 8 wins"),
]
fig.legend(handles=legend_handles, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.05),
           fontsize=7.5, frameon=False)

fig.tight_layout()
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH, bbox_inches="tight")
fig.savefig(OUT_PATH.with_name(OUT_PATH.stem + "_preview.png"), dpi=200, bbox_inches="tight")
print(f"wrote {OUT_PATH}")
print("pooled wins:", int(pooled_grid.sum()), "/20")
print("end-to-end-only wins:", int(e2e_grid.sum()), "/20")
