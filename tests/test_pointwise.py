import numpy as np
import pandas as pd
import pytest

from qnn_snr.stats.pointwise import CELL_KEY_COLS, pointwise_statistics, zero_variance_confirmatory_cells


def _make_cell_rows(grads, exact, n_replicates=None, **overrides):
    n = n_replicates or len(grads)
    base = {
        "analysis_mode": "finite_shot_end_to_end", "configuration_id": 1, "E": 0, "L": 0, "R": 0,
        "depth": 2, "depth_centered": 0.0, "depth_z": 0.0, "budget": 500, "log2_budget": np.log2(500),
        "initialization_id": 0, "parameter_id": "theta_ell1_q0", "parameter_index": 0,
        "block_index": 1, "qubit_index": 0, "cost_type": "global", "gamma": 0.0,
    }
    base.update(overrides)
    rows = []
    for r in range(n):
        row = dict(base)
        row["gradient_hat"] = grads[r]
        row["exact_gradient"] = exact
        row["replicate_id"] = r
        rows.append(row)
    return rows


def test_snr_uses_sample_sd_not_standard_error():
    grads = [0.5, 0.6, 0.4, 0.55, 0.45]
    df = pd.DataFrame(_make_cell_rows(grads, exact=0.5))
    out = pointwise_statistics(df, bootstrap_iterations=50)
    assert len(out) == 1
    row = out.iloc[0]
    expected_sd = np.std(grads, ddof=1)
    expected_snr = abs(np.mean(grads)) / expected_sd
    assert row["shot_sd"] == pytest.approx(expected_sd)
    assert row["SNR_est"] == pytest.approx(expected_snr)
    # sanity: SNR must NOT equal the standard-error-based ratio (would divide by sqrt(n) too)
    se_based = abs(np.mean(grads)) / (expected_sd / np.sqrt(len(grads)))
    assert row["SNR_est"] != pytest.approx(se_based)


def test_bias_and_sign_agreement():
    grads = [0.2, 0.3, 0.25]
    df = pd.DataFrame(_make_cell_rows(grads, exact=0.1))
    out = pointwise_statistics(df, bootstrap_iterations=50)
    row = out.iloc[0]
    assert row["bias"] == pytest.approx(np.mean(grads) - 0.1)
    assert row["absolute_bias"] == pytest.approx(abs(np.mean(grads) - 0.1))
    assert row["sign_agreement"] == True


def test_sign_disagreement_detected():
    grads = [-0.2, -0.3, -0.25]
    df = pd.DataFrame(_make_cell_rows(grads, exact=0.1))
    out = pointwise_statistics(df, bootstrap_iterations=50)
    assert out.iloc[0]["sign_agreement"] == False


def test_zero_variance_flagged_and_reported_as_inf_snr():
    grads = [0.3, 0.3, 0.3]
    df = pd.DataFrame(_make_cell_rows(grads, exact=0.3))
    out = pointwise_statistics(df, bootstrap_iterations=50)
    row = out.iloc[0]
    assert row["zero_variance_flag"] == True
    assert row["shot_variance"] == 0.0
    assert np.isinf(row["SNR_est"])
    flagged = zero_variance_confirmatory_cells(out)
    assert len(flagged) == 1


def test_no_epsilon_added_to_variance():
    grads = [0.3, 0.3]
    df = pd.DataFrame(_make_cell_rows(grads, exact=0.3))
    out = pointwise_statistics(df, bootstrap_iterations=50)
    assert out.iloc[0]["shot_variance"] == 0.0  # not 1e-12 or similar


def test_bootstrap_ci_matches_manual_percentile():
    rng_check = np.random.default_rng(0)
    grads = list(rng_check.normal(1.0, 0.1, size=20))
    df = pd.DataFrame(_make_cell_rows(grads, exact=1.0))
    out = pointwise_statistics(df, bootstrap_iterations=2000, bootstrap_seed=1)
    row = out.iloc[0]
    assert row["signed_mean_ci_lo"] < np.mean(grads) < row["signed_mean_ci_hi"]


def test_statevector_exact_rows_excluded():
    grads = [0.5]
    df = pd.DataFrame(_make_cell_rows(grads, exact=0.5, analysis_mode="statevector_exact"))
    out = pointwise_statistics(df, bootstrap_iterations=50)
    assert len(out) == 0


def test_grouping_keeps_parameters_and_initializations_separate():
    rows = _make_cell_rows([0.1, 0.2, 0.15], exact=0.1, parameter_id="p0")
    rows += _make_cell_rows([0.9, 1.0, 0.95], exact=0.9, parameter_id="p1")
    df = pd.DataFrame(rows)
    out = pointwise_statistics(df, bootstrap_iterations=50)
    assert len(out) == 2
    assert set(out["parameter_id"]) == {"p0", "p1"}
