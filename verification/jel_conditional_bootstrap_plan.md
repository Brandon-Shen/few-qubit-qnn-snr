# Conditional J_EL definition and bootstrap plan

**Status:** post-primary descriptive analysis, frozen before calculating any new conditional J value.

## Definition and inputs

Inputs are the two validated unique exact tables used by H1. For configuration `c`, define `G_c = sqrt(mean(g^2))` over all finite exact-gradient rows in that configuration, pooling rows before RMS. Thus every parameter-row receives equal weight; deeper depths receive more aggregate weight because they contain more matched parameters; initializations enter through their parameter rows; no prior initialization or depth aggregation occurs. Report this historical weighting transparently and do not introduce an R-marginal index.

Configuration mapping from `CONFIGURATION_TABLE`:

- `J_EL_given_R0 = G_5 G_1/(G_2 G_3)` using `(EL, baseline, E, L)` at R=0.
- `J_EL_given_R1 = G_8 G_4/(G_6 G_7)` using `(ELR, R, ER, LR)` at R=1.

Acceptance requires reproducing historical `J_EL_given_R0=1.2417603765323095` on the frozen original table within `1e-12` via both the authoritative function and an independent implementation. Denominator zero/nonfinite yields undefined with a reason; no epsilon.

## Bootstrap and reporting

For original and independent-seed datasets separately, resample complete initialization clusters with replacement, uniquely relabel sampled copies, retain all configurations/depths/parameters, and recompute both indices. No model fit or within-cell resampling. Seeds: original `255001`, independent seed `255002`, keyed by iteration. Target 2,000 completed iterations each; checkpoint every 100 attempts and summarize 100, 250, 400, 1,000, 2,000. Frozen interval: percentile 95%. Record attempted/completed/undefined/failed and reasons.

Report ratio and `100*(J-1)%`; do not call either index a centered-H1 equivalent, training benefit, or shot saving. Outputs: `results/jel_conditional/` draw Parquets, summaries CSV/JSON, checkpoints, failures, definition metadata, tests for J=1/no interaction and direction examples, and original-versus-independent comparison. Stop if the historical value cannot be traced/reproduced, row uniqueness fails, or competing weighting implementations disagree.
