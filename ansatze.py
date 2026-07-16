"""Ansatz circuit builders: baseline HEA, constrained-entanglement ("brick-layer"),
and the mid-circuit snapshot plumbing needed for residual connections.

All ansätze share the same per-layer structure: a layer of Ry(theta) on every
qubit followed by an entangling layer of CNOTs. What differs between
'full' (baseline) and 'brick' (constrained entanglement, design choice A) is
only which CNOTs are applied in each layer -- the parameter count (L * n_qubits
Ry angles) is identical between the two, as required by the spec.

Residual connections (design choice C) need the statevector immediately
*before* each block's gates are applied (z_in^(l) for l = 1..L). We use
PennyLane's qml.Snapshot()/qml.snapshots() machinery to capture these
intermediate statevectors within a single circuit evaluation, then compute
single-qubit Z expectation values from them classically in numpy. Block 1's
"input" is simply the initial |0000> state.
"""
import numpy as np
import pennylane as qml


def entangling_pairs(layer_idx, n_qubits, entanglement):
    """Returns list of (control, target) CNOT pairs for layer `layer_idx` (0-indexed).

    'full'  : linear-chain CNOT(i, i+1) for i in 0..n_qubits-2, every layer
              (volume-law-scaling baseline / HEA entanglement).
    'brick' : alternating brick pattern, fixed for n_qubits == 4:
              odd layers (1-indexed: 1, 3, 5, ...) -> CNOT(0,1), CNOT(2,3)
              even layers (1-indexed: 2, 4, 6, ...) -> CNOT(1,2)
              (boundary/area-law-scaling entanglement growth).
    """
    if entanglement == "full":
        return [(i, i + 1) for i in range(n_qubits - 1)]
    elif entanglement == "brick":
        if n_qubits != 4:
            raise NotImplementedError("brick pattern is specified for n_qubits == 4 only")
        layer_num = layer_idx + 1  # 1-indexed, matches spec wording
        if layer_num % 2 == 1:
            return [(0, 1), (2, 3)]
        else:
            return [(1, 2)]
    else:
        raise ValueError(f"unknown entanglement pattern: {entanglement}")


def n_theta_params(n_qubits, L):
    return n_qubits * L


def build_snapshot_circuit(n_qubits, L, entanglement):
    """Returns a callable `run(theta) -> dict` where the dict has keys
    'block_1_input', ..., 'block_L_input' (statevectors just before each
    block's gates) and 'execution_results' (final statevector).

    theta has shape (n_qubits * L,) and is reshaped internally to (L, n_qubits).
    """
    dev = qml.device("default.qubit", wires=n_qubits)

    @qml.qnode(dev, interface=None)
    def circuit(theta):
        theta_grid = qml.math.reshape(theta, (L, n_qubits))
        for l in range(L):
            qml.Snapshot(f"block_{l + 1}_input")
            for q in range(n_qubits):
                qml.RY(theta_grid[l, q], wires=q)
            for (a, b) in entangling_pairs(l, n_qubits, entanglement):
                qml.CNOT(wires=[a, b])
        return qml.state()

    snapshot_circuit = qml.snapshots(circuit)

    def run(theta):
        theta = np.asarray(theta, dtype=float)
        return snapshot_circuit(theta)

    return run


def z_expectation_per_qubit(state, n_qubits):
    """Single-qubit <Z_j> expectation values for every qubit, computed directly
    from a statevector's amplitudes (marginal probabilities per wire axis).
    """
    probs = (np.abs(state) ** 2).reshape([2] * n_qubits)
    z_vals = np.empty(n_qubits)
    for k in range(n_qubits):
        other_axes = tuple(i for i in range(n_qubits) if i != k)
        marg = probs.sum(axis=other_axes) if other_axes else probs
        z_vals[k] = marg[0] - marg[1]
    return z_vals


def block_inputs_z(snapshots, L, n_qubits):
    """Extracts z_in^(l) = [<Z0>,...,<Z_{n-1}>] for l = 1..L from a snapshot dict."""
    return [
        z_expectation_per_qubit(snapshots[f"block_{l}_input"], n_qubits)
        for l in range(1, L + 1)
    ]
