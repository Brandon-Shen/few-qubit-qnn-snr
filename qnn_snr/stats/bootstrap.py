"""Nested matched bootstrap (Section 14).

Outer level: resample complete initialization IDs with replacement; every
selected copy of an initialization keeps its full matched factorial
structure (every configuration, parameter, depth, budget belonging to it)
and is relabeled with a unique bootstrap-cluster id when an initialization is
drawn more than once, so within-initialization correlation is preserved and
no downstream code can accidentally conflate two draws of the same
initialization.

Inner level (estimator-SNR bootstrap only): within every selected
initialization-copy x configuration x parameter x depth x budget cell,
resample the R replicate signed gradients with replacement and recompute
pointwise statistics from the resampled draws. The exact-signal (H1)
bootstrap needs no inner resampling -- exact gradients are deterministic.

Both bootstraps refit the primary mixed model on every iteration and record
target coefficients plus convergence/diagnostic status; failed fits are
tracked explicitly (never silently dropped) and iteration stops short of the
configured `min_success_fraction` are reported as a hard warning in
`bootstrap_diagnostics.json`.
"""
from __future__ import annotations

import concurrent.futures as cf
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from qnn_snr.stats.models import H1_FORMULA, H2_H4_FORMULA, build_h1_dataset, build_h2h4_dataset, fit_mixed_model
from qnn_snr.stats.pointwise import pointwise_statistics

TARGET_COEFFICIENTS = {
    "H1": "E:L",
    "H2": "E:L",
    "H3": "E:R",
    "H4": "L:R:depth_z",
}


@dataclass
class BootstrapResult:
    hypothesis_family: str  # "exact_signal" or "estimator_snr"
    n_requested: int
    n_successful: int
    min_success_fraction: float
    success_fraction_met: bool
    coefficients: pd.DataFrame  # columns: iteration, <coef names...>
    failed_iterations: list[int]
    percentile_ci: dict  # coef_name -> (lo, hi)
    seed: int


