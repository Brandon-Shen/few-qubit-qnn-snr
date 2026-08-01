# Results and Discussion — QNN-SNR Confirmatory Run

> **SUPERSEDED — historical draft, narrates pre-fix pooled-mode numbers.**
> This document predates the mode-pooling bug fix (`verification/mode_pooling_guard.md`)
> and the manuscript itself. Its H2-H4 coefficients and discussion reflect the
> pooled-mode fit now archived under `results/superseded_pooled/`, not the
> adopted end-to-end-only record in `results/production_confirmatory/`. For
> the current, citable results and discussion, see `paper/main.tex` (the
> manuscript) and `verification/confirmatory_numbers_adopted.md`. Kept here
> unedited for its process/provenance narrative, not for its numbers.

Run: `configs/confirmatory.yaml`, `config_hash=bb1fe393a979c8d2`, git commit `cbbeafa8`.
Generated from `results/` (this run); the prior `results/` contents — a `configs/smoke.yaml`
run explicitly marked "not statistically meaningful — do not use for any reported result" —
were moved to `results_smoke_20260727/` before this run started and are not used below.

## 0. Scope and integrity notes (read this section first)

**No `preregistration.md` or `report.md` file exists in this repository.** The preregistered
design lives in the external review paper (the numbered Sections cited throughout
`ASSUMPTIONS.md` and this codebase); it is not a file this analysis can diff against
directly. What follows compares the *executed run* against the design as encoded in
`configs/confirmatory.yaml`, `ASSUMPTIONS.md`, and the codebase's own stated methodology
(`results/statistical_methods.md`), which is the best available proxy for "the
preregistration" inside this repo.

**Two real deviations from the preregistered/documented design, both forced by wall-clock
infeasibility, not by choice of convenience:**

1. **The replicate count `R=30` was never validated by the pilot calibration procedure.**
   Running `pilot-replicates` against the confirmatory config's own representative cells
   (Section 17.A) showed the calibration search hit its configured ceiling (`max_R=200`)
   *without converging* for 4 of 8 representative cells — all four at nominal depth=1
   (`results/pilot_replicate_selection.json`). The four depth=6 cells did converge, but at
   R=40–70, still above the committed R=30. `configs/confirmatory.yaml`'s own header
   comment says replicate/initialization counts there are "pilot-utility minimums" to be
   updated before a real run; that update was never done. This is a genuine calibration
   gap, not a cosmetic one — see §1 below for its visible fingerprint in the data.

2. **The preregistered 2000-iteration nested bootstrap (Section 14) was not run.** A timing
   probe (2 iterations, full confirmatory-scale data) measured ~13.5s/iteration for the H1
   bootstrap and ~474s/iteration (≈7.9 min) for the H2–H4 bootstrap — the latter recomputes
   pointwise statistics from scratch on a full resample of the 6.17M-row shot dataset every
   iteration, not a cheap model refit. Extrapolated to 2000 iterations: ~7.5 hours (H1) and
   **~11 days** (H2–H4), sequential — the codebase's own `ASSUMPTIONS.md` (A21) already
   flags this bootstrap as unparallelized and warns publication-scale runs should budget
   accordingly or shard across separate invocations, which the CLI does not currently
   support out of the box. Given the cost, the bootstrap was explicitly skipped rather than
   run at a silently reduced iteration count. **Consequence: `bootstrap_ci_lo`/`bootstrap_ci_hi`
   are `NaN` for every hypothesis in `confirmatory_hypotheses.csv`, and Figure
   `01_forest_plot_H1_H4.png`'s x-axis label ("bootstrap 95% CI") does not correspond to an
   actual interval in this run — it shows point estimates only, no error bars.** Every H1–H4
   conclusion below rests solely on the Wald-normal SE/p-value engine (Section 13,
   `ASSUMPTIONS.md` A9); there is no percentile-bootstrap cross-check of direction or width
   for any coefficient in this run.

Everything else in the design was run as committed and at full stated scope: all 8
configurations, the full depth sweep `[1,2,3,4,6]`, the full budget sweep
`[250,500,1000,2000]`, 50 matched initializations, 30 replicates per finite-shot cell,
6,169,600 validated rows (`data_validation_report.json`: `passed=true`, 0 errors). The
initialization-count calibration (`pilot-initializations`, Section 17.B) *did* run
successfully against the real generated data and converged cleanly on its first candidate,
`n=50`, matching the committed value exactly (`p90` half-widths 0.112 / 0.112 / 0.080, all
under the 0.20 target) — that part of the design is legitimately calibrated, unlike R.

---

## Results

### Calibration sanity

