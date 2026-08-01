# H2 depth-heterogeneity analysis — results

**Status: complete.** Governing plan: `verification/h2_depth_heterogeneity_plan.md`
(frozen at commit `87a46d4`, before any coefficient below was inspected).
Explicitly post-run / exploratory / diagnostic / sensitivity throughout —
no Holm correction applied anywhere in this document, and none of it
changes the original H1-H4 confirmatory decisions or the prespecified H2
Wald/Holm rejection (`beta_EL = 0.024995843985971582`, rejected).

No original production data, replication raw/pointwise data, or config
was modified. All new code is `qnn_snr/stats/depth_heterogeneity.py` +
`scripts/run_h2_depth_heterogeneity.py`; all new outputs are under
`results/h2_robustness/depth_heterogeneity/` and
`results/h2_replication_v1/depth_heterogeneity/`.

---

## 1. Mixed-model findings (primary, complete-case eligibility)

### 1.1 Continuous depth-moderation model

`y ~ E*L*R + depth_z + log2_budget + E:depth_z + L:depth_z + R:depth_z + E:L:depth_z + L:R:depth_z`

| dataset | `E:L` (at mean depth) | `E:L:depth_z` | converged |
|---|---|---|:-:|
| Original | 0.011486, CI [-0.003874, 0.026845] (includes zero) | **0.024952, CI [0.014438, 0.035466]** (excludes zero) | Yes, not singular |
| Replication | see `results/h2_replication_v1/depth_heterogeneity/replication_continuous_model.csv` | | Yes, not singular |

**Interpretation (linear depth-moderation diagnostic only)**: in the
original data, the `E:L` effect *at the mean depth* is not
distinguishable from zero, but its *linear trend across depth* is
strongly distinguishable from zero. This already indicates the pooled
model's single `E:L` coefficient is not representative of the effect at
any specific depth — it averages over a real depth-dependent trend.

### 1.2 Categorical depth-moderation model — omnibus test

`wald_test_terms` joint Wald chi-square on all four `E:L:C(depth, Sum)` coefficients:

| dataset | statistic | df | p |
|---|---:|---:|---:|
| Original | 154.045 | 4 | **2.76e-32** |
| Replication | 37.767 | 4 | **1.25e-07** |

**Primary Question 1 (does a single model support depth-varying E:L?):
under the matched mixed model, yes, in both datasets independently**, by
a wide margin — qualitatively different from, and statistically stronger
than, the prior package's five independent per-depth fits, because it
tests the joint hypothesis in one model with one covariance matrix rather
than eyeballing five separate confidence intervals. **This is not
corroborated by the cluster-robust version of the same omnibus test**
(Section 2): chi2=6.706, p=0.152 (original); chi2=2.793, p=0.593
(replication) — neither rejects. This is the depth-heterogeneity
analogue of the pooled-`E:L` pattern already established in the prior
package (mixed-model Wald rejects, cluster-robust does not): **the
evidence for a single model supporting depth-varying `E:L` is real under
the mixed model's assumptions and does not survive relaxing them.**

**Primary Question 2 (continuous vs. categorical): both treatments
agree** that depth moderates `E:L` in the original data (continuous:
`E:L:depth_z` CI excludes zero; categorical: omnibus p=2.76e-32). The
categorical model additionally reveals that the depth-dependence is
**not monotonic** in a way a single linear `depth_z` slope can fully
capture: depth-specific estimates go -0.082 (D=1) → -0.118 (D=2) → +0.093
(D=3) → +0.037 (D=4) → +0.019 (D=6) — the magnitude decreases *within*
each sign region as depth increases, not a simple straight line.

### 1.3 Categorical depth-specific contrasts (original)

| depth | estimate | 95% CI | n_obs eligible | n_zero_variance |
|---:|---:|---|---:|---:|
| 1 | -0.082264 | [-0.122937, -0.041592] | 6,235 | 165 |
| 2 | **-0.117716** | **[-0.146141, -0.089291]** | 12,716 | 84 |
| 3 | +0.092819 | [0.069647, 0.115990] | 19,121 | 79 |
| 4 | +0.037340 | [0.017284, 0.057397] | 25,521 | 79 |
| 6 | +0.019268 | [0.002896, 0.035640] | 38,298 | 102 |

