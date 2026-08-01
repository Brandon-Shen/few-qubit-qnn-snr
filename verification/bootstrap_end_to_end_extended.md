# QMI/QIP robustness package -- Task 4: extended end-to-end nested bootstrap

**Final achieved count: n=443 (target: minimum 400, preferred 1000).
Reported exactly as achieved -- not rounded up, not extrapolated toward
1000.** 0 failed fits across all 443 draws (0.0%). Below the QMI/QIP
prompt's preferred target of 1000, but comfortably above its stated minimum
acceptable count of 400, and reached via three independently-seeded,
staggered, checkpointed shards plus the pre-existing 8-draw regression
check -- stopped at a deliberately chosen target (145/shard) rather than
run open-endedly, once that target comfortably cleared 400.

## Method (unchanged from the existing end-to-end-only bootstrap)

Same resampling hierarchy as `verification/h2h4_bootstrap_endtoend_only.md`
and the production `qnn_snr/stats/bootstrap.py`/
`verification/h2h4_bootstrap_lowmem.py` (bit-identical-output low-memory
reimplementation): outer resampling by complete matched initialization
(with relabeling for duplicate draws), inner resampling of gradient
replicates within every selected initialization x configuration x
parameter x depth x budget cell, pointwise-statistics recomputation
(including the same zero-variance eligibility rule), and a full refit of
`H2_H4_FORMULA` on `analysis_mode == "finite_shot_end_to_end"` data only,
every iteration. No pooled-mode data entered this bootstrap at any point.

## Reused draws and new shards

- **Reused as-is**: `h2h4_boot_endtoend_regression_a` (seed 266001, 8
  draws). Its duplicate check `regression_b` (same seed, independent
  from-scratch rerun, bit-identical output) is **excluded from pooling**
  throughout -- it verifies reproducibility, it is not 8 additional
  independent draws.
- **Extended in place to completion**: `h2h4_boot_endtoend_shard0` (seed
  366001, previously 16/60, now 145/145, 0 failures, 11,541s /
  ~3.21 hours) and `h2h4_boot_endtoend_shard1` (seed 376001, previously
  16/60, now 145/145, 0 failures, 11,825s / ~3.28 hours).
- **New shard, completed fresh**: `h2h4_boot_endtoend_shard2` (seed 386001
  = `366001 + 2*10000`, following the pre-existing shard-seed stride
  convention exactly), 145/145, 0 failures, 12,492s / ~3.47 hours.
- **Seed non-overlap**: verified both analytically
  (`tests/test_qmi_qip_robustness.py::test_shard_seed_ranges_cannot_overlap`)
  and empirically against the real checkpoint files
  (`verification/build_bootstrap_seed_manifest.py`: "CONFIRMED: no
  overlapping (seed, iteration) pairs among pooled ... streams", 451 total
  manifest rows including the excluded `regression_b` duplicate).

## Concurrency and resource notes

