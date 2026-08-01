"""Low-memory-redesign counterpart of verification/run_h2h4_bootstrap_shard.py.

Same shard/seed convention (BASE_SEED=66001, SEED_STRIDE=10_000, shard N uses
seed BASE_SEED + N*SEED_STRIDE) so shard 0 with this script continues the
exact same (seed, iteration) draw sequence as the original
h2h4_boot_shard0.parquet checkpoint -- i.e. running shard 0 here for more
iterations *extends* that checkpoint with bit-identical iterations 0-7 (a
no-op on those, since the checkpoint skip logic keys off `iteration`) plus
new iterations 8, 9, 10, ... computed via the low-memory redesign.

Only run this against shard 0 to extend the existing checkpoint AFTER the
regression test (run_h2h4_lowmem_regression_test.py) has confirmed the
low-memory redesign reproduces iterations 0-7 bit-identically. Other shard
ids (>=1) start fresh checkpoints under a distinct filename so they never
collide with or overwrite the original shard0 ground truth.

Run from the repo root:
    python verification/run_h2h4_bootstrap_shard_lowmem.py --shard-id 0 --iterations 30
    python verification/run_h2h4_bootstrap_shard_lowmem.py --shard-id 1 --iterations 30
    ...
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

from qnn_snr.schema import read_tidy_dataset

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_DIR = Path(__file__).parent / "_bootstrap_checkpoints"
SHOT_MODES = ("finite_shot_conditional", "finite_shot_end_to_end")
BASE_SEED = 66001
SEED_STRIDE = 10_000

sys.path.insert(0, str(Path(__file__).parent))
from h2h4_bootstrap_lowmem import _precompute_cell_index, run_h2h4_bootstrap_lowmem  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard-id", type=int, required=True)
    ap.add_argument("--iterations", type=int, required=True)
    args = ap.parse_args()

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    # Uses the SAME naming convention as the original run_h2h4_bootstrap_shard.py
    # (h2h4_boot_shard{N}.parquet) for every shard id, including 0, so that
    # combine_h2h4_shards.py pools all shards -- original and lowmem-redesign
    # alike -- without modification. Shard 0 therefore *extends* the existing
    # ground-truth checkpoint (iterations 0-7 already present are skipped by
    # the checkpoint-resume logic; only new iterations 8+ are computed). This
    # is intentional and only done because the regression test
    # (run_h2h4_lowmem_regression_test.py) already confirmed the low-memory
    # redesign reproduces iterations 0-7 bit-identically -- see guardrails in
    # the module docstring above.
    checkpoint_path = CHECKPOINT_DIR / f"h2h4_boot_shard{args.shard_id}.parquet"
    seed = BASE_SEED + args.shard_id * SEED_STRIDE

    t_load = time.time()
    parts = [read_tidy_dataset(REPO_ROOT / "results" / "production_confirmatory" / "raw" / f"{m}.parquet") for m in SHOT_MODES]
    shot_df = pd.concat(parts, ignore_index=True)
    print(f"[shard {args.shard_id}] loaded {len(shot_df)} rows in {time.time()-t_load:.1f}s", flush=True)

    t_pre = time.time()
    pre = _precompute_cell_index(shot_df)
    del shot_df
    print(f"[shard {args.shard_id}] precomputed cell index ({len(pre.sorted_full_keys)} cells) in "
          f"{time.time()-t_pre:.1f}s; seed={seed}, target={args.iterations} iterations, "
          f"checkpoint={checkpoint_path}", flush=True)

    t0 = time.time()
    result = run_h2h4_bootstrap_lowmem(
        raw_shot_df=None, n_iterations=args.iterations, seed=seed, min_success_fraction=0.0,
        checkpoint_path=checkpoint_path, checkpoint_every=1, precomputed=pre, verbose=True,
    )
    dt = time.time() - t0

    summary = {
        "shard_id": args.shard_id,
        "seed": seed,
        "n_requested": result.n_requested,
        "n_successful": result.n_successful,
        "failed_iterations": result.failed_iterations,
        "wall_clock_seconds": dt,
        "implementation": "lowmem_redesign",
    }
    # Distinct suffix from the original shard0 summary file (h2h4_boot_shard0_summary.json,
    # which belongs to the original run and is left untouched) so this run's own
    # summary (covering only the newly-computed lowmem iterations) doesn't clobber it.
    summary_path = CHECKPOINT_DIR / f"h2h4_boot_shard{args.shard_id}_lowmem_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"[shard {args.shard_id}] DONE. n_successful={result.n_successful}/{result.n_requested} "
          f"wall_clock={dt:.1f}s ({dt/60:.1f}min)", flush=True)


if __name__ == "__main__":
    main()