def _relabel_outer_resample(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    unique_inits = np.sort(df["initialization_id"].unique())
    n = len(unique_inits)
    chosen = rng.choice(unique_inits, size=n, replace=True)
    parts = []
    for new_id, orig in enumerate(chosen):
        sub = df[df["initialization_id"] == orig].copy()
        sub["initialization_id"] = new_id
        parts.append(sub)
    return pd.concat(parts, ignore_index=True)


def _inner_resample_replicates(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    cell_cols = ["analysis_mode", "configuration_id", "depth", "budget", "initialization_id", "parameter_id"]
    parts = []
    for _, g in df.groupby(cell_cols, sort=False):
        n = len(g)
        idx = rng.integers(0, n, size=n)
        parts.append(g.iloc[idx])
    return pd.concat(parts, ignore_index=True)


def _percentile_ci(values: np.ndarray, alpha: float = 0.05) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return float("nan"), float("nan")
    lo, hi = np.percentile(finite, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def _load_checkpoint(checkpoint_path) -> tuple[list[dict], list[int]]:
    import json
    from pathlib import Path
    p = Path(checkpoint_path) if checkpoint_path else None
    if p is None or not p.exists():
        return [], []
    df = pd.read_parquet(p)
    meta_path = p.with_suffix(".meta.json")
    failed = json.loads(meta_path.read_text())["failed_iterations"] if meta_path.exists() else []
    return df.to_dict("records"), failed


def _save_checkpoint(checkpoint_path, coef_rows: list[dict], failed: list[int]) -> None:
    import json
    from pathlib import Path
    if not checkpoint_path or not coef_rows:
        return
    p = Path(checkpoint_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(coef_rows).to_parquet(p, index=False)
    p.with_suffix(".meta.json").write_text(json.dumps({"failed_iterations": failed}))


def run_h1_bootstrap(exact_df: pd.DataFrame, n_iterations: int, seed: int,
                      min_success_fraction: float = 0.9, alpha: float = 0.05,
                      checkpoint_path=None, checkpoint_every: int = 100) -> BootstrapResult:
    coef_rows, failed = _load_checkpoint(checkpoint_path)
    done_iters = {r["iteration"] for r in coef_rows} | set(failed)
    for it in range(n_iterations):
        if it in done_iters:
            continue
        rng = np.random.default_rng((seed, it))
        try:
            resampled = _relabel_outer_resample(exact_df, rng)
            h1_ds = build_h1_dataset(resampled)
            result = fit_mixed_model(H1_FORMULA, h1_ds, "a")
            if result.error is not None or not result.converged:
                failed.append(it)
                continue
            coef_rows.append({"iteration": it, **result.params})
        except Exception:
            failed.append(it)
        if checkpoint_path and (it + 1) % checkpoint_every == 0:
            _save_checkpoint(checkpoint_path, coef_rows, failed)
    _save_checkpoint(checkpoint_path, coef_rows, failed)
    coef_df = pd.DataFrame(coef_rows)
    n_success = len(coef_df)
    ci = {}
    if n_success > 0:
        for coef in ("E:L", "E:R", "L:R", "E:L:R"):
            if coef in coef_df.columns:
                ci[coef] = _percentile_ci(coef_df[coef].to_numpy(), alpha)
    return BootstrapResult(
        hypothesis_family="exact_signal", n_requested=n_iterations, n_successful=n_success,
        min_success_fraction=min_success_fraction,
        success_fraction_met=(n_success / n_iterations) >= min_success_fraction if n_iterations else False,
        coefficients=coef_df, failed_iterations=failed, percentile_ci=ci, seed=seed,
    )


def run_h2h4_bootstrap(raw_shot_df: pd.DataFrame, n_iterations: int, seed: int,
                        min_success_fraction: float = 0.9, alpha: float = 0.05,
                        pointwise_bootstrap_iterations: int = 50,
                        checkpoint_path=None, checkpoint_every: int = 50) -> BootstrapResult:
    coef_rows, failed = _load_checkpoint(checkpoint_path)
    done_iters = {r["iteration"] for r in coef_rows} | set(failed)
    for it in range(n_iterations):
        if it in done_iters:
            continue
        rng = np.random.default_rng((seed, it))
        try:
            outer = _relabel_outer_resample(raw_shot_df, rng)
            inner = _inner_resample_replicates(outer, rng)
            pw = pointwise_statistics(inner, bootstrap_iterations=pointwise_bootstrap_iterations,
                                       bootstrap_seed=int(rng.integers(0, 2 ** 31 - 1)))
            snr_ds = build_h2h4_dataset(pw)
            if snr_ds.empty:
                failed.append(it)
                continue
            result = fit_mixed_model(H2_H4_FORMULA, snr_ds, "y")
            if result.error is not None or not result.converged:
                failed.append(it)
                continue
            coef_rows.append({"iteration": it, **result.params})
        except Exception:
            failed.append(it)
        if checkpoint_path and (it + 1) % checkpoint_every == 0:
            _save_checkpoint(checkpoint_path, coef_rows, failed)
    _save_checkpoint(checkpoint_path, coef_rows, failed)
    coef_df = pd.DataFrame(coef_rows)
    n_success = len(coef_df)
    ci = {}
    if n_success > 0:
        for coef in ("E:L", "E:R", "L:R", "E:L:R", "L:R:depth_z"):
            if coef in coef_df.columns:
                ci[coef] = _percentile_ci(coef_df[coef].to_numpy(), alpha)
    return BootstrapResult(
        hypothesis_family="estimator_snr", n_requested=n_iterations, n_successful=n_success,
        min_success_fraction=min_success_fraction,
        success_fraction_met=(n_success / n_iterations) >= min_success_fraction if n_iterations else False,
        coefficients=coef_df, failed_iterations=failed, percentile_ci=ci, seed=seed,
    )


def confirmatory_bootstrap_ci(h1_boot: BootstrapResult, h2h4_boot: BootstrapResult) -> dict[str, tuple[float, float]]:
    out = {}
    if "E:L" in h1_boot.percentile_ci:
        out["H1"] = h1_boot.percentile_ci["E:L"]
    for hyp, coef in (("H2", "E:L"), ("H3", "E:R"), ("H4", "L:R:depth_z")):
        if coef in h2h4_boot.percentile_ci:
            out[hyp] = h2h4_boot.percentile_ci[coef]
    return out
