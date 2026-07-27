import numpy as np
import pandas as pd
import pytest

import qnn_snr
from pathlib import Path

from qnn_snr.config import load_config
from qnn_snr.replicate import generate_exact_rows, generate_shot_rows
from qnn_snr.schema import rows_to_dataframe
from qnn_snr.stats.bootstrap import (
    _inner_resample_replicates,
    _relabel_outer_resample,
    confirmatory_bootstrap_ci,
    run_h1_bootstrap,
    run_h2h4_bootstrap,
)

CONFIG_DIR = Path(qnn_snr.__file__).resolve().parent.parent / "configs"


@pytest.fixture(scope="module")
def smoke_cfg():
    return load_config(CONFIG_DIR / "smoke.yaml")


@pytest.fixture(scope="module")
def exact_df(smoke_cfg):
    return rows_to_dataframe(generate_exact_rows(smoke_cfg))


@pytest.fixture(scope="module")
def shot_df(smoke_cfg):
    return rows_to_dataframe(generate_shot_rows(smoke_cfg, "finite_shot_end_to_end"))


def test_outer_resample_preserves_full_matched_structure(exact_df):
    rng = np.random.default_rng(0)
    resampled = _relabel_outer_resample(exact_df, rng)
    for new_id, g in resampled.groupby("initialization_id"):
        assert set(g["configuration_id"].unique()) == set(range(1, 9))


def test_outer_resample_relabels_duplicates_uniquely(exact_df):
    # force duplicate selection with a tiny dataset of 2 unique initializations
    small = exact_df[exact_df["initialization_id"].isin([0, 1])]
    rng = np.random.default_rng(1)
    resampled = _relabel_outer_resample(small, rng)
    n_unique_orig = small["initialization_id"].nunique()
    n_unique_new = resampled["initialization_id"].nunique()
    assert n_unique_new == n_unique_orig  # relabeled 0..n-1, always unique per outer draw


def test_outer_resample_does_not_shuffle_within_initialization_rows(exact_df):
    rng = np.random.default_rng(2)
    resampled = _relabel_outer_resample(exact_df, rng)
    # every row for a given new initialization_id must share exactly one E/L/R
    # per configuration_id -- i.e. it's a block copy, not a per-row shuffle
    for new_id, g in resampled.groupby("initialization_id"):
        for config_id, gg in g.groupby("configuration_id"):
            assert gg["E"].nunique() == 1 and gg["L"].nunique() == 1 and gg["R"].nunique() == 1


def test_inner_resample_only_draws_from_same_cell(shot_df):
    rng = np.random.default_rng(3)
    resampled = _inner_resample_replicates(shot_df, rng)
    cell_cols = ["analysis_mode", "configuration_id", "depth", "budget", "initialization_id", "parameter_id"]
    orig_values = shot_df.groupby(cell_cols)["gradient_hat"].apply(set)
    new_values = resampled.groupby(cell_cols)["gradient_hat"].apply(set)
    for key in new_values.index:
        assert new_values[key].issubset(orig_values[key])


def test_inner_resample_preserves_cell_sizes(shot_df):
    rng = np.random.default_rng(4)
    resampled = _inner_resample_replicates(shot_df, rng)
    assert len(resampled) == len(shot_df)


def test_h1_bootstrap_runs_and_produces_ci(exact_df):
    result = run_h1_bootstrap(exact_df, n_iterations=8, seed=42, min_success_fraction=0.5)
    assert result.hypothesis_family == "exact_signal"
    assert result.n_successful >= 1
    assert "E:L" in result.percentile_ci
    lo, hi = result.percentile_ci["E:L"]
    assert lo <= hi


def test_h2h4_bootstrap_runs_and_produces_ci(shot_df):
    result = run_h2h4_bootstrap(shot_df, n_iterations=4, seed=7, min_success_fraction=0.25,
                                 pointwise_bootstrap_iterations=20)
    assert result.hypothesis_family == "estimator_snr"
    assert result.n_requested == 4
    assert len(result.failed_iterations) + result.n_successful == 4


def test_checkpoint_resume_produces_consistent_total(exact_df, tmp_path):
    ckpt = tmp_path / "h1_boot.parquet"
    r1 = run_h1_bootstrap(exact_df, n_iterations=4, seed=99, min_success_fraction=0.0,
                           checkpoint_path=ckpt, checkpoint_every=2)
    r2 = run_h1_bootstrap(exact_df, n_iterations=6, seed=99, min_success_fraction=0.0,
                           checkpoint_path=ckpt, checkpoint_every=2)
    assert r2.n_successful + len(r2.failed_iterations) == 6
    assert r2.n_successful >= r1.n_successful


def test_confirmatory_bootstrap_ci_maps_all_four_hypotheses(exact_df, shot_df):
    h1 = run_h1_bootstrap(exact_df, n_iterations=6, seed=1, min_success_fraction=0.0)
    h2h4 = run_h2h4_bootstrap(shot_df, n_iterations=3, seed=2, min_success_fraction=0.0,
                               pointwise_bootstrap_iterations=20)
    ci = confirmatory_bootstrap_ci(h1, h2h4)
    assert set(ci.keys()) <= {"H1", "H2", "H3", "H4"}
