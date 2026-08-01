"""Regression tests for the H2 robustness package, Phase 4: robust
inference methods (A-F) on the original data.

Covers the methods that do not require long-running resampling (C, D, F);
tests for (B) initialization-level resampling and (E) extended
leave-one-out are appended once those background jobs complete (see
verification/h2_robustness_replication_results.md for status).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import qnn_snr

REPO_ROOT = Path(qnn_snr.__file__).resolve().parent.parent
PROD_DIR = REPO_ROOT / "results" / "production_confirmatory"
ROBUST_DIR = REPO_ROOT / "results" / "h2_robustness" / "robust_inference"
POINTWISE_PATH = PROD_DIR / "pointwise_gradient_statistics.parquet"

pytestmark = pytest.mark.skipif(
    not POINTWISE_PATH.exists(),
    reason="full confirmatory dataset not present in this checkout",
)


@pytest.mark.skipif(not (ROBUST_DIR / "h2_cluster_robust_ols.csv").exists(), reason="Phase 4(C) has not been run yet")
class TestClusterRobust:
    def test_cluster_robust_uses_all_50_initializations_as_clusters(self):
        df = pd.read_csv(ROBUST_DIR / "h2_cluster_robust_ols.csv")
        assert (df["n_clusters"] == 50).all()

    def test_cluster_robust_n_obs_matches_mixed_model_eligible_set(self):
        df = pd.read_csv(ROBUST_DIR / "h2_cluster_robust_ols.csv")
        assert (df["n_obs"] == 101_891).all()

    def test_cluster_robust_se_is_reported_and_not_identical_to_naive_ols(self):
        df = pd.read_csv(ROBUST_DIR / "h2_cluster_robust_ols.csv")
        el = df[df["coefficient"] == "E:L"].iloc[0]
        assert el["se_cluster_robust"] > 0
        # Cluster-robust SE at the initialization level should differ from
        # (and here, be larger than) the mixed model's Wald SE (0.007279),
        # since it does not assume the mixed model's parametric variance
        # structure -- this is the whole point of the check, so assert the
        # comparison is at least computable and nontrivial, not a specific
        # direction (that would be a significance-motivated assertion).
        assert el["se_cluster_robust"] != 0.007279011371641417


@pytest.mark.skipif(not (ROBUST_DIR / "h2_depth_stratified.csv").exists(), reason="Phase 4(D) has not been run yet")
class TestDepthStratified:
    def test_all_five_depths_present(self):
        df = pd.read_csv(ROBUST_DIR / "h2_depth_stratified.csv")
        assert set(df["depth"].unique()) == {1, 2, 3, 4, 6}

    def test_depth_strata_n_obs_sums_to_full_sample(self):
        df = pd.read_csv(ROBUST_DIR / "h2_depth_stratified.csv")
        el = df[df["coefficient"] == "E:L"]
        assert int(el["n_obs"].sum()) == 101_891

    def test_no_stratum_was_silently_dropped_on_failure(self):
        df = pd.read_csv(ROBUST_DIR / "h2_depth_stratified.csv")
        # Every depth must have a row, converged or not (failures are recorded, not omitted).
        assert len(df[df["coefficient"] == "E:L"]) == 5


@pytest.mark.skipif(not (ROBUST_DIR / "h2_budget_stratified.csv").exists(), reason="Phase 4(D) has not been run yet")
class TestBudgetStratified:
    def test_two_budget_strata_present(self):
        df = pd.read_csv(ROBUST_DIR / "h2_budget_stratified.csv")
        assert set(df["budget_stratum"].unique()) == {"B<=500", "B>500"}

    def test_budget_strata_n_obs_sums_to_full_sample(self):
        df = pd.read_csv(ROBUST_DIR / "h2_budget_stratified.csv")
        el = df[df["coefficient"] == "E:L"]
        assert int(el["n_obs"].sum()) == 101_891


@pytest.mark.skipif(not (ROBUST_DIR / "h2_variance_floor_sensitivity_grid.csv").exists(),
                     reason="Phase 4(F.3) has not been run yet")
class TestVarianceFloorGrid:
    def test_grid_has_seven_predefined_points(self):
        df = pd.read_csv(ROBUST_DIR / "h2_variance_floor_sensitivity_grid.csv")
        assert len(df) == 7

    def test_baseline_floor_zero_matches_production_complete_case(self):
        df = pd.read_csv(ROBUST_DIR / "h2_variance_floor_sensitivity_grid.csv")
        baseline = df[df["floor"] == 0.0].iloc[0]
        assert baseline["n_obs"] == 101_891
        assert np.isclose(baseline["E:L_estimate"], 0.024995843985971582, atol=1e-9)

    def test_nonzero_floors_include_all_102400_cells(self):
        df = pd.read_csv(ROBUST_DIR / "h2_variance_floor_sensitivity_grid.csv")
        nonzero = df[df["floor"] != 0.0]
        assert (nonzero["n_obs"] == 102_400).all()

    def test_no_floor_is_silently_selected_as_primary(self):
        """The full trajectory must be written; this test just guards
        against a future edit collapsing the grid to a single row."""
        df = pd.read_csv(ROBUST_DIR / "h2_variance_floor_sensitivity_grid.csv")
        assert df["floor"].nunique() == 7


@pytest.mark.skipif(not (ROBUST_DIR / "h2_zero_variance_logistic_model.csv").exists(),
                     reason="Phase 4(F.2) has not been run yet")
def test_logistic_model_of_zero_variance_flag_was_recorded_including_separation_caveat():
    df = pd.read_csv(ROBUST_DIR / "h2_zero_variance_logistic_model.csv")
    assert "L" in set(df["coefficient"])
    l_row = df[df["coefficient"] == "L"].iloc[0]
    # L deterministically predicts zero_variance_flag==0 whenever L==1 (Phase 2),
    # which produces quasi-complete separation -- the huge SE is the expected
    # symptom, not a bug; this test documents that this is understood, not silently trusted.
    assert l_row["se"] > 100  # a well-behaved logistic fit would never have an SE this large
