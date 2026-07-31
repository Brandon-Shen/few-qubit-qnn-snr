# The `B` shot-budget variable: exact definition, and realized shots vs nominal budget

## 1. Where `B` is consumed, quoted from the code

`B` (values `{250, 500, 1000, 2000}` per `configs/confirmatory.yaml`,
`budget.values`) enters the simulation exactly once per replicate, in
`qnn_snr/gradients.py::total_gradients_finite_shot`:

```python
# qnn_snr/gradients.py, lines 213-216
d = len(theta_blocks)
jobs = enumerate_jobs(d, n_qubits, cost_type, mode)
allocation = allocate_budget(budget_B, jobs)
shots_by_key = _index_allocation(jobs, allocation)
```

`enumerate_jobs()` (`qnn_snr/budget.py`) builds the **complete list of every
circuit measurement job needed to compute one full gradient vector** for one
replicate at one depth/cost-type/mode combination:

- forward-feature measurement jobs (`end_to_end` mode only — one per
  non-terminal block, `ell in range(1, depth)`),
- node-level parameter-shift Jacobian jobs (every block × every qubit ×
  both shift signs, for all non-terminal blocks),
- terminal-cost jobs (every qubit × both shift signs × the cost's
  observable bases — 1 basis, `overlap`, for the global cost; 2 bases,
  `z` and `x`, for the local TFIM-energy cost).

`allocate_budget()` then does floor-division of the *single* scalar `B`
across that *entire* job list, with the remainder distributed one shot at a
time in a fixed, reproducible sort order (`ASSUMPTION A8`):

```python
# qnn_snr/budget.py, lines 59-69
def allocate_budget(B: int, jobs: list[JobSpec]) -> dict[str, int]:
    n_jobs = len(jobs)
    if n_jobs == 0:
        return {}
    base = B // n_jobs
    remainder = B % n_jobs
    ordered = sorted(jobs, key=lambda j: j.sort_key())
    allocation = {j.job_id: base for j in ordered}
    for j in ordered[:remainder]:
        allocation[j.job_id] += 1
    return allocation
```

`budget.py`'s own module docstring already states this design intent
explicitly (not inferred from the variable name — quoted directly):

> "`B` is the total measurement budget for one complete matched
> total-gradient *vector* in one replicate... It covers every measurement
> job the computational graph requires: unshifted forward-feature
> measurements, all node-level parameter shifts, input-angle Jacobians...,
> Pauli terms, and overlap-circuit settings."

**Direct answer: `B` is neither "shots per circuit" nor "shots per
observable term."** It is a single total budget, divided (by floor-division
+ deterministic remainder) across the *entire* computational-graph job list
for one replicate's complete gradient vector — i.e. the third option in the
task's framing (total budget divided across the computational graph). This
is confirmed by code behavior, not just the docstring: `resource_accounting()`
computes `unused_remainder_shots = B - total_allocated_shots`, and by
construction (`base*n_jobs + remainder == B` always) this is exactly 0 —
every one of the `B` shots is consumed and none are held back per-circuit.

## 2. Realized shots per gradient component, per configuration, per depth

Because `B` is divided across a job list whose length (`n_jobs`) itself
depends on `depth`, `cost_type` (global vs local), and `mode` (conditional
vs end-to-end), **the same nominal `B` produces very different per-circuit
(per gradient-component) shot counts** across configurations, even though
the *total* shots per replicate is always exactly `B`. Enumerated directly
from `enumerate_jobs()` across the full confirmatory design space
(`n_qubits=4`, `depths=[1,2,3,4,6]`):

