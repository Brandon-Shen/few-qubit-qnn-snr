# Measurement and resource-accounting plan

**Status:** implementation audit and descriptive accounting, frozen before generating new resource tables.

## Scope and sources

Inspect `qnn_snr/costs.py`, `gradients.py`, `budget.py`, `circuits.py`, `hamiltonian.py`, configuration/run manifests, raw finite-shot schemas, and existing resource records. Document implemented simulator behavior, not an idealized hardware protocol.

For global infidelity determine projector/basis/inverse-preparation behavior, estimator conversion, settings/jobs, represented target gates, included and omitted costs, and whether “one basis” is technically accurate. For TFIM energy record Hamiltonian terms, commuting/basis grouping, settings, per-basis allocation, remainder handling, and estimator. Separately document conditional and end-to-end shifted-node, forward-feature, and objective-observable jobs; exact versus resampled quantities; nonlinear re-encoding; and complete-gradient budget distribution.

## Table and invariants

Generate one row per `(configuration,E,L,R,D,B,estimator_mode)` for original implemented design. Include total allocated shots/jobs, shifted jobs, forward-feature jobs, observable settings, min/median/mean/max shots per job, remainder allocation, zero-shot jobs, and gate/cost omissions. Deterministic allocation has no stochastic seed.

Tests require total allocated shots exactly equal B, nonnegative integer allocations, no dropped jobs, reproducible allocation, correct job-count differences including the manuscript's approximate D=6 27% statement, and joinability of every zero-variance pointwise cell to its allocation record. Join zero-variance cells descriptively without causal claims.

Outputs: `verification/measurement_resource_accounting.md`, `results/resource_accounting/resource_table.{csv,parquet}`, `measurement_protocol.json`, `zero_variance_resource_join.csv`, tests, and source manifest. State prominently that total shot budget—not shots per circuit, jobs, physical gates, noise, calibration, or wall-clock cost—is matched. Stop if code paths cannot determine estimator behavior, allocations disagree with raw records, or invariants fail.
