# Few-Qubit QNN Barren-Plateau Mitigation: Gradient SNR Study

Tests whether three barren-plateau mitigation strategies for a few-qubit QNN --
(A) constrained ("brick-layer") entanglement, (B) a local cost function, and
(C) classically-parameterized residual/shortcut connections -- combine
additively or not, using gradient signal-to-noise ratio (SNR) as the outcome
metric.

The project has two phases. The **pilot** (4 qubits, one TFIM Hamiltonian,
`L=3`, 50 seeds) established the core methodology and headline findings. The
**companion-paper phase 2** generalizes the same machinery to a qubit-count
sweep (n=2..10), two additional Hamiltonians/tasks, and a residual-connection
scaling sensitivity check, to test whether the pilot's findings hold beyond
its single (n=4, TFIM) reference point. Both phases' raw results and plots
are kept, clearly labeled, in `results/`.

## How to run

```bash
pip install -r requirements.txt
python main.py
```

This runs the full pipeline end to end, both phases: pilot (Hamiltonian
sanity check -> 7 configs x 50 seeds at L=3 -> H3 depth sweep -> hypothesis
tests -> plots) followed by companion phase 2 (Hamiltonian + brick-pattern
regression checks across the full task x n_qubits sweep -> main grid ->
headline reference re-run -> sum-vs-mean sensitivity check -> scoped H3 depth
sweep -> hypothesis tests -> plots) -> a single `RESULTS.md` with both
phases' sections. **Pilot wall time: ~109s.** **Companion-phase wall time:
~91 min** (measured: 5463.8s, see `results/runtime_phase2.json`) on the
machine this was developed on (see "Seed-count reduction" in RESULTS.md's
companion-phase section for why the main grid and sensitivity check use a
reduced seed count to fit within the ~1-2hr runtime budget the spec allows
for this phase). Both phases together run in one `python main.py`
invocation, so budget roughly 93 minutes for a full run.

Individual stages can also be run/imported separately. Pilot: `python
hamiltonian.py` (sanity check only), `python experiment.py` (raw data only,
writes to `results/`), `python analysis.py` (hypothesis tests from existing
raw data), `python plots.py` (plots from existing raw data). Companion phase
2: `experiment.run_companion_phase()`, `analysis.run_companion_phase_analyses()`,
`plots.generate_companion_phase_plots()` (each importable and independently
re-runnable against the CSV/JSON already in `results/`).

## Project layout

- `hamiltonian.py` -- TFIM Hamiltonian construction (explicit Kronecker
  products) + exact diagonalization sanity check; phase 2 adds
  `build_xxz_hamiltonian` (Task C) and a generic `sanity_check_hamiltonian`
  reused across every (task, n_qubits) grid point.
- `ansatze.py` -- baseline (HEA) and brick-layer entangling patterns, and the
  PennyLane `qml.Snapshot`/`qml.snapshots` plumbing that exposes mid-circuit
  statevectors for residual connections. Phase 2 generalizes the brick-layer
  pattern to arbitrary `n_qubits` (`brick_pattern_matches_pilot_n4` is the
  regression check that it still reduces to the pilot's n=4 pattern).
- `cost_functions.py` -- global (`<H>`) and local (`<Z0Z1>`) cost/variance
  formulas, and the residual-connection cost/variance combinators. Phase 2
  adds the `reduction="sum"|"mean"` toggle to the residual combinators.
- `snr.py` -- the two-branch gradient/SNR estimator: parameter-shift for
  gate angles `theta_i`, direct analytic gradient for residual weights
  `alpha_l`. Phase 2 adds the tolerance-based deterministic-parameter rule
  (`_DETERMINISTIC_VAR_TOL`) and threads `residual_reduction` through both
  branches.
- `experiment.py` -- defines the 7 ablation configs and the H3 depth-sweep
  configs, runs them, saves raw CSV/JSON to `results/` (pilot, unchanged).
  Phase 2 adds the `TASKS` registry, the n_qubits x task main grid
  (`run_main_grid`), the headline reference re-run, the sum-vs-mean
  sensitivity check (`run_sensitivity_check`), and the scoped depth sweep
  (`run_depth_sweep_scoped`), orchestrated by `run_companion_phase`.
- `analysis.py` -- Wilcoxon signed-rank hypothesis tests (H1/H2a/H2b/H3) and
  summary statistics (pilot, unchanged). Phase 2 adds `run_grid_analysis`,
  `run_sensitivity_analysis`, and `run_scoped_h3_analysis`, all reusing
  `analyze_h1`/`h2a`/`h2b`/`h3` unchanged, one grid cell at a time.
- `plots.py` -- SNR-by-configuration box/bar plots and the SNR-vs-depth plot
  (pilot, unchanged). Phase 2 adds the hypothesis-outcome heatmap grid, the
  sum-vs-mean sensitivity comparison plot, and the n-faceted depth-sweep plot.
- `main.py` -- orchestrates all of the above (both phases) and writes
  `RESULTS.md` (pilot section, then companion-phase-2 sections appended).

Raw output lives in `results/` (CSV/JSON, git-tracked) and
`results/plots/` (PNGs); the human-readable summary is `RESULTS.md` at the
repo root.

## Design choices

The spec asked that genuinely underspecified points be resolved with a
documented, reasonable choice rather than a silent guess. Here's every place
that applied:

**Residual connections, operationalized at the cost function, not the gate
parameters.** Per the spec's explicit steer, rotation angles stay static,
classically-optimized parameters -- there is no mid-circuit feedback or
measurement-based adaptivity anywhere in this project. Concretely:
`C_res = C_quantum + Sum_l alpha_l * Sum_j <Z_j>_in^(l)`, where
`<Z_j>_in^(l)` is read off the *intermediate statevector* just before block
`l`'s gates, within the same circuit evaluation (via PennyLane's
`qml.Snapshot()` + `qml.snapshots()`, which return every marked intermediate
statevector from one `qml.state()`-based execution). Block 1's "input" is
simply the initial `|0000>` state, since there's nothing upstream of it.