| depth | cost_type | mode | n_jobs (circuits) | shots/job @ B=1000 (floor) | shots/job @ B=250 (floor) |
|---|---|---|---|---|---|
| 1 | global | cond | 8  | 125 | 31 |
| 1 | global | e2e  | 8  | 125 | 31 |
| 1 | local  | cond | 16 | 62  | 15 |
| 1 | local  | e2e  | 16 | 62  | 15 |
| 2 | global | cond | 16 | 62  | 15 |
| 2 | global | e2e  | 17 | 58  | 14 |
| 2 | local  | cond | 24 | 41  | 10 |
| 2 | local  | e2e  | 25 | 40  | 10 |
| 3 | global | cond | 24 | 41  | 10 |
| 3 | global | e2e  | 26 | 38  | 9  |
| 3 | local  | cond | 32 | 31  | 7  |
| 3 | local  | e2e  | 34 | 29  | 7  |
| 4 | global | cond | 32 | 31  | 7  |
| 4 | global | e2e  | 35 | 28  | 7  |
| 4 | local  | cond | 40 | 25  | 6  |
| 4 | local  | e2e  | 43 | 23  | 5  |
| 6 | global | cond | 48 | 20  | 5  |
| 6 | global | e2e  | 53 | 18  | 4  |
| 6 | local  | cond | 56 | 17  | 4  |
| 6 | local  | e2e  | 61 | 16  | 4  |

(`cond` = `finite_shot_conditional`, `e2e` = `finite_shot_end_to_end`. Every
`total_allocated_shots` in every row of this table equals `B` exactly, by
construction — confirmed programmatically, not just asserted.)

Reading down any fixed depth: **local-cost configurations always have more
jobs than global-cost configurations at the same depth** (16 vs 8 terminal
jobs, because the local TFIM-energy cost sums over 2 Pauli bases (`z`,`x`)
per qubit while the global infidelity cost needs only 1 (`overlap`)), and
**end-to-end mode always has more jobs than conditional mode** at the same
depth/cost_type (by exactly `depth-1`, the forward-feature jobs conditional
mode skips). Both effects compound: at `depth=6`, global/conditional needs
48 circuits for the same total `B` that local/end-to-end needs 61 circuits
for — a ~27% difference in circuit count for identical nominal `B`.

## 3. Does "matched total measurement budget" hold?

**It depends which quantity "budget" refers to, and the paper is currently
right to avoid the unqualified claim:**

- **Total shots per replicate**: yes, trivially and exactly. `B` shots are
  always fully consumed (`unused_remainder_shots == 0` in every cell of the
  design), so if "measurement budget" means "total number of quantum
  circuit executions summed over the whole gradient computation," every
  configuration at a given nominal `B` uses exactly `B`, full stop —
  global vs local, conditional vs end-to-end, any depth. Matched exactly by
  construction.
- **Shots per circuit / per gradient component (the resource that actually
  determines each measurement's statistical precision)**: **no, not
  matched, and systematically so.** For fixed `B` and `depth`, local-cost
  configurations get fewer shots per circuit than global-cost configurations
  (e.g. at depth=6, B=1000: global≈20 shots/circuit vs local≈17
  shots/circuit for conditional mode; 18 vs 16 for end-to-end mode), because
  the same total budget is spread over more circuit settings. Likewise,
  end-to-end mode gets fewer shots per circuit than conditional mode at
  fixed depth/cost_type, and the gap widens with depth (at depth=6 global,
  conditional≈20 vs end-to-end≈18 shots/circuit at B=1000; the *relative*
  gap is largest at high depth since forward-feature jobs scale with
  `depth-1`).

This directly confirms the concern the paper's Methods section already
flags qualitatively ("the global and local objectives can require different
numbers of observable terms/circuit settings, so equal nominal `B` does not
guarantee equal realized resources") — the local-cost configurations are the
systematically shot-starved-per-circuit side of the E/L/R design at matched
nominal `B`, and this gets worse as depth increases. **The paper should
continue to avoid an unqualified "matched total measurement budgets" claim**;
the accurate statement is: total shot count is exactly matched across all
configurations at a given nominal `B`, but per-circuit (per gradient
component) shot count is not, and is systematically lower for local-cost and
for end-to-end-mode configurations, more so at higher depth.

## Reproduction

```python
from qnn_snr.budget import enumerate_jobs, allocate_budget

jobs = enumerate_jobs(depth=6, n_qubits=4, cost_type="local", mode="finite_shot_end_to_end")
alloc = allocate_budget(1000, jobs)
sum(alloc.values())   # == 1000, always
len(jobs)              # == 61
```
