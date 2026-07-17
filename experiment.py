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

from hamiltonian import (build_tfim_hamiltonian, build_xxz_hamiltonian, z0z1_operator,
                          sanity_check, sanity_check_hamiltonian)
from snr import init_params, compute_snr_for_initialization
from ansatze import build_snapshot_circuit, brick_pattern_matches_pilot_n4

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
            grads, snrs, labels, _classes, _meta = compute_snr_for_initialization(
                theta, alpha, L_MAIN, N_QUBITS, config["entanglement"], config["cost"],
                config["residual"], H, H2, ZZ, N_shots=N_SHOTS, run_circuit=run_circuit,
                residual_reduction="sum",
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
                grads, snrs, labels, _classes, _meta = compute_snr_for_initialization(
                    theta, alpha, L, N_QUBITS, config["entanglement"], config["cost"],
                    config["residual"], H, H2, ZZ, N_shots=N_SHOTS, run_circuit=run_circuit,
                    residual_reduction="sum",
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


# ============================================================================
# Companion-paper phase 2: n-qubit x task grid, sum-vs-mean residual
# sensitivity check, and a scoped (n in {4,6,10}) depth sweep.
#
# The pilot's own run_main_experiment/run_depth_sweep/_summarize above are
# left untouched (still n=4, TFIM(h=0.5)-only, using np.isfinite exclusion) so
# `python experiment.py`'s existing behavior and the committed pilot result
# files stay byte-for-byte reproducible. Everything below is new and lives in
# its own results/*grid*/*sensitivity*/*scoped* files instead.
# ============================================================================

TASKS = [
    {"name": "tfim_h0.5", "label": "TFIM (J=1, h=0.5)", "kind": "tfim",
     "params": {"J": 1.0, "h": 0.5}},
    {"name": "tfim_h2.0", "label": "TFIM (J=1, h=2.0)", "kind": "tfim",
     "params": {"J": 1.0, "h": 2.0}},
    {"name": "xxz_delta0.5", "label": "XXZ (Delta=0.5)", "kind": "xxz",
     "params": {"delta": 0.5}},
]
REFERENCE_TASK_NAME = "tfim_h0.5"  # matches the pilot's exact TFIM(J=1,h=0.5) task

N_QUBITS_SWEEP = list(range(2, 11))  # 2..10
# Sensitivity check scope per the residual-parameter correction: 'sum' is the
# secondary check, evaluated at n=4, depth=L_MAIN, measurement budget=N_SHOTS
# (narrowed from the original {4,10} range now that 'mean' -- n-invariant --
# is the primary reduction used throughout the main grid).
SENSITIVITY_N_QUBITS = [4]
DEPTH_SWEEP_N_QUBITS = [4, 6, 10]
RESIDUAL_CONFIG_NAMES = {"residual_only", "entanglement_residual", "combined"}

# Runtime-budget-driven seed counts (see README "Design choices" / RESULTS.md
# runtime note). A calibration run before the full data generation measured:
#   main grid (3 tasks x 9 n-values x 7 configs) at 200 seeds  -> ~88 min
#   sensitivity check (3 tasks x n in {4,10} x 7 configs) at 200 seeds x2 reductions -> ~46 min
#   scoped depth sweep (n in {4,6,10} x 3 configs x 5 depths) at 200 seeds -> ~58 min
# Running all three at the spec's suggested 200 seeds would total ~2.7 hours,
# exceeding the stated 1-2 hour budget. Per the spec's explicit instruction to
# "reduce seeds for the full n x task grid specifically ... but keep 200 seeds
# for whichever single reference point you'd call out as a headline result":
# the main grid and sensitivity check are reduced to 50 seeds (matching the
# pilot's own seed count, which already produced clean, significant Wilcoxon
# results), while the depth sweep keeps the full 200 (it fits the budget on
# its own and is the piece most sensitive to a heavy-tailed distribution at
# low L). The single grid point most directly comparable to the pilot
# (n_qubits=4, task=tfim_h0.5) is additionally re-run at the full 200 seeds
# as this phase's headline reference result.
N_SEEDS_MAIN_GRID = 50
N_SEEDS_SENSITIVITY = 50
N_SEEDS_DEPTH_SWEEP = 200
N_SEEDS_HEADLINE = 200
HEADLINE_TASK_NAME = "tfim_h0.5"
HEADLINE_N_QUBITS = 4


def build_task_hamiltonian(task, n_qubits):
    if task["kind"] == "tfim":
        return build_tfim_hamiltonian(n_qubits, task["params"]["J"], task["params"]["h"])
    elif task["kind"] == "xxz":
        return build_xxz_hamiltonian(n_qubits, task["params"]["delta"])
    else:
        raise ValueError(f"unknown task kind: {task['kind']}")


def _summarize_grid(snrs, classes, labels, param_meta):
    """Like `_summarize`, but built around the three-way parameter
    classification (snr.snr_from_grad_var: "active", "deterministic_nonzero",
    "inactive_zero") and the parameter_type/estimator_family metadata
    (snr._parameter_metadata). Only "active" parameters feed the aggregate
    mean/median; "deterministic_nonzero" and "inactive_zero" are reported as
    separate diagnostic fields (count + identity) rather than silently
    dropped, and "deterministic_nonzero" additionally counts toward the
    operationally-resolvable fraction (a real, resolvable gradient with no
    measurement noise, as opposed to a truly flat "inactive_zero" direction).
    """
    classes = np.asarray(classes)
    active_mask = classes == "active"
    det_nonzero_mask = classes == "deterministic_nonzero"
    inactive_mask = classes == "inactive_zero"

    finite = snrs[active_mask]
    if finite.size == 0:
        finite = np.array([np.nan])

    n_params = int(snrs.size)
    n_operationally_resolvable = int(np.sum(active_mask) + np.sum(det_nonzero_mask))
    parameter_types = [m["parameter_type"] for m in param_meta]

    return {
        "mean_snr": float(np.mean(finite)),
        "median_snr": float(np.median(finite)),
        "std_snr": float(np.std(finite)),
        "min_snr": float(np.min(finite)),
        "max_snr": float(np.max(finite)),
        "n_params": n_params,
        "n_active_params": int(np.sum(active_mask)),
        "n_deterministic_nonzero_params": int(np.sum(det_nonzero_mask)),
        "n_inactive_zero_params": int(np.sum(inactive_mask)),
        "operationally_resolvable_fraction": (
            float(n_operationally_resolvable / n_params) if n_params else float("nan")
        ),
        "deterministic_nonzero_labels": ";".join(l for l, m in zip(labels, det_nonzero_mask) if m),
        "inactive_zero_labels": ";".join(l for l, m in zip(labels, inactive_mask) if m),
        "n_circuit_theta_params": sum(1 for t in parameter_types if t == "circuit_theta"),
        "n_residual_alpha_params": sum(1 for t in parameter_types if t == "residual_alpha"),
    }


def assert_no_residual_alpha_misrouting(labels, param_meta):
    """Standing validation: every 'alpha_*' label must be tagged
    parameter_type='residual_alpha' with the dedicated exact-linear gradient
    method and independent-per-qubit analytic variance method (zero shift
    evaluations, zero tomography settings -- this codebase has no tomography
    or mixed-state-fidelity path at all); every 'theta_*' label must be
    tagged parameter_type='circuit_theta' with the parameter-shift method.
    Raises AssertionError on any violation, so a routing bug fails loudly
    rather than silently mislabeling a parameter-level row.
    """
    for label, meta in zip(labels, param_meta):
        if label.startswith("alpha_"):
            assert meta["parameter_type"] == "residual_alpha", \
                f"{label} misrouted: parameter_type={meta['parameter_type']!r}"
            assert meta["gradient_method"] == "residual_alpha_exact_linear", \
                f"{label} misrouted: gradient_method={meta['gradient_method']!r}"
            assert meta["variance_method"] == "residual_alpha_analytic_independent_z", \
                f"{label} misrouted: variance_method={meta['variance_method']!r}"
            assert meta["number_of_shift_evaluations"] == 0, \
                f"{label} misrouted: number_of_shift_evaluations != 0"
            assert meta["number_of_tomography_settings"] == 0, \
                f"{label} misrouted: number_of_tomography_settings != 0"
        elif label.startswith("theta_"):
            assert meta["parameter_type"] == "circuit_theta", \
                f"{label} misrouted: parameter_type={meta['parameter_type']!r}"
            assert meta["gradient_method"] == "parameter_shift", \
                f"{label} misrouted: gradient_method={meta['gradient_method']!r}"
        else:
            raise AssertionError(f"unrecognized parameter label: {label}")
    return True


def run_hamiltonian_and_pattern_checks(tasks=None, n_qubits_sweep=None, verbose=True):
    """Hamiltonian sanity check (Hermiticity, Z0Z1 idempotency, exact ground
    energy) for every (task, n) point in the sweep, plus the brick-pattern
    generalization regression check -- the regression guard against a
    generalization bug, run before any grid data is generated.
    """
    tasks = tasks if tasks is not None else TASKS
    n_qubits_sweep = n_qubits_sweep if n_qubits_sweep is not None else N_QUBITS_SWEEP

    assert brick_pattern_matches_pilot_n4(), \
        "brick-layer generalization does not reduce to the pilot's n=4 pattern"

    results = []
    for task in tasks:
        for n_qubits in n_qubits_sweep:
            H = build_task_hamiltonian(task, n_qubits)
            r = sanity_check_hamiltonian(H, n_qubits, label=task["name"],
                                          task_params=task["params"], verbose=False)
            results.append(r)
    if verbose:
        print(f"  Hamiltonian sanity checks passed: {len(results)} (task, n) points "
              f"({len(tasks)} tasks x {len(n_qubits_sweep)} n-values); "
              f"brick-pattern n=4 regression check passed.")
    return results


def run_main_grid(tasks=None, n_qubits_sweep=None, n_seeds=N_SEEDS_MAIN_GRID,
                   L=L_MAIN, N_shots=N_SHOTS, residual_reduction="mean", verbose=True):
    """Runs all 7 CONFIGS x n_seeds seeds at L=L_MAIN, for every (task, n_qubits)
    grid point. Returns a single long-format summary DataFrame (one row per
    task/n_qubits/config/seed) -- the main new empirical contribution of this
    phase. No full per-parameter JSON is kept for the grid (see README
    "Design choices" / data-volume scoping); only the summary statistics
    `_summarize_grid` computes per seed are retained.
    """
    tasks = tasks if tasks is not None else TASKS
    n_qubits_sweep = n_qubits_sweep if n_qubits_sweep is not None else N_QUBITS_SWEEP

    summary_rows = []
    for task in tasks:
        for n_qubits in n_qubits_sweep:
            H = build_task_hamiltonian(task, n_qubits)
            H2 = H @ H
            ZZ = z0z1_operator(n_qubits)
            circuit_cache = {}
            for config in CONFIGS:
                key = (config["entanglement"], L)
                if key not in circuit_cache:
                    circuit_cache[key] = build_snapshot_circuit(n_qubits, L, config["entanglement"])
                run_circuit = circuit_cache[key]

                t0 = time.time()
                for seed in range(n_seeds):
                    theta, alpha = init_params(seed, L, n_qubits, config["residual"])
                    grads, snrs, labels, classes, meta = compute_snr_for_initialization(
                        theta, alpha, L, n_qubits, config["entanglement"], config["cost"],
                        config["residual"], H, H2, ZZ, N_shots=N_shots,
                        run_circuit=run_circuit, residual_reduction=residual_reduction,
                    )
                    assert_no_residual_alpha_misrouting(labels, meta)
                    row = {"task": task["name"], "task_label": task["label"], "n_qubits": n_qubits,
                           "config_id": config["id"], "config_name": config["name"],
                           "config_label": config["label"], "seed": seed, "L": L,
                           "residual_reduction": residual_reduction}
                    row.update(_summarize_grid(snrs, classes, labels, meta))
                    row["mean_abs_grad"] = float(np.mean(np.abs(grads)))
                    summary_rows.append(row)
                if verbose:
                    print(f"  [{task['name']:14s} n={n_qubits:2d}] {config['label']:32s} "
                          f"{n_seeds} seeds in {time.time() - t0:.2f}s")

    return pd.DataFrame(summary_rows)


def run_sensitivity_check(tasks=None, n_qubits_list=None, n_seeds=N_SEEDS_SENSITIVITY,
                           L=L_MAIN, N_shots=N_SHOTS, verbose=True):
    """Self-contained mean-vs-sum residual-reduction sensitivity check. 'mean'
    is the primary reduction (used throughout the main grid); 'sum' is
    retained as a secondary sensitivity check, scoped to n=4, depth=L_MAIN,
    measurement budget=N_SHOTS (per the residual-parameter correction -- not
    the full {4,10} x 3-tasks range used in the original companion-phase
    design, now that 'mean' is n-invariant and no longer needs cross-n
    validation against 'sum' as the default).

    Runs ALL 7 CONFIGS under residual_reduction='mean', plus the three
    residual-bearing configs (residual_only, entanglement_residual, combined)
    again under 'sum' -- the other four configs never touch alpha, so they
    are exactly invariant to this toggle and their 'mean' rows are valid
    under the 'sum' label too, with no separate computation needed.

    Deliberately self-contained (does not reuse rows from `run_main_grid`,
    which may use a different seed count -- see N_SEEDS_MAIN_GRID vs.
    N_SEEDS_SENSITIVITY): both reductions here are computed at the *same*
    seeds, so the comparison stays properly paired.

    Returns (sum_df, mean_df): each has all 7 configs at every (task,
    n_qubits) point, ready for a full H1/H2a/H2b comparison under both
    reductions.
    """
    tasks = tasks if tasks is not None else TASKS
    n_qubits_list = n_qubits_list if n_qubits_list is not None else SENSITIVITY_N_QUBITS

    mean_rows = []
    sum_only_rows = []
    for task in tasks:
        for n_qubits in n_qubits_list:
            H = build_task_hamiltonian(task, n_qubits)
            H2 = H @ H
            ZZ = z0z1_operator(n_qubits)
            circuit_cache = {}
            for config in CONFIGS:
                key = (config["entanglement"], L)
                if key not in circuit_cache:
                    circuit_cache[key] = build_snapshot_circuit(n_qubits, L, config["entanglement"])
                run_circuit = circuit_cache[key]

                t0 = time.time()
                for seed in range(n_seeds):
                    theta, alpha = init_params(seed, L, n_qubits, config["residual"])
                    grads, snrs, labels, classes, meta = compute_snr_for_initialization(
                        theta, alpha, L, n_qubits, config["entanglement"], config["cost"],
                        config["residual"], H, H2, ZZ, N_shots=N_shots,
                        run_circuit=run_circuit, residual_reduction="mean",
                    )
                    assert_no_residual_alpha_misrouting(labels, meta)
                    row = {"task": task["name"], "task_label": task["label"], "n_qubits": n_qubits,
                           "config_id": config["id"], "config_name": config["name"],
                           "config_label": config["label"], "seed": seed, "L": L,
                           "residual_reduction": "mean"}
                    row.update(_summarize_grid(snrs, classes, labels, meta))
                    row["mean_abs_grad"] = float(np.mean(np.abs(grads)))
                    mean_rows.append(row)
                if verbose:
                    print(f"  [sensitivity mean] [{task['name']:14s} n={n_qubits:2d}] "
                          f"{config['label']:32s} {n_seeds} seeds in {time.time() - t0:.2f}s")

                if config["name"] in RESIDUAL_CONFIG_NAMES:
                    t0 = time.time()
                    for seed in range(n_seeds):
                        theta, alpha = init_params(seed, L, n_qubits, config["residual"])
                        grads, snrs, labels, classes, meta = compute_snr_for_initialization(
                            theta, alpha, L, n_qubits, config["entanglement"], config["cost"],
                            config["residual"], H, H2, ZZ, N_shots=N_shots,
                            run_circuit=run_circuit, residual_reduction="sum",
                        )
                        assert_no_residual_alpha_misrouting(labels, meta)
                        row = {"task": task["name"], "task_label": task["label"], "n_qubits": n_qubits,
                               "config_id": config["id"], "config_name": config["name"],
                               "config_label": config["label"], "seed": seed, "L": L,
                               "residual_reduction": "sum"}
                        row.update(_summarize_grid(snrs, classes, labels, meta))
                        row["mean_abs_grad"] = float(np.mean(np.abs(grads)))
                        sum_only_rows.append(row)
                    if verbose:
                        print(f"  [sensitivity sum]  [{task['name']:14s} n={n_qubits:2d}] "
                              f"{config['label']:32s} {n_seeds} seeds in {time.time() - t0:.2f}s")

    mean_df = pd.DataFrame(mean_rows)
    sum_only_df = pd.DataFrame(sum_only_rows)
    non_residual_as_sum = mean_df[~mean_df["config_name"].isin(RESIDUAL_CONFIG_NAMES)].copy()
    non_residual_as_sum["residual_reduction"] = "sum"
    sum_df = pd.concat([non_residual_as_sum, sum_only_df], ignore_index=True, sort=False)
    return sum_df, mean_df


def run_headline_reference(n_seeds=N_SEEDS_HEADLINE, L=L_MAIN, N_shots=N_SHOTS, verbose=True):
    """Re-runs the single grid point most directly comparable to the pilot
    (n_qubits=HEADLINE_N_QUBITS, task=HEADLINE_TASK_NAME, all 7 configs) at
    the full N_SEEDS=200 the spec asks for throughout this phase, even though
    the full grid itself had to use a reduced seed count to fit the runtime
    budget (see N_SEEDS_MAIN_GRID above). This is "whichever single reference
    point you'd call out as a headline result."
    """
    task = next(t for t in TASKS if t["name"] == HEADLINE_TASK_NAME)
    return run_main_grid(tasks=[task], n_qubits_sweep=[HEADLINE_N_QUBITS], n_seeds=n_seeds,
                          L=L, N_shots=N_shots, residual_reduction="mean", verbose=verbose)


def run_depth_sweep_scoped(n_qubits_list=None, n_seeds=N_SEEDS_DEPTH_SWEEP, N_shots=N_SHOTS,
                            verbose=True):
    """H3 depth sweep (spec section 6): DEPTH_CONFIGS x DEPTHS x n_seeds seeds,
    restricted to the reference task (TFIM h=0.5) at n_qubits in {4,6,10} --
    not the full 5-depth x 9-n x 3-task sweep, which is disproportionately
    expensive for what it buys (see README "Non-goals"). Applies the
    deterministic-parameter rule explicitly, which is specifically relevant at
    L=1 (see snr.py module docstring). Returns (summary_df, per_param_records).
    """
    n_qubits_list = n_qubits_list if n_qubits_list is not None else DEPTH_SWEEP_N_QUBITS
    ref_task = next(t for t in TASKS if t["name"] == REFERENCE_TASK_NAME)

    summary_rows = []
    per_param_records = []
    for n_qubits in n_qubits_list:
        H = build_task_hamiltonian(ref_task, n_qubits)
        H2 = H @ H
        ZZ = z0z1_operator(n_qubits)
        for L in DEPTHS:
            circuit_cache = {}
            for config in DEPTH_CONFIGS:
                key = config["entanglement"]
                if key not in circuit_cache:
                    circuit_cache[key] = build_snapshot_circuit(n_qubits, L, config["entanglement"])
                run_circuit = circuit_cache[key]

                t0 = time.time()
                for seed in range(n_seeds):
                    theta, alpha = init_params(seed, L, n_qubits, config["residual"])
                    grads, snrs, labels, classes, meta = compute_snr_for_initialization(
                        theta, alpha, L, n_qubits, config["entanglement"], config["cost"],
                        config["residual"], H, H2, ZZ, N_shots=N_shots, run_circuit=run_circuit,
                    )
                    assert_no_residual_alpha_misrouting(labels, meta)
                    row = {"n_qubits": n_qubits, "config_name": config["name"],
                           "config_label": config["label"], "seed": seed, "L": L}
                    row.update(_summarize_grid(snrs, classes, labels, meta))
                    row["mean_abs_grad"] = float(np.mean(np.abs(grads)))
                    summary_rows.append(row)

                    per_param_records.append({
                        "n_qubits": n_qubits, "config_name": config["name"], "seed": seed, "L": L,
                        "labels": labels, "grads": grads.tolist(), "snrs": snrs.tolist(),
                        "classes": classes,
                        "parameter_type": [m["parameter_type"] for m in meta],
                        "gradient_method": [m["gradient_method"] for m in meta],
                        "variance_method": [m["variance_method"] for m in meta],
                        "variance_method_family": [m["variance_method_family"] for m in meta],
                        "estimator_family": [m["estimator_family"] for m in meta],
                        "number_of_shift_evaluations": [m["number_of_shift_evaluations"] for m in meta],
                        "number_of_tomography_settings": [m["number_of_tomography_settings"] for m in meta],
                        "number_of_measurement_settings": [m["number_of_measurement_settings"] for m in meta],
                    })
                if verbose:
                    print(f"  [depth scoped] n={n_qubits:2d} L={L} [{config['label']:24s}] "
                          f"{n_seeds} seeds in {time.time() - t0:.2f}s")

    return pd.DataFrame(summary_rows), per_param_records


def run_companion_phase(n_seeds_grid=N_SEEDS_MAIN_GRID, n_seeds_sensitivity=N_SEEDS_SENSITIVITY,
                         n_seeds_depth=N_SEEDS_DEPTH_SWEEP, n_seeds_headline=N_SEEDS_HEADLINE,
                         verbose=True):
    """Orchestrates the full companion-paper phase 2: hamiltonian/pattern
    checks -> main n x task grid -> headline reference re-run -> sum-vs-mean
    sensitivity check -> scoped depth sweep. Writes all raw output to
    results/. Does not touch or re-run the pilot's own files
    (main_experiment_summary.csv, depth_sweep_summary.csv, etc.), which stay
    as the labeled n=4/single-task reference. See the seed-count constants
    above for the runtime-budget-driven reduction applied to the main grid
    and sensitivity check.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    runtime = {}

    print("Running Hamiltonian + brick-pattern regression checks across the full (task, n) sweep...")
    ham_checks = run_hamiltonian_and_pattern_checks(verbose=verbose)
    with open(os.path.join(RESULTS_DIR, "hamiltonian_check_grid.json"), "w") as f:
        json.dump(ham_checks, f, indent=2)

    print(f"\nRunning main grid: {len(TASKS)} tasks x {len(N_QUBITS_SWEEP)} n-values x "
          f"{len(CONFIGS)} configs x {n_seeds_grid} seeds at L={L_MAIN}...")
    t0 = time.time()
    main_grid_df = run_main_grid(n_seeds=n_seeds_grid, verbose=verbose)
    runtime["main_grid_seconds"] = time.time() - t0
    main_grid_df.to_csv(os.path.join(RESULTS_DIR, "main_grid_summary.csv"), index=False)
    print(f"Main grid done in {runtime['main_grid_seconds']:.1f}s "
          f"({len(main_grid_df)} rows).")

    print(f"\nRunning headline reference re-run: n_qubits={HEADLINE_N_QUBITS}, "
          f"task={HEADLINE_TASK_NAME}, {n_seeds_headline} seeds...")
    t0 = time.time()
    headline_df = run_headline_reference(n_seeds=n_seeds_headline, verbose=verbose)
    runtime["headline_seconds"] = time.time() - t0
    headline_df.to_csv(os.path.join(RESULTS_DIR, "main_grid_headline_reference.csv"), index=False)
    print(f"Headline reference done in {runtime['headline_seconds']:.1f}s.")

    print(f"\nRunning sum-vs-mean residual sensitivity check at n in {SENSITIVITY_N_QUBITS} "
          f"across all tasks, {n_seeds_sensitivity} seeds...")
    t0 = time.time()
    sensitivity_sum_df, sensitivity_mean_df = run_sensitivity_check(
        n_seeds=n_seeds_sensitivity, verbose=verbose)
    runtime["sensitivity_seconds"] = time.time() - t0
    sensitivity_sum_df.to_csv(os.path.join(RESULTS_DIR, "sensitivity_sum_summary.csv"), index=False)
    sensitivity_mean_df.to_csv(os.path.join(RESULTS_DIR, "sensitivity_mean_summary.csv"), index=False)
    print(f"Sensitivity check done in {runtime['sensitivity_seconds']:.1f}s.")

    print(f"\nRunning scoped H3 depth sweep at n in {DEPTH_SWEEP_N_QUBITS} "
          f"(reference task only), {n_seeds_depth} seeds...")
    t0 = time.time()
    depth_scoped_df, depth_scoped_per_param = run_depth_sweep_scoped(n_seeds=n_seeds_depth,
                                                                      verbose=verbose)
    runtime["depth_sweep_scoped_seconds"] = time.time() - t0
    depth_scoped_df.to_csv(os.path.join(RESULTS_DIR, "depth_sweep_scoped_summary.csv"), index=False)
    with open(os.path.join(RESULTS_DIR, "depth_sweep_scoped_per_parameter.json"), "w") as f:
        json.dump(depth_scoped_per_param, f)
    print(f"Scoped depth sweep done in {runtime['depth_sweep_scoped_seconds']:.1f}s.")

    runtime["total_seconds"] = sum(runtime.values())
    runtime["n_seeds_grid"] = n_seeds_grid
    runtime["n_seeds_sensitivity"] = n_seeds_sensitivity
    runtime["n_seeds_depth"] = n_seeds_depth
    runtime["n_seeds_headline"] = n_seeds_headline
    with open(os.path.join(RESULTS_DIR, "runtime_phase2.json"), "w") as f:
        json.dump(runtime, f, indent=2)
    print(f"\nCompanion phase 2 total runtime: {runtime['total_seconds']:.1f}s "
          f"({runtime['total_seconds'] / 60:.1f} min)")

    return {
        "main_grid_df": main_grid_df,
        "headline_df": headline_df,
        "sensitivity_sum_df": sensitivity_sum_df,
        "sensitivity_mean_df": sensitivity_mean_df,
        "depth_scoped_df": depth_scoped_df,
        "depth_scoped_per_param": depth_scoped_per_param,
        "runtime": runtime,
    }


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
