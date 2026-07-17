"""Plots: SNR-by-configuration (box + bar) and SNR-vs-depth (H3).

Styling follows a fixed categorical hue order (never cycled/re-assigned per
filter) and a light neutral chart surface, per the project's dataviz
conventions; hex values below are the validated default categorical palette.
"""
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")

CATEGORICAL = ["#2a78d6", "#008300", "#e87ba4", "#eda100", "#1baf7a", "#eb6834", "#4a3aa7", "#e34948"]
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
AXIS_LINE = "#c3c2b7"

CONFIG_ORDER = [
    "baseline", "entanglement_only", "local_cost_only", "residual_only",
    "entanglement_local", "entanglement_residual", "combined",
]
CONFIG_LABELS = {
    "baseline": "1. Baseline", "entanglement_only": "2. Entanglement",
    "local_cost_only": "3. Local cost", "residual_only": "4. Residual",
    "entanglement_local": "5. Ent.+local", "entanglement_residual": "6. Ent.+residual",
    "combined": "7. Combined",
}

DEPTH_CONFIG_ORDER = ["local_cost_only", "residual_only", "local_and_residual"]
DEPTH_CONFIG_LABELS = {
    "local_cost_only": "Local cost only", "residual_only": "Residual only",
    "local_and_residual": "Local cost + residual",
}

# Status pair (fixed, reserved meaning -- never themed/cycled): used only for
# the companion-paper phase's "does this grid point replicate the pilot's
# finding" heatmaps below, where a cell genuinely is good/bad relative to a
# hypothesis, not just "series N".
STATUS_GOOD = "#0ca30c"
STATUS_CRITICAL = "#d03b3b"

TASK_ORDER = ["tfim_h0.5", "tfim_h2.0", "xxz_delta0.5"]
TASK_LABELS = {
    "tfim_h0.5": "TFIM (h=0.5)", "tfim_h2.0": "TFIM (h=2.0)", "xxz_delta0.5": "XXZ (Delta=0.5)",
}


