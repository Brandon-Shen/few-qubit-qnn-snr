# H2 robustness and independent replication — frozen analysis plan

**Status: FROZEN before any new-analysis or replication result was inspected.**
This document is written and committed (or content-hashed, if committed
separately) before Phase 2's audit script is executed, before Phase 3's
decomposition models are fit, before Phase 4's robustness methods are run,
and before any replication data exists. Every method, threshold,
transformation, seed, iteration count, and decision rule below is fixed
*before* outcomes are known. If a later phase deviates from this plan, the
deviation and its reason are recorded in
`verification/h2_robustness_replication_results.md`, not silently absorbed
here.

This plan governs a new, clearly-separated package
(`scripts/`, `results/h2_robustness/`, `results/h2_replication_v1/`) that
investigates the H2 (`beta_EL`, `E:L` interaction) finding without touching
any original confirmatory data, config, or output. Nothing under
`results/production_confirmatory/`, `results/production_corrected_end_to_end/`,
`results/superseded_pooled/`, `configs/confirmatory.yaml`, or `paper/main.tex`
is modified by this work. Everything here is additive.

---

## 0. Why this package exists

The current H2 result is a positive, Holm-significant `E:L` interaction on
`asinh(SNR_est)` under the prespecified Wald/Holm mixed-model analysis, but
four properties of the existing analysis warrant a dedicated robustness and
replication pass before that result is treated as settled:

1. **Zero-variance exclusions are not random with respect to the design.**
   All 509 excluded end-to-end cells (of 102,400) occur at `L=0`; zero at
   `L=1`. If exclusion probability depends on the true effect being
   estimated, complete-case analysis is not guaranteed unbiased for the
   `E:L` contrast.
2. **Wald/Holm rejects; the nested percentile bootstrap does not
   corroborate.** At the current best achieved bootstrap scale (`n=443`,
   `results/production_corrected_end_to_end/`), the `E:L` percentile
   interval is `[-0.018024, 0.065688]` — includes zero — while the Wald CI
   is `[0.010729, 0.039263]`. This disagreement between exactly the two
   methods most people would treat as default choices is reported, not
   explained away, in the existing record.
3. **Residual variance is systematically structured** by block count
   (`D`; SD 0.659 at `D=1` down to 0.276 at `D=6`) and by shot budget
   (`B`; SD 0.301 at `B=250` up to 0.513 at `B=2000`) — the Wald SEs assume
   homoscedasticity that the data do not have.
4. **The ratio estimand (`SNR_est = |mean| / SD`) can produce an
   interaction from the numerator, the denominator, or their
   covariance**, and the existing analysis has never decomposed which.

None of this is presented here as evidence that H2 is wrong. It is
presented as exactly the set of open questions a careful reviewer would
raise, and this package exists to answer them honestly, including the
possibility that the answer is "H2 does not survive" or "inconclusive."

---

## 1. Repository audit (Phase 1 findings)

### 1.1 Raw finite-shot replicate-level files (frozen, original, immutable)

| File | Rows | SHA-256 |
|---|---:|---|
| `results/production_confirmatory/raw/exact.parquet` | 25,600 | `77e54bed863de79be0d1ebb4937f015fe29a1b1cb5d58e0f216f3acd4b9bb542` |
| `results/production_confirmatory/raw/finite_shot_end_to_end.parquet` | 3,072,000 | `22b5e761f461c6bfde7a60a4efa7ac13bc59ae003488be84d2f0c1e57ddb7f39` |
| `results/production_confirmatory/raw/finite_shot_conditional.parquet` | 3,072,000 | `b15b19088d22a0429f48158cdee5ee3caec52f6819815579b3e6aed189afe413` |

Schema: `qnn_snr/schema.py::REQUIRED_COLUMNS` (one row per replicate; key
identity columns `analysis_mode, configuration_id, E, L, R, depth, budget,
initialization_id, parameter_id, replicate_id`; per-replicate signed
gradient in `gradient_hat`; matched deterministic ground truth in
`exact_gradient`).

### 1.2 Pointwise aggregated file (frozen, original, immutable)

| File | Rows | SHA-256 |
|---|---:|---|
| `results/production_confirmatory/pointwise_gradient_statistics.parquet` | 204,800 (both finite-shot modes) | `99a4decf8597c9fcc5a61a8e59075d34e1cf6668714ee19e38b39258e15d1342` |

