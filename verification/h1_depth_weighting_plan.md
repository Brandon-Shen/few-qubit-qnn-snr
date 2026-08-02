# H1 depth and weighting plan

**Status:** post-primary exploratory analysis, frozen before depth-specific centered H1 results. Original and independent-seed datasets are never pooled.

## Inputs and eligibility

Use the validated unique exact tables from `results/production_confirmatory/raw/exact.parquet` and `results/h2_replication_v1/_pipeline_output_stage1/raw/exact.parquet`, with the same inclusion, uniqueness, centered coding, response, depth scaling, matched identities, and random effects as corrected H1.

## Models and contrasts

For each dataset separately fit one categorical REML mixed model retaining all corrected H1 terms while replacing the linear `E_c:L_c` pooling with an identifiable `E_c:L_c:C(depth, Sum)` moderation structure. Preserve centered `E_c*L_c*R_c`, appropriate factor-by-depth nuisance terms, initialization intercept, nested matched-parameter intercept, and optimizer fallback. Derive `E_c:L_c` at `D=1,2,3,4,6`, marginalized equally over R, with linear contrasts against the full fixed-effect covariance. Run a joint Wald moderation test; if the repository cluster-robust OLS framework accepts this same fixed design, also report initialization-clustered joint and depth-specific intervals as exploratory variance-robust checks.

Calculate covariance-aware: (1) equal-depth average with weights `1/5`; (2) observation-count-weighted average with weights proportional to eligible exact-gradient rows at depth (equivalently matched parameter observations, explicitly tabulated); and (3) the adopted corrected primary mixed-model `E_c:L_c`, reported as a distinct model-implied pooled estimand rather than a weighted categorical contrast.

Every output states averaging over depth, matched parameter identities, initialization clusters, R, and configurations. No bootstrap is planned for these exploratory contrasts; model-based and supported cluster-robust intervals are reported without multiplicity adjustment.

Outputs: `results/h1_depth_weighting/effect_coded/` CSV/JSON for models, depth contrasts, joint tests, weighting summaries, comparison/source data; two figures; methods note; and manuscript-update note. Determinism follows fixed row ordering and no stochastic resampling. Stop if categorical design is rank deficient, model spaces/contrasts are ambiguous, random-effects structure cannot be retained, or robust covariance cannot be applied without changing the estimand (in which case omit and explain it).
