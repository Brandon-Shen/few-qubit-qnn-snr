"""Deterministic shot-budget allocation and resource accounting (Section 7).

`B` is the total measurement budget for one complete matched total-gradient
*vector* in one replicate (Section 5/6 design note, ASSUMPTION A16: given the
computational cost of a fully independent per-parameter budget for a 4-qubit,
depth-<=6 sweep, this codebase pools the forward-feature and node-Jacobian
measurements shared by every parameter's chain-rule term into one replicate
-- see ASSUMPTIONS.md A16). It covers every measurement job the computational
graph requires: unshifted forward-feature measurements, all node-level
parameter shifts, input-angle Jacobians (identical to the theta-Jacobian
under ASSUMPTION A15, so not double-counted), Pauli terms, and overlap-circuit
settings.

The default allocator splits B equally (floor division) over the required
job list, then assigns the remainder shots one at a time following a fixed
job order sorted by (block_index, parameter_index, shift_sign, basis) --
ASSUMPTION A8 -- so allocation is exactly reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    category: str  # "forward_feature" | "node_jacobian" | "terminal_cost"
    block_index: int  # 1-indexed block ell this job measures
    parameter_index: int  # 0-indexed qubit/parameter index, -1 for forward-feature jobs
    shift_sign: int  # +1, -1, or 0 (unshifted)
    basis: str  # "z", "x", "overlap"

    def sort_key(self):
        return (self.block_index, self.parameter_index, self.shift_sign, self.basis)


def enumerate_jobs(depth: int, n_qubits: int, cost_type: str, mode: str) -> list[JobSpec]:
    jobs: list[JobSpec] = []

    if mode == "finite_shot_end_to_end":
        for ell in range(1, depth):  # forward features needed to build x^(2..d)
            jobs.append(JobSpec(f"fwd_z_ell{ell}", "forward_feature", ell, -1, 0, "z"))

    for ell in range(1, depth):  # node-level Jacobians for non-terminal blocks
        for k in range(n_qubits):
            for sign in (+1, -1):
                jobs.append(JobSpec(f"node_ell{ell}_k{k}_s{sign}", "node_jacobian", ell, k, sign, "z"))

    terminal_bases = ["overlap"] if cost_type == "global" else ["z", "x"]
    for k in range(n_qubits):
        for sign in (+1, -1):
            for basis in terminal_bases:
                jobs.append(JobSpec(f"term_ell{depth}_k{k}_s{sign}_{basis}", "terminal_cost", depth, k, sign, basis))

    jobs.sort(key=lambda j: j.sort_key())
    return jobs


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


@dataclass
class ResourceAccounting:
    total_allocated_shots: int
    n_circuits: int
    n_shifted_circuits: int
    n_observable_groups: int
    n_forward_feature_measurements: int
    n_jacobian_measurements: int
    unused_remainder_shots: int
    total_quantum_evaluations: int

    def as_dict(self) -> dict:
        return {
            "total_allocated_shots": self.total_allocated_shots,
            "n_circuits": self.n_circuits,
            "n_shifted_circuits": self.n_shifted_circuits,
            "n_observable_groups": self.n_observable_groups,
            "n_forward_feature_measurements": self.n_forward_feature_measurements,
            "n_jacobian_measurements": self.n_jacobian_measurements,
            "unused_remainder_shots": self.unused_remainder_shots,
            "total_quantum_evaluations": self.total_quantum_evaluations,
        }


def resource_accounting(B: int, jobs: list[JobSpec], allocation: dict[str, int]) -> ResourceAccounting:
    n_forward = sum(1 for j in jobs if j.category == "forward_feature")
    n_jacobian = sum(1 for j in jobs if j.category in ("node_jacobian", "terminal_cost"))
    n_shifted = sum(1 for j in jobs if j.shift_sign != 0)
    bases = {j.basis for j in jobs}
    total_allocated = sum(allocation.values())
    return ResourceAccounting(
        total_allocated_shots=total_allocated,
        n_circuits=len(jobs),
        n_shifted_circuits=n_shifted,
        n_observable_groups=len(bases),
        n_forward_feature_measurements=n_forward,
        n_jacobian_measurements=n_jacobian,
        unused_remainder_shots=B - total_allocated,  # 0 by construction; kept explicit for the schema
        total_quantum_evaluations=total_allocated,
    )
