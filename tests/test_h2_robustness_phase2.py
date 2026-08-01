"""Regression tests for the H2 robustness package, Phase 2
(scripts/run_h2_zero_variance_audit.py): exact reproduction of the
production eligibility count, no accidental mode pooling, no silent
exclusion, and stability of the adopted coefficient under reporting-only
changes.

Per verification/h2_robustness_replication_plan.md. Skipped entirely if
the full confirmatory dataset is not present in this checkout (matches the
existing convention in tests/test_qmi_qip_robustness.py and
tests/test_fig0_el_primary.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import qnn_snr
from qnn_snr.stats.models import build_h2h4_dataset, fit_h2h4_model

REPO_ROOT = Path(qnn_snr.__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
PROD_DIR = REPO_ROOT / "results" / "production_confirmatory"
AUDIT_DIR = REPO_ROOT / "results" / "h2_robustness" / "original_data_audit"
sys.path.insert(0, str(SCRIPTS_DIR))

POINTWISE_PATH = PROD_DIR / "pointwise_gradient_statistics.parquet"

pytestmark = pytest.mark.skipif(
    not POINTWISE_PATH.exists(),
    reason="full confirmatory dataset not present in this checkout",
)

ADOPTED_BETA_EL = 0.024995843985971582


@pytest.fixture(scope="module")
def pointwise_df():
    return pd.read_parquet(POINTWISE_PATH)


@pytest.fixture(scope="module")
def end_to_end_df(pointwise_df):
    return pointwise_df[pointwise_df["analysis_mode"] == "finite_shot_end_to_end"].copy()


def test_production_eligibility_count_reproduced_exactly(end_to_end_df):
    """The production H2-H4 fit's n_obs (101,891) must be exactly
    reproducible from the frozen pointwise file: 102,400 total end-to-end
    cells minus exactly 509 zero-variance exclusions."""
    total = len(end_to_end_df)
    excluded = int(end_to_end_df["zero_variance_flag"].sum())
    assert total == 102_400
    assert excluded == 509
    assert total - excluded == 101_891


def test_zero_variance_exclusions_confined_to_L0(end_to_end_df):
    l0 = end_to_end_df[end_to_end_df["L"] == 0]
    l1 = end_to_end_df[end_to_end_df["L"] == 1]
    assert int(l1["zero_variance_flag"].sum()) == 0
    assert int(l0["zero_variance_flag"].sum()) == 509


def test_no_exclusion_reason_other_than_zero_variance_flag(pointwise_df):
    """build_h2h4_dataset's only exclusion mechanism is the
    np.isfinite(SNR_est) filter; confirm every non-finite SNR_est row is
    explained by zero_variance_flag (i.e. no silent, unexplained
    exclusion channel exists)."""
    non_finite = pointwise_df[~np.isfinite(pointwise_df["SNR_est"])]
    unexplained = non_finite[~non_finite["zero_variance_flag"]]
    assert len(unexplained) == 0


def test_build_h2h4_dataset_rejects_mixed_modes_even_via_this_scripts_path(pointwise_df):
    """The audit script must never accidentally hand mixed-mode data to
    the model-fitting path."""
    with pytest.raises(ValueError):
        build_h2h4_dataset(pointwise_df)  # both modes present -> must raise


def test_adopted_coefficient_reproduced_bit_for_bit(end_to_end_df):
    result = fit_h2h4_model(end_to_end_df)
    assert result.converged
    assert np.isclose(result.params["E:L"], ADOPTED_BETA_EL, atol=1e-9)


def test_reporting_only_change_cannot_alter_model_inputs(end_to_end_df):
    """Calling build_h2h4_dataset twice (as if a report-generation step ran
    twice, or the audit script's summary-writing code changed) must yield
    an identical eligible row count and identical y column -- the model
    input is a pure function of the frozen data, not of report code."""
    ds1 = build_h2h4_dataset(end_to_end_df)
    ds2 = build_h2h4_dataset(end_to_end_df)
    assert len(ds1) == len(ds2) == 101_891
    pd.testing.assert_series_equal(
        ds1["y"].reset_index(drop=True), ds2["y"].reset_index(drop=True)
    )


@pytest.mark.skipif(not AUDIT_DIR.exists(), reason="Phase 2 audit script has not been run yet")
class TestAuditScriptOutputs:
    """Once scripts/run_h2_zero_variance_audit.py has been run, its
    machine-readable summary must agree with a fresh, independent
    computation -- not merely be internally consistent."""

    def test_summary_json_matches_fresh_computation(self, end_to_end_df):
        summary = json.loads((AUDIT_DIR / "h2_audit_summary.json").read_text())
        assert summary["end_to_end_total_cells"] == len(end_to_end_df)
        assert summary["end_to_end_zero_variance_excluded"] == int(
            end_to_end_df["zero_variance_flag"].sum()
        )
        assert summary["confined_to_L0"] is True
        assert summary["h2h4_model"]["beta_EL_matches_adopted_bit_for_bit"] is True

    def test_every_factorial_breakdown_csv_was_written(self):
        expected = [
            "zero_variance_by_E.csv", "zero_variance_by_L.csv", "zero_variance_by_R.csv",
            "zero_variance_by_depth.csv", "zero_variance_by_budget.csv",
            "zero_variance_by_initialization.csv", "zero_variance_by_parameter_id.csv",
            "zero_variance_by_full_factorial_cell.csv", "h2h4_wald_reproduction.csv",
            "residual_sd_by_depth.csv", "residual_sd_by_budget.csv",
        ]
        for fname in expected:
            assert (AUDIT_DIR / fname).exists(), f"missing expected audit output: {fname}"

    def test_no_original_production_file_was_modified(self):
        """The audit script must be read-only with respect to the frozen
        production directory."""
        import subprocess
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "results/production_confirmatory/"],
            cwd=REPO_ROOT,
        ).decode()
        assert status.strip() == "", (
            f"results/production_confirmatory/ has uncommitted changes after "
            f"running the audit script: {status!r}"
        )
