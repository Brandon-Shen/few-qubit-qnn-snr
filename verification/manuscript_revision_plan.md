# Manuscript revision plan

**Status:** prospective editorial/reproducibility plan; no new scientific analysis.  
**Frozen source:** annotated tag `submission-numerical-results-freeze-v1`, commit `6ec255cab39a516bfc1cd188c71e0225713605c4`; numerical freeze commit `f2c5f496bd9223aa1aa0f00382fafa1ab95bfc05`.  
**Revision branch:** `submission-manuscript-revision-20260802`.

## Scope and authoritative inputs

The primary article source is the user-supplied Springer source `paper/sn-article.tex`, which replaces tracked `paper/main.tex`. The supplement is `paper/supplemental.tex`; bibliography is `paper/references.bib`. Submission metadata also includes `README.md`, `MANUSCRIPT_COMMIT.txt`, and any existing cover-letter source discovered during packaging.

Numbers and interpretations will be copied or rounded only from, in order: `results/final_submission_v1/manifest.json`, `final_numerical_results.json`, `final_numerical_results.csv`, `verification/final_numerical_results_freeze.md`, then the frozen component reports and source data referenced by the manifest. No model, bootstrap, contrast, weighting rule, or scientific source-data construction will be run.

The figure scripts are `paper/scripts/make_fig0_el_primary.py`, `make_fig1_forest.py`, `make_fig2_h4_fragility.py`, `make_fig3_entanglement.py`, `make_fig4_mode_split_bias.py`, `make_fig5_q1_comparison.py`, `make_fig6_d1_exclusion_sensitivity.py`, `make_fig7_zero_variance_heatmap.py`, `make_fig9_initialization_influence.py`, `make_fig10_bootstrap_endpoint_stability.py`, and `make_fig11_h2_depth_heterogeneity.py`, plus new render-only scripts for frozen H1-depth, conditional-J, task-metric, and resource-accounting source files if needed. Existing source data include `paper/figure_data/*`, `results/h1_depth_weighting/comparison/*_source.csv`, `results/jel_conditional/summary.csv`, `results/task_metrics/prepared_state/figure_source.csv`, and `results/resource_accounting/resource_table.csv`.

Main tables currently include configurations, prospective/post-run status, confirmatory results, and any concise task/resource summary added during revision. Supplement tables include zero-variance eligibility, H4 sensitivities, confirmatory results, H2 depth material, reproducibility index, and the new frozen H1/H3/J/task/resource tables. Every table and caption will be traced through `verification/manuscript_claim_inventory.csv`.

## Editorial sequence

1. Preserve the authorized `main.tex` to `sn-article.tex` transition and update path-aware tests/build commands.
2. Revise Methods/provenance: centered coding, adopted estimands, bootstrap hierarchy/count terminology, H1 weights, H3 post-primary diagnostics, conditional J definitions, initialization-state metrics, implemented measurement protocol, and simulator-specific resource scope.
3. Revise Results in the frozen order: eligibility; H1; independent-seed H1; H1 depth/weighting; H2; H3; H4; conditional J; prepared-state metrics; resources; implementation checks.
4. Revise structured abstract (150--250 words), Discussion, Limitations, and Conclusion using the frozen classifications without adding scientific quantities.
5. Replace the confirmatory table and render-only forest figure from frozen values. Integrate existing frozen H1 depth/weight figures. Render supplementary J/task/resource displays solely from frozen source data. Preserve Figure 0 scientific source unchanged.
6. Rewrite the supplement comprehensively, retaining historical direct-0/1 results only in an explicit correction/audit subsection. Use `ESM_1.pdf` and “Online Resource 1.”
7. Audit declarations and references without inventing facts or using external research unless a bibliographic identifier proves unresolvable locally.
8. Add a manuscript-value checker and targeted tests for frozen numbers, obsolete values/phrases, table values, figure sources, manifest integrity, source paths, and package completeness.
9. Compile main and supplement from a clean build directory, inspect logs and every PDF page, check fonts/images/references/citations, and fix layout without changing scientific values.
10. Complete the post-edit claim audit, assemble a self-contained `submission_package/`, clean-build it, write provenance, and create a collision-safe annotated local tag.

## Figure and accessibility rules

All scientific inputs are frozen. Rendered PDFs will use vector output where supported, embedded non-Type-3 fonts, final-size labels, and marker/line/hatch distinctions in addition to color. Captions will define abbreviations, analysis status, interval type, cluster count, and bootstrap iterations where applicable. No plot will imply monotonic depth, causal gradient-performance association, or preference for a more significant weighting.

## Compilation and validation

Planned commands (adapted only to locally available TeX tools):

```powershell
python scripts/check_manuscript_frozen_values.py
python -m pytest -q -p no:cacheprovider
latexmk -pdf -interaction=nonstopmode -halt-on-error paper/sn-article.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error paper/supplemental.tex
```

If Springer `sn-jnl.cls`/`sn-basic.bst` are absent, the installed template bundle or repository-local required files must be identified without network research; otherwise compilation is a blocker. Compilation records will include engine/version, citations/references, box warnings, fonts, images, and clean-package reproduction. The baseline before planned path correction is 262 passed, 2 manuscript-path failures, 1 optional H2-table skip; the numerical freeze baseline was 264 passed, 1 skipped, 0 failed.

## Intended commits

1. Plan and claim inventory.
2. Primary-source transition, Methods, and provenance.
3. Results.
4. Abstract, Discussion, Limitations, and Conclusion.
5. Tables and figures.
6. Supplement.
7. Declarations and references.
8. Consistency checker and tests.
9. PDF/layout fixes.
10. Final claim audit.
11. Submission package.
12. Final revision provenance and tag.

## Stop conditions

Stop and write `verification/manuscript_revision_blocking_report.{md,json}` if a required number is absent or frozen sources conflict; a figure/table needs a new scientific calculation; a frozen checksum changes; a scientific result lacks traceable frozen provenance; required source/template files cannot be found; either PDF cannot compile; author/affiliation/disclosure facts are ambiguous; or any requested claim would exceed the frozen interpretation. No frozen numerical CSV, JSON, Parquet, manifest, or scientific figure-source file may be modified.
