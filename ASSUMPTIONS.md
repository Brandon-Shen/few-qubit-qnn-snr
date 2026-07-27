# Implementation assumptions

This document records every scientifically consequential choice that the
companion review paper ("Gradient Usability in Few-Qubit Quantum Neural
Networks: A Signal-to-Noise Ratio Framework for Evaluating Mitigation
Strategies", Section 5.3) does not fully determine. None of these are
conclusions of the review — they are implementation decisions of this
codebase. Every item below is exposed as a field in `configs/*.yaml`, carries
a documented default, and is echoed into `run_manifest.json` /
`config_hash` so results can be traced back to the exact assumption set that
produced them.

## A1. Mapping of L (cost) to objective function

The factorial design fixes `L in {0,1}` but the paper does not itself name
which cost function attaches to which level. This codebase fixes:

- `L=0` -> global cost `C_global = 1 - Tr[rho_0 rho(theta)]`
- `L=1` -> local cost `C_local = (Tr[H rho(theta)] - E_0) / (E_max - E_0)`

Config key: `cost.mapping.L0` / `cost.mapping.L1` (default `global` / `local`).
Both costs are always evaluated and logged for every configuration
regardless of which one drives gradients (Section 3), so this choice affects
which gradients are the primary confirmatory signal, not which quantities are
observable.

## A2. Ry initialization distribution

Gate-parameter initialization is drawn `theta ~ U[0, 2*pi)` i.i.d. per
parameter, matched by seed across all 8 configurations. This is a common
hardware-efficient-ansatz default, not specified by the review.

Config key: `circuit.init_low`, `circuit.init_high` (default `0`, `2*pi`).

## A3. Depth-to-hybrid-block mapping

The paper specifies a depth sweep `[1,2,3,4,6]` and a residual architecture
with block index `ell`, but does not state how many hybrid (quantum ->
classical) blocks a circuit of nominal depth `d` is divided into.

This codebase assumes **one hybrid block per ansatz layer**: a depth-`d`
circuit has `d` blocks, each block being exactly one Ry-layer +
entangling-layer unit, with a quantum-feature readout `z^(ell)` taken at the
block boundary (i.e. after the entangling layer of block `ell`, before block
`ell+1`'s rotations). Block 1 additionally receives no `z^(ell-1)` residual
term (no block 0), so the residual shortcut is only structurally active for
`ell >= 2`. This preserves "no additional quantum gates" (Section 5) exactly.

Config key: `residual.blocks_per_depth` (default `one_per_layer`).

## A4. Initial classical input vector x^(0)

The classical recursion `x^(ell+1) = W_ell z^(ell) + b_ell [+ gamma * z^(ell-1)]`
requires an anchor `x^(0)`, which is never measured from a quantum node.
This codebase defines `x^(0) = 0` (the zero vector in R^{n_qubits}), i.e. the
first block's classical pathway carries only `b_0` before any quantum
feature exists. This is scientifically inert for the confirmatory gradient
tests (Section 6), since the confirmatory quantities are quantum-parameter
gradients evaluated through the chain rule, not the value of x^(0) itself,
but it is recorded because it fixes the classical forward pass exactly.

Config key: `residual.x0_init` (default `zeros`).

## A5. Classical layer dimensionality and initialization

`W_ell` is assumed square, `R^{n_qubits x n_qubits}`, so that `x^(ell)` and
`z^(ell)` share dimensionality across blocks. `W_ell` uses Glorot-uniform
initialization and `b_ell = 0`, matched by seed between the `R=0` and `R=1`
conditions (Section 5: "Match W and b initialization between residual and
non-residual conditions").

Config keys: `residual.hidden_dim` (default `n_qubits`), `residual.weight_init`
(default `glorot_uniform`), `residual.bias_init` (default `zeros`).

## A6. gamma values and trainability

Fixed exactly as specified: `gamma=0` for `R=0`, `gamma=1` for `R=1`,
non-trainable in the confirmatory design. `gamma in {0.5, 1.0}` sensitivity
sweep (Section 16) is exploratory only and implemented as a separate labeled
analysis, never substituted into H1-H4.

Config key: `residual.gamma_by_R.R0` / `residual.gamma_by_R.R1` (default
`0.0` / `1.0`); `residual.gamma_sensitivity_values` (default `[0.5, 1.0]`,
exploratory).

## A7. Confirmatory measurement point

Section 2: "the primary confirmatory analysis occurs immediately after
initialization and before the first optimizer update." This codebase
therefore never trains parameters for the H1-H4 confirmatory tests; the
matched initial `theta` (and `W`, `b`) is the sole point at which confirmatory
gradients/SNR are computed. Any post-training checkpoint analysis
(Section 2, Section 16) uses a separate `pilot_or_confirmatory`-orthogonal
`checkpoint_id` field and is always exploratory.

## A8. Budget allocator tie-breaking

The equal-allocation default (Section 7) distributes `floor(B / n_jobs)`
shots to every required measurement job, then assigns the `B mod n_jobs`
remainder shots one at a time to jobs in a fixed deterministic order (job
list sorted by `(block_index, parameter_index, shift_sign)`), so the
allocation is exactly reproducible and independent of dict/set iteration
order.

Config key: `budget.remainder_policy` (default `deterministic_sorted`).

## A9. p-value engine for H1-H4

Section 13 explicitly leaves the unadjusted p-value engine undetermined
while fixing two-sided testing and Holm-Bonferroni adjustment. This codebase
uses the mixed model's Wald z-statistic (`estimate / SE`) with a normal
reference distribution as the documented default, with the method name
recorded per-row in `confirmatory_hypotheses.csv` and selectable via
`stats.p_value_method` (default `wald_normal`) so a preregistered
bootstrap-null method can be swapped in later without silently changing
results of an existing run.

## A10. Entanglement diagnostic cuts

"Bipartite von Neumann entropy across all nontrivial cuts" is computed for
every contiguous and non-contiguous bipartition of the 4 qubits into
non-empty proper subsets (7 unique unordered bipartitions for n=4), plus the
corresponding reduced-state purities. No area-law/volume-law scaling claim is
made anywhere in the generated report (Section 4 explicitly forbids this for
a 4-qubit system).

## A11. Noise model for `hardware_noisy` mode

Section 6 requires the API to "support it cleanly" but does not require a
noise model for the first smoke test. This codebase defines the mode
interface (a `NoiseModel` protocol consumed by `gradients.py`) and ships one
concrete depolarizing-channel implementation as a placeholder, but no
`hardware_noisy` results are included in the confirmatory or exploratory
outputs of the default configs. Enabling it requires explicitly setting
`gradient.hardware_noisy.enabled: true` and is always exploratory.

## A15b. Blocks do not share a continued statevector (self-contained nodes)

This is the single most consequential implementation choice in the codebase,
so it is documented in detail.

Section 4 describes the ansatz gate sequence (Ry-layer + 4 CNOTs) and calls
`depths=[1,2,3,4,6]` a **depth sweep**, which invites the standard reading of
one continuously-evolving multi-layer circuit (the same wavefunction passed
through `d` Ry+CNOT layers in sequence) -- how "circuit depth" is normally
used in barren-plateau literature. Section 5, however, writes each block's
output as `rho_ell(x^(ell), theta^(ell))` -- a function of *only* that
block's own classical input and gate parameters, with no term for any
upstream raw quantum state -- and Section 6 gives an explicit, exact
total-derivative formula, `dC/dtheta_k^(ell) = sum_j (dC/dz_j^(ell))
(dz_j^(ell)/dtheta_k^(ell))`, which routes theta^(ell)'s *entire* effect on
C through z^(ell) alone.

These two readings are mutually exclusive. Under a continued-statevector
architecture, theta_k^(ell) affects the final cost through **two** channels:
(1) direct continued unitary propagation into blocks ell+1..d (present even
with no residual/classical structure at all), and (2) the classical z -> x
feedback path. Section 6's formula only accounts for (2); it would be
*incomplete* (and demonstrably wrong against a finite-difference check --
this was caught by `tests/test_gradients.py` during development, which
initially failed by large margins, not by numerical-precision-sized errors)
under a continued-statevector reading.

This codebase therefore implements each block as a **self-contained circuit
that always starts from the all-zero state `|0...0>_n`**, receiving only the
classical vector x^(ell) as an additive angle bias into its own Ry layer
(ASSUMPTION A15). Blocks communicate *exclusively* through the declared
z -> W,b,gamma -> x chain; there is no other channel. Under this
architecture, Section 6's formula is exactly correct (not a simplification),
and the reverse-mode assembly in `qnn_snr/gradients.py` implements it
directly:

    T[d]   = direct parameter-shift gradient of C w.r.t. block d's own angles
    g[ell] = W_ell^T @ T[ell+1]  +  gamma * T[ell+2]   (gamma term only if
                                                          R=1 and ell+2 <= d)
    T[ell] = J_theta[ell]^T @ g[ell]     for ell = d-1 .. 1

reusing dz^(ell)/dx^(ell) == dz^(ell)/dtheta^(ell) (ASSUMPTION A15) so the
local node Jacobian doubles as the upstream sensitivity handed to block
ell-1.

The repeated qualifier **"nominal circuit depth"** (Sections 2, 4, 6, and
`config.depth` in the required schema) is read as corroborating this choice:
it flags that the stated depth is not the depth of one literal monolithic
circuit. A consequence worth flagging explicitly: because block `d`'s own
gate sequence is always exactly one Ry-layer + one CNOT-layer regardless of
`d`, the *entanglement diagnostics* (Section 4) computed on the final state
do not directly reflect "how many entangling layers deep" the circuit is in
the traditional sense -- they reflect the entanglement producible by one
layer acting on the angle bias accumulated through `d-1` blocks of upstream
classical processing. This is reported as such, not described as area-law or
volume-law scaling evidence (Section 4 already forbids that claim for a
4-qubit system regardless).

If this reading turns out not to match the review paper's intent, the
alternative (continued-statevector, standard multi-layer HEA) architecture
would need its own from-scratch reverse-mode/autodiff derivation through the
full statevector (not just through z), since a naive shift-and-rerun
approach on a continued-statevector circuit is provably inexact whenever a
parameter re-enters a later gate nonlinearly through a measurement-based
feedback loop -- exactly the failure mode Section 6 warns against. This is
flagged here as the one item in this document most worth revisiting with the
paper's authors before treating downstream depth-dependent conclusions as
final.

## A17. Per-depth independent initialization draws

Each `(initialization_id, depth)` cell draws its own independent theta/W/b
seed derived from `(seed_root, initialization_id, depth)` only -- never from
`(E, L, R)` -- so all 8 configurations see bit-identical parameters for a
given cell (Section 2). Depth levels are **not** prefix-nested (a depth-6
draw does not reuse depth-4's first four blocks' angles); each depth gets a
fresh independent draw. Config key: implicit in the seed derivation
(`qnn_snr/replicate.py`); no separate flag, since prefix-nesting would create
a different, not-obviously-better, matching structure than the one Section 2
actually asks for (matching *across E/L/R*, not across depth levels).

## A18. Depth centering/scaling reference

`depth_centered`/`depth_z` are standardized against the **design's distinct
nominal depth levels** (`config.circuit.depths`, unweighted by how many
replicate rows each level produces), not a per-row empirical mean/std of the
generated dataset. This keeps the transform fixed by the config alone
(reproducible without needing the full dataset in hand) and matches Section
10's "values calculated from the complete confirmatory design" (the design
*specifies* 5 depth levels; weighting by row count would let unrelated
choices like replicate count silently shift the standardization).

## A19. Exact-mode budget sentinel

`statevector_exact` rows are not shot-budget-dependent (Section 6: "exact
features; exact node Jacobians; exact total gradients"); they carry
`budget=0` / `log2_budget=NaN` as an explicit sentinel and a single
`replicate_id=0` per (initialization, depth, configuration, parameter) cell,
since the mode is fully deterministic given the matched initialization.

## A20. Nested random-effect unit for the mixed models

The nested random intercept "(1 | initialization_id:parameter_id)" (Sections
10/11) is implemented as `(1 | initialization_id : depth : parameter_id)` --
i.e. the nested unit also includes depth, not just initialization x
parameter. Reason: under ASSUMPTION A17, each depth level draws an
independent theta value, so "theta_ell1_q0" at depth=2 and depth=4 are
different underlying numbers that only share a label; what is genuinely
matched (identical value, varying only E/L/R) is a parameter within one
initialization *and* one depth. Implemented via a combined
`nested_param_id` column consumed by statsmodels' `vc_formula` variance-
component mechanism, with an explicit `re_formula="1"` so the top-level
`(1 | initialization_id)` intercept is estimated *alongside* (not replaced
by) the nested component -- statsmodels silently drops the top-level
group intercept when `vc_formula` is given without an explicit `re_formula`,
which was caught by `tests/test_models.py`'s synthetic-recovery tests during
development (`cov_re` came back empty).

## A21. Bootstrap parallel execution

`qnn_snr/stats/bootstrap.py` implements checkpoint/resume (periodic Parquet +
JSON checkpoint of completed/failed iteration indices, config key
`stats.bootstrap.checkpoint_every`) but runs bootstrap iterations
**sequentially**, not in worker processes. Section 14 asks for "parallel
execution"; each iteration refits a `statsmodels` MixedLM model, which is
CPU-bound pure-Python/numpy work that would need process-level (not thread-
level) parallelism to actually speed up, and reliably pickling the resample
+ refit closure across processes was judged not worth the implementation
risk relative to correctness work elsewhere in this codebase. `n_workers` is
accepted in `configs/*.yaml` for forward compatibility but is currently a
no-op. This is flagged as a known gap, not a silent one: publication-scale
bootstrap runs (2000 iterations) should budget wall-clock time accordingly
or shard iterations across separate `bootstrap` CLI invocations with
different `--seed-offset` values and concatenate `bootstrap_coefficients.parquet`
afterward (the checkpoint file format supports this by construction, since
each iteration's row is independently keyed by iteration index).

## A12. Pilot representative cells

Section 17.A requires "representative prespecified cells" for replicate-count
selection. This codebase prespecifies: configuration 1 (baseline) and
configuration 8 (all interventions), at the minimum and maximum depth
(1 and 6) and minimum and maximum budget (250 and 2000), i.e. 8 cells,
chosen *before* any confirmatory data are inspected, listed explicitly in
`configs/*.yaml` under `pilot.replicate_count.representative_cells` so the
choice is auditable rather than post-hoc.
