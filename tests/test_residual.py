import numpy as np
import pytest

from qnn_snr.residual import init_classical_params, initial_x, next_x


def test_matched_initialization_same_seed_identical_across_R():
    p0 = init_classical_params(seed=42, depth=4, n_qubits=4, hidden_dim=4)
    p1 = init_classical_params(seed=42, depth=4, n_qubits=4, hidden_dim=4)
    for w0, w1 in zip(p0.W, p1.W):
        assert np.array_equal(w0, w1)
    for b0, b1 in zip(p0.b, p1.b):
        assert np.array_equal(b0, b1)


def test_transition_count_is_depth_minus_one():
    params = init_classical_params(seed=1, depth=5, n_qubits=4, hidden_dim=4)
    assert len(params.W) == 4
    assert len(params.b) == 4


def test_depth_one_has_no_transitions():
    params = init_classical_params(seed=1, depth=1, n_qubits=4, hidden_dim=4)
    assert params.W == []
    assert params.b == []


def test_hidden_dim_mismatch_raises():
    with pytest.raises(ValueError):
        init_classical_params(seed=1, depth=3, n_qubits=4, hidden_dim=6)


def test_next_x_gamma_zero_matches_plain_transition():
    W = np.eye(3) * 2.0
    b = np.array([1.0, 1.0, 1.0])
    z = np.array([0.5, 0.5, 0.5])
    z_prev = np.array([9.0, 9.0, 9.0])
    out0 = next_x(W, b, z, z_prev, gamma=0.0)
    out1 = next_x(W, b, z, z_prev, gamma=1.0)
    assert np.allclose(out0, W @ z + b)
    assert np.allclose(out1, W @ z + b + z_prev)
    assert not np.allclose(out0, out1)


def test_initial_x_is_zero_vector():
    assert np.array_equal(initial_x(4), np.zeros(4))
