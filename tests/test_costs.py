import numpy as np
import pytest

from qnn_snr.costs import (
    evaluate_both_costs,
    global_cost_exact,
    local_cost_exact,
    local_cost_from_terms,
    term_expectations_exact,
)
from qnn_snr.hamiltonian import diagonalize_tfim

SPECTRUM = diagonalize_tfim(n_qubits=4, J=1.0, h=0.5)


def _random_state(seed):
    rng = np.random.default_rng(seed)
    s = rng.normal(size=16) + 1j * rng.normal(size=16)
    return s / np.linalg.norm(s)


def test_local_cost_from_terms_matches_dense_hamiltonian():
    state = _random_state(1)
    terms = term_expectations_exact(state, n_qubits=4)
    from_terms = local_cost_from_terms(terms.zz, terms.x, SPECTRUM)
    from_dense = local_cost_exact(state, SPECTRUM)
    assert from_terms == pytest.approx(from_dense, abs=1e-10)


def test_evaluate_both_costs_reports_fidelity_and_energy_always():
    state = _random_state(2)
    out = evaluate_both_costs(state, SPECTRUM)
    assert set(out.keys()) == {"final_tfim_energy", "global_fidelity", "global_cost", "local_cost"}
    assert out["global_cost"] == pytest.approx(1.0 - out["global_fidelity"], abs=1e-12)


def test_costs_bounded_appropriately():
    for seed in range(5):
        state = _random_state(seed)
        g = global_cost_exact(state, SPECTRUM.psi_0)
        l = local_cost_exact(state, SPECTRUM)
        assert -1e-9 <= g <= 1.0 + 1e-9
        assert l >= -1e-9  # local cost is normalized so ground state maps to 0, bounded below
