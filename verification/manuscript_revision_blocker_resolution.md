# Manuscript-revision blocker resolution addendum

The local-compilation blocker recorded at `fb429133ac282c49ee4dd6a47fb5009d818510f8` is superseded. The user supplied 20-page and seven-page Overleaf PDFs and identified the repository article/supplement sources as the supplied text. No TeX installation, PATH modification, template download, or local compilation was performed or needed.

Verification instead used immutable artifact imports, SHA-256 checks, source/PDF structural comparison, extracted PDF text, frozen-value tests, rendering and visual inspection of all 27 pages, contact sheets, font/object preflight, and dependency inventory.

The original blocker is resolved, but final freeze is now pending a required Overleaf correction cycle: main page 14 and supplement page 2 clip wide tables. Current sources contain minimal width fixes and supplement PDF metadata, so the supplied PDFs no longer correspond to final source. Official `sn-jnl.cls` and `sn-basic.bst` must also be exported from the user's existing Overleaf project. Exact actions are in `verification/overleaf_recompile_actions.md`.

No final manuscript tag or source ZIP is created until corrected Overleaf PDFs return and pass the same audit.
