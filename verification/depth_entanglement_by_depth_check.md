# Depth-broken-out entanglement diagnostic check

Companion to `verification/depth_semantics_resolution.md` §7 (the entangling-schedule
tension). Purpose: a cheap, concrete **data lookup** — no re-simulation — checking
whether the confirmatory run's own entanglement diagnostics show a pattern consistent
with the self-contained/reset-per-block reading (flat across depth within a given
`E`) or with the paper's "requires multiple layers to propagate" language taken
literally (trending upward with depth within a given `E`).

## 0. Data source

**Update (Task G, follow-up pass): §2's original "sd" column below was not a real error
bar.** `results/configuration_summaries.csv` only stores the *mean* entropy/purity per
`(configuration_id, depth)` cell, already averaged over the 50 matched initializations
(not 8 as originally stated in this section — corrected below). The original §2 computed
"sd" as the standard deviation *across the 4 configs sharing a given `E`*, which is a
completely different (and much smaller) source of variation than init-to-init sampling
noise — it was identically 0.0000 at depth 1-2 (where `R`'s residual term is inactive, so
all 4 configs are bit-identical) and only reflected `R`'s small systematic depth>=3 effect
afterward. It said nothing about how noisy any single point estimate actually is. This is
fixed below using the real per-initialization values.

`results/configuration_summaries.csv`, columns `mean_entanglement_entropy` and
`mean_purity` — computed once per `(configuration_id, depth)` cell by
`qnn_snr.stats.descriptive.physics_summary_rows` on the confirmatory run's final
statevector (`entanglement_diagnostics`, `qnn_snr/circuits.py`), averaged over the 50
matched initializations (`cfg.design.n_initializations`, `configs/confirmatory.yaml`),
and identical across `budget` within a cell (deterministic given the matched initial
state). §1's table below (unchanged from the original pass) deduplicates on
`(configuration_id, depth)` and is still a straight re-grouping of existing output.

§§2-3 below are new: `physics_summary_rows(cfg)` was called directly
(`verification/entanglement_per_init_check.py`) to recompute the same deterministic
diagnostic *before* it gets averaged, recovering the per-initialization values (2,000
rows = 8 configs x 5 depths x 50 inits, 1.4s to compute). This reuses the same
`(theta_seed, classical_seed)` draws already baked into the confirmatory run's config —
it is not new science or a new random draw, just keeping data the pipeline already
discards after averaging.

## 1. Per-configuration, per-depth entropy and purity

