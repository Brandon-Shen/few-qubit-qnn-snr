"""Figure 3 (fig:entanglement-diagnostic): entanglement entropy and purity
by block count, E=0 vs E=1, with real per-initialization SEM error bars
(not the flawed across-condition spread from the original pass -- see
verification/depth_entanglement_by_depth_check.md).

Data: verification/_fig3_entanglement_marginal.csv, freshly recomputed in
this session directly from qnn_snr.stats.descriptive.physics_summary_rows
(the exact same deterministic diagnostic the confirmatory pipeline computes,
called directly to recover per-initialization values before they get
averaged away) -- not retyped from the verification doc's prose tables.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

import sys
sys.path.insert(0, str(Path(__file__).parent))
from plot_style import (
    COLOR_SERIES_A, COLOR_SERIES_B, MARKER_A, MARKER_B,
    TEXT_WIDTH_IN, apply_style,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig3_entanglement.pdf"

marg = pd.read_csv(REPO_ROOT / "verification" / "_fig3_entanglement_marginal.csv")

DEPTHS = [1, 2, 3, 4, 6]
X = list(range(len(DEPTHS)))

apply_style()
fig, axes = plt.subplots(1, 2, figsize=(TEXT_WIDTH_IN * 0.98, 2.35))

for E, color, marker, label in [(0, COLOR_SERIES_A, MARKER_A, "$E=0$"), (1, COLOR_SERIES_B, MARKER_B, "$E=1$")]:
    sub = marg[marg["E"] == E].set_index("depth").loc[DEPTHS].reset_index()
    axes[0].errorbar(X, sub["entropy_mean"], yerr=sub["entropy_sem_within_R"],
                      color=color, marker=marker, markersize=4.0, capsize=2.2,
                      linewidth=1.1, elinewidth=0.8, label=label)
    axes[1].errorbar(X, sub["purity_mean"], yerr=sub["purity_sem_within_R"],
                      color=color, marker=marker, markersize=4.0, capsize=2.2,
                      linewidth=1.1, elinewidth=0.8, label=label)

axes[0].set_ylabel("Mean entanglement entropy")
axes[1].set_ylabel("Mean purity")
for ax, letter in zip(axes, ("a", "b")):
    ax.set_xticks(X)
    ax.set_xticklabels([str(d) for d in DEPTHS])
    ax.set_xlabel("Block count $D$")
    ax.set_title(f"({letter})", loc="left", fontsize=8.5, fontweight="normal")
axes[0].legend(loc="center left", bbox_to_anchor=(0.02, 0.5))

fig.tight_layout()
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH)
fig.savefig(OUT_PATH.with_name(OUT_PATH.stem + "_preview.png"), dpi=200)
print(f"wrote {OUT_PATH}")
print(marg.to_string(index=False))
