# D≥3 sensitivity refit for H3/H4

**Status: sensitivity check only. Does not supersede, replace, or redefine the
full-sweep confirmatory H3/H4 result.** The full block-count sweep
(`D ∈ {1,2,3,4,6}`) remains the confirmatory analysis and is usable in
Results as-is. This document reports the promised `D≥3` post-run sensitivity
fit and compares it against that result — it does not choose a winner.

---

## Addendum (2026-07-29): end-to-end-only rerun — supersedes the body below

**Everything in the original "Method"/"Results"/"Direct comparison" sections
below this addendum pooled `finite_shot_conditional` and
`finite_shot_end_to_end` rows, because it ran before the mode-pooling bug was
fixed (`verification/mode_pooling_guard.md`) and before end-to-end-only was
formally adopted as the confirmatory mode
(`verification/confirmatory_numbers_adopted.md`). That pooled version of
this sensitivity check is now superseded by this addendum.** It is kept
below (not deleted) for the same reason the pooled confirmatory numbers were
kept: the mode-sensitivity finding is itself informative.

### Method (unchanged except for the mode filter)

Same source (`results/production_confirmatory/pointwise_gradient_statistics.parquet`), same
`H2_H4_FORMULA` via `fit_h2h4_model()`, same non-recentered `depth_z`
convention as the original version below — the only change is an added
`analysis_mode == "finite_shot_end_to_end"` filter alongside
`depth.isin([3, 4, 6])`. Subset: 83,200 rows, 82,940 with finite `SNR_est`
entering the model (260 dropped).

### Results

| Coefficient | Model | Estimate | SE | z | p (Wald, 2-sided) | 95% CI |
|---|---|---:|---:|---:|---:|---|
| `beta_ER` (`E:R`) | End-to-end-only full sweep (adopted confirmatory, D∈{1,2,3,4,6}) | -0.000958 | 0.007293 | -0.131 | 0.896 | [-0.01525, 0.01334] |
| `beta_ER` (`E:R`) | **End-to-end-only D≥3 sensitivity (D∈{3,4,6})** | **-0.002128** | **0.007004** | **-0.304** | **0.761** | **[-0.01586, 0.01160]** |
| `beta_LRd` (`L:R:depth_z`) | End-to-end-only full sweep (adopted confirmatory, D∈{1,2,3,4,6}) | -0.010179 | 0.005362 | -1.898 | 0.058 | [-0.02069, 0.00033] |
| `beta_LRd` (`L:R:depth_z`) | **End-to-end-only D≥3 sensitivity (D∈{3,4,6})** | **-0.005160** | **0.006731** | **-0.767** | **0.443** | **[-0.01835, 0.00803]** |

Fit converged (`lbfgs`, REML, `singular_fit=False`) but, unlike every other
fit in this document and in `d_ge_3_sensitivity_refit.md`'s pooled version,
**also emitted `ConvergenceWarning: The Hessian matrix at the estimated
parameter values is not positive definite`** in addition to the usual
boundary warning. This is a new caveat specific to the end-to-end-only D≥3
subset (n=82,940 — the smallest fit in this comparison) and should be read
as a mild reliability caveat on the SEs reported for this fit specifically,
though it did not prevent convergence and `singular_fit` is still `False`.

### Direct comparison

- **Sign**: unchanged between subset and full sweep for both coefficients —
  `beta_ER` negative in both, `beta_LRd` negative in both.
- **CI overlap**: extensive for both coefficients (`beta_ER`: [-0.0159,
  0.0116] vs [-0.0153, 0.0133]; `beta_LRd`: [-0.0184, 0.0080] vs [-0.0207,
  0.0003]).
- **Magnitude and the one thing worth flagging**: `beta_ER` is essentially
  unchanged (-0.0021 vs -0.0010, both deeply non-significant). `beta_LRd`
  **shrinks toward zero and loses its near-boundary character**: the
  adopted full-sweep end-to-end-only estimate sits at p=0.058 (just above
  the α=0.05 line), while the D≥3 subset estimate is less than half the
  magnitude (-0.0052 vs -0.0102) and comfortably non-significant (p=0.443).
  This is **not** a sign reversal or a materially contradictory result — the
  D≥3 CI is fully consistent with (nested well inside) the full-sweep CI —
  but the D≥3 sensitivity fit does **not independently corroborate** how
  close the full-sweep `beta_LRd` estimate came to the significance
  threshold. Read plainly: dropping `D∈{1,2}` removes whatever was pulling
  `beta_LRd` toward its near-boundary full-sweep value, without reversing
  its direction.
