# QMI/QIP robustness package -- Task 1: D=1-exclusion sensitivity fit

**Status: sensitivity check only. Does not supersede, replace, or redefine
the full-sweep confirmatory H2--H4 result, and is a distinct population from
the existing `D>=3` sensitivity fit in
`verification/d_ge_3_sensitivity_refit.md` (which additionally excludes
`D=2`).** The full block-count sweep (`D in {1,2,3,4,6}`) remains the
confirmatory analysis.

**One result below crosses a QMI/QIP-prompt-specified material-change stop
condition ("any D!=1 estimate moves by more than one original full-sweep
SE") by a narrow margin (1.011 SE for `beta_EL`). Per that prompt's explicit
instruction, this is flagged here rather than folded quietly into the
manuscript narrative -- see "Flag" below. No manuscript prose has been
written or edited based on this result.**

## Method

- Source: `results/pointwise_gradient_statistics.parquet`, filtered to
  `analysis_mode == "finite_shot_end_to_end"` (the adopted confirmatory
  mode) for both fits compared here.
- Full-sweep (adopted): all five depth levels, `D in {1,2,3,4,6}`, 102,400
  candidate rows.
- Sensitivity population: `D != 1`, i.e. `D in {2,3,4,6}`, 96,000 candidate
  rows -- a different, less aggressive exclusion than `D>=3` (which drops
  19,200 more rows by additionally excluding `D=2`).
- **Critical comparability requirement, verified rather than assumed**:
  `depth_z` is a precomputed column standardized once against the full
  five-level nominal design (`verification/qmi_qip_analysis_inputs.md`
  Section 4) and is never recentered by `fit_h2h4_model` on a per-call
  basis. This script (`verification/run_d1_exclusion_sensitivity.py`)
  asserts directly that the `D!=1` subset's four `depth_z` values are a
  strict subset of the full sweep's five `depth_z` values before fitting --
  confirmed: `{-0.6975, -0.1162, 0.4650, 1.6275}` subset of
  `{-1.2787, -0.6975, -0.1162, 0.4650, 1.6275}`. **No re-standardization was
  performed or needed**; both coefficients are on the same scale.
- Model: identical `H2_H4_FORMULA`, random-effect structure, optimizer
  fallback order, REML, and zero-variance eligibility rule as the adopted
  fit -- called via the unmodified `fit_h2h4_model()` entry point, no
  formula edits.
- No Holm correction applied to this sensitivity comparison (per the
  prompt's instruction); the official Holm-adjusted decision remains the
  full-sweep one in `results/holm_adjustment.csv`.

## Results

Both fits converged (`lbfgs`, REML) and both emitted the same
`ConvergenceWarning: The MLE may be on the boundary of the parameter space`
already documented as a pre-existing, non-blocking property of this
model/data combination (`verification/qmi_qip_analysis_inputs.md` Section
3) -- not a new caveat introduced by the `D!=1` filter. Neither fit reported
`singular_fit=True`.

| Coefficient | Model | Estimate | SE | Wald z | p (2-sided) | 95% CI |
|---|---|---:|---:|---:|---:|---|
| `beta_EL` (`E:L`, H2) | Full sweep (adopted, `D∈{1,2,3,4,6}`) | +0.024996 | 0.007279 | +3.434 | 0.000595 | [+0.010729, +0.039263] |
| `beta_EL` (`E:L`, H2) | **`D≠1` sensitivity (`D∈{2,3,4,6}`)** | **+0.032354** | **0.007087** | **+4.565** | **4.99e-06** | **[+0.018464, +0.046244]** |
| `beta_ER` (`E:R`, H3) | Full sweep (adopted, `D∈{1,2,3,4,6}`) | -0.000958 | 0.007293 | -0.131 | 0.896 | [-0.015252, +0.013337] |
| `beta_ER` (`E:R`, H3) | **`D≠1` sensitivity (`D∈{2,3,4,6}`)** | **-0.000941** | **0.007095** | **-0.133** | **0.895** | **[-0.014848, +0.012966]** |
| `beta_LRd` (`L:R:depth_z`, H4) | Full sweep (adopted, `D∈{1,2,3,4,6}`) | -0.010179 | 0.005362 | -1.898 | 0.058 | [-0.020688, +0.000331] |
| `beta_LRd` (`L:R:depth_z`, H4) | **`D≠1` sensitivity (`D∈{2,3,4,6}`)** | **-0.009847** | **0.005781** | **-1.703** | **0.089** | **[-0.021179, +0.001485]** |

## Direct comparison (per-coefficient)

| Coefficient | Abs. change | Change in original-SE units | Sign agreement | CI overlap | Interpretation change? |
|---|---:|---:|---|---|---|
| `beta_EL` | +0.007358 | **+1.011** | Yes | Yes (extensive) | No -- see "Flag" below |
| `beta_ER` | +0.000017 | +0.002 | Yes | Yes (near-total) | No |
| `beta_LRd` | +0.000332 | +0.062 | Yes | Yes (extensive) | No |

- **`beta_ER` (H3)**: essentially unchanged in every respect. Remains a
  clean null (p=0.895 vs 0.896). No conclusion changes.
- **`beta_LRd` (H4)**: point estimate barely moves (-0.0102 -> -0.0098,
  0.062 original-SE units), same sign, CI overlap extensive. If anything the
  `D≠1` estimate moves *further* from the significance boundary (p: 0.058 ->
  0.089) rather than closer, which is the opposite direction from what the
  existing `D>=3` sensitivity fit shows (p: 0.058 -> 0.443, a much larger
  shrinkage). This is consistent with `D>=3`'s more aggressive exclusion
  (which also drops `D=2`) removing more of whatever depth-range structure
  the full sweep needs to produce the near-boundary estimate than the
  less-aggressive `D≠1` exclusion does -- `D≠1` keeps `D=2` in the
  sensitivity population, `D>=3` does not. No conclusion changes: H4 remains
  not rejected under both the full sweep and this `D≠1` subset.
- **`beta_EL` (H2)**: sign unchanged (positive in both), CI overlap
  extensive, and the coefficient becomes *more* significant, not less
  (p: 0.000595 -> 4.99e-06) -- if this were being read purely by the
  "does the qualitative conclusion survive" standard, the answer is an
  unambiguous yes, more so than before. **But the point estimate itself
  moves by +1.011 original-SE units**, which is, by a narrow margin (0.011
  SE past the threshold), a literal trigger of the QMI/QIP prompt's own
  material-change stop condition ("any D!=1 estimate moves by more than one
  original full-sweep SE"). See "Flag" immediately below.

## Flag: `beta_EL`'s +1.011-SE shift under `D≠1` exclusion

**What changed**: excluding `D=1` entirely moves the `beta_EL` point
estimate up by about 29% (0.024996 -> 0.032354), a shift of 1.011 times the
full-sweep coefficient's own standard error (0.007279).

**Why this is very likely a precision effect, not evidence the adopted
estimate is an artifact of `D=1`** (read as context, not as a resolution --
per the prompt's stop-condition instructions, this is reported for the
user's judgment, not resolved unilaterally here):

- `D=1` has the highest zero-variance exclusion rate of any block count in
  end-to-end mode -- 165/6,400 cells excluded (2.58%), versus 84/12,800
  (0.66%) at `D=2`, 79/19,200 (0.41%) at `D=3`, 79/25,600 (0.31%) at `D=4`,
  and 102/38,400 (0.27%) at `D=6` (full breakdown in
  `verification/zero_variance_exclusion_audit.md`, Task 2). `D=1` is also
  the block count Section 4.1 of the paper already documents as the one
  where the replicate-count calibration criterion did not converge even at
  a raised ceiling. Removing the noisiest, worst-calibrated block count
  making the coefficient *more* precisely estimated (SE narrows slightly,
  0.007279 -> 0.007087) and *more* significant, in the same direction, is
  the pattern expected from removing a noisier subpopulation, not the
  pattern expected from removing a subpopulation that was driving a
  spurious effect (which would typically shrink the estimate toward zero
  and/or widen the CI when removed).
- The two independent sensitivity fits sitting either side of `beta_EL`
  give a consistent qualitative picture: `D>=3` (dropping D=1 *and* D=2,
  `verification/d_ge_3_sensitivity_refit.md`'s counterpart for H3/H4 does
  not cover `beta_EL` since it is not part of that document's H3/H4 scope --
  this `D≠1` fit is the first sensitivity check run specifically against
  `beta_EL`) is not directly available for a three-point comparison here;
  this is noted as a gap rather than papered over. A `D>=3` refit of
  `beta_EL` specifically was not part of this task's required scope and was
  not run.
- No sign reversal, no CI-non-overlap, no p-value crossing 0.05 in an
  unfavorable direction (H2 was already solidly rejected; it becomes more
  so). The shift is real and larger than a purely cosmetic sensitivity check
  would produce, but every other diagnostic available points toward "H2's
  rejection is not an artifact of the `D=1` data," not away from it.

**This is reported as a flagged, unresolved observation per the prompt's own
guardrails, not as a settled finding.** No change has been made to
`main.tex`, to the confirmatory Holm decision, or to any prose describing
H2 as a result of this observation. Task 5 (manuscript integration) should
present this `D≠1` sensitivity result plainly, including the +1.011-SE
shift and the context above, and should not describe it as "no conclusion
changes" without the user's explicit sign-off, since that phrase is exactly
what the stop condition is designed to prevent being written quietly.

## Effective sample size / convergence notes

- `n_obs`: 101,891 (full sweep, 509 dropped for non-finite `SNR_est`) ->
  95,656 (`D≠1`, 344 dropped), a ~6.1% reduction in modeled rows (96,000
  candidate rows before the finite-SNR filter, vs 102,400 for the full
  sweep) -- much smaller than the ~19% reduction the `D>=3` sensitivity fit
  produces, as expected since only one depth level (of five) is dropped
  here versus two.
- `n_groups`: unchanged at 50 in both fits.
- `n_vc_levels`: 3,200 (full) -> 3,000 (`D≠1`) -- proportionally smaller
  reduction than `D>=3`'s 3,200 -> 2,600, consistent with dropping one depth
  level instead of two.
- Condition number: 118.88 (full) -> 120.47 (`D≠1`) -- a small increase, not
  in a range indicating a materially worse-conditioned design matrix.
- Random-effect variances: group-intercept variance 0.001145 -> 0.001348;
  nested-parameter variance 0.087723 -> 0.072193. Neither is close to the
  `1e-8` singular-fit tolerance in either fit.
- Fit wall-clock, actually measured this session: 30.8s (full sweep),
  38.1s (`D≠1`), single-threaded `lbfgs` REML on this machine.

## Reproduction

```bash
python verification/run_d1_exclusion_sensitivity.py
```

Writes `results/d1_exclusion_sensitivity_coefficients.csv` (per-coefficient
full-sweep and `D≠1` estimate/SE/z/p/CI rows, plus a `comparison` row per
coefficient carrying `abs_change`/`se_units_change`/`sign_agree`/
`ci_overlap`) and `verification/_d1_exclusion_sensitivity_diagnostics.json`
(convergence/singularity/condition-number diagnostics for both fits).

## Files produced

- `verification/run_d1_exclusion_sensitivity.py` -- the fitting script.
- `results/d1_exclusion_sensitivity_coefficients.csv`
- `verification/_d1_exclusion_sensitivity_diagnostics.json`
- `paper/scripts/make_fig6_d1_exclusion_sensitivity.py`,
  `paper/figures/fig6_d1_exclusion_sensitivity.pdf`
