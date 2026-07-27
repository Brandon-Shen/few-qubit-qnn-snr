"""TFIM Hamiltonian construction, exact diagonalization, and validation.

H = -J * sum_{i=0}^{n-2} Z_i Z_{i+1} - h * sum_{i=0}^{n-1} X_i

Open-boundary transverse-field Ising model. Dense matrices are built via
explicit Kronecker products in wire order (wire 0 = most significant bit),
matching PennyLane's `default.qubit` statevector convention.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)


def _kron_n(ops: list[np.ndarray]) -> np.ndarray:
    result = ops[0]
    for op in ops[1:]:
        result = np.kron(result, op)
    return result


def single_qubit_op(op: np.ndarray, qubit: int, n_qubits: int) -> np.ndarray:
    ops = [I2] * n_qubits
    ops[qubit] = op
    return _kron_n(ops)


def two_qubit_op(op: np.ndarray, q1: int, q2: int, n_qubits: int) -> np.ndarray:
    ops = [I2] * n_qubits
    ops[q1] = op
    ops[q2] = op
    return _kron_n(ops)


def build_tfim_hamiltonian(n_qubits: int = 4, J: float = 1.0, h: float = 0.5) -> np.ndarray:
    dim = 2 ** n_qubits
    H = np.zeros((dim, dim), dtype=complex)
    for i in range(n_qubits - 1):
        H -= J * two_qubit_op(Z, i, i + 1, n_qubits)
    for i in range(n_qubits):
        H -= h * single_qubit_op(X, i, n_qubits)
    return H


@dataclass(frozen=True)
class TFIMSpectrum:
    n_qubits: int
    J: float
    h: float
    H: np.ndarray
    eigvals: np.ndarray
    eigvecs: np.ndarray
    psi_0: np.ndarray
    rho_0: np.ndarray
    E_0: float
    E_max: float
    spectral_gap: float
    degenerate_ground_state: bool


def diagonalize_tfim(n_qubits: int = 4, J: float = 1.0, h: float = 0.5,
                      degeneracy_tol: float = 1e-9) -> TFIMSpectrum:
    H = build_tfim_hamiltonian(n_qubits, J, h)
    eigvals, eigvecs = np.linalg.eigh(H)
    psi_0 = eigvecs[:, 0]
    rho_0 = np.outer(psi_0, psi_0.conj())
    degenerate = bool(eigvals.size > 1 and (eigvals[1] - eigvals[0]) < degeneracy_tol)
    return TFIMSpectrum(
        n_qubits=n_qubits,
        J=J,
        h=h,
        H=H,
        eigvals=eigvals,
        eigvecs=eigvecs,
        psi_0=psi_0,
        rho_0=rho_0,
        E_0=float(eigvals[0]),
        E_max=float(eigvals[-1]),
        spectral_gap=float(eigvals[1] - eigvals[0]) if eigvals.size > 1 else float("nan"),
        degenerate_ground_state=degenerate,
    )


def validate_spectrum(spectrum: TFIMSpectrum, expected_E0: float, expected_Emax: float,
                       tol: float) -> dict:
    """Raises AssertionError with a clear message if the diagonalization does
    not match the paper's reported reference values, or if the ground state
    is (numerically) degenerate -- both objectives require a nondegenerate
    target (Section 3)."""
    checks = {
        "hermitian": bool(np.allclose(spectrum.H, spectrum.H.conj().T)),
        "E0_matches_reference": bool(abs(spectrum.E_0 - expected_E0) <= tol),
        "Emax_matches_reference": bool(abs(spectrum.E_max - expected_Emax) <= tol),
        "nondegenerate_ground_state": not spectrum.degenerate_ground_state,
        "psi0_normalized": bool(np.isclose(np.linalg.norm(spectrum.psi_0), 1.0)),
        "rho0_trace_one": bool(np.isclose(np.trace(spectrum.rho_0).real, 1.0)),
        "rho0_is_projector": bool(np.allclose(spectrum.rho_0 @ spectrum.rho_0, spectrum.rho_0, atol=1e-8)),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise AssertionError(
            f"TFIM spectrum validation failed: {failed}. "
            f"E_0={spectrum.E_0:.6f} (expected {expected_E0}), "
            f"E_max={spectrum.E_max:.6f} (expected {expected_Emax})."
        )
    return checks
