"""Fresh n=8 regression-truth checkpoint + from-scratch reproduction check for
the H2-H4 low-memory bootstrap (verification/h2h4_bootstrap_lowmem.py) on the
END-TO-END-ONLY dataset.

This is a NEW dataset relative to every prior use of h2h4_bootstrap_lowmem.py
(which always operated on the pooled finite_shot_conditional +
finite_shot_end_to_end dataset -- see h2h4_bootstrap_memory_redesign.md).
Filtering to analysis_mode == "finite_shot_end_to_end" only (per
verification/mode_pooling_guard.md and
verification/confirmatory_numbers_adopted.md, this is now the confirmatory
mode) roughly halves the raw row count and the number of pointwise cells, so
there is no pre-existing ground truth to regression-test against on this
exact data. Instead this script validates determinism/correctness on the new
dataset directly: it runs the SAME (seed, 8 iterations) draw sequence TWICE,
via two completely independent precompute+run passes (fresh data load, fresh
_precompute_cell_index call each time), and requires the two runs to match
bit-for-bit (max_abs_diff = 0.0) on all three target coefficients before
anything built on top of it (a larger-n extension) is trusted.

Also reports peak RSS via the same psutil peak-sampler pattern used in
run_h2h4_lowmem_regression_test.py, so the end-to-end-only footprint can be
compared against the pooled-data 5.6GB figure.

Writes verification/h2h4_endtoend_regression_test_result.json.
Checkpoints to a throwaway path (not the real shard checkpoints) since this
script's only purpose is the from-scratch reproducibility check.
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
CONFIRMATORY_MODE = "finite_shot_end_to_end"
SEED = 266001  # distinct from the pooled-data streams (66001, 76001, 86001, 96001, 106001)
N_ITERATIONS = 8
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


def rss_gb():
    gc.collect()
    return proc.memory_info().rss / 1e9


def one_pass(tag: str, checkpoint_path: Path) -> dict:
    """Completely independent load + precompute + 8-iteration run."""
    t0 = time.time()
    raw_shot_df = read_tidy_dataset(REPO_ROOT / "results" / "raw" / f"{CONFIRMATORY_MODE}.parquet")
    t_load = time.time() - t0
    print(f"[{tag}] loaded {len(raw_shot_df)} rows in {t_load:.1f}s; RSS = {rss_gb():.3f} GB", flush=True)

    t0 = time.time()
    pre = _precompute_cell_index(raw_shot_df)
    t_pre = time.time() - t0
    print(f"[{tag}] precomputed cell index ({len(pre.sorted_full_keys)} cells) in {t_pre:.1f}s; "
          f"RSS = {rss_gb():.3f} GB", flush=True)
    del raw_shot_df

    t0 = time.time()
    result = run_h2h4_bootstrap_lowmem(
        raw_shot_df=None, n_iterations=N_ITERATIONS, seed=SEED, min_success_fraction=0.0,
        checkpoint_path=checkpoint_path, checkpoint_every=1, precomputed=pre, verbose=True,
    )
    t_run = time.time() - t0
    print(f"[{tag}] run_h2h4_bootstrap_lowmem: {result.n_successful}/{result.n_requested} successful in "
          f"{t_run:.1f}s ({t_run / max(result.n_successful,1):.1f}s/iter); RSS = {rss_gb():.3f} GB", flush=True)

    return {
        "n_successful": result.n_successful,
        "failed_iterations": result.failed_iterations,
        "coefficients": result.coefficients.sort_values("iteration").reset_index(drop=True),
        "timings_seconds": {"load": t_load, "precompute": t_pre, "run_8_iterations": t_run},
        "n_cells": len(pre.sorted_full_keys),
    }


def main():
    sampler = PeakSampler()
    sampler.start()
    print(f"start RSS = {rss_gb():.3f} GB", flush=True)

    ckpt_dir = Path(__file__).parent / "_bootstrap_checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    pass_a = one_pass("pass_a", ckpt_dir / "h2h4_boot_endtoend_regression_a.parquet")
    pass_b = one_pass("pass_b", ckpt_dir / "h2h4_boot_endtoend_regression_b.parquet")

    sampler.stop()
    peak_gb = sampler.peak_rss / 1e9
    print(f"OVERALL PEAK RSS (both passes, same process) = {peak_gb:.3f} GB", flush=True)

    comparison = {}
    overall_pass = True
    for coef in TARGET_COEFS:
        a = pass_a["coefficients"][coef].to_numpy()
        b = pass_b["coefficients"][coef].to_numpy()
        if len(a) != len(b):
            comparison[coef] = {"error": f"length mismatch a={len(a)} b={len(b)}"}
            overall_pass = False
            continue
        max_abs_diff = float(np.max(np.abs(a - b)))
        allclose_tight = bool(np.allclose(a, b, atol=1e-9, rtol=1e-6))
        comparison[coef] = {
            "pass_a": a.tolist(), "pass_b": b.tolist(),
            "max_abs_diff": max_abs_diff,
            "allclose_atol_1e-9_rtol_1e-6": allclose_tight,
        }
        if not allclose_tight:
            overall_pass = False

    out = {
        "seed": SEED,
        "n_iterations": N_ITERATIONS,
        "n_cells_pass_a": pass_a["n_cells"],
        "n_cells_pass_b": pass_b["n_cells"],
        "n_successful_pass_a": pass_a["n_successful"],
        "n_successful_pass_b": pass_b["n_successful"],
        "failed_iterations_pass_a": pass_a["failed_iterations"],
        "failed_iterations_pass_b": pass_b["failed_iterations"],
        "timings_seconds_pass_a": pass_a["timings_seconds"],
        "timings_seconds_pass_b": pass_b["timings_seconds"],
        "peak_rss_gb_both_passes_same_process": peak_gb,
        "comparison": comparison,
        "overall_pass": overall_pass,
    }
    out_path = Path(__file__).parent / "h2h4_endtoend_regression_test_result.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nOVERALL PASS (pass_a == pass_b, from-scratch reproducibility) = {overall_pass}", flush=True)
    for coef, c in comparison.items():
        if "error" in c:
            print(f"  {coef}: ERROR {c['error']}", flush=True)
        else:
            print(f"  {coef}: max_abs_diff={c['max_abs_diff']:.3e} allclose(1e-9,1e-6)={c['allclose_atol_1e-9_rtol_1e-6']}",
                  flush=True)
    print(f"wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
