"""Figure 2 (fig:h4-fragility): beta_LRD across four refits, making the
conditional/end-to-end sign flip and the D>=3 shrinkage both visible at a
glance. This is the single most important figure in the paper (Section
4.5's "pulls against optimism" argument made visual).

All four values are read from real fit-output files -- none retyped from
the paper's prose:
  - adopted full-sweep confirmatory (end-to-end-only) and "end-to-end-only"
    (the same fit, by definition): results/production_confirmatory/snr_model_coefficients.csv
  - D>=3 sensitivity, end-to-end-only: verification/_fig2_dge3_endtoend_coefficients.csv
    (freshly refit in this session, reproduces the verification doc's
    numbers bit-for-bit)
  - conditional-only, full sweep: verification/_fig2_conditional_fullsweep_coefficients.csv
    (same -- freshly refit, bit-identical reproduction)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import sys
sys.path.insert(0, str(Path(__file__).parent))
from plot_style import (
    COLOR_SERIES_A, COLOR_SERIES_B, COLOR_ACCENT, COLOR_NEUTRAL,
    TEXT_WIDTH_IN, ANNOTATION_FONT_SIZE, ZERO_LINE_KW, apply_style,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
VER_DIR = REPO_ROOT / "verification"
OUT_PATH = Path(__file__).resolve().parents[1] / "figures" / "fig2_h4_fragility.pdf"

adopted = pd.read_csv(REPO_ROOT / "results" / "production_confirmatory" / "snr_model_coefficients.csv")
adopted_row = adopted[adopted["coefficient"] == "L:R:depth_z"].iloc[0]
adopted_est, adopted_se = float(adopted_row["estimate"]), float(adopted_row["se"])

dge3 = pd.read_csv(VER_DIR / "_fig2_dge3_endtoend_coefficients.csv")
dge3_row = dge3[dge3["coefficient"] == "L:R:depth_z"].iloc[0]
dge3_est, dge3_se = float(dge3_row["estimate"]), float(dge3_row["se"])

cond = pd.read_csv(VER_DIR / "_fig2_conditional_fullsweep_coefficients.csv")
cond_row = cond[cond["coefficient"] == "L:R:depth_z"].iloc[0]
cond_est, cond_se = float(cond_row["estimate"]), float(cond_row["se"])

# Ordered so each requested comparison sits on an adjacent pair of rows:
# rows 0-1 show the conditional/end-to-end sign flip, rows 1-2 show the
# D>=3 shrinkage relative to the full-sweep end-to-end (= adopted) value.
# "Adopted full-sweep confirmatory" and "end-to-end-only" are, by
# definition, the same fit (Section 3.7 / Appendix A.11) -- shown once,
# labeled with both names, rather than duplicated as a fourth identical bar.
ROWS = [
    ("Conditional, full sweep\n(mode diagnostic)", cond_est, cond_se, COLOR_SERIES_A),
    ("End-to-end, full sweep\n(adopted confirmatory)", adopted_est, adopted_se, COLOR_ACCENT),
    ("End-to-end, $D\\geq3$\n(depth sensitivity)", dge3_est, dge3_se, COLOR_SERIES_B),
]

apply_style()
fig, ax = plt.subplots(figsize=(TEXT_WIDTH_IN * 0.62, 2.35))

y_positions = np.arange(len(ROWS))[::-1]
for i, (label, est, se, color) in enumerate(ROWS):
    y = y_positions[i]
    lo, hi = est - 1.96 * se, est + 1.96 * se
    ax.plot([lo, hi], [y, y], color=color, solid_capstyle="butt", zorder=3, linewidth=1.6)
    ax.plot(est, y, marker="o", color=color, zorder=4, markersize=4.5)
    ax.annotate(f"{est:+.4f}", xy=(hi, y), xytext=(6, 0), textcoords="offset points",
                va="center", ha="left", fontsize=ANNOTATION_FONT_SIZE, color=color)

ax.axvline(0, **ZERO_LINE_KW)
ax.set_yticks(y_positions)
ax.set_yticklabels([r[0] for r in ROWS])
ax.set_xlabel(r"$\beta_{LRD}$ estimate (95% Wald CI)")
ax.set_xlim(-0.033, 0.043)
ax.set_ylim(-0.55, len(ROWS) - 0.35)


def draw_bracket(x, y_bottom, y_top, label):
    """A caliper-style bracket (spine + short end ticks) so the annotation
    reads unambiguously as 'these two rows are being compared', rather than
    as a bare, unexplained vertical line."""
    cap = 0.0016
    ax.plot([x, x], [y_bottom, y_top], color=COLOR_NEUTRAL, linewidth=0.7, zorder=2)
    ax.plot([x - cap, x], [y_bottom, y_bottom], color=COLOR_NEUTRAL, linewidth=0.7, zorder=2)
    ax.plot([x - cap, x], [y_top, y_top], color=COLOR_NEUTRAL, linewidth=0.7, zorder=2)
    ax.text(x + 0.0015, (y_bottom + y_top) / 2, label, fontsize=ANNOTATION_FONT_SIZE,
            color=COLOR_NEUTRAL, va="center", ha="left")


# Both brackets sit in the same right-hand column, stacked top to bottom, so
# they read as one consistent annotation style rather than two unrelated
# lines on opposite sides of the axis.
x_bracket = 0.0275
draw_bracket(x_bracket, y_positions[1] + 0.1, y_positions[0] - 0.1, "sign\nflip")
draw_bracket(x_bracket, y_positions[2] + 0.1, y_positions[1] - 0.1, "shrinks")

fig.tight_layout()
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_PATH)
fig.savefig(OUT_PATH.with_name(OUT_PATH.stem + "_preview.png"), dpi=200)
print(f"wrote {OUT_PATH}")
for label, est, se, _ in ROWS:
    print(f"{label!r}: est={est:.6f} se={se:.6f} CI=[{est-1.96*se:.6f}, {est+1.96*se:.6f}]")
