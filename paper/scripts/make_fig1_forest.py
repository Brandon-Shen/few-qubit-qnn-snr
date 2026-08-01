"""Figure 1 (fig:confirmatory-forest): forest plot of the four confirmatory
coefficients (eta_EL, beta_EL, beta_ER, beta_LRD) with their Wald 95% CIs
and bootstrap percentile CIs at the achieved n, plus Holm-adjusted p labels.

All numbers are read directly from real result files -- nothing here is
retyped from the paper's prose:
  - Wald estimate/SE/p_holm: results/production_confirmatory/confirmatory_hypotheses.csv
  - H1 bootstrap draws (n=400): verification/_bootstrap_checkpoints/h1_boot.parquet
  - H2-H4 bootstrap draws: results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_iterations.parquet
    (verification/summarize_bootstrap_checkpoints.py's pooled, end-to-end-only-
    only extended-bootstrap output -- QMI/QIP robustness package Task 4.
    Deliberately excludes the old pooled-mode shard checkpoints
    (h2h4_boot_shard{N}.parquet) and the regression_b duplicate-check draws;
    see verification/bootstrap_end_to_end_extended.md.)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

import sys
sys.path.insert(0, str(Path(__file__).parent))
from plot_style import (
    COLOR_SERIES_A, COLOR_SERIES_B, COLOR_NEUTRAL, COLUMN_WIDTH_IN,
    ANNOTATION_FONT_SIZE, LEGEND_FONT_SIZE, ZERO_LINE_KW, new_fig,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig1_confirmatory_forest.pdf"

conf = pd.read_csv(REPO_ROOT / "results" / "production_confirmatory" / "confirmatory_hypotheses.csv")

h1_draws = pd.read_parquet(REPO_ROOT / "verification" / "_bootstrap_checkpoints" / "h1_boot.parquet")
h2h4_draws = pd.read_parquet(REPO_ROOT / "results" / "production_corrected_end_to_end" / "bootstrap_end_to_end_h2_h4_iterations.parquet")

ROWS = [
    # (row label, hypothesis, coefficient name, bootstrap draw source, draw column)
    (r"H1: $\eta_{EL}$", "H1", "E:L", h1_draws, "E:L"),
    (r"H2: $\beta_{EL}$", "H2", "E:L", h2h4_draws, "E:L"),
    (r"H3: $\beta_{ER}$", "H3", "E:R", h2h4_draws, "E:R"),
    (r"H4: $\beta_{LRD}$", "H4", "L:R:depth_z", h2h4_draws, "L:R:depth_z"),
]


def percentile_ci(draws: np.ndarray, alpha: float = 0.05):
    finite = draws[np.isfinite(draws)]
    lo, hi = np.percentile(finite, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return lo, hi, len(finite)


fig, ax = new_fig(COLUMN_WIDTH_IN, 2.55)

y_positions = np.arange(len(ROWS))[::-1]
wald_offset, boot_offset = 0.12, -0.12

for i, (label, hyp, coef, draws_df, col) in enumerate(ROWS):
    y = y_positions[i]
    row = conf[conf["hypothesis"] == hyp].iloc[0]
    est, se, p_holm = row["estimate"], row["standard_error"], row["p_holm"]
    wald_lo, wald_hi = est - 1.96 * se, est + 1.96 * se

    boot_lo, boot_hi, n_boot = percentile_ci(draws_df[col].to_numpy())

    ax.plot([wald_lo, wald_hi], [y + wald_offset, y + wald_offset],
            color=COLOR_SERIES_A, solid_capstyle="butt", zorder=3)
    ax.plot(est, y + wald_offset, marker="o", color=COLOR_SERIES_A, zorder=4, markersize=3.6)

    ax.plot([boot_lo, boot_hi], [y + boot_offset, y + boot_offset],
            color=COLOR_SERIES_B, linestyle=(0, (3, 1.5)), solid_capstyle="butt", zorder=3)
    ax.plot(est, y + boot_offset, marker="s", color=COLOR_SERIES_B, zorder=4, markersize=3.2)

    p_str = f"$p_{{\\mathrm{{Holm}}}}={p_holm:.3g}$" if p_holm >= 1e-3 else f"$p_{{\\mathrm{{Holm}}}}={p_holm:.2e}$"
    ax.annotate(f"{p_str}  (n={n_boot})", xy=(1.0, y), xycoords=("axes fraction", "data"),
                xytext=(4, 0), textcoords="offset points", va="center", ha="left",
                fontsize=ANNOTATION_FONT_SIZE, color=COLOR_NEUTRAL)

ax.axvline(0, **ZERO_LINE_KW)
ax.set_yticks(y_positions)
ax.set_yticklabels([r[0] for r in ROWS])
ax.set_xlabel("Coefficient estimate")
ax.set_xlim(-0.045, 0.062)
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

for label, hyp, coef, draws_df, col in ROWS:
    row = conf[conf["hypothesis"] == hyp].iloc[0]
    lo, hi, n = percentile_ci(draws_df[col].to_numpy())
    print(f"{hyp} {coef}: est={row['estimate']:.6f} wald=[{row['estimate']-1.96*row['standard_error']:.6f}, "
          f"{row['estimate']+1.96*row['standard_error']:.6f}] boot(n={n})=[{lo:.6f}, {hi:.6f}] p_holm={row['p_holm']:.6g}")
