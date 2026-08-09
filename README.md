# Factorial Benchmarking of Exact and Finite-Shot Gradient Resolvability in a Four-Qubit Hybrid Quantum Neural Network

This repository contains the manuscript, frozen data, analysis code, and audit trail for the current submission. If one machine-readable source is used for the submitted numerical conclusions, use [`results/final_submission_v1/manifest.json`](results/final_submission_v1/manifest.json).

The current analysis uses centered binary coding. Historical direct-0/1 lower-order interpretations remain only for auditability and are not current primary results.

## Current primary results

| Hypothesis | Centered estimand | Estimate | SE | Wald 95% CI | raw p | Holm p | Bootstrap 95% CI | Fits |
|---|---|---:|---:|---|---:|---:|---|---:|
| H1 | exact-gradient E×L | 0.004043 | 0.001081 | [0.001924, 0.006162] | 0.000185 | 0.000739 | [0.000473, 0.007535] | 2,000 |
| H2 | end-to-end E×L | 0.014338 | 0.005145 | [0.004255, 0.024422] | 0.005321 | 0.015963 | [-0.016240, 0.045992] | 1,000 |
| H3 | end-to-end E×R | -0.011615 | 0.005144 | [-0.021697, -0.001534] | 0.023937 | 0.047875 | [-0.031375, 0.009563] | 1,000 |
| H4 | L×R×depth | -0.010179 | 0.005362 | [-0.020688, 0.000331] | 0.057658 | 0.057658 | [-0.025964, 0.005863] | 1,000 |

H1 is supported by both model-based and bootstrap inference. H2 and H3 meet the model-based Wald/Holm rule but their nested-bootstrap intervals include zero. H4 remains unresolved.

## Authoritative files

- Manuscript: [`paper/sn-article.tex`](paper/sn-article.tex)
- Online Resource 1: [`paper/supplemental.tex`](paper/supplemental.tex)
- Upload copies: `submission_package/main.tex` and `submission_package/ESM_1.tex`, synchronized byte-for-byte with the canonical sources
- Numerical manifest: [`results/final_submission_v1/manifest.json`](results/final_submission_v1/manifest.json)
- Finalized-state record: [`MANUSCRIPT_COMMIT.txt`](MANUSCRIPT_COMMIT.txt)
- Preferred immutable reviewer entry point after release: tag `sncs-submission-v1`

The existing `submission-numerical-results-freeze-v1` tag identifies the numerical-results freeze and is distinct from the final manuscript release.

The final substantive manuscript state is commit `a98835e1dd4b40c0abeaf636c1dbe1e33b3849d3` on branch `main`. The immutable reviewer entry point is [`sncs-submission-v1`](https://github.com/Brandon-Shen/few-qubit-qnn-snr/releases/tag/sncs-submission-v1). The numerical freeze remains [`submission-numerical-results-freeze-v1`](https://github.com/Brandon-Shen/few-qubit-qnn-snr/tree/submission-numerical-results-freeze-v1). `MANUSCRIPT_COMMIT.txt` distinguishes the release-metadata commit from the substantive manuscript state.

## Installation

Use Python 3.12 and the locked environment:

```text
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
```

## Validation

```text
python -m pytest tests/ -q
python scripts/check_manuscript_frozen_values.py --output verification/manuscript_check.json
python scripts/regenerate_checksum_inventories.py --check
```

## Regenerating submission artifacts

Quick, non-scientific rendering and validation commands are:

```text
python paper/scripts/make_fig0_el_primary.py
python paper/scripts/make_fig1_forest.py
python paper/scripts/make_fig12_j_conditional.py
python paper/scripts/make_fig16_architecture.py
python scripts/check_manuscript_frozen_values.py --output submission_validation_report.json
python -m pytest tests/ -q
```

Compile `paper/sn-article.tex` with pdfLaTeX, BibTeX, pdfLaTeX, pdfLaTeX in a Springer Nature template project containing the official `sn-jnl.cls` and `sn-basic.bst`. Repeat for `paper/supplemental.tex` and name its output exactly `ESM_1.pdf`. The repository export does not include those Springer-owned template files, so local compilation requires an existing TeX installation/template project or Overleaf.

The frozen result map is `results/final_submission_v1/manifest.json`. Primary centered results are in `results/primary_corrected/`; the internal new-seed data and results are in `results/independent_seed_h1/` and `results/h2_replication_v1/`; post-primary sensitivities are under `results/h1_depth_weighting/`, `results/h3_centered_robustness/`, `results/jel_conditional/`, and `results/sensitivity_analyses/`; figures and generators are under `paper/figures/` and `paper/scripts/`; verification records are under `verification/`; historical results are under `results/superseded/` and `results/superseded_pooled/`.

Figure regeneration and frozen-value checks normally complete in seconds to minutes on an ordinary laptop. The full test suite took approximately 5--7 minutes in recorded clean Windows/Linux runs. Raw confirmatory simulation, new-seed simulation, and nested mixed-model bootstraps require substantial CPU time and memory and are not needed to verify the frozen submission. Exact recorded commands are in `results/final_submission_v1/commands.txt` and the relevant verification plans/reports.

No repository code or data license has been selected. A license is therefore a manual pre-submission decision; none is implied by public GitHub access.

The production raw-data generation and nested bootstrap are expensive and are not required to verify the frozen submission. The smoke pipeline is non-scientific:

```text
python -m qnn_snr run-all --config configs/smoke.yaml --iterations 5 --pointwise-bootstrap-iterations 10
```

The corrected candidate submission state was validated in clean Ubuntu and Windows GitHub Actions environments using Python 3.12.10: 275 tests passed, 1 was skipped, and none failed on each operating system. See [`verification/cross_platform_submission_validation.md`](verification/cross_platform_submission_validation.md) for the exact runs, commits, counts, images, durations, checker results, smoke result, and diagnostic artifacts. See [`results/README.md`](results/README.md) for numerical provenance and current-versus-historical status.
