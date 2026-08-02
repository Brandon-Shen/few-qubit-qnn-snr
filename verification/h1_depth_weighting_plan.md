# H1 depth heterogeneity and weighting plan

**Status:** prospectively frozen post-primary exploratory/robustness analysis. This revision supersedes the shorter placeholder plan committed at `7cdb9a2`. It is written after structural input validation but before fitting or inspecting any new depth-specific H1 result. The original and independent-seed datasets will be fit separately and never pooled at the row level. Nothing here enters or changes the H1--H4 Holm family.

## Inputs and validated construction

The authoritative inputs are `results/production_confirmatory/raw/exact.parquet` (original) and `results/h2_replication_v1/_pipeline_output_stage1/raw/exact.parquet` (independent seed). The response is `a = asinh(abs(exact_gradient))`, constructed by `build_h1_dataset`; centered factors are `E_c=E-.5`, `L_c=L-.5`, and `R_c=R-.5`. The scientific key is `(initialization_id, configuration_id, depth, parameter_id)`. Exact rows must have only `statevector_exact`, budget 0 only, one row per key, eight configurations, depths `{1,2,3,4,6}`, 50 initialization clusters, complete configuration coverage for every `(initialization,depth,parameter)`, finite gradients/responses, and parameter counts `{1:4,2:8,3:12,4:16,6:24}` per initialization. Nested identity is `(initialization_id,depth,parameter_id)`. The two initialization-seed sets and input checksums must be disjoint/different. Failure stops the analysis.

The pre-result structural audit is frozen in `verification/h1_depth_weighting_preanalysis_validation.{md,json}`. Checksums and the adopted H1 tables are recorded there. No depth-specific interaction was computed in that audit.

## Questions

1. Does the centered exact-gradient `E_c:L_c` interaction vary by depth?
2. Do both datasets retain the same point-estimate direction at each depth?
3. Does equal-depth averaging materially differ from unique-observation weighting?
4. Does the adopted pooled H1 coefficient emphasize depths containing more matched parameters?
5. Can the original-versus-seed pooled-estimate difference be localized descriptively to named depths?

## Categorical mixed model and contrasts

Fit by REML, separately in each dataset, using repository `fit_mixed_model`, optimizer order `lbfgs,bfgs,cg,powell,nm`, initialization random intercept, and variance-component intercept for `(initialization,depth,parameter)`. The fixed formula is:

```text
a ~ E_c*L_c*R_c + C(depth, Sum)
    + E_c:C(depth, Sum) + L_c:C(depth, Sum) + R_c:C(depth, Sum)
    + E_c:L_c:C(depth, Sum)
```

`C(depth, Sum)` and its factor interactions replace the collinear continuous `depth_z`, `E_c:depth_z`, `L_c:depth_z`, and `R_c:depth_z` terms while spanning their depth variation. `E_c*L_c*R_c` retains all centered factorial terms, including the unmoderated `E_c:L_c:R_c`; it must not be removed. The design matrix must have full column rank. Record formula, design names/rank/condition number, fit dimensions, optimizer attempts/adoption, convergence, singularity, variance components, residual variance, REML log likelihood, warnings, and Python/package versions. No post-result optimizer or formula change is allowed.

