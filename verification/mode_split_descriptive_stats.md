# Mode-split descriptive statistics: fold-change indices, bias, and sign agreement

**Status: consistency cleanup, not a bug fix.** Unlike the H2–H4 confirmatory
fit (`verification/mode_pooling_guard.md`), these descriptive quantities
were never claimed to be end-to-end-only — `qnn_snr/stats/interactions.py`
and `qnn_snr/stats/descriptive.py` compute them from whatever `pointwise_df`
is passed in, and the production `cmd_report` path passes the full pooled
table. This document adds a per-mode breakdown alongside the existing pooled
figures because, per the paper's own reasoning about what each mode
isolates, the pooled figures turn out to hide a real and fully consistent
difference between modes (see §2). **Nothing in `qnn_snr/` was changed for
this task** — this is a reporting addition, not a code fix; the production
`configuration_summaries`/`compute_interaction_indices` calls in `cli.py`
still receive pooled `pointwise_df` by design (they are purely descriptive
tables, not model fits, and pooling a descriptive summary is a defensible
default in a way pooling a confirmatory model fit is not).

## 1. Fold-change indices (`I_AB`, `J_AB`)

`compute_interaction_indices(pointwise_df, exact_df)` computes two separate
quantities per pair (E_L, E_R, L_R):

- `I_AB` uses `pointwise_df["SNR_est"]` (RMS pointwise SNR per
  configuration) — **mode-dependent**, since `SNR_est` comes from the
  finite-shot estimator.
- `J_AB` uses `exact_df["exact_gradient"]` (RMS exact-gradient magnitude per
  configuration) — **mode-independent**, since `exact_df` is always
  `analysis_mode == "statevector_exact"` regardless of which finite-shot
  mode `pointwise_df` came from.

Confirmed empirically: `J_AB` is bit-identical across all three runs below
(1.241760, 1.183744, 0.992065 for E_L/E_R/L_R respectively, unchanged). Only
`I_AB` needed recomputation.

| pair | I_AB (pooled, existing) | I_AB (end-to-end-only, primary) | I_AB (conditional-only, secondary) | J_AB (mode-invariant) |
|---|---:|---:|---:|---:|
| E_L | 1.072295 | **1.034074** | 1.099814 | 1.241760 |
| E_R | 1.033594 | **1.010312** | 1.049486 | 1.183744 |
| L_R | 0.997088 | **0.963169** | 1.019186 | 0.992065 |

**End-to-end-only is reported as the primary version** (consistent with it
now being the confirmatory mode per
`verification/confirmatory_numbers_adopted.md`); the pooled and
conditional-only versions are kept as labeled secondary comparisons in the
table above.

**Does splitting by mode reveal anything beyond the pooled figures?**
Modestly, and mostly in the E_L/E_R direction rather than L_R:

- E_L and E_R keep the same qualitative label ("super-additive fold change",
  `I_AB > 1`) in all three of pooled/end-to-end-only/conditional-only — the
  magnitude shifts somewhat (E_L: 1.072 pooled vs 1.034 end-to-end-only vs
  1.100 conditional-only) but the direction and rough size are stable.
- **L_R is the one pair where the qualitative label is sensitive to which
  data feeds it**: `I_AB(L_R)` = 0.997 (pooled, "sub-additive" by the
  `< 1` rule), 0.963 (end-to-end-only, "sub-additive"), 1.019
  (conditional-only, "**super-additive**"). All three values sit within
  ~4% of exactly 1.0 (multiplicative independence) — this reads as **a
  genuinely borderline case whose sub-/super-additive label flips with small
  changes in which rows feed the RMS, not a robust qualitative finding in
  either direction**. The flip itself is the useful piece of information:
  it says the L_R fold-change label in the existing `results/production_confirmatory/interaction_indices.csv`
  (pooled, "sub-additive") should not be read as a confident categorical
  claim.

## 2. Bias distribution and sign-agreement fraction, split by mode