- **Net read**: no conclusion changes. H3/H4 remain not rejected under both
  the full sweep and the D≥3 subset in end-to-end-only mode. The interesting
  finding is specifically that H4's near-boundary p-value is not a robust
  feature of the D≥3-only data — it is a property of the full depth range,
  consistent with (but not proof of) a `depth_z`-moderated effect that needs
  the low-depth end of the design to be detectable at all.

### Effective sample size / convergence notes (end-to-end-only, full sweep → D≥3)

- `n_obs`: 101,891 (full sweep, end-to-end-only) → 82,940 (D≥3), a ~19%
  reduction — the same proportional drop seen in the pooled version of this
  comparison.
- `n_groups`: unchanged at 50.
- `n_vc_levels`: 3,200 (full) → 2,600 (D≥3), identical pattern to the pooled
  comparison (mode does not affect how many nested nested-nested groups
  exist).
- Condition number: 118.9 (full) → 126.9 (D≥3), consistent with the pooled
  comparison's modest increase.
- The Hessian-non-positive-definite warning (noted above) is the one new
  wrinkle relative to the pooled D≥3 fit, which did not emit it.

### Reproduction

```python
import pandas as pd
from qnn_snr.stats.models import fit_h2h4_model

pw = pd.read_parquet("results/production_confirmatory/pointwise_gradient_statistics.parquet")
sub = pw[(pw["analysis_mode"] == "finite_shot_end_to_end") & (pw["depth"].isin([3, 4, 6]))]
res = fit_h2h4_model(sub)
```

Fit wall-clock, actually measured: ~86s for the end-to-end-only D≥3 subset
(82,940 obs), single-threaded `lbfgs` REML on this machine.

---

## Original version (pooled-mode, superseded by the addendum above)

**The formula and mechanics below are still accurate** (`H2_H4_FORMULA`,
random-effect structure, `depth_z` handling) — only the mode composition of
the input data is now superseded. Numbers in this section pool
`finite_shot_conditional` and `finite_shot_end_to_end`, matching what the
confirmatory fit did *before* `verification/mode_pooling_guard.md` and
`verification/confirmatory_numbers_adopted.md`. Kept for the same
mode-sensitivity-is-itself-informative reason as the superseded confirmatory
CSVs in `results/`.

## Method

1. Source data: `results/production_confirmatory/pointwise_gradient_statistics.parquet`, the pointwise
   `(analysis_mode, configuration, matched parameter, depth, budget,
   initialization)` cell table already computed from
   `results/production_confirmatory/raw/finite_shot_end_to_end.parquet` and
   `results/production_confirmatory/raw/finite_shot_conditional.parquet` (Section 9 pipeline). This is
   a precomputed superset of the full-sweep confirmatory input — no new
   simulation was run, consistent with the instruction that this is a subset
   of already-generated data.
2. Subset filter: `depth.isin([3, 4, 6])`. Rows: 166,400 out of 204,800 total
   pointwise cells; of those, 165,160 have finite `SNR_est` and enter the
   model (1,240 dropped for non-finite SNR, same drop rule as the full-sweep
   fit — `build_h2h4_dataset` in `qnn_snr/stats/models.py`).
