# H2 robustness and replication: results (IN PROGRESS)

**Status as of this writing: Phases 1-3 complete; Phase 4 complete except
(B) initialization-level resampling and the numerator/denominator
extension of (E), both running in the background; Phase 5 (design +
pilot benchmark) complete; Phase 6-7 (replication execution) not started,
pending a go/no-go decision on Stage 1 (Section 5).** This document will
be updated, not replaced, as the remaining background jobs complete —
updates are appended with a timestamp, consistent with the rest of this
repository's convention for post-run status updates.

Governing plan: `verification/h2_robustness_replication_plan.md` (frozen
at commit `7b57e3e`, before any of the results below were inspected).

---

## 1. Reproduced original findings (Phase 2)

Independently reproduced from frozen `results/production_confirmatory/`
inputs (`scripts/run_h2_zero_variance_audit.py`), matching the existing
record bit-for-bit:

- End-to-end pointwise cells: 102,400. Zero-variance excluded: **509**
  (0.497%). **100% confined to `L=0`** (509/509 at `L=0`, 0/0 at `L=1`) —
  reconfirmed independently.
- Adopted `E:L` (H2): **0.024995843985971582**, reproduced bit-for-bit
  (`atol=1e-9`) from the frozen `finite_shot_end_to_end` data.
- Current bootstrap (`n=443`, from `results/production_corrected_end_to_end/`):
  median `0.023685`, 95% percentile CI `[-0.018024, 0.065688]` — **includes
  zero**, as previously documented.
- Residual heteroscedasticity by depth (SD 0.659→0.276, D=1→D=6) and by
  budget (SD 0.301→0.513, B=250→B=2000) reproduced exactly.

**New finding in this pass**: all 509 zero-variance end-to-end cells have
`mu_hat` (the mean of the 30 replicate gradient estimates) **exactly
0.0**, not merely a tied nonzero value. This was not previously
documented and matters directly for Phase 4(F) below.

## 2. Robustness analyses on the original data (Phase 3-4)

### 2.1 Numerator/denominator decomposition (Phase 3) — diagnostic

| model | response | `E:L` estimate | 95% CI | role |
|---|---|---:|---|---|
| SNR_est (reference) | `arcsinh(SNR_est)` | 0.024996 | [0.010729, 0.039262] | reference |
| numerator | `arcsinh(\|mu_hat\|)` | **0.004315** | [0.003076, 0.005554] | primary/diagnostic |
| denominator | `log(shot_sd)` | **-0.149866** | [-0.173538, -0.126194] | primary/diagnostic |

**Both components show an `E:L` effect distinguishable from zero, and
both point the same direction** (numerator increases the gradient-signal
magnitude; denominator decreases the noise SD) — mechanistically coherent
and mutually reinforcing, not an artifact of one weird component. This is
a genuine strengthening of the *mechanistic* story behind H2, independent
of the *inferential* question addressed next.

### 2.2 Robust inference (Phase 4)

**(A) Baseline** — see Section 1 above.

**(C) Cluster-robust OLS at the initialization level** — same fixed-effect
formula, standard errors clustered on `initialization_id` (50 clusters),
no assumption of the mixed model's parametric variance structure:

| coefficient | estimate | cluster-robust SE | 95% CI | p |
|---|---:|---:|---|---:|
| `E:L` | 0.023550 | **0.023107** | **[-0.021739, 0.068839]** | 0.308 |

**This CI includes zero and the effect is not significant at α=0.05.**
The point estimate is nearly identical to the mixed model's (0.0236 vs.
0.0250), but the standard error more than triples (0.0231 vs. 0.0073)
once the homoscedasticity assumption is dropped. **This corroborates the
existing bootstrap disagreement, via an entirely different, single-fit
method**: two independent ways of relaxing the mixed model's variance
assumptions (the nested bootstrap and cluster-robust SEs) both fail to
corroborate the Wald/Holm rejection.

**(D) Depth-stratified diagnostics** — exploratory, no Holm correction:

| depth | `E:L` estimate | 95% CI | n_obs |
|---:|---:|---|---:|
| 1 | -0.090293 | [-0.182127, 0.001541] | 6,235 |
| 2 | **-0.111762** | **[-0.164917, -0.058608]** | 12,716 |
| 3 | +0.098048 | [0.061440, 0.134656] | 19,121 |
| 4 | +0.066700 | [0.040925, 0.092475] | 25,521 |
| 6 | +0.024632 | [0.009123, 0.040140] | 38,298 |

**The `E:L` coefficient changes sign across block counts.** At `D=2` it is
significantly *negative* (CI excludes zero on the negative side); at
`D=1` it is negative but not distinguishable from zero (CI upper bound
+0.0015); at `D=3,4,6` it is positive and significant, most closely
resembling the aggregate estimate at `D=6` (the largest stratum). The
aggregate positive estimate is a weighted average dominated by the three
deeper block counts (81% of eligible rows). **This is new information not
previously documented anywhere in the existing verification record or the
manuscript.** Budget-stratified diagnostics (B≤500: 0.0256 [0.0097,
0.0416]; B>500: 0.0247 [0.0014, 0.0479]) show no comparable instability —
the sign reversal is specific to block count, not shot budget.

