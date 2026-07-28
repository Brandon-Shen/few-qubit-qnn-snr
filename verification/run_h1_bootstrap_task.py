"""Task C.1: H1 (exact-signal) bootstrap, run at full/near-full iteration count.

Standalone -- does not touch results/_checkpoints or results/bootstrap_coefficients.parquet.
Checkpoints to verification/_bootstrap_checkpoints/h1_boot.parquet (resumable, same
mechanism qnn_snr/stats/bootstrap.py uses for the confirmatory pipeline's own bootstrap).

Run from the repo root (intended to run in the background -- this can take ~1-3 hours):
    python verification/run_h1_bootstrap_task.py --iterations 2000
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from qnn_snr.schema import read_tidy_dataset
from qnn_snr.stats.bootstrap import run_h1_bootstrap

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_DIR = Path(__file__).parent / "_bootstrap_checkpoints"
CHECKPOINT_PATH = CHECKPOINT_DIR / "h1_boot.parquet"
SEED = 55001  # distinct from the confirmatory pipeline's own bootstrap seed (12345/12346)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=2000)
    args = ap.parse_args()

    exact_df = read_tidy_dataset(REPO_ROOT / "results" / "raw" / "exact.parquet")
    exact_df = exact_df[exact_df["analysis_mode"] == "statevector_exact"]
    print(f"[{time.strftime('%H:%M:%S')}] loaded {len(exact_df)} exact-signal rows; "
          f"target {args.iterations} iterations, checkpointing to {CHECKPOINT_PATH}", flush=True)

    t0 = time.time()
    result = run_h1_bootstrap(exact_df, n_iterations=args.iterations, seed=SEED,
                               min_success_fraction=0.9, checkpoint_path=CHECKPOINT_PATH,
                               checkpoint_every=5)
    dt = time.time() - t0

    summary = {
        "n_requested": result.n_requested,
        "n_successful": result.n_successful,
        "success_fraction_met": result.success_fraction_met,
        "failed_iterations": result.failed_iterations,
        "percentile_ci": result.percentile_ci,
        "seed": result.seed,
        "wall_clock_seconds": dt,
    }
    (Path(__file__).parent / "h1_bootstrap_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"[{time.strftime('%H:%M:%S')}] DONE. n_successful={result.n_successful}/{result.n_requested} "
          f"wall_clock={dt:.1f}s ({dt/3600:.2f}h)", flush=True)
    print(f"percentile_ci: {result.percentile_ci}", flush=True)


if __name__ == "__main__":
    main()
