# Results

Total experiment runtime: **108.9s** (main experiment 15.8s, depth sweep 93.1s).

## Configuration summary (mean gradient SNR across 50 seeds, L=3)

| # | Configuration | Mean SNR | Median SNR | Std |
|---|---|---|---|---|
| 1 | Baseline (HEA) | 11.242 | 11.292 | 2.533 |
| 2 | Constrained entanglement only | 14.135 | 13.893 | 2.837 |
| 3 | Local cost function only | 10.234 | 9.665 | 3.466 |
| 4 | Residual connections only | 8.168 | 8.092 | 2.703 |
| 5 | Entanglement + local cost | 11.159 | 9.673 | 6.479 |
| 6 | Entanglement + residual | 10.697 | 10.758 | 2.686 |
| 7 | Combined (A+B+C) | 9.504 | 10.044 | 3.046 |

## H1: does the combined configuration (7) beat configs 1-4 individually?

**Result: NO** -- combined mean SNR does *not* exceed all four individual baselines (it only exceeds: residual_only) (not all differences are significant at p<0.05).

| vs. config | mean(combined) | mean(other) | Wilcoxon p | combined > other |
|---|---|---|---|---|
| baseline | 9.504 | 11.242 | 0.0032 | False |
| entanglement_only | 9.504 | 14.135 | 1.77e-11 | False |
| local_cost_only | 9.504 | 10.234 | 0.2955 | False |
| residual_only | 9.504 | 8.168 | 0.0297 | True |

## H2a: entanglement + local cost (config 5) vs. entanglement (2) and local cost (3) alone

- Wilcoxon config 5 vs. config 2: mean 11.159 vs 14.135, p = 0.0001
- Wilcoxon config 5 vs. config 3: mean 11.159 vs 10.234, p = 0.4548
- Gain over baseline: entanglement alone = 2.894, other factor alone = -1.007, config 5 actual = -0.082
- **Sum framing**: additive prediction = 1.887 -> sub-additive (actual < prediction)
- **Product/ratio framing**: multiplicative prediction = 1.145x -> sub-additive (actual ratio 0.993x)

## H2b: entanglement + residual (config 6) vs. entanglement (2) and residual (4) alone

- Wilcoxon config 6 vs. config 2: mean 10.697 vs 14.135, p = 2.02e-10
- Wilcoxon config 6 vs. config 4: mean 10.697 vs 8.168, p = 9.36e-07
- Gain over baseline: entanglement alone = 2.894, other factor alone = -3.074, config 6 actual = -0.545
- **Sum framing**: additive prediction = -0.180 -> sub-additive (actual < prediction)
- **Product/ratio framing**: multiplicative prediction = 0.914x -> super-additive/additive (actual ratio 0.952x)

## H3: depth-dependence of local-cost vs. residual mitigation

