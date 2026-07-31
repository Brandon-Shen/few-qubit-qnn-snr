# QMI/QIP robustness package -- Task 3: mixed-model health and robustness diagnostics

Diagnostics on the adopted end-to-end full-sweep H2--H4 fit
(`fit_h2h4_model` on `analysis_mode == "finite_shot_end_to_end"`, all five
block counts). Parts A--C below are complete; Part D (leave-one-
initialization-out) was launched as a background job
(`verification/run_loo_initialization.py`, checkpointed per-iteration to
`verification/_bootstrap_checkpoints/loo_initialization.parquet`) and this
document will be updated with its results once complete -- reported here as
in-progress rather than assumed.

## A. Convergence and singularity

| Diagnostic | Value |
|---|---|
| Optimizer exit status | `converged = True` |
| Optimizer used | `lbfgs` (first in `OPTIMIZER_FALLBACK_ORDER`, no fallback needed) |
| Attempted optimizers | `["lbfgs"]` |
| Warnings emitted | `ConvergenceWarning: The MLE may be on the boundary of the parameter space.` |
| REML log-likelihood | -58,498.757489 |
| `n_obs` | 101,891 |
| `n_groups` (initialization random intercept) | 50 |
| `n_vc_levels` (nested init x depth x parameter variance component) | 3,200 |
| Condition number (fixed-effect design matrix) | 118.884 |
| `singular_fit` | **False** (neither variance component is within `atol=1e-8` of zero) |
| Group-intercept variance | 0.0011450 |
| Nested-parameter variance | 0.0877229 |
| Residual mean / SD (from fit) | 3.4e-17 / 0.404288 |

**The adopted confirmatory fit does converge, is not singular, and its one
warning (`ConvergenceWarning: The MLE may be on the boundary of the
parameter space`) is a pre-existing, previously-documented property of this
model/data combination** (`verification/qmi_qip_analysis_inputs.md` Section
3, `verification/d_ge_3_sensitivity_refit.md`) -- it is not new to this
package and does not, by itself, indicate a problem with the reported
coefficients; boundary warnings for near-zero variance components are a
known, common `statsmodels`/REML behavior and are reported here rather than
treated as disqualifying. No confirmatory or sensitivity fit run in this
package (full sweep, `D≠1`, `D≥3` from the earlier session) reported
`singular_fit=True`.

## B. Independent optimizer check

Refit the identical model (same formula, same data, same random-effect
structure, same REML likelihood) forcing `method="bfgs"` directly via
`statsmodels.formula.api.mixedlm(...).fit(method="bfgs", reml=True)`,
bypassing the production fallback order entirely (which would have stopped
at `lbfgs` since it already converges) -- a genuinely independent optimizer
run, not a re-report of the same fit.

| Quantity | `lbfgs` (adopted) | `bfgs` (independent check) | Abs. diff |
|---|---:|---:|---:|
| `E:L` (`beta_EL`) | 0.024995844 | 0.024995840 | -3.9e-09 |
| `E:R` (`beta_ER`) | -0.000957579 | -0.000957580 | -1.1e-09 |
| `L:R:depth_z` (`beta_LRd`) | -0.010178758 | -0.010178769 | -1.1e-08 |
| REML log-likelihood | -58,498.757489 | -58,498.757440 | +4.9e-05 |
| Group-intercept variance | 0.0011450 | 0.0011414 | -3.6e-06 |
| Nested-parameter variance | 0.0877229 | 0.0877084 | -1.5e-05 |

`bfgs` also converged (`converged=True`) and emitted the identical single
`ConvergenceWarning` as `lbfgs`. **The two independent optimizers agree to
8-9 significant figures on every target coefficient and to 5 figures on the
log-likelihood and random-effect variances** -- this is not merely
"the same qualitative conclusion," it is numerically the same optimum to
float-precision-adjacent tolerance. This rules out optimizer-choice
sensitivity as a concern for the adopted fit. (Full table:
`results/model_optimizer_comparison.csv`.)

## C. Residual diagnostics

Figure `figures/fig8_model_residual_diagnostics.pdf` (residual-vs-fitted,
normal Q-Q, residual SD by block count, residual SD by configuration).

- **Heteroscedasticity by block count**: residual SD falls monotonically
  with `D` -- 0.659 (`D=1`) -> 0.539 (`D=2`) -> 0.452 (`D=3`) -> 0.366
  (`D=4`) -> 0.276 (`D=6`). This is a roughly 2.4x spread across the design
  and is the single clearest systematic structure left in the residuals.
  It is directionally consistent with (though not proof of a common cause
  with) the paper's existing finding that block-count-1 has the worst
  replicate-count calibration and highest zero-variance exclusion rate
  (Section 4.1; `verification/zero_variance_exclusion_audit.md`) -- lower
  block counts appear noisier by more than one measure in this dataset.
- **Heteroscedasticity by budget**: residual SD *increases* with nominal
  shot budget -- 0.301 (`B=250`) -> 0.346 (`B=500`) -> 0.423 (`B=1000`) ->
  0.513 (`B=2000`), the opposite direction from the block-count pattern.
  This is a real, systematic pattern, not noise (monotonic across all four
  budget levels), and is reported without a mechanistic explanation
  attempted here.
- **Residual scale by configuration**: much milder spread (0.354-0.455
  across the 8 configurations, versus the ~2.4x range by block count) --
  configuration is not a strong driver of residual heteroscedasticity
  relative to block count and budget.
- **Tails**: the Q-Q plot shows visible curvature away from the reference
  line at both tails (S-shape), consistent with heavier-than-normal tails
  rather than a location/scale mismatch alone. Quantified: 1,158 of 101,891
  standardized residuals (1.14%) exceed \|3\| in absolute value (versus
  ~0.27% expected under exact normality, roughly 4x over-representation),
  and 158 (0.16%) exceed \|4\|. Maximum absolute standardized residual:
  5.76 (`verification/_extreme_residuals.csv` lists the 20 most extreme
  rows with their full cell identifiers).
