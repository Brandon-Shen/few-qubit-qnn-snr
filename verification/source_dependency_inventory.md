# Overleaf/Springer source dependency inventory

Both sources use `\documentclass[pdflatex,sn-basic,Numbered]{sn-jnl}`. The main source loads `graphicx`, `amsmath`, `amssymb`, `amsfonts`, `booktabs`, `braket`, `array`, `tabularx`, `enumitem`, `seqsplit`, and `appendix`; Online Resource 1 loads `graphicx`, `amsmath`, `amssymb`, `booktabs`, `array`, `tabularx`, and `seqsplit`. Hyperref is supplied by the class.

The main bibliography command is `\bibliography{references}`; the `sn-basic` option requires the official `sn-basic.bst`. The source package includes `references.bib`. All bibliography keys are cited and every citation key exists.

Required figure dependencies, all present under `submission_package/figures/`:

- `fig0_el_primary.pdf`
- `fig1_confirmatory_forest.pdf`
- `fig12_j_conditional.pdf`
- `fig13_h1_depth.pdf`
- `fig14_h1_weighting.pdf`
- `fig15_prepared_state_metrics.pdf`

No `\input`, `\include`, or custom style dependency is referenced.

Missing official Overleaf export dependencies:

- `sn-jnl.cls`
- `sn-basic.bst`

These must be exported from the user's existing Overleaf project. They were not downloaded or substituted. Until present, `submission_package/` is a staging package and no source ZIP or final tag can be created.
