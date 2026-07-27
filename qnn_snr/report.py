"""Publication tables and markdown report generation (Section 18).

`results_summary.md` automatically generates wording that keeps four
distinctions explicit throughout (Section 18):
  - rejection vs. failure to reject a Holm-corrected null;
  - a signal-level (H1, exact-gradient) interaction vs. an estimator-SNR
    (H2-H4) interaction -- these are different outcome scales and different
    scientific claims;
  - a statistical interaction (a mixed-model coefficient) vs. improved task
    performance (final energy / global fidelity) -- Section 16's
    configuration-8 comparisons are exploratory and kept labeled as such;
  - confirmatory findings (H1-H4, Holm-adjusted) vs. exploratory findings
    (three-way interaction, configuration-8 comparisons, interaction
    indices, sensitivity models).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from qnn_snr.config import config_hash as _config_hash

ASSUMPTIONS_PATH = Path(__file__).resolve().parent.parent / "ASSUMPTIONS.md"

STATISTICAL_METHODS_TEMPLATE = """# Statistical methods

## Pointwise estimator statistics (Section 9)
Within each (analysis_mode, configuration, matched parameter, depth, budget,
initialization) cell, `mu_hat = mean(gradient_hat)` and `shot_sd =
sqrt(sample variance of gradient_hat, ddof=1)` across the R replicate signed
gradients. `SNR_est = |mu_hat| / shot_sd` and, where an exact reference is
available, `SNR_exact = |exact_gradient| / shot_sd`. The denominator is
always the sample SD across replicates, never the standard error of the
mean (no division by sqrt(R)). Cells with exactly zero replicate variance
are flagged explicitly (`zero_variance_flag`) and excluded from the SNR
mixed model rather than assigned an arbitrary large finite value.

## H1: exact-signal mixed model (Section 10)
`asinh(|exact_gradient|) ~ E*L*R + depth_z + E:depth_z + L:depth_z +
R:depth_z + (1|initialization_id) + (1|initialization_id:depth:parameter_id)`,
fit once per matched initial parameter point (before any optimizer update).
`eta_EL` is the `E:L` coefficient. Two-sided test.

## H2-H4: estimator-SNR mixed model (Section 11)
`asinh(SNR_est) ~ E*L*R + depth_z + log2_budget + E:depth_z + L:depth_z +
R:depth_z + L:R:depth_z + (1|initialization_id) +
(1|initialization_id:depth:parameter_id)`. `beta_EL` (H2), `beta_ER` (H3),
and `beta_LRd` (H4, the `L:R:depth_z` coefficient) are all two-sided tests.
The `E:L:R` coefficient in this model is exploratory only.

## Mixed-model implementation (Section 12)
`statsmodels` `MixedLM` with `groups=initialization_id` and a nested
variance component (`vc_formula`) keyed by a combined
`initialization_id:depth:parameter_id` label (ASSUMPTIONS.md A20), fit with
REML and an optimizer fallback order (lbfgs -> bfgs -> cg -> powell -> nm)
until convergence. Convergence status, random-effect variances, a design-
matrix condition number, and residual diagnostics are recorded for every
fit; a failed fit is reported, never silently replaced by OLS.

## Confirmatory p-values and Holm-Bonferroni (Section 13)
Unadjusted two-sided p-values use each coefficient's mixed-model Wald
z-statistic against a normal reference (documented default,
`stats.p_value_method`, ASSUMPTIONS.md A9). Holm-Bonferroni is applied
jointly across exactly four coefficients (eta_EL, beta_EL, beta_ER,
beta_LRd) at family-wise alpha=0.05. A confirmatory claim requires the
Holm-adjusted p-value to meet alpha; failure to reject is never described as
proof of zero effect, additivity, or equivalence.

## Nested matched bootstrap (Section 14)
Outer resampling draws complete initialization IDs with replacement,
relabeling repeated draws with unique bootstrap-cluster ids and carrying
every configuration/parameter/depth/budget that belongs to the drawn
initialization. The estimator-SNR bootstrap additionally resamples, within
every selected cell, the R replicate signed gradients with replacement
before recomputing pointwise statistics and refitting the model. The
exact-signal (H1) bootstrap needs no inner resampling. Percentile intervals
are reported; failed fits are tracked and reported, never silently dropped.

