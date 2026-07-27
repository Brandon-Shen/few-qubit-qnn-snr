"""Ansatz circuit blocks: RY+CNOT layer construction, statevector propagation,
measurement-basis probabilities, and entanglement diagnostics.

Each block applies (Section 4):
  1. one independently parameterized Ry rotation to every qubit;
  2. exactly four logical CNOT gates, using the baseline schedule (E=0) or the
     odd/even restricted schedule (E=1) from `config.entangling_pairs`.

Per ASSUMPTION A15 (see ASSUMPTIONS.md), the classical activation x^(ell)
feeding into block `ell` is applied as an additive offset to that block's
trainable Ry angles: applied_angle_q = theta_q^(ell) + x_q^(ell). This keeps
the gate sequence of Section 4 exactly intact (no additional gates, same
trainable Ry count) while giving rho_ell a genuine dependence on x^(ell) as
required by Section 5.

Block-to-block propagation is done here with direct numpy gate application
(RY and CNOT as dense 2x2/4x4 matrices acting on the n-qubit statevector) for
speed across the very large number of shifted block re-evaluations the
replicate pipeline requires. This is cross-validated against a PennyLane
`default.qubit` QNode in tests/test_circuits.py, and PennyLane is used
directly for the exact-diagonalization/statevector pipeline, gradient
cross-checks (Section 20), and as the reference full-circuit builder below.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
import pennylane as qml

from qnn_snr.config import entangling_pairs

_I2 = np.eye(2, dtype=complex)


def ry_matrix(theta: float) -> np.ndarray:
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def apply_single_qubit_gate(state: np.ndarray, gate: np.ndarray, qubit: int, n_qubits: int) -> np.ndarray:
    state = state.reshape([2] * n_qubits)
    state = np.moveaxis(state, qubit, 0)
    state = np.tensordot(gate, state, axes=([1], [0]))
    state = np.moveaxis(state, 0, qubit)
    return state.reshape(-1)


# Precompute CNOT permutation indices once per (control, target, n_qubits) since the
# ansatz only ever uses a fixed small set of wire pairs on a 4-qubit register.
_CNOT_PERM_CACHE: dict[tuple[int, int, int], np.ndarray] = {}


def _cnot_permutation(control: int, target: int, n_qubits: int) -> np.ndarray:
    key = (control, target, n_qubits)
    if key not in _CNOT_PERM_CACHE:
        dim = 2 ** n_qubits
        perm = np.arange(dim)
        for basis_index in range(dim):
            bits = [(basis_index >> (n_qubits - 1 - w)) & 1 for w in range(n_qubits)]
            if bits[control] == 1:
                bits[target] ^= 1
                new_index = 0
                for b in bits:
                    new_index = (new_index << 1) | b
                perm[basis_index] = new_index
        _CNOT_PERM_CACHE[key] = perm
    return _CNOT_PERM_CACHE[key]


def apply_cnot_fast(state: np.ndarray, control: int, target: int, n_qubits: int) -> np.ndarray:
    perm = _cnot_permutation(control, target, n_qubits)
    out = np.empty_like(state)
    out[perm] = state
    return out


def apply_block(state: np.ndarray, angles: np.ndarray, layer_idx: int, E: int, n_qubits: int) -> np.ndarray:
    """Applies one ansatz block (Ry layer + entangling layer) to `state` in
    place-equivalent (returns new array). `angles` are the *applied* angles
    (theta + x offset already summed), length n_qubits."""
    out = state
    for q in range(n_qubits):
        out = apply_single_qubit_gate(out, ry_matrix(angles[q]), q, n_qubits)
    for (a, b) in entangling_pairs(layer_idx, E):
        out = apply_cnot_fast(out, a, b, n_qubits)
    return out


def zero_state(n_qubits: int) -> np.ndarray:
    state = np.zeros(2 ** n_qubits, dtype=complex)
    state[0] = 1.0
    return state


def z_expectations_from_probs(probs: np.ndarray, n_qubits: int) -> np.ndarray:
    """<Z_j> for every qubit j from a Z-basis probability vector (length 2^n),
    whether exact (Born-rule) or empirical (shot counts / n_shots)."""
    probs = probs.reshape([2] * n_qubits)
    z_vals = np.empty(n_qubits)
    for k in range(n_qubits):
        other_axes = tuple(i for i in range(n_qubits) if i != k)
        marg = probs.sum(axis=other_axes) if other_axes else probs
        z_vals[k] = marg[0] - marg[1]
    return z_vals


def z_expectations(state: np.ndarray, n_qubits: int) -> np.ndarray:
    """<Z_j> for every qubit j, from Born-rule marginal probabilities."""
    return z_expectations_from_probs(np.abs(state) ** 2, n_qubits)


def z_basis_probs(state: np.ndarray) -> np.ndarray:
    return np.abs(state) ** 2


_H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)


def x_basis_probs(state: np.ndarray, n_qubits: int) -> np.ndarray:
    out = state
    for q in range(n_qubits):
        out = apply_single_qubit_gate(out, _H, q, n_qubits)
    return np.abs(out) ** 2


def zz_expectation_from_z_probs(probs: np.ndarray, q1: int, q2: int, n_qubits: int) -> float:
    dim = probs.shape[0]
    val = 0.0
    for idx in range(dim):
        bits = [(idx >> (n_qubits - 1 - w)) & 1 for w in range(n_qubits)]
        sign = (1 - 2 * bits[q1]) * (1 - 2 * bits[q2])
        val += sign * probs[idx]
    return float(val)


def x_expectation_from_x_probs(probs: np.ndarray, q: int, n_qubits: int) -> float:
    dim = probs.shape[0]
    val = 0.0
    for idx in range(dim):
        bit = (idx >> (n_qubits - 1 - q)) & 1
        sign = 1 - 2 * bit
        val += sign * probs[idx]
    return float(val)


def overlap_probability(state: np.ndarray, psi_0: np.ndarray) -> float:
    """P(all-zero) of the inversion-test circuit U_prep(psi_0)^dagger applied
    to `state`, i.e. |<psi_0|state>|^2 -- the fidelity used by C_global."""
    return float(np.abs(np.vdot(psi_0, state)) ** 2)


# ---------------------------------------------------------------------------
# PennyLane reference circuit (used for cross-validation and full-state tests)
# ---------------------------------------------------------------------------

def build_full_circuit_qnode(n_qubits: int, depth: int, E: int):
    dev = qml.device("default.qubit", wires=n_qubits)

    @qml.qnode(dev)
    def circuit(applied_angles):
        grid = qml.math.reshape(applied_angles, (depth, n_qubits))
        for ell in range(depth):
            for q in range(n_qubits):
                qml.RY(grid[ell, q], wires=q)
            for (a, b) in entangling_pairs(ell, E):
                qml.CNOT(wires=[a, b])
        return qml.state()

    return circuit


# ---------------------------------------------------------------------------
# Entanglement diagnostics (Section 4)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EntanglementDiagnostic:
    cut: tuple[int, ...]
    von_neumann_entropy: float
    purity: float


def _reduced_density_matrix(state: np.ndarray, subsystem: tuple[int, ...], n_qubits: int) -> np.ndarray:
    psi = state.reshape([2] * n_qubits)
    other = tuple(i for i in range(n_qubits) if i not in subsystem)
    axes = list(subsystem) + list(other)
    psi_t = np.transpose(psi, axes).reshape(2 ** len(subsystem), 2 ** len(other))
    rho = psi_t @ psi_t.conj().T
    return rho


def entanglement_diagnostics(state: np.ndarray, n_qubits: int, entropy_tol: float = 1e-12) -> list[EntanglementDiagnostic]:
    """Bipartite von Neumann entropy and reduced-state purity for every
    nontrivial bipartition of the n-qubit register (Section 4)."""
    results = []
    seen = set()
    for size in range(1, n_qubits):
        for subsystem in itertools.combinations(range(n_qubits), size):
            complement = tuple(sorted(set(range(n_qubits)) - set(subsystem)))
            canon = tuple(sorted([subsystem, complement]))
            if canon in seen:
                continue
            seen.add(canon)
            rho = _reduced_density_matrix(state, subsystem, n_qubits)
            eigvals = np.linalg.eigvalsh(rho)
            eigvals = np.clip(eigvals.real, 0.0, 1.0)
            nz = eigvals[eigvals > entropy_tol]
            entropy = float(-np.sum(nz * np.log2(nz))) if nz.size else 0.0
            purity = float(np.real(np.trace(rho @ rho)))
            results.append(EntanglementDiagnostic(cut=subsystem, von_neumann_entropy=entropy, purity=purity))
    return results
