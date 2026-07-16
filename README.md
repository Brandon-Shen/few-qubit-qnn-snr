# Few-Qubit QNN Barren-Plateau Mitigation: Gradient SNR Study

Tests whether three barren-plateau mitigation strategies for a 4-qubit QNN --
(A) constrained ("brick-layer") entanglement, (B) a local cost function, and
(C) classically-parameterized residual/shortcut connections -- combine
additively or not, using gradient signal-to-noise ratio (SNR) as the outcome
metric. Reference task: ground-state energy estimation for a 4-site
open-boundary transverse-field Ising model (TFIM).

## How to run

```bash
pip install -r requirements.txt
python main.py
```

This runs the full pipeline end to end: Hamiltonian sanity check -> 7 configs
x 50 seeds at L=3 -> H3 depth sweep (3 configs x 5 depths x 50 seeds) ->
hypothesis tests -> plots -> `RESULTS.md`. **Total wall time: ~109s** on the
machine this was developed on (main experiment ~16s, depth sweep ~93s --
the depth sweep dominates because circuit-evaluation cost and parameter
count both grow with L, up to L=8). No reduction in seed count or shot-repeat
count was needed to hit a reasonable runtime.

Individual stages can also be run/imported separately: `python hamiltonian.py`
(sanity check only), `python experiment.py` (raw data only, writes to
`results/`), `python analysis.py` (hypothesis tests from existing raw data),
`python plots.py` (plots from existing raw data).

## Project layout

- `hamiltonian.py` -- TFIM Hamiltonian construction (explicit Kronecker
  products) + exact diagonalization sanity check.
- `ansatze.py` -- baseline (HEA) and brick-layer entangling patterns, and the
  PennyLane `qml.Snapshot`/`qml.snapshots` plumbing that exposes mid-circuit
  statevectors for residual connections.
- `cost_functions.py` -- global (`<H>`) and local (`<Z0Z1>`) cost/variance
  formulas, and the residual-connection cost/variance combinators.
- `snr.py` -- the two-branch gradient/SNR estimator: parameter-shift for
  gate angles `theta_i`, direct analytic gradient for residual weights
  `alpha_l`.
- `experiment.py` -- defines the 7 ablation configs and the H3 depth-sweep
  configs, runs them, saves raw CSV/JSON to `results/`.
- `analysis.py` -- Wilcoxon signed-rank hypothesis tests (H1/H2a/H2b/H3) and
  summary statistics.
- `plots.py` -- SNR-by-configuration box/bar plots and the SNR-vs-depth plot.
- `main.py` -- orchestrates all of the above and writes `RESULTS.md`.

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

## Assumptions carried over directly from the spec (not independent choices)

- 4 qubits, `J=1`, `h=0.5`, open-boundary TFIM, `L=3` for the main experiment.
- `N=1000` shots per circuit evaluation; shot-noise variance is derived
  analytically from a single noiseless statevector pass per shifted circuit,
  never resampled empirically.
- 50 seeds, `theta ~ U[0, 2*pi)`, identical seeds across all 7 configurations
  (paired design).
- Wilcoxon signed-rank test (not Mann-Whitney U) for every paired
  configuration comparison.

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