| config_id | E | L | R | depth | mean entropy | mean purity |
|---|---|---|---|---|---|---|
| 1 | 0 | 0 | 0 | 1 | 0.8139 | 0.6438 |
| 3 | 0 | 1 | 0 | 1 | 0.8139 | 0.6438 |
| 4 | 0 | 0 | 1 | 1 | 0.8139 | 0.6438 |
| 7 | 0 | 1 | 1 | 1 | 0.8139 | 0.6438 |
| 1 | 0 | 0 | 0 | 2 | 0.8122 | 0.6438 |
| 3 | 0 | 1 | 0 | 2 | 0.8122 | 0.6438 |
| 4 | 0 | 0 | 1 | 2 | 0.8122 | 0.6438 |
| 7 | 0 | 1 | 1 | 2 | 0.8122 | 0.6438 |
| 1 | 0 | 0 | 0 | 3 | 0.7534 | 0.6749 |
| 3 | 0 | 1 | 0 | 3 | 0.7534 | 0.6749 |
| 4 | 0 | 0 | 1 | 3 | 0.7777 | 0.6629 |
| 7 | 0 | 1 | 1 | 3 | 0.7777 | 0.6629 |
| 1 | 0 | 0 | 0 | 4 | 0.8230 | 0.6377 |
| 3 | 0 | 1 | 0 | 4 | 0.8230 | 0.6377 |
| 4 | 0 | 0 | 1 | 4 | 0.8146 | 0.6419 |
| 7 | 0 | 1 | 1 | 4 | 0.8146 | 0.6419 |
| 1 | 0 | 0 | 0 | 6 | 0.7746 | 0.6665 |
| 3 | 0 | 1 | 0 | 6 | 0.7746 | 0.6665 |
| 4 | 0 | 0 | 1 | 6 | 0.7829 | 0.6644 |
| 7 | 0 | 1 | 1 | 6 | 0.7829 | 0.6644 |
| 2 | 1 | 0 | 0 | 1 | 0.3451 | 0.8681 |
| 5 | 1 | 1 | 0 | 1 | 0.3451 | 0.8681 |
| 6 | 1 | 0 | 1 | 1 | 0.3451 | 0.8681 |
| 8 | 1 | 1 | 1 | 1 | 0.3451 | 0.8681 |
| 2 | 1 | 0 | 0 | 2 | 0.4189 | 0.8328 |
| 5 | 1 | 1 | 0 | 2 | 0.4189 | 0.8328 |
| 6 | 1 | 0 | 1 | 2 | 0.4189 | 0.8328 |
| 8 | 1 | 1 | 1 | 2 | 0.4189 | 0.8328 |
| 2 | 1 | 0 | 0 | 3 | 0.3378 | 0.8724 |
| 5 | 1 | 1 | 0 | 3 | 0.3378 | 0.8724 |
| 6 | 1 | 0 | 1 | 3 | 0.3461 | 0.8655 |
| 8 | 1 | 1 | 1 | 3 | 0.3461 | 0.8655 |
| 2 | 1 | 0 | 0 | 4 | 0.3829 | 0.8500 |
| 5 | 1 | 1 | 0 | 4 | 0.3829 | 0.8500 |
| 6 | 1 | 0 | 1 | 4 | 0.3475 | 0.8608 |
| 8 | 1 | 1 | 1 | 4 | 0.3475 | 0.8608 |
| 2 | 1 | 0 | 0 | 6 | 0.3221 | 0.8719 |
| 5 | 1 | 1 | 0 | 6 | 0.3221 | 0.8719 |
| 6 | 1 | 0 | 1 | 6 | 0.3556 | 0.8600 |
| 8 | 1 | 1 | 1 | 6 | 0.3556 | 0.8600 |

(`L` never changes entropy/purity — expected, since `L` only selects the cost function
used to *train* against, and no training/optimization happens in this pipeline at all,
per `results_and_discussion.md`'s "convergence is not the right frame" note. `R`
starts to make a small difference only from `depth=3` on, matching the codebase's own
`gamma` residual term only activating when `R=1` and `ell+2 <= d`.)

## 2. Real per-initialization error bars (n=50, not n=4)

First: `L` was confirmed to have **exactly zero effect** on the entanglement diagnostic
(`max |entropy diff|` between the two `L`-duplicate configs at matched `E,R,depth,init` =
`0.000e+00`, every pair, every depth) — expected, since `L` only selects which cost
function the (nonexistent, in this pipeline) training would target, per §1's note. This
means the 4 configs sharing an `E` value are **not 4 independent draws** — they are at
most 2 genuinely distinct conditions (by `R`), each duplicated bit-for-bit by `L`. Pooling
all 4 as if they were 4 independent samples (as an earlier, less careful version of this
check might do) would be pseudo-replication. The table below instead uses one
representative config per `(E,R)` pair and reports the real sampling unit: 50 independent
initializations.

**Per (E, R, depth) — n=50 real inits, mean +/- SEM (SEM = sd/sqrt(50)):**

