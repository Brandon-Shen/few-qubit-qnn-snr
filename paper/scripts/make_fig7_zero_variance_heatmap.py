"""Figure 7 (fig:zero-variance-heatmap): end-to-end D=1 zero-variance
exclusion percentage by configuration x budget, annotated with raw
excluded/total counts. Read directly from
results/zero_variance_exclusions_d1_config_budget.csv
(verification/run_zero_variance_audit.py) -- nothing retyped by hand.

The near-total zero column-block for configurations 3, 5, 7, 8 (all L=1) is
a real, previously-unreported deterministic pattern (verified across the
*entire* dataset, not just D=1, in verification/zero_variance_exclusion_audit.md):
across 204,800 pointwise cells in both analysis modes, zero_variance_flag is
never True when L=1. This figure makes that pattern visible at a glance
rather than only reporting it in a table.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import sys
sys.path.insert(0, str(Path(__file__).parent))
from plot_style import TEXT_WIDTH_IN, ANNOTATION_FONT_SIZE, apply_style

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig7_zero_variance_exclusion_rates.pdf"

df = pd.read_csv(REPO_ROOT / "results" / "zero_variance_exclusions_d1_config_budget.csv")
budgets = [250, 500, 1000, 2000]
configs = list(range(1, 9))

pct = df.set_index("configuration_id")[[f"pct_B{b}" for b in budgets]].reindex(configs).to_numpy()
excl = df.set_index("configuration_id")[[f"excluded_B{b}" for b in budgets]].reindex(configs).to_numpy()
tot = df.set_index("configuration_id")[[f"total_B{b}" for b in budgets]].reindex(configs).to_numpy()

apply_style()
fig, ax = plt.subplots(figsize=(TEXT_WIDTH_IN * 0.72, 3.2))

im = ax.imshow(pct, cmap="Reds", aspect="auto", vmin=0, vmax=np.nanmax(pct))

for i in range(pct.shape[0]):
    for j in range(pct.shape[1]):
        p, e, t = pct[i, j], int(excl[i, j]), int(tot[i, j])
        color = "white" if p > 0.55 * np.nanmax(pct) else "black"
        ax.text(j, i, f"{p:.1f}%\n({e}/{t})", ha="center", va="center",
                fontsize=ANNOTATION_FONT_SIZE, color=color)

ax.set_xticks(range(len(budgets)))
ax.set_xticklabels([str(b) for b in budgets])
ax.set_xlabel("Shot budget $B$")
ax.set_yticks(range(len(configs)))
ax.set_yticklabels([str(c) for c in configs])
ax.set_ylabel("Configuration")
ax.set_title(r"End-to-end, $D=1$ zero-variance exclusion rate (%)", fontsize=ANNOTATION_FONT_SIZE + 1)

cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("Exclusion %", fontsize=ANNOTATION_FONT_SIZE)

fig.tight_layout()
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH)
fig.savefig(OUT_PATH.with_name(OUT_PATH.stem + "_preview.png"), dpi=200)
print(f"wrote {OUT_PATH}")
