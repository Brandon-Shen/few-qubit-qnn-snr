# Task C — Reduced-iteration sharded bootstrap for H1/H2 (and H3/H4 as a byproduct)

**Actual iteration counts achieved: H1 = 400 (of a 2000 target), H2–H4 = 8 (of a
100–150 target). This is a reduced-iteration sensitivity check, not the
preregistered 2000-iteration confirmatory bootstrap (`configs/confirmatory.yaml`
`stats.bootstrap.iterations: 2000`) — the H2–H4 result in particular (n=8) is too
small to be a reliable percentile-CI estimate on its own and should not be cited as
if it were. Do not treat this as replacing or superseding the Wald-based
`confirmatory_hypotheses.csv` results.**

## 0. What actually happened (read before the numbers)

The original plan — 2000 sequential H1 iterations, and H2–H4 sharded across as many
of this machine's 20 CPU cores as reasonable — did not survive contact with two real
constraints:

1. **H2–H4 is memory-bound, not CPU-bound.** A single H2–H4 bootstrap iteration
   (full resample of the combined 6,144,000-row finite-shot dataset, both modes,
   recomputing pointwise statistics and refitting the mixed model) peaks around
   **16GB working set**. Running 2 shards concurrently was attempted; free system
   memory dropped to **590MB** within seconds (caught by an active memory monitor
   before anything crashed). The second shard was killed immediately. **Effective
   usable parallelism on this machine for this workload is 1, not 20** — this is
   itself a finding worth recording alongside the result, since it directly bears on
   what "shard across available parallelism" can mean here.
2. **Long-running background processes were killed once, mid-run, for reasons outside
   this check's control** — both the H1 bootstrap (at 150/2000 iterations) and the
   first H2–H4 shard attempt (0/50, before its first checkpoint) were terminated
   together partway through the first attempt. Checkpointing meant H1's 150
   completed iterations survived; the H2–H4 attempt had made no checkpoint yet and
   lost its partial progress entirely. Both were relaunched with per-iteration
   checkpointing (`checkpoint_every=1` for H2–H4, `=5` for H1) specifically so a
   second interruption would lose at most one iteration's work, and the session was
   kept continuously active (foreground polling instead of a detached hand-off) for
   the remainder of the run to avoid a repeat.

Given these two constraints, the targets were revised downward **in-flight**, not
silently rounded up after the fact: H1 to 400 total iterations (resumed from the
surviving 150-iteration checkpoint, seed 55001, checkpoint:
`verification/_bootstrap_checkpoints/h1_boot.parquet`), H2–H4 to a single stream of 8
iterations (seed 66001 via the "shard 0" script — the sharding *mechanism*
(`verification/run_h2h4_bootstrap_shard.py`, `verification/combine_h2h4_shards.py`)
was built and works as designed, but only one shard could actually run given the
memory ceiling found in (1)).

**A wall-clock oddity worth flagging rather than hiding**: a direct single-iteration
benchmark of the combined H2–H4 dataset (run in isolation, before any of this) took
327.8s. The actual 8-iteration production run's *reported* wall clock
(`time.time()` inside the script, `verification/_bootstrap_checkpoints/h2h4_boot_shard0_summary.json`)
was **34,988s (~9.7h) for 8 iterations — an average of ~4,373s/iteration**, over 13x
the isolated benchmark. All 8 iterations succeeded (no failed fits) and the resulting
draws look scientifically sane (see §2) — nothing suggests the *computation* was
wrong, only that it took far longer in practice than the isolated single-iteration
timing predicted. The most likely explanation, based on directly observing this
session's own progress-polling logs, is that wall-clock elapsed noticeably faster
than actual compute-bound progress during the gaps between this check-in's own tool
calls — consistent with background compute being throttled or effectively paused
during those gaps rather than running at full speed continuously. This wasn't
independently confirmed against OS-level scheduling data, so it's reported as the
best available explanation, not a verified root cause. **Practical consequence**:
per-iteration cost benchmarked in isolation is not a reliable predictor of
production wall-clock for a long unattended background run in this environment —
plan future runs of this kind around the actual observed completion rate, not the
isolated benchmark.

## 1. H1 (exact-signal) bootstrap — 400/400 successful

Seed 55001, checkpointed resume from an earlier 150-iteration checkpoint. Wall clock
for the final 250-iteration increment: 1,889s (~31.5 min; ~7.6s/iteration under
concurrent load from the H2–H4 run, vs. ~4.8s/iteration measured in isolation earlier
— consistent with genuine CPU contention between the two concurrent processes, a much
smaller and more explicable effect than the H2–H4 wall-clock oddity above). 0 failed
iterations.

| coefficient | Wald point estimate | **Wald 95% CI** (`results/confirmatory_hypotheses.csv`) | **Bootstrap percentile 95% CI (n=400)** |
|---|---|---|---|
| `eta_EL` (H1) | 0.004346 | [0.001349, 0.007343] | **[0.000810, 0.008027]** |

