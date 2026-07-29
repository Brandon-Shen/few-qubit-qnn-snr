# Task F — memory-efficient redesign of the H2-H4 bootstrap

**Bottom line**: the ~16GB/iteration footprint (`verification/reduced_bootstrap_results.md`)
came from the original implementation building three successive full-width physical
copies of the combined 6.14M-row raw shot dataset per iteration. A redesign
(`verification/h2h4_bootstrap_lowmem.py`) that precomputes the (iteration-invariant) cell
grouping once and then does per-iteration resampling with numpy index arrays instead of
`pandas.concat`/`.copy()` of full rows cuts a complete 8-iteration run's peak RSS to
**5.6GB** (measured, whole-run peak, not per-iteration) and reproduces the existing
8-iteration ground truth (`h2h4_bootstrap_combined_draws.parquet`, seed 66001) **exactly**
(`max_abs_diff = 0.0` on all three target coefficients). With the memory ceiling gone, 2
concurrent shards ran cleanly (previously impossible — a second concurrent stream of the
original implementation drove free memory to 590MB and had to be killed). The sharded
bootstrap was extended from n=8 to **n=100** (50 new iterations per shard, one shard
continuing the original seed-66001 stream, one new seed-76001 stream) in **~77 minutes**
combined wall clock, versus **9.7 hours** for the original 8 iterations. 100 is the floor
of the original 100-150 target, not the full range — see §4 for why, and it is not rounded
up here.

## 1. Profiling: where the ~16GB actually goes

Two separate profiling efforts were run against the real combined dataset
(`results/raw/finite_shot_conditional.parquet` + `finite_shot_end_to_end.parquet`,
6,144,000 rows, 50 unique `initialization_id`, 204,800 distinct
`(analysis_mode, configuration_id, depth, budget, initialization_id, parameter_id)` cells
at R=30 replicates/cell):

**Staged profile of the original pipeline** (`verification/profile_h2h4_iteration.py`,
`verification/_profile_run_stdout.log`) got partway through before time ran out on this
task, so treat the later stages as *not directly measured*, not zero-cost:

| stage | RSS (post-gc) | peak RSS so far |
|---|---|---|
| start | 0.145 GB | 0.145 GB |
| after loading raw combined data | 4.781 GB | 4.781 GB |
| after `_relabel_outer_resample` (1st full-width copy) | 5.912 GB | 6.919 GB |
| after `_inner_resample_replicates` (2nd full-width copy) | **not measured** | — |
| after `pointwise_statistics` (groupby of the 2x-copied frame, 204,800 groups) | **not measured** | — |
| after `fit_mixed_model` | **not measured** | — |

Loading the raw data alone (`read_tidy_dataset` on both finite-shot parquet files,
concatenated) already costs 4.78GB — well above the 2.56GB `memory_usage(deep=True)`
figure for the same data, because many of the 30 columns are object/string dtype
(`experiment_id`, `parameter_id`, `cost_type`, `quantum_framework`, `simulator_backend`,
`software_version`, `git_commit`, `config_hash`, `pilot_or_confirmatory`) and pandas'
per-object overhead multiplies real memory well past the raw byte count. The first
full-width copy (`_relabel_outer_resample`) pushes peak RSS to 6.9GB by itself. The
original code then does this **two more times** — `_inner_resample_replicates` builds a
second full-width copy via 204,800 `g.iloc[idx]` slices + `pd.concat`, and
`pointwise_statistics` groups *that* copy again (204,800 groups, each producing a Python
dict accumulated into a list of ~204,800 records before `pd.DataFrame.from_records`).
Three full-width copies of a dataset whose string-heavy columns already inflate its
in-memory footprint to ~1.9x its byte count, plus the per-group Python-object overhead of
two separate 204,800-group operations, is consistent with — though not independently
pinned down beyond the two measured stages above — the previously observed ~16GB peak.

**Whole-run measurement of the redesigned pipeline** (`run_h2h4_lowmem_regression_test.py`,
background `psutil` peak sampler at 0.2s resolution, covering data load + one-time
precompute + all 8 iterations): **peak RSS = 5.599GB**, essentially all of it the one-time
cost of loading the raw data and building the precomputed cell index — per-iteration
incremental cost is small (numpy index arrays and small per-cell aggregates, no full-width
copies at all). This is a real, complete, directly measured number, unlike the original
pipeline's partial profile above.

