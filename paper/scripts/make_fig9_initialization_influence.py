"""Figure 9 (fig:initialization-influence): all 50 leave-one-initialization-out
estimates for beta_EL, beta_ER, beta_LRD, against the full-data reference
value. Read directly from
results/sensitivity_analyses/leave_one_initialization_out_coefficients.csv
(verification/run_loo_initialization.py) -- nothing retyped by hand.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import sys
sys.path.insert(0, str(Path(__file__).parent))
from plot_style import COLOR_SERIES_A, COLOR_NEUTRAL, TEXT_WIDTH_IN, ANNOTATION_FONT_SIZE, apply_style

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig9_initialization_influence.pdf"

df = pd.read_csv(REPO_ROOT / "results" / "sensitivity_analyses" / "leave_one_initialization_out_coefficients.csv")

FULL = {"E:L": 0.024995843985971582, "E:R": -0.0009575787575784316, "L:R:depth_z": -0.010178757716721849}
LABELS = {"E:L": r"$\beta_{EL}$ (H2)", "E:R": r"$\beta_{ER}$ (H3)", "L:R:depth_z": r"$\beta_{LRD}$ (H4)"}

apply_style()
fig, axes = plt.subplots(1, 3, figsize=(TEXT_WIDTH_IN, 2.6), sharex=True)

for ax, coef in zip(axes, ["E:L", "E:R", "L:R:depth_z"]):
    vals = df[f"{coef}_estimate"].to_numpy()
    order = np.argsort(vals)
    ax.scatter(np.arange(len(vals)), vals[order], s=10, color=COLOR_SERIES_A, zorder=3)
    ax.axhline(FULL[coef], color=COLOR_NEUTRAL, linewidth=1.0, linestyle="--", zorder=2)
    ax.axhline(0, color="black", linewidth=0.6, alpha=0.5, zorder=1)
    ax.set_title(LABELS[coef], fontsize=ANNOTATION_FONT_SIZE + 1)
    ax.set_xlabel("LOO deletion (sorted)")

axes[0].set_ylabel("Coefficient estimate")
legend_handles = [
    plt.Line2D([0], [0], marker="o", color=COLOR_SERIES_A, linestyle="", markersize=4, label="LOO estimate (n=50)"),
    plt.Line2D([0], [0], color=COLOR_NEUTRAL, linestyle="--", label="Full-data estimate"),
]
fig.legend(handles=legend_handles, loc="upper center", ncol=2, fontsize=ANNOTATION_FONT_SIZE,
           bbox_to_anchor=(0.5, 1.06), frameon=False)

fig.tight_layout()
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH, bbox_inches="tight")
fig.savefig(OUT_PATH.with_name(OUT_PATH.stem + "_preview.png"), dpi=200, bbox_inches="tight")
print(f"wrote {OUT_PATH}")
