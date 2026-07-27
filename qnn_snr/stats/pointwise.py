"""Pointwise estimator statistics (Section 9).

Computed per (analysis_mode, configuration, matched parameter, depth,
budget, initialization) cell from the R replicate signed gradients.
Deliberately does *not* touch `statevector_exact` rows: that mode has a
single deterministic replicate per cell (ASSUMPTION A19), so shot_variance/
SNR are not defined there -- H1 (Section 10) consumes its `exact_gradient`
column directly.

SNR's denominator is the sample SD across replicates (`ddof=1`), never the
standard error of the mean -- no `sqrt(R)` division anywhere here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CELL_KEY_COLS = [
    "analysis_mode", "configuration_id", "E", "L", "R", "depth", "depth_centered", "depth_z",
    "budget", "log2_budget", "initialization_id", "parameter_id", "parameter_index",
    "block_index", "qubit_index", "cost_type", "gamma",
]

ZERO_VARIANCE_TOL = 0.0  # exact zero only -- Section 9 forbids silently adding epsilon


def _bootstrap_ci_for_mean(values: np.ndarray, rng: np.random.Generator, n_boot: int,
                            alpha: float = 0.05) -> tuple[float, float]:
    n = len(values)
    if n < 2:
        return (float("nan"), float("nan"))
    idx = rng.integers(0, n, size=(n_boot, n))
    boot_means = values[idx].mean(axis=1)
    lo, hi = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def pointwise_statistics(df: pd.DataFrame, bootstrap_iterations: int = 500,
                          bootstrap_seed: int = 777, alpha: float = 0.05) -> pd.DataFrame:
    shot_df = df[df["analysis_mode"].isin(["finite_shot_conditional", "finite_shot_end_to_end"])]
    rng = np.random.default_rng(bootstrap_seed)
    records = []
    for keys, g in shot_df.groupby(CELL_KEY_COLS, dropna=False):
        grads = g["gradient_hat"].to_numpy(dtype=float)
        exact = float(g["exact_gradient"].iloc[0])
        n = len(grads)
        mu_hat = float(grads.mean())
        shot_variance = float(grads.var(ddof=1)) if n > 1 else float("nan")
        shot_sd = float(np.sqrt(shot_variance)) if np.isfinite(shot_variance) else float("nan")

        zero_variance_flag = bool(np.isfinite(shot_variance) and shot_variance <= ZERO_VARIANCE_TOL)
        if zero_variance_flag:
            snr_est = float("inf") if mu_hat != 0 else float("nan")
            snr_exact = float("inf") if exact != 0 else float("nan")
        elif np.isfinite(shot_sd) and shot_sd > 0:
            snr_est = abs(mu_hat) / shot_sd
            snr_exact = abs(exact) / shot_sd
        else:
            snr_est = float("nan")
            snr_exact = float("nan")

        bias = mu_hat - exact
        sign_agreement = bool(np.sign(mu_hat) == np.sign(exact)) if mu_hat != 0 and exact != 0 else False

        ci_lo, ci_hi = _bootstrap_ci_for_mean(grads, rng, bootstrap_iterations, alpha)
        ci_excludes_zero = bool(np.isfinite(ci_lo) and np.isfinite(ci_hi) and (ci_lo > 0 or ci_hi < 0))

        record = dict(zip(CELL_KEY_COLS, keys))
        record.update({
            "n_replicates": n,
            "mu_hat": mu_hat,
            "exact_gradient": exact,
            "shot_variance": shot_variance,
            "shot_sd": shot_sd,
            "zero_variance_flag": zero_variance_flag,
            "SNR_est": snr_est,
            "SNR_exact": snr_exact,
            "bias": bias,
            "absolute_bias": abs(bias),
            "sign_agreement": sign_agreement,
            "signed_mean_ci_lo": ci_lo,
            "signed_mean_ci_hi": ci_hi,
            "signed_mean_ci_excludes_zero": ci_excludes_zero,
        })
        records.append(record)
    return pd.DataFrame.from_records(records)


def zero_variance_confirmatory_cells(pointwise_df: pd.DataFrame) -> pd.DataFrame:
    """Confirmatory finite-shot cells with exactly zero replicate variance
    (Section 9: must be flagged explicitly and stop the confirmatory model
    unless a prespecified policy exists -- no such policy is prespecified in
    this codebase, so any nonempty result here is a hard stop for `fit`)."""
    return pointwise_df[pointwise_df["zero_variance_flag"]]
