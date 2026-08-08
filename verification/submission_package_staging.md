# Submission-package staging status

`submission_package/` contains the current corrected main and Online Resource sources, `references.bib`, every referenced figure, and byte-identical copies of the two supplied Overleaf PDFs. It excludes raw data, analysis outputs, caches, verification logs, temporary TeX files, and `.claude/`.

The staging package is intentionally not zipped or frozen because:

1. official `sn-jnl.cls` and `sn-basic.bst` have not been exported from Overleaf;
2. the included PDFs predate required table-width/source metadata corrections;
3. main page 14 and supplement page 2 in those supplied PDFs contain clipped tables;
4. a fresh Overleaf compile and returned PDFs are required for final consistency/preflight.

No unofficial template dependency was downloaded, no TeX software was installed, and no local compilation was attempted.
