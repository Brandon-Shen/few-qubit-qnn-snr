# Revision changelog

No H1--H4 analysis was rerun and no frozen numerical value was changed.

## Manuscript sources

- `paper/sn-article.tex`: preserved the pre-existing `xurl`/path-formatting, figure-width, and evidence-label edits; changed the title and metadata; rewrote the abstract evidence hierarchy; distinguished population and plug-in SNR; added complete architecture, dimensions, initialization, matching, parameter-population, algorithm, and diagram material; expanded protocol provenance; defined three H1 estimands; added bootstrap checkpoint/stopping caveats; promoted structural H3 facts; expanded validation diagnostics; removed percent-improvement framing; separated implementation and AI statements; retained public-release links.
- `paper/supplemental.tex`: preserved pre-existing path/table-layout edits; changed the title; added code-verified architecture and SNR sections; added the five checkpoint rows; expanded validation, optimizer, residual, structural, and promised-outcome reporting; clarified protocol-source and Monte Carlo limitations.
- `submission_package/main.tex`, `submission_package/ESM_1.tex`: mechanically synchronized byte-for-byte from canonical sources.

## Figures

- `paper/scripts/make_fig0_el_primary.py`: removed the embedded practical-magnitude title; numerical source and calculations unchanged.
- `paper/figures/fig0_el_primary.pdf` and preview: rendering-only regeneration; frozen source checksum and `I/J` values unchanged.
- `paper/scripts/make_fig16_architecture.py`: new non-interactive Matplotlib generator using PDF font type 42.
- `paper/figures/fig16_architecture.pdf`: new vector architecture schematic.
- `submission_package/figures/`: synchronized the two affected PDFs.

## Documentation and validation

- `README.md`: updated title, public release/commit/freeze provenance, artifact-generation commands, directory map, runtime guidance, TeX requirement, and missing-license notice.
- `scripts/validate_submission_revision.py`: added source synchronization, frozen-token, bootstrap, stale-reference, architecture, compilation-tool, font-tool, and license checks.
- `submission_validation_report.json`: machine-readable observed validation status and manual actions.
- `SUBMISSION_READINESS_REPORT.md`: readiness verdict, audit findings, scientific changes, rerun/non-rerun record, limitations, and manual actions.
- `REVISION_CHANGELOG.md`: this file-by-file record.

## Generated files requiring review before a future commit

Source/documentation: the two canonical TeX files, synchronized upload TeX files, README, two figure scripts, validation script, and both final reports. Generated assets: revised Figure 0 PDF/preview, architecture PDF, synchronized submission figures, and validation JSON. Final compiled manuscript/supplement PDFs should be added only after the manual Springer-template compile and page inspection.