The bootstrap CI **excludes zero**, same as the Wald CI, and is centered in a similar
place (slightly wider, shifted marginally down at the low end). This is a genuine,
non-Wald corroboration of H1's rejection direction — the first one this run has had
(`results_and_discussion.md` §0.2 flagged this as completely absent). 400 iterations
is a reasonable, if not fully publication-scale, sample for a percentile CI on a
single coefficient — this result carries real weight, more than the H2–H4 result
below.

## 2. H2–H4 (estimator-SNR) bootstrap — 8/8 successful, single stream

Seed 66001, `verification/_bootstrap_checkpoints/h2h4_boot_shard0.parquet`. All three
target coefficients come from the same 8 refits (each refit produces `E:L`, `E:R`,
`L:R:depth_z` simultaneously):

| coefficient | hypothesis | Wald point estimate | **Wald 95% CI** | **Bootstrap percentile 95% CI (n=8)** | bootstrap median |
|---|---|---|---|---|---|
| `E:L` | H2 (`beta_EL`) | 0.023732 | [0.012658, 0.034807] | **[-0.001193, 0.053131]** | 0.021502 |
| `E:R` | H3 (`beta_ER`) | 0.003528 | [-0.007594, 0.014650] | **[-0.015524, 0.026300]** | 0.005858 |
| `L:R:depth_z` | H4 (`beta_LRd`) | 0.000511 | [-0.007647, 0.008669] | **[-0.016208, 0.024394]** | 0.000276 |

The 8 raw draws (`verification/h2h4_bootstrap_combined_draws.parquet`):

| iteration | E:L | E:R | L:R:depth_z |
|---|---|---|---|
| 0 | 0.054059 | -0.016488 | 0.020936 |
| 1 | 0.000400 | 0.002201 | 0.025128 |
| 2 | 0.048757 | -0.003560 | -0.005057 |
| 3 | 0.025612 | 0.011031 | 0.010492 |
| 4 | 0.045398 | 0.015022 | -0.009011 |
| 5 | 0.016545 | 0.009514 | 0.005608 |
| 6 | -0.001531 | -0.010978 | -0.017384 |
| 7 | 0.017392 | 0.028692 | -0.010662 |

**Read this table with real caution — n=8 is not a reliable percentile-CI sample.**
`np.percentile` at 2.5/97.5 on 8 sorted points is essentially interpolating between
the smallest 1-2 values and the largest 1-2 values; a single unusual draw (e.g.
iteration 0's `E:L=0.054`) visibly drags the upper bound. This is not a criticism of
the mechanism (the sharding/combine code, `run_h2h4_bootstrap_shard.py` +
`combine_h2h4_shards.py`, works correctly and pools draws as designed — it would
produce a trustworthy CI at n=100+) — it's a direct consequence of only 8 iterations
having been achievable given the memory and wall-clock constraints in §0.

**What this small sample does and doesn't support:**

- **H2 (`E:L`)**: the bootstrap median (0.0215) sits close to the Wald point
  estimate (0.0237) — directionally consistent — but the percentile CI is wide enough
  to *include* zero (barely: [-0.0012, 0.0531]), unlike the Wald CI. This is **not**
  evidence against H2 — with n=8, a CI this wide is expected sampling behavior, not a
  contradiction of the Wald-based rejection. It simply means 8 iterations is not
  enough to independently corroborate H2's significance the way the H1 check above
  managed to for `eta_EL`.
- **H3 (`E:R`) and H4 (`L:R:depth_z`)**: both percentile CIs include zero, consistent
  with their existing null results — but this was already true of the Wald CIs, so
  this adds little beyond "not contradicted," which is the weakest possible form of
  corroboration.

## 3. Bottom line

- H1 got a real, if reduced-scale, non-Wald corroboration: 400 bootstrap iterations
  is enough to say the percentile CI for `eta_EL` also excludes zero, in the same
  direction as the confirmatory Wald result. This is worth citing as partial support
  — clearly labeled as n=400, not n=2000.
- H2–H4 did not get a comparably meaningful check. 8 iterations is a real result (no
  failed fits, sensible-looking draws) but is far too small a sample to treat as
  either corroborating or challenging the Wald-based H2/H3/H4 conclusions. It is best
  read as a demonstration that the sharding mechanism works end-to-end
  (script → checkpoint → combine → percentile CI) at production scale on real data,
  not as a statistically meaningful cross-check in its own right.
- The dominant obstacle was not raw compute time but **memory** for H2–H4 (limits
  this machine to 1 concurrent stream) and **environment-level wall-clock overhead**
  during a long unattended run (§0) that made the achievable iteration count far
  lower than the per-iteration benchmark predicted. Both are recorded here as
  operational findings for anyone attempting a fuller version of this bootstrap on
  similar hardware — future attempts should budget wall-clock around observed
  production throughput (~4,373s/iteration for H2–H4 in this run), not the isolated
  single-iteration benchmark (328s/iteration), and should not assume core count
  translates into usable parallelism for this specific workload.
