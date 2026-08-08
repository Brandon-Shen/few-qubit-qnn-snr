# H1 submission-finalization blocking report

**Status:** blocked before analysis-plan commit and before any new analysis output was generated.

## Blocking condition

The requested H1 estimand cannot be frozen without choosing between two materially different factor codings:

- The manuscript (`paper/main.tex`, Methods) and the submission-finalization request define `E`, `L`, and `R` as effect coded `{-1/2,+1/2}` and state that lower-order coefficients average over the other factorial conditions.
- Both frozen exact datasets store `E`, `L`, and `R` as integer `{0,1}` columns.
- `qnn_snr/stats/models.py::H1_FORMULA` uses those columns directly in `a ~ E*L*R + depth_z + E:depth_z + L:depth_z + R:depth_z`.
- `qnn_snr/stats/models.py` explicitly documents that the columns are numeric `0/1`; `build_h1_dataset()` transforms only the response and does not recode the factors.
- The synthetic model tests in `tests/test_models.py` likewise construct and fit `0/1` predictors.
- The current production H1 coefficient (`0.004345925498518687`) is therefore provenance-linked to the direct `0/1` implementation, despite the manuscript's effect-coding description.

Because the model contains `E:L:R`, this is not a cosmetic intercept/main-effect reparameterization for the target coefficient. With direct `0/1` coding, `E:L` is the two-factor interaction at `R=0`. With centered `{-1/2,+1/2}` coding, `E:L` is the two-factor interaction averaged across the two `R` conditions. The requested target `eta_EL` therefore changes meaning.

This meets the stated stop condition: proceeding would require an unplanned change in coding or silently retain a coding that contradicts the manuscript and explicit task specification.

## Evidence inspected

- Frozen original input: `results/production_confirmatory/raw/exact.parquet`, 25,600 rows, SHA-256 `77e54bed863de79be0d1ebb4937f015fe29a1b1cb5d58e0f216f3acd4b9bb542`.
- Frozen independent-seed input: `results/h2_replication_v1/_pipeline_output_stage1/raw/exact.parquet`, 25,600 rows, SHA-256 `70c562c2724f5310330c2ea4bf10efa4b0fd76327dde8becba9ffe1f7d602715`.
- In both inputs, each of `E`, `L`, and `R` has unique values `[0,1]`; neither input contains precomputed centered factor columns.
- Both inputs contain exactly one statevector-exact row per `(initialization_id, configuration_id, depth, parameter_id)` key, so budget duplication is not the source of this discrepancy.
- Both inputs contain 50 initialization clusters, all eight configurations, depths `{1,2,3,4,6}`, and the same depth scaling.
- Authoritative implementation: `qnn_snr/stats/models.py`.
- Manuscript statement: `paper/main.tex`, mixed-model Methods paragraph beginning “Let i index initialization”.
- Existing result: `results/production_confirmatory/confirmatory_hypotheses.csv`.

## Work completed safely

- Created local branch `submission-prep-h1-finalization-20260802`.
- Created annotated pre-analysis tag `pre-h1-finalization-20260802` at baseline commit `e69ce1c6ab0f9b93b43c6744391540830ed7ae0b`.
- Generated and committed pre-analysis freeze records in commit `295f7968a4c3f15b176c1d22a4a5401c3b4dabb4`.
- Deliberately excluded untracked local tooling configuration `.claude/settings.local.json`.
- Located the authoritative `J_EL` implementation and its trace to the reported value; no new `J_EL` analysis was run.

## Work deliberately not performed

No six-file analysis plan was committed because its required “exact factor coding” field cannot truthfully be frozen. No independent-seed H1 fit, new bootstrap iteration, depth/weighting model, `J_EL` bootstrap, task-metric analysis, resource-accounting analysis, manuscript edit, or final-results freeze was run or generated. Existing results were not modified.

## Required adjudication

An authoritative decision is needed between:

1. **Preserve the historical implementation and estimand:** retain direct `0/1` coding for all original and independent-seed H1 work, explicitly redefine `eta_EL` as the `E:L` interaction at `R=0`, and correct the manuscript's effect-coding/averaging description; or
2. **Preserve the manuscript-defined estimand:** recode all three factors to `{-1/2,+1/2}`, treat the resulting original-data H1 coefficient and inference as a corrected analysis, preserve the historical `0/1` outputs as superseded, and reassess the H1 member of the original Holm family without silently replacing it.

A third scientifically transparent option is to preserve the historical `0/1` H1 as the protocol-derived primary analysis and add the centered-effect-coded fit as a clearly labeled coding sensitivity. That option still requires specifying which coefficient is the manuscript's `eta_EL`; it cannot be inferred from the current contradictory records.

After adjudication, the six plans must be written and committed before inspecting any newly fitted result, as originally required.