End-to-end mode subset: 102,400 cells (`analysis_mode=="finite_shot_end_to_end"`).

### 1.3 Current H2–H4 model-fitting code

- `qnn_snr/stats/models.py::H2_H4_FORMULA` =
  `"y ~ E*L*R + depth_z + log2_budget + E:depth_z + L:depth_z + R:depth_z + L:R:depth_z"`,
  `y = arcsinh(SNR_est)`.
- Random effects: `groups=initialization_id` (random intercept, i.e. one
  variance component per initialization), plus a variance component
  `vc_formula={"param": "0 + C(nested_param_id)"}` where
  `nested_param_id = initialization_id__depth__parameter_id` (ASSUMPTION
  A20: a parameter is only "the same" within one initialization *and* one
  depth, since each depth draws an independent `theta`).
- Fit via `statsmodels` `MixedLM`, REML, optimizer fallback order
  `["lbfgs","bfgs","cg","powell","nm"]` (`qnn_snr/stats/models.py::_fit_with_fallback`).
- `build_h2h4_dataset()` refuses mixed-mode input unless `pool_modes=True`
  is passed explicitly (the mode-pooling-bug guard, `verification/mode_pooling_guard.md`).

### 1.4 Current zero-variance exclusion code

`qnn_snr/stats/pointwise.py`:
- `ZERO_VARIANCE_TOL = 0.0` — **exact** zero only, `ddof=1` sample
  variance across the `R=30` replicates in a cell. No epsilon is added
  anywhere in production code.
- If `shot_variance <= 0.0` (i.e. `== 0.0`, since variance cannot be
  negative): `SNR_est = inf` if `mu_hat != 0`, else `nan`.
- `build_h2h4_dataset()` drops all non-finite `SNR_est` rows
  (`np.isfinite(d["SNR_est"])` filter) — this is the *only* exclusion
  mechanism feeding the confirmatory model
  (`verification/run_zero_variance_audit.py` already confirmed zero rows
  are non-finite for any reason other than `zero_variance_flag`).

### 1.5 Current production sample sizes and zero-variance breakdown

Reproduced directly from the frozen pointwise file (independently
re-verified in Phase 2, not assumed from prior `.md` records):

- End-to-end total pointwise cells: **102,400** (`50` inits × `8` configs ×
  `5` depths × `4` budgets × `24` distinct `parameter_id` per depth-set,
  irregular because `parameter_id` count scales with `depth × n_qubits`).
- Zero-variance excluded: **509** (0.497%). `n_obs` in the adopted fit:
  **101,891** (matches `verification/end_to_end_model_diagnostics.md`).
- **By `L`: 509/509 at `L=0` (51,200 cells), 0/0 at `L=1` (51,200 cells) —
  100% confinement to `L=0`, reconfirmed independently in this pass
  (see §1.5.1).**
- By `E`: 381 at `E=0`, 128 at `E=1` (of 51,200 each).
- By `R`: 306 at `R=0`, 203 at `R=1` (of 51,200 each).
- By depth: `D=1`: 165/6,400 (2.58%); `D=2`: 84/12,800 (0.66%); `D=3`:
  79/19,200 (0.41%); `D=4`: 79/25,600 (0.31%); `D=6`: 102/38,400 (0.27%).
- By budget: `B=250`: 219/25,600 (0.86%); `B=500`: 141/25,600 (0.55%);
  `B=1000`: 82/25,600 (0.32%); `B=2000`: 67/25,600 (0.26%) — monotonically
  decreasing with budget.

#### 1.5.1 Why exclusion is confined to `L=0`, mechanistically (context, not new claim)

