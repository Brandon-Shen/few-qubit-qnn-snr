# Conditional-mode vs end-to-end-mode H2–H4 fit comparison

**Status: exploratory throughout**, consistent with the paper's Results
drop-in guide ("4.6: ...conditional mode... are exploratory"). Nothing here
is part of the Holm-corrected confirmatory family.

## Important premise correction — read this first

The task that generated this analysis assumed "only end-to-end [mode] has
been reported" for the H2–H4 confirmatory fit, with conditional mode still
missing. **That is not what the existing confirmatory numbers are.**
Checking `qnn_snr/cli.py` (`cmd_fit`, `cmd_report`) and
`qnn_snr/stats/pointwise.py` directly:

- `pointwise_statistics()` filters to
  `analysis_mode.isin(["finite_shot_conditional", "finite_shot_end_to_end"])`
  and keeps `analysis_mode` as a `CELL_KEY_COLS` grouping key, so each
  pointwise cell is mode-specific.
- But `fit_h2h4_model(pw)` is then called on the **combined** `pw` table
  containing both modes' cells together. `H2_H4_FORMULA` does not include
  `analysis_mode` as a fixed effect, and the random-effect grouping
  (`initialization_id`, nested by `depth`/`parameter_id`) does not condition
  on mode either. So the model has no way to distinguish which mode a row
  came from — it is fit as if all rows were exchangeable observations.
- Confirmed empirically: `results/production_confirmatory/pointwise_gradient_statistics.parquet` has
  102,400 `finite_shot_conditional` rows and 102,400 `finite_shot_end_to_end`
  rows, 204,800 total, and refitting `fit_h2h4_model()` on that full,
  unfiltered table reproduces `results/production_confirmatory/confirmatory_hypotheses.csv` exactly
  (`E:L=0.023732`, `E:R=0.003528`, `L:R:depth_z=0.000511` — bit-for-bit match
  down to the value stored in the CSV).

So the number currently in `results_and_discussion.md` /
`results/production_confirmatory/confirmatory_hypotheses.csv` is a **pooled fit across both modes**,
not an end-to-end-only fit. This document therefore reports three fits, not
two: conditional-only, end-to-end-only, and the existing pooled number for
reference — so the comparison the paper's Methods section actually promises
(conditional vs end-to-end) can be made at all.

## Method

Same formula and random-effect structure as the confirmatory fit
(`H2_H4_FORMULA`, full block-count sweep `D∈{1,2,3,4,6}`), applied to
`results/production_confirmatory/pointwise_gradient_statistics.parquet` filtered to a single
`analysis_mode` value per fit:

```python
sub_cond = pw[pw["analysis_mode"] == "finite_shot_conditional"]
sub_e2e  = pw[pw["analysis_mode"] == "finite_shot_end_to_end"]
```

Both fits converged (`lbfgs`, REML, `singular_fit=False`); both also emitted
the same boundary `ConvergenceWarning` noted in
[`d_ge_3_sensitivity_refit.md`](d_ge_3_sensitivity_refit.md), which is not
mode-specific.

- `finite_shot_conditional`: n_obs=101,076, n_groups=50, n_vc_levels=3,200,
  condition number=119.2.
- `finite_shot_end_to_end`: n_obs=101,891, n_groups=50, n_vc_levels=3,200,
  condition number=118.9.

## Results

