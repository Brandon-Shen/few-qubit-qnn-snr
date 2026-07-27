import numpy as np
import pytest

from qnn_snr.costs import global_cost_exact, local_cost_exact
from qnn_snr.hamiltonian import build_tfim_hamiltonian, diagonalize_tfim, validate_spectrum


def test_hamiltonian_hermitian_and_shape():
    H = build_tfim_hamiltonian(n_qubits=4, J=1.0, h=0.5)
    assert H.shape == (16, 16)
    assert np.allclose(H, H.conj().T)


def test_ground_and_max_energy_match_reference():
    spectrum = diagonalize_tfim(n_qubits=4, J=1.0, h=0.5)
    assert spectrum.E_0 == pytest.approx(-3.4270, abs=5e-3)
    assert spectrum.E_max == pytest.approx(3.4270, abs=5e-3)


def test_nondegenerate_ground_state():
    spectrum = diagonalize_tfim(n_qubits=4, J=1.0, h=0.5)
    assert not spectrum.degenerate_ground_state
    assert spectrum.spectral_gap > 1e-6


def test_validate_spectrum_passes_for_reference_params():
    spectrum = diagonalize_tfim(n_qubits=4, J=1.0, h=0.5)
    checks = validate_spectrum(spectrum, expected_E0=-3.4270, expected_Emax=3.4270, tol=5e-3)
    assert all(checks.values())


def test_validate_spectrum_fails_for_wrong_reference():
    spectrum = diagonalize_tfim(n_qubits=4, J=1.0, h=0.5)
    with pytest.raises(AssertionError):
        validate_spectrum(spectrum, expected_E0=-1.0, expected_Emax=3.4270, tol=1e-6)


def test_costs_zero_at_exact_ground_state():
    spectrum = diagonalize_tfim(n_qubits=4, J=1.0, h=0.5)
    assert global_cost_exact(spectrum.psi_0, spectrum.psi_0) == pytest.approx(0.0, abs=1e-10)
    assert local_cost_exact(spectrum.psi_0, spectrum) == pytest.approx(0.0, abs=1e-8)


def test_costs_nonzero_for_orthogonal_excited_state():
    spectrum = diagonalize_tfim(n_qubits=4, J=1.0, h=0.5)
    excited = spectrum.eigvecs[:, 1]
    assert global_cost_exact(excited, spectrum.psi_0) == pytest.approx(1.0, abs=1e-8)
