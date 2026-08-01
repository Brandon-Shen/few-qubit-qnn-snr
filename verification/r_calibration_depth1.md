# Task D — R-calibration re-check for depth=1, `max_R=500`

Scope: `results/production_confirmatory/pilot_replicate_selection.json` (the confirmatory run's own pilot
output) showed 4 of 8 representative cells — all four at nominal depth=1 — failing to
converge at the confirmatory config's `max_R=200` ceiling. This re-runs
`select_replicate_count` (`qnn_snr/pilot.py`, the same function
`pilot-replicates` calls) restricted to those 4 depth=1 cells, with `max_R` raised to
500. Does not touch `results/production_confirmatory/pilot_replicate_selection.json` or any confirmatory
output.

Script: `verification/r_calibration_depth1_check.py`. Full output:
`verification/pilot_replicate_selection_depth1_maxR500.json`. Wall clock for the
entire re-check (4 cells, `R` ramped 30→500 in steps of 10 for the 3 that didn't
converge): **43.4s** — this calibration search itself is cheap; the finding below is
about the *statistic*, not about compute cost.

## 1. Result: 1 of 4 cells converges, 3 still don't at R=500

| config | depth | budget | `selected_R` (max_R=200, from committed run) | `selected_R` (max_R=500, this check) | `snr_halfwidth` @ R=500 | naive extrapolated R for 0.25 target |
|---|---|---|---|---|---|---|
| 1 | 1 | 250 | not converged | **270** | 0.2294 (converged) | — |
| 1 | 1 | 2000 | not converged | not converged | 0.5418 | ~2,350 |
| 8 | 1 | 250 | not converged | not converged | 0.2834 | ~640 |
| 8 | 1 | 2000 | not converged | not converged | 0.8010 | ~5,130 |

Compare: the 4 depth=6 representative cells (already in
`results/production_confirmatory/pilot_replicate_selection.json`, not re-run here) converged at R=40–70 —
1.3–2.3× the committed R=30. The one depth=1 cell that converges here needs 9× the
committed R (270 vs 30); the extrapolated requirement for the worst depth=1 cell
(config 8, budget 2000) is ~170× the committed R.

The mean-halfwidth criterion (`abs_halfwidth_tolerance=0.05`) is never the binding
constraint at depth=1 — it's satisfied at R=30 already (values 0.004–0.018 throughout).
**The SNR-halfwidth criterion (`0.25`) is what fails to converge.** Extrapolated R
requirements use a naive `halfwidth ∝ 1/√R` (CLT) scaling from the R=500 value; this is
a rough order-of-magnitude estimate, not a precise projection — the actual trajectories
are noisy (bootstrap-of-a-bootstrap: `snr_halfwidth` is itself a Monte Carlo statistic
with its own sampling variance, visible in the non-monotonic wobble between consecutive
R steps in the full history, e.g. config 1/budget 2000 R=480→490→500: 0.6156→0.5976→0.5418).

## 2. A real, physically sensible pattern, not calibration noise

At every R checked, the **budget=2000 cells have a worse (larger) `snr_halfwidth` than
the budget=250 cells at the same configuration** — counter to the naive intuition that
more shots per replicate should reduce noise everywhere. This is consistent with a
known instability of ratio statistics: SNR = |mean|/std is a ratio of two
gradient-derived quantities; at higher shot budget, per-replicate measurement noise is
smaller, so `std` across R replicates is itself smaller and more sensitive to sampling
variability — dividing by a smaller, noisier denominator amplifies the *relative*
noise in the SNR statistic even though the underlying gradient estimate is more
precise in absolute terms. This is worth reporting as a substantive finding about
depth=1 in this design (single Ry+CNOT block, only 4 gate parameters, minimal
entangling structure to generate a stable gradient-noise distribution), not dismissed
as a fluke of this particular pilot run.

## 3. Cost of actually re-collecting depth=1 data at a higher R

Benchmarked directly (`_pilot_replicate_gradients`, the same core call
`generate_shot_rows` uses per replicate): **~0.55 ms/replicate** at depth=1, for either
budget tested. This is cheap because a depth=1 circuit is a single Ry+CNOT block —
the cheapest possible cell in the whole design. Extrapolating to a full depth=1
dataset regeneration (50 inits × 8 configs × 4 budgets × both finite-shot modes ×
`R`):

| target R | replicate computations | estimated raw compute time |
|---|---|---|
| 270 (converges cell 1) | 864,000 | **~7.9 min** |
| 500 (this check's ceiling) | 1,600,000 | **~14.6 min** |
| 643 (extrapolated for config 8/budget 250) | 2,057,600 | **~18.8 min** |

This estimate covers only the raw gradient-generation step (the dominant cost); it
does not include re-running `aggregate`/`fit`/`report` on the merged dataset
afterward, which are separate, already-demonstrated-fast steps on data of this scale
elsewhere in the pipeline. **The practical conclusion is the opposite of what the
non-convergence might suggest**: depth=1 is so cheap to simulate that re-collecting
its finite-shot data at R=270–500 is a matter of minutes, not the "11 days" problem
that makes the H2–H4 bootstrap infeasible (Task C). Compute cost is not the reason to
avoid re-collecting depth=1 data at a higher R.

## 4. Recommendation

Two separate questions, two separate answers:

- **Should depth=1's committed R be raised for a future confirmatory run?** Yes, and
  cheaply — R≈270 converges one cell outright and gets the other three substantially
  closer to the 0.25 target (0.28, 0.54, 0.80 vs their R=30 values of 0.69–2.81), all
  for ~8 minutes of compute. This does not require Task C-style sharding or overnight
  runs; it's a same-session-tractable improvement if a re-collection is in scope.
- **Should this run's existing depth=1 data (R=30) be discarded or re-collected before
  trusting `results_and_discussion.md`'s H1–H4 conclusions?** No — not on this
  evidence alone. `results_and_discussion.md` already carries an explicit, correctly-scoped
  caveat ("depth=1 estimates rest on a thinner, noisier effective sample than
  deeper-depth estimates") rather than treating R=30 as fully calibrated. This
  re-check confirms that caveat is well-founded (the SNR-halfwidth criterion
  genuinely doesn't converge for 3 of 4 depth=1 cells even at 16.7× the original
  ceiling) and adds a second, independent finding worth folding into that same
  caveat: **the non-convergence itself is asymmetric by budget** (worse at
  budget=2000 than budget=250), which the current write-up doesn't distinguish.

**Recommended next step, not executed here per the task's scope (calibration only,
not a re-run):** if a future run re-collects depth=1 data, target R≈270–300 as a
practical middle ground (converges/nearly-converges 3 of 4 cells cheaply) rather than
chasing the ~5,000 needed for the worst cell (config 8, budget 2000) — that cell's
instability looks structural (ratio-statistic sensitivity at high budget/low depth),
not something a moderate R increase will resolve, and is worth reporting as a finding
about this design's depth=1 cells rather than a target to hit.