Three shards launched with 20s staggered starts. Free system RAM checked
periodically through the run: 12.9GB free before launch, 11-12.5GB free
with all three shards concurrently active (plus, for part of the run, the
concurrently-executing Task 3D leave-one-initialization-out job) -- no
memory pressure observed, no shard required termination, unlike the
earlier pooled-mode 4-way run that needed one shard killed on a near-miss.
Per-iteration wall-clock this session: roughly 43-120s/iteration across
all three shards (shard-level totals above give per-iteration means of
79.6s, 81.6s, and 86.2s respectively for shards 0/1/2) -- faster than the
historical single-stream range documented in
`verification/h2h4_bootstrap_endtoend_only.md` (80-550s/iteration,
mean~150-190s). This is reported as an observation (three same-size
single-mode shards may interleave I/O/compute more favorably than the
historical runs' conditions did), not a mechanism verified further.

## Final checkpoint summary

From `results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_checkpoints.csv`, using the fixed
deterministic pooling order (`regression_a` first, then shards by ascending
shard-id, iterations ascending within each) needed to define "the first `n`
draws" when multiple shards ran concurrently. **This order is a documented
convention for defining checkpoint prefixes, not a claim about wall-clock
arrival order** -- the `n=40` row below is therefore a different specific
draw composition than the `n=40` reported in the earlier
`verification/h2h4_bootstrap_endtoend_only.md` document (that document's
`n=40` used shard0's and shard1's full first-16 draws each; this
document's `n=40` prefix, defined once three shards existed, takes the
first 40 by shard-id-then-iteration order and lands on a slightly
different mix) -- both are valid, honestly-labeled `n=40` snapshots of
overlapping but not identical draw sets, not a discrepancy in either.
`n=600/800/1000` are **not reached** at the achieved final count (443) and
are omitted rather than estimated.

| n | Coefficient | Median | 2.5% | 97.5% | Width | Includes zero | Lower move since prev. | Upper move since prev. |
|---:|---|---:|---:|---:|---:|:-:|---:|---:|
| 40 | `beta_EL` | 0.020846 | -0.012625 | 0.055332 | 0.067957 | Yes | -- | -- |
| 40 | `beta_ER` | -0.004466 | -0.021444 | 0.016996 | 0.038441 | Yes | -- | -- |
| 40 | `beta_LRd` | -0.009713 | -0.024829 | 0.006450 | 0.031279 | Yes | -- | -- |
| 100 | `beta_EL` | 0.022765 | -0.020983 | 0.057293 | 0.078276 | Yes | -0.00836 | +0.00196 |
| 100 | `beta_ER` | -0.004216 | -0.030833 | 0.025558 | 0.056391 | Yes | -0.00939 | +0.00856 |
| 100 | `beta_LRd` | -0.010274 | -0.027224 | 0.005826 | 0.033051 | Yes | -0.00240 | -0.00062 |
| 200 | `beta_EL` | 0.023422 | -0.015124 | 0.061585 | 0.076708 | Yes | +0.00586 | +0.00429 |
| 200 | `beta_ER` | -0.002382 | -0.028957 | 0.025130 | 0.054087 | Yes | +0.00188 | -0.00043 |
| 200 | `beta_LRd` | -0.010601 | -0.024829 | 0.005711 | 0.030540 | Yes | +0.00239 | -0.00012 |
| 400 | `beta_EL` | 0.023598 | -0.015124 | 0.062726 | 0.077849 | Yes | 0.00000 | +0.00114 |
| 400 | `beta_ER` | -0.001807 | -0.030143 | 0.024791 | 0.054934 | Yes | -0.00119 | -0.00034 |
| 400 | `beta_LRd` | -0.010827 | -0.026885 | 0.006433 | 0.033318 | Yes | -0.00206 | +0.00072 |
| **443 (final)** | `beta_EL` | **0.023685** | **-0.018024** | **0.065688** | **0.083712** | **Yes** | -0.00290 | +0.00296 |
| **443 (final)** | `beta_ER` | **-0.001868** | **-0.030298** | **0.024478** | **0.054777** | **Yes** | -0.00016 | -0.00031 |
| **443 (final)** | `beta_LRd` | **-0.010811** | **-0.026975** | **0.006403** | **0.033378** | **Yes** | -0.00009 | -0.00003 |

**Endpoint trajectory, discussed directly rather than summarized by the
median alone**: for `beta_EL`, the CI **does not narrow** as `n` grows from
40 to 443 -- width goes 0.068 -> 0.078 -> 0.077 -> 0.078 -> 0.084, i.e. it
is, if anything, slightly *wider* at the final n=443 than at n=100, and the
upper endpoint drifts upward at every single checkpoint (0.0553 -> 0.0573
-> 0.0616 -> 0.0627 -> 0.0657) without ever turning over. The interval
includes zero at every checkpoint, including the final one. This pattern
-- an interval that neither narrows nor stops including zero across a
10x increase in iterations -- is what licenses, for the first time in this
package's history, language like "this is a stable, not merely
small-sample, property of the resampling distribution" for H2's bootstrap
non-corroboration (see Final interpretation below). `beta_ER`'s interval
is essentially flat by n=100 onward (width 0.056 -> 0.054 -> 0.055 ->
0.055), consistent with a well-resolved null. `beta_LRd`'s interval is the
most stable of the three across every checkpoint from n=100 onward (width
0.033 -> 0.031 -> 0.033 -> 0.033, upper endpoint pinned near +0.006
throughout) -- "stable" is used advisedly here, meaning the *interval's
shape* stopped moving well before n=443, not that the underlying question
(does H4 reflect a real effect) is resolved, which the interval alone
cannot answer since it includes zero throughout.

## Final interpretation

**H2 (`beta_EL`)**: the prespecified confirmatory decision remains the
Wald/Holm decision -- **rejected** (`p_Holm=0.00238`). The final n=443
percentile bootstrap CI, `[-0.018024, 0.065688]`, **includes zero**, so
**the bootstrap does not independently corroborate the Wald/Holm
rejection**. This is now stated with more confidence than at any earlier
n in this package's history: the interval did not narrow or move away from
zero across a full order-of-magnitude increase in iterations (n=40 to
n=443), so this is reported as a stable property of the resampling
distribution for this specific coefficient under this design, not as an
artifact of an insufficiently large bootstrap that a still-larger n would
resolve. The confirmatory rejection itself is not retroactively redefined
by this -- H2's Wald/Holm test remains the prespecified confirmatory
analysis, exactly as every other hypothesis in this paper's Holm family is
decided.

**H3 (`beta_ER`)**: no confirmatory rejection to corroborate or contradict.
The final bootstrap CI (`[-0.030298, 0.024478]`) is centered near zero and
essentially unchanged in shape from n=100 onward, consistent with the
Wald estimate (`-0.000958`, the cleanest null in the model) and with the
existing `D>=3` sensitivity fit (`-0.002128`). Inclusion of zero is not
treated as proof of equivalence -- no smallest-effect-of-interest or
equivalence test was prespecified for this coefficient.

**H4 (`beta_LRd`)**: no confirmatory rejection (`p_Holm=0.115`, the
closest of the three non-rejected hypotheses to the boundary). The final
bootstrap CI (`[-0.026975, 0.006403]`) includes zero and has been the most
stable-in-shape of the three coefficients from n=100 onward, but stability
of the *interval's shape* is not the same as resolving the underlying
near-boundary Wald result -- the interval still straddles zero, so it
neither corroborates nor contradicts the Wald test's near-miss, exactly as
at every smaller n reported for this coefficient. This is now the
best-powered (n=443, versus the earlier n=40) version of that same
"genuinely inconclusive" read, and it does not change: comparing against
the existing `D>=3` sensitivity fit (which shrinks `beta_LRd` to less than
half magnitude, `p=0.443`) and the mode-split fit (opposite signs,
conditional +0.0104 vs. end-to-end -0.0102), the extended bootstrap adds a
fourth independent line of evidence that is consistent with, not
contradictory to, the paper's existing framing of H4 as fragile rather
than a real near-miss awaiting more data.

## Material-change stop conditions -- checked explicitly

None triggered by this task:

- The extended H2 bootstrap **did not** change from including zero (at the
  earlier n=40 diagnostic) to excluding zero, or vice versa -- it includes
  zero at n=40, at every intermediate checkpoint, and at the final n=443.
- Bootstrap model-fit failures: **0 of 443 (0.0%)**, well under the 1%
  threshold, with no concentration in any particular shard or resample
  (0 failures in every one of the four streams individually).

## Files produced

- `verification/summarize_bootstrap_checkpoints.py`,
  `verification/build_bootstrap_seed_manifest.py` (infrastructure)
- `results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_iterations.parquet` (443 rows, lossless)
- `results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_summary.csv`
- `results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_checkpoints.csv` (n=40/100/200/400/443)
- `results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_seed_manifest.csv` (451 rows, includes the excluded duplicate-check stream, clearly labeled)
- `verification/_bootstrap_stream_report.json`
- `paper/scripts/make_fig10_bootstrap_endpoint_stability.py`, `paper/figures/fig10_bootstrap_endpoint_stability.pdf` (final)
- `paper/scripts/make_fig1_forest.py` (updated to read the pooled end-to-end-only file), `paper/figures/fig1_confirmatory_forest.pdf` (regenerated, n=443 for H2-H4, n=400 for H1 unchanged)
- `verification/_shard{0,1,2}_extend_stdout.log`, `verification/_bootstrap_checkpoints/h2h4_boot_endtoend_shard{0,1,2}_summary.json`
