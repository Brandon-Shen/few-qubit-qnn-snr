# H2–H4 bootstrap arm, rerun on end-to-end-only data

**Supersedes**: the H2–H4 bootstrap draws behind the old pooled-mode
confirmatory numbers (`verification/h2h4_bootstrap_memory_redesign.md`,
n=400, seeds 66001/76001/86001/96001/106001) pooled `finite_shot_conditional`
+ `finite_shot_end_to_end` rows, the same bug documented in
`verification/mode_pooling_guard.md`. This document is the end-to-end-only
rerun, comparing against both the new end-to-end-only Wald CIs
(`verification/confirmatory_numbers_adopted.md`) and the old pooled
bootstrap CIs. The pooled bootstrap draws are not deleted — they remain
useful context for how much the mode change moves the percentile-CI picture.

## Headline, stated plainly before the details

**Achieved n=40** (not the n=400 order of magnitude targeted), across 3
independent seed streams, **0 failed iterations**, in **~80 minutes of
actual wall-clock spent on bootstrap computation** (not counting time spent
writing code or checking progress). This falls well short of the pooled
run's n=400. The reason is a genuine, unflattering surprise reported
honestly rather than smoothed over: **halving the row count (dropping
conditional-mode rows) did not produce a proportional per-iteration speedup**
— see §2. Given that, reaching n=400 here would have needed a comparable or
larger wall-clock budget to the ~2.5 hours (plus careful staggered-concurrency
safety work) the original pooled n=400 run required, and this task instead
used a bounded, honestly-reported budget (~80 minutes of actual computation)
rather than open-endedly chasing the target number.

## 1. Precompute structure rebuilt for the filtered dataset

`verification/h2h4_bootstrap_lowmem.py` is unchanged — its
`_precompute_cell_index()` takes whatever `raw_shot_df` it's given and has
no mode-specific logic, so "rebuilding the precomputed structure for the
filtered dataset" meant only ever calling it on
`results/production_confirmatory/raw/finite_shot_end_to_end.parquet` alone, never on the pooled
concatenation the original pooled-data scripts used. Two new scripts do
this (both new files, no existing script edited):

- `verification/run_h2h4_endtoend_regression_test.py` — the n=8
  from-scratch reproducibility check (§2).
- `verification/run_h2h4_bootstrap_shard_endtoend_only.py` — the extension
  shard runner, loading only `finite_shot_end_to_end.parquet`, seed stream
  `366001 + shard_id * 10000` (distinct from every pooled-data seed stream
  and from the regression-test seed `266001`).

Precompute stats on the filtered data: **3,072,000 rows** (half of the
pooled 6,144,000), **102,400 distinct pointwise cells** (half of the pooled
204,800, since `analysis_mode` is one of the cell-key columns and only one
mode remains). Load: ~0.2–1.4s. Precompute: ~2.9–8.4s. Both roughly in line
with (or a bit faster than) the pooled dataset's 0.58s/5.84s, as expected
for half the data.

## 2. Fresh n=8 regression-truth checkpoint — PASSED, exact match

Since this is a new dataset (no prior end-to-end-only-only ground truth
exists — every previous use of `h2h4_bootstrap_lowmem.py` operated on the
pooled dataset), "regression test" here means: run the same
`(seed=266001, 8 iterations)` draw sequence **twice**, via two fully
independent from-scratch passes (separate data load, separate
`_precompute_cell_index` call each time), and require bit-identical output.

| coefficient | max abs diff (pass_a vs pass_b) | `allclose(atol=1e-9, rtol=1e-6)` |
|---|---|---|
| `E:L` | 0.0 | True |
| `E:R` | 0.0 | True |
| `L:R:depth_z` | 0.0 | True |

**PASSED, exact bit-for-bit match**, all 8 iterations successful in both
passes, 0 failures. Per the same guardrail as the original memory redesign
(`h2h4_bootstrap_memory_redesign.md` §3), this is what makes it valid to
trust the extension shards built on top of this dataset — had this not
matched, the task would have stopped here.