**Theta-gradient vs. alpha-gradient are two genuinely different code paths.**
`d C_res / d theta_i` uses the exact parameter-shift rule on the *full*
`C_res` (not just `C_quantum`) at the shifted circuits, because the residual
sum depends on `theta_i` whenever block `l > `(theta_i's layer) -- an
earlier layer's rotation angles do influence a later block's input state.
`d C_res / d alpha_l = Sum_j <Z_j>_in^(l)` is exact and linear, read off a
*single* unshifted evaluation; `alpha_l` is never shifted by pi/2 (there's no
gate to shift). See `snr.py`'s module docstring and `_theta_gradient_snr` /
`_alpha_gradient_snr`.

**Shot-noise variance under residual connections assumes independent
measurement channels.** Per the spec's explicit simplifying assumption (and
the follow-up clarification appended to the prompt), the final-cost
measurement and every intermediate single-qubit `Z_j` measurement are treated
as statistically independent, giving
`Var(single-shot) = Var_quantum + Sum_l alpha_l^2 * Sum_j (1 - <Z_j>_in^(l)^2)`.
This ignores any real covariance between the final observable and the
intermediate one-qubit observables (and between qubits within a block) that a
literal shared-shot hardware realization would have. Implemented in
`cost_functions.residual_single_shot_var`.

**`alpha_l` initialization range.** The spec states initializations are drawn
"uniform over `[0, 2*pi)`" for "trainable parameters" generally, and
separately says `alpha_l` counts as a trainable parameter. There's no explicit
statement of `alpha_l`'s range (a classical weight has no natural `2*pi`
periodicity the way a rotation angle does), so `alpha_l` is initialized the
same `U[0, 2*pi)` for consistency and simplicity. See `snr.init_params`.
A more "natural" choice (e.g. `U[-1, 1]`) would rescale `alpha_l`'s SNR
contributions but not the qualitative comparisons between configurations,
since every config with residual connections uses the same draw.

**Seed pairing across configurations with/without `alpha`.** `theta` is
always drawn first from a seed's RNG stream, and `alpha` (when applicable) is
drawn immediately after, from the *same* stream. This guarantees `theta` is
bit-identical for a given seed across every configuration, whether or not
that configuration also draws `alpha` afterward -- required for the paired
(not independent-sample) Wilcoxon design the spec calls for.

**Brick-layer pattern.** Defined exactly as the spec's example: odd layers
(1-indexed) apply `CNOT(0,1)` and `CNOT(2,3)`; even layers apply `CNOT(1,2)`.
Fixed for `n_qubits=4` (the only qubit count this project uses).

**H3 depth-sweep "combination" config.** The spec asks to repeat configs 3
(local cost only) and 4 (residual only) "and their combination" across
`L in {1,2,3,5,8}`. Since H3 is specifically about isolating B (local cost)
and C (residual) from A (entanglement), the sweep's three configs all use the
baseline (full-chain) entangling pattern -- brick-layer entanglement is not
part of the depth sweep.

