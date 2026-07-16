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
