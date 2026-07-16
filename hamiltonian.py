"""TFIM Hamiltonian construction and exact-diagonalization sanity checks.

H = -J * (Z0 Z1 + Z1 Z2 + Z2 Z3) - h * (X0 + X1 + X2 + X3)

Open-boundary 4-site transverse-field Ising model. Matrices are built by
explicit Kronecker products in wire order (wire 0 = most significant bit),
matching PennyLane's `default.qubit` statevector convention (verified: a
PauliX on wire 0 alone produces the same state as np.kron(X, I, I, I) @ |0>).
"""
import numpy as np

I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)


def _kron_n(ops):
    result = ops[0]
    for op in ops[1:]:
        result = np.kron(result, op)
    return result


def _single_qubit_op(op, qubit, n_qubits):
    ops = [I2] * n_qubits
    ops[qubit] = op
    return _kron_n(ops)


def _two_qubit_op(op, q1, q2, n_qubits):
    ops = [I2] * n_qubits
    ops[q1] = op
    ops[q2] = op
    return _kron_n(ops)


def build_tfim_hamiltonian(n_qubits=4, J=1.0, h=0.5):
    """Open-boundary TFIM: H = -J * sum_i Z_i Z_{i+1} - h * sum_i X_i."""
    dim = 2 ** n_qubits
    H = np.zeros((dim, dim), dtype=complex)
    for i in range(n_qubits - 1):
        H -= J * _two_qubit_op(Z, i, i + 1, n_qubits)
    for i in range(n_qubits):
        H -= h * _single_qubit_op(X, i, n_qubits)
    return H


def build_xxz_hamiltonian(n_qubits, delta=0.5):
    """Open-boundary XXZ (Heisenberg with anisotropy): H = sum_i (X_i X_{i+1}
    + Y_i Y_{i+1} + delta * Z_i Z_{i+1}). U(1)-symmetric (total Z magnetization
    conserved), no external field -- structurally distinct from the TFIM
    (Z2 symmetry, field term), used as Task C's "structurally different model"
    rather than just a reparameterization of the TFIM.
    """
    dim = 2 ** n_qubits
    H = np.zeros((dim, dim), dtype=complex)
    for i in range(n_qubits - 1):
        H += _two_qubit_op(X, i, i + 1, n_qubits)
        H += _two_qubit_op(Y, i, i + 1, n_qubits)
        H += delta * _two_qubit_op(Z, i, i + 1, n_qubits)
    return H


def z0z1_operator(n_qubits=4):
    """Local cost observable O = Z0 Z1."""
    return _two_qubit_op(Z, 0, 1, n_qubits)


def exact_diagonalize(H):
    """Returns (eigenvalues sorted ascending, eigenvectors) via numpy.linalg.eigh."""
    eigvals, eigvecs = np.linalg.eigh(H)
    return eigvals, eigvecs


def exact_ground_energy(H):
    eigvals = np.linalg.eigvalsh(H)
    return float(eigvals[0])


def sanity_check(n_qubits=4, J=1.0, h=0.5, verbose=True):
    """Builds H, diagonalizes it exactly, and validates basic properties:
    Hermiticity, dimensionality, and that Z0Z1 is a valid +/-1 Pauli observable.
    Returns a dict of results for reporting.
    """
    H = build_tfim_hamiltonian(n_qubits, J, h)
    assert H.shape == (2 ** n_qubits, 2 ** n_qubits)
    assert np.allclose(H, H.conj().T), "Hamiltonian is not Hermitian"

    eigvals, eigvecs = exact_diagonalize(H)
    ground_energy = eigvals[0]
    ground_state = eigvecs[:, 0]

    ZZ = z0z1_operator(n_qubits)
    assert np.allclose(ZZ @ ZZ, np.eye(2 ** n_qubits)), "Z0Z1 is not idempotent (O^2 != I)"

    ground_zz_expval = float(np.real(ground_state.conj() @ ZZ @ ground_state))

    results = {
        "n_qubits": n_qubits,
        "J": J,
        "h": h,
        "ground_energy": float(ground_energy),
        "first_excited_energy": float(eigvals[1]),
        "spectral_gap": float(eigvals[1] - eigvals[0]),
        "ground_state_zz01_expval": ground_zz_expval,
        "hermitian_check_passed": True,
        "zz_idempotent_check_passed": True,
    }
    if verbose:
        print("=== TFIM Hamiltonian sanity check ===")
        print(f"  n_qubits={n_qubits}, J={J}, h={h}")
        print(f"  Exact ground energy:      {results['ground_energy']:.6f}")
        print(f"  First excited energy:     {results['first_excited_energy']:.6f}")
        print(f"  Spectral gap:             {results['spectral_gap']:.6f}")
        print(f"  <ground| Z0Z1 |ground>:   {results['ground_state_zz01_expval']:.6f}")
        print(f"  Hermitian check:          passed")
        print(f"  Z0Z1 idempotent check:    passed")
    return results


def sanity_check_hamiltonian(H, n_qubits, label="", task_params=None, verbose=False):
    """Generic version of `sanity_check` for an arbitrary (already-built)
    Hamiltonian `H`, used by the n x task sweep (companion-paper phase) so
    every (task, n) grid point gets the same Hermiticity / Z0Z1-idempotency /
    exact-ground-energy regression guard as the pilot's n=4 TFIM check,
    without hardcoding a Hamiltonian builder here.
    """
    assert H.shape == (2 ** n_qubits, 2 ** n_qubits)
    assert np.allclose(H, H.conj().T), f"Hamiltonian is not Hermitian ({label}, n={n_qubits})"

    eigvals, eigvecs = exact_diagonalize(H)
    ground_energy = eigvals[0]
    ground_state = eigvecs[:, 0]

    ZZ = z0z1_operator(n_qubits)
    assert np.allclose(ZZ @ ZZ, np.eye(2 ** n_qubits)), \
        f"Z0Z1 is not idempotent ({label}, n={n_qubits})"
    ground_zz_expval = float(np.real(ground_state.conj() @ ZZ @ ground_state))

    results = {
        "task": label,
        "task_params": task_params or {},
        "n_qubits": n_qubits,
        "ground_energy": float(ground_energy),
        "first_excited_energy": float(eigvals[1]) if len(eigvals) > 1 else None,
        "spectral_gap": float(eigvals[1] - eigvals[0]) if len(eigvals) > 1 else None,
        "ground_state_zz01_expval": ground_zz_expval,
        "hermitian_check_passed": True,
        "zz_idempotent_check_passed": True,
    }
    if verbose:
        print(f"  [{label}, n={n_qubits}] ground={results['ground_energy']:.6f}  "
              f"gap={results['spectral_gap']}  <Z0Z1>_gs={ground_zz_expval:.6f}")
    return results


if __name__ == "__main__":
    sanity_check()