**Correction (Task H, follow-up pass): the "~3.7-3.8GB per process" figure reported below
in §4 for the 2-concurrent-shard run was measured with `tasklist`, a different tool than
the `psutil` peak sampler used for the 5.6GB single-stream figure above — that was not an
apples-to-apples comparison, and it produced a number that looked (wrongly) like
concurrent per-process memory was *lower* than single-stream, which has no plausible
mechanism given both cases do the same load+precompute. See §7 below for the corrected,
same-tool measurement: concurrent per-process peak is actually ~4.8GB, in the same
ballpark as (if anything marginally below, within noise) the single-stream peak — nothing
mysterious, `tasklist` just wasn't sampling continuously and caught an
instantaneous-lower-than-peak snapshot. The §4 narrative and its bottom-line conclusions
("2 concurrent shards ran cleanly, without incident") are otherwise still correct; only
the specific 3.7-3.8GB figure was wrong.

## 2. What changed and why

New module: `verification/h2h4_bootstrap_lowmem.py` (not wired into
`qnn_snr/stats/bootstrap.py` — kept as a standalone, drop-in-compatible module so the
production statistics module is untouched pending a decision on whether to promote this).

Approach (closest to the "resample indices, not data" + "streaming aggregation" options,
in combination): the original code's two resampling steps
(`_relabel_outer_resample`, `_inner_resample_replicates`) and `pointwise_statistics`'s
groupby all traverse the data in an order that turns out to be **entirely
iteration-invariant** — only *which* `initialization_id`s get drawn, and which replicate
indices get resampled within a cell, changes iteration to iteration; the *set* of cells and
both groupby traversal orders are fixed properties of the raw dataset. So:

- `_precompute_cell_index` (run **once**, not per iteration): builds, per original
  `initialization_id`, the ordered list of `(analysis_mode, configuration_id, depth,
  budget, parameter_id)` cells and each cell's row positions (as `np.int64` arrays), plus
  the canonical pandas-sort-order of the full 17-column key tuples used by
  `pointwise_statistics`. Also pulls `gradient_hat`/`exact_gradient` out as flat numpy
  arrays once.
- Each iteration (`_one_iteration_lowmem`) replays the **exact same sequence** of
  `rng.choice`/`rng.integers` calls, in the same order, that the original code makes —
  same seed, same call sizes, same call order — but instead of copying rows, gathers
  values via numpy fancy-indexing into the precomputed position arrays. No
  `pd.concat`/`.copy()` of full rows anywhere in the per-iteration path.

This reproduces the original's RNG draw sequence and grouping order exactly, which is what
makes bit-identical output possible (§3) rather than just "statistically similar."

## 3. Regression test — PASSED, exact match

`verification/run_h2h4_lowmem_regression_test.py`, seed 66001, iterations 0-7, against
`verification/h2h4_bootstrap_combined_draws.parquet` (the original ground truth):

| coefficient | max abs diff | `allclose(atol=1e-9, rtol=1e-6)` |
|---|---|---|
| `E:L` | 0.0 | True |
| `E:R` | 0.0 | True |
| `L:R:depth_z` | 0.0 | True |

All 8 iterations succeeded, 0 failures, **exact bit-for-bit match** on all three target
coefficients — not just "close." Timings: load 0.58s, precompute 5.84s, 8 iterations in
588.97s (~73.6s/iteration, single-stream). Peak RSS for the whole run: 5.599GB (§1).

Per the task's own guardrail, this result is what makes it valid to trust the redesign for
anything beyond iterations 0-7 — had this not matched, the task would have stopped here.

## 4. Concurrency test and extended run

With the per-iteration footprint down from ~16GB to a low-single-digit-GB regime, 2
concurrent shard processes were run (`verification/run_h2h4_bootstrap_shard_lowmem.py`,
same shard/seed convention as the original `run_h2h4_bootstrap_shard.py`: shard N uses
seed `66001 + N*10000`):

- **Shard 0** (seed 66001) *extends* the original ground-truth checkpoint: iterations 0-7
  already present are skipped (checkpoint-resume logic), 42 new iterations (8-49) computed
  via the low-memory redesign. `n_successful=50/50`, wall clock for this invocation
  4,189.8s (69.8 min; this includes the ~1-2s of skip-checks for the 8 pre-existing
  iterations, so effectively ~99.8s/iteration for the 42 new ones under 2-way
  concurrency).
