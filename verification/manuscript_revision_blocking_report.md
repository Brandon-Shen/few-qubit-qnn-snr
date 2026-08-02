# Manuscript revision blocking report

**Status:** blocked at clean compilation and PDF inspection.  
**Branch:** `submission-manuscript-revision-20260802`.  
**Starting tag:** `submission-numerical-results-freeze-v1` at `6ec255cab39a516bfc1cd188c71e0225713605c4`.  
**Plan commit:** `ea091a8661e64d16821af0e8dc16e01af8439dc4`.

## Blocking condition

The local environment contains no discoverable `pdflatex`, `latexmk`, `bibtex`, `xelatex`, `lualatex`, or `tectonic` executable. It also contains no repository-local or user-installation copy of the Springer Nature template files `sn-jnl.cls` and `sn-basic.bst`. Consequently neither `paper/sn-article.tex` nor `paper/supplemental.tex` can be compiled, and the required clean-build, page-by-page PDF inspection, citation/reference validation from TeX logs, embedded-font audit, `ESM_1.pdf`, and self-contained submission-package build cannot yet be completed.

This matches the prospective stop condition “required source/template files cannot be found or either PDF cannot compile.” No dependency was downloaded and no frozen scientific output was changed.

## Completed before the block

- Verified the numerical tag/manifest and all referenced component hashes.
- Recorded baseline tests: 262 passed, two expected manuscript-path failures from the authorized `main.tex` to `sn-article.tex` transition, and one unrelated optional H2-table skip.
- Committed the prospective revision plan and 31-row claim inventory.
- Adopted the user-authorized Springer source transition.
- Revised centered-coding Methods/provenance, frozen Results, structured abstract (186 words), Discussion, Limitations, Conclusion, declarations, and Online Resource 1.
- Updated the corrected H1--H4 forest render and integrated frozen H1 depth/weighting, conditional-J, and task-metric figures.
- Added a frozen-value checker. It passes 28 required-value checks, finds no prohibited superseded primary values in the article, verifies all frozen manifest component hashes, and confirms conditional figure-source naming.
- Focused manuscript/source tests pass 6/6.

## Required resolution

Provide or authorize installation of a TeX distribution containing `latexmk`, `pdflatex`, and `bibtex`, plus the official Springer Nature `sn-jnl.cls` and `sn-basic.bst` files. Once available, work can resume with compilation, layout/font inspection, the final claim audit, submission-package assembly, full-suite validation, provenance commit, and annotated tag.

## Current revision commits

- Plan/inventory: `ea091a8661e64d16821af0e8dc16e01af8439dc4`
- Methods/provenance: `0248e9227cbec84f72dcf307ee24f9b02e52ed48`
- Results: `8c8b3971a3b4c8611a72194567de11d6b36d08af`
- Abstract/discussion/conclusion: `fe219abbaa466c5c8f85e3a3eca3fe89945ab653`
- Figures/tables: `da1f620a10d7329a03aee7540d5774f5a20e1890`
- Supplement: `8f2fd8becab954f1b7274afe40e377bf11676166`
- Declarations/references: `ec25f01164bdadfd5f1f9b922a6f4a701f496268`
- Consistency/tests: `498ff7097085b56ce570ec17cd8509799f752cb6`
