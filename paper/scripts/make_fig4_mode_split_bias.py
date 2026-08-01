"""Figure 4 (fig:mode-split-bias): sign agreement and median absolute bias
by configuration (1-8), conditional vs. end-to-end mode -- visualizing the
"conditional beats end-to-end in 8/8 configurations, no exceptions" finding.

Data: verification/_fig4_mode_split_by_config.csv, freshly recomputed in
this session directly from results/production_confirmatory/pointwise_gradient_statistics.parquet
(groupby configuration_id x analysis_mode), not retyped from prose.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import sys
sys.path.insert(0, str(Path(__file__).parent))
from plot_style import COLOR_SERIES_A, COLOR_SERIES_B, TEXT_WIDTH_IN, apply_style

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig4_mode_split_bias.pdf"

df = pd.read_csv(REPO_ROOT / "verification" / "_fig4_mode_split_by_config.csv")
configs = sorted(df["configuration_id"].unique())
cond = df[df["analysis_mode"] == "finite_shot_conditional"].set_index("configuration_id").loc[configs]
e2e = df[df["analysis_mode"] == "finite_shot_end_to_end"].set_index("configuration_id").loc[configs]

apply_style()
fig, axes = plt.subplots(1, 2, figsize=(TEXT_WIDTH_IN * 0.98, 2.35))

x = np.arange(len(configs))
w = 0.36

axes[0].bar(x - w / 2, cond["sign_agreement_fraction"], width=w, color=COLOR_SERIES_A, label="Conditional")
axes[0].bar(x + w / 2, e2e["sign_agreement_fraction"], width=w, color=COLOR_SERIES_B, label="End-to-end")
axes[0].set_ylabel("Sign agreement fraction")
axes[0].set_ylim(0.7, 0.96)

axes[1].bar(x - w / 2, cond["median_absolute_bias"], width=w, color=COLOR_SERIES_A, label="Conditional")
axes[1].bar(x + w / 2, e2e["median_absolute_bias"], width=w, color=COLOR_SERIES_B, label="End-to-end")
axes[1].set_ylabel("Median absolute bias")

for ax, letter in zip(axes, ("a", "b")):
    ax.set_xticks(x)
    ax.set_xticklabels([str(c) for c in configs])
    ax.set_xlabel("Configuration")
    ax.set_title(f"({letter})", loc="left", fontsize=8.5, fontweight="normal")
axes[0].legend(loc="upper left", fontsize=7.5)

fig.tight_layout()
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH)
fig.savefig(OUT_PATH.with_name(OUT_PATH.stem + "_preview.png"), dpi=200)
print(f"wrote {OUT_PATH}")
print("sign agreement, conditional > end-to-end in all configs:",
      bool((cond["sign_agreement_fraction"].to_numpy() > e2e["sign_agreement_fraction"].to_numpy()).all()))
print("median |bias|, conditional < end-to-end in all configs:",
      bool((cond["median_absolute_bias"].to_numpy() < e2e["median_absolute_bias"].to_numpy()).all()))