- **R (replicates): not converged.** See §0.1. The practical fingerprint: the rate of
  finite-shot pointwise cells with *exactly zero* replicate variance (excluded from the
  SNR model per Section 9's no-epsilon policy) is 4.3% at depth=1/budget=250, dropping
  monotonically to 1.3% at depth=1/budget=2000, versus 0.4–1.5% at every deeper depth
  (`pointwise_gradient_statistics.parquet`, 204,800 cells total, 1,833 flagged overall).
  This is exactly the population the R calibration flagged as under-sampled. It does not
  invalidate the fit (zero-variance cells are excluded, not imputed), but it does mean
  depth=1 estimates rest on a thinner, noisier effective sample than deeper-depth estimates.
- **N_init (initializations): converged cleanly**, first candidate, as noted above.
- **Bootstrap: not run** (§0.2) — this is a scope decision, not a non-convergence; don't
  read "no bootstrap CI" as "bootstrap failed."

### H1 — exact-signal E×L interaction (`eta_EL`)

Estimate **+0.004346** (SE 0.001529, Wald z=2.84), p_unadjusted=0.00448,
**p_holm=0.01345 → rejected** at family-wise α=0.05.

The interaction is **super-additive** (positive sign): Figure
`05_exact_gradient_EL_interaction.png` shows the L=1 line's E=0→E=1 rise (0.0423→0.0487)
is steeper than the L=0 line's (0.0231→0.0254), on the `asinh(|exact_gradient|)` scale.

**This is the opposite sign from the paper's one prespecified interpretive expectation** —
the mechanistic argument from the exact local-cost gradient identity motivated expecting
*sub-additivity* (`eta_EL<0`) for E×L specifically, at the exact-signal level. The data
reject the null in the *other* direction. This should not be read as the mechanism being
wrong in some general sense — the identity is exact and the codebase's own gradient
implementation is tested against finite-difference checks (`ASSUMPTIONS.md` A15b) — but
the sign result itself does not match the paper's hedge, and that mismatch is worth
surfacing to the paper's authors rather than reframed to fit. No bootstrap CI exists to
corroborate the direction (§0.2); the Wald CI (estimate ± ~1.96×SE ≈ [0.0013, 0.0073])
excludes zero but is the only interval available.

### H2 — estimator-SNR E×L interaction (`beta_EL`)

Estimate **+0.023732** (SE 0.005650, z=4.20), p_unadjusted=2.67e-5,
**p_holm=1.07e-4 → rejected**.

Same sign as H1 (super-additive, positive). **This is the more interesting comparison the
design was built to make**: the exact-signal interaction (H1) and the estimator-SNR
interaction (H2) agree in both sign and significance. Finite-shot sampling noise, at the
committed replicate count, neither erases nor inverts the E×L super-additivity present in
the noise-free gradient signal — it survives through to the operationally relevant SNR_est
outcome. That said, Figure `02_snr_interaction_EL.png` shows the raw SNR_est error bars
(±1 SD across matched cells) are enormous relative to the mean shift (means ~0.7→0.8 for
L=0, ~1.13→1.24 for L=1, against SDs exceeding 1.5–2 in the raw cell distribution) — the
interaction is real and resolvable given N=204,800 cells and the mixed model's variance
structure, but it is not visually dramatic in raw SNR units; don't over-read the effect
size from the p-value alone.

No directional prior existed for `beta_EL` itself (only for `eta_EL`); the fact that both
land the same direction is a data outcome, not confirmation of a prespecified beta_EL
hypothesis.

### H3 — estimator-SNR E×R interaction (`beta_ER`)

Estimate +0.003528 (SE 0.005675, z=0.62), p_unadjusted=0.534, **p_holm=1 → not rejected**.

No directional prior existed for this pair. Figure `03_snr_interaction_ER.png` shows
essentially overlapping R=0/R=1 lines across E. **Failing to reject H0 here is not evidence
of additivity, equivalence, or that E and R have identical effects on SNR_est** — no
equivalence/TOST test was prespecified anywhere in this codebase's statistical methods
(confirmed against `statistical_methods.md` and `ASSUMPTIONS.md`; no such test is
implemented), so this result simply means the data don't resolve an E×R interaction at
this sample size and effect scale, nothing stronger.

### H4 — estimator-SNR L×R×depth interaction (`beta_LRd`)

Estimate +0.000511 (SE 0.004162, z=0.12), p_unadjusted=0.902, **p_holm=1 → not rejected**.

No directional prior existed. Figure `04_LR_interaction_depth.png` makes the *shape* of
this null visible across the full depth sweep, not just as a pooled coefficient: the
L=1,R=0 and L=1,R=1 curves track each other almost exactly at every one of the five depth
levels (1,2,3,4,6), and separately the L=0,R=0 and L=0,R=1 curves track each other almost
exactly at every depth. In other words, SNR_est in this design is overwhelmingly separated
by **L alone** (a large main effect, visually — L=1 configs sit roughly 2–3× the L=0
configs' SNR at every depth), and R does not visibly perturb that separation at any single
depth, not merely on average. As with H3, this is a failure to reject, not evidence of
equivalence — no equivalence tolerance was prespecified.

### Secondary: interaction indices (descriptive, not confirmatory)

From `interaction_indices.csv` (RMS-SNR-based `I_AB`):

| Pair | I_AB | Reading |
|---|---|---|
| E×L | 1.072 | super-additive fold-change |
| E×R | 1.034 | super-additive fold-change |
| L×R | 0.997 | ≈1, no fold-change interaction |

E×L's descriptive index agrees directionally with the H1/H2 regression results
(super-additive). L×R's index (≈1) agrees with H4's null. **E×R's index (1.034,
nominally super-additive) does not contradict H3's null result** — a raw fold-change
computed on RMS SNR is not adjusted for the mixed model's random-effects structure
(matched initialization/parameter variance), so a non-unity descriptive index next to a
null regression coefficient is expected, not a contradiction; the regression result is the
one that should be trusted for a confirmatory claim, and it is what's reported above.

### Exploratory findings (not part of the H1–H4 Holm family — cannot support or refute H1–H4)

**Three-way E:L:R interaction** (from the H2–H4 model, `exploratory_results.csv`): estimate
−0.0111, SE 0.00799 (rough z≈−1.39, not a preregistered or Holm-corrected test — reported
for completeness only). Negative sign, opposite of the E×L pairwise result, suggestive of a
diminishing return when all three interventions combine, but this is exploratory and
underpowered relative to a real confirmatory test of a 3-way term.

**Performance Q1 — does configuration 8 (all three interventions) beat the best single
intervention on SNR_est?** The best single-intervention configuration is **configuration 3
(local cost alone, E=0,R=0) in every one of the 20 (depth,budget) cells tested** — L is
clearly the dominant single lever for SNR_est in this design, consistent with the H4
figure's visual pattern above. Configuration 8 exceeds configuration 3's RMS SNR_est in
only **9/20 cells (45%)**, concentrated at depth 3–4 and inconsistent at depth 1–2 and 6.
Circuit-cost-normalized SNR tracks this same 9/20 split almost exactly (both metrics are
scaled by the same per-cell shot budget). **Bundling all three interventions together does
not reliably outperform local cost alone on this metric in this design.**

**Performance Q2 — does an SNR advantage survive final energy/global fidelity?** This
question needs a strong caveat before it's read as a performance claim: **this codebase
never trains parameters for the confirmatory design** (`ASSUMPTIONS.md` A7 — the
confirmatory measurement point is immediately after initialization, before any optimizer
update). "`final_tfim_energy`" and "`global_fidelity`" in every table here are therefore
properties of the **single matched random-initial state** for a given (configuration,
depth) — verified constant across all four shot budgets within a config/depth cell in
`configuration_summaries.csv` — not the result of any optimization run. Values range
roughly −0.23 to +0.36 in energy and 0.03–0.10 in fidelity, both far from the TFIM ground
state, exactly as expected for an untrained random circuit. Reading
`config8_energy_improves_on_baseline` (mixed True/False across depths) as "configuration 8
trains to a better final state" would be a direct overclaim; the correct reading is "the
architectural differences between configurations shift where their untrained initial state
sits in the energy/fidelity landscape, inconsistently across depth." No claim about
trainability or convergence quality can be drawn from these two columns in this dataset.

**Longitudinal/checkpoint trajectories**: not generated in this run. The pipeline commands
executed (`generate-exact`, `generate-shots`, `aggregate`, `fit`, `report`) only ever
produce the single-point confirmatory dataset described in A7; no separate `checkpoint_id`
post-training dataset (Section 2/16) was generated, so there is nothing to report here.
This is a gap relative to the paper's full described scope, not a result of "not
statistically meaningful."

### Diagnostics that qualify the whole experiment

**Restricted-entanglement label — validated.** `E=1` configurations show substantially
lower mean bipartite von Neumann entropy and higher mean reduced-state purity than their
`E=0` counterparts at **every** tested depth (Figure `12_entanglement_by_depth.png`):
entropy ≈0.32–0.42 (E=1) vs ≈0.75–0.82 (E=0); purity ≈0.83–0.87 (E=1) vs ≈0.64–0.67 (E=0).
The separation is clean and consistent across the full depth sweep, so "restricted
entanglement" is an empirically justified label for this implementation, not just a name.
No area-/volume-law scaling claim is made from this (correctly — the figure's own title
says so), consistent with the paper's Section 4 restriction for a 4-qubit system.

**"Convergence" is not the right frame for energy/fidelity here** — see Performance Q2
above; there is no optimization step to have converged or failed. What can be checked
instead is *consistency*: energy/fidelity are identical across shot budgets within a
(config, depth) cell as they should be (deterministic given the matched initial state),
which they are.

**Bias and sign agreement** (Figure `07_bias_sign_agreement.png`, own terms only — not used
to qualify SNR_est or vice versa): the bias distribution (`mu_hat - exact_gradient`) is
tightly centered at zero across all 204,800 pointwise cells; sign agreement between the
finite-shot mean and the exact gradient ranges 0.79–0.89 by configuration — reasonably high
but meaningfully below 1, i.e. roughly 1 in 8–5 cells the finite-shot estimator's sign
doesn't even match the exact gradient's sign at the committed replicate count. This is a
property of the estimator's fidelity, separate from whether SNR_est is usable, and is
worth reading alongside the R-calibration shortfall in §1 rather than in isolation.

---

## Discussion

**What this run supports.** Within the tested design — a 4-qubit open-boundary TFIM
ground-state task, this specific Ry+CNOT hybrid ansatz with self-contained per-block
circuits (`ASSUMPTIONS.md` A15b), and these specific implementations of restricted
entanglement, local cost, and residual connections — the data give two confirmatory,
Holm-corrected results (H1, H2) and two non-results (H3, H4). The E×L interaction is
super-additive and this super-additivity is visible at *both* the exact-gradient-signal
level and the finite-shot estimator-SNR level, which is the strongest single finding here:
whatever mechanism produces the E×L super-additivity in the noiseless gradient, it isn't
being washed out by finite-shot sampling noise at 30 replicates. Neither E×R nor the
L×R×depth term is resolvable as an interaction in this design and sample size, and L
dominates SNR_est as a main effect strongly enough that bundling all three interventions
(configuration 8) beats local-cost-alone only in a minority of tested cells.

**What it does not support.** The H1 sign result runs counter to the paper's one
prespecified interpretive expectation (sub-additive E×L on the exact-signal scale); this
run's data argue against that specific mechanistic hedge as stated, not for it — that
should be flagged to the paper's authors rather than smoothed over. Nothing here supports
or refutes any claim about asymptotic barren-plateau scaling class (exponential vs.
polynomial) — that was never the design's goal, consistent with the SNR-based framing this
codebase exists to implement. Nothing here supports a claim that configuration 8 "wins" in
general, or that any configuration trains better than another — no training was run in this
confirmatory design, and the energy/fidelity columns describe untrained initial states.

**Scope.** All of the above is scoped strictly to: 4 qubits (not the paper's full 2–10
qubit claimed range — only n=4 was actually run here), this open-boundary TFIM task at
J=1.0, h=0.5, this Ry+CNOT hybrid block ansatz under the self-contained-circuit reading of
depth (`ASSUMPTIONS.md` A15b — flagged by the codebase's own author as the single most
consequential implementation choice, worth confirming against the paper's actual intent
before treating any depth-dependent result, including H4, as final), and these specific
implementations of E (restricted CNOT schedule), L (global-infidelity vs. local-energy
cost), and R (fixed γ residual shortcut). No claim here generalizes to other qubit counts,
other ansätze, other tasks, or different implementations of the same three interventions.

**Not powered to answer, flagged for future work rather than treated as a conclusion:**

- Whether H1/H2's super-additivity direction (opposite the prespecified hedge) holds at
  other qubit counts or is specific to n=4 — this run cannot distinguish those.
- A real percentile-bootstrap cross-check of direction/width for any of H1–H4 (§0.2) — the
  Wald-normal p-values and CIs used throughout are the documented default (A9), not a
  validated substitute for the preregistered nested bootstrap.
- Whether R≥40–70 (the depth=6 calibrated range) or higher (the depth=1 range, which never
  converged even at the pilot's ceiling of 200) changes the H3/H4 null results — this run's
  zero-variance cell audit (§"Calibration sanity") suggests depth=1 estimates specifically
  are on thinner ground than deeper-depth estimates, and a properly calibrated R (especially
  for depth=1) is the single most direct next step before trusting this run's estimates as
  final.
- The longitudinal/checkpoint and cost-normalized-performance questions the paper's Section
  16 describes — no post-training data exists in this run to answer them (see Performance
  Q2 above).
