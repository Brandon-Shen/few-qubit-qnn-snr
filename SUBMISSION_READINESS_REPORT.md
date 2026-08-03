# Submission readiness report

## 1. Executive verdict

**Ready after listed manual actions.** Scientific/source revision and frozen-value validation are complete. Final PDF compilation and page-level inspection remain manual because this repository environment has no TeX engine and the exported repository intentionally lacks Springer Nature's `sn-jnl.cls` and `sn-basic.bst`. No H1--H4 analysis was rerun and no frozen numerical result changed.

## 2. Files changed

- Canonical article and Online Resource 1: `paper/sn-article.tex`, `paper/supplemental.tex`.
- Synchronized upload sources: `submission_package/main.tex`, `submission_package/ESM_1.tex`.
- Figure source/assets: `paper/scripts/make_fig0_el_primary.py`, `paper/scripts/make_fig16_architecture.py`, `paper/figures/fig0_el_primary.pdf`, its preview, and `paper/figures/fig16_architecture.pdf`; synchronized submission-package PDFs.
- Reproduction and validation: `README.md`, `scripts/validate_submission_revision.py`, `submission_validation_report.json`.
- Revision records: this report and `REVISION_CHANGELOG.md`.

Pre-existing untracked `.claude/`, `.tag-validation/`, and `.tmp_pytest/` directories were not modified as submission content. Pre-existing uncommitted TeX edits were preserved; none conflicted with frozen results.

## 3. Scientific changes

- Retitled the article “Factorial Benchmarking of Exact and Finite-Shot Gradient Resolvability in a Four-Qubit Hybrid Quantum Neural Network.”
- Added the complete code-verified reset-per-block forward pass, dimensions, gate order, classical transition, residual activation, initialization distributions, seed matching, parameter population, pseudocode, and a source-generated architecture diagram.
- Distinguished population repeated-shot SNR from the 30-replicate plug-in estimator, including the denominator-29 sample variance and zero-variance rule.
- Defined parameter-weighted, equal-depth, and depth-specific H1 estimands and preserved their distinct interpretations.
- Made residual inactivity at `D=1,2`, active-depth interpretation, objective specificity, estimator-mode reversal, and lack of bootstrap corroboration central to H3.
- Preserved the evidence hierarchy: H1 both procedures; H2/H3 Wald only; H4 neither/unresolved.
- Added transparent H2--H4 bootstrap stopping language and checkpoint intervals at 40, 100, 200, 400, and 443 completed fits.
- Added finite-difference, optimizer, singularity, residual, influence, eligibility, resource, and promised-outcome summaries.
- Separated implementation validation from the generative-AI statement and retained author responsibility.
- Limited all resource conclusions to the implemented abstract simulator-shot protocol.

## 4. Analyses rerun

No scientific or statistical analysis was rerun.

Rendering-only commands:

```text
python paper/scripts/make_fig0_el_primary.py
python paper/scripts/make_fig16_architecture.py
```

The first reread the already frozen, reconciled figure source and reproduced the same underlying `I` and `J` values; only the embedded title was removed. The second produced a non-numerical schematic from code-confirmed architecture rules. Runtime was seconds on the local Python 3.12 environment. No seeds or scientific values changed.

## 5. Analyses not rerun and why

- H1--H4 mixed models, Holm correction, and all frozen bootstrap intervals: prohibited by the revision constraints and unnecessary.
- H2--H4 bootstrap extension: retained at 443 completed fits as directed. At least 400 were targeted, 1,000 preferred, and 443 completed with zero failures. Every relevant interval included zero at all existing checkpoints. Percentile endpoints retain finite Monte Carlo uncertainty.
- Raw confirmatory and new-seed simulation: frozen and computationally expensive; not required for source revision.
- New categorical-depth or physical-overlap analysis: no new hypothesis-family or physical-resource analysis was authorized.

## 6. Numerical-consistency results

- `scripts/check_manuscript_frozen_values.py`: pass; 28 required values, no prohibited current values, no manifest/hash errors, no source synchronization errors; abstract 200 words.
- Active and immutable checksum inventories: pass.
- Focused manuscript/figure/submission tests: 30 passed. Smoke-only temporary model fits emitted their expected warnings; no test failed.
- Full suite: 276 passed, 1 skipped, 0 failed in 324.97 seconds. The 567 warnings arose from deliberately small smoke/pilot mixed-model fits and are covered by existing warning/fallback tests; they did not fail validation.
- Canonical and upload TeX sources are byte-identical.
- No current figure or table input references a superseded directory.

## 7. Repository-access status

The repository is publicly accessible at <https://github.com/Brandon-Shen/few-qubit-qnn-snr>. The manuscript directly links intended release `sncs-submission-v2`; numerical tag `submission-numerical-results-freeze-v1`, manifest `results/final_submission_v1/manifest.json`, and `MANUSCRIPT_COMMIT.txt` remain distinct and explicit. The published protocol is cited. The full protocol source is not claimed to be locally archived; local decision plans, adjudication records, and verification reports are described accurately.

## 8. Remaining manual tasks

1. Compile `paper/sn-article.tex` and `paper/supplemental.tex` in the existing Springer Nature template/Overleaf project containing official `sn-jnl.cls` and `sn-basic.bst`; name the supplement exactly `ESM_1.pdf`.
2. Copy the resulting PDFs to `paper/output/main_manuscript.pdf`, `paper/output/ESM_1.pdf`, `submission_package/Manuscript.pdf`, and `submission_package/ESM_1.pdf` as appropriate.
3. Inspect every final page for clipping, overfull boxes, table placement, references, metadata, fonts, and figure legibility; run `pdffonts` and confirm no Type 3 figure fonts.
4. Select code/data licenses only if the author chooses to do so. No license is currently granted or implied.
5. Optionally archive the published protocol PDF/source locally if redistribution permits; this is not required for the scientific claims.
6. Optionally mint an archival DOI and update the existing placeholder.
7. After review, update commit metadata for the eventual final commit. Do not claim the working tree itself is represented by the prior immutable release until a new reviewed release is intentionally made.

## 9. Scientific limitations intentionally retained

Four qubits; one TFIM task; one reset-per-block architecture; one pair-restricted schedule; one fixed-gain classical shortcut; initialization behavior only; no optimization trajectories; no hardware noise or physical-resource comparison; 50 top-level clusters; finite-replicate objective-linked eligibility; H1 depth/weighting/covariance uncertainty; H2/H3 procedure disagreement; H3 objective and estimator-mode sensitivity; unresolved H4; and finite Monte Carlo uncertainty in the 443-fit percentile endpoints.

## 10. Recommended cover-letter disclosures

- The prior protocol article proposed the design but reported no data from this implementation.
- Operational reset, eligibility, estimator-mode, and residual-activation details were resolved during implementation; the study is protocol-derived rather than fully preregistered.
- Lower-order direct-coded interpretations were corrected to centered factorial estimands without changing fitted values or selecting a more favorable model.
- The second dataset is an internal new-seed replication, not an external replication.
- Generative-AI tools assisted planning, scripting, checking, and prose feedback but were neither authors nor evidence; the author reviewed and accepts responsibility.
- Cite the public repository, `sncs-submission-v2`, numerical freeze tag, manifest, and substantive commit record distinctly.

Submission-portal caption: “Online Resource 1. Corrected interaction estimates, bootstrap procedures, depth-weighting analyses, estimator-mode sensitivities, implementation-validation results, resource accounting, and reproducibility information.”
