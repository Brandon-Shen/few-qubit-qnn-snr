"""Shared matplotlib style for every figure in this paper.

No LaTeX toolchain is available in this environment (no pdflatex/biber found
on PATH or in common install locations), so `text.usetex` stays False
throughout -- matplotlib's built-in mathtext renderer is used instead,
with a serif font family chosen to visually match the paper's default
Computer Modern typeface as closely as mathtext allows. Every figure in the
paper imports this module so the five figures share one visual language
(font, sizes, color/marker conventions) rather than looking like five
separate plotting sessions.

Column widths are computed from main.tex's actual geometry
(`\\usepackage[margin=0.75in]{geometry}`, `\\columnsep=0.28in`,
`\\documentclass[10pt,twocolumn]{article}`, US letter 8.5in page width):
text width = 8.5 - 2*0.75 = 7.0in; single column = (7.0 - 0.28) / 2 = 3.36in.
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

TEXT_WIDTH_IN = 7.0
COLUMN_WIDTH_IN = (TEXT_WIDTH_IN - 0.28) / 2  # 3.36in

BASE_FONT_SIZE = 8.5  # legible at the paper's 10pt base size once scaled into a 3.36in column
TITLE_FONT_SIZE = 8.5
LABEL_FONT_SIZE = 8.5
TICK_FONT_SIZE = 7.5
LEGEND_FONT_SIZE = 7.5
ANNOTATION_FONT_SIZE = 7.0

# E=0 / E=1 (and generally "first" / "second" series) color convention,
# reused identically across every figure that needs a two-series contrast
# (entanglement E=0/E=1, conditional/end-to-end mode). Colorblind-safe,
# print-safe (distinguishable in pure grayscale via the paired marker shapes).
COLOR_SERIES_A = "#1b4f72"  # dark blue -- E=0 / conditional / Wald
COLOR_SERIES_B = "#b7410e"  # dark burnt orange -- E=1 / end-to-end / bootstrap
COLOR_NEUTRAL = "#4d4d4d"   # dark gray -- reference lines, baseline/pooled
COLOR_ACCENT = "#6b8e23"    # olive -- a third series when needed (conditional-only in 3-way comparisons)

MARKER_A = "o"
MARKER_B = "s"
MARKER_ACCENT = "^"

ZERO_LINE_KW = dict(color="black", linewidth=0.7, linestyle="-", zorder=0, alpha=0.6)


def apply_style() -> None:
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["STIXGeneral", "DejaVu Serif", "Times New Roman", "serif"],
        "mathtext.fontset": "stix",
        "text.usetex": False,
        "font.size": BASE_FONT_SIZE,
        "axes.titlesize": TITLE_FONT_SIZE,
        "axes.labelsize": LABEL_FONT_SIZE,
        "xtick.labelsize": TICK_FONT_SIZE,
        "ytick.labelsize": TICK_FONT_SIZE,
        "legend.fontsize": LEGEND_FONT_SIZE,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "lines.linewidth": 1.1,
        "lines.markersize": 4.0,
        "legend.frameon": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,
    })


def new_fig(width_in: float, height_in: float):
    apply_style()
    fig, ax = plt.subplots(figsize=(width_in, height_in))
    return fig, ax
