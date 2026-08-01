# H2 depth-heterogeneity analysis — frozen plan

**Status: FROZEN before any continuous, categorical, omnibus, weighted,
cluster-robust, or include-zero coefficient in this package was
inspected.** Written immediately after Phase 0 inspection, committed
before Phase 1's runner is executed. This is explicitly a post-run
package: the separate-depth diagnostic that motivates it
(`scripts/run_h2_robust_inference_fast.py`'s `run_depth_stratified`,
recorded in `verification/h2_robustness_replication_results.md` Section
3.1) is already known. Freezing this plan prevents any further
outcome-dependent change to formulas, contrasts, weights, or
interpretation language.

Governs a new package: `qnn_snr/stats/depth_heterogeneity.py`,
`scripts/run_h2_depth_heterogeneity.py`,
`results/h2_robustness/depth_heterogeneity/`,
`results/h2_replication_v1/depth_heterogeneity/`,
`paper/figures/fig11_h2_depth_heterogeneity.*`,
`paper/tables/h2_depth_heterogeneity.tex`. Nothing under
`results/production_confirmatory/`, `results/h2_replication_v1/_pipeline_output_stage1/raw|pointwise*`,
`configs/`, or the original `results/h2_robustness/{original_data_audit,decomposition,robust_inference}/`
is modified.

---

## 0. Phase 0 inspection summary

### 0.1 Input files and hashes (frozen, read-only in this package)

| Dataset | File | SHA-256 |
|---|---|---|
| Original | `results/production_confirmatory/pointwise_gradient_statistics.parquet` | `99a4decf8597c9fcc5a61a8e59075d34e1cf6668714ee19e38b39258e15d1342` |
| Replication | `results/h2_replication_v1/_pipeline_output_stage1/pointwise_gradient_statistics.parquet` | `e85f31d8f33ac46d717795bfd9879bd79dfa72a3095e517eedfe3b042c159998` |
| Original config | `configs/confirmatory.yaml` (hash `bb1fe393a979c8d2`) | `d531ed722df1c5be2b19da6e366f398471f0d72ac3573fc6acecafe4c1e40a3a` |
| Replication config | `configs/h2_replication_v1_stage1.yaml` (hash `ccc2d9fdc5ba9cbd`) | `89521e5a483bf8714fa4524d302a83568dedb552b35a26d91d7b4f328072b8e8` |

Git commit at freeze time: `7051f5842adef7f6336df724d36d540f006cb11f`.

### 0.2 Original vs. replication eligibility (reconfirmed directly, matches prior records)

| | original | replication |
|---|---:|---:|
| End-to-end cells | 102,400 | 102,400 |
| Zero-variance excluded | 509 (0.497%) | 585 (0.571%) |
| Zero-variance cells with `mu_hat==0` | 509/509 (100%) | 585/585 (100%) |
| Depths present | {1,2,3,4,6} | {1,2,3,4,6} |
| Distinct initializations | 50 | 50 |

### 0.3 Existing code reused (not duplicated)

- `qnn_snr.stats.pointwise.pointwise_statistics` / `zero_variance_confirmatory_cells` /
  `ZERO_VARIANCE_TOL` — zero-variance flag, unchanged.
- `qnn_snr.stats.models.fit_mixed_model` — REML fit, optimizer fallback
  order `["lbfgs","bfgs","cg","powell","nm"]`, convergence/singularity
  reporting, residual diagnostics. Reused as-is for every mixed-model fit
  in this package (continuous and categorical).
- `qnn_snr.stats.models.build_h2h4_dataset` — single-mode guard
  (`ValueError` on mixed `analysis_mode`), `arcsinh(SNR_est)` response,
  identical exclusion filter (`np.isfinite(SNR_est)`). Reused unchanged
  for the primary (complete-case) eligibility path in this package.
  Reused (bypassed only via an explicit, separately labeled path, never
  silently) for the Section 6 include-zero sensitivity.
- `qnn_snr.stats.models.CONFIRMATORY_MODE` (`"finite_shot_end_to_end"`) —
  the only mode used anywhere in this package.
