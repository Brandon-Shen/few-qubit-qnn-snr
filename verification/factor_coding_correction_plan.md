# Factor-coding correction plan

**Status:** frozen after adjudication commit `79b6b87bbde5228e1450fafcd6a8df132b56cf4d` and before calculating or inspecting any corrected scientific result.

## Purpose and status

Correct the implementation mismatch between historical direct `{0,1}` predictors and the adjudicated centered primary estimands. This is a correction of the protocol-derived H1--H4 family, not a new hypothesis family or a robustness analysis. Results will be reported regardless of direction, significance, or agreement with historical claims.

## Frozen inputs and eligibility

- H1: `results/production_confirmatory/raw/exact.parquet`, SHA-256 recorded in `verification/input_checksums.sha256`. Require `analysis_mode == "statevector_exact"`, one row per `(initialization_id, configuration_id, depth, parameter_id)`, all finite exact gradients, all eight configurations, depths `{1,2,3,4,6}`, and 50 initialization clusters. No budget replication or finite-shot resampling is permitted.
- H2--H4: `results/production_confirmatory/pointwise_gradient_statistics.parquet`, restricted to `analysis_mode == "finite_shot_end_to_end"`, then the existing `build_h2h4_dataset()` finite-SNR eligibility rule. No eligibility change is permitted.
- Historical H1 draws: `verification/_bootstrap_checkpoints/h1_boot.parquet` and metadata.
- Historical corrected-end-to-end H2--H4 draws: `results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_iterations.parquet`, summary, checkpoints, and seed manifest.

Any checksum mismatch, duplicate H1 key, mixed finite-shot mode, missing target coefficient, or changed eligibility stops the correction.

## Coding and models

Historical columns remain untouched. Explicit corrected columns are added:

`E_c = E - 0.5`, `L_c = L - 0.5`, `R_c = R - 0.5`.

Historical direct model formulas:

- H1: `a ~ E*L*R + depth_z + E:depth_z + L:depth_z + R:depth_z`.
- H2--H4: `y ~ E*L*R + depth_z + log2_budget + E:depth_z + L:depth_z + R:depth_z + L:R:depth_z`.

Corrected centered formulas replace only `E,L,R` by `E_c,L_c,R_c`. Response transformations, depth scaling, log-budget scaling, row eligibility, REML, optimizer fallback order `lbfgs,bfgs,cg,powell,nm`, initialization random intercept, and `(initialization,depth,parameter)` variance-component intercept remain identical.

Historical direct interpretations:

- `E:L`: E-by-L interaction at `R=0`.
- `E:R`: E-by-R interaction at `L=0`.
- `L:R`: L-by-R interaction at `E=0`.
- `L:R:depth_z`: change with standardized depth in the L-by-R interaction; its invariance is tested, not assumed.

Corrected centered interpretations:

- `E_c:L_c`: E-by-L interaction averaged equally across R.
- `E_c:R_c`: E-by-R interaction averaged equally across L.
- `L_c:R_c`: L-by-R interaction averaged equally across E.
- `L_c:R_c:depth_z`: standardized-depth moderation of the E-averaged L-by-R interaction.

## Algebraic transformation

Let `b_01` be the full direct fixed-effect coefficient vector and `b_c = T b_01` its centered representation. Construct `T` from the actual Patsy design matrices, not from coefficient-name assumptions alone, by solving and verifying `X_01 = X_c T` (equivalently the coefficient map consistent with `X_01 b_01 = X_c b_c`). Require full rank and maximum column-space projection error at most `1e-10`.

Required identities to verify from the actual design matrices include:

- `EL_c = EL_01 + 0.5 ELR_01`.
- `ER_c = ER_01 + 0.5 ELR_01`.
- `LR_c = LR_01 + 0.5 ELR_01`.
- `EL at R=0 = EL_01`.
- `EL at R=1 = EL_01 + ELR_01`.
- `EL averaged across R = EL_01 + 0.5 ELR_01`.
- `ER at L=0 = ER_01`.
- `ER at L=1 = ER_01 + ELR_01`.
- `ER averaged across L = ER_01 + 0.5 ELR_01`.

For H2--H4, verify rather than assume the complete map involving `L:R:depth_z`, including whether `L_c:R_c:depth_z = L:R:depth_z`. All transformed standard errors and covariances use `V_c = T V_01 T'`; for example `Var(EL_c) = Var(EL_01) + 0.25 Var(ELR_01) + Cov(EL_01,ELR_01)`.

## Reparameterization audit

Fit historical and centered models with the frozen implementation. Compare the design column spaces and then, at strict tolerances appropriate to optimizer noise:

