# Cross-platform submission validation

## Current status

Cross-platform clean-checkout validation is pending. The local Windows working-tree suite passed, but it is not represented as a clean GitHub Actions result.

| Environment | Python | Commit/state | Tests | Duration | Manifest | Checksums |
|---|---|---|---|---:|---|---|
| Windows 11 local | 3.12.10 | working tree based on `b68eacbbeaff947657320a799b5df6f7d2bf4bb7` | 275 passed, 1 skipped, 0 failed | 327.24 s | pass; abstract 205 words | pass |
| Ubuntu clean checkout | pending | pending candidate commit | not run | — | pending | pending |
| Windows clean checkout | pending | pending GitHub Actions run | not run | — | pending | pending |

The first full-suite invocation was terminated by a 120-second command wrapper before pytest produced a result. It was rerun with a longer allowance and passed. Baseline targeted tests before edits had 5 passes, 2 failures (a pre-existing manuscript figure removal conflicted with reconciliation tests), and 1 setup error (the sandbox denied pytest's default temporary directory). The figure reference was restored consistently, and later tests used a workspace-local temporary directory.

GitHub CLI is unavailable in this environment. No push, workflow run, clean Linux result, or clean Windows result has yet been obtained; therefore no cross-platform pass claim is made.
