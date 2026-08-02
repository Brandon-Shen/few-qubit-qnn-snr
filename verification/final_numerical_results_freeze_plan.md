# Final numerical-results freeze plan

**Status:** prospective provenance/reproducibility plan. It does not authorize manuscript headline edits.

After every committed analysis plan is executed, run focused and full relevant tests with headless plotting and a workspace-local pytest base directory; document the known stale Figure-0 reference test separately unless corrected by planned non-headline integration work. Regenerate all new outputs from frozen inputs into fresh staging paths and compare checksums/numeric tables before promoting them. Never overwrite corrected primary, independent-seed, robustness, descriptive, resource, or superseded sources.

Create `results/final_submission_v1/` with separated subdirectories/manifest entries for corrected primary, post-primary robustness, independent-seed, task metrics, resource accounting, conditional J, figure source data, warnings/failures, and superseded references. Include copies or immutable references plus SHA-256, source script/output, input checksum, plan commit, analysis commit, command, environment, estimate/SE/CI/p where applicable, dataset, weighting, depth, clusters, and bootstrap iterations.

Generate `final_numerical_results.{json,csv}`, `manifest.json`, `checksums.sha256`, command log, environment record, and `verification/final_numerical_results_freeze.md`. Validate schema uniqueness, referenced-file existence/checksums, figure/table source consistency, no unexplained working-tree changes, and one-command reproducibility. Use no stochastic process beyond the seeds frozen in component plans.

The human report must state corrected original H1/H1 bootstrap, independent-seed H1, depth/weighting dependence, H3 robustness category, both conditional J indices, task metrics, resource findings, every manuscript claim/table/figure needing correction, exact commit/tag, and blockers. Provide exact proposed replacement language for later human review but do not edit abstract/conclusion. Create a collision-safe annotated tag `submission-numerical-results-freeze-v1` only after all validations pass; never push.

Stop rather than tag if any input checksum changes, output cannot be regenerated, manifest reference/checksum fails, required analysis is incomplete, tests reveal an unexplained scientific failure, or the worktree contains unexplained changes.