Computed directly from `results/production_confirmatory/pointwise_gradient_statistics.parquet`
(102,400 cells per mode), not through `configuration_summaries` (which
would require re-deriving `physics_df`/`resource_df` for no benefit — the
relevant columns, `absolute_bias`/`bias`/`sign_agreement`/
`signed_mean_ci_excludes_zero`, already exist directly on the pointwise
table).

| quantity | `finite_shot_conditional` | `finite_shot_end_to_end` | pooled (existing) |
|---|---:|---:|---:|
| `sign_agreement_fraction` | **0.869209** | **0.814404** | 0.841807 |
| `median(absolute_bias)` | **0.002651** | **0.004162** | 0.003285 |
| `mean(absolute_bias)` | 0.005121 | 0.010303 | 0.007712 |
| `IQR(absolute_bias)` | [0.000863, 0.006445] | [0.001286, 0.011149] | [0.001039, 0.008425] |
| `fraction_ci_excludes_zero` (mean signed-gradient CI) | 0.601426 | 0.517412 | — (not in existing pooled summary at this granularity) |

**This is not a marginal or noisy difference — it is completely consistent
across every one of the 8 configurations**, checked directly:

| configuration_id | sign_agreement (conditional) | sign_agreement (end-to-end) | median\|bias\| (conditional) | median\|bias\| (end-to-end) |
|---|---:|---:|---:|---:|
| 1 | 0.8014 | 0.7630 | 0.0012 | 0.0017 |
| 2 | 0.8576 | 0.8130 | 0.0015 | 0.0021 |
| 3 | 0.8823 | 0.8226 | 0.0032 | 0.0046 |
| 4 | 0.8048 | 0.7627 | 0.0019 | 0.0033 |
| 5 | 0.9094 | 0.8692 | 0.0032 | 0.0047 |
| 6 | 0.8768 | 0.8080 | 0.0024 | 0.0040 |
| 7 | 0.8993 | 0.8220 | 0.0044 | 0.0079 |
| 8 | 0.9221 | 0.8546 | 0.0047 | 0.0087 |

Conditional mode has **higher sign agreement and lower absolute bias than
end-to-end mode in all 8 of 8 configurations**, with no exceptions. The
gap is not fixed in absolute terms — it widens at higher-bias configurations
(configs 7, 8: end-to-end's median bias is ~1.8x conditional's) and stays
proportionally similar at lower-bias configurations (configs 1, 4: ~1.4-1.7x).

**Does splitting by mode reveal anything beyond the pooled figures?** Yes,
and this is the more informative of the two recomputations in this
document. The pooled `sign_agreement_fraction` (0.8418) and
`median_absolute_bias` (0.003285) sit, as expected from an unweighted
average of two equal-sized groups, roughly between the two modes' values —
but reporting only the pooled number obscures that this is not one
homogeneous population. The split confirms, directly and without exception
across configurations, the paper's own stated mechanism for why the two
modes are collected separately: conditional mode isolates node-Jacobian
(parameter-shift) noise only, while end-to-end mode additionally carries
forward-feature re-estimation noise from every non-terminal block, and that
extra noise source visibly and consistently degrades both bias and sign
agreement. This is independent corroboration, at the descriptive-statistics
level, of the same mechanism invoked in
`verification/conditional_vs_endtoend_comparison.md` to explain the
`beta_LRd` sign disagreement between modes.

## Reproduction

```python
import pandas as pd
from qnn_snr.stats.interactions import compute_interaction_indices

pw = pd.read_parquet("results/production_confirmatory/pointwise_gradient_statistics.parquet")
exact_df = pd.read_parquet("results/production_confirmatory/raw/exact.parquet")
exact_df = exact_df[exact_df["analysis_mode"] == "statevector_exact"]

for mode in ("finite_shot_end_to_end", "finite_shot_conditional"):
    idx = compute_interaction_indices(pw[pw["analysis_mode"] == mode], exact_df)

for mode in ("finite_shot_conditional", "finite_shot_end_to_end"):
    sub = pw[pw["analysis_mode"] == mode]
    sub["sign_agreement"].mean()
    sub["absolute_bias"].median()
```
