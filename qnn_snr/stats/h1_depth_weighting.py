"""Prospectively planned post-primary H1 depth/weighting utilities."""
from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import patsy
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests

from qnn_snr.stats.factor_coding import add_centered_factors
from qnn_snr.stats.models import OPTIMIZER_FALLBACK_ORDER, build_h1_dataset, fit_mixed_model

DEPTHS = (1, 2, 3, 4, 6)
Z975 = 1.959963984540054
CATEGORICAL_FORMULA = (
    "a ~ E_c*L_c*R_c + C(depth, Sum) + E_c:C(depth, Sum) "
    "+ L_c:C(depth, Sum) + R_c:C(depth, Sum) + E_c:L_c:C(depth, Sum)"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_validated_h1(exact: pd.DataFrame, dataset: str) -> tuple[pd.DataFrame, dict]:
    """Validate the frozen exact-gradient scientific table and add response/coding."""
    key = ["initialization_id", "configuration_id", "depth", "parameter_id"]
    required = set(key + ["analysis_mode", "budget", "E", "L", "R", "exact_gradient", "initialization_seed"])
    missing = required - set(exact.columns)
    if missing:
        raise ValueError(f"{dataset}: missing columns {sorted(missing)}")
    d = exact.copy()
    checks = {
        "dataset": dataset,
        "rows": int(len(d)),
        "duplicate_scientific_keys": int(d.duplicated(key).sum()),
        "analysis_modes": sorted(d.analysis_mode.unique().tolist()),
        "budget_values": sorted(int(x) for x in d.budget.unique()),
        "configurations": sorted(int(x) for x in d.configuration_id.unique()),
        "depths": sorted(int(x) for x in d.depth.unique()),
        "initialization_clusters": int(d.initialization_id.nunique()),
        "rows_by_depth": {str(k): int(v) for k, v in d.groupby("depth").size().items()},
        "parameter_counts_by_depth": {str(k): int(v) for k, v in d.groupby("depth").parameter_id.nunique().items()},
    }
    expected_rows = {"1": 1600, "2": 3200, "3": 4800, "4": 6400, "6": 9600}
    expected_params = {"1": 4, "2": 8, "3": 12, "4": 16, "6": 24}
    errors = []
    if checks["rows"] != 25600: errors.append("row count")
    if checks["duplicate_scientific_keys"]: errors.append("duplicate scientific keys")
    if checks["analysis_modes"] != ["statevector_exact"]: errors.append("analysis mode")
    if checks["budget_values"] != [0]: errors.append("budget duplication")
    if checks["configurations"] != list(range(1, 9)): errors.append("configurations")
    if checks["depths"] != list(DEPTHS): errors.append("depths")
    if checks["initialization_clusters"] != 50: errors.append("initializations")
    if checks["rows_by_depth"] != expected_rows: errors.append("rows by depth")
    if checks["parameter_counts_by_depth"] != expected_params: errors.append("parameters by depth")
    if not np.isfinite(d.exact_gradient).all(): errors.append("nonfinite gradient")
    cell_sizes = d.groupby(["initialization_id", "depth", "parameter_id"]).size()
    checks["configuration_rows_per_matched_parameter"] = sorted(int(x) for x in cell_sizes.unique())
    if checks["configuration_rows_per_matched_parameter"] != [8]: errors.append("unbalanced matched cells")
    combos = d.groupby(["initialization_id", "depth", "parameter_id"])[["E", "L", "R"]].apply(
        lambda x: len(set(map(tuple, x.to_numpy())))
    )
    checks["factor_combinations_per_matched_parameter"] = sorted(int(x) for x in combos.unique())
    if checks["factor_combinations_per_matched_parameter"] != [8]: errors.append("factor coverage")
    per_init = d.groupby(["initialization_id", "depth"]).parameter_id.nunique().unstack()
    for depth, count in zip(DEPTHS, (4, 8, 12, 16, 24)):
        if not (per_init[depth] == count).all(): errors.append(f"parameter nesting D={depth}")
    out = add_centered_factors(build_h1_dataset(d))
    checks["centered_support"] = {c: sorted(out[c].unique().tolist()) for c in ("E_c", "L_c", "R_c")}
    checks["finite_response"] = bool(np.isfinite(out.a).all())
    if any(v != [-0.5, 0.5] for v in checks["centered_support"].values()): errors.append("centered coding")
    if not checks["finite_response"]: errors.append("nonfinite response")
    checks["errors"] = errors
    checks["passed"] = not errors
    if errors:
        raise ValueError(f"{dataset}: validation failed: {errors}")
    return out.sort_values(key).reset_index(drop=True), checks


@dataclass
class FitBundle:
    result: object
    warnings: list[str]


def fit_categorical_mixed(data: pd.DataFrame) -> FitBundle:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = fit_mixed_model(CATEGORICAL_FORMULA, data, "a")
    return FitBundle(result, sorted(set(f"{w.category.__name__}: {w.message}" for w in caught)))


def _design_row(design_info, depth: int, e: float, l: float, r: float) -> pd.Series:
    frame = pd.DataFrame({"E_c": [e], "L_c": [l], "R_c": [r], "depth": [depth]})
    return patsy.build_design_matrices([design_info], frame, return_type="dataframe")[0].iloc[0]


def depth_contrast_vector(design_info, depth: int) -> pd.Series:
    """Centered E:L difference-in-differences, equally averaged over R."""
    pieces = []
    for r in (-0.5, 0.5):
        pieces.append(
            _design_row(design_info, depth, 0.5, 0.5, r)
            - _design_row(design_info, depth, 0.5, -0.5, r)
            - _design_row(design_info, depth, -0.5, 0.5, r)
            + _design_row(design_info, depth, -0.5, -0.5, r)
        )
    return (pieces[0] + pieces[1]) / 2


def contrast_matrix(raw_result) -> pd.DataFrame:
    info = raw_result.model.data.design_info
    matrix = pd.DataFrame([depth_contrast_vector(info, d) for d in DEPTHS], index=DEPTHS)
    matrix.index.name = "depth"
    params = raw_result.fe_params if hasattr(raw_result, "fe_params") else raw_result.params
    if matrix.shape[1] != len(params):
        raise ValueError("contrast/design fixed-effect dimension mismatch")
    return matrix


def fixed_covariance(raw_result) -> pd.DataFrame:
    params = raw_result.fe_params if hasattr(raw_result, "fe_params") else raw_result.params
    names = list(params.index)
    return raw_result.cov_params().loc[names, names]


def summarize_contrasts(raw_result, data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    c = contrast_matrix(raw_result)
    params = raw_result.fe_params if hasattr(raw_result, "fe_params") else raw_result.params
    beta = params.loc[c.columns].to_numpy()
    v = fixed_covariance(raw_result).loc[c.columns, c.columns].to_numpy()
    cvct = c.to_numpy() @ v @ c.to_numpy().T
    estimates = c.to_numpy() @ beta
    ses = np.sqrt(np.diag(cvct))
    p = 2 * stats.norm.sf(np.abs(estimates / ses))
    p_holm = multipletests(p, method="holm")[1]
    rows = []
    for i, depth in enumerate(DEPTHS):
        rows.append({
            "depth": depth, "estimate": estimates[i], "se": ses[i],
            "ci_lo": estimates[i] - Z975 * ses[i], "ci_hi": estimates[i] + Z975 * ses[i],
            "p_raw": p[i], "p_holm_within_dataset": p_holm[i],
            "n_rows": int((data.depth == depth).sum()),
            "n_matched_parameters_per_initialization": int(data.loc[data.depth == depth, "parameter_id"].nunique()),
            "n_initialization_clusters": int(data.initialization_id.nunique()),
            "contrast_expression": f"E_c:L_c at D={depth}, averaged equally over R_c",
            "contrast_vector_nonzero": ";".join(f"{k}={x:.17g}" for k, x in c.loc[depth].items() if abs(x) > 1e-14),
        })
    cov = pd.DataFrame(cvct, index=DEPTHS, columns=DEPTHS)
    cov.index.name = "depth"
    return pd.DataFrame(rows), c, cov


def equal_weights() -> dict[int, float]:
    return {d: 0.2 for d in DEPTHS}


def observation_weights(data: pd.DataFrame) -> dict[int, float]:
    counts = data.groupby("depth").size()
    return {d: float(counts[d] / counts.sum()) for d in DEPTHS}


def parameter_weights(data: pd.DataFrame) -> dict[int, float]:
    counts = data.groupby("depth").parameter_id.nunique()
    return {d: float(counts[d] / counts.sum()) for d in DEPTHS}


def weighted_summary(depth: pd.DataFrame, cov: pd.DataFrame, weights: dict[int, float], label: str) -> dict:
    if set(weights) != set(DEPTHS) or not np.isclose(sum(weights.values()), 1):
        raise ValueError("weights must cover all depths and sum to one")
    ordered = depth.set_index("depth").loc[list(DEPTHS), "estimate"].to_numpy()
    w = np.array([weights[d] for d in DEPTHS])
    estimate = float(w @ ordered)
    se = float(np.sqrt(w @ cov.loc[list(DEPTHS), list(DEPTHS)].to_numpy() @ w))
    return {"estimand": label, "estimate": estimate, "se": se,
            "ci_lo": estimate-Z975*se, "ci_hi": estimate+Z975*se,
            "p_raw_descriptive": float(2*stats.norm.sf(abs(estimate/se))),
            **{f"weight_D{d}": weights[d] for d in DEPTHS}}


def moderation_test(raw_result) -> dict:
    c_frame = contrast_matrix(raw_result)
    c = c_frame.to_numpy()
    restriction = c[1:] - c[0]
    params = raw_result.fe_params if hasattr(raw_result, "fe_params") else raw_result.params
    beta = params.loc[c_frame.columns].to_numpy()
    covariance = fixed_covariance(raw_result).loc[c_frame.columns, c_frame.columns].to_numpy()
    effect = restriction @ beta
    restriction_covariance = restriction @ covariance @ restriction.T
    statistic = float(effect @ np.linalg.pinv(restriction_covariance) @ effect)
    df = int(np.linalg.matrix_rank(restriction))
    return {"statistic": statistic, "df": df, "p_value": float(stats.chi2.sf(statistic, df)),
            "restriction": "D2-D1=D3-D1=D4-D1=D6-D1=0"}


def cluster_robust_analysis(data: pd.DataFrame) -> tuple[pd.DataFrame, dict, dict]:
    ols = smf.ols(CATEGORICAL_FORMULA, data=data).fit(
        cov_type="cluster", cov_kwds={"groups": data["initialization_id"], "use_correction": True}
    )
    depth, _, _ = summarize_contrasts(ols, data)
    joint = moderation_test(ols)
    meta = {"covariance": "cluster(initialization_id), finite-sample correction", "n_clusters": int(data.initialization_id.nunique()),
            "df_resid": float(ols.df_resid), "design_rank": int(np.linalg.matrix_rank(ols.model.exog))}
    return depth, joint, meta
