# Required Overleaf actions

The supplied PDFs correspond exactly to the archived pre-correction sources, but visual review found clipped tables. Repository sources now contain minimal layout corrections and the supplement metadata correction; therefore the supplied PDFs are outdated relative to current source.

Required before final freeze:

1. Export the official `sn-jnl.cls` and `sn-basic.bst` from the existing Overleaf project and place them at the project root / `submission_package/` root.
2. Replace Overleaf `main.tex` with `submission_package/main.tex` and the Online Resource source with `submission_package/ESM_1.tex`.
3. Retain `references.bib` and all six PDFs under `figures/`.
4. Recompile both documents in Overleaf. The table changes use `\resizebox{\textwidth}{!}` for the main confirmatory table and supplement Tables 1--2. The supplement now sets title/author PDF metadata.
5. Confirm main page 14 and Online Resource page 2 show every table column inside the text area.
6. Export new `Manuscript.pdf` and `ESM_1.pdf` and return them for checksum, all-page visual review, source/PDF consistency, and preflight.
7. Recommended before final export: replace the six included Matplotlib figure PDFs with otherwise identical font-embedded (non-Type-3) renders. At minimum, confirm the journal accepts the current Type 3 subsets.

No scientific value or interpretation is to be changed. No local TeX build is requested or permitted.
