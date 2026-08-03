# Interaction-Aware Benchmarking of Exact-Gradient Signal and Finite-Shot Resolvability in a Four-Qubit Hybrid Quantum Neural Network

This repository contains the manuscript, frozen data, analysis code, and audit trail for the current submission. If one machine-readable source is used for the submitted numerical conclusions, use [`results/final_submission_v1/manifest.json`](results/final_submission_v1/manifest.json).

The current analysis uses centered binary coding. Historical direct-0/1 lower-order interpretations remain only for auditability and are not current primary results.

## Current primary results

| Hypothesis | Centered estimand | Estimate | SE | Wald 95% CI | raw p | Holm p | Bootstrap 95% CI | Fits |
|---|---|---:|---:|---|---:|---:|---|---:|
| H1 | exact-gradient E×L | 0.004043 | 0.001081 | [0.001924, 0.006162] | 0.000185 | 0.000739 | [0.000473, 0.007535] | 2,000 |
| H2 | end-to-end E×L | 0.014338 | 0.005145 | [0.004255, 0.024422] | 0.005321 | 0.015963 | [-0.016638, 0.043563] | 443 |
| H3 | end-to-end E×R | -0.011615 | 0.005144 | [-0.021697, -0.001534] | 0.023937 | 0.047875 | [-0.030943, 0.010259] | 443 |
| H4 | L×R×depth | -0.010179 | 0.005362 | [-0.020688, 0.000331] | 0.057658 | 0.057658 | [-0.026975, 0.006403] | 443 |

H1 is supported by both model-based and bootstrap inference. H2 and H3 meet the model-based Wald/Holm rule but their nested-bootstrap intervals include zero. H4 remains unresolved.

## Authoritative files

- Manuscript: [`paper/sn-article.tex`](paper/sn-article.tex)
- Online Resource 1: [`paper/supplemental.tex`](paper/supplemental.tex)
- Upload copies: `submission_package/main.tex` and `submission_package/ESM_1.tex`, synchronized byte-for-byte with the canonical sources
- Numerical manifest: [`results/final_submission_v1/manifest.json`](results/final_submission_v1/manifest.json)
- Finalized-state record: [`MANUSCRIPT_COMMIT.txt`](MANUSCRIPT_COMMIT.txt)
- Preferred immutable reviewer entry point after release: tag `sncs-submission-v1`

The existing `submission-numerical-results-freeze-v1` tag identifies the numerical-results freeze and is distinct from the final manuscript release.

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

The production raw-data generation and nested bootstrap are expensive and are not required to verify the frozen submission. The smoke pipeline is non-scientific:

```text
python -m qnn_snr run-all --config configs/smoke.yaml --iterations 5 --pointwise-bootstrap-iterations 10
```

The corrected candidate submission state was validated in clean Ubuntu and Windows GitHub Actions environments using Python 3.12.10: 275 tests passed, 1 was skipped, and none failed on each operating system. See [`verification/cross_platform_submission_validation.md`](verification/cross_platform_submission_validation.md) for the exact runs, commits, counts, images, durations, checker results, smoke result, and diagnostic artifacts. See [`results/README.md`](results/README.md) for numerical provenance and current-versus-historical status.