**Every single depth's CI excludes zero** in this single joint model —
tighter and more conclusive than the prior package's separate-fit
diagnostic (where D=1's CI barely touched zero). This is the paper's
strongest direct evidence that the pooled `E:L` coefficient conceals
depth-dependent effect modification with an actual sign reversal, not
just a noisy trend.

---

## 2. Cluster-robust findings (Phase 1E)

Identical categorical formula, OLS with SEs clustered by `initialization_id`:

| depth | estimate | 95% CI | ci excludes zero |
|---:|---:|---|:-:|
| 1 | -0.068828 | [-0.229224, 0.091567] | No |
| 2 | -0.120952 | [-0.265671, 0.023767] | No |
| 3 | +0.090758 | [0.005161, 0.176356] | **Yes** |
| 4 | +0.036082 | [-0.028010, 0.100173] | No |
| 6 | +0.018122 | [-0.017074, 0.053319] | No |

Omnibus (cluster-robust): original chi2=6.706, df=4, **p=0.152** (does
not reject); replication chi2=2.793, df=4, **p=0.593** (does not reject).
Neither dataset's cluster-robust omnibus test finds joint evidence of
depth-varying `E:L` — in sharp contrast to the mixed-model omnibus test
(Section 1.2), which rejects overwhelmingly in both.

**Primary Question 3, cluster-robust arm**: the *sign* of every
depth-specific point estimate is preserved (D=1, D=2 still negative;
D=3, D=4, D=6 still positive) — **the D=2 reversal survives as a sign,
but not as a statistically significant effect** once clustering absorbs
within-initialization correlation without assuming the mixed model's
parametric variance structure. Only D=3 remains individually
significant. This mirrors the pooled-level finding from the prior
package (cluster-robust CI on the pooled `E:L` also included zero) —
extended here to show the same erosion of significance happens
depth-by-depth, not just in aggregate.

---

## 3. Include-zero sensitivity (Phase 1F, original only)

Every one of the 509 zero-variance rows was verified to have `mu_hat==0`
exactly (the runner's hard precondition check; no exception was raised,
confirming the prior package's finding held for all 509 rows, not just a
sample).

| depth | estimate | 95% CI | ci excludes zero |
|---:|---:|---|:-:|
| 1 | -0.102928 | [-0.143133, -0.062723] | Yes |
| 2 | -0.135255 | [-0.163684, -0.106825] | Yes |
| 3 | +0.087045 | [0.063833, 0.110258] | Yes |
| 4 | +0.034170 | [0.014068, 0.054273] | Yes |
| 6 | +0.017138 | [0.000725, 0.033552] | Yes |

Include-zero omnibus (mixed model): chi2=179.028, df=4, p=1.21e-37 —
slightly *stronger* than the primary complete-case omnibus (154.045),
not weaker.

**Primary Question 3, include-zero arm**: **the D=2 reversal not only
survives but remains essentially unchanged in magnitude and
significance** when zero-variance cells are included as `y=arcsinh(0)=0`
rather than excluded — this treatment moves every depth's estimate by a
modest amount without changing any sign or any significance
determination.

**Summary of Primary Question 3**: the D=2 sign reversal survives the
matched mixed-model categorical analysis (significant), survives the
include-zero treatment (significant, materially unchanged), but **does
not survive** cluster-robust inference as a statistically distinguishable
effect (sign preserved, CI widens to include zero).

---

## 4. Original data

Summarized in Sections 1-3 above. 102,400 total end-to-end cells; 509
zero-variance excluded (100% confined to `L=0`, reconfirmed); 101,891
eligible for the primary path.

## 5. Replication data

| depth | estimate | 95% CI |
|---:|---:|---|
| 1 | +0.133223 | [0.093245, 0.173201] |
| 2 | +0.047949 | [0.019834, 0.076063] |
| 3 | +0.076663 | [0.053770, 0.099557] |
| 4 | +0.027226 | [0.007426, 0.047026] |
| 6 | +0.020674 | [0.004521, 0.036826] |

**Primary Question 4**: the replication's omnibus test is independently
significant (depth *does* moderate `E:L` in the replication too), but
**every depth is positive — there is no sign reversal at low depth in
the replication.** This is the opposite qualitative pattern from the
original at D=1 and D=2 specifically.

---

## 6. Original vs. replication comparison (post-run approximate, not confirmatory)

| depth | original | replication | same sign | CI overlap |
|---:|---|---|:-:|:-:|
| 1 | -0.082 [-0.123, -0.042] | +0.133 [0.093, 0.173] | **No** | **No** |
| 2 | -0.118 [-0.146, -0.089] | +0.048 [0.020, 0.076] | **No** | **No** |
| 3 | +0.093 [0.070, 0.116] | +0.077 [0.054, 0.100] | Yes | Yes |
| 4 | +0.037 [0.017, 0.057] | +0.027 [0.007, 0.047] | Yes | Yes |
| 6 | +0.019 [0.003, 0.036] | +0.021 [0.005, 0.037] | Yes | Yes |

**Classification (per the frozen plan's 4/5 threshold): 3/5 depths agree
→ "original and replication depth patterns partially agree."** Not
"replicated." The disagreement is concentrated exactly where the
original data's replicate-count calibration was already known to be
weakest (D=1 has the highest zero-variance exclusion rate and the worst
pilot replicate-count convergence of any stratum in this project, per
`verification/r_calibration_depth1.md` and
`results/h2_robustness/original_data_audit/`) — this is offered as
context for interpretation, not as a claim that the original D=1/D=2
estimates are therefore wrong; both are independently, internally
significant single-dataset findings.

Weighted contrasts, side by side:

| weighting | original | replication |
|---|---|---|
| Equal-depth | -0.010111 [-0.022226, 0.002005] (includes zero) | +0.061147 [0.049204, 0.073090] (excludes zero) |
| Observation-count | +0.014289 [0.004249, 0.024328] (excludes zero) | +0.043134 [0.033224, 0.053044] (excludes zero) |
| Adopted (mixed model, full pooling) | +0.024996 [0.010729, 0.039262] | 0.049294 [0.035236, 0.063352] (prior package) |

**Primary Question 5**: equal-depth and observation-count weighting give
materially different answers in the original data (one includes zero,
one does not, and they differ by more than 2x in magnitude) — observation-
count weighting gives more influence to the three deeper block counts
because they contain more matched quantum parameters per initialization
(more rows), not because they are more trustworthy. Neither weighted
contrast, in either dataset, equals the adopted full-pooling model's
coefficient — the adopted model's implicit (GLS/REML) weighting is
neither of these two schemes, and no claim is made that it should be.

---

## 7. Unresolved discrepancies

- Why the D=1/D=2 sign reverses in the original data but not in the
  replication is not resolved by this package. Plausible contributors
  (calibration quality at low depth, sampling variability given each
  dataset has only 50 independent initializations) are named, not
  adjudicated.
- Whether the categorical model's non-monotonic depth pattern (large
  negative → large positive → decaying positive) reflects a real
  physical mechanism or is itself partly a low-depth calibration artifact
  is not addressed here — this package tests statistical structure, not
  physical mechanism.
- No hierarchical/zero-inflated model was fit (carried over limitation
  from the prior package; still not implemented here — no vetted
  dependency for it in this stack).

## 8. Deviations from the frozen plan

None. Every formula, contrast definition, weighting scheme, cluster
setting, and interpretation threshold in this document matches
`verification/h2_depth_heterogeneity_plan.md` exactly as frozen at commit
`87a46d4`. (One implementation bug was found and fixed *before* any
result was inspected a second time: the runner's `--resume` path
initially failed to reload `omnibus_tests`/`weighted_contrasts` from disk
before building the cross-dataset summary, raising a `KeyError` — a
mechanical bug in the orchestration code, not a change to any formula,
contrast, or interpretation rule, and it required rerunning the
replication fit once more to regenerate its diagnostics record that had
been computed but not yet persisted when the bug was hit. No coefficient
value was altered by this fix.)
