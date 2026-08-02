# Main PDF technical preflight

**Artifact:** supplied Overleaf `main_overleaf.pdf`; 20 A4 pages; PDF 1.5; 504,450 bytes; SHA-256 `9e99088a2225d8bb2e2e02ca4ae51d88caee7bdefb2a79e04dc63ec9d96e6248`.

- Identity, text extraction, object parsing, and all 20 page renders: pass.
- Encryption: none. Page dimensions: 595.276 by 841.890 points (A4).
- Metadata title and author: correct; producer `pdfTeX-1.40.27`; creator `LaTeX with hyperref`.
- Hyperlinks: 79 link annotations detected.
- Conventional document fonts are embedded/subset. Five Type 3 DejaVu subsets occur on pages 12--13, introduced by included Matplotlib figures. They render correctly but conflict with the preferred no-Type-3 submission criterion; recommended Overleaf correction is to replace those figure PDFs with font-embedded renderings before final freeze.
- Figures are vector/form content; no raster image objects requiring effective-DPI assessment were detected.
- **Submission blocker:** the corrected confirmatory table extends past the right page edge on page 14, clipping the bootstrap column.
- No encryption, malformed-page, missing-glyph, unresolved-reference, missing-image, page-number, header/footer, or title-page identity defect was observed.

Classification: `submission blocker pending Overleaf recompile` because of page-14 clipping. Class-generated `1*` and “Corresponding author(s). E-mail(s)” follow standard `\author*[1]`, `\email`, and `\affil*[1]` source usage and are acceptable.
