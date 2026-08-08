"""Low-memory redesign of the H2-H4 (estimator-SNR) bootstrap iteration.

Motivation (see verification/h2h4_bootstrap_memory_redesign.md for the full
writeup): the production implementation in qnn_snr/stats/bootstrap.py +
qnn_snr/stats/pointwise.py builds THREE successive full-width physical copies
of the combined ~6.14M-row raw shot dataset per iteration --

  1. `_relabel_outer_resample`: 50x `df[df.initialization_id == orig].copy()`
     then `pd.concat` -> one full 30-column copy ("outer").
  2. `_inner_resample_replicates`: 204,800x `g.iloc[idx]` then `pd.concat`
     -> a second full 30-column copy ("inner").
  3. `pointwise_statistics`: `shot_df.groupby(CELL_KEY_COLS, ...)` iterates
     204,800 groups *of the already-doubly-copied* "inner" frame.

Several of those 30 columns are large, high-cardinality or constant string
columns (experiment_id, software_version, git_commit, config_hash, ...) that
are irrelevant to resampling or statistics but get duplicated across all
6.14M rows on every single iteration regardless.

This module computes *bit-identical* results using a fundamentally different
data path: numpy index arrays + direct column arrays, no `.copy()`/`concat`
of full rows at all. The key insight that makes exact reproduction possible
without replicating pandas' internal groupby machinery every iteration is
that the *set* of resampling cells and both groupby orderings used by the
original code are entirely iteration-invariant:

  - `_inner_resample_replicates` groups the outer-resampled frame with
    `sort=False`, so its traversal order is "insertion order in `outer`" --
    which is exactly "new_id 0..49 ascending, then within each new_id block,
    the order (analysis_mode, configuration_id, depth, budget, parameter_id)
    combinations first appear for the *original* initialization that new_id
    was relabeled from". That per-original-initialization order is a fixed
    property of the raw dataset, independent of which iteration or which
    new_id is asking for it, so it is computed ONCE, outside the iteration
    loop (`_precompute_cell_index`).
  - `pointwise_statistics` groups with the pandas default `sort=True` over
    17 key columns. Because `initialization_id` in every outer-resampled
    frame always spans exactly 0..49 (relabeling always produces a dense
    0..49 range, regardless of which original ids were drawn), and every
    other key column's value is a fixed property of
    (analysis_mode, configuration_id, depth, budget, parameter_id), the full
    lexicographically-sorted key order is *also* iteration-invariant and is
    computed ONCE (`_precompute_sorted_keys`).

Given both orderings precomputed once, each iteration only needs to replay
the same sequence of `rng.choice` / `rng.integers` calls (same call count,
same sizes, same order) that the original code makes, and gather values
through cheap numpy fancy-indexing instead of copying rows -- producing
numerically identical resampled draws for the same seed.

`raw_shot_df` is still read via `qnn_snr.schema.read_tidy_dataset` (unchanged
production I/O) but this module immediately narrows it to the handful of
numpy arrays actually needed for resampling + statistics.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from qnn_snr.stats.models import H2_H4_FORMULA, build_h2h4_dataset, fit_mixed_model
from qnn_snr.stats.pointwise import CELL_KEY_COLS, ZERO_VARIANCE_TOL, _bootstrap_ci_for_mean

CELLKEY5_COLS = ["analysis_mode", "configuration_id", "depth", "budget", "parameter_id"]
# positions of the CELLKEY5_COLS values and initialization_id within CELL_KEY_COLS tuples
_CK5_IDX = [CELL_KEY_COLS.index(c) for c in CELLKEY5_COLS]
_INIT_IDX = CELL_KEY_COLS.index("initialization_id")


@dataclass
class PrecomputedCellIndex:
    """Everything derivable from the raw dataset alone, independent of any
    bootstrap iteration -- computed once and reused across all iterations."""

    orig_ids: np.ndarray  # sorted unique original initialization_id values
    per_orig_order: dict  # orig(int) -> list[cellkey5 tuple] in first-appearance order
    per_orig_positions: dict  # orig(int) -> {cellkey5 tuple -> np.ndarray[int64] row positions}
    sorted_full_keys: list  # list of 17-tuples (CELL_KEY_COLS order), pandas-sort order
    gradient_hat: np.ndarray  # float64, full length, aligned with raw_shot_df row positions
    exact_gradient: np.ndarray  # float64, full length


def _precompute_cell_index(raw_shot_df: pd.DataFrame) -> PrecomputedCellIndex:
    orig_ids = np.sort(raw_shot_df["initialization_id"].unique())

    group_cols = ["initialization_id"] + CELLKEY5_COLS
    gb = raw_shot_df.groupby(group_cols, sort=False)
    indices = gb.indices  # dict: (orig, *cellkey5) -> ndarray of row positions (positional)

    per_orig_raw: dict = {}
    for key, positions in indices.items():
        orig = int(key[0])
        cellkey5 = tuple(key[1:])
        per_orig_raw.setdefault(orig, []).append((int(positions.min()), cellkey5, positions))

    per_orig_order: dict = {}
    per_orig_positions: dict = {}
    for orig, items in per_orig_raw.items():
        items.sort(key=lambda t: t[0])  # first-appearance order
        per_orig_order[orig] = [t[1] for t in items]
        per_orig_positions[orig] = {t[1]: t[2].astype(np.int64) for t in items}

    # canonical pandas-sorted key order for the pointwise-statistics stage
    size_series = raw_shot_df.groupby(CELL_KEY_COLS, dropna=False, sort=True).size()
    sorted_full_keys = list(size_series.index)

    gradient_hat = raw_shot_df["gradient_hat"].to_numpy(dtype=np.float64)
    exact_gradient = raw_shot_df["exact_gradient"].to_numpy(dtype=np.float64)

    return PrecomputedCellIndex(
        orig_ids=orig_ids,
        per_orig_order=per_orig_order,
        per_orig_positions=per_orig_positions,
        sorted_full_keys=sorted_full_keys,
        gradient_hat=gradient_hat,
        exact_gradient=exact_gradient,
    )


def _one_iteration_lowmem(pre: PrecomputedCellIndex, rng: np.random.Generator,
                           pointwise_bootstrap_iterations: int) -> pd.DataFrame:
    """Reproduces one full H2-H4 bootstrap iteration's pointwise-statistics
    table, bit-identically to
    pointwise_statistics(_inner_resample_replicates(_relabel_outer_resample(raw_shot_df, rng), rng), ...)
    but without ever materializing a full-width resampled dataframe."""
    n = len(pre.orig_ids)
    chosen = rng.choice(pre.orig_ids, size=n, replace=True)  # same call as _relabel_outer_resample

    cell_grads: dict = {}
    cell_exact: dict = {}
    for new_id, orig in enumerate(chosen):
        orig = int(orig)
        order = pre.per_orig_order[orig]
        positions_map = pre.per_orig_positions[orig]
        for cellkey5 in order:
            positions = positions_map[cellkey5]
            r = len(positions)
            idx = rng.integers(0, r, size=r)  # same call as _inner_resample_replicates per group
            resampled_positions = positions[idx]
            cell_grads[(new_id, cellkey5)] = pre.gradient_hat[resampled_positions]
            cell_exact[(new_id, cellkey5)] = pre.exact_gradient[resampled_positions[0]]

    bootstrap_seed = int(rng.integers(0, 2 ** 31 - 1))  # same call, same position, as run_h2h4_bootstrap
    rng2 = np.random.default_rng(bootstrap_seed)

    records = []
    model_only = pointwise_bootstrap_iterations == 0
    model_columns = ["analysis_mode", "E", "L", "R", "depth", "depth_z", "log2_budget",
                     "initialization_id", "parameter_id"]
    model_indices = [CELL_KEY_COLS.index(c) for c in model_columns]
    for key17 in pre.sorted_full_keys:
        cellkey5 = tuple(key17[i] for i in _CK5_IDX)
        new_id = key17[_INIT_IDX]
        grads = cell_grads[(new_id, cellkey5)]
        exact = cell_exact[(new_id, cellkey5)]

        mu_hat = float(grads.mean())
        rn = len(grads)
        shot_variance = float(grads.var(ddof=1)) if rn > 1 else float("nan")
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

        if model_only:
            record = {name: key17[idx] for name, idx in zip(model_columns, model_indices)}
            record["SNR_est"] = snr_est
            records.append(record)
            continue

        bias = mu_hat - exact
        sign_agreement = bool(np.sign(mu_hat) == np.sign(exact)) if mu_hat != 0 and exact != 0 else False

        ci_lo, ci_hi = _bootstrap_ci_for_mean(grads, rng2, pointwise_bootstrap_iterations)
        ci_excludes_zero = bool(np.isfinite(ci_lo) and np.isfinite(ci_hi) and (ci_lo > 0 or ci_hi < 0))

        record = dict(zip(CELL_KEY_COLS, key17))
        record.update({
            "n_replicates": rn,
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


def _percentile_ci(values: np.ndarray, alpha: float = 0.05) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return float("nan"), float("nan")
    lo, hi = np.percentile(finite, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def _load_checkpoint(checkpoint_path):
    import json
    from pathlib import Path
    p = Path(checkpoint_path) if checkpoint_path else None
    if p is None or not p.exists():
        return [], []
    df = pd.read_parquet(p)
    meta_path = p.with_suffix(".meta.json")
    failed = json.loads(meta_path.read_text())["failed_iterations"] if meta_path.exists() else []
    return df.to_dict("records"), failed


def _save_checkpoint(checkpoint_path, coef_rows, failed) -> None:
    import json
    from pathlib import Path
    if not checkpoint_path or not coef_rows:
        return
    p = Path(checkpoint_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(coef_rows).to_parquet(p, index=False)
    p.with_suffix(".meta.json").write_text(json.dumps({"failed_iterations": failed}))


def run_h2h4_bootstrap_lowmem(raw_shot_df: pd.DataFrame, n_iterations: int, seed: int,
                               min_success_fraction: float = 0.9, alpha: float = 0.05,
                               pointwise_bootstrap_iterations: int = 50,
                               checkpoint_path=None, checkpoint_every: int = 1,
                               precomputed: PrecomputedCellIndex | None = None,
                               verbose: bool = False):
    """Drop-in low-memory replacement for qnn_snr.stats.bootstrap.run_h2h4_bootstrap.

    Same (seed, iteration) -> RNG contract, same checkpoint format, same
    BootstrapResult-shaped return (as a plain namespace to avoid importing
    the production dataclass and its potential for divergence)."""
    from qnn_snr.stats.bootstrap import BootstrapResult

    if precomputed is None:
        t0 = time.time()
        precomputed = _precompute_cell_index(raw_shot_df)
        if verbose:
            print(f"  precompute_cell_index: {time.time() - t0:.1f}s", flush=True)

    coef_rows, failed = _load_checkpoint(checkpoint_path)
    done_iters = {r["iteration"] for r in coef_rows} | set(failed)
    for it in range(n_iterations):
        if it in done_iters:
            continue
        rng = np.random.default_rng((seed, it))
        t_it = time.time()
        try:
            pw = _one_iteration_lowmem(precomputed, rng, pointwise_bootstrap_iterations)
            snr_ds = build_h2h4_dataset(pw)
            if snr_ds.empty:
                failed.append(it)
                continue
            result = fit_mixed_model(H2_H4_FORMULA, snr_ds, "y")
            if result.error is not None or not result.converged:
                failed.append(it)
                continue
            coef_rows.append({"iteration": it, **result.params})
        except Exception as exc:  # noqa: BLE001 -- matches production bootstrap's blanket catch
            if verbose:
                print(f"  iteration {it} FAILED: {exc!r}", flush=True)
            failed.append(it)
        if verbose:
            print(f"  iteration {it} done in {time.time() - t_it:.1f}s", flush=True)
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
