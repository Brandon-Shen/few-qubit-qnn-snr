# Results provenance

**If you trust one source for the submitted numerical conclusions, use `results/final_submission_v1/manifest.json`.**

| Directory | Provenance and status |
|---|---|
| `final_submission_v1/` | Current machine-readable submission source of truth. |
| `primary_corrected/` | Corrected centered H1–H4 models and bootstrap intervals. |
| `independent_seed_h1/` | Independent-seed H1 rerun. |
| `h1_depth_weighting/` | Post-primary depth and weighting analyses. |
| `h3_centered_robustness/` | Objective-specific, active-depth, estimator-mode, and influence analyses for centered H3. |
| `jel_conditional/` | Conditional descriptive exact-gradient indices. |
| `task_metrics/` | Prepared-state metrics at initialization; not optimization outcomes. |
| `resource_accounting/` | Implemented simulator-shot and job accounting; not matched physical-resource costs. |
| `production_confirmatory/` | Frozen production raw inputs and historical production outputs. Raw data remain valid; older direct-0/1 lower-order interpretations here are not current primary estimands. |
| `production_corrected_end_to_end/` | Final 1,000-draw finite-shot bootstrap stream used by the corrected centered analysis; the preserved 443 prefix is historical. Older direct-coded coefficient summaries are not final centered primary estimates. |
| `superseded/`, `superseded_pooled/` | Audit-only historical outputs; never current conclusions. |
| `sensitivity_analyses/` | Historical and current robustness artifacts as identified by the final manifest. |
| `smoke_test/` | Non-scientific pipeline exercise. |

## Current primary conclusions

| Hypothesis | Model-based Holm decision | Bootstrap corroboration | Current interpretation |
|---|---|---|---|
| H1, centered exact-gradient E×L | Reject; estimate 0.004043, Holm p=0.000739 | Yes; 2,000-fit CI [0.000473, 0.007535] | Only primary interaction supported by both procedures. |
| H2, centered end-to-end E×L | Reject; estimate 0.014338, Holm p=0.015963 | No; 1,000-fit CI [-0.016240, 0.045992] | Model-based rejection, procedure-sensitive. |
| H3, centered end-to-end E×R | Reject; estimate -0.011615, Holm p=0.047875 | No; 1,000-fit CI [-0.031375, 0.009563] | Model-dependent signal with objective- and estimator-mode sensitivity. |
| H4, centered L×R×depth | Do not reject; estimate -0.010179, Holm p=0.057658 | No; 1,000-fit CI [-0.025964, 0.005863] | Unresolved; not evidence of absence. |

## Reproducing current manuscript artifacts

The current manuscript sources are `paper/sn-article.tex` and `paper/supplemental.tex`. Current figure/table sources and scripts are indexed by `final_submission_v1/manifest.json` and its component references. Figure 0 is a conditional descriptive `R=0` artifact, not a centered primary coefficient. Scripts and figures tied to an earlier manuscript numbering or direct-0/1 coefficient structure are historical unless the final manifest references them.

Verification from frozen artifacts does not require raw-data regeneration:

```text
python scripts/build_final_submission_freeze.py
python scripts/check_manuscript_frozen_values.py --output verification/manuscript_check.json
python scripts/regenerate_checksum_inventories.py --check
```

Checksum inventories are regenerated and checked by the cross-platform Python script; immutable external-input or historical hashes are classified rather than silently rewritten.
