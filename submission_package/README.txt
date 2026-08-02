OVERLEAF / SPRINGER PACKAGE STAGING README

Status: INCOMPLETE AND NOT FINAL. The included PDFs are the user-supplied
Overleaf renders, but they predate the table-width and supplement-metadata
corrections in main.tex and ESM_1.tex. A fresh Overleaf compile is required.

Required files still to export from the existing Overleaf project:
  sn-jnl.cls
  sn-basic.bst

Project layout:
  main.tex                 main article source
  ESM_1.tex                Online Resource 1 source
  references.bib           bibliography database
  figures/                 six referenced vector PDFs
  Manuscript.pdf           supplied pre-correction 20-page render
  ESM_1.pdf                supplied pre-correction 7-page render

Overleaf steps:
  1. Add the two official Springer files above.
  2. Set main.tex as the main document and compile using the project's
     existing pdfLaTeX/BibTeX workflow.
  3. Set ESM_1.tex as the main document and compile Online Resource 1.
  4. Verify all table columns are visible on main page 14 and ESM page 2.
  5. Export and replace both PDFs, then return them for final audit.

No local TeX compilation was performed or claimed.
