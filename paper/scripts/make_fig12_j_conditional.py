"""Render conditional exact-gradient J indices from the frozen summary CSV."""
from pathlib import Path
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
mpl.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"})
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "results/jel_conditional/summary.csv"
OUT = ROOT / "paper/figures/fig12_j_conditional.pdf"

d = pd.read_csv(SOURCE)
expected = {
    ("original", "J_EL_given_R0"),
    ("original", "J_EL_given_R1"),
    ("independent_seed", "J_EL_given_R0"),
    ("independent_seed", "J_EL_given_R1"),
}
assert set(zip(d.dataset, d.estimand)) == expected
labels = ["Original\n$R=0$", "Original\n$R=1$", "Independent seed\n$R=0$", "Independent seed\n$R=1$"]
d["order"] = d.dataset.map({"original": 0, "independent_seed": 2}) + d.estimand.map({"J_EL_given_R0": 0, "J_EL_given_R1": 1})
d = d.sort_values("order")

fig, ax = plt.subplots(figsize=(6.6, 3.4))
for i, row in enumerate(d.itertuples()):
    marker = "o" if "R0" in row.estimand else "s"
    linestyle = "-" if row.dataset == "original" else "--"
    ax.errorbar(i, row.estimate,
                yerr=[[row.estimate-row.ci_lo], [row.ci_hi-row.estimate]],
                fmt=marker, linestyle=linestyle, color="black", capsize=3,
                markersize=5, linewidth=1.2)
ax.axhline(1, color="0.45", linestyle=":", linewidth=1)
ax.set_xticks(range(4), labels)
ax.set_ylabel(r"Conditional exact-gradient index $J_{EL\mid R}$")
ax.set_ylim(0.9, 1.52)
ax.grid(axis="y", color="0.9", linewidth=0.6)
fig.tight_layout()
OUT.parent.mkdir(parents=True, exist_ok=True)
metadata = {"Creator": "make_fig12_j_conditional.py", "CreationDate": None, "ModDate": None}
fig.savefig(OUT, metadata=metadata)
fig.savefig(OUT.with_name(OUT.stem + "_preview.png"), dpi=200)
print(OUT)