At each depth, derive the `E_c:L_c` difference-in-differences from Patsy's fitted `design_info`, averaging equally over `R_c=-.5,+.5`. Do not hard-code coefficient positions. Save the full five-by-fixed-effect contrast matrix and its five-by-five covariance `C V C'`. Report estimate, covariance-aware SE, normal-reference 95% Wald CI, two-sided raw p, contrast expression/vector, H1 rows, matched parameters per initialization, and initialization clusters. Apply a clearly labeled Holm adjustment across the five depth contrasts separately within each dataset; raw intervals remain unadjusted and this exploratory adjustment cannot alter the primary family.

## Weighting estimands

From the five-vector and its full covariance calculate:

- equal depth: weights `(0.2,0.2,0.2,0.2,0.2)`;
- observation count: `n_rows_d / sum(n_rows_d)`, expected `(0.0625,0.125,0.1875,0.25,0.375)`;
- matched-parameter count: `n_parameter_d / sum(n_parameter_d)`, expected to be identical to observation weighting because initialization/configuration counts are balanced. If verified identical, retain it machine-readably but avoid redundant prose/plot marks;
- adopted corrected pooled coefficient, read unchanged from each frozen H1 output and reported as a distinct model estimand.

Each categorical weighted estimate uses one combined contrast and `w' CVC' w` for its SE, interval, and descriptive raw p. We will test whether the adopted pooled coefficient is algebraically representable by a fixed design-only combination of categorical depth contrasts. Because a mixed model's generalized least-squares weighting can depend on fitted covariance components, no equality will be asserted unless verified numerically and algebraically.

## Cross-dataset comparisons

Never concatenate raw datasets. For each depth and each weighted summary calculate `seed-original`, with variance equal to the sum of the two separately fitted variances because seed roots and initialization seeds are verified independent. Apply the same rule to adopted pooled coefficients using their frozen SEs. Report normal-reference intervals and p-values descriptively. CI overlap is not a test and an interval containing zero is not equivalence.

For localization, define each depth's observation-weighted contribution as `w_d * (seed_d-original_d)`. A difference is **concentrated in a named depth** if one depth supplies at least 50% of the sum of absolute contributions, or **concentrated at shallow depths** if D=1 and D=2 together supply at least 60%; otherwise report **no clear localization**. Contributions will be reported regardless of classification.

## Moderation inference

The model-based joint Wald test targets the four nonredundant columns of `E_c:L_c:C(depth, Sum)`. Also fit OLS with the identical fixed formula and initialization-clustered covariance, using the established H2 framework, and test the identical four-column term. Report chi-square statistic, df=4, and p-value. Cluster-robust output is an exploratory covariance check, not a replacement for the mixed model. If OLS and mixed-model point contrasts are not numerically identical within `1e-8`, state that the robust fit is a fixed-effect-equivalent sensitivity with a different estimator and do not substitute its estimates.

## Frozen interpretation rules

Depth direction uses point estimates: **retained at all depths** = all five positive in both datasets; **retained at most depths** = three or four depthwise signs agree and are positive in both; **mixed depth pattern** = only one or two agree positively; **not retained** = none. Interval uncertainty is always reported separately.

Weighting uses the original corrected H1 SE `0.0010812660` as a frozen materiality unit. **Materially insensitive** means the maximum estimate range across equal/observation/parameter summaries is at most one such SE within each dataset; **same direction but magnitude weighting-sensitive** means all signs agree but either range exceeds one SE; **direction changes under weighting** is literal; **too imprecise** applies if every weighting interval in either dataset spans zero.

Cross-dataset magnitude is **broadly similar** if the absolute seed-minus-original difference is at most one original-H1 SE; otherwise **direction retained but magnitude differs**, supplemented by the frozen localization rule. The final report will assess whether the existing phrase “direction retained but magnitude uncertain” remains appropriate; it may add localization precision only if these frozen rules support it.

## Verification and outputs

Tests will cover unique construction/no budget duplication, centered coding, design rank, design-derived contrasts, covariance quadratic forms, weights, dataset independence, known synthetic depth interactions, equivalent cell difference-in-differences, figure-source consistency, deterministic regeneration, and manifest integrity. The full relevant suite will run with `MPLBACKEND=Agg`; the known unrelated `main.tex`/fig0 reference failure will be reported.

Outputs are:

- `verification/h1_depth_weighting_results.{md,json}` (the only place containing exact recommended future manuscript wording; the manuscript itself is not edited);
- `results/h1_depth_weighting/original/` and `independent_seed/`: validation, model metadata/coefficients, contrast matrix/covariance, depth contrasts, weights, weighted summaries, warnings;
- `results/h1_depth_weighting/comparison/`: depth/weighted/pool differences, figure source CSVs, PDF figures and PNG previews, figure metadata, checksums, commands, and provenance.

Stop for any eligibility/provenance failure, rank deficiency, nonconvergent or structurally changed mixed model, ambiguous contrast, irreproducible weight, dataset mixing, protected fig0 modification, or required post-result plan change.
