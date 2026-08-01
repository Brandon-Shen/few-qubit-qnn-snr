"""Figure 11 (fig:h2-depth-heterogeneity): post-run, exploratory H2
depth-heterogeneity analysis.

Panel (a): the categorical mixed model's depth-specific E:L contrast
(arcsinh(SNR_est) scale), original vs. independent replication, with 95%
Wald CIs. Panel (b): the two pooled-weighting schemes vs. the adopted
full-pooling confirmatory coefficient, original and (where available)
replication.

Source data only: results/h2_robustness/depth_heterogeneity/original_depth_contrasts.csv,
results/h2_replication_v1/depth_heterogeneity/replication_depth_contrasts.csv,
results/h2_robustness/depth_heterogeneity/original_weighted_contrasts.csv,
results/h2_replication_v1/depth_heterogeneity/replication_weighted_contrasts.csv.
No number in this script is computed or retyped by hand.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
from plot_style import (  # noqa: E402
    COLOR_SERIES_A, COLOR_SERIES_B, COLOR_NEUTRAL, MARKER_A, MARKER_B,
    TEXT_WIDTH_IN, ANNOTATION_FONT_SIZE, ZERO_LINE_KW, apply_style,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig11_h2_depth_heterogeneity.pdf"
SOURCE_OUT = Path(__file__).resolve().parents[1] / "figure_data" / "fig11_h2_depth_heterogeneity_source.csv"

DEPTH_DIR = REPO_ROOT / "results" / "h2_robustness" / "depth_heterogeneity"
REPL_DIR = REPO_ROOT / "results" / "h2_replication_v1" / "depth_heterogeneity"

orig_contrasts = pd.read_csv(DEPTH_DIR / "original_depth_contrasts.csv").sort_values("depth")
repl_contrasts = pd.read_csv(REPL_DIR / "replication_depth_contrasts.csv").sort_values("depth")
orig_weighted = pd.read_csv(DEPTH_DIR / "original_weighted_contrasts.csv")
repl_weighted = pd.read_csv(REPL_DIR / "replication_weighted_contrasts.csv")

apply_style()
fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(TEXT_WIDTH_IN, 3.0))

# --- Panel (a): depth-specific contrasts, original vs. replication ---
offset = 0.08
x_orig = orig_contrasts["depth"] - offset
x_repl = repl_contrasts["depth"] + offset

ax_a.errorbar(x_orig, orig_contrasts["estimate"],
              yerr=[orig_contrasts["estimate"] - orig_contrasts["ci95_lo"],
                    orig_contrasts["ci95_hi"] - orig_contrasts["estimate"]],
              fmt=MARKER_A, color=COLOR_SERIES_A, linestyle="-", linewidth=1.0,
              markersize=4.5, capsize=2.5, label="Original")
ax_a.errorbar(x_repl, repl_contrasts["estimate"],
              yerr=[repl_contrasts["estimate"] - repl_contrasts["ci95_lo"],
                    repl_contrasts["ci95_hi"] - repl_contrasts["estimate"]],
              fmt=MARKER_B, color=COLOR_SERIES_B, linestyle="--", linewidth=1.0,
              markersize=4.5, capsize=2.5, label="Replication")
ax_a.axhline(0, **ZERO_LINE_KW)
ax_a.set_xlabel("Block count $D$")
ax_a.set_ylabel(r"$E{:}L$ contrast, $\mathrm{arcsinh}(\mathrm{SNR}_{\mathrm{est}})$ scale")
ax_a.set_xticks(sorted(set(orig_contrasts["depth"]).union(repl_contrasts["depth"])))
ax_a.legend(loc="upper right", fontsize=ANNOTATION_FONT_SIZE)
ax_a.text(0.02, 0.02, "(a)", transform=ax_a.transAxes, fontsize=ANNOTATION_FONT_SIZE + 1, fontweight="bold")

# --- Panel (b): weighting schemes vs. adopted pooled coefficient ---
labels = ["Equal-depth\n(original)", "Obs.-weighted\n(original)", "Equal-depth\n(replication)",
          "Obs.-weighted\n(replication)", "Adopted\n(original)", "Pooled Wald\n(replication)"]
o_eq = orig_weighted[orig_weighted["weighting"] == "equal_depth"].iloc[0]
o_obs = orig_weighted[orig_weighted["weighting"] == "observation_count"].iloc[0]
o_adopted = orig_weighted[orig_weighted["weighting"] == "adopted_confirmatory_pooled"].iloc[0]
r_eq = repl_weighted[repl_weighted["weighting"] == "equal_depth"].iloc[0]
r_obs = repl_weighted[repl_weighted["weighting"] == "observation_count"].iloc[0]
r_adopted = repl_weighted[repl_weighted["weighting"] == "replication_pooled_wald"].iloc[0]

points = [o_eq, o_obs, r_eq, r_obs, o_adopted, r_adopted]
colors = [COLOR_SERIES_A, COLOR_SERIES_A, COLOR_SERIES_B, COLOR_SERIES_B, COLOR_NEUTRAL, COLOR_NEUTRAL]
markers = [MARKER_A, MARKER_A, MARKER_B, MARKER_B, "D", "D"]
x = list(range(len(points)))
for xi, pt, c, m in zip(x, points, colors, markers):
    ax_b.errorbar([xi], [pt["estimate"]], yerr=[[pt["estimate"] - pt["ci95_lo"]], [pt["ci95_hi"] - pt["estimate"]]],
                  fmt=m, color=c, markersize=5.5, capsize=3)
ax_b.axhline(0, **ZERO_LINE_KW)
ax_b.set_xticks(x)
ax_b.set_xticklabels(labels, fontsize=ANNOTATION_FONT_SIZE - 0.5, rotation=30, ha="right")
ax_b.set_ylabel(r"Pooled $E{:}L$ estimate")
ax_b.text(0.02, 0.02, "(b)", transform=ax_b.transAxes, fontsize=ANNOTATION_FONT_SIZE + 1, fontweight="bold")

fig.tight_layout()
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH, bbox_inches="tight")
fig.savefig(OUT_PATH.with_name(OUT_PATH.stem + "_preview.png"), dpi=200, bbox_inches="tight")

# --- source table (panel a + b, single flat CSV, so the figure is regeneratable
# from one file if the two upstream CSVs are unavailable) ---
source_rows = []
for _, r in orig_contrasts.iterrows():
    source_rows.append({"panel": "a", "series": "original", "depth": r["depth"],
                         "estimate": r["estimate"], "ci95_lo": r["ci95_lo"], "ci95_hi": r["ci95_hi"]})
for _, r in repl_contrasts.iterrows():
    source_rows.append({"panel": "a", "series": "replication", "depth": r["depth"],
                         "estimate": r["estimate"], "ci95_lo": r["ci95_lo"], "ci95_hi": r["ci95_hi"]})
for label, pt in zip(labels, points):
    source_rows.append({"panel": "b", "series": label.replace("\n", " "), "depth": None,
                         "estimate": pt["estimate"], "ci95_lo": pt["ci95_lo"], "ci95_hi": pt["ci95_hi"]})
SOURCE_OUT.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(source_rows).to_csv(SOURCE_OUT, index=False)

print(f"wrote {OUT_PATH}")
print(f"wrote {SOURCE_OUT}")