Seed-level SNR is heavy-tailed (a near-deterministic shallow circuit can send one parameter's shot-noise variance close to zero while its gradient stays finite, producing an SNR blowup for that single seed) -- the crossover below is therefore located using the **median** across seeds, matching `results/plots/snr_vs_depth.png` (log-scale, median + IQR). Per-depth means are also reported for transparency but can be pulled far above the bulk of the distribution by such outliers.

**Crossover found at L = 2**: residual-only's median SNR dominates at shallower depth and local-cost-only's median SNR dominates from this depth onward -- the **opposite** direction from the H3 hypothesis (which predicted local-cost dominating shallow, residual dominating deep), within the swept depths [1, 2, 3, 5, 8].

| L | median SNR (local) | median SNR (residual) | median SNR (local+residual) | mean SNR (local) | mean SNR (residual) | local > residual (median) |
|---|---|---|---|---|---|---|
| 1 | 8.597 | 20.165 | 8.597 | 168.597 | 19.673 | False |
| 2 | 9.958 | 8.840 | 7.485 | 12.173 | 8.931 | True |
| 3 | 9.665 | 8.092 | 7.251 | 10.234 | 8.168 | True |
| 5 | 8.342 | 7.692 | 7.735 | 8.393 | 7.911 | True |
| 8 | 8.448 | 7.071 | 6.983 | 8.644 | 7.156 | True |

## Notes

- All comparisons use the Wilcoxon signed-rank test on 50 paired seed-level mean-SNR values (identical seeds -> identical theta draws across configurations).
- Full per-parameter raw data: `results/main_experiment_per_parameter.json`, `results/depth_sweep_per_parameter.json`.
- Landscape gradient variance (Var_theta across seeds, secondary measure): `results/main_landscape_variance.csv`.
- Plots: `results/plots/`.

---

# Companion paper: expanded empirical testing (phase 2)

Companion-phase runtime: **6105.3s** (101.8 min) -- main grid 1385.6s, headline reference 57.9s, sensitivity check 63.0s, scoped depth sweep 4598.7s.

**Seed-count reduction (runtime budget):** the main n x task grid and the sensitivity check use **50 seeds** (matching the pilot's own seed count) instead of the spec's suggested 200 -- a calibration run showed the full grid at 200 seeds alone would take ~88 minutes, and combined with the depth sweep and sensitivity check would total ~2.7 hours, exceeding the stated 1-2 hour budget. The scoped depth sweep keeps the full **200 seeds** (it fits the budget on its own and is the piece most sensitive to a heavy-tailed distribution at low L). The single grid point most comparable to the pilot (n_qubits=4, task=tfim_h0.5) is additionally re-run at the full **200 seeds** as this phase's headline reference result -- see below.

## Main grid: does the pilot's n=4/TFIM(h=0.5) finding replicate?

Heatmap: `results/plots/grid_hypothesis_heatmap.png` (rows = task, columns = n_qubits, green/Y = matches the labeled claim).

- Entanglement-alone is the best of the 7 configs: **7/27** grid points.
- Combined underperforms baseline: **10/27** grid points.
- H2a (entanglement+local) is sub-additive, sum framing: **23/27** grid points.
- H2b (entanglement+residual) is sub-additive, sum framing: **5/27** grid points.

Grid points where at least one of the two headline pilot claims does *not* replicate:

| task | n_qubits | entanglement best | combined < baseline | best config |
|---|---|---|---|---|
| tfim_h0.5 | 3 | False | True | entanglement_local |
| tfim_h0.5 | 6 | False | False | entanglement_residual |
| tfim_h0.5 | 7 | False | False | entanglement_residual |
| tfim_h0.5 | 8 | False | False | entanglement_residual |
| tfim_h0.5 | 9 | False | False | entanglement_residual |
| tfim_h0.5 | 10 | False | False | entanglement_residual |
| tfim_h2.0 | 3 | False | True | entanglement_local |
| tfim_h2.0 | 5 | False | False | entanglement_residual |
| tfim_h2.0 | 6 | False | False | entanglement_residual |
| tfim_h2.0 | 7 | False | False | entanglement_residual |
| tfim_h2.0 | 8 | False | False | entanglement_residual |
| tfim_h2.0 | 9 | False | False | entanglement_residual |
| tfim_h2.0 | 10 | False | False | entanglement_residual |
| xxz_delta0.5 | 2 | False | True | entanglement_local |
| xxz_delta0.5 | 5 | False | False | entanglement_residual |
| xxz_delta0.5 | 6 | False | False | entanglement_residual |
| xxz_delta0.5 | 7 | False | False | entanglement_residual |
| xxz_delta0.5 | 8 | False | False | entanglement_residual |
| xxz_delta0.5 | 9 | False | False | entanglement_residual |
| xxz_delta0.5 | 10 | False | False | entanglement_residual |

## Headline reference (n_qubits=4, TFIM h=0.5, 200 seeds)

Same grid point as the pilot's own experiment, re-run at the full requested seed count for direct comparison to the pilot's 50-seed result (see `results/main_grid_headline_reference.csv`).

- Best config: **entanglement_only** (entanglement-alone best: True; combined < baseline: True)
- H1 (combined exceeds configs 1-4): False
- H2a sub-additive (sum framing): True
- H2b sub-additive (sum framing): False

## Mean vs. sum residual-reduction sensitivity check

`mean` is the primary residual reduction throughout this phase (n-invariant in scale); `sum` is retained as a secondary sensitivity check at n_qubits=4, depth=L_MAIN, measurement budget=N_SHOTS (narrower than the original {4,10} x 3-task range, now that `mean` no longer needs cross-n validation as the default). Plot: `results/plots/sensitivity_sum_vs_mean.png` (residual-bearing configs only).

**1/3** (task, n_qubits) points show a qualitative difference between 'mean' and 'sum' reduction on at least one of H1/H2a/H2b/best-config/pilot-finding outcomes.

| task | n_qubits | diverging outcomes |
|---|---|---|
| tfim_h2.0 | 4 | h2b_product_framing_sub_additive |

## Parameter routing and operationally-resolvable fraction

Every parameter-level row in the main grid carries an explicit `parameter_type`/`gradient_method`/`variance_method`/`estimator_family` tag (`circuit_theta` via parameter-shift, or `residual_alpha` via the dedicated exact-linear gradient + independent-per-qubit analytic variance path), and every row passed `experiment.assert_no_residual_alpha_misrouting` at generation time -- no `alpha_l` was ever routed through the parameter-shift path or vice versa.

- Total `circuit_theta` parameters seen: **170100**; total `residual_alpha` parameters seen: **12150** (across 9450 main-grid seed-config rows).
- `deterministic_nonzero` parameters (e.g. `alpha_1`, resolvable but noise-free): **4050**; `inactive_zero` parameters (flat, no signal): **0**.
- Operationally-resolvable fraction per seed-config row: min **1.000**, mean **1.000**, max **1.000**.

## Scoped H3 depth sweep (n_qubits in {4, 6, 10}, reference task only)

Plot: `results/plots/depth_sweep_scoped_faceted.png`. The deterministic-parameter rule (snr.py `_DETERMINISTIC_VAR_TOL`) is applied throughout.

| n_qubits | crossover depth L | crossover direction |
|---|---|---|
| 4 | 5 | local_overtakes_residual |
| 6 | n/a | none (one config dominates throughout) |
| 10 | n/a | none (one config dominates throughout) |

### Does the deterministic-parameter rule resolve the L=1 mean/median gap?

Checked directly against the real per-seed data at L=1 (`depth_sweep_scoped_l1_gap_diagnostic.csv`), not assumed:

| n_qubits | config | mean(mean_snr) | median(mean_snr) | mean/median ratio | max deterministic_nonzero params/seed |
|---|---|---|---|---|---|
| 4 | local_and_residual | 68.287 | 10.196 | 6.70x | 1 |
| 4 | local_cost_only | 68.287 | 10.196 | 6.70x | 0 |
| 4 | residual_only | 19.773 | 20.840 | 0.95x | 1 |
| 6 | local_and_residual | 45.524 | 6.797 | 6.70x | 1 |
| 6 | local_cost_only | 45.524 | 6.797 | 6.70x | 0 |
| 6 | residual_only | 15.796 | 16.197 | 0.98x | 1 |
| 10 | local_and_residual | 27.315 | 4.078 | 6.70x | 1 |
| 10 | local_cost_only | 27.315 | 4.078 | 6.70x | 0 |
| 10 | residual_only | 12.154 | 12.343 | 0.98x | 1 |

**Answer: partially, and only for the mechanism it actually targets.** `residual_only` has `alpha_1` (`deterministic_nonzero` by construction: block 1's input is always the fixed `|0...0>` state, giving a real nonzero gradient with exactly zero variance) and its mean/median ratio is close to 1x -- the rule cleanly excludes it from finite-SNR aggregates while still counting it toward the operationally-resolvable fraction. `local_cost_only` and `local_and_residual` show **zero** `deterministic_nonzero` parameters at L=1 yet still show a large mean/median ratio: inspecting the offending seed directly shows a shot-noise variance of order 1e-9 -- three orders of magnitude above the `1e-12` tolerance, so correctly classified as `active`, not `deterministic_nonzero`. This is a specific seed's random theta draw landing extremely close to a `Z0Z1` eigenstate -- a genuine, continuous small-sample statistical fluke, not a provably-exact-zero case, and not something the deterministic-parameter rule fixes or should fix (there is no principled tolerance that excludes it without also excluding legitimately large finite SNRs from other seeds). The median remains the correct robust summary statistic for this second phenomenon, exactly as the pilot's own H3 analysis already documents.

## Companion-phase notes

- Full grid raw data: `results/main_grid_summary.csv` (no per-parameter JSON at grid scale -- see README 'Design choices' data-volume scoping note).
- Hypothesis-test detail per grid point: `results/grid_hypothesis_results.json`.
- Parameter-routing summary (circuit_theta vs. residual_alpha counts, operationally-resolvable fraction): `results/parameter_routing_summary.json`.
- Sensitivity check raw data: `results/sensitivity_sum_summary.csv`, `results/sensitivity_mean_summary.csv`.
- Scoped depth sweep per-parameter detail (incl. `classes`, `parameter_type`, `gradient_method`, `variance_method` per parameter): `results/depth_sweep_scoped_per_parameter.json`.
- Hamiltonian + brick-pattern regression checks for every (task, n) point: `results/hamiltonian_check_grid.json`.