- **Shard 1** (seed 76001) is a fresh stream: `n_successful=50/50`, wall clock 4,595.3s
  (76.6 min; ~91.9s/iteration under concurrency).
- Both processes ran concurrently and completed without incident — free memory was
  monitored throughout and never approached the danger zone the original implementation
  hit (590MB free with 2 concurrent original-implementation streams, one of which had to
  be killed). Peak RSS per concurrent process during this run was observed around
  3.7-3.8GB via `tasklist` — **corrected in §7 below: this was an instantaneous-snapshot
  artifact, not a real reduction from single-stream.** A same-tool (`psutil` peak sampler)
  remeasurement gives ~4.8GB per process under 2-way concurrency, in the same range as
  the 5.6GB single-stream figure. Either way, combined concurrent memory use
  (~9.6-10.6GB for 2 processes) was comfortably within this machine's memory — a regime
  the original ~16GB/iteration/stream implementation could never reach with 2 streams.
- Per-iteration cost under 2-way concurrency (~92-100s/iteration) is roughly 25-35%
  slower than the single-stream regression-test rate (~73.6s/iteration) — real but modest
  contention, nothing like the original implementation's memory-driven failure mode.
- **Total combined wall clock for the extended run: ~76.6 minutes** (bounded by the
  slower of the two concurrently-running shards), producing 92 new successful iterations
  (42 + 50) on top of the pre-existing 8.

**Pooled total: n=100 successful iterations** (8 original + 92 new), computed directly
from `verification/_bootstrap_checkpoints/h2h4_boot_shard{0,1}.parquet` without
overwriting either the original ground-truth checkpoint or
`verification/h2h4_bootstrap_combined_draws.parquet` (that file is also the regression
test's ground-truth reference in `run_h2h4_lowmem_regression_test.py` and was
deliberately left untouched — `combine_h2h4_shards.py` would overwrite it, so it was not
run as-is; the pooled CI below was computed directly from the two shard checkpoints
instead).

**This is the floor of the original 100-150 target, not the full range, reported as such
— not rounded up.** The two shards were each run to a fixed target of 50 iterations
(chosen deliberately to land at the low end of the target range within a modest,
well-monitored time budget) rather than run until a multi-hour time-box was exhausted;
only ~77 minutes of the "a few hours" budget was used. Extending further (e.g. toward
150) is straightforward and cheap given the demonstrated ~90-100s/iteration under 2-way
concurrency — roughly another 45-75 minutes for 50 more iterations split across the two
shards — but was not done here since n=100 already gives a meaningfully larger sample
than the original n=8 and the task's core goals (profile, redesign, validate) are
satisfied; extending further is a easy follow-up if a larger n is wanted later.

## 5. New percentile CIs (n=100) vs. Wald CIs vs. original n=8

| coefficient | hypothesis | Wald point estimate | Wald 95% CI | n=8 percentile CI (original) | n=8 median | **n=100 percentile CI (new)** | **n=100 median** |
|---|---|---|---|---|---|---|---|
| `E:L` | H2 | 0.023732 | [0.012658, 0.034807] | [-0.001193, 0.053131] | 0.021502 | **[-0.016351, 0.061620]** | **0.024522** |
| `E:R` | H3 | 0.003528 | [-0.007594, 0.014650] | [-0.015524, 0.026300] | 0.005858 | **[-0.027791, 0.033305]** | **0.002768** |
| `L:R:depth_z` | H4 | 0.000511 | [-0.007647, 0.008669] | [-0.016208, 0.024394] | 0.000276 | **[-0.018906, 0.021103]** | **-0.000223** |

**Read this honestly, not optimistically:**

- **H2 (`E:L`)**: the n=100 median (0.0245) sits very close to the Wald point estimate
  (0.0237) — good directional agreement, better centered than the n=8 median even was.
  But the n=100 percentile CI is **wider** than the n=8 CI, not narrower, and **still
  includes zero**. This is not a data-quality problem — with only 8 points, a 2.5/97.5
  percentile is essentially interpolating between the 1st-2nd smallest/largest values,
  which tends to look artificially narrow; n=100 resolves the tails more honestly and
  they turn out to be wider than 8 points suggested. **Practical conclusion: even at
  n=100, the percentile bootstrap still does not independently corroborate H2's
  Wald-based rejection** (unlike H1, which got real corroboration at n=400 in
  `reduced_bootstrap_results.md`). This is a legitimate, if unflattering, finding — it
  does not overturn the Wald-based H2 rejection (Holm-corrected, p=0.000107), but it
  means H2 still lacks the kind of non-Wald backup that H1 has, and more than 100
  iterations would likely be needed to get it, if it's obtainable at all with this
  amount of underlying data.
