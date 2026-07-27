"""Global and local cost functions (Section 3).

C_global(theta) = 1 - Tr[rho_0 rho(theta)] = 1 - |<psi_0|psi(theta)>|^2
C_local(theta)  = (Tr[H rho(theta)] - E_0) / (E_max - E_0)

Both are implemented from (a) an exact statevector directly, and (b) from
measured Pauli-term expectation values (Z_iZ_{i+1}, X_i, and the overlap
probability), so the same cost formula is used whether the underlying
expectation values come from exact linear algebra or from finite-shot
Born-rule sampling (see circuits.py / gradients.py).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from qnn_snr.circuits import (
    overlap_probability,
    x_basis_probs,
    x_expectation_from_x_probs,
    z_basis_probs,
    zz_expectation_from_z_probs,
)
from qnn_snr.hamiltonian import TFIMSpectrum


def global_cost_exact(state: np.ndarray, psi_0: np.ndarray) -> float:
    return 1.0 - overlap_probability(state, psi_0)


def local_energy_from_terms(zz: list[float], x: list[float], J: float, h: float) -> float:
    return -J * float(sum(zz)) - h * float(sum(x))


def local_cost_from_terms(zz: list[float], x: list[float], spectrum: TFIMSpectrum) -> float:
    energy = local_energy_from_terms(zz, x, spectrum.J, spectrum.h)
    return (energy - spectrum.E_0) / (spectrum.E_max - spectrum.E_0)


def exact_energy_expectation(state: np.ndarray, H: np.ndarray) -> float:
    return float(np.real(np.conj(state) @ H @ state))


def local_cost_exact(state: np.ndarray, spectrum: TFIMSpectrum) -> float:
    energy = exact_energy_expectation(state, spectrum.H)
    return (energy - spectrum.E_0) / (spectrum.E_max - spectrum.E_0)


@dataclass(frozen=True)
class TermExpectations:
    zz: list[float]  # <Z_i Z_{i+1}>, i = 0..n_qubits-2
    x: list[float]  # <X_i>, i = 0..n_qubits-1


def term_expectations_exact(state: np.ndarray, n_qubits: int) -> TermExpectations:
    zprobs = z_basis_probs(state)
    xprobs = x_basis_probs(state, n_qubits)
    zz = [zz_expectation_from_z_probs(zprobs, i, i + 1, n_qubits) for i in range(n_qubits - 1)]
    x = [x_expectation_from_x_probs(xprobs, i, n_qubits) for i in range(n_qubits)]
    return TermExpectations(zz=zz, x=x)


def evaluate_cost(cost_type: str, state: np.ndarray, spectrum: TFIMSpectrum) -> float:
    if cost_type == "global":
        return global_cost_exact(state, spectrum.psi_0)
    elif cost_type == "local":
        return local_cost_exact(state, spectrum)
    raise ValueError(f"unknown cost_type: {cost_type}")


def evaluate_both_costs(state: np.ndarray, spectrum: TFIMSpectrum) -> dict:
    """Always-reported quantities (Section 3): final TFIM energy and global
    fidelity, regardless of which cost drove optimization/gradients."""
    energy = exact_energy_expectation(state, spectrum.H)
    fidelity = overlap_probability(state, spectrum.psi_0)
    return {
        "final_tfim_energy": energy,
        "global_fidelity": fidelity,
        "global_cost": 1.0 - fidelity,
        "local_cost": (energy - spectrum.E_0) / (spectrum.E_max - spectrum.E_0),
    }
