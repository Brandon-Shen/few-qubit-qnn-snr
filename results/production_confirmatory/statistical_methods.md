# Statistical methods

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
