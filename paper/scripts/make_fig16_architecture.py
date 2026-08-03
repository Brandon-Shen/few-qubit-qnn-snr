"""Render the code-verified reset-per-block architecture schematic."""
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
mpl.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"})
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

mpl.rcParams.update({"font.size": 8})
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "figures" / "fig16_architecture.pdf"
PREVIEW = ROOT / "paper" / "figures" / "fig16_architecture_preview.png"

fig, ax = plt.subplots(figsize=(7.2, 3.0))
ax.set(xlim=(0, 12), ylim=(0, 6))
ax.axis("off")

def box(x, y, w, h, label, shade="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04",
                               facecolor=shade, edgecolor="black", linewidth=0.9))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center")

def arrow(a, b, dashed=False):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=9,
                                 linewidth=0.9, linestyle="--" if dashed else "-",
                                 color="black"))

box(.2, 3.8, 1.2, .7, r"$x^{(1)}=0$")
box(1.8, 3.2, 2.1, 2.0,
    "Reset $|0000\\rangle$\n$R_y(\\theta^{(1)}+x^{(1)})$\n4 ordered CNOTs\nmeasure $z^{(1)}$")
box(4.4, 3.7, 2.2, 1.0, r"$x^{(2)}=W_1z^{(1)}+b_1$")
box(7.1, 3.2, 2.1, 2.0,
    "Reset $|0000\\rangle$\n$R_y(\\theta^{(2)}+x^{(2)})$\n4 ordered CNOTs\nmeasure $z^{(2)}$")
box(9.7, 3.7, 2.1, 1.0, r"$x^{(3)}=W_2z^{(2)}+b_2+\gamma z^{(1)}$")
for a, b in [((1.4, 4.15), (1.8, 4.15)), ((3.9, 4.15), (4.4, 4.15)),
             ((6.6, 4.15), (7.1, 4.15)), ((9.2, 4.15), (9.7, 4.15))]:
    arrow(a, b)
arrow((2.85, 3.2), (10.5, 3.65), dashed=True)
ax.text(6.5, 2.75, r"fixed shortcut $\gamma z^{(1)}$; first active at $D=3$", ha="center")
box(1.0, .45, 4.4, 1.25,
    "Baseline $E=0$ (every block)\n" + r"$0\to1,\;1\to2,\;2\to3,\;3\to0$", "0.95")
box(6.4, .45, 4.6, 1.25,
    "Pair-restricted $E=1$\n" +
    r"odd: $0\leftrightarrow1,\;2\leftrightarrow3$; even: $1\leftrightarrow2,\;3\leftrightarrow0$",
    "0.95")
ax.text(11.8, 5.6, r"repeat to terminal reset block $\rightarrow C_L$", ha="right")
fig.tight_layout(pad=.3)
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, bbox_inches="tight", metadata={"CreationDate": None, "ModDate": None})
fig.savefig(PREVIEW, dpi=180, bbox_inches="tight")
plt.close(fig)
