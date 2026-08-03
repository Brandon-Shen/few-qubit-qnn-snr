"""Figure 10 (fig:bootstrap-endpoint-stability): lower endpoint, median, and
upper endpoint of the percentile bootstrap CI for beta_EL, beta_ER,
beta_LRD, plotted against completed iteration count, from
results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_checkpoints.csv
(verification/summarize_bootstrap_checkpoints.py) -- makes the endpoint
*trajectory* visible (per the QMI/QIP prompt: "do not claim endpoint
stability merely because the median is stable; discuss the endpoint
trajectory directly"), not just the final interval.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt

import sys
sys.path.insert(0, str(Path(__file__).parent))
from plot_style import COLOR_SERIES_A, COLOR_SERIES_B, COLOR_NEUTRAL, TEXT_WIDTH_IN, ANNOTATION_FONT_SIZE, apply_style

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig10_bootstrap_endpoint_stability.pdf"

df = pd.read_csv(REPO_ROOT / "results" / "production_corrected_end_to_end" / "bootstrap_end_to_end_h2_h4_checkpoints.csv")
LABELS = {"E_c:L_c": r"$\beta_{EL}$ (H2)", "E_c:R_c": r"$\beta_{ER}$ (H3)",
          "L_c:R_c:depth_z": r"$\beta_{LRD}$ (H4)"}

apply_style()
fig, axes = plt.subplots(1, 3, figsize=(TEXT_WIDTH_IN, 2.7), sharex=True)

for ax, coef in zip(axes, LABELS):
    sub = df[df["coefficient"] == coef].sort_values("n")
    if sub.empty:
        ax.set_title(f"{LABELS[coef]}\n(no checkpoints yet)", fontsize=ANNOTATION_FONT_SIZE + 1)
        continue
    ax.plot(sub["n"], sub["ci_lo"], marker="o", color=COLOR_SERIES_A, markersize=3.5, label="Lower endpoint")
    ax.plot(sub["n"], sub["median"], marker="s", color=COLOR_NEUTRAL, markersize=3.5, label="Median")
    ax.plot(sub["n"], sub["ci_hi"], marker="^", color=COLOR_SERIES_B, markersize=3.5, label="Upper endpoint")
    ax.axhline(0, color="black", linewidth=0.6, alpha=0.6)
    ax.set_title(LABELS[coef], fontsize=ANNOTATION_FONT_SIZE + 1)
    ax.set_xlabel("Completed iterations $n$")

axes[0].set_ylabel("Bootstrap percentile CI")
handles, labels_ = axes[0].get_legend_handles_labels()
if handles:
    fig.legend(handles, labels_, loc="upper center", ncol=3, fontsize=ANNOTATION_FONT_SIZE,
               bbox_to_anchor=(0.5, 1.08), frameon=False)

fig.tight_layout()
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH, bbox_inches="tight")
fig.savefig(OUT_PATH.with_name(OUT_PATH.stem + "_preview.png"), dpi=200, bbox_inches="tight")
print(f"wrote {OUT_PATH}")