- `qnn_snr.stats.models._add_nested_id` — nested
  `initialization_id__depth__parameter_id` variance-component id,
  reused unchanged (ASSUMPTION A20 is unaffected by adding `E:L:depth_z`
  or by switching `depth_z` to `C(depth, Sum)` in the *fixed*-effect
  formula — the nested random-effect id remains defined the same way).
- `E`, `L`, `R`, `depth`, `depth_z`, `log2_budget` columns — numeric 0/1
  (E,L,R) and numeric depth/scaling columns already present in the
  pointwise file, produced by `qnn_snr/replicate.py::depth_standardization`.
  **Not recomputed.** `depth_standardization([1,2,3,4,6])` gives
  `mean=3.2, std=1.7204650534085253` (population std, `ddof=0`) — this is
  already baked into both the original's and the replication's
  `depth_z` column (both configs use the identical `circuit.depths:
  [1,2,3,4,6]`, so the replication's `depth_z` is already computed with
  the *same* scaling constants; no rescaling is performed anywhere in
  this package for either dataset — reusing the input columns as-is is
  exactly "preserving the original full-sweep depth_z centering and
  scaling").
- `verification/h2_robustness_replication_plan.md`/`_results.md` — prior
  package's zero-variance-exact-zero-mu_hat finding, cluster-robust
  method choice and justification, seed-namespace verification. Not
  re-derived; cited.
- `scripts/run_h2_robust_inference_fast.py::run_depth_stratified` — the
  existing per-depth separate-fit diagnostic this package's categorical
  model is designed to test more rigorously (Primary Question 1: does
  *one* model support depth-moderation, vs. five independent fits).
  Read for reference; not modified, not called.

### 0.4 statsmodels capabilities confirmed (Phase 0 sandbox checks, not part of any reported result)

- `MixedLMResults.wald_test_terms(skip_single=False, scalar=True)`
  correctly groups patsy design-matrix columns by term (e.g.
  `"E:L:C(depth, Sum)"`, `df=4`) and returns a table with `statistic`,
  `pvalue`, `df_constraint` per term — used for the Phase 1(C) omnibus
  test. **No hardcoded coefficient-name matching is needed or used.**
  `scalar=True` avoids a `FutureWarning` and returns plain floats.
- `MixedLMResults.t_test(r_matrix)` requires `r_matrix.shape[1] ==
  k_fe` (fixed-effect columns only, *not* including the appended
  `Group Var`/`param Var` random-effect variance rows in `.params`) —
  contrast vectors built from `patsy.build_design_matrices` against the
  fitted model's own `design_info` (`result.raw_result.model.data.design_info`)
  are used directly, with no padding, no reordering.
- This same `design_info` + `build_design_matrices` + `t_test` pattern
  works identically for the cluster-robust OLS fits (Phase 1E), since
  `RegressionResultsWrapper.t_test` uses the same `r_matrix`-shape
  convention with no random-effect terms to exclude.

---

## 1. Formulas (fixed)

### 1.1 Continuous depth-moderation model (Phase 1A)

```
y ~ E*L*R + depth_z + log2_budget + E:depth_z + L:depth_z + R:depth_z
    + E:L:depth_z + L:R:depth_z
```

Exactly the adopted `H2_H4_FORMULA` plus one added focal term,
`E:L:depth_z`. Fit with `fit_mixed_model` (REML, existing optimizer
fallback, existing random-effect structure). `E:L` is read directly by
name from `result.params["E:L"]` (the coefficient at `depth_z=0`, i.e.
mean depth, since `depth_z` is centered) — no contrast construction is
needed for this model.

### 1.2 Categorical depth-moderation model (Phase 1B)

```
y ~ E*L*R + C(depth, Sum) + log2_budget
    + E:C(depth, Sum) + L:C(depth, Sum) + R:C(depth, Sum)
    + E:L:C(depth, Sum) + L:R:C(depth, Sum)
```

`C(depth, Sum)` = patsy sum (deviation) coding, 5 levels
(`{1,2,3,4,6}`) → 4 non-redundant columns per term, named
`C(depth, Sum)[S.<level>]` by patsy (level order = sorted unique values
= `[1,2,3,4,6]`, so `[S.1],[S.2],[S.3],[S.4]` correspond to depths
1,2,3,4; depth 6 is the implicit sum-to-zero reference and is recovered
by construction, never assumed to be "the omitted category" for
interpretation — all depth-specific values are read off via explicit
contrasts (Section 2), never off a raw coefficient's reference-category
meaning). **No `E:R:C(depth, Sum)` or `E:L:R:C(depth, Sum)` term is
added** — per the task's explicit instruction, `E:L:R` (from `E*L*R`,
depth-invariant) is the only three-way term, so the depth-specific `E:L`
moderation this model can express is assumed constant across `R` by
construction of the formula, not by an additional averaging assumption
error.

