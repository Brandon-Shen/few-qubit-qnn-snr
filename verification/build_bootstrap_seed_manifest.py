"""QMI/QIP robustness package, Task 4: reproducibility seed manifest for the
extended end-to-end-only H2-H4 bootstrap.

Each shard's per-iteration RNG is `np.random.default_rng((seed, it))`
(qnn_snr/stats/bootstrap.py / verification/h2h4_bootstrap_lowmem.py,
unchanged production RNG contract) -- deterministic given (seed, it), so the
manifest records that pair directly per iteration rather than a derived
hash. `seed` per shard is `366001 + shard_id * 10000` for the extension
shards (verification/run_h2h4_bootstrap_shard_endtoend_only.py) and the
fixed `266001` for the from-scratch regression-check draws
(verification/run_h2h4_endtoend_regression_test.py).

Run from the repo root: python verification/build_bootstrap_seed_manifest.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
CKPT_DIR = REPO_ROOT / "verification" / "_bootstrap_checkpoints"

POOL_SOURCES = [
    ("regression_a", "h2h4_boot_endtoend_regression_a", 266001, "pooled (real draws)"),
    ("regression_b", "h2h4_boot_endtoend_regression_b", 266001, "duplicate check ONLY -- excluded from pooled summary"),
    ("shard0", "h2h4_boot_endtoend_shard0", 366001, "pooled (real draws)"),
    ("shard1", "h2h4_boot_endtoend_shard1", 376001, "pooled (real draws)"),
    ("shard2", "h2h4_boot_endtoend_shard2", 386001, "pooled (real draws)"),
    ("shard3", "h2h4_boot_endtoend_shard3", 396001, "pooled (real draws)"),
    ("shard4", "h2h4_boot_endtoend_shard4", 406001, "pooled (real draws)"),
]

INPUT_FILES = [
    REPO_ROOT / "results" / "raw" / "finite_shot_end_to_end.parquet",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def software_versions() -> dict:
    import numpy, pandas as pd_, statsmodels, scipy, sys
    return {
        "python": sys.version.split()[0], "numpy": numpy.__version__, "pandas": pd_.__version__,
        "statsmodels": statsmodels.__version__, "scipy": scipy.__version__,
    }


def main():
    commit = git_commit()
    versions = software_versions()
    input_hashes = {p.name: sha256_of(p) for p in INPUT_FILES if p.exists()}

    rows = []
    for stream_name, filestem, seed, pooling_status in POOL_SOURCES:
        p = CKPT_DIR / f"{filestem}.parquet"
        meta_p = CKPT_DIR / f"{filestem}.meta.json"
        if not p.exists():
            continue
        df = pd.read_parquet(p, columns=["iteration"])
        failed = json.loads(meta_p.read_text()).get("failed_iterations", []) if meta_p.exists() else []
        success_iters = sorted(df["iteration"].tolist())
        all_iters = sorted(set(success_iters) | set(failed))
        for it in all_iters:
            rows.append({
                "stream": stream_name, "shard_seed": seed, "iteration": it,
                "rng_key": f"({seed}, {it})", "status": "completed" if it in success_iters else "failed",
                "failure_reason": "recorded in .meta.json failed_iterations; per-exception detail not "
                                   "separately retained by the production checkpoint format" if it in failed else "",
                "pooling_status": pooling_status,
                "git_commit": commit,
                "input_file_sha256": json.dumps(input_hashes),
                "software_versions": json.dumps(versions),
            })

    manifest = pd.DataFrame(rows).sort_values(["stream", "iteration"])
    out_path = REPO_ROOT / "results" / "bootstrap_end_to_end_h2_h4_seed_manifest.csv"
    manifest.to_csv(out_path, index=False)
    print(f"wrote {out_path} ({len(manifest)} rows across {manifest['stream'].nunique()} streams)")
    print(manifest.groupby(["stream", "status"]).size())

    # sanity check: no overlapping (seed, iteration) pairs across REAL (non-duplicate) streams
    real = manifest[manifest["pooling_status"] == "pooled (real draws)"]
    dup_check = real.groupby(["shard_seed", "iteration"]).size()
    overlaps = dup_check[dup_check > 1]
    if len(overlaps):
        print(f"WARNING: {len(overlaps)} overlapping (seed, iteration) pairs found among pooled streams!")
    else:
        print("CONFIRMED: no overlapping (seed, iteration) pairs among pooled (non-duplicate-check) streams.")


if __name__ == "__main__":
    main()