3. Model: **identical formula and random-effect structure** to the
   confirmatory fit — `qnn_snr.stats.models.H2_H4_FORMULA`:
   `y ~ E*L*R + depth_z + log2_budget + E:depth_z + L:depth_z + R:depth_z + L:R:depth_z`,
   random intercept on `initialization_id`, variance component on the nested
   `(initialization_id, depth, parameter_id)` id. Called via
   `fit_h2h4_model()` exactly as the confirmatory pipeline calls it — no
   formula edits, no re-standardization of `depth_z` (the column is reused
   as-is from the full-sweep design, i.e. it is *not* recentered/rescaled
   against only the `{3,4,6}` subset; this keeps the coefficient on the same
   scale as the confirmatory fit for direct comparison, at the cost of
   `depth_z`'s mean no longer being exactly 0 within the subset).
4. Both `finite_shot_conditional` and `finite_shot_end_to_end` rows are
   pooled in this refit, matching exactly how the existing full-sweep
   confirmatory number pools both modes (see `analysis_mode` value counts
   below) — the only thing varied here is the depth filter.

## Results

| Coefficient | Model | Estimate | SE | z | p (Wald, 2-sided) | 95% CI |
|---|---|---:|---:|---:|---:|---|
| `beta_ER` (`E:R`) | Full sweep (confirmatory, D∈{1,2,3,4,6}) | 0.003528 | 0.005675 | 0.622 | 0.534 | [-0.00759, 0.01465] |
| `beta_ER` (`E:R`) | **D≥3 sensitivity (D∈{3,4,6})** | **0.004078** | **0.005701** | **0.715** | **0.474** | **[-0.00710, 0.01525]** |
| `beta_LRd` (`L:R:depth_z`) | Full sweep (confirmatory, D∈{1,2,3,4,6}) | 0.000511 | 0.004162 | 0.123 | 0.902 | [-0.00765, 0.00867] |
| `beta_LRd` (`L:R:depth_z`) | **D≥3 sensitivity (D∈{3,4,6})** | **0.004717** | **0.005466** | **0.863** | **0.388** | **[-0.00600, 0.01543]** |

Both fits converged (`lbfgs`, `reml=True`) and reported `singular_fit=False`.
Both also emitted statsmodels' `ConvergenceWarning: The MLE may be on the
boundary of the parameter space` — **this warning appears in the full-sweep
fit too** (reproduced independently as part of this check), so it is a
pre-existing property of this model/data combination, not something the
D≥3 subsetting introduced.

## Direct comparison (the actual point of this analysis)

- **Sign**: both coefficients keep the same sign in the D≥3 subset as in the
  full sweep (`beta_ER` positive, `beta_LRd` positive in both — the full-sweep
  `beta_LRd` point estimate is `+0.000511`, essentially zero but not
  negative).
- **CI overlap**: extensive. The D≥3 CI for `beta_ER` ([-0.0071, 0.0153]) sits
  almost on top of the full-sweep CI ([-0.0076, 0.0146]); same for
  `beta_LRd` ([-0.0060, 0.0154] vs [-0.0076, 0.0087] — heavy overlap).
- **Magnitude**: `beta_ER` is essentially unchanged (0.00408 vs 0.00353, both
  far from significance). `beta_LRd` increases about 9x in point-estimate
  terms (0.00047 → 0.00472) but the SEs are wide enough (0.0042–0.0055) that
  this is not a material disagreement — the D≥3 estimate remains well inside
  the full-sweep 95% CI, and neither estimate is remotely close to rejecting
  at α=0.05 (p=0.39–0.90 across both fits for `beta_LRd`).
- **Net read**: the D≥3 sensitivity fit does not reverse or materially
  contradict the full-sweep confirmatory non-rejection of H3/H4. Neither
  coefficient becomes significant, and neither changes sign. The Methods
  section's sensitivity claim ("reports the same residual-related
  coefficients... as a post-run sensitivity analysis") is satisfied by this
  table; both results should be presented together as designed, not merged
  or used to override each other.

## Effective sample size / convergence notes when moving from full sweep to D≥3

- `n_obs`: 202,967 (full sweep) → 165,160 (D≥3), a ~19% reduction, as
  expected from dropping the `D=1` and `D=2` block-count levels.
- `n_groups` (initialization-level random intercept): unchanged at 50 in
  both fits — the design has 50 initializations regardless of depth filter,
  so this random-effect stratum loses no levels.
- `n_vc_levels` (nested `initialization_id × depth × parameter_id` variance
  component): 3,200 (full) → 2,600 (D≥3). Fewer depth levels mechanically
  reduce the number of distinct nested groups, since each additional depth
  contributes its own set of parameter ids.
- Condition number of the fixed-effect design matrix: 119.1 (full) vs 127.1
  (D≥3) — modestly higher but not in a range indicating a materially
  worse-conditioned fit.
- No singular-fit warning appeared in either fit (`singular_fit=False`).
- **Power for the `depth_z`-type moderation term (`beta_LRd`)**: as
  anticipated, going from 5 depth levels to 3 widens `beta_LRd`'s SE only
  modestly (0.004162 → 0.005466, ~+31%) — smaller than the roughly 19% drop
  in `n_obs` alone would suggest in isolation, likely because the retained
  depths (`3,4,6`) span a wider range of `depth_z` than the dropped
  `D∈{1,2}` levels, partially offsetting the loss of levels. Still, this is
  the coefficient most exposed to the reduced depth range, and the wider CI
  should be read as reduced sensitivity-analysis power relative to the
  full-sweep fit, not as a stronger or weaker finding in its own right.

## Reproduction

```python
import pandas as pd
from qnn_snr.stats.models import fit_h2h4_model

pw = pd.read_parquet("results/production_confirmatory/pointwise_gradient_statistics.parquet")
sub = pw[pw["depth"].isin([3, 4, 6])]
res = fit_h2h4_model(sub)
# res.params["E:R"], res.bse["E:R"], res.params["L:R:depth_z"], res.bse["L:R:depth_z"]
```

Fit wall-clock: ~99s for the D≥3 subset (165,160 obs), ~132s for the
full-sweep reproduction (202,967 obs), both single-threaded `lbfgs` REML
fits on this machine, actually measured for this check (not estimated).
