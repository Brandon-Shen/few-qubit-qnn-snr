"""End-to-end-only counterpart of run_h2h4_bootstrap_shard_lowmem.py.

Extends the H2-H4 bootstrap on the CONFIRMATORY (end-to-end-only) dataset
past the n=8 from-scratch reproducibility check in
run_h2h4_endtoend_regression_test.py. Uses a seed stream distinct from every
prior pooled-data shard (66001/76001/86001/96001/106001) and from the
regression-test seed (266001): shard N uses seed 366001 + N*10000.

Run from the repo root:
    python verification/run_h2h4_bootstrap_shard_endtoend_only.py --shard-id 0 --iterations 50
    python verification/run_h2h4_bootstrap_shard_endtoend_only.py --shard-id 1 --iterations 50
    ...

Checkpoints to _bootstrap_checkpoints/h2h4_boot_endtoend_shard{N}.parquet --
a distinct filename from every pooled-data shard checkpoint, so this never
collides with or overwrites pooled-data results.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from qnn_snr.schema import read_tidy_dataset

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_DIR = Path(__file__).parent / "_bootstrap_checkpoints"
CONFIRMATORY_MODE = "finite_shot_end_to_end"
BASE_SEED = 366001
SEED_STRIDE = 10_000

sys.path.insert(0, str(Path(__file__).parent))
from h2h4_bootstrap_lowmem import _precompute_cell_index, run_h2h4_bootstrap_lowmem  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard-id", type=int, required=True)
    ap.add_argument("--iterations", type=int, required=True)
    ap.add_argument("--pointwise-bootstrap-iterations", type=int, default=0,
                    help="Unused pointwise mean-CI draws; 0 emits only the unchanged mixed-model input columns")
    args = ap.parse_args()

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_path = CHECKPOINT_DIR / f"h2h4_boot_endtoend_shard{args.shard_id}.parquet"
    seed = BASE_SEED + args.shard_id * SEED_STRIDE

    t_load = time.time()
    shot_df = read_tidy_dataset(REPO_ROOT / "results" / "production_confirmatory" / "raw" / f"{CONFIRMATORY_MODE}.parquet")
    print(f"[shard {args.shard_id}] loaded {len(shot_df)} rows in {time.time()-t_load:.1f}s", flush=True)

    t_pre = time.time()
    pre = _precompute_cell_index(shot_df)
    del shot_df
    print(f"[shard {args.shard_id}] precomputed cell index ({len(pre.sorted_full_keys)} cells) in "
          f"{time.time()-t_pre:.1f}s; seed={seed}, target={args.iterations} iterations, "
          f"checkpoint={checkpoint_path}", flush=True)

    t0 = time.time()
    # --iterations is a successful-fit target.  If a fit fails or is rejected,
    # extend the deterministic (seed, iteration) stream until the target is met.
    attempted_target = args.iterations
    while True:
        result = run_h2h4_bootstrap_lowmem(
            raw_shot_df=None, n_iterations=attempted_target, seed=seed, min_success_fraction=0.0,
            pointwise_bootstrap_iterations=args.pointwise_bootstrap_iterations,
            checkpoint_path=checkpoint_path, checkpoint_every=1, precomputed=pre, verbose=True,
        )
        if result.n_successful >= args.iterations:
            break
        attempted_target += args.iterations - result.n_successful
    dt = time.time() - t0

    summary = {
        "shard_id": args.shard_id,
        "seed": seed,
        "successful_target": args.iterations,
        "n_attempted": result.n_successful + len(result.failed_iterations),
        "n_requested_stream_positions": result.n_requested,
        "n_successful": result.n_successful,
        "failed_iterations": result.failed_iterations,
        "n_rejected": 0,
        "pointwise_bootstrap_iterations": args.pointwise_bootstrap_iterations,
        "wall_clock_seconds": dt,
        "implementation": "lowmem_redesign_endtoend_only",
    }
    summary_path = CHECKPOINT_DIR / f"h2h4_boot_endtoend_shard{args.shard_id}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"[shard {args.shard_id}] DONE. n_successful={result.n_successful}/{result.n_requested} "
          f"wall_clock={dt:.1f}s ({dt/60:.1f}min)", flush=True)


if __name__ == "__main__":
    main()
