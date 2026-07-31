# Mode-pooling guard: code fix for the bug found in `conditional_vs_endtoend_comparison.md`

**Context**: `conditional_vs_endtoend_comparison.md` found that the H2–H4
confirmatory fit silently pooled `finite_shot_conditional` and
`finite_shot_end_to_end` rows into one mixed-mode model, because
`build_h2h4_dataset`/`fit_h2h4_model` had no `analysis_mode` awareness and
nothing upstream filtered to one mode before fitting. The paper's Methods
section designates end-to-end as confirmatory and conditional as a
diagnostic only — the pooled fit was a bug, not an alternative valid design.
This document is the code-level fix.

## What changed

### `qnn_snr/stats/models.py`

- Added `CONFIRMATORY_MODE = "finite_shot_end_to_end"`, the single mode the
  paper's Methods designates as confirmatory.
- `build_h2h4_dataset(pointwise_df, pool_modes: bool = False)`: if the input
  has an `analysis_mode` column with more than one distinct value and
  `pool_modes` is not explicitly `True`, it now raises `ValueError` naming
  the offending modes and pointing at
  `verification/conditional_vs_endtoend_comparison.md` /
  `verification/mode_pooling_guard.md`. Single-mode input (or input with no
  `analysis_mode` column at all — e.g. the synthetic frames used in
  `tests/test_models.py`'s existing recovery tests) is unaffected.
- `fit_h2h4_model()` and `fit_sensitivity_model()` both gained a
  `pool_modes: bool = False` passthrough parameter to the same guard, so
  pooling is only ever possible by explicit caller opt-in, never by default.

### `qnn_snr/cli.py`

Every call site that used to build `pw`/`shot_df` from
`analysis_mode.isin(SHOT_MODES)` (both modes at once) and then feed it
straight into a fit was changed to filter to a single mode first:

- **`cmd_fit`** (the confirmatory path): now takes `--mode` (default
  `CONFIRMATORY_MODE`, choices `SHOT_MODES`). The default path filters the
  precomputed `pointwise_gradient_statistics.parquet` to
  `finite_shot_end_to_end` before calling `fit_h2h4_model`/
  `fit_sensitivity_model`, and only in that default (confirmatory) branch
  does it write `exact_model_coefficients.csv`, `snr_model_coefficients.csv`,
  `confirmatory_hypotheses.csv`, and `holm_adjustment.csv`. Passing
  `--mode finite_shot_conditional` takes a **separate, explicitly-labeled
  diagnostic branch**: it fits only the SNR model on conditional-mode data,
  writes the result to `snr_model_coefficients_diagnostic_finite_shot_conditional.csv`,
  prints a `NOTE:` to stderr saying it is diagnostic-only, and returns before
  touching any of the confirmatory files (H1 isn't even refit on that path,
  since H1 has no mode dependence and a diagnostic SNR run shouldn't imply a
  new H1 result). This directly satisfies "conditional-mode fit available as
  a separate, explicitly-labeled diagnostic command/flag rather than
  something that can be silently mixed in."
- **`cmd_report`**: `fit_h2h4_model(pw)` → `fit_h2h4_model(pw[pw["analysis_mode"] == CONFIRMATORY_MODE])`.
  (The purely descriptive computations in `cmd_report` —
  `configuration_summaries`, `compute_interaction_indices`,
  `generate_all_figures`'s `pointwise_df` — still receive the full pooled
  `pw`; those never called `build_h2h4_dataset` and pooling there is a
  separate, lower-priority cleanup tracked in
  `verification/mode_split_descriptive_stats.md`, not a bug this guard needs
  to stop.)
- **`cmd_bootstrap`**: `shot_df = df[df["analysis_mode"].isin(SHOT_MODES)]` →
  `shot_df = df[df["analysis_mode"] == CONFIRMATORY_MODE]` before
  `run_h2h4_bootstrap`. (`run_h2h4_bootstrap` calls `build_h2h4_dataset`
  internally on every iteration inside a blanket `try/except`, so leaving
  pooled data flowing in would not have crashed loudly — it would have
  turned every bootstrap iteration into a silently recorded "failed
  iteration" instead. Fixing the call site avoids that failure mode
  entirely rather than relying on the guard to be noticed inside the
  exception handler.)
- **`cmd_pilot_initializations`**: same fix, filtered to `CONFIRMATORY_MODE`
  before `pointwise_statistics`/`fit_h2h4_model`, matching the mode already
  used by default for `select_replicate_count` (pilot precision selection
  should use the same mode as the confirmatory analysis it's sizing).

## Test added

`tests/test_models.py` gained four tests built around a minimal two-mode
synthetic frame (`_two_mode_snr_df`, 4 rows split across both modes):

- `test_build_h2h4_dataset_rejects_mixed_analysis_mode_by_default` — asserts
  `ValueError` (matching `"analysis_mode"`) is raised on the mixed-mode
  frame. **This is the test that would have caught the original bug** — run
  against the pre-fix code, it fails because the old `build_h2h4_dataset`
  silently pooled and returned all 4 rows.
- `test_build_h2h4_dataset_allows_pooling_with_explicit_opt_in` — confirms
  `pool_modes=True` still works and returns all rows, so the escape hatch
  for any future intentional pooling exists.
- `test_build_h2h4_dataset_single_mode_does_not_raise` — confirms filtering
  to one mode first (the fixed call-site pattern) works normally.
- `test_fit_h2h4_model_rejects_mixed_analysis_mode` — same check one level
  up, through the public `fit_h2h4_model` entry point actually used by
  `cli.py`.

All four pass against the fixed code
(`python -m pytest tests/test_models.py -q` → 14 passed, actually run, not
assumed).

## Regression check on the rest of the suite

Ran the full set of tests touching these code paths after the change:
`tests/test_models.py`, `tests/test_bootstrap.py`, `tests/test_pilot.py`,
`tests/test_report.py`, `tests/test_cli.py` — **26 passed** (actually run,
`python -m pytest tests/test_models.py tests/test_bootstrap.py
tests/test_pilot.py tests/test_report.py tests/test_cli.py -q`, 210.9s
wall-clock). No test needed modification: `tests/test_bootstrap.py`'s
`shot_df` fixture was already single-mode
(`generate_shot_rows(smoke_cfg, "finite_shot_end_to_end")`), and
`tests/test_pilot.py` likewise already used single-mode data — the pooling
bug was specific to the `cli.py` call sites listed above, not to the test
fixtures. `tests/test_cli.py::test_run_all_produces_every_required_output_file`
exercises the full `cmd_run_all` pipeline (which calls the now-guarded
`cmd_fit`, `cmd_bootstrap`, `cmd_report`) end-to-end on `configs/smoke.yaml`
and still passes, confirming the guarded default path produces a complete,
valid confirmatory run without hitting the guard.

## Confirmation: does `cmd_fit`'s default path now only ever touch end-to-end-mode rows?

Yes. Traced explicitly:

1. `pw_all` is read from `pointwise_gradient_statistics.parquet` (or
   recomputed), which still legitimately contains both modes' cells — that
   file is a per-cell statistics table, not a fit, and both modes belong in
   it.
2. `pw = pw_all[pw_all["analysis_mode"] == mode]` slices to exactly one mode
   before any fit call, and `mode` defaults to `CONFIRMATORY_MODE`.
3. `fit_h2h4_model(pw)` / `fit_sensitivity_model(pw)` then see single-mode
   data and the guard is a no-op (would only fire if the slice above were
   ever skipped or wrong — an intentional double safety net).
4. No other line in `cmd_fit`'s confirmatory branch touches
   `finite_shot_conditional` rows at all.

## No second bug found

Per the guardrail to stop and report rather than work around anything
unexpected: no second silent-pooling or mode-mixing issue was found while
making this change. The conditional-mode diagnostic path added to `cmd_fit`
was verified to write only to its own `*_diagnostic_*.csv` file and not
touch `confirmatory_hypotheses.csv`, `holm_adjustment.csv`,
`snr_model_coefficients.csv`, or `exact_model_coefficients.csv`.
