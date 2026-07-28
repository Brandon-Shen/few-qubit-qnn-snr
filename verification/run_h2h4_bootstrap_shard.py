"""Task C.2: one independent shard of the H2-H4 (estimator-SNR) bootstrap.

The pipeline (qnn_snr/stats/bootstrap.py, per ASSUMPTIONS.md A21) runs bootstrap
iterations sequentially and does not support sharding across processes. This script
is the minimal sharding support the task asked for: each invocation is one
independent shard with its own seed and its own checkpoint file, runnable as a
separate OS process in parallel with other shards. combine_h2h4_shards.py pools all
shards' checkpoint files into one percentile-CI computation afterward.

Standalone -- does not touch results/_checkpoints or results/bootstrap_coefficients.parquet.
Checkpoints to verification/_bootstrap_checkpoints/h2h4_boot_shard{N}.parquet.

Run from the repo root (intended to run in the background, one process per shard):
    python verification/run_h2h4_bootstrap_shard.py --shard-id 0 --iterations 20
    python verification/run_h2h4_bootstrap_shard.py --shard-id 1 --iterations 20
    ...
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from qnn_snr.schema import read_tidy_dataset
from qnn_snr.stats.bootstrap import run_h2h4_bootstrap

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_DIR = Path(__file__).parent / "_bootstrap_checkpoints"
SHOT_MODES = ("finite_shot_conditional", "finite_shot_end_to_end")
BASE_SEED = 66001  # distinct from the confirmatory pipeline's own bootstrap seed (12346)
SEED_STRIDE = 10_000  # per shard, so shard seeds never collide with each other's (seed, it) draws


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard-id", type=int, required=True)
    ap.add_argument("--iterations", type=int, required=True)
    args = ap.parse_args()

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_path = CHECKPOINT_DIR / f"h2h4_boot_shard{args.shard_id}.parquet"
    seed = BASE_SEED + args.shard_id * SEED_STRIDE

    t_load = time.time()
    parts = [read_tidy_dataset(REPO_ROOT / "results" / "raw" / f"{m}.parquet") for m in SHOT_MODES]
    shot_df = pd.concat(parts, ignore_index=True)
    print(f"[shard {args.shard_id}] loaded {len(shot_df)} rows in {time.time()-t_load:.1f}s; "
          f"seed={seed}, target={args.iterations} iterations, checkpoint={checkpoint_path}", flush=True)

    t0 = time.time()
    result = run_h2h4_bootstrap(shot_df, n_iterations=args.iterations, seed=seed,
                                 min_success_fraction=0.0, checkpoint_path=checkpoint_path,
                                 checkpoint_every=1)
    dt = time.time() - t0

    summary = {
        "shard_id": args.shard_id,
        "seed": seed,
        "n_requested": result.n_requested,
        "n_successful": result.n_successful,
        "failed_iterations": result.failed_iterations,
        "wall_clock_seconds": dt,
    }
    (CHECKPOINT_DIR / f"h2h4_boot_shard{args.shard_id}_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"[shard {args.shard_id}] DONE. n_successful={result.n_successful}/{result.n_requested} "
          f"wall_clock={dt:.1f}s ({dt/60:.1f}min)", flush=True)


if __name__ == "__main__":
    main()