**(F.2) Logistic model of `P(zero_variance_flag)`** — exhibits
quasi-complete separation on `L` (since `L=1` has exactly zero exclusions,
per Section 1), producing uninterpretable coefficient magnitudes/SEs for
every term involving `L`. Reported as a failed/inconclusive check, not
forced into a numeric interpretation — this is expected given the
deterministic Phase 2 finding, not new information.

**(F.3) Variance-floor sensitivity grid** — 7 predefined floors
(1e-12 to 1e-3): **all seven nonzero floors produce the identical `E:L`
estimate (0.018170, CI [0.003885, 0.032454])**, because every one of the
509 zero-variance cells has `mu_hat=0` exactly (Section 1) — the floor
value is mathematically irrelevant to a ratio whose numerator is zero.
The only real choice is *exclude* (adopted: 0.024996) vs. *include as a
zero-response point* (0.018170) — both remain distinguishable from zero,
so this particular robustness check does not overturn H2 on its own, but
it does show the point estimate moving by roughly 1 original-SE unit
depending on the exclusion convention.

**(B) initialization-level resampling and the (E) numerator/denominator
LOO extension are running in the background; this section will be updated
with their results.** (B)'s originally planned n=200 was revised to n=50
after discovering the per-iteration cost (145s, not the ~32-40s assumed)
would make n=200 an ~8-hour job — a feasibility-only revision made from
wall-clock alone, before any coefficient was inspected (see the frozen
plan's revision note).

## 3. Assessment so far: is H2 robust?

**Not unconditionally.** The prespecified Wald/Holm test rejects the null
for H2, and that decision stands as the paper's prespecified confirmatory
result — this package does not overturn it or claim authority to. But:

- The nested bootstrap (existing, n=443) does not corroborate it (CI
  includes zero).
- An independent, single-fit cluster-robust method does not corroborate
  it either (CI includes zero, p=0.308).
- The effect's sign is not stable across block counts — it is
  significantly *negative* at `D=2` and reverses to positive only from
  `D=3` onward.

**Three independent lines of evidence now agree that H2's statistical
significance is not robust to relaxing the mixed model's variance
assumptions or to stratifying by block count**, even though the
*mechanism* (Section 2.1) is coherent and the *prespecified* test rejects.
This is reported plainly, per the task's instruction, rather than
resolved in either direction.

## 4. Independent replication (Phase 5-7) — Stage 1 complete

Design frozen, seed namespace verified non-overlapping
(`seed_root=3872531887`), pilot benchmark run. **Stage 1 executed**
(user go-ahead): `R_rep=30`, full 8×5×4×50 design, end-to-end mode, new
seed namespace. All 6 pipeline steps (`generate-exact`, `generate-shots`,
`validate`, `aggregate`, `fit`, `report`) exited 0 in **19.4 minutes**
(faster than the ~30-35 min estimate). 27 output files hashed
(`results/h2_replication_v1/_pipeline_output_stage1/SHA256SUMS_stage1_output.json`).

| | original | replication | difference |
|---|---:|---:|---:|
| `E:L` estimate | 0.024996 | **0.049294** | +0.024298 (**3.34** original-SE units) |
| 95% Wald CI | [0.010729, 0.039262] | [0.035236, 0.063352] | overlap: yes (barely, at the boundary) |
| Sign | positive | positive | agree |
| Eligible `n_obs` | 101,891 | 101,815 | -76 (-0.07%) |
| Zero-variance excluded | 509 (0.497%) | 585 (0.571%) | +76, still 100% confined to `L=0` |

**Interpretation (fixed decision rule, computed mechanically):
"direction replicated but magnitude uncertain."** The replication
independently reproduces a positive, statistically significant `E:L`
effect (its own 95% CI excludes zero) and independently reconfirms the
100%-`L=0` zero-variance confinement under entirely new randomness — both
substantively reassuring. But the replication's point estimate is
roughly double the original's and 3.34 original-SE units away, which
exceeds the frozen plan's ≤2-SE-unit threshold for "direction and
magnitude replicated." This is reported exactly as it came out, not
rounded toward either "confirmed" or "failed to replicate."

**Stage 2 (`R_rep=300`) expansion rule was NOT triggered**: the frozen
plan's only data-driven trigger is a >2x divergence in zero-variance
exclusion rate (production 0.497% vs. replication 0.571% — a 1.15x
ratio, well under 2x). Stage 2 is available if wanted but is not
mechanically indicated by the predefined rule.

The replication's own initialization-level bootstrap (`n=30`, ~72 min
projected) was launched separately and will be added to this section
when complete.

## 5. Next steps

1. (B)/(E) background jobs and the replication's own bootstrap are
   completing; this document will be updated with their results.
2. Phase 9 final deliverables (manuscript revision proposal update,
   final honest summary) to follow.
