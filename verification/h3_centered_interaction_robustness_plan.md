# Centered H3 interaction robustness plan

**Status:** post-primary explanatory and sensitivity analysis. It cannot alter corrected H3 or the Holm family.

## Inputs, coding, and simple interactions

Use original `results/production_confirmatory/pointwise_gradient_statistics.parquet`, one estimator mode at a time, with existing finite-SNR eligibility, response `asinh(SNR_est)`, centered factors, depth/budget scaling, REML, optimizer fallback, initialization intercept, and nested matched-parameter intercept. Primary explanatory input is end-to-end mode; conditional mode is diagnostic.

From the frozen corrected full-sweep covariance derive: ER at `L=0 = E:R` in direct coding (equivalently `E_c:R_c - .5 E_c:L_c:R_c`); ER at `L=1 = E:R + E:L:R` (equivalently `E_c:R_c + .5 E_c:L_c:R_c`); and equal average `E_c:R_c`. Use full covariance for SEs/Wald CIs/raw normal p-values. These three explanatory contrasts receive no multiplicity adjustment.

Transform the 443 frozen draws because they contain `E:R` and `E:L:R`; report medians/percentile intervals for L=0, L=1, and average. The already committed explicit centered refits of regression-stream iterations 0--2 validate transformation; additionally test simple identities mechanically.

## Sensitivities

- Active residual: filter D to `{3,4,6}`, preserve frozen full-sweep `depth_z`, eligibility, centered formula, and random effects. Report average and L-specific ER contrasts and Wald inference. No active-subset nested bootstrap is planned: full-sweep draws cannot be filtered after fitting, and a new finite-shot nested run would be a separate computational estimand. State this limitation rather than reusing the full-sweep interval.
- Depth heterogeneity: fit one centered categorical model with `E_c:R_c:C(depth, Sum)` moderation while preserving identifiable H2--H4 nuisance structure. Derive covariance-aware ER contrasts at five depths, joint Wald test, equal-depth and eligible-observation-weighted summaries. Run initialization-clustered OLS using the identical fixed design if supported by existing depth infrastructure; otherwise omit with reason.
- Estimator mode: fit corrected centered H2--H4 separately on end-to-end and conditional eligible rows. Report average and objective-specific ER contrasts, interval overlap, direction/magnitude agreement, and exclusions of zero; never pool modes.
- Leave-one-initialization-out: transform existing end-to-end LOO coefficients only if every row contains `E:R` and `E:L:R`; otherwise run 50 centered LOO fits. Report sign flips, raw-p crossings, extrema, and maximum standardized shift without treating LOO as confirmatory.

Outputs: `results/h3_centered_robustness/` model/contrast/depth/mode/LOO CSV/JSON and figure source data; `verification/h3_centered_interaction_robustness_results.{md,json}`. Recommended category is chosen by frozen rules: “robust interaction” only if full-sweep Wald and bootstrap exclude zero with consistent objective/mode/depth direction; “objective-specific interaction only” if evidence is confined to one objective; “model-dependent directional signal” if Wald rejects but bootstrap/major sensitivities do not; otherwise “no stable conclusion.” Stop for rank deficiency, model-space change, altered eligibility, or unavailable contrast covariance.
