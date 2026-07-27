import numpy as np
import pytest

from qnn_snr.circuits import (
    apply_block,
    build_full_circuit_qnode,
    entanglement_diagnostics,
    overlap_probability,
    x_basis_probs,
    x_expectation_from_x_probs,
    z_basis_probs,
    z_expectations,
    zero_state,
    zz_expectation_from_z_probs,
)
from qnn_snr.config import entangling_pairs

N_QUBITS = 4


def _random_angles(depth, n_qubits, seed):
    rng = np.random.default_rng(seed)
    return rng.uniform(0, 2 * np.pi, size=(depth, n_qubits))


@pytest.mark.parametrize("E", [0, 1])
@pytest.mark.parametrize("depth", [1, 2, 3, 4, 6])
def test_numpy_block_propagation_matches_pennylane(depth, E):
    angles = _random_angles(depth, N_QUBITS, seed=depth * 10 + E)
    state = zero_state(N_QUBITS)
    for ell in range(depth):
        state = apply_block(state, angles[ell], ell, E, N_QUBITS)

    qnode = build_full_circuit_qnode(N_QUBITS, depth, E)
    reference = np.array(qnode(angles.reshape(-1)))

    assert np.allclose(state, reference, atol=1e-10)


def test_state_stays_normalized():
    angles = _random_angles(4, N_QUBITS, seed=7)
    state = zero_state(N_QUBITS)
    for ell in range(4):
        state = apply_block(state, angles[ell], ell, 1, N_QUBITS)
    assert np.linalg.norm(state) == pytest.approx(1.0, abs=1e-10)


def test_logical_cnot_counts_identical_between_schedules():
    for layer_idx in range(6):
        assert len(entangling_pairs(layer_idx, 0)) == len(entangling_pairs(layer_idx, 1)) == 4


def test_z_expectation_of_all_zero_state():
    state = zero_state(N_QUBITS)
    z = z_expectations(state, N_QUBITS)
    assert np.allclose(z, np.ones(N_QUBITS))


def test_z_expectation_after_single_x_flip():
    # apply an RY(pi) on qubit 0 == X gate up to phase; check <Z_0> flips to -1
    state = apply_block(zero_state(N_QUBITS), np.array([np.pi, 0, 0, 0]), layer_idx=0, E=0, n_qubits=N_QUBITS)
    # baseline layer 0 also applies CNOT 0->1,1->2,2->3,3->0 after the RY; undo by comparing
    # just the RY-only effect using a 1-qubit manual check instead:
    from qnn_snr.circuits import ry_matrix, apply_single_qubit_gate
    s = zero_state(N_QUBITS)
    s = apply_single_qubit_gate(s, ry_matrix(np.pi), 0, N_QUBITS)
    z = z_expectations(s, N_QUBITS)
    assert z[0] == pytest.approx(-1.0, abs=1e-10)


def test_zz_and_x_expectation_helpers_consistent_with_bruteforce():
    rng = np.random.default_rng(3)
    state = rng.normal(size=16) + 1j * rng.normal(size=16)
    state /= np.linalg.norm(state)

    from qnn_snr.hamiltonian import single_qubit_op, two_qubit_op, X, Z
    zz01_exact = float(np.real(np.conj(state) @ two_qubit_op(Z, 0, 1, N_QUBITS) @ state))
    x0_exact = float(np.real(np.conj(state) @ single_qubit_op(X, 0, N_QUBITS) @ state))

    zprobs = z_basis_probs(state)
    xprobs = x_basis_probs(state, N_QUBITS)
    zz01 = zz_expectation_from_z_probs(zprobs, 0, 1, N_QUBITS)
    x0 = x_expectation_from_x_probs(xprobs, 0, N_QUBITS)

    assert zz01 == pytest.approx(zz01_exact, abs=1e-10)
    assert x0 == pytest.approx(x0_exact, abs=1e-10)


def test_overlap_probability_matches_fidelity():
    rng = np.random.default_rng(4)
    a = rng.normal(size=16) + 1j * rng.normal(size=16)
    a /= np.linalg.norm(a)
    b = rng.normal(size=16) + 1j * rng.normal(size=16)
    b /= np.linalg.norm(b)
    assert overlap_probability(a, a) == pytest.approx(1.0, abs=1e-10)
    assert overlap_probability(a, b) == pytest.approx(abs(np.vdot(a, b)) ** 2, abs=1e-10)


def test_entanglement_diagnostics_zero_for_product_state():
    state = zero_state(N_QUBITS)  # |0000>, a product state
    diags = entanglement_diagnostics(state, N_QUBITS)
    assert len(diags) == 7  # all nontrivial bipartitions of 4 qubits
    for d in diags:
        assert d.von_neumann_entropy == pytest.approx(0.0, abs=1e-8)
        assert d.purity == pytest.approx(1.0, abs=1e-8)


def test_entanglement_diagnostics_nonzero_after_entangling_layer():
    # NOTE: pi/2 is a bad choice here -- RY(pi/2) sends every qubit to |+>, and
    # CNOT leaves an all-|+> product state exactly invariant (|+> is an X
    # eigenstate), so that angle is a genuine (zero-entanglement) degenerate
    # case, not a bug. Use a generic angle instead.
    angles = np.array([1.1, 0.7, 2.3, 0.4])
    state = apply_block(zero_state(N_QUBITS), angles, layer_idx=0, E=0, n_qubits=N_QUBITS)
    diags = entanglement_diagnostics(state, N_QUBITS)
    assert any(d.von_neumann_entropy > 1e-6 for d in diags)
