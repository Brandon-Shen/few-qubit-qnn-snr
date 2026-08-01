"""H2 robustness package, Phase 4 (B): initialization-level resampling with
explicit per-iteration zero-variance logging.

This wraps the identical outer/inner resampling primitives already used by
the production bootstrap (qnn_snr/stats/bootstrap.py) -- resample complete
initializations with replacement, preserving full matched factorial
structure, then resample replicates within each cell, recompute pointwise
statistics, and refit -- but does NOT modify that module. It logs, for
every iteration, the number of cells that become zero-variance in that
particular resample, before build_h2h4_dataset()'s filter silently drops
them (a gap in the existing production bootstrap identified in
verification/h2_robustness_replication_plan.md Section 1.6).

Iterations, seed, and checkpoint cadence are fixed in the frozen plan
(Section 2.2(B)): n=200, seed=900001 (new, non-overlapping with the
production bootstrap seed 12345 and with the replication seed namespace).

Run from the repo root: python scripts/run_h2_init_level_resampling.py
Resumable: safe to interrupt and rerun: checkpoints every 10 iterations.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qnn_snr.stats.bootstrap import _inner_resample_replicates, _relabel_outer_resample  # noqa: E402
from qnn_snr.stats.models import build_h2h4_dataset, fit_h2h4_model  # noqa: E402
from qnn_snr.stats.pointwise import pointwise_statistics  # noqa: E402
from qnn_snr.schema import read_tidy_dataset  # noqa: E402

PROD_DIR = REPO_ROOT / "results" / "production_confirmatory"
OUT_DIR = REPO_ROOT / "results" / "h2_robustness" / "robust_inference"
CHECKPOINT_PATH = OUT_DIR / "init_resample_checkpoint.parquet"
DIAGNOSTICS_PATH = OUT_DIR / "init_resample_per_iteration_diagnostics.csv"

N_ITERATIONS = 200
SEED = 900001
CHECKPOINT_EVERY = 10
CONFIRMATORY_MODE = "finite_shot_end_to_end"


def load_checkpoint() -> tuple[list[dict], list[dict]]:
    if CHECKPOINT_PATH.exists():
        coef_rows = pd.read_parquet(CHECKPOINT_PATH).to_dict("records")
    else:
        coef_rows = []
    if DIAGNOSTICS_PATH.exists():
        diag_rows = pd.read_csv(DIAGNOSTICS_PATH).to_dict("records")
    else:
        diag_rows = []
    return coef_rows, diag_rows


def save_checkpoint(coef_rows: list[dict], diag_rows: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if coef_rows:
        pd.DataFrame(coef_rows).to_parquet(CHECKPOINT_PATH, index=False)
    if diag_rows:
        pd.DataFrame(diag_rows).to_csv(DIAGNOSTICS_PATH, index=False)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_end_to_end = read_tidy_dataset(PROD_DIR / "raw" / "finite_shot_end_to_end.parquet")

    coef_rows, diag_rows = load_checkpoint()
    done_iters = {r["iteration"] for r in diag_rows}
    print(f"resuming: {len(done_iters)}/{N_ITERATIONS} iterations already completed", flush=True)

    for it in range(N_ITERATIONS):
        if it in done_iters:
            continue
        t0 = time.time()
        rng = np.random.default_rng((SEED, it))
        outer = _relabel_outer_resample(raw_end_to_end, rng)
        inner = _inner_resample_replicates(outer, rng)
        pw = pointwise_statistics(inner, bootstrap_iterations=20,
                                   bootstrap_seed=int(rng.integers(0, 2 ** 31 - 1)))
        n_total = len(pw)
        n_zero_variance = int(pw["zero_variance_flag"].sum())
        n_l0_zero_variance = int(pw.loc[pw["L"] == 0, "zero_variance_flag"].sum())
        n_l1_zero_variance = int(pw.loc[pw["L"] == 1, "zero_variance_flag"].sum())
        n_non_finite_unexplained = int(len(pw[(~np.isfinite(pw["SNR_est"])) & (~pw["zero_variance_flag"])]))

        diag_row = {
            "iteration": it, "n_total_cells": n_total, "n_zero_variance": n_zero_variance,
            "n_l0_zero_variance": n_l0_zero_variance, "n_l1_zero_variance": n_l1_zero_variance,
            "n_non_finite_unexplained": n_non_finite_unexplained,
        }
        try:
            snr_ds = build_h2h4_dataset(pw)
            if snr_ds.empty:
                diag_row.update({"converged": False, "error": "empty dataset after exclusion", "wallclock_s": time.time() - t0})
            else:
                fit = fit_h2h4_model(pw)
                diag_row.update({
                    "converged": fit.converged, "error": None, "wallclock_s": time.time() - t0,
                    "n_obs_fit": fit.n_obs,
                })
                if fit.converged:
                    coef_rows.append({"iteration": it, **fit.params})
        except Exception as exc:  # noqa: BLE001 -- record and continue, never silently drop
            diag_row.update({"converged": False, "error": str(exc), "wallclock_s": time.time() - t0})

        diag_rows.append(diag_row)
        print(f"[iter {it}] {diag_row}", flush=True)

        if (it + 1) % CHECKPOINT_EVERY == 0:
            save_checkpoint(coef_rows, diag_rows)

    save_checkpoint(coef_rows, diag_rows)

    coef_df = pd.DataFrame(coef_rows)
    n_success = len(coef_df)
    ci = {}
    if n_success > 0:
        for coef in ("E:L", "E:R", "L:R:depth_z"):
            if coef in coef_df.columns:
                vals = coef_df[coef].to_numpy()
                lo, hi = np.percentile(vals, [2.5, 97.5])
                ci[coef] = (float(lo), float(hi))

    diag_df = pd.DataFrame(diag_rows)
    summary = {
        "n_iterations_requested": N_ITERATIONS,
        "n_iterations_successful": n_success,
        "seed": SEED,
        "percentile_ci": ci,
        "median_E_L": float(coef_df["E:L"].median()) if n_success else None,
        "mean_n_zero_variance_per_iteration": float(diag_df["n_zero_variance"].mean()),
        "max_n_zero_variance_in_a_single_iteration": int(diag_df["n_zero_variance"].max()),
        "any_l1_zero_variance_ever_observed_across_resamples": bool((diag_df["n_l1_zero_variance"] > 0).any()),
        "any_non_finite_unexplained_ever_observed": bool((diag_df["n_non_finite_unexplained"] > 0).any()),
    }
    (OUT_DIR / "init_resample_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
