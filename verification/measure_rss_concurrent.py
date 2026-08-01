"""Task H: apples-to-apples RSS measurement, same psutil peak-sampler tool used
single-stream and under concurrency (the original comparison in
verification/h2h4_bootstrap_memory_redesign.md mixed a psutil-based peak
(5.6GB, single-stream, whole 8-iteration run) against a tasklist-based
INSTANTANEOUS snapshot (3.7-3.8GB, taken at one arbitrary polling moment
during a 2-concurrent-shard run) -- not a like-for-like comparison).

Standalone probe, does not touch any real bootstrap checkpoint (checkpoint_path=None).

Run from the repo root:
    python verification/measure_rss_concurrent.py --seed 900001 --iterations 5 --tag solo --out-json verification/_rss_probe_solo.json
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import threading
import time
from pathlib import Path

import pandas as pd
import psutil

from qnn_snr.schema import read_tidy_dataset

REPO_ROOT = Path(__file__).resolve().parent.parent
SHOT_MODES = ("finite_shot_conditional", "finite_shot_end_to_end")

sys.path.insert(0, str(Path(__file__).parent))
from h2h4_bootstrap_lowmem import _precompute_cell_index, run_h2h4_bootstrap_lowmem  # noqa: E402

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--iterations", type=int, default=5)
    ap.add_argument("--tag", type=str, required=True)
    ap.add_argument("--out-json", type=str, required=True)
    args = ap.parse_args()

    sampler = PeakSampler()
    sampler.start()

    t0 = time.time()
    parts = [read_tidy_dataset(REPO_ROOT / "results" / "production_confirmatory" / "raw" / f"{m}.parquet") for m in SHOT_MODES]
    raw_shot_df = pd.concat(parts, ignore_index=True)
    del parts
    t_load = time.time() - t0
    rss_after_load = rss_gb()
    print(f"[{args.tag}] loaded {len(raw_shot_df)} rows in {t_load:.1f}s; RSS={rss_after_load:.3f}GB", flush=True)

    t0 = time.time()
    pre = _precompute_cell_index(raw_shot_df)
    t_pre = time.time() - t0
    del raw_shot_df
    rss_after_precompute = rss_gb()
    print(f"[{args.tag}] precomputed in {t_pre:.1f}s; RSS={rss_after_precompute:.3f}GB", flush=True)

    t0 = time.time()
    result = run_h2h4_bootstrap_lowmem(
        raw_shot_df=None, n_iterations=args.iterations, seed=args.seed, min_success_fraction=0.0,
        checkpoint_path=None, precomputed=pre, verbose=True,
    )
    t_run = time.time() - t0
    rss_after_run = rss_gb()
    print(f"[{args.tag}] ran {result.n_successful}/{args.iterations} iterations in {t_run:.1f}s "
          f"({t_run/max(result.n_successful,1):.1f}s/iter); RSS={rss_after_run:.3f}GB", flush=True)

    sampler.stop()
    peak_gb = sampler.peak_rss / 1e9
    print(f"[{args.tag}] PEAK RSS = {peak_gb:.3f} GB", flush=True)

    out = {
        "tag": args.tag, "seed": args.seed, "iterations": args.iterations,
        "n_successful": result.n_successful,
        "rss_after_load_gb": rss_after_load, "rss_after_precompute_gb": rss_after_precompute,
        "rss_after_run_gb": rss_after_run, "peak_rss_gb": peak_gb,
        "t_load": t_load, "t_precompute": t_pre, "t_run": t_run,
        "start_time": time.time() - (t_load + t_pre + t_run),
    }
    Path(args.out_json).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[{args.tag}] wrote {args.out_json}", flush=True)


if __name__ == "__main__":
    main()
