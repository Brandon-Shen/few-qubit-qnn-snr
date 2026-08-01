# Q1 (best-single vs. combined-configuration SNR), end-to-end-only

**Status: exploratory only**, per `qnn_snr/stats/exploratory.py`'s own
framing ("Everything here is explicitly labeled exploratory and must never
be pooled into the H1-H4 Holm family or presented as confirmatory"). Nothing
below affects any Holm-corrected confirmatory conclusion.

## Method

`exploratory_configuration_8_comparisons()` (`qnn_snr/stats/exploratory.py`)
takes a `configuration_summaries` table and, per (depth, budget) cell,
compares configuration 8 (all three interventions combined) against whichever
of configurations 2/3/4 (single-intervention) has the higher `rms_SNR_est`.
`configuration_summaries()` (`qnn_snr/stats/descriptive.py`) builds
`rms_SNR_est` from whatever `pointwise_df` it's given, filtered only by
`(configuration_id, depth, budget)` — **not** by `analysis_mode** — so the
production `cmd_report` path (which passes the full pooled
`pointwise_gradient_statistics.parquet`) pools both modes into this
computation, the same pattern already documented for the bias/sign-agreement
figures in `verification/mode_split_descriptive_stats.md`. This task
recomputes it filtered to `analysis_mode == "finite_shot_end_to_end"` only.

`physics_df` (`final_tfim_energy`, `global_fidelity`, entanglement
diagnostics) and `resource_df` (`total_circuit_evaluations_mean`, used for
the cost-normalized SNR check) were rebuilt fresh for this task using the
same `physics_summary_rows(cfg)` / `resource_accounting_table(shot_df)`
calls `cmd_report` uses, with `resource_df` filtered to
`finite_shot_end_to_end` rows.

## Result: 20-cell comparison, end-to-end-only

| depth | budget | best single config | config8 RMS SNR | best-single RMS SNR | config8 exceeds? |
|---|---|---|---:|---:|---|
| 1 | 250  | 3 | 2.4116 | 2.5640 | No |
| 1 | 500  | 3 | 3.4675 | 3.6128 | No |
| 1 | 1000 | 3 | 4.8720 | 5.0234 | No |
| 1 | 2000 | 3 | 6.7375 | 7.4326 | No |
| 2 | 250  | 3 | 1.2245 | 1.3702 | No |
| 2 | 500  | 3 | 1.8269 | 2.0244 | No |
| 2 | 1000 | 3 | 2.5045 | 2.8838 | No |
| 2 | 2000 | 3 | 3.7358 | 4.0928 | No |
| 3 | 250  | 3 | 0.9171 | 0.8513 | **Yes** |
| 3 | 500  | 3 | 1.4075 | 1.2954 | **Yes** |
| 3 | 1000 | 3 | 2.0223 | 1.8568 | **Yes** |
| 3 | 2000 | 3 | 2.8466 | 2.6878 | **Yes** |
| 4 | 250  | 3 | 0.5047 | 0.5731 | No |
| 4 | 500  | 3 | 0.8026 | 0.8839 | No |
| 4 | 1000 | 3 | 1.1776 | 1.2795 | No |
| 4 | 2000 | 3 | 1.7758 | 1.8278 | No |
| 6 | 250  | 3 | 0.2974 | 0.4158 | No |
| 6 | 500  | 3 | 0.4672 | 0.5906 | No |
| 6 | 1000 | 3 | 0.7156 | 0.8801 | No |
| 6 | 2000 | 3 | 1.0337 | 1.2824 | No |

**Best single-intervention configuration is configuration 3 (L-only) in all
20/20 cells** — identical to the pooled-data answer.

**Configuration 8 exceeds the best single intervention in 4/20 cells, all
at depth 3 (every budget level), and nowhere else.**

## Direct comparison against the old pooled-data answer

| | Old pooled (superseded) | New end-to-end-only |
|---|---|---|
| Best single-intervention config, all 20 cells | configuration 3, 20/20 | configuration 3, 20/20 (**unchanged**) |
| Config 8 beats best single | **9/20** | **4/20** |
| Winning cells | depth 3 (all 4 budgets) + depth 4 (all 4 budgets) + depth 6/budget 2000 | depth 3 (all 4 budgets) only |

- **Identity of the best single configuration does not change**: configuration 3
  remains the best single intervention in every one of the 20 cells under
  both pooled and end-to-end-only data. This part of Q1's answer is robust
  to the mode-pooling fix.
- **The 9/20 figure does move materially, roughly by half (9/20 → 4/20)**,
  not just noise-level drift. The pattern also narrows in a specific way:
  under pooled data, configuration 8's advantage extended across depth 3
  *and* depth 4 (8 of the 9 winning cells) plus one high-budget depth-6 cell;
  under end-to-end-only data, the depth-4 wins and the depth-6/budget-2000
  win all disappear, leaving only the depth-3 cluster (which is itself
  unchanged in all 4 of its budget levels — configuration 8 still wins there
  under both pooled and end-to-end-only data). **Read plainly: whatever
  drove configuration 8's apparent advantage at depth 4 and at
  depth 6/budget 2000 in the pooled data was coming disproportionately from
  conditional-mode rows, not from the end-to-end estimator the paper treats
  as confirmatory** — removing those rows removes those wins specifically,
  while leaving the depth-3 result intact.
- This is an exploratory finding about where a previously-reported
  "sometimes exceeds" pattern actually lives across depth and mode; it does
  not change the qualitative headline (configuration 8 does **not**
  uniformly exceed the best single intervention — it wins in a minority of
  cells under both pooled and end-to-end-only data, 9/20 and 4/20
  respectively, both well short of 20/20).

## Confirming Q2 needs no rerun (verified directly, not assumed)

`physics_summary_rows()` (`qnn_snr/stats/descriptive.py`) builds
`final_tfim_energy`/`global_fidelity`/entanglement-diagnostic columns
directly from `forward_pass_exact(...)` and `evaluate_both_costs(...)` on
the exact final statevector at each `(configuration_id, depth,
initialization_id)` — it never reads `pointwise_df`, `shot_df`, or any
finite-shot-derived quantity at all, and never even constructs an
`analysis_mode` column:

```
physics_df.columns = ['configuration_id', 'E', 'L', 'R', 'depth',
                       'initialization_id', 'final_tfim_energy',
                       'global_fidelity', 'mean_entanglement_entropy',
                       'mean_purity']
```

**No `analysis_mode` column exists in `physics_df` at all** — confirmed by
inspecting the actual columns produced, not inferred from the function's
docstring. Consequently `config8_final_energy`, `baseline_final_energy`,
`config8_energy_improves_on_baseline`, `config8_global_fidelity`,
`baseline_global_fidelity`, and `config8_fidelity_improves_on_baseline`
were directly compared, cell-by-cell, between the old pooled
`results/production_confirmatory/exploratory_results.csv` and this task's end-to-end-only
recomputation: **bit-for-bit identical across all 20 cells**
(`pandas.DataFrame.compare()` on the two column sets returns an empty diff).
**Q2 required no rerun, and this is now verified rather than assumed.**

## Reproduction

```python
import pandas as pd
from qnn_snr.config import load_config
from qnn_snr.schema import read_tidy_dataset
from qnn_snr.stats.descriptive import configuration_summaries, physics_summary_rows, resource_accounting_table
from qnn_snr.stats.exploratory import exploratory_configuration_8_comparisons

cfg = load_config("configs/confirmatory.yaml")
pw = pd.read_parquet("results/production_confirmatory/pointwise_gradient_statistics.parquet")
pw_e2e = pw[pw["analysis_mode"] == "finite_shot_end_to_end"]

exact_df = read_tidy_dataset("results/production_confirmatory/raw/exact.parquet")
exact_df = exact_df[exact_df["analysis_mode"] == "statevector_exact"]
shot_e2e = read_tidy_dataset("results/production_confirmatory/raw/finite_shot_end_to_end.parquet")
resource_df = resource_accounting_table(shot_e2e)
physics_df = pd.DataFrame(physics_summary_rows(cfg))

summaries = configuration_summaries(pw_e2e, exact_df, physics_df, resource_df)
comparisons = exploratory_configuration_8_comparisons(summaries)
```
