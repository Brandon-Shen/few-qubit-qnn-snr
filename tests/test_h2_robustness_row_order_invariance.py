"""Phase 8: row-order invariance tests for the H2 robustness package's
core aggregation functions -- shuffling the input pointwise dataframe must
never change a marginal count, a decomposition coefficient, or the
zero-variance confinement finding.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import qnn_snr
from qnn_snr.stats.models import build_h2h4_dataset, fit_h2h4_model

REPO_ROOT = Path(qnn_snr.__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
POINTWISE_PATH = REPO_ROOT / "results" / "production_confirmatory" / "pointwise_gradient_statistics.parquet"
sys.path.insert(0, str(SCRIPTS_DIR))

pytestmark = pytest.mark.skipif(
    not POINTWISE_PATH.exists(),
    reason="full confirmatory dataset not present in this checkout",
)


@pytest.fixture(scope="module")
def eo_df():
    pw = pd.read_parquet(POINTWISE_PATH)
    return pw[pw["analysis_mode"] == "finite_shot_end_to_end"].copy()


def test_marginal_table_is_row_order_invariant(eo_df):
    from run_h2_zero_variance_audit import marginal_table

    rng = np.random.default_rng(12345)
    shuffled = eo_df.sample(frac=1.0, random_state=rng.integers(0, 2**31 - 1)).reset_index(drop=True)

    original = marginal_table(eo_df, ["L"]).sort_values("L").reset_index(drop=True)
    shuffled_result = marginal_table(shuffled, ["L"]).sort_values("L").reset_index(drop=True)
    pd.testing.assert_frame_equal(original, shuffled_result)


def test_fit_h2h4_model_coefficient_is_row_order_invariant(eo_df):
    rng = np.random.default_rng(999)
    shuffled = eo_df.sample(frac=1.0, random_state=rng.integers(0, 2**31 - 1)).reset_index(drop=True)

    original_fit = fit_h2h4_model(eo_df)
    shuffled_fit = fit_h2h4_model(shuffled)

    assert np.isclose(original_fit.params["E:L"], shuffled_fit.params["E:L"], atol=1e-8)
    assert original_fit.n_obs == shuffled_fit.n_obs


def test_zero_variance_confinement_is_row_order_invariant(eo_df):
    rng = np.random.default_rng(42)
    shuffled = eo_df.sample(frac=1.0, random_state=rng.integers(0, 2**31 - 1)).reset_index(drop=True)

    for df in (eo_df, shuffled):
        l1_excluded = int(df.loc[df["L"] == 1, "zero_variance_flag"].sum())
        assert l1_excluded == 0
