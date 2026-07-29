"""Task I step 1: test how many concurrent H2-H4 lowmem shard processes this
machine can safely run, with an ACTIVE kill-switch (not just passive
monitoring) -- if system free memory drops below --danger-gb, every spawned
child is killed immediately, matching the caution the original 2-concurrent
original-implementation test used (which required a manual kill after
free memory hit 590MB) but automated so a real crash risk cannot be missed.

Uses verification/measure_rss_concurrent.py as the worker (small iteration
count, no checkpoint writes, safe to run repeatedly).

Run from the repo root:
    python verification/test_concurrency_safety.py --n 3 --iterations 3 --danger-gb 1.5
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import psutil

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_SEED = 910000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--iterations", type=int, default=3)
    ap.add_argument("--danger-gb", type=float, default=1.5)
    ap.add_argument("--stagger-s", type=float, default=0.0)
    args = ap.parse_args()

    tags = [f"safety_n{args.n}_{i}" for i in range(args.n)]
    out_jsons = [Path(__file__).parent / f"_rss_probe_{t}.json" for t in tags]
    for p in out_jsons:
        if p.exists():
            p.unlink()

    procs = []
    print(f"launching {args.n} concurrent workers, {args.iterations} iterations each, "
          f"danger threshold {args.danger_gb}GB free", flush=True)
    for i, tag in enumerate(tags):
        cmd = [sys.executable, str(Path(__file__).parent / "measure_rss_concurrent.py"),
               "--seed", str(BASE_SEED + i * 1000), "--iterations", str(args.iterations),
               "--tag", tag, "--out-json", str(out_jsons[i])]
        log_path = Path(__file__).parent / f"_rss_probe_{tag}.log"
        with open(log_path, "w") as logf:
            p = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, cwd=str(REPO_ROOT))
        procs.append(p)
        print(f"  launched {tag} pid={p.pid}", flush=True)
        if args.stagger_s > 0:
            time.sleep(args.stagger_s)

    t0 = time.time()
    aborted = False
    min_free_gb = float("inf")
    while True:
        free_gb = psutil.virtual_memory().available / 1e9
        min_free_gb = min(min_free_gb, free_gb)
        elapsed = time.time() - t0
        print(f"[t={elapsed:.0f}s] free={free_gb:.3f}GB min_so_far={min_free_gb:.3f}GB", flush=True)

        if free_gb < args.danger_gb:
            print(f"DANGER: free memory {free_gb:.3f}GB below threshold {args.danger_gb}GB -- "
                  f"KILLING all {len(procs)} workers now", flush=True)
            for p in procs:
                try:
                    p.kill()
                except Exception:
                    pass
            aborted = True
            break

        if all(p.poll() is not None for p in procs):
            print("all workers exited normally", flush=True)
            break

        time.sleep(1.0)

    exit_codes = [p.poll() for p in procs]
    print(f"\nRESULT: aborted={aborted} min_free_seen_gb={min_free_gb:.3f} "
          f"exit_codes={exit_codes} elapsed={time.time()-t0:.1f}s", flush=True)

    if not aborted:
        peaks = []
        for p in out_jsons:
            if p.exists():
                import json
                d = json.loads(p.read_text())
                peaks.append(d["peak_rss_gb"])
                print(f"  {d['tag']}: peak_rss={d['peak_rss_gb']:.3f}GB n_successful={d['n_successful']}")
        if peaks:
            print(f"  per-process peaks: min={min(peaks):.3f} max={max(peaks):.3f} "
                  f"sum={sum(peaks):.3f}GB (n={len(peaks)})")


if __name__ == "__main__":
    main()