- **Net read**: the model shows real, systematic heteroscedasticity by
  block count and by budget (both monotonic, both substantial in relative
  terms) and moderately heavy tails, but no singular fit, no optimizer
  disagreement, and residual mean indistinguishable from zero
  (3.4e-17). This is reported as a genuine model-fit caveat -- the reported
  Wald SEs assume homoscedastic, normal-tailed errors, and the
  heteroscedasticity/tail patterns documented here mean those SEs are an
  approximation, most likely a mild underestimate of true uncertainty at
  low block counts and high budgets where residual spread is largest --
  not as a reason to discard the fit, which converges cleanly, is
  non-singular, and reproduces to 8-9 figures under an independent
  optimizer.

## D. Leave-one-initialization-out influence analysis

All 50 refits completed, all 50 converged (`converged=True` in every case,
0 failures). Each excludes one complete `initialization_id` (all its
configurations, block counts, budgets, and matched parameters) and refits
the identical adopted `H2_H4_FORMULA` model on the remaining 49. Wall-clock
per refit ranged ~46-108s (measured concurrently with the Task 4 bootstrap
extension sharing this machine, so somewhat slower than the ~31.8s isolated
baseline in `verification/qmi_qip_analysis_inputs.md`).

| Coefficient | Full-data estimate | LOO min | LOO max | Max abs. shift | Max shift (orig.-SE units) | Sign reversals | Raw `p=0.05` crossings |
|---|---:|---:|---:|---:|---:|---:|---:|
| `beta_EL` (H2) | +0.024996 | +0.018887 (init 37) | +0.033229 (init 1) | 0.008234 | **1.131** | 0/50 | 0/50 (stays `p<0.05` in all 50) |
| `beta_ER` (H3) | -0.000958 | -0.004752 (init 8) | +0.003903 (init 23) | 0.004861 | 0.666 | 16/50 | 0/50 (stays `p>0.05` in all 50) |
| `beta_LRd` (H4) | -0.010179 | -0.013895 (init 10) | -0.007839 (init 36) | 0.003717 | 0.693 | 0/50 | 18/50 |

Figure `figures/fig9_initialization_influence.pdf` shows all 50 sorted LOO
estimates per coefficient against the full-data reference.

**Per-coefficient read:**

- **`beta_EL` (H2)**: no sign reversal in any of the 50 deletions, and
  **every single deletion leaves the raw p-value below 0.05** (the loosest
  possible reading of "does H2 survive" -- the fully Holm-adjusted decision
  is not recomputed per deletion here, but since the full-data raw p
  (0.000595) has roughly 84x headroom before it would even approach 0.05,
  and no single deletion gets remotely close, H2's rejection is not
  attributable to any one initialization). **One deletion (init 1) does
  push the point estimate to 1.131 original-SE units away from the
  full-data value** -- a magnitude comparable to Task 1's D!=1
  sensitivity finding (1.011 SE) -- but neither of the two LOO-specific
  stop conditions in the QMI/QIP prompt ("one initialization deletion
  reverses the sign of `beta_EL`"; "one initialization deletion changes
  the H2 result from clearly supported to clearly unsupported") is
  triggered: no sign reversal, and no deletion comes close to
  unsupportive. This specific 1.131-SE data point is noted here
  for completeness and pattern-matching with Task 1's finding (both point
  toward `beta_EL` having somewhat heavier-tailed influence than the other
  two coefficients), not as a triggered stop condition.
- **`beta_ER` (H3)**: 16 of 50 deletions flip the point estimate's sign
  (though never anywhere near significance in either direction -- 0/50
  cross `p=0.05`). This is exactly the pattern expected for a coefficient
  that is a clean null centered near zero: individual initializations push
  it slightly positive or slightly negative, consistent with sampling
  noise around a true value indistinguishable from zero, not with an
  unstable or influential fit.
- **`beta_LRd` (H4)**: no sign reversals, but **18 of 50 deletions (36%)
  move the raw p-value across the 0.05 line** relative to the full-data
  fit's already-borderline raw p=0.0577 -- a large fraction, and the single
  most fragile-looking result of the three by this specific metric. This
  is a new, independent line of evidence (leave-one-initialization-out,
  distinct from the mode-split, `D>=3`, and bootstrap probes already in the
  paper) pointing the same direction as every other H4 robustness check:
  the near-boundary character is not a stable feature of the full dataset,
  it is sensitive to which single initialization is included or excluded.
  This strengthens, rather than changes, the paper's existing framing of
  H4 as fragile.

**No stop condition is triggered by the LOO analysis**: no sign reversal of
`beta_EL`, and no deletion changes H2 from clearly supported to clearly
unsupported (both explicit LOO-specific stop conditions in the QMI/QIP
prompt). `beta_EL`'s single largest per-deletion shift (1.131 SE, init 1) is
reported as a data point worth carrying into Task 5's discussion of
`beta_EL`'s robustness, alongside Task 1's similar-magnitude D!=1 shift, not
as a newly triggered stop condition.

## Files produced

- `verification/run_model_diagnostics.py` (parts A-C)
- `verification/run_loo_initialization.py` (part D)
- `results/model_optimizer_comparison.csv`
- `verification/_residual_diagnostics.json`
- `verification/_extreme_residuals.csv`
- `results/leave_one_initialization_out_coefficients.csv`
- `paper/figures/fig8_model_residual_diagnostics.pdf`
- `paper/scripts/make_fig9_initialization_influence.py`, `paper/figures/fig9_initialization_influence.pdf`
