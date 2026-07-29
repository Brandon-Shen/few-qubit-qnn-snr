"""Profile ONE real H2-H4 bootstrap iteration (seed 66001, it=0) on the real
combined finite-shot dataset, reporting peak RSS by stage.

Uses a background sampler thread polling psutil Process RSS every 50ms so
that transient peaks *during* a stage (e.g. mid-`pd.concat`) are captured,
not just the RSS after each stage completes.

Run from repo root:
    python verification/profile_h2h4_iteration.py
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
from qnn_snr.stats.bootstrap import _inner_resample_replicates, _relabel_outer_resample
from qnn_snr.stats.models import H2_H4_FORMULA, build_h2h4_dataset, fit_mixed_model
from qnn_snr.stats.pointwise import pointwise_statistics

REPO_ROOT = Path(__file__).resolve().parent.parent
SHOT_MODES = ("finite_shot_conditional", "finite_shot_end_to_end")
SEED = 66001
ITERATION = 0

proc = psutil.Process()


class PeakSampler:
    """Background thread that continuously tracks peak RSS since start()."""

    def __init__(self, interval: float = 0.05):
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None
        self.peak_rss = 0
        self.samples = []

    def _run(self):
        while not self._stop.is_set():
            rss = proc.memory_info().rss
            self.peak_rss = max(self.peak_rss, rss)
            self.samples.append((time.time(), rss))
            time.sleep(self.interval)

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)


def rss_gb() -> float:
    return proc.memory_info().rss / 1e9


def main():
    sampler = PeakSampler(interval=0.05)
    sampler.start()

    stages = {}

    def record(name: str):
        gc.collect()
        current = rss_gb()
        peak_so_far = sampler.peak_rss / 1e9
        stages[name] = {"rss_after_gc_gb": current, "peak_rss_seen_so_far_gb": peak_so_far}
        print(f"[{name}] current RSS (post-gc) = {current:.3f} GB | peak RSS seen so far = {peak_so_far:.3f} GB",
              flush=True)

    record("00_start")

    t0 = time.time()
    parts = [read_tidy_dataset(REPO_ROOT / "results" / "raw" / f"{m}.parquet") for m in SHOT_MODES]
    raw_shot_df = pd.concat(parts, ignore_index=True)
    del parts
    t_load = time.time() - t0
    print(f"loaded combined raw shot df: {len(raw_shot_df)} rows in {t_load:.1f}s", flush=True)
    record("01_after_load_raw_data")

    rng = np.random.default_rng((SEED, ITERATION))

    t0 = time.time()
    outer = _relabel_outer_resample(raw_shot_df, rng)
    t_outer = time.time() - t0
    print(f"outer resample: {len(outer)} rows in {t_outer:.1f}s", flush=True)
    record("02_after_outer_resample")

    t0 = time.time()
    inner = _inner_resample_replicates(outer, rng)
    t_inner = time.time() - t0
    print(f"inner resample: {len(inner)} rows in {t_inner:.1f}s", flush=True)
    record("03_after_inner_resample")

    # outer/inner no longer needed once pointwise stats are computed from `inner`;
    # drop `outer` now to see how much of the peak was outer-specific.
    del outer
    gc.collect()
    record("03b_after_dropping_outer")

    t0 = time.time()
    bootstrap_seed = int(rng.integers(0, 2 ** 31 - 1))
    pw = pointwise_statistics(inner, bootstrap_iterations=50, bootstrap_seed=bootstrap_seed)
    t_pw = time.time() - t0
    print(f"pointwise_statistics: {len(pw)} rows in {t_pw:.1f}s", flush=True)
    record("04_after_pointwise_statistics")

    del inner
    gc.collect()
    record("04b_after_dropping_inner")

    t0 = time.time()
    snr_ds = build_h2h4_dataset(pw)
    t_build = time.time() - t0
    print(f"build_h2h4_dataset: {len(snr_ds)} rows in {t_build:.1f}s", flush=True)
    record("05_after_build_h2h4_dataset")

    t0 = time.time()
    result = fit_mixed_model(H2_H4_FORMULA, snr_ds, "y")
    t_fit = time.time() - t0
    print(f"fit_mixed_model: converged={result.converged} in {t_fit:.1f}s", flush=True)
    record("06_after_fit_mixed_model")

    sampler.stop()
    overall_peak_gb = sampler.peak_rss / 1e9

    timings = {
        "load_raw_data_s": t_load,
        "outer_resample_s": t_outer,
        "inner_resample_s": t_inner,
        "pointwise_statistics_s": t_pw,
        "build_h2h4_dataset_s": t_build,
        "fit_mixed_model_s": t_fit,
        "total_s": t_load + t_outer + t_inner + t_pw + t_build + t_fit,
    }

    out = {
        "seed": SEED,
        "iteration": ITERATION,
        "stages_rss_gb": stages,
        "overall_peak_rss_gb": overall_peak_gb,
        "timings_seconds": timings,
        "n_samples_collected": len(sampler.samples),
        "converged": result.converged,
        "params": result.params,
    }
    out_path = Path(__file__).parent / "h2h4_profile_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nOVERALL PEAK RSS = {overall_peak_gb:.3f} GB", flush=True)
    print(f"wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