**Statevector simulator: PennyLane's `default.qubit`, no custom engine.** We
verified PennyLane's wire-ordering convention empirically (wire 0 = most
significant bit, matching `np.kron(op_wire0, op_wire1, ...)`) so that
Hamiltonian/observable matrices built directly in numpy compose correctly
with statevectors read out of PennyLane. `qml.snapshots()` gives exact
mid-circuit statevector access without needing measurement-based tricks or a
hand-rolled simulator, so PennyLane was sufficient on its own -- there was no
need to fall back to a custom engine or to Qiskit. Autodiff is unused
throughout: every gradient in this project is either an exact analytic
parameter-shift evaluation or an exact closed-form linear derivative, per the
spec's design (statevector access replaces empirical shot resampling, and
parameter-shift replaces autodiff).

**H3 crossover detection uses the median, not the mean, across seeds.**
Seed-level mean SNR is heavy-tailed: a shallow, near-deterministic circuit
can push one parameter's shot-noise variance close to zero while its
gradient stays finite, producing a very large (but finite) SNR for that one
seed that dominates a 50-seed arithmetic mean. This is real, not a bug --
see `RESULTS.md`'s H3 section, where local-cost-only's *mean* SNR at L=1 is
168.6 versus its *median* of 8.6. The Wilcoxon signed-rank test itself is
rank-based and unaffected by this, but the auxiliary "which config wins"
flag used to locate the H3 crossover uses the median (matching the log-scale,
median+IQR depth plot) rather than the outlier-sensitive mean. Both are
reported in `RESULTS.md` for transparency.

**SNR at zero shot-noise variance.** A parameter whose shot-noise variance
rounds to exactly zero (a real, physically-meaningful case -- e.g. a
parameter that provably cannot affect a Pauli-valued local cost, per the
no-signaling theorem, which shows up for late-layer rotations on qubits
outside the local cost's support) is assigned `SNR = inf` if its gradient is
nonzero, or `NaN` if both are zero (a fully flat direction). These are
excluded from the "finite" mean/median reported per seed
(`experiment._summarize`), and are visible in the raw per-parameter JSON for
anyone who wants to look at them directly.

## Design choices -- companion paper phase 2

**Brick-layer generalization.** The pilot's n=4 pattern (odd layers ->
`CNOT(0,1),CNOT(2,3)`; even layers -> `CNOT(1,2)`) is one instance of the
standard brick-wall construction: odd layers apply CNOT to disjoint pairs
`(0,1),(2,3),(4,5),...`, even layers to `(1,2),(3,4),(5,6),...`, with any
trailing unpaired qubit simply untouched that layer. Implemented as
`range(start, n_qubits-1, 2)` with `start=0`/`1` for odd/even layers
(`ansatze.entangling_pairs`); `ansatze.brick_pattern_matches_pilot_n4` is a
standing regression check (run at the start of `run_companion_phase`) that
this reduces exactly to the pilot's hardcoded n=4 pattern.

**Task selection, and why the local cost stays fixed across all three.**
Task A (TFIM, `J=1,h=0.5`) is the pilot's own task, unchanged. Task B (TFIM,
`J=1,h=2.0`) is the same model in the field-dominated regime. Task C (XXZ,
`Delta=0.5`) is a structurally different model -- U(1) symmetry (conserved
total Z-magnetization) instead of the TFIM's Z2 symmetry, and no external
field term. The local cost function is deliberately kept as `<Z0Z1>` for all
three tasks (only the global cost `<H>` changes, since global cost is always
`<H>` for whichever Hamiltonian is active): the point of sweeping the task is
to isolate the Hamiltonian as the varying factor, not to also vary the
cost-function lever at the same time, which would confound "the interaction
effects changed because the task changed" with "...because we also changed
what's measured."