## Secondary interaction indices (Section 15)
`I_AB = (M_AB * M_0) / (M_A * M_B)` (M = RMS pointwise SNR_est) and the
analogous `J_AB` on RMS exact-gradient magnitude, for E x L, E x R, L x R.
Secondary/descriptive only. A zero or undefined denominator is reported as
`undefined` with a stated reason, never replaced by an epsilon.
"""


def write_assumptions_snapshot(results_dir: Path) -> Path:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / "assumptions_snapshot.md"
    out_path.write_text(ASSUMPTIONS_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return out_path


def write_statistical_methods(results_dir: Path) -> Path:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / "statistical_methods.md"
    out_path.write_text(STATISTICAL_METHODS_TEMPLATE, encoding="utf-8")
    return out_path


def _hypothesis_sentence(row: pd.Series) -> str:
    scale = "exact-gradient signal" if row["hypothesis"] == "H1" else "estimator-SNR"
    verdict = "rejected" if row["reject_after_holm"] else "not rejected"
    direction = ""
    if row["reject_after_holm"] and pd.notna(row["bootstrap_ci_lo"]) and pd.notna(row["bootstrap_ci_hi"]):
        if row["bootstrap_ci_hi"] < 0:
            direction = " (sub-additive on the tested scale)"
        elif row["bootstrap_ci_lo"] > 0:
            direction = " (super-additive on the tested scale)"
    return (
        f"- **{row['hypothesis']}** ({row['coefficient_label']}, {scale} scale): H0 is **{verdict}** "
        f"after Holm correction (estimate={row['estimate']:.4g}, p_holm={row['p_holm']:.4g}){direction}. "
        f"{row['interpretation']}"
    )


def generate_results_summary(confirmatory_table: pd.DataFrame, interaction_indices: pd.DataFrame,
                              configuration_summaries: pd.DataFrame, exploratory_table: pd.DataFrame,
                              cfg) -> str:
    lines = []
    lines.append(f"# Results summary: {cfg.name}")
    lines.append("")
    lines.append(
        "Scope: 4-qubit open-boundary TFIM, nominal depths "
        f"{cfg.circuit.depths}, finite-shot budgets {cfg.budget.values}, "
        f"{cfg.design.n_initializations} matched initializations, "
        f"{cfg.design.replicates} replicates per finite-shot cell. "
        "Conclusions below are limited to this tested design; they are not "
        "general claims about barren plateaus, other qubit counts, or other "
        "circuit families."
    )
    lines.append("")
    lines.append("## Confirmatory results (H1-H4, Holm-adjusted, family-wise alpha=0.05)")
    lines.append("")
    for _, row in confirmatory_table.iterrows():
        lines.append(_hypothesis_sentence(row))
    lines.append("")
    lines.append(
        "H1 tests an interaction in the **exact-gradient signal** "
        "(asinh(|exact_gradient|)); H2-H4 test interactions in the "
        "**estimator SNR** (asinh(SNR_est)). These are different outcome "
        "scales and different scientific claims -- a rejection in one family "
        "does not imply a rejection in the other, and neither is a claim "
        "about optimizer or task success on its own."
    )
    lines.append("")
    lines.append(
        "Any hypothesis marked 'not rejected' above is **not** evidence "
        "that the tested coefficient equals zero, that the two "
        "interventions are additive, or that they have identical effects; "
        "no equivalence test was prespecified for this run."
    )
    lines.append("")

    lines.append("## Secondary interaction indices (descriptive, not confirmatory)")
    lines.append("")
    for _, row in interaction_indices.iterrows():
        if pd.isna(row["I_AB"]):
            lines.append(f"- {row['pair']}: I_AB undefined ({row['I_AB_undefined_reason']}).")
        else:
            lines.append(f"- {row['pair']}: I_AB={row['I_AB']:.3g} ({row['interpretation']}).")
    lines.append("")

    lines.append("## Exploratory findings (not part of the Holm family)")
    lines.append("")
    lines.append(
        "The E:L:R three-way interaction, whether configuration 8 exceeds "
        "the best single-intervention configuration in SNR, final energy, "
        "global fidelity, and circuit-cost-normalized SNR are reported in "
        "`exploratory_results.csv`. A statistical interaction between "
        "interventions (a mixed-model coefficient) is a distinct claim from "
        "improved task performance (lower final energy or higher global "
        "fidelity); both are reported separately below and neither is "
        "confirmatory."
    )
    if not exploratory_table.empty:
        n_snr_wins = int(exploratory_table["config8_exceeds_best_single_SNR"].sum())
        n_cells = len(exploratory_table)
        lines.append(
            f"- Configuration 8 exceeded the best single-intervention configuration's RMS SNR_est in "
            f"{n_snr_wins}/{n_cells} (depth, budget) cells (exploratory)."
        )
    lines.append("")

    lines.append("## Task fidelity and circuit cost (always reported alongside SNR, Section 3)")
    lines.append("")
    if not configuration_summaries.empty:
        for cid, g in configuration_summaries.groupby("configuration_id"):
            lines.append(
                f"- Configuration {cid}: mean final TFIM energy "
                f"{g['final_tfim_energy_mean'].mean():.4g}, mean global fidelity "
                f"{g['global_fidelity_mean'].mean():.4g}, RMS SNR_est {g['rms_SNR_est'].mean():.4g} "
                f"(N={int(g['n_matched_observations'].sum())} matched observations)."
            )
    lines.append("")
    lines.append(
        "This report and every table/figure it references were generated by "
        "`python -m qnn_snr report` from the tidy dataset and config recorded "
        f"in `run_manifest.json` (config_hash={_config_hash(cfg)})."
    )
    return "\n".join(lines)


def write_results_summary(results_dir: Path, confirmatory_table, interaction_indices,
                           configuration_summaries, exploratory_table, cfg) -> Path:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    text = generate_results_summary(confirmatory_table, interaction_indices, configuration_summaries,
                                     exploratory_table, cfg)
    out_path = results_dir / "results_summary.md"
    out_path.write_text(text, encoding="utf-8")
    return out_path
