"""Gradient signal-to-noise ratio (SNR) estimation.

SNR_i = |E[d C / d theta_i]| / sqrt(Var_shots[d C / d theta_i])

Two distinct parameter families are handled by two distinct code paths, and
they are never mixed:

  * theta_i (rotation angles, inside quantum gates): the *exact* gradient is
    obtained via the analytic parameter-shift rule, C(theta_i + pi/2) minus
    C(theta_i - pi/2), evaluated on noiseless statevectors. When residual
    connections are active, C here is the *full* C_res (quantum cost plus the
    residual shortcut sum), since C_res depends on theta_i through every
    block whose input state is downstream of theta_i's layer -- so the
    shifted circuits must also carry their own residual-block snapshots.

  * alpha_l (classical residual weights, outside any gate): C_res is exactly
    linear in alpha_l, so d C_res / d alpha_l = Sum_j <Z_j>_in^(l) is read off
    a *single* unshifted circuit evaluation -- no parameter shift, no
    additional circuit executions. alpha_l must never be fed into the
    parameter-shift branch above (there is no gate to shift).

Shot-noise variance is derived analytically (never resampled): for a
parameter-shift gradient g = (M+ - M-)/2 built from two independent shot-
averaged means over N shots each, Var[g] = (Var(M+) + Var(M-)) / 4, with
Var(M+/-) = Var(single-shot)+/- / N.

Deterministic parameters (companion-paper phase). A parameter whose shot-noise
variance (var_shots) is exactly zero at the point being evaluated -- e.g.
alpha_1 when block 1's input is the fixed |0...0> state (every <Z_j> = 1
exactly, zero variance), or a theta_i outside a local cost's support (the
no-signaling argument already used in the pilot) -- is a genuine physical
"no measurement noise in this direction" case, not a numerical failure.
Floating-point roundoff means this can land at ~1e-15 rather than exactly
0.0, so the classification uses a fixed tolerance `_DETERMINISTIC_VAR_TOL`
rather than an exact-zero test: this also fixes a latent bug where such
near-zero-but-nonzero variances produced a huge *finite* SNR (grad/sqrt(1e-15))
that silently polluted the mean/median instead of being excluded alongside
the genuinely infinite cases.
"""
import numpy as np

from ansatze import build_snapshot_circuit, block_inputs_z, n_theta_params
from cost_functions import quantum_cost_and_var, residual_addition, residual_single_shot_var

_VAR_FLOOR = 0.0  # analytic variances are >= 0; clip tiny float roundoff noise
_DETERMINISTIC_VAR_TOL = 1e-12  # var_shots at/below this -> deterministic (see module docstring)


def init_params(seed, L, n_qubits, include_residual, low=0.0, high=2 * np.pi):
    """Draws theta ~ U[low, high) first, then (if applicable) alpha ~ U[low, high)
    from the *same* RNG stream continuing right after theta. This guarantees
    that for a given seed, theta is bit-identical across every configuration
    (residual or not) -- required for the paired seed-level design used by the
    Wilcoxon signed-rank comparisons in analysis.py.
    """
    rng = np.random.default_rng(seed)
    theta = rng.uniform(low, high, size=n_qubits * L)
    alpha = rng.uniform(low, high, size=L) if include_residual else np.zeros(0)
    return theta, alpha


