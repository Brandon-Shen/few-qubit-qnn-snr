"""Synthetic-data recovery tests for the mixed models (Section 20).

Response columns are synthesized directly (bypassing the exact_gradient ->
asinh(abs(.)) and SNR_est -> asinh(.) transforms, which have their own
narrow unit tests below) so these tests isolate the mixed-model *fitting*
machinery: design-matrix construction, nested random effects, and
coefficient extraction. Tolerances are generous by design -- Section 20
requires recovery "within reasonable tolerance," not that a single stochastic
draw always yields a significant p-value.
"""
import numpy as np
import pandas as pd
import pytest

from qnn_snr.config import CONFIGURATION_TABLE
from qnn_snr.stats.models import (
    CONFIRMATORY_MODE,
    H1_FORMULA,
    H2_H4_FORMULA,
    build_h1_dataset,
    build_h2h4_dataset,
    fit_h2h4_model,
    fit_mixed_model,
)

DEPTHS = [1, 2, 3, 4, 6]
N_PARAMS = 3
N_INIT = 40


def _depth_z_map():
    arr = np.array(DEPTHS, dtype=float)
    mean, std = arr.mean(), arr.std(ddof=0)
    return {d: (d - mean) / std for d in DEPTHS}


def _make_synthetic(coefs: dict, sigma_init: float, sigma_param: float, sigma_resid: float,
                     seed: int, extra_terms=None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dz = _depth_z_map()
    rows = []
    for init_id in range(N_INIT):
        u_init = rng.normal(0, sigma_init)
        for depth in DEPTHS:
            depth_z = dz[depth]
            for p in range(N_PARAMS):
                u_param = rng.normal(0, sigma_param)
                for config_id, (E, L, R) in CONFIGURATION_TABLE.items():
                    mu = (coefs.get("Intercept", 0.0)
                          + coefs.get("E", 0.0) * E + coefs.get("L", 0.0) * L + coefs.get("R", 0.0) * R
                          + coefs.get("E:L", 0.0) * E * L + coefs.get("E:R", 0.0) * E * R
                          + coefs.get("L:R", 0.0) * L * R + coefs.get("E:L:R", 0.0) * E * L * R
                          + coefs.get("depth_z", 0.0) * depth_z
                          + coefs.get("E:depth_z", 0.0) * E * depth_z
                          + coefs.get("L:depth_z", 0.0) * L * depth_z
                          + coefs.get("R:depth_z", 0.0) * R * depth_z
                          + coefs.get("log2_budget", 0.0) * 10.0  # fixed placeholder budget term
                          + coefs.get("L:R:depth_z", 0.0) * L * R * depth_z)
                    y = mu + u_init + u_param + rng.normal(0, sigma_resid)
                    rows.append({
                        "initialization_id": init_id, "configuration_id": config_id,
                        "E": float(E), "L": float(L), "R": float(R), "depth": depth,
                        "depth_z": depth_z, "log2_budget": 10.0, "parameter_id": f"p{p}",
                        "y": y, "a": y,
                    })
    return pd.DataFrame(rows)


@pytest.mark.parametrize("formula,response", [(H1_FORMULA, "a"), (H2_H4_FORMULA, "y")])
def test_null_dataset_recovers_near_zero_interactions(formula, response):
    df = _make_synthetic({"Intercept": 1.0}, sigma_init=0.2, sigma_param=0.15, sigma_resid=0.1, seed=1)
    result = fit_mixed_model(formula, df, response)
    assert result.error is None, result.error
    assert result.converged
    for coef in ("E:L", "E:R", "L:R"):
        assert abs(result.params[coef]) < 0.15, f"{coef}={result.params[coef]}"


def test_h1_only_dataset_recovers_negative_eta_EL():
    df = _make_synthetic({"Intercept": 1.0, "E:L": -0.6}, sigma_init=0.2, sigma_param=0.15,
                          sigma_resid=0.1, seed=2)
    result = fit_mixed_model(H1_FORMULA, df, "a")
    assert result.converged
    assert result.params["E:L"] == pytest.approx(-0.6, abs=0.2)
    assert result.params["E:L"] < 0


def test_h2_only_dataset_recovers_beta_EL():
    df = _make_synthetic({"Intercept": 1.0, "E:L": 0.5}, sigma_init=0.2, sigma_param=0.15,
                          sigma_resid=0.1, seed=3)
    result = fit_mixed_model(H2_H4_FORMULA, df, "y")
    assert result.converged
    assert result.params["E:L"] == pytest.approx(0.5, abs=0.2)


def test_h3_only_dataset_recovers_beta_ER():
    df = _make_synthetic({"Intercept": 1.0, "E:R": 0.45}, sigma_init=0.2, sigma_param=0.15,
                          sigma_resid=0.1, seed=4)
    result = fit_mixed_model(H2_H4_FORMULA, df, "y")
    assert result.converged
    assert result.params["E:R"] == pytest.approx(0.45, abs=0.2)


def test_h4_only_dataset_recovers_beta_LRd():
    df = _make_synthetic({"Intercept": 1.0, "L:R:depth_z": 0.4}, sigma_init=0.2, sigma_param=0.15,
                          sigma_resid=0.1, seed=5)
    result = fit_mixed_model(H2_H4_FORMULA, df, "y")
    assert result.converged
    assert result.params["L:R:depth_z"] == pytest.approx(0.4, abs=0.2)


def test_combined_dataset_recovers_all_effects_simultaneously():
    coefs = {"Intercept": 1.0, "E": 0.3, "L": -0.2, "R": 0.1, "E:L": -0.4, "E:R": 0.35,
             "L:R": 0.1, "E:L:R": 0.05, "depth_z": 0.2, "E:depth_z": -0.1,
             "L:R:depth_z": 0.3}
    df = _make_synthetic(coefs, sigma_init=0.25, sigma_param=0.15, sigma_resid=0.1, seed=6)
    result = fit_mixed_model(H2_H4_FORMULA, df, "y")
    assert result.converged
    for name, true_val in coefs.items():
        if name == "Intercept" or name not in result.params:
            continue
        assert result.params[name] == pytest.approx(true_val, abs=0.2), f"{name}"


def test_convergence_and_diagnostics_reported():
    df = _make_synthetic({"Intercept": 1.0}, sigma_init=0.2, sigma_param=0.15, sigma_resid=0.1, seed=7)
    result = fit_mixed_model(H2_H4_FORMULA, df, "y")
    assert result.converged
    assert result.optimizer_used in result.attempted_optimizers
    assert result.n_obs == len(df)
    assert result.n_groups == N_INIT
    assert np.isfinite(result.condition_number)
    assert "resid_sd" in result.residual_diagnostics


def test_build_h1_dataset_applies_asinh_abs():
    df = pd.DataFrame({"exact_gradient": [-2.0, 3.0, 0.0]})
    out = build_h1_dataset(df)
    assert np.allclose(out["a"], np.arcsinh(np.abs([-2.0, 3.0, 0.0])))


def test_build_h2h4_dataset_applies_asinh_and_drops_nonfinite():
    df = pd.DataFrame({"SNR_est": [1.0, float("inf"), float("nan"), 2.5]})
    out = build_h2h4_dataset(df)
    assert len(out) == 2
    assert np.allclose(sorted(out["y"]), sorted(np.arcsinh([1.0, 2.5])))


def _two_mode_snr_df():
    # Minimal frame with both modes present -- this is the shape that silently
    # produced the pooled confirmatory fit before the guard existed.
    return pd.DataFrame({
        "SNR_est": [1.0, 2.0, 1.5, 2.5],
        "analysis_mode": ["finite_shot_conditional", "finite_shot_conditional",
                           "finite_shot_end_to_end", "finite_shot_end_to_end"],
    })


def test_build_h2h4_dataset_rejects_mixed_analysis_mode_by_default():
    """Regression test for the mode-pooling bug (verification/mode_pooling_guard.md):
    a dataframe spanning both finite_shot_conditional and finite_shot_end_to_end
    must not silently fit as one pooled model."""
    df = _two_mode_snr_df()
    with pytest.raises(ValueError, match="analysis_mode"):
        build_h2h4_dataset(df)


def test_build_h2h4_dataset_allows_pooling_with_explicit_opt_in():
    df = _two_mode_snr_df()
    out = build_h2h4_dataset(df, pool_modes=True)
    assert len(out) == 4


def test_build_h2h4_dataset_single_mode_does_not_raise():
    df = _two_mode_snr_df()
    single = df[df["analysis_mode"] == CONFIRMATORY_MODE]
    out = build_h2h4_dataset(single)
    assert len(out) == 2


def test_fit_h2h4_model_rejects_mixed_analysis_mode():
    df = _two_mode_snr_df()
    with pytest.raises(ValueError, match="analysis_mode"):
        fit_h2h4_model(df)
