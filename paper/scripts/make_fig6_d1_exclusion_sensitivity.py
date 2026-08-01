"""Figure 6 (fig:d1-exclusion-sensitivity): adopted full-sweep vs. D!=1
sensitivity estimates for all three H2-H4 coefficients, 95% Wald CIs.

Distinct from fig2 (which compares mode and D>=3 for beta_LRD alone) -- this
figure shows all three coefficients (beta_EL, beta_ER, beta_LRD) under only
two models (full sweep vs. D!=1), read directly from
results/d1_exclusion_sensitivity_coefficients.csv (verification/run_d1_exclusion_sensitivity.py).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import sys
sys.path.insert(0, str(Path(__file__).parent))
from plot_style import (
    COLOR_SERIES_A, COLOR_SERIES_B, ANNOTATION_FONT_SIZE, LEGEND_FONT_SIZE,
    TEXT_WIDTH_IN, ZERO_LINE_KW, apply_style,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig6_d1_exclusion_sensitivity.pdf"

df = pd.read_csv(REPO_ROOT / "results" / "d1_exclusion_sensitivity_coefficients.csv")

COEF_ORDER = [
    ("E:L", r"H2: $\beta_{EL}$"),
    ("E:R", r"H3: $\beta_{ER}$"),
    ("L:R:depth_z", r"H4: $\beta_{LRD}$"),
]

apply_style()
fig, ax = plt.subplots(figsize=(TEXT_WIDTH_IN * 0.68, 2.5))

y_positions = np.arange(len(COEF_ORDER))[::-1]
full_offset, d1_offset = 0.11, -0.11

for i, (coef, label) in enumerate(COEF_ORDER):
    y = y_positions[i]
    full_row = df[(df["coefficient"] == coef) & (df["model"] == "full_sweep_adopted")].iloc[0]
    d1_row = df[(df["coefficient"] == coef) & (df["model"] == "d_neq_1_sensitivity")].iloc[0]

    ax.plot([full_row["ci_lo"], full_row["ci_hi"]], [y + full_offset, y + full_offset],
            color=COLOR_SERIES_A, solid_capstyle="butt", zorder=3, linewidth=1.6)
    ax.plot(full_row["estimate"], y + full_offset, marker="o", color=COLOR_SERIES_A, zorder=4, markersize=4.2)

    ax.plot([d1_row["ci_lo"], d1_row["ci_hi"]], [y + d1_offset, y + d1_offset],
            color=COLOR_SERIES_B, solid_capstyle="butt", zorder=3, linewidth=1.6)
    ax.plot(d1_row["estimate"], y + d1_offset, marker="s", color=COLOR_SERIES_B, zorder=4, markersize=4.0)

ax.axvline(0, **ZERO_LINE_KW)
ax.set_yticks(y_positions)
ax.set_yticklabels([c[1] for c in COEF_ORDER])
ax.set_xlabel("Coefficient estimate (95% Wald CI)")
# Extra headroom above the H2 row (the topmost) so the legend, placed above
# the axes entirely, has clear separation from the topmost CI markers.
ax.set_ylim(-0.6, len(COEF_ORDER) + 0.35)

legend_handles = [
    plt.Line2D([0], [0], color=COLOR_SERIES_A, marker="o", markersize=4.2,
               label="Full sweep ($D\\in\\{1,2,3,4,6\\}$, adopted)"),
    plt.Line2D([0], [0], color=COLOR_SERIES_B, marker="s", markersize=4.0,
               label="$D\\neq1$ sensitivity ($D\\in\\{2,3,4,6\\}$)"),
]
# fig-level legend anchored above the whole figure (not "upper left" inside
# the axes) so it never crowds the H2 row underneath it.
fig.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.56, 1.1),
           fontsize=LEGEND_FONT_SIZE, handlelength=2.0, frameon=False)

fig.tight_layout()
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH)
fig.savefig(OUT_PATH.with_name(OUT_PATH.stem + "_preview.png"), dpi=200)
print(f"wrote {OUT_PATH}")
