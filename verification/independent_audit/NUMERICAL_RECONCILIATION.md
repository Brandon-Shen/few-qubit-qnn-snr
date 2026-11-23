# Numerical reconciliation

The checked current H1–H4 estimates, Wald/Holm quantities and archived bootstrap endpoints match the frozen artifacts and the reported rounded values. The broader audit found ten unresolved findings, including methodological and provenance issues that matching numbers do not resolve. No statistical model or scientific bootstrap was refit during this audit.

## Numerical authority

Entry point: `results/final_submission_v1/manifest.json`, SHA-256 `c5a046541088fc35c363d3eb4519a34170f65e232ad214b0f8cd095bca4abc43`. Coefficients/SE/Wald/p values come from `results/primary_corrected/effect_coded/corrected_confirmatory_hypotheses.csv`; percentile summaries come from `corrected_bootstrap_intervals_current_draws.csv` in that directory. `stage4_primary_authority_map.csv` distinguishes these paths and hashes. `stage4_result_source_map.csv` maps all 347 frozen rows. Superseded, conditional and direct-coded historical results were retained only in explicitly labeled contexts.

All 19 embedded component hashes and six freeze self-checksums match; CSV/JSON tables agree and row keys are unique. Five hashes in the separate `component_references.json` conflict with embedded references (IA-003). Bootstrap rows omit the actual endpoint-source path (IA-004). These are unresolved provenance defects, not numerical substitutions.

## H1–H4

| Hypothesis | Estimate | SE | Raw p | Holm p | Wald 95% CI | Archived-draw bootstrap 95% CI |
|---|---:|---:|---:|---:|---|---|
| H1, exact E_c:L_c | 0.004043 | 0.001081 | 0.000185 | 0.000739 | [0.001924, 0.006162] | [0.000473, 0.007535] |
| H2, end-to-end E_c:L_c | 0.014338 | 0.005145 | 0.005321 | 0.015963 | [0.004255, 0.024422] | [−0.016240, 0.045992] |
| H3, end-to-end E_c:R_c | −0.011615 | 0.005144 | 0.023937 | 0.047875 | [−0.021697, −0.001534] | [−0.031375, 0.009563] |
| H4, end-to-end L_c:R_c:depth_z | −0.010179 | 0.005362 | 0.057658 | 0.057658 | [−0.020688, 0.000331] | [−0.025964, 0.005863] |

Normal p-values, 1.959963984540054-based Wald intervals and a single four-test Holm family were independently recomputed from archived estimate/SE values. H1–H3 reject by Wald/Holm at .05; H4 does not. Only H1's bootstrap interval excludes zero. This supports positive H1 interaction in the adopted analysis, procedure-sensitive finite-shot H2/H3 findings, and unresolved H4. It does not establish all inference procedures as valid or optimization performance improvements.

Main372/428/432/436 and supplement88–111 match within their displayed precision. Later repeated occurrences are linked in the final 277-row numerical comparison. H2/H3 Wald significance must not be described as bootstrap corroboration.

## Centered coding, models and eligibility

Factors use E−1/2, L−1/2 and R−1/2. Five-depth standardization gives mean3.2 and population SD1.7204650534085253. Independent direct/centered design matrices on 25,600 exact and 101,891 eligible end-to-end rows have equivalent column spaces and predictions using archived coefficients (maximum prediction error 3.53e−14). Full archived fixed coefficients transform to target values within1.36e−14. Centered E:L is direct E:L+0.5E:L:R; centered E:R is direct E:R+0.5E:L:R; H4 is unchanged. This is fixed-design/point-estimate verification, not an independent REML/covariance fit.

The inspected formulas retain three-way factors and depth moderation; finite-shot models add log2 budget. Initialization intercepts and initialization/depth/parameter variance components are present; no observation weighting or random slopes are supplied. Fit convergence, optimizer comparisons, residual adequacy, sensitivity and LOO fit statuses remain archived evidence where not explicitly recalculated.

| Mode | Cells | Zero variance | Eligible finite-SNR cells |
|---|---:|---:|---:|
| End-to-end | 102,400 | 509 | 101,891 |
| Conditional | 102,400 | 1,324 | 101,076 |

All cells store30 replicates; all1,833 zero-variance means are zero and all occur under L=0. Eligible primary rows retain50 initialization clusters and3,200 nested levels. Include-zero sensitivity construction recovers102,400 end-to-end rows by setting the509 flagged SNRs to0; its model was not refit. Eligibility is objective-linked selection, not verified random missingness. See [stage 4](STAGE_4_FROZEN_PRIMARY_RECONCILIATION.md).

## Bootstrap

Archived original H1 and independent-seed H1 each contain2,000 unique included draws; H2–H4 contain1,000. Independent centering and explicit linear percentile interpolation reproduce endpoints/medians to floating-point CSV precision. Historical400 H1 and443 finite-shot prefixes agree with final tables. The finite-shot ledger has1,186 records:1,000 included,178 post-target exclusions and8 duplicate-validation entries;1,178 unique real draw keys. Excluded/duplicate entries did not enter reproduced percentiles. Archived failure lists report zero; every fit was not rerun and pooling labels are not full optimizer traces.

