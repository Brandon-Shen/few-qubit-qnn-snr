"""Replicate generation orchestration (Phase 2): builds the tidy row set for
`statevector_exact` (Section 10's exact-signal input) and for the two
finite-shot modes (Section 11's estimator-SNR input), matched across all 8
configurations and every (initialization, depth) cell.

ASSUMPTION A17: each (initialization_id, depth) cell draws its own
independent theta/W/b seed (not a depth-nested prefix of a longer draw); the
seed depends only on (seed_root, initialization_id, depth), never on
(E, L, R), so theta and the classical parameters are bit-identical across all
8 configurations for a given cell (Section 2's "matched initialization"
requirement).

ASSUMPTION A18: `depth_centered`/`depth_z` are standardized against the
*design's* distinct nominal depth levels (`config.circuit.depths`, unweighted
by replicate count), not a per-row empirical mean/std, so the transform is
fixed by the config alone and identical for every row (Section 10: "using
values calculated from the complete confirmatory design").

ASSUMPTION A19: `statevector_exact` rows are not shot-budget-dependent; they
carry the sentinel `budget=0` / `log2_budget=nan` and a single
`replicate_id=0` (the mode is fully deterministic given the matched
initialization).
"""
from __future__ import annotations

import math

import numpy as np

from qnn_snr.budget import resource_accounting
from qnn_snr.config import CONFIGURATION_TABLE, ExperimentConfig, config_hash
from qnn_snr.gradients import total_gradients_exact, total_gradients_finite_shot
from qnn_snr.hamiltonian import TFIMSpectrum, diagonalize_tfim
from qnn_snr.residual import ClassicalParams, init_classical_params
from qnn_snr.seeds import derive_seed

QUANTUM_FRAMEWORK = "pennylane"
SIMULATOR_BACKEND = "default.qubit"


def _software_version() -> str:
    import pennylane

    return f"pennylane=={pennylane.__version__}"


def draw_theta_blocks(seed: int, depth: int, n_qubits: int, low: float, high: float) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    return [rng.uniform(low, high, size=n_qubits) for _ in range(depth)]


def depth_standardization(depths: list[int]) -> tuple[float, float]:
    arr = np.array(sorted(set(depths)), dtype=float)
    mean = float(arr.mean())
    std = float(arr.std(ddof=0))
    return mean, std


def _base_row(cfg: ExperimentConfig, experiment_id: str, git_commit: str, analysis_mode: str,
              config_id: int, E: int, L: int, R: int, gamma: float, cost_type: str,
              depth: int, depth_mean: float, depth_std: float, budget, init_id: int,
              init_seed: int, parameter_index: int, block_index: int, qubit_index: int,
              replicate_id: int, gradient_hat: float, exact_gradient: float, total_shots: int,
              total_circuit_evaluations: int) -> dict:
    depth_centered = depth - depth_mean
    depth_z = depth_centered / depth_std if depth_std > 0 else 0.0
    log2_budget = math.log2(budget) if budget and budget > 0 else float("nan")
    return {
        "experiment_id": experiment_id,
        "analysis_mode": analysis_mode,
        "pilot_or_confirmatory": "confirmatory",
        "configuration_id": config_id,
        "E": E,
        "L": L,
        "R": R,
        "depth": depth,
        "depth_centered": depth_centered,
        "depth_z": depth_z,
        "budget": budget if budget else 0,
        "log2_budget": log2_budget,
        "initialization_id": init_id,
        "initialization_seed": init_seed,
        "parameter_id": f"theta_ell{block_index}_q{qubit_index}",
        "parameter_index": parameter_index,
        "block_index": block_index,
        "qubit_index": qubit_index,
        "replicate_id": replicate_id,
        "gradient_hat": gradient_hat,
        "exact_gradient": exact_gradient,
        "cost_type": cost_type,
        "gamma": gamma,
        "total_shots": total_shots,
        "total_circuit_evaluations": total_circuit_evaluations,
        "quantum_framework": QUANTUM_FRAMEWORK,
        "simulator_backend": SIMULATOR_BACKEND,
        "software_version": _software_version(),
        "git_commit": git_commit,
        "config_hash": config_hash(cfg),
    }