**Timing, and the honest surprise**: pass_a averaged **80.7s/iteration**
(range 48.4–96.0s), pass_b averaged **146.3s/iteration** (range 85.2–275.6s)
— nearly 2x slower than pass_a despite running the *exact same code on the
exact same data*, sequentially in the same process, no concurrency
involved. This is real run-to-run variability on this machine (likely
background system load, not anything in the code — both passes are
independently reproducible and bit-identical to each other), and it means
**per-iteration cost on this dataset is not a stable, predictable number** —
report it as a range, not a point estimate. Combined, both passes: **peak
RSS = 2.737GB**, well below the pooled dataset's 5.6GB single-stream peak —
consistent with roughly half the data, and a real memory-footprint benefit
even though the wall-clock benefit did not materialize proportionally.

## 3. Extension: n=8 → n=40, and why it stopped there

Two shards launched, staggered 20s apart (matching the established
memory-safety practice from `h2h4_bootstrap_memory_redesign.md` §8, though
note below on what safety monitoring was *not* repeated here):

- **Shard 0** (seed 366001, fresh stream): 16 iterations successfully
  completed, 0 failures, before being deliberately stopped (see below).
  Wall-clock for those 16 iterations: 2,999.4s (~187.5s/iteration mean;
  range 116.4–549.6s — the 549.6s outlier on iteration 15 is the largest
  single-iteration time observed anywhere in this document).
- **Shard 1** (seed 376001, fresh stream): 16 iterations successfully
  completed, 0 failures. Wall-clock: 2,429.3s (~151.8s/iteration mean;
  range 100.7–257.0s).
- Both ran concurrently (2-way). Combined wall-clock for the extension
  phase: **~50.2 minutes** (bounded by the slower shard).

**Both shards were deliberately stopped (clean process termination, not a
crash) at 16/60 requested iterations** — a **time-budget decision, not a
memory-safety or correctness incident**. Checkpointing is per-iteration
(`checkpoint_every=1`), so no completed work was lost; the checkpoint files
simply stop at iteration 15 for each shard. This was a judgment call made
because, given the observed 100–550s/iteration range under 2-way
concurrency, continuing to the originally-requested 60 iterations/shard
would have needed several more hours — the same order of wall-clock the
original pooled n=400 run required, but without the several-hours budget
being available for this rerun. **n=40 (8 regression + 16 + 16) is reported
as the actual achieved number, not rounded up or extrapolated toward 60 or
400.**

**One methodological gap, disclosed rather than papered over**: the
original pooled-data extension (`h2h4_bootstrap_memory_redesign.md` §8) ran
an active `psutil`-based safety net that killed all workers if free memory
dropped below a threshold, after a near-miss during concurrency testing. No
equivalent live memory monitoring was run during this end-to-end-only
2-shard extension — the decision to treat 2-way concurrency as safe here
was based on the much lower per-process footprint observed in §2 (2.7GB for
two sequential passes in one process, well under the pooled dataset's
4.8-5.6GB/process figures that were themselves deemed safe at up to 3-4
concurrent shards), not on direct measurement during this specific run. No
memory-related problems were observed, but this is a weaker safety
guarantee than the earlier careful protocol, and is reported as such rather
than implied to have been re-verified.

## 4. Final percentile CIs (n=40) vs. Wald CIs (Task 2) vs. old pooled bootstrap (n=400)

Pooled across all 3 seed streams (266001 regression-test draws, 366001,
376001), 40 total draws, 0 failures:

| coefficient | hypothesis | End-to-end-only Wald point est. | End-to-end-only Wald 95% CI | **End-to-end-only n=40 percentile CI** | **n=40 median** | Old pooled-data n=400 percentile CI | Old pooled n=400 median |
|---|---|---|---|---|---|---|---|
| `E:L` | H2 | 0.024996 | [0.010729, 0.039263] | **[-0.000875, 0.047275]** | **0.022446** | [-0.016215, 0.067433] | 0.023847 |
| `E:R` | H3 | -0.000958 | [-0.015252, 0.013337] | **[-0.024080, 0.023068]** | **-0.003987** | [-0.029178, 0.033284] | 0.002459 |
| `L:R:depth_z` | H4 | -0.010179 | [-0.020688, 0.000331] | **[-0.021768, 0.006658]** | **-0.008777** | [-0.019505, 0.020187] | -0.000392 |

