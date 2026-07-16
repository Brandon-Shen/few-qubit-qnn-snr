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


def generate_all_plots():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    main_df = pd.read_csv(os.path.join(RESULTS_DIR, "main_experiment_summary.csv"))
    depth_df = pd.read_csv(os.path.join(RESULTS_DIR, "depth_sweep_summary.csv"))

    plot_snr_by_config_box(main_df, os.path.join(PLOTS_DIR, "snr_by_config_box.png"))
    plot_snr_by_config_bar(main_df, os.path.join(PLOTS_DIR, "snr_by_config_bar.png"))
    plot_snr_vs_depth(depth_df, os.path.join(PLOTS_DIR, "snr_vs_depth.png"))

    print(f"Saved plots to {PLOTS_DIR}")


if __name__ == "__main__":
    generate_all_plots()