def _theta_gradient_snr(run_circuit, theta, alpha, i, L, n_qubits, cost_type,
                         H, H2, ZZ, include_residual, N_shots, residual_reduction="sum"):
    theta_p = theta.copy()
    theta_p[i] += np.pi / 2
    theta_m = theta.copy()
    theta_m[i] -= np.pi / 2

    snap_p = run_circuit(theta_p)
    snap_m = run_circuit(theta_m)
    state_p, state_m = snap_p["execution_results"], snap_m["execution_results"]

    Cq_p, Varq_p = quantum_cost_and_var(state_p, cost_type, H, H2, ZZ)
    Cq_m, Varq_m = quantum_cost_and_var(state_m, cost_type, H, H2, ZZ)

    if include_residual:
        zs_p = block_inputs_z(snap_p, L, n_qubits)
        zs_m = block_inputs_z(snap_m, L, n_qubits)
        C_p = Cq_p + residual_addition(alpha, zs_p, residual_reduction)
        C_m = Cq_m + residual_addition(alpha, zs_m, residual_reduction)
        var_single_p = residual_single_shot_var(Varq_p, alpha, zs_p, residual_reduction)
        var_single_m = residual_single_shot_var(Varq_m, alpha, zs_m, residual_reduction)
    else:
        C_p, C_m = Cq_p, Cq_m
        var_single_p, var_single_m = Varq_p, Varq_m

    grad = (C_p - C_m) / 2.0
    var_shots = (var_single_p / N_shots + var_single_m / N_shots) / 4.0
    return grad, max(var_shots, _VAR_FLOOR)


def _alpha_gradient_snr(zs0, l_idx, N_shots, residual_reduction="sum"):
    z = zs0[l_idx]
    if residual_reduction == "sum":
        grad = float(np.sum(z))
        var_shots = (1.0 / N_shots) * float(np.sum(1.0 - z ** 2))
    elif residual_reduction == "mean":
        grad = float(np.sum(z)) / len(z)
        var_shots = (1.0 / N_shots) * float(np.sum(1.0 - z ** 2)) / (len(z) ** 2)
    else:
        raise ValueError(f"unknown residual_reduction: {residual_reduction}")
    return grad, max(var_shots, _VAR_FLOOR)


def snr_from_grad_var(grad, var_shots, tol=_DETERMINISTIC_VAR_TOL):
    """Returns (snr, is_deterministic). `var_shots <= tol` is treated as a
    deterministic direction (see module docstring): SNR is reported as inf
    (nonzero gradient) or nan (both zero) for the raw record, but callers
    should exclude `is_deterministic` parameters from aggregate statistics
    rather than relying on `np.isfinite` alone, since floating-point roundoff
    can leave var_shots at a tiny nonzero value instead of exactly 0.0.
    """
    if var_shots <= tol:
        snr = float("inf") if abs(grad) > 0.0 else float("nan")
        return snr, True
    return abs(grad) / np.sqrt(var_shots), False


def compute_snr_for_initialization(theta, alpha, L, n_qubits, entanglement, cost_type,
                                    include_residual, H, H2, ZZ, N_shots=1000,
                                    run_circuit=None, residual_reduction="sum"):
    """Computes per-parameter gradients and SNRs for one (theta, alpha) draw.

    Returns (grads, snrs, labels, deterministic): each an array/list of length
    P_theta (+ L if include_residual), ordered theta_0..theta_{P-1} then
    (if present) alpha_0..alpha_{L-1}. `deterministic[i]` is True iff that
    parameter's shot-noise variance is at/below `_DETERMINISTIC_VAR_TOL`.
    """
    if run_circuit is None:
        run_circuit = build_snapshot_circuit(n_qubits, L, entanglement)

    P_theta = n_theta_params(n_qubits, L)
    n_params = P_theta + (L if include_residual else 0)
    grads = np.empty(n_params)
    snrs = np.empty(n_params)
    deterministic = np.zeros(n_params, dtype=bool)
    labels = [f"theta_{i}" for i in range(P_theta)]

    for i in range(P_theta):
        g, v = _theta_gradient_snr(run_circuit, theta, alpha, i, L, n_qubits, cost_type,
                                    H, H2, ZZ, include_residual, N_shots, residual_reduction)
        grads[i] = g
        snrs[i], deterministic[i] = snr_from_grad_var(g, v)

    if include_residual:
        snap0 = run_circuit(theta)
        zs0 = block_inputs_z(snap0, L, n_qubits)
        for l in range(L):
            g, v = _alpha_gradient_snr(zs0, l, N_shots, residual_reduction)
            grads[P_theta + l] = g
            snrs[P_theta + l], deterministic[P_theta + l] = snr_from_grad_var(g, v)
        labels += [f"alpha_{l}" for l in range(L)]

    return grads, snrs, labels, deterministic