- transformed coefficients and centered-refit coefficients: absolute tolerance `1e-7`;
- transformed fixed-effect covariance and centered-refit covariance: absolute/relative tolerance `1e-6`;
- fitted and predicted values and residuals: maximum absolute difference `1e-7`;
- log-likelihood and REML-reported objective: absolute difference `1e-6`;
- group variance, nested-parameter variance, and residual scale: relative tolerance `1e-6` and absolute tolerance `1e-9`.

The fixed-effect recoding should preserve the model space, fitted values, residuals, likelihood/REML criterion (the coding transformation is nonsingular and unit-determinant), random effects, and residual variance. If column spaces differ, or discrepancies persist after fitting both parameterizations with a common converged optimizer, stop with a new blocking report. Optimizer disagreement is logged and never resolved by selecting a favorable fit.

Automated tests will cover coding values, design-space equivalence, all simple-effect identities, coefficient/covariance transformation, fitted-value equivalence, H4 behavior, and regression against the archived historical coefficients.

## Corrected H1--H4 family

From the centered fits, extract H1 `E_c:L_c`, H2 `E_c:L_c`, H3 `E_c:R_c`, and H4 `L_c:R_c:depth_z`. Compute model-based 95% Wald intervals and two-sided normal-reference Wald p-values using the transformed/full fitted covariance. Recompute Holm--Bonferroni across exactly these four corrected raw p-values. Record every decision change without qualification based on favorability.

Corrected outputs go under `results/primary_corrected/effect_coded/`. Historical artifacts are copied, not moved or overwritten, into `results/superseded/direct_01_factor_coding/` with provenance and interpretation metadata; existing source locations remain untouched.

## Bootstrap correction

First validate draw schemas and iteration provenance.

- H1 historical draws are usable for a corrected 400-draw audit only if every completed draw contains both `E:L` and `E:L:R`. Transform draw by draw as `E_c:L_c = E:L + 0.5(E:L:R)`. Validate at least 10 deterministically selected draws against explicit centered refits from the identical resampled clusters. Preserve all historical direct draws.
- The corrected primary H1 bootstrap will then extend the same deterministic initialization-cluster resampling stream to at least 2,000 completed fits, preferring 5,000 only if computationally practical. Existing valid draws and their iteration seeds are preserved. Repeated sampled clusters remain uniquely relabeled. Checkpoints are saved near 100, 250, 400, 1,000, 2,000, and 5,000 completed fits, with attempted/completed/failed counts and endpoint histories.
- H2--H4 historical 443 draws are transformable only if each included draw has every coefficient required by its centered linear combination and the combined file/seed manifest proves unique valid iterations. Transform H2/H3 draw by draw; derive H4 from the verified full design-matrix map. Validate a deterministic subset against explicit centered refits using the archived seed/resampling implementation. If reconstruction is impossible, rerun the exact planned bootstrap streams; do not substitute direct intervals.

Percentile 95% intervals are frozen. No interval-method switching is allowed after values are viewed. Bootstrap counts are called “bootstrap iterations” or “completed bootstrap fits,” never experimental `n`.

## J indices

The historical `J_EL` is renamed `J_EL_given_R0` and retains the authoritative formula and mapping: baseline configuration 1 `(0,0,0)`, E-only 2 `(1,0,0)`, L-only 3 `(0,1,0)`, and EL 5 `(1,1,0)`; `J_EL_given_R0 = G_5 G_1/(G_2 G_3)`.

No new J value is calculated under this correction plan. A separate committed J plan must precede calculation of `J_EL_given_R1 = G_8 G_4/(G_6 G_7)`, bootstraps, independent-seed values, or any alternative weighting. No overall R-marginal index will be invented without a prospective definition.

## Outputs and manuscript impact

Planned outputs include design-matrix diagnostics, coefficient/covariance transforms, centered model summaries, corrected H1--H4 table, corrected Holm table, historical-versus-corrected comparison, bootstrap transformed draws/checkpoints/intervals, warnings/failures, archival manifests, and `verification/factor_coding_correction_results.{md,json}`. Every output metadata file records adjudication, plan, input, and analysis commits.

Affected manuscript locations include the abstract Results, Methods coding/model paragraphs, H1--H4 Results, confirmatory summary table, forest/interaction figures and source data, Discussion, Conclusion, supplement model/diagnostic/bootstrap text and tables, and all claims using `J_EL` as though it were R-marginal. The title, abstract, and headline conclusions are not edited in this phase; the correction report will state whether material revision is required.

## Stop rules

Stop rather than guess if protocol evidence later contradicts the adjudication; inputs fail provenance/structure checks; model spaces differ; required covariance or draw coefficients are unavailable; bootstrap streams cannot be reconstructed uniquely; a corrected fit requires changed eligibility, random effects, likelihood choice, depth scaling, or optimizer policy; or correction would redefine rather than reparameterize the four-hypothesis family.