**IA-005 High:** finite-shot inner resampling independently draws replicate indices for each parameter despite shared vector measurements. Static tracing and an executed counterexample establish lost within-vector dependence. Production interval effects are unmeasured. Exact H1 outer-cluster bootstrap is unaffected by this particular mechanism. Finite-shot simple H3 intervals inherit it. See [stage 5](STAGE_5_MODELS_BOOTSTRAP_DEPTH.md).

## Independent seed and depth weighting

The independent exact dataset contains25,600 unique rows and50 clusters; stored quantum initialization seeds do not overlap the original. Root3872531887 differs from20260726. Independent H1 estimate0.00772562533718829, archived SE0.0010888318741472493, recomputed Wald interval[0.0055915540786405,0.0098596965957361], archived-draw bootstrap interval[0.0034020524731532,0.0119226573459692]. Direction is retained; magnitude is larger and not established as stable.

| Dataset | Equal-depth estimate (Wald CI) | Observation/parameter-weighted estimate (Wald CI) |
|---|---|---|
| Original | 0.002374 [−0.000164,0.004911] | 0.004043 [0.001929,0.006157] |
| Independent | 0.005997 [0.003443,0.008552] | 0.007726 [0.005597,0.009854] |

Equal weights are0.2; independently counted observation/parameter weights are[.0625,.125,.1875,.25,.375] at D=1,2,3,4,6. Contrasts and weighted SEs reproduce using archived covariance. Categorical-weighted intervals and pooled-model intervals use different uncertainty calculations and are not interchangeable. Original equal-depth uncertainty includes zero. Model-based moderation p-values reproduce as.000136015/.108984; robust covariance origins remain archived-only. No monotonic depth law is established.

## Secondary quantities and cross-document scope

- Conditional exact-gradient J points independently reaggregate to1.241760/1.126633 (original R0/R1) and1.163219/1.242137 (independent); archived2,000-draw percentiles reproduce. Original R1 includes reference1. End-to-end I(R0)=1.0340744657849426 independently reproduces from eligible SNR RMS values. These descriptive ratios are not centered coefficients.
- H3 objective-specific/active/conditional contrasts, depth p-value arithmetic and50 archived LOO rows reconcile; LOO estimates are all negative,41 raw p-values below.05. Originating fit covariance and final optimizer statuses were not recreated.
- H1 adjusted locations and sinh contrasts reproduce from archived fixed coefficients. Reported9.9%/15.0% changes are contrasts of modeled locations, not raw mean gradients or optimization gains. Some projected/delta-method SE origins remain archived-only.
- Stored4,000 prepared-state records pass metric algebra/bounds checks;320 means and reported ranges reproduce. These are distinct cell records, not proof of4,000 distinct states; all terminal states and task-metric bootstrap intervals were not regenerated.
- Pilot width arithmetic, historical224-derivative errors, diagnostic count arithmetic and resource counts reconcile. Prospective independent initialization calibration is not established. Overstated significant-figure wording persists.

The final stage6D census reviews234 identified candidate lines;277 numerical comparison records and9 caveat records are preserved in `stage6d_numerical_and_caveat_comparison.csv`. Most numerical matches are after rounding. These counts use overlapping units and do not prove every atomic claim was extracted. Stage8 integrates later software/testing/figure dispositions in `VERIFICATION_MATRIX.csv`: main560 remains a TODO, main362's all-principal-path testing assertion remains only partly checked, and supplement225 has the IA-010 style mismatch. The old stage6D queue is a historical checkpoint, not a claim that these later checks never occurred.

## Discrepancies and uncertainty

| ID | Severity | Issue and scientific implication |
|---|---|---|
| IA-001 | Medium |70 duplicate seed assignments; inferential effect unknown.|
| IA-002 | Medium |Empirical sign notation/zero convention incomplete; code behavior verified.|
| IA-003 | Medium |Five conflicting frozen reference hashes; embedded list matches current files.|
| IA-004 | Low |Interval-source metadata incomplete; endpoints match actual summary.|
| IA-005 | High |Component-wise inner bootstrap loses vector dependence; CI impact unknown.|
| IA-006 | Low |Significant-figure claims exceed actual archived precision; errors remain small.|
| IA-007 | Medium |Independent initialization-pilot lineage/exclusion unestablished.|
| IA-008 | Medium |All160 reader-facing descriptive rows pool modes; primary models and fig0 remain end-to-end-only.|
| IA-009 | Low |Software-version TODO in revised main560.|
| IA-010 | Low |Conditional-J caption dataset line-style encoding invisible; labels remain readable.|

No finding is resolved. External protocol chronology/literature claims were not verified. Numerical consistency is strong for the checked quantities, with these explicit exceptions and evidence limits; universal cross-document correctness is not certified. The [findings register](FINDINGS_REGISTER.csv) contains exact evidence/actions and the [verification matrix](VERIFICATION_MATRIX.csv) preserves method-specific statuses.
