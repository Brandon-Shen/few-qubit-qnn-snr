# Online Resource 1 PDF technical preflight

**Artifact:** supplied Overleaf `ESM_1_overleaf.pdf`; 7 A4 pages; PDF 1.5; 322,512 bytes; SHA-256 `3c713f29fec9927f2369f28ebf4a6193a1d4a9b6022c6130d6991272c7d7b756`.

- Identity, text extraction, object parsing, and all seven page renders: pass.
- Encryption: none. Page dimensions: 595.276 by 841.890 points (A4).
- PDF title/author metadata are blank. Visible title and author are correct; adding PDF metadata in Overleaf is recommended but not itself blocking.
- One hyperlink annotation detected.
- Conventional text fonts render correctly. Ten Type 3 DejaVu subset occurrences appear on pages 3, 5, and 6 through included Matplotlib figures. Replace those figures with font-embedded versions before final freeze to meet the preferred no-Type-3 criterion.
- Figures are vector/form content; no raster image objects requiring effective-DPI assessment were detected.
- **Submission blocker:** Tables 1 and 2 extend beyond the right page edge on page 2. Their rightmost columns are visibly clipped.
- The seven-page layout is compact. Figures and body text remain readable, but some figure labels are small; this is secondary to the clipped tables.
- No encryption, malformed page, missing image, missing glyph, unresolved-reference marker, or accidental blank page was observed.

Classification: `submission blocker pending Overleaf recompile` because of page-2 clipping.