`L=1` is the local (normalized TFIM-energy) cost; `L=0` is the global
(state-infidelity) cost. This package does not attempt to resolve *why*
the estimator's finite-shot variance is never exactly zero under the local
cost — that mechanism is out of scope here (it is a property of the cost
function's shot-noise sensitivity, not of the exclusion rule) — but the
fact itself is directly relevant to bias risk: if `L=0`'s finite-replicate
variance estimator has a nonzero probability mass exactly at zero (a
genuine floor/discreteness effect at `R=30`) while `L=1`'s does not, then
complete-case exclusion at `L=0` only removes the *low-signal* tail of the
`L=0` distribution, which could inflate the apparent `L=0` versus `L=1`
contrast in a specific, checkable direction (Phase 4F asks whether varying
the treatment of these cells moves `beta_EL` toward or away from zero).

### 1.6 Current bootstrap structure

`qnn_snr/stats/bootstrap.py::run_h2h4_bootstrap`:
- **Outer resample**: draw `n` = (number of unique `initialization_id`)
  initialization IDs with replacement from the *raw replicate-level* data;
  each drawn copy keeps its full matched factorial structure and is
  relabeled with a unique synthetic `initialization_id` so repeated draws
  of the same real initialization are never conflated
  (`_relabel_outer_resample`).
- **Inner resample**: within every (mode, config, depth, budget, init-copy,
  parameter) cell, resample the `R` replicate `gradient_hat` values with
  replacement (`_inner_resample_replicates`).
- Recompute `pointwise_statistics()` on the doubly-resampled data, then
  `build_h2h4_dataset()` (same non-finite-`SNR_est` filter as production)
  and refit `H2_H4_FORMULA`.
- **Gap this package fixes**: `build_h2h4_dataset()`'s filter is applied
  silently inside each bootstrap iteration — the *number* of cells that
  become zero-variance within a given resample is not currently recorded
  per iteration anywhere. Phase 4B fixes this by wrapping the same
  resampling primitives in a new function that logs it explicitly.
- Achieved production scale for the adopted end-to-end-only bootstrap:
  **n=443** successful iterations (0 failed), median `E:L` = 0.023685, 95%
  percentile CI = `[-0.018024, 0.065688]` (`results/production_corrected_end_to_end/`).
- Empirically measured cost on this machine: one `fit_h2h4_model` call on
  the full end-to-end dataset ≈ **31.8s** (`verification/qmi_qip_analysis_inputs.md`
  §3, reconfirmed by `verification/run_loo_initialization.py`'s per-fit
  timings on a ~2%-smaller dataset). This number directly drives the
  iteration-count decisions in §4 below — they are chosen for feasibility
  in this session, not for effect on significance.

### 1.7 Deterministic seed utilities

`qnn_snr/seeds.py::derive_seed(seed_root, stream, *ids)` = first 8 bytes of
`SHA256(f"{seed_root}|{stream}|{'|'.join(str(i) for i in ids)}")`, taken
mod `2**31 - 1`. Called at each production site with a **string-literal**
stream name (`"init_theta"`, `"init_classical"`, `"shots"`,
`"pilot_init_theta"`, `"pilot_init_classical"`, `"pilot_shots"`) — the
`seed_streams: {initialization:1, shot_sampling:2, ...}` integers in
`ExperimentConfig` are recorded into `run_manifest.json` for documentation
but are **not** consumed by `derive_seed` calls; the stream identity comes
entirely from the string literal at the call site.

**Consequence for replication seed design (binding decision, see §6.1):**
because `replicate_id` cycles `0..R-1` and the `"shots"` stream string is
hardcoded in `qnn_snr/replicate.py`, a replication run that reused
`seed_root=20260726` (production) would produce **bit-identical** shot
draws to the original data for every `(init_id, depth, config_id, mode,
budget, replicate_id)` combination with `replicate_id < 30` — not an
independent replication at all for those cells. The only way to guarantee
zero seed overlap without editing `qnn_snr/replicate.py` (which is
production code feeding the immutable original data path) is to use a
**different `seed_root`**. §6.1 fixes this value now.

### 1.8 Production configuration

`configs/confirmatory.yaml` (config_hash `bb1fe393a979c8d2`, frozen copy at
`results/production_confirmatory/config_used.confirmatory.yaml`): 4 qubits,
TFIM `J=1.0, h=0.5`; depths `[1,2,3,4,6]`; budgets `[250,500,1000,2000]`;
`n_initializations=50`; `replicates=30`; 8 configurations; gradient modes
`[statevector_exact, finite_shot_conditional, finite_shot_end_to_end]`;
`seed_root=20260726`.

### 1.9 Existing verification records and regression tests consulted

`verification/mode_pooling_guard.md`, `confirmatory_numbers_adopted.md`,
`zero_variance_exclusion_audit.md`, `run_zero_variance_audit.py`,
`end_to_end_model_diagnostics.md`, `run_model_diagnostics.py`,
`run_loo_initialization.py`, `bootstrap_end_to_end_extended.md`,
`qmi_qip_analysis_inputs.md`; `tests/test_bootstrap.py`,
`tests/test_models.py`, `tests/test_pointwise.py` (existing coverage of
the resampling primitives, model-fitting invariants, and zero-variance
flagging — this package's new tests target the *new* code only, not
re-tests of these).

### 1.10 Smoke-test outputs that must not be confused with production results

`results/smoke_test/` (both `results_smoke_20260727/` and
`bootstrap_timing_probe_NOT_REAL_RESULTS/`) and `configs/smoke.yaml`,
`configs/dev.yaml` — explicitly excluded from every analysis in this
package. No script in `scripts/` reads from `results/smoke_test/` or
`configs/{smoke,dev}.yaml`.

---

## 2. Planned robustness analyses on the *original* data (Phase 3–4)

All of the below operate only on the already-frozen files in §1.1–1.2. No
new quantum simulation is run for this section.

### 2.1 Phase 3 — numerator/denominator decomposition

For the end-to-end mode only (primary), construct per-cell:

| # | Quantity | Definition | Role |
|---|---|---|---|
| 1 | signed mean | `mu_hat` (already in pointwise file) | diagnostic |
| 2 | abs mean | `\|mu_hat\|` | diagnostic |
| 3 | `asinh(abs mean)` | stable transform, same family as H1's `a` | **primary numerator model response** |
| 4 | shot variance | `shot_variance` (already in pointwise file) | diagnostic |
| 5 | shot SD | `shot_sd` (already in pointwise file) | diagnostic |
| 6 | `log(shot variance)` | defined only where `shot_variance>0` (i.e. the same eligible set as the SNR model) | **primary denominator model response** |
| 7 | sign agreement | `sign(mu_hat)==sign(exact_gradient)` (already in pointwise file) | descriptive only (binary; not modeled with `MixedLM`) |
| 8 | signed bias | `mu_hat - exact_gradient` (already in pointwise file) | diagnostic |
| 9 | absolute bias | `\|bias\|` (already in pointwise file) | diagnostic |
| 10 | `SNR_est` | production quantity | reference (already modeled, not refit here) |
| 11 | `SNR_exact` | `\|exact_gradient\| / shot_sd` (already in pointwise file, undefined for zero-variance cells identically to `SNR_est`) | diagnostic |

**Primary models** (fit with `fit_mixed_model`, identical `H2_H4_FORMULA`
fixed-effect structure, same random-effect structure, on the same eligible
row set as the adopted SNR model — i.e. rows with `shot_variance>0`, so the
numerator/denominator models and the SNR model are directly comparable on
n_obs):

- **Numerator model**: `asinh(|mu_hat|) ~ E*L*R + depth_z + log2_budget + ... `
- **Denominator model**: `log(shot_sd) ~ E*L*R + depth_z + log2_budget + ...`

These are explicitly **diagnostic / mechanism-explaining, not a
replacement for the SNR estimand.** The summary table (§9 output
`h2_decomposition_summary.csv`) reports, for each of the two primary
models plus the reference SNR model: `E:L` coefficient, SE, 95% Wald CI,
sign, `n_obs`, whether zero values required special treatment, and a
`role` column (`primary` for numerator/denominator, `reference` for SNR).

Interpretation rule (fixed now): if the numerator model's `E:L` and the
denominator model's `E:L` point in directions that *both* increase
`SNR_est` under `E=L=1` relative to the marginal effects, both numerator
and denominator contribute; if only one coefficient is distinguishable
from zero at the same nominal `alpha=0.05` (unadjusted, since this is
diagnostic, not confirmatory), that one is reported as the dominant
driver, with the explicit caveat that "dominant" here means "detectable at
this sample size," not "the other is exactly zero."

### 2.2 Phase 4 — robust inference on the original data

**(A) Baseline.** Reproduce `fit_h2h4_model` exactly (Phase 2 script) —
this is the number every other method in this section is compared against.

**(B) Initialization-level resampling with explicit zero-variance
logging.** New function (not a modification of
`qnn_snr/stats/bootstrap.py::run_h2h4_bootstrap`) that performs the
identical outer-resample → inner-resample → `pointwise_statistics()`
pipeline, but records, **for every iteration**, before the
`build_h2h4_dataset()` filter: total resampled cells, count with
`zero_variance_flag`, count with non-finite `SNR_est` not explained by
`zero_variance_flag` (should always be 0, checked), and whether the fit
converged. Failed fits and iterations with `<90%` of cells eligible are
recorded, not dropped from the report (only from the coefficient
percentile calculation, exactly as the existing `min_success_fraction`
convention already does — but now the exclusion is visible).
- **Iterations: n=200, seed 900001** (new, non-overlapping value, distinct
  from the production bootstrap seed `12345` and from the replication seed
  namespace in §3). Chosen before running: at ≈32–40s per pointwise
  recompute + refit (recompute is cheap relative to the fit; the fit
  dominates), n=200 is projected at roughly 100–140 minutes, run in the
  background with per-iteration checkpointing
  (`results/h2_robustness/robust_inference/init_resample_checkpoint.parquet`)
  so it is resumable and inspectable at any partial count. **This n is
  fixed now and will not be raised or lowered after inspecting how close
  the resulting CI is to including zero.**

**(C) Heteroscedasticity-aware alternative: cluster-robust regression at
the initialization level.** Justification: the mixed model's Wald SEs
assume the two modeled variance components are the *entire* correlation
structure and that residual variance is homoscedastic; §1.6's diagnostics
show it is not (systematic by `D` and `B`). Refitting the identical
fixed-effect formula (`H2_H4_FORMULA`, same eligible rows) as an OLS via
`statsmodels.formula.api.ols(...).fit(cov_type="cluster",
cov_kwds={"groups": initialization_id})` gives heteroscedasticity- **and**
within-initialization-correlation-robust standard errors without assuming
a specific parametric variance model, because clustering by
`initialization_id` absorbs *all* correlation among rows sharing an
initialization — the same unit the mixed model's random intercept and
nested variance component are built to capture. This is **not** presented
as equivalent to the mixed model (it drops the explicit nested-parameter
variance decomposition and the shrinkage/partial-pooling behavior of
`MixedLM`); it is presented as a check of whether the Wald conclusion
survives dropping the homoscedasticity assumption entirely, holding the
point estimate's defining equation (the same fixed-effect formula) fixed.
Single fit, no resampling, so this method costs seconds, not hours — its
cost is not the reason it was chosen; a wild cluster bootstrap was
considered and rejected as the primary alternative here because each
iteration would require the same ~32s-per-fit cost as (B) with no clear
gain in this design over the initialization-level resampling already
planned in (B), not because it is invalid.

**(D) Depth- and budget-stratified diagnostics.** Refit `H2_H4_FORMULA`
(dropping the now-inapplicable `depth_z`/`log2_budget` main effects and
their interactions where a stratum fixes that variable) separately for
each of the 5 depths, and, if any stratum retains enough eligible cells
to fit without a new singularity, for a coarser budget split
(`B<=500` vs `B>500`, chosen now, before seeing results, as the only
budget split tested, since finer splits would shrink `n` per stratum
below what nested random effects with 50 groups can support reliably).
Reported explicitly as **exploratory diagnostics**, not additional
confirmatory tests — no Holm correction is applied because these are not
part of the original prespecified family, and this package does not
promote a "best" stratum.

**(E) Leave-one-initialization-out, extended.** Reuse
`verification/run_loo_initialization.py`'s checkpointed output directly
(it already covers all 50 deletions) and **extend** it in this package
with: (i) the same computation run on the *numerator* and *denominator*
component models from §2.1, so influence can be attributed to the
numerator, denominator, or both; (ii) explicit original-SE-unit movement
for all three (SNR, numerator, denominator) per deletion, reported per
initialization, not just the max. No initialization is removed from the
primary analysis.

**(F) Zero-variance sensitivity — at least two treatments beyond
complete-case exclusion, plus a predefined floor grid:**

1. **Separate numerator/denominator modeling without ever forming `SNR`
   when `shot_variance==0`** — this is exactly what §2.1's two primary
   models already do (they use `asinh(|mu_hat|)` and `log(shot_sd)`
   directly; the denominator model's eligible set still excludes
   `shot_variance==0` because `log(0)` is undefined, but no ratio is ever
   formed and no epsilon is added — the exclusion is on a different,
   more defensible ground: an undefined log, not an infinite ratio).
2. **Treat zero empirical variance as a finite-replicate measurement
   outcome**: fit a model of `P(zero_variance_flag) ~ E*L*R + depth_z +
   log2_budget + ...` (logistic, `statsmodels.formula.api.logit`, no
   random effects — a per-initialization random-intercept GLMM is not
   attempted here because `statsmodels` does not provide a stable REML
   mixed logistic fit and a from-scratch implementation is out of scope
   for this pass; this limitation is stated explicitly in the results
   record, not hidden). This directly tests whether the *probability* of
   landing exactly on zero variance itself depends on `E:L`, which is the
   more precise version of "is exclusion informative."
3. **Predefined variance-floor sensitivity grid** (fixed now, run over the
   *entire* grid, full coefficient trajectory reported, no single floor
   selected as "the" answer):
   `{0 (baseline, no floor / complete-case), 1e-12, 6.227451072756091e-11
   (= the minimum nonzero `shot_variance` actually observed in the
   end-to-end data), 1e-9, 8.246974048968847e-07 (empirical 1st percentile
   of nonzero variance), 1.0579851428657802e-05 (empirical 5th
   percentile), 1e-3 (≈ empirical median nonzero variance,
   0.0010416128709740018)}`. For each floor value `f>0`, cells with
   `shot_variance==0` are refloored to `shot_variance=f` (and
   `SNR_est=|mu_hat|/sqrt(f)` recomputed) **only** in this labeled
   sensitivity path — never in `results/h2_robustness/original_data_audit/`
   or anywhere touching the production files.

If a statistically principled hierarchical/Bayesian repeated-replicate
model (candidate 3 in the task's own list) is not implemented, the reason
will be stated plainly in the results record (most likely: no existing
dependency in `pyproject.toml`/`requirements-lock.txt` supports a
hierarchical likelihood model for this response shape without introducing
a new, unvetted dependency mid-analysis, which this plan explicitly
declines to do silently).

---

## 3. Planned independent replication (Phase 5)

### 3.1 Seed namespace (binding decision)

New `seed_root` derived deterministically and documented, **not equal to**
`20260726` (production), `dev`'s or `smoke`'s roots, or any seed used in
§2.2(B)/(C):

```
seed_root = int.from_bytes(
    hashlib.sha256(b"h2_independent_replication_v1").digest()[:4], "big"
)
```

Computed once, on this machine, before any config was written:
**`seed_root = 3872531887`**. This is a fixed integer hardcoded into
`configs/h2_replication_v1.yaml` (never recomputed at runtime, so the
config is self-contained and auditable), and is checked against the three
existing roots actually present in the repo today
(`configs/confirmatory.yaml`, `configs/dev.yaml`, and `configs/smoke.yaml`
all use `seed_root: 20260726`) — `3872531887 != 20260726`, confirmed.
Because `derive_seed`'s entire
output depends on the SHA-256 of `f"{seed_root}|{stream}|{ids}"`, changing
`seed_root` changes every single derived seed relative to production —
there is no `(stream, ids)` combination for which production and
replication coincide. This is verified by a new regression test (Phase 8:
`test_replication_seed_root_differs_from_all_known_roots`) that checks the
computed root against the production, dev, and smoke roots and asserts
inequality, plus a spot-check that `derive_seed` output differs for a
sample of matched `(stream, ids)` tuples between the two roots.

### 3.2 Design

- Same 8 E/L/R configurations, same 5 depths `[1,2,3,4,6]`, same 4 budgets
  `[250,500,1000,2000]` — unchanged from production, so the replication is
  testing the same estimand under new randomness, not a different design.
- `n_initializations`: **50** (matches original; not reduced).
- End-to-end mode is primary; conditional mode is **not generated** for
  the replication (optional per the task, and generating it would
  roughly double the wall-clock cost in §3.3 for a mode this package
  treats as diagnostic-only even in the original data). `statevector_exact`
  **is** generated (cheap, needed for `exact_gradient` matching and the
  numerator/denominator decomposition on replication data).
- Handling rules (zero-variance flagging, exclusion, transforms) are
  byte-identical code paths to production (`qnn_snr.stats.pointwise`,
  `qnn_snr.stats.models`) — no special-casing by `L`.
- Original and replication datasets are **never pooled** for the primary
  replication comparison (a hard rule enforced by a Phase 8 test that
  checks the two output roots never share a `git_commit`+`config_hash`
  combination in a single downstream table meant to be a "pooled" fit).

### 3.3 Resource estimate (pilot-benchmarked, not guessed)

A real pilot benchmark (§3.3.1) was run on this machine before writing the
numbers below.

**Full design at `R_rep=300`** (10x production's `R_rep=30`), end-to-end
mode only, `N_init=50`, all 5 depths, all 4 budgets, all 8 configs:

- Total circuit evaluations: scales linearly with `R_rep` for the
  finite-shot generation step. Production's end-to-end generation (`R=30`)
  took **~26 minutes** wall-clock on this machine
  (`run_manifest.json` step timestamps: 03:51:33→04:17:38). At `R=300`,
  linear projection: **~260 minutes (≈4.3 hours)**.
- `generate-exact` (deterministic, `R`-independent): <1 minute (unchanged
  from production).
- Model fitting (`fit`): unaffected by `R` in cost (~2 minutes, matches
  production `aggregate`/`fit` step spacing).
- Disk: raw end-to-end parquet scales ~linearly with `R` from production's
  20MB at `R=30` → **≈200MB at `R=300`**. Pointwise file size is
  `R`-independent (same cell count, ~17MB).
- Memory: raw generation is streamed per-cell in `qnn_snr/replicate.py`
  (no evidence of `R`-dependent peak-memory blowup in production logs);
  the aggregation step (`pointwise_statistics`) processes one cell's `R`
  replicates at a time, so peak memory is also not expected to scale
  materially with `R`. Confirmed empirically, not assumed, in §3.3.1.

**This is a ~4.3-hour, single-mode generation job before any
fitting/bootstrap**, on top of whatever the replication's own robustness
checks (§4) cost. This is disclosed here, before Phase 6 execution, for an
explicit go/no-go decision — see §3.4.

#### 3.3.1 Pilot benchmark (actually executed, not estimated)

A pilot benchmark generating a small but real slice (1 configuration, 1
depth, 2 initializations, `R=20` replicates, end-to-end mode) is run and
timed under the replication seed root, writing to a disposable path
(`results/h2_replication_v1/config/_pilot_benchmark/`, not part of the
staged output tree) purely to calibrate the per-replicate wall-clock and
peak-RSS figures above. This is *not* replication data (wrong
initialization count, wrong configuration coverage, will not be reused for
any reported statistic) and is deleted or clearly marked disposable after
timing is recorded. Results of this benchmark are recorded in
`results/h2_robustness/replication_design/pilot_benchmark.json` and used
only to sanity-check the linear projection above.

### 3.4 Staged design (fixed now; expansion rule does not depend on significance)

Given the ~4.3-hour cost of a full `R_rep=300` single-mode generation, and
that this session's compute budget for a single uninterrupted job is
finite and unverified in advance, the replication is staged:

- **Stage 0 (pilot, §3.3.1)**: already scoped above, run first,
  unconditionally.
- **Stage 1 (fixed first-stage replication)**: full 8×5×4×50 design at
  **`R_rep=30`** (matching production's replicate count exactly, so
  Stage 1 is the cleanest apples-to-apples independent replication of the
  *exact* original design at a cost close to production's own generation
  time, ≈26 minutes projected). This is the **primary replication
  analysis** reported in Phase 7 unless Stage 2 is triggered and
  completes.
- **Predefined expansion rule to Stage 2 (`R_rep=300`)**: triggered **only**
  by one or both of the following, decided before Stage 1 results are
  inspected:
  (a) Stage 1's zero-variance exclusion rate at `L=0` differs from
  production's 0.995% (509/51,200) by more than a factor of 2 in either
  direction (a signal that `R_rep=30` is too coarse to trust at this
  seed), **or**
  (b) Stage 1 completes with more than 50% of the session's remaining
  compute-time budget unused, as a feasibility (not significance)
  criterion.
  **The expansion rule explicitly excludes** "the Stage 1 CI includes
  zero" or "the Stage 1 point estimate has the wrong sign" as triggers —
  those are the two significance-adjacent outcomes replication is
  supposed to test, not reasons to collect more data.
- **Final target**: Stage 2, if triggered, targets `R_rep=300` but a
  partial completion (checkpointed, resumable) is reported honestly as
  "Stage 2, `R_rep=<achieved>`," never silently presented as the full
  target.

---

## 4. Planned exclusion, failure, and transformation rules (binding, repeated from above for a single-page reference)

- No epsilon added to any zero variance in any primary or robustness
  output. Epsilon/floor treatment exists **only** in the labeled §2.2(F.3)
  sensitivity grid.
- Every zero-variance cell, every failed fit, every non-convergent
  optimizer attempt, and every convergence warning is written to a
  machine-readable diagnostics file in every phase — never silently
  dropped, never silently absorbed into a summary statistic without a
  paired count column.
- `finite_shot_end_to_end` and `finite_shot_conditional` are never pooled
  in any model in this package; every function that could receive
  mixed-mode data reuses or mirrors `build_h2h4_dataset`'s explicit guard.
- Transformations used: `arcsinh(SNR_est)` (production, unchanged),
  `arcsinh(|mu_hat|)` (numerator model, §2.1), `log(shot_sd)` /
  `log(shot_variance)` where strictly positive (denominator model, §2.1),
  logistic link for `P(zero_variance_flag)` (§2.2 F.2). No other
  transformation is introduced.

---

## 5. Primary vs. secondary outputs

**Primary** (directly answer the four questions in the task's PRIMARY GOAL):
- `results/h2_robustness/original_data_audit/h2_audit_summary.md` (Phase 2)
- `results/h2_robustness/decomposition/h2_decomposition_summary.csv` (Phase 3)
- `results/h2_robustness/robust_inference/h2_robust_inference_summary.csv` (Phase 4, methods A–C)
- `results/h2_replication_v1/tables/original_vs_replication.csv` (Phase 7)

**Secondary / diagnostic** (inform interpretation, not confirmatory):
- Depth/budget-stratified diagnostics (§2.2 D)
- Extended leave-one-out (§2.2 E)
- Zero-variance sensitivity grid and logistic model (§2.2 F)
- All figures under `results/h2_robustness/*/figures/`

---

## 6. Decision rules for interpreting replication (fixed before any replication data exists)

Computed automatically from the Stage 1 (or Stage 2, if triggered) Wald
fit and compared against the original end-to-end Wald fit
(`beta_EL=0.024995843985971582`, `SE=0.007279`, 95% CI
`[0.010729, 0.039263]`):

Let `delta_se = (replication_estimate - 0.024995843985971582) / 0.007279`
(movement in **original**-SE units) and `overlap` = boolean, whether the
replication's own 95% Wald CI overlaps `[0.010729, 0.039263]`.

- **"Direction and magnitude replicated"**: `sign(replication_estimate) ==
  sign(original_estimate)` AND `overlap == True` AND `|delta_se| <= 2`.
- **"Direction replicated but magnitude uncertain"**: same sign as
  original, but `overlap == False` OR `|delta_se| > 2` OR the
  replication's own CI width exceeds 3x the original CI width (too wide to
  pin magnitude even though the point estimate agrees in sign).
- **"Inconclusive"**: the replication's own 95% CI includes zero
  (regardless of point-estimate sign), or the replication's eligible
  `n_obs` fell more than 20% below the original's 101,891 for reasons
  other than the deliberate `R_rep=30` vs `R_rep=30` match (i.e. an
  unexpected data-quality shortfall), or Stage 1 failed to converge and
  Stage 2 was not run.
- **"Did not replicate"**: `sign(replication_estimate) !=
  sign(original_estimate)` AND (the replication's own CI excludes zero OR
  `|delta_se| > 2`) — a confidently opposite-sign or grossly discrepant
  result.

`"confirmed"` is never used as a label in this package's outputs,
regardless of which category above is reached, per the task's explicit
instruction.

---

## 7. What this plan does *not* decide yet

This plan fixes methodology, not results. It does not state, imply, or
assume: whether H2 will survive robust inference; whether the replication
will land in any particular category in §6; whether the zero-variance
floor grid in §2.2(F.3) will move `beta_EL` toward or away from
significance at any point on the grid; or whether Stage 2 will be
triggered. All of that is determined by running the plan, not by writing
it.

---

## 8. File/hash freeze record

This plan is committed to git immediately after being written, before
Phase 2's script is executed. The commit hash containing this file is the
freeze point; any git history after that commit that touches
`scripts/run_h2_zero_variance_audit.py`, `results/h2_robustness/`, or
`results/h2_replication_v1/` postdates this freeze by construction.
