"""H2 replication Stage 1: bootstrap step with tight per-iteration
checkpointing.

The generic `qnn_snr bootstrap` CLI command's checkpoint interval
(default checkpoint_every=100 for H1, =50 for H2-H4) never triggers
within a 30-iteration target, so a single interruption loses all
progress -- this happened once already in this session (background jobs
were killed by something external, with no Python-level error, partway
through the generic CLI's bootstrap step). This script calls the same
underlying qnn_snr.stats.bootstrap functions directly with
checkpoint_every=3 instead, so at most 3 iterations of work are ever at
risk.

Run from the repo root: python scripts/run_h2_replication_stage1_bootstrap.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qnn_snr.config import load_config  # noqa: E402
from qnn_snr.schema import read_tidy_dataset  # noqa: E402
from qnn_snr.stats.bootstrap import confirmatory_bootstrap_ci, run_h1_bootstrap, run_h2h4_bootstrap  # noqa: E402

CONFIG_PATH = REPO_ROOT / "configs" / "h2_replication_v1_stage1.yaml"


def main() -> None:
    cfg = load_config(CONFIG_PATH)
    results_dir = REPO_ROOT / "results" / "h2_replication_v1" / "_pipeline_output_stage1"
    ckpt_dir = results_dir / "_checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    exact_df = read_tidy_dataset(results_dir / "raw" / "exact.parquet")
    shot_df = read_tidy_dataset(results_dir / "raw" / "finite_shot_end_to_end.parquet")

    n_iter = cfg.stats.bootstrap.iterations
    print(f"Running H1 bootstrap: n={n_iter}, checkpoint_every=3")
    h1_boot = run_h1_bootstrap(
        exact_df, n_iter, cfg.stats.bootstrap.seed, cfg.stats.bootstrap.min_success_fraction,
        checkpoint_path=ckpt_dir / "h1_boot.parquet", checkpoint_every=3,
    )
    print(f"H1: {h1_boot.n_successful}/{h1_boot.n_requested} successful")

    print(f"Running H2-H4 bootstrap: n={n_iter}, checkpoint_every=3")
    h2h4_boot = run_h2h4_bootstrap(
        shot_df, n_iter, cfg.stats.bootstrap.seed + 1, cfg.stats.bootstrap.min_success_fraction,
        pointwise_bootstrap_iterations=20,
        checkpoint_path=ckpt_dir / "h2h4_boot.parquet", checkpoint_every=3,
    )
    print(f"H2-H4: {h2h4_boot.n_successful}/{h2h4_boot.n_requested} successful")

    ci = confirmatory_bootstrap_ci(h1_boot, h2h4_boot)
    summary = {
        "n_iterations_requested": n_iter,
        "h1_n_successful": h1_boot.n_successful,
        "h2h4_n_successful": h2h4_boot.n_successful,
        "h2h4_failed_iterations": h2h4_boot.failed_iterations,
        "percentile_ci": {k: list(v) for k, v in ci.items()},
    }
    (results_dir / "bootstrap_summary_tight_checkpoints.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
