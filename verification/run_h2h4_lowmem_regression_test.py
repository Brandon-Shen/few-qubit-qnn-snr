"""Step 3 of the memory redesign task: regression-test the low-memory H2-H4
bootstrap redesign (verification/h2h4_bootstrap_lowmem.py) against the real,
already-completed 8-iteration ground truth
(verification/h2h4_bootstrap_combined_draws.parquet, seed 66001, shard 0,
iterations 0-7) on the REAL full combined dataset.

Also reports peak RSS (via a background psutil sampler thread) so the
redesign's memory footprint can be compared directly against the ~16GB peak
found for the original implementation.

Writes verification/h2h4_lowmem_regression_test_result.json with the
draws, per-coefficient max abs diff vs ground truth, and pass/fail.

Does NOT touch verification/_bootstrap_checkpoints/h2h4_boot_shard0.parquet
(the original ground-truth checkpoint) -- checkpoints to a new file,
verification/_bootstrap_checkpoints/h2h4_boot_lowmem_regression.parquet.
"""
from __future__ import annotations

import gc
import json
import threading
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psutil

from qnn_snr.schema import read_tidy_dataset

import sys
sys.path.insert(0, str(Path(__file__).parent))
from h2h4_bootstrap_lowmem import _precompute_cell_index, run_h2h4_bootstrap_lowmem

REPO_ROOT = Path(__file__).resolve().parent.parent
SHOT_MODES = ("finite_shot_conditional", "finite_shot_end_to_end")
SEED = 66001
N_ITERATIONS = 8
GROUND_TRUTH_PATH = Path(__file__).parent / "h2h4_bootstrap_combined_draws.parquet"
CHECKPOINT_PATH = Path(__file__).parent / "_bootstrap_checkpoints" / "h2h4_boot_lowmem_regression.parquet"
TARGET_COEFS = ("E:L", "E:R", "L:R:depth_z")

proc = psutil.Process()


class PeakSampler:
    def __init__(self, interval: float = 0.2):
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None
        self.peak_rss = 0

    def _run(self):
        while not self._stop.is_set():
            self.peak_rss = max(self.peak_rss, proc.memory_info().rss)
            time.sleep(self.interval)

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)


def main():
    sampler = PeakSampler()
    sampler.start()

    def rss_gb():
        gc.collect()
        return proc.memory_info().rss / 1e9

    print(f"start RSS = {rss_gb():.3f} GB", flush=True)

    t0 = time.time()
    parts = [read_tidy_dataset(REPO_ROOT / "results" / "raw" / f"{m}.parquet") for m in SHOT_MODES]
    raw_shot_df = pd.concat(parts, ignore_index=True)
    del parts
    t_load = time.time() - t0
    print(f"loaded {len(raw_shot_df)} rows in {t_load:.1f}s; RSS = {rss_gb():.3f} GB", flush=True)

    t0 = time.time()
    pre = _precompute_cell_index(raw_shot_df)
    t_pre = time.time() - t0
    print(f"precomputed cell index ({len(pre.sorted_full_keys)} cells) in {t_pre:.1f}s; "
          f"RSS = {rss_gb():.3f} GB", flush=True)

    # raw_shot_df itself is no longer needed once pre-computation is done --
    # everything the per-iteration loop needs lives in `pre` (numpy arrays).
    del raw_shot_df
    print(f"dropped raw_shot_df; RSS = {rss_gb():.3f} GB", flush=True)

    t0 = time.time()
    result = run_h2h4_bootstrap_lowmem(
        raw_shot_df=None, n_iterations=N_ITERATIONS, seed=SEED, min_success_fraction=0.0,
        checkpoint_path=CHECKPOINT_PATH, checkpoint_every=1, precomputed=pre, verbose=True,
    )
    t_run = time.time() - t0
    print(f"run_h2h4_bootstrap_lowmem: {result.n_successful}/{result.n_requested} successful in "
          f"{t_run:.1f}s ({t_run / max(result.n_successful,1):.1f}s/iter); RSS = {rss_gb():.3f} GB", flush=True)

    sampler.stop()
    peak_gb = sampler.peak_rss / 1e9
    print(f"OVERALL PEAK RSS = {peak_gb:.3f} GB", flush=True)

    ground_truth = pd.read_parquet(GROUND_TRUTH_PATH).sort_values("iteration").reset_index(drop=True)
    new_draws = result.coefficients.sort_values("iteration").reset_index(drop=True)

    comparison = {}
    overall_pass = True
    for coef in TARGET_COEFS:
        if coef not in ground_truth.columns or coef not in new_draws.columns:
            comparison[coef] = {"error": "coefficient missing"}
            overall_pass = False
            continue
        gt = ground_truth[coef].to_numpy()
        nd = new_draws[coef].to_numpy()
        if len(gt) != len(nd):
            comparison[coef] = {"error": f"length mismatch gt={len(gt)} new={len(nd)}"}
            overall_pass = False
            continue
        max_abs_diff = float(np.max(np.abs(gt - nd)))
        allclose_tight = bool(np.allclose(gt, nd, atol=1e-9, rtol=1e-6))
        comparison[coef] = {
            "ground_truth": gt.tolist(),
            "new_draws": nd.tolist(),
            "max_abs_diff": max_abs_diff,
            "allclose_atol_1e-9_rtol_1e-6": allclose_tight,
        }
        if not allclose_tight:
            overall_pass = False

    out = {
        "seed": SEED,
        "n_iterations": N_ITERATIONS,
        "n_successful": result.n_successful,
        "failed_iterations": result.failed_iterations,
        "timings_seconds": {"load": t_load, "precompute": t_pre, "run_8_iterations": t_run},
        "peak_rss_gb": peak_gb,
        "comparison": comparison,
        "overall_pass": overall_pass,
    }
    out_path = Path(__file__).parent / "h2h4_lowmem_regression_test_result.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nOVERALL PASS = {overall_pass}", flush=True)
    for coef, c in comparison.items():
        if "error" in c:
            print(f"  {coef}: ERROR {c['error']}", flush=True)
        else:
            print(f"  {coef}: max_abs_diff={c['max_abs_diff']:.3e} allclose(1e-9,1e-6)={c['allclose_atol_1e-9_rtol_1e-6']}",
                  flush=True)
    print(f"wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
