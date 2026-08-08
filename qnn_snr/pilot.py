"""Pilot precision utilities (Section 17). Both utilities operate on data
explicitly labeled `pilot_or_confirmatory="pilot"` and excluded from the
confirmatory dataset by construction (a separate seed stream and a separate
`generate_pilot_shot_rows` entry point, never reused by `generate-exact` /
`generate-shots`).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qnn_snr.config import CONFIGURATION_TABLE, ExperimentConfig
from qnn_snr.hamiltonian import diagonalize_tfim
from qnn_snr.gradients import total_gradients_finite_shot
from qnn_snr.replicate import draw_theta_blocks, depth_standardization
from qnn_snr.residual import init_classical_params
from qnn_snr.seeds import derive_seed
from qnn_snr.stats.pointwise import pointwise_statistics


def _pilot_replicate_gradients(cfg: ExperimentConfig, config_id: int, depth: int, budget: int,
                                mode: str, R: int) -> np.ndarray:
    """One fixed pilot initialization (init_id='pilot0'), R independent
    finite-shot replicates of the FIRST block's first parameter's total
    gradient -- a cheap, representative pointwise cell used purely to choose
    R, never merged into the confirmatory dataset."""
    spectrum = diagonalize_tfim(cfg.task.n_qubits, cfg.task.J, cfg.task.h)
    theta_seed = derive_seed(cfg.seed_root, "pilot_init_theta", depth)
    classical_seed = derive_seed(cfg.seed_root, "pilot_init_classical", depth)
    theta_blocks = draw_theta_blocks(theta_seed, depth, cfg.task.n_qubits, cfg.circuit.init_low, cfg.circuit.init_high)
    classical = init_classical_params(classical_seed, depth, cfg.task.n_qubits, cfg.resolved_hidden_dim(),
                                       cfg.residual.weight_init, cfg.residual.bias_init)
    E, L, R_flag = CONFIGURATION_TABLE[config_id]
    gamma = cfg.gamma_for(R_flag)
    cost_type = cfg.cost_type_for(L)

    grads = np.empty(R)
    for r in range(R):
        shot_seed = derive_seed(cfg.seed_root, "pilot_shots", config_id, depth, budget, mode, r)
        rng = np.random.default_rng(shot_seed)
        T_hat, _, _, _ = total_gradients_finite_shot(theta_blocks, classical, E, gamma, cost_type, spectrum,
                                                       cfg.task.n_qubits, mode, budget, rng, cfg.residual.x0_init)
        grads[r] = T_hat[1][0]
    return grads


def _bootstrap_halfwidth(values: np.ndarray, rng: np.random.Generator, n_boot: int = 500,
                          alpha: float = 0.05) -> float:
    n = len(values)
    idx = rng.integers(0, n, size=(n_boot, n))
    boot_means = values[idx].mean(axis=1)
    lo, hi = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float((hi - lo) / 2)


def select_replicate_count(cfg: ExperimentConfig, mode: str = "finite_shot_end_to_end",
                            seed: int = 2024) -> dict:
    """Section 17.A: increase R from `pilot.replicate_count.start_R` in
    configured increments until the bootstrap CI half-width for the signed
    mean AND for pointwise SNR meets the configured tolerance and remains
    stable after the next increment, evaluated across the prespecified
    representative cells."""
    spec = cfg.pilot.replicate_count
    rng = np.random.default_rng(seed)
    per_cell_results = []
    selected_Rs = []

    for cell in spec.representative_cells:
        config_id, depth, budget = cell["configuration_id"], cell["depth"], cell["budget"]
        R = spec.start_R
        history = []
        selected_R = None
        while R <= spec.max_R:
            grads = _pilot_replicate_gradients(cfg, config_id, depth, budget, mode, R)
            mean_hw = _bootstrap_halfwidth(grads, rng)
            sd = grads.std(ddof=1) if len(grads) > 1 else float("nan")
            snr = abs(grads.mean()) / sd if sd > 0 else float("inf")
            # crude SNR half-width via bootstrap of the SNR statistic itself
            n = len(grads)
            idx = rng.integers(0, n, size=(300, n))
            boot_snr = np.abs(grads[idx].mean(axis=1)) / grads[idx].std(axis=1, ddof=1)
            boot_snr = boot_snr[np.isfinite(boot_snr)]
            snr_hw = float((np.percentile(boot_snr, 97.5) - np.percentile(boot_snr, 2.5)) / 2) if len(boot_snr) else float("nan")

            history.append({"R": R, "mean_halfwidth": mean_hw, "snr_halfwidth": snr_hw})
            meets_tol = (mean_hw <= spec.abs_halfwidth_tolerance) and (
                not np.isfinite(snr_hw) or snr_hw <= spec.abs_halfwidth_tolerance * 5)
            if meets_tol and len(history) >= 2:
                prev = history[-2]
                stable = abs(prev["mean_halfwidth"] - mean_hw) <= spec.rel_halfwidth_tolerance * mean_hw + 1e-9
                if stable:
                    selected_R = R
                    break
            R += spec.increment
        per_cell_results.append({"configuration_id": config_id, "depth": depth, "budget": budget,
                                  "selected_R": selected_R, "history": history})
        selected_Rs.append(selected_R or spec.max_R)

    return {
        "selected_R_overall": int(max(selected_Rs)),
        "per_cell": per_cell_results,
        "note": "pilot data used for this selection are excluded from the confirmatory dataset by construction",
    }


def select_initialization_count(cfg: ExperimentConfig, h1_pilot_result, h2h4_pilot_result,
                                 seed: int = 4242) -> dict:
    """Section 17.B: using variance components estimated from independent
    pilot data, simulate complete factorial datasets for candidate
    initialization counts and select the smallest count whose simulated 95%
    CI half-width 90th percentile is <= 0.20 for each of the three H2--H4
    finite-shot interaction coefficients on the asinh(SNR_est) scale.

    H1 is not part of this implemented selection rule; this documentation
    correction does not alter the frozen computation.
    """
    from qnn_snr.stats.models import H2_H4_FORMULA, fit_mixed_model

    spec = cfg.pilot.initialization_count
    rng = np.random.default_rng(seed)

    group_var = h2h4_pilot_result.random_effect_variances.get("group_intercept_var", 0.1)
    nested_var = h2h4_pilot_result.random_effect_variances.get("nested_param_var", 0.1)
    resid_sd = h2h4_pilot_result.residual_diagnostics.get("resid_sd", 0.3)
    group_var = group_var if np.isfinite(group_var) and group_var > 0 else 0.05
    nested_var = nested_var if np.isfinite(nested_var) and nested_var > 0 else 0.05
    resid_sd = resid_sd if np.isfinite(resid_sd) and resid_sd > 0 else 0.3

    true_coefs = {"E:L": h2h4_pilot_result.params.get("E:L", 0.0),
                  "E:R": h2h4_pilot_result.params.get("E:R", 0.0),
                  "L:R:depth_z": h2h4_pilot_result.params.get("L:R:depth_z", 0.0)}

    depths = cfg.circuit.depths
    depth_mean, depth_std = depth_standardization(depths)
    n_sim_datasets = 20  # per candidate count, to build the half-width distribution

    results = []
    n_candidate = spec.start_n
    achieved = None
    while n_candidate <= spec.max_n:
        halfwidths = {c: [] for c in ("E:L", "E:R", "L:R:depth_z")}
        for _ in range(n_sim_datasets):
            rows = []
            for init_id in range(n_candidate):
                u_init = rng.normal(0, np.sqrt(group_var))
                for depth in depths:
                    depth_z = (depth - depth_mean) / depth_std if depth_std > 0 else 0.0
                    u_param = rng.normal(0, np.sqrt(nested_var))
                    for config_id, (E, L, R) in CONFIGURATION_TABLE.items():
                        mu = (true_coefs["E:L"] * E * L + true_coefs["E:R"] * E * R
                              + true_coefs["L:R:depth_z"] * L * R * depth_z)
                        y = mu + u_init + u_param + rng.normal(0, resid_sd)
                        rows.append({"initialization_id": init_id, "depth": depth, "depth_z": depth_z,
                                     "log2_budget": 10.0, "E": float(E), "L": float(L), "R": float(R),
                                     "parameter_id": "p0", "y": y})
            df = pd.DataFrame(rows)
            result = fit_mixed_model(H2_H4_FORMULA, df, "y")
            if result.error is not None or not result.converged:
                continue
            for coef in halfwidths:
                if coef in result.bse and np.isfinite(result.bse[coef]):
                    halfwidths[coef].append(1.96 * result.bse[coef])

        p90 = {c: (float(np.percentile(v, 90)) if len(v) else float("inf")) for c, v in halfwidths.items()}
        meets = all(p90[c] <= 0.20 for c in p90)
        results.append({"n": n_candidate, "p90_halfwidth": p90, "meets_target": meets})
        if meets and achieved is None:
            achieved = n_candidate
            break
        n_candidate += spec.increment

    return {
        "selected_n": achieved,
        "candidates": results,
        "assumptions": {"group_var": group_var, "nested_var": nested_var, "resid_sd": resid_sd,
                         "true_coefs_from_pilot": true_coefs},
        "note": "pilot initializations used to estimate variance components are excluded from the confirmatory dataset",
    }
