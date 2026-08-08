# Overleaf source/PDF consistency

**Result:** structural and scientific content match; no substantive source/PDF content mismatch. The supplied PDFs were produced from sources byte-identical to `paper/sn-article.tex` and `paper/supplemental.tex`. A separate visual defect (wide-table clipping) requires a source correction and new Overleaf render.

The main source/PDF agree on the full title, Brandon Shen, ORCID `0009-0002-3545-2106`, independent-researcher affiliation, corresponding email, four-part abstract, all 34 section/subsection headings, four figures, three tables, declarations, and bibliography. The supplement agrees on its Online Resource 1 identity, 12 headings, four figures, and five tables. LaTeX mathematical notation, Unicode minus signs, ligatures, line wrapping, and BibTeX numbering were treated as expected typesetting differences.

All frozen headline values were found in extracted PDF text, including corrected H1--H4 estimates/intervals/Holm values/bootstrap counts, independent-seed H1, H1 depth and weighting, H3 objective-specific and conditional-mode values, all four conditional J estimates, 4,000 prepared states, 320 resource rows, 1,833 joined zero-variance cells, and the 27.08% job-count difference. The PDFs state that H2/H3 bootstrap intervals include zero, H3 is model-dependent rather than robust, H4 is unresolved rather than absent, J is conditional on R, task metrics are at initialization, and shot matching is simulator-specific.

Expected differences: formulas are extracted in reading order rather than TeX order; `$2^3$` extracts as `23`; mathematical minus signs extract as Unicode; bibliography numbers are generated; visual line wrapping/hyphenation differs from source.

Visual-layout findings are not source/PDF inconsistencies: main page 14 clips the rightmost confirmatory-table column; supplement page 2 clips the right edges of Tables 1 and 2.
