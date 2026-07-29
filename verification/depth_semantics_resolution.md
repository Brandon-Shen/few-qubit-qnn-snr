# Task B — A15b depth-semantics resolution

Scope: decide whether the paper intends each ansatz block to be an independent
self-contained circuit re-initialized from `|0...0>` and driven only by the classical
re-encoded input (what `ASSUMPTIONS.md` A15b calls the "self-contained circuit
reading," and what the codebase implements), or a single continuous multi-layer
circuit where the residual/classical structure only perturbs *inputs* partway through
an otherwise-coherent statevector. This gates trustworthy interpretation of H4 and any
other depth-dependent claim, including the `E:L:depth_z` sensitivity check in Task A.

**Evidentiary limitation, stated up front**: this repository does not contain the
paper itself (no PDF/text file — confirmed by search). The evidence available is (a)
`ASSUMPTIONS.md` A15b's own extensive documented reasoning, which was evidently
written with the paper in hand and cites specific paper text, and (b) the two
paper excerpts quoted directly in this task's own prompt — the `z^(ℓ) = q_ℓ(x^(ℓ),
θ^(ℓ))` notation and "an upstream quantum parameter affects the final cost through
subsequent re-encoding operations and quantum blocks." I do not have independent
access to the full text of Section 5.2.2 ("circuit controls") beyond what's quoted
here, so this resolution is built on convergent evidence from what's available, not a
line-by-line read of the source section. If the actual Section 5.2.2 text is
available, it should be checked against the conclusion below before treating this as
final.

## 1. What A15b's implementation actually does

From `qnn_snr/gradients.py` (`forward_pass_exact`) and `ASSUMPTIONS.md` A15b: every
block `ell` starts from the fixed all-zero state `|0...0>_n` (`_zero_state`, called
fresh at the top of each loop iteration, never carrying `state` forward from the
previous block). The *only* thing that varies block-to-block is the applied Ry angle,
`theta^(ell) + x^(ell)`, where `x^(ell)` is a purely classical vector computed from
the *previous* block's measured `z^(ell-1)` via `W_{ell-1} z^(ell-1) + b_{ell-1} [+
gamma z^(ell-2)]`. This is "measure-then-reinitialize": block `ell` never receives any
raw quantum state, entangled or otherwise, from block `ell-1` — communication is
exclusively through the classical `z -> x` chain. This is the first of the two
readings the task describes, not the second.

## 2. Cross-check against the quoted paper text

**`z^(ℓ) = q_ℓ(x^(ℓ), θ^(ℓ))`.** The right-hand side's argument list is exactly two
items: this block's own classical input and this block's own gate parameters. Under a
continued-statevector architecture, block `ℓ`'s measurement outcome would necessarily
also depend on the incoming quantum state from block `ℓ-1` — i.e. the notation would
need a third argument, something like `q_ℓ(ρ^(ℓ-1), x^(ℓ), θ^(ℓ))`, to be accurate.
Its absence is direct evidence that the paper models each block's quantum output as a
function of *only* its own classical input and parameters — which is precisely the
self-contained-circuit reading.

**"An upstream quantum parameter affects the final cost through subsequent
re-encoding operations and quantum blocks."** **Correction (this pass): this argument
does not hold up and is downgraded to inconclusive — it should not be counted as
corroboration.** The original reasoning here depended on this sentence naming
*exactly one* channel (re-encoding). It doesn't: read literally, the sentence names
*two* things — "re-encoding operations" **and** "quantum blocks" — not one. "Quantum
blocks" is exactly the kind of phrase a continued-statevector reading would also use
to name its second (direct-propagation) channel, so the absence of a more explicit
phrase like "the surviving quantum state" cannot be read as ruling that channel out.
This sentence is compatible with both readings and provides no evidence for either
one on its own; it should not have been treated as pointing the same direction as the
`z^(ℓ) = q_ℓ(...)` notation below.

Of the two pieces of quoted paper text, only the `z^(ℓ) = q_ℓ(x^(ℓ), θ^(ℓ))` notation
actually supports the self-contained reading; the "re-encoding operations and quantum
blocks" sentence is neutral, not corroborating.

## 3. A15b's internal argument (independent corroboration)

`ASSUMPTIONS.md` A15b makes a third, structurally different argument that doesn't
depend on textual parsing: Section 6's own stated total-derivative formula,

```
dC/dtheta_k^(ell) = sum_j (dC/dz_j^(ell)) (dz_j^(ell)/dtheta_k^(ell))
```

routes an upstream parameter's *entire* effect on `C` through `z^(ell)` alone. This
formula is only exactly correct if there is no other channel — i.e. only under the
self-contained-block reading. Under a continued-statevector reading, this formula
would be missing a term (the direct-propagation channel) and would be a
mathematically incomplete gradient. A15b states this was tested empirically during
development: "this was caught by `tests/test_gradients.py` ... which initially failed
by large margins, not by numerical-precision-sized errors" when a continued-state
version was tried. That earlier finding is itself essentially a finite-difference bug
hunt of exactly the kind Task 1 of this verification pass just ran independently for
the *current* (self-contained) implementation — and Task 1 found agreement to <1e-6
relative error, not "large margins." Put together: the self-contained reading is the
one under which the paper's own stated gradient formula is exactly true; the
alternative reading was tried and found to break that formula outright.

## 4. Decision

**The self-contained-circuit reading (current A15b implementation) matches the
paper's intent.** This now rests on **two** independent lines of evidence, not three
— §2's "re-encoding operations and quantum blocks" argument is struck (see the
correction above) and no longer counted:

1. The quoted `z^(ℓ) = q_ℓ(x^(ℓ), θ^(ℓ))` notation has no state-carryover argument —
   textual, suggestive on its own but not conclusive by itself.
2. **Load-bearing.** Section 6's own exact gradient formula is only correct under this
   reading, and the alternative was empirically tested and found to produce a formula
   that doesn't match finite differences by a wide margin (per A15b's account of
   `tests/test_gradients.py`'s development history). This is a mathematical/empirical
   argument, independent of how any one sentence is parsed, and is what the decision
   below actually rests on.

Losing the struck argument does not overturn the decision — line 2 was always the
strongest of the original three and is sufficient on its own — but the decision is now
explicitly a two-line, not three-line, convergence, and should be cited that way.

No divergence found. `A15b` does not need to change, and no re-simulation is implied
by this resolution.

## 5. Residual uncertainty and what would firm this up further

This decision rests on one textual fragment (the `z^(ℓ)` notation) plus one
document's account of its own development history, not a full read of Section 5.2.2
or a look at the paper's actual printed Equation 7 (the "re-encoding operations and
quantum blocks" quote, previously treated as a second textual line, no longer counts
— see §2's correction and §4). The convergence across these two lines — one textual,
one mathematical/empirical — makes this a reasonably confident call, but two things
would make it airtight rather than "reasonably confident":

- **The actual Section 5.2.2 text** ("circuit controls"), which this task named as
  load-bearing but did not quote. If it contains language describing depth as
  literal continuous circuit evolution (e.g., explicit reference to barren-plateau
  scaling arguments that assume a single evolving state, or explicit circuit
  diagrams showing entangling gates spanning block boundaries), that would
  contradict the conclusion above and should be checked before treating this as
  fully closed.
- **The paper's own Equation 7**, to see whether the chain-rule assembly shown there
  (gradient contributions summed only through `z`) matches
  `qnn_snr/gradients.py`'s reverse-mode structure (`W_ell^T @ T[ell+1] + gamma *
  T[ell+2]`) term-for-term, or whether it has an extra term this codebase is missing.

**Impact assessment if this resolution is later overturned** (i.e., if Section 5.2.2
turns out to describe continued-statevector semantics): per A15b's own text, "the
alternative ... architecture would need its own from-scratch reverse-mode/autodiff
derivation through the full statevector (not just through z)" — this is not a
relabeling fix. It would require: (a) a new gradient implementation (a different
`total_gradients_exact`/`total_gradients_finite_shot` that propagates one continued
state through all `d` blocks and differentiates through the full circuit, likely via
autodiff rather than the current block-local parameter-shift + chain-rule assembly),
(b) full re-simulation of both `exact.parquet` and both finite-shot mode datasets
(the underlying quantum computation changes, not just its interpretation — this is
not a caveat that can be added to existing numbers), and (c) re-running
`aggregate`/`fit`/`bootstrap`/`report` on the new data. Every depth-dependent
quantity in `results_and_discussion.md` (H4 directly; H1/H2's depth_z control terms;
the entanglement-by-depth diagnostic, which A15b already flags as not reflecting
"how many entangling layers deep" under the current reading) would need
re-derivation, not just re-captioning. Given the decision in §4 above, this
contingency is not triggered — flagged here only so the cost of being wrong is on
record.

## 6. Proposed next steps (for approval, none executed)

1. **If available, provide the actual text of Section 5.2.2 and Equation 7** so §5's
   residual uncertainty can be closed rather than left as "reasonably confident."
2. **No code or data changes recommended** — this resolution found A15b's current
   implementation consistent with the paper as quoted, so Task C/D's outputs (and
   the existing confirmatory H1–H4 results) do not need to be re-scoped on this basis.
3. If you want the E:L:depth_z-style check from Task A extended to H4/H3 as well (i.e.
   checking whether the confirmatory model's depth-related terms behave sensibly
   under this now-corroborated reading), that would be a cheap follow-up fit-only
   check, not a re-simulation — flagged as optional, not started here since it wasn't
   asked for.

## 7. A separate, unresolved tension: the entangling-schedule description (Section 5.2.2)

This is a new open question raised in this pass, not resolved by the decision in §4
above — the tension below is between two pieces of the paper's own text, not
something that re-reading the same fragments harder would settle.

**The quotes.** The paper's own description of the entangling schedule (Section
5.2.2) states that the baseline (E=0) schedule produces "a causal path spanning the
complete register within one entangling layer," while the restricted (E=1) schedule
is such that "circuit-wide propagation requires multiple layers rather than occurring
within one layer."

**Why this is in tension with the self-contained/reset-per-block reading.** Both
halves of this description are about entangling correlations *building up across
layers* — the restricted schedule's defining property, per this text, is that it
takes more layers (i.e., more of the `depths=[1,2,3,4,6]` sweep) for "circuit-wide
propagation" to occur than the baseline schedule needs. That claim only makes sense if
the entangling structure produced at layer `ell` can still influence what happens at
layer `ell+k` for `k>1` — i.e., if there is a single continuously evolving quantum
state that layer `ell+1`'s CNOTs act on top of, carrying forward whatever
correlations layer `ell` already produced. Under the self-contained/reset-per-block
reading confirmed in §4 (every block re-initialized fresh from `|0...0>`, per
`qnn_snr/gradients.py` `forward_pass_exact` — see §1), there is no such carryover:
block `ell+1`'s entangling layer acts on a fresh all-zero state, not on block `ell`'s
output state, so "requires multiple layers to propagate" cannot describe what this
implementation actually does — each block's entangling layer either spans the
register on its own or it doesn't, independent of `d`, and nothing about that changes
as `depths` increases.

**This looks like underspecification in the source paper, not a misreading.** The
entangling-schedule prose in Section 5.2.2 reads as though it was written with the
standard continuous-multi-layer-circuit picture in mind — the same picture Section
4's "depth sweep" language invites, per `ASSUMPTIONS.md` A15b's own opening paragraph
— without full reconciliation with the residual/self-contained-block formalism
introduced in Sections 5–6 that §4 above confirms the codebase correctly implements.
The paper's own internal consistency between these two descriptions is not something
this codebase's implementation choice can fix by being read more carefully; it is a
property of the source text, and adjudicating which of the two passages should yield
is a question for the paper's authors, not an implementation question. This section
documents the tension rather than resolving it.

**What this does *not* affect.** Section 6's gradient formula — the load-bearing
argument in §4 — makes no reference to entangling-layer propagation at all; it is a
statement about how `theta^(ell)` enters the cost through `z^(ell)`, orthogonal to
whether the entangling gates *within* a block's own layer produce register-wide
correlations. The self-contained-block architecture and its gradient formula stand
regardless of how this tension is eventually resolved by the paper's authors.

**Practical check and takeaway**: see `verification/depth_entanglement_by_depth_check.md`
for a cheap, concrete data check of whether this tension is visible in the actual
confirmatory run's entanglement diagnostics, and for the practical bottom line for
H1–H4 validity and for how the companion paper's discussion section should describe
this mechanism.
