"""Total-gradient estimation via the hybrid chain rule (Section 6).

For the terminal block `d`, theta^(d) affects the cost only through the
final state (no downstream block consumes z^(d)), so its total gradient is
the *direct* parameter-shift gradient of C itself.

For every other block `ell < d`, theta^(ell) affects C only through
z^(ell), so:

    dC/dtheta_k^(ell) = sum_j (dC/dz_j^(ell)) (dz_j^(ell)/dtheta_k^(ell))

Reverse-mode assembly (derivation in ASSUMPTIONS.md A15): because x^(ell) and
theta^(ell) enter block ell identically (additive offset into the same Ry
angle -- A15), the local input-angle Jacobian dz^(ell)/dx^(ell) equals the
local gate-parameter Jacobian dz^(ell)/dtheta^(ell) exactly, so the total
gradient T[ell] := dC/dtheta^(ell) doubles as dC/dx^(ell) and can be reused
directly as the upstream sensitivity for block ell-1:

    T[d]   = direct parameter-shift gradient of C w.r.t. block d's angles
    g[ell] = W_ell^T @ T[ell+1]  +  gamma * T[ell+2]   (gamma term only if
                                                          R=1 and ell+2 <= d)
    T[ell] = J_theta[ell]^T @ g[ell]     for ell = d-1 .. 1

Three modes (Section 6):
  statevector_exact        -- exact features, exact node Jacobians (see
                               `total_gradients_exact`, no shot budget).
  finite_shot_conditional  -- exact forward features, resampled node
                               Jacobians only.
  finite_shot_end_to_end   -- forward features AND node Jacobians resampled;
                               noisy features are re-encoded into later
                               blocks (primary finite-shot analysis).

ASSUMPTION A16 (see ASSUMPTIONS.md): one replicate's finite-shot budget B
covers the *entire* total-gradient vector (forward pass + every block's node
Jacobian), not a fully independent budget per parameter -- computing every
parameter's chain independently would multiply circuit cost by the total
parameter count. Every parameter's gradient_hat within a replicate is
therefore drawn from that replicate's shared shot draws; independence holds
across replicates (fresh `rng` per replicate) and across +/- shift arms
(independent multinomial draws), matching Section 6's "different Jacobian
factors use independent shot batches" for the shift-arm axis.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from qnn_snr.budget import JobSpec, allocate_budget, enumerate_jobs
from qnn_snr.circuits import (
    apply_block,
    overlap_probability,
    x_basis_probs,
    x_expectation_from_x_probs,
    z_basis_probs,
    z_expectations,
    z_expectations_from_probs,
    zz_expectation_from_z_probs,
)
from qnn_snr.costs import evaluate_cost, local_energy_from_terms
from qnn_snr.hamiltonian import TFIMSpectrum
from qnn_snr.residual import ClassicalParams, initial_x, next_x

PI_2 = np.pi / 2


@dataclass
class ForwardResult:
    z: dict
    x: dict
    pre_block_states: dict
    final_state: np.ndarray
    cost: float
    applied_angles: dict


def forward_pass_exact(theta_blocks: list[np.ndarray], classical: ClassicalParams, E: int,
                        gamma: float, cost_type: str, spectrum: TFIMSpectrum,
                        n_qubits: int, x0_init: str = "zeros") -> ForwardResult:
    """Each block ell is a self-contained circuit that always starts from
    |0...0>_n (ASSUMPTION A15b): rho_ell = rho_ell(x^(ell), theta^(ell)) only,
    with no dependence on earlier blocks' raw quantum state -- their only
    channel of communication is the classical z -> x chain. `pre_block_states`
    is therefore always the zero state, kept per-block for API symmetry with
    the finite-shot path and so node Jacobians/terminal gradients share one
    signature regardless of block index."""
    d = len(theta_blocks)
    z = {0: np.zeros(n_qubits)}
    x = {1: initial_x(n_qubits, x0_init)}
    pre_block_states, applied_angles = {}, {}
    final_state = None
    for ell in range(1, d + 1):
        pre_state = _zero_state(n_qubits)
        pre_block_states[ell] = pre_state
        angle = theta_blocks[ell - 1] + x[ell]
        applied_angles[ell] = angle
        state = apply_block(pre_state, angle, ell - 1, E, n_qubits)
        if ell < d:
            z_ell = z_expectations(state, n_qubits)
            z[ell] = z_ell
            W_ell, b_ell = classical.W[ell - 1], classical.b[ell - 1]
            x[ell + 1] = next_x(W_ell, b_ell, z[ell], z[ell - 1], gamma)
        else:
            final_state = state
    cost = evaluate_cost(cost_type, final_state, spectrum)
    return ForwardResult(z=z, x=x, pre_block_states=pre_block_states, final_state=final_state,
                          cost=cost, applied_angles=applied_angles)


def _zero_state(n_qubits: int) -> np.ndarray:
    from qnn_snr.circuits import zero_state
    return zero_state(n_qubits)


def node_jacobian_exact(pre_state: np.ndarray, base_angle: np.ndarray, layer_idx: int, E: int,
                         n_qubits: int) -> np.ndarray:
    J = np.empty((n_qubits, n_qubits))
    for k in range(n_qubits):
        angle_p, angle_m = base_angle.copy(), base_angle.copy()
        angle_p[k] += PI_2
        angle_m[k] -= PI_2
        state_p = apply_block(pre_state, angle_p, layer_idx, E, n_qubits)
        state_m = apply_block(pre_state, angle_m, layer_idx, E, n_qubits)
        J[:, k] = (z_expectations(state_p, n_qubits) - z_expectations(state_m, n_qubits)) / 2.0
    return J


def terminal_cost_gradient_exact(pre_state: np.ndarray, base_angle: np.ndarray, layer_idx: int,
                                  E: int, n_qubits: int, cost_type: str,
                                  spectrum: TFIMSpectrum) -> np.ndarray:
    grad = np.empty(n_qubits)
    for k in range(n_qubits):
        angle_p, angle_m = base_angle.copy(), base_angle.copy()
        angle_p[k] += PI_2
        angle_m[k] -= PI_2
        state_p = apply_block(pre_state, angle_p, layer_idx, E, n_qubits)
        state_m = apply_block(pre_state, angle_m, layer_idx, E, n_qubits)
        Cp = evaluate_cost(cost_type, state_p, spectrum)
        Cm = evaluate_cost(cost_type, state_m, spectrum)
        grad[k] = (Cp - Cm) / 2.0
    return grad


def total_gradients_exact(theta_blocks: list[np.ndarray], classical: ClassicalParams, E: int,
                           gamma: float, cost_type: str, spectrum: TFIMSpectrum, n_qubits: int,
                           x0_init: str = "zeros"):
    d = len(theta_blocks)
    fwd = forward_pass_exact(theta_blocks, classical, E, gamma, cost_type, spectrum, n_qubits, x0_init)
    T = {d: terminal_cost_gradient_exact(fwd.pre_block_states[d], fwd.applied_angles[d], d - 1,
                                          E, n_qubits, cost_type, spectrum)}
    for ell in range(d - 1, 0, -1):
        g = classical.W[ell - 1].T @ T[ell + 1]
        if gamma != 0 and (ell + 2) <= d:
            g = g + gamma * T[ell + 2]
        J = node_jacobian_exact(fwd.pre_block_states[ell], fwd.applied_angles[ell], ell - 1, E, n_qubits)
        T[ell] = J.T @ g
    return T, fwd


# ---------------------------------------------------------------------------
# Finite-shot (noisy) variants
# ---------------------------------------------------------------------------

def _index_allocation(jobs: list[JobSpec], allocation: dict[str, int]) -> dict[tuple, dict]:
    """Maps (category, block_index, parameter_index, shift_sign) -> {basis: n_shots}."""
    out: dict[tuple, dict] = {}
    for j in jobs:
        key = (j.category, j.block_index, j.parameter_index, j.shift_sign)
        out.setdefault(key, {})[j.basis] = allocation[j.job_id]
    return out


def _sample_z_probs(state: np.ndarray, n_shots: int, rng: np.random.Generator) -> np.ndarray:
    probs = z_basis_probs(state)
    counts = rng.multinomial(n_shots, probs)
    return counts / n_shots


def _sample_x_probs(state: np.ndarray, n_qubits: int, n_shots: int, rng: np.random.Generator) -> np.ndarray:
    probs = x_basis_probs(state, n_qubits)
    counts = rng.multinomial(n_shots, probs)
    return counts / n_shots


def _noisy_z(state: np.ndarray, n_qubits: int, n_shots: int, rng: np.random.Generator) -> np.ndarray:
    return z_expectations_from_probs(_sample_z_probs(state, n_shots, rng), n_qubits)


def _noisy_cost(cost_type: str, state: np.ndarray, spectrum: TFIMSpectrum, n_qubits: int,
                 shots: dict, rng: np.random.Generator) -> float:
    if cost_type == "global":
        p0 = min(max(overlap_probability(state, spectrum.psi_0), 0.0), 1.0)
        n = shots["overlap"]
        k = rng.binomial(n, p0)
        return 1.0 - k / n
    emp_z = _sample_z_probs(state, shots["z"], rng)
    zz = [zz_expectation_from_z_probs(emp_z, i, i + 1, n_qubits) for i in range(n_qubits - 1)]
    emp_x = _sample_x_probs(state, n_qubits, shots["x"], rng)
    xs = [x_expectation_from_x_probs(emp_x, i, n_qubits) for i in range(n_qubits)]
    energy = local_energy_from_terms(zz, xs, spectrum.J, spectrum.h)
    return (energy - spectrum.E_0) / (spectrum.E_max - spectrum.E_0)


def total_gradients_finite_shot(theta_blocks: list[np.ndarray], classical: ClassicalParams, E: int,
                                 gamma: float, cost_type: str, spectrum: TFIMSpectrum, n_qubits: int,
                                 mode: str, budget_B: int, rng: np.random.Generator,
                                 x0_init: str = "zeros"):
    """One finite-shot replicate's total-gradient vector. `mode` in
    {"finite_shot_conditional", "finite_shot_end_to_end"}."""
    if mode not in ("finite_shot_conditional", "finite_shot_end_to_end"):
        raise ValueError(f"total_gradients_finite_shot does not support mode={mode!r}")

    d = len(theta_blocks)
    jobs = enumerate_jobs(d, n_qubits, cost_type, mode)
    allocation = allocate_budget(budget_B, jobs)
    shots_by_key = _index_allocation(jobs, allocation)

    z = {0: np.zeros(n_qubits)}
    x = {1: initial_x(n_qubits, x0_init)}
    pre_block_states, applied_angles = {}, {}
    final_state = None
    for ell in range(1, d + 1):
        pre_state = _zero_state(n_qubits)
        pre_block_states[ell] = pre_state
        angle = theta_blocks[ell - 1] + x[ell]
        applied_angles[ell] = angle
        state = apply_block(pre_state, angle, ell - 1, E, n_qubits)
        if ell < d:
            if mode == "finite_shot_end_to_end":
                n_shots = shots_by_key[("forward_feature", ell, -1, 0)]["z"]
                z_ell = _noisy_z(state, n_qubits, n_shots, rng)
            else:
                z_ell = z_expectations(state, n_qubits)
            z[ell] = z_ell
            W_ell, b_ell = classical.W[ell - 1], classical.b[ell - 1]
            x[ell + 1] = next_x(W_ell, b_ell, z[ell], z[ell - 1], gamma)
        else:
            final_state = state

    T = {}
    grad = np.empty(n_qubits)
    base_angle = applied_angles[d]
    for k in range(n_qubits):
        angle_p, angle_m = base_angle.copy(), base_angle.copy()
        angle_p[k] += PI_2
        angle_m[k] -= PI_2
        state_p = apply_block(pre_block_states[d], angle_p, d - 1, E, n_qubits)
        state_m = apply_block(pre_block_states[d], angle_m, d - 1, E, n_qubits)
        shots_p = shots_by_key[("terminal_cost", d, k, +1)]
        shots_m = shots_by_key[("terminal_cost", d, k, -1)]
        Cp = _noisy_cost(cost_type, state_p, spectrum, n_qubits, shots_p, rng)
        Cm = _noisy_cost(cost_type, state_m, spectrum, n_qubits, shots_m, rng)
        grad[k] = (Cp - Cm) / 2.0
    T[d] = grad

    for ell in range(d - 1, 0, -1):
        g = classical.W[ell - 1].T @ T[ell + 1]
        if gamma != 0 and (ell + 2) <= d:
            g = g + gamma * T[ell + 2]
        base = applied_angles[ell]
        J = np.empty((n_qubits, n_qubits))
        for k in range(n_qubits):
            angle_p, angle_m = base.copy(), base.copy()
            angle_p[k] += PI_2
            angle_m[k] -= PI_2
            state_p = apply_block(pre_block_states[ell], angle_p, ell - 1, E, n_qubits)
            state_m = apply_block(pre_block_states[ell], angle_m, ell - 1, E, n_qubits)
            shots_p = shots_by_key[("node_jacobian", ell, k, +1)]["z"]
            shots_m = shots_by_key[("node_jacobian", ell, k, -1)]["z"]
            zp = _noisy_z(state_p, n_qubits, shots_p, rng)
            zm = _noisy_z(state_m, n_qubits, shots_m, rng)
            J[:, k] = (zp - zm) / 2.0
        T[ell] = J.T @ g

    fwd = ForwardResult(z=z, x=x, pre_block_states=pre_block_states, final_state=final_state,
                         cost=evaluate_cost(cost_type, final_state, spectrum), applied_angles=applied_angles)
    return T, fwd, jobs, allocation
