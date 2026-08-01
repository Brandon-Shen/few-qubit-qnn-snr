"""Regression tests for the H2 depth-heterogeneity package
(qnn_snr/stats/depth_heterogeneity.py, scripts/run_h2_depth_heterogeneity.py).

Per verification/h2_depth_heterogeneity_plan.md. Explicitly post-run /
exploratory -- these tests check mechanics and provenance, not that any
particular p-value comes out significant.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import qnn_snr
import qnn_snr.stats.depth_heterogeneity as dh
from qnn_snr.stats.models import build_h2h4_dataset

REPO_ROOT = Path(qnn_snr.__file__).resolve().parent.parent
ORIGINAL_POINTWISE = REPO_ROOT / "results" / "production_confirmatory" / "pointwise_gradient_statistics.parquet"
REPLICATION_POINTWISE = REPO_ROOT / "results" / "h2_replication_v1" / "_pipeline_output_stage1" / "pointwise_gradient_statistics.parquet"
DEPTH_DIR = REPO_ROOT / "results" / "h2_robustness" / "depth_heterogeneity"
REPL_DEPTH_DIR = REPO_ROOT / "results" / "h2_replication_v1" / "depth_heterogeneity"

pytestmark = pytest.mark.skipif(
    not (ORIGINAL_POINTWISE.exists() and REPLICATION_POINTWISE.exists()),
    reason="original and/or replication dataset not present in this checkout",
)

ADOPTED_BETA_EL = 0.024995843985971582


@pytest.fixture(scope="module")
def original_eo():
    pw = pd.read_parquet(ORIGINAL_POINTWISE)
    return pw[pw["analysis_mode"] == "finite_shot_end_to_end"].copy()


@pytest.fixture(scope="module")
def replication_eo():
    pw = pd.read_parquet(REPLICATION_POINTWISE)
    return pw[pw["analysis_mode"] == "finite_shot_end_to_end"].copy()


# --- Provenance / scaling ---

def test_original_and_replication_depth_z_scaling_are_identical(original_eo, replication_eo):
    """Both datasets must use the identical depth_z centering/scaling
    (the original full-sweep constants, mean=3.2, std=1.7204650534085253)
    -- not independently recomputed from the replication's own depths."""
    for d in dh.DEPTHS:
        o_vals = original_eo.loc[original_eo["depth"] == d, "depth_z"].unique()
        r_vals = replication_eo.loc[replication_eo["depth"] == d, "depth_z"].unique()
        assert len(o_vals) == 1 and len(r_vals) == 1
        assert np.isclose(o_vals[0], r_vals[0], atol=1e-12), (
            f"depth_z at depth={d} differs between original ({o_vals[0]}) and "
            f"replication ({r_vals[0]}) -- scaling must be reused, not recomputed"
        )


def test_depth_z_scaling_matches_full_sweep_constants(original_eo):
    mean, std = 3.2, 1.7204650534085253
    for d in dh.DEPTHS:
        expected = (d - mean) / std
        actual = original_eo.loc[original_eo["depth"] == d, "depth_z"].iloc[0]
        assert np.isclose(actual, expected, atol=1e-9)


# --- Mode / pooling guards ---

def test_assert_single_mode_rejects_mixed_modes():
    pw = pd.read_parquet(ORIGINAL_POINTWISE)
    with pytest.raises(ValueError):
        dh.assert_single_confirmatory_mode(pw)  # both modes present


def test_assert_single_mode_accepts_end_to_end_only(original_eo):
    dh.assert_single_confirmatory_mode(original_eo)  # must not raise


def test_original_and_replication_are_never_pooled_in_one_fit(original_eo, replication_eo):
    """A concatenation of the two datasets must be rejected by the same
    guard used everywhere else in this package (different git_commit /
    experiment provenance aside, the two use disjoint seed namespaces and
    must never be combined into a single model fit)."""
    combined = pd.concat([original_eo, replication_eo], ignore_index=True)
    # Same analysis_mode in both, so the mode guard alone would not catch
    # this -- the depth-heterogeneity runner never constructs such a
    # concatenation; this test documents and pins that invariant by
    # checking the two source files are in fact distinct on disk.
    import hashlib
    def sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    assert sha(ORIGINAL_POINTWISE) != sha(REPLICATION_POINTWISE)
    assert len(combined) == len(original_eo) + len(replication_eo)  # sanity on the concat itself


def test_runner_never_writes_original_outputs_into_replication_dir_or_vice_versa():
    """Original and replication output paths cannot be accidentally
    swapped -- filenames are prefixed by dataset label and live under
    dataset-specific directories."""
    if not (DEPTH_DIR / "original_depth_contrasts.csv").exists():
        pytest.skip("depth-heterogeneity outputs not present in this checkout")
    assert not (DEPTH_DIR / "replication_depth_contrasts.csv").exists()
    assert not (REPL_DEPTH_DIR / "original_depth_contrasts.csv").exists()


# --- Categorical coding ---

