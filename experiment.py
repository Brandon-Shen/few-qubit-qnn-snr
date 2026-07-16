"""Runs the 7 ablation configurations x 50 seeds, plus the H3 depth sweep,
and saves raw results to results/.

Config table (matches spec section "The seven ablation configurations"):
  1. baseline               HEA,   global cost
  2. entanglement_only       brick, global cost                (A)
  3. local_cost_only         HEA,   local cost                 (B)
  4. residual_only           HEA,   global cost, residual      (C)
  5. entanglement_local      brick, local cost                 (A+B)  [H2a]
  6. entanglement_residual   brick, global cost, residual      (A+C)  [H2b]
  7. combined                brick, local cost, residual       (A+B+C)
"""
import json
import os
import time

import numpy as np
import pandas as pd

from hamiltonian import build_tfim_hamiltonian, z0z1_operator, sanity_check
from snr import init_params, compute_snr_for_initialization
from ansatze import build_snapshot_circuit

N_QUBITS = 4
J, H_FIELD = 1.0, 0.5
L_MAIN = 3
N_SEEDS = 50
N_SHOTS = 1000
DEPTHS = [1, 2, 3, 5, 8]

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

CONFIGS = [
    {"id": 1, "name": "baseline", "label": "Baseline (HEA)",
     "entanglement": "full", "cost": "global", "residual": False},
    {"id": 2, "name": "entanglement_only", "label": "Constrained entanglement only",
     "entanglement": "brick", "cost": "global", "residual": False},
    {"id": 3, "name": "local_cost_only", "label": "Local cost function only",
     "entanglement": "full", "cost": "local", "residual": False},
    {"id": 4, "name": "residual_only", "label": "Residual connections only",
     "entanglement": "full", "cost": "global", "residual": True},
    {"id": 5, "name": "entanglement_local", "label": "Entanglement + local cost",
     "entanglement": "brick", "cost": "local", "residual": False},
    {"id": 6, "name": "entanglement_residual", "label": "Entanglement + residual",
     "entanglement": "brick", "cost": "global", "residual": True},
    {"id": 7, "name": "combined", "label": "Combined (A+B+C)",
     "entanglement": "brick", "cost": "local", "residual": True},
]

# H3 depth sweep: local-cost-only, residual-only, and their combination, all
# on the *baseline* (full-chain) entanglement pattern -- the sweep isolates B
# and C from A, per "Repeat configurations 3 (local cost only) and 4
# (residual only) -- and their combination".
DEPTH_CONFIGS = [
    {"name": "local_cost_only", "label": "Local cost only",
     "entanglement": "full", "cost": "local", "residual": False},
    {"name": "residual_only", "label": "Residual only",
     "entanglement": "full", "cost": "global", "residual": True},
    {"name": "local_and_residual", "label": "Local cost + residual",
     "entanglement": "full", "cost": "local", "residual": True},
]


def _summarize(snrs):
    finite = snrs[np.isfinite(snrs)]
    if finite.size == 0:
        finite = np.array([np.nan])
    return {
        "mean_snr": float(np.mean(finite)),
        "median_snr": float(np.median(finite)),
        "std_snr": float(np.std(finite)),
        "min_snr": float(np.min(finite)),
        "max_snr": float(np.max(finite)),
        "n_params": int(snrs.size),
        "n_finite_params": int(finite.size),
    }


def run_main_experiment(H, H2, ZZ, verbose=True):
    """Runs all 7 configs x N_SEEDS seeds at L_MAIN. Returns (summary_df, per_param_records)."""
    summary_rows = []
    per_param_records = []  # for landscape variance + detailed analysis

    circuit_cache = {}
    for config in CONFIGS:
        key = (config["entanglement"], L_MAIN)
        if key not in circuit_cache:
            circuit_cache[key] = build_snapshot_circuit(N_QUBITS, L_MAIN, config["entanglement"])
        run_circuit = circuit_cache[key]

        t0 = time.time()
        for seed in range(N_SEEDS):
            theta, alpha = init_params(seed, L_MAIN, N_QUBITS, config["residual"])
            grads, snrs, labels = compute_snr_for_initialization(
                theta, alpha, L_MAIN, N_QUBITS, config["entanglement"], config["cost"],
                config["residual"], H, H2, ZZ, N_shots=N_SHOTS, run_circuit=run_circuit,
            )
            row = {"config_id": config["id"], "config_name": config["name"],
                   "config_label": config["label"], "seed": seed, "L": L_MAIN}
            row.update(_summarize(snrs))
            row["mean_abs_grad"] = float(np.mean(np.abs(grads)))
            summary_rows.append(row)

            per_param_records.append({
                "config_name": config["name"], "seed": seed, "L": L_MAIN,
                "labels": labels, "grads": grads.tolist(), "snrs": snrs.tolist(),
            })
        if verbose:
            print(f"  [{config['id']}] {config['label']:32s} "
                  f"{N_SEEDS} seeds in {time.time() - t0:.2f}s")

    return pd.DataFrame(summary_rows), per_param_records


