"""QMI/QIP robustness package, Task 4: pool and summarize the extended
end-to-end-only H2-H4 bootstrap.

Pools every checkpoint that represents genuinely independent draws:
  - h2h4_boot_endtoend_regression_a.parquet (seed 266001, 8 draws) -- the
    "pass_a" from-scratch reproducibility check in
    verification/h2h4_bootstrap_endtoend_only.md Section 2.
  - h2h4_boot_endtoend_shard{0,1,2,...}.parquet (seeds 366001, 376001,
    386001, ... = 366001 + shard_id*10000) -- the extension shards.

Deliberately EXCLUDES h2h4_boot_endtoend_regression_b.parquet: that
checkpoint is a bit-identical duplicate of regression_a (same seed 266001,
run a second time purely to verify reproducibility -- see
verification/h2h4_bootstrap_endtoend_only.md Section 2). Pooling it in
would double-count 8 draws and understate the reported interval's true
Monte Carlo uncertainty. This matches the existing convention already
established in that document ("40 total draws" = 8 + 16 + 16, not 48).

Reports checkpoint summaries at n in {40, 100, 200, 400, 600, 800, 1000}
"where available" (i.e. only for thresholds <= the current pooled count),
ordered by a fixed, deterministic draw sequence (regression_a first, then
shards in ascending shard-id order, iterations ascending within each) so
"movement since the previous checkpoint" is well-defined and reproducible
regardless of which order shards happened to finish in wall-clock time.

Run from the repo root: python verification/summarize_bootstrap_checkpoints.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
CKPT_DIR = REPO_ROOT / "verification" / "_bootstrap_checkpoints"
TARGET_COEFS = ["E:L", "E:R", "L:R:depth_z"]
CHECKPOINT_NS = [40, 100, 200, 400, 600, 800, 1000]

POOL_SOURCES = [
    ("regression_a", "h2h4_boot_endtoend_regression_a", 266001),
    ("shard0", "h2h4_boot_endtoend_shard0", 366001),
    ("shard1", "h2h4_boot_endtoend_shard1", 376001),
    ("shard2", "h2h4_boot_endtoend_shard2", 386001),
    ("shard3", "h2h4_boot_endtoend_shard3", 396001),
    ("shard4", "h2h4_boot_endtoend_shard4", 406001),
]


def load_source(stream_name: str, filestem: str, seed: int):
    p = CKPT_DIR / f"{filestem}.parquet"
    meta_p = CKPT_DIR / f"{filestem}.meta.json"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df = df.copy()
    df["_stream"] = stream_name
    df["_seed"] = seed
    failed = []
    if meta_p.exists():
        failed = json.loads(meta_p.read_text()).get("failed_iterations", [])
    return df, failed


def percentile_ci(values: np.ndarray, alpha: float = 0.05):
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return float("nan"), float("nan")
    lo, hi = np.percentile(finite, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def main():
    frames = []
    n_failed_total = 0
    stream_report = []
    for stream_name, filestem, seed in POOL_SOURCES:
        loaded = load_source(stream_name, filestem, seed)
        if loaded is None:
            continue
        df, failed = loaded
        frames.append(df)
        n_failed_total += len(failed)
        stream_report.append({
            "stream": stream_name, "seed": seed, "n_success": len(df),
            "n_failed": len(failed), "iterations": sorted(df["iteration"].tolist()),
            "failed_iterations": failed,
        })

    pooled = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    n_pooled = len(pooled)
    print(f"Pooled draws (excluding regression_b duplicate check): {n_pooled}")
    for s in stream_report:
        print(f"  {s['stream']} (seed {s['seed']}): {s['n_success']} success, {s['n_failed']} failed")

    # write iteration-level parquet (lossless)
    iter_path = REPO_ROOT / "results" / "bootstrap_end_to_end_h2_h4_iterations.parquet"
    if not pooled.empty:
        pooled.to_parquet(iter_path, index=False)
        print(f"wrote {iter_path} ({n_pooled} rows)")

    # deterministic pooling order for checkpoint-prefix definitions
    stream_order = {name: i for i, (name, _, _) in enumerate(POOL_SOURCES)}
    if not pooled.empty:
        pooled_sorted = pooled.copy()
        pooled_sorted["_stream_order"] = pooled_sorted["_stream"].map(stream_order)
        pooled_sorted = pooled_sorted.sort_values(["_stream_order", "iteration"]).reset_index(drop=True)
    else:
        pooled_sorted = pooled

    checkpoint_rows = []
    prev = {c: None for c in TARGET_COEFS}
    for n in CHECKPOINT_NS:
        if n > n_pooled:
            break
        prefix = pooled_sorted.iloc[:n]
        for coef in TARGET_COEFS:
            vals = prefix[coef].to_numpy()
            median = float(np.median(vals[np.isfinite(vals)])) if np.isfinite(vals).any() else float("nan")
            lo, hi = percentile_ci(vals)
            width = hi - lo
            includes_zero = bool(lo <= 0 <= hi) if np.isfinite(lo) and np.isfinite(hi) else None
            move_lo = None if prev[coef] is None else lo - prev[coef][0]
            move_hi = None if prev[coef] is None else hi - prev[coef][1]
            checkpoint_rows.append({
                "n": n, "coefficient": coef, "median": median, "ci_lo": lo, "ci_hi": hi,
                "width": width, "includes_zero": includes_zero,
                "lo_move_since_prev": move_lo, "hi_move_since_prev": move_hi,
            })
            prev[coef] = (lo, hi)

    ckpt_df = pd.DataFrame(checkpoint_rows)
    ckpt_path = REPO_ROOT / "results" / "bootstrap_end_to_end_h2_h4_checkpoints.csv"
    ckpt_df.to_csv(ckpt_path, index=False)
    print(f"\nwrote {ckpt_path}")
    print(ckpt_df.to_string())

    # final summary (using ALL pooled draws, not just the last listed checkpoint)
    summary_rows = []
    for coef in TARGET_COEFS:
        vals = pooled[coef].to_numpy() if not pooled.empty else np.array([])
        lo, hi = percentile_ci(vals)
        summary_rows.append({
            "coefficient": coef, "n_pooled": n_pooled, "n_failed": n_failed_total,
            "fit_failure_rate_pct": 100 * n_failed_total / (n_pooled + n_failed_total) if (n_pooled + n_failed_total) else float("nan"),
            "median": float(np.median(vals)) if len(vals) else float("nan"),
            "ci_lo": lo, "ci_hi": hi, "width": hi - lo if np.isfinite(lo) and np.isfinite(hi) else float("nan"),
            "includes_zero": bool(lo <= 0 <= hi) if np.isfinite(lo) and np.isfinite(hi) else None,
        })
    summary_df = pd.DataFrame(summary_rows)
    summary_path = REPO_ROOT / "results" / "bootstrap_end_to_end_h2_h4_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"\nwrote {summary_path}")
    print(summary_df.to_string())

    stream_report_path = REPO_ROOT / "verification" / "_bootstrap_stream_report.json"
    stream_report_path.write_text(json.dumps(stream_report, indent=2, default=str), encoding="utf-8")
    print(f"wrote {stream_report_path}")


if __name__ == "__main__":
    main()
