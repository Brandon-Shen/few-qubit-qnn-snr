import numpy as np
import pennylane as qml
import pytest

from qnn_snr.circuits import apply_block, zero_state
from qnn_snr.config import entangling_pairs
from qnn_snr.costs import evaluate_cost
from qnn_snr.gradients import (
    node_jacobian_exact,
    terminal_cost_gradient_exact,
    total_gradients_exact,
)
from qnn_snr.hamiltonian import diagonalize_tfim
from qnn_snr.residual import init_classical_params

N_QUBITS = 4
SPECTRUM = diagonalize_tfim(n_qubits=N_QUBITS, J=1.0, h=0.5)
EPS = 1e-6


def _theta_blocks(depth, seed):
    rng = np.random.default_rng(seed)
    return [rng.uniform(0, 2 * np.pi, size=N_QUBITS) for _ in range(depth)]


def _forward_cost(theta_blocks, classical, E, gamma, cost_type):
    from qnn_snr.gradients import forward_pass_exact
    return forward_pass_exact(theta_blocks, classical, E, gamma, cost_type, SPECTRUM, N_QUBITS).cost


@pytest.mark.parametrize("cost_type", ["global", "local"])
def test_terminal_node_jacobian_matches_pennylane_autodiff(cost_type):
    depth, E = 2, 0
    theta = _theta_blocks(depth, seed=1)
    classical = init_classical_params(seed=2, depth=depth, n_qubits=N_QUBITS, hidden_dim=N_QUBITS)
    from qnn_snr.gradients import forward_pass_exact
    fwd = forward_pass_exact(theta, classical, E, 0.0, cost_type, SPECTRUM, N_QUBITS)
    pre_state = fwd.pre_block_states[depth]
    base_angle = fwd.applied_angles[depth]

    manual = terminal_cost_gradient_exact(pre_state, base_angle, depth - 1, E, N_QUBITS, cost_type, SPECTRUM)

    dev = qml.device("default.qubit", wires=N_QUBITS)

    @qml.qnode(dev, diff_method="parameter-shift")
    def circuit(angles):
        qml.StatePrep(pre_state, wires=range(N_QUBITS))
        for q in range(N_QUBITS):
            qml.RY(angles[q], wires=q)
        for (a, b) in entangling_pairs(depth - 1, E):
            qml.CNOT(wires=[a, b])
        if cost_type == "global":
            return qml.expval(qml.Hermitian(np.outer(SPECTRUM.psi_0, SPECTRUM.psi_0.conj()), wires=range(N_QUBITS)))
        return qml.expval(qml.Hermitian(SPECTRUM.H, wires=range(N_QUBITS)))

    angles_pl = qml.numpy.array(base_angle, requires_grad=True)
    if cost_type == "global":
        pl_grad = -np.array(qml.grad(circuit)(angles_pl))  # d(1-fidelity)/dtheta = -d(fidelity)/dtheta
    else:
        pl_grad = np.array(qml.grad(circuit)(angles_pl)) / (SPECTRUM.E_max - SPECTRUM.E_0)

    assert manual == pytest.approx(pl_grad, abs=1e-7)


def test_node_jacobian_matches_finite_difference():
    depth, E = 3, 1
    theta = _theta_blocks(depth, seed=5)
    classical = init_classical_params(seed=6, depth=depth, n_qubits=N_QUBITS, hidden_dim=N_QUBITS)
    from qnn_snr.gradients import forward_pass_exact
    fwd = forward_pass_exact(theta, classical, E, 1.0, "local", SPECTRUM, N_QUBITS)
    ell = 1
    pre_state = fwd.pre_block_states[ell]
    base_angle = fwd.applied_angles[ell]

    J = node_jacobian_exact(pre_state, base_angle, ell - 1, E, N_QUBITS)

    from qnn_snr.circuits import z_expectations
    for k in range(N_QUBITS):
        angle_p, angle_m = base_angle.copy(), base_angle.copy()
        angle_p[k] += EPS
        angle_m[k] -= EPS
        zp = z_expectations(apply_block(pre_state, angle_p, ell - 1, E, N_QUBITS), N_QUBITS)
        zm = z_expectations(apply_block(pre_state, angle_m, ell - 1, E, N_QUBITS), N_QUBITS)
        fd = (zp - zm) / (2 * EPS)
        assert J[:, k] == pytest.approx(fd, abs=1e-5)


@pytest.mark.parametrize("R,gamma", [(0, 0.0), (1, 1.0)])
@pytest.mark.parametrize("cost_type", ["global", "local"])
def test_total_chain_rule_gradient_matches_full_finite_difference(R, gamma, cost_type):
    depth, E = 3, 1
    theta = _theta_blocks(depth, seed=11)
    classical = init_classical_params(seed=12, depth=depth, n_qubits=N_QUBITS, hidden_dim=N_QUBITS)

    T, fwd = total_gradients_exact(theta, classical, E, gamma, cost_type, SPECTRUM, N_QUBITS)

    for ell in range(1, depth + 1):
        for k in range(N_QUBITS):
            theta_p = [t.copy() for t in theta]
            theta_m = [t.copy() for t in theta]
            theta_p[ell - 1][k] += EPS
            theta_m[ell - 1][k] -= EPS
            Cp = _forward_cost(theta_p, classical, E, gamma, cost_type)
            Cm = _forward_cost(theta_m, classical, E, gamma, cost_type)
            fd = (Cp - Cm) / (2 * EPS)
            assert T[ell][k] == pytest.approx(fd, abs=1e-4), f"ell={ell} k={k} R={R} cost={cost_type}"


def test_gamma_zero_vs_one_changes_upstream_gradients():
    depth, E, cost_type = 4, 0, "local"
    theta = _theta_blocks(depth, seed=21)
    classical = init_classical_params(seed=22, depth=depth, n_qubits=N_QUBITS, hidden_dim=N_QUBITS)

    T0, fwd0 = total_gradients_exact(theta, classical, E, 0.0, cost_type, SPECTRUM, N_QUBITS)
    T1, fwd1 = total_gradients_exact(theta, classical, E, 1.0, cost_type, SPECTRUM, N_QUBITS)

    # x^(2) never receives a residual term (needs z^(0), fixed at zero), so it must
    # be identical regardless of gamma.
    assert np.allclose(fwd0.x[2], fwd1.x[2], atol=1e-12)
    # x^(3) = W_2 z^(2) + b_2 + gamma*z^(1) does depend on gamma once z^(1) != 0.
    assert not np.allclose(fwd0.x[3], fwd1.x[3], atol=1e-9)
    # Block 1's gradient must change once the gamma shortcut (feeding x^(3) = ... +
    # gamma*z^(1)) is switched on.
    assert not np.allclose(T0[1], T1[1], atol=1e-9)


def test_gamma_zero_matches_no_residual_reference_path():
    depth, E, cost_type = 3, 1, "global"
    theta = _theta_blocks(depth, seed=31)
    classical = init_classical_params(seed=32, depth=depth, n_qubits=N_QUBITS, hidden_dim=N_QUBITS)
    T_gamma0, fwd0 = total_gradients_exact(theta, classical, E, 0.0, cost_type, SPECTRUM, N_QUBITS)
    # gamma=0 must reproduce the plain non-residual transition x^(ell+1)=W z^(ell)+b_ell
    x2_expected = classical.W[0] @ fwd0.z[1] + classical.b[0]
    assert np.allclose(fwd0.x[2], x2_expected, atol=1e-12)
