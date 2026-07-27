"""Descriptive/secondary per-(configuration, depth, budget) statistics
(Section 15) and the physics quantities (final energy, global fidelity,
entanglement diagnostics) that Section 3/4 require reported for every
configuration regardless of which cost drove gradients."""
from __future__ import annotations

import numpy as np
import pandas as pd

from qnn_snr.circuits import entanglement_diagnostics
from qnn_snr.config import CONFIGURATION_TABLE, ExperimentConfig
from qnn_snr.costs import evaluate_both_costs
from qnn_snr.gradients import forward_pass_exact
from qnn_snr.hamiltonian import diagonalize_tfim
from qnn_snr.replicate import draw_theta_blocks, depth_standardization
from qnn_snr.residual import init_classical_params
from qnn_snr.seeds import derive_seed


def physics_summary_rows(cfg: ExperimentConfig) -> list[dict]:
    spectrum = diagonalize_tfim(cfg.task.n_qubits, cfg.task.J, cfg.task.h)
    rows = []
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
                fwd = forward_pass_exact(theta_blocks, classical, E, gamma, cost_type, spectrum,
                                          cfg.task.n_qubits, cfg.residual.x0_init)
                both = evaluate_both_costs(fwd.final_state, spectrum)
                diags = entanglement_diagnostics(fwd.final_state, cfg.task.n_qubits)
                rows.append({
                    "configuration_id": config_id, "E": E, "L": L, "R": R, "depth": depth,
                    "initialization_id": init_id,
                    "final_tfim_energy": both["final_tfim_energy"],
                    "global_fidelity": both["global_fidelity"],
                    "mean_entanglement_entropy": float(np.mean([d.von_neumann_entropy for d in diags])),
                    "mean_purity": float(np.mean([d.purity for d in diags])),
                })
    return rows


def configuration_summaries(pointwise_df: pd.DataFrame, exact_df: pd.DataFrame,
                             physics_df: pd.DataFrame, resource_df: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = []
    group_keys = pointwise_df[["configuration_id", "depth", "budget"]].drop_duplicates().itertuples(index=False)
    for config_id, depth, budget in group_keys:
        cell = pointwise_df[(pointwise_df["configuration_id"] == config_id) &
                             (pointwise_df["depth"] == depth) & (pointwise_df["budget"] == budget)]
        snr = cell["SNR_est"].to_numpy()
        finite_snr = snr[np.isfinite(snr)]
        exact_cell = exact_df[(exact_df["configuration_id"] == config_id) & (exact_df["depth"] == depth)]
        exact_by_init = exact_cell.groupby("initialization_id")["exact_gradient"].apply(lambda s: np.abs(s).mean())
        physics_cell = physics_df[(physics_df["configuration_id"] == config_id) & (physics_df["depth"] == depth)]

        row = {
            "configuration_id": config_id, "depth": depth, "budget": budget,
            "median_SNR_est": float(np.median(finite_snr)) if len(finite_snr) else float("nan"),
            "iqr_SNR_est": float(np.subtract(*np.percentile(finite_snr, [75, 25]))) if len(finite_snr) else float("nan"),
            "rms_SNR_est": float(np.sqrt(np.mean(finite_snr ** 2))) if len(finite_snr) else float("nan"),
            "fraction_SNR_est_geq_1": float(np.mean(finite_snr >= 1)) if len(finite_snr) else float("nan"),
            "fraction_ci_excludes_zero": float(cell["signed_mean_ci_excludes_zero"].mean()) if len(cell) else float("nan"),
            "median_SNR_exact": float(np.median(cell["SNR_exact"][np.isfinite(cell["SNR_exact"])])) if len(cell) else float("nan"),
            "median_absolute_bias": float(cell["absolute_bias"].median()) if len(cell) else float("nan"),
            "iqr_absolute_bias": float(np.subtract(*np.percentile(cell["absolute_bias"], [75, 25]))) if len(cell) else float("nan"),
            "sign_agreement_fraction": float(cell["sign_agreement"].mean()) if len(cell) else float("nan"),
            "rms_exact_gradient_magnitude": float(np.sqrt(np.mean(exact_cell["exact_gradient"].to_numpy() ** 2))) if len(exact_cell) else float("nan"),
            "exact_gradient_landscape_variance_across_inits": float(exact_by_init.var(ddof=1)) if len(exact_by_init) > 1 else float("nan"),
            "final_tfim_energy_mean": float(physics_cell["final_tfim_energy"].mean()) if len(physics_cell) else float("nan"),
            "global_fidelity_mean": float(physics_cell["global_fidelity"].mean()) if len(physics_cell) else float("nan"),
            "mean_entanglement_entropy": float(physics_cell["mean_entanglement_entropy"].mean()) if len(physics_cell) else float("nan"),
            "mean_purity": float(physics_cell["mean_purity"].mean()) if len(physics_cell) else float("nan"),
            "n_matched_observations": int(len(cell)),
        }
        if resource_df is not None:
            rcell = resource_df[(resource_df["configuration_id"] == config_id) &
                                 (resource_df["depth"] == depth) & (resource_df["budget"] == budget)]
            row["total_circuit_evaluations_mean"] = float(rcell["total_circuit_evaluations_mean"].mean()) if len(rcell) else float("nan")
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["configuration_id", "depth", "budget"]).reset_index(drop=True)


def resource_accounting_table(raw_shot_df: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["analysis_mode", "configuration_id", "depth", "budget"]
    agg = raw_shot_df.groupby(group_cols).agg(
        total_shots_mean=("total_shots", "mean"),
        total_circuit_evaluations_mean=("total_circuit_evaluations", "mean"),
        n_rows=("total_shots", "size"),
    ).reset_index()
    return agg