- **H3 (`E:R`) and H4 (`L:R:depth_z`)**: both n=100 CIs include zero, consistent with
  their existing Wald-based null results, same as at n=8 — "not contradicted," the
  weakest form of corroboration, unchanged by more iterations. No surprises here.
- None of this changes any confirmatory conclusion — the Wald-based
  `results/confirmatory_hypotheses.csv` results remain the primary confirmatory analysis
  throughout, per the same framing `reduced_bootstrap_results.md` used for n=8.

## 6. RSS reconciliation (Task H, follow-up pass)

The discrepancy flagged at the top of §1: 5.6GB single-stream peak (`psutil`, tracked
continuously) vs. 3.7-3.8GB per process under 2-way concurrency (`tasklist`, an
instantaneous snapshot at one arbitrary polling moment during the original extended run)
was not apples-to-apples. Re-measured with the *same* tool
(`verification/measure_rss_concurrent.py`, a `psutil` peak sampler embedded in each
process, 5 iterations, same load+precompute+run code path, checkpointing disabled so as
not to touch any real checkpoint file):

| run | tag | seed | peak RSS (psutil, tracked) |
|---|---|---|---|
| single-stream | `solo` | 900001 | **5.335 GB** |
| 2-concurrent, process A | `conc_a` | 900002 | **4.806 GB** |
| 2-concurrent, process B | `conc_b` | 900003 | **4.807 GB** |

**Reconciled: concurrent per-process peak (~4.8GB) is in the same range as single-stream
(~5.3GB) — if anything marginally lower, well within normal run-to-run variance, not
mysteriously smaller.** There is no real reduction in per-process memory need under
concurrency; the original `tasklist`-based 3.7-3.8GB figure was simply not sampling
continuously and happened to catch both processes at a moment between iterations when
some allocations had already been freed (e.g. just after a checkpoint write and before
the next iteration's allocations), not at their true peak. Free system memory was
monitored throughout this remeasurement (started at ~13.1GB free with the desktop's other
running applications already using ~21GB of this machine's ~34GB total; dropped to ~6.7GB
free during the concurrent load spike, recovered to ~11-12GB during steady-state
iteration, back to ~14.3GB once both processes exited) — never approached a danger zone.

**Practical implication for concurrency planning (feeds into Task I)**: budget ~5GB per
concurrent process, not ~4GB, when deciding how many shards this machine can safely run
at once — and note that on *this particular machine right now*, the binding constraint is
not the workload's own footprint (which the redesign already cut ~3x) but **total system
free memory net of everything else running** (~11-14GB free with normal desktop load in
this session, out of 34GB total physical RAM). See Task I for how this plays out at
higher concurrency.

**Retroactive tie-in to `reduced_bootstrap_results.md`'s wall-clock oddity**: that
document's §0 attributed an unexplained ~13x wall-clock slowdown (327.8s isolated
benchmark vs. ~4,373s/iteration in the original implementation's production run) to
unconfirmed "background throttling." A note has been added to that document (see its §0)
pointing to a better-fitting explanation now available: the original implementation's
~16GB/iteration working set was close enough to this machine's physical memory ceiling
(free memory hit 590MB with just 2 concurrent streams of that implementation) that disk
swapping/paging under memory pressure is a more likely cause than throttling — though, as
noted there, this is not independently confirmed via actual swap/paging counters from
that run (no such logging was active at the time), so it remains "a better explanation,
not a proven one."

## 7. Files produced

- `verification/profile_h2h4_iteration.py`, `_profile_run_stdout.log` — staged profiling
  of the original implementation (partial, see §1).
- `verification/h2h4_bootstrap_lowmem.py` — the redesigned low-memory implementation.
- `verification/run_h2h4_lowmem_regression_test.py`,
  `h2h4_lowmem_regression_test_result.json`, `_lowmem_regression_stdout.log`,
  `_bootstrap_checkpoints/h2h4_boot_lowmem_regression.parquet` — the regression test and
  its full output (§3).
- `verification/run_h2h4_bootstrap_shard_lowmem.py`,
  `_bootstrap_checkpoints/h2h4_boot_shard{0,1}_lowmem_summary.json`,
  `_shard{0,1}_lowmem_stdout.log` — the extended concurrent run (§4). Shard 0's parquet
  checkpoint (`h2h4_boot_shard0.parquet`) now has 50 iterations, extending (not
  replacing) the original 8; shard 1's checkpoint (`h2h4_boot_shard1.parquet`) is new.
- `verification/_validate_lowmem_smoke.py`, `_validate_lowmem_dev.py` — smaller
  development-time validation scripts used while building the redesign (kept for
  reference, not part of the final regression test).
- No changes to `qnn_snr/stats/bootstrap.py`, `qnn_snr/stats/pointwise.py`, `results/`,
  or `results_and_discussion.md`. `verification/h2h4_bootstrap_combined_draws.parquet`
  (the original n=8 ground truth) is untouched.
- **Task I additions** (see §8 below): `verification/test_concurrency_safety.py`,
  `_concurrency_test_n3.log`, `_concurrency_test_n4_staggered.log`,
  `_rss_probe_safety_n{3,4}_*.json/.log` — the concurrency-safety probes.
  `_bootstrap_checkpoints/h2h4_boot_shard{0,1,2,4}.parquet` now each hold 100 iterations
  (shard 0 and 1 extended from 50, shard 2 and 4 are new); a `h2h4_boot_shard3.parquet`
  checkpoint was never created (that shard was killed for safety before completing its
  first iteration — see §8, no work was lost). `_shard{0,1}_ext_stdout.log`,
  `_shard{2,4}_stdout.log`, and the corresponding `*_lowmem_summary.json` files hold the
  production run's logs and timings.

## 8. Task I: extending further toward n=400, and a real concurrency near-miss

**Step 1 — concurrency safety testing.** `verification/test_concurrency_safety.py`
launches N `measure_rss_concurrent.py` workers and kills all of them immediately if
system free memory drops below a configurable threshold — an active safety net, not just
passive monitoring, given real damage was possible.

- **3-way, unstaggered (all launched at once), danger threshold 1.5GB**: survived, but
  **free memory hit 1.511GB — 11MB above the kill threshold**, a genuine near-miss, not a
  comfortable pass. All 3 workers' initial data-load stage (each transiently needing
  ~4.7-5.6GB before settling to ~2.4GB post-precompute) overlapped almost exactly,
  producing a combined transient demand (`sum=14.098GB` across the 3 processes' own
  peaks) that came within a hair of exceeding this machine's actual free memory at the
  time. Per-process peaks (4.66-4.74GB) were unremarkable on their own — the risk is
  entirely in the *simultaneous* transient overlap, not steady-state per-process memory.
