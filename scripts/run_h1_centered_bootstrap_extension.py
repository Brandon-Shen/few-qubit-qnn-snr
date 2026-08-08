"""Extend the corrected H1 cluster bootstrap to 2,000 completed fits."""
from __future__ import annotations

import argparse
import json
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from qnn_snr.stats.bootstrap import _relabel_outer_resample
from qnn_snr.stats.factor_coding import transform_bootstrap_draws
from qnn_snr.stats.models import H1_FORMULA, build_h1_dataset, fit_mixed_model

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "results/production_confirmatory/raw/exact.parquet"
HISTORICAL = ROOT / "verification/_bootstrap_checkpoints/h1_boot.parquet"
OUT = ROOT / "results/primary_corrected/effect_coded"
DIRECT_CKPT = OUT / "h1_direct_bootstrap_2000_checkpoint.parquet"
CENTERED_CKPT = OUT / "h1_centered_bootstrap_2000.parquet"
META = OUT / "h1_centered_bootstrap_2000.meta.json"
CHECKPOINTS = OUT / "h1_centered_bootstrap_endpoint_checkpoints.csv"
SEED = 55001
PLAN_COMMIT = "ec35570569cb0078bbf3f49a4b1b421ccad8c1c4"
_EXACT = None


def _init_worker(path: str) -> None:
    global _EXACT
    _EXACT = pd.read_parquet(path)


def _one(iteration: int) -> dict:
    rng = np.random.default_rng((SEED, iteration))
    try:
        sample = _relabel_outer_resample(_EXACT, rng)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fit = fit_mixed_model(H1_FORMULA, build_h1_dataset(sample), "a")
        if fit.error or not fit.converged:
            return {"iteration": iteration, "status": "failed", "reason": fit.error or "nonconverged"}
        return {"iteration": iteration, "status": "completed",
                "warnings": " | ".join(sorted(set(str(w.message) for w in caught))), **fit.params}
    except Exception as exc:  # noqa: BLE001
        return {"iteration": iteration, "status": "failed", "reason": repr(exc)}


def endpoint_rows(centered: pd.DataFrame) -> list[dict]:
    rows = []
    ordered = centered.sort_values("iteration")
    for count in (100, 250, 400, 1000, 2000, 5000):
        if len(ordered) < count:
            continue
        values = ordered.iloc[:count]["E_c:L_c"].to_numpy()
        lo, med, hi = np.percentile(values, [2.5, 50, 97.5])
        rows.append({"completed_bootstrap_fits": count, "lower": lo, "median": med, "upper": hi})
    return rows


def save(direct: pd.DataFrame, failures: list[dict], attempted: int, started: float) -> None:
    direct = direct.sort_values("iteration").drop_duplicates("iteration", keep="first")
    centered = transform_bootstrap_draws(direct, "h1")
    direct.to_parquet(DIRECT_CKPT, index=False)
    centered.to_parquet(CENTERED_CKPT, index=False)
    pd.DataFrame(endpoint_rows(centered)).to_csv(CHECKPOINTS, index=False)
    values = centered["E_c:L_c"].to_numpy()
    lo, med, hi = np.percentile(values, [2.5, 50, 97.5])
    META.write_text(json.dumps({
        "seed": SEED, "plan_commit": PLAN_COMMIT, "attempted_iterations": attempted,
        "completed_bootstrap_fits": len(centered), "failed_iterations": failures,
        "percentile_interval": [float(lo), float(hi)], "median": float(med),
        "elapsed_seconds": time.time() - started,
        "historical_draws_preserved": 400,
        "cluster_relabeling": "unique synthetic initialization_id per sampled draw",
    }, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=2000)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    started = time.time()
    historical = pd.read_parquet(HISTORICAL)
    if DIRECT_CKPT.exists():
        direct = pd.read_parquet(DIRECT_CKPT)
    else:
        direct = historical.copy()
    failures = []
    if META.exists():
        failures = json.loads(META.read_text(encoding="utf-8")).get("failed_iterations", [])
    done = set(direct.iteration.astype(int)) | {int(x["iteration"]) for x in failures}

    # Frozen deterministic validation: regenerated direct draws 0--9 must match archive.
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_worker, initargs=(str(INPUT),)) as pool:
        validation = list(pool.map(_one, range(10)))
    archived = historical.set_index("iteration")
    for row in validation:
        if row["status"] != "completed":
            raise RuntimeError(f"Historical validation draw failed: {row}")
        for coef in ("E:L", "E:R", "L:R", "E:L:R"):
            if not np.isclose(row[coef], archived.loc[row["iteration"], coef], atol=1e-8, rtol=1e-7):
                raise RuntimeError(f"Historical draw mismatch iteration={row['iteration']} coefficient={coef}")

    next_iteration = 0
    while len(direct) < args.target:
        batch = []
        while len(batch) < min(50, args.target - len(direct)):
            if next_iteration not in done:
                batch.append(next_iteration)
            next_iteration += 1
        with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_worker, initargs=(str(INPUT),)) as pool:
            results = list(pool.map(_one, batch))
        completed = [{k: v for k, v in row.items() if k not in ("status", "reason")} for row in results if row["status"] == "completed"]
        failures.extend([{k: v for k, v in row.items() if k != "status"} for row in results if row["status"] != "completed"])
        if completed:
            direct = pd.concat([direct, pd.DataFrame(completed)], ignore_index=True)
        done.update(batch)
        save(direct, failures, len(done), started)
    save(direct.iloc[:args.target], failures, len(done), started)


if __name__ == "__main__":
    main()
