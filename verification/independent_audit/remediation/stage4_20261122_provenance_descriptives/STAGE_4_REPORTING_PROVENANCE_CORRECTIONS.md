# Stage 4: provenance corrections and separate descriptive summaries

Date: 2026-11-22 (America/Los_Angeles). **Stage 4 only, complete for author review.** The user explicitly authorized corrective provenance records and separately derived mode-specific descriptives. Frozen scientific outputs, original metadata, scientific production code and all manuscript/supplement files were preserved. No bootstrap, mixed model, quantum-state simulation, production regeneration, commit or release update was run.

## Inputs and authority

Consulted the existing scientific/code audit, numerical reconciliation, reproducibility assessment, findings register/matrix, submission-readiness assessment and relevant prior Stage 4/6C evidence. Also read the finalized Stage 3 sensitivity report and its completion/source records: 1,000 accepted draws, no failed attempts, unchanged zero-crossing classifications, preserved original results. That post-audit sensitivity is linked separately and never substituted into the original primary or bootstrap rows.

The authoritative numerical entry point remains `results/final_submission_v1/manifest.json`, SHA-256 `c5a046541088fc35c363d3eb4519a34170f65e232ad214b0f8cd095bca4abc43`. All 19 embedded component hashes match actual raw bytes and canonical-LF hashes; all six freeze self-checksums match. This establishes identity, not a new model-validity assessment. The freeze builder was inspected, not executed: it would write outside this new directory. Source hashes, Git identity, dependency versions and the pre-existing dirty-file list are retained in `source_baseline.json`.

## IA-003: line-ending provenance explains all five hash conflicts

All five hashes in the separate `component_references.json` match the **CRLF variants** of the current LF files. Their numerical/text content is consistent after the documented CRLF-to-LF normalization. Git inventory history shows no conflicting hashes through `a8328ef`; all five conflicts appear in `fd25501366de8361eae3ad4ea69a01cfcc53a51d` (2026-08-03T01:31:20-07:00 Make frozen checksums cross-platform). That portability revision updates the manifest hashes while the separate inventory retains the CRLF hashes.

The same five entries in **both inventories also retain CRLF byte counts**, although current files use LF. These stale byte-count assertions are additional metadata detail within IA-003, not altered scientific values. For earlier commits where a current path/reference did not yet exist, the timeline records that limitation; absent historical blobs were not treated as proof of absent underlying data.

| Artifact | Original recorded bytes | Verified current/canonical-LF bytes |
|---|---:|---:|
| `results/h1_marginal_effects/h1_marginal_effects.json` | 3775 | 3662 |
| `results/h1_marginal_effects/h1_marginal_effects_table.tex` | 1958 | 1934 |
| `results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_seed_manifest.csv` | 441110 | 439923 |
| `results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_summary.csv` | 959 | 955 |
| `verification/h3_centered_interaction_robustness_results.json` | 1904 | 1825 |

`component_references.corrected_candidate.json` supplies 19 verified references aligned with the manifest's content hashes and actual LF byte counts. `component_reference_corrections.csv` retains both original hashes/counts, current raw/canonical hashes and CRLF counterfactual hashes/counts. `manifest_reference_byte_count_overlay.json` corrects only the five stale byte-count assertions in a separate proposed record. `provenance_correction_metadata.json` states the checksum/byte-count convention and binds these proposals to the original freeze hashes. Neither original inventory, checksum file nor manifest was overwritten. This is a metadata correction, not a numerical-results replacement or a new freeze.

Overall disposition: **partially resolved**. The mechanism and corrected records are verified; adoption and reader-facing traceability are pending review. The old register remains unchanged.

## IA-004: four bootstrap rows now have explicit separate sources

`bootstrap_interval_provenance_overlay.json` uses each frozen row's full manifest-defined key. It retains the historical `source_output`/script while separately recording coefficient and endpoint sources and hashes, lookup columns, adopted fit counts, centered/direct coefficient-draw sources, raw generator inputs, historical recorded input roles, transform/finalization scripts and original-procedure labels.

- Point estimates, model-based covariance/Wald and Holm fields originate in `results/primary_corrected/effect_coded/corrected_confirmatory_hypotheses.csv`.
- Adopted percentile endpoints originate in `results/primary_corrected/effect_coded/corrected_bootstrap_intervals_current_draws.csv`.
- H1's actual centered/direct draw files contain 2,000 rows; H2-H4's contain 1,000. Target columns and counts were checked using archive metadata; no percentile distribution was regenerated and no model was fit.
- H2-H4 inner resampling consumes raw end-to-end replicates. The old pointwise-table checksum identifies the originating model input; the overlay does not incorrectly characterize it as the raw inner-resampling input.

All four frozen point estimates, endpoints and counts agree with their corresponding actual source rows. `bootstrap_interval_source_index.csv` is the concise path/hash index and `bootstrap_interval_source_reconciliation.csv` records the numerical source comparison. `post_audit_sensitivity_source_links.json` separately identifies Stage 3's final report, coefficient table and interval table, explicitly as post-audit sensitivity. The original historical H1-H4 estimates, Wald/Holm results, bootstrap values and source fields remain unchanged.

Overall disposition: **partially resolved**. Verified overlay complete; author adoption and reader-facing references remain pending.

## IA-008: separate estimator-mode summaries derived from archived replicates

