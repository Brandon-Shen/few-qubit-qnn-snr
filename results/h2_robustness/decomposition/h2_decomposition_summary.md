# H2 decomposition: numerator vs. denominator (Phase 3, diagnostic only)

Diagnostic / mechanism-explaining only. Does not replace the SNR_est
estimand or the adopted H2 result.

Eligible rows (matched to the adopted SNR model): **101891**

## E:L coefficient by model

| model | response | estimate | 95% CI | n_obs |
|---|---|---:|---|---:|
| SNR_est (reference, not refit) | arcsinh(SNR_est) | 0.024996 | [0.010729, 0.039262] | 101891 |
| numerator (gradient-mean magnitude) | arcsinh(|mu_hat|) | 0.004315 | [0.003076, 0.005554] | 101891 |
| denominator (repeated-shot SD) | log(shot_sd) | -0.149866 | [-0.173538, -0.126194] | 101891 |

**Interpretation (fixed rule, computed mechanically, not selected post hoc):** both numerator and denominator show an E:L effect distinguishable from zero at alpha=0.05 (unadjusted, diagnostic)

## Descriptive bias / sign-agreement by (E, L) [not a fitted model]

| E | L | n_cells | mean abs bias | median abs bias | sign agreement rate | mean SNR_exact |
|---|---|---:|---:|---:|---:|---:|
| 0 | 0 | 25219 | 0.007288 | 0.002424 | 0.7744 | 0.6048 |
| 0 | 1 | 25600 | 0.012494 | 0.006007 | 0.8223 | 1.0158 |
| 1 | 0 | 25472 | 0.007919 | 0.002866 | 0.8146 | 0.7155 |
| 1 | 1 | 25600 | 0.013649 | 0.006308 | 0.8619 | 1.1331 |