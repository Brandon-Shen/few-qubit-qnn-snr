"""Render the corrected H1--H4 forest plot from frozen numerical outputs.

H2--H4 rows in the frozen corrected table are the adopted end_to_end
estimator-mode results; conditional-mode rows are never read by this renderer.
"""
from __future__ import annotations

from pathlib import Path

import json
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
mpl.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"})
import matplotlib.pyplot as plt

import sys
sys.path.insert(0, str(Path(__file__).parent))
from plot_style import (
    COLOR_SERIES_A, COLOR_SERIES_B, COLOR_NEUTRAL, COLUMN_WIDTH_IN,
    ANNOTATION_FONT_SIZE, LEGEND_FONT_SIZE, ZERO_LINE_KW, new_fig,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig1_confirmatory_forest.pdf"

conf = pd.read_csv(REPO_ROOT / "results/primary_corrected/effect_coded/corrected_confirmatory_hypotheses.csv")
boot = pd.read_csv(REPO_ROOT / "results/primary_corrected/effect_coded/corrected_bootstrap_intervals_current_draws.csv")
h1_meta = json.loads((REPO_ROOT / "results/primary_corrected/effect_coded/h1_centered_bootstrap_2000.meta.json").read_text())

ROWS = [
    (r"H1: $E_cL_c$ exact", "H1"),
    (r"H2: $E_cL_c$ finite-shot", "H2"),
    (r"H3: $E_cR_c$ finite-shot", "H3"),
    (r"H4: $L_cR_c\times$depth", "H4"),
]


fig, ax = new_fig(COLUMN_WIDTH_IN, 2.55)

y_positions = np.arange(len(ROWS))[::-1]
wald_offset, boot_offset = 0.12, -0.12

for i, (label, hyp) in enumerate(ROWS):
    y = y_positions[i]
    row = conf[conf["hypothesis"] == hyp].iloc[0]
    est, p_holm = row["corrected_estimate"], row["corrected_p_holm"]
    wald_lo, wald_hi = row["corrected_ci_lo"], row["corrected_ci_hi"]
    if hyp == "H1":
        boot_lo, boot_hi = h1_meta["percentile_interval"]
        n_boot = h1_meta["completed_bootstrap_fits"]
    else:
        brow = boot[boot["hypothesis"] == hyp].iloc[0]
        boot_lo, boot_hi = brow["percentile_ci_lo"], brow["percentile_ci_hi"]
        n_boot = int(brow["completed_bootstrap_iterations"])

    ax.plot([wald_lo, wald_hi], [y + wald_offset, y + wald_offset],
            color=COLOR_SERIES_A, solid_capstyle="butt", zorder=3)
    ax.plot(est, y + wald_offset, marker="o", color=COLOR_SERIES_A, zorder=4, markersize=3.6)

    ax.plot([boot_lo, boot_hi], [y + boot_offset, y + boot_offset],
            color=COLOR_SERIES_B, linestyle=(0, (3, 1.5)), solid_capstyle="butt", zorder=3)
    ax.plot(est, y + boot_offset, marker="s", color=COLOR_SERIES_B, zorder=4, markersize=3.2)

    p_str = f"$p_{{\\mathrm{{Holm}}}}={p_holm:.3g}$" if p_holm >= 1e-3 else f"$p_{{\\mathrm{{Holm}}}}={p_holm:.2e}$"
    ax.annotate(f"{p_str}  ({n_boot} fits)", xy=(1.0, y), xycoords=("axes fraction", "data"),
                xytext=(4, 0), textcoords="offset points", va="center", ha="left",
                fontsize=ANNOTATION_FONT_SIZE, color=COLOR_NEUTRAL)

ax.axvline(0, **ZERO_LINE_KW)
ax.set_yticks(y_positions)
ax.set_yticklabels([r[0] for r in ROWS])
ax.set_xlabel("Coefficient estimate")
ax.set_xlim(-0.05, 0.05)
ax.set_ylim(-0.65, len(ROWS) - 0.35)

legend_handles = [
    plt.Line2D([0], [0], color=COLOR_SERIES_A, marker="o", markersize=3.6, label="Wald 95% CI"),
    plt.Line2D([0], [0], color=COLOR_SERIES_B, linestyle=(0, (3, 1.5)), marker="s", markersize=3.2,
               label="Bootstrap percentile CI"),
]
# Placed above the axes (not "upper left" inside it) so the legend never
# competes for space with the H1 row, which sits closest to the top.
fig.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.55, 1.06),
           ncol=2, fontsize=LEGEND_FONT_SIZE, handlelength=2.2, frameon=False)

fig.tight_layout()
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH)
fig.savefig(OUT_PATH.with_name(OUT_PATH.stem + "_preview.png"), dpi=200)
print(f"wrote {OUT_PATH}")

for label, hyp in ROWS:
    row = conf[conf["hypothesis"] == hyp].iloc[0]
    print(f"{hyp}: est={row['corrected_estimate']:.6f} "
          f"wald=[{row['corrected_ci_lo']:.6f}, {row['corrected_ci_hi']:.6f}] "
          f"p_holm={row['corrected_p_holm']:.6g}")