Reaggregated **6,144,000 signed gradient component rows** from the two finite-shot archives, aligning all explicit configuration/depth/budget/initialization/parameter/replicate keys. NumPy mean, ddof=1 variance/SD, exact gradients, plug-in/exact-reference SNR, signed/absolute bias, zero flags and empirical sign agreement reproduce **all 204,800 archived pointwise cells with maximum absolute checked-statistic error 0.0** and matching nonfinite masks. This check is justified by the new summary derivation; it does not regenerate the experiment or rerun a bootstrap.

New tables:

- `configuration_summaries_finite_shot_end_to_end.csv`: **160 rows**, primary estimator population, descriptive only.
- `configuration_summaries_finite_shot_conditional.csv`: **160 rows**, diagnostic estimator population.
- `configuration_summaries_by_estimator_mode.csv`: the same **320 rows**, keyed explicitly by mode/configuration/depth/budget.

End-to-end totals: 102,400 parameter cells, 101,891 finite SNRs, 509 nonfinite/zero-variance cells. Conditional totals: 102,400 parameter cells, 101,076 finite SNRs, 1,324 nonfinite/zero-variance cells. Each summary row retains 50 top-level initializations; its 50x4D parameter cells are not independent initialization samples. Thirty measured vectors per initialization represent 1,500 vectors per row, with shared component measurement noise. Raw component rows must not be counted as additional physical vector measurements.

The 31-column dictionary states every denominator and source role. SNR summaries use finite values; bias, empirical sign and archived signed-mean CI fractions use all parameter cells. Existing signed-mean CI flags are explicitly inherited rather than recomputed. Empirical sign agreement uses the sample-mean sign, with either zero returning false. Shared exact references are recalculated from unique exact-gradient rows, and initialization-landscape variance is the sample variance of 50 initialization means of absolute exact gradients. Resource means are mode-specific and checked against both raw values and the archived mode-keyed resource table.

The historical pooled construction reproduces for **13 non-physics fields at all 160 rows (2,080 field comparisons)**. The four original physics/state-preparation columns are intentionally outside this derivation and omitted from the new estimator tables; their historical values remain available, not relabeled as newly simulated mode-specific measurements. `historical_fields_not_rederived.csv` records this boundary. The pooled table's missing mode key is a descriptive reporting issue; the separately verified end-to-end primary H2-H4 filter was not changed or reopened.

Example, configuration 1 / D=3 / B=250: historical pooled RMS SNR 0.7402949564; end-to-end 0.5895453523; conditional 0.8686069696. The historical count 1200 pools 600 parameter cells per mode. Pooled medians/ratios cannot generally be reconstructed by averaging mode-specific medians/ratios; use the original pooled cell population when checking historical outputs.

`descriptive_source_anchors.json` distinguishes direct freeze input-checksum matches (exact and pointwise data) from production-inventory matches for the other descriptive inputs. It does not invent a direct manifest reference for files absent from the 19-component list. All six descriptive source hashes match the frozen production inventory. `mode_specific_descriptives_metadata.json` binds the new tables and procedures to these actual sources. No H2-H4 primary coefficient, eligibility rule or uncertainty calculation was changed.

Overall disposition: **partially resolved**. Separate descriptive artifacts and historical labeling evidence are complete; the broad separate-reporting/no-pooling prose and supplementary source index still require the separately authorized manuscript stage.

## Affected text and proposed wording for later review

`affected_manuscript_statements.csv` records current source hashes, exact lines, existing statements and narrowly scoped proposals. Key IA-008 locations are main 233/249 and supplement 249/267. Main 309 is identified as a valid primary-model statement, not a pooled-primary defect. IA-003 traceability contexts are the data/source-of-truth passages; IA-004 contexts are the original bootstrap methods, Results and table captions. Their historical numbers require no replacement in Stage 4.

Proposed IA-003 clarification: “The original numerical freeze is retained. A separate metadata-correction record documents canonical-LF text hashes and byte counts, including the original CRLF inventory discrepancy.”

Proposed IA-004 clarification: “Point estimates and Wald/Holm quantities are sourced from the corrected confirmatory coefficient table; adopted bootstrap percentile endpoints have a separate interval-summary source, with draw/input hashes recorded in the provenance index. Post-audit vector-preserving intervals remain separately labeled sensitivity results.”

Proposed IA-008 clarification: “Primary end-to-end models and conditional diagnostics are analyzed separately. The historical configuration summary table pooled finite-shot modes and is retained as a labeled historical artifact; new post-audit descriptive tables report the two estimator modes separately, with explicit cell and eligibility denominators.”

These are proposals, not manuscript edits, released corrections or evidence that post-audit work was preregistered. No LaTeX candidate or production-code patch was created.

## Verification, dispositions and stop

`STAGE_4_FINDINGS_DISPOSITION.csv/json` distinguishes verified artifact-level corrections from overall adoption/editorial completion; all three findings are partially resolved, none prematurely closed. `STAGE_4_VERIFICATION.json` and `stage4_artifact_hashes.json` record final checks and identities. Original frozen metadata, scientific outputs, manuscripts, production scientific source and prior Stage 3 summary artifacts must retain their baseline hashes. The progress tracker is updated with the old version preserved. Reliable token usage is unavailable.

Audit preparation initially caught an incorrect submission supplement filename and then the stale CRLF byte counts; bounded historical Git inspection also required accounting for references introduced after the first freeze. The script was corrected and resumed only by reusing byte-identical already-written preparation records, never overwriting them. These were preparation/check-coverage issues, not altered scientific results. No old audit script or builder was rerun against its frozen output paths.

**Stage 4 stops here for review. Stage 5, LaTeX edits, publication/adoption of these candidate records, and changes to released metadata require explicit next-stage authorization.**
