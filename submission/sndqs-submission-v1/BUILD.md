# SNDQS submission v1 build

main.tex and ESM_1.tex are availability-only candidates derived from the approved v3 pair. The local Stage 6C-2A source inventory records both sets of hashes. The sources request figure PDFs by basename, so the six figures sit beside both entry points. references.bib is the repository bibliography.

Compilation is blocked pending the compatible official Springer Nature template export. The main source uses the sn-mathphys-num class option and calls BibTeX. ESM_1 uses sn-basic and has no bibliography command. Supply sn-jnl.cls, sn-mathphys-num.bst, sn-basic.bst and any companion files required by that export. Run the following from an isolated copy of this folder using an existing TeX installation with required packages available. Disable automatic package installation in MiKTeX.

    pdflatex -no-install -recorder -halt-on-error main.tex
    bibtex main
    pdflatex -no-install -recorder -halt-on-error main.tex
    pdflatex -no-install -recorder -halt-on-error main.tex
    pdflatex -no-install -recorder -halt-on-error ESM_1.tex
    pdflatex -no-install -recorder -halt-on-error ESM_1.tex

For another TeX distribution, use its equivalent no-install configuration and omit MiKTeX's -no-install switch. Inspect the build logs for unresolved citations, references and layout warnings. Check recorder inputs for paths outside the staged folder or TeX distribution. Capture SHA-256 hashes of sources, project inputs and outputs, tool versions, and the visual review disposition. The supplement's build output must be named ESM_1.pdf.
