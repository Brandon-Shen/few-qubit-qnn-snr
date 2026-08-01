"""Post-run H2 depth-heterogeneity analysis (not part of the confirmatory
H1-H4 family; no Holm correction is applied to anything here).

Per verification/h2_depth_heterogeneity_plan.md. Extends
qnn_snr.stats.models rather than duplicating it: every fit in this module
goes through fit_mixed_model / build_h2h4_dataset, with two added
formulas (a continuous E:L:depth_z moderation term, and a categorical
C(depth, Sum) moderation model) and a contrast-construction layer built
directly on top of patsy's own design_info, so no coefficient name or
position is ever hardcoded.

Primary questions this module answers (see the plan for full definitions):
  1. Does a single (categorical) model support E:L varying with depth?
  2. Continuous vs. categorical depth treatment.
  3. Does the shallow-depth sign reversal survive the matched mixed model,
     cluster-robust inference, and include-zero-as-zero-SNR treatment?
  4/5/6. Replication comparison, weighting schemes, manuscript claims --
     computed by the runner script from this module's outputs.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import patsy
import statsmodels.formula.api as smf

from qnn_snr.stats.models import (
    CONFIRMATORY_MODE,
    H2_H4_FORMULA,
    MixedModelResult,
    build_h2h4_dataset,
    fit_mixed_model,
)

Z975 = 1.959963984540054
DEPTHS = (1, 2, 3, 4, 6)

CONTINUOUS_FORMULA = (
    "y ~ E*L*R + depth_z + log2_budget + E:depth_z + L:depth_z + R:depth_z "
    "+ E:L:depth_z + L:R:depth_z"
)
CATEGORICAL_FORMULA = (
    "y ~ E*L*R + C(depth, Sum) + log2_budget "
    "+ E:C(depth, Sum) + L:C(depth, Sum) + R:C(depth, Sum) "
    "+ E:L:C(depth, Sum) + L:R:C(depth, Sum)"
)
OMNIBUS_TERM_NAME = "E:L:C(depth, Sum)"

assert H2_H4_FORMULA in CONTINUOUS_FORMULA.replace(" + E:L:depth_z", ""), (
    "CONTINUOUS_FORMULA must be the adopted H2_H4_FORMULA plus exactly one new term"
)


def assert_single_confirmatory_mode(df: pd.DataFrame) -> None:
    modes = df["analysis_mode"].unique().tolist()
    if modes != [CONFIRMATORY_MODE]:
        raise ValueError(
            f"expected exactly one analysis_mode ({CONFIRMATORY_MODE!r}), found {modes!r} -- "
            f"depth-heterogeneity analyses must never see pooled or diagnostic-mode rows."
        )


def assert_depth_levels(df: pd.DataFrame) -> None:
    levels = sorted(int(d) for d in df["depth"].unique())
    if levels != list(DEPTHS):
        raise ValueError(f"expected depth levels {list(DEPTHS)}, found {levels}")


@dataclass
class FitWithWarnings:
    result: MixedModelResult
    warnings_captured: list[str] = field(default_factory=list)


def _fit_with_warning_capture(formula: str, df: pd.DataFrame, response_col: str) -> FitWithWarnings:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = fit_mixed_model(formula, df, response_col)
    messages = [f"{w.category.__name__}: {w.message}" for w in caught]
    return FitWithWarnings(result=result, warnings_captured=messages)


def build_include_zero_dataset(eo_df: pd.DataFrame) -> pd.DataFrame:
    """Phase 1F: include zero-variance cells as SNR_est=0 (y=arcsinh(0)=0),
    instead of excluding them. Hard precondition: every zero-variance row
    must have mu_hat==0 -- raises otherwise, never silently proceeds."""
    assert_single_confirmatory_mode(eo_df)
    zv = eo_df[eo_df["zero_variance_flag"]]
    offenders = zv[zv["mu_hat"] != 0]
    if len(offenders) > 0:
        raise ValueError(
            f"{len(offenders)} zero-variance row(s) have mu_hat != 0 -- the include-zero "
            f"sensitivity path is only valid when every excluded cell's mean gradient is "
            f"exactly zero. Offending rows (first 5):\n{offenders.head()}"
        )
    d = eo_df.copy()
    d.loc[d["zero_variance_flag"], "SNR_est"] = 0.0
    d["y"] = np.arcsinh(d["SNR_est"])
    return d


def fit_continuous_model(eo_df: pd.DataFrame) -> FitWithWarnings:
    assert_single_confirmatory_mode(eo_df)
    assert_depth_levels(eo_df)
    dataset = build_h2h4_dataset(eo_df)
    return _fit_with_warning_capture(CONTINUOUS_FORMULA, dataset, "y")


def fit_categorical_model(eo_df: pd.DataFrame) -> FitWithWarnings:
    assert_single_confirmatory_mode(eo_df)
    assert_depth_levels(eo_df)
    dataset = build_h2h4_dataset(eo_df)
    return _fit_with_warning_capture(CATEGORICAL_FORMULA, dataset, "y")


def _design_info(raw_result):
    return raw_result.model.data.design_info


def _depth_diff_in_diff_row(design_info, depth: int, r_value: int, log2_budget: float) -> pd.Series:
    def row(e, l, r):
        d = pd.DataFrame({"E": [float(e)], "L": [float(l)], "R": [float(r)],
                           "depth": [depth], "log2_budget": [log2_budget]})
        mat = patsy.build_design_matrices([design_info], d, return_type="dataframe")[0]
        return mat.iloc[0]

    return row(1, 1, r_value) - row(1, 0, r_value) - row(0, 1, r_value) + row(0, 0, r_value)


def depth_contrast_vector(design_info, depth: int, log2_budget: float = 9.0) -> pd.Series:
    """E:L difference-in-differences at a given depth, marginalized
    equally over R (weight 0.5/0.5), as a single design-matrix row
    (contrast vector). Verified (by the caller, see verify_contrast_invariance)
    to not depend on the chosen log2_budget value."""
    r0 = _depth_diff_in_diff_row(design_info, depth, 0, log2_budget)
    r1 = _depth_diff_in_diff_row(design_info, depth, 1, log2_budget)
    return 0.5 * r0 + 0.5 * r1


def verify_contrast_invariance_to_budget(design_info, depth: int) -> None:
    c_a = depth_contrast_vector(design_info, depth, log2_budget=8.0)
    c_b = depth_contrast_vector(design_info, depth, log2_budget=11.0)
    if not np.allclose(c_a.values, c_b.values, atol=0.0, rtol=0.0):
        raise AssertionError(
            f"depth contrast at depth={depth} depends on the chosen log2_budget value -- "
            f"this violates the plan's structural assumption that no term multiplies "
            f"log2_budget by E, L, or depth."
        )


def _t_test_contrast(raw_result, contrast_row: pd.Series) -> dict:
    r_matrix = contrast_row.values.reshape(1, -1)
    tt = raw_result.t_test(r_matrix)
    # statsmodels returns effect/sd/pvalue as either plain scalars or
    # (1,)/(1,1)-shaped arrays depending on the results-object type
    # (MixedLMResults vs. RegressionResultsWrapper) -- ravel().item()
    # handles every case uniformly rather than assuming a fixed shape.
    est = float(np.asarray(tt.effect).ravel()[0])
    se = float(np.asarray(tt.sd).ravel()[0])
    pvalue = float(np.asarray(tt.pvalue).ravel()[0])
    ci = np.asarray(tt.conf_int()).reshape(-1)
    ci_lo, ci_hi = float(ci[0]), float(ci[1])
    return {
        "estimate": est, "se": se, "ci95_lo": ci_lo, "ci95_hi": ci_hi,
        "p_unadjusted": pvalue,
    }


def compute_depth_contrasts(raw_result, eligible_df: pd.DataFrame,
                             all_cells_df: pd.DataFrame) -> pd.DataFrame:
    """One row per depth: E:L contrast from the categorical model
    (accepts either a MixedLMResults or a RegressionResultsWrapper --
    both expose .t_test and .model.data.design_info), plus eligible
    n_obs and zero-variance count at that depth (from the full,
    pre-exclusion cell set, so exclusions are always visible)."""
    raw = raw_result
    design_info = _design_info(raw)
    rows = []
    for d in DEPTHS:
        verify_contrast_invariance_to_budget(design_info, d)
        contrast = depth_contrast_vector(design_info, d)
        stats = _t_test_contrast(raw, contrast)
        n_eligible_d = int((eligible_df["depth"] == d).sum())
        cell_d = all_cells_df[all_cells_df["depth"] == d]
        n_zero_variance_d = int(cell_d["zero_variance_flag"].sum())
        rows.append({
            "depth": d, **stats, "n_obs_eligible": n_eligible_d,
            "n_zero_variance": n_zero_variance_d,
            "sign": "positive" if stats["estimate"] > 0 else ("negative" if stats["estimate"] < 0 else "zero"),
            "ci_excludes_zero": bool(stats["ci95_lo"] > 0 or stats["ci95_hi"] < 0),
        })
    return pd.DataFrame(rows)


def compute_omnibus_test(raw_result) -> dict:
    raw = raw_result
    wt = raw.wald_test_terms(skip_single=False, scalar=True)
    if OMNIBUS_TERM_NAME not in wt.table.index:
        raise KeyError(
            f"expected term {OMNIBUS_TERM_NAME!r} in wald_test_terms() output, "
            f"found terms: {list(wt.table.index)}"
        )
    row = wt.table.loc[OMNIBUS_TERM_NAME]
    return {
        "term": OMNIBUS_TERM_NAME,
        "statistic": float(row["statistic"]),
        "df_numerator": float(row["df_constraint"]),
        "df_denominator": None,  # not defined for this chi2-based Wald test on a mixed model
        "p_unadjusted": float(row["pvalue"]),
        "test_type": "joint Wald chi-square (statsmodels wald_test_terms, scalar=True)",
    }


def compute_weighted_contrast(raw_result, eligible_df: pd.DataFrame, weights: dict[int, float],
                               label: str) -> dict:
    raw = raw_result
    design_info = _design_info(raw)
    total_w = sum(weights.values())
    if not np.isclose(total_w, 1.0):
        raise ValueError(f"weights for {label!r} must sum to 1.0, got {total_w}")
    combined = None
    for d, w in weights.items():
        c = depth_contrast_vector(design_info, d) * w
        combined = c if combined is None else combined + c
    stats = _t_test_contrast(raw, combined)
    return {"weighting": label, **stats, "n_obs_total": int(len(eligible_df))}


def equal_depth_weights() -> dict[int, float]:
    return {d: 1.0 / len(DEPTHS) for d in DEPTHS}


def observation_count_weights(eligible_df: pd.DataFrame) -> dict[int, float]:
    total = len(eligible_df)
    return {d: float((eligible_df["depth"] == d).sum()) / total for d in DEPTHS}


def fit_cluster_robust_categorical(eo_df: pd.DataFrame) -> object:
    """Phase 1E: identical categorical fixed-effect formula, OLS with
    cluster-robust SEs (clusters = initialization_id), statsmodels
    defaults (use_correction=True, df_correction=True)."""
    assert_single_confirmatory_mode(eo_df)
    assert_depth_levels(eo_df)
    dataset = build_h2h4_dataset(eo_df)
    model = smf.ols(CATEGORICAL_FORMULA, data=dataset)
    result = model.fit(cov_type="cluster", cov_kwds={"groups": dataset["initialization_id"]})
    return result, dataset
