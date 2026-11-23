# Stage 3: post-audit vector-preserving bootstrap sensitivity

Created 2026-11-22T17:40:47.987532+00:00. **Status: 1,000 accepted target reached.** Stop reason: `accepted_target_reached`. This is the separately authorized full sensitivity following the validated November 12 pilot; it is not a preregistered or replacement primary analysis.

## Procedure and provenance

The full run used master seed 2026112103, distinct from the pilot's 2026111203, deterministic iteration/copy/vector-cell keys, and the byte-identical validated vector engine. The inherited literal `pilot` token remains part of that engine's RNG key format; the distinct master seed separates full-run streams. No pilot or control draws entered this sample. All scientific inputs, model formulas, eligibility rules and optimizer fallback/acceptance policies were retained. H1 was not refit. Source archive SHA-256: `22b5e761f461c6bfde7a60a4efa7ac13bc59ae003488be84d2f0c1e57ddb7f39`. Plan and code hashes are pinned in `full_plan.json`; per-draw lineage, model-input hashes, warnings and covariance records are retained under `fits/`.

Outer draws retain 50 complete matched initialization clusters with separate copy IDs. Inner draws resample 30 entire signed-gradient vectors jointly across parameters within each configuration/depth/budget/mode, with distinct streams across vector cells. SNR uses ddof=1 SD, unchanged exact-zero handling, finite-SNR eligibility recomputed in each draw, and the historical asinh response. The direct REML model retains the initialization random intercept and copy/depth/parameter variance component; all 14 fixed effects are transformed to centered coding. H2-H4 and simple H3 contrasts share each accepted fit. No new quantum experiment, collision-deletion sensitivity, production-code edit or manuscript edit was performed.

## Counts and limits

Attempted vector resamples: **1000**; accepted coefficient draws: **1000**; failed, rejected or interrupted: **0**. Actual model fits started: 1000. Every reserved attempt consumes an iteration even if interrupted before fitting; completed valid result checkpoints are recovered without refitting. Statuses, convergence, optimizer fallbacks, singularity flags and eligibility changes are reported in CSV/JSON files. Failed iterations are not hidden or replaced with chosen seeds.

The authorized limits were 1,000 accepted draws, 1,200 attempts, one worker/one BLAS thread, 8,000,000,000-byte sampled worker RSS and a fixed absolute 36-hour deadline. Restarting never resets that deadline. Per-launch resource traces and termination reasons are under `launches/`; the Windows job object terminates the worker if its controller dies. RSS was checked at 0.1-second intervals, so instantaneous peaks between samples may be missed. This reporting step performs no model fits. If the accepted target is not reached, all intervals below are explicitly provisional and no budget is automatically extended.

## Procedure-level comparison

These are unadjusted 95% linear-percentile intervals, not a newly defined Holm family. Original H1-H4 estimates, Wald intervals and Holm decisions remain historical results of the adopted analyses. The saved comparison also records endpoint differences, widths/ratios, medians, SD/IQR and actual inference classifications.

| Quantity | Frozen component-wise interval | Post-audit vector interval | Vector classification |
|---|---|---|---|
| H2 | [-0.016240, 0.045992] | [-0.015673, 0.045908] | includes_zero |
| H3 | [-0.031375, 0.009563] | [-0.032595, 0.008511] | includes_zero |
| H4 | [-0.025964, 0.005863] | [-0.026397, 0.007255] | includes_zero |
| H3_L0 | [-0.029117, 0.024560] | [-0.030918, 0.025868] | includes_zero |
| H3_L1 | [-0.049490, 0.007197] | [-0.048136, 0.009100] | includes_zero |
| H3_average | [-0.031375, 0.009563] | [-0.032595, 0.008511] | includes_zero |

Quantities whose zero-crossing classification differs: **none observed among estimated intervals**. This statement describes the sampled procedures; endpoint Monte Carlo uncertainty must also be considered. The six rows include the intentional H3/H3_average duplicate; simple H3 contrasts are post-primary, not additional confirmatory tests.

`endpoint_monte_carlo_rank_intervals.csv` reports binomial/order-statistic uncertainty for each historical and new endpoint, with explicit one-based rank definitions and achieved binomial rank coverage. These ranges quantify finite bootstrap simulation precision; they are not additional scientific confidence intervals. Coefficient comparisons are unpaired distributions from different RNG streams. Differences combine procedure effects and finite Monte Carlo variation; the procedure was not selected for significance. Results are reported whether they strengthen or weaken evidence.

## Scientific disposition

The within-vector dependence defect in the historical procedure remains independently confirmed. This run measures the interval/distribution consequences of the specified vector-preserving sensitivity on the frozen archive; it does not prove nominal coverage or validate the complete mixed-model/bootstrap assumptions. IA-001's cross-initialization RNG reuse remains in the inputs, and this analysis does not repair it. IA-007's historical pilot lineage remains a separate documentation/provenance issue. No finding is automatically marked resolved, and no submission-readiness verdict is made.

Protected source hash mismatches observed at finalization: 0; prior-stage artifact mismatches: 0. Any mismatches are listed in `final_verification.json`; they cannot be attributed to this runner without further evidence. Accepted checkpoint hashes and sampled first/middle/last complete resampling lineages were independently checked. The original frozen percentile references were reconciled before comparison.

## Reproduction and next checkpoint

Launch command: `python -B run_full.py` from this run directory. Crash recovery within the same fixed deadline: `python -B run_full.py --resume`. Explicit stop: `python -B run_full.py --stop`. The OS lock prevents a second controller/worker; a finalized run rejects additional fitting. Reproduction of scientific draws uses the pinned engine, full master/iteration and source identities, and is subject to the approved fit budget. Do not overwrite this evidence or rerun it as a new primary analysis.

Machine-readable coefficients, intervals, comparisons, diagnostics, resource records and hashes are retained. **Stage 3 stops here. Stage 4, manuscript edits, additional sensitivities and any budget extension require separate approval.**