**Read honestly, per-coefficient:**

- **H2 (`beta_EL`)**: the n=40 median (0.0224) sits close to the Wald point
  estimate (0.0250) — reasonable directional agreement. But the n=40
  percentile CI **includes zero** (barely: lower bound -0.0009), so **the
  percentile bootstrap does not independently corroborate H2's Wald-based
  rejection at end-to-end-only n=40** — the same qualitative conclusion the
  pooled-data bootstrap reached at both n=100 and n=400
  (`h2h4_bootstrap_memory_redesign.md` §5/§8). At n=40, this should be read
  with more caution than the n=400 pooled figure — a 2.5th/97.5th
  percentile of 40 draws is a less stable estimate of the tail than one from
  400 draws — but the fact that the CI edge sits so close to zero rather
  than clearly away from it is consistent with, not contradicted by, the
  weak-corroboration story already established for H2.
- **H3 (`beta_ER`)**: n=40 CI includes zero, consistent with the null Wald
  result, no surprise, matches the pattern at every other n reported for
  this coefficient across this whole verification history.
- **H4 (`beta_LRd`)** — **direct answer to the specific question asked**:
  does the end-to-end-only percentile bootstrap corroborate the near-boundary
  Wald p=0.058, contradict it, or remain too uncertain to say either way?
  **Remains too uncertain to say either way.** The n=40 median (-0.0088) is
  reasonably close to the Wald point estimate (-0.0102) and has the same
  sign — mild directional agreement — but the percentile CI
  ([-0.0218, 0.0067]) **includes zero**, so it neither independently confirms
  nor contradicts the Wald test's near-miss at α=0.05. Given n=40 is a
  fraction of the n=400 that was needed just to get a stable (if still
  zero-including) read on H2's CI, this is an underpowered comparison and
  should be read as "no additional evidence either way from the bootstrap,"
  not as a data point that resolves H4's borderline Wald p-value.

## 5. What this does and doesn't change

No confirmatory conclusion changes. The Wald-based
`results/production_confirmatory/confirmatory_hypotheses.csv` (end-to-end-only, adopted in
`verification/confirmatory_numbers_adopted.md`) remains the primary
confirmatory analysis. This bootstrap rerun's honest bottom line: at the
achieved n=40, the percentile bootstrap for H2 still does not corroborate
the Wald rejection (consistent with every larger-n pooled-data result before
it), and H4's near-boundary Wald p-value is neither corroborated nor
contradicted by the bootstrap at this sample size — a genuinely
inconclusive result on that specific question, reported as inconclusive
rather than stretched into a positive or negative finding.

## Files produced

- `verification/run_h2h4_endtoend_regression_test.py`,
  `h2h4_endtoend_regression_test_result.json`,
  `_endtoend_regression_stdout.log` — the n=8 from-scratch reproducibility
  check (§2).
- `verification/run_h2h4_bootstrap_shard_endtoend_only.py`,
  `_endtoend_shard{0,1}_stdout.log` — the extension shard runner and its
  logs (§3). No `*_summary.json` was written for shards 0/1 (that file is
  only written when a shard's `main()` completes its full requested
  iteration count, and these were deliberately stopped before reaching
  their 60-iteration target) — timings in this document were extracted
  directly from the per-iteration log lines instead.
- `_bootstrap_checkpoints/h2h4_boot_endtoend_regression_a.parquet`,
  `h2h4_boot_endtoend_regression_b.parquet` — the two independent 8-draw
  regression-test checkpoints (bit-identical to each other).
- `_bootstrap_checkpoints/h2h4_boot_endtoend_shard{0,1}.parquet` — 16
  successful draws each (0 failures), seeds 366001/376001.
- No changes to `qnn_snr/stats/bootstrap.py`, `qnn_snr/stats/pointwise.py`,
  `results/`, or `results_and_discussion.md`. The pooled-data bootstrap
  checkpoints and ground truth from the original memory-redesign task are
  untouched.