def generate_exact_rows(cfg: ExperimentConfig, git_commit: str = "unknown") -> list[dict]:
    spectrum = diagonalize_tfim(cfg.task.n_qubits, cfg.task.J, cfg.task.h)
    depth_mean, depth_std = depth_standardization(cfg.circuit.depths)
    experiment_id = f"{cfg.name}_{config_hash(cfg)}"
    rows: list[dict] = []

    for depth in cfg.circuit.depths:
        for init_id in range(cfg.design.n_initializations):
            theta_seed = derive_seed(cfg.seed_root, "init_theta", init_id, depth)
            classical_seed = derive_seed(cfg.seed_root, "init_classical", init_id, depth)
            theta_blocks = draw_theta_blocks(theta_seed, depth, cfg.task.n_qubits,
                                              cfg.circuit.init_low, cfg.circuit.init_high)
            classical = init_classical_params(classical_seed, depth, cfg.task.n_qubits,
                                               cfg.resolved_hidden_dim(),
                                               cfg.residual.weight_init, cfg.residual.bias_init)
            for config_id in cfg.design.configurations:
                E, L, R = CONFIGURATION_TABLE[config_id]
                gamma = cfg.gamma_for(R)
                cost_type = cfg.cost_type_for(L)
                T, fwd = total_gradients_exact(theta_blocks, classical, E, gamma, cost_type,
                                                spectrum, cfg.task.n_qubits, cfg.residual.x0_init)
                for ell in range(1, depth + 1):
                    for k in range(cfg.task.n_qubits):
                        param_index = (ell - 1) * cfg.task.n_qubits + k
                        rows.append(_base_row(
                            cfg, experiment_id, git_commit, "statevector_exact",
                            config_id, E, L, R, gamma, cost_type, depth, depth_mean, depth_std,
                            budget=0, init_id=init_id, init_seed=theta_seed,
                            parameter_index=param_index, block_index=ell, qubit_index=k,
                            replicate_id=0, gradient_hat=float(T[ell][k]), exact_gradient=float(T[ell][k]),
                            total_shots=0, total_circuit_evaluations=0,
                        ))
    return rows


def generate_shot_rows(cfg: ExperimentConfig, mode: str, git_commit: str = "unknown") -> list[dict]:
    if mode not in ("finite_shot_conditional", "finite_shot_end_to_end"):
        raise ValueError(f"unsupported mode for generate_shot_rows: {mode}")

    spectrum = diagonalize_tfim(cfg.task.n_qubits, cfg.task.J, cfg.task.h)
    depth_mean, depth_std = depth_standardization(cfg.circuit.depths)
    experiment_id = f"{cfg.name}_{config_hash(cfg)}"
    rows: list[dict] = []

    for depth in cfg.circuit.depths:
        for init_id in range(cfg.design.n_initializations):
            theta_seed = derive_seed(cfg.seed_root, "init_theta", init_id, depth)
            classical_seed = derive_seed(cfg.seed_root, "init_classical", init_id, depth)
            theta_blocks = draw_theta_blocks(theta_seed, depth, cfg.task.n_qubits,
                                              cfg.circuit.init_low, cfg.circuit.init_high)
            classical = init_classical_params(classical_seed, depth, cfg.task.n_qubits,
                                               cfg.resolved_hidden_dim(),
                                               cfg.residual.weight_init, cfg.residual.bias_init)
            for config_id in cfg.design.configurations:
                E, L, R = CONFIGURATION_TABLE[config_id]
                gamma = cfg.gamma_for(R)
                cost_type = cfg.cost_type_for(L)
                T_exact, _ = total_gradients_exact(theta_blocks, classical, E, gamma, cost_type,
                                                    spectrum, cfg.task.n_qubits, cfg.residual.x0_init)
                for budget_B in cfg.budget.values:
                    for replicate_id in range(cfg.design.replicates):
                        shot_seed = derive_seed(cfg.seed_root, "shots", init_id, depth, config_id,
                                                 mode, budget_B, replicate_id)
                        rng = np.random.default_rng(shot_seed)
                        T_hat, _, jobs, allocation = total_gradients_finite_shot(
                            theta_blocks, classical, E, gamma, cost_type, spectrum,
                            cfg.task.n_qubits, mode, budget_B, rng, cfg.residual.x0_init,
                        )
                        resource = resource_accounting(budget_B, jobs, allocation)
                        for ell in range(1, depth + 1):
                            for k in range(cfg.task.n_qubits):
                                param_index = (ell - 1) * cfg.task.n_qubits + k
                                rows.append(_base_row(
                                    cfg, experiment_id, git_commit, mode,
                                    config_id, E, L, R, gamma, cost_type, depth, depth_mean, depth_std,
                                    budget=budget_B, init_id=init_id, init_seed=theta_seed,
                                    parameter_index=param_index, block_index=ell, qubit_index=k,
                                    replicate_id=replicate_id, gradient_hat=float(T_hat[ell][k]),
                                    exact_gradient=float(T_exact[ell][k]),
                                    total_shots=resource.total_allocated_shots,
                                    total_circuit_evaluations=resource.total_quantum_evaluations,
                                ))
    return rows