| E | R | depth | entropy mean | entropy sd | entropy SEM | purity mean | purity SEM |
|---|---|---|---|---|---|---|---|
| 0 | 0 | 1 | 0.8139 | 0.1768 | 0.0250 | 0.6438 | 0.0123 |
| 0 | 0 | 2 | 0.8122 | 0.2095 | 0.0296 | 0.6438 | 0.0140 |
| 0 | 0 | 3 | 0.7534 | 0.1782 | 0.0252 | 0.6749 | 0.0128 |
| 0 | 0 | 4 | 0.8230 | 0.1813 | 0.0256 | 0.6377 | 0.0126 |
| 0 | 0 | 6 | 0.7746 | 0.1854 | 0.0262 | 0.6665 | 0.0130 |
| 0 | 1 | 1 | 0.8139 | 0.1768 | 0.0250 | 0.6438 | 0.0123 |
| 0 | 1 | 2 | 0.8122 | 0.2095 | 0.0296 | 0.6438 | 0.0140 |
| 0 | 1 | 3 | 0.7777 | 0.1728 | 0.0244 | 0.6629 | 0.0121 |
| 0 | 1 | 4 | 0.8146 | 0.1480 | 0.0209 | 0.6419 | 0.0105 |
| 0 | 1 | 6 | 0.7829 | 0.1807 | 0.0256 | 0.6644 | 0.0128 |
| 1 | 0 | 1 | 0.3451 | 0.2393 | 0.0338 | 0.8681 | 0.0149 |
| 1 | 0 | 2 | 0.4189 | 0.2629 | 0.0372 | 0.8328 | 0.0165 |
| 1 | 0 | 3 | 0.3378 | 0.2290 | 0.0324 | 0.8724 | 0.0140 |
| 1 | 0 | 4 | 0.3829 | 0.2683 | 0.0379 | 0.8500 | 0.0169 |
| 1 | 0 | 6 | 0.3221 | 0.2384 | 0.0337 | 0.8719 | 0.0152 |
| 1 | 1 | 1 | 0.3451 | 0.2393 | 0.0338 | 0.8681 | 0.0149 |
| 1 | 1 | 2 | 0.4189 | 0.2629 | 0.0372 | 0.8328 | 0.0165 |
| 1 | 1 | 3 | 0.3461 | 0.2258 | 0.0319 | 0.8655 | 0.0142 |
| 1 | 1 | 4 | 0.3475 | 0.2506 | 0.0354 | 0.8608 | 0.0158 |
| 1 | 1 | 6 | 0.3556 | 0.2592 | 0.0367 | 0.8600 | 0.0161 |

**The real per-init sd (~0.15-0.27 for entropy) is an order of magnitude larger than the
old across-configs "sd"** (which topped out at 0.0205) — individual initializations
genuinely produce quite different entanglement values at fixed `(E, R, depth)`. The SEM
(~0.02-0.04) is the honest uncertainty on each point estimate in the mean table.

**Per (E, depth) marginal (n=100, pooling both `R` values)** — reported for continuity
with §1/the original pass, but note this pools two systematically-different-from-depth-3
conditions together, so `entropy_sem_within_R` (the average of the two `R`-specific SEMs
above) is the more honest per-point uncertainty than `entropy_sem_pooled` (which is
inflated by the real `R` systematic difference, not just noise):

| E | depth | entropy mean | entropy SEM (within-R) | entropy SEM (pooled, R-inflated) |
|---|---|---|---|---|
| 0 | 1 | 0.8139 | 0.0250 | 0.0176 |
| 0 | 2 | 0.8122 | 0.0296 | 0.0208 |
| 0 | 3 | 0.7656 | 0.0248 | 0.0175 |
| 0 | 4 | 0.8188 | 0.0233 | 0.0165 |
| 0 | 6 | 0.7787 | 0.0259 | 0.0182 |
| 1 | 1 | 0.3451 | 0.0338 | 0.0238 |
| 1 | 2 | 0.4189 | 0.0372 | 0.0262 |
| 1 | 3 | 0.3419 | 0.0322 | 0.0226 |
| 1 | 4 | 0.3652 | 0.0367 | 0.0259 |
| 1 | 6 | 0.3389 | 0.0352 | 0.0248 |

## 3. Formal regression: is there a depth trend, once real uncertainty is attached?

Fit per `E` value (`verification/entanglement_per_init_check.py`, statsmodels), on the
full 500-row per-init long dataset (50 inits x 5 depths x 2 `R` values, `L` collapsed out
per §2): `mean_entanglement_entropy ~ depth_z * R`, random intercept per
`initialization_id` (`depth_z` standardized the same way as everywhere else in this
codebase — `(depth - mean(design.depths)) / std(design.depths, ddof=0)`, `ASSUMPTION
A18`). Both models converged (confirmed via a second optimizer after an initial
convergence warning, and cross-checked against cluster-robust OLS by `initialization_id`,
which agrees to 4 decimal places on every coefficient):

