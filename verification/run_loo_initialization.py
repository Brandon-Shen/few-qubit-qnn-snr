"""QMI/QIP robustness package, Task 3 part D: leave-one-initialization-out
influence analysis.

Refits the adopted end-to-end full-sweep H2-H4 model 50 times, each time
excluding one complete initialization_id (all its configurations, block
counts, budgets, and matched parameters), and records the three target
coefficients, SEs, raw p-values, and convergence status per deletion.

Checkpointed every iteration so an interrupted run loses no completed work
(same convention as qnn_snr/stats/bootstrap.py's checkpointing).

Run from the repo root: python verification/run_loo_initialization.py
Estimated wall-clock: ~30-40s/refit x 50 = 25-35 minutes on this machine
(measured single-fit cost in verification/qmi_qip_analysis_inputs.md
Section 3 was 31.8s; each LOO refit is a plain fit_h2h4_model call on
~2% fewer rows, no bootstrap resampling overhead, so a similar per-fit cost
is expected).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from qnn_snr.stats.models import fit_h2h4_model

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_PATH = REPO_ROOT / "verification" / "_bootstrap_checkpoints" / "loo_initialization.parquet"
TARGET_COEFS = ["E:L", "E:R", "L:R:depth_z"]


def load_checkpoint():
    if CHECKPOINT_PATH.exists():
        return pd.read_parquet(CHECKPOINT_PATH).to_dict("records")
    return []


def save_checkpoint(rows):
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(CHECKPOINT_PATH, index=False)


def main():
    pw = pd.read_parquet(REPO_ROOT / "results" / "production_confirmatory" / "pointwise_gradient_statistics.parquet")
    eo_full = pw[pw["analysis_mode"] == "finite_shot_end_to_end"].copy()
    init_ids = sorted(eo_full["initialization_id"].unique())
    assert len(init_ids) == 50, f"expected 50 initializations, found {len(init_ids)}"

    rows = load_checkpoint()
    done = {r["excluded_initialization_id"] for r in rows}
    print(f"resuming: {len(done)}/50 already completed", flush=True)

    for init_id in init_ids:
        if init_id in done:
            continue
        t0 = time.time()
        subset = eo_full[eo_full["initialization_id"] != init_id]
        try:
            res = fit_h2h4_model(subset)
            dt = time.time() - t0
            row = {"excluded_initialization_id": int(init_id), "converged": res.converged,
                   "n_obs": res.n_obs, "wallclock_s": dt}
            for coef in TARGET_COEFS:
                est, se = res.params[coef], res.bse[coef]
                z = est / se
                p = 2 * (1 - stats.norm.cdf(abs(z)))
                row[f"{coef}_estimate"] = est
                row[f"{coef}_se"] = se
                row[f"{coef}_p"] = p
            print(f"[init {init_id}] done in {dt:.1f}s converged={res.converged} "
                  f"E:L={row['E:L_estimate']:+.6f} E:R={row['E:R_estimate']:+.6f} "
                  f"L:R:depth_z={row['L:R:depth_z_estimate']:+.6f}", flush=True)
        except Exception as exc:
            dt = time.time() - t0
            row = {"excluded_initialization_id": int(init_id), "converged": False,
                   "n_obs": len(subset), "wallclock_s": dt, "error": str(exc)}
            print(f"[init {init_id}] FAILED after {dt:.1f}s: {exc!r}", flush=True)
        rows.append(row)
        save_checkpoint(rows)

    out_df = pd.DataFrame(rows).sort_values("excluded_initialization_id")
    out_path = REPO_ROOT / "results" / "sensitivity_analyses" / "leave_one_initialization_out_coefficients.csv"
    out_df.to_csv(out_path, index=False)
    print(f"\nwrote {out_path} ({len(out_df)} rows)")


if __name__ == "__main__":
    main()