- **4-way, staggered 20s apart, same threshold**: **min free memory 8.637GB** — a
  comfortable margin, no danger. Staggering launches means each process's brief
  (~10s) load-spike no longer overlaps with the others', so the worst-case simultaneous
  demand stays low even with more total processes.

**Conclusion: on this machine, launch staggering (not just per-process footprint) is
what actually determines safe concurrency.** The workload's own footprint was already
cut ~3x by the redesign (§1); the remaining constraint is `min(other-apps' memory
headroom, worst-case simultaneous transient overlap)`, and only the second half is under
this codebase's control.

**Step 2-3 — the production run (and a real near-miss during it, not just the probe).**
Based on step 1, 4 shards were launched staggered 20s apart: shard 0 (seed 66001,
extending 50→100) and shard 1 (seed 76001, extending 50→100) resuming existing
checkpoints, plus two new shards, 2 (seed 86001) and 3 (seed 96001), each targeting 100.
**Despite the successful staggered probe in step 1, free system memory in the real
production run dropped to 1.29-2.34GB within the first ~10 minutes** — tighter than the
probe predicted, most likely because this machine's other applications (browser, editor,
etc.) had grown their own memory use in the time since the probe ran, eating into the
margin the probe measured. Rather than wait for an automated kill-switch that might react
too slowly to a fast drop (as very nearly happened in step 1's 3-way test), **shard 3 was
proactively killed by hand** (0 completed iterations at that point — no checkpointed work
lost) to drop back to 3-way concurrency. Free memory recovered immediately (1.29GB ->
4.26GB). The run then proceeded safely at 3-way concurrency (a tighter 2GB auto-kill
threshold and 5-minute polling were used from this point on, and never triggered).

When shard 0 and shard 1 finished (both reaching 100 first), a new shard was opportunistically launched into the freed capacity — **shard 4** (seed 106001, a fresh stream, since shard 3's seed/checkpoint was abandoned when it was killed pre-checkpoint) — bringing concurrency back to 2 (shard 2 + shard 4), which by this point was well within the demonstrated-safe range. When shard 2 finished, shard 4 continued alone (single-stream) to its own 100-iteration target.

**Actual outcome, honestly reported**: 4 checkpoints reached 100/100 successfully
(shards 0, 1, 2, 4 — 0 failed iterations across all of them, per their summary JSONs).
Shard 3 never produced a checkpoint (killed for safety before its first completed
iteration) and contributes nothing to the pooled total. **Pooled total: n=400** (up from
n=100 before this task), not the 500 that would have resulted had shard 3 not been
aborted — this is reported as 400, not rounded toward what a 5th shard might have added.

Wall-clock for the whole extension effort (from launching shard 0's extension to shard 4
finishing its 100th iteration, wall-clock timestamps): **~2.56 hours (9,208s)**, on top of
which the two concurrency-safety probes in step 1 took a combined ~11 minutes. Per-shard
wall-clock as self-reported (`*_lowmem_summary.json`, includes each shard's own mix of
3-way/2-way/1-way concurrency phases and is not directly comparable to a fixed-contention
rate): shard 0, 5,233s for 50 new iterations (~104.7s/iter); shard 1, 5,184s for 50 new
(~103.7s/iter); shard 2, 10,046s for 100 new (~100.5s/iter, ran under heavier contention
for longer); shard 4, 9,100s for 100 new (~91.0s/iter, benefited from running alone for
its final stretch).

**This did not reach the "several hundred to 1000+" target's upper end — 400 is
solidly in the "few hundred" range explicitly flagged as an acceptable, honestly-reported
outcome if 1000 isn't practical in one session.** Reaching 1000 at the observed
~90-105s/iteration/shard and a demonstrated safe ceiling of ~3-4 concurrent shards on
this specific machine (with its current other-application memory load) would need
roughly another 6-7 hours of wall-clock beyond what was spent here — mechanically
straightforward (extend the same checkpoints further with more staggered shards) but not
attempted in this pass.

**Step 4 — final percentile CIs at n=400, and a direct answer to the corroboration
question.**

| coefficient | hypothesis | Wald point estimate | Wald 95% CI | n=8 CI | n=100 CI | **n=400 CI (new)** | **n=400 median** |
|---|---|---|---|---|---|---|---|
| `E:L` | H2 | 0.023732 | [0.012658, 0.034807] | [-0.001193, 0.053131] | [-0.016351, 0.061620] | **[-0.016215, 0.067433]** | **0.023847** |
| `E:R` | H3 | 0.003528 | [-0.007594, 0.014650] | [-0.015524, 0.026300] | [-0.027791, 0.033305] | **[-0.029178, 0.033284]** | **0.002459** |
| `L:R:depth_z` | H4 | 0.000511 | [-0.007647, 0.008669] | [-0.016208, 0.024394] | [-0.018906, 0.021103] | **[-0.019505, 0.020187]** | **-0.000392** |

**Direct answer: no — H2's percentile-bootstrap CI still includes zero at n=400, and the
interval has not meaningfully narrowed going from n=100 to n=400** (width 0.0776 at
n=100 vs. 0.0836 at n=400 — if anything very slightly wider, well within what's expected
from percentile-CI sampling variability at this alpha, not evidence of a data problem).
The n=400 median (0.02385) is now very close to the Wald point estimate (0.02373) —
excellent agreement on the central estimate — but the *spread* of the resampling
distribution genuinely does not exclude zero at the 95% level, and this is no longer
attributable to small-sample noise the way it plausibly was at n=8. **This is a stable,
believable statistical fact about this particular bootstrap distribution, not an
artifact of an insufficient sample: at 400 iterations, the percentile bootstrap for H2
(`beta_EL`) does not independently corroborate the Wald-based rejection.** This does not
overturn H2's Wald-based Holm-corrected significance (p=0.000107) — the two methods are
answering related but distinct questions, and Wald remains the confirmatory analysis
throughout, per the same framing used at every smaller n in this verification pass — but
it is a genuine, non-flattering finding, reported as such rather than reframed. H3 and H4
remain "not contradicted" at n=400, unchanged from n=8/n=100 — no surprises there.