**Deterministic-parameter rule -- formalizes and generalizes an exclusion the
pilot already relied on implicitly, verified against the real per-parameter
data rather than assumed.** The pilot's `snr_from_grad_var` treated
`var_shots <= 0.0` as the "assign inf/nan, exclude from aggregate" case.
`alpha_1`'s variance is exactly `0.0` by construction (block 1's input is
always the fixed `|0...0>`, so `<Z_j>=1.0` exactly, no floating-point path
involved) and was already being excluded cleanly by the pilot's own
`np.isfinite` filter. `snr.py` now uses a fixed tolerance,
`_DETERMINISTIC_VAR_TOL = 1e-12` (`VAR_TOL`), combined with a second
tolerance on the gradient itself, `_GRAD_TOL = 1e-12` (`GRAD_TOL`), to split
the `var_shots <= VAR_TOL` case into two: `deterministic_nonzero`
(`|grad| > GRAD_TOL` -- a real, resolvable direction with no measurement
noise, e.g. `alpha_1`) and `inactive_zero` (`|grad| <= GRAD_TOL` -- a
genuinely flat direction, e.g. a no-signaling zero-gradient `theta_i` outside
a local cost's support). Only `active` parameters (`var_shots > VAR_TOL`)
feed the aggregate mean/median; both `deterministic_nonzero` and
`inactive_zero` are excluded from it, but `deterministic_nonzero` additionally
counts toward the `operationally_resolvable_fraction` (real gradient signal,
just no shot noise to divide by) while `inactive_zero` does not (no signal at
all). Every parameter's classification, count, and identity are reported
explicitly (`experiment._summarize_grid`'s `n_deterministic_nonzero_params`/
`n_inactive_zero_params`/`*_labels`/`operationally_resolvable_fraction`
columns) instead of only implicitly falling out of an `isfinite` filter --
this also guards against roundoff landing a few orders of magnitude off exact
zero in geometries/tasks the pilot never tested.

**This is a distinct phenomenon from the pilot's separate L=1 mean/median
heavy-tailedness, confirmed by inspecting the actual companion-phase-2 raw
data, not assumed.** The pilot's noted ~20x L=1 gap (mean 168.6 vs median
8.6) was for `local_cost_only`, which has no `alpha` at all -- so it was
never the exact-zero-variance mechanism above. Re-running the scoped depth
sweep (n=4, L=1, 200 seeds) and inspecting the offending seed directly shows
the real cause: seed 38's random `theta_1` draw happens to put the circuit
extremely close to a `Z0Z1` eigenstate, giving a shot-noise variance of
`~1.38e-9` -- three orders of magnitude *above* the `1e-12` tolerance, so
correctly classified as non-deterministic, and correctly *not* excluded: it
is a genuine (if extreme) draw from a continuous distribution, not a
provably-exact-zero case, and there is no principled tolerance that would
exclude it without also excluding legitimately large-but-finite SNR values
from other seeds. Excluding it would be an arbitrary, unprincipled cutoff,
not a fix. `residual_only`'s alpha-driven gap is (and, per the pilot's own
`np.isfinite` filter, already was) cleanly resolved by exclusion; the
separate local-cost heavy tail is not something this rule fixes or should
fix -- the median remains the correct, already-documented robust summary
statistic for it (see "H3 crossover detection uses the median" above and
`RESULTS.md`'s companion-phase H3 section). The pilot's own
`_summarize`/`run_main_experiment`/`run_depth_sweep` are untouched, so the
pilot's committed result files stay byte-for-byte reproducible.

**`residual_reduction`: mean (primary) vs. sum (secondary sensitivity
check).** The residual term
`C_res = C_quantum + Sum_l alpha_l * reduce(<Z_j>_in^(l))` has a magnitude
that scales with `n_qubits` under `"sum"` (the pilot's only option) -- a
genuine confound once n is swept from 2 to 10, since it could produce
spurious n-dependence unrelated to the mitigation strategies themselves.
`cost_functions.residual_addition`/`residual_single_shot_var` support
`reduction="mean"|"sum"` (`"mean"` divides each block's sum, and its
independent-channel variance contribution, by `n_qubits`/`n_qubits^2`).
Per the residual-parameter correction, `"mean"` (n-invariant) is now the
*primary* reduction used throughout the main n x task grid, the headline
reference, and the scoped depth sweep; `"sum"` is retained only as a
secondary sensitivity check, at n_qubits=4, depth=`L_MAIN`, measurement
budget=`N_SHOTS` (narrower than the original `{4,10}` x 3-task range, since
`"mean"` no longer needs cross-n validation as the default). The sensitivity
check is self-contained (both reductions computed at the same seeds, not
reusing a possibly different-seed-count grid subset) so the comparison stays
properly paired.

**Parameter/estimator taxonomy: `circuit_theta` vs. `residual_alpha`, each
with its own dedicated, explicitly-labeled gradient and variance path.**
This codebase has exactly two parameter families and no others -- there is
no tomography or mixed-state-fidelity estimator anywhere in it, since both
quantum costs (`<H>` and `<Z0Z1>`) are evaluated exactly from a noiseless
statevector, not estimated via measurement tomography. Every parameter-level
record now carries explicit `parameter_type`, `gradient_method`,
`variance_method`, `variance_method_family`, `estimator_family`,
`number_of_shift_evaluations`, `number_of_tomography_settings`, and
`number_of_measurement_settings` fields (`snr._parameter_metadata`), rather
than only being distinguishable by a `theta_`/`alpha_` label prefix:
`circuit_theta` parameters get `gradient_method="parameter_shift"`,
`variance_method` distinguishing the global-Hamiltonian vs. local-Pauli-
Bernoulli analytic variance formula, `number_of_shift_evaluations=2`, zero
tomography settings; `residual_alpha` parameters get
`gradient_method="residual_alpha_exact_linear"`,
`variance_method="residual_alpha_analytic_independent_z"`, zero shift
evaluations, zero tomography settings, and `number_of_measurement_settings
=n_qubits` (one independent per-qubit `Z` estimator per block).
`experiment.assert_no_residual_alpha_misrouting` is a standing check, run on
every seed/config during data generation, that no `alpha_l` is ever tagged
with the parameter-shift method (or vice versa) -- a routing bug fails loudly
at generation time rather than silently mislabeling a row.

**Data volume: full per-parameter JSON only for reference points.** The main
grid is 3 tasks x 9 n-values x 7 configs x 50 seeds = ~9,450 seed-configs;
dumping full per-parameter grad/SNR arrays for all of them would add tens of
MB of git-tracked JSON for marginal value, since the grid's hypothesis tests
only need the seed-level `mean_snr` already in the summary row. The main
grid and sensitivity check therefore write summary CSVs only (with the
deterministic-parameter diagnostic columns); full per-parameter JSON is kept
for the scoped depth sweep (much smaller, same order of magnitude as the
pilot's own per-parameter file) and the pilot's own untouched files serve as
the single-grid-point reference case.

**Seed-count reduction for runtime.** See "Seed-count reduction (runtime
budget)" in `RESULTS.md`'s companion-phase section for the specific numbers:
a calibration run showed the spec's suggested 200 seeds everywhere would put
total phase-2 runtime at ~2.7 hours, over the stated 1-2 hour budget. The
main grid and sensitivity check use 50 seeds (matching the pilot's own count)
instead; the scoped depth sweep keeps the full 200; the single grid point
most comparable to the pilot (n_qubits=4, task=tfim_h0.5) is additionally
re-run at 200 seeds as the headline reference result.

## Assumptions carried over directly from the spec (not independent choices)

- 4 qubits, `J=1`, `h=0.5`, open-boundary TFIM, `L=3` for the main experiment.
- `N=1000` shots per circuit evaluation; shot-noise variance is derived
  analytically from a single noiseless statevector pass per shifted circuit,
  never resampled empirically.
- 50 seeds, `theta ~ U[0, 2*pi)`, identical seeds across all 7 configurations
  (paired design).
- Wilcoxon signed-rank test (not Mann-Whitney U) for every paired
  configuration comparison.
- Companion phase 2: n_qubits in {2,...,10}; three tasks (TFIM h=0.5, TFIM
  h=2.0, XXZ Delta=0.5); local cost fixed at `<Z0Z1>` across all tasks;
  scoped H3 depth sweep at n_qubits in {4,6,10}, reference task only; no
  hardware noise modeling and no qubit counts beyond n=10 (both explicit
  non-goals).

## Validation performed

- `hamiltonian.py::sanity_check` verifies the Hamiltonian is Hermitian, that
  `Z0Z1` squares to the identity (a valid +-1 Pauli observable), and reports
  the exact ground energy from `numpy.linalg.eigh` (`-3.427034` for
  `J=1, h=0.5`) alongside the spectral gap and `<ground|Z0Z1|ground>`. This
  runs automatically at the start of every `main.py` invocation and its
  output is saved to `results/hamiltonian_check.json`.
- The PennyLane wire-ordering convention (wire 0 = MSB) was independently
  verified against a hand-built `numpy.kron` circuit before being relied on
  anywhere in `hamiltonian.py`'s Hamiltonian/observable construction.
- Zero-gradient parameters observed under the local cost function were
  cross-checked against the no-signaling theorem (a local unitary on a
  disjoint subsystem cannot change a local observable's expectation value on
  another subsystem) rather than assumed to be a bug.
