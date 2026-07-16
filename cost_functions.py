"""Global and local cost functions, and their single-shot variance formulas.

Global cost:  C_global = <psi| H |psi>            (H = TFIM Hamiltonian, not a Pauli -> H^2 != I)
Local cost:   C_local  = <psi| Z0 Z1 |psi>          (Pauli observable -> O^2 = I)

Single-shot variance of a Hermitian observable O in state |psi> is the usual
Var = <O^2> - <O>^2. For a Pauli operator (eigenvalues +-1) this reduces to
1 - <O>^2 exactly, without needing to form O^2. For the Hamiltonian we need
the dense H^2 = H @ H matrix since H is not idempotent.
"""
import numpy as np


def global_cost_and_var(state, H, H2):
    """<H>, Var(single-shot) = <H^2> - <H>^2, computed from a statevector."""
    expval = float(np.real(np.conj(state) @ H @ state))
    exp_sq = float(np.real(np.conj(state) @ H2 @ state))
    var = exp_sq - expval ** 2
    return expval, var


def local_cost_and_var(state, ZZ):
    """<Z0Z1>, Var(single-shot) = 1 - <Z0Z1>^2 (exact, since (Z0Z1)^2 = I)."""
    expval = float(np.real(np.conj(state) @ ZZ @ state))
    var = 1.0 - expval ** 2
    return expval, var


def quantum_cost_and_var(state, cost_type, H=None, H2=None, ZZ=None):
    """Dispatches to global or local cost/variance based on `cost_type`."""
    if cost_type == "global":
        return global_cost_and_var(state, H, H2)
    elif cost_type == "local":
        return local_cost_and_var(state, ZZ)
    else:
        raise ValueError(f"unknown cost_type: {cost_type}")


def _reduce_z(z, reduction):
    """Sum_j z_j ('sum', the pilot's original scale-with-n behavior) or
    (1/n) Sum_j z_j ('mean', n-invariant in scale -- see README "Design choices",
    `residual_reduction`)."""
    s = float(np.sum(z))
    if reduction == "sum":
        return s
    elif reduction == "mean":
        return s / len(z)
    else:
        raise ValueError(f"unknown residual_reduction: {reduction}")


def residual_addition(alpha, block_inputs_z_list, reduction="sum"):
    """Sum_l alpha_l * reduce(<Z_j>_in^(l)), the classical residual-shortcut term
    added to C_quantum to form C_res. `block_inputs_z_list` is a list of length
    L, each entry a length-n_qubits array of <Z_j> values for that block's input.
    `reduction` selects 'sum' (pilot default) or 'mean' (n-invariant) per block.
    """
    return float(sum(a * _reduce_z(z, reduction) for a, z in zip(alpha, block_inputs_z_list)))


def residual_single_shot_var(var_quantum, alpha, block_inputs_z_list, reduction="sum"):
    """Total single-shot variance of C_res = C_quantum + Sum_l alpha_l * reduce(Z_j_in^(l)),
    under the simplifying assumption that the final-cost measurement and every
    intermediate single-qubit measurement are independent (no covariance modeled
    between them, nor between qubits within a block). See README "Design choices".

    'sum'  : Var(single-shot) = Var_quantum + Sum_l alpha_l^2 * Sum_j (1 - <Z_j>_in^(l)^2)
    'mean' : same, but each block's term is divided by n_qubits^2 (Var of an
             average of n independent terms), keeping the residual variance
             contribution n-invariant in scale just like the mean itself.
    """
    def block_var(z):
        v = float(np.sum(1.0 - np.asarray(z) ** 2))
        if reduction == "sum":
            return v
        elif reduction == "mean":
            return v / (len(z) ** 2)
        else:
            raise ValueError(f"unknown residual_reduction: {reduction}")

    residual_var = sum((a ** 2) * block_var(z) for a, z in zip(alpha, block_inputs_z_list))
    return var_quantum + residual_var