| Coefficient | Conditional-only | End-to-end-only | Pooled (existing confirmatory) |
|---|---|---|---|
| `beta_EL` (`E:L`) | est=0.023170, SE=0.008458, z=2.739, **p=0.0062**, CI=[0.00659, 0.03975] | est=0.024996, SE=0.007279, z=3.434, **p=0.00059**, CI=[0.01073, 0.03926] | est=0.023732, SE=0.005650, z=4.200, p=2.7e-5, CI=[0.01266, 0.03481] |
| `beta_ER` (`E:R`) | est=0.006884, SE=0.008516, z=0.808, p=0.419, CI=[-0.00981, 0.02358] | est=-0.000958, SE=0.007293, z=-0.131, p=0.896, CI=[-0.01525, 0.01334] | est=0.003528, SE=0.005675, z=0.622, p=0.534, CI=[-0.00759, 0.01465] |
| `beta_LRd` (`L:R:depth_z`) | est=0.010437, SE=0.006231, z=1.675, p=0.094, CI=[-0.00178, 0.02265] | est=-0.010179, SE=0.005362, z=-1.898, p=0.058, CI=[-0.02069, 0.00033] | est=0.000511, SE=0.004162, z=0.123, p=0.902, CI=[-0.00765, 0.00867] |

(All fits use the two-sided Wald normal method, matching
`stats.p_value_method` in `configs/confirmatory.yaml`.)

## Per-coefficient agreement check

- **`beta_EL`**: **agrees** across modes. Same sign (positive) in both,
  overlapping magnitude (0.0232 vs 0.0250), heavily overlapping CIs, and
  both individually significant at α=0.05 even before any multiplicity
  correction. This is the one coefficient that looks robust to which mode
  generated the forward features.
- **`beta_ER`**: signs disagree (conditional positive, end-to-end
  effectively zero/slightly negative), but both CIs are wide, both contain
  zero, both are far from significant, and the CIs overlap each other
  substantially ([-0.0098, 0.0236] vs [-0.0153, 0.0133]). This does not read
  as a material disagreement — it reads as two independently noisy
  estimates of a coefficient that neither mode nor the pooled fit
  distinguishes from zero.
- **`beta_LRd`**: **signs disagree** and the disagreement is more
  structured than for `beta_ER` — conditional-only is positive and close to
  the α=0.10 boundary (p=0.094), end-to-end-only is negative and also close
  to that boundary from the other side (p=0.058). Neither individually
  clears α=0.05, and the CIs still overlap (both contain the region around
  ±0.003), but the point estimates sit on opposite sides of zero with
  comparable magnitude (+0.0104 vs -0.0102) and comparable precision (SE
  0.0062 vs 0.0054). **This is the coefficient where the two modes show the
  most tension.**

## Interpretation

Per the paper's own framing (Methods: "material disagreement between the
modes is interpreted as sensitivity to forward-feature sampling"), the
`beta_LRd` split here is the clearest candidate for that interpretation:
conditional mode (which reuses the same forward features / does not
re-estimate them from finite-shot data at each stage) and end-to-end mode
(which re-estimates forward features at every stage, propagating their
finite-shot noise) disagree in sign on this three-way interaction, in a way
that is directionally consistent with forward-feature noise mattering more
for the depth-moderated residual-path term than for the others.

This is **not** grounds to prefer one mode's estimate, and it is **not**
evidence against the existing pooled confirmatory result — if anything it
explains why the pooled `beta_LRd` estimate is so close to zero
(`+0.000511`): it is numerically consistent with an unweighted average of a
positive conditional-mode effect and a similarly-sized negative
end-to-end-mode effect roughly cancelling. That the pooled fit does not
statistically distinguish `analysis_mode` as its own factor (see premise
correction above) means this cancellation happens silently inside the
existing confirmatory number; readers of `results_and_discussion.md` should
be aware the reported `beta_LRd≈0` reflects mode-pooling, not necessarily a
genuinely near-zero effect within either mode individually.

`beta_EL` shows no such tension and can be read as robust across the
forward-feature sampling design choice.

## Reproduction

```python
import pandas as pd
from qnn_snr.stats.models import fit_h2h4_model

pw = pd.read_parquet("results/production_confirmatory/pointwise_gradient_statistics.parquet")
for mode in ("finite_shot_conditional", "finite_shot_end_to_end"):
    res = fit_h2h4_model(pw[pw["analysis_mode"] == mode])
```

Fit wall-clock, actually measured: ~64s (conditional), ~65s (end-to-end),
single-threaded `lbfgs` REML on this machine.