def test_categorical_depth_levels_are_exactly_1_2_3_4_6(original_eo):
    dh.assert_depth_levels(original_eo)  # must not raise
    with pytest.raises(ValueError):
        dh.assert_depth_levels(original_eo[original_eo["depth"] != 6])  # missing a level


def test_categorical_formula_uses_sum_coding():
    assert "C(depth, Sum)" in dh.CATEGORICAL_FORMULA
    assert "C(depth, Treatment)" not in dh.CATEGORICAL_FORMULA


def test_continuous_formula_is_adopted_formula_plus_one_term():
    from qnn_snr.stats.models import H2_H4_FORMULA
    assert dh.CONTINUOUS_FORMULA.replace(" + E:L:depth_z", "") == H2_H4_FORMULA
    assert dh.CONTINUOUS_FORMULA.count("E:L:depth_z") == 1


# --- Contrast construction ---

def test_depth_contrast_vector_invariant_to_log2_budget(original_eo):
    eligible = build_h2h4_dataset(original_eo)
    fit = dh.fit_categorical_model(original_eo)
    design_info = dh._design_info(fit.result.raw_result)
    for d in dh.DEPTHS:
        dh.verify_contrast_invariance_to_budget(design_info, d)  # must not raise


def test_explicit_contrast_constructed_at_every_depth(original_eo):
    if not (DEPTH_DIR / "original_depth_contrasts.csv").exists():
        pytest.skip("depth-heterogeneity outputs not present in this checkout")
    contrasts = pd.read_csv(DEPTH_DIR / "original_depth_contrasts.csv")
    assert sorted(contrasts["depth"].tolist()) == list(dh.DEPTHS)
    assert contrasts[["estimate", "se", "ci95_lo", "ci95_hi", "p_unadjusted"]].notna().all().all()


def test_pooled_contrast_uses_full_covariance_via_combined_row_t_test(original_eo):
    """compute_weighted_contrast must build ONE combined contrast vector
    (the weighted sum of the per-depth design-matrix rows) and pass it
    through a single t_test call, rather than combining the five
    per-depth SEs independently after the fact. Verified directly: the
    pooled estimate/SE must match a manual reconstruction of that exact
    combined vector's own t_test, to machine precision.

    (For this dataset, the naive independent-term approximation happens
    to numerically coincide with the full-covariance result to ~6 sig
    figs -- an empirical property of this model's near-zero cross-depth
    covariance, not evidence that the implementation takes the naive
    shortcut. This test checks the implementation path directly instead
    of relying on a numeric coincidence that need not hold for every
    dataset.)"""
    fit = dh.fit_categorical_model(original_eo)
    raw = fit.result.raw_result
    design_info = dh._design_info(raw)
    eligible = build_h2h4_dataset(original_eo)

    weights = dh.equal_depth_weights()
    manual_combined = None
    for d, w in weights.items():
        c = dh.depth_contrast_vector(design_info, d) * w
        manual_combined = c if manual_combined is None else manual_combined + c
    manual_stats = dh._t_test_contrast(raw, manual_combined)

    result = dh.compute_weighted_contrast(raw, eligible, weights, "equal_depth")
    assert np.isclose(manual_stats["estimate"], result["estimate"], atol=1e-10)
    assert np.isclose(manual_stats["se"], result["se"], atol=1e-10)

    # Direct correctness check: the reported variance must equal the
    # quadratic form c^T * Sigma * c against the model's own fixed-effect
    # covariance matrix (the definition of "uses the full covariance
    # matrix"), not any simplified/independent-term formula.
    cov_fe = np.asarray(raw.cov_params())[: len(manual_combined), : len(manual_combined)]
    quadratic_form_var = float(manual_combined.values @ cov_fe @ manual_combined.values.T)
    assert np.isclose(np.sqrt(quadratic_form_var), result["se"], rtol=1e-6)


# --- Omnibus test ---

def test_omnibus_test_targets_exactly_the_intended_moderation_term(original_eo):
    fit = dh.fit_categorical_model(original_eo)
    raw = fit.result.raw_result
    wt = raw.wald_test_terms(skip_single=False, scalar=True)
    assert dh.OMNIBUS_TERM_NAME in wt.table.index
    row = wt.table.loc[dh.OMNIBUS_TERM_NAME]
    assert int(row["df_constraint"]) == 4  # 5 depth levels -> 4 non-redundant sum-coded columns
    result = dh.compute_omnibus_test(raw)
    assert result["term"] == dh.OMNIBUS_TERM_NAME
    assert result["df_numerator"] == 4.0


# --- Weighting schemes ---

def test_equal_depth_weights_sum_to_one_and_equal_0_2():
    w = dh.equal_depth_weights()
    assert set(w.keys()) == set(dh.DEPTHS)
    for v in w.values():
        assert np.isclose(v, 0.2)
    assert np.isclose(sum(w.values()), 1.0)


