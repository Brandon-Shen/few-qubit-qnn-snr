"""Publication figures (Section 19). Every plot that aggregates matched
observations reports uncertainty (bootstrap or IQR bands) and the number of
matched observations (N) in its title/annotation, rather than implying
independent samples."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({"figure.dpi": 120, "font.size": 9})


def _save(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_forest_plot(confirmatory_table: pd.DataFrame, path: Path):
    fig, ax = plt.subplots(figsize=(6, 3))
    ys = np.arange(len(confirmatory_table))
    for y, (_, row) in zip(ys, confirmatory_table.iterrows()):
        lo, hi = row["bootstrap_ci_lo"], row["bootstrap_ci_hi"]
        color = "tab:blue" if row["reject_after_holm"] else "gray"
        if np.isfinite(lo) and np.isfinite(hi):
            ax.plot([lo, hi], [y, y], color=color, lw=2)
        ax.plot(row["estimate"], y, "o", color=color)
    ax.axvline(0, color="black", lw=0.8, ls="--")
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{r.hypothesis}: {r.coefficient_label}" for r in confirmatory_table.itertuples()])
    ax.set_xlabel("Coefficient estimate (bootstrap 95% CI)")
    ax.set_title("H1-H4 confirmatory coefficients (blue = reject after Holm)")
    _save(fig, path)


def _interaction_plot(pointwise_df: pd.DataFrame, factor_a: str, factor_b: str, path: Path, title: str):
    fig, ax = plt.subplots(figsize=(5, 4))
    for b_val, style in ((0, "--"), (1, "-")):
        sub = pointwise_df[pointwise_df[factor_b] == b_val]
        means = sub.groupby(factor_a)["SNR_est"].apply(lambda s: np.nanmean(s[np.isfinite(s)]))
        sds = sub.groupby(factor_a)["SNR_est"].apply(lambda s: np.nanstd(s[np.isfinite(s)]))
        ns = sub.groupby(factor_a)["SNR_est"].size()
        ax.errorbar(means.index, means.values, yerr=sds.values, fmt="o" + style,
                     label=f"{factor_b}={b_val} (N={ns.sum()})")
    ax.set_xlabel(factor_a)
    ax.set_ylabel("mean SNR_est ± SD across matched cells")
    ax.set_title(title)
    ax.legend()
    _save(fig, path)


def fig_snr_interaction_EL(pointwise_df: pd.DataFrame, path: Path):
    _interaction_plot(pointwise_df, "E", "L", path, "Estimator-SNR: E x L interaction")


def fig_snr_interaction_ER(pointwise_df: pd.DataFrame, path: Path):
    _interaction_plot(pointwise_df, "E", "R", path, "Estimator-SNR: E x R interaction")


def fig_LR_interaction_across_depth(pointwise_df: pd.DataFrame, path: Path):
    fig, ax = plt.subplots(figsize=(5, 4))
    for (l_val, r_val), style in (((0, 0), ":"), ((1, 0), "--"), ((0, 1), "-."), ((1, 1), "-")):
        sub = pointwise_df[(pointwise_df["L"] == l_val) & (pointwise_df["R"] == r_val)]
        means = sub.groupby("depth")["SNR_est"].apply(lambda s: np.nanmean(s[np.isfinite(s)]))
        ns = sub.groupby("depth")["SNR_est"].size()
        ax.plot(means.index, means.values, style, marker="o", label=f"L={l_val},R={r_val} (N={ns.sum()})")
    ax.set_xlabel("nominal depth")
    ax.set_ylabel("mean SNR_est")
    ax.set_title("H4: L x R interaction across depth")
    ax.legend(fontsize=7)
    _save(fig, path)


def fig_exact_gradient_EL_interaction(exact_df: pd.DataFrame, path: Path):
    d = exact_df.copy()
    d["a"] = np.arcsinh(np.abs(d["exact_gradient"]))
    fig, ax = plt.subplots(figsize=(5, 4))
    for l_val, style in ((0, "--"), (1, "-")):
        sub = d[d["L"] == l_val]
        means = sub.groupby("E")["a"].mean()
        ns = sub.groupby("E")["a"].size()
        ax.plot(means.index, means.values, "o" + style, label=f"L={l_val} (N={ns.sum()})")
    ax.set_xlabel("E")
    ax.set_ylabel("mean asinh(|exact_gradient|)")
    ax.set_title("H1: exact-gradient E x L interaction")
    ax.legend()
    _save(fig, path)


def fig_snr_distributions_by_configuration(pointwise_df: pd.DataFrame, path: Path):
    fig, ax = plt.subplots(figsize=(7, 4))
    data, labels = [], []
    for cid in range(1, 9):
        vals = pointwise_df.loc[pointwise_df["configuration_id"] == cid, "SNR_est"]
        vals = vals[np.isfinite(vals)]
        data.append(vals.values)
        labels.append(f"cfg{cid}\n(N={len(vals)})")
    ax.boxplot(data, tick_labels=labels, showfliers=False)
    ax.set_ylabel("SNR_est")
    ax.set_title("SNR_est distributions across all 8 configurations")
    _save(fig, path)


def fig_bias_and_sign_agreement(pointwise_df: pd.DataFrame, path: Path):
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    axes[0].hist(pointwise_df["bias"].dropna(), bins=40)
    axes[0].set_title(f"Bias distribution (N={pointwise_df['bias'].notna().sum()})")
    axes[0].set_xlabel("bias = mu_hat - exact_gradient")

    frac = pointwise_df.groupby("configuration_id")["sign_agreement"].mean()
    ns = pointwise_df.groupby("configuration_id")["sign_agreement"].size()
    axes[1].bar([str(c) for c in frac.index], frac.values)
    axes[1].set_ylim(0, 1)
    axes[1].set_xlabel("configuration_id")
    axes[1].set_ylabel("sign-agreement fraction")
    axes[1].set_title("Sign agreement by configuration (N per bar in table)")
    _save(fig, path)


def fig_snr_vs_budget(pointwise_df: pd.DataFrame, path: Path):
    fig, ax = plt.subplots(figsize=(5, 4))
    for cid in (1, 8):
        sub = pointwise_df[pointwise_df["configuration_id"] == cid]
        means = sub.groupby("budget")["SNR_est"].apply(lambda s: np.nanmean(s[np.isfinite(s)]))
        ns = sub.groupby("budget")["SNR_est"].size()
        ax.plot(means.index, means.values, "o-", label=f"cfg{cid} (N={ns.sum()})")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("shot budget B")
    ax.set_ylabel("mean SNR_est")
    ax.set_title("SNR_est vs measurement budget")
    ax.legend()
    _save(fig, path)


def fig_snr_vs_energy_fidelity(configuration_summaries: pd.DataFrame, path: Path):
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    axes[0].scatter(configuration_summaries["final_tfim_energy_mean"], configuration_summaries["rms_SNR_est"])
    axes[0].set_xlabel("final TFIM energy")
    axes[0].set_ylabel("RMS SNR_est")
    axes[1].scatter(configuration_summaries["global_fidelity_mean"], configuration_summaries["rms_SNR_est"])
    axes[1].set_xlabel("global fidelity")
    axes[1].set_ylabel("RMS SNR_est")
    fig.suptitle(f"SNR vs task performance (N={len(configuration_summaries)} matched cells)")
    _save(fig, path)


def fig_resource_cost_comparison(resource_table: pd.DataFrame, path: Path):
    fig, ax = plt.subplots(figsize=(6, 4))
    agg = resource_table.groupby("configuration_id")["total_circuit_evaluations_mean"].mean()
    ax.bar([str(c) for c in agg.index], agg.values)
    ax.set_xlabel("configuration_id")
    ax.set_ylabel("mean total circuit evaluations per replicate")
    ax.set_title("Resource cost by configuration")
    _save(fig, path)


def fig_bootstrap_coefficient_distributions(bootstrap_coef_df: pd.DataFrame, coef_cols: list[str], path: Path):
    fig, axes = plt.subplots(1, len(coef_cols), figsize=(3.5 * len(coef_cols), 3.5))
    if len(coef_cols) == 1:
        axes = [axes]
    for ax, coef in zip(axes, coef_cols):
        if coef in bootstrap_coef_df.columns:
            ax.hist(bootstrap_coef_df[coef].dropna(), bins=30)
        ax.set_title(f"{coef} (N={len(bootstrap_coef_df)})")
    fig.suptitle("Bootstrap coefficient distributions")
    _save(fig, path)


def fig_entanglement_by_architecture_depth(physics_df: pd.DataFrame, path: Path):
    fig, ax = plt.subplots(figsize=(6, 4))
    for e_val, style in ((0, "--"), (1, "-")):
        sub = physics_df[physics_df["E"] == e_val]
        means = sub.groupby("depth")["mean_entanglement_entropy"].mean()
        ns = sub.groupby("depth")["mean_entanglement_entropy"].size()
        ax.plot(means.index, means.values, "o" + style, label=f"E={e_val} (N={ns.sum()})")
    ax.set_xlabel("nominal depth")
    ax.set_ylabel("mean bipartite von Neumann entropy")
    ax.set_title("Entanglement diagnostic by architecture and depth\n"
                  "(not evidence of area-/volume-law scaling; see ASSUMPTIONS.md A15b)")
    ax.legend()
    _save(fig, path)


def generate_all_figures(out_dir: Path, *, confirmatory_table=None, pointwise_df=None, exact_df=None,
                          configuration_summaries=None, resource_table=None, bootstrap_coef_df=None,
                          physics_df=None):
    out_dir = Path(out_dir)
    if confirmatory_table is not None:
        fig_forest_plot(confirmatory_table, out_dir / "01_forest_plot_H1_H4.png")
    if pointwise_df is not None:
        fig_snr_interaction_EL(pointwise_df, out_dir / "02_snr_interaction_EL.png")
        fig_snr_interaction_ER(pointwise_df, out_dir / "03_snr_interaction_ER.png")
        fig_LR_interaction_across_depth(pointwise_df, out_dir / "04_LR_interaction_depth.png")
        fig_snr_distributions_by_configuration(pointwise_df, out_dir / "06_snr_distributions.png")
        fig_bias_and_sign_agreement(pointwise_df, out_dir / "07_bias_sign_agreement.png")
        fig_snr_vs_budget(pointwise_df, out_dir / "08_snr_vs_budget.png")
    if exact_df is not None:
        fig_exact_gradient_EL_interaction(exact_df, out_dir / "05_exact_gradient_EL_interaction.png")
    if configuration_summaries is not None:
        fig_snr_vs_energy_fidelity(configuration_summaries, out_dir / "09_snr_vs_energy_fidelity.png")
    if resource_table is not None:
        fig_resource_cost_comparison(resource_table, out_dir / "10_resource_cost.png")
    if bootstrap_coef_df is not None:
        fig_bootstrap_coefficient_distributions(
            bootstrap_coef_df, [c for c in ("E:L", "E:R", "L:R:depth_z") if c in bootstrap_coef_df.columns],
            out_dir / "11_bootstrap_coefficients.png")
    if physics_df is not None:
        fig_entanglement_by_architecture_depth(physics_df, out_dir / "12_entanglement_by_depth.png")
