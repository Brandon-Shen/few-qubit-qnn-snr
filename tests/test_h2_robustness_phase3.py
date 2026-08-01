"""Regression tests for the H2 robustness package, Phase 3
(scripts/run_h2_decomposition.py): numerator/denominator decomposition
correctness and row-set matching to the adopted SNR model.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import qnn_snr

REPO_ROOT = Path(qnn_snr.__file__).resolve().parent.parent
PROD_DIR = REPO_ROOT / "results" / "production_confirmatory"
DECOMP_DIR = REPO_ROOT / "results" / "h2_robustness" / "decomposition"
POINTWISE_PATH = PROD_DIR / "pointwise_gradient_statistics.parquet"

pytestmark = pytest.mark.skipif(
    not POINTWISE_PATH.exists(),
    reason="full confirmatory dataset not present in this checkout",
)


@pytest.fixture(scope="module")
def eligible_df():
    pw = pd.read_parquet(POINTWISE_PATH)
    eo = pw[pw["analysis_mode"] == "finite_shot_end_to_end"]
    return eo[~eo["zero_variance_flag"]]


def test_numerator_and_denominator_use_identical_eligible_set_as_snr_model(eligible_df):
    assert len(eligible_df) == 101_891
    assert (eligible_df["shot_sd"] > 0).all()
    assert np.isfinite(eligible_df["mu_hat"]).all()


@pytest.mark.skipif(not DECOMP_DIR.exists(), reason="Phase 3 decomposition has not been run yet")
class TestDecompositionOutputs:
    def test_summary_has_three_models_times_three_coefficients(self):
        df = pd.read_csv(DECOMP_DIR / "h2_decomposition_summary.csv")
        assert len(df) == 9  # 3 models x 3 target coefficients
        assert set(df["model"].unique()) == {
            "SNR_est (reference, not refit)",
            "numerator (gradient-mean magnitude)",
            "denominator (repeated-shot SD)",
        }
        assert set(df["coefficient"].unique()) == {"E:L", "E:R", "L:R:depth_z"}

    def test_all_models_share_the_same_n_obs(self):
        df = pd.read_csv(DECOMP_DIR / "h2_decomposition_summary.csv")
        assert df["n_obs"].nunique() == 1
        assert int(df["n_obs"].iloc[0]) == 101_891

    def test_reference_snr_row_matches_adopted_beta_EL(self):
        df = pd.read_csv(DECOMP_DIR / "h2_decomposition_summary.csv")
        row = df[(df["model"] == "SNR_est (reference, not refit)") & (df["coefficient"] == "E:L")].iloc[0]
        assert np.isclose(row["estimate"], 0.024995843985971582, atol=1e-9)

    def test_numerator_and_denominator_are_labeled_primary_not_confirmatory(self):
        df = pd.read_csv(DECOMP_DIR / "h2_decomposition_summary.csv")
        primary = df[df["model"] != "SNR_est (reference, not refit)"]
        assert (primary["role"] == "primary").all()
        reference = df[df["model"] == "SNR_est (reference, not refit)"]
        assert (reference["role"] == "reference").all()

    def test_descriptive_bias_table_covers_all_four_EL_cells(self):
        df = pd.read_csv(DECOMP_DIR / "h2_descriptive_bias_sign_by_EL.csv")
        cells = set(zip(df["E"], df["L"]))
        assert cells == {(0, 0), (0, 1), (1, 0), (1, 1)}
