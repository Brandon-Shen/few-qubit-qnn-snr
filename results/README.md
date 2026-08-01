# `results/` — production data, organized by provenance

This directory holds every data artifact the paper's Data/Code availability
statements point to. It is split into five directories so a reviewer can
immediately tell which numbers are the adopted confirmatory record, which
are a superseded intermediate, and which are non-reportable pipeline
exercises. **If you only trust one directory, trust `production_confirmatory/`
plus `production_corrected_end_to_end/` for the bootstrap arm — everything
else is either historical, a robustness check, or explicitly not real.**

| Directory | What it is | Status |
|---|---|---|
| `production_confirmatory/` | The adopted end-to-end-mode raw data, aggregated statistics, H1–H4 coefficient/hypothesis tables, and all 11 report figures, produced by `configs/confirmatory.yaml` (config_hash `bb1fe393a979c8d2`, frozen copy at `production_confirmatory/config_used.confirmatory.yaml`). | **Current, cite this.** |
| `production_corrected_end_to_end/` | The end-to-end-only nested bootstrap for H2–H4, extended to n=443 completed iterations after the mode-pooling fix (see `verification/bootstrap_end_to_end_extended.md`). Kept separate from `production_confirmatory/` because it was regenerated in a later pass than the Wald/Holm fit. | **Current, cite this.** |
| `superseded_pooled/` | The pre-fix confirmatory coefficient/hypothesis tables, when `finite_shot_conditional` and `finite_shot_end_to_end` rows were inadvertently pooled into one model (see `verification/mode_pooling_guard.md` and `verification/confirmatory_numbers_adopted.md`). Kept for reference, **never** the current record. | Superseded — do not cite as current. |
| `sensitivity_analyses/` | Post-run, data-dependent robustness checks that do not replace the confirmatory family: D=1-exclusion refit, leave-one-initialization-out, zero-variance exclusion audit, optimizer comparison. | Robustness checks, not confirmatory. |
| `smoke_test/` | Non-statistically-meaningful pipeline exercises (`configs/smoke.yaml` output, a bootstrap timing probe). Explicitly excluded from any reported result. | **Not real data — do not cite.** |

`results/_checkpoints/` (gitignored) is the live pipeline's in-progress
bootstrap-resume scratch space, not an archive — it is empty in a clean
checkout.

Every one of the four data directories above (excluding `smoke_test/`)
contains a `SHA256SUMS.txt` covering its own files; verify with
`sha256sum -c SHA256SUMS.txt` from inside that directory (or `shasum -c` on
macOS). The manuscript commit these hashes correspond to is recorded in
`/MANUSCRIPT_COMMIT.txt` at the repository root.

## Reproducing every main figure and table

Run from the repository root, after `pip install -e ".[dev]"` (see the top-level
README for the exact pinned environment). None of these regenerate raw
simulation data — they recompute figures/tables from the frozen files above,
which is what "reproduce Figure N" means for a paper whose raw generation is a
multi-hour run (see "Reproducing the full pipeline" below for that separately).

| Figure/Table | Command | Reads |
|---|---|---|
| Fig. 0 (`fig:el-primary`) | `python paper/scripts/make_fig0_el_primary.py` | `production_confirmatory/pointwise_gradient_statistics.parquet`, `production_confirmatory/raw/exact.parquet` |
| Fig. 1 (`fig:confirmatory-forest`) | `python paper/scripts/make_fig1_forest.py` | `production_confirmatory/confirmatory_hypotheses.csv`, `verification/_bootstrap_checkpoints/h1_boot.parquet`, `production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_iterations.parquet` |
| Fig. 2 (`fig:h4-fragility`) | `python paper/scripts/make_fig2_h4_fragility.py` | `production_confirmatory/snr_model_coefficients.csv`, `verification/_fig2_dge3_endtoend_coefficients.csv`, `verification/_fig2_conditional_fullsweep_coefficients.csv` |
| Fig. 3 (`fig:entanglement-diagnostic`) | `python paper/scripts/make_fig3_entanglement.py` | `verification/_fig3_entanglement_marginal.csv` (from `verification/entanglement_per_init_check.py`) |
| Fig. 4 (`fig:mode-split-bias`) | `python paper/scripts/make_fig4_mode_split_bias.py` | `verification/_fig4_mode_split_by_config.csv` (derived from `production_confirmatory/pointwise_gradient_statistics.parquet`) |
| Fig. 5 (`fig:q1-comparison`) | `python paper/scripts/make_fig5_q1_comparison.py` | `production_confirmatory/exploratory_results.csv`, `verification/_q1_endtoend_recompute.csv` |
| Fig. 6 (`fig:d1-sensitivity`) | `python paper/scripts/make_fig6_d1_exclusion_sensitivity.py` | `sensitivity_analyses/d1_exclusion_sensitivity_coefficients.csv` |
| Fig. 7 (`fig:zero-variance-heatmap`) | `python paper/scripts/make_fig7_zero_variance_heatmap.py` | `sensitivity_analyses/zero_variance_exclusions_d1_config_budget.csv` |
| Fig. 8 (`fig:residual-diagnostics`) | `python verification/run_model_diagnostics.py` | `production_confirmatory/pointwise_gradient_statistics.parquet` (also writes `sensitivity_analyses/model_optimizer_comparison.csv`) |
| Fig. 9 (`fig:initialization-influence`) | `python paper/scripts/make_fig9_initialization_influence.py` | `sensitivity_analyses/leave_one_initialization_out_coefficients.csv` |
| Fig. 10 (`fig:bootstrap-stability`) | `python paper/scripts/make_fig10_bootstrap_endpoint_stability.py` | `production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_checkpoints.csv` |
| Table `tab:configurations` | (definitional — the 2×2×2 factorial design; not computed from a data file) | — |
| Table `tab:confirmatory-summary` | Values are read directly from: | `production_confirmatory/confirmatory_hypotheses.csv`, `production_confirmatory/holm_adjustment.csv`, `production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_summary.csv` |
| Table `tab:repro-index` | (self-referential — this table's own content is the reproduction index; see it in `paper/main.tex` or the row-by-row mapping there) | — |

All 11 figure/diagnostic-generation commands above were re-run against this
directory layout on 2026-08-01 and confirmed to (a) exit 0, (b) reproduce the
adopted coefficients bit-for-bit (`beta_EL=0.024996`, `beta_ER=-0.000958`,
`beta_LRd=-0.010179`, bootstrap n=443 CIs matching `verification/bootstrap_end_to_end_extended.md`
exactly), and (c) pass the full `pytest tests/ -q` suite (156/156).

Sensitivity-analysis and audit scripts that *produce* the CSVs consumed above
(rather than just plotting them) are documented individually in the
reproducibility index (`Table tab:repro-index` in `paper/main.tex`) and in
`verification/*.md`.

## Reproducing the full pipeline from raw simulation

This is a separate, much larger undertaking (8 configurations × 50
initializations × 30 replicates × 5 depths × 4 budgets × 3 gradient modes,
plus a 2000-iteration nested bootstrap) and was intentionally **not**
re-executed as part of assembling this archive. See the top-level README's
"Reproducing the full pipeline" section for the exact commands, environment,
and expected wall-clock/resource profile if you want to regenerate the raw
data from scratch rather than from these frozen files.
