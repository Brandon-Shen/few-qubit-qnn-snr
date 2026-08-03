# Cross-platform submission validation

## Validation states

Local working-tree validation, the original Task 1--6 candidate, and the corrected clean-checkout validation are reported separately.

### Local Windows working tree

- Base state: `b68eacbbeaff947657320a799b5df6f7d2bf4bb7` plus uncommitted Task 1--6 changes
- OS: Windows 11
- Python: 3.12.10
- Full suite: 275 passed, 1 skipped, 0 failed in 327.24 s
- Manuscript checker: pass (205-word abstract; component-reference verification passed)
- Active checksum checker: pass

### Original Task 1--6 candidate (failed)

- Candidate commit: `a665b75303cdcfcd2a0c8d60eac02a37fd049f4e`
- Workflow: `tests`
- Run: [30771907844](https://github.com/Brandon-Shen/few-qubit-qnn-snr/actions/runs/30771907844)
- Conclusion: failure on both operating systems. The failure was not concealed; LF checkout changed protected bytes without corresponding portable manifest/checksum regeneration.
- Ubuntu job: [91560376847](https://github.com/Brandon-Shen/few-qubit-qnn-snr/actions/runs/30771907844/job/91560376847), 270 passed, 1 skipped, 5 failed in 423.82 s; Ubuntu smoke and later checker steps did not establish a passing candidate.
- Windows job: [91560376865](https://github.com/Brandon-Shen/few-qubit-qnn-snr/actions/runs/30771907844/job/91560376865), 270 passed, 1 skipped, 5 failed in 327.21 s; checker failures matched the Ubuntu portability failures.

### Corrected clean GitHub Actions validation

- Corrective commit: `82c2fd7fc097e9e1c01d4615e3cc6bf24588c098`
- Workflow: `tests`
- Run: [30772885026](https://github.com/Brandon-Shen/few-qubit-qnn-snr/actions/runs/30772885026)

| Field | Clean Ubuntu | Clean Windows |
|---|---|---|
| Job | [91563004440](https://github.com/Brandon-Shen/few-qubit-qnn-snr/actions/runs/30772885026/job/91563004440) | [91563004456](https://github.com/Brandon-Shen/few-qubit-qnn-snr/actions/runs/30772885026/job/91563004456) |
| Image | `ubuntu-24.04`, image version `20260720.247.2` | `windows-2025-vs2026`, image version `20260714.173.1` |
| Python | CPython 3.12.10 | CPython 3.12.10 |
| Full suite | 275 passed, 1 skipped, 0 failed | 275 passed, 1 skipped, 0 failed |
| Pytest duration | 269.39 s | 387.84 s |
| Job duration | 341 s | 508 s |
| Manuscript checker | pass; abstract 205 words; manifest references passed | pass; abstract 205 words; manifest references passed |
| Checksum checker | pass | pass |
| Final-manifest verification | pass through full-suite and manuscript component-reference checks | pass through full-suite and manuscript component-reference checks |
| Smoke CLI | pass; validation passed, H1 and H2--H4 each completed 5/5 bootstrap iterations | intentionally not run |
| Diagnostic artifact | `submission-validation-Linux`, uploaded successfully, artifact ID 8841148381 | `submission-validation-Windows`, uploaded successfully, artifact ID 8841178816 |

The corrected clean Ubuntu and Windows jobs both passed. These results complete Task 6 for the corrected successor to the originally nominated candidate; they must not be misattributed to the failed `a665b753...` run.
