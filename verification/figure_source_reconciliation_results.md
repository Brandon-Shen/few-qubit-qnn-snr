# Figure-source and manuscript-reference reconciliation

**Status:** completed reproducibility reconciliation under plan `645521db6511ca049d89e64f810e65a3407a7b52`.

The protected starting bytes were archived losslessly at `verification/figure_source_archive/fig0_el_primary_source.pre_reconciliation.csv`; both original and archive have SHA-256 `f89ccd263f2ea2e3fb92aed4677d0e32292851eda316244d014ccd49342a9a11`. The working-tree modification was a valid regeneration: every scientific number, formula, input checksum, and row count matched the tracked source; only the generation timestamp and then-current code commit differed. It was neither a centered-model coefficient nor an independent-seed/depth result.

The source was formally regenerated after archival. The ambiguous metric names `I_EL` and `J_EL` are now `I_EL_given_R0` and `J_EL_given_R0`, matching their configuration mapping. Input paths use platform-independent separators, and metadata now comes from the immutable production run manifest rather than wall-clock time/current HEAD. PDF creation metadata is fixed. Two consecutive regenerations produced identical CSV SHA-256 `beae88aa2da0d01686952a5f70704c9853849b18d89fbf3aa92a6bca31b59903` and PDF SHA-256 `7a6e13a3106388355346dd3ea72f38a2d3b67da94b7ba14b6b51c28aab234149`.

Repository history and `verification/fig0_el_primary_regeneration.md` show that the PDF was intended for the manuscript, while its `\includegraphics` was lost in later manuscript editing. A non-headline figure environment was restored immediately after the existing H1 multiplicative-index paragraph, with a caption explicitly identifying R=0 conditioning and non-equivalence to centered mixed-model interactions. The test was updated only for the clarified metric names; its manuscript-path assertion was retained and now passes. All 16 fig0 tests plus dedicated archive/source tests pass.

No archived content was discarded, and no abstract, conclusion, title, or headline claim was edited.