| E | term | estimate | SE (mixed model) | p | SE (cluster-robust OLS, cross-check) | p (OLS) |
|---|---|---|---|---|---|---|
| 0 | `depth_z` | -0.0103 | 0.0108 | 0.338 | 0.0099 | 0.298 |
| 0 | `R` | 0.0048 | 0.0152 | 0.751 | — | — |
| 0 | `depth_z:R` | 0.0013 | 0.0152 | 0.930 | — | — |
| 1 | `depth_z` | -0.0141 | 0.0151 | 0.351 | 0.0140 | 0.314 |
| 1 | `R` | 0.0013 | 0.0214 | 0.952 | — | — |
| 1 | `depth_z:R` | 0.0074 | 0.0214 | 0.728 | — | — |

**No depth trend is statistically distinguishable from zero for either `E` value.** The
`depth_z` slope is small in both absolute terms (roughly -0.01 to -0.014 entropy units per
standardized depth unit, against a `depth_z` range of about -1.5 to +1.9 across the actual
sweep) and small relative to its own uncertainty (p=0.30-0.35 by two different estimation
methods that agree closely) — not remotely close to a conventional significance threshold.
`R` and its interaction with `depth_z` are also not distinguishable from zero once real
per-init noise is accounted for, despite the small systematic-looking shift visible in
§2's raw means from depth 3 onward.

**Reassessed conclusion: "flat, not trending" holds up, now on solid footing rather than
a five-point eyeball impression.** The original pass's qualitative read was correct, but
its supporting "evidence" (near-zero across-config sd) was not actually testing the right
thing. With the real per-init sampling distribution in hand, the honest statement is
stronger, not weaker: the between-depth differences in the mean (~0.05-0.09 range for
entropy) are well within one to two real per-init SEMs of each other, and a formal
regression confirms no depth-`E` interaction that the codebase's own `E:L:depth_z`-style
sensitivity methodology (Task A) would flag as real. This is consistent with the
self-contained/reset-per-block reading (`depth_semantics_resolution.md` §4, §7): no
mechanism exists for entanglement to accumulate across blocks, and the data do not show
any such accumulation once properly quantified.

## 4. Practical takeaway

(Updated after Task G's regression above; conclusions unchanged, now on firmer footing.)

- **No re-simulation or code change is implied.** The confirmatory H1-H4 results and
  the Task 1 finite-difference gradient verification are unaffected by anything in
  this check or in `depth_semantics_resolution.md` §7 — Eq. 7's gradient formula does
  not reference entangling-layer propagation, and its correctness (verified to <1e-6
  relative error against finite differences) is what actually establishes the
  self-contained implementation is right for computing gradients, independent of how
  the entangling-schedule prose in Section 5.2.2 should be read.
- **What this does change**: the *mechanistic narrative* the companion paper's
  discussion section should use when explaining why `E` interacts with depth (or
  doesn't — H4's `L:R:depth_z` term is a null result). It would be incorrect for that
  discussion to lean on "restricted entanglement takes multiple layers to propagate
  across the register" as a mechanism in *this* implementation, because the depth
  sweep here does not let entanglement propagate across blocks at all — each block's
  entanglement diagnostic is close to a fresh draw, not an accumulating one. The
  correct framing is closer to "restricted entanglement lowers the entanglement
  produced by any single block's entangling layer, and this reduction is stable
  across the depth sweep" — an `E` main effect, not an `E`-times-depth accumulation
  effect.
- **Actionable note for the paper's authors** (not a vague caveat — quote the exact
  tension): the paper's Section 5.2.2 describes the restricted schedule as one where
  "circuit-wide propagation requires multiple layers rather than occurring within one
  layer," but Sections 5-6's own block formalism (the `z^(ℓ) = q_ℓ(x^(ℓ), θ^(ℓ))`
  notation and the Section 6 gradient formula that only holds under a self-contained
  per-block reading) has each block start from a reset state, so there is no
  continuously evolving register for correlations to propagate across between blocks.
  These two parts of the paper describe mutually incompatible circuit pictures, and
  reconciling them (e.g., clarifying whether "layer" in 5.2.2 means something
  different from "block" elsewhere, or whether the entangling-schedule language was
  written before the residual/self-contained-block design was finalized) is something
  only the authors can resolve — this codebase's implementation follows the
  mathematically load-bearing half (the gradient formula) and documents the
  discrepancy here rather than guessing which passage is authoritative.
