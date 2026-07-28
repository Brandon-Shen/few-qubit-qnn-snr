"""Task 1 verification script: finite-difference cross-check of the H1
exact-gradient chain-rule assembly (`total_gradients_exact` in
qnn_snr/gradients.py) against direct central finite differences on the full
hybrid cost, for a small targeted set of matched initial-parameter points
pulled from the confirmatory design (configs/confirmatory.yaml).

Not part of the pipeline; run standalone from the repo root:
    python verification/h1_finite_difference_check.py

Writes:
    verification/h1_fd_check_full_table.csv   (every point x parameter x h)
    verification/h1_fd_check_EL_contrast.csv  (the E x L slope comparison)
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from qnn_snr.config import CONFIGURATION_TABLE, load_config
from qnn_snr.gradients import forward_pass_exact, total_gradients_exact
from qnn_snr.hamiltonian import diagonalize_tfim
from qnn_snr.replicate import draw_theta_blocks
from qnn_snr.residual import init_classical_params
from qnn_snr.seeds import derive_seed

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "configs" / "confirmatory.yaml"

H_VALUES = [1e-3, 1e-4, 1e-5]
DEPTHS = [1, 6]
INIT_IDS = [0, 1]
CONFIG_IDS = [1, 2, 3, 5]  # baseline, E only, L only, E+L -- the R=0 quadrant, matching the E x L contrast under test
REL_ERR_FLOOR = 1e-8
REL_ERR_TOLERANCE = 1e-6  # at h=1e-5, double-precision statevector sim; see writeup for justification


def cost_fn(theta_blocks, classical, E, gamma, cost_type, spectrum, n_qubits, x0_init):
    return forward_pass_exact(theta_blocks, classical, E, gamma, cost_type, spectrum, n_qubits, x0_init).cost


def central_fd(theta_blocks, classical, E, gamma, cost_type, spectrum, n_qubits, x0_init,
                block_index_1based, qubit_index, h):
    """(C(theta+h e_k) - C(theta-h e_k)) / (2h) on the FULL hybrid cost, re-running
    the entire forward pass (all downstream blocks, all re-encoding) for each shift."""
    plus = [b.copy() for b in theta_blocks]
    minus = [b.copy() for b in theta_blocks]
    plus[block_index_1based - 1][qubit_index] += h
    minus[block_index_1based - 1][qubit_index] -= h
    Cp = cost_fn(plus, classical, E, gamma, cost_type, spectrum, n_qubits, x0_init)
    Cm = cost_fn(minus, classical, E, gamma, cost_type, spectrum, n_qubits, x0_init)
    return (Cp - Cm) / (2 * h)


def main():
    cfg = load_config(CONFIG_PATH)
    n_qubits = cfg.task.n_qubits
    spectrum = diagonalize_tfim(n_qubits, cfg.task.J, cfg.task.h)

    points = list(itertools.product(DEPTHS, INIT_IDS, CONFIG_IDS))
    print(f"{len(points)} points selected (depths={DEPTHS}, init_ids={INIT_IDS}, configs={CONFIG_IDS})")

    rows = []
    point_id = 0
    for depth, init_id, config_id in points:
        theta_seed = derive_seed(cfg.seed_root, "init_theta", init_id, depth)
        classical_seed = derive_seed(cfg.seed_root, "init_classical", init_id, depth)
        theta_blocks = draw_theta_blocks(theta_seed, depth, n_qubits, cfg.circuit.init_low, cfg.circuit.init_high)
        classical = init_classical_params(classical_seed, depth, n_qubits, cfg.resolved_hidden_dim(),
                                           cfg.residual.weight_init, cfg.residual.bias_init)
        E, L, R = CONFIGURATION_TABLE[config_id]
        gamma = cfg.gamma_for(R)
        cost_type = cfg.cost_type_for(L)

        T_chain, fwd = total_gradients_exact(theta_blocks, classical, E, gamma, cost_type, spectrum,
                                              n_qubits, cfg.residual.x0_init)

        for ell in range(1, depth + 1):
            for k in range(n_qubits):
                chain_val = float(T_chain[ell][k])
                fd_vals = {}
                for h in H_VALUES:
                    fd_vals[h] = central_fd(theta_blocks, classical, E, gamma, cost_type, spectrum,
                                             n_qubits, cfg.residual.x0_init, ell, k, h)
                row = {
                    "point_id": point_id,
                    "depth": depth,
                    "init_id": init_id,
                    "config_id": config_id,
                    "E": E, "L": L, "R": R,
                    "block_index": ell,
                    "qubit_index": k,
                    "is_terminal_block": ell == depth,
                    "chain_rule_grad": chain_val,
                }
                for h in H_VALUES:
                    row[f"fd_grad_h{h:.0e}"] = fd_vals[h]
                    denom = max(abs(chain_val), REL_ERR_FLOOR)
                    row[f"rel_err_h{h:.0e}"] = abs(chain_val - fd_vals[h]) / denom
                # O(h^2) convergence ratios: error(1e-3)/error(1e-4) and error(1e-4)/error(1e-5)
                # should be ~100 if truncation-error-dominated, i.e. not yet at the floating-point floor.
                errs = [abs(chain_val - fd_vals[h]) for h in H_VALUES]
                row["convergence_ratio_1"] = errs[0] / errs[1] if errs[1] > 0 else float("inf")
                row["convergence_ratio_2"] = errs[1] / errs[2] if errs[2] > 0 else float("inf")
                rows.append(row)
        point_id += 1

    df = pd.DataFrame(rows)
    out_full = Path(__file__).parent / "h1_fd_check_full_table.csv"
    df.to_csv(out_full, index=False)
    print(f"wrote {len(df)} parameter-level rows to {out_full}")

    best_h = H_VALUES[-1]  # 1e-5, smallest step tested
    worst_rel_err = df[f"rel_err_h{best_h:.0e}"].max()
    n_above_tol = (df[f"rel_err_h{best_h:.0e}"] > REL_ERR_TOLERANCE).sum()
    print(f"worst relative error at h={best_h:.0e}: {worst_rel_err:.3e}")
    print(f"rows above tolerance ({REL_ERR_TOLERANCE:.0e}): {n_above_tol} / {len(df)}")

    # --- E x L contrast: L=0 slope (config1->config2) vs L=1 slope (config3->config5) ---
    df["a_chain"] = np.arcsinh(np.abs(df["chain_rule_grad"]))
    df["a_fd"] = np.arcsinh(np.abs(df[f"fd_grad_h{best_h:.0e}"]))

    mean_a_chain = df.groupby("config_id")["a_chain"].mean()
    mean_a_fd = df.groupby("config_id")["a_fd"].mean()
    n_by_config = df.groupby("config_id").size()

    contrast_rows = []
    for label, means in (("chain_rule", mean_a_chain), ("finite_difference", mean_a_fd)):
        l0_slope = means[2] - means[1]
        l1_slope = means[5] - means[3]
        contrast_rows.append({
            "method": label,
            "mean_a_config1": means[1], "mean_a_config2": means[2],
            "mean_a_config3": means[3], "mean_a_config5": means[5],
            "L0_slope_config1_to_2": l0_slope,
            "L1_slope_config3_to_5": l1_slope,
            "super_additive_L1_gt_L0": bool(l1_slope > l0_slope),
        })
    contrast_df = pd.DataFrame(contrast_rows)
    out_contrast = Path(__file__).parent / "h1_fd_check_EL_contrast.csv"
    contrast_df.to_csv(out_contrast, index=False)
    print(f"\nn per config_id:\n{n_by_config}\n")
    print(contrast_df.to_string(index=False))
    print(f"\nwrote {out_contrast}")


if __name__ == "__main__":
    main()
