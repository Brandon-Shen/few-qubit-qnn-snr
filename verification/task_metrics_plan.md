# Prepared-state task-metrics plan

**Status:** post-primary descriptive analysis, frozen before new task-metric aggregation.

## Question and inputs

Describe prepared-state energy and target overlap at initialization, without implying optimization. Use frozen original and independent-seed exact-generation inputs/outputs and the authoritative circuit, cost, Hamiltonian, and seed code. Prefer deterministically regenerating terminal-block exact states from recorded configuration/depth/initialization seeds only if metrics are not already stored; validate regeneration against existing exact gradients/cost metadata before aggregation.

Require all 8 configurations, depths `{1,2,3,4,6}`, matched initialization identity, 50 clusters per dataset, and one state metric per `(dataset,initialization,configuration,depth)`. Remove only exact budget/parameter duplicates after proving metric identity; never weight a state by parameter count or budget. Confirm both L objectives share the same ground state from `qnn_snr.hamiltonian`.

## Metrics and summaries

Calculate terminal-block prepared-state TFIM energy, normalized energy `(E-E0)/(Emax-E0)`, fidelity `|<psi0|psi>|^2`, and infidelity `1-fidelity`, regardless of active L. Assert fidelity/infidelity in `[0,1]` and normalized energy within spectral bounds up to `1e-10`; reject duplicate overcounting.

Summarize separately by dataset/configuration/depth with count, mean, median, SD, Q1, Q3, and IQR. Initialization-cluster percentile intervals for means use 2,000 deterministic resamples (original seed `355001`, independent `355002`), resampling complete initialization profiles and checkpointing every 100. This is descriptive; no p-values or factorial hypothesis tests.

Outputs: `results/task_metrics/prepared_state/` tidy Parquet/CSV, summaries, bootstrap draws/intervals, bounds validation, table/figure source data, supplement-ready table and figure, and a note assessing only whether an obvious descriptive task-metric pattern accompanies gradient interactions. Stop if state regeneration is not uniquely determined, target states differ, bounds fail beyond tolerance, or duplication cannot be resolved authoritatively.
