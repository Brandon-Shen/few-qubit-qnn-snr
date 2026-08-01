# H2 replication Stage 1 resource estimate (Phase 5)

Per `verification/h2_robustness_replication_plan.md` Section 3.3-3.4. Two
independent estimates are reported; they disagree by ~1.8x, and the
disagreement itself is reported rather than resolved by picking the
smaller number.

## Estimate 1 (primary): production's own measured wall-clock

Production's `finite_shot_end_to_end` generation at `R_rep=30`, the exact
row count Stage 1 will also produce (3,072,000 rows), took **1,560
seconds (26.0 minutes)** on this machine
(`results/production_confirmatory/run_manifest.json` step timestamps).
Stage 1 uses the identical design shape (8 configs x 5 depths x 4 budgets
x 50 inits x 30 replicates, end-to-end mode only), so this is treated as
the **primary** estimate: **~26-30 minutes**, plus `generate-exact`
(<1 minute) and model fitting (~2 minutes) = **~30-35 minutes total**
wall-clock for Stage 1 data generation and initial fit.

## Estimate 2 (cross-check): pilot benchmark extrapolation

A real pilot slice (1 config, 1 depth=4, 2 inits, R=20, end-to-end mode,
under the replication seed root 3872531887) was generated and timed:

- 640 rows in 0.182 seconds -> 3,522 rows/second measured throughput.
- RSS delta: ~1.9MB (negligible; no evidence of R-dependent memory
  blowup for this generation step).
- Linear extrapolation to the full 3,072,000-row Stage 1 design: **~872
  seconds (~14.5 minutes)**.

## Why the two estimates disagree, and which is used

The pilot's extrapolation (~14.5 min) is roughly half of production's
directly-measured time (~26 min) for the identical row count. Plausible
reasons (not confirmed, not investigated further -- out of scope for a
resource estimate): the pilot used a single mid-range depth/budget cell,
while the full run spans all 5 depths (different parameter counts) and 4
budgets; a short pilot cannot capture memory-growth or cache effects that
appear only over millions of rows; system load may differ between the two
measurements. **Production's directly-measured figure is used as the
operative estimate** because it reflects an actual full-scale run rather
than an extrapolation from 0.02% of the target row count.

## Decision point

Stage 1 (~30-35 minutes total) is **not yet executed**. Per the frozen
plan, this is a deliberate go/no-go checkpoint: Stage 1 commits real
wall-clock time to generating genuinely new quantum-simulation data (as
opposed to Phase 2-4, which only re-analyze already-frozen data). Stage 2
(`R_rep=300`), if triggered per the plan's predefined expansion rule,
would cost roughly 10x Stage 1's generation time (~4.3-5 hours), separately
from Stage 1's cost.
