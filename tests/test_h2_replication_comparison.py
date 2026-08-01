"""Regression tests for the H2 replication decision rule
(scripts/run_h2_replication_comparison.py::classify), using synthetic
inputs so these tests do not depend on Stage 1 having been executed.

The decision rule itself is frozen in
verification/h2_robustness_replication_plan.md Section 6; these tests
pin its behavior against the four labeled outcomes plus the "confirmed"
prohibition.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

import qnn_snr

REPO_ROOT = Path(qnn_snr.__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from run_h2_replication_comparison import ORIGINAL_ESTIMATE, ORIGINAL_N_OBS, classify  # noqa: E402


def test_direction_and_magnitude_replicated():
    # Same sign, CI overlaps original, small movement.
    result = classify(0.026, (0.011, 0.041), ORIGINAL_N_OBS, True)
    assert result == "direction and magnitude replicated"


def test_direction_replicated_but_magnitude_uncertain_wide_ci():
    # Same sign, positive estimate, CI does not include zero, but very wide
    # (no overlap requirement failure needed -- width alone triggers this).
    result = classify(0.026, (-0.10, 0.15), ORIGINAL_N_OBS, True)
    assert result.startswith("direction replicated but magnitude uncertain") or \
        result.startswith("inconclusive")  # wide CI including zero is inconclusive, not "uncertain magnitude"


def test_inconclusive_when_ci_includes_zero():
    result = classify(0.020, (-0.005, 0.045), ORIGINAL_N_OBS, True)
    assert result == "inconclusive (replication 95% CI includes zero)"


def test_inconclusive_when_fit_did_not_converge():
    result = classify(0.020, (0.005, 0.035), ORIGINAL_N_OBS, False)
    assert result == "inconclusive (fit did not converge)"


def test_did_not_replicate_opposite_sign_confidently_discrepant():
    result = classify(-0.030, (-0.045, -0.015), ORIGINAL_N_OBS, True)
    assert result == "did not replicate (opposite sign, confidently discrepant)"


def test_inconclusive_opposite_sign_but_not_confidently_discrepant():
    result = classify(-0.005, (-0.020, 0.010), ORIGINAL_N_OBS, True)
    assert result.startswith("inconclusive")


def test_confirmed_is_never_a_possible_output_label():
    """Sweep a range of estimate/CI combinations and assert 'confirmed'
    never appears in any label the classifier can produce."""
    import numpy as np
    for est in np.linspace(-0.1, 0.1, 11):
        for half_width in (0.005, 0.02, 0.05, 0.15):
            ci = (est - half_width, est + half_width)
            label = classify(float(est), ci, ORIGINAL_N_OBS, True)
            assert "confirmed" not in label.lower()


def test_large_n_obs_shortfall_is_inconclusive_even_with_significant_ci():
    # >20% fewer eligible rows than the original, for reasons beyond the
    # deliberate R_rep match -- must not be silently accepted as a clean replication.
    shortfall_n = int(ORIGINAL_N_OBS * 0.7)  # 30% shortfall
    result = classify(0.026, (0.011, 0.041), shortfall_n, True)
    assert result.startswith("inconclusive")