### 1.3 Sample sizes note

The categorical model with 8 fixed-effect terms (several 4-df) has more
free fixed-effect parameters (33, confirmed in the Phase 0 sandbox check)
than the adopted production model (14). At ~100k eligible rows and 50
initialization groups this is not a data-sparsity concern; convergence
and singularity are still checked and reported per fit (Section 4), not
assumed.

---

## 2. Contrast definitions (fixed)

All contrasts are built as literal row-differences of the fitted
categorical model's own design matrix (via
`patsy.build_design_matrices([design_info], synthetic_df)`), never by
reading off a raw coefficient assuming a particular reference-category
meaning.

**Depth-specific E:L contrast at depth `d`, marginalized equally over
`R`** (Primary Question 5's per-depth building block):

```
row(E,L,R,d) := design row at (E,L,R,depth=d, log2_budget=<any fixed value>)
diffindiff(d, R) := row(1,1,R,d) - row(1,0,R,d) - row(0,1,R,d) + row(0,0,R,d)
contrast(d) := 0.5 * diffindiff(d, 0) + 0.5 * diffindiff(d, 1)
```

`log2_budget`'s fixed value is arbitrary and does not affect the
contrast (no term in the formula multiplies `log2_budget` by `E`, `L`,
or depth), confirmed structurally, not assumed — the runner asserts this
by computing `contrast(d)` at two different `log2_budget` values and
requiring bit-identical results before reporting.

`t_test(contrast(d).reshape(1,-1))` on the fitted `MixedLMResults` (or
`RegressionResultsWrapper` for the cluster-robust fit) gives estimate,
SE, 95% CI, and raw two-sided p-value directly from the model's own
covariance matrix — satisfying "pooled contrast variance uses the full
covariance matrix, not independent-term approximations."

**Pooled contrasts** (Primary Question 5): linear combinations of the
five `contrast(d)` row-vectors, combined *before* calling `t_test` (so
the resulting single `t_test` call uses the full covariance matrix for
the pooled quantity, not a post-hoc combination of five separate
variances):

```
equal_weight[d]       = 1/5                          for d in {1,2,3,4,6}
obs_weight[d]         = eligible_n_d / total_eligible_n
pooled_contrast(w)    = sum_d w[d] * contrast(d)
```

`eligible_n_d` = the categorical model's own eligible row count at depth
`d` (post zero-variance exclusion), read from the fitted data, not
assumed equal to the raw cell count. Reported explicitly per depth in
every output table.

---

## 3. Weighting definitions (fixed, restated for Section 2's grid)

- **Equal-depth weighting**: `1/5` per depth, testing "if every block
  count mattered equally regardless of how much data it contributes."
- **Observation-count weighting**: `eligible_n_d / total_eligible_n`,
  testing "the pooled estimate a complete-pooling model like the adopted
  one implicitly approximates." Stated explicitly in every output: this
  gives more influence to deeper block counts because deeper circuits
  have more matched quantum parameters per initialization (more rows per
  cell-set), not because deeper depths are more reliable.
- Neither weighting is claimed to reproduce the adopted mixed model's
  pooled `beta_EL` exactly (the adopted model's implicit weighting is
  neither of these — it is whatever weighting REML/GLS assigns given the
  full random-effects covariance structure). This is stated in the
  results record, not treated as a discrepancy to explain away.

---

## 4. Eligibility rule and model-failure rules (fixed)

- **Primary path** (Phases A-E, both datasets): identical to the
  production model — `build_h2h4_dataset(eo_df)` (single mode,
  `np.isfinite(SNR_est)` filter). No epsilon, no floor.
- **Include-zero path** (Phase F, original only): a separate function
  that starts from the *same* `eo_df`, and for rows with
  `zero_variance_flag == True`, asserts `mu_hat == 0` for every such row
  (`raise ValueError` naming the offending rows otherwise — this is a
  precondition check, not a silent skip), sets `SNR_est = 0.0`, and
  `y = arcsinh(0.0) = 0.0`. Every other row is untouched. This produces
  102,400 eligible rows (vs. 101,891 in the primary path).
- **Model-failure rule**: if `fit_mixed_model` returns
  `converged=False` or raises, the failure (optimizer, error message,
  attempted optimizers) is recorded in `model_diagnostics.json` under
  that specific (dataset, model, sensitivity-arm) key, and the runner
  **stops for that arm** (does not silently substitute a simpler
  formula or drop the arm from the output tables — the row is written
  with `converged=False` and null coefficient fields instead of being
  omitted). Every convergence warning captured via Python's warnings
  system during each fit is also recorded (count and message text) per
  fit.
- Mode filtering: every function in this package that accepts a
  dataframe asserts `df["analysis_mode"].unique() == ["finite_shot_end_to_end"]`
  (single value) before proceeding, raising otherwise — this is in
  addition to, not a replacement for, `build_h2h4_dataset`'s own guard,
  since several of this package's functions operate on data that has
  already been mode-filtered before `build_h2h4_dataset` is called.

---

## 5. Cluster-robust sensitivity (Phase 1E, fixed settings)

`statsmodels.formula.api.ols(categorical_formula, data=eligible_df).fit(
cov_type="cluster", cov_kwds={"groups": eligible_df["initialization_id"]})`.
Finite-cluster correction: statsmodels' default `cov_kwds` for
`cov_type="cluster"` applies the small-sample multiplier
`(n_clusters / (n_clusters - 1)) * ((n_obs - 1) / (n_obs - k))` unless
overridden — **no override is applied** (defaults used, documented
explicitly in the output manifest as `use_correction=True` [statsmodels
default], `df_correction=True` [default]). This mirrors the choice
already justified in `verification/h2_robustness_replication_plan.md`
Section 2.2(C) for the pooled cluster-robust check — same clustering
unit (`initialization_id`), same absence of a parametric variance-model
assumption, extended here to the categorical formula. Joint omnibus test
on this fit uses `wald_test_terms` identically to the mixed-model path
(Section 2's `t_test`/contrast machinery is dataset-agnostic — it only
requires a fitted results object exposing `.t_test` and a `design_info`
with matching columns, which both `MixedLMResults` and
`RegressionResultsWrapper` provide).

---

## 6. Inference methods summary (fixed)

| Model | Fit method | Purpose |
|---|---|---|
| A. Continuous `E:L:depth_z` | `fit_mixed_model` (REML) | linear depth-moderation diagnostic only |
| B. Categorical `C(depth,Sum)` | `fit_mixed_model` (REML) | primary depth-heterogeneity model; source of all contrasts in Sections 2-4 |
| C. Omnibus joint Wald | `wald_test_terms` on B's fit | "does one model support depth variation" (Primary Question 1) |
| D. Weighted pooled contrasts | `t_test` on B's fit | Primary Question 5 |
| E. Cluster-robust categorical | `smf.ols(...).fit(cov_type="cluster")` | Primary Question 3's cluster-robust arm |
| F. Include-zero categorical | same as B, on the include-zero dataset | Primary Question 3's include-zero arm |

No Holm or other multiplicity correction is applied to any of the above
— all are explicitly post-run/exploratory/diagnostic/sensitivity, per
the task's nonnegotiable constraints, and are never merged into the
original H1-H4 Holm family or presented as confirmatory.

---

## 7. Original-vs-replication comparison rule (fixed, Phase 2 deliverable)

For each depth `d`, given original estimate `e_o`/SE `s_o` and
replication estimate `e_r`/SE `s_r` (both from the categorical model's
depth-specific contrast, Section 2):

```
difference        = e_r - e_o
se_difference     = sqrt(s_o^2 + s_r^2)     # independent-sample approximation
ci_difference     = difference +/- 1.959963984540054 * se_difference
same_sign         = sign(e_o) == sign(e_r)
interval_overlap  = not (CI_r entirely above or entirely below CI_o)
```

Explicitly labeled in every output as **"a post-run approximate
comparison, not a confirmatory test"** — the independent-sample SE
formula assumes the two fits are independent (true, since original and
replication use disjoint seed namespaces and are never pooled) but does
not itself carry a joint-model guarantee the way a single combined-data
fit's contrast would.

**Depth pattern is called "replicated" only if, for at least 4 of the 5
depths, `same_sign` is true AND `interval_overlap` is true.** This
threshold (4/5) is fixed now, before the replication's categorical model
is fit in this package (the *pooled* replication result is already known
from the prior package, but the *depth-specific* replication pattern is
not). If fewer than 4/5 depths meet both conditions, the pattern is
reported as **"original and replication depth patterns disagree"** or
**"partially agree,"** using that exact language — never "replicated,"
never "confirmed."

---

## 8. Figure and table outputs (fixed)

- `paper/figures/fig11_h2_depth_heterogeneity.pdf` (+ `_preview.png`):
  two-panel. Panel (a): x=depth, y=E:L contrast (arcsinh scale), original
  and replication as distinct marker shapes + line styles, 95% CI
  whiskers, horizontal zero line, no embedded title. Panel (b): equal-
  weighted, observation-weighted, and adopted pooled `beta_EL` as three
  points with CIs (adopted point uses the existing Wald CI, not a
  contrast from this package's models). Source data: a single generated
  CSV (`results/h2_robustness/depth_heterogeneity/original_depth_contrasts.csv`
  + the replication and weighted-contrast CSVs) — the figure script
  performs no arithmetic beyond unit conversion/plotting.
- `paper/tables/h2_depth_heterogeneity.tex`: generated (not
  hand-transcribed) from `h2_depth_heterogeneity_summary.csv`, explicitly
  captioned as post-run/exploratory, not part of the confirmatory Table.

---

## 9. Manuscript interpretation rules (fixed, binding for Phase 6 editing)

- Never: "confirmed," "proven," "real mechanism," "model-independent,"
  "H2's mechanism is solid," "stable in sign across the reported
  sensitivity analyses," "a real, replicable phenomenon."
- The three sensitivity CIs that include zero (existing nested
  bootstrap, cluster-robust regression, independently implemented
  initialization-level resampling) are described as producing intervals
  that include zero — **not** described as "fully independent relaxations
  of every mixed-model assumption" (each relaxes a specific, named
  assumption; none is a universal check).
- The component decomposition (numerator/denominator, from the prior
  package) may be called "stable and directionally coherent" — not
  "solid" and not "a mechanism."
- The original H1-H4 confirmatory decisions, the prespecified Wald/Holm
  H2 rejection, and the existing n=443 bootstrap result are unchanged
  and are not re-litigated by this package.
- Depth-heterogeneity findings are reported as exploratory/post-run
  throughout — in the Methods subsection, the Results paragraphs, the
  table caption, and the figure caption.
- The replication's depth-specific pattern is only called "the same
  pattern" if Section 7's 4/5 rule is met by the *actual* fitted
  contrasts — this document does not pre-judge that outcome.

---

## 10. What this plan does not decide yet

Whether the continuous `E:L:depth_z` term is distinguishable from zero;
whether the categorical omnibus test rejects; the sign or magnitude of
any individual depth contrast in this package's own (re-)fit (the prior
package's separate-fit numbers are known, but this package's single-model
contrasts are a different statistical construction and are not assumed
to reproduce them exactly); whether cluster-robust or include-zero
sensitivity changes any sign; whether the replication's depth pattern
meets the 4/5 agreement rule. All of this is determined by running the
plan, not by writing it.
