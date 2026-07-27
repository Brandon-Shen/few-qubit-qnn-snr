"""Classical residual/non-residual layer (Section 5).

Non-residual transition:  x^(ell+1) = W_ell z^(ell) + b_ell
Residual transition:      x^(ell+1) = W_ell z^(ell) + b_ell + gamma * z^(ell-1)

with z^(0) := 0 (a fixed constant, not a function of any parameter -- see
ASSUMPTIONS.md A3), so the same formula applies uniformly for ell = 1..d-1
(x^(2) has a formally-present but always-zero gamma*z^(0) term when ell=1).

`gamma` is fixed (0 or 1) and non-trainable in the confirmatory design
(Section 5). W and b are matched by seed between the R=0 and R=1 conditions.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ClassicalParams:
    W: list[np.ndarray]  # length depth-1, each (n_qubits, n_qubits)
    b: list[np.ndarray]  # length depth-1, each (n_qubits,)


def init_classical_params(seed: int, depth: int, n_qubits: int, hidden_dim: int,
                           weight_init: str = "glorot_uniform",
                           bias_init: str = "zeros") -> ClassicalParams:
    if hidden_dim != n_qubits:
        raise ValueError(
            "residual.hidden_dim must equal n_qubits: x^(ell) is added elementwise "
            "to the next block's n_qubits Ry angles (ASSUMPTION A15); a differing "
            "hidden width would require an unspecified projection layer."
        )
    n_transitions = max(depth - 1, 0)
    rng = np.random.default_rng(seed)
    W, b = [], []
    for _ in range(n_transitions):
        if weight_init == "glorot_uniform":
            limit = np.sqrt(6.0 / (hidden_dim + n_qubits))
            W_ell = rng.uniform(-limit, limit, size=(hidden_dim, n_qubits))
        elif weight_init == "zeros":
            W_ell = np.zeros((hidden_dim, n_qubits))
        else:
            raise ValueError(f"unknown weight_init: {weight_init}")
        if bias_init == "zeros":
            b_ell = np.zeros(hidden_dim)
        else:
            raise ValueError(f"unknown bias_init: {bias_init}")
        W.append(W_ell)
        b.append(b_ell)
    return ClassicalParams(W=W, b=b)


def initial_x(n_qubits: int, x0_init: str = "zeros") -> np.ndarray:
    if x0_init != "zeros":
        raise ValueError(f"unknown residual.x0_init: {x0_init}")
    return np.zeros(n_qubits)


def next_x(W_ell: np.ndarray, b_ell: np.ndarray, z_ell: np.ndarray, z_prev: np.ndarray,
           gamma: float) -> np.ndarray:
    """x^(ell+1) = W_ell z^(ell) + b_ell + gamma * z^(ell-1)."""
    return W_ell @ z_ell + b_ell + gamma * z_prev
