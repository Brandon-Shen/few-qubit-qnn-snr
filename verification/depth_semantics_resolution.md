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
re-encoding operations and quantum blocks."** Read literally, this sentence names
exactly one channel: re-encoding (the classical `z -> x` feedback) into subsequent
blocks. It does not say "through re-encoding *and* through continued unitary
propagation" or "through the surviving quantum state." If a continued-statevector
architecture were intended, an upstream parameter would affect the cost through *two*
channels — direct continued propagation (present even with zero residual structure)
and re-encoding — and a sentence naming the mechanism precisely would be expected to
name both, or use general language ("affects the final cost downstream") rather than
specifically "through re-encoding operations." Naming only re-encoding is evidence
the paper does not consider a direct continued-propagation channel to exist at all.

Both pieces of quoted text point the same direction, independently of A15b's own
argument.

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
paper's intent.** All three independent lines of evidence agree:

1. The quoted `z^(ℓ) = q_ℓ(x^(ℓ), θ^(ℓ))` notation has no state-carryover argument.
2. The quoted "affects the final cost through subsequent re-encoding operations and
   quantum blocks" names only the re-encoding channel.
3. Section 6's own exact gradient formula is only correct under this reading, and the
   alternative was empirically tested and found to produce a formula that doesn't
   match finite differences by a wide margin (per A15b's account of
   `tests/test_gradients.py`'s development history).

No divergence found. `A15b` does not need to change, and no re-simulation is implied
by this resolution.

## 5. Residual uncertainty and what would firm this up further

This decision rests on textual fragments (two quotes) plus one document's account of
its own development history, not a full read of Section 5.2.2 or a look at the
paper's actual printed Equation 7. The convergence across three independent lines of
evidence makes this a reasonably confident call, but two things would make it
airtight rather than "reasonably confident":

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
