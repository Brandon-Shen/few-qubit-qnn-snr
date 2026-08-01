# H2 zero-variance and current-result audit (Phase 2, original data only)

Reproduced at commit `7b57e3e1a03fb4b2bea3e488842ca18cdface54b` from frozen inputs in `results/production_confirmatory/` (hashes below). No original file was modified.

## Input hashes

- `pointwise`: `99a4decf8597c9fcc5a61a8e59075d34e1cf6668714ee19e38b39258e15d1342`
- `raw_exact`: `77e54bed863de79be0d1ebb4937f015fe29a1b1cb5d58e0f216f3acd4b9bb542`
- `raw_end_to_end`: `22b5e761f461c6bfde7a60a4efa7ac13bc59ae003488be84d2f0c1e57ddb7f39`
- `raw_conditional`: `b15b19088d22a0429f48158cdee5ee3caec52f6819815579b3e6aed189afe413`

## Cell counts and zero-variance exclusion

- End-to-end total cells: **102400**; excluded (zero variance): **509** (0.497%).
- Conditional total cells: **102400**; excluded: **1324** (1.293%).
- **Confined to L=0: True** (L=0 excluded=509, L=1 excluded=0).
- Non-finite `SNR_est` rows not explained by `zero_variance_flag` (should be 0): **0**.

## Reproduced H2-H4 Wald fit

- `n_obs`=101891, converged=True, optimizer=lbfgs, singular_fit=False
- Reproduced `E:L` (H2): **0.024995843985972** (adopted: 0.024995843985972, bit-for-bit match: True)

| coefficient | estimate | se | wald_z | p_unadjusted | ci95_lo | ci95_hi |
| --- | --- | --- | --- | --- | --- | --- |
| E:L | 0.024995843985971582 | 0.007279011371641417 | 3.4339613870303682 | 0.0005948289235313542 | 0.010729243854496907 | 0.039262444117446255 |
| E:R | -0.0009575787575784316 | 0.007292917086826747 | -0.13130257017567273 | 0.8955359586892191 | -0.015251433589995625 | 0.013336276074838763 |
| L:R:depth_z | -0.010178757716721849 | 0.005362074992735445 | -1.8982870867177464 | 0.05765827411115354 | -0.020688231584886193 | 0.0003307161514424957 |

## Current bootstrap interval (read from `results/production_corrected_end_to_end/bootstrap_end_to_end_h2_h4_summary.csv`)

| coefficient | n_pooled | n_failed | fit_failure_rate_pct | median | ci_lo | ci_hi | width | includes_zero |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E:L | 443 | 0 | 0.0 | 0.0236854648080451 | -0.0180243482083222 | 0.0656878879950304 | 0.0837122362033526 | True |
| E:R | 443 | 0 | 0.0 | -0.0018676837644237 | -0.0302982755992361 | 0.0244783606838962 | 0.0547766362831324 | True |
| L:R:depth_z | 443 | 0 | 0.0 | -0.0108112626682918 | -0.0269750506541731 | 0.0064031121402603 | 0.0333781627944335 | True |

## Residual SD by depth (reproduced fit)

| depth | resid_sd |
| --- | --- |
| 1.0 | 0.6592752974175753 |
| 2.0 | 0.5392617126402137 |
| 3.0 | 0.4521001373286116 |
| 4.0 | 0.36596695588179995 |
| 6.0 | 0.27603260774395916 |

## Residual SD by budget (reproduced fit)

| budget | resid_sd |
| --- | --- |
| 250.0 | 0.3010579039402127 |
| 500.0 | 0.34602019465752065 |
| 1000.0 | 0.4225344432649439 |
| 2000.0 | 0.5132225710620099 |
