# Proposed manuscript revisions arising from the H2 robustness/replication package

**Not applied to `paper/main.tex`.** This is proposed text only, per the
task instruction not to rewrite manuscript claims until the analyses are
complete. Source: `verification/h2_robustness_replication_plan.md` and
`verification/h2_robustness_replication_results.md`
(`results/h2_robustness/`, `results/h2_replication_v1/`).

**Status: final — all placeholders below filled in from the completed
Phase 1-7 results** (`verification/h2_robustness_replication_results.md`).

---

## Proposed addition to Methods (a new paragraph, after the existing
mixed-model description in the Methods section)

> Because the estimator-SNR ratio can obscure whether an interaction
> arises from the gradient-mean magnitude, the repeated-shot variance, or
> their relationship, and because zero-variance cells are excluded
> asymmetrically across the design (Section 4.1), we additionally fit two
> diagnostic models on the identical eligible row set as the confirmatory
> SNR model: an `arcsinh`-transformed model of the absolute repeated-shot
> gradient mean (numerator), and a log-transformed model of the
> repeated-shot standard deviation (denominator). We also refit the
> confirmatory fixed-effect specification as a cluster-robust ordinary
> least-squares regression (clusters = initialization) as a
> heteroscedasticity-agnostic alternative to the mixed model's Wald
> inference, and refit it separately within each block count. These are
> reported as robustness and mechanism-diagnostic analyses
> (Appendix X), not as replacements for the prespecified confirmatory
> model.

## Proposed addition to Results (immediately after the existing H2
paragraph, before the Limitations discussion)

> **H2 robustness.** The positive `E:L` interaction decomposes into two
> components that both move in the direction that increases `SNR_est`:
> the gradient-mean magnitude increases under `E=L=1`
> (`arcsinh|mu_hat|` `E:L` coefficient `+0.004315`, 95% CI
> `[0.003076, 0.005554]`) and the repeated-shot standard deviation
> decreases (`log(shot_sd)` `E:L` coefficient `-0.149866`, 95% CI
> `[-0.173538, -0.126194]`) — the interaction is not an artifact of one
> component, and this decomposition is stable under leave-one-
> initialization-out (no sign reversal in either component across all 50
> deletions). However, the statistical significance of the aggregate
> effect is not robust to three independent relaxations of the mixed
> model's assumptions. A cluster-robust (initialization-level) OLS refit
> of the identical fixed-effect specification gives `E:L = 0.023550` with
> a 95% CI of `[-0.021739, 0.068839]` (p=0.308); an independently
> implemented initialization-level resampling scheme (n=50, with explicit
> per-iteration zero-variance accounting) gives a percentile CI of
> `[-0.003038, 0.066606]`. Both include zero, consistent with (and
> independently corroborating) the existing nested bootstrap's
> non-corroboration (Section [existing bootstrap section]; n=443,
> `[-0.018024, 0.065688]`). Separately, refitting within each block count
> shows the effect is not of consistent sign: it is significantly
> *negative* at block count 2 (`-0.111762`, 95% CI
> `[-0.164917, -0.058608]`), negative but not distinguishable from zero at
> block count 1, and positive and significant at block counts 3, 4, and 6
> — the deeper block counts comprising 81% of the eligible data and
> dominating the pooled estimate.
>
> An independent replication (new seed namespace, identical design,
> `R_rep=30` matching the original exactly) reproduces the direction and
> statistical significance of H2 (`E:L = 0.049294`, 95% CI
> `[0.035236, 0.063352]`; its own bootstrap, `n=30`,
> `[0.015691, 0.069828]`) and independently reconfirms the zero-variance
> exclusion's 100% confinement to `L=0` under entirely new randomness.
> The replication's point estimate is approximately twice the original's,
> however (3.34 original-standard-error units away), which we do not
> treat as a clean magnitude match: per our prespecified interpretation
> rule, this is **"direction replicated but magnitude uncertain,"** not
> confirmed.

## Proposed revision to the existing Limitations paragraph

Current text (paraphrased from context established earlier in this
session) frames the bootstrap non-corroboration as an open, unresolved
tension. Proposed replacement/extension:

> The percentile bootstrap's non-corroboration of H2 (Section
> [results-robustness]) is not an isolated disagreement: an
> initialization-level cluster-robust standard error and an independently
> implemented initialization-level resampling scheme, both computed
> without relying on the bootstrap's own implementation, produce the same
> qualitative conclusion (95% CI includes zero). Furthermore, the `E:L`
> effect is not homogeneous across block counts, reversing sign at the
> shallowest block counts tested. We therefore do not treat H2 as a
> robust finding independent of the specific inferential assumptions of
> the prespecified mixed model, even though the prespecified Wald/Holm
> test does reject the null and remains the paper's confirmatory decision
> per the preregistered analysis plan. An independent replication at the
> original design and replicate count reproduces the effect's direction
> and statistical significance but not its magnitude (point estimate
> approximately double the original's); we characterize this as
> "direction replicated but magnitude uncertain."

## Proposed revision to the Abstract

Current framing (as established in this session's exploration of
`paper/main.tex`) reports H2 as rejected under Wald/Holm without
qualifying its robustness in the abstract itself. Proposed addition (one
sentence, appended to the existing H2-related abstract sentence):

> ...though this effect's statistical significance depends on the
> specific variance-structure assumptions of the confirmatory model and
> is not consistent in sign across block counts when examined outside
> those assumptions; an independent replication reproduces its direction
> and significance but not its magnitude.

## Proposed revision to the Conclusion

> H2 (the `E`x`L` interaction on estimator SNR) illustrates a case where
> a prespecified, formally rejected hypothesis does not straightforwardly
> license a robust scientific claim: four lines of evidence developed
> post hoc — a nested bootstrap, a cluster-robust reanalysis, an
> independently implemented resampling scheme, and a block-count
> stratification — all show that either the interval includes zero or
> the effect's sign is unstable across a design dimension the
> confirmatory model pools over. An independent replication at the
> original design nonetheless reproduces the effect's direction and
> statistical significance, at roughly twice the original magnitude —
> evidence for a real, replicable phenomenon whose precise size is not
> yet well pinned down and whose statistical significance in the original
> sample is sensitive to modeling choices we did not anticipate when the
> analysis was prespecified. We report this as a genuine limitation of
> prespecified single-model inference in a finite-shot setting with
> structural heteroscedasticity, not as a reason to discard the
> confirmatory framework itself.

## What is deliberately NOT proposed

- No proposal to change the confirmatory Wald/Holm decision itself (H2
  remains rejected under the preregistered analysis).
- No proposal to delete or reframe the existing bootstrap
  non-corroboration text — the new material supplements it.
- No claim that the replication "confirms" H2 — the predefined decision
  rule classified it as "direction replicated but magnitude uncertain,"
  and that exact language is used throughout, not a stronger word.
