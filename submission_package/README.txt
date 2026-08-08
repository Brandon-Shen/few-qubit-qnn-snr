OVERLEAF / SPRINGER PACKAGE STAGING README

Status: FINAL PACKAGE PREPARED FOR INTENDED RELEASE sncs-submission-v5.
The included PDFs are the final compiled renders corresponding to the synchronized main.tex and ESM_1.tex
sources. Their immutable hashes are recorded in
verification/final_release_artifacts.json.

Official template files required only to recompile the sources independently:
  sn-jnl.cls
  sn-basic.bst

Project layout:
  main.tex                 main article source
  ESM_1.tex                Online Resource 1 source
  references.bib           bibliography database
  figures/                 six referenced vector PDFs
  Manuscript.pdf           final compiled main-article render
  ESM_1.pdf                final compiled Online Resource 1 render

Optional independent-recompilation steps:
  1. Add the two official Springer files above.
  2. Set main.tex as the main document and compile using the project's
     existing pdfLaTeX/BibTeX workflow.
  3. Set ESM_1.tex as the main document and compile Online Resource 1.
  4. Verify all table columns are visible on main page 14 and ESM page 2.
  5. Compare any replacement PDFs against the final artifact record and audit them before substitution.

No local TeX compilation was performed or claimed.
