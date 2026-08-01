"""H2 robustness/replication package, Phase 5, Stage 0: a real (not
guessed) pilot benchmark to calibrate the resource estimate for the
independent replication, before any Stage 1/2 execution decision.

Generates a small, disposable slice under the replication seed namespace
(1 configuration, 1 depth, 2 initializations, R=20 replicates, end-to-end
mode only) purely to measure per-replicate wall-clock and peak RSS on this
machine. This is NOT replication data: wrong initialization count, wrong
configuration coverage, never reused for any reported statistic. Output
goes to a directory this script deletes on successful completion (kept
only if RSS/timing recording fails, for debugging).

Run from the repo root: python scripts/run_h2_replication_pilot_benchmark.py
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import psutil  # noqa: E402

from qnn_snr.config import ExperimentConfig, config_hash  # noqa: E402
from qnn_snr.replicate import generate_shot_rows  # noqa: E402
from qnn_snr.schema import write_tidy_dataset  # noqa: E402

OUT_DIR = REPO_ROOT / "results" / "h2_robustness" / "replication_design"
PILOT_DISPOSABLE_DIR = REPO_ROOT / "results" / "h2_replication_v1" / "_pilot_benchmark_disposable"

REPLICATION_SEED_ROOT = 3872531887


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cfg = ExperimentConfig(
        name="h2_replication_pilot_benchmark",
        seed_root=REPLICATION_SEED_ROOT,
    )
    cfg.design.configurations = [1]
    cfg.design.n_initializations = 2
    cfg.design.replicates = 20
    cfg.circuit.depths = [4]  # representative mid-depth cell, not the cheapest (D=1) or most expensive (D=6)
    cfg.budget.values = [1000]  # representative mid-budget cell

    process = psutil.Process()
    rss_before = process.memory_info().rss

    t0 = time.time()
    rows = generate_shot_rows(cfg, "finite_shot_end_to_end", git_commit="pilot_benchmark_not_a_real_commit")
    dt = time.time() - t0

    rss_after = process.memory_info().rss

    PILOT_DISPOSABLE_DIR.mkdir(parents=True, exist_ok=True)
    df = write_tidy_dataset(rows, PILOT_DISPOSABLE_DIR / "pilot_slice.parquet")
    disk_bytes = (PILOT_DISPOSABLE_DIR / "pilot_slice.parquet").stat().st_size

    n_cells = cfg.design.n_initializations * len(cfg.design.configurations) * cfg.task.n_qubits * cfg.circuit.depths[0]
    n_replicate_evals = n_cells * cfg.design.replicates

    # --- Extrapolation to full Stage 1 design (8 configs, 5 depths, 4 budgets, 50 inits, R=30) ---
    full_design_replicate_evals = 8 * 5 * 4 * 50 * 30  # per-parameter-cell count varies by depth; this
    # undercounts slightly since deeper depths have more parameters -- deliberately conservative
    # (production's own measured 26-minute figure below is the primary estimate; this pilot
    # cross-checks it independently rather than replacing it).
    per_replicate_eval_seconds = dt / n_replicate_evals if n_replicate_evals else float("nan")

    result = {
        "pilot_config": {
            "seed_root": cfg.seed_root, "n_initializations": cfg.design.n_initializations,
            "configurations": cfg.design.configurations, "depths": cfg.circuit.depths,
            "budgets": cfg.budget.values, "replicates": cfg.design.replicates,
        },
        "rows_generated": len(df),
        "wallclock_seconds": dt,
        "rss_before_bytes": int(rss_before),
        "rss_after_bytes": int(rss_after),
        "rss_delta_bytes": int(rss_after - rss_before),
        "disk_bytes_for_slice": disk_bytes,
        "per_replicate_eval_seconds_measured": per_replicate_eval_seconds,
        "production_measured_full_end_to_end_generation_seconds": 26 * 60,  # run_manifest.json, R=30
        "production_measured_seconds_per_R30_generation_row_group": (26 * 60) / (8 * 5 * 4 * 50 * 30),
        "note": "This is a cross-check pilot, not the primary estimate. The primary Stage 1 "
                "wall-clock estimate (~26-30 min) comes from production's own measured R=30 "
                "generation time (verification/h2_robustness_replication_plan.md Section 3.3), "
                "since Stage 1 uses the identical R_rep=30 and the identical design shape.",
    }
    (OUT_DIR / "pilot_benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result, indent=2))

    shutil.rmtree(PILOT_DISPOSABLE_DIR, ignore_errors=True)
    print(f"\ndeleted disposable pilot output at {PILOT_DISPOSABLE_DIR} (not replication data)")


if __name__ == "__main__":
    main()