def _style_axes(ax):
    ax.set_facecolor(SURFACE)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color(AXIS_LINE)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)
    ax.yaxis.grid(True, color=GRIDLINE, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    ax.title.set_color(INK_PRIMARY)
    ax.xaxis.label.set_color(INK_SECONDARY)
    ax.yaxis.label.set_color(INK_SECONDARY)


def plot_snr_by_config_box(main_df, out_path):
    fig, ax = plt.subplots(figsize=(9, 5.5), facecolor=SURFACE)
    data = [main_df[main_df["config_name"] == c]["mean_snr"].to_numpy() for c in CONFIG_ORDER]
    labels = [CONFIG_LABELS[c] for c in CONFIG_ORDER]
    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True, widths=0.55,
                     medianprops={"color": INK_PRIMARY, "linewidth": 2},
                     whiskerprops={"color": INK_SECONDARY}, capprops={"color": INK_SECONDARY},
                     flierprops={"markeredgecolor": INK_MUTED, "markersize": 4})
    for patch, color in zip(bp["boxes"], CATEGORICAL):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
        patch.set_edgecolor(color)
    _style_axes(ax)
    ax.set_ylabel("Per-seed mean gradient SNR")
    ax.set_title("Gradient SNR by ablation configuration (n=50 seeds each, L=3)")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def plot_snr_by_config_bar(main_df, out_path):
    means = [main_df[main_df["config_name"] == c]["mean_snr"].mean() for c in CONFIG_ORDER]
    stds = [main_df[main_df["config_name"] == c]["mean_snr"].std() for c in CONFIG_ORDER]
    labels = [CONFIG_LABELS[c] for c in CONFIG_ORDER]

    fig, ax = plt.subplots(figsize=(9, 5.5), facecolor=SURFACE)
    x = np.arange(len(labels))
    ax.bar(x, means, yerr=stds, capsize=4, color=CATEGORICAL[: len(labels)],
           edgecolor="none", zorder=3,
           error_kw={"ecolor": INK_SECONDARY, "elinewidth": 1.2})
    _style_axes(ax)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Mean gradient SNR across 50 seeds (+/- 1 std)")
    ax.set_title("Gradient SNR by ablation configuration (L=3)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def plot_snr_vs_depth(depth_df, out_path):
    """Uses median + IQR (not mean +/- std) and a log y-axis: SNR is heavy-tailed
    (near-deterministic shallow circuits can produce very large finite SNRs for
    individual seeds), so mean/std is dominated by outliers and would otherwise
    compress the L>=2 region into an unreadable sliver.
    """
    fig, ax = plt.subplots(figsize=(8, 5.5), facecolor=SURFACE)
    depths = sorted(depth_df["L"].unique())
    for i, cfg in enumerate(DEPTH_CONFIG_ORDER):
        medians, q25, q75 = [], [], []
        for L in depths:
            sub = depth_df[(depth_df["config_name"] == cfg) & (depth_df["L"] == L)]["mean_snr"]
            medians.append(sub.median())
            q25.append(sub.quantile(0.25))
            q75.append(sub.quantile(0.75))
        medians = np.array(medians)
        color = CATEGORICAL[i]
        ax.plot(depths, medians, marker="o", markersize=6, linewidth=2, color=color,
                label=DEPTH_CONFIG_LABELS[cfg], zorder=3)
        ax.fill_between(depths, q25, q75, color=color, alpha=0.15, zorder=2)
    _style_axes(ax)
    ax.set_yscale("log")
    ax.set_xlabel("Circuit depth L (layers)")
    ax.set_ylabel("Median gradient SNR across 50 seeds (log scale, shaded = IQR)")
    ax.set_title("Gradient SNR vs. circuit depth (H3)")
    ax.set_xticks(depths)
    legend = ax.legend(frameon=False, labelcolor=INK_PRIMARY, loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


# ============================================================================
# Companion-paper phase 2 plots.
# ============================================================================

_HEATMAP_PANELS = [
    ("entanglement_only_is_best", "Entanglement-alone is best config\n(replicates pilot finding)"),
    ("combined_worse_than_baseline", "Combined underperforms baseline\n(replicates pilot finding)"),
    ("h2a_sum_framing_sub_additive", "H2a: entanglement+local is sub-additive\n(sum framing)"),
    ("h2b_sum_framing_sub_additive", "H2b: entanglement+residual is sub-additive\n(sum framing)"),
]


def plot_hypothesis_heatmap_grid(grid_summary_df, out_path):
    """2x2 small-multiples heatmap: rows=task, columns=n_qubits, cell=whether
    that grid point replicates the pilot's finding / shows sub-additivity
    (good/critical status color -- these are genuinely good/bad relative to
    the pilot's headline claims, not arbitrary series identity). Each cell is
    also directly labeled (Y/N), per the status-color pairing rule.
    """
    n_values = sorted(grid_summary_df["n_qubits"].unique())
    tasks = [t for t in TASK_ORDER if t in grid_summary_df["task"].unique()]

    fig, axes = plt.subplots(2, 2, figsize=(11, 7), facecolor=SURFACE)
    for ax, (col, title) in zip(axes.flat, _HEATMAP_PANELS):
        grid = np.zeros((len(tasks), len(n_values)))
        for i, task in enumerate(tasks):
            for j, n in enumerate(n_values):
                row = grid_summary_df[(grid_summary_df["task"] == task)
                                       & (grid_summary_df["n_qubits"] == n)]
                grid[i, j] = 1.0 if bool(row[col].iloc[0]) else 0.0

        cmap = plt.matplotlib.colors.ListedColormap([STATUS_CRITICAL, STATUS_GOOD])
        ax.imshow(grid, cmap=cmap, vmin=0, vmax=1, aspect="auto")
        for i in range(len(tasks)):
            for j in range(len(n_values)):
                label = "Y" if grid[i, j] == 1.0 else "N"
                ax.text(j, i, label, ha="center", va="center", color="white",
                        fontsize=9, fontweight="bold")
        ax.set_xticks(range(len(n_values)))
        ax.set_xticklabels([f"n={n}" for n in n_values], fontsize=8)
        ax.set_yticks(range(len(tasks)))
        ax.set_yticklabels([TASK_LABELS.get(t, t) for t in tasks], fontsize=8)
        ax.set_title(title, fontsize=9.5, color=INK_PRIMARY)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)

    handles = [
        plt.matplotlib.patches.Patch(facecolor=STATUS_GOOD, label="Yes"),
        plt.matplotlib.patches.Patch(facecolor=STATUS_CRITICAL, label="No"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
               labelcolor=INK_PRIMARY, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Does the pilot's n=4 / TFIM(h=0.5) finding replicate across the grid?",
                 fontsize=12, color=INK_PRIMARY)
    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    fig.savefig(out_path, dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def plot_sensitivity_comparison(sensitivity_combined_df, out_path):
    """Grouped-bar comparison of mean SNR under residual_reduction='mean'
    (primary) vs. 'sum' (secondary sensitivity check), for the three
    residual-bearing configs only (the other four are provably invariant to
    this toggle -- see README "Design choices" -- so plotting them would be
    uninformative), faceted by task, grouped by whichever n_qubits values are
    present in `sensitivity_combined_df` (SENSITIVITY_N_QUBITS in
    experiment.py). Color encodes reduction identity (2 series, fixed
    categorical slots 1 and 8 for maximum CVD separation).
    """
    residual_configs = ["residual_only", "entanglement_residual", "combined"]
    tasks = [t for t in TASK_ORDER if t in sensitivity_combined_df["task"].unique()]
    n_values = sorted(sensitivity_combined_df["n_qubits"].unique())
    reductions = ["mean", "sum"]
    colors = {"sum": CATEGORICAL[0], "mean": CATEGORICAL[7]}

    fig, axes = plt.subplots(1, len(tasks), figsize=(5 * len(tasks), 5), facecolor=SURFACE,
                              sharey=True)
    if len(tasks) == 1:
        axes = [axes]

    bar_width = 0.35
    for ax, task in zip(axes, tasks):
        x_labels = [f"{CONFIG_LABELS[c].split('. ')[1]}\n(n={n})"
                    for n in n_values for c in residual_configs]
        x = np.arange(len(x_labels))
        for k, reduction in enumerate(reductions):
            heights = []
            for n in n_values:
                for c in residual_configs:
                    sub = sensitivity_combined_df[
                        (sensitivity_combined_df["task"] == task)
                        & (sensitivity_combined_df["n_qubits"] == n)
                        & (sensitivity_combined_df["config_name"] == c)
                        & (sensitivity_combined_df["residual_reduction"] == reduction)
                    ]
                    heights.append(sub["mean_snr"].mean())
            offset = (k - 0.5) * bar_width
            ax.bar(x + offset, heights, width=bar_width, color=colors[reduction],
                   label=reduction, zorder=3)
        _style_axes(ax)
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, fontsize=7, rotation=15, ha="right")
        ax.set_title(TASK_LABELS.get(task, task), fontsize=10, color=INK_PRIMARY)
        ax.set_ylabel("Mean gradient SNR")

    handles = [plt.matplotlib.patches.Patch(facecolor=colors[r], label=r) for r in reductions]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
               labelcolor=INK_PRIMARY, bbox_to_anchor=(0.5, -0.06))
    n_label = ", ".join(f"n={n}" for n in n_values)
    fig.suptitle(f"Residual-connection mean (primary) vs. sum (secondary) reduction: "
                 f"mean SNR at {n_label}", fontsize=12, color=INK_PRIMARY)
    fig.tight_layout(rect=[0, 0.05, 1, 0.94])
    fig.savefig(out_path, dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def plot_depth_sweep_faceted(depth_scoped_df, out_path):
    """3-panel (n=4,6,10) faceted version of `plot_snr_vs_depth`: same
    median+IQR / log-scale styling per panel, testing whether the pilot's H3
    crossover direction (found reversed from the original hypothesis at n=4)
    is stable as qubit count grows.
    """
    n_values = sorted(depth_scoped_df["n_qubits"].unique())
    depths = sorted(depth_scoped_df["L"].unique())

    fig, axes = plt.subplots(1, len(n_values), figsize=(5.5 * len(n_values), 5.5),
                              facecolor=SURFACE, sharey=True)
    if len(n_values) == 1:
        axes = [axes]

    for ax, n_qubits in zip(axes, n_values):
        sub_n = depth_scoped_df[depth_scoped_df["n_qubits"] == n_qubits]
        for i, cfg in enumerate(DEPTH_CONFIG_ORDER):
            medians, q25, q75 = [], [], []
            for L in depths:
                sub = sub_n[(sub_n["config_name"] == cfg) & (sub_n["L"] == L)]["mean_snr"]
                medians.append(sub.median())
                q25.append(sub.quantile(0.25))
                q75.append(sub.quantile(0.75))
            color = CATEGORICAL[i]
            ax.plot(depths, medians, marker="o", markersize=6, linewidth=2, color=color,
                    label=DEPTH_CONFIG_LABELS[cfg], zorder=3)
            ax.fill_between(depths, q25, q75, color=color, alpha=0.15, zorder=2)
        _style_axes(ax)
        ax.set_yscale("log")
        ax.set_xlabel("Circuit depth L (layers)")
        ax.set_title(f"n_qubits = {n_qubits}", fontsize=11, color=INK_PRIMARY)
        ax.set_xticks(depths)

    axes[0].set_ylabel("Median gradient SNR (log scale, shaded = IQR)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               labelcolor=INK_PRIMARY, bbox_to_anchor=(0.5, -0.04))
    fig.suptitle("Gradient SNR vs. circuit depth, faceted by qubit count (scoped H3)",
                 fontsize=12, color=INK_PRIMARY)
    fig.tight_layout(rect=[0, 0.06, 1, 0.94])
    fig.savefig(out_path, dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def generate_all_plots():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    main_df = pd.read_csv(os.path.join(RESULTS_DIR, "main_experiment_summary.csv"))
    depth_df = pd.read_csv(os.path.join(RESULTS_DIR, "depth_sweep_summary.csv"))

    plot_snr_by_config_box(main_df, os.path.join(PLOTS_DIR, "snr_by_config_box.png"))
    plot_snr_by_config_bar(main_df, os.path.join(PLOTS_DIR, "snr_by_config_bar.png"))
    plot_snr_vs_depth(depth_df, os.path.join(PLOTS_DIR, "snr_vs_depth.png"))

    print(f"Saved plots to {PLOTS_DIR}")


def generate_companion_phase_plots():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    grid_summary_df = pd.read_csv(os.path.join(RESULTS_DIR, "grid_hypothesis_summary.csv"))
    sensitivity_sum_df = pd.read_csv(os.path.join(RESULTS_DIR, "sensitivity_sum_summary.csv"))
    sensitivity_mean_df = pd.read_csv(os.path.join(RESULTS_DIR, "sensitivity_mean_summary.csv"))
    sensitivity_combined_df = pd.concat([sensitivity_sum_df, sensitivity_mean_df],
                                         ignore_index=True)
    depth_scoped_df = pd.read_csv(os.path.join(RESULTS_DIR, "depth_sweep_scoped_summary.csv"))

    plot_hypothesis_heatmap_grid(grid_summary_df,
                                  os.path.join(PLOTS_DIR, "grid_hypothesis_heatmap.png"))
    plot_sensitivity_comparison(sensitivity_combined_df,
                                 os.path.join(PLOTS_DIR, "sensitivity_sum_vs_mean.png"))
    plot_depth_sweep_faceted(depth_scoped_df,
                              os.path.join(PLOTS_DIR, "depth_sweep_scoped_faceted.png"))

    print(f"Saved companion-phase plots to {PLOTS_DIR}")


if __name__ == "__main__":
    generate_all_plots()