def run_depth_sweep(H, H2, ZZ, verbose=True):
    """Runs DEPTH_CONFIGS x DEPTHS x N_SEEDS seeds. Returns (summary_df, per_param_records)."""
    summary_rows = []
    per_param_records = []

    for L in DEPTHS:
        circuit_cache = {}
        for config in DEPTH_CONFIGS:
            key = config["entanglement"]
            if key not in circuit_cache:
                circuit_cache[key] = build_snapshot_circuit(N_QUBITS, L, config["entanglement"])
            run_circuit = circuit_cache[key]

            t0 = time.time()
            for seed in range(N_SEEDS):
                theta, alpha = init_params(seed, L, N_QUBITS, config["residual"])
                grads, snrs, labels = compute_snr_for_initialization(
                    theta, alpha, L, N_QUBITS, config["entanglement"], config["cost"],
                    config["residual"], H, H2, ZZ, N_shots=N_SHOTS, run_circuit=run_circuit,
                )
                row = {"config_name": config["name"], "config_label": config["label"],
                       "seed": seed, "L": L}
                row.update(_summarize(snrs))
                row["mean_abs_grad"] = float(np.mean(np.abs(grads)))
                summary_rows.append(row)

                per_param_records.append({
                    "config_name": config["name"], "seed": seed, "L": L,
                    "labels": labels, "grads": grads.tolist(), "snrs": snrs.tolist(),
                })
            if verbose:
                print(f"  L={L} [{config['label']:24s}] "
                      f"{N_SEEDS} seeds in {time.time() - t0:.2f}s")

    return pd.DataFrame(summary_rows), per_param_records


def landscape_gradient_variance(per_param_records):
    """Var_theta[d C/d theta_i] across the 50 seeds, per (config, param label).
    This is the secondary "Eq.-1-style" landscape-variance quantity requested
    in the spec, distinct from the per-seed shot-noise SNR.
    """
    from collections import defaultdict
    buckets = defaultdict(list)
    for rec in per_param_records:
        for label, g in zip(rec["labels"], rec["grads"]):
            buckets[(rec["config_name"], rec.get("L"), label)].append(g)

    rows = []
    for (config_name, L, label), grads in buckets.items():
        grads = np.array(grads)
        rows.append({
            "config_name": config_name, "L": L, "param_label": label,
            "landscape_grad_var": float(np.var(grads)),
            "landscape_grad_mean": float(np.mean(grads)),
            "n_seeds": len(grads),
        })
    return pd.DataFrame(rows)


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("Building TFIM Hamiltonian and running exact-diagonalization sanity check...")
    ham_check = sanity_check(N_QUBITS, J, H_FIELD, verbose=True)
    with open(os.path.join(RESULTS_DIR, "hamiltonian_check.json"), "w") as f:
        json.dump(ham_check, f, indent=2)

    H = build_tfim_hamiltonian(N_QUBITS, J, H_FIELD)
    H2 = H @ H
    ZZ = z0z1_operator(N_QUBITS)

    print("\nRunning main experiment: 7 configs x 50 seeds at L=3...")
    t0 = time.time()
    main_summary, main_per_param = run_main_experiment(H, H2, ZZ)
    main_elapsed = time.time() - t0
    print(f"Main experiment done in {main_elapsed:.2f}s")

    main_summary.to_csv(os.path.join(RESULTS_DIR, "main_experiment_summary.csv"), index=False)
    with open(os.path.join(RESULTS_DIR, "main_experiment_per_parameter.json"), "w") as f:
        json.dump(main_per_param, f)

    main_landscape = landscape_gradient_variance(main_per_param)
    main_landscape.to_csv(os.path.join(RESULTS_DIR, "main_landscape_variance.csv"), index=False)

    print("\nRunning H3 depth sweep: 3 configs x 5 depths x 50 seeds...")
    t0 = time.time()
    depth_summary, depth_per_param = run_depth_sweep(H, H2, ZZ)
    depth_elapsed = time.time() - t0
    print(f"Depth sweep done in {depth_elapsed:.2f}s")

    depth_summary.to_csv(os.path.join(RESULTS_DIR, "depth_sweep_summary.csv"), index=False)
    with open(os.path.join(RESULTS_DIR, "depth_sweep_per_parameter.json"), "w") as f:
        json.dump(depth_per_param, f)

    total_elapsed = main_elapsed + depth_elapsed
    runtime_info = {
        "main_experiment_seconds": main_elapsed,
        "depth_sweep_seconds": depth_elapsed,
        "total_seconds": total_elapsed,
    }
    with open(os.path.join(RESULTS_DIR, "runtime.json"), "w") as f:
        json.dump(runtime_info, f, indent=2)

    print(f"\nTotal experiment runtime: {total_elapsed:.2f}s")
    return main_summary, main_per_param, depth_summary, depth_per_param, runtime_info


if __name__ == "__main__":
    main()
