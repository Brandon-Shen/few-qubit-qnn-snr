# Final numerical-results freeze plan

**Status:** prospective provenance/reproducibility freeze; no direct abstract/conclusion/title/headline edits.

Prerequisites are frozen/audited H3, J, task metrics, resource accounting, completed fig0 reconciliation, and passing scientific tests. Component outputs remain immutable. Build fresh staging `results/final_submission_v1_staging/`, compare, then promote only if `results/final_submission_v1/` is absent. Include corrected primary, H1 bootstrap/seed/depth, H3, J, task metrics, resources, figure sources, warnings/failures, superseded references, plans/commits/checksums/environment/commands.

The row key is `(analysis_identifier,dataset,estimand,depth,weighting,estimator_mode,interval_method)` with explicit nulls. Required fields: status, response, estimate, SE, CI/method, raw/adjusted p, clusters, bootstrap count, source script/output, plan/analysis commits, input checksum. Preserve component multiplicity; create no family. Superseded values are labeled only. Generate JSON/CSV, manifest, checksums (excluding itself/self-reference), commands, environment, and `verification/final_numerical_results_freeze.{md,json}`. Report exact replacement language for later review, not manuscript edits.

Run focused/full headless suites with workspace temp, fig0 path test, deterministic fresh regeneration/checksum/numeric comparison, manifest schema/references, and clean-status audit. No new resampling. Stop for incomplete input, mismatch/nondeterminism, unexplained scientific failure/worktree change, or unreconciled fig0. After freeze commit/provenance, create unused collision-safe annotated tag `submission-numerical-results-freeze-v1` (or next vN), never overwrite or push.