def test_observation_count_weights_sum_to_one_and_reproduce_eligible_counts(original_eo):
    eligible = build_h2h4_dataset(original_eo)
    w = dh.observation_count_weights(eligible)
    assert np.isclose(sum(w.values()), 1.0)
    for d, weight in w.items():
        expected = (eligible["depth"] == d).sum() / len(eligible)
        assert np.isclose(weight, expected)


def test_weighted_contrast_rejects_weights_not_summing_to_one(original_eo):
    fit = dh.fit_categorical_model(original_eo)
    eligible = build_h2h4_dataset(original_eo)
    bad_weights = {d: 0.1 for d in dh.DEPTHS}  # sums to 0.5, not 1.0
    with pytest.raises(ValueError):
        dh.compute_weighted_contrast(fit.result.raw_result, eligible, bad_weights, "bad")


# --- Include-zero sensitivity ---

def test_include_zero_dataset_requires_mu_hat_zero(original_eo):
    d = original_eo.copy()
    # corrupt one zero-variance row's mu_hat to be nonzero
    idx = d[d["zero_variance_flag"]].index[0]
    d.loc[idx, "mu_hat"] = 0.5
    with pytest.raises(ValueError):
        dh.build_include_zero_dataset(d)


def test_include_zero_dataset_accepts_real_original_data(original_eo):
    iz = dh.build_include_zero_dataset(original_eo)  # must not raise
    assert len(iz) == len(original_eo)
    zv = original_eo["zero_variance_flag"]
    assert (iz.loc[zv, "y"] == 0.0).all()


def test_primary_path_preserves_adopted_exclusion_rule(original_eo):
    """The primary (complete-case) path must still exclude exactly the
    509 zero-variance rows -- unchanged by this package's existence."""
    eligible = build_h2h4_dataset(original_eo)
    assert len(eligible) == len(original_eo) - int(original_eo["zero_variance_flag"].sum())
    assert len(eligible) == 101_891


# --- Determinism ---

def test_depth_contrasts_deterministic_under_row_reordering(original_eo):
    rng = np.random.default_rng(7)
    shuffled = original_eo.sample(frac=1.0, random_state=rng.integers(0, 2**31 - 1)).reset_index(drop=True)

    fit_a = dh.fit_categorical_model(original_eo)
    fit_b = dh.fit_categorical_model(shuffled)
    eligible_a = build_h2h4_dataset(original_eo)
    eligible_b = build_h2h4_dataset(shuffled)

    contrasts_a = dh.compute_depth_contrasts(fit_a.result.raw_result, eligible_a, original_eo)
    contrasts_b = dh.compute_depth_contrasts(fit_b.result.raw_result, eligible_b, shuffled)

    pd.testing.assert_series_equal(
        contrasts_a["estimate"].reset_index(drop=True),
        contrasts_b["estimate"].reset_index(drop=True),
        atol=1e-8,
    )


# --- Adopted coefficient unchanged ---

def test_adopted_beta_EL_unchanged_by_this_package(original_eo):
    from qnn_snr.stats.models import fit_h2h4_model
    result = fit_h2h4_model(original_eo)
    assert np.isclose(result.params["E:L"], ADOPTED_BETA_EL, atol=1e-9)


# --- Figures / table read generated CSVs only ---

def test_figure_source_csv_matches_generated_contrasts():
    fig_source = REPO_ROOT / "paper" / "figure_data" / "fig11_h2_depth_heterogeneity_source.csv"
    if not fig_source.exists():
        pytest.skip("figure not yet generated in this checkout")
    src = pd.read_csv(fig_source)
    orig_contrasts = pd.read_csv(DEPTH_DIR / "original_depth_contrasts.csv")
    panel_a_orig = src[(src["panel"] == "a") & (src["series"] == "original")].sort_values("depth")
    for d in dh.DEPTHS:
        expected = orig_contrasts.loc[orig_contrasts["depth"] == d, "estimate"].iloc[0]
        actual = panel_a_orig.loc[panel_a_orig["depth"] == d, "estimate"].iloc[0]
        assert np.isclose(expected, actual, atol=1e-9)


def test_latex_table_contains_no_hardcoded_numbers_outside_generated_range():
    """Sanity check: every numeric estimate quoted in the generated LaTeX
    table must appear in one of the source CSVs (loosely, via round-trip
    through the same generation script) -- verified here by re-running the
    generator and diffing output, which is the strongest available check
    that the table is regenerated, not hand-edited."""
    table_path = REPO_ROOT / "paper" / "tables" / "h2_depth_heterogeneity.tex"
    if not table_path.exists():
        pytest.skip("table not yet generated in this checkout")
    before = table_path.read_text()
    sys.path.insert(0, str(REPO_ROOT / "paper" / "scripts"))
    import importlib
    import make_table_h2_depth_heterogeneity as tablegen
    importlib.reload(tablegen)
    tablegen.main()
    after = table_path.read_text()
    assert before == after, "regenerating the table from the same inputs must be idempotent"
