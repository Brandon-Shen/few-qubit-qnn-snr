"""Regression tests for the completed Phase 4(B) and (E) outputs
(initialization-level resampling and extended leave-one-out), plus the
completed replication bootstrap (Phase 6-7).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import qnn_snr

REPO_ROOT = Path(qnn_snr.__file__).resolve().parent.parent
ROBUST_DIR = REPO_ROOT / "results" / "h2_robustness" / "robust_inference"
REPL_DIR = REPO_ROOT / "results" / "h2_replication_v1" / "_pipeline_output_stage1"

pytestmark = pytest.mark.skipif(
    not (ROBUST_DIR / "init_resample_summary.json").exists(),
    reason="Phase 4(B) has not completed in this checkout",
)


def test_init_resample_completed_all_50_iterations():
    summary = json.loads((ROBUST_DIR / "init_resample_summary.json").read_text())
    assert summary["n_iterations_successful"] == 50
    assert summary["seed"] == 900001


def test_init_resample_never_observed_l1_zero_variance():
    """Across all 50 independent resamples (with inner replicate
    resampling), the L=0 confinement must hold in every single one --
    the exhaustive version of the Phase 2 finding."""
    summary = json.loads((ROBUST_DIR / "init_resample_summary.json").read_text())
    assert summary["any_l1_zero_variance_ever_observed_across_resamples"] is False

    diag = pd.read_csv(ROBUST_DIR / "init_resample_per_iteration_diagnostics.csv")
    assert (diag["n_l1_zero_variance"] == 0).all()
    assert len(diag) == 50


def test_init_resample_every_iteration_explicitly_recorded_zero_variance_count():
    """No silent exclusion: every iteration's diagnostics row must report
    a zero-variance count, not just a coefficient."""
    diag = pd.read_csv(ROBUST_DIR / "init_resample_per_iteration_diagnostics.csv")
    assert diag["n_zero_variance"].notna().all()
    assert diag["n_non_finite_unexplained"].eq(0).all()


@pytest.mark.skipif(not (ROBUST_DIR / "h2_loo_numerator.csv").exists(), reason="Phase 4(E) extension not run")
class TestExtendedLOO:
    def test_all_50_deletions_present_for_both_components(self):
        num = pd.read_csv(ROBUST_DIR / "h2_loo_numerator.csv")
        den = pd.read_csv(ROBUST_DIR / "h2_loo_denominator.csv")
        assert len(num) == 50
        assert len(den) == 50
        assert num["converged"].all()
        assert den["converged"].all()

    def test_no_sign_reversal_in_numerator_or_denominator_loo(self):
        num = pd.read_csv(ROBUST_DIR / "h2_loo_numerator.csv")
        den = pd.read_csv(ROBUST_DIR / "h2_loo_denominator.csv")
        assert (num["estimate"] > 0).all()
        assert (den["estimate"] < 0).all()

    def test_combined_influence_table_was_written(self):
        assert (ROBUST_DIR / "h2_loo_combined_influence.csv").exists()
        combined = pd.read_csv(ROBUST_DIR / "h2_loo_combined_influence.csv")
        assert len(combined) == 50


@pytest.mark.skipif(not (REPL_DIR / "bootstrap_summary_tight_checkpoints.json").exists(),
                     reason="replication bootstrap has not completed in this checkout")
class TestReplicationBootstrap:
    def test_replication_bootstrap_completed_all_iterations_no_failures(self):
        summary = json.loads((REPL_DIR / "bootstrap_summary_tight_checkpoints.json").read_text())
        assert summary["h1_n_successful"] == summary["n_iterations_requested"]
        assert summary["h2h4_n_successful"] == summary["n_iterations_requested"]
        assert summary["h2h4_failed_iterations"] == []

    def test_replication_bootstrap_ci_reported_for_all_four_hypotheses(self):
        summary = json.loads((REPL_DIR / "bootstrap_summary_tight_checkpoints.json").read_text())
        assert set(summary["percentile_ci"].keys()) == {"H1", "H2", "H3", "H4"}
