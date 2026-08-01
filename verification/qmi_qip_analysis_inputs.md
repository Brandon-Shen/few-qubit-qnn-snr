# QMI/QIP robustness package -- Task 0: frozen adopted-analysis inputs

**Purpose**: freeze, in one place, the exact code paths, data files, and
modeling conventions that Tasks 1-4 of the QMI/QIP robustness package must
reuse without modification, and confirm the adopted H2-H4 coefficients
reproduce exactly before any new analysis is built on top of them. This
document does not change any adopted number; it is a provenance record.

## 1. Git state

- **HEAD commit**: `3f4c04e3b0cdcca44c63043566057eb9537182f5`
  ("Add H2-H4 low-memory bootstrap redesign, concurrency safety tests, and
  RSS profiling artifacts").
- **Working tree**: not clean -- 34 modified/untracked paths at the time this
  record was written, entirely `paper/` (new, unrelated LaTeX work in
  progress), `.claude/` tooling, and pre-existing untracked `verification/`
  files from the mode-pooling-fix and low-memory-bootstrap sessions
  (`verification/_bootstrap_checkpoints/*`, `verification/run_h2h4_*`,
  `verification/*.md`, `verification/_*_stdout.log`,
  `verification/_*_coefficients.csv`). None of `qnn_snr/`'s tracked source
  files other than `qnn_snr/cli.py` and `qnn_snr/stats/models.py` (both
  already committed as part of the mode-pooling guard, per
  `verification/mode_pooling_guard.md`) show as modified relative to HEAD --
  i.e. the fitting/bootstrap production code this package depends on is the
  code actually at `3f4c04e`, not a further uncommitted edit.
- **Raw simulation data provenance**: `results/production_confirmatory/raw/finite_shot_end_to_end.parquet`
  (and its `finite_shot_conditional`/`exact` siblings) carry an embedded
  `git_commit` column recorded at generation time:
  `cbbeafa853b0e87e153a783296fed1f9c750681a` ("Replace pilot codebase with
  full QNN-SNR confirmatory pipeline") -- two commits behind current HEAD.
  This confirms the quantum simulation itself has not been regenerated since
  `cbbeafa`; every commit since then (`d089529`, `3f4c04e`) is analysis-code
  and verification-artifact work on top of the same frozen raw dataset, which
  is exactly the "do not regenerate" precondition this package operates
  under. Embedded `software_version = pennylane==0.45.1`,
  `quantum_framework = pennylane`, `simulator_backend = default.qubit`,
  `config_hash = bb1fe393a979c8d2` (identical across all rows of the file --
  confirmed via `drop_duplicates()`).

## 2. Located inputs

| Item | Path | Notes |
|---|---|---|
| Pointwise statistics | `results/production_confirmatory/pointwise_gradient_statistics.parquet` | 204,800 rows (102,400 `finite_shot_end_to_end` + 102,400 `finite_shot_conditional`); SHA-256 `99a4decf8597c9fcc5a61a8e59075d34e1cf6668714ee19e38b39258e15d1342` |
| Replicate-level finite-shot data (bootstrap inner-resampling source) | `results/production_confirmatory/raw/finite_shot_end_to_end.parquet` | SHA-256 `22b5e761f461c6bfde7a60a4efa7ac13bc59ae003488be84d2f0c1e57ddb7f39` |
| (diagnostic-only sibling, not used by the confirmatory bootstrap) | `results/production_confirmatory/raw/finite_shot_conditional.parquet` | SHA-256 `b15b19088d22a0429f48158cdee5ee3caec52f6819815579b3e6aed189afe413` |
| Exact-gradient data (H1 only, no finite-shot mode) | `results/production_confirmatory/raw/exact.parquet` | SHA-256 `77e54bed863de79be0d1ebb4937f015fe29a1b1cb5d58e0f216f3acd4b9bb542` |
| Confirmatory formula | `qnn_snr/stats/models.py:30` | `H2_H4_FORMULA = "y ~ E*L*R + depth_z + log2_budget + E:depth_z + L:depth_z + R:depth_z + L:R:depth_z"` |
| Official end-to-end fitting function | `qnn_snr.stats.models.fit_h2h4_model` (calls `fit_mixed_model(H2_H4_FORMULA, build_h2h4_dataset(pointwise_df, pool_modes=False), "y")`) | `build_h2h4_dataset` raises `ValueError` if more than one `analysis_mode` value is present unless `pool_modes=True` is passed explicitly |
| Production CLI confirmatory path | `qnn_snr/cli.py:cmd_fit` (default `--mode` = `CONFIRMATORY_MODE`) | Filters `pw_all` to one mode (line 134/152 region) before calling `fit_h2h4_model`/`fit_sensitivity_model`; a separate `--mode finite_shot_conditional` branch writes only to a `*_diagnostic_*.csv` file and never touches confirmatory outputs |
| Adopted coefficients record | `results/production_confirmatory/snr_model_coefficients.csv`, `results/production_confirmatory/confirmatory_hypotheses.csv`, `results/production_confirmatory/holm_adjustment.csv` | Regenerated through the guarded `cmd_fit` path per `verification/confirmatory_numbers_adopted.md` |
| Adoption writeup | `verification/confirmatory_numbers_adopted.md` | End-to-end-only adoption, Holm recomputation, disposition of superseded pooled files |
| Mode-pooling bug fix | `verification/mode_pooling_guard.md` | Code-level guard added to `build_h2h4_dataset`/`fit_h2h4_model`/`cli.py` call sites |

## 3. Reproduction check

Ran, fresh, in this session (not copied from any prior derivation):

```python
import pandas as pd
from qnn_snr.stats.models import fit_h2h4_model

df = pd.read_parquet("results/production_confirmatory/pointwise_gradient_statistics.parquet")
eo = df[df["analysis_mode"] == "finite_shot_end_to_end"].copy()
res = fit_h2h4_model(eo)  # raises if mixed-mode; eo is single-mode here
```

- `eo` rows: 102,400 (depth counts: D=1: 6,400; D=2: 12,800; D=3: 19,200;
  D=4: 25,600; D=6: 38,400 -- matches the expected replicate-count-weighted
  design, not a uniform split across depths).
- Fit wall-clock this session: **31.8s** (single-threaded `lbfgs`, `reml=True`,
  on this machine, right now -- consistent with, though on the faster end of,
  the 86-132s range reported for similar-size fits in
  `verification/d_ge_3_sensitivity_refit.md`, underscoring that this
  machine's per-fit wall-clock is not a stable, predictable number and should
  always be measured fresh rather than assumed from a prior session).
- `converged = True`, `optimizer_used = "lbfgs"` (first optimizer in
  `OPTIMIZER_FALLBACK_ORDER` succeeded, no fallback needed).
- Emitted `ConvergenceWarning: The MLE may be on the boundary of the
  parameter space` -- **the same warning already documented as a
  pre-existing, non-blocking property of this model/data combination** in
  `verification/d_ge_3_sensitivity_refit.md` (confirmed there to also appear
  on the full-sweep fit, not introduced by any subsetting). Task 3 below
  treats this as the baseline convergence-warning state to compare all
  sensitivity/diagnostic refits against.
- **Coefficients reproduced exactly** to displayed precision against the
  values quoted in the QMI/QIP prompt and in
  `verification/confirmatory_numbers_adopted.md`:

  | Coefficient | Adopted (prior record) | Reproduced this session |
  |---|---:|---:|
  | `E:L` (`beta_EL`, H2) | 0.024995843985971582 | 0.024995843985971582 |
  | `E:R` (`beta_ER`, H3) | -0.0009575787575784316 | -0.0009575787575784316 |
  | `L:R:depth_z` (`beta_LRd`, H4) | -0.010178757716721849 | -0.010178757716721849 |

  Bit-for-bit identical (not merely close) at full float64 precision.
  **The adopted fit is reproducible from the frozen inputs above; this
  package proceeds on that basis.**

- Confirmed (by reading `qnn_snr/stats/models.py` and
  `qnn_snr/cli.py`, not just by trusting the docstrings): the production
  path filters to `analysis_mode == "finite_shot_end_to_end"` before any
  H2-H4 fit, and `build_h2h4_dataset` raises on mixed-mode input unless
  `pool_modes=True` is passed explicitly. No `pool_modes=True` call site
  exists anywhere in `qnn_snr/cli.py`'s confirmatory branches.

**Adopted fit is exactly reproducible and the production path is
single-mode by construction. Proceeding with Tasks 1-4.**

## 4. Frozen modeling conventions (must not be altered by any sensitivity/diagnostic task below)

- **Response transformation**: `y = arcsinh(SNR_est)` (`build_h2h4_dataset`,
  `qnn_snr/stats/models.py:176`). `SNR_est = inf` cells (zero replicate
  variance with nonzero mean) are excluded via `np.isfinite(d["SNR_est"])`
  (same line) -- this *is* the zero-variance exclusion rule Task 2 audits.
- **Effect coding**: `E`, `L`, `R` are stored as numeric 0/1 columns and
  entered into the patsy formula as `E*L*R`, which the module docstring notes
  expands to `E+L+R+E:L+E:R+L:R+E:L:R`. (Note: the paper's Methods describes
  effect coding as {-1/2, +1/2}; the code's numeric 0/1 columns combined with
  the raw `E*L*R` patsy expansion is what actually produced the adopted
  coefficients above -- this record describes the code as it exists, not a
  re-derivation of the paper's symbolic convention. Any discrepancy between
  the paper's stated coding and the code's actual 0/1 coding is out of scope
  for this package and is not resolved here.)
- **Block-count centering/scaling**: `depth_z = (depth - depth_mean) /
  depth_std`, computed once from the design's five *distinct nominal depth
  levels* `{1,2,3,4,6}` (`config.circuit.depths`), unweighted by replicate
  count (ASSUMPTION A18, `qnn_snr/replicate.py`) -- **not** a per-row or
  per-subset empirical standardization. Verified directly from the data:
  distinct `(depth, depth_z)` pairs are `(1, -1.278724)`, `(2, -0.697486)`,
  `(3, -0.116248)`, `(4, 0.464991)`, `(6, 1.627467)`, constant across every
  row regardless of `analysis_mode`, configuration, or budget. **This means
  the "critical comparability requirement" flagged in the QMI/QIP prompt for
  Task 1 (preserve full-sweep depth centering/scaling when fitting the
  D\ne1 subset) is already satisfied by construction**: filtering
  `pointwise_gradient_statistics.parquet` to `D != 1` and calling
  `fit_h2h4_model` directly reuses the existing `depth_z` column verbatim --
  there is no re-standardization step to disable, because none exists in the
  per-subset fitting path (`fit_h2h4_model` never recomputes `depth_z`; it is
  a precomputed input column). This is the same convention already used,
  and explicitly confirmed as unchanged, by the existing `D>=3` sensitivity
  fit (`verification/d_ge_3_sensitivity_refit.md`, "Method" section).
- **Random-effects structure**: random intercept on `initialization_id`
  (`re_formula="1"`, `groups=initialization_id`) plus a variance component on
  `nested_param_id = initialization_id__d{depth}__{parameter_id}`
  (`vc_formula={"param": "0 + C(nested_param_id)"}`) -- i.e. matched
  parameter nested within initialization *and* depth (ASSUMPTION A20,
  `qnn_snr/stats/models.py:4-13`: each depth level draws an independent theta
  value, so nesting must include depth, not just `(init, parameter_id)`).
- **ML vs. REML**: **REML** (`reml=True`, hard-coded in
  `_fit_with_fallback`, `qnn_snr/stats/models.py:77`) for every production
  and sensitivity fit. No ML-fit variant exists in the current codebase.
- **Optimizer**: `OPTIMIZER_FALLBACK_ORDER = ["lbfgs", "bfgs", "cg", "powell",
  "nm"]` (`qnn_snr/stats/models.py:27`) -- tries `lbfgs` first via
  `statsmodels.regression.mixed_linear_model.MixedLM.fit(method=..., reml=True)`,
  falling through the list only if the current method raises or reports
  non-convergence. The adopted fit (and the reproduction above) both used
  `lbfgs` with no fallback needed.
- **Convergence tolerances**: no explicit `gtol`/`ftol`/`maxiter` overrides
  are passed anywhere in `_fit_with_fallback` -- every fit uses
  `statsmodels`'/`scipy.optimize.minimize`'s built-in defaults for the chosen
  method. This is stated plainly rather than guessed: the call is literally
  `model.fit(method=method, reml=True)` with no additional keyword
  arguments, so whatever `scipy` ships as the default tolerance for `lbfgs`
  (etc.) is what every fit in this codebase, including the adopted
  confirmatory fit, actually used.
- **Singular-fit policy**: `MixedModelResult.singular_fit` is
  `True` iff the estimated group-level random-intercept variance or the
  nested variance-component variance is within `atol=1e-8` of zero
  (`np.isclose(..., 0.0, atol=1e-8)`, `qnn_snr/stats/models.py:120`) -- a
  hard-coded tolerance, not user-configurable per call. The adopted
  confirmatory fit has `singular_fit=False` (measured directly in Task 3
  below, not assumed).
- **Zero-variance exclusion rule**: `ZERO_VARIANCE_TOL = 0.0` (exact zero
  only, `qnn_snr/stats/pointwise.py:24`, "Section 9 forbids silently adding
  epsilon") -- a pointwise cell's `zero_variance_flag` is `True` iff its
  across-replicate sample variance (`ddof=1`) is finite and `<= 0.0`. Flagged
  cells get `SNR_est = inf` (if the mean is nonzero) or `nan` (if the mean is
  exactly zero too), both of which `build_h2h4_dataset` drops via
  `np.isfinite`. This flag is stored directly as the `zero_variance_flag`
  boolean column in `pointwise_gradient_statistics.parquet` -- Task 2 reads
  this column directly rather than re-deriving it from any rounded output.

## 5. Gate for continuing

Per the QMI/QIP prompt's instruction not to continue if the adopted fit
cannot be reproduced or if the production path silently contains multiple
estimator modes: **both checks passed** (Section 3 above). Proceeding to
Task 1.
