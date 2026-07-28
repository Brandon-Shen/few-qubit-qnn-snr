"""Task C.2 combine step: pool every h2h4_boot_shard*.parquet checkpoint under
verification/_bootstrap_checkpoints/ into one set of resampled coefficient draws and
compute percentile CIs for eta_EL's H2 counterpart (E:L), plus beta_ER (E:R) and
beta_LRd (L:R:depth_z) as a free byproduct of the same shard set.

Run any time (safe to run against partial/in-progress shards -- reports whatever
completed iterations exist at the time it's run):
    python verification/combine_h2h4_shards.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

CHECKPOINT_DIR = Path(__file__).parent / "_bootstrap_checkpoints"
ALPHA = 0.05
TARGET_COEFS = ("E:L", "E:R", "L:R:depth_z")


def percentile_ci(values: np.ndarray) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return float("nan"), float("nan")
    lo, hi = np.percentile(finite, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return float(lo), float(hi)


def main():
    shard_files = sorted(CHECKPOINT_DIR.glob("h2h4_boot_shard*.parquet"))
    if not shard_files:
        print(f"no shard checkpoints found under {CHECKPOINT_DIR}")
        return

    frames = []
    per_shard_counts = {}
    for f in shard_files:
        df = pd.read_parquet(f)
        df["shard_file"] = f.name
        frames.append(df)
        per_shard_counts[f.name] = len(df)
    combined = pd.concat(frames, ignore_index=True)

    print(f"shards found: {len(shard_files)}")
    for name, n in per_shard_counts.items():
        print(f"  {name}: {n} successful iterations")
    print(f"total pooled successful iterations: {len(combined)}")

    out = {"n_shards": len(shard_files), "per_shard_successful_iterations": per_shard_counts,
           "total_pooled_successful_iterations": len(combined), "percentile_ci": {}}
    for coef in TARGET_COEFS:
        if coef in combined.columns:
            lo, hi = percentile_ci(combined[coef].to_numpy())
            out["percentile_ci"][coef] = {"lo": lo, "hi": hi, "n": int(combined[coef].notna().sum())}
            print(f"{coef}: 95% percentile CI [{lo:.6f}, {hi:.6f}]  (n={out['percentile_ci'][coef]['n']})")

    out_path = Path(__file__).parent / "h2h4_bootstrap_combined_summary.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    combined.to_parquet(Path(__file__).parent / "h2h4_bootstrap_combined_draws.parquet", index=False)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
